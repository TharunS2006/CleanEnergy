"""Imports billing data in FOCUS format (FinOps Open Cost & Usage Spec).

FOCUS is the vendor-neutral billing schema that AWS, Azure, GCP and Oracle
can all export. Supporting it means CloudPulse can read any provider's bill
from one importer.

The bundled file, data/focus_sample_100000.csv.gz, is the FinOps Foundation's
anonymised real-world sample (CC BY 4.0). It's used when no live account is
connected, so the charts show a real bill rather than random numbers.
"""
import csv
import gzip
import io
import json
from collections import defaultdict
from pathlib import Path

SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "focus_sample_100000.csv.gz"

PROVIDER_ALIASES = {
    "aws": "aws", "amazon web services": "aws",
    "microsoft": "azure", "azure": "azure", "microsoft azure": "azure",
    "google cloud": "gcp", "google": "gcp", "gcp": "gcp",
    "oracle": "oci", "oracle cloud infrastructure": "oci",
}


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _has_owner_tag(raw: str) -> bool:
    if not raw or raw in ("NULL", "{}"):
        return False
    try:
        tags = json.loads(raw)
    except ValueError:
        return False
    return bool(tags)


def aggregate(lines) -> list[dict]:
    """Collapse line items to one row per (provider, service, day).

    Keeps two figures per row: total billed cost, and the part of it that
    carried at least one tag, so the dashboard can show how much spend has
    no owner on record.
    """
    reader = csv.DictReader(lines)
    totals = defaultdict(float)
    tagged = defaultdict(float)
    currency = {}
    for row in reader:
        if (row.get("ChargeCategory") or "").lower() != "usage":
            continue  # skip credits, tax and adjustments: they distort a usage view
        cost = _num(row.get("BilledCost"))
        if cost <= 0:
            continue
        provider_name = row.get("ProviderName") or row.get("ServiceProviderName") or "unknown"
        provider = PROVIDER_ALIASES.get(provider_name.strip().lower(), provider_name.strip().lower())
        day = (row.get("ChargePeriodStart") or "")[:10]
        service = row.get("ServiceName") or "Other"
        key = (provider, service, day)
        totals[key] += cost
        if _has_owner_tag(row.get("Tags", "")):
            tagged[key] += cost
        currency[key] = row.get("BillingCurrency") or "USD"

    return [
        {
            "provider": p, "service": s, "date": d,
            "amount": round(amount, 6),
            "tagged_amount": round(tagged[(p, s, d)], 6),
            "currency": currency[(p, s, d)],
        }
        for (p, s, d), amount in totals.items()
    ]


def load_sample() -> list[dict]:
    if not SAMPLE_PATH.exists():
        return []
    with gzip.open(SAMPLE_PATH, "rt", encoding="utf-8-sig", newline="") as fh:
        return aggregate(fh)


def load_upload(content: bytes, filename: str) -> list[dict]:
    if filename.endswith(".gz"):
        content = gzip.decompress(content)
    text = io.StringIO(content.decode("utf-8-sig"))
    return aggregate(text)
