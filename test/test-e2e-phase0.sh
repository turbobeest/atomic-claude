#!/usr/bin/env bash
#
# E2E Test Script - Phase 0 Automation
# Simulates user inputs for rapid testing and UI inspection
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
# Test project root is parent of ATOMIC-CLAUDE
TEST_PROJECT_ROOT="$(cd "$ATOMIC_DIR/.." && pwd)"

# Test configuration
TEST_MODE="${1:-minimal}"  # minimal | full | custom
LOG_FILE="$SCRIPT_DIR/e2e-test.log"

echo "" | tee -a "$LOG_FILE"
echo -e "${CYAN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}" | tee -a "$LOG_FILE"
echo -e "${CYAN}${BOLD}║  E2E Test Runner - Phase 0 Automation                     ║${NC}" | tee -a "$LOG_FILE"
echo -e "${CYAN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo -e "${BOLD}Mode:${NC} $TEST_MODE" | tee -a "$LOG_FILE"
echo -e "${BOLD}Started:${NC} $(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Clean previous state
echo -e "${YELLOW}→${NC} Cleaning previous test state..." | tee -a "$LOG_FILE"
rm -rf "$ATOMIC_DIR/.claude" "$ATOMIC_DIR/.state" "$ATOMIC_DIR/.outputs" "$ATOMIC_DIR/.logs"
echo -e "${GREEN}✓${NC} State cleaned" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Prepare .env file with test credentials
echo -e "${YELLOW}→${NC} Checking .env file..." | tee -a "$LOG_FILE"
ENV_FILE="$ATOMIC_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${YELLOW}⚠${NC}  No .env file found at: $ENV_FILE" | tee -a "$LOG_FILE"
    echo -e "  ${DIM}E2E test requires credentials in .env${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo -e "  ${BOLD}Create .env file with credentials:${NC}" | tee -a "$LOG_FILE"
    echo -e "    Location: $ENV_FILE" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo -e "    ${DIM}# AWS Bedrock (Corporate/SSO)${NC}" | tee -a "$LOG_FILE"
    echo -e "    AWS_PROFILE=bedrock-dev" | tee -a "$LOG_FILE"
    echo -e "    AWS_REGION=us-gov-west-1" | tee -a "$LOG_FILE"
    echo -e "    CLAUDE_CODE_USE_BEDROCK=1" | tee -a "$LOG_FILE"
    echo -e "    ANTHROPIC_MODEL='us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0'" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo -e "  ${DIM}Then authenticate: aws sso login --profile bedrock-dev${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo -e "${RED}✗${NC} Cannot proceed without API credentials" | tee -a "$LOG_FILE"
    exit 1
else
    echo -e "${GREEN}✓${NC} .env file found" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# Prepare setup.md with test values
echo -e "${YELLOW}→${NC} Preparing setup.md..." | tee -a "$LOG_FILE"
SETUP_FILE="$ATOMIC_DIR/initialization/setup.md"

# Backup original
if [[ ! -f "$SETUP_FILE.backup" ]]; then
    cp "$SETUP_FILE" "$SETUP_FILE.backup"
fi

# Restore from backup (in case previous test modified it)
cp "$SETUP_FILE.backup" "$SETUP_FILE"

echo -e "${GREEN}✓${NC} Setup file ready" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Function to simulate task interaction
run_phase0_automated() {
    echo -e "${CYAN}${BOLD}Starting Phase 0 with automated inputs...${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    # Task 001: Setup File Validation
    # Expects: Press Enter to confirm setup.md is ready
    # Task 002: Config Collection
    # Expects: Nothing (uses pre-detected setup file)
    # Task 003: Config Review
    # Expects: [a]pprove or [e]dit
    # Task 004: API Keys
    # Expects: API key inputs (can skip)
    # Task 005-009: Various prompts

    # Create input file with automated responses
    cat > /tmp/phase0-inputs.txt << 'INPUTS'

a
skip
skip
skip



y
c
c
c
c
c
c
c
INPUTS

    # Run Phase 0 with automated inputs
    echo -e "${YELLOW}→${NC} Launching Phase 0..." | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    # Use script command to capture all terminal output including colors
    if command -v script &>/dev/null; then
        # macOS/BSD version
        script -q /tmp/phase0-output.log bash -c "cd '$TEST_PROJECT_ROOT' && '$ATOMIC_DIR/main.sh' run 0 --skip-intro < /tmp/phase0-inputs.txt" || true
    else
        # Linux version
        script -q -c "cd '$TEST_PROJECT_ROOT' && '$ATOMIC_DIR/main.sh' run 0 --skip-intro < /tmp/phase0-inputs.txt" /tmp/phase0-output.log || true
    fi

    # Copy to main log
    cat /tmp/phase0-output.log >> "$LOG_FILE"
}

