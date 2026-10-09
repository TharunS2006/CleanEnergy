from svglib import *
W, H = 900, 1180
s = Svg(W, H)
cols = [("Operator", "Cloud Shell / az CLI", 90, EXT_D), ("CloudPulse", "server", 300, APP_D),
        ("Microsoft Entra ID", "token endpoint", 520, AZ_D), ("Azure Resource", "Manager + RBAC", 720, AZ_D),
        ]
for n1, n2, x, c in cols:
    s.rect(x - 75, 20, 150, 62, c, c, 1, 8)
    s.text(x, 47, n1, 16.5, "700", "#fff", "middle")
    s.text(x, 68, n2, 14, fill="#dbe7f3", anchor="middle")
    s.line([(x, 82), (x, 1135)], LINE, 1.6, dash="6 5", marker=None)
X = {n: x for n, _, x, _ in cols}
O, C, E, A = 90, 300, 520, 720

def phase(y, h, title, color, light):
    s.rect(10, y, W - 20, h, light, color, 1.3, 10, dash="6 4")
    s.rect(10, y, 4, h, color, color, 1, 2)
    s.text(26, y + 24, title, 16, "700", color)

def msg(x1, x2, y, t1, t2=None, n=None, color=INK, dash=None, mk="arr"):
    s.line([(x1, y), (x2, y)], color, 2.2, dash=dash, marker=mk)
    lx = min(x1, x2) + 30
    s.text(lx, y - 26 if t2 else y - 10, t1, 14.5, "700", color)
    if t2:
        s.text(lx, y - 9, t2, 13.5, fill=MUTE)
    if n is not None:
        s.badge(min(x1, x2) - (0 if False else -2) + (14 if x2 > x1 else 14), y + 0, n, color, 11)

def selfnote(x, y, lines, color=INK, w=190):
    h = 14 + 17 * len(lines)
    s.rect(x - w / 2, y, w, h, "#fff", color, 1.4, 6)
    for i, t in enumerate(lines):
        s.text(x, y + 20 + 17 * i, t, 13.5, fill=INK, anchor="middle")

# ---- phase A: one-time setup
phase(100, 330, "A.  One-time setup  (Azure Cloud Shell, scripts/azure/03-reader-identity.sh)", EXT_D, "#f4f5f6")
msg(O, E, 168, "az ad sp create-for-rbac", "creates app registration + service principal", 1, EXT_D, "3 5")
msg(E, O, 218, "appId + client secret + tenant", "secret shown once; 1-year expiry", 2, EXT_D, "3 5")
msg(O, A, 280, "az role assignment create", "Reader + Cost Management Reader @ /subscriptions/{id}", 3, EXT_D, "3 5")
msg(O, C, 350, "paste 4 values: Connect Azure", "subscription · tenant · client ID · secret", 4, SEC)
selfnote(C, 372, ["secret → Fernet token", "stored in connections"], SEC, 200)

# ---- phase B: runtime sign-in
phase(450, 215, "B.  Runtime sign-in  (every sync, ClientSecretCredential)", AZ_D, AZ_L)
msg(C, E, 520, "POST /{tenant}/oauth2/v2.0/token", "client_id · client_secret · scope management.azure.com/.default", 5, AZ_D)
selfnote(E, 538, ["Entra ID verifies secret", "and tenant, issues JWT"], AZ_D, 200)
msg(E, C, 624, "access token (JWT, ≈ 1 hour)", "cached in memory; refreshed by azure-identity", 6, AZ_D, "7 4")

# ---- phase C: reading
phase(685, 290, "C.  Reading the subscription  (read-only ARM calls)", APP_D, APP_L)
msg(C, A, 755, "GET / POST management.azure.com/…", "Authorization: Bearer <token> · api-version", 7, APP_D)
selfnote(A, 773, ["validate token, then check", "RBAC role at the scope"], SEC, 210)
msg(A, C, 863, "200 JSON  (or 403 / 404 / 429)", "403 = missing role · 429 = wait Retry-After, retry", 8, APP_D, "7 4")
selfnote(C, 885, ["page results (nextLink,", "$skipToken); store costs,", "signals → findings"], APP_D, 210)

# ---- phase D: result
phase(995, 130, "D.  Connection test  (shown when the admin saves the connection)", SEC_D, SEC_L)
s.text(26, 1048, "GET /subscriptions/{id}  →  “Connected: <subscription name>”, or an exact reason:", 14.5, fill=INK)
s.text(26, 1072, "no Reader role (403) · subscription not found (404) · sign-in failed (bad secret / tenant).", 14.5, fill=INK)
s.text(26, 1104, "The same check is available offline:  python -m app.manage check-azure", 14.5, "700", SEC_D, family="Liberation Mono, monospace")
open("fig_credflow.svg", "w").write(s.render())
