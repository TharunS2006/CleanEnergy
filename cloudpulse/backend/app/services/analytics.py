"""CloudPulse's algorithms, as pure functions (no database, no network).

Everything here is deliberately explainable: medians, percentiles,
exponential smoothing and a weighted score. Each function documents the
exact rule it applies so the numbers on screen can be traced by hand.
"""
from __future__ import annotations

import calendar
import math
from collections import defaultdict
from datetime import date, timedelta

DAYS_PER_MONTH = 30.4  # average month length used for every "per month" figure


# ==========================================================================
# Small statistics helpers
# ==========================================================================
def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def percentile(xs, p):
    """Linear interpolation between closest ranks (the common 'type 7' rule)."""
    s = sorted(xs)
    if not s:
        return 0.0
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def mad(xs):
    """Median absolute deviation."""
    m = median(xs)
    return median([abs(x - m) for x in xs])


def daterange(start: date, days: int) -> list[str]:
    return [(start + timedelta(days=i)).isoformat() for i in range(days)]


# ==========================================================================
# 1. Anomaly detection: weekday-aware robust z-score
# ==========================================================================
Z_THRESHOLD = 3.5        # Iglewicz & Hoaglin's usual cut-off for modified z-scores
MIN_EXCESS = 1.0         # ignore spikes smaller than this (currency units)
MIN_EXCESS_SHARE = 0.20  # ...or smaller than 20% of the baseline


def _baseline_indices(i: int, first: int) -> tuple[list[int], str]:
    same_weekday = [i - 7 * k for k in (1, 2, 3, 4) if i - 7 * k >= first]
    if len(same_weekday) >= 3:
        return same_weekday, "same weekday in the previous 4 weeks"
    return list(range(max(first, i - 14), i)), "previous 14 days"


def find_anomalies(series: list[dict], by_day_service: dict | None = None) -> list[dict]:
    """Flag days that are far above their own baseline.

    For each day:
      baseline  = the same weekday in the previous 4 weeks (if at least 3 of
                  them exist), otherwise the previous 14 days
      m         = median(baseline)
      s         = 1.4826 x MAD(baseline), floored at 5% of m (and 0.01) so a
                  perfectly flat history can't make s zero
      z         = (value - m) / s
      flagged when z > 3.5 AND value - m >= max(1, 20% of m)

    Needs at least 7 billed days of history. Root cause: each service's
    increase over its own median on the same baseline days; shares add to 100%.
    Persistence: if both following days stay above m + half the excess, the
    spike is treated as ongoing and projected per month.
    """
    by_day_service = by_day_service or {}
    amounts = [float(s["amount"]) for s in series]
    try:
        first = next(i for i, a in enumerate(amounts) if a > 0)
    except StopIteration:
        return []
    out = []
    for i in range(first + 7, len(series)):
        idx, method = _baseline_indices(i, first)
        base = [amounts[j] for j in idx]
        if sum(1 for b in base if b > 0) < min(3, len(base)):
            continue
        m = median(base)
        s = max(1.4826 * mad(base), 0.05 * m, 0.01)
        x = amounts[i]
        z = (x - m) / s
        excess = x - m
        if not (z > Z_THRESHOLD and excess >= max(MIN_EXCESS, MIN_EXCESS_SHARE * m)):
            continue

        day = series[i]["date"]
        drivers = []
        services = by_day_service.get(day, {})
        for svc, amt in services.items():
            usual = median([by_day_service.get(series[j]["date"], {}).get(svc, 0.0) for j in idx])
            delta = amt - usual
            if delta > 0:
                drivers.append({"service": svc, "amount": round(amt, 2), "usual": round(usual, 2),
                                "increase": round(delta, 2)})
        total_up = sum(d["increase"] for d in drivers) or 1.0
        for d in drivers:
            d["share"] = round(d["increase"] / total_up, 4)
        drivers.sort(key=lambda d: d["increase"], reverse=True)

        after = amounts[i + 1:i + 3]
        ongoing = len(after) == 2 and all(a > m + 0.5 * excess for a in after)
        out.append({
            "date": day,
            "amount": round(x, 2),
            "expected": round(m, 2),
            "excess": round(excess, 2),
            "z": round(z, 2),
            "spread": round(s, 2),
            "method": method,
            "baseline_days": [series[j]["date"] for j in idx],
            "ongoing": ongoing,
            "monthly_impact": round(excess * DAYS_PER_MONTH, 2) if ongoing else round(excess, 2),
            "impact_basis": "if it continues for a month" if ongoing else "one-off excess",
            "confidence": round(min(0.95, 0.55 + 0.05 * (z - Z_THRESHOLD)), 2),
            "drivers": drivers[:5],
        })
    return out


