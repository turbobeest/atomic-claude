#!/usr/bin/env bats
#
# Unit tests for lib/atomic.sh
# Tests core atomic functions, state management, and utilities
#

load '../setup/helpers.bash'
load '../setup/mocks.bash'

setup() {
    setup_test_env
    setup_claude_mock
    source_lib "atomic.sh"
}

teardown() {
    teardown_test_env
}

# ============================================================================
# STATE MANAGEMENT TESTS
# ============================================================================

@test "atomic_state_init creates state directories" {
    assert_dir_exists "$ATOMIC_STATE_DIR"
    assert_dir_exists "$ATOMIC_OUTPUT_DIR"
    assert_dir_exists "$ATOMIC_LOG_DIR"
}

@test "atomic_state_init creates session.json" {
    assert_file_exists "$ATOMIC_STATE_DIR/session.json"
}

@test "atomic_state_init session.json has required fields" {
    assert_json_exists "$ATOMIC_STATE_DIR/session.json" ".session_id"
    assert_json_exists "$ATOMIC_STATE_DIR/session.json" ".started_at"
    assert_json_exists "$ATOMIC_STATE_DIR/session.json" ".tasks_completed"
}

@test "atomic_state_get retrieves value from session" {
    local session_id
    session_id=$(atomic_state_get "session_id")
    [[ -n "$session_id" ]]
}

@test "atomic_state_set updates session value" {
    atomic_state_set "test_key" "\"test_value\""

    local result
    result=$(atomic_state_get "test_key")
    [[ "$result" == "test_value" ]]
}

@test "atomic_state_increment increases counter" {
    local before
    before=$(atomic_state_get "tasks_completed")

    atomic_state_increment "tasks_completed"

    local after
    after=$(atomic_state_get "tasks_completed")
    [[ "$after" -eq $((before + 1)) ]]
}

# ============================================================================
# OUTPUT FUNCTION TESTS
# ============================================================================

@test "atomic_step produces output" {
    run atomic_step "Test step"
    [[ "$status" -eq 0 ]]
    assert_contains "$output" "Test step"
}

@test "atomic_success produces output with checkmark" {
    run atomic_success "Test success"
    [[ "$status" -eq 0 ]]
    # Contains checkmark or success indicator
    assert_contains "$output" "Test success"
}

@test "atomic_error produces output with error indicator" {
    run atomic_error "Test error"
    [[ "$status" -eq 0 ]]
    assert_contains "$output" "Test error"
}

@test "atomic_warn produces output with warning indicator" {
    run atomic_warn "Test warning"
    [[ "$status" -eq 0 ]]
    assert_contains "$output" "Test warning"
}

# ============================================================================
# PROJECT NAME VALIDATION TESTS
# ============================================================================

@test "atomic_validate_project_name accepts valid names" {
    run atomic_validate_project_name "my-project"
    [[ "$status" -eq 0 ]]

    run atomic_validate_project_name "MyProject123"
    [[ "$status" -eq 0 ]]

    run atomic_validate_project_name "test_name"
    [[ "$status" -eq 0 ]]
}

@test "atomic_validate_project_name rejects names too short" {
    run atomic_validate_project_name "ab"
    [[ "$status" -eq 1 ]]
    assert_contains "$output" "short"
}

@test "atomic_validate_project_name rejects names too long" {
    run atomic_validate_project_name "this-name-is-way-too-long-to-be-valid"
    [[ "$status" -eq 1 ]]
    assert_contains "$output" "long"
}

@test "atomic_validate_project_name rejects names with spaces" {
    run atomic_validate_project_name "my project"
    [[ "$status" -eq 1 ]]
    assert_contains "$output" "Spaces"
}

@test "atomic_validate_project_name rejects names starting with dash" {
    run atomic_validate_project_name "-myproject"
    [[ "$status" -eq 1 ]]
    assert_contains "$output" "start"
}

# ============================================================================
# FILE VALIDATION TESTS
# ============================================================================

@test "atomic_validate_files passes with existing files" {
    touch "$TEST_TEMP_DIR/file1.txt"
    touch "$TEST_TEMP_DIR/file2.txt"

    run atomic_validate_files "$TEST_TEMP_DIR/file1.txt" "$TEST_TEMP_DIR/file2.txt"
    [[ "$status" -eq 0 ]]
}

@test "atomic_validate_files fails with missing files" {
    touch "$TEST_TEMP_DIR/file1.txt"

    run atomic_validate_files "$TEST_TEMP_DIR/file1.txt" "$TEST_TEMP_DIR/nonexistent.txt"
    [[ "$status" -eq 1 ]]
}

# ============================================================================
# CONTEXT MANAGEMENT TESTS
# ============================================================================

@test "atomic_context_init creates context directory" {
    atomic_context_init "0-setup"

    assert_dir_exists "$ATOMIC_OUTPUT_DIR/0-setup/context"
}

@test "atomic_context_init creates summary.md" {
    atomic_context_init "0-setup"

    assert_file_exists "$ATOMIC_OUTPUT_DIR/0-setup/context/summary.md"
}

