#!/usr/bin/env bats
#
# Unit tests for lib/phase.sh
# Tests phase lifecycle management and task orchestration
#

load '../setup/helpers.bash'
load '../setup/mocks.bash'

setup() {
    setup_test_env
    setup_claude_mock
    source_all_libs
}

teardown() {
    teardown_test_env
}

# ============================================================================
# PHASE LIFECYCLE TESTS
# ============================================================================

@test "phase_start sets CURRENT_PHASE" {
    phase_start "1-discovery" "Discovery"

    [[ "$CURRENT_PHASE" == "1-discovery" ]]
}

@test "phase_start sets CURRENT_PHASE_NAME" {
    phase_start "1-discovery" "Discovery"

    [[ "$CURRENT_PHASE_NAME" == "Discovery" ]]
}

@test "phase_start creates output directory" {
    phase_start "1-discovery" "Discovery"

    assert_dir_exists "$ATOMIC_OUTPUT_DIR/1-discovery"
}

@test "phase_start initializes task state" {
    phase_start "1-discovery" "Discovery"

    assert_file_exists "$TEST_TEMP_DIR/.claude/task-state.json"
    assert_json_equals "$TEST_TEMP_DIR/.claude/task-state.json" ".current_phase" "1-discovery"
}

@test "phase_start initializes context" {
    phase_start "1-discovery" "Discovery"

    assert_dir_exists "$ATOMIC_OUTPUT_DIR/1-discovery/context"
}

@test "phase_complete creates closeout file" {
    phase_start "1-discovery" "Discovery"
    phase_complete

    assert_file_exists "$ATOMIC_OUTPUT_DIR/1-discovery/closeout.json"
}

@test "phase_complete closeout has required fields" {
    phase_start "1-discovery" "Discovery"
    phase_complete

    local closeout_file="$ATOMIC_OUTPUT_DIR/1-discovery/closeout.json"

    assert_json_exists "$closeout_file" ".phase_id"
    assert_json_exists "$closeout_file" ".phase_name"
    assert_json_exists "$closeout_file" ".status"
    assert_json_exists "$closeout_file" ".completed_at"
}

@test "phase_complete marks status as complete" {
    phase_start "1-discovery" "Discovery"
    phase_complete

    local closeout_file="$ATOMIC_OUTPUT_DIR/1-discovery/closeout.json"
    assert_json_equals "$closeout_file" ".status" "complete"
}

# ============================================================================
# PHASE TASK TESTS
# ============================================================================

@test "phase_task executes task function" {
    phase_start "1-discovery" "Discovery"

    task_executed=false
    test_task() {
        task_executed=true
        return 0
    }

    phase_task "101" "Test Task" test_task

    [[ "$task_executed" == "true" ]]
}

@test "phase_task increments PHASE_TASKS_RUN" {
    phase_start "1-discovery" "Discovery"

    test_task() { return 0; }

    phase_task "101" "Test Task 1" test_task
    phase_task "102" "Test Task 2" test_task

    [[ "$PHASE_TASKS_RUN" -eq 2 ]]
}

@test "phase_task returns 0 on success" {
    phase_start "1-discovery" "Discovery"

    success_task() { return 0; }

    run phase_task "101" "Success Task" success_task
    [[ "$status" -eq 0 ]]
}

@test "phase_task returns 1 on failure" {
    phase_start "1-discovery" "Discovery"

    fail_task() { return 1; }

    run phase_task "101" "Fail Task" fail_task
    [[ "$status" -eq 1 ]]
}

# ============================================================================
# CHECKPOINT TESTS
# ============================================================================

@test "phase_checkpoint creates checkpoint file" {
    phase_start "1-discovery" "Discovery"

    phase_checkpoint "test_checkpoint" '{"key": "value"}'

    assert_file_exists "$ATOMIC_OUTPUT_DIR/1-discovery/checkpoints.json"
}

@test "phase_checkpoint records checkpoint data" {
    phase_start "1-discovery" "Discovery"

    phase_checkpoint "test_checkpoint" '{"key": "value"}'

    local checkpoint_file="$ATOMIC_OUTPUT_DIR/1-discovery/checkpoints.json"
    local count
    count=$(jq '.checkpoints | length' "$checkpoint_file")

    [[ "$count" -ge 1 ]]
}

# ============================================================================
# PHASE DETERMINISTIC TESTS
# ============================================================================

