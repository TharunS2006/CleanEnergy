"""Detectors that work on a workspace's stored cost history, whatever the
cloud: spend anomalies, budget risk, untagged spend."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CostSnapshot, ResourceCost, Setting
from app.services import analytics as A

ANOMALY_LOOKBACK_DAYS = 90
ANOMALY_OPEN_WINDOW = 14          # only spikes from the last 14 billed days become findings
UNTAGGED_MIN_SHARE = 0.10
UNTAGGED_MIN_AMOUNT = 5.0


def last_cost_day(db: Session, ws_id: int, book: str) -> date | None:
    d = db.query(func.max(CostSnapshot.date)).filter(
        CostSnapshot.workspace_id == ws_id, CostSnapshot.source == book).scalar()
    return date.fromisoformat(d) if d else None


def daily(db: Session, ws_id: int, book: str, end: date, days: int):
    start = end - timedelta(days=days - 1)
    rows = db.query(CostSnapshot.date, CostSnapshot.service, CostSnapshot.provider, CostSnapshot.amount).filter(
        CostSnapshot.workspace_id == ws_id, CostSnapshot.source == book,
        CostSnapshot.date >= start.isoformat(), CostSnapshot.date <= end.isoformat()).all()
    totals, by_service, provider_of = defaultdict(float), defaultdict(lambda: defaultdict(float)), {}
    for d, svc, prov, amt in rows:
        totals[d] += amt
        by_service[d][svc] += amt
        provider_of[svc] = prov
    series = [{"date": d, "amount": round(totals.get(d, 0.0), 4)} for d in A.daterange(start, days)]
    return series, by_service, provider_of


def _money(x):
    return f"${x:,.2f}"


def anomaly_signals(db: Session, ws_id: int, book: str, end: date, owner_lookup=None) -> list[dict]:
    series, by_service, provider_of = daily(db, ws_id, book, end, ANOMALY_LOOKBACK_DAYS)
    found = A.find_anomalies(series, by_service)
    cutoff = (end - timedelta(days=ANOMALY_OPEN_WINDOW - 1)).isoformat()
    out = []
    for a in found:
        if a["date"] < cutoff:
            continue
        top = a["drivers"][0] if a["drivers"] else None
        res_drivers = _resource_drivers(db, ws_id, a) if book == "live" else []
        ratio = a["amount"] / a["expected"] if a["expected"] > 0 else None
        d = date.fromisoformat(a["date"])
        title = (f"Spend on {d.strftime('%d %b')} was {ratio:.1f}x the usual" if ratio
                 else f"Unusual spend on {d.strftime('%d %b')}")
        summary = f"{_money(a['amount'])} against a usual {_money(a['expected'])}."
        if top:
            summary += f" Mostly {top['service']} (+{_money(top['increase'])}, {top['share']:.0%} of the increase)."
        if a["ongoing"]:
            summary += " It hasn't come back down yet."
        evidence = {**a, "resource_drivers": res_drivers, "rule": "robust z-score > 3.5"}
        sig = {
            "kind": "anomaly", "provider": provider_of.get(top["service"]) if top else None,
            "resource_id": res_drivers[0]["resource_id"] if res_drivers else None,
            "resource_name": (res_drivers[0]["name"] if res_drivers else (top["service"] if top else "")),
            "resource_type": "service" if not res_drivers else "resource",
            "title": title, "summary": summary, "evidence": evidence,
            "monthly_impact": a["monthly_impact"], "impact_basis": a["impact_basis"],
            "confidence": a["confidence"], "fix": [],
        }
        if res_drivers and owner_lookup:
            who = owner_lookup(res_drivers[0]["resource_id"])
            sig["owner"], sig["owner_source"] = who.get("principal"), who.get("source")
            evidence["owner_trail"] = who
        out.append(sig)
    return out


def _resource_drivers(db: Session, ws_id: int, a: dict, top_n: int = 3) -> list[dict]:
    days = [a["date"]] + a["baseline_days"]
    rows = db.query(ResourceCost.resource_id, ResourceCost.date, ResourceCost.amount).filter(
        ResourceCost.workspace_id == ws_id, ResourceCost.date.in_(days)).all()
    grid = defaultdict(lambda: defaultdict(float))
    for rid, d, amt in rows:
        grid[rid][d] += amt
    out = []
    for rid, per_day in grid.items():
        usual = A.median([per_day.get(d, 0.0) for d in a["baseline_days"]])
        delta = per_day.get(a["date"], 0.0) - usual
        if delta > 0:
            out.append({"resource_id": rid, "name": rid.split("/")[-1], "amount": round(per_day.get(a["date"], 0), 2),
                        "usual": round(usual, 2), "increase": round(delta, 2)})
    out.sort(key=lambda r: r["increase"], reverse=True)
    return out[:top_n]


def budget_amount(db: Session, ws_id: int) -> float | None:
    row = db.query(Setting).filter_by(workspace_id=ws_id, key="budget_monthly").first()
    return float(row.value) if row else None


def budget_signal(db: Session, ws_id: int, book: str, end: date, today: date) -> tuple[dict | None, dict | None]:
    budget = budget_amount(db, ws_id)
    series, by_service, _ = daily(db, ws_id, book, end, 60)
    fc = A.month_forecast({s["date"]: s["amount"] for s in series}, end, today, budget)
    if not budget or fc["forecast"] <= budget:
        return None, fc
    over = fc["forecast"] / budget
    complete = fc["days_remaining"] == 0
    # What grew: month-to-date by service vs the same days of the previous month.
    first = end.replace(day=1)
    prev_first = (first - timedelta(days=1)).replace(day=1)
    n = (end - first).days + 1
    now_by, prev_by = defaultdict(float), defaultdict(float)
    for d, svcs in by_service.items():
        dd = date.fromisoformat(d)
        for svc, amt in svcs.items():
            if first <= dd <= end:
                now_by[svc] += amt
            elif prev_first <= dd < prev_first + timedelta(days=n):
                prev_by[svc] += amt
    growth = sorted(({"service": k, "this_month": round(v, 2), "last_month_same_days": round(prev_by.get(k, 0), 2),
                      "change": round(v - prev_by.get(k, 0), 2)} for k, v in now_by.items()),
                    key=lambda x: x["change"], reverse=True)[:5]
    fc_small = {k: v for k, v in fc.items() if k != "path"}
    breach = fc.get("breach_date")
    if complete:
        title = f"{fc['month_label']} ended {over - 1:.0%} over budget"
    else:
        title = f"On track to exceed the {fc['month_label']} budget by {over - 1:.0%}"
    summary = (f"{'Spent' if complete else 'Forecast'} {_money(fc['forecast'])} against a budget of {_money(budget)}"
               + (f"; the budget is passed on {date.fromisoformat(breach).strftime('%d %b')}." if breach else "."))
    return {
        "kind": "budget_risk", "provider": None, "resource_id": None, "resource_name": fc["month_label"],
        "resource_type": "budget", "title": title, "summary": summary,
        "evidence": {"forecast": fc_small, "budget": budget, "overrun_ratio": round(over, 4),
                     "breach_date": breach, "growth": growth, "rule": "forecast > budget"},
        "monthly_impact": round(fc["forecast"] - budget, 2), "impact_basis": "forecast minus budget",
        "confidence": 0.95 if complete else (0.75 if fc["billed_days_used"] >= 14 else 0.6),
        "fix": [],
    }, fc


def untagged_signal(total_30d: float, untagged_30d: float, top: list[dict], coverage: float | None,
                    source_note: str) -> dict | None:
    if total_30d <= 0:
        return None
    share = untagged_30d / total_30d
    if share < UNTAGGED_MIN_SHARE or untagged_30d < UNTAGGED_MIN_AMOUNT:
        return None
    summary = f"{share:.0%} of the last 30 days' spend ({_money(untagged_30d)}) sits on resources with no tags."
    if coverage is not None:
        summary += f" CloudPulse still traced a creator for {coverage:.0%} of it through the audit log."
    return {
        "kind": "untagged_spend", "provider": None, "resource_id": None, "resource_name": "Tag coverage",
        "resource_type": "governance", "title": f"{share:.0%} of spend has no owner tag", "summary": summary,
        "evidence": {"share": round(share, 4), "untagged_30d": untagged_30d, "total_30d": total_30d,
                     "top_untagged": top[:10], "owner_coverage": coverage, "source": source_note,
                     "rule": "untagged share >= 10% and >= $5"},
        "monthly_impact": round(untagged_30d / 30 * A.DAYS_PER_MONTH, 2), "impact_basis": "untagged spend per month",
        "confidence": 0.9,
        "fix": [{"label": "Require an owner tag on new resources (Azure Policy, built-in definition)",
                 "cmd": "az policy assignment create --name require-owner-tag --policy "
                        "871b6d14-10aa-478d-b590-94f262ecfa99 --params '{\"tagName\":{\"value\":\"owner\"}}' "
                        "--scope /subscriptions/<subscription-id>"}],
    }


def focus_tag_stats(db: Session, ws_id: int, end: date) -> tuple[float, float]:
    start = (end - timedelta(days=29)).isoformat()
    rows = db.query(CostSnapshot.amount, CostSnapshot.tagged_amount).filter(
        CostSnapshot.workspace_id == ws_id, CostSnapshot.source == "focus",
        CostSnapshot.date >= start, CostSnapshot.date <= end.isoformat(),
        CostSnapshot.tagged_amount.isnot(None)).all()
    total = sum(a for a, _ in rows)
    tagged = sum(t for _, t in rows)
    return round(total, 2), round(total - tagged, 2)
