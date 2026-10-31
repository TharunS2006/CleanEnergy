"""Command line:  python -m resopt.cli demo | cpu | memory | disk   (each uses the textbook examples unless values are given)"""
import argparse, sys
from . import optimizer, cpu, memory, disk
from .cpu import Proc

TEXTBOOK_PROCS = [Proc("P1", 0, 24), Proc("P2", 0, 3), Proc("P3", 0, 3)]
TEXTBOOK_REFS = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]
TEXTBOOK_DISK = [98, 183, 37, 122, 14, 124, 65, 67]


def show_cpu(procs, quantum):
    rec = optimizer.recommend_cpu(procs, quantum)
    print(f"{'algorithm':12}{'avg wait':>10}{'avg turn':>10}{'avg resp':>10}{'switches':>10}")
    for a, r in rec["runs"].items():
        m = r["metrics"]; print(f"{a:12}{m['avg_waiting']:10.2f}{m['avg_turnaround']:10.2f}{m['avg_response']:10.2f}{m['context_switches']:10d}")
    print(f"-> recommended: {rec['recommended']} ({rec['why']}); {rec['improvement']:.1f}% lower average waiting than FCFS")


def show_memory(refs, frames):
    rec = optimizer.recommend_memory(refs, frames)
    for a, r in rec["runs"].items(): print(f"{a:6} faults {r['faults']:4d}  fault rate {r['fault_rate']:.2f}")
    print(f"-> recommended: {rec['recommended']}  ({rec['gap_to_optimal']} faults above the optimal {rec['optimal_faults']})")


def show_disk(reqs, head, cylinders, direction):
    rec = optimizer.recommend_disk(reqs, head, cylinders, direction)
    for a, r in rec["runs"].items(): print(f"{a:7} head movement {r['total']:5d}")
    print(f"-> recommended: {rec['recommended']}  ({rec['improvement']:.1f}% less movement than FCFS)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="resopt")
    ap.add_argument("what", choices=["demo", "cpu", "memory", "disk"])
    ap.add_argument("--procs", help="CPU: 'P1:0:24,P2:0:3' = name:arrival:burst[:priority]")
    ap.add_argument("--quantum", type=int, default=4)
    ap.add_argument("--refs", help="memory: comma-separated page numbers"); ap.add_argument("--frames", type=int, default=3)
    ap.add_argument("--requests", help="disk: comma-separated cylinders"); ap.add_argument("--head", type=int, default=53)
    ap.add_argument("--cylinders", type=int, default=200); ap.add_argument("--direction", type=int, default=1, choices=[-1, 1])
    a = ap.parse_args(argv)
    procs = TEXTBOOK_PROCS if not a.procs else [Proc(*([x[0], *map(int, x[1:])])) for x in (s.split(":") for s in a.procs.split(","))]
    refs = TEXTBOOK_REFS if not a.refs else [int(x) for x in a.refs.split(",")]
    reqs = TEXTBOOK_DISK if not a.requests else [int(x) for x in a.requests.split(",")]
    if a.what in ("demo", "cpu"): print("CPU scheduling"); show_cpu(procs, a.quantum)
    if a.what in ("demo", "memory"): print("\nPage replacement, %d frames" % a.frames); show_memory(refs, a.frames)
    if a.what in ("demo", "disk"): print("\nDisk scheduling, head at %d" % a.head); show_disk(reqs, a.head, a.cylinders, a.direction)
    return 0


if __name__ == "__main__":
    sys.exit(main())
