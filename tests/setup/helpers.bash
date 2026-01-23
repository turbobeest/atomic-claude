#!/bin/bash
#
# BATS Test Helpers for ATOMIC CLAUDE
# Common utilities for test setup, teardown, and assertions
#

# Test environment
TEST_ROOT="${BATS_TEST_DIRNAME}/.."
PROJECT_ROOT="$(cd "$TEST_ROOT/.." && pwd)"
FIXTURES_DIR="$TEST_ROOT/fixtures"

# Temporary test directory (created per test)
TEST_TEMP_DIR=""

# ============================================================================
# SETUP & TEARDOWN
# ============================================================================

# Create isolated test environment
setup_test_env() {
    TEST_TEMP_DIR=$(mktemp -d)

    # Set ATOMIC paths to temp directory
    export ATOMIC_ROOT="$TEST_TEMP_DIR"
    export ATOMIC_STATE_DIR="$TEST_TEMP_DIR/.state"
    export ATOMIC_OUTPUT_DIR="$TEST_TEMP_DIR/.outputs"
    export ATOMIC_LOG_DIR="$TEST_TEMP_DIR/.logs"

    # Create directories
    mkdir -p "$ATOMIC_STATE_DIR" "$ATOMIC_OUTPUT_DIR" "$ATOMIC_LOG_DIR"
    mkdir -p "$TEST_TEMP_DIR/.claude"

    # Copy lib files for sourcing
    cp -r "$PROJECT_ROOT/lib" "$TEST_TEMP_DIR/"
}

# Clean up test environment
teardown_test_env() {
    if [[ -n "$TEST_TEMP_DIR" ]] && [[ -d "$TEST_TEMP_DIR" ]]; then
        rm -rf "$TEST_TEMP_DIR"
    fi
}

# ============================================================================
# MOCK HELPERS
# ============================================================================

# Setup mock PATH to intercept claude command
setup_claude_mock() {
    local mock_dir="$TEST_TEMP_DIR/mock_bin"
    mkdir -p "$mock_dir"

    # Create mock claude script
    cat > "$mock_dir/claude" << 'MOCK_EOF'
#!/bin/bash
# Mock claude command for testing
# Reads MOCK_RESPONSE_FILE env var to return canned response

if [[ -n "$MOCK_RESPONSE_FILE" ]] && [[ -f "$MOCK_RESPONSE_FILE" ]]; then
    cat "$MOCK_RESPONSE_FILE"
    exit 0
elif [[ -n "$MOCK_RESPONSE" ]]; then
    echo "$MOCK_RESPONSE"
    exit 0
else
    echo "Mock claude: No response configured"
    exit 0
fi
MOCK_EOF
    chmod +x "$mock_dir/claude"

    # Prepend to PATH
    export PATH="$mock_dir:$PATH"
}

# Set mock response from fixture file
set_mock_response_file() {
    local fixture_name="$1"
    export MOCK_RESPONSE_FILE="$FIXTURES_DIR/claude-responses/$fixture_name"
}

# Set mock response from string
set_mock_response() {
    local response="$1"
    export MOCK_RESPONSE="$response"
}

# ============================================================================
# ASSERTIONS
# ============================================================================

# Assert file exists
assert_file_exists() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        echo "Expected file to exist: $file" >&2
        return 1
    fi
}

# Assert file does not exist
assert_file_not_exists() {
    local file="$1"
    if [[ -f "$file" ]]; then
        echo "Expected file to not exist: $file" >&2
        return 1
    fi
}

# Assert directory exists
assert_dir_exists() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        echo "Expected directory to exist: $dir" >&2
        return 1
    fi
}

# Assert string contains substring
assert_contains() {
    local haystack="$1"
    local needle="$2"
    if [[ "$haystack" != *"$needle"* ]]; then
        echo "Expected string to contain: $needle" >&2
        echo "Actual: $haystack" >&2
        return 1
    fi
}

# Assert string does not contain substring
assert_not_contains() {
    local haystack="$1"
    local needle="$2"
    if [[ "$haystack" == *"$needle"* ]]; then
        echo "Expected string to not contain: $needle" >&2
        return 1
    fi
}

# Assert JSON field equals value
assert_json_equals() {
    local file="$1"
    local path="$2"
    local expected="$3"

    local actual
    actual=$(jq -r "$path" "$file" 2>/dev/null)

    if [[ "$actual" != "$expected" ]]; then
        echo "JSON path $path: expected '$expected', got '$actual'" >&2
        return 1
    fi
}

# Assert JSON field exists
assert_json_exists() {
    local file="$1"
    local path="$2"

    local result
    result=$(jq -e "$path" "$file" 2>/dev/null)

    if [[ $? -ne 0 ]]; then
        echo "JSON path $path does not exist in $file" >&2
        return 1
    fi
}

# Assert exit code
assert_exit_code() {
    local expected="$1"
    local actual="$2"

    if [[ "$actual" -ne "$expected" ]]; then
        echo "Expected exit code $expected, got $actual" >&2
        return 1
    fi
}

# Assert output matches regex
assert_output_matches() {
    local output="$1"
    local pattern="$2"

    if [[ ! "$output" =~ $pattern ]]; then
        echo "Output does not match pattern: $pattern" >&2
        echo "Actual output: $output" >&2
        return 1
    fi
}

# ============================================================================
# FIXTURE HELPERS
# ============================================================================

# Copy a fixture file to test temp directory
copy_fixture() {
    local fixture_path="$1"
    local dest_path="${2:-$fixture_path}"

    local src="$FIXTURES_DIR/$fixture_path"
    local dst="$TEST_TEMP_DIR/$dest_path"

    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
}

# Load a state snapshot fixture
load_state_snapshot() {
    local snapshot_name="$1"

    local src="$FIXTURES_DIR/state-snapshots/$snapshot_name"

    if [[ -f "$src/task-state.json" ]]; then
        mkdir -p "$TEST_TEMP_DIR/.claude"
        cp "$src/task-state.json" "$TEST_TEMP_DIR/.claude/"
    fi

    if [[ -f "$src/session.json" ]]; then
        mkdir -p "$TEST_TEMP_DIR/.state"
        cp "$src/session.json" "$TEST_TEMP_DIR/.state/"
    fi
}

# ============================================================================
# SOURCE HELPERS
# ============================================================================

# Source a lib file in test context
source_lib() {
    local lib_name="$1"
    source "$TEST_TEMP_DIR/lib/$lib_name"
}

# Source all libs
source_all_libs() {
    source_lib "atomic.sh"
    source_lib "task-state.sh"
    source_lib "phase.sh"
}
