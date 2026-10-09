"""One sync of one workspace: read the clouds, store the data, turn signals
into findings, verify fixes, rescore.

Steps (each recorded on the CollectionRun so the page can show progress):
  1. for each connection: check sign-in, scan, store costs, find owners,
     update resource findings
  2. workspace detectors: anomalies, budget risk, untagged spend
  3. verification of resolved findings
  4. rescore everything still open (priority grows with age)
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import (
    CloudConnection, CollectionRun, CostSnapshot, Finding, FindingEvent, Membership, ResourceCost, Setting, User, Workspace,
)
from app.security import generate_password, hash_password
from app.services import aws_collector, azure_collector, demo_data, findings, focus_importer, owners
from app.services import workspace_detectors as W
from app.services.connections import build_target
from app.services.prices import PriceBook

log = logging.getLogger("cloudpulse")
SAMPLE_DATASET = "focus-sample"
BACKFILL_DAYS = 90
REFRESH_DAYS = 10   # Azure revises recent days, so the last 10 are fetched again every sync


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ==========================================================================
# storage
# ==========================================================================
def store_costs(db: Session, ws_id: int, rows: list[dict], source: str, dataset: str | None = None,
                provider: str | None = None, start: date | None = None):
    base = db.query(CostSnapshot).filter(CostSnapshot.workspace_id == ws_id, CostSnapshot.source == source)
    if source == "focus":
        base.delete(synchronize_session=False)
    else:
        q = base.filter(CostSnapshot.provider == provider)
        if start:
            q = q.filter(CostSnapshot.date >= start.isoformat())
        q.delete(synchronize_session=False)
    db.bulk_save_objects([
        CostSnapshot(workspace_id=ws_id, provider=r["provider"], service=r["service"], date=r["date"],
                     amount=r["amount"], tagged_amount=r.get("tagged_amount"),
                     currency=r.get("currency", "USD"), source=source, dataset=dataset)
        for r in rows
    ])
    db.commit()


def store_resource_costs(db: Session, ws_id: int, provider: str, rows: list[dict], start: date | None):
    q = db.query(ResourceCost).filter(ResourceCost.workspace_id == ws_id, ResourceCost.provider == provider)
    if start:
        q = q.filter(ResourceCost.date >= start.isoformat())
    q.delete(synchronize_session=False)
    db.bulk_save_objects([
        ResourceCost(workspace_id=ws_id, provider=provider, resource_id=r["resource_id"].lower(),
                     service=r.get("service"), date=r["date"], amount=r["amount"])
        for r in rows
    ])
    db.commit()


def _step(db: Session, run: CollectionRun, text: str):
    run.step = text
    db.commit()


# ==========================================================================
# per provider
# ==========================================================================
def _sync_azure(db: Session, ws: Workspace, conn: CloudConnection, target, today: date, entry: dict, ctx: dict):
    prices = PriceBook(db)
    last = db.query(CostSnapshot.date).filter_by(workspace_id=ws.id, source="live", provider="azure") \
        .order_by(CostSnapshot.date.desc()).first()
    cost_start = today - timedelta(days=BACKFILL_DAYS)
    if last:
        cost_start = max(cost_start, date.fromisoformat(last[0]) - timedelta(days=REFRESH_DAYS))
    result = azure_collector.scan(target, prices, cost_start, today)
    entry["errors"] = result["errors"]
    entry["stats"] = result["stats"]

    if result["costs"] is not None:
        store_costs(db, ws.id, result["costs"], "live", provider="azure", start=cost_start)
    if result["resource_costs"] is not None:
        store_resource_costs(db, ws.id, "azure", result["resource_costs"], today - timedelta(days=45))
    if result["inventory"] is None:
        return  # without an inventory we can't say what's gone, so leave findings alone

    # Prefer what Azure actually billed over list prices, where the resource has cost history.
    if result["resource_costs"]:
        index = azure_collector.index_resource_costs(result["resource_costs"])
        last_day = W.last_cost_day(db, ws.id, "live")
        apply_actual_costs(result["signals"], index, last_day)

    lookup = lambda rid: azure_collector.fetch_creator(target, rid)  # noqa: E731
    owners.attach(db, ws.id, result["signals"], lookup)

    kinds = ["idle_resource"]
    if "metrics" not in result["errors"]:
        kinds += ["idle_vm", "rightsize_vm"]
    if "advisor" not in result["errors"]:
        kinds.append("advisor")
    entry["findings"] = findings.upsert_signals(
        db, ws.id, result["signals"],
        {"kinds": kinds, "provider": "azure", "id_prefix": f"/subscriptions/{target.subscription_id}"})

    # Tag coverage for the governance check (live data).
    if result["resource_costs"] is not None:
        last_day = W.last_cost_day(db, ws.id, "live")
        stats = azure_collector.tag_stats(result["inventory"], result["resource_costs"], last_day)
        top = stats["untagged"][:10]
        traced_amt = 0.0
        for u in top:
            who = owners.resolve(db, ws.id, u["id_original"], None, lookup)
            u["owner"] = who["principal"]
            if who["principal"]:
                traced_amt += u["cost_30d"]
        top_amt = sum(u["cost_30d"] for u in top)
        ctx["tags"] = {"total": stats["total_30d"], "untagged": stats["untagged_30d"], "top": top,
                       "coverage": round(traced_amt / top_amt, 4) if top_amt else None,
                       "note": "Azure resource and resource-group tags, last 30 days"}
        ctx["owner_lookup"] = lookup


def apply_actual_costs(signals: list[dict], index: dict, last_day: date | None):
    for sig in signals:
        if sig["kind"] not in ("idle_resource", "idle_vm") or not sig.get("resource_id"):
            continue
        got = azure_collector.actual_monthly(index, [sig["resource_id"]] + sig.get("extra_cost_ids", []), last_day)
        if got and got[0] > 0:
            sig["list_price_impact"] = sig["monthly_impact"]
            sig["monthly_impact"] = got[0]
            sig["impact_basis"] = f"actual billed cost, last {got[1]} days"


def _aws_signal(leak: dict) -> dict:
    rid, t = leak["resource_id"], leak["resource_type"]
    fixes = {
        "volume": [{"label": "Keep a copy first (optional)", "cmd": f"aws ec2 create-snapshot --volume-id {rid}"},
                   {"label": "Delete the volume", "cmd": f"aws ec2 delete-volume --volume-id {rid}"}],
        "elastic_ip": [{"label": "Release the address", "cmd": f"aws ec2 release-address --allocation-id {rid}"}],
        "instance": [{"label": "Terminate the instance", "cmd": f"aws ec2 terminate-instances --instance-ids {rid}"}],
    }
    name = leak.get("display_name") or rid
    titles = {"volume": f"EBS volume {name} is attached to nothing",
              "elastic_ip": f"Elastic IP {name} is attached to nothing",
              "instance": f"EC2 instance {name} is stopped; its volumes still bill"}
    return {
        "kind": "idle_resource", "provider": "aws", "resource_id": rid, "resource_name": name,
        "resource_type": t, "resource_group": "", "region": leak.get("region", ""), "tags": {},
        "title": titles.get(t, f"{name} looks idle"), "summary": leak["reason"],
        "monthly_impact": leak["estimated_monthly_waste_usd"], "impact_basis": "list price, built-in estimate",
        "confidence": 0.9, "evidence": {"rule": leak["reason"]}, "fix": fixes.get(t, []),
    }


def _sync_aws(db: Session, ws: Workspace, conn: CloudConnection, target, today: date, entry: dict, ctx: dict):
    entry["errors"] = {}
    try:
        rows = aws_collector.fetch_costs(target)
        store_costs(db, ws.id, rows, "live", provider="aws", start=today - timedelta(days=31))
    except Exception as e:  # noqa: BLE001
        entry["errors"]["spend"] = str(e).splitlines()[0][:300]
    try:
        signals = [_aws_signal(x) for x in aws_collector.fetch_leaks(target)]
    except Exception as e:  # noqa: BLE001
        entry["errors"]["inventory"] = str(e).splitlines()[0][:300]
        return
    by_id = {s["resource_id"]: s for s in signals}
    lookup = lambda rid: aws_collector.attribute(target, rid, by_id.get(rid, {}).get("resource_type"))  # noqa: E731
    owners.attach(db, ws.id, signals, lookup)
    entry["findings"] = findings.upsert_signals(db, ws.id, signals, {"kinds": ["idle_resource"], "provider": "aws"})


SYNCERS = {"azure": (azure_collector, _sync_azure), "aws": (aws_collector, _sync_aws)}


# ==========================================================================
# workspace-level
# ==========================================================================
def _workspace_findings(db: Session, ws: Workspace, book: str, today: date, ctx: dict, now: datetime,
                        source: str = "live"):
    end = W.last_cost_day(db, ws.id, book)
    if end is None:
        return {"budget_ok": None}
    lookup = ctx.get("owner_lookup")
    owner_fn = (lambda rid: owners.resolve(db, ws.id, rid, None, lookup, now)) if lookup else None
    signals = W.anomaly_signals(db, ws.id, book, end, owner_fn)
    budget_sig, fc = W.budget_signal(db, ws.id, book, end, today)
    if budget_sig:
        signals.append(budget_sig)
    kinds = ["anomaly", "budget_risk"]
    tags = ctx.get("tags")
    if tags:
        u = W.untagged_signal(tags["total"], tags["untagged"], tags["top"], tags["coverage"], tags["note"])
        kinds.append("untagged_spend")
        if u:
            signals.append(u)
    elif book == "focus":
        total, untagged = W.focus_tag_stats(db, ws.id, end)
        tags = {"total": total, "untagged": untagged}
        u = W.untagged_signal(total, untagged, [], None, "FOCUS bill Tags column, last 30 days")
        kinds.append("untagged_spend")
        if u:
            signals.append(u)
    stats = findings.upsert_signals(db, ws.id, signals, {"kinds": kinds, "provider": None}, now=now, source=source)
    series, _, _ = W.daily(db, ws.id, book, end, 14)
    billed = [(s["date"], s["amount"]) for s in series if s["amount"] > 0]
    share = (tags["untagged"] / tags["total"]) if tags and tags.get("total") else None
    return {"stats": stats, "last_cost_day": end, "recent_daily": billed, "untagged_share": share,
            "budget_ok": (fc is not None and W.budget_amount(db, ws.id) is not None
                          and fc["forecast"] <= W.budget_amount(db, ws.id))}


# ==========================================================================
# demo
# ==========================================================================
def _ensure_demo_people(db: Session, ws: Workspace) -> dict[str, User]:
    out = {}
    for email, name, role in demo_data.PEOPLE:
        u = db.query(User).filter_by(email=email).first()
        if u is None:
            u = User(email=email, name=name, password_hash=hash_password(generate_password(24)),
                     is_placeholder=True, disabled=True)
            db.add(u)
            db.commit()
        if not db.query(Membership).filter_by(user_id=u.id, workspace_id=ws.id).first():
            db.add(Membership(user_id=u.id, workspace_id=ws.id, role=role))
            db.commit()
        out[email] = u
    return out


def _sync_demo(db: Session, ws: Workspace) -> dict:
    now = demo_data.DEMO_CLOCK
    if db.query(CostSnapshot).filter_by(workspace_id=ws.id, source="focus").first() is None:
        rows = focus_importer.load_sample()
        if rows:
            store_costs(db, ws.id, rows, "focus", dataset=SAMPLE_DATASET)
    if db.query(Finding).filter_by(workspace_id=ws.id).first() is not None:
        return {"demo": {"state": "demo"}}

    if not db.query(Setting).filter_by(workspace_id=ws.id, key="budget_monthly").first():
        db.add(Setting(workspace_id=ws.id, key="budget_monthly", value=str(demo_data.DEMO_BUDGET)))
        db.commit()
    people = _ensure_demo_people(db, ws)

    start = datetime(2024, 9, 1, 10, 0)
    resolved_on = {}
    for key, steps in demo_data.SCRIPT.items():
        for day, _, action, _ in steps:
            if action == "resolve":
                resolved_on[key] = (start + timedelta(days=day)).date()
    store_resource_costs(db, ws.id, "azure", [r for r in demo_data.resource_cost_rows(resolved_on) if r["provider"] == "azure"], None)
    store_resource_costs(db, ws.id, "aws", [r for r in demo_data.resource_cost_rows(resolved_on) if r["provider"] == "aws"], None)

    signals = [{k: v for k, v in s.items() if k != "key"} for s in demo_data.SIGNALS]
    findings.upsert_signals(db, ws.id, signals, {"kinds": list(findings.RESOURCE_KINDS)}, now=start, source="demo")
    by_key = {}
    for s in demo_data.SIGNALS:
        fp = findings.fingerprint({k: v for k, v in s.items() if k != "key"})
        by_key[s["key"]] = db.query(Finding).filter_by(workspace_id=ws.id, fingerprint=fp).first()

    for key, steps in demo_data.SCRIPT.items():
        f = by_key[key]
        for day, actor_email, action, extra in steps:
            actor = people[actor_email]
            when = start + timedelta(days=day)
            if action == "assign":
                f.assignee_id = people[extra["to"]].id
                f.status = "assigned"
                findings.record(db, f, actor_email, "assigned", f"Assigned to {extra['to']}: {extra['note']}", at=when)
            elif action == "start":
                f.status = "in_progress"
                f.assignee_id = f.assignee_id or actor.id
                findings.record(db, f, actor_email, "status", f"Started working on it: {extra['note']}", at=when)
            elif action == "resolve":
                f.status, f.resolved_at, f.resolved_by = "resolved", when, actor_email
                f.assignee_id = f.assignee_id or actor.id
                f.still_detected = False
                findings.record(db, f, actor_email, "status",
                                f"Marked as fixed: {extra['note']}. CloudPulse will check on the next syncs.", at=when)
            elif action == "dismiss":
                f.status, f.status_note = "dismissed", extra["note"]
                findings.record(db, f, actor_email, "status", f"Dismissed: {extra['note']}", at=when)
            elif action == "snooze":
                f.status = "snoozed"
                f.snoozed_until = when + timedelta(days=extra["days"])
                findings.record(db, f, actor_email, "status",
                                f"Snoozed for {extra['days']} day(s): {extra['note']}", at=when)
            elif action == "comment":
                findings.record(db, f, actor_email, "comment", extra["note"], at=when)
    db.commit()

    ctx_ws = _workspace_findings(db, ws, "focus", date(2024, 9, 30), {}, now, source="demo")
    # The spike was noticed the morning after, and the ops team stopped its cause two days later.
    for f in db.query(Finding).filter_by(workspace_id=ws.id, kind="anomaly").all():
        spike = date.fromisoformat(json.loads(f.evidence)["date"])
        seen = datetime.combine(spike + timedelta(days=1), datetime.min.time()).replace(hour=6)
        fixed = seen + timedelta(days=2, hours=4)
        f.first_seen = f.last_seen = f.created_at = seen
        db.query(FindingEvent).filter_by(finding_id=f.id, kind="created").update({"at": seen})
        f.assignee_id = people["meera.ops@example.com"].id
        findings.record(db, f, "meera.ops@example.com", "assigned", "Took this: looking at the EC2 bill", at=seen + timedelta(hours=3))
        f.status, f.resolved_at, f.resolved_by = "resolved", fixed, "meera.ops@example.com"
        findings.record(db, f, "meera.ops@example.com", "status",
                        "Marked as fixed: a load test was left running over the weekend; stopped it", at=fixed)
    db.commit()

    # Verify with the real algorithm, as if each check ran a few days after the fix.
    for key, day in resolved_on.items():
        f = by_key[key]
        check_time = datetime.combine(day + timedelta(days=5), datetime.min.time()).replace(hour=6)
        findings.verify(db, ws.id, {"last_cost_day": date(2024, 9, 30)}, now=check_time, only_ids=[f.id])
    findings.verify(db, ws.id, {"last_cost_day": ctx_ws.get("last_cost_day"),
                                "recent_daily": ctx_ws.get("recent_daily"),
                                "untagged_share": ctx_ws.get("untagged_share"),
                                "budget_ok": ctx_ws.get("budget_ok")}, now=now,
                    only_ids=[f.id for f in db.query(Finding).filter_by(workspace_id=ws.id).all()
                              if f.kind in findings.WORKSPACE_KINDS])
    for f in db.query(Finding).filter_by(workspace_id=ws.id).all():
        findings.rescore(f, now)
    db.commit()
    return {"demo": {"state": "demo"}}


# ==========================================================================
# entry points
# ==========================================================================
def sync_workspace(db: Session, ws: Workspace, run: CollectionRun | None = None, today: date | None = None) -> CollectionRun:
    if run is None:
        run = CollectionRun(workspace_id=ws.id, status="running", started_at=_now())
        db.add(run)
        db.commit()
    run.status, run.started_at = "running", run.started_at or _now()
    db.commit()
    today = today or date.today()

    if ws.kind == "demo":
        _step(db, run, "Preparing the demo")
        report = _sync_demo(db, ws)
        status = "demo"
    else:
        report, ok, failed = {}, 0, 0
        ctx: dict = {}
        conns = db.query(CloudConnection).filter_by(workspace_id=ws.id, enabled=True).all()
        for conn in conns:
            module, syncer = SYNCERS.get(conn.provider, (None, None))
            entry = {"provider": conn.provider, "label": conn.label}
            report[str(conn.id)] = entry
            if module is None:
                entry.update(state="error", message=f"Unknown provider {conn.provider}")
                failed += 1
                continue
            _step(db, run, f"Signing in to {conn.label or conn.provider}")
            try:
                target = build_target(conn)
                good, info = module.check_connection(target)
            except Exception as e:  # noqa: BLE001
                good, info = False, str(e)
            if not good:
                entry.update(state="error", message=info)
                failed += 1
                continue
            entry.update(state="connected", identity=info)
            _step(db, run, f"Reading {conn.label or conn.provider}: costs, resources, usage, Advisor")
            try:
                syncer(db, ws, conn, target, today, entry, ctx)
            except Exception as e:  # noqa: BLE001
                log.exception("sync failed for connection %s", conn.id)
                db.rollback()
                entry.setdefault("errors", {})["sync"] = str(e).splitlines()[0][:300]
            if entry.get("errors"):
                # Keep older field names for the UI.
                entry["cost_error"] = entry["errors"].get("spend")
                entry["leak_error"] = entry["errors"].get("inventory")
            ok += 1

        _step(db, run, "Looking for anomalies, budget risk and untagged spend")
        wctx = _workspace_findings(db, ws, "live", today, ctx, _now()) if ok else {}
        _step(db, run, "Checking fixes")
        findings.verify(db, ws.id, {"last_cost_day": wctx.get("last_cost_day"),
                                    "recent_daily": wctx.get("recent_daily"),
                                    "untagged_share": wctx.get("untagged_share"),
                                    "budget_ok": wctx.get("budget_ok")})
        findings.rescore_active(db, ws.id)
        status = "empty" if not conns else "live" if ok and not failed else "partial" if ok else "failed"

    run.status = status
    run.step = None
    run.detail = json.dumps(report, default=str)
    run.finished_at = _now()
    db.commit()
    db.refresh(run)
    return run


def sync_all(db: Session):
    for ws in db.query(Workspace).all():
        try:
            sync_workspace(db, ws)
        except Exception:  # noqa: BLE001
            log.exception("sync failed for workspace %s", ws.slug)
            db.rollback()


def import_focus_file(db: Session, ws: Workspace, content: bytes, filename: str) -> int:
    rows = focus_importer.load_upload(content, filename)
    if not rows:
        raise ValueError("No usage rows found. Is this a FOCUS export?")
    store_costs(db, ws.id, rows, "focus", dataset=filename)
    return len(rows)
