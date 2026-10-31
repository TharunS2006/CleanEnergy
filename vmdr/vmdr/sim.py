"""Monte Carlo simulation of VM availability.

The world is a set of independent hosts, zones and regions that fail and are repaired at random (exponential times, which is
the usual assumption when only the mean time between failures and the mean repair time are known). Every strategy is then
judged on the SAME simulated failures, so differences between strategies come from the strategy and not from luck.

Time is in hours internally; results are reported in minutes.
"""
import heapq
import random
from dataclasses import dataclass, field, replace

HOURS_PER_YEAR = 8760.0


@dataclass
class Params:
    host_mtbf: float = 2000.0       # hours between failures of one physical host
    host_mttr: float = 4.0          # hours to repair a host (the VM is down for this long if nothing restarts it)
    zone_mtbf: float = 17520.0      # an availability-zone outage about every two years
    zone_mttr: float = 3.0
    region_mtbf: float = 175200.0   # a region-wide disaster about every twenty years
    region_mttr: float = 48.0
    restart_minutes: float = 6.0    # HA restarts a VM on another host: detection plus boot
    failover_minutes: float = 2.0   # switch from the active VM to the standby VM
    detect_minutes: float = 5.0     # time to notice a region outage and decide to fail over


STRATEGIES = {
    "single":        "Single VM, one zone",
    "restart":       "Single VM with automatic restart on another host",
    "ap-one-zone":   "Active-passive pair in one zone",
    "ap-two-zones":  "Active-passive pair in two zones",
    "aa-two-zones":  "Active-active pair in two zones",
    "aa-dr":         "Active-active in two zones plus a DR region",
}


# ------------------------------------------------------------------ intervals
def union(*lists):
    pts = sorted(iv for lst in lists for iv in lst)
    out = []
    for s, e in pts:
        if out and s <= out[-1][1]:
            if e > out[-1][1]:
                out[-1] = (out[-1][0], e)
        else:
            out.append((s, e))
    return out


def intersect(a, b):
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        s, e = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if s < e:
            out.append((s, e))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def total(iv):
    return sum(e - s for s, e in iv)


def clip(iv, lo, hi):
    return [(max(s, lo), min(e, hi)) for s, e in iv if min(e, hi) > max(s, lo)]


def renewal(rng, mtbf, mttr, horizon):
    """Down intervals of one component: up for Exp(mtbf), down for Exp(mttr), repeated."""
    out, t = [], 0.0
    while True:
        t += rng.expovariate(1.0 / mtbf)
        if t >= horizon:
            return out
        d = rng.expovariate(1.0 / mttr)
        out.append((t, min(t + d, horizon)))
        t += d


@dataclass
class World:
    years: float
    host: list = field(default_factory=list)       # two hosts
    zone: list = field(default_factory=list)       # two zones
    region: list = field(default_factory=list)     # primary region
    dr_region: list = field(default_factory=list)  # DR region (independent)
    host_failures_restart: list = field(default_factory=list)   # (start, duration) pairs, for the restart strategy


def make_world(p, years, seed=1):
    rng = random.Random(seed)
    h = years * HOURS_PER_YEAR
    w = World(years)
    w.host = [renewal(rng, p.host_mtbf, p.host_mttr, h) for _ in range(2)]
    w.zone = [renewal(rng, p.zone_mtbf, p.zone_mttr, h) for _ in range(2)]
    w.region = renewal(rng, p.region_mtbf, p.region_mttr, h)
    w.dr_region = renewal(rng, p.region_mtbf, p.region_mttr, h)
    return w


