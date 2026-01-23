#!/usr/bin/env bats
#
# Unit tests for lib/task-state.sh
# Tests task state tracking, persistence, and navigation
#

load '../setup/helpers.bash'
load '../setup/mocks.bash'

setup() {
    setup_test_env
    source_lib "atomic.sh"
    source_lib "task-state.sh"
}

teardown() {
    teardown_test_env
}

# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

@test "task_state_init creates state file" {
    task_state_init "1-discovery"

    assert_file_exists "$TEST_TEMP_DIR/.claude/task-state.json"
}

@test "task_state_init creates phase entry" {
    task_state_init "1-discovery"

    assert_json_exists "$TASK_STATE_FILE" '.phases["1-discovery"]'
}

@test "task_state_init sets current_phase" {
    task_state_init "1-discovery"

    assert_json_equals "$TASK_STATE_FILE" ".current_phase" "1-discovery"
}

@test "task_state_init preserves existing phases" {
    task_state_init "0-setup"
    task_state_complete "001" "First task"

    task_state_init "1-discovery"

    # Old phase should still exist
    assert_json_exists "$TASK_STATE_FILE" '.phases["0-setup"]'
}

# ============================================================================
# TASK LIFECYCLE TESTS
# ============================================================================

@test "task_state_start marks task in_progress" {
    task_state_init "1-discovery"
    task_state_start "101" "Entry Validation"

    local status
    status=$(jq -r '.phases["1-discovery"].tasks["101"].status' "$TASK_STATE_FILE")

    [[ "$status" == "in_progress" ]]
}

@test "task_state_start records task name" {
    task_state_init "1-discovery"
    task_state_start "101" "Entry Validation"

    local name
    name=$(jq -r '.phases["1-discovery"].tasks["101"].name' "$TASK_STATE_FILE")

    [[ "$name" == "Entry Validation" ]]
}

@test "task_state_complete marks task complete" {
    task_state_init "1-discovery"
    task_state_start "101" "Entry Validation"
    task_state_complete "101" "Entry Validation"

    local status
    status=$(jq -r '.phases["1-discovery"].tasks["101"].status' "$TASK_STATE_FILE")

    [[ "$status" == "complete" ]]
}

@test "task_state_complete records artifacts" {
    task_state_init "1-discovery"
    task_state_start "101" "Entry Validation"
    task_state_complete "101" "Entry Validation" "artifact1.json" "artifact2.md"

    local artifact_count
    artifact_count=$(jq '.phases["1-discovery"].tasks["101"].artifacts | length' "$TASK_STATE_FILE")

    [[ "$artifact_count" -eq 2 ]]
}

@test "task_state_fail marks task failed" {
    task_state_init "1-discovery"
    task_state_start "101" "Entry Validation"
    task_state_fail "101" "Something went wrong"

    local status
    status=$(jq -r '.phases["1-discovery"].tasks["101"].status' "$TASK_STATE_FILE")

    [[ "$status" == "failed" ]]
}

@test "task_state_fail records error message" {
    task_state_init "1-discovery"
    task_state_start "101" "Entry Validation"
    task_state_fail "101" "Something went wrong"

    local error
    error=$(jq -r '.phases["1-discovery"].tasks["101"].error' "$TASK_STATE_FILE")

    [[ "$error" == "Something went wrong" ]]
}

# ============================================================================
# QUERY TESTS
# ============================================================================

@test "task_state_is_complete returns true for complete task" {
    task_state_init "1-discovery"
    task_state_start "101" "Entry Validation"
    task_state_complete "101" "Entry Validation"

    run task_state_is_complete "101"
    [[ "$status" -eq 0 ]]
}

@test "task_state_is_complete returns false for incomplete task" {
    task_state_init "1-discovery"
    task_state_start "101" "Entry Validation"

    run task_state_is_complete "101"
    [[ "$status" -eq 1 ]]
}

@test "task_state_is_complete returns false for nonexistent task" {
    task_state_init "1-discovery"

    run task_state_is_complete "999"
    [[ "$status" -eq 1 ]]
}

@test "task_state_get_last_complete returns last completed task" {
    task_state_init "1-discovery"

    task_state_start "101" "Task 1"
    task_state_complete "101" "Task 1"

    task_state_start "102" "Task 2"
    task_state_complete "102" "Task 2"

    local last
    last=$(task_state_get_last_complete)

    [[ "$last" == "102" ]]
}

# ============================================================================
# SKIP LOGIC TESTS
# ============================================================================

@test "task_state_should_skip returns true for complete task" {
    task_state_init "1-discovery"
    task_state_start "101" "Task 1"
    task_state_complete "101" "Task 1"

    run task_state_should_skip "101"
    [[ "$status" -eq 0 ]]
}

