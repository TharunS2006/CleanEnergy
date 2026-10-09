from svglib import *
W, H = 900, 600
s = Svg(W, H)
def st(x, y, name, sub, c, light, w=190, h=70):
    s.rect(x, y, w, h, light, c, 2, 12)
    s.text(x + w / 2, y + 30, name, 20, "700", c, "middle")
    s.text(x + w / 2, y + 54, sub, 14.5, fill=MUTE, anchor="middle")
st(20, 70, "open", "detected, no owner yet", EXT_D, EXT_L)
st(240, 70, "assigned", "owner chosen", USR_D, USR_L)
st(460, 70, "in progress", "being fixed", DATA_D, DATA_L)
st(680, 70, "resolved", "marked fixed", AZ_D, AZ_L)
st(680, 290, "verified", "bill dropped: saving counted", APP_D, APP_L)
st(20, 450, "dismissed", "reason required", SEC_D, SEC_L)
st(240, 450, "snoozed", "1 – 90 days", EXT_D, EXT_L)
def lab(x, y, t, c=INK, a="middle"):
    s.text(x, y, t, 15, "700", c, a)
for x1, x2, t in [(210, 240, "assign"), (430, 460, "start"), (650, 680, "resolve")]:
    s.line([(x1, 105), (x2, 105)], INK, 2.4)
lab(225, 60, "assign"); lab(445, 60, "start"); lab(665, 60, "resolve")
s.line([(775, 140), (775, 290)], APP_D, 2.6, marker="arrG")
s.text(763, 200, "7-day before / after", 14.5, "700", APP_D, "end")
s.text(763, 219, "bill comparison", 14.5, "700", APP_D, "end")
s.text(763, 238, "(≥ 3 days after the fix)", 13.5, fill=MUTE, anchor="end")
# reopen arc resolved -> assigned
s.line([(775, 70), (775, 28), (335, 28), (335, 70)], SEC, 2.2, dash="7 4", marker="arrR")
s.text(555, 20, "still detected after the fix  →  reopened", 14.5, "700", SEC_D, "middle")
# bus for dismiss/snooze
s.line([(115, 140), (115, 450)], SEC, 2.2, dash="7 4", marker="arrR")
s.line([(335, 140), (335, 450)], EXT_D, 2.2, dash="7 4", marker="arr")
s.line([(555, 140), (555, 190), (335, 190)], EXT_D, 2.2, dash="7 4", marker=None)
s.line([(115, 190), (115, 190)], SEC, 2, marker=None)
s.text(127, 330, "dismiss", 14.5, "700", SEC_D)
s.text(347, 330, "snooze", 14.5, "700", EXT_D)
s.text(130, 168, "from any active state", 13.5, fill=MUTE, italic=True)
# notes
s.rect(440, 420, 440, 164, "#fff", LINE, 1.4, 10)
s.text(456, 446, "Automatic transitions", 16, "700")
s.lines(456, 472, ["• snooze expires  →  back to open",
                   "• no longer detected  →  resolved automatically",
                   "• verified resource returns  →  reopened,",
                   "   its saving is withdrawn",
                   "• dismissed finding detected again  →  reopened"], 14.5, 22, fill=MUTE)
s.text(20, 556, "Owners and admins may take every action;", 13.5, fill=MUTE, italic=True)
s.text(20, 574, "the assignee may start and resolve.", 13.5, fill=MUTE, italic=True)
open("fig_lifecycle.svg", "w").write(s.render())

# ---------------- pipeline
W2, H2 = 900, 1010
p = Svg(W2, H2)
steps = [
 ("Trigger", "APScheduler (every 6 h) or the Sync button", "", USR_D, i_clock),
 ("1  Sign in to the cloud", "Entra ID token for the service principal, managed identity or az CLI", "login.microsoftonline.com", AZ_D, i_key),
 ("2  Read the bill", "daily actual cost by service and by resource, 90 days", "Microsoft.CostManagement/query", AZ_D, i_chart),
 ("3  Read the inventory", "disks, public IPs, snapshots, VMs with power state, tags", "Microsoft.ResourceGraph/resources", AZ_D, i_cloud),
 ("4  Read usage and advice", "14 days of VM CPU and network; Azure Advisor cost items", "Microsoft.Insights · Microsoft.Advisor", AZ_D, i_server),
 ("5  Attribute owners and prices", "creator from the Activity Log, then tags; list price fallback", "Insights/eventtypes · prices.azure.com", AZ_D, i_user),
 ("6  Detect", "idle / oversized VMs, unattached disks, idle IPs, orphan snapshots", "rules + analytics.vm_verdict()", APP_D, i_gear),
 ("7  Score and de-duplicate", "fingerprint, priority P1–P4, upsert; reopen or auto-resolve", "findings.upsert_signals()", APP_D, i_shield),
 ("8  Workspace detectors", "spend anomalies, budget forecast, untagged spend", "find_anomalies · month_forecast", APP_D, i_chart),
 ("9  Verify fixes and notify", "7-day before / after check; write ledger, audit and inbox", "findings.verify()", APP_D, i_db),
]
y = 20
for i, (a, b, c, col, ic) in enumerate(steps):
    h = 74
    p.rect(60, y, 560, h, "#fff", col, 2, 10)
    p.rect(60, y, 8, h, col, col, 1, 3)
    ic(p, 94, y + h / 2, col)
    p.text(122, y + 30, a, 18.5, "700")
    p.text(122, y + 54, b, 14.2, fill=MUTE)
    if c:
        p.text(650, y + 44, c, 13.5, fill=col, italic=True)
    if i < len(steps) - 1:
        p.line([(340, y + h), (340, y + h + 24)], INK, 2.4)
    y += h + 24
open("fig_pipeline.svg", "w").write(p.render())
print(y)
