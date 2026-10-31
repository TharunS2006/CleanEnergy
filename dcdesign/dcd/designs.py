"""Reference designs, and an automatic remediation that applies the technical fixes."""
import math
from .model import Design, Host, VM, Rule, HARDENING_ITEMS
from . import capacity
from .security import POLICY

HOST_CPU, HOST_RAM = 32, 128


def make_vms(n_vms=40):
    n_db, n_mgmt = 2, 2
    n_web = max(2, int(round(0.45 * (n_vms - n_db - n_mgmt))))
    n_app = n_vms - n_db - n_mgmt - n_web
    # replicas of one service form a pair (a group) and must not share a host
    vms = [VM(f"web{i + 1}", 2, 4, "web", f"web-{i // 2 + 1}") for i in range(n_web)] + [VM(f"app{i + 1}", 4, 8, "app", f"app-{i // 2 + 1}") for i in range(n_app)]
    vms += [VM(f"db{i + 1}", 8, 32, "db", "db-1", True) for i in range(n_db)] + [VM(f"mgmt{i + 1}", 2, 4, "mgmt", "mgmt-1", True) for i in range(n_mgmt)]
    return vms


def policy_rules():
    return [Rule(s, d, p, "allow", True, "intended flow") for s, d, p in sorted(POLICY)]


def reference_design(kind="basic", n_vms=40):
    """basic: flat network, one of everything. segmented: zones and a default-deny firewall, same single-path hardware.
    resilient: segmented plus two of every path and a spare host."""
    vms = make_vms(n_vms)
    need = capacity.lower_bound_hosts(vms, HOST_CPU, HOST_RAM)
    resilient = kind == "resilient"
    n_hosts = need + (2 if resilient else 1)                 # a little slack so that anti-affinity can be satisfied
    racks = ["R1", "R2"] if resilient else ["R1"]
    hosts = [Host(f"h{i + 1}", HOST_CPU, HOST_RAM, racks[i % len(racks)], ("A", "B") if resilient else ("A",),
                  ("SW1", "SW2") if resilient else ("SW1",), ("C1", "C2") if resilient else ("C1",)) for i in range(n_hosts)]
    if kind == "basic":
        rules, default = [Rule("any", "any", "any", "allow", False, "flat network")], "allow"
        hardening = {"hypervisor_patched": True, "time_sync_and_audit": True}
    elif kind == "segmented":
        rules, default = policy_rules(), "deny"
        hardening = {k: True for k in ("hypervisor_patched", "mfa_admin", "vlan_isolation", "central_logging", "time_sync_and_audit", "rbac_least_privilege")}
    else:
        rules, default = policy_rules(), "deny"
        hardening = {k: True for k in HARDENING_ITEMS if k not in ("intrusion_detection", "secure_boot")}
    d = Design(kind, hosts, vms, rules, default, ("FW1", "FW2") if resilient else ("FW1",),
               {"SAN1": True, "SAN2": True} if resilient else {"SAN1": False}, {}, hardening)
    d.placement, un = capacity.place(d.vms, d.hosts, "ffd")
    assert not un, un
    arrays = list(d.arrays)
    d.vm_array = {v.name: arrays[i % len(arrays)] for i, v in enumerate(d.vms)}
    return d


def harden(design):
    """Apply the fixes that a tool can make safely. Returns (new design, list of changes). Process items (patching, MFA, backups ...)
    are not touched: they need people, and they stay in the list of recommendations."""
    d = design.copy()
    changes = []
    if d.default_action != "deny":
        d.default_action = "deny"; changes.append("default action set to deny")
    kept = []
    for r in d.rules:
        triple = (r.src, r.dst, r.port)
        if r.action == "allow" and (("any" in triple) or triple not in POLICY):
            changes.append(f"removed rule {r.action} {r.src} -> {r.dst} port {r.port}")
        else:
            kept.append(r)
    have = {(r.src, r.dst, r.port) for r in kept if r.action == "allow"}
    for s, dd, p in sorted(POLICY):
        if (s, dd, p) not in have:
            kept.append(Rule(s, dd, p, "allow", True, "intended flow")); changes.append(f"added intended flow {s} -> {dd} port {p}")
    for r in kept:
        if not r.encrypted:
            r.encrypted = True; changes.append(f"encryption required on {r.src} -> {r.dst} port {r.port}")
    d.rules = kept
    if len(d.edge) < 2:
        d.edge = d.edge + ("FW2",); changes.append("second firewall added")
    for h in d.hosts:
        if len(h.feeds) < 2: h.feeds = ("A", "B")
        if len(h.switches) < 2: h.switches = ("SW1", "SW2")
        if len(h.cooling) < 2: h.cooling = ("C1", "C2")
    if any(len(x.feeds) < 2 for x in design.hosts): changes.append("second power feed to every host")
    if any(len(x.switches) < 2 for x in design.hosts): changes.append("second switch to every host")
    if any(len(x.cooling) < 2 for x in design.hosts): changes.append("second cooling unit for every row")
    if len({h.rack for h in d.hosts}) < 2:
        for i, h in enumerate(d.hosts): h.rack = ["R1", "R2"][i % 2]
        changes.append("hosts spread over two racks")
    if not all(d.arrays.values()):
        d.arrays = {"SAN1": True, "SAN2": True}; names = list(d.arrays)
        d.vm_array = {v.name: names[i % 2] for i, v in enumerate(d.vms)}; changes.append("storage mirrored over two arrays")
    from . import resilience
    def rack_ok(x):
        return all(resilience.scenario(x, {("rack", r)})["tolerated"] for r in {h.rack for h in x.hosts})
    added = 0
    d.placement, _ = capacity.place(d.vms, d.hosts, "ffd")
    while (not capacity.n_plus_one(d)["ok"] or not rack_ok(d)) and added < 30:
        i = len(d.hosts) + 1
        template = d.hosts[0]
        d.hosts.append(Host(f"h{i}", template.cpu, template.ram, ["R1", "R2"][i % 2], template.feeds, template.switches, template.cooling)); added += 1
        d.placement, _ = capacity.place(d.vms, d.hosts, "ffd")
    if added:
        changes.append(f"{added} extra host(s) added so that the loss of a host or of a whole rack can be absorbed")
    d.placement, un = capacity.place(d.vms, d.hosts, "ffd")
    assert not un
    return d, changes
