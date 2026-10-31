"""Disk-arm scheduling: FCFS, SSTF, SCAN, C-SCAN, LOOK, C-LOOK.

Cylinders are numbered 0 .. cylinders-1. `direction` is the way the arm moves first (+1 towards the high cylinders).
Head movement is the sum of the distances travelled. SCAN and C-SCAN go on to the end of the disk; LOOK and C-LOOK turn back at
the last request. The return sweep of C-SCAN and C-LOOK is counted as movement (the arm still travels that distance).
"""
ALGORITHMS = ["FCFS", "SSTF", "SCAN", "C-SCAN", "LOOK", "C-LOOK"]


def simulate(algorithm, requests, head, cylinders=200, direction=1):
    algorithm = algorithm.upper()
    if algorithm not in ALGORITHMS:
        raise ValueError(f"unknown algorithm {algorithm}")
    if not requests:
        raise ValueError("no requests")
    if any(not 0 <= r < cylinders for r in requests) or not 0 <= head < cylinders:
        raise ValueError(f"cylinders must be between 0 and {cylinders - 1}")
    up = sorted(r for r in requests if r >= head)
    down = sorted((r for r in requests if r < head), reverse=True)
    path = [head]
    if algorithm == "FCFS":
        path += list(requests)
    elif algorithm == "SSTF":
        todo, pos = list(requests), head
        while todo:
            nxt = min(todo, key=lambda r: (abs(r - pos), r)); todo.remove(nxt); path.append(nxt); pos = nxt
    else:
        first, second = (up, down) if direction > 0 else (down, up)
        end_first = cylinders - 1 if direction > 0 else 0
        end_second = 0 if direction > 0 else cylinders - 1
        if algorithm == "SCAN":
            path += first
            if second:
                if path[-1] != end_first: path.append(end_first)
                path += second
        elif algorithm == "LOOK":
            path += first + second
        elif algorithm == "C-SCAN":
            path += first
            if second:
                if path[-1] != end_first: path.append(end_first)
                path.append(end_second)
                path += list(reversed(second))             # sweep the same way as before: from the far end back to the requests
        else:                                              # C-LOOK
            path += first
            if second:
                path += list(reversed(second))
    total = sum(abs(a - b) for a, b in zip(path, path[1:]))
    return {"algorithm": algorithm, "head": head, "path": path, "total": total, "average": total / len(requests)}


def compare(requests, head, cylinders=200, direction=1, algorithms=None):
    return {a: simulate(a, requests, head, cylinders, direction) for a in (algorithms or ALGORITHMS)}
