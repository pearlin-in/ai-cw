import csv
import matplotlib.pyplot as plt

rows = [r for r in csv.DictReader(open("results.csv")) if r["Status"] in ("Solved", "No solution")]
names = [r["Puzzle"] for r in rows]
steps = [max(int(r["Steps"]), 1) for r in rows]

plt.bar(names, steps)
plt.yscale("log")
plt.ylabel("Search steps (log scale)")
plt.xticks(rotation=20)
plt.tight_layout()
plt.savefig("steps.png", dpi=200)