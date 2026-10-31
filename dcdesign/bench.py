"""Experiments for Chapter 6 (fixed seeds, repeatable)."""
import itertools, json, random, time
from dcd import designs, evaluate, capacity, security, resilience
from dcd.model import Rule, VM

out = {}
YEARS = 5000

# 1. Four designs
rows = {}
designs_ = {k: designs.reference_design(k) for k in ("basic", "segmented", "resilient")}
designs_["basic+fixes"], changes = designs.harden(designs_["basic"])
for k, d in designs_.items():
    r = evaluate.evaluate(d, YEARS, 1)
    s, rs, c = r["security"], r["resilience"], r["capacity"]
    rows[k] = {"hosts": c["hosts"], "cpu_pct": c["cpu_pct"], "ram_pct": c["ram_pct"], "n_plus_one": c["n_plus_one"], "capacity_score": c["score"],
               "counts": s["counts"], "policy_score": s["policy_score"], "hardening_score": s["hardening_score"], "security_score": s["score"],
               "db_routes": s["paths"]["db"]["count"], "db_shortest": s["paths"]["db"]["shortest"], "mgmt_shortest": s["paths"]["mgmt"]["shortest"],
               "spofs": [x["component"] for x in rs["spofs"]], "resilience_score": rs["score"], "tier": rs["tier"]["label"], "scenarios": len(rs["scenarios"]),
               "degraded": sum(1 for x in rs["scenarios"] if x["tolerated"] and x["degraded"]),
               "e2e_down_min": rs["availability"]["end_to_end"]["downtime_min_per_year"], "e2e_avail": rs["availability"]["end_to_end"]["availability"],
               "tier_down": {t: v["downtime_min_per_year"] for t, v in rs["availability"]["tiers"].items()}, "overall": r["overall"]}
out["designs"] = rows
out["fix_changes"] = changes
out["fix_remaining"] = security.hardening(designs_["basic+fixes"])["missing"]

# 2. Placement algorithms on 300 random workloads (40 VMs, replica pairs)
shapes = [(1, 2), (2, 4), (2, 8), (4, 8), (4, 16), (8, 16), (8, 32), (16, 32)]
res = {a: {"hosts": [], "gap": [], "lb": 0} for a in ("ff", "bf", "ffd")}
for seed in range(300):
    rng = random.Random(seed)
    vms = []
    for i in range(40):
        c, m = rng.choice(shapes)
        vms.append(VM(f"v{i}", c, m, "app", f"g{i // 2}"))
    hosts = [designs.Host(f"h{i}", 32, 128, "R1", ("A",), ("S",), ("C",)) for i in range(60)]
    lb = capacity.lower_bound_hosts(vms, 32, 128)
    for a in res:
        pl, un = capacity.place(vms, hosts, a)
        used = len(set(pl.values()))
        res[a]["hosts"].append(used); res[a]["gap"].append(used - lb); res[a]["lb"] += used == lb
out["placement"] = {a: {"mean_hosts": sum(v["hosts"]) / 300, "mean_gap": sum(v["gap"]) / 300, "at_lower_bound_pct": 100 * v["lb"] / 300} for a, v in res.items()}

# 3. Detection of misconfigured rules
policy = designs.policy_rules()
rng = random.Random(5)
ports = ["443", "22", "5432", "8443", "3306", "any"]
zones = ["internet", "dmz", "app", "db", "mgmt", "storage", "any"]
tested = flagged = 0; benign = benign_flag = 0; by_kind = {}
for _ in range(600):
    r = Rule(rng.choice(zones[:-1]), rng.choice(zones[:-1]), rng.choice(ports), "allow", True)
    if r.src == r.dst: continue
    d = designs.reference_design("segmented"); d.rules = list(d.rules) + [r]
    f = [x for x in security.findings(d) if x["rule"] == len(d.rules) - 1]
    inpol = (r.src, r.dst, r.port) in security.POLICY
    kinds = {x["kind"] for x in f}
    if inpol:
        benign += 1; benign_flag += bool(kinds - {"shadowed-rule"})
    else:
        tested += 1; flagged += bool(kinds - {"shadowed-rule"})
        for k in kinds: by_kind[k] = by_kind.get(k, 0) + 1
out["detection"] = {"injected": tested, "flagged": flagged, "benign_duplicates": benign, "benign_flagged_as_violation": benign_flag, "by_kind": by_kind}

# 4. Double failures
dbl = {}
for k in ("resilient", "basic+fixes"):
    d = designs_[k]; comps = resilience.components(d)
    pairs = list(itertools.combinations(comps, 2))
    ok = sum(resilience.scenario(d, set(p))["tolerated"] for p in pairs)
    bad_pairs = [p for p in pairs if not resilience.scenario(d, set(p))["tolerated"]]
    dbl[k] = {"components": len(comps), "pairs": len(pairs), "tolerated": ok, "pct": 100 * ok / len(pairs),
              "examples": [f"{a[0]} {a[1]} + {b[0]} {b[1]}" for a, b in bad_pairs[:4]]}
out["double_failures"] = dbl

# 5. Scale
scale = []
for n in (20, 40, 80, 160, 320):
    t = time.perf_counter(); d = designs.reference_design("resilient", n); r = evaluate.evaluate(d, 500, 1); dt = time.perf_counter() - t
    scale.append({"vms": n, "hosts": r["capacity"]["hosts"], "seconds": round(dt, 2), "overall": r["overall"], "scenarios": len(r["resilience"]["scenarios"])})
out["scale"] = scale
out["years"] = YEARS
json.dump(out, open("bench_results.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("placement", "detection", "double_failures", "scale")}, indent=1))
for k, v in rows.items(): print(k, {a: (round(b, 1) if isinstance(b, float) else b) for a, b in v.items() if a not in ('tier_down','counts')}, v['counts'])
