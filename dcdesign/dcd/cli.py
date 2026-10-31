"""Command line:  python -m dcd.cli demo | evaluate <basic|segmented|resilient> | harden | compare"""
import argparse, sys
from . import designs, evaluate


def show(r):
    c, s, rs = r["capacity"], r["security"], r["resilience"]
    print(f"design {r['name']}: {c['hosts']} hosts, {c['vms']} VMs, CPU {c['cpu_pct']:.0f}% RAM {c['ram_pct']:.0f}%, N+1 {'yes' if c['n_plus_one'] else 'NO'}")
    print(f"  security {s['score']:.1f}  (policy {s['policy_score']:.0f}, hardening {s['hardening_score']:.0f}; critical {s['counts']['critical']} high {s['counts']['high']} medium {s['counts']['medium']} low {s['counts']['low']})")
    for z, p in s["paths"].items():
        print(f"    internet -> {z}: " + ("no route" if p["shortest"] is None else f"{p['count']} route(s), shortest {p['shortest']} hop(s): {' > '.join(p['example'])}"))
    e2e = rs["availability"]["end_to_end"]
    print(f"  resilience {rs['score']:.1f}  ({len(rs['spofs'])} single points of failure: {', '.join(x['component'] for x in rs['spofs']) or 'none'}); {rs['tier']['label']}")
    print(f"    end-to-end availability {100 * e2e['availability']:.4f}%  ({e2e['downtime_min_per_year']:.1f} min/year down)")
    print(f"  overall {r['overall']:.1f}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dcd")
    ap.add_argument("what", choices=["demo", "evaluate", "harden", "compare"])
    ap.add_argument("kind", nargs="?", default="basic", choices=["basic", "segmented", "resilient"])
    ap.add_argument("--vms", type=int, default=40); ap.add_argument("--years", type=int, default=1000)
    a = ap.parse_args(argv)
    if a.what == "evaluate":
        show(evaluate.evaluate(designs.reference_design(a.kind, a.vms), a.years))
    elif a.what == "harden":
        d = designs.reference_design(a.kind, a.vms); print("before"); show(evaluate.evaluate(d, a.years))
        h, ch = designs.harden(d); print("\nchanges:"); [print("  -", c) for c in ch]; print("\nafter"); show(evaluate.evaluate(h, a.years))
        print("\nstill to do by people: " + ", ".join(evaluate.security.hardening(h)["missing"]))
    else:
        for k in ("basic", "segmented", "resilient"):
            show(evaluate.evaluate(designs.reference_design(k, a.vms), a.years)); print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