# ==========================================================================
# 2. Forecast: Holt's linear smoothing with weekday factors
# ==========================================================================
ALPHAS = (0.2, 0.4, 0.6, 0.8)
BETAS = (0.05, 0.1, 0.2)
Z80 = 1.2816  # two-sided 80% interval


def holt_fit(values: list[float]) -> dict:
    """Holt's linear method. Tries a small grid of smoothing constants and
    keeps the pair with the lowest one-step-ahead squared error."""
    best = None
    for a in ALPHAS:
        for b in BETAS:
            level, trend = values[0], values[1] - values[0]
            sse, n = 0.0, 0
            for y in values[1:]:
                pred = level + trend
                sse += (y - pred) ** 2
                n += 1
                new_level = a * y + (1 - a) * (level + trend)
                trend = b * (new_level - level) + (1 - b) * trend
                level = new_level
            if best is None or sse < best["sse"]:
                best = {"alpha": a, "beta": b, "level": level, "trend": trend, "sse": sse,
                        "rmse": math.sqrt(sse / n) if n else 0.0}
    return best


def weekday_factors(dates: list[date], values: list[float]) -> dict[int, float]:
    """Average of each weekday divided by the overall average, needs 4 weeks.
    Clipped to 0.5-1.5 so a single odd week can't dominate."""
    if len(values) < 28 or mean(values) <= 0:
        return {wd: 1.0 for wd in range(7)}
    overall = mean(values)
    groups = defaultdict(list)
    for d, v in zip(dates, values):
        groups[d.weekday()].append(v)
    return {wd: min(1.5, max(0.5, mean(groups[wd]) / overall)) if groups[wd] else 1.0 for wd in range(7)}