# ------------------------------------------------------------------ strategies
def active_passive_down(dA, dB, failover, horizon):
    """Service-down intervals for an active-passive pair. The service runs on the active instance. When it goes down and the other
    instance is up, the service is down for `failover` hours and then runs on the other one (no fail-back). If the original
    instance comes back before the switch is finished, the switch is abandoned. If both are down the service waits for the first repair."""
    ev = []
    for idx, d in enumerate((dA, dB)):
        for s, e in d:
            ev.append((s, 0, "down", idx)); ev.append((e, 1, "up", idx))
    ev.sort()
    timers, i, serial = [], 0, 0
    up = [True, True]
    active, switching, down_start, out = 0, None, None, []      # switching = (target, serial) while a switch is in progress

    def begin(t, target):
        nonlocal serial, switching
        serial += 1
        switching = (target, serial)
        heapq.heappush(timers, (t + failover, serial, target))

    while i < len(ev) or timers:
        if timers and (i >= len(ev) or timers[0][0] <= ev[i][0]):
            t, sid, target = heapq.heappop(timers)
            if switching == (target, sid):
                switching = None
                active = target
                out.append((down_start, t)); down_start = None
            continue
        t, _, kind, idx = ev[i]; i += 1
        if kind == "down":
            up[idx] = False
            if switching is not None and switching[0] == idx:       # the instance we were switching to has failed
                switching = None
            elif switching is None and idx == active and down_start is None:
                down_start = t
                if up[1 - idx]:
                    begin(t, 1 - idx)
        else:
            up[idx] = True
            if down_start is not None:
                if idx == active:                                   # the active instance is back: resume (abandon any switch)
                    out.append((down_start, t)); down_start = None; switching = None
                elif switching is None:                             # the standby is available while the service waits
                    begin(t, idx)
    if down_start is not None:
        out.append((down_start, horizon))
    return out


def dr_takeover(in_region_down, region_down, dr_down, detect_h, restore_h, horizon):
    """Add a DR region. For every outage (s, e) of the primary region: if it lasts longer than the takeover time T the service
    moves to the DR region at s + T (if that region is up), otherwise the service waits. Returns (down intervals, takeovers)."""
    T = detect_h + restore_h
    down = list(in_region_down)
    takeovers = []
    for s, e in region_down:
        if e - s <= T:
            down.append((s, e)); continue
        dr_at_takeover = [iv for iv in dr_down if iv[0] <= s + T < iv[1]]
        if dr_at_takeover:                                   # DR region is down too: wait for the first recovery
            down.append((s, min(e, dr_at_takeover[0][1]))); continue
        down.append((s, s + T))
        takeovers.append((s, s + T))
        down += intersect(dr_down, [(s + T, e)])             # the DR region may fail while it carries the service
    return union(down), takeovers


def run(strategy, p, w, dr_tier=None):
    """Evaluate one strategy on a world. Returns a dictionary of results."""
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy}")
    h = w.years * HOURS_PER_YEAR
    restart_h, failover_h = p.restart_minutes / 60.0, p.failover_minutes / 60.0
    inst0 = union(w.host[0], w.zone[0])                      # instance 0: its host or its zone is down
    inst1_other_zone = union(w.host[1], w.zone[1])
    inst1_same_zone = union(w.host[1], w.zone[0])
    takeovers = []
    if strategy == "single":
        down = union(inst0, w.region)
    elif strategy == "restart":
        quick = [(s, min(e, s + restart_h)) for s, e in w.host[0]]
        down = union(quick, w.zone[0], w.region)
    elif strategy == "ap-one-zone":
        down = union(active_passive_down(inst0, inst1_same_zone, failover_h, h), w.region)
    elif strategy == "ap-two-zones":
        down = union(active_passive_down(inst0, inst1_other_zone, failover_h, h), w.region)
    elif strategy == "aa-two-zones":
        down = union(intersect(inst0, inst1_other_zone), w.region)
    else:                                                     # aa-dr
        in_region = intersect(inst0, inst1_other_zone)
        if dr_tier is None:
            raise ValueError("the aa-dr strategy needs a DR tier")
        down, takeovers = dr_takeover(in_region, w.region, w.dr_region, p.detect_minutes / 60.0, dr_tier.restore_minutes / 60.0, h)
    down = clip(down, 0.0, h)
    dt = total(down)
    out = {"strategy": strategy, "availability": 1.0 - dt / h, "downtime_min_per_year": dt / w.years * 60.0,
           "incidents_per_year": len(down) / w.years, "mean_incident_min": (dt / len(down) * 60.0) if down else 0.0,
           "longest_incident_min": max((e - s for s, e in down), default=0.0) * 60.0, "takeovers": len(takeovers),
           "down": down}
    return out


def compare(p, years=2000, seed=1, dr_tier=None, strategies=None):
    from .dr import TIERS
    w = make_world(p, years, seed)
    tier = dr_tier or TIERS["warm-standby"]
    res = {}
    for s in (strategies or STRATEGIES):
        r = run(s, p, w, tier)
        r.pop("down")
        res[s] = r
    return res
