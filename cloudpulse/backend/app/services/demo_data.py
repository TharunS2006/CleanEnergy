"""The demo workspace: a realistic month (September 2024) that shows every
stage of the findings loop.

Spend comes from the FinOps Foundation's FOCUS sample bill. The resources
below are examples; their lifecycle (assigned, fixed, verified, dismissed,
snoozed) is scripted once, and then the *real* verification, anomaly,
forecast and scoring code runs on top of it.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

S = "/subscriptions/00000000-demo-0000-0000-000000000000/resourceGroups"
DEMO_CLOCK = datetime(2024, 10, 1, 9, 0)   # "now" inside the demo
DEMO_BUDGET = 2600.0

PEOPLE = [
    ("arjun.k@example.edu", "Arjun K", "owner"),
    ("meera.ops@example.com", "Meera (Ops)", "owner"),
    ("priya.fin@example.com", "Priya (Finance)", "viewer"),
]


def _vm(name, rg):
    return f"{S}/{rg}/providers/Microsoft.Compute/virtualMachines/{name}"


SIGNALS = [
    {"key": "gpu", "kind": "idle_resource", "provider": "azure", "resource_type": "vm", "region": "centralindia",
     "resource_id": _vm("gpu-trial-01", "ml-lab"), "resource_name": "gpu-trial-01", "resource_group": "ml-lab",
     "title": "VM gpu-trial-01 is stopped but still billed",
     "summary": "Standard_D2s_v3 was shut down from inside (stopped, not deallocated), so compute keeps billing.",
     "monthly_impact": 70.08, "impact_basis": "list price, built-in estimate", "confidence": 0.9,
     "evidence": {"rule": "power state = stopped", "size": "Standard_D2s_v3", "compute_monthly": 70.08},
     "fix": [{"label": "Stop billing for compute", "cmd": "az vm deallocate --ids " + _vm("gpu-trial-01", "ml-lab")}],
     "owner": "arjun.k@example.edu", "owner_source": "example"},
    {"key": "backup", "kind": "idle_resource", "provider": "aws", "resource_type": "volume", "region": "ap-south-1",
     "resource_id": "vol-0c3f19a2be7d45e10", "resource_name": "db-backup-old", "resource_group": "",
     "title": "EBS volume db-backup-old is attached to nothing",
     "summary": "200 GB gp3 volume with no instance attached.",
     "monthly_impact": 16.00, "impact_basis": "list price, built-in estimate", "confidence": 0.95,
     "evidence": {"rule": "status = available", "size_gb": 200},
     "fix": [{"label": "Delete the volume", "cmd": "aws ec2 delete-volume --volume-id vol-0c3f19a2be7d45e10"}],
     "owner": "meera.ops@example.com", "owner_source": "example"},
    {"key": "osdisk", "kind": "idle_resource", "provider": "azure", "resource_type": "disk", "region": "centralindia",
     "resource_id": f"{S}/web/providers/Microsoft.Compute/disks/web-01_OsDisk_old",
     "resource_name": "web-01_OsDisk_old", "resource_group": "web",
     "title": "Disk web-01_OsDisk_old is attached to nothing",
     "summary": "128 GB Premium LRS disk (billed as P10) with no VM attached.",
     "monthly_impact": 19.71, "impact_basis": "list price, built-in estimate", "confidence": 0.95,
     "evidence": {"rule": "diskState = Unattached", "size_gb": 128, "billing_tier": "P10 LRS"},
     "fix": [{"label": "Delete the disk", "cmd": f"az disk delete --ids {S}/web/providers/Microsoft.Compute/disks/web-01_OsDisk_old --yes"}],
     "owner": None, "owner_source": "unknown"},
    {"key": "loadtest", "kind": "idle_resource", "provider": "aws", "resource_type": "instance", "region": "ap-south-1",
     "resource_id": "i-07a1d2c9e4b3f6a58", "resource_name": "load-test-runner", "resource_group": "",
     "title": "EC2 instance load-test-runner is stopped; its volumes still bill",
     "summary": "m5.large stopped; its 100 GB of volumes keep billing.",
     "monthly_impact": 8.00, "impact_basis": "list price, built-in estimate", "confidence": 0.9,
     "evidence": {"rule": "state = stopped", "volumes_gb": 100},
     "fix": [{"label": "Terminate the instance", "cmd": "aws ec2 terminate-instances --instance-ids i-07a1d2c9e4b3f6a58"}],
     "owner": "meera.ops@example.com", "owner_source": "example"},
    {"key": "stagingip", "kind": "idle_resource", "provider": "azure", "resource_type": "public_ip", "region": "southindia",
     "resource_id": f"{S}/staging/providers/Microsoft.Network/publicIPAddresses/staging-lb-ip",
     "resource_name": "staging-lb-ip", "resource_group": "staging",
     "title": "Public IP staging-lb-ip points at nothing",
     "summary": "Static public IP 20.193.14.7 is reserved but not attached to any resource.",
     "monthly_impact": 3.65, "impact_basis": "list price, built-in estimate", "confidence": 0.95,
     "evidence": {"rule": "no ipConfiguration, static allocation", "address": "20.193.14.7"},
     "fix": [], "owner": "arjun.k@example.edu", "owner_source": "example"},
    {"key": "eip", "kind": "idle_resource", "provider": "aws", "resource_type": "elastic_ip", "region": "ap-south-1",
     "resource_id": "eipalloc-0b5e2f7c91d3a4e62", "resource_name": "eipalloc-0b5e2f7c91d3a4e62", "resource_group": "",
     "title": "Elastic IP 13.232.81.40 is attached to nothing",
     "summary": "Elastic IP 13.232.81.40 allocated but attached to nothing.",
     "monthly_impact": 3.60, "impact_basis": "list price, built-in estimate", "confidence": 0.95,
     "evidence": {"rule": "no association"}, "fix": [],
     "owner": "meera.ops@example.com", "owner_source": "example"},
    {"key": "snap", "kind": "idle_resource", "provider": "azure", "resource_type": "snapshot", "region": "centralindia",
     "resource_id": f"{S}/ml-lab/providers/Microsoft.Compute/snapshots/pre-upgrade-snap",
     "resource_name": "pre-upgrade-snap", "resource_group": "ml-lab",
     "title": "Snapshot pre-upgrade-snap is no longer needed",
     "summary": "64 GB snapshot kept although its source disk has been deleted.",
     "monthly_impact": 3.20, "impact_basis": "list price, built-in estimate", "confidence": 0.9,
     "evidence": {"rule": "source disk missing", "size_gb": 64}, "fix": [],
     "owner": "service identity 3f9c1a52-7d10-4b2e-9a61-0c2d6e8b4f11 (app ci-deploy)", "owner_source": "example"},
    {"key": "reporting", "kind": "idle_vm", "provider": "azure", "resource_type": "vm", "region": "centralindia",
     "resource_id": _vm("reporting-vm", "analytics"), "resource_name": "reporting-vm", "resource_group": "analytics",
     "title": "VM reporting-vm runs but does almost nothing",
     "summary": "Standard_D2s_v3: CPU stayed under 2.1% (95th percentile) and network under 0.8 MB/hour over 336 hours.",
     "monthly_impact": 70.08, "impact_basis": "list price, built-in estimate", "confidence": 0.85,
     "evidence": {"rule": "p95 CPU < 5% and p95 network < 5 MB/h", "size": "Standard_D2s_v3", "hours": 336,
                  "coverage": 1.0, "cpu_p95": 2.1, "cpu_mean": 1.3, "cpu_peak": 9.8, "net_p95_mb": 0.8, "metrics_days": 14},
     "fix": [{"label": "Deallocate it", "cmd": "az vm deallocate --ids " + _vm("reporting-vm", "analytics")}],
     "owner": "priya.fin@example.com", "owner_source": "example"},
    {"key": "api", "kind": "rightsize_vm", "provider": "azure", "resource_type": "vm", "region": "centralindia",
     "resource_id": _vm("api-prod-01", "shop"), "resource_name": "api-prod-01", "resource_group": "shop",
     "title": "VM api-prod-01 is larger than it needs to be",
     "summary": "Standard_D4s_v3 peaks at 41.0% CPU with a 95th percentile of 13.4%. Standard_D2s_v3 is the next size down.",
     "monthly_impact": 70.08, "impact_basis": "price difference, built-in estimate", "confidence": 0.7,
     "evidence": {"rule": "p95 CPU < 20% and peak < 80%", "size": "Standard_D4s_v3", "suggested_size": "Standard_D2s_v3",
                  "current_hourly": 0.192, "suggested_hourly": 0.096, "hours": 336, "coverage": 1.0, "cpu_p95": 13.4,
                  "cpu_mean": 7.9, "cpu_peak": 41.0, "net_p95_mb": 38.2, "metrics_days": 14,
                  "note": "Memory use isn't measured here; check it before resizing."},
     "fix": [{"label": "Resize to Standard_D2s_v3 (restarts the VM)",
              "cmd": "az vm resize --ids " + _vm("api-prod-01", "shop") + " --size Standard_D2s_v3"}],
     "owner": "arjun.k@example.edu", "owner_source": "example"},
    {"key": "advisor", "kind": "advisor", "provider": "azure", "resource_type": "subscription", "region": "",
     "resource_id": "/subscriptions/00000000-demo-0000-0000-000000000000", "resource_name": "Demo subscription",
     "resource_group": "", "fingerprint_extra": "reserved-instances",
     "title": "Advisor: Consider virtual machine reserved instances to save over pay-as-you-go",
     "summary": "Buy a 1-year reservation for 2 x Standard_D2s_v3 in Central India based on 30 days of steady usage.",
     "monthly_impact": 41.50, "impact_basis": "Azure Advisor estimate (USD)", "confidence": 0.7,
     "evidence": {"rule": "Azure Advisor", "advisor_impact": "Medium", "details": {"term": "P1Y", "qty": "2"}},
     "fix": [], "owner": None, "owner_source": "unknown"},
]

# Scripted history: (signal key, [(days after 1 Sept, actor, action, extra)])
SCRIPT = {
    "gpu": [(24, "arjun.k@example.edu", "start", {"note": "Checking whether the ML team still needs it"})],
    "backup": [(11, "meera.ops@example.com", "resolve", {"note": "Old backup copied to S3 Glacier, volume deleted"})],
    "osdisk": [(9, "arjun.k@example.edu", "assign", {"to": "priya.fin@example.com", "note": "Finance, is this still needed for the audit?"}),
               (17, "priya.fin@example.com", "resolve", {"note": "Audit closed; disk deleted"})],
    "loadtest": [],
    "stagingip": [(20, "arjun.k@example.edu", "dismiss", {"note": "Reserved for the October launch; keeping the address"})],
    "eip": [(26, "meera.ops@example.com", "snooze", {"days": 21, "note": "Waiting for the DNS cutover"})],
    "snap": [],
    "reporting": [],
    "api": [(27, "arjun.k@example.edu", "comment", {"note": "Load test booked for Friday before resizing"})],
    "advisor": [],
}
# Resolved dates above are chosen so the real before/after check has data.

# What the bill actually showed per month, where it differs from the list-price
# estimate (discounts, partial months, a smaller tier than expected).
ACTUAL_MONTHLY = {"osdisk": 18.24, "backup": 15.20}


def resource_cost_rows(resolved_on: dict[str, date]) -> list[dict]:
    """Daily cost for each demo resource through September 2024, stopping on
    the day it was fixed."""
    rows = []
    for s in SIGNALS:
        if s["kind"] == "advisor":
            continue
        per_day = ACTUAL_MONTHLY.get(s["key"], s["monthly_impact"]) / 30.4
        end = resolved_on.get(s["key"], date(2024, 9, 30))
        d = date(2024, 9, 1)
        while d <= end:
            rows.append({"provider": s["provider"], "resource_id": s["resource_id"].lower(),
                         "service": "demo", "date": d.isoformat(), "amount": round(per_day, 4)})
            d += timedelta(days=1)
    return rows
