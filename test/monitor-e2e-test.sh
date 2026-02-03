#!/usr/bin/env bash
#
# E2E Test Monitor - Real-time evaluation and feedback
# Run this in a separate terminal while test-e2e-phase0.sh runs
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Script is at ATOMIC-CLAUDE/test/, so ATOMIC_DIR is parent
ATOMIC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="$ATOMIC_DIR/.state"
OUTPUT_DIR="$ATOMIC_DIR/.outputs"
LOG_DIR="$ATOMIC_DIR/.logs"

# Monitoring state
declare -A TASK_START_TIMES
declare -A TASK_DURATIONS
PHASE_START_TIME=""
CURRENT_TASK=""
TASK_COUNT=0
ERROR_COUNT=0
WARNING_COUNT=0
MONITOR_START_TIME=$(date +%s)

clear
echo ""
echo -e "${CYAN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║  E2E Test Monitor - Live Evaluation                       ║${NC}"
echo -e "${CYAN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${DIM}Monitoring: $ATOMIC_DIR${NC}"
echo -e "${DIM}Started: $(date)${NC}"
echo ""

# Function to check task state
get_current_task() {
    if [[ -f "$STATE_DIR/current-task.json" ]]; then
        jq -r '.description // "Unknown"' "$STATE_DIR/current-task.json" 2>/dev/null || echo "Unknown"
    else
        echo "No active task"
    fi
}

# Function to check for errors
check_for_errors() {
    local log_file="${1:-$LOG_DIR/invocations.log}"
    if [[ -f "$log_file" ]]; then
        local new_errors=$(grep -i "error" "$log_file" | tail -5)
        if [[ -n "$new_errors" ]]; then
            echo "$new_errors"
        fi
    fi
}

