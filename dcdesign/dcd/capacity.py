"""Placing VMs on hosts, and checking that the cluster survives the loss of a host (N+1)."""
import math


def _fits(free, vm):
    return free[0] >= vm.cpu and free[1] >= vm.ram


def place(vms, hosts, algorithm="ffd", fixed=None, blocked=()):
    """Assign every VM to a host without exceeding CPU or memory, and without putting two VMs of one group on the same host.
    algorithm: 'ff' first fit in the given order, 'bf' best fit (least space left), 'ffd' first fit after sorting the VMs by size
    (largest first). Returns (placement, unplaced). `fixed` keeps VMs that already have a host; `blocked` are hosts that must not be used."""
    free = {h.name: [h.cpu, h.ram] for h in hosts if h.name not in blocked}
    groups = {h: set() for h in free}
    rack_of = {h.name: h.rack for h in hosts}
    group_racks = {}                                 # replicas are also spread over racks when that is possible
    placement = {}
    for vm_name, host_name in (fixed or {}).items():
        vm = next(v for v in vms if v.name == vm_name)
        free[host_name][0] -= vm.cpu; free[host_name][1] -= vm.ram; groups[host_name].add(vm.group); placement[vm_name] = host_name
        group_racks.setdefault(vm.group, set()).add(rack_of[host_name])
    todo = [v for v in vms if v.name not in placement]
    if algorithm == "ffd":
        todo.sort(key=lambda v: (-(v.cpu / 32 + v.ram / 128), v.name))
    order = [h.name for h in hosts if h.name in free]
    unplaced = []
    for vm in todo:
        cands = [n for n in order if _fits(free[n], vm) and vm.group not in groups[n]]
        if not cands:
            unplaced.append(vm.name); continue
        apart = [n for n in cands if rack_of[n] not in group_racks.get(vm.group, ())]
        cands = apart or cands
        if algorithm == "bf":
            n = min(cands, key=lambda n: ((free[n][0] - vm.cpu) / 32 + (free[n][1] - vm.ram) / 128, n))
        else:
            n = cands[0]
        free[n][0] -= vm.cpu; free[n][1] -= vm.ram; groups[n].add(vm.group); placement[vm.name] = n
        group_racks.setdefault(vm.group, set()).add(rack_of[n])
    return placement, unplaced


def lower_bound_hosts(vms, host_cpu, host_ram):
    return max(math.ceil(sum(v.cpu for v in vms) / host_cpu), math.ceil(sum(v.ram for v in vms) / host_ram))


def utilisation(design):
    used = {h.name: [0, 0] for h in design.hosts}
    vm = {v.name: v for v in design.vms}
    for v, h in design.placement.items():
        used[h][0] += vm[v].cpu; used[h][1] += vm[v].ram
    rows = []
    for h in design.hosts:
        rows.append({"host": h.name, "rack": h.rack, "cpu_pct": 100.0 * used[h.name][0] / h.cpu, "ram_pct": 100.0 * used[h.name][1] / h.ram,
                     "vms": sum(1 for x in design.placement.values() if x == h.name)})
    tc, tr = sum(h.cpu for h in design.hosts), sum(h.ram for h in design.hosts)
    return {"hosts": rows, "cpu_pct": 100.0 * sum(u[0] for u in used.values()) / tc, "ram_pct": 100.0 * sum(u[1] for u in used.values()) / tr}


def survive_host_failure(design, host_name):
    """Can the VMs of one failed host be restarted on the other hosts? Returns the VMs that cannot."""
    vm_map = {v.name: v for v in design.vms}
    fixed = {v: h for v, h in design.placement.items() if h != host_name}
    lost = [v for v, h in design.placement.items() if h == host_name]
    _, unplaced = place(design.vms, design.hosts, "ffd", fixed=fixed, blocked=(host_name,))
    return [v for v in unplaced if v in lost]


def n_plus_one(design):
    """The cluster is N+1 when every single host can fail without losing a VM."""
    bad = {}
    for h in design.hosts:
        left = survive_host_failure(design, h.name)
        if left:
            bad[h.name] = left
    return {"ok": not bad, "failing_hosts": bad}
