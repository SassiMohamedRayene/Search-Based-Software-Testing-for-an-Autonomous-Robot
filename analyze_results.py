# ============================================================
# GOOGLE COLAB — Experiment Analysis
# Rayene — Robot Search-Based Software Testing
# ============================================================
# INSTRUCTIONS:
#   1. Open Google Colab (colab.research.google.com)
#   2. Click the folder icon on the left sidebar
#   3. Upload your 4 JSON files:
#        baseline.json, baseline2.json,
#        experiment1.json, experiment2.json
#   4. Copy-paste this entire script into a cell and run it
# ============================================================

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import wilcoxon

# ============================================================
# STEP 1 — Load the 4 JSON files
# ============================================================

def load(filename):
    with open(filename) as f:
        runs = json.load(f)
    return runs

baseline    = load("baseline.json")
baseline2   = load("baseline2.json")
experiment1 = load("experiment1.json")
experiment2 = load("experiment2.json")

print(f"baseline    : {len(baseline)} runs")
print(f"baseline2   : {len(baseline2)} runs")
print(f"experiment1 : {len(experiment1)} runs")
print(f"experiment2 : {len(experiment2)} runs")

# ============================================================
# STEP 2 — Extract metrics into lists (like your prof's example)
# ============================================================

def extract(runs, key):
    return [r[key] for r in runs if r.get(key) is not None]

# Total time
time_b1  = extract(baseline,    "total_time")
time_b2  = extract(baseline2,   "total_time")
time_e1  = extract(experiment1, "total_time")
time_e2  = extract(experiment2, "total_time")

# Average speed
speed_b1 = extract(baseline,    "average_speed")
speed_b2 = extract(baseline2,   "average_speed")
speed_e1 = extract(experiment1, "average_speed")
speed_e2 = extract(experiment2, "average_speed")

# Collisions
col_b1   = extract(baseline,    "collisions")
col_b2   = extract(baseline2,   "collisions")
col_e1   = extract(experiment1, "collisions")
col_e2   = extract(experiment2, "collisions")

# Distance
dist_b1  = extract(baseline,    "total_distance")
dist_b2  = extract(baseline2,   "total_distance")
dist_e1  = extract(experiment1, "total_distance")
dist_e2  = extract(experiment2, "total_distance")

# Memory usage
mem_b1 = extract(baseline,    "memory_mb")
mem_b2 = extract(baseline2,   "memory_mb")
mem_e1 = extract(experiment1, "memory_mb")
mem_e2 = extract(experiment2, "memory_mb")

LABELS = ['Baseline\n(no GA, no fuzzer)',
          'Baseline 2\n(fuzzer, no GA)',
          'Experiment 1\n(GA, no fuzzer)',
          'Experiment 2\n(GA + fuzzer)']

# ============================================================
# STEP 3 — Boxplots (avec échelles personnalisées)
# ============================================================

# Remplacement de ymin par y_limits (un tuple contenant min et max)
def boxplot(data_list, title, ylabel, filename, y_limits=None):
    plt.figure(figsize=(10, 5))
    sns.boxplot(data=data_list, palette=["#9E9E9E", "#5C6BC0", "#26A69A", "#EF5350"])
    plt.title(title)
    plt.xticks([0, 1, 2, 3], LABELS)
    plt.xlabel("Treatment")
    plt.ylabel(ylabel)

    # Applique des limites spécifiques à l'axe Y si elles sont fournies
    if y_limits is not None:
        plt.ylim(y_limits)

    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.show()
    print(f"Saved: {filename}\n")

# Plot 1 — Total time (Ajusté entre 14 et 27 secondes)
boxplot(
    [time_b1, time_b2, time_e1, time_e2],
    "Total run time over 25 runs per treatment",
    "Total time (s)",
    "plot_total_time.png",
    y_limits=(14, 27)
)

# Plot 2 — Average speed (Ajusté entre 0.05 et 0.17 m/s)
boxplot(
    [speed_b1, speed_b2, speed_e1, speed_e2],
    "Average speed over 25 runs per treatment",
    "Average speed (m/s)",
    "plot_average_speed.png",
    y_limits=(0.05, 0.17)
)

# Plot 3 — Collisions (Ajusté entre -1 et 26 pour ne pas coller le zéro au bord bas)
boxplot(
    [col_b1, col_b2, col_e1, col_e2],
    "Collisions over 25 runs per treatment",
    "Number of collisions",
    "plot_collisions.png",
    y_limits=(-1, 26)
)

# Plot 4 — Distance (Ajusté entre 2.2 et 2.7 mètres comme tu l'as suggéré)
boxplot(
    [dist_b1, dist_b2, dist_e1, dist_e2],
    "Distance traveled over 25 runs per treatment",
    "Distance (m)",
    "plot_distance.png",
    y_limits=(2.2, 2.7)
)

boxplot(
    [mem_b1, mem_b2, mem_e1, mem_e2],
    "Memory usage over 25 runs per treatment",
    "Memory (MB)",
    "plot_memory.png"
)


# ============================================================
# STEP 4 — Wilcoxon tests (exactly like your prof's example)
# ============================================================

print("=" * 50)
print("  WILCOXON SIGNED-RANK TESTS")
print("=" * 50)

def wilcoxon_test(name_a, a, name_b, b):
    n = min(len(a), len(b))
    stat, pvalue = wilcoxon(a[:n], b[:n])
    sig = "***" if pvalue < 0.001 else ("**" if pvalue < 0.01 else ("*" if pvalue < 0.05 else "ns (not significant)"))
    print(f"\n{name_a}  vs  {name_b}")
    print(f"  p-value = {pvalue:.4f}  {sig}")
    return pvalue

print("\n--- Total Time ---")
wilcoxon_test("Baseline",    time_b1, "Experiment 2", time_e2)
wilcoxon_test("Baseline",    time_b1, "Experiment 1", time_e1)
wilcoxon_test("Baseline 2",  time_b2, "Experiment 2", time_e2)

print("\n--- Collisions ---")
wilcoxon_test("Baseline",     col_b1, "Experiment 2", col_e2)
wilcoxon_test("Baseline",     col_b1, "Baseline 2",   col_b2)
wilcoxon_test("Experiment 1", col_e1, "Experiment 2", col_e2)

print("\n--- Average Speed ---")
wilcoxon_test("Baseline",   speed_b1, "Experiment 2", speed_e2)
wilcoxon_test("Baseline 2", speed_b2, "Experiment 2", speed_e2)

print("\n--- Memory Usage ---")
wilcoxon_test("Baseline",    mem_b1, "Experiment 2", mem_e2)
wilcoxon_test("Baseline 2",  mem_b2, "Experiment 2", mem_e2)

# ============================================================
# STEP 5 — Summary table
# ============================================================

print("\n" + "=" * 50)
print("  MEDIAN SUMMARY")
print("=" * 50)
print(f"{'Treatment':<20} {'Time(s)':>8} {'Speed':>8} {'Collisions':>12} {'Distance':>10}")
print("-" * 60)
for name, t, s, c, d in [
    ("Baseline",     time_b1, speed_b1, col_b1, dist_b1),
    ("Baseline 2",   time_b2, speed_b2, col_b2, dist_b2),
    ("Experiment 1", time_e1, speed_e1, col_e1, dist_e1),
    ("Experiment 2", time_e2, speed_e2, col_e2, dist_e2),
]:
    print(f"{name:<20} {np.median(t):>8.3f} {np.median(s):>8.4f} {np.median(c):>12.1f} {np.median(d):>10.3f}")
