"""
iRobot Create Controller
Reads treatment configuration from environment variables:
  USE_GA      = "1" or "0"
  USE_FUZZER  = "1" or "0"
  RUN_SEED    = integer seed for reproducibility
  RUN_INDEX   = run number within the treatment
  TREATMENT   = treatment name string
  RESULTS_DIR = path to folder where JSON files are saved

This single file handles all 4 treatments:
  baseline    (no GA, no fuzzer)
  baseline2   (no GA,    fuzzer)
  experiment1 (GA,    no fuzzer)
  experiment2 (GA,       fuzzer)
"""

from controller import Supervisor
import math
import random
import string
import time
import threading
import os
import json
import psutil
import os as _os

# ============================================================
# 0 — Read environment configuration
# ============================================================

USE_GA      = os.environ.get("USE_GA",      "1") == "1"
USE_FUZZER  = os.environ.get("USE_FUZZER",  "1") == "1"
RUN_SEED    = int(os.environ.get("RUN_SEED",    "42"))
RUN_INDEX   = int(os.environ.get("RUN_INDEX",   "1"))
TREATMENT   = os.environ.get("TREATMENT",   "experiment2")
RESULTS_DIR = os.environ.get("RESULTS_DIR", "./results")

random.seed(RUN_SEED)   # deterministic run

print(f">>> Config: treatment={TREATMENT}  seed={RUN_SEED}  run={RUN_INDEX}")
print(f">>>         USE_GA={USE_GA}  USE_FUZZER={USE_FUZZER}")

# ============================================================
# 1 — GENETIC ALGORITHM (runs in a separate thread if enabled)
# ============================================================

TARGET = "hello world"
ALPHABET = string.ascii_lowercase + " !"
POPULATION_SIZE = 200
MUTATION_RATE = 0.01
ELITE_SIZE = 20

ga_status = {
    "running": False,
    "done":    False,
    "generation": 0,
    "best":    "",
    "fitness": 0,
    "time":    0.0,
}


def random_individual():
    return "".join(random.choice(ALPHABET) for _ in range(len(TARGET)))


def ga_fitness(individual):
    return sum(1 for i, c in enumerate(individual) if c == TARGET[i])


def crossover(parent1, parent2):
    cut = random.randint(0, len(TARGET) - 1)
    return parent1[:cut] + parent2[cut:]


def mutate_gene(individual):
    return "".join(
        random.choice(ALPHABET) if random.random() < MUTATION_RATE else c
        for c in individual
    )


def run_genetic_algorithm():
    ga_status["running"] = True
    population = [random_individual() for _ in range(POPULATION_SIZE)]
    generation = 0
    t_start = time.perf_counter()

    while True:
        generation += 1
        population.sort(key=ga_fitness, reverse=True)
        best = population[0]
        best_fit = ga_fitness(best)
        ga_status["generation"] = generation
        ga_status["best"] = best
        ga_status["fitness"] = best_fit
        if best == TARGET:
            break
        new_population = population[:ELITE_SIZE]
        while len(new_population) < POPULATION_SIZE:
            p1 = random.choice(population[:50])
            p2 = random.choice(population[:50])
            new_population.append(mutate_gene(crossover(p1, p2)))
        population = new_population

    ga_status["time"] = time.perf_counter() - t_start
    ga_status["running"] = False
    ga_status["done"] = True
    print(f"\n  [GA] Done: '{best}' in {generation} gen ({ga_status['time']:.4f}s)")


ga_thread = None
if USE_GA:
    ga_thread = threading.Thread(target=run_genetic_algorithm, daemon=True)
    ga_thread.start()
    print(">>> GA thread started...")
else:
    ga_status["done"] = True
    print(">>> GA disabled for this treatment.")

# ============================================================
# 2 — SEARCH-BASED FUZZER (hillclimber, runs in a thread if enabled)
# ============================================================

