"""Hand-checkable tests for every algorithm. Each expected number is worked
out in the comment next to it."""
from datetime import date, timedelta

import pytest

from app.services import analytics as A


# ---------------------------------------------------------------- helpers
def test_median_percentile_mad():
    assert A.median([3, 1, 2]) == 2
    assert A.median([4, 1, 3, 2]) == 2.5
    # type-7 percentile of 1..5 at p95: k = 4 * 0.95 = 3.8 -> 4 + 0.8 * (5 - 4) = 4.8
    assert A.percentile([1, 2, 3, 4, 5], 95) == pytest.approx(4.8)
    # MAD of [1,2,3,4,100]: median 3, deviations [2,1,0,1,97] -> median 1
    assert A.mad([1, 2, 3, 4, 100]) == 1


# ---------------------------------------------------------------- anomalies
def _series(values, start=date(2026, 8, 3)):
    return [{"date": (start + timedelta(days=i)).isoformat(), "amount": v} for i, v in enumerate(values)]


def test_no_anomaly_on_flat_series():
    assert A.find_anomalies(_series([10.0] * 30)) == []


def test_spike_detected_with_weekday_baseline_and_drivers():
    values = [10.0] * 28 + [40.0] + [10.0, 10.0]
    s = _series(values)
    day = s[28]["date"]
    by_service = {d["date"]: {"VM": 8.0, "Storage": 2.0} for d in s}
    by_service[day] = {"VM": 36.0, "Storage": 4.0}
    found = A.find_anomalies(s, by_service)
    assert len(found) == 1
    a = found[0]
    # baseline: days 21, 14, 7, 0 -> all 10 -> median 10, MAD 0 -> spread floored at 5% of 10 = 0.5
    assert a["method"] == "same weekday in the previous 4 weeks"
    assert a["expected"] == 10.0
    assert a["spread"] == 0.5
    assert a["excess"] == 30.0
    assert a["z"] == 60.0            # (40 - 10) / 0.5
    assert a["ongoing"] is False     # next two days back at 10
    assert a["monthly_impact"] == 30.0
    # drivers: VM +28, Storage +2 -> shares 0.9333 / 0.0667
    assert [d["service"] for d in a["drivers"]] == ["VM", "Storage"]
    assert a["drivers"][0]["share"] == pytest.approx(28 / 30, abs=1e-4)
    assert a["confidence"] == 0.95   # capped


def test_ongoing_spike_is_projected_monthly():
    values = [10.0] * 28 + [40.0, 38.0, 39.0]
    a = A.find_anomalies(_series(values))[0]
    assert a["ongoing"] is True
    assert a["monthly_impact"] == pytest.approx(30.0 * 30.4)


def test_small_increase_is_ignored():
    # +0.8 is below the 1.0 minimum even though the history is flat
    values = [2.0] * 20 + [2.8] + [2.0] * 3
    assert A.find_anomalies(_series(values)) == []


def test_needs_seven_billed_days():
    assert A.find_anomalies(_series([0, 0, 0, 5, 5, 5, 50, 5])) == []


def test_fallback_to_previous_14_days():
    values = [10, 12, 11, 9, 10, 11, 10, 12, 11, 10, 60]
    a = A.find_anomalies(_series(values))[0]
    assert a["method"] == "previous 14 days"
    assert a["expected"] == 10.5  # median of the 10 earlier values


# ---------------------------------------------------------------- forecast
def test_forecast_complete_month_equals_actual():
    daily = {f"2024-09-{d:02d}": 10.0 for d in range(1, 31)}
    f = A.month_forecast(daily, date(2024, 9, 30), today=date(2026, 9, 17))
    assert f["forecast"] == 300.0
    assert f["days_remaining"] == 0
    assert f["method"].startswith("Month complete")


def test_forecast_constant_series_projects_same_rate():
    today = date(2026, 9, 17)
    end = date(2026, 9, 16)
    daily = {(end - timedelta(days=k)).isoformat(): 5.0 for k in range(40)}
    f = A.month_forecast(daily, end, today, budget=100)
    # 16 days so far x 5 = 80; 14 days left x 5 = 70; total 150
    assert f["month_to_date"] == 80.0
    assert f["days_remaining"] == 14
    assert f["forecast"] == pytest.approx(150.0, abs=0.01)
    assert f["model"]["trend_per_day"] == 0.0
    # running total passes 100 on day 21 (5 x 21 = 105)
    assert f["breach_date"] == "2026-09-21"


def test_forecast_linear_trend_is_followed():
    today = date(2026, 9, 11)
    end = date(2026, 9, 10)
    # 1, 2, ..., 20 ending on 10 Sept (grows 1 per day)
    daily = {(end - timedelta(days=19 - i)).isoformat(): float(i + 1) for i in range(20)}
    f = A.month_forecast(daily, end, today)
    # Holt fits a perfect line: next days 21..40 -> sum = (21+40)*20/2 = 610
    assert f["model"]["rmse"] == pytest.approx(0.0, abs=1e-9)
    assert f["forecast"] == pytest.approx(sum(range(11, 21)) + 610, abs=0.01)


