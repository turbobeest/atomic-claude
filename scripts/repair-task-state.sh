#!/usr/bin/env bash
# Repair task state by inferring from outputs and closeouts

set -euo pipefail

ATOMIC_ROOT="${ATOMIC_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUTPUTS_DIR="$ATOMIC_ROOT/.outputs"
TASK_STATE="$ATOMIC_ROOT/.claude/task-state.json"

echo "Repairing task state from outputs..."

# Check which phases have closeouts
phases_completed=()
for phase_dir in "$OUTPUTS_DIR"/*; do
    if [[ -d "$phase_dir" && -f "$phase_dir/closeout.md" ]]; then
        phase_id=$(basename "$phase_dir")
        phases_completed+=("$phase_id")
        echo "  Found completed phase: $phase_id"
    fi
done

# Read current task state
current_state=$(cat "$TASK_STATE")
current_phase=$(echo "$current_state" | jq -r '.current_phase // "null"')

# For each completed phase, add stub tasks if not present
for phase_id in "${phases_completed[@]}"; do
    # Check if phase exists in task state
    if ! echo "$current_state" | jq -e ".phases[\"$phase_id\"]" > /dev/null 2>&1; then
        echo "  Adding phase $phase_id to task state..."
        
        # Infer task count from phase (setup=9, discovery=10, prd=10, etc.)
        case "$phase_id" in
            0-setup) task_count=9 ;;
            1-discovery) task_count=10 ;;
            2-prd) task_count=10 ;;
            *) task_count=6 ;;
        esac
        
        # Build tasks object
        tasks_json="{"
        phase_num="${phase_id%%-*}"
        for ((i=1; i<=task_count; i++)); do
            task_id=$(printf "%d%02d" "$phase_num" "$i")
            tasks_json+="\"$task_id\":{\"name\":\"Task $task_id\",\"status\":\"complete\",\"started_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"completed_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"artifacts\":[]}"
            [[ $i -lt $task_count ]] && tasks_json+=","
        done
        tasks_json+="}"
        
        # Add phase to state
        current_state=$(echo "$current_state" | jq ".phases[\"$phase_id\"] = {
            \"started_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
            \"tasks\": $tasks_json,
            \"completed\": true
        }")
    fi
done

# Write updated state
echo "$current_state" | jq '.' > "$TASK_STATE"
echo "✅ Task state repaired"
