"""Experiments for Chapter 6. Every workload is generated from a fixed seed, so the numbers can be reproduced exactly."""
import json, statistics as st, time
from resopt import cpu, memory, disk, optimizer
from resopt.workloads import cpu_workload, page_refs, disk_requests

out = {}
mean = lambda xs: sum(xs) / len(xs)

# 1. CPU scheduling on 500 random workloads of 8 processes (quantum 4)
cpu_res = {}
for kind in ("mixed", "short"):
    agg = {a: {"wait": [], "turn": [], "resp": [], "max_wait": [], "sw": [], "util": []} for a in cpu.ALGORITHMS}
    best = {a: 0 for a in cpu.ALGORITHMS}
    for seed in range(500):
        runs = cpu.compare(cpu_workload(8, seed, kind), 4)
        low = min(r["metrics"]["avg_waiting"] for r in runs.values())
        for a, r in runs.items():
            m = r["metrics"]
            agg[a]["wait"].append(m["avg_waiting"]); agg[a]["turn"].append(m["avg_turnaround"]); agg[a]["resp"].append(m["avg_response"])
            agg[a]["max_wait"].append(m["max_waiting"]); agg[a]["sw"].append(m["context_switches"]); agg[a]["util"].append(m["utilisation"])
            best[a] += m["avg_waiting"] <= low + 1e-9
    cpu_res[kind] = {a: {"avg_waiting": round(mean(v["wait"]), 2), "avg_turnaround": round(mean(v["turn"]), 2), "avg_response": round(mean(v["resp"]), 2),
                         "max_waiting": round(mean(v["max_wait"]), 2), "switches": round(mean(v["sw"]), 2), "utilisation": round(mean(v["util"]), 3),
                         "best_share": round(100 * best[a] / 500, 1)} for a, v in agg.items()}
out["cpu"] = cpu_res

# 2. Round-robin quantum sweep (300 mixed workloads of 8 processes)
sweep = []
for q in range(1, 21):
    rows = [optimizer.tune_quantum(cpu_workload(8, s), [q])["rows"][0] for s in range(300)]
    sweep.append({"quantum": q, "avg_waiting": round(mean([r["avg_waiting"] for r in rows]), 2), "avg_response": round(mean([r["avg_response"] for r in rows]), 2),
                  "avg_turnaround": round(mean([r["avg_turnaround"] for r in rows]), 2), "switches": round(mean([r["context_switches"] for r in rows]), 2),
                  "score": round(mean([r["score"] for r in rows]), 2)})
out["quantum"] = sweep
out["quantum_best_score"] = min(sweep, key=lambda r: r["score"])["quantum"]

# 3. Page replacement: 200 strings with locality, 20 pages, 200 references
mem = {}
for frames in range(3, 13):
    mem[frames] = {a: round(mean([memory.simulate(a, page_refs(200, 20, s), frames)["fault_rate"] for s in range(200)]), 4) for a in memory.ALGORITHMS}
out["memory"] = mem
need = {}
for a in ("FIFO", "LRU", "CLOCK"):
    need[a] = next((f for f in range(3, 13) if mem[f][a] <= 0.18), None)
out["frames_for_18pct"] = need
out["memory_uniform"] = {a: round(mean([memory.simulate(a, page_refs(200, 20, s, locality=False), 8)["fault_rate"] for s in range(200)]), 4) for a in memory.ALGORITHMS}
# Belady's anomaly: how often does adding a frame increase the faults? (500 uniform random strings, 60 refs, 8 pages)
anom = {}
for a in memory.ALGORITHMS:
    n = 0
    for s in range(500):
        r = page_refs(60, 8, s, locality=False)
        f = [memory.simulate(a, r, k)["faults"] for k in range(1, 8)]
        n += any(y > x for x, y in zip(f, f[1:]))
    anom[a] = n
out["belady_strings_with_anomaly_of_500"] = anom
book = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
out["belady_book"] = {a: [memory.simulate(a, book, f)["faults"] for f in range(1, 8)] for a in ("FIFO", "LRU", "OPT", "CLOCK")}

# 4. Disk scheduling: 300 queues of 20 requests, 200 cylinders
dsk = {}
for name, clustered in (("uniform", False), ("clustered", True)):
    tot = {a: [] for a in disk.ALGORITHMS}
    for s in range(300):
        reqs, head = disk_requests(20, 200, s, clustered)
        for a, r in disk.compare(reqs, head).items(): tot[a].append(r["total"])
    dsk[name] = {a: round(mean(v), 1) for a, v in tot.items()}
out["disk"] = dsk

# 5. One scenario, three resources (the same seeds are used in the report)
procs = cpu_workload(8, 11); refs = page_refs(200, 20, 11); reqs, head = disk_requests(20, 200, 11)
sc = optimizer.optimise(procs, refs, 5, reqs, head)
out["scenario"] = {k: {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in sc.items()}

# 6. How long do the simulations take?
perf = []
def clock(fn, reps=3):
    best = 1e9
    for _ in range(reps):
        t = time.perf_counter(); fn(); best = min(best, time.perf_counter() - t)
    return round(best * 1000, 2)
for n in (50, 100, 200):
    p = cpu_workload(n, 1, "mixed", spread=n * 3)
    perf.append({"what": f"CPU, {n} processes (all 6 algorithms)", "ms": clock(lambda: cpu.compare(p, 4))})
for L in (1000, 5000):
    r = page_refs(L, 50, 1)
    perf.append({"what": f"Memory, {L} references, 8 frames (all 4 algorithms)", "ms": clock(lambda: memory.compare(r, 8), 2)})
rq, hd = disk_requests(1000, 200, 1)
perf.append({"what": "Disk, 1000 requests (all 6 algorithms)", "ms": clock(lambda: disk.compare(rq, hd))})
out["perf"] = perf
json.dump(out, open("bench_results.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("frames_for_18pct", "belady_strings_with_anomaly_of_500", "belady_book", "disk", "scenario", "perf", "quantum_best_score", "memory_uniform")}, indent=1))
print(json.dumps(out["cpu"]["mixed"], indent=1))
