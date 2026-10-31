from svglib import *

# ============ Figure 4.1: layers ============
W, H = 900, 600
s = Svg(W, H)
s.text(450, 34, "Layers of the Data Centre Design Evaluator", 21, "700", INK, "middle")
def layer(y, h, title, color, light):
    s.rect(30, y, 840, h, light, color, 2, 12, dash="7 5")
    s.rect(46, y - 14, 10.4 * len(title) + 30, 28, color, color, 1, 6); s.text(60, y + 6, title, 15.5, "700", "#fff")
layer(66, 112, "PRESENTATION", USR_D, USR_L)
s.box(60, 90, 250, 74, "Command line", ["dcd.cli", "evaluate, harden, compare"], USR_D, "#fff", i_gear)
s.box(340, 90, 250, 74, "Browser page", ["web/index.html", "five tabs, editable firewall"], USR_D, "#fff", i_doc)
s.box(620, 90, 220, 74, "HTTP server", ["dcd.server", "/api/evaluate, /api/harden"], USR_D, "#fff", i_server)
layer(214, 118, "EVALUATOR", APP_D, APP_L)
s.box(60, 240, 250, 78, "evaluate()", ["capacity, security, resilience", "and the overall score"], APP_D, "#fff", i_chart)
s.box(340, 240, 250, 78, "Reference designs", ["basic, segmented, resilient", "built for any number of VMs"], APP_D, "#fff", i_db)
s.box(620, 240, 220, 78, "harden()", ["technical fixes applied", "automatically"], APP_D, "#fff", i_shield)
layer(366, 118, "ANALYSIS", AZ_D, AZ_L)
s.box(60, 392, 250, 76, "capacity.py", ["VM placement, N+1", "utilisation"], AZ_D, "#fff", i_server)
s.box(340, 392, 250, 76, "security.py", ["firewall findings, routes", "from the internet, hardening"], AZ_D, "#fff", i_lock)
s.box(620, 392, 220, 76, "resilience.py", ["failure scenarios,", "simulated availability"], AZ_D, "#fff", i_clock)
layer(520, 62, "MODEL", DATA_D, DATA_L)
s.rect(60, 536, 780, 34, "#fff", DATA_D, 1.8, 8)
s.text(450, 559, "model.py: Host, VM, Rule, Design  ·  zones, intended policy, hardening checklist, failure parameters", 14.5, "400", INK, "middle")
for x in (260, 465, 730):
    s.line([(x, 164), (x, 240)], INK, 2); s.line([(x, 318), (x, 392)], INK, 2)
s.line([(450, 484), (450, 520)], DATA_D, 2.2, marker="arr", start=True)
open("fig41.svg", "w").write(s.render())

# ============ Figure 4.2: the resilient reference design ============
W2, H2 = 900, 600
p = Svg(W2, H2)
p.text(450, 30, "The resilient reference design", 21, "700", INK, "middle")
p.rect(30, 56, 120, 60, EXT_L, EXT_D, 1.8, 10); p.text(90, 92, "Internet", 16, "700", INK, "middle")
p.rect(200, 56, 330, 60, SEC_L, SEC_D, 1.8, 10); p.text(365, 80, "Firewall pair FW1 + FW2", 15.5, "700", INK, "middle"); p.text(365, 100, "default deny, only the intended flows", 12.5, "400", MUTE, "middle")
p.line([(150, 86), (200, 86)], INK, 2.2)
p.rect(580, 56, 290, 60, SEC_L, SEC_D, 1.8, 10); p.text(725, 80, "Management zone (mgmt)", 15.5, "700", INK, "middle"); p.text(725, 100, "no route from the internet", 12.5, "400", MUTE, "middle")
p.zone(30, 150, 520, 150, "NETWORK ZONES (virtual)", USR_D, USR_L)
for x, name, port in ((60, "dmz: web VMs", "443"), (240, "app: app VMs", "8443"), (420, "db: databases", "5432")):
    p.rect(x, 190, 120, 80, "#fff", USR_D, 1.8, 8); p.text(x + 60, 222, name, 13.5, "700", INK, "middle"); p.text(x + 60, 244, "port " + port, 12.5, "400", MUTE, "middle")
