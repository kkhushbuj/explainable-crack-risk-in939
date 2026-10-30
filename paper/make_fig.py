import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Counts exactly as in dissertation Table 2.1: (label, n samples, n cracked, n doped)
rows = [
    ("Doğu 2024", 27, 27, 0), ("Marchese 2020", 48, 48, 0),
    ("Li 2024/25", 3, 3, 0), ("Rodríguez-Barber 2023", 27, 23, 0),
    ("Ozer 2024", 3, 3, 0), ("Hu 2024", 1, 1, 0),
    ("Zhang 2023", 3, 2, 2), ("Chen 2026", 2, 2, 1),
    ("Ding 2026", 3, 1, 2), ("Bae 2025", 12, 4, 8),
]
assert sum(r[1] for r in rows) == 129 and sum(r[2] for r in rows) == 114
labels = [r[0] for r in rows]
rate = [100 * r[2] / r[1] for r in rows]
cols = ["#2b6cb0" if r[3] == 0 else "#d97706" for r in rows]
fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
ax.bar(range(len(rows)), rate, color=cols)
for i, r in enumerate(rows):
    ax.text(i, rate[i] + 1.5, f"{r[2]}/{r[1]}", ha="center", fontsize=7)
ax.set_xticks(range(len(rows)))
ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=8)
ax.set_ylabel("Samples reporting cracking (%)")
ax.set_ylim(0, 100)
ax.set_ylim(0, 118)
ax.spines[["top", "right"]].set_visible(False)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color="#2b6cb0", label="no doped samples"),
                   Patch(color="#d97706", label="includes doped samples")],
          frameon=False, fontsize=8, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.0))
fig.tight_layout()
fig.savefig("figs/fig_crack_rate_by_paper.png")
print("ok")
