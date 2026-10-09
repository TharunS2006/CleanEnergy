"""Azure: everything CloudPulse reads from one subscription, in one scan.

Reads (all read-only, Reader + Cost Management Reader is enough):
  1. Cost Management  - daily cost by service, and daily cost by resource
  2. Resource Graph   - every resource with its tags, plus details of disks,
                        public IPs, snapshots and VMs (incl. power state)
  3. Azure Monitor    - 14 days of hourly CPU and network for running VMs
  4. Azure Advisor    - cost recommendations
  5. Activity Log     - who created a resource (called per flagged resource)

A scan returns plain data plus a list of *signals*. The findings engine
(app/services/findings.py) turns signals into findings.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from app.services import analytics as A
from app.services.azure_rest import ArmClient, ArmError
from app.services.prices import HOURS_PER_MONTH, PriceBook

log = logging.getLogger("cloudpulse")
PROVIDER = "azure"
COST_API = "2023-11-01"
MAX_VMS_WITH_METRICS = 50
METRIC_DAYS = 14
GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


# ==========================================================================
# helpers
# ==========================================================================
def _get(d: dict, *keys, default=None):
    """Read a key from a dict or its nested `properties` block, accepting
    camelCase or snake_case spellings."""
    for scope in (d, d.get("properties") or {}):
        for k in keys:
            if isinstance(scope, dict) and k in scope and scope[k] is not None:
                return scope[k]
    return default


def _path(d, *path, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
    return default if cur is None else cur


def resource_group(resource_id: str) -> str:
    parts = (resource_id or "").split("/")
    for i, p in enumerate(parts):
        if p.lower() == "resourcegroups" and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def client_for(t) -> ArmClient:
    if getattr(t, "_arm", None) is None:
        t._arm = ArmClient(t.credential())
    return t._arm


# ==========================================================================
# connection
# ==========================================================================
def check_connection(t) -> tuple[bool, str]:
    try:
        body = client_for(t).get(f"/subscriptions/{t.subscription_id}", {"api-version": "2022-12-01"})
    except ArmError as e:
        if e.status in (401, 403):
            return False, "Signed in, but this identity has no Reader role on the subscription."
        if e.status == 404:
            return False, "Subscription not found. Check the subscription ID."
        return False, f"Azure answered {e.status}: {e.message[:200]}"
    except Exception as e:  # noqa: BLE001
        return False, f"Azure sign-in failed: {str(e).splitlines()[0][:240]}"
    return True, body.get("displayName") or f"Subscription {t.subscription_id}"


# ==========================================================================
# 1. Cost Management
# ==========================================================================
def _cost_body(start: date, end: date, grouping: list[str]) -> dict:
    return {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {"from": f"{start.isoformat()}T00:00:00Z", "to": f"{end.isoformat()}T23:59:59Z"},
        "dataset": {
            "granularity": "Daily",
            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            "grouping": [{"type": "Dimension", "name": g} for g in grouping],
        },
    }


def parse_cost_rows(columns: list[str], rows: list[list]) -> list[dict]:
    """Cost Management returns a table, e.g. [Cost, UsageDate, ServiceName, Currency].
    UsageDate arrives as an int like 20260914."""
    idx = {(name or "").lower(): i for i, name in enumerate(columns)}
    cost_i = next((idx[k] for k in ("cost", "pretaxcost", "totalcost", "costusd") if k in idx), None)
    date_i = idx.get("usagedate")
    svc_i = idx.get("servicename")
    res_i = idx.get("resourceid")
    cur_i = idx.get("currency")
    if cost_i is None or date_i is None:
        return []
    out = []
    for r in rows:
        amount = float(r[cost_i] or 0)
        if amount == 0:
            continue
        raw = str(r[date_i])
        day = f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}" if raw.isdigit() else raw[:10]
        item = {
            "provider": PROVIDER,
            "service": (r[svc_i] if svc_i is not None else None) or "Other",
            "date": day,
            "amount": amount,
            "currency": (r[cur_i] if cur_i is not None else None) or "USD",
        }
        if res_i is not None:
            item["resource_id"] = (r[res_i] or "").lower()
        out.append(item)
    return out


def fetch_costs(t, start: date, end: date) -> list[dict]:
    cols, rows = client_for(t).post_all_rows(
        f"/subscriptions/{t.subscription_id}/providers/Microsoft.CostManagement/query",
        _cost_body(start, end, ["ServiceName"]), {"api-version": COST_API})
    return parse_cost_rows(cols, rows)


def fetch_resource_costs(t, start: date, end: date) -> list[dict]:
    cols, rows = client_for(t).post_all_rows(
        f"/subscriptions/{t.subscription_id}/providers/Microsoft.CostManagement/query",
        _cost_body(start, end, ["ResourceId", "ServiceName"]), {"api-version": COST_API})
    return [r for r in parse_cost_rows(cols, rows) if r.get("resource_id")]


# ==========================================================================
# 2. Resource Graph inventory
# ==========================================================================
Q_ALL = "Resources | project id, name, type, location, resourceGroup, tags"
Q_GROUPS = ("ResourceContainers | where type =~ 'microsoft.resources/subscriptions/resourcegroups' "
            "| project name, tags")
Q_DETAIL = ("Resources | where type in~ ('microsoft.compute/disks', 'microsoft.network/publicipaddresses', "
            "'microsoft.compute/snapshots', 'microsoft.compute/virtualmachines') "
            "| project id, name, type, location, resourceGroup, tags, sku, properties")


def fetch_inventory(t) -> dict:
    c = client_for(t)
    return {
        "resources": c.resource_graph(t.subscription_id, Q_ALL),
        "groups": c.resource_graph(t.subscription_id, Q_GROUPS),
        "detail": c.resource_graph(t.subscription_id, Q_DETAIL),
    }


def tag_stats(inventory: dict, resource_costs: list[dict], last_day: date | None) -> dict:
    """Untagged spend over the last 30 days. A resource counts as tagged if it
    or its resource group has at least one tag."""
    rg_tagged = {(g.get("name") or "").lower() for g in inventory.get("groups", []) if g.get("tags")}
    by_id = {(r.get("id") or "").lower(): r for r in inventory.get("resources", [])}
    since = (last_day - timedelta(days=29)).isoformat() if last_day else "0000"
    cost = defaultdict(float)
    for r in resource_costs:
        if r["date"] >= since:
            cost[r["resource_id"]] += r["amount"]
    total = sum(cost.values())
    untagged = []
    for rid, amt in cost.items():
        res = by_id.get(rid)
        rg = resource_group(rid).lower()
        has_tags = bool(res and res.get("tags")) or rg in rg_tagged
        if not has_tags:
            untagged.append({"resource_id": rid, "name": (res or {}).get("name") or rid.split("/")[-1],
                             "type": (res or {}).get("type", ""), "cost_30d": round(amt, 2),
                             "id_original": (res or {}).get("id") or rid})
    untagged.sort(key=lambda x: x["cost_30d"], reverse=True)
    return {"total_30d": round(total, 2), "untagged_30d": round(sum(u["cost_30d"] for u in untagged), 2),
            "untagged": untagged}


# ==========================================================================
# 3. Actual cost per resource
# ==========================================================================
def index_resource_costs(resource_costs: list[dict]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in resource_costs:
        out[r["resource_id"]][r["date"]] += r["amount"]
    return out


def actual_monthly(cost_index: dict, ids: list[str], last_day: date | None) -> tuple[float, int] | None:
    """Average daily cost of these resources since they first appear in the
    cost data (at most the last 30 days), times 30.4. Needs 3+ days."""
    if not last_day:
        return None
    ids = [i.lower() for i in ids if i]
    days_seen = sorted({d for i in ids for d in cost_index.get(i, {})})
    if not days_seen:
        return None
    start = max(date.fromisoformat(days_seen[0]), last_day - timedelta(days=29))
    window = (last_day - start).days + 1
    if window < 3:
        return None
    total = sum(v for i in ids for d, v in cost_index.get(i, {}).items() if d >= start.isoformat())
    return round(total / window * A.DAYS_PER_MONTH, 2), window


# ==========================================================================
# 4. Idle-resource detectors (pure; input = Resource Graph rows)
# ==========================================================================
def _enum(v) -> str:
    return str(getattr(v, "value", v) or "")


def _base(r: dict, rtype: str) -> dict:
    rid = r.get("id") or ""
    return {"provider": PROVIDER, "resource_id": rid, "resource_name": r.get("name") or rid.split("/")[-1],
            "resource_type": rtype, "resource_group": r.get("resourceGroup") or resource_group(rid),
            "region": r.get("location", ""), "tags": r.get("tags") or {}}


def find_unattached_disks(disks: list[dict], prices: PriceBook) -> list[dict]:
    out = []
    for d in disks:
        if _enum(_get(d, "diskState", "disk_state")).lower() != "unattached":
            continue
        size = int(_get(d, "diskSizeGB", "disk_size_gb", default=0) or 0)
        sku = _enum((d.get("sku") or {}).get("name")) or "Standard_LRS"
        monthly, source, tier = prices.disk_monthly(d.get("location", ""), sku, size)
        s = _base(d, "disk")
        s.update(
            kind="idle_resource", title=f"Disk {s['resource_name']} is attached to nothing",
            summary=f"{size} GB {sku.replace('_', ' ')} disk (billed as {tier}) with no VM attached.",
            monthly_impact=monthly, impact_basis=f"list price, {source}", confidence=0.95,
            evidence={"rule": "diskState = Unattached", "size_gb": size, "sku": sku, "billing_tier": tier,
                      "created": _get(d, "timeCreated", "time_created")},
            fix=[{"label": "Keep a copy first (optional)",
                  "cmd": f"az snapshot create -g {s['resource_group']} -n {s['resource_name']}-backup --source {d.get('id')}"},
                 {"label": "Delete the disk", "cmd": f"az disk delete --ids {d.get('id')} --yes"}],
        )
        out.append(s)
    return out


def find_idle_public_ips(ips: list[dict], prices: PriceBook) -> list[dict]:
    out = []
    for p in ips:
        if _get(p, "ipConfiguration", "ip_configuration") or _get(p, "natGateway", "nat_gateway"):
            continue
        method = _enum(_get(p, "publicIPAllocationMethod", "public_ip_allocation_method")).lower()
        if method == "dynamic":
            continue  # a dynamic IP with nothing attached has no address and costs nothing
        monthly, source = prices.public_ip_monthly(p.get("location", ""))
        address = _get(p, "ipAddress", "ip_address") or "no address"
        s = _base(p, "public_ip")
        s.update(
            kind="idle_resource", title=f"Public IP {s['resource_name']} points at nothing",
            summary=f"Static public IP {address} is reserved but not attached to any resource.",
            monthly_impact=monthly, impact_basis=f"list price, {source}", confidence=0.95,
            evidence={"rule": "no ipConfiguration and no NAT gateway, static allocation", "address": address},
            fix=[{"label": "Release the address", "cmd": f"az network public-ip delete --ids {p.get('id')}"}],
        )
        out.append(s)
    return out


def find_stale_snapshots(snapshots: list[dict], disk_ids: set[str], prices: PriceBook,
                         now: datetime | None = None, max_age_days: int = 30) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    out = []
    for sn in snapshots:
        size = int(_get(sn, "diskSizeGB", "disk_size_gb", default=0) or 0)
        source_id = (_get(_get(sn, "creationData", "creation_data", default={}) or {},
                          "sourceResourceId", "source_resource_id") or "").lower()
        created_raw = _get(sn, "timeCreated", "time_created")
        age = None
        if created_raw:
            try:
                age = (now - datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))).days
            except ValueError:
                pass
        orphaned = bool(source_id) and "/disks/" in source_id and source_id not in disk_ids
        old = age is not None and age > max_age_days
        if not (orphaned or old):
            continue
        monthly, source = prices.snapshot_monthly(sn.get("location", ""), size)
        why = "its source disk has been deleted" if orphaned else f"it is {age} days old"
        s = _base(sn, "snapshot")
        s.update(
            kind="idle_resource", title=f"Snapshot {s['resource_name']} is no longer needed",
            summary=f"{size} GB snapshot kept although {why}.",
            monthly_impact=monthly, impact_basis=f"list price, {source}",
            confidence=0.9 if orphaned else 0.6,
            evidence={"rule": "source disk missing" if orphaned else f"older than {max_age_days} days",
                      "size_gb": size, "age_days": age, "source_disk": source_id or None},
            fix=[{"label": "Delete the snapshot", "cmd": f"az snapshot delete --ids {sn.get('id')}"}],
        )
        out.append(s)
    return out


def vm_power_state(vm: dict) -> str:
    code = _path(vm, "properties", "extended", "instanceView", "powerState", "code", default="")
    if not code:
        codes = [c.lower() for c in vm.get("_statuses", [])]
        code = next((c for c in codes if c.startswith("powerstate/")), "")
    return code.lower().replace("powerstate/", "")


def vm_size(vm: dict) -> str:
    return _get(_get(vm, "hardwareProfile", "hardware_profile", default={}) or {}, "vmSize", "vm_size") or ""


def vm_disk_ids(vm: dict) -> list[str]:
    sp = _get(vm, "storageProfile", "storage_profile", default={}) or {}
    ids = [_path(sp, "osDisk", "managedDisk", "id")]
    ids += [_path(d, "managedDisk", "id") for d in sp.get("dataDisks", []) or []]
    return [i.lower() for i in ids if i]


def _disks_monthly(disk_ids, disks_by_id, prices):
    total, parts = 0.0, []
    for i in disk_ids:
        d = disks_by_id.get(i)
        if not d:
            continue
        size = int(_get(d, "diskSizeGB", "disk_size_gb", default=0) or 0)
        sku = _enum((d.get("sku") or {}).get("name")) or "Standard_LRS"
        m, _, tier = prices.disk_monthly(d.get("location", ""), sku, size)
        total += m
        parts.append({"disk": d.get("name"), "size_gb": size, "tier": tier, "monthly": m})
    return round(total, 2), parts


def find_stopped_vms(vms: list[dict], disks_by_id: dict, prices: PriceBook) -> list[dict]:
    out = []
    for vm in vms:
        state = vm_power_state(vm)
        if state not in ("stopped", "deallocated"):
            continue
        size = vm_size(vm)
        disk_total, disk_parts = _disks_monthly(vm_disk_ids(vm), disks_by_id, prices)
        s = _base(vm, "vm")
        rid = vm.get("id")
        if state == "stopped":
            hourly, source = prices.vm_hourly(vm.get("location", ""), size)
            compute = round((hourly or 0) * HOURS_PER_MONTH, 2)
            s.update(
                kind="idle_resource", title=f"VM {s['resource_name']} is stopped but still billed",
                summary=f"{size} was shut down from inside (stopped, not deallocated), so compute keeps billing.",
                monthly_impact=round(compute + disk_total, 2),
                impact_basis=f"list price, {source}" if hourly else "disk list price only (VM size price unknown)",
                confidence=0.9,
                evidence={"rule": "power state = stopped", "size": size, "compute_monthly": compute,
                          "disks_monthly": disk_total, "disks": disk_parts},
                fix=[{"label": "Stop billing for compute", "cmd": f"az vm deallocate --ids {rid}"},
                     {"label": "Or remove it if nobody needs it", "cmd": f"az vm delete --ids {rid} --yes"}],
            )
        else:
            s.update(
                kind="idle_resource", title=f"Deallocated VM {s['resource_name']} still pays for its disks",
                summary=f"{size} is deallocated (no compute charge) but its {len(disk_parts)} disk(s) keep billing.",
                monthly_impact=disk_total, impact_basis="disk list price", confidence=0.6,
                evidence={"rule": "power state = deallocated", "size": size, "disks": disk_parts,
                          "note": "Some teams keep deallocated VMs on purpose; dismiss this finding if so."},
                fix=[{"label": "Delete the VM if it's no longer needed (disks are kept unless you delete them too)",
                      "cmd": f"az vm delete --ids {rid} --yes"}],
            )
        s["extra_cost_ids"] = vm_disk_ids(vm)
        out.append(s)
    return out


# ==========================================================================
# 5. Azure Monitor: running VMs
# ==========================================================================
def fetch_vm_metrics(t, vm_id: str, end: datetime) -> dict:
    start = end - timedelta(days=METRIC_DAYS)
    body = client_for(t).get(f"{vm_id}/providers/Microsoft.Insights/metrics", {
        "api-version": "2023-10-01",
        "metricnames": "Percentage CPU,Network In Total,Network Out Total",
        "timespan": f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "interval": "PT1H",
        "aggregation": "Average,Maximum,Total",
    })
    return parse_vm_metrics(body)


def parse_vm_metrics(body: dict) -> dict:
    cpu_avg, cpu_max, net = [], [], defaultdict(float)
    for metric in body.get("value", []):
        name = _path(metric, "name", "value", default="")
        series = metric.get("timeseries") or []
        points = series[0].get("data", []) if series else []
        for p in points:
            if name == "Percentage CPU":
                if p.get("average") is not None:
                    cpu_avg.append(float(p["average"]))
                if p.get("maximum") is not None:
                    cpu_max.append(float(p["maximum"]))
            elif name in ("Network In Total", "Network Out Total") and p.get("total") is not None:
                net[p.get("timeStamp")] += float(p["total"]) / 1_000_000
    return {"cpu_avg": cpu_avg, "cpu_max": cpu_max, "net_mb": list(net.values())}


def judge_running_vm(vm: dict, metrics: dict, prices: PriceBook) -> dict | None:
    size = vm_size(vm)
    verdict = A.vm_verdict(metrics["cpu_avg"], metrics["cpu_max"], metrics["net_mb"], METRIC_DAYS * 24)
    stats = verdict["stats"]
    rid = vm.get("id")
    s = _base(vm, "vm")
    if verdict["verdict"] == "idle":
        hourly, source = prices.vm_hourly(vm.get("location", ""), size)
        if not hourly:
            return None
        s.update(
            kind="idle_vm", title=f"VM {s['resource_name']} runs but does almost nothing",
            summary=f"{size}: CPU stayed under {stats['cpu_p95']}% (95th percentile) and network under "
                    f"{stats['net_p95_mb']} MB/hour over {stats['hours']} hours.",
            monthly_impact=round(hourly * HOURS_PER_MONTH, 2), impact_basis=f"list price, {source}",
            confidence=verdict["confidence"],
            evidence={"rule": "p95 CPU < 5% and p95 network < 5 MB/h", "size": size, **stats,
                      "metrics_days": METRIC_DAYS},
            fix=[{"label": "Deallocate it", "cmd": f"az vm deallocate --ids {rid}"},
                 {"label": "Or shut it down every evening (19:00 IST = 13:30 UTC)",
                  "cmd": f"az vm auto-shutdown --ids {rid} --time 1330"}],
        )
        return s
    if verdict["verdict"] == "oversized":
        target = A.smaller_size(size)
        if not target:
            return None
        cur, src1 = prices.vm_hourly(vm.get("location", ""), size)
        new, src2 = prices.vm_hourly(vm.get("location", ""), target)
        if not cur or not new or new >= cur:
            return None
        s.update(
            kind="rightsize_vm", title=f"VM {s['resource_name']} is larger than it needs to be",
            summary=f"{size} peaks at {stats['cpu_peak']}% CPU with a 95th percentile of {stats['cpu_p95']}%. "
                    f"{target} is the next size down.",
            monthly_impact=round((cur - new) * HOURS_PER_MONTH, 2),
            impact_basis=f"price difference, {src1 if src1 == src2 else src1 + ' / ' + src2}",
            confidence=verdict["confidence"],
            evidence={"rule": "p95 CPU < 20% and peak < 80%", "size": size, "suggested_size": target,
                      "current_hourly": cur, "suggested_hourly": new, **stats, "metrics_days": METRIC_DAYS,
                      "note": "Memory use isn't measured here; check it before resizing."},
            fix=[{"label": f"Resize to {target} (restarts the VM)",
                  "cmd": f"az vm resize --ids {rid} --size {target}"}],
        )
        return s
    return None


# ==========================================================================
# 6. Azure Advisor
# ==========================================================================
ADVISOR_CONFIDENCE = {"high": 0.8, "medium": 0.7, "low": 0.6}


def fetch_advisor(t) -> list[dict]:
    return client_for(t).get_all(
        f"/subscriptions/{t.subscription_id}/providers/Microsoft.Advisor/recommendations",
        {"api-version": "2023-01-01", "$filter": "Category eq 'Cost'"})


def advisor_signals(recs: list[dict]) -> list[dict]:
    out = []
    for r in recs:
        p = r.get("properties", {})
        ext = p.get("extendedProperties") or {}
        rid = _path(p, "resourceMetadata", "resourceId") or ""
        annual = ext.get("annualSavingsAmount")
        try:
            monthly = float(annual) / 12 if annual not in (None, "") else float(ext.get("savingsAmount") or 0)
        except (TypeError, ValueError):
            monthly = 0.0
        problem = _path(p, "shortDescription", "problem", default="Azure Advisor cost recommendation")
        solution = _path(p, "shortDescription", "solution", default="")
        name = p.get("impactedValue") or rid.split("/")[-1] or "subscription"
        out.append({
            "kind": "advisor", "provider": PROVIDER, "resource_id": rid, "resource_name": name,
            "resource_type": ((p.get("impactedField") or "").split("/")[-1] or "resource").lower(),
            "resource_group": resource_group(rid), "region": ext.get("region", ""), "tags": {},
            "title": f"Advisor: {problem}",
            "summary": solution or problem,
            "monthly_impact": round(monthly, 2),
            "impact_basis": f"Azure Advisor estimate ({ext.get('savingsCurrency') or 'USD'})",
            "confidence": ADVISOR_CONFIDENCE.get((p.get("impact") or "").lower(), 0.6),
            "evidence": {"rule": "Azure Advisor", "advisor_impact": p.get("impact"),
                         "recommendation_type": p.get("recommendationTypeId"),
                         "last_updated": p.get("lastUpdated"),
                         "details": {k: v for k, v in ext.items() if len(str(v)) < 200}},
            "fingerprint_extra": p.get("recommendationTypeId") or r.get("name"),
            "fix": [],
        })
    return out


# ==========================================================================
# 7. Activity Log: who created it
# ==========================================================================
def fetch_creator(t, resource_id: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=89)
    flt = (f"eventTimestamp ge '{since.strftime('%Y-%m-%dT%H:%M:%SZ')}' and "
           f"eventTimestamp le '{now.strftime('%Y-%m-%dT%H:%M:%SZ')}' and resourceUri eq '{resource_id}'")
    events = client_for(t).get_all(
        f"/subscriptions/{t.subscription_id}/providers/Microsoft.Insights/eventtypes/management/values",
        {"api-version": "2015-04-01", "$filter": flt,
         "$select": "caller,operationName,status,eventTimestamp,claims"}, limit_pages=5)
    return pick_creator(events)


def pick_creator(events: list[dict]) -> dict:
    """Earliest create/update ('.../write') event that Azure accepted.
    The caller is a user's sign-in name, or a GUID for apps and managed
    identities."""
    writes = []
    for e in events:
        op = e.get("operationName") or e.get("operation_name") or {}
        status = e.get("status") or {}
        op_value = (op.get("value") if isinstance(op, dict) else str(op)) or ""
        st = ((status.get("value") if isinstance(status, dict) else str(status)) or "").lower()
        if op_value.lower().endswith("/write") and st in ("succeeded", "started", "accepted"):
            ts = e.get("eventTimestamp") or e.get("event_timestamp")
            writes.append((str(ts), e.get("caller") or "", op_value, e.get("claims") or {}))
    if not writes:
        return {"principal": None, "event": None, "at": None, "source": "unknown", "principal_type": None}
    ts, caller, op_value, claims = sorted(writes, key=lambda w: w[0])[0]
    if GUID.match(caller or ""):
        app = claims.get("appid") or claims.get("azp") or ""
        principal = f"service identity {caller}" + (f" (app {app})" if app and app != caller else "")
        ptype = "service"
    else:
        principal, ptype = caller, "user"
    parts = op_value.split("/")
    return {"principal": principal, "event": "/".join(parts[-2:]) if len(parts) >= 2 else op_value,
            "at": ts, "source": "activity_log", "principal_type": ptype}


# ==========================================================================
# The scan
# ==========================================================================
def scan(t, prices: PriceBook, cost_start: date, today: date) -> dict:
    """Everything for one subscription. Each step records its own error so
    one failing API doesn't hide the rest."""
    out = {"costs": None, "resource_costs": None, "inventory": None, "signals": [],
           "errors": {}, "stats": {}}
    res_start = today - timedelta(days=45)

    try:
        out["costs"] = fetch_costs(t, cost_start, today)
    except Exception as e:  # noqa: BLE001
        out["errors"]["spend"] = _msg(e)
    try:
        out["resource_costs"] = fetch_resource_costs(t, res_start, today)
    except Exception as e:  # noqa: BLE001
        out["errors"]["resource_spend"] = _msg(e)
    try:
        out["inventory"] = fetch_inventory(t)
    except Exception as e:  # noqa: BLE001
        out["errors"]["inventory"] = _msg(e)
        return out

    inv = out["inventory"]
    by_type = defaultdict(list)
    for r in inv["detail"]:
        by_type[(r.get("type") or "").lower()].append(r)
    disks = by_type["microsoft.compute/disks"]
    disks_by_id = {(d.get("id") or "").lower(): d for d in disks}
    vms = by_type["microsoft.compute/virtualmachines"]

    signals = []
    signals += find_unattached_disks(disks, prices)
    signals += find_idle_public_ips(by_type["microsoft.network/publicipaddresses"], prices)
    signals += find_stale_snapshots(by_type["microsoft.compute/snapshots"], set(disks_by_id), prices)
    signals += find_stopped_vms(vms, disks_by_id, prices)

    running = [v for v in vms if vm_power_state(v) == "running"][:MAX_VMS_WITH_METRICS]
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    checked = 0
    for vm in running:
        try:
            s = judge_running_vm(vm, fetch_vm_metrics(t, vm["id"], now), prices)
            checked += 1
            if s:
                signals.append(s)
        except Exception as e:  # noqa: BLE001
            out["errors"].setdefault("metrics", _msg(e))

    try:
        adv = advisor_signals(fetch_advisor(t))
        merge_advisor(signals, adv)
        out["stats"]["advisor"] = len(adv)
    except Exception as e:  # noqa: BLE001
        out["errors"]["advisor"] = _msg(e)

    out["signals"] = signals
    out["stats"].update(resources=len(inv["resources"]), vms=len(vms), vms_checked=checked)
    return out


def merge_advisor(signals: list[dict], advisor: list[dict]):
    """If CloudPulse already flagged the same resource, Advisor's advice is
    attached as supporting evidence instead of becoming a second finding."""
    ours = {}
    for s in signals:
        if s.get("resource_id"):
            ours.setdefault(s["resource_id"].lower(), []).append(s)
    for a in advisor:
        rid = (a["resource_id"] or "").lower()
        if rid and rid in ours:
            for s in ours[rid]:
                s["evidence"]["advisor_agrees"] = a["summary"]
                s["confidence"] = round(min(0.98, s["confidence"] + 0.05), 2)
        else:
            signals.append(a)


def _msg(e: Exception) -> str:
    if isinstance(e, ArmError):
        return f"{e.status} {e.code}: {e.message[:200]}"
    return str(e).splitlines()[0][:240] if str(e) else e.__class__.__name__