def test_forecast_short_history_uses_average():
    today = date(2026, 9, 5)
    end = date(2026, 9, 4)
    daily = {"2026-09-03": 2.0, "2026-09-04": 4.0}
    f = A.month_forecast(daily, end, today)
    # average 3/day x 26 remaining days + 6 so far = 84
    assert f["forecast"] == 84.0
    assert "Average" in f["method"]


# ---------------------------------------------------------------- priority
@pytest.mark.parametrize("impact,sev,conf,days,score,band", [
    # log10(71)/log10(1001)=0.6169 -> (0.6*0.6169 + 0.4*0.55) * 0.9 * 1 = 0.531 -> 53
    (70.08, "medium", 0.9, 0, 53, "P2"),
    # log10(1.18)/3.0004=0.02396 -> (0.01438 + 0.12) * 0.95 = 0.1277 -> 13
    (0.18, "low", 0.95, 0, 13, "P4"),
    # log10(501)/3.0004=0.9000 -> (0.54 + 0.4) * 0.8 = 0.752 -> 75
    (500, "critical", 0.8, 0, 75, "P1"),
    # same as the first but open 30 days: 0.531 * 1.3 = 0.690 -> 69
    (70.08, "medium", 0.9, 30, 69, "P2"),
])
def test_priority_examples(impact, sev, conf, days, score, band):
    p = A.priority(impact, sev, conf, days)
    assert p["score"] == score
    assert p["band"] == band


def test_governance_impact_is_down_weighted():
    full = A.priority(400, "high", 0.9, 0)
    gov = A.priority(400, "high", 0.9, 0, kind="untagged_spend")
    assert gov["parts"]["weighted_impact"] == 100.0
    assert gov["score"] < full["score"]


def test_severity_tiers():
    assert [A.severity_for_impact(x) for x in (0, 19.99, 20, 100, 500)] == ["low", "low", "medium", "high", "critical"]


# ---------------------------------------------------------------- VMs
def test_vm_idle_and_oversized_and_fine():
    hours = 14 * 24
    idle = A.vm_verdict([1.0] * hours, [3.0] * hours, [0.5] * hours, hours)
    assert idle["verdict"] == "idle" and idle["confidence"] == 0.85
    over = A.vm_verdict([12.0] * hours, [40.0] * hours, [50.0] * hours, hours)
    assert over["verdict"] == "oversized" and over["confidence"] == 0.7
    bursty = A.vm_verdict([12.0] * hours, [95.0] * hours, [50.0] * hours, hours)
    assert bursty["verdict"] == "fine"
    short = A.vm_verdict([1.0] * 30, [1.0] * 30, [0.1] * 30, hours)
    assert short["verdict"] == "insufficient"
    few_days = A.vm_verdict([1.0] * 72, [1.0] * 72, [0.1] * 72, hours)
    assert few_days["confidence"] == 0.65


def test_smaller_size_ladder():
    assert A.smaller_size("Standard_D4s_v3") == "Standard_D2s_v3"
    assert A.smaller_size("standard_b2s") == "Standard_B1ms"
    assert A.smaller_size("Standard_B1ls") is None
    assert A.smaller_size("Standard_M128") is None


# ---------------------------------------------------------------- verification
def test_before_after_resource_deleted():
    change = date(2026, 9, 10)
    daily = {(change - timedelta(days=k)).isoformat(): 2.0 for k in range(1, 8)}
    r = A.before_after(daily, change, last_cost_day=date(2026, 9, 14))
    # before 2.0/day, after 4 days of 0 -> 2.0 x 30.4 = 60.8
    assert r["before_daily"] == 2.0
    assert r["after_daily"] == 0.0
    assert r["after_days"] == 4
    assert r["drop_pct"] == 1.0
    assert r["realized_monthly"] == 60.8


def test_before_after_waits_for_data():
    change = date(2026, 9, 10)
    assert A.before_after({}, change, last_cost_day=date(2026, 9, 12)) is None
    assert A.before_after({}, change, last_cost_day=None) is None


def test_before_after_partial_drop_and_no_negative():
    change = date(2026, 9, 10)
    daily = {(change - timedelta(days=k)).isoformat(): 4.0 for k in range(1, 8)}
    daily.update({(change + timedelta(days=k)).isoformat(): 1.0 for k in range(1, 8)})
    r = A.before_after(daily, change, last_cost_day=date(2026, 9, 20))
    assert r["realized_monthly"] == pytest.approx(3.0 * 30.4)
    up = {k: 9.0 for k in daily}
    assert A.before_after(up, change, date(2026, 9, 20))["realized_monthly"] == 0.0


def test_saved_to_date():
    assert A.saved_to_date(60.8, date(2026, 9, 1), date(2026, 9, 16)) == 30.0
