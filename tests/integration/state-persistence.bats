#!/usr/bin/env bats
#
# Integration tests for state persistence across sessions
# Tests that task state survives restarts and can be resumed
#

load '../setup/helpers.bash'
load '../setup/mocks.bash'

setup() {
    setup_test_env
    setup_claude_mock
}

teardown() {
    teardown_test_env
}

# ============================================================================
# STATE FILE PERSISTENCE
# ============================================================================

@test "state file persists after phase_complete" {
    source_all_libs

    phase_start "0-setup" "Setup"
    phase_complete

    # State file should exist and have completion info
    assert_file_exists "$TEST_TEMP_DIR/.claude/task-state.json"

    local is_complete
    is_complete=$(jq -r '.phases["0-setup"].completed' "$TEST_TEMP_DIR/.claude/task-state.json")

    [[ "$is_complete" == "true" ]]
}

@test "state file can be loaded in new session" {
    source_all_libs

    # Simulate first session
    phase_start "0-setup" "Setup"
    task_state_start "001" "Task 1"
    task_state_complete "001" "Task 1"

    # Capture state file location
    local state_file="$TEST_TEMP_DIR/.claude/task-state.json"

    # Simulate new session by re-sourcing libs
    source_all_libs

    # Initialize for same phase (simulating resume)
    task_state_init "0-setup"

    # Previous task should still be complete
    run task_state_is_complete "001"
    [[ "$status" -eq 0 ]]
}

@test "multiple phases are preserved" {
    source_all_libs

    # Complete phase 0
    task_state_init "0-setup"
    task_state_start "001" "Task 1"
    task_state_complete "001" "Task 1"
    task_state_phase_complete

    # Start phase 1
    task_state_init "1-discovery"
    task_state_start "101" "Task 101"
    task_state_complete "101" "Task 101"

    # Both phases should be in state file
    assert_json_exists "$TEST_TEMP_DIR/.claude/task-state.json" '.phases["0-setup"]'
    assert_json_exists "$TEST_TEMP_DIR/.claude/task-state.json" '.phases["1-discovery"]'
}

# ============================================================================
# RESUME FUNCTIONALITY
# ============================================================================

@test "resume from partial state snapshot" {
    source_all_libs

    # Load partial phase 1 snapshot
    load_state_snapshot "phase-1-partial"

    task_state_init "1-discovery"

    # Tasks 101-103 should be complete
    run task_state_is_complete "101"
    [[ "$status" -eq 0 ]]

    run task_state_is_complete "102"
    [[ "$status" -eq 0 ]]

    run task_state_is_complete "103"
    [[ "$status" -eq 0 ]]

    # Task 104 should not be complete (was in_progress)
    run task_state_is_complete "104"
    [[ "$status" -eq 1 ]]
}

@test "resume skips completed tasks" {
    source_all_libs

    # Load partial state
    load_state_snapshot "phase-1-partial"

    task_state_init "1-discovery"

    # Export for subshell in 'run'
    export TASK_STATE_FILE
    export ATOMIC_ROOT

    # Should skip 101, 102, 103
    run task_state_should_skip "101"
    [[ "$status" -eq 0 ]]

    run task_state_should_skip "102"
    [[ "$status" -eq 0 ]]

    run task_state_should_skip "103"
    [[ "$status" -eq 0 ]]

    # Should NOT skip 104 (was in_progress)
    run task_state_should_skip "104"
    [[ "$status" -eq 1 ]]
}

@test "force redo overrides completion status" {
    source_all_libs

    # Load complete phase 0
    load_state_snapshot "phase-0-complete"

    task_state_init "0-setup"

    # Set redo flag
    TASK_FORCE_REDO="true"

    # Should NOT skip even though complete
    run task_state_should_skip "001"
    [[ "$status" -eq 1 ]]

    unset TASK_FORCE_REDO
}

# ============================================================================
# RESET FUNCTIONALITY
# ============================================================================

@test "reset from task clears subsequent tasks" {
    source_all_libs

    load_state_snapshot "phase-0-complete"
    task_state_init "0-setup"

    # Reset from task 005
    task_state_reset_from "005"

    # Tasks 001-004 should still be complete
    run task_state_is_complete "001"
    [[ "$status" -eq 0 ]]

    run task_state_is_complete "004"
    [[ "$status" -eq 0 ]]

    # Tasks 005+ should be reset
    run task_state_is_complete "005"
    [[ "$status" -eq 1 ]]

    run task_state_is_complete "008"
    [[ "$status" -eq 1 ]]
}

@test "clear phase removes all task state" {
    source_all_libs

    load_state_snapshot "phase-0-complete"
    task_state_init "0-setup"

    task_state_clear_phase

    # All tasks should now be incomplete
    run task_state_is_complete "001"
    [[ "$status" -eq 1 ]]

    run task_state_is_complete "008"
    [[ "$status" -eq 1 ]]
}

# ============================================================================
# OUTPUT ARTIFACTS
# ============================================================================

@test "artifacts are tracked in task state" {
    source_all_libs

    task_state_init "0-setup"
    task_state_start "001" "Task 1"

    # Create some artifacts
    echo "test" > "$TEST_TEMP_DIR/artifact1.json"
    echo "test" > "$TEST_TEMP_DIR/artifact2.md"

    task_state_complete "001" "Task 1" \
        "$TEST_TEMP_DIR/artifact1.json" \
        "$TEST_TEMP_DIR/artifact2.md"

    # Artifacts should be recorded
    local artifact_count
    artifact_count=$(jq '.phases["0-setup"].tasks["001"].artifacts | length' \
        "$TEST_TEMP_DIR/.claude/task-state.json")

    [[ "$artifact_count" -eq 2 ]]
}

# ============================================================================
# CONCURRENT SAFETY (basic)
# ============================================================================

@test "state updates are atomic" {
    source_all_libs

    task_state_init "0-setup"

    # Rapid sequential updates
    for i in {1..5}; do
        task_state_start "00$i" "Task $i"
        task_state_complete "00$i" "Task $i"
    done

    # All tasks should be recorded
    local task_count
    task_count=$(jq '.phases["0-setup"].tasks | length' \
        "$TEST_TEMP_DIR/.claude/task-state.json")

    [[ "$task_count" -eq 5 ]]
}

# ============================================================================
# CONTEXT PERSISTENCE
# ============================================================================

@test "context decisions persist" {
    source_all_libs

    phase_start "0-setup" "Setup"

    atomic_context_decision "Decision 1" "category1"
    atomic_context_decision "Decision 2" "category2"

    # Decisions should be in file
    local decisions_file="$ATOMIC_OUTPUT_DIR/0-setup/context/decisions.json"
    assert_file_exists "$decisions_file"

    local count
    count=$(jq '. | length' "$decisions_file")

    [[ "$count" -ge 2 ]]
}

@test "context artifacts persist" {
    source_all_libs

    phase_start "0-setup" "Setup"

    echo "content" > "$TEST_TEMP_DIR/test-artifact.json"
    atomic_context_artifact "$TEST_TEMP_DIR/test-artifact.json" "Test artifact" "output"

    # Artifact should be indexed
    local artifacts_file="$ATOMIC_OUTPUT_DIR/0-setup/context/artifacts.json"
    assert_file_exists "$artifacts_file"

    local count
    count=$(jq '.artifacts | length' "$artifacts_file")

    [[ "$count" -ge 1 ]]
}
