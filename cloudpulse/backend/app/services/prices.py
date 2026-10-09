"""List prices for the things CloudPulse flags.

Source: Azure's public Retail Prices API (no sign-in needed), cached for a
week. If the API can't be reached, a built-in table of approximate US list
prices is used instead, and the finding says so ("built-in estimate").
All prices are pay-as-you-go USD, before discounts or credits.
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import PriceCache

log = logging.getLogger("cloudpulse")
API = "https://prices.azure.com/api/retail/prices"
HOURS_PER_MONTH = 730
CACHE_DAYS = 7

# Built-in fallback (approximate US East pay-as-you-go, Linux).
VM_HOURLY = {
    "standard_b1ls": 0.0052, "standard_b1s": 0.0104, "standard_b1ms": 0.0207, "standard_b2s": 0.0416,
    "standard_b2ms": 0.0832, "standard_b4ms": 0.166, "standard_b8ms": 0.333,
    "standard_b2ats_v2": 0.0094, "standard_b2als_v2": 0.0376, "standard_b2as_v2": 0.0752,
    "standard_d2s_v3": 0.096, "standard_d4s_v3": 0.192, "standard_d8s_v3": 0.384, "standard_d16s_v3": 0.768,
    "standard_d2s_v5": 0.096, "standard_d4s_v5": 0.192, "standard_d8s_v5": 0.384,
    "standard_d2as_v5": 0.086, "standard_d4as_v5": 0.172, "standard_d8as_v5": 0.344,
    "standard_e2s_v3": 0.126, "standard_e4s_v3": 0.252, "standard_e2s_v5": 0.126, "standard_e4s_v5": 0.252,
    "standard_f2s_v2": 0.0846, "standard_f4s_v2": 0.169,
}
DISK_TIERS = {
    "S": [(32, "S4"), (64, "S6"), (128, "S10"), (256, "S15"), (512, "S20"), (1024, "S30"), (2048, "S40"),
          (4096, "S50"), (8192, "S60"), (16384, "S70"), (32767, "S80")],
    "E": [(4, "E1"), (8, "E2"), (16, "E3"), (32, "E4"), (64, "E6"), (128, "E10"), (256, "E15"), (512, "E20"),
          (1024, "E30"), (2048, "E40"), (4096, "E50"), (8192, "E60"), (16384, "E70"), (32767, "E80")],
    "P": [(4, "P1"), (8, "P2"), (16, "P3"), (32, "P4"), (64, "P6"), (128, "P10"), (256, "P15"), (512, "P20"),
          (1024, "P30"), (2048, "P40"), (4096, "P50"), (8192, "P60"), (16384, "P70"), (32767, "P80")],
}
DISK_MONTHLY = {
    "S4": 1.54, "S6": 3.01, "S10": 5.89, "S15": 11.33, "S20": 21.76, "S30": 40.96, "S40": 77.83, "S50": 143.36,
    "E1": 0.30, "E2": 0.60, "E3": 1.20, "E4": 2.40, "E6": 4.80, "E10": 9.60, "E15": 19.20, "E20": 38.40,
    "E30": 76.80, "E40": 153.60, "E50": 307.20,
    "P1": 0.77, "P2": 1.54, "P3": 3.08, "P4": 5.28, "P6": 10.21, "P10": 19.71, "P15": 38.02, "P20": 73.22,
    "P30": 135.17, "P40": 259.20, "P50": 495.43,
}
PUBLIC_IP_HOURLY = 0.005
SNAPSHOT_GB_MONTH = 0.05

PRODUCT_BY_FAMILY = {"S": "Standard HDD Managed Disks", "E": "Standard SSD Managed Disks", "P": "Premium SSD Managed Disks"}


def disk_tier(sku: str, size_gb: int) -> tuple[str, str, str]:
    """Managed disks bill by tier: the smallest tier at least as large as the
    disk. Returns (family letter, tier name, redundancy)."""
    s = (sku or "Standard_LRS").lower()
    family = "P" if s.startswith("premium") else "E" if s.startswith("standardssd") else "S"
    redundancy = "ZRS" if s.endswith("zrs") else "LRS"
    for limit, name in DISK_TIERS[family]:
        if size_gb <= limit:
            return family, name, redundancy
    return family, DISK_TIERS[family][-1][1], redundancy


class PriceBook:
    def __init__(self, db: Session | None, fetch=None, now=None):
        self.db = db
        self.fetch = fetch or _fetch_items
        self.now = now or (lambda: datetime.now(timezone.utc).replace(tzinfo=None))
        self.offline = False

    # ------------------------------------------------------------ cache
    def _cached(self, key: str):
        if self.db is None:
            return None
        row = self.db.get(PriceCache, key)
        if row and row.fetched_at > self.now() - timedelta(days=CACHE_DAYS):
            return json.loads(row.value)
        return None

    def _store(self, key: str, value):
        if self.db is None:
            return
        row = self.db.get(PriceCache, key) or PriceCache(key=key)
        row.value = json.dumps(value)
        row.fetched_at = self.now()
        self.db.merge(row)
        self.db.commit()

    def _lookup(self, key: str, flt: str, pick):
        hit = self._cached(key)
        if hit is not None:
            return hit.get("price"), hit.get("source")
        if self.offline:
            return None, None
        try:
            items = self.fetch(flt)
        except Exception as e:  # noqa: BLE001
            log.info("Retail Prices API unavailable (%s); using built-in prices", e)
            self.offline = True
            return None, None
        price = pick(items)
        if price is not None:
            self._store(key, {"price": price, "source": "Azure Retail Prices API"})
            return price, "Azure Retail Prices API"
        return None, None

    # ------------------------------------------------------------ public
    def vm_hourly(self, region: str, size: str) -> tuple[float | None, str]:
        flt = (f"serviceName eq 'Virtual Machines' and armRegionName eq '{region}' "
               f"and armSkuName eq '{size}' and priceType eq 'Consumption'")

        def pick(items):
            ok = [i for i in items if i.get("unitOfMeasure") == "1 Hour"
                  and "windows" not in (i.get("productName") or "").lower()
                  and not any(w in (i.get("skuName") or "") for w in ("Spot", "Low Priority"))]
            return min((i["retailPrice"] for i in ok), default=None)

        price, source = self._lookup(f"vm:{region}:{size}".lower(), flt, pick)
        if price is None:
            price = VM_HOURLY.get((size or "").lower())
            source = "built-in estimate" if price is not None else "unknown"
        return price, source

    def disk_monthly(self, region: str, sku: str, size_gb: int) -> tuple[float, str, str]:
        family, tier, red = disk_tier(sku, size_gb)
        flt = (f"serviceName eq 'Storage' and armRegionName eq '{region}' and productName eq "
               f"'{PRODUCT_BY_FAMILY[family]}' and skuName eq '{tier} {red}' and priceType eq 'Consumption'")

        def pick(items):
            ok = [i for i in items if i.get("unitOfMeasure") == "1/Month"
                  and "disk" in (i.get("meterName") or "").lower()
                  and "operation" not in (i.get("meterName") or "").lower()]
            return min((i["retailPrice"] for i in ok), default=None)

        price, source = self._lookup(f"disk:{region}:{tier}:{red}".lower(), flt, pick)
        if price is None:
            price = DISK_MONTHLY.get(tier)
            if price is None:
                per_gb = {"S": 0.045, "E": 0.075, "P": 0.135}[family]
                price = round(size_gb * per_gb, 2)
            source = "built-in estimate"
        return price, source, f"{tier} {red}"

    def public_ip_monthly(self, region: str) -> tuple[float, str]:
        flt = "serviceName eq 'Virtual Network' and productName eq 'IP Addresses' and priceType eq 'Consumption'"

        def pick(items):
            ok = [i for i in items if i.get("unitOfMeasure") == "1 Hour"
                  and "static" in (i.get("meterName") or "").lower()
                  and "standard" in ((i.get("skuName") or "") + (i.get("meterName") or "")).lower()
                  and "ipv6" not in (i.get("meterName") or "").lower()]
            return min((i["retailPrice"] for i in ok), default=None)

        price, source = self._lookup("ip:standard-static", flt, pick)
        if price is None:
            price, source = PUBLIC_IP_HOURLY, "built-in estimate"
        return round(price * HOURS_PER_MONTH, 2), source

    def snapshot_monthly(self, region: str, size_gb: int) -> tuple[float, str]:
        flt = (f"serviceName eq 'Storage' and armRegionName eq '{region}' and "
               f"productName eq 'Standard HDD Managed Disks' and priceType eq 'Consumption'")

        def pick(items):
            ok = [i for i in items if "snapshot" in (i.get("meterName") or "").lower()
                  and "GB" in (i.get("unitOfMeasure") or "") and "zrs" not in (i.get("meterName") or "").lower()]
            return min((i["retailPrice"] for i in ok), default=None)

        price, source = self._lookup(f"snapshot:{region}".lower(), flt, pick)
        if price is None:
            price, source = SNAPSHOT_GB_MONTH, "built-in estimate"
        return round(price * size_gb, 2), source


def _fetch_items(flt: str, pages: int = 5) -> list[dict]:
    url = API + "?" + urllib.parse.urlencode({"api-version": "2023-01-01-preview", "$filter": flt})
    items = []
    for _ in range(pages):
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = json.load(resp)
        items.extend(body.get("Items", []))
        url = body.get("NextPageLink")
        if not url:
            break
    return items
