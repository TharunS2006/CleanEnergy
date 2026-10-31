"""Command line:  python -m vmdr.cli avail | compare | plan | backup | demo"""
import argparse, sys
from . import avail, sim, dr, backup


def show_avail(mtbf, mttr):
    a = avail.availability(mtbf, mttr)
    print(f"availability {100 * a:.5f}%   nines {avail.nines(a):.2f}   downtime {avail.downtime_minutes_per_year(a):.1f} min/year")
    for n in (2, 3):
        print(f"  {n} copies, any one enough: {100 * avail.parallel(*[a] * n):.7f}%")


def show_compare(p, years):
    res = sim.compare(p, years)
    print(f"{'strategy':14}{'availability':>14}{'down min/yr':>13}{'incidents/yr':>14}{'longest (min)':>15}")
    for k, r in res.items():
        print(f"{k:14}{100 * r['availability']:13.4f}%{r['downtime_min_per_year']:13.1f}{r['incidents_per_year']:14.2f}{r['longest_incident_min']:15.0f}")


def show_plan(target, rto, rpo):
    r = dr.plan(target, rto, rpo)
    for row in r["rows"]:
        name = row["strategy"] + (f" + {row['tier']}" if row["tier"] else "")
        print(f"{'OK ' if row['meets'] else '-- '}{name:34}cost {row['cost']:.2f}  availability {100 * row['availability']:.4f}%  " + ("; ".join(row["why_not"]) if row["why_not"] else ""))
    b = r["recommended"]
    print("-> recommended: " + (f"{b['strategy']}" + (f" + {b['tier']}" if b['tier'] else "") + f" (cost {b['cost']:.2f})" if b else "no strategy meets the limits"))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vmdr")
    ap.add_argument("what", choices=["demo", "avail", "compare", "plan", "backup"])
    ap.add_argument("--mtbf", type=float, default=2000.0); ap.add_argument("--mttr", type=float, default=4.0)
    ap.add_argument("--years", type=int, default=2000)
    ap.add_argument("--target", type=float, default=0.9999); ap.add_argument("--rto", type=float); ap.add_argument("--rpo", type=float)
    ap.add_argument("--interval", type=float, default=1440.0, help="backup interval, minutes"); ap.add_argument("--success", type=float, default=0.98)
    a = ap.parse_args(argv)
    if a.what in ("demo", "avail"): print("Availability of one component"); show_avail(a.mtbf, a.mttr)
    if a.what in ("demo", "compare"): print("\nStrategies on the same simulated failures (%d years)" % a.years); show_compare(sim.Params(), a.years)
    if a.what in ("demo", "plan"): print("\nPlanner: target %.4f%%, RTO %s min, RPO %s min" % (100 * a.target, a.rto, a.rpo)); show_plan(a.target, a.rto, a.rpo)
    if a.what in ("demo", "backup"):
        print("\nBackups every %.0f min, success probability %.2f" % (a.interval, a.success))
        print(f"  mean age of the newest good backup {backup.mean_data_age_minutes(a.interval, a.success):.1f} min; 99th percentile {backup.percentile_data_age_minutes(a.interval, a.success):.0f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