@test "phase_deterministic runs command successfully" {
    phase_start "1-discovery" "Discovery"

    run phase_deterministic "Test deterministic" true
    [[ "$status" -eq 0 ]]
}

@test "phase_deterministic fails on command failure" {
    phase_start "1-discovery" "Discovery"

    run phase_deterministic "Test deterministic fail" false
    [[ "$status" -eq 1 ]]
}

# ============================================================================
# PHASE TRANSITION TESTS
# ============================================================================

@test "phase_transition_banner produces output" {
    run phase_transition_banner "1" "2" "PRD"
    [[ "$status" -eq 0 ]]
    assert_contains "$output" "PHASE TRANSITION"
}

# ============================================================================
# EXIT CODE CONSTANTS TESTS
# ============================================================================

@test "TASK_CONTINUE is defined as 0" {
    [[ "$TASK_CONTINUE" -eq 0 ]]
}

@test "TASK_BACK is defined as 100" {
    [[ "$TASK_BACK" -eq 100 ]]
}

@test "TASK_QUIT is defined as 101" {
    [[ "$TASK_QUIT" -eq 101 ]]
}

# ============================================================================
# PHASE RUN TASKS TESTS
# ============================================================================

@test "phase_run_tasks extracts task IDs from function names" {
    phase_start "1-discovery" "Discovery"

    # Create simple task functions
    task_101_entry() { return 0; }
    task_102_corpus() { return 0; }

    # Mock the interactive wrapper to just run tasks
    phase_task_interactive() {
        local task_id="$1"
        local task_name="$2"
        local task_func="$3"
        $task_func
        return $TASK_CONTINUE
    }

    run phase_run_tasks task_101_entry task_102_corpus
    [[ "$status" -eq 0 ]]
}

# ============================================================================
# LLM TASK TESTS
# ============================================================================

@test "phase_llm_task invokes with correct output path" {
    phase_start "1-discovery" "Discovery"
    set_mock_response '{"result": "test"}'

    # Create a simple prompt file
    echo "Test prompt" > "$TEST_TEMP_DIR/prompt.md"

    run phase_llm_task "Test LLM Task" "$TEST_TEMP_DIR/prompt.md" "output.json"

    # Output should be created in phase directory
    assert_file_exists "$ATOMIC_OUTPUT_DIR/1-discovery/output.json"
}

# ============================================================================
# HUMAN GATE TESTS
# ============================================================================

@test "phase_human_gate produces output" {
    phase_start "1-discovery" "Discovery"

    # Can't fully test interactive function, but check it doesn't crash
    # when given piped input
    echo "approve" | run phase_human_gate "Test gate message"

    # Should mention approval required
    assert_contains "$output" "HUMAN"
}

# ============================================================================
# REVIEW TESTS
# ============================================================================

@test "phase_review displays file content" {
    phase_start "1-discovery" "Discovery"

    echo "Review content here" > "$TEST_TEMP_DIR/review.md"

    echo "" | run phase_review "$TEST_TEMP_DIR/review.md" "Test Review"

    assert_contains "$output" "Review content here"
}

@test "phase_review handles missing file" {
    phase_start "1-discovery" "Discovery"

    echo "" | run phase_review "/nonexistent/file.md" "Test Review"

    assert_contains "$output" "not found"
}

# ============================================================================
# VERIFICATION TESTS
# ============================================================================

@test "phase_verify runs verification script" {
    phase_start "1-discovery" "Discovery"

    # Create a passing verification script
    cat > "$TEST_TEMP_DIR/verify.sh" << 'EOF'
#!/bin/bash
exit 0
EOF
    chmod +x "$TEST_TEMP_DIR/verify.sh"

    run phase_verify "$TEST_TEMP_DIR/verify.sh"
    [[ "$status" -eq 0 ]]
}

@test "phase_verify fails on script failure" {
    phase_start "1-discovery" "Discovery"

    # Create a failing verification script
    cat > "$TEST_TEMP_DIR/verify.sh" << 'EOF'
#!/bin/bash
exit 1
EOF
    chmod +x "$TEST_TEMP_DIR/verify.sh"

    run phase_verify "$TEST_TEMP_DIR/verify.sh"
    [[ "$status" -eq 1 ]]
}

@test "phase_verify skips if no script found" {
    phase_start "1-discovery" "Discovery"

    run phase_verify "/nonexistent/verify.sh"
    [[ "$status" -eq 0 ]]  # Should pass (skip)
}