def month_forecast(daily: dict[str, float], end: date, today: date, budget: float | None = None) -> dict:
    """Forecast the month that contains `end` (the last billed day).

    - Month already over: forecast = actual.
    - Fewer than 7 billed days: average of what exists x remaining days.
    - Otherwise: remove weekday pattern, fit Holt, project each remaining
      day as (level + h x trend) x weekday factor, never below zero.
    Band: 80% interval, 1.2816 x RMSE x sqrt(remaining days) (in weekday-
    adjusted units, scaled back by the average factor).
    Budget breach date: first day the running total passes the budget.
    """
    first = end.replace(day=1)
    n_days = calendar.monthrange(end.year, end.month)[1]
    month_end = end.replace(day=n_days)
    month_days = [first + timedelta(days=i) for i in range(n_days)]
    mtd = sum(daily.get(d.isoformat(), 0.0) for d in month_days if d <= end)
    remaining = (month_end - end).days if (end.year, end.month) == (today.year, today.month) else 0

    hist_dates = [end - timedelta(days=k) for k in range(59, -1, -1)]
    hist = [(d, daily.get(d.isoformat(), 0.0)) for d in hist_dates]
    while hist and hist[0][1] <= 0:
        hist.pop(0)
    values = [v for _, v in hist]
    dates = [d for d, _ in hist]

    path = []
    running = 0.0
    for d in month_days:
        if d <= end:
            running += daily.get(d.isoformat(), 0.0)
            path.append({"date": d.isoformat(), "actual": round(running, 2), "forecast": None})

    result = {
        "month": first.strftime("%Y-%m"),
        "month_label": first.strftime("%B %Y"),
        "month_to_date": round(mtd, 2),
        "days_remaining": remaining,
        "billed_days_used": len(values),
        "run_rate": round(mean(values[-7:]), 2) if values else 0.0,
    }

    if remaining == 0:
        result.update(forecast=round(mtd, 2), low=round(mtd, 2), high=round(mtd, 2),
                      method="Month complete: actual total", model={})
    elif len(values) < 7:
        rate = mean(values) if values else 0.0
        proj = [rate] * remaining
        result.update(method=f"Average of the {len(values)} billed day(s) so far", model={"daily_rate": round(rate, 2)})
        result["forecast"] = round(mtd + sum(proj), 2)
        result["low"] = result["high"] = result["forecast"]
        _extend_path(path, end, proj)
    else:
        factors = weekday_factors(dates, values)
        adjusted = [v / factors[d.weekday()] for d, v in zip(dates, values)]
        fit = holt_fit(adjusted)
        proj = []
        for h in range(1, remaining + 1):
            d = end + timedelta(days=h)
            proj.append(max(0.0, (fit["level"] + h * fit["trend"]) * factors[d.weekday()]))
        band = Z80 * fit["rmse"] * math.sqrt(remaining) * mean(factors.values())
        total = mtd + sum(proj)
        seasonal = any(abs(f - 1) > 1e-9 for f in factors.values())
        result.update(
            forecast=round(total, 2),
            low=round(max(mtd, total - band), 2),
            high=round(total + band, 2),
            method="Holt's linear smoothing" + (" with weekday pattern" if seasonal else ""),
            model={"alpha": fit["alpha"], "beta": fit["beta"], "level": round(fit["level"], 2),
                   "trend_per_day": round(fit["trend"], 3), "rmse": round(fit["rmse"], 2),
                   "weekday_factors": {calendar.day_abbr[k]: round(v, 2) for k, v in factors.items()}},
        )
        _extend_path(path, end, proj)

    result["path"] = path
    result["breach_date"] = None
    if budget:
        for p in path:
            val = p["actual"] if p["forecast"] is None else p["forecast"]
            if val is not None and val > budget:
                result["breach_date"] = p["date"]
                break
    return result


def _extend_path(path, end, proj):
    running = path[-1]["actual"] if path else 0.0
    for h, v in enumerate(proj, start=1):
        running += v
        path.append({"date": (end + timedelta(days=h)).isoformat(), "actual": None, "forecast": round(running, 2)})


# ==========================================================================
# 3. Priority score
# ==========================================================================
SEVERITY_WEIGHT = {"critical": 1.0, "high": 0.8, "medium": 0.55, "low": 0.3}
IMPACT_REFERENCE = 1000.0   # a $1,000/month finding gets the full impact score
KIND_IMPACT_WEIGHT = {"untagged_spend": 0.25, "budget_risk": 1.0}  # governance $ isn't all waste


def severity_for_impact(monthly: float) -> str:
    if monthly >= 500:
        return "critical"
    if monthly >= 100:
        return "high"
    if monthly >= 20:
        return "medium"
    return "low"


