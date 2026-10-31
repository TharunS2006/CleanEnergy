import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
R = json.load(open("../bench_results.json"))
names = list(R["sizes"]); nfa = [R["sizes"][k]["nfa"] for k in names]; dfa = [R["sizes"][k]["dfa"] for k in names]; mn = [R["sizes"][k]["min"] for k in names]
import numpy as np
x = np.arange(len(names)); w = 0.27
fig, ax = plt.subplots(figsize=(8.2, 3.9), dpi=200)
ax.bar(x - w, nfa, w, label="NFA (Thompson)", color="#7f9cc9"); ax.bar(x, dfa, w, label="DFA (subset construction)", color="#3f5f9b"); ax.bar(x + w, mn, w, label="Minimal DFA", color="#1b2f5e")
ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels(names, rotation=20, ha="right"); ax.set_ylabel("number of states (log scale)")
ax.legend(frameon=False, fontsize=9.5); ax.grid(axis="y", alpha=.25)
for i, v in enumerate(mn): ax.text(i + w, v * 1.12, str(v), ha="center", fontsize=8.5, color="#1b2f5e")
fig.tight_layout(); fig.savefig("assets/chart_sizes.png"); plt.close(fig)

sc = R["scaling"]
fig, ax = plt.subplots(figsize=(6.2, 3.6), dpi=200)
L = [a for a, b in sc]; T = [b for a, b in sc]
ax.loglog(L, T, "o-", color="#1b2f5e", lw=2, label="measured (DFA runner)")
ax.loglog(L, [T[0] * l / L[0] for l in L], "--", color="#999", lw=1.3, label="straight line (linear in length)")
ax.set_xlabel("URL length (characters)"); ax.set_ylabel("time per URL (microseconds)"); ax.grid(alpha=.25, which="both"); ax.legend(frameon=False, fontsize=9.5)
fig.tight_layout(); fig.savefig("assets/chart_scaling.png"); plt.close(fig)

g = R["label_growth"]
fig, ax = plt.subplots(figsize=(6.2, 3.4), dpi=200)
ax.plot([a for a, *_ in g], [d for a, n, d, m in g], "s-", color="#7f9cc9", lw=2, label="DFA before minimisation")
ax.plot([a for a, *_ in g], [m for a, n, d, m in g], "o-", color="#1b2f5e", lw=2, label="minimal DFA")
ax.set_xlabel("longest allowed label (characters)"); ax.set_ylabel("states"); ax.grid(alpha=.25); ax.legend(frameon=False, fontsize=9.5)
fig.tight_layout(); fig.savefig("assets/chart_labels.png"); plt.close(fig)
