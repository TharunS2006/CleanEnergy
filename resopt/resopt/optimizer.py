"""The optimizer: runs every algorithm on the same workload, ranks them, and says which one to use and why."""
from . import cpu, memory, disk

CPU_NOTES = {
    "SRTF": "gives the smallest average waiting time of all algorithms, but long processes can be starved",
    "SJF": "very low average waiting time without pre-emption; needs the burst length in advance",
    "RR": "best response time and fair to every process; more context switches",
    "FCFS": "simplest and fair by arrival, but one long process delays everything behind it",
    "PRIORITY": "obeys priorities; low-priority processes can wait indefinitely",
    "PRIORITY-P": "obeys priorities at once; low-priority processes can wait indefinitely",
}


def recommend_cpu(procs, quantum=4):
    runs = cpu.compare(procs, quantum)
    best = {}
    for key in ("avg_waiting", "avg_turnaround", "avg_response", "max_waiting", "context_switches"):
        low = min(r["metrics"][key] for r in runs.values())
        best[key] = [a for a, r in runs.items() if r["metrics"][key] == low]
    pick = best["avg_waiting"][0]
    return {"runs": runs, "best": best, "recommended": pick, "why": CPU_NOTES[pick],
            "baseline": runs["FCFS"]["metrics"]["avg_waiting"], "improvement": gain(runs["FCFS"]["metrics"]["avg_waiting"], runs[pick]["metrics"]["avg_waiting"])}


def tune_quantum(procs, quanta, switch_cost=0.5):
    """score = average turnaround + switch_cost x context switches / number of processes.
    The switch cost (time units lost at every context switch) is a parameter of the model, not a measured value."""
    rows = []
    for q in quanta:
        m = cpu.simulate("RR", procs, q)["metrics"]
        rows.append({"quantum": q, "avg_waiting": m["avg_waiting"], "avg_response": m["avg_response"], "avg_turnaround": m["avg_turnaround"],
                     "context_switches": m["context_switches"],
                     "score": m["avg_turnaround"] + switch_cost * m["context_switches"] / len(procs)})
    best = min(rows, key=lambda r: (r["score"], r["quantum"]))
    return {"rows": rows, "best_quantum": best["quantum"], "switch_cost": switch_cost}


def recommend_memory(refs, frames):
    runs = memory.compare(refs, frames)
    real = {a: r["faults"] for a, r in runs.items() if a != "OPT"}
    pick = min(real, key=lambda a: (real[a], a))
    return {"runs": runs, "recommended": pick, "optimal_faults": runs["OPT"]["faults"],
            "gap_to_optimal": runs[pick]["faults"] - runs["OPT"]["faults"],
            "improvement": gain(runs["FIFO"]["faults"], runs[pick]["faults"])}


def tune_frames(refs, algorithm, max_frames, target_rate=0.1):
    curve = [(f, memory.simulate(algorithm, refs, f)["fault_rate"]) for f in range(1, max_frames + 1)]
    enough = next((f for f, rate in curve if rate <= target_rate), None)
    return {"curve": curve, "frames_needed": enough, "target_rate": target_rate}


def recommend_disk(requests, head, cylinders=200, direction=1):
    runs = disk.compare(requests, head, cylinders, direction)
    pick = min(runs, key=lambda a: (runs[a]["total"], a))
    return {"runs": runs, "recommended": pick, "improvement": gain(runs["FCFS"]["total"], runs[pick]["total"])}


def gain(base, new):
    """Percentage by which `new` is lower than `base` (positive = better)."""
    return 0.0 if base == 0 else 100.0 * (base - new) / base


def optimise(procs, refs, frames, requests, head, quantum=4, cylinders=200):
    """One scenario, all three resources: best choice for each and the saving against the plain baseline (FCFS, FIFO, FCFS)."""
    c, m, d = recommend_cpu(procs, quantum), recommend_memory(refs, frames), recommend_disk(requests, head, cylinders)
    return {"cpu": {"choice": c["recommended"], "baseline": c["baseline"], "best": c["runs"][c["recommended"]]["metrics"]["avg_waiting"], "gain": c["improvement"]},
            "memory": {"choice": m["recommended"], "baseline": m["runs"]["FIFO"]["faults"], "best": m["runs"][m["recommended"]]["faults"], "gain": m["improvement"]},
            "disk": {"choice": d["recommended"], "baseline": d["runs"]["FCFS"]["total"], "best": d["runs"][d["recommended"]]["total"], "gain": d["improvement"]}}
