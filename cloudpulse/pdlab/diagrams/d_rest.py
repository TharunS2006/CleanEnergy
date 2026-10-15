from dio import D

# ---- credential flow (sequence)
d = D(1000, 760)
cols = [("Operator", 110, "grey"), ("CloudPulse", 340, "green"), ("Microsoft Entra ID", 600, "orange"), ("Azure Resource Manager", 860, "blue")]
for n, x, k in cols:
    d.box(x - 85, 15, 170, 46, n, k, 15, True)
    d.add(f'<path d="M{x},61 L{x},735" stroke="#888" stroke-width="1.3" stroke-dasharray="6 5"/>')
d.arrow([(110, 110), (600, 110)], "1  az ad sp create-for-rbac (once)", lx=355, ly=100)
d.arrow([(600, 150), (110, 150)], "2  client ID, secret, tenant ID", dashed=True, lx=355, ly=140)
d.arrow([(110, 195), (860, 195)], "3  assign Reader + Cost Management Reader", lx=485, ly=185)
d.arrow([(110, 240), (340, 240)], "4  enter 4 values in Connect Azure", lx=225, ly=230, size=12)
d.box(250, 262, 180, 44, ["secret encrypted", "with Fernet, stored"], "red", 12)
d.arrow([(340, 350), (600, 350)], "5  token request (client credentials)", lx=470, ly=340, size=12)
d.box(520, 372, 160, 40, ["secret and tenant", "verified"], "yellow", 12)
d.arrow([(600, 440), (340, 440)], "6  access token (JWT, about 1 hour)", dashed=True, lx=470, ly=430, size=12)
d.arrow([(340, 500), (860, 500)], "7  GET/POST + Bearer token", lx=600, ly=490)
d.box(780, 520, 160, 44, ["token and role", "checked (RBAC)"], "red", 12)
d.arrow([(860, 600), (340, 600)], "8  JSON: costs, resources, logs", dashed=True, lx=600, ly=590)
d.box(240, 625, 200, 44, ["paging, retry on 429,", "store as findings"], "purple", 12)
d.arrow([(340, 705), (110, 705)], "9  Connected: subscription name", dashed=True, lx=225, ly=695, size=12)
d.save("f_cred")

# ---- sync pipeline (flowchart)
d = D(760, 980)
steps = [("Scheduler (6 h) or Sync button", "orange"), ("Sign in to Azure: obtain access token", "blue"),
         ("Read bill: Cost Management query (daily cost)", "blue"), ("Read inventory: Resource Graph (disks, IPs, snapshots, VMs)", "blue"),
         ("Read usage and advice: VM metrics, Azure Advisor", "blue"), ("Find owners: Activity Log, then tags; price with Retail Prices", "blue"),
         ("Detect waste: rules and VM verdict", "purple"), ("Score, de-duplicate, upsert findings", "purple"),
         ("Anomalies, budget forecast, untagged spend", "purple"), ("Verify fixes, notify, write audit log", "green")]
y = 15
for i, (t, k) in enumerate(steps):
    d.box(130, y, 500, 54, t, k, 15)
    if i < len(steps) - 1:
        d.arrow([(380, y + 54), (380, y + 86)])
    y += 86
d.text(380, y - 8, "Each step stores its own error, so one failing source does not stop the others.", 13, anchor="middle", italic=True, color="#555")
d.save("f_pipe")

# ---- lifecycle (state diagram)
d = D(1000, 560)
d.ellipse(60, 90, 40, 26, "start", "grey", 14)
d.box(130, 62, 130, 56, "open", "grey", 16, True)
d.box(330, 62, 130, 56, "assigned", "blue", 16, True)
d.box(530, 62, 140, 56, "in progress", "yellow", 16, True)
d.box(740, 62, 130, 56, "resolved", "orange", 16, True)
d.box(740, 260, 130, 56, "verified", "green", 16, True)
d.box(130, 420, 140, 56, "dismissed", "red", 16, True)
d.box(380, 420, 140, 56, "snoozed", "grey", 16, True)
d.arrow([(100, 90), (130, 90)])
d.arrow([(260, 90), (330, 90)], "assign", lx=295, ly=80)
d.arrow([(460, 90), (530, 90)], "start", lx=495, ly=80)
d.arrow([(670, 90), (740, 90)], "resolve", lx=705, ly=80)
d.arrow([(805, 118), (805, 260)], ["bill drops for", "3+ days"], lx=880, ly=185)
d.arrow([(740, 40), (740, 20), (395, 20), (395, 62)], "waste still detected: reopen", lx=570, ly=14, size=12)
d.arrow([(805, 316), (805, 340), (600, 340), (600, 118)], "resource returns:", lx=680, ly=332, size=12)
d.text(680, 358, "reopen, saving withdrawn", 12)
d.arrow([(195, 118), (195, 420)], "dismiss (reason)", lx=125, ly=300, size=12)
d.arrow([(420, 118), (440, 420)], "snooze 1-90 days", lx=330, ly=300, size=12)
d.arrow([(520, 448), (560, 448), (560, 130)], dashed=True, lx=560, ly=470, label=None)
d.text(500, 520, "Snooze expiry returns the finding to open. Roles: owner/admin all actions; assignee start and resolve.", 12.5, italic=True, color="#555")
d.save("f_life")

