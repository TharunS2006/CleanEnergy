"""Generates a small Azure bill in FOCUS format for importing into CloudPulse (Data sources -> Choose file)."""
import csv, json, random, gzip
from datetime import date, timedelta
random.seed(7)
END = date(2024, 9, 30)   # the demo workspace treats "today" as 1 Oct 2024
DAYS = 100
START = END - timedelta(days=DAYS - 1)
SERVICES = [  # name, category, daily base USD, weekend factor, share of cost that carries tags
    ("Virtual Machines", "Compute", 14.0, 0.92, 0.55),
    ("Storage", "Storage", 4.2, 1.0, 0.7),
    ("Azure SQL Database", "Databases", 7.5, 1.0, 0.8),
    ("Azure App Service", "Compute", 5.1, 0.85, 0.6),
    ("Bandwidth", "Networking", 2.4, 0.9, 0.2),
    ("Azure Kubernetes Service", "Compute", 9.0, 0.9, 0.5),
    ("Azure OpenAI", "AI and Machine Learning", 3.0, 0.8, 0.4),
]
TAGSETS = [{"owner": "arjun.k@example.edu", "env": "dev"}, {"owner": "priya.fin@example.com", "env": "prod"},
           {"owner": "meera.ops@example.com", "env": "test"}]
FIELDS = ["BillingAccountId", "BillingAccountName", "BillingCurrency", "BillingPeriodStart", "BillingPeriodEnd",
          "ChargeCategory", "ChargeDescription", "ChargePeriodStart", "ChargePeriodEnd", "BilledCost", "EffectiveCost",
          "ListCost", "ProviderName", "PublisherName", "InvoiceIssuerName", "RegionId", "RegionName", "ResourceId",
          "ResourceName", "ResourceType", "ServiceCategory", "ServiceName", "SubAccountId", "SubAccountName", "Tags"]
rows = []
for n in range(DAYS):
    d = START + timedelta(days=n)
    wk = d.weekday() >= 5
    for svc, cat, base, wf, tagged in SERVICES:
        cost = base * (wf if wk else 1) * (1 + 0.004 * n) * random.uniform(0.9, 1.1)
        if svc == "Virtual Machines" and d >= date(2024, 9, 22):        # a forgotten GPU VM starts billing
            cost += 38.0
        if svc == "Azure OpenAI" and d == date(2024, 9, 25):             # a test script loops on the API
            cost += 55.0
        if svc == "Azure OpenAI" and d == date(2024, 9, 26):
            cost += 48.0
        parts = 4
        for k in range(parts):
            tags = random.choice(TAGSETS) if random.random() < tagged else {}
            c = cost / parts
            rid = f"/subscriptions/0000-1111/resourceGroups/rg-{svc.split()[-1].lower()}-{k}/providers/{svc.replace(' ', '')}/res{k}"
            rows.append({
                "BillingAccountId": "0000-1111-2222", "BillingAccountName": "RMKCET Student Subscription",
                "BillingCurrency": "USD", "BillingPeriodStart": d.replace(day=1).isoformat() + "T00:00:00Z",
                "BillingPeriodEnd": (d.replace(day=28) + timedelta(days=4)).replace(day=1).isoformat() + "T00:00:00Z",
                "ChargeCategory": "Usage", "ChargeDescription": f"{svc} usage",
                "ChargePeriodStart": d.isoformat() + "T00:00:00Z", "ChargePeriodEnd": (d + timedelta(days=1)).isoformat() + "T00:00:00Z",
                "BilledCost": f"{c:.6f}", "EffectiveCost": f"{c:.6f}", "ListCost": f"{c:.6f}",
                "ProviderName": "Microsoft", "PublisherName": "Microsoft", "InvoiceIssuerName": "Microsoft",
                "RegionId": "southindia", "RegionName": "South India", "ResourceId": rid,
                "ResourceName": f"{svc.split()[-1].lower()}-{k}", "ResourceType": svc, "ServiceCategory": cat,
                "ServiceName": svc, "SubAccountId": "sub-0001", "SubAccountName": "cloudpulse-test",
                "Tags": json.dumps(tags) if tags else "{}"})
with open("focus_azure_sample.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
print(len(rows), "rows", START, "to", END)
