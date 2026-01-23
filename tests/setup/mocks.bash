#!/bin/bash
#
# Mock implementations for ATOMIC CLAUDE testing
# Provides mock versions of external commands and services
#

# ============================================================================
# CLAUDE MOCK
# ============================================================================

# Mock registry - maps prompt patterns to response files
declare -A CLAUDE_MOCK_RESPONSES

# Register a mock response for a prompt pattern
register_mock_response() {
    local pattern="$1"
    local response_file="$2"
    CLAUDE_MOCK_RESPONSES["$pattern"]="$response_file"
}

# Find matching mock response for a prompt
find_mock_response() {
    local prompt="$1"

    for pattern in "${!CLAUDE_MOCK_RESPONSES[@]}"; do
        if [[ "$prompt" == *"$pattern"* ]]; then
            echo "${CLAUDE_MOCK_RESPONSES[$pattern]}"
            return 0
        fi
    done

    return 1
}

# Create the claude mock script with pattern matching
create_smart_claude_mock() {
    local mock_dir="$TEST_TEMP_DIR/mock_bin"
    mkdir -p "$mock_dir"

    # Export mock registry for use in mock script
    export MOCK_REGISTRY_FILE="$TEST_TEMP_DIR/.mock_registry"

    # Save registry to file (can't export associative arrays)
    {
        for pattern in "${!CLAUDE_MOCK_RESPONSES[@]}"; do
            echo "$pattern|${CLAUDE_MOCK_RESPONSES[$pattern]}"
        done
    } > "$MOCK_REGISTRY_FILE"

    cat > "$mock_dir/claude" << 'MOCK_SCRIPT'
#!/bin/bash
# Smart mock claude command - matches prompts to responses

prompt=""
model=""
output_to_stdout=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -p)
            prompt="$2"
            shift 2
            ;;
        --model)
            model="$2"
            shift 2
            ;;
        --dangerously-skip-permissions)
            shift
            ;;
        -o|--output)
            output_to_stdout=false
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Check for direct response override
if [[ -n "$MOCK_RESPONSE" ]]; then
    echo "$MOCK_RESPONSE"
    exit 0
fi

if [[ -n "$MOCK_RESPONSE_FILE" ]] && [[ -f "$MOCK_RESPONSE_FILE" ]]; then
    cat "$MOCK_RESPONSE_FILE"
    exit 0
fi

# Search mock registry for matching pattern
if [[ -f "$MOCK_REGISTRY_FILE" ]]; then
    while IFS='|' read -r pattern response_file; do
        if [[ "$prompt" == *"$pattern"* ]]; then
            if [[ -f "$response_file" ]]; then
                cat "$response_file"
                exit 0
            fi
        fi
    done < "$MOCK_REGISTRY_FILE"
fi

# Default response
echo '{"status": "mock", "message": "No matching mock response found"}'
exit 0
MOCK_SCRIPT

    chmod +x "$mock_dir/claude"
    export PATH="$mock_dir:$PATH"
}

# ============================================================================
# JQ MOCK (for systems without jq)
# ============================================================================

# Check if jq is available
check_jq() {
    if ! command -v jq &> /dev/null; then
        skip "jq is required for this test"
    fi
}

# ============================================================================
# TIMEOUT MOCK
# ============================================================================

# Mock timeout command to avoid actual timeouts in tests
mock_timeout() {
    local mock_dir="$TEST_TEMP_DIR/mock_bin"
    mkdir -p "$mock_dir"

    cat > "$mock_dir/timeout" << 'TIMEOUT_MOCK'
#!/bin/bash
# Mock timeout - just run the command without timeout
shift  # Remove timeout argument
exec "$@"
TIMEOUT_MOCK

    chmod +x "$mock_dir/timeout"
}

# ============================================================================
# DATE MOCK (for deterministic timestamps)
# ============================================================================

# Mock date to return predictable values
mock_date() {
    local mock_dir="$TEST_TEMP_DIR/mock_bin"
    local fixed_date="${1:-2025-01-22T12:00:00}"

    mkdir -p "$mock_dir"

    cat > "$mock_dir/date" << DATE_MOCK
#!/bin/bash
# Mock date command for deterministic testing

if [[ "\$*" == *"-Iseconds"* ]]; then
    echo "$fixed_date"
elif [[ "\$*" == *"+%s"* ]]; then
    echo "1737550800"  # Fixed epoch
elif [[ "\$*" == *"+%Y%m%d"* ]]; then
    echo "20250122"
elif [[ "\$*" == *"+%Y-%m-%d"* ]]; then
    echo "2025-01-22"
else
    /bin/date "\$@"
fi
DATE_MOCK

    chmod +x "$mock_dir/date"
}

# ============================================================================
# READ MOCK (for stdin testing)
# ============================================================================

# Queue input for interactive prompts
MOCK_INPUT_QUEUE=()

queue_input() {
    MOCK_INPUT_QUEUE+=("$1")
}

# Mock read to use queued input
mock_read() {
    local mock_dir="$TEST_TEMP_DIR/mock_bin"
    mkdir -p "$mock_dir"

    # Create input file from queue
    export MOCK_INPUT_FILE="$TEST_TEMP_DIR/.mock_input"
    printf '%s\n' "${MOCK_INPUT_QUEUE[@]}" > "$MOCK_INPUT_FILE"
}

# ============================================================================
# GIT MOCK
# ============================================================================

# Mock git for isolated testing
mock_git() {
    local mock_dir="$TEST_TEMP_DIR/mock_bin"
    mkdir -p "$mock_dir"

    cat > "$mock_dir/git" << 'GIT_MOCK'
#!/bin/bash
# Mock git command

case "$1" in
    status)
        echo "On branch main"
        echo "nothing to commit, working tree clean"
        ;;
    tag)
        echo "mock-tag-v1.0.0"
        ;;
    rev-parse)
        if [[ "$2" == "--show-toplevel" ]]; then
            echo "$ATOMIC_ROOT"
        else
            echo "abc123def"
        fi
        ;;
    *)
        echo "git mock: $*"
        ;;
esac

exit 0
GIT_MOCK

    chmod +x "$mock_dir/git"
}

# ============================================================================
# FUNCTION MOCKS
# ============================================================================

# Create a spy function that records calls
create_spy() {
    local func_name="$1"
    local spy_log="$TEST_TEMP_DIR/.spy_$func_name"

    eval "
    $func_name() {
        echo \"\$*\" >> \"$spy_log\"
        return 0
    }
    "

    # Create empty spy log
    : > "$spy_log"
}

# Check if spy was called with specific args
spy_was_called_with() {
    local func_name="$1"
    local expected_args="$2"
    local spy_log="$TEST_TEMP_DIR/.spy_$func_name"

    if [[ ! -f "$spy_log" ]]; then
        return 1
    fi

    grep -q "$expected_args" "$spy_log"
}

# Get spy call count
spy_call_count() {
    local func_name="$1"
    local spy_log="$TEST_TEMP_DIR/.spy_$func_name"

    if [[ ! -f "$spy_log" ]]; then
        echo 0
        return
    fi

    wc -l < "$spy_log" | tr -d ' '
}

# ============================================================================
# RESET ALL MOCKS
# ============================================================================

reset_all_mocks() {
    unset MOCK_RESPONSE
    unset MOCK_RESPONSE_FILE
    unset MOCK_REGISTRY_FILE
    CLAUDE_MOCK_RESPONSES=()
    MOCK_INPUT_QUEUE=()
}
