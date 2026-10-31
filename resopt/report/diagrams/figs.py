from svglib import *

# ============ Figure 4.1: layers ============
W, H = 900, 600
s = Svg(W, H)
s.text(450, 34, "Layers of the Resource Optimization tool", 21, "700", INK, "middle")
def layer(y, h, title, color, light):
    s.rect(30, y, 840, h, light, color, 2, 12, dash="7 5")
    s.rect(46, y - 14, 10.4 * len(title) + 30, 28, color, color, 1, 6); s.text(60, y + 6, title, 15.5, "700", "#fff")
layer(66, 112, "PRESENTATION", USR_D, USR_L)
s.box(60, 90, 250, 74, "Command line", ["resopt.cli", "demo, cpu, memory, disk"], USR_D, "#fff", i_gear)
s.box(340, 90, 250, 74, "Browser page", ["web/index.html", "three tabs with charts"], USR_D, "#fff", i_doc)
s.box(620, 90, 220, 74, "HTTP server", ["resopt.server", "JSON endpoints /api/*"], USR_D, "#fff", i_server)
layer(214, 118, "OPTIMIZER", APP_D, APP_L)
s.box(60, 240, 250, 78, "recommend_*()", ["rank every algorithm, pick the", "best, explain the choice"], APP_D, "#fff", i_chart)
s.box(340, 240, 250, 78, "Parameter tuning", ["tune_quantum, tune_frames:", "sweep one value, find the best"], APP_D, "#fff", i_gear)
s.box(620, 240, 220, 78, "optimise()", ["all three resources,", "gain against the baseline"], APP_D, "#fff", i_shield)
layer(366, 118, "SIMULATORS", AZ_D, AZ_L)
s.box(60, 392, 250, 76, "cpu.py", ["FCFS, SJF, SRTF, PRIORITY,", "PRIORITY-P, RR"], AZ_D, "#fff", i_clock)
s.box(340, 392, 250, 76, "memory.py", ["FIFO, LRU, OPT, CLOCK"], AZ_D, "#fff", i_db)
s.box(620, 392, 220, 76, "disk.py", ["FCFS, SSTF, SCAN,", "C-SCAN, LOOK, C-LOOK"], AZ_D, "#fff", i_server)
layer(520, 62, "WORKLOADS", DATA_D, DATA_L)
s.rect(60, 536, 780, 34, "#fff", DATA_D, 1.8, 8)
s.text(450, 559, "workloads.py: seeded generators for processes, page references and disk requests  ·  textbook examples", 14.5, "400", INK, "middle")
for x in (185, 465, 730):
    s.line([(x, 164), (x, 240)], INK, 2); s.line([(x, 318), (x, 392)], INK, 2)
s.line([(450, 484), (450, 520)], DATA_D, 2.2, marker="arr", start=True)
open("fig41.svg", "w").write(s.render())

# ============ Figure 4.2: one request ============
W2, H2 = 900, 560
p = Svg(W2, H2)
p.text(450, 32, "From a workload to a recommendation", 21, "700", INK, "middle")
p.rect(30, 62, 150, 90, "#fff", DATA_D, 1.8, 8); p.text(105, 96, "Workload", 17, "700", INK, "middle"); p.lines(105, 118, ["processes, page", "references or", "disk requests"], 12.5, 15.5, fill=MUTE, anchor="middle")
lanes = [(70, "CPU", AZ_D, AZ_L, "FCFS · SJF · SRTF · PRIORITY · PRIORITY-P · RR", "waiting, turnaround, response, switches"),
         (210, "MEMORY", APP_D, APP_L, "FIFO · LRU · OPT · CLOCK", "page faults, hits, fault rate"),
         (350, "I/O", USR_D, USR_L, "FCFS · SSTF · SCAN · C-SCAN · LOOK · C-LOOK", "total head movement")]
for i, (y, name, c, l, algs, met) in enumerate(lanes):
    p.rect(250, y, 380, 100, l, c, 2, 10); p.text(266, y + 26, f"{name}: run every algorithm", 15.5, "700", c)
    p.text(266, y + 52, algs, 13, "400", INK); p.text(266, y + 78, "measures: " + met, 12.5, "400", MUTE)
    p.line([(180, 107), (215, 107), (215, y + 50), (250, y + 50)] if i == 0 else [(215, y + 50), (250, y + 50)], INK, 2, marker="arr")
p.line([(215, 107), (215, 400)], INK, 2, marker=None)
p.rect(690, 150, 180, 220, DATA_L, DATA_D, 2, 10)
p.text(780, 182, "Optimizer", 18, "700", INK, "middle")
p.lines(780, 210, ["1. rank by the metric", "2. pick the best", "3. compare with", "    the baseline", "4. explain the choice"], 13, 21, fill=INK, anchor="middle")
for y in (120, 260, 400):
    p.line([(630, y), (660, y), (660, 260), (690, 260)] if y != 260 else [(630, 260), (690, 260)], INK, 2, marker="arr" if y == 260 else None)
p.rect(250, 484, 620, 60, APP_L, APP_D, 2, 10)
p.text(560, 510, "Recommendation: best algorithm per resource, with the percentage saved", 15.5, "700", APP_D, "middle")
p.text(560, 531, "against FCFS (CPU), FIFO (memory) and FCFS (disk), and the reason it wins", 13.5, "400", MUTE, "middle")
p.line([(780, 370), (780, 484)], APP_D, 2.4, marker="arrG")
open("fig42.svg", "w").write(p.render())
