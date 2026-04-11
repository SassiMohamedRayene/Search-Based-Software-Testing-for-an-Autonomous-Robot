# Search-Based Software Testing for an Autonomous Robot — Webots Simulation

> **Research project** | Grand Valley State University  
> **Author:** Rayene Sassi  
> **Supervisor:** Erik Fredericks
> **Tool:** Webots Robot Simulator + Python

---

## Table of Contents

1. [What is this project?](#1-what-is-this-project)
2. [How the system works](#2-how-the-system-works)
3. [The 4 experimental treatments](#3-the-4-experimental-treatments)
4. [Project file structure](#4-project-file-structure)
5. [Code explanation](#5-code-explanation)
6. [How to run the project](#6-how-to-run-the-project)
7. [How to analyze results in Google Colab](#7-how-to-analyze-results-in-google-colab)
8. [Results and metrics explained](#8-results-and-metrics-explained)

---

## 1. What is this project?

This project applies **Search-Based Software Testing (SBST)** to an autonomous robot simulation. The goal is to automatically find difficult situations that challenge the robot — situations that a human tester might not think of.

The robot used is an **iRobot Create**, simulated inside **Webots**. The robot starts at one position and must reach a target destination. We measure how well it performs across 25 repeated runs per configuration.

Two testing tools run at the same time as the robot:

- **A Genetic Algorithm (GA)** — a search algorithm that evolves a population of strings to match a target phrase. It runs in a parallel thread to simulate a concurrent computational load.
- **A Search-Based Fuzzer** — a hillclimber algorithm that automatically places and moves physical obstacles in the robot's path. Its goal is to find the obstacle configuration that causes the most collisions and the biggest speed reduction.

By combining these tools across 4 different configurations, we can measure what effect each tool has on the robot's behavior.

---

## 2. How the system works

```
Webots simulation starts
        │
        ▼
Robot moves toward TARGET_X = 2.0 m
        │
        ├──► GA thread runs in parallel (string evolution)
        │
        ├──► Fuzzer thread places obstacles dynamically
        │         └── hillclimber mutates obstacle positions
        │             to maximize: speed drop + collisions
        │
        ▼
Robot reaches destination
        │
        ▼
Results saved to JSON file
        │
        ▼
Webots closes → next run starts automatically
```

The robot uses **bumper sensors** and **cliff sensors** to detect obstacles. When it hits something, it backs up, turns, and continues forward. Every collision is counted.

---

## 3. The 4 experimental treatments

We run 25 simulations for each treatment — **100 runs in total**.

| Treatment | GA | Fuzzer | Purpose |
|---|---|---|---|
| **Baseline** | No | No | Pure robot behavior, no interference |
| **Baseline 2** | No | Yes | Fuzzer effect only |
| **Experiment 1** | Yes | No | GA effect only |
| **Experiment 2** | Yes | Yes | Full system — both tools active |

Each run uses a **different random seed** (1001 to 1025) to ensure reproducibility. The same seed always produces the same run.

---

## 4. Project file structure

```
my_first_simulation/                  ← your Webots project root
│
├── controllers/
│   └── iRobot_controller/
│       └── iRobot_controller.py      ← MAIN robot controller (all 4 treatments)
│
├── worlds/
│   └── my_first_simulation.wbt       ← Webots world file (the simulation scene)
│
├── libraries/                        ← Webots internal (do not modify)
├── plugins/                          ← Webots internal (do not modify)
├── protos/                           ← Webots internal (do not modify)
│
├── run_experiments.sh                ← Bash script: runs 100 simulations automatically
│
├── results/                          ← Created automatically when you run the script
│   ├── baseline.json                 ← 25 runs, no GA, no fuzzer
│   ├── baseline2.json                ← 25 runs, fuzzer only
│   ├── experiment1.json              ← 25 runs, GA only
│   └── experiment2.json              ← 25 runs, GA + fuzzer
│
└── analyze_results.py                ← Google Colab analysis script (boxplots + stats)
```

---

## 5. Code explanation

### `iRobot_controller.py` — the main controller

This single file handles all 4 treatments. It reads its configuration from **environment variables** set by the bash script.

**Structure of the file:**

```
Section 0 — Read environment variables (treatment, seed, flags)
Section 1 — Genetic Algorithm (runs in a parallel thread if USE_GA=1)
Section 2 — Search-Based Fuzzer (runs in a parallel thread if USE_FUZZER=1)
Section 3 — Robot controller (obstacle avoidance state machine)
Section 4 — Save results to JSON when robot reaches destination
```

**Key variables:**

| Variable | Description |
|---|---|
| `USE_GA` | `"1"` = GA enabled, `"0"` = disabled |
| `USE_FUZZER` | `"1"` = Fuzzer enabled, `"0"` = disabled |
| `TREATMENT` | Name string saved in JSON (e.g. `"baseline"`) |
| `RUN_SEED` | Integer seed for `random.seed()` — makes runs reproducible |
| `RUN_INDEX` | Run number (1 to 25) |
| `RESULTS_DIR` | Full path to the `results/` folder |
| `TARGET_X` | X coordinate the robot must reach (set to `2.0` m) |

**Obstacle avoidance — state machine:**

The robot has 3 states:
- `FORWARD` — drives straight toward the target
- `BACKWARD` — reverses after hitting an obstacle
- `TURN` — rotates left or right before resuming forward motion

**Fuzzer fitness function:**

```python
fitness = speed_drop + (collision_count × 5.0)
```

The fuzzer tries to maximize this value by mutating obstacle positions. Higher fitness = more disruptive scenario for the robot.

**Metrics collected per run:**

| Metric | Description |
|---|---|
| `total_time` | Seconds from start to reaching target |
| `total_distance` | Total meters traveled (including detours) |
| `average_speed` | total_distance / total_time |
| `max_speed` | Highest instantaneous speed recorded |
| `collisions` | Number of bumper sensor activations |
| `memory_mb` | RAM used by the controller process (via `psutil`) |
| `ga_time` | Seconds for GA to find the solution |
| `ga_generations` | Number of GA generations needed |
| `fuzzer_iterations` | Number of hillclimber iterations completed |
| `fuzzer_best_fitness` | Best fitness score found by the fuzzer |

---

### `run_experiments.sh` — the automation script

This bash script runs Webots **100 times automatically** — 25 runs × 4 treatments. It:

1. Sets the environment variables for each run (`TREATMENT`, `USE_GA`, `USE_FUZZER`, `RUN_SEED`, etc.)
2. Launches Webots in **headless mode** (`--no-rendering`) and **fast mode** (`--mode=fast`)
3. Waits for Webots to close (the controller calls `os.kill()` when done)
4. Moves to the next run

**The 4 treatments are called in order:**
```bash
run_treatment "baseline"    "0" "0"
run_treatment "baseline2"   "0" "1"
run_treatment "experiment1" "1" "0"
run_treatment "experiment2" "1" "1"
```

---

### `analyze_results.py` — Google Colab analysis

This script:
1. Loads the 4 JSON files
2. Extracts each metric into a Python list
3. Produces **side-by-side boxplots** using `seaborn`
4. Runs **Wilcoxon signed-rank tests** using `scipy` to check if differences are statistically significant
5. Prints a **median summary table** for all treatments

---

## 6. How to run the project

### Requirements

- **Webots** installed at `/Applications/Webots.app` (Mac) or equivalent path
- **Python 3** with `psutil` installed:
  ```bash
  /usr/bin/python3 -m pip install psutil
  ```

### Step 1 — Clone or download this project

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

### Step 2 — Open the world in Webots once to verify it works

Open Webots → File → Open World → select `worlds/my_first_simulation.wbt`  
Press Play. The robot should move and reach the destination.  
Close Webots.

### Step 3 — Edit `run_experiments.sh` — 2 lines only

Open `run_experiments.sh` with any text editor and update:

```bash
WEBOTS="/Applications/Webots.app/Contents/MacOS/webots"   # your Webots path
WORLD="/full/path/to/my_first_simulation/worlds/my_first_simulation.wbt"
```

To find your Webots path on Mac:
```bash
find /Applications -name "webots" -type f
```

To find your world path:
```bash
find ~ -name "*.wbt"
```

### Step 4 — Make the script executable

```bash
chmod +x run_experiments.sh
```

### Step 5 — Run all 100 experiments

```bash
cd /path/to/my_first_simulation
./run_experiments.sh
```

Webots will open and close automatically 100 times. Each run saves its result to the `results/` folder. The full run takes approximately **2-3 hours**.

You will see in the terminal:
```
Treatment : baseline   USE_GA : 0   USE_FUZZER : 0
  Run 1 / 25  (seed=1001)
  Run 2 / 25  (seed=1002)
  ...
```

### Step 6 — Check your results

```bash
ls results/
# baseline.json   baseline2.json   experiment1.json   experiment2.json

cat results/baseline.json | python3 -m json.tool | head -30
```

---

## 7. How to analyze results in Google Colab

1. Go to [colab.research.google.com](https://colab.research.google.com) → New notebook
2. Click the **folder icon** on the left sidebar → upload your 4 JSON files
3. In the first cell, run:
   ```python
   !pip install seaborn scipy -q
   ```
4. In the second cell, paste the full content of `analyze_results.py` and run it

You will get:
- 5 boxplot images (time, speed, collisions, distance, memory)
- Wilcoxon p-values for all key comparisons
- A median summary table

---

## 8. Results and metrics explained

### What the results show

| Observation | Explanation |
|---|---|
| Baseline = Experiment 1 (identical) | The GA runs in a separate thread and does not affect the robot's movement. This is expected. |
| Baseline 2 and Experiment 2 have high variability | The fuzzer places different obstacles each run, creating varied scenarios. |
| Collisions = 0 without fuzzer | Without obstacles, the path is always clear. The robot never hits anything. |
| Speed drops ~30% with fuzzer | The robot slows down due to obstacle avoidance maneuvers. |
| Fuzzer + GA produces the most collisions | Experiment 2 shows median 17 collisions vs 15 for Baseline 2. |

### Statistical significance

All key comparisons between treatments with and without the fuzzer have **p < 0.05** (Wilcoxon test), meaning the differences are **statistically significant** and not due to random chance.

The comparison Baseline vs Experiment 1 returns **p = NaN** because both datasets are identical — this is not an error, it confirms that the GA has no effect on robot behavior.

### Number of obstacles per run

The fuzzer generates **3 obstacles per run**. Their positions are mutated by the hillclimber at each iteration to find the most disruptive configuration.

### Robot getting stuck

In rare cases (very low frequency), the robot entered a loop where it repeatedly hit the same obstacle without escaping. These cases are visible as outliers in the boxplots (very high total time).

---

## Dependencies

| Library | Used in | Install |
|---|---|---|
| `psutil` | Controller (memory tracking) | `pip install psutil` |
| `seaborn` | Colab analysis (boxplots) | `pip install seaborn` |
| `scipy` | Colab analysis (Wilcoxon test) | `pip install scipy` |
| `matplotlib` | Colab analysis (plots) | included with Colab |
| `numpy` | Colab analysis (median) | included with Colab |
| `controller` | Robot controller | included with Webots |

---

*This project was developed as part of a research study on Search-Based Software Testing applied to autonomous robotics.*
