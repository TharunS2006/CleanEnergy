"""AWS collector: spend (Cost Explorer), leakage (EC2), and tagless
attribution (CloudTrail). Read-only; see README for the IAM policy.

Every function takes an `AwsTarget` (see app/services/connections.py).
"""
from datetime import date, datetime, timedelta, timezone


PROVIDER = "aws"
EBS_PER_GB_MONTH = 0.08   # gp3, us-east-1
EIP_IDLE_MONTH = 3.60     # $0.005/hour

CREATE_EVENTS = {"volume": "CreateVolume", "elastic_ip": "AllocateAddress", "instance": "RunInstances"}


def check_connection(t) -> tuple[bool, str]:
    try:
        arn = t.client("sts").get_caller_identity().get("Arn", "unknown")
        return True, arn
    except Exception as e:  # noqa: BLE001
        return False, f"AWS sign-in failed: {str(e).splitlines()[0][:240]}"


def fetch_costs(t, days: int = 30) -> list[dict]:
    end = date.today()
    start = end - timedelta(days=days)
    ce = t.client("ce", region="us-east-1")
    out, token = [], None
    while True:
        kwargs = dict(
            TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        if token:
            kwargs["NextPageToken"] = token
        resp = ce.get_cost_and_usage(**kwargs)
        for day in resp.get("ResultsByTime", []):
            for g in day.get("Groups", []):
                metric = g["Metrics"]["UnblendedCost"]
                amount = float(metric["Amount"])
                if amount > 0:
                    out.append({
                        "provider": PROVIDER,
                        "service": g["Keys"][0],
                        "date": day["TimePeriod"]["Start"],
                        "amount": amount,
                        "currency": metric.get("Unit", "USD"),
                    })
        token = resp.get("NextPageToken")
        if not token:
            return out


def fetch_leaks(t) -> list[dict]:
    ec2 = t.client("ec2")
    region = ec2.meta.region_name
    out = []

    for page in ec2.get_paginator("describe_volumes").paginate(
        Filters=[{"Name": "status", "Values": ["available"]}]
    ):
        for v in page["Volumes"]:
            out.append({
                "provider": PROVIDER,
                "resource_id": v["VolumeId"],
                "display_name": _name_tag(v),
                "resource_type": "volume",
                "region": region,
                "reason": f"{v['Size']} GB {v.get('VolumeType', '')} volume, not attached to any instance",
                "estimated_monthly_waste_usd": round(v["Size"] * EBS_PER_GB_MONTH, 2),
            })

    for a in ec2.describe_addresses().get("Addresses", []):
        if "AssociationId" in a or "InstanceId" in a or "NetworkInterfaceId" in a:
            continue
        out.append({
            "provider": PROVIDER,
            "resource_id": a.get("AllocationId", a.get("PublicIp")),
            "display_name": _name_tag(a),
            "resource_type": "elastic_ip",
            "region": region,
            "reason": f"Elastic IP {a.get('PublicIp')} allocated but attached to nothing",
            "estimated_monthly_waste_usd": EIP_IDLE_MONTH,
        })

    for page in ec2.get_paginator("describe_instances").paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]
    ):
        for r in page["Reservations"]:
            for inst in r["Instances"]:
                vol_ids = [m["Ebs"]["VolumeId"] for m in inst.get("BlockDeviceMappings", []) if "Ebs" in m]
                gb = 0
                if vol_ids:
                    vols = ec2.describe_volumes(VolumeIds=vol_ids)["Volumes"]
                    gb = sum(v["Size"] for v in vols)
                out.append({
                    "provider": PROVIDER,
                    "resource_id": inst["InstanceId"],
                    "display_name": _name_tag(inst),
                    "resource_type": "instance",
                    "region": region,
                    "reason": f"{inst['InstanceType']} stopped; its {gb} GB of volumes still bill",
                    "estimated_monthly_waste_usd": round(gb * EBS_PER_GB_MONTH, 2),
                })
    return out


def attribute(t, resource_id: str, resource_type: str) -> dict:
    event_name = CREATE_EVENTS.get(resource_type)
    end = datetime.now(timezone.utc)
    resp = t.client("cloudtrail").lookup_events(
        LookupAttributes=[{"AttributeKey": "ResourceName", "AttributeValue": resource_id}],
        StartTime=end - timedelta(days=90),
        EndTime=end,
        MaxResults=50,
    )
    events = resp.get("Events", [])
    creates = [e for e in events if e.get("EventName") == event_name] or []
    if not creates:
        return {"principal": None, "event": None, "at": None, "source": "unknown"}
    ev = min(creates, key=lambda e: e["EventTime"])
    return {
        "principal": ev.get("Username") or "unknown principal",
        "event": ev["EventName"],
        "at": ev["EventTime"].isoformat(),
        "source": "cloudtrail",
    }


def _name_tag(obj: dict):
    for t in obj.get("Tags", []) or []:
        if t.get("Key") == "Name":
            return t.get("Value")
    return None