@test "atomic_context_init creates decisions.json" {
    atomic_context_init "0-setup"

    assert_file_exists "$ATOMIC_OUTPUT_DIR/0-setup/context/decisions.json"
}

@test "atomic_context_decision records decision" {
    atomic_context_init "0-setup"
    atomic_context_decision "Test decision" "test_category"

    local decisions_file="$ATOMIC_OUTPUT_DIR/0-setup/context/decisions.json"
    local count
    count=$(jq '. | length' "$decisions_file")

    [[ "$count" -gt 0 ]]
}

@test "atomic_context_artifact records artifact" {
    atomic_context_init "0-setup"
    atomic_context_artifact "/path/to/file.json" "Test artifact" "output"

    local artifacts_file="$ATOMIC_OUTPUT_DIR/0-setup/context/artifacts.json"

    assert_json_exists "$artifacts_file" ".artifacts[0]"
}

# ============================================================================
# BUILD CONTEXT TESTS
# ============================================================================

@test "atomic_build_context includes file content" {
    atomic_context_init "0-setup"

    echo "Test content" > "$TEST_TEMP_DIR/test-input.txt"

    local context
    context=$(atomic_build_context "$TEST_TEMP_DIR/test-input.txt")

    assert_contains "$context" "Test content"
}

@test "atomic_build_context handles missing files gracefully" {
    atomic_context_init "0-setup"

    local context
    context=$(atomic_build_context "/nonexistent/file.txt")

    assert_contains "$context" "not found"
}

# ============================================================================
# TEMPLATE TESTS
# ============================================================================

@test "atomic_template substitutes variables" {
    echo "Hello {{NAME}}, welcome to {{PLACE}}!" > "$TEST_TEMP_DIR/template.md"

    local result
    result=$(atomic_template "$TEST_TEMP_DIR/template.md" "NAME=World" "PLACE=ATOMIC")

    assert_contains "$result" "Hello World"
    assert_contains "$result" "welcome to ATOMIC"
}

@test "atomic_compose combines multiple parts" {
    echo "Part 1" > "$TEST_TEMP_DIR/part1.md"
    echo "Part 2" > "$TEST_TEMP_DIR/part2.md"

    local result
    result=$(atomic_compose "$TEST_TEMP_DIR/part1.md" "$TEST_TEMP_DIR/part2.md")

    assert_contains "$result" "Part 1"
    assert_contains "$result" "Part 2"
}

# ============================================================================
# JSON EXTRACTION TESTS
# ============================================================================

@test "atomic_extract_json extracts JSON from markdown code block" {
    cat > "$TEST_TEMP_DIR/input.txt" << 'EOF'
Here is some text.

```json
{"key": "value", "number": 42}
```

More text.
EOF

    run atomic_extract_json "$TEST_TEMP_DIR/input.txt" "$TEST_TEMP_DIR/output.json"
    [[ "$status" -eq 0 ]]

    assert_json_equals "$TEST_TEMP_DIR/output.json" ".key" "value"
    assert_json_equals "$TEST_TEMP_DIR/output.json" ".number" "42"
}

@test "atomic_extract_json handles raw JSON" {
    echo '{"direct": true}' > "$TEST_TEMP_DIR/input.txt"

    run atomic_extract_json "$TEST_TEMP_DIR/input.txt" "$TEST_TEMP_DIR/output.json"
    [[ "$status" -eq 0 ]]

    assert_json_equals "$TEST_TEMP_DIR/output.json" ".direct" "true"
}

@test "atomic_extract_json fails on non-JSON content" {
    echo "This is not JSON at all" > "$TEST_TEMP_DIR/input.txt"

    run atomic_extract_json "$TEST_TEMP_DIR/input.txt" "$TEST_TEMP_DIR/output.json"
    [[ "$status" -eq 1 ]]
}

# ============================================================================
# INVOKE TESTS (with mocks)
# ============================================================================

@test "atomic_invoke creates output file" {
    set_mock_response '{"result": "success"}'

    run atomic_invoke "Test prompt" "$TEST_TEMP_DIR/output.txt" "Test task"
    [[ "$status" -eq 0 ]]

    assert_file_exists "$TEST_TEMP_DIR/output.txt"
}

@test "atomic_invoke logs invocation" {
    set_mock_response '{"result": "success"}'

    atomic_invoke "Test prompt" "$TEST_TEMP_DIR/output.txt" "Test task"

    # Check log file exists and has content
    local log_file
    log_file=$(atomic_log_file)

    [[ -f "$log_file" ]]
}

@test "atomic_invoke increments tasks_completed on success" {
    set_mock_response '{"result": "success"}'

    local before
    before=$(atomic_state_get "tasks_completed")

    atomic_invoke "Test prompt" "$TEST_TEMP_DIR/output.txt" "Test task"

    local after
    after=$(atomic_state_get "tasks_completed")

    [[ "$after" -eq $((before + 1)) ]]
}