robot_state = {
    "x": 0.0,
    "z": 0.0,
    "speed": 0.0,
    "collision_count": 0,
    "lock": threading.Lock(),
}

fuzzer_log = []


def fuzzer_fitness(snap, baseline_speed):
    speed_drop = max(0.0, baseline_speed - snap["speed"])
    collision_bonus = snap["collision_count"] * 5.0
    return speed_drop + collision_bonus


def place_obstacle(supervisor, name, x, z, size=0.15):
    root = supervisor.getRoot()
    children_field = root.getField("children")
    node_string = f"""
    DEF {name} Solid {{
      translation {x:.3f} {size:.3f} {z:.3f}
      children [
        Shape {{
          appearance Appearance {{
            material Material {{ diffuseColor 1 0.3 0 }}
          }}
          geometry Box {{ size {size*2:.3f} {size*2:.3f} {size*2:.3f} }}
        }}
      ]
      boundingObject Box {{ size {size*2:.3f} {size*2:.3f} {size*2:.3f} }}
      physics Physics {{ density 500 }}
    }}
    """
    children_field.importMFNodeFromString(-1, node_string)


def remove_obstacle(supervisor, name):
    node = supervisor.getFromDef(name)
    if node is not None:
        node.remove()


def mutate_obstacle(obs, delta=0.15):
    x, z, size = obs
    choice = random.randint(0, 2)
    if choice == 0:
        x = max(0.1, min(1.9, x + random.uniform(-delta, delta)))
    elif choice == 1:
        z = max(-0.5, min(0.5, z + random.uniform(-delta, delta)))
    else:
        size = max(0.05, min(0.3, size + random.uniform(-0.05, 0.05)))
    return (x, z, size)


def run_fuzzer(supervisor, baseline_speed, robot_x_goal=2.0, observe_secs=2.0):
    print(">>> Fuzzer thread started...")
    max_iter = 25
    n_obs = 3
    obs_names = [f"FUZZ_{i}" for i in range(n_obs)]

    current = [
        (random.uniform(0.3, 1.7), random.uniform(-0.35, 0.35), random.uniform(0.08, 0.18))
        for _ in range(n_obs)
    ]

    for name, obs in zip(obs_names, current):
        place_obstacle(supervisor, name, obs[0], obs[1], obs[2])

    time.sleep(observe_secs)
    with robot_state["lock"]:
        snap = dict(robot_state)
    best_fitness = fuzzer_fitness(snap, baseline_speed)

    for it in range(max_iter):
        with robot_state["lock"]:
            if robot_state["x"] >= robot_x_goal:
                break

        idx = random.randint(0, n_obs - 1)
        candidate = list(current)
        candidate[idx] = mutate_obstacle(current[idx])

        remove_obstacle(supervisor, obs_names[idx])
        place_obstacle(supervisor, obs_names[idx], candidate[idx][0],
                       candidate[idx][1], candidate[idx][2])

        time.sleep(observe_secs)
        with robot_state["lock"]:
            snap = dict(robot_state)
        cfit = fuzzer_fitness(snap, baseline_speed)

        if cfit >= best_fitness:
            current = candidate
            best_fitness = cfit
        else:
            remove_obstacle(supervisor, obs_names[idx])
            place_obstacle(supervisor, obs_names[idx], current[idx][0],
                           current[idx][1], current[idx][2])

        fuzzer_log.append({"iter": it + 1, "fitness": best_fitness, "layout": list(current)})

    for name in obs_names:
        remove_obstacle(supervisor, name)
    print(f"  [FUZZER] Best fitness: {best_fitness:.4f}")


# ============================================================
# 3 — ROBOT CONTROLLER with OBSTACLE AVOIDANCE
# ============================================================

robot = Supervisor()
timestep = int(robot.getBasicTimeStep())

gps = robot.getDevice('gps')
gps.enable(timestep)

