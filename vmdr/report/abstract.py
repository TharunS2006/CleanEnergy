import json, pathlib
R = json.load(open(pathlib.Path(__file__).parent.parent / "bench_results.json"))
S = R["strategies"]; T = {t["key"]: t for t in R["tiers"]}
ABSTRACT = (
    "Businesses run their services on virtual machines (VMs) that sit on physical hosts, inside availability zones, inside regions, and every "
    "one of these layers can fail. The design of a deployment, how many VMs, in which zones, with what failover and with what copy in another "
    "region, decides how much downtime and how much lost data a failure causes, and also decides the cost. Choosing the design usually "
    "rests on rules of thumb. This mini project builds a tool that replaces the rules of thumb with calculation and simulation, using only the Python "
    "standard library. It provides the closed-form mathematics of availability (MTBF and MTTR, series and parallel systems, a Markov model of "
    "an active-passive pair), a Monte Carlo simulator that fails hosts, zones and regions at random and judges six designs on the same failures, "
    "four disaster-recovery tiers (backup and restore, pilot light, warm standby, multi-region active-active) with their recovery time (RTO) and data loss (RPO), "
    "a backup calculator, and a planner that returns the cheapest design meeting an availability target and RTO and RPO limits. "
    "The simulator reproduces the closed-form and Markov-model results within 2.4% in all six comparisons. "
    f"Over {R['years']:,} simulated years a single VM was down {S['single']['downtime_min_per_year'] / 60:.1f} hours a year; automatic restart cut this to {S['restart']['downtime_min_per_year'] / 60:.1f} hours; "
    f"two active VMs in two zones reached {S['aa-two-zones']['downtime_min_per_year'] / 60:.1f} hours, a floor set by region disasters; and adding a warm-standby DR region reduced downtime to "
    f"{S['aa-dr']['downtime_min_per_year']:.1f} minutes a year, with about {T['warm-standby']['rpo_mean_min']:.0f} minute of data lost per disaster. "
    "A command-line tool and a browser interface are provided, and 39 automated tests pass.")
