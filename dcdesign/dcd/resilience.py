"""Resilience evaluation: what happens when one component fails (scenarios), and how available is each service (simulation)."""
import random
from . import capacity

HOURS_PER_YEAR = 8760.0
# (mean time between failures, mean time to repair) in hours; model assumptions, not vendor figures
FAILURE_PARAMS = {"host": (2000.0, 4.0), "rack": (500000.0, 8.0), "switch": (100000.0, 4.0), "feed": (17520.0, 4.0),
                  "cooling": (50000.0, 8.0), "edge": (100000.0, 4.0), "array": (200000.0, 8.0)}


def components(design):
    comp = {("host", h.name) for h in design.hosts} | {("rack", h.rack) for h in design.hosts}
    for h in design.hosts:
        comp |= {("feed", f) for f in h.feeds} | {("switch", s) for s in h.switches} | {("cooling", c) for c in h.cooling}
    comp |= {("edge", e) for e in design.edge} | {("array", a) for a in design.arrays}
    return sorted(comp)


def host_is_down(design, h, failed):
    return (("host", h.name) in failed or ("rack", h.rack) in failed
            or all(("feed", f) in failed for f in h.feeds) or all(("switch", s) in failed for s in h.switches)
            or all(("cooling", c) in failed for c in h.cooling) or all(("edge", e) in failed for e in design.edge))


def scenario(design, failed):
    """Fail the given components. VMs on dead hosts are restarted elsewhere if there is room; VMs whose only copy of the data was on a
    failed array stay down. Returns a description of the effect."""
    failed = set(failed)
    dead = {h.name for h in design.hosts if host_is_down(design, h, failed)}
    vm_map = {v.name: v for v in design.vms}
    data_lost = {v for v, a in design.vm_array.items() if ("array", a) in failed and not design.arrays[a]}
    moving = [v for v, h in design.placement.items() if h in dead and v not in data_lost]
    fixed = {v: h for v, h in design.placement.items() if h not in dead and v not in data_lost}
    placement, unplaced = capacity.place([v for v in design.vms if v.name not in data_lost], design.hosts, "ffd", fixed=fixed, blocked=tuple(dead))
    unplaced = [u for u in unplaced if u in moving]
    running = {v for v in placement}
    tiers = {v.tier for v in design.vms}
    down_groups = sorted(t for t in tiers if not any(vm_map[x].tier == t for x in running))      # a tier is a service: it is down when no VM of it runs
    critical_lost = [v for v in set(unplaced) | data_lost if vm_map[v].critical]
    return {"hosts_down": len(dead), "vms_affected": len(moving) + len(data_lost), "vms_restarted": len(moving) - len(unplaced), "vms_down": len(unplaced) + len(data_lost),
            "services_down": down_groups, "critical_vms_down": len(critical_lost), "tolerated": not down_groups and not critical_lost,
            "degraded": bool(unplaced or data_lost)}


def single_failures(design):
    rows = []
    for kind, name in components(design):
        s = scenario(design, {(kind, name)})
        rows.append({"component": f"{kind} {name}", **s})
    return rows


def spofs(rows):
    return [r for r in rows if not r["tolerated"]]


# ------------------------------------------------------------------ availability by simulation
def _union(*lists):
    pts = sorted(iv for lst in lists for iv in lst)
    out = []
    for s, e in pts:
        if out and s <= out[-1][1]:
            if e > out[-1][1]: out[-1] = (out[-1][0], e)
        else:
            out.append((s, e))
    return out


def _intersect(a, b):
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        s, e = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if s < e: out.append((s, e))
        if a[i][1] < b[j][1]: i += 1
        else: j += 1
    return out


def _renewal(rng, mtbf, mttr, horizon):
    out, t = [], 0.0
    while True:
        t += rng.expovariate(1.0 / mtbf)
        if t >= horizon: return out
        d = rng.expovariate(1.0 / mttr)
        out.append((t, min(t + d, horizon))); t += d


def _all(lists):
    """Down while ALL of the parallel paths are down."""
    it = iter(lists)
    cur = next(it)
    for nxt in it:
        cur = _intersect(cur, nxt)
    return cur


def availability(design, years=2000, seed=1, params=None):
    """Per tier, per replica pair and end to end (web, app and db all working): fraction of time the service works. Replicas share whatever they share (rack, feed, switch, array ...),
    so a failure of a shared part takes several replicas down together, which a simple series/parallel formula would miss."""
    p = params or FAILURE_PARAMS
    rng = random.Random(seed)
    horizon = years * HOURS_PER_YEAR
    draw = {c: _renewal(rng, *p[c[0]], horizon) for c in components(design)}
    array2 = {a: _renewal(rng, *p["array"], horizon) for a, mirrored in design.arrays.items() if mirrored}
    def array_down(a):
        return _intersect(draw[("array", a)], array2[a]) if design.arrays[a] else draw[("array", a)]
    host = {h.name: h for h in design.hosts}
    vm_map = {v.name: v for v in design.vms}
    cache = {}
    def replica_down(vm_name):
        h = host[design.placement[vm_name]]
        if h.name not in cache:
            cache[h.name] = _union(draw[("host", h.name)], draw[("rack", h.rack)], _all([draw[("feed", f)] for f in h.feeds]),
                                   _all([draw[("switch", s)] for s in h.switches]), _all([draw[("cooling", c)] for c in h.cooling]),
                                   _all([draw[("edge", e)] for e in design.edge]))
        return _union(cache[h.name], array_down(design.vm_array[vm_name])) if vm_name in design.vm_array else cache[h.name]
    out = {"groups": {}, "tiers": {}}
    def summary(down, replicas):
        dt = sum(e - s for s, e in down)
        return {"availability": 1 - dt / horizon, "downtime_min_per_year": dt / years * 60.0, "incidents_per_year": len(down) / years, "replicas": replicas}
    tier_down = {}
    for t in ("web", "app", "db", "mgmt"):
        members = [v.name for v in design.vms if v.tier == t]
        if members:
            tier_down[t] = _all([replica_down(m) for m in members])
            out["tiers"][t] = summary(tier_down[t], len(members))
    for g in sorted({v.group for v in design.vms}):
        members = [v.name for v in design.vms if v.group == g]
        out["groups"][g] = summary(_all([replica_down(m) for m in members]), len(members))
    out["end_to_end"] = summary(_union(*[tier_down[t] for t in ("web", "app", "db") if t in tier_down]), len(design.vms))
    return out


def tier_class(design, rows):
    """A simplified reading of the Uptime Institute tier ideas from the properties of the design. It cannot judge compartmentalisation, so the top tier is never awarded."""
    n1 = capacity.n_plus_one(design)["ok"]
    dual_power = all(len(h.feeds) >= 2 for h in design.hosts)
    dual_net = all(len(h.switches) >= 2 for h in design.hosts) and len(design.edge) >= 2
    dual_cool = all(len(h.cooling) >= 2 for h in design.hosts)
    mirrored = all(design.arrays.values())
    props = {"hosts N+1": n1, "dual power feeds": dual_power, "dual network and firewalls": dual_net, "redundant cooling": dual_cool, "mirrored storage": mirrored,
             "no single point of failure": not spofs(rows)}
    if all(props.values()):
        label = "Tier III-like (concurrently maintainable)"
    elif n1 and (dual_power or dual_cool):
        label = "Tier II-like (redundant components)"
    else:
        label = "Tier I-like (basic capacity)"
    return {"label": label, "properties": props}
