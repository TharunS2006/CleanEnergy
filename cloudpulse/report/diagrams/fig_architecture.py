from svglib import *

W, H = 1500, 985
s = Svg(W, H)
T, S = 18, 15.5   # title / sub font sizes

# ------------------------------------------------------------------ zones
s.zone(20, 50, 190, 690, "CLIENT TIER", USR, USR_L)
s.zone(240, 50, 580, 690, "CLOUDPULSE SERVER  (Python · FastAPI)", APP, APP_L)
s.zone(20, 780, 800, 170, "DATA & CONFIGURATION TIER", DATA, DATA_L)
s.zone(960, 50, 520, 895, "MICROSOFT AZURE  (customer subscription)", AZ, AZ_L)

# ------------------------------------------------------------------ client tier
s.box(36, 90, 158, 112, "Web UI", ["SPA, no framework", "HTML·CSS·JS", "SVG charts"], USR, "#fff", i_chart, T, S)
users = [("Administrator", "all workspaces"), ("Customer owner", "sync · budgets"),
         ("Customer viewer", "read only"), ("Demo visitor", "sample data")]
for i, (a, b) in enumerate(users):
    y = 262 + i * 66
    s.rect(36, y, 158, 56, "#fff", USR, 1.6, 8)
    i_user(s, 58, y + 28, USR)
    s.text(76, y + 24, a, 14, "700")
    s.text(78, y + 43, b, 13.5, fill=MUTE)
s.line([(115, 262), (115, 204)], USR, 2, marker="arr")
s.text(128, 240, "HTTPS", 13.5, fill=MUTE)
s.badge(115, 232, 1, USR_D)
s.rect(36, 560, 158, 150, "#fff", EXT, 1.4, 8)
s.text(46, 585, "Legend", 15, "700")
s.line([(48, 608), (92, 608)], INK, 2.2)
s.text(104, 613, "request", 13, fill=MUTE)
s.line([(48, 634), (92, 634)], INK, 2.2, dash="7 4")
s.text(104, 639, "response/read", 13, fill=MUTE)
s.line([(48, 660), (92, 660)], EXT_D, 2.2, dash="3 5")
s.text(104, 665, "setup (once)", 13, fill=MUTE)
s.badge(60, 688, "n", INK, 11)
s.text(78, 693, "step (Table 4.1)", 13.5, fill=MUTE)

# ------------------------------------------------------------------ server
s.box(260, 90, 540, 100, "API & security layer", ["FastAPI routers: /api/auth · /api/admin · /api/*",
      "HttpOnly session cookie · CSRF header · login", "rate-limit · role checks (admin / owner / viewer)"], SEC, "#fff", i_shield, T, S)
s.box(260, 210, 262, 60, "APScheduler", "background sync every 6 h", APP, "#fff", i_clock, T, S)
s.box(538, 210, 262, 60, "Audit & notifications", "who did what, in-app inbox", APP, "#fff", i_doc, T, S)
s.box(260, 290, 540, 56, "Collection orchestrator", "sign in → read → detect → score → verify", APP_D, "#fff", i_gear, T, S)

s.box(260, 362, 262, 130, "AWS / FOCUS input", ["optional: boto3 Cost", "Explorer, EC2, CloudWatch", "FOCUS CSV bill import"], EXT, "#fff", i_cloud, T, S)
s.box(538, 362, 262, 130, "Azure collector", ["Custom ARM REST client", "retry on 429 / 5xx, paging", "Bearer-token calls"], AZ, "#fff", i_cloud, T, S)
s.box(260, 508, 262, 84, "Detectors & analytics", ["idle disk/IP/snapshot/VM", "z-score · Holt forecast"], APP, "#fff", i_chart, T, S)
s.box(538, 508, 262, 84, "Findings engine", ["priority P1–P4 · lifecycle", "7-day bill verification"], APP, "#fff", i_gear, T, S)
s.box(260, 608, 262, 66, "Owner resolver", "Activity Log → tag → user", APP, "#fff", i_user, T, S)
s.box(538, 608, 262, 66, "Price book", "Azure Retail Prices + cache", APP, "#fff", i_doc, T, S)
s.box(260, 686, 540, 40, "Data-access layer (SQLAlchemy ORM)", None, APP_D, "#fff", None, 16.5, S)

# ------------------------------------------------------------------ data tier
s.box(36, 818, 240, 112, "Credential store", ["connections table:", "client secret as Fernet", "token (AES-128 + HMAC)"], SEC, "#fff", i_lock, T, S)
s.box(292, 818, 260, 112, "SQL database", ["SQLite (dev) / PostgreSQL", "findings · resource_costs", "audit_log · sessions · users"], DATA, "#fff", i_db, T, S)
s.box(568, 818, 236, 120, "Server settings", ["AZURE_* sign-in values", "APP_SECRET_KEY", "or az CLI / managed", "identity (no secret)"], DATA, "#fff", i_key, T, S)

