"""End-to-end: a fake Azure subscription goes through several syncs and a
person acts on the findings. Checks detection, owner assignment, reopening,
verification with real before/after numbers, permissions and the ledger."""
import json
import os
import tempfile
from datetime import date, datetime, timedelta, timezone

import pytest

DB = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{DB}", "ADMIN_EMAIL": "admin@test.local", "ADMIN_PASSWORD": "Admin-Pass-2026",
    "APP_SECRET_KEY": "test", "AZURE_SUBSCRIPTION_ID": "11111111-2222-3333-4444-555555555555",
    "AZURE_USE_CLI": "true", "WORKSPACE_NAME": "Test Azure", "DEMO_ENABLED": "false",
})
os.environ.pop("AWS_ACCESS_KEY_ID", None)
os.environ.pop("AWS_SECRET_ACCESS_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

from app.services import azure_collector, prices  # noqa: E402
from app.services.azure_rest import ArmClient  # noqa: E402

SUB = "/subscriptions/11111111-2222-3333-4444-555555555555"
RG = f"{SUB}/resourceGroups/demo/providers"
DISK = f"{RG}/Microsoft.Compute/disks/leftover-disk"
IP = f"{RG}/Microsoft.Network/publicIPAddresses/unused-ip"
VM_IDLE = f"{RG}/Microsoft.Compute/virtualMachines/idle-vm"
VM_BIG = f"{RG}/Microsoft.Compute/virtualMachines/big-vm"
OWNER = "owner@test.local"
TODAY = date.today()
H = {"x-cloudpulse": "1"}


class World:
    """What the fake Azure currently contains."""
    def __init__(self):
        self.disk_exists = True
        self.ip_exists = True
        self.disk_cost_until = TODAY  # disk bills every day up to this date


world = World()


def _cost_rows(grouping):
    rows = []
    for k in range(40, -1, -1):
        d = TODAY - timedelta(days=k)
        day = int(d.strftime("%Y%m%d"))
        spike = 60.0 if k == 3 else 0.0
        if grouping == ["ServiceName"]:
            rows.append([20.0 + spike, day, "Virtual Machines", "USD"])
            rows.append([5.0, day, "Storage", "USD"])
        else:
            rows.append([20.0 + spike, day, VM_BIG.lower(), "Virtual Machines", "USD"])
            if d <= world.disk_cost_until:
                rows.append([0.06, day, DISK.lower(), "Storage", "USD"])
            rows.append([4.94, day, f"{RG}/Microsoft.Storage/storageAccounts/untaggedstore".lower(), "Storage", "USD"])
    return rows


def _graph(query):
    if query.startswith("ResourceContainers"):
        return [{"name": "demo", "tags": {}}]
    if "type in~" in query:
        out = [
            {"id": VM_IDLE, "name": "idle-vm", "type": "microsoft.compute/virtualmachines", "location": "centralindia",
             "resourceGroup": "demo", "tags": {}, "properties": {"hardwareProfile": {"vmSize": "Standard_B2s"},
             "extended": {"instanceView": {"powerState": {"code": "PowerState/running"}}}}},
            {"id": VM_BIG, "name": "big-vm", "type": "microsoft.compute/virtualmachines", "location": "centralindia",
             "resourceGroup": "demo", "tags": {"team": "shop"}, "properties": {"hardwareProfile": {"vmSize": "Standard_D4s_v3"},
             "extended": {"instanceView": {"powerState": {"code": "PowerState/running"}}}}},
        ]
        if world.disk_exists:
            out.append({"id": DISK, "name": "leftover-disk", "type": "microsoft.compute/disks", "location": "centralindia",
                        "resourceGroup": "demo", "tags": {}, "sku": {"name": "Standard_LRS"},
                        "properties": {"diskState": "Unattached", "diskSizeGB": 4}})
        if world.ip_exists:
            out.append({"id": IP, "name": "unused-ip", "type": "microsoft.network/publicipaddresses",
                        "location": "centralindia", "resourceGroup": "demo", "tags": {},
                        "properties": {"publicIPAllocationMethod": "Static", "ipAddress": "4.2.1.9"}})
        return out
    return [{"id": VM_BIG, "name": "big-vm", "type": "microsoft.compute/virtualmachines", "tags": {"team": "shop"}},
            {"id": f"{RG}/Microsoft.Storage/storageAccounts/untaggedstore", "name": "untaggedstore",
             "type": "microsoft.storage/storageaccounts", "tags": {}}]


def _metrics(vm):
    hours = 14 * 24
    cpu = 1.0 if vm == VM_IDLE else 12.0
    peak = 3.0 if vm == VM_IDLE else 40.0
    net = 100_000 if vm == VM_IDLE else 50_000_000
    ts = [f"t{i}" for i in range(hours)]
    return {"value": [
        {"name": {"value": "Percentage CPU"}, "timeseries": [{"data": [{"timeStamp": t, "average": cpu, "maximum": peak} for t in ts]}]},
        {"name": {"value": "Network In Total"}, "timeseries": [{"data": [{"timeStamp": t, "total": net} for t in ts]}]},
        {"name": {"value": "Network Out Total"}, "timeseries": [{"data": [{"timeStamp": t, "total": 0} for t in ts]}]},
    ]}


def fake_opener(method, url, headers, data, timeout):
    body = json.loads(data) if data else None
    if "/providers/Microsoft.CostManagement/query" in url:
        grouping = [g["name"] for g in body["dataset"]["grouping"]]
        cols = [{"name": "Cost"}, {"name": "UsageDate"}] + [{"name": g} for g in grouping] + [{"name": "Currency"}]
        return 200, {}, json.dumps({"properties": {"columns": cols, "rows": _cost_rows(grouping)}}).encode()
    if "Microsoft.ResourceGraph" in url:
        return 200, {}, json.dumps({"data": _graph(body["query"])}).encode()
    if "/providers/Microsoft.Insights/metrics" in url:
        vm = url.split("https://management.azure.com")[1].split("/providers/Microsoft.Insights")[0]
        return 200, {}, json.dumps(_metrics(vm)).encode()
    if "Microsoft.Advisor/recommendations" in url:
        return 200, {}, json.dumps({"value": [
            {"id": "rec1", "name": "rec1", "properties": {
                "impact": "High", "impactedField": "Microsoft.Compute/virtualMachines", "impactedValue": "idle-vm",
                "resourceMetadata": {"resourceId": VM_IDLE},
                "shortDescription": {"problem": "Right-size or shutdown underutilized virtual machines",
                                     "solution": "Shut down idle-vm"},
                "extendedProperties": {"annualSavingsAmount": "360", "savingsCurrency": "USD"}}},
        ]}).encode()
    if "eventtypes/management/values" in url:
        return 200, {}, json.dumps({"value": [
            {"caller": OWNER, "operationName": {"value": "Microsoft.Compute/disks/write"},
             "status": {"value": "Succeeded"}, "eventTimestamp": "2026-09-01T10:00:00Z"},
            {"caller": "someone.else@test.local", "operationName": {"value": "Microsoft.Compute/disks/write"},
             "status": {"value": "Succeeded"}, "eventTimestamp": "2026-09-05T10:00:00Z"},
        ]}).encode()
    if url.split("?")[0].endswith(SUB):
        return 200, {}, json.dumps({"displayName": "Test subscription"}).encode()
    return 404, {}, b'{"error":{"code":"NotFound","message":"no fake for this url"}}'


class FakeCred:
    def get_token(self, scope):
        class T:
            token = "x"
            expires_on = datetime.now(timezone.utc).timestamp() + 3600
        return T()


@pytest.fixture(scope="module")
def client():
    azure_collector.client_for = lambda t: ArmClient(FakeCred(), opener=fake_opener, sleep=lambda s: None)
    prices._fetch_items = lambda flt, pages=5: (_ for _ in ()).throw(OSError("offline in tests"))
    from app.main import app
    from app import jobs
    with TestClient(app) as c:
        jobs.scheduler.shutdown(wait=True)   # run syncs inline so the test is deterministic
        yield c


def login(c, email, pw):
    c.post("/api/auth/logout", headers=H)
    r = c.post("/api/auth/login", json={"email": email, "password": pw}, headers=H)
    assert r.status_code == 200, r.text


def findings_by_title(c, ws, status="all"):
    items = c.get(f"/api/findings?ws={ws}&status={status}").json()["items"]
    return {f["resource_name"] if f["kind"] not in ("anomaly", "budget_risk", "untagged_spend") else f["kind"]: f
            for f in items}


def test_full_loop(client):
    c = client
    from app.database import SessionLocal
    from app.models import Finding, User

    login(c, "admin@test.local", "Admin-Pass-2026")
    ws = c.get("/api/auth/me").json()["workspaces"][0]["slug"]
    ws_id = [w for w in c.get("/api/admin/overview").json()["workspaces"] if w["slug"] == ws][0]["id"]
    person = c.post("/api/admin/users", json={"email": OWNER, "workspace_id": ws_id, "role": "viewer"}, headers=H).json()
    c.post(f"/api/budget?ws={ws}", json={"amount": 500}, headers=H)   # triggers a sync
    run = c.post(f"/api/collect?ws={ws}", headers=H).json()
    assert run["status"] == "live", run

    f = findings_by_title(c, ws)
    # --- detection -----------------------------------------------------------
    assert f["leftover-disk"]["kind"] == "idle_resource"
    # 4 GB Standard_LRS bills as S4; built-in price $1.54, but actual cost wins: 0.06/day * 30.4 = 1.82
    assert f["leftover-disk"]["monthly_impact"] == pytest.approx(1.82)
    assert "actual billed cost" in f["leftover-disk"]["impact_basis"]
    assert f["unused-ip"]["monthly_impact"] == pytest.approx(3.65)            # $0.005 x 730
    assert f["idle-vm"]["kind"] == "idle_vm"
    assert f["idle-vm"]["monthly_impact"] == pytest.approx(30.37)             # $0.0416 x 730
    assert f["big-vm"]["kind"] == "rightsize_vm"
    assert f["big-vm"]["monthly_impact"] == pytest.approx(70.08)              # ($0.192 - $0.096) x 730
    assert "idle-vm" in f and all(x["kind"] != "advisor" for x in f.values())  # Advisor merged into our finding
    assert f["anomaly"]["title"].startswith("Spend on")                       # the day-3 spike
    assert f["budget_risk"]["status"] == "open"                               # forecast ~$750 > $500
    assert f["untagged_spend"]["kind"] == "untagged_spend"                    # untaggedstore has no tags

    # --- owner: earliest create event -> matched to the CloudPulse user -----------
    disk = f["leftover-disk"]
    assert disk["owner"] == OWNER
    assert disk["status"] == "assigned" and disk["assignee"]["email"] == OWNER

    # --- the owner (a viewer) can act on their own finding, not on others -------
    login(c, OWNER, person["temporary_password"])
    r = c.post(f"/api/findings/{disk['id']}/action?ws={ws}", json={"action": "resolve", "note": "deleted"}, headers=H)
    assert r.status_code == 200 and r.json()["status"] == "resolved"
    r = c.post(f"/api/findings/{f['big-vm']['id']}/action?ws={ws}", json={"action": "dismiss", "note": "no"}, headers=H)
    assert r.status_code == 400
    notes = c.get("/api/notifications").json()
    assert notes["unread"] >= 1

    # --- the admin claims the IP is fixed, but it's still there -------------------
    login(c, "admin@test.local", "Admin-Pass-2026")
    ip = f["unused-ip"]
    c.post(f"/api/findings/{ip['id']}/action?ws={ws}", json={"action": "resolve"}, headers=H)
    r = c.post(f"/api/findings/{ip['id']}/action?ws={ws}", json={"action": "dismiss"}, headers=H)
    assert r.status_code == 400  # a reason is required

    # Time passes: the disk is really gone and stopped billing 5 days ago.
    world.disk_exists = False
    world.disk_cost_until = TODAY - timedelta(days=5)
    with SessionLocal() as db:
        for row in db.query(Finding).filter(Finding.id.in_([disk["id"], ip["id"]])):
            row.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=5)
        db.commit()
    c.post(f"/api/collect?ws={ws}", headers=H)
    f2 = findings_by_title(c, ws)

    # IP still exists -> reopened (back to its owner, who the activity log also names)
    assert f2["unused-ip"]["status"] in ("open", "assigned")
    # Disk: verified with real before/after: 0.06/day before, 0 after -> 1.82/month
    d2 = c.get(f"/api/findings/{disk['id']}?ws={ws}").json()
    assert d2["status"] == "verified", d2["verification"]
    assert d2["verification"]["before_daily"] == pytest.approx(0.06)
    assert d2["verification"]["after_daily"] == 0
    assert d2["realized_monthly"] == pytest.approx(1.82)
    assert [e["kind"] for e in d2["events"]][:3] == ["created", "assigned", "status"]

    s = c.get(f"/api/savings?ws={ws}").json()
    assert s["ledger"]["verified_monthly"] == pytest.approx(1.82)
    assert s["verified"][0]["accuracy"] == pytest.approx(1.0)

    # Disk comes back -> reopened and the saving is withdrawn
    world.disk_exists = True
    c.post(f"/api/collect?ws={ws}", headers=H)
    d3 = c.get(f"/api/findings/{disk['id']}?ws={ws}").json()
    assert d3["status"] == "assigned" and d3["realized_monthly"] is None
    assert c.get(f"/api/savings?ws={ws}").json()["ledger"]["verified_monthly"] == 0

    # Audit trail recorded the actions
    actions = {a["action"] for a in c.get("/api/admin/audit").json()}
    assert {"finding_resolve", "sync_requested", "budget_set", "user_created", "sign_in"} <= actions

    with SessionLocal() as db:
        assert db.query(User).filter_by(email=OWNER).one().must_change_password is True
