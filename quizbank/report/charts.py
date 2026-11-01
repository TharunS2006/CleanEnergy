import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
R = json.load(open("../report_results.json"))
C = ["#27405e", "#1f7a6d", "#b5651d", "#7a4b9a", "#a23b3b"]

# 1. calibration score by profile
c = R["calibration"]; names = ["calibrated", "overconfident", "underconfident", "random"]
fig, ax = plt.subplots(figsize=(6.6, 3.6), dpi=200)
m = [c[n]["calibration_mean"] for n in names]; sd = [c[n]["calibration_sd"] for n in names]
ax.bar(range(4), m, yerr=sd, capsize=4, color=[C[1], C[4], C[2], "#8a93a0"], width=0.58)
for i, v in enumerate(m): ax.text(i, v + sd[i] + 1.5, f"{v:.1f}", ha="center", fontsize=9.5)
ax.set_xticks(range(4)); ax.set_xticklabels(["calibrated\\n(sure only when right)".replace("\\n", "\n"), "always\ncertain", "always\nguessing", "random\nconfidence"], fontsize=9)
ax.set_ylim(0, 105); ax.set_ylabel("calibration score (mean, bar = 1 s.d.)"); ax.grid(axis="y", alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_calibration.png"); plt.close(fig)

# 2. Leitner
L = R["leitner"]; ps = list(L); fig, axs = plt.subplots(1, 2, figsize=(8.2, 3.3), dpi=200)
axs[0].bar(range(len(ps)), [L[p]["reviews_mean"] for p in ps], color=C[0], width=0.55); axs[0].set_title("mean number of reviews", fontsize=10.5)
axs[1].bar(range(len(ps)), [L[p]["days_mean"] for p in ps], color=C[2], width=0.55); axs[1].set_title("mean days until the question is learned", fontsize=10.5)
for ax, key in ((axs[0], "reviews_mean"), (axs[1], "days_mean")):
    for i, p in enumerate(ps): ax.text(i, L[p][key] * 1.02 + 0.5, f"{L[p][key]:.1f}", ha="center", fontsize=9)
    ax.set_xticks(range(len(ps))); ax.set_xticklabels([f"p = {p}" for p in ps]); ax.set_xlabel("chance of answering correctly at each review")
fig.tight_layout(); fig.savefig("assets/chart_leitner.png"); plt.close(fig)

# 3. adaptive practice
A = R["adaptive"]; fig, ax = plt.subplots(figsize=(6.4, 3.5), dpi=200)
prof = ["weak", "average", "strong"]; bottom = np.zeros(3)
for lvl, col, lab in ((1, "#7fb08f", "easy"), (2, "#e0b04c", "medium"), (3, "#c0605a", "hard")):
    v = np.array([A[p]["share_late"][str(lvl)] for p in prof]); ax.bar(range(3), v, bottom=bottom, color=col, label=lab, width=0.55)
    for i, x in enumerate(v):
        if x > 6: ax.text(i, bottom[i] + x / 2, f"{x:.0f}%", ha="center", va="center", fontsize=9.5, color="white")
    bottom += v
ax.set_xticks(range(3)); ax.set_xticklabels(["weak student\n(80%, 45%, 15% right)", "average student\n(92%, 70%, 40%)", "strong student\n(98%, 90%, 75%)"], fontsize=9)
ax.set_ylabel("share of questions served (%)"); ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.12), fontsize=9.5)
fig.tight_layout(); fig.savefig("assets/chart_adaptive.png"); plt.close(fig)

# 4. latency
Lt = R["latency"]; keys = list(Lt); fig, ax = plt.subplots(figsize=(7.4, 3.5), dpi=200)
y = np.arange(len(keys))[::-1]
ax.barh(y, [Lt[k]["median_ms"] for k in keys], color=C[1], height=0.55)
for yy, k in zip(y, keys): ax.text(Lt[k]["median_ms"] + 0.8, yy, f"{Lt[k]['median_ms']:.1f} ms", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(keys, fontsize=9); ax.set_xlabel("median time per request (ms)"); ax.grid(axis="x", alpha=.25)
fig.tight_layout(); fig.savefig("assets/chart_latency.png"); plt.close(fig)
print("ok")