p.line([(180, 230), (240, 230)], APP_D, 2.2, marker="arrG"); p.line([(360, 230), (420, 230)], APP_D, 2.2, marker="arrG")
p.line([(365, 116), (365, 174), (120, 174), (120, 190)], APP_D, 2.2, marker="arrG")
p.rect(580, 150, 290, 150, "#fff", LINE, 1.4, 10)
p.lines(596, 176, ["Intended flows only:", "internet → dmz : 443", "dmz → app : 8443", "app → db : 5432", "mgmt → dmz, app, db : 22"], 13.5, 20, fill=MUTE)
p.zone(30, 330, 840, 250, "PHYSICAL LAYER (every path doubled)", AZ_D, AZ_L)
for k, (x, rk) in enumerate(((60, "Rack R1"), (250, "Rack R2"))):
    p.rect(x, 366, 170, 150, "#fff", AZ_D, 1.8, 10); p.text(x + 85, 390, rk, 15, "700", AZ_D, "middle")
    for j in range(3 if k == 0 else 4):
        p.rect(x + 14 + (j % 2) * 78, 404 + (j // 2) * 38, 70, 30, USR_L, USR_D, 1.4, 6); p.text(x + 49 + (j % 2) * 78, 424 + (j // 2) * 38, "host", 12.5, "400", INK, "middle")
p.rect(470, 366, 380, 66, DATA_L, DATA_D, 1.8, 8); p.text(660, 392, "Power: feed A + feed B (each host has both)", 14.5, "700", INK, "middle"); p.text(660, 414, "Cooling: unit C1 + unit C2", 13.5, "400", MUTE, "middle")
p.rect(470, 442, 380, 66, DATA_L, DATA_D, 1.8, 8); p.text(660, 468, "Network: switch SW1 + SW2 per host", 14.5, "700", INK, "middle"); p.text(660, 490, "Storage: arrays SAN1 + SAN2, mirrored", 13.5, "400", MUTE, "middle")
p.text(450, 548, "Seven hosts for 40 VMs: the loss of any one host, or of a whole rack, leaves every service running", 13.5, "400", MUTE, "middle")
open("fig42.svg", "w").write(p.render())

# ============ Figure 5.1: zones and allowed flows ============
W3, H3 = 900, 470
d = Svg(W3, H3)
d.text(450, 30, "Zone graph of the intended policy", 21, "700", INK, "middle")
def zone(x, y, name, color, light, w=150):
    d.rect(x, y, w, 60, light, color, 2.2, 28); d.text(x + w / 2, y + 36, name, 17, "700", INK, "middle")
zone(30, 190, "internet", EXT_D, EXT_L); zone(250, 190, "dmz", USR_D, USR_L, 120); zone(450, 190, "app", USR_D, USR_L, 120); zone(650, 190, "db", SEC_D, SEC_L, 120)
zone(450, 350, "mgmt", DATA_D, DATA_L, 120); zone(30, 350, "storage", SEC_D, SEC_L, 150)
d.line([(180, 220), (250, 220)], APP_D, 2.4, marker="arrG"); d.text(215, 210, "443", 13.5, "700", APP_D, "middle")
d.line([(370, 220), (450, 220)], APP_D, 2.4, marker="arrG"); d.text(410, 210, "8443", 13.5, "700", APP_D, "middle")
d.line([(570, 220), (650, 220)], APP_D, 2.4, marker="arrG"); d.text(610, 210, "5432", 13.5, "700", APP_D, "middle")
d.line([(470, 350), (330, 250)], DATA_D, 2, dash="6 4", marker="arr")
d.line([(510, 350), (510, 250)], DATA_D, 2, dash="6 4", marker="arr")
d.line([(550, 350), (690, 250)], DATA_D, 2, dash="6 4", marker="arr"); d.text(636, 304, "22", 13.5, "700", DATA_D); d.text(522, 304, "22", 13.5, "700", DATA_D); d.text(366, 300, "22", 13.5, "700", DATA_D, "end")
d.line([(105, 190), (105, 118), (710, 118), (710, 190)], SEC_D, 2.2, dash="3 4", marker="arrR"); d.text(400, 108, "blocked by default deny: internet → db (the attack path)", 13.5, "700", SEC_D, "middle")
d.line([(150, 250), (450, 372)], SEC_D, 2.2, dash="3 4", marker="arrR"); d.text(34, 322, "blocked: internet → mgmt", 13, "700", SEC_D)
d.text(105, 428, "no route from the internet", 12.5, "400", MUTE, "middle") if False else None
d.rect(30, 420, 840, 40, "#fff", LINE, 1.4, 8)
d.text(44, 445, "Green: allowed flow.  Brown dashed: administration.  Red dotted: a route that must not exist; the evaluator searches for such routes.", 13, "400", MUTE)
open("fig51.svg", "w").write(d.render())