# Monitor function - runs in background
monitor_test() {
    local pid=$1
    local start_time=$(date +%s)

    while kill -0 "$pid" 2>/dev/null; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        # Check current task
        if [[ -f "$ATOMIC_DIR/.state/current-task.json" ]]; then
            local task=$(jq -r '.description // "Unknown"' "$ATOMIC_DIR/.state/current-task.json" 2>/dev/null || echo "Unknown")
            echo -e "${CYAN}[${elapsed}s]${NC} Current: $task" | tee -a "$LOG_FILE"
        fi

        sleep 5
    done
}

# Interactive mode - pause between tasks
run_phase0_interactive() {
    echo -e "${CYAN}${BOLD}Interactive Mode - Manual Testing${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "This will run Phase 0 normally, but you can inspect each step." | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}Press Enter to start Phase 0...${NC}"
    read -r

    cd "$SCRIPT_DIR"
    "$ATOMIC_DIR/main.sh" run 0 --skip-intro 2>&1 | tee -a "$LOG_FILE"
}

# Custom mode - specify task to start from
run_phase0_custom() {
    local start_task="${2:-001}"

    echo -e "${CYAN}${BOLD}Custom Mode - Starting from Task $start_task${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    cd "$SCRIPT_DIR"
    "$ATOMIC_DIR/main.sh" run 0 --task="$start_task" 2>&1 | tee -a "$LOG_FILE"
}

# Run based on mode
case "$TEST_MODE" in
    minimal|auto|automated)
        run_phase0_automated &
        TEST_PID=$!

        # Start monitor in background
        monitor_test "$TEST_PID" &
        MONITOR_PID=$!

        # Wait for test to complete
        wait "$TEST_PID" || true
        kill "$MONITOR_PID" 2>/dev/null || true

        echo "" | tee -a "$LOG_FILE"
        echo -e "${GREEN}✓ Automated test completed${NC}" | tee -a "$LOG_FILE"
        ;;

    interactive|manual)
        run_phase0_interactive
        ;;

    custom)
        run_phase0_custom "$@"
        ;;

    *)
        echo -e "${RED}Error: Unknown mode '$TEST_MODE'${NC}"
        echo ""
        echo "Usage: $0 [mode] [options]"
        echo ""
        echo "Modes:"
        echo "  minimal      - Automated with minimal inputs (default)"
        echo "  interactive  - Manual step-through for UI inspection"
        echo "  custom NNN   - Start from specific task"
        echo ""
        exit 1
        ;;
esac

# Analysis and reporting
echo "" | tee -a "$LOG_FILE"
echo -e "${CYAN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}" | tee -a "$LOG_FILE"
echo -e "${CYAN}${BOLD}║  Test Analysis                                             ║${NC}" | tee -a "$LOG_FILE"
echo -e "${CYAN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Check outputs
if [[ -d "$ATOMIC_DIR/.outputs/0-setup" ]]; then
    echo -e "${BOLD}Outputs created:${NC}" | tee -a "$LOG_FILE"
    ls -lh "$ATOMIC_DIR/.outputs/0-setup/" | tail -n +2 | while read -r line; do
        echo "  $line" | tee -a "$LOG_FILE"
    done
    echo "" | tee -a "$LOG_FILE"
fi

# Check for errors in log
if grep -qi "error" "$LOG_FILE"; then
    echo -e "${RED}⚠ Errors detected in execution${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo "Error lines:" | tee -a "$LOG_FILE"
    grep -i "error" "$LOG_FILE" | head -10 | while read -r line; do
        echo "  $line"
    done
    echo "" | tee -a "$LOG_FILE"
fi

# Check task completion
if [[ -f "$ATOMIC_DIR/.outputs/0-setup/closeout.json" ]]; then
    echo -e "${GREEN}✓ Phase 0 completed successfully${NC}" | tee -a "$LOG_FILE"

    local completed_at=$(jq -r '.completed_at' "$ATOMIC_DIR/.outputs/0-setup/closeout.json")
    local tasks_completed=$(jq -r '.tasks_completed' "$ATOMIC_DIR/.outputs/0-setup/closeout.json")

    echo "  Completed: $completed_at" | tee -a "$LOG_FILE"
    echo "  Tasks: $tasks_completed" | tee -a "$LOG_FILE"
else
    echo -e "${YELLOW}⚠ Phase 0 did not complete${NC}" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo -e "${BOLD}Completed:${NC} $(date)" | tee -a "$LOG_FILE"
echo -e "${BOLD}Log saved:${NC} $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Cleanup temp files
rm -f /tmp/phase0-inputs.txt /tmp/phase0-output.log

# Restore original setup.md if backup exists
if [[ -f "$SETUP_FILE.backup" ]]; then
    echo -e "${YELLOW}→${NC} Restoring original setup.md..." | tee -a "$LOG_FILE"
    cp "$SETUP_FILE.backup" "$SETUP_FILE"
    echo -e "${GREEN}✓${NC} Restored" | tee -a "$LOG_FILE"
fi

echo ""
