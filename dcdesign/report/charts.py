import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
R = json.load(open("../bench_results.json"))
C = ["#7b93b4", "#27405e", "#1f7a6d", "#b5651d", "#a23b3b"]
D = R["designs"]; names = list(D); label = {"basic": "Basic", "segmented": "Segmented", "resilient": "Resilient", "basic+fixes": "Basic after\nautomatic fixes"}

# 1. scores
fig, ax = plt.subplots(figsize=(8.2, 3.8), dpi=200)
keys = [("capacity_score", "capacity", C[0]), ("security_score", "security", C[1]), ("resilience_score", "resilience", C[2]), ("overall", "overall", C[3])]
w = 0.2; x = np.arange(len(names))
for i, (k, lab, c) in enumerate(keys):
    ax.bar(x + (i - 1.5) * w, [D[n][k] for n in names], w, label=lab, color=c)
    for j, n in enumerate(names): ax.text(x[j] + (i - 1.5) * w, D[n][k] + 1.5, f"{D[n][k]:.0f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([label[n] for n in names]); ax.set_ylim(0, 112); ax.set_ylabel("score (0 to 100)"); ax.legend(frameon=False, ncol=4, loc="upper left", fontsize=9); ax.grid(axis="y", alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_scores.png"); plt.close(fig)

# 2. downtime
fig, ax = plt.subplots(figsize=(6.6, 3.5), dpi=200)
v = [D[n]["e2e_down_min"] for n in names]
ax.bar(x, v, color=[C[3], C[3], C[2], C[2]], width=0.6)
for j, a in enumerate(v): ax.text(j, a * 1.12, f"{a:.1f} min", ha="center", fontsize=9.5)
ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels([label[n] for n in names]); ax.set_ylabel("downtime per year (minutes, log scale)"); ax.grid(axis="y", alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_downtime.png"); plt.close(fig)

# 3. placement
P = R["placement"]; al = ["ff", "bf", "ffd"]; nm = {"ff": "first fit", "bf": "best fit", "ffd": "first fit\ndecreasing"}
fig, axs = plt.subplots(1, 2, figsize=(8.0, 3.2), dpi=200)
axs[0].bar(range(3), [P[a]["mean_hosts"] for a in al], color=C[1], width=0.55); axs[0].set_ylim(7, 8.4)
for i, a in enumerate(al): axs[0].text(i, P[a]["mean_hosts"] + 0.03, f"{P[a]['mean_hosts']:.2f}", ha="center", fontsize=9)
axs[0].set_xticks(range(3)); axs[0].set_xticklabels([nm[a] for a in al], fontsize=9); axs[0].set_title("mean hosts used (40 VMs)", fontsize=10.5)
axs[1].bar(range(3), [P[a]["at_lower_bound_pct"] for a in al], color=C[2], width=0.55)
for i, a in enumerate(al): axs[1].text(i, P[a]["at_lower_bound_pct"] + 1, f"{P[a]['at_lower_bound_pct']:.0f}%", ha="center", fontsize=9)
axs[1].set_xticks(range(3)); axs[1].set_xticklabels([nm[a] for a in al], fontsize=9); axs[1].set_ylim(0, 100); axs[1].set_title("runs at the theoretical minimum (%)", fontsize=10.5)
fig.tight_layout(); fig.savefig("assets/chart_placement.png"); plt.close(fig)

# 4. scale
S = R["scale"]; fig, ax = plt.subplots(figsize=(5.8, 3.3), dpi=200)
ax.plot([s["vms"] for s in S], [s["seconds"] for s in S], "o-", color=C[1], lw=2); ax.set_xlabel("number of VMs"); ax.set_ylabel("time to evaluate (seconds)"); ax.grid(alpha=.25)
for s in S: ax.annotate(f"{s['hosts']} hosts", (s["vms"], s["seconds"]), textcoords="offset points", xytext=(-6, 7), fontsize=8.5, ha="right")
fig.tight_layout(); fig.savefig("assets/chart_scale.png"); plt.close(fig)

# 5. before and after the automatic fixes
b, a = D["basic"], D["basic+fixes"]; ks = [("policy_score", "firewall policy"), ("hardening_score", "hardening\nchecklist"), ("resilience_score", "resilience"), ("overall", "overall")]
fig, ax = plt.subplots(figsize=(6.8, 3.4), dpi=200); x2 = np.arange(len(ks)); w = 0.34
ax.bar(x2 - w / 2, [b[k] for k, _ in ks], w, label="before", color=C[3]); ax.bar(x2 + w / 2, [a[k] for k, _ in ks], w, label="after", color=C[2])
for i, (k, _) in enumerate(ks):
    ax.text(i - w / 2, b[k] + 1.5, f"{b[k]:.0f}", ha="center", fontsize=9); ax.text(i + w / 2, a[k] + 1.5, f"{a[k]:.0f}", ha="center", fontsize=9)
ax.set_xticks(x2); ax.set_xticklabels([l for _, l in ks]); ax.set_ylim(0, 112); ax.set_ylabel("score (0 to 100)"); ax.legend(frameon=False, loc="upper left"); ax.grid(axis="y", alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_fix.png"); plt.close(fig)
print("ok")