@test "task_state_should_skip returns false for incomplete task" {
    task_state_init "1-discovery"

    run task_state_should_skip "101"
    [[ "$status" -eq 1 ]]
}

@test "task_state_should_skip respects TASK_FORCE_REDO" {
    task_state_init "1-discovery"
    task_state_start "101" "Task 1"
    task_state_complete "101" "Task 1"

    TASK_FORCE_REDO="true"

    run task_state_should_skip "101"
    [[ "$status" -eq 1 ]]  # Should NOT skip

    unset TASK_FORCE_REDO
}

@test "task_state_should_skip respects TASK_RESUME_AT" {
    task_state_init "1-discovery"
    task_state_start "101" "Task 1"
    task_state_complete "101" "Task 1"

    TASK_RESUME_AT="103"

    # Should skip until we reach 103
    run task_state_should_skip "101"
    [[ "$status" -eq 0 ]]  # Skip

    run task_state_should_skip "102"
    [[ "$status" -eq 0 ]]  # Skip

    run task_state_should_skip "103"
    [[ "$status" -eq 1 ]]  # Don't skip - this is the target

    unset TASK_RESUME_AT
}

# ============================================================================
# NAVIGATION TESTS
# ============================================================================

@test "task_state_reset_from resets tasks from specified point" {
    task_state_init "1-discovery"

    task_state_start "101" "Task 1"
    task_state_complete "101" "Task 1"
    task_state_start "102" "Task 2"
    task_state_complete "102" "Task 2"
    task_state_start "103" "Task 3"
    task_state_complete "103" "Task 3"

    task_state_reset_from "102"

    # 101 should still be complete
    run task_state_is_complete "101"
    [[ "$status" -eq 0 ]]

    # 102 and 103 should be reset
    run task_state_is_complete "102"
    [[ "$status" -eq 1 ]]

    run task_state_is_complete "103"
    [[ "$status" -eq 1 ]]
}

@test "task_state_clear_phase clears all tasks" {
    task_state_init "1-discovery"

    task_state_start "101" "Task 1"
    task_state_complete "101" "Task 1"
    task_state_start "102" "Task 2"
    task_state_complete "102" "Task 2"

    task_state_clear_phase

    local task_count
    task_count=$(jq '.phases["1-discovery"].tasks | length' "$TASK_STATE_FILE")

    [[ "$task_count" -eq 0 ]]
}

@test "task_state_phase_complete marks phase as complete" {
    task_state_init "1-discovery"
    task_state_phase_complete

    local is_complete
    is_complete=$(jq -r '.phases["1-discovery"].completed' "$TASK_STATE_FILE")

    [[ "$is_complete" == "true" ]]
}

# ============================================================================
# ARGUMENT PARSING TESTS
# ============================================================================

@test "task_state_parse_args sets TASK_RESUME_AT" {
    task_state_parse_args --resume-at 105

    [[ "$TASK_RESUME_AT" == "105" ]]
}

@test "task_state_parse_args sets TASK_FORCE_REDO" {
    task_state_parse_args --redo

    [[ "$TASK_FORCE_REDO" == "true" ]]
}

@test "task_state_parse_args handles equals syntax" {
    task_state_parse_args --resume-at=107

    [[ "$TASK_RESUME_AT" == "107" ]]
}

# ============================================================================
# CROSS-PHASE RESET TESTS
# ============================================================================

@test "task_state_pipeline_reset resets from specific task" {
    # Initialize multiple phases
    task_state_init "1-discovery"
    task_state_start "101" "Task 1"
    task_state_complete "101" "Task 1"
    task_state_start "102" "Task 2"
    task_state_complete "102" "Task 2"
    task_state_phase_complete

    task_state_init "2-prd"
    task_state_start "201" "Task 1"
    task_state_complete "201" "Task 1"

    # Reset from task 102 in phase 1
    task_state_pipeline_reset "102"

    # Phase 1 task 101 should still be complete
    task_state_init "1-discovery"
    run task_state_is_complete "101"
    [[ "$status" -eq 0 ]]

    # Phase 1 task 102 should be reset
    run task_state_is_complete "102"
    [[ "$status" -eq 1 ]]
}

# ============================================================================
# STATUS DISPLAY TESTS
# ============================================================================

@test "task_state_show produces output" {
    task_state_init "1-discovery"
    task_state_start "101" "Task 1"
    task_state_complete "101" "Task 1"

    run task_state_show

    [[ "$status" -eq 0 ]]
    assert_contains "$output" "1-discovery"
}

@test "task_state_pipeline_status produces output" {
    task_state_init "1-discovery"
    task_state_start "101" "Task 1"
    task_state_complete "101" "Task 1"

    run task_state_pipeline_status

    [[ "$status" -eq 0 ]]
    assert_contains "$output" "PIPELINE STATE"
}
