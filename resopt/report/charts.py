import json, sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
sys.path.insert(0, "..")
from resopt import cpu, disk
from resopt.cpu import Proc
plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
R = json.load(open("../bench_results.json"))
C1, C2, C3, C4 = "#1f5f5b", "#7a4b9a", "#b5651d", "#2b6cb0"

# 1. CPU: waiting and response per algorithm (500 mixed workloads)
d = R["cpu"]["mixed"]; algs = list(d); x = np.arange(len(algs)); w = 0.38
fig, ax = plt.subplots(figsize=(7.6, 3.7), dpi=200)
ax.bar(x - w / 2, [d[a]["avg_waiting"] for a in algs], w, label="average waiting time", color=C1)
ax.bar(x + w / 2, [d[a]["avg_response"] for a in algs], w, label="average response time", color=C3)
for i, a in enumerate(algs):
    ax.text(i - w / 2, d[a]["avg_waiting"] + 0.3, f'{d[a]["avg_waiting"]:.1f}', ha="center", fontsize=9)
    ax.text(i + w / 2, d[a]["avg_response"] + 0.3, f'{d[a]["avg_response"]:.1f}', ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(algs); ax.set_ylabel("time units"); ax.legend(frameon=False); ax.grid(axis="y", alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_cpu.png"); plt.close(fig)

# 2. Round-robin quantum sweep
q = R["quantum"]; xs = [r["quantum"] for r in q]
fig, axs = plt.subplots(1, 2, figsize=(8.4, 3.4), dpi=200)
axs[0].plot(xs, [r["avg_waiting"] for r in q], "o-", color=C1, ms=3.5, label="average waiting"); axs[0].plot(xs, [r["avg_response"] for r in q], "s-", color=C3, ms=3.5, label="average response")
axs[0].set_xlabel("time quantum"); axs[0].set_ylabel("time units"); axs[0].legend(frameon=False, fontsize=9); axs[0].grid(alpha=.25)
axs[1].plot(xs, [r["switches"] for r in q], "o-", color=C2, ms=3.5); axs[1].set_xlabel("time quantum"); axs[1].set_ylabel("context switches per workload"); axs[1].grid(alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_quantum.png"); plt.close(fig)

# 3. Page-fault rate against the number of frames
m = R["memory"]; fr = sorted(map(int, m)); fig, ax = plt.subplots(figsize=(6.6, 3.6), dpi=200)
for a, c, mk in (("FIFO", C3, "s"), ("CLOCK", C2, "^"), ("LRU", C1, "o"), ("OPT", "#444", "d")):
    ax.plot(fr, [100 * m[str(f)][a] for f in fr], marker=mk, ms=4, color=c, lw=1.8, label=a, ls="--" if a == "OPT" else "-")
ax.set_xlabel("number of frames"); ax.set_ylabel("page-fault rate (%)"); ax.legend(frameon=False); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_memory.png"); plt.close(fig)

# 4. Belady's anomaly on the textbook string
b = R["belady_book"]; fig, ax = plt.subplots(figsize=(6.2, 3.4), dpi=200)
for a, c, mk in (("FIFO", C3, "s"), ("LRU", C1, "o"), ("OPT", "#444", "d")):
    ax.plot(range(1, 8), b[a], marker=mk, color=c, lw=1.8, label=a, ls="--" if a == "OPT" else "-")
ax.annotate("3 frames: 9 faults\n4 frames: 10 faults", xy=(4, 10), xytext=(5, 11.2), arrowprops=dict(arrowstyle="->", color=C3), fontsize=9.5, color=C3)
ax.set_xlabel("number of frames"); ax.set_ylabel("page faults"); ax.set_ylim(4, 13); ax.legend(frameon=False, loc="lower left"); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_belady.png"); plt.close(fig)

# 5. Disk: average head movement per 20 requests
dk = R["disk"]; algs = list(dk["uniform"]); x = np.arange(len(algs))
fig, ax = plt.subplots(figsize=(7.4, 3.6), dpi=200)
ax.bar(x - w / 2, [dk["uniform"][a] for a in algs], w, label="requests spread evenly", color=C1); ax.bar(x + w / 2, [dk["clustered"][a] for a in algs], w, label="requests in busy regions", color=C4)
for i, a in enumerate(algs):
    ax.text(i - w / 2, dk["uniform"][a] + 15, f'{dk["uniform"][a]:.0f}', ha="center", fontsize=8.5); ax.text(i + w / 2, dk["clustered"][a] + 15, f'{dk["clustered"][a]:.0f}', ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(algs); ax.set_ylabel("head movement (cylinders)"); ax.legend(frameon=False); ax.grid(axis="y", alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_disk.png"); plt.close(fig)

# 6. Gantt charts of the textbook example
P = [Proc("P1", 0, 24), Proc("P2", 0, 3), Proc("P3", 0, 3)]
cols = {"P1": C1, "P2": C3, "P3": C2}
fig, axs = plt.subplots(3, 1, figsize=(7.4, 3.5), dpi=200, sharex=True)
for ax, (name, a, qq) in zip(axs, (("FCFS", "FCFS", 4), ("SJF", "SJF", 4), ("Round robin, quantum 4", "RR", 4))):
    r = cpu.simulate(a, P, qq)
    for pid, s, e in r["gantt"]:
        ax.barh(0, e - s, left=s, color=cols[pid], edgecolor="white", height=0.7); ax.text((s + e) / 2, 0, pid, ha="center", va="center", color="white", fontsize=9)
    ax.set_yticks([]); ax.set_ylabel(name, rotation=0, ha="right", va="center", fontsize=10); ax.spines["left"].set_visible(False)
    ax.set_xlim(0, 30); ax.text(30.4, 0, f'avg wait {r["metrics"]["avg_waiting"]:.2f}', va="center", fontsize=9)
axs[-1].set_xlabel("time"); fig.subplots_adjust(left=0.2, right=0.82, hspace=0.35, bottom=0.17, top=0.97)
fig.savefig("assets/chart_gantt.png"); plt.close(fig)

# 7. Head paths on the textbook queue
Q = [98, 183, 37, 122, 14, 124, 65, 67]
fig, axs = plt.subplots(1, 4, figsize=(9.2, 3.6), dpi=200, sharey=True)
for ax, a in zip(axs, ("FCFS", "SSTF", "SCAN", "C-LOOK")):
    r = disk.simulate(a, Q, 53, 200, 1); p = r["path"]
    ax.plot(p, range(len(p)), "o-", color=C1, ms=3.5, lw=1.4); ax.set_title(f'{a}: {r["total"]}', fontsize=10.5); ax.set_xlim(0, 199); ax.invert_yaxis(); ax.set_xlabel("cylinder"); ax.grid(alpha=.25)
axs[0].set_ylabel("order of service")
fig.tight_layout(); fig.savefig("assets/chart_diskpath.png"); plt.close(fig)
print("charts ok")