# ---- use case
d = D(1000, 620)
d.actor(70, 80, "Administrator"); d.actor(70, 300, "Workspace owner"); d.actor(70, 480, ["Viewer /", "demo visitor"])
d.add('<rect x="260" y="20" width="520" height="580" fill="none" stroke="#666" stroke-width="1.6"/>')
d.text(520, 46, "CloudPulse", 17, True)
uc = [("Create workspace, add people", 105, 90), ("Connect Azure subscription", 105, 170), ("Run or schedule a sync", 520, 250),
      ("Set monthly budget", 105, 330), ("Import FOCUS bill", 105, 410), ("View spend, anomalies, budgets", 520, 490), ("Assign, start, resolve findings", 520, 570)]
pos = [(520, 90, "Create workspace, add people"), (520, 160, "Connect Azure (read-only identity)"), (520, 230, "Run or schedule a sync"),
       (520, 300, "Set monthly budget / import FOCUS bill"), (520, 370, "Assign, start, resolve, dismiss findings"),
       (520, 440, "View findings, owners, savings, audit log"), (520, 510, "View spend, anomalies and budgets")]
for x, y, t in pos:
    d.ellipse(x, y, 190, 28, t, "yellow", 14)
for y in (90, 160):
    d.arrow([(120, 130), (330, y)])
for y in (230, 300, 370, 440):
    d.arrow([(120, 330), (330, y)])
for y in (440, 510):
    d.arrow([(120, 520), (330, y)])
d.ellipse(900, 370, 70, 40, ["Azure", "(read only)"], "blue", 14)
d.arrow([(710, 230), (840, 360)], "reads", lx=800, ly=290, size=12)
d.save("f_usecase")

# ---- data model
d = D(1000, 700)
def ent(x, y, w, name, fields, k="blue"):
    h = 34 + 20 * len(fields)
    d.box(x, y, w, h, name, k, 15, True, top=True)
    d.add(f'<path d="M{x},{y + 30} L{x + w},{y + 30}" stroke="#666" stroke-width="1.2"/>')
    d.text(x + 10, y + 50, fields, 12.5, anchor="start", lh=1.6)
ent(30, 30, 200, "users", ["id, email, name", "password_hash (scrypt)", "is_admin, is_demo"])
ent(300, 30, 200, "memberships", ["user_id, workspace_id", "role: owner / viewer"], "grey")
ent(570, 30, 200, "workspaces", ["id, slug, name", "kind: customer / demo"], "green")
ent(790, 30, 190, "connections", ["workspace_id, provider", "auth, config JSON", "secret (Fernet)"], "red")
ent(30, 250, 220, "findings", ["id, workspace_id, kind", "fingerprint (unique)", "monthly_impact, severity", "priority_score, status", "assignee_id, realized_monthly", "evidence, verification JSON"], "purple")
ent(330, 250, 210, "finding_events", ["finding_id, actor", "kind, message, at"], "yellow")
ent(330, 400, 210, "notifications", ["user_id, finding_id", "message, read"], "yellow")
ent(620, 250, 190, "cost_snapshots", ["workspace_id, provider", "service, date, amount"], "orange")
ent(620, 400, 190, "resource_costs", ["resource_id, date", "amount"], "orange")
ent(30, 500, 220, "resource_owners", ["resource_id, principal", "source, checked_at"], "blue")
ent(330, 540, 210, "audit_log", ["actor, action, detail, at"], "grey")
ent(620, 540, 190, "sessions / settings", ["token hash, expiry", "workspace budget"], "grey")
d.arrow([(230, 70), (300, 70)]); d.arrow([(500, 70), (570, 70)]); d.arrow([(770, 70), (790, 70)])
d.arrow([(670, 130), (200, 250)], "1 workspace : many findings", lx=420, ly=190, size=12)
d.arrow([(330, 300), (250, 300)]); d.arrow([(330, 430), (250, 400)])
d.arrow([(700, 130), (700, 250)]); d.arrow([(715, 350), (715, 400)])
d.text(500, 690, "Arrows show one-to-many relationships (workspace_id / user_id foreign keys).", 12.5, italic=True, color="#555")
d.save("f_er")

# ---- deployment
d = D(1000, 520)
d.box(30, 190, 160, 90, ["User's browser", "(HTTPS)"], "blue", 15)
d.arrow([(190, 235), (290, 235)], "HTTPS", lx=240, ly=222, size=12)
d.group(290, 60, 420, 400, "Hosting options (same container image)", "grey")
for i, (n, s) in enumerate([("Laptop", "uvicorn + SQLite file"), ("Docker Compose", "named volume for database"),
                           ("Render", "render.yaml, health check /api/health"), ("Azure App Service", "managed identity, no secret")]):
    d.box(310, 100 + i * 88, 380, 70, [n, s], ["green", "green", "yellow", "orange"][i], 15, True)
d.arrow([(710, 235), (790, 235)], "HTTPS, Bearer token", lx=750, ly=215, size=12)
d.group(790, 120, 190, 230, "Microsoft Azure", "blue", 14)
d.box(805, 160, 160, 60, ["Entra ID", "token"], "orange", 14)
d.box(805, 245, 160, 80, ["Resource Manager", "(read only)"], "blue", 14)
d.text(500, 500, "Azure scripts 01-06 create the test workload, planted waste, identity, deployment and domain.", 12.5, italic=True, color="#555")
d.save("f_deploy")