# Function to display task progress
display_task_progress() {
    local task="$1"
    local elapsed="$2"

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Task:${NC} $task"
    echo -e "${BOLD}Duration:${NC} ${elapsed}s"

    # Check for task state file
    if [[ -f "$STATE_DIR/current-task.json" ]]; then
        local provider=$(jq -r '.provider // "unknown"' "$STATE_DIR/current-task.json" 2>/dev/null || echo "unknown")
        local model=$(jq -r '.model // "unknown"' "$STATE_DIR/current-task.json" 2>/dev/null || echo "unknown")
        local active=$(jq -r '.active // false' "$STATE_DIR/current-task.json" 2>/dev/null || echo "false")

        echo -e "${BOLD}Provider:${NC} $provider"
        echo -e "${BOLD}Model:${NC} $model"
        echo -e "${BOLD}Active:${NC} $active"
    fi

    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to display statistics
display_stats() {
    echo ""
    echo -e "${BOLD}Statistics:${NC}"
    echo -e "  Tasks Monitored: $TASK_COUNT"
    echo -e "  Errors: ${ERROR_COUNT}"
    echo -e "  Warnings: ${WARNING_COUNT}"

    if [[ -n "$PHASE_START_TIME" ]]; then
        local now=$(date +%s)
        local phase_elapsed=$((now - PHASE_START_TIME))
        echo -e "  Phase Duration: ${phase_elapsed}s"
    fi

    echo ""
}

# Function to check UI features
check_ui_features() {
    echo ""
    echo -e "${BOLD}UI Feature Checks:${NC}"

    # Check if dashboard started
    if curl -s --connect-timeout 1 "http://localhost:5173/api/status" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Dashboard running on port 5173"
    else
        echo -e "  ${YELLOW}○${NC} Dashboard not detected"
    fi

    # Check for task state tracking
    if [[ -f "$STATE_DIR/current-task.json" ]]; then
        echo -e "  ${GREEN}✓${NC} Task state tracking active"
    else
        echo -e "  ${RED}✗${NC} No task state file"
    fi

    # Check for output files
    if [[ -d "$OUTPUT_DIR/0-setup" ]]; then
        local file_count=$(ls -1 "$OUTPUT_DIR/0-setup" 2>/dev/null | wc -l)
        echo -e "  ${GREEN}✓${NC} Output directory created ($file_count files)"
    else
        echo -e "  ${YELLOW}○${NC} No outputs yet"
    fi

    # Check navigation prompts
    if [[ -f "$LOG_DIR/invocations.log" ]]; then
        if grep -q "\[c\] Continue" "$LOG_DIR/invocations.log" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Navigation prompts present"
        fi
    fi

    echo ""
}

# Function to evaluate task execution
evaluate_task_execution() {
    local task="$1"
    local duration="$2"

    echo -e "${BOLD}Task Evaluation:${NC}"

    # Performance check
    if [[ $duration -lt 30 ]]; then
        echo -e "  ${GREEN}✓${NC} Performance: Excellent (<30s)"
    elif [[ $duration -lt 60 ]]; then
        echo -e "  ${YELLOW}⚠${NC} Performance: Acceptable (30-60s)"
    else
        echo -e "  ${RED}⚠${NC} Performance: Slow (>60s)"
    fi

    # Check for errors in this task
    local errors=$(check_for_errors)
    if [[ -z "$errors" ]]; then
        echo -e "  ${GREEN}✓${NC} No errors detected"
    else
        echo -e "  ${RED}✗${NC} Errors found:"
        echo "$errors" | while read -r line; do
            echo -e "    ${DIM}$line${NC}"
        done
        ((ERROR_COUNT++))
    fi

    echo ""
}

# Main monitoring loop
echo -e "${YELLOW}Waiting for Phase 0 to start...${NC}"
echo ""

while true; do
    # Check if Phase 0 is running
    if [[ -f "$STATE_DIR/current-task.json" ]]; then
        # Check if state file is fresh (modified after monitor started)
        state_file_mtime=$(stat -f %m "$STATE_DIR/current-task.json" 2>/dev/null || echo "0")

        # Only process if file was modified after monitor started
        if [[ $state_file_mtime -lt $MONITOR_START_TIME ]]; then
            # Stale file from previous run
            sleep 1
            continue
        fi

        if [[ -z "$PHASE_START_TIME" ]]; then
            PHASE_START_TIME=$(date +%s)
            echo -e "${GREEN}✓ Phase 0 started${NC}"
            echo ""
        fi

        # Get current task
        task=$(get_current_task)

        # Detect task change
        if [[ "$task" != "$CURRENT_TASK" && "$task" != "No active task" ]]; then
            # Task changed
            if [[ -n "$CURRENT_TASK" && "$CURRENT_TASK" != "No active task" ]]; then
                # Previous task completed
                task_end_time=$(date +%s)
                task_duration=$((task_end_time - TASK_START_TIMES[$CURRENT_TASK]))
                TASK_DURATIONS[$CURRENT_TASK]=$task_duration

                clear
                echo -e "${GREEN}✓ Task completed: $CURRENT_TASK (${task_duration}s)${NC}"
                evaluate_task_execution "$CURRENT_TASK" "$task_duration"
                sleep 2
            fi

            # New task started
            CURRENT_TASK="$task"
            TASK_START_TIMES[$task]=$(date +%s)
            ((TASK_COUNT++))

            clear
            echo -e "${CYAN}→ New task: $task${NC}"
            echo ""
        fi

        # Display current progress
        if [[ -n "$CURRENT_TASK" && "$CURRENT_TASK" != "No active task" ]]; then
            now=$(date +%s)
            elapsed=$((now - TASK_START_TIMES[$CURRENT_TASK]))

            clear
            display_task_progress "$CURRENT_TASK" "$elapsed"
            check_ui_features
            display_stats
        fi
    else
        # Check if phase completed
        if [[ -f "$OUTPUT_DIR/0-setup/closeout.json" ]]; then
            clear
            echo ""
            echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}${BOLD}║  Phase 0 Completed Successfully                           ║${NC}"
            echo -e "${GREEN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
            echo ""

            display_stats

            echo -e "${BOLD}Task Durations:${NC}"
            for task in "${!TASK_DURATIONS[@]}"; do
                echo -e "  $task: ${TASK_DURATIONS[$task]}s"
            done
            echo ""

            check_ui_features

            echo -e "${BOLD}Final Evaluation:${NC}"
            if [[ $ERROR_COUNT -eq 0 ]]; then
                echo -e "  ${GREEN}✓${NC} All tasks executed cleanly"
            else
                echo -e "  ${YELLOW}⚠${NC} $ERROR_COUNT errors encountered"
            fi
            echo ""

            break
        fi

        # Not started yet
        sleep 1
    fi

    sleep 2
done

echo -e "${DIM}Monitor ended: $(date)${NC}"
echo ""
