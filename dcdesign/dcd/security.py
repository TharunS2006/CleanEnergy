"""Rule-based security evaluation: firewall policy between zones, reachability of critical zones from the internet, hardening."""
from .model import ZONES, CRITICAL_ZONES, HARDENING_ITEMS

# the intended flows of a three-tier design; everything else must be blocked
POLICY = {("internet", "dmz", "443"), ("dmz", "app", "8443"), ("app", "db", "5432"),
          ("mgmt", "dmz", "22"), ("mgmt", "app", "22"), ("mgmt", "db", "22")}
PENALTY = {"critical": 25, "high": 12, "medium": 6, "low": 2}


def _covers(a, b):
    """Rule a matches everything that rule b matches (any = wildcard)."""
    return all(x == "any" or x == y for x, y in ((a.src, b.src), (a.dst, b.dst), (a.port, b.port)))


def allowed(design, src, dst, port):
    """First matching rule decides, as in a real firewall; otherwise the default action applies."""
    for r in design.rules:
        if all(x == "any" or x == y for x, y in ((r.src, src), (r.dst, dst), (r.port, port))):
            return r.action == "allow"
    return design.default_action == "allow"


def findings(design):
    out = []
    def add(sev, kind, text, rule=None):
        out.append({"severity": sev, "kind": kind, "text": text, "penalty": PENALTY[sev], "rule": rule})
    if design.default_action == "allow":
        add("critical", "default-allow", "the default action is allow: any flow that no rule mentions is permitted")
    for i, r in enumerate(design.rules):
        label = f"rule {i + 1} ({r.action} {r.src} -> {r.dst} port {r.port})"
        if r.action == "allow":
            if r.src == "any" and r.dst == "any":
                add("critical", "any-any", f"{label} allows every flow between every zone", i)
            elif "any" in (r.src, r.dst, r.port):
                add("high", "broad-rule", f"{label} uses a wildcard", i)
            elif (r.src, r.dst, r.port) not in POLICY:
                sev = "critical" if r.dst in CRITICAL_ZONES and r.src in ("internet", "dmz") else "high" if r.dst in CRITICAL_ZONES else "medium"
                add(sev, "unauthorised-flow", f"{label} is not part of the intended policy", i)
            if not r.encrypted and (r.src == "internet" or r.dst in ("db", "mgmt", "storage")):
                add("medium", "unencrypted", f"{label} carries traffic without encryption", i)
        for j in range(i):
            if _covers(design.rules[j], r):
                add("low", "shadowed-rule", f"{label} can never match: rule {j + 1} already covers it", i)
                break
    for src, dst, port in sorted(POLICY):
        if not allowed(design, src, dst, port):
            add("low", "missing-flow", f"the intended flow {src} -> {dst} port {port} is blocked, so the service may not work")
    return out


def reachability(design):
    """Zone graph: an edge exists if any flow between two zones is allowed (checked on every port named in a rule, and on 'other')."""
    ports = {r.port for r in design.rules} | {"other"}
    edges = {z: set() for z in ZONES}
    for s in ZONES:
        for d in ZONES:
            if s != d and any(allowed(design, s, d, p) for p in ports):
                edges[s].add(d)
    return edges


def attack_paths(design, max_len=4):
    """Simple paths from the internet to each critical zone through the allowed flows."""
    edges = reachability(design)
    result = {}
    for target in CRITICAL_ZONES:
        paths, stack = [], [("internet", ["internet"])]
        while stack:
            node, path = stack.pop()
            if node == target:
                paths.append(path); continue
            if len(path) > max_len:
                continue
            for n in sorted(edges[node]):
                if n not in path:
                    stack.append((n, path + [n]))
        paths.sort(key=lambda p: (len(p), p))
        result[target] = {"count": len(paths), "shortest": (len(paths[0]) - 1) if paths else None, "example": paths[0] if paths else None}
    return result


def hardening(design):
    items = {k: bool(design.hardening.get(k, False)) for k in HARDENING_ITEMS}
    score = sum(w for k, w in HARDENING_ITEMS.items() if items[k])
    return {"items": items, "score": 100.0 * score / sum(HARDENING_ITEMS.values()), "missing": [k for k, v in items.items() if not v]}


def evaluate(design):
    f = findings(design)
    paths = attack_paths(design)
    penalty = min(100, sum(x["penalty"] for x in f))
    # an open route from the internet to a critical zone is penalised even if no single rule looks wrong
    for z, p in paths.items():
        if p["shortest"] is not None and p["shortest"] <= 1:
            penalty = min(100, penalty + 20)
        elif p["shortest"] is not None and p["shortest"] == 2 and z != "db":
            penalty = min(100, penalty + 10)
    policy_score = 100 - penalty
    h = hardening(design)
    counts = {s: sum(1 for x in f if x["severity"] == s) for s in PENALTY}
    return {"policy_score": policy_score, "hardening_score": h["score"], "score": 0.6 * policy_score + 0.4 * h["score"], "findings": f, "counts": counts,
            "paths": paths, "hardening": h}
