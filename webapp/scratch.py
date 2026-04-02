import sqlite3
import matplotlib.pyplot as plt
import math

conn = sqlite3.connect("issues.db")
repos = [r[0] for r in conn.execute("SELECT DISTINCT repo FROM issues")]

cols = 3
rows = math.ceil(len(repos) / cols)
fig = plt.figure(figsize=(7 * cols, 7 * rows))

colors = {"Easy": "#4CAF50", "Medium": "#FF9800", "Hard": "#F44336"}

for i, repo in enumerate(repos):
    result = conn.execute(
        "SELECT difficulty, COUNT(*) FROM issues WHERE repo = ? GROUP BY difficulty",
        (repo,)
    )
    data = {r[0]: r[1] for r in result}
    labels = list(data.keys())
    vals = list(data.values())
    c = [colors.get(l, "#999") for l in labels]

    ax = fig.add_subplot(rows, cols, i + 1)
    ax.pie(vals, colors=c, startangle=90, radius=1.1)
    ax.set_title(repo, fontsize=12, fontweight="bold", y=1.15)

conn.close()

patches = [plt.matplotlib.patches.Patch(color=colors[k], label=k) for k in ["Easy", "Medium", "Hard"]]
fig.legend(handles=patches, loc="lower center", ncol=3, fontsize=12)
fig.subplots_adjust(top=0.90, bottom=0.08, hspace=0.5, wspace=0.3)
plt.savefig("difficulty_piechart.png", dpi=150, bbox_inches="tight")
plt.show()