left_motor  = robot.getDevice('left wheel motor')
right_motor = robot.getDevice('right wheel motor')
left_motor.setPosition(float('inf'))
right_motor.setPosition(float('inf'))
left_motor.setVelocity(0)
right_motor.setVelocity(0)

bumper_left  = robot.getDevice('bumper_left')
bumper_right = robot.getDevice('bumper_right')
bumper_left.enable(timestep)
bumper_right.enable(timestep)

cliff_fl = robot.getDevice('cliff_front_left')
cliff_fr = robot.getDevice('cliff_front_right')
cliff_l  = robot.getDevice('cliff_left')
cliff_r  = robot.getDevice('cliff_right')
cliff_fl.enable(timestep)
cliff_fr.enable(timestep)
cliff_l.enable(timestep)
cliff_r.enable(timestep)

MOTOR_SPEED     = 5.0
BACK_SPEED      = -3.0
TURN_SPEED      = 3.0
TARGET_X        = 2.0
CLIFF_THRESHOLD = 100

FORWARD  = "forward"
BACKWARD = "backward"
TURN     = "turn"

avoidance_state = FORWARD
avoidance_timer = 0
turn_direction  = 1

start_time         = None
last_pos           = None
total_distance     = 0.0
max_speed_detected = 0.0
baseline_speed     = None
fuzzer_thread      = None
step_count         = 0

print(">>> Robot controller started...")

# ============================================================
# MAIN LOOP
# ============================================================

