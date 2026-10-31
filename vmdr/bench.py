"""Experiments for Chapter 6 (fixed seeds, repeatable)."""
import json, time, statistics as st
from vmdr import avail, sim, dr, backup

out = {}
P = sim.Params()
Y = 20000

# 1. Simulation against closed-form results
rows = []
ah, az, ar = (avail.availability(P.host_mtbf, P.host_mttr), avail.availability(P.zone_mtbf, P.zone_mttr), avail.availability(P.region_mtbf, P.region_mttr))
w = sim.make_world(P, Y, 7)
inst = avail.series(ah, az)
for key, exact in (("single", avail.series(ah, az, ar)), ("aa-two-zones", avail.series(avail.parallel(inst, inst), ar))):
    got = sim.run(key, P, w)["availability"]
    rows.append({"what": sim.STRATEGIES[key], "model": "closed form", "exact_unavail": 1 - exact, "sim_unavail": 1 - got, "error_pct": 100 * ((1 - got) - (1 - exact)) / (1 - exact)})
for mtbf, mttr, f in ((2000, 4, 2), (2000, 4, 10), (500, 8, 2), (1000, 24, 5)):
    pp = sim.Params(host_mtbf=mtbf, host_mttr=mttr, zone_mtbf=1e12, region_mtbf=1e12, failover_minutes=f)
    ww = sim.make_world(pp, 60000, 3)
    got = 1 - sim.run("ap-one-zone", pp, ww)["availability"]; exact = avail.active_passive_unavailability(mtbf, mttr, f / 60.0)
    rows.append({"what": f"Active-passive pair, MTBF {mtbf} h, MTTR {mttr} h, failover {f} min", "model": "Markov chain", "exact_unavail": exact, "sim_unavail": got, "error_pct": 100 * (got - exact) / exact})
out["validation"] = rows

# 2. Six strategies on the same failures, and the spread over 5 seeds
res = sim.compare(P, Y, 1, dr.TIERS["warm-standby"])
out["strategies"] = {k: {kk: v for kk, v in r.items()} for k, r in res.items()}
spread = {k: [] for k in sim.STRATEGIES}
for seed in range(1, 6):
    for k, r in sim.compare(P, Y, seed, dr.TIERS["warm-standby"]).items():
        spread[k].append(r["downtime_min_per_year"])
out["spread"] = {k: [min(v), max(v)] for k, v in spread.items()}

# 3. Failover time (active-passive in two zones)
fo = []
for f in (1, 2, 5, 10, 20, 30, 60):
    pp = sim.Params(failover_minutes=f)
    ww = sim.make_world(pp, Y, 1)
    r = sim.run("ap-two-zones", pp, ww)
    hostonly = sim.Params(failover_minutes=f, zone_mtbf=1e12, region_mtbf=1e12)
    wh = sim.make_world(hostonly, 40000, 2)
    sh = sim.run("ap-one-zone", hostonly, wh)
    fo.append({"failover_min": f, "downtime_min_per_year": r["downtime_min_per_year"],
               "host_only_sim_min_per_year": sh["downtime_min_per_year"],
               "host_only_markov_min_per_year": avail.active_passive_unavailability(hostonly.host_mtbf, hostonly.host_mttr, f / 60.0) * 8760 * 60})
out["failover_sweep"] = fo

# 4. Host repair time
mt = []
for mttr in (1, 4, 12, 24, 48):
    pp = sim.Params(host_mttr=mttr); ww = sim.make_world(pp, Y, 1)
    mt.append({"mttr": mttr, **{k: sim.run(k, pp, ww)["downtime_min_per_year"] for k in ("single", "restart", "ap-two-zones", "aa-two-zones")}})
out["mttr_sweep"] = mt

# 5. DR tiers
tiers = []
for key, t in dr.TIERS.items():
    ev = dr.dr_events(P, t, Y, 1)
    r = sim.run("aa-dr", P, sim.make_world(P, Y, 1), t)
    tiers.append({"key": key, "name": t.name, "restore_min": t.restore_minutes, "rto_min": ev["rto_minutes"], "rpo_mean_min": t.rpo_mean_minutes,
                  "mean_loss_sim": ev["mean_data_loss_min"], "cost_extra": t.extra_cost, "takeovers_per_year": ev["takeovers_per_year"],
                  "disasters_per_year": ev["disasters_per_year"], "availability": r["availability"], "downtime_min_per_year": r["downtime_min_per_year"]})
out["tiers"] = tiers

# 6. Backups
bk = []
for p in (1.0, 0.98, 0.9):
    for i in (60, 240, 1440):
        bk.append({"interval": i, "success": p, "mean": backup.mean_data_age_minutes(i, p), "p99": backup.percentile_data_age_minutes(i, p),
                   "sim_mean": backup.simulate_data_age(i, p, 100000, 1)})
out["backup"] = bk
out["restore"] = [{"size_gb": g, "minutes": backup.restore_minutes(g, 100)} for g in (100, 500, 1000, 5000)]

# 7. Planner scenarios
sc = {}
for name, args in (("internal tool", (0.999, None, None)), ("web shop", (0.9999, 60, 15)), ("payments", (0.9999, 15, 1)), ("five nines", (0.99999, 15, 1))):
    r = dr.plan(*args)
    b = r["recommended"]
    sc[name] = {"target": args[0], "rto": args[1], "rpo": args[2], "choice": None if b is None else (b["strategy"] + (" + " + b["tier"] if b["tier"] else "")),
                "cost": None if b is None else b["cost"], "availability": None if b is None else b["availability"],
                "options": [{"name": x["strategy"] + (" + " + x["tier"] if x["tier"] else ""), "cost": x["cost"], "availability": x["availability"], "meets": x["meets"]} for x in r["rows"]]}
out["planner"] = sc

# 8. Speed
t = time.perf_counter(); sim.compare(P, Y, 1); out["time_compare_s"] = round(time.perf_counter() - t, 2)
t = time.perf_counter(); dr.plan(0.9999, 60, 15); out["time_plan_s"] = round(time.perf_counter() - t, 2)
out["years"] = Y
json.dump(out, open("bench_results.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("validation", "spread", "failover_sweep", "mttr_sweep", "tiers", "planner", "time_compare_s", "time_plan_s")}, indent=1)[:9000])
