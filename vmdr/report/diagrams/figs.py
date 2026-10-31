from svglib import *

# ============ Figure 4.1: layers ============
W, H = 900, 600
s = Svg(W, H)
s.text(450, 34, "Layers of the VM Availability and DR tool", 21, "700", INK, "middle")
def layer(y, h, title, color, light):
    s.rect(30, y, 840, h, light, color, 2, 12, dash="7 5")
    s.rect(46, y - 14, 10.4 * len(title) + 30, 28, color, color, 1, 6); s.text(60, y + 6, title, 15.5, "700", "#fff")
layer(66, 112, "PRESENTATION", USR_D, USR_L)
s.box(60, 90, 250, 74, "Command line", ["vmdr.cli", "avail, compare, plan, backup"], USR_D, "#fff", i_gear)
s.box(340, 90, 250, 74, "Browser page", ["web/index.html", "four tabs with tables"], USR_D, "#fff", i_doc)
s.box(620, 90, 220, 74, "HTTP server", ["vmdr.server", "JSON endpoints /api/*"], USR_D, "#fff", i_server)
layer(214, 118, "PLANNER", APP_D, APP_L)
s.box(60, 240, 250, 78, "plan()", ["cheapest design that meets", "availability, RTO and RPO"], APP_D, "#fff", i_shield)
s.box(340, 240, 250, 78, "DR tiers", ["backup-restore, pilot light,", "warm standby, multi-active"], APP_D, "#fff", i_db)
s.box(620, 240, 220, 78, "dr_events()", ["takeovers, recovery time,", "data lost per disaster"], APP_D, "#fff", i_chart)
layer(366, 118, "SIMULATION ENGINE", AZ_D, AZ_L)
s.box(60, 392, 250, 76, "make_world()", ["random failures of hosts,", "zones and regions"], AZ_D, "#fff", i_clock)
s.box(340, 392, 250, 76, "Strategies", ["single, restart, active-passive,", "active-active, + DR region"], AZ_D, "#fff", i_gear)
s.box(620, 392, 220, 76, "Failover machine", ["switching, waiting,", "DR takeover"], AZ_D, "#fff", i_server)
layer(520, 62, "MATHEMATICS", DATA_D, DATA_L)
s.rect(60, 536, 780, 34, "#fff", DATA_D, 1.8, 8)
s.text(450, 559, "avail.py: MTBF/MTTR, series, parallel, k-of-n, Markov model  ·  backup.py: data age, restore time", 14.5, "400", INK, "middle")
for x in (260, 465, 730):
    s.line([(x, 164), (x, 240)], INK, 2); s.line([(x, 318), (x, 392)], INK, 2)
s.line([(450, 484), (450, 520)], DATA_D, 2.2, marker="arr", start=True)
open("fig41.svg", "w").write(s.render())

