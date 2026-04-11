#!/bin/bash
# ============================================================
# run_experiments.sh — compatible Mac (bash 3)
# Runs 25 × 4 treatments = 100 runs total
#
# HOW TO RUN:
#   cd /Users/rayene/Documents/my_first_simulation
#   chmod +x run_experiments.sh
#   ./run_experiments.sh
# ============================================================

WEBOTS="/Applications/Webots.app/Contents/MacOS/webots"
WORLD="/Users/.../my_first_simulation/worlds/my_first_simulation.wbt"
RESULTS="/Users/.../my_first_simulation/results"
N=25

mkdir -p "$RESULTS"

run_treatment() {
    local TREATMENT_NAME=$1
    local GA=$2
    local FUZZER=$3

    echo ""
    echo "========================================"
    echo "  Treatment : $TREATMENT_NAME"
    echo "  USE_GA    : $GA"
    echo "  USE_FUZZER: $FUZZER"
    echo "========================================"

    for i in $(seq 1 $N); do
        SEED=$((1000 + i))
        echo "  Run $i / $N  (seed=$SEED)"

        TREATMENT="$TREATMENT_NAME"    \
        USE_GA="$GA"                   \
        USE_FUZZER="$FUZZER"           \
        RUN_SEED="$SEED"               \
        RUN_INDEX="$i"                 \
        RESULTS_DIR="$RESULTS"         \
        "$WEBOTS" --mode=fast --no-rendering --batch "$WORLD"

        sleep 1
    done

    echo "  Done: $N runs saved for $TREATMENT_NAME"
}

# 4 treatments
run_treatment "baseline"    "0" "0"
run_treatment "baseline2"   "0" "1"
run_treatment "experiment1" "1" "0"
run_treatment "experiment2" "1" "1"

echo ""
echo "ALL DONE. Results in: $RESULTS"
