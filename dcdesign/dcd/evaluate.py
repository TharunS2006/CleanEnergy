"""Evaluate a design as a whole."""
from . import capacity, security, resilience


def evaluate(design, years=2000, seed=1):
    util = capacity.utilisation(design)
    n1 = capacity.n_plus_one(design)
    sec = security.evaluate(design)
    rows = resilience.single_failures(design)
    bad = resilience.spofs(rows)
    res_score = 100.0 * (len(rows) - len(bad)) / len(rows)
    av = resilience.availability(design, years, seed)
    tier = resilience.tier_class(design, rows)
    cap_score = 100.0 if n1["ok"] else 100.0 * (1 - len(n1["failing_hosts"]) / len(design.hosts))
    return {"name": design.name, "capacity": {"hosts": len(design.hosts), "vms": len(design.vms), "cpu_pct": util["cpu_pct"], "ram_pct": util["ram_pct"],
                                               "n_plus_one": n1["ok"], "failing_hosts": n1["failing_hosts"], "score": cap_score, "per_host": util["hosts"]},
            "security": sec, "resilience": {"score": res_score, "scenarios": rows, "spofs": bad, "availability": av, "tier": tier},
            "overall": 0.25 * cap_score + 0.4 * sec["score"] + 0.35 * res_score}
