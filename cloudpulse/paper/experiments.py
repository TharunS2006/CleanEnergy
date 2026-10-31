"""Controlled simulation of the anomaly detector and the forecaster (seeded, reproducible).
Series model: base level with slow trend, weekday pattern (weekends cheaper) and log-normal noise."""
import importlib.util, json, math, random, statistics as st, sys
from datetime import date, timedelta
B = "/home/user/CleanEnergy/cloudpulse/backend/app/services/"
spec = importlib.util.spec_from_file_location("analytics", B + "analytics.py"); an = importlib.util.module_from_spec(spec)
sys.modules["analytics"] = an; spec.loader.exec_module(an)
START = date(2024, 1, 1)

def make(n, sigma, rng, base=100.0, trend=0.002):
    out = []
    for i in range(n):
        d = START + timedelta(days=i)
        wk = 0.78 if d.weekday() >= 5 else 1.0
        v = base * (1 + trend * i) * wk * math.exp(rng.gauss(0, sigma))
        out.append({"date": d.isoformat(), "amount": v})
    return out

def cp_flags(ser):
    return {a["date"] for a in an.find_anomalies(ser)}

def naive_flags(ser):          # textbook rule: value > mean + 3 sd of the previous 14 days
    a = [s["amount"] for s in ser]; out = set()
    for i in range(14, len(a)):
        w = a[i - 14:i]; m, s = st.mean(w), st.pstdev(w)
        if s > 0 and a[i] > m + 3 * s: out.add(ser[i]["date"])
    return out

N, TRIALS = 120, 400
result = {"detect": {}, "false_alarms": {}, "forecast": {}}
for sigma in (0.08, 0.15):
    rng = random.Random(100 + int(sigma * 100))
    # false alarms: flagged days per 100 clean days
    fp_cp = fp_nv = days = 0
    for _ in range(300):
        s = make(N, sigma, rng)
        fp_cp += len(cp_flags(s)); fp_nv += len(naive_flags(s)); days += N
    result["false_alarms"][str(sigma)] = {"cloudpulse": round(100 * fp_cp / days, 2), "naive": round(100 * fp_nv / days, 2)}
    for k in (1.25, 1.5, 2.0, 3.0):
        hit_cp = hit_nv = 0
        for _ in range(TRIALS):
            s = make(N, sigma, rng); i = rng.randrange(45, N - 3)
            s[i]["amount"] *= k
            day = s[i]["date"]
            hit_cp += day in cp_flags(s); hit_nv += day in naive_flags(s)
        result["detect"].setdefault(str(sigma), {})[str(k)] = {"cloudpulse": round(hit_cp / TRIALS, 3), "naive": round(hit_nv / TRIALS, 3)}
    print("sigma", sigma, result["false_alarms"][str(sigma)], result["detect"][str(sigma)])

# forecast backtest: 7 days ahead, 60-day history, rolling origin, 200 series
rng = random.Random(5); H = 7; err = {"holt+weekday": [], "naive": [], "ma7": []}
for _ in range(200):
    s = make(150, 0.08, rng, trend=0.004)
    a = [x["amount"] for x in s]; dates = [date.fromisoformat(x["date"]) for x in s]
    for t in range(80, 150 - H, 6):
        hist, hd = a[t - 60:t], dates[t - 60:t]
        fac = an.weekday_factors(hd, hist)
        f = an.holt_fit([v / fac[d.weekday()] for v, d in zip(hist, hd)])
        tgt = t + H - 1; actual = a[tgt]
        err["holt+weekday"].append(abs((f["level"] + f["trend"] * H) * fac[dates[tgt].weekday()] - actual) / actual)
        err["naive"].append(abs(hist[-1] - actual) / actual)
        err["ma7"].append(abs(st.mean(hist[-7:]) - actual) / actual)
result["forecast"] = {k: round(100 * st.mean(v), 2) for k, v in err.items()}; result["forecast_n"] = len(err["naive"])
print("MAPE", result["forecast"], result["forecast_n"])
json.dump(result, open("results.json", "w"), indent=1)