# ============ Figure 4.2: the deployment the tool models ============
W2, H2 = 900, 560
p = Svg(W2, H2)
p.text(450, 30, "The deployment that is modelled", 21, "700", INK, "middle")
p.zone(30, 62, 560, 330, "PRIMARY REGION", AZ_D, AZ_L)
p.rect(60, 100, 230, 190, "#fff", USR_D, 1.8, 10); p.text(76, 124, "Availability zone 1", 15, "700", USR_D)
p.rect(80, 140, 190, 56, USR_L, USR_D, 1.6, 8); p.text(175, 164, "VM A (active)", 15, "700", INK, "middle"); p.text(175, 184, "on host A", 12.5, "400", MUTE, "middle")
p.rect(80, 210, 190, 56, "#fff", LINE, 1.4, 8); p.text(175, 234, "spare host", 14, "400", MUTE, "middle"); p.text(175, 254, "for auto-restart", 12.5, "400", MUTE, "middle")
p.rect(330, 100, 230, 190, "#fff", USR_D, 1.8, 10); p.text(346, 124, "Availability zone 2", 15, "700", USR_D)
p.rect(350, 140, 190, 56, USR_L, USR_D, 1.6, 8); p.text(445, 164, "VM B (active or standby)", 14.5, "700", INK, "middle"); p.text(445, 184, "on host B", 12.5, "400", MUTE, "middle")
p.rect(150, 316, 300, 52, DATA_L, DATA_D, 1.8, 8); p.text(300, 340, "Load balancer / failover manager", 15, "700", INK, "middle"); p.text(300, 358, "health checks, switches traffic", 12.5, "400", MUTE, "middle")
p.line([(175, 316), (175, 290)], INK, 2); p.line([(445, 316), (445, 290)], INK, 2)
p.line([(290, 168), (350, 168)], APP_D, 2, dash="6 4", marker="arrG", start=True); p.text(320, 160, "sync", 12, "700", APP_D, "middle")
p.zone(630, 62, 240, 330, "DR REGION", APP_D, APP_L)
p.rect(650, 110, 200, 70, "#fff", APP_D, 1.8, 8); p.text(750, 136, "Standby copy", 15, "700", INK, "middle"); p.text(750, 156, "cold, pilot light,", 12.5, "400", MUTE, "middle"); p.text(750, 171, "warm or active", 12.5, "400", MUTE, "middle")
p.rect(650, 210, 200, 70, "#fff", APP_D, 1.8, 8); p.text(750, 236, "Backup vault", 15, "700", INK, "middle"); p.text(750, 256, "copies of the disks", 12.5, "400", MUTE, "middle")
p.line([(590, 145), (650, 145)], APP_D, 2.4, dash="7 4", marker="arrG"); p.text(610, 136, "async", 12, "700", APP_D, "middle")
p.line([(590, 245), (650, 245)], DATA_D, 2.4, dash="7 4", marker="arr"); p.text(610, 266, "backup", 12, "700", DATA_D, "middle")
p.rect(30, 420, 840, 124, "#fff", LINE, 1.4, 10)
p.text(48, 448, "What can fail, and what each design survives", 16, "700", INK)
p.lines(48, 474, ["• a host (hours): auto-restart, a standby VM or a second active VM keeps the service going",
                  "• a whole zone (rare): needs the second VM in another zone",
                  "• a whole region (very rare): needs the DR region; its recovery time (RTO) and the data lost (RPO) depend on the tier"], 14, 22, fill=MUTE)
open("fig42.svg", "w").write(p.render())

# ============ Figure 5.1: the Markov chain of an active-passive pair ============
W3, H3 = 900, 480
d = Svg(W3, H3)
d.text(450, 30, "Active-passive pair as a four-state Markov chain", 20, "700", INK, "middle")
def st(x, y, label, sub, color, light, w=190, h=70):
    d.rect(x, y, w, h, light, color, 2.2, 32); d.text(x + w / 2, y + 30, label, 17, "700", INK, "middle"); d.text(x + w / 2, y + 52, sub, 13, "400", MUTE, "middle")
st(60, 90, "0  both up", "service up", APP_D, APP_L)
st(60, 300, "1  standby down", "service up", APP_D, APP_L)
st(560, 90, "2  switching", "service down", SEC_D, SEC_L)
st(560, 300, "3  both down", "service down", SEC_D, SEC_L)
d.line([(155, 160), (155, 300)], INK, 2.2); d.text(143, 235, "λ standby fails", 13.5, "700", INK, "end")
d.line([(185, 300), (185, 160)], INK, 2.2); d.text(197, 235, "μ repaired", 13.5, "700", INK)
d.line([(250, 118), (560, 118)], INK, 2.2); d.text(405, 108, "λ active fails", 13.5, "700", INK, "middle")
d.line([(560, 142), (250, 142)], INK, 2.2); d.text(405, 164, "μ original repaired: switch abandoned", 13.5, "700", INK, "middle")
d.line([(560, 150), (250, 318)], INK, 2.2); d.text(470, 244, "φ switch done", 13.5, "700", INK, "middle")
d.line([(250, 345), (560, 345)], INK, 2.2); d.text(405, 336, "λ active fails", 13.5, "700", INK, "middle")
d.line([(560, 365), (250, 365)], INK, 2.2); d.text(405, 388, "μ original repaired", 13.5, "700", INK, "middle")
d.line([(655, 160), (655, 300)], INK, 2.2); d.text(667, 235, "λ target fails", 13.5, "700", INK)
d.line([(700, 300), (700, 160)], INK, 2.2); d.text(712, 280, "μ standby back", 13.5, "700", INK)
d.rect(60, 410, 780, 56, "#fff", LINE, 1.4, 8)
d.text(76, 434, "λ = 1 / MTBF   μ = 1 / MTTR   φ = 1 / failover time.   Unavailability = probability of state 2 + probability of state 3.", 14, "400", MUTE)
d.text(76, 455, "The simulator is checked against this model (Table 6.2).", 14, "400", MUTE)
open("fig51.svg", "w").write(d.render())