# ------------------------------------------------------------------ azure
s.box(1010, 90, 440, 150, "Microsoft Entra ID  (tenant)", ["App registration + service principal", "Tenant ID · Client ID · Client secret", "Token endpoint: login.microsoftonline.com", "OAuth 2.0 client-credentials grant"], AZ_D, "#fff", i_key, T, S)
s.box(1010, 270, 440, 100, "Azure RBAC  (least privilege)", ["Roles: Reader + Cost Management Reader", "Scope: /subscriptions/{id}  (read-only)"], SEC, "#fff", i_shield, T, S)
s.rect(1010, 410, 440, 330, "#fff", AZ, 1.8, 8)
s.rect(1010, 410, 7, 330, AZ, AZ, 1, 3)
i_cloud(s, 1032, 440, AZ)
s.text(1062, 436, "Azure Resource Manager (ARM)", T, "700")
s.text(1062, 458, "management.azure.com · scope .default", S, fill=MUTE)
chips = [("Cost Management", "daily actual cost by service / resource"),
         ("Resource Graph", "disks · public IPs · snapshots · VMs"),
         ("Azure Monitor", "VM CPU and network, 14 days"),
         ("Activity Log", "who created each resource (owner)"),
         ("Azure Advisor", "cost recommendations")]
for i, (a, b) in enumerate(chips):
    y = 480 + i * 51
    s.rect(1030, y, 400, 43, AZ_L, AZ, 1.2, 6)
    s.text(1044, y + 19, a, 15.5, "700", AZ_D)
    s.text(1044, y + 36, b, 13.5, fill=MUTE)
s.box(1010, 765, 440, 62, "Retail Prices API  (public)", "prices.azure.com · no credential needed", EXT, "#fff", i_doc, T, S)
s.box(1010, 850, 440, 62, "Operator: Cloud Shell / az CLI", "scripts 01–06 create the service principal + roles", EXT, "#fff", i_gear, T, S)

# ------------------------------------------------------------------ flows
# 1 browser -> API
s.line([(194, 150), (260, 140)], USR_D, 2.2)
# 2 write credentials (encrypted)
s.line([(260, 178), (222, 178), (222, 818)], SEC, 2.4, marker="arrR")
s.badge(222, 400, 2, SEC_D)
# read credentials (decrypt)
s.line([(248, 818), (248, 318), (260, 318)], SEC, 2.4, marker="arrR", dash="7 4")
s.badge(248, 540, 4, SEC_D)
# 3 scheduler -> orchestrator
s.line([(391, 270), (391, 290)], APP_D, 2.2, marker="arrG")
s.badge(417, 280, 3, APP_D)
# collectors fed by orchestrator
s.line([(391, 346), (391, 362)], APP_D, 2.2, marker="arrG")
s.line([(669, 346), (669, 362)], APP_D, 2.2, marker="arrG")
# collectors -> detectors / findings (data returns)
s.line([(391, 492), (391, 508)], APP_D, 2.2, marker="arrG")
s.line([(522, 550), (538, 550)], APP_D, 2.2, marker="arrG")
s.line([(600, 492), (600, 500), (460, 500), (460, 508)], APP_D, 2.2, marker="arrG")
# azure collector <-> entra / ARM
s.line([(800, 385), (905, 385), (905, 140), (1010, 140)], AZ, 2.4, marker="arrB")
s.badge(905, 262, 5, AZ_D)
s.line([(1010, 205), (940, 205), (940, 418), (800, 418)], AZ, 2.4, marker="arrB", dash="7 4")
s.badge(940, 310, 6, AZ_D)
s.line([(800, 452), (1010, 452)], AZ, 2.4, marker="arrB")
s.badge(850, 452, 7, AZ_D, 12)
s.line([(1010, 482), (800, 482)], AZ, 2.4, marker="arrB", dash="7 4")
s.badge(960, 482, 8, AZ_D, 12)
# RBAC check
s.line([(1230, 410), (1230, 370)], SEC, 2.2, marker="arrR")
s.text(1242, 396, "authorise", 14, fill=SEC_D, italic=True)
# price book -> retail prices
s.line([(800, 641), (925, 641), (925, 796), (1010, 796)], EXT_D, 2, marker="arr", dash="5 4")
# operator -> entra (one-time setup, dashed)
s.line([(1010, 881), (978, 881), (978, 210), (1010, 210)], EXT_D, 2.2, dash="3 5")
s.badge(978, 600, 0, EXT_D)
s.line([(978, 320), (1010, 320)], EXT_D, 2.2, dash="3 5")
# ORM <-> DB
s.line([(400, 726), (400, 818)], DATA_D, 2.2, marker="arr")
s.badge(430, 770, 9, DATA_D)
s.line([(470, 818), (470, 726)], DATA_D, 2.2, marker="arr")
s.badge(500, 770, 10, DATA_D, 14)

open("fig_architecture.svg", "w").write(s.render())
print("ok", W, H)
