"""Disaster-recovery tiers and the planner that chooses between strategies.

The tier parameters (restore time, replication lag, relative cost) are modelling assumptions in the style of common cloud
architecture guidance; they are inputs of the model, not measurements. Change them to match a real provider and price list.
"""
import math
import random
from dataclasses import dataclass

from . import sim
from .avail import HOURS_PER_YEAR


@dataclass(frozen=True)
class Tier:
    key: str
    name: str
    restore_minutes: float      # time from the decision to fail over until the service runs in the DR region (RTO part)
    rpo_model: str              # "backup" (age of the last backup) or "async" (replication lag)
    rpo_mean_minutes: float     # mean age of the data that is lost at takeover
    extra_cost: float           # added cost in 'VM equivalents' (the primary site costs 2.1 for two VMs and a load balancer)
    note: str


TIERS = {
    "backup-restore": Tier("backup-restore", "Backup and restore", 240.0, "backup", 720.0, 0.1,
                           "daily backup copied to another region; the VM is rebuilt from the backup after a disaster"),
    "pilot-light": Tier("pilot-light", "Pilot light", 60.0, "async", 5.0, 0.3,
                        "data is replicated continuously, but the VMs in the DR region are switched off and started on demand"),
    "warm-standby": Tier("warm-standby", "Warm standby", 15.0, "async", 1.0, 1.0,
                         "a smaller copy of the service runs all the time in the DR region and is scaled up on demand"),
    "multi-active": Tier("multi-active", "Multi-region active-active", 2.0, "async", 0.1, 2.1,
                         "both regions serve users; the surviving region takes all the traffic"),
}


def sample_data_loss_minutes(tier, rng):
    """Age of the data lost at one takeover: uniform over the backup interval, or exponential with the replication lag."""
    if tier.rpo_model == "backup":
        return rng.uniform(0.0, 2.0 * tier.rpo_mean_minutes)
    return rng.expovariate(1.0 / tier.rpo_mean_minutes)


def dr_events(p, tier, years=20000, seed=1):
    """Simulate region disasters on their own: how often the service must be moved, how long it takes and how much data is lost."""
    w = sim.make_world(p, years, seed)
    h = years * HOURS_PER_YEAR
    down, takeovers = sim.dr_takeover([], w.region, w.dr_region, p.detect_minutes / 60.0, tier.restore_minutes / 60.0, h)
    rng = random.Random(seed + 1)
    losses = [sample_data_loss_minutes(tier, rng) for _ in takeovers]
    outage_hours = sim.total(down)
    return {"disasters": len(w.region), "takeovers": len(takeovers), "disasters_per_year": len(w.region) / years,
            "takeovers_per_year": len(takeovers) / years, "rto_minutes": p.detect_minutes + tier.restore_minutes,
            "mean_data_loss_min": (sum(losses) / len(losses)) if losses else 0.0, "max_data_loss_min": max(losses, default=0.0),
            "disaster_downtime_min_per_year": outage_hours / years * 60.0}


# ------------------------------------------------------------------ planner
COSTS = {"single": 1.0, "restart": 1.1, "ap-one-zone": 2.0, "ap-two-zones": 2.05, "aa-two-zones": 2.1}


def plan(target_availability, rto_minutes=None, rpo_minutes=None, p=None, years=4000, seed=1):
    """Cheapest strategy that meets the availability target, and the RTO and RPO limits for a region disaster.
    A strategy without a DR region cannot meet an RTO or RPO that is shorter than the repair of a region, so it fails those limits."""
    p = p or sim.Params()
    w = sim.make_world(p, years, seed)
    rows = []
    region_hours = p.region_mttr
    for s in ("single", "restart", "ap-one-zone", "ap-two-zones", "aa-two-zones"):
        r = sim.run(s, p, w)
        rto = region_hours * 60.0                          # a region disaster is survived only by waiting for the region
        rows.append({"strategy": s, "tier": None, "cost": COSTS[s], "availability": r["availability"], "rto_minutes": rto, "rpo_minutes": 0.0,
                     "downtime_min_per_year": r["downtime_min_per_year"]})
    for key, tier in TIERS.items():
        r = sim.run("aa-dr", p, w, tier)
        rows.append({"strategy": "aa-dr", "tier": key, "cost": COSTS["aa-two-zones"] + tier.extra_cost,
                     "availability": r["availability"], "rto_minutes": p.detect_minutes + tier.restore_minutes, "rpo_minutes": tier.rpo_mean_minutes,
                     "downtime_min_per_year": r["downtime_min_per_year"]})
    for row in rows:
        why = []
        if row["availability"] < target_availability:
            why.append(f"availability {100 * row['availability']:.4f}% is below the target")
        if rto_minutes is not None and row["rto_minutes"] > rto_minutes:
            why.append(f"recovery time {row['rto_minutes']:.0f} min is above {rto_minutes:.0f} min")
        if rpo_minutes is not None and row["strategy"] == "aa-dr" and row["rpo_minutes"] > rpo_minutes:
            why.append(f"data loss {row['rpo_minutes']:.1f} min is above {rpo_minutes:.1f} min")
        if rpo_minutes is not None and row["strategy"] != "aa-dr":
            why.append("no copy of the data outside the region")
        row["meets"] = not why
        row["why_not"] = why
    ok = [r for r in rows if r["meets"]]
    best = min(ok, key=lambda r: (r["cost"], -r["availability"])) if ok else None
    return {"rows": rows, "recommended": best, "target": target_availability, "rto_minutes": rto_minutes, "rpo_minutes": rpo_minutes}
