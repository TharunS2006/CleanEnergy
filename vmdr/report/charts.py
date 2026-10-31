import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
R = json.load(open("../bench_results.json"))
C1, C2, C3, C4, C5 = "#2a4b8d", "#1f7a6d", "#b5651d", "#7a4b9a", "#a23b3b"
NAME = {"single": "Single VM", "restart": "Single + auto-restart", "ap-one-zone": "Active-passive\none zone", "ap-two-zones": "Active-passive\ntwo zones", "aa-two-zones": "Active-active\ntwo zones", "aa-dr": "Active-active\n+ DR region"}

# 1. downtime per year by design
ks = list(R["strategies"]); v = [R["strategies"][k]["downtime_min_per_year"] for k in ks]
fig, ax = plt.subplots(figsize=(8.0, 3.8), dpi=200)
bars = ax.bar(range(len(ks)), v, color=[C3, C3, C1, C1, C1, C2], width=0.62)
for i, (b, k) in enumerate(zip(bars, ks)):
    lo, hi = R["spread"][k]; ax.errorbar(i, v[i], yerr=[[v[i] - lo], [hi - v[i]]], color="#333", capsize=3, lw=1)
    ax.text(i, hi * 1.12, f"{v[i]:.0f}" if v[i] > 20 else f"{v[i]:.1f}", ha="center", fontsize=9.5)
ax.set_yscale("log"); ax.set_xticks(range(len(ks))); ax.set_xticklabels([NAME[k] for k in ks], fontsize=9); ax.set_ylabel("downtime (minutes per year, log scale)"); ax.grid(axis="y", alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_strategies.png"); plt.close(fig)

# 2. failover time
fo = R["failover_sweep"]; x = [r["failover_min"] for r in fo]
fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=200)
ax.plot(x, [r["host_only_markov_min_per_year"] for r in fo], "s--", color=C3, label="Markov model", ms=4)
ax.plot(x, [r["host_only_sim_min_per_year"] for r in fo], "o-", color=C1, label="simulation", ms=4)
ax.set_xlabel("failover time (minutes)"); ax.set_ylabel("downtime from host failures\n(minutes per year)"); ax.legend(frameon=False); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_failover.png"); plt.close(fig)

# 3. repair time
mt = R["mttr_sweep"]; x = [r["mttr"] for r in mt]
fig, ax = plt.subplots(figsize=(6.6, 3.7), dpi=200)
for k, c, mk in (("single", C3, "o"), ("restart", C4, "^"), ("ap-two-zones", C1, "s"), ("aa-two-zones", C2, "d")):
    ax.plot(x, [r[k] for r in mt], marker=mk, color=c, lw=1.8, ms=4.5, label=NAME[k].replace("\n", " "))
ax.set_yscale("log"); ax.set_xlabel("host repair time MTTR (hours)"); ax.set_ylabel("downtime (minutes per year, log scale)"); ax.legend(frameon=False, fontsize=9); ax.grid(alpha=.25, which="both")
fig.tight_layout(); fig.savefig("assets/chart_mttr.png"); plt.close(fig)

# 4. DR tiers
t = R["tiers"]; names = [x["name"].replace(" ", "\n", 1) if len(x["name"]) > 14 else x["name"] for x in t]
fig, axs = plt.subplots(1, 3, figsize=(9.2, 3.3), dpi=200)
for ax, key, lab, c in ((axs[0], "rto_min", "recovery time, RTO (min)", C1), (axs[1], "rpo_mean_min", "mean data lost, RPO (min)", C3), (axs[2], "cost_extra", "extra cost (VM equivalents)", C2)):
    ax.bar(range(4), [x[key] for x in t], color=c, width=0.6)
    for i, x_ in enumerate(t): ax.text(i, x_[key] * 1.05 + 0.01, f"{x_[key]:g}", ha="center", fontsize=9)
    ax.set_yscale("log" if key != "cost_extra" else "linear"); ax.set_xticks(range(4)); ax.set_xticklabels(names, fontsize=7.5); ax.set_title(lab, fontsize=10.5)
fig.tight_layout(); fig.savefig("assets/chart_tiers.png"); plt.close(fig)

# 5. backups
bk = R["backup"]; fig, ax = plt.subplots(figsize=(6.2, 3.5), dpi=200)
for p, c, mk in ((1.0, C1, "o"), (0.98, C2, "s"), (0.9, C3, "^")):
    pts = [b for b in bk if b["success"] == p]
    ax.plot([b["interval"] for b in pts], [b["mean"] for b in pts], marker=mk, color=c, lw=1.8, label=f"backup succeeds {int(100 * p)}% of the time")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks([60, 240, 1440]); ax.set_xticklabels(["1 h", "4 h", "24 h"]); ax.set_xlabel("backup interval"); ax.set_ylabel("average age of newest good backup (min)"); ax.legend(frameon=False, fontsize=9); ax.grid(alpha=.25, which="both")
fig.tight_layout(); fig.savefig("assets/chart_backup.png"); plt.close(fig)

# 6. cost against availability for the planner (web shop case)
rows = R["planner"]["web shop"]["options"]
import math
fig, ax = plt.subplots(figsize=(6.8, 3.8), dpi=200)
for r in rows:
    nines = -math.log10(1 - r["availability"]); ax.scatter(r["cost"], nines, s=60, color=C2 if r["meets"] else "#9aa5b1", zorder=3)
    lab = r["name"].replace("aa-dr + ", "DR: ").replace("aa-two-zones", "active-active").replace("ap-", "active-passive ").replace("-one-zone", " one zone").replace("-two-zones", " two zones")
    off = {"active-active": (6, 7), "active-passive two zones": (6, -11)}.get(lab, (6, -3))
    ax.annotate(lab, (r["cost"], nines), textcoords="offset points", xytext=off, fontsize=7.5)
ax.set_xlim(0.8, 5.1); ax.axhline(4, color=C3, ls="--", lw=1.2); ax.text(0.95, 4.05, "target: 4 nines", color=C3, fontsize=9)
ax.set_xlabel("cost (VM equivalents)"); ax.set_ylabel("availability (number of nines)"); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_cost.png"); plt.close(fig)
print("ok")