def priority(monthly_impact: float, severity: str, confidence: float, days_open: float,
             kind: str = "") -> dict:
    """score = 100 x (0.6 x impact_score + 0.4 x severity_weight) x confidence x age_factor

    impact_score = log10(1 + impact) / log10(1 + 1000), capped at 1
                   (log scale: $10 -> 0.35, $100 -> 0.67, $1,000 -> 1.0)
    age_factor   = 1 + min(0.3, days_open / 100)   (up to +30% if left open)
    P1 >= 70, P2 >= 45, P3 >= 25, else P4
    """
    weighted = max(0.0, monthly_impact) * KIND_IMPACT_WEIGHT.get(kind, 1.0)
    impact_score = min(1.0, math.log10(1 + weighted) / math.log10(1 + IMPACT_REFERENCE))
    sev = SEVERITY_WEIGHT.get(severity, 0.3)
    age = 1 + min(0.3, max(0.0, days_open) / 100)
    score = min(100, round(100 * (0.6 * impact_score + 0.4 * sev) * confidence * age))
    band = "P1" if score >= 70 else "P2" if score >= 45 else "P3" if score >= 25 else "P4"
    return {
        "score": score, "band": band,
        "parts": {"impact_score": round(impact_score, 3), "severity_weight": sev,
                  "confidence": round(confidence, 2), "age_factor": round(age, 3),
                  "weighted_impact": round(weighted, 2)},
    }


# ==========================================================================
# 4. VM utilisation verdict
# ==========================================================================
IDLE_CPU_P95 = 5.0          # %
IDLE_NET_P95_MB = 5.0       # MB per hour, in + out
RIGHTSIZE_CPU_P95 = 20.0    # %
RIGHTSIZE_MAX_PEAK = 80.0   # % - bursty machines are left alone

SIZE_LADDERS = [
    ["Standard_B1ls", "Standard_B1s", "Standard_B1ms", "Standard_B2s", "Standard_B2ms", "Standard_B4ms", "Standard_B8ms"],
    ["Standard_B2ats_v2", "Standard_B2als_v2", "Standard_B2as_v2", "Standard_B4als_v2", "Standard_B4as_v2", "Standard_B8as_v2"],
    ["Standard_D2s_v3", "Standard_D4s_v3", "Standard_D8s_v3", "Standard_D16s_v3", "Standard_D32s_v3"],
    ["Standard_D2s_v4", "Standard_D4s_v4", "Standard_D8s_v4", "Standard_D16s_v4"],
    ["Standard_D2s_v5", "Standard_D4s_v5", "Standard_D8s_v5", "Standard_D16s_v5", "Standard_D32s_v5"],
    ["Standard_D2as_v5", "Standard_D4as_v5", "Standard_D8as_v5", "Standard_D16as_v5"],
    ["Standard_D2ads_v5", "Standard_D4ads_v5", "Standard_D8ads_v5", "Standard_D16ads_v5"],
    ["Standard_E2s_v3", "Standard_E4s_v3", "Standard_E8s_v3", "Standard_E16s_v3"],
    ["Standard_E2s_v5", "Standard_E4s_v5", "Standard_E8s_v5", "Standard_E16s_v5"],
    ["Standard_F2s_v2", "Standard_F4s_v2", "Standard_F8s_v2", "Standard_F16s_v2"],
]


def smaller_size(size: str) -> str | None:
    for ladder in SIZE_LADDERS:
        for i, s in enumerate(ladder):
            if s.lower() == (size or "").lower():
                return ladder[i - 1] if i > 0 else None
    return None