while robot.step(timestep) != -1:
    pos = gps.getValues()
    if math.isnan(pos[0]):
        continue

    curr_x, curr_y, curr_z = pos[0], pos[1], pos[2]
    step_count += 1

    if start_time is None:
        start_time = robot.getTime()
        last_pos   = (curr_x, curr_z)
        print(f"Start at X={curr_x:.2f}")
        continue

    dist_step = math.sqrt(
        (curr_x - last_pos[0]) ** 2 + (curr_z - last_pos[1]) ** 2
    )
    total_distance += dist_step
    instant_speed = dist_step / (timestep / 1000.0)
    if instant_speed > max_speed_detected:
        max_speed_detected = instant_speed
    last_pos = (curr_x, curr_z)

    with robot_state["lock"]:
        robot_state["x"]     = curr_x
        robot_state["z"]     = curr_z
        robot_state["speed"] = instant_speed

    hit_left    = bumper_left.getValue()  > 0.5
    hit_right   = bumper_right.getValue() > 0.5
    cliff_front = (cliff_fl.getValue() < CLIFF_THRESHOLD or
                   cliff_fr.getValue() < CLIFF_THRESHOLD)

    if hit_left or hit_right:
        with robot_state["lock"]:
            robot_state["collision_count"] += 1

    # Obstacle avoidance state machine
    if avoidance_state == FORWARD:
        if hit_left and hit_right:
            avoidance_state = BACKWARD
            avoidance_timer = 20
            turn_direction  = 1
        elif hit_left or cliff_front:
            avoidance_state = BACKWARD
            avoidance_timer = 15
            turn_direction  = 1
        elif hit_right:
            avoidance_state = BACKWARD
            avoidance_timer = 15
            turn_direction  = -1
        else:
            left_motor.setVelocity(MOTOR_SPEED)
            right_motor.setVelocity(MOTOR_SPEED)

    elif avoidance_state == BACKWARD:
        left_motor.setVelocity(BACK_SPEED)
        right_motor.setVelocity(BACK_SPEED)
        avoidance_timer -= 1
        if avoidance_timer <= 0:
            avoidance_state = TURN
            avoidance_timer = 25

    elif avoidance_state == TURN:
        left_motor.setVelocity( TURN_SPEED * turn_direction)
        right_motor.setVelocity(-TURN_SPEED * turn_direction)
        avoidance_timer -= 1
        if avoidance_timer <= 0:
            avoidance_state = FORWARD

    # Launch fuzzer after warm-up (only if enabled)
    if USE_FUZZER and step_count == 60 and fuzzer_thread is None:
        baseline_speed = instant_speed if instant_speed > 0 else 0.01
        fuzzer_thread = threading.Thread(
            target=run_fuzzer,
            args=(robot, baseline_speed, TARGET_X, 2.0),
            daemon=True
        )
        fuzzer_thread.start()

    # Check destination
    if curr_x >= TARGET_X:
        end_time      = robot.getTime()
        total_time    = end_time - start_time
        average_speed = total_distance / total_time if total_time > 0 else 0

        left_motor.setVelocity(0)
        right_motor.setVelocity(0)

        if USE_GA and ga_status["running"]:
            print(">>> Waiting for GA thread...")
            ga_thread.join()

        with robot_state["lock"]:
            collisions = robot_state["collision_count"]

        # --- Print results (same as before) ---
        print("\n" + "=" * 45)
        print("   ROBOT PERFORMANCE RESULTS")
        print("=" * 45)
        print(f"Total Time        : {total_time:.3f} s")
        print(f"Distance Traveled : {total_distance:.3f} m")
        print(f"Average Speed     : {average_speed:.3f} m/s")
        print(f"Max Speed         : {max_speed_detected:.3f} m/s")
        print(f"Total Collisions  : {collisions}")
        if USE_GA:
            print("-" * 45)
            print(f"GA Time           : {ga_status['time']:.4f} s")
            print(f"GA Generations    : {ga_status['generation']}")
            print(f"GA Solution       : '{ga_status['best']}'")
        if USE_FUZZER and fuzzer_log:
            best_e = max(fuzzer_log, key=lambda e: e["fitness"])
            print("-" * 45)
            print(f"Fuzzer Iterations : {len(fuzzer_log)}")
            print(f"Best Fitness      : {best_e['fitness']:.4f}")
        print("=" * 45)

        # ============================================================
        # SAVE RESULTS TO JSON
        # ============================================================
        # Memory usage at end of run
        process = psutil.Process(_os.getpid())
        memory_mb = process.memory_info().rss / (1024 * 1024)
        print(f">>> Memory usage: {memory_mb:.2f} MB")
        
        result = {
            "treatment":   TREATMENT,
            "run_index":   RUN_INDEX,
            "seed":        RUN_SEED,
            "use_ga":      USE_GA,
            "use_fuzzer":  USE_FUZZER,
            # Robot metrics
            "total_time":       round(total_time, 4),
            "total_distance":   round(total_distance, 4),
            "average_speed":    round(average_speed, 4),
            "max_speed":        round(max_speed_detected, 4),
            "collisions":       collisions,
            "memory_mb":  round(memory_mb, 2),
            # GA metrics (None if GA not used)
            "ga_time":          round(ga_status["time"], 4) if USE_GA else None,
            "ga_generations":   ga_status["generation"]     if USE_GA else None,
            "ga_solution":      ga_status["best"]           if USE_GA else None,
            # Fuzzer metrics (None if fuzzer not used)
            "fuzzer_iterations": len(fuzzer_log) if USE_FUZZER else None,
            "fuzzer_best_fitness": round(max(fuzzer_log, key=lambda e: e["fitness"])["fitness"], 4)
                                   if USE_FUZZER and fuzzer_log else None,
        }

        os.makedirs(RESULTS_DIR, exist_ok=True)
        output_file = os.path.join(RESULTS_DIR, f"{TREATMENT}.json")

        # Load existing data (if file already has runs), then append
        existing = []
        if os.path.exists(output_file):
            with open(output_file, "r") as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []

        existing.append(result)

        with open(output_file, "w") as f:
            json.dump(existing, f, indent=2)

        print(f">>> Result saved → {output_file}  (total runs: {len(existing)})")
        import os, signal
        os.kill(os.getppid(), signal.SIGTERM)
