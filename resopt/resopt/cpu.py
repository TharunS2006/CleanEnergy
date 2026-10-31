"""CPU scheduling simulator. Time advances in whole units, so every result can be checked by hand on paper.

Algorithms: FCFS, SJF (non-preemptive), SRTF (preemptive SJF), PRIORITY and PRIORITY-P (a smaller number means a higher
priority), RR (round robin with a time quantum).
Ties are broken by arrival time and then by the order in which the processes were given.
"""
from dataclasses import dataclass

ALGORITHMS = ["FCFS", "SJF", "SRTF", "PRIORITY", "PRIORITY-P", "RR"]
PREEMPTIVE = {"SRTF", "PRIORITY-P"}


@dataclass
class Proc:
    pid: str
    arrival: int
    burst: int
    priority: int = 0


def _rows(procs, first_run, finish):
    out = []
    for p in procs:
        turnaround = finish[p.pid] - p.arrival
        out.append({"pid": p.pid, "arrival": p.arrival, "burst": p.burst, "priority": p.priority, "first_run": first_run[p.pid],
                    "finish": finish[p.pid], "turnaround": turnaround, "waiting": turnaround - p.burst,
                    "response": first_run[p.pid] - p.arrival})
    return out


def _metrics(rows, gantt):
    n = len(rows)
    busy = sum(e - s for pid, s, e in gantt if pid != "idle")
    start = min(r["arrival"] for r in rows); end = max(r["finish"] for r in rows)
    span = end - start
    run = [pid for pid, _, _ in gantt if pid != "idle"]
    switches = sum(1 for a, b in zip(run, run[1:]) if a != b)
    return {"avg_waiting": sum(r["waiting"] for r in rows) / n, "avg_turnaround": sum(r["turnaround"] for r in rows) / n,
            "avg_response": sum(r["response"] for r in rows) / n, "max_waiting": max(r["waiting"] for r in rows),
            "utilisation": busy / span if span else 1.0, "throughput": n / span if span else float(n),
            "context_switches": switches, "makespan": end - start}


def _merge(slices):
    out = []
    for pid, s, e in slices:
        if out and out[-1][0] == pid and out[-1][2] == s:
            out[-1] = (pid, out[-1][1], e)
        else:
            out.append((pid, s, e))
    return out


def simulate(algorithm, procs, quantum=4):
    algorithm = algorithm.upper()
    if algorithm not in ALGORITHMS:
        raise ValueError(f"unknown algorithm {algorithm}")
    if not procs:
        raise ValueError("no processes")
    if any(p.burst <= 0 or p.arrival < 0 for p in procs):
        raise ValueError("burst must be positive and arrival must not be negative")
    if len({p.pid for p in procs}) != len(procs):
        raise ValueError("process names must be different")
    if algorithm == "RR" and quantum < 1:
        raise ValueError("quantum must be at least 1")
    order = {p.pid: i for i, p in enumerate(procs)}
    remaining = {p.pid: p.burst for p in procs}
    first_run, finish, slices = {}, {}, []
    t = 0

    if algorithm == "RR":
        pending = sorted(procs, key=lambda p: (p.arrival, order[p.pid]))
        queue, i = [], 0
        while len(finish) < len(procs):
            while i < len(pending) and pending[i].arrival <= t:
                queue.append(pending[i]); i += 1
            if not queue:
                nxt = pending[i].arrival
                slices.append(("idle", t, nxt)); t = nxt
                continue
            p = queue.pop(0)
            first_run.setdefault(p.pid, t)
            run = min(quantum, remaining[p.pid])
            slices.append((p.pid, t, t + run)); t += run; remaining[p.pid] -= run
            while i < len(pending) and pending[i].arrival <= t:        # arrivals during the slice queue up first
                queue.append(pending[i]); i += 1
            if remaining[p.pid]:
                queue.append(p)
            else:
                finish[p.pid] = t
    else:
        primary = {"FCFS": lambda p: p.arrival, "SJF": lambda p: p.burst, "SRTF": lambda p: remaining[p.pid],
                   "PRIORITY": lambda p: p.priority, "PRIORITY-P": lambda p: p.priority}[algorithm]
        cur = None
        while len(finish) < len(procs):
            ready = [p for p in procs if p.arrival <= t and remaining[p.pid] > 0]
            if not ready:
                nxt = min(p.arrival for p in procs if remaining[p.pid] > 0)
                slices.append(("idle", t, nxt)); t = nxt; cur = None
                continue
            if cur is None or remaining[cur.pid] == 0 or algorithm in PREEMPTIVE:
                cur = min(ready, key=lambda p: (primary(p), 0 if p is cur else 1, p.arrival, order[p.pid]))
            first_run.setdefault(cur.pid, t)
            if algorithm in PREEMPTIVE:
                step = 1
            else:
                step = remaining[cur.pid]
            slices.append((cur.pid, t, t + step)); t += step; remaining[cur.pid] -= step
            if remaining[cur.pid] == 0:
                finish[cur.pid] = t
    gantt = _merge(slices)
    rows = _rows(procs, first_run, finish)
    return {"algorithm": algorithm, "quantum": quantum if algorithm == "RR" else None, "rows": rows, "gantt": gantt,
            "metrics": _metrics(rows, gantt)}


def compare(procs, quantum=4, algorithms=None):
    return {a: simulate(a, procs, quantum) for a in (algorithms or ALGORITHMS)}