def vm_verdict(cpu_avg: list[float], cpu_max: list[float], net_mb: list[float], hours_expected: int) -> dict:
    """Decide idle / oversized / fine from hourly Azure Monitor points.

    idle      : p95(hourly CPU) < 5% and p95(hourly network) < 5 MB
    oversized : p95(hourly CPU) < 20% and peak CPU < 80%
    Needs 48+ hourly points. Confidence 0.85 with 7+ days of data (0.65 with
    less); oversized is 0.15 lower because memory isn't measured.
    """
    points = len(cpu_avg)
    stats = {
        "hours": points,
        "coverage": round(points / hours_expected, 2) if hours_expected else 0,
        "cpu_p95": round(percentile(cpu_avg, 95), 2) if cpu_avg else None,
        "cpu_mean": round(mean(cpu_avg), 2) if cpu_avg else None,
        "cpu_peak": round(max(cpu_max), 2) if cpu_max else (round(max(cpu_avg), 2) if cpu_avg else None),
        "net_p95_mb": round(percentile(net_mb, 95), 2) if net_mb else None,
    }
    if points < 48:
        return {"verdict": "insufficient", "confidence": 0.0, "stats": stats}
    base = 0.85 if points >= 7 * 24 else 0.65
    net_ok = stats["net_p95_mb"] is None or stats["net_p95_mb"] < IDLE_NET_P95_MB
    if stats["cpu_p95"] < IDLE_CPU_P95 and net_ok:
        return {"verdict": "idle", "confidence": base, "stats": stats}
    if stats["cpu_p95"] < RIGHTSIZE_CPU_P95 and (stats["cpu_peak"] or 0) < RIGHTSIZE_MAX_PEAK:
        return {"verdict": "oversized", "confidence": round(base - 0.15, 2), "stats": stats}
    return {"verdict": "fine", "confidence": 0.0, "stats": stats}


# ==========================================================================
# 5. Verification: before / after cost
# ==========================================================================
VERIFY_WINDOW = 7
VERIFY_MIN_AFTER = 3


def before_after(daily_cost: dict[str, float], change_day: date, last_cost_day: date | None) -> dict | None:
    """Compare a resource's average daily cost in the 7 days before a change
    with the days after it (skipping the change day itself, when billing is
    mixed). Days with no cost row count as zero, but only up to the last day
    the workspace has any cost data, since Azure publishes costs late.
    Returns None until at least 3 'after' days are available.
    """
    if last_cost_day is None:
        return None
    before_days = [change_day - timedelta(days=k) for k in range(VERIFY_WINDOW, 0, -1)]
    after_days = [change_day + timedelta(days=k) for k in range(1, VERIFY_WINDOW + 1)
                  if change_day + timedelta(days=k) <= last_cost_day]
    if len(after_days) < VERIFY_MIN_AFTER:
        return None
    before = [daily_cost.get(d.isoformat(), 0.0) for d in before_days]
    after = [daily_cost.get(d.isoformat(), 0.0) for d in after_days]
    b, a = mean(before), mean(after)
    realized_daily = max(0.0, b - a)
    return {
        "before_daily": round(b, 4),
        "after_daily": round(a, 4),
        "before_days": len(before),
        "after_days": len(after),
        "drop_pct": round((b - a) / b, 4) if b > 0 else None,
        "realized_monthly": round(realized_daily * DAYS_PER_MONTH, 2),
        "series_before": [{"date": d.isoformat(), "amount": round(v, 4)} for d, v in zip(before_days, before)],
        "series_after": [{"date": d.isoformat(), "amount": round(v, 4)} for d, v in zip(after_days, after)],
    }


def saved_to_date(realized_monthly: float, verified_on: date, today: date) -> float:
    days = max(0, (today - verified_on).days)
    return round(realized_monthly * days / DAYS_PER_MONTH, 2)


# ==========================================================================
# 6. Stacked daily series (charts)
# ==========================================================================
def stacked(rows, start: date, days: int, key, top_n: int = 5) -> dict:
    """Daily series split into the top N groups plus 'Other'."""
    totals = defaultdict(float)
    for r in rows:
        totals[key(r)] += r.amount
    top = [k for k, _ in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:top_n]]
    groups = top + (["Other"] if len(totals) > top_n else [])
    grid = {d: defaultdict(float) for d in daterange(start, days)}
    for r in rows:
        if r.date in grid:
            g = key(r)
            grid[r.date][g if g in top else "Other"] += r.amount
    return {
        "groups": [
            {"key": g, "total": round(totals[g] if g != "Other" else sum(v for k, v in totals.items() if k not in top), 2)}
            for g in groups
        ],
        "days": [{"date": d, "values": {g: round(grid[d].get(g, 0.0), 2) for g in groups}} for d in daterange(start, days)],
    }
