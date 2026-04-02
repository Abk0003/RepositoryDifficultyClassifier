import sqlite3
import matplotlib.pyplot as plt
import numpy as np

conn = sqlite3.connect("issues.db")
repos = [r[0] for r in conn.execute("SELECT DISTINCT repo FROM issues")]

colors = {"Easy": "#4CAF50", "Medium": "#FF9800", "Hard": "#F44336"}
data = {}

for repo in repos:
    result = conn.execute(
        "SELECT difficulty, COUNT(*) FROM issues WHERE repo = ? GROUP BY difficulty",
        (repo,)
    )
    counts = {r[0]: r[1] for r in result}
    total = sum(counts.values())
    data[repo] = {k: counts.get(k, 0) / total * 100 for k in ["Easy", "Medium", "Hard"]}

conn.close()

names = [r.split("/")[1] for r in repos]
easy = [data[r]["Easy"] for r in repos]
med = [data[r]["Medium"] for r in repos]
hard = [data[r]["Hard"] for r in repos]

fig, ax = plt.subplots(figsize=(max(len(repos) * 1.5, 8), 6))

x = np.arange(len(repos))
ax.bar(x, easy, color=colors["Easy"], label="Easy")
ax.bar(x, med, bottom=easy, color=colors["Medium"], label="Medium")
ax.bar(x, hard, bottom=[e + m for e, m in zip(easy, med)], color=colors["Hard"], label="Hard")

ax.set_xticks(x)
ax.set_xticklabels(names, rotation=45, ha="right", fontsize=11)
ax.set_ylabel("Percentage (%)", fontsize=12)
ax.set_title("Issue Difficulty Distribution by Repository", fontsize=14, fontweight="bold")
ax.legend(fontsize=11)
ax.set_ylim(0, 100)

plt.tight_layout()
plt.savefig("difficulty_barchart.png", dpi=150, bbox_inches="tight")
plt.show()