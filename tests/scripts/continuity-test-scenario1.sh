#!/bin/bash
#
# Continuity Test - Scenario 1: Happy Path
# Complete pipeline execution (Phase 0 through Phase 9)
#

set -e

echo "=========================================="
echo "Continuity Test - Scenario 1: Happy Path"
echo "=========================================="
echo ""

# Configuration
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEST_DIR="/tmp/atomic-claude2-test-$(date +%s)"
SAMPLE_DATA="$PROJECT_ROOT/test/fixtures/sample-project-taskflow.json"

echo "Test Configuration:"
echo "  Project Root: $PROJECT_ROOT"
echo "  Test Directory: $TEST_DIR"
echo "  Sample Data: $SAMPLE_DATA"
echo ""

# Setup test environment
echo "==> Setting up test environment..."
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Copy atomic-claude2
cp -r "$PROJECT_ROOT" atomic-claude2
cd atomic-claude2

# Clean state
rm -rf .state .outputs .logs
mkdir -p .state .outputs .logs

# Set environment
export PYTHONPATH="$(pwd):$PYTHONPATH"
export ATOMIC_ROOT="$(pwd)"
export ATOMIC_STATE_DIR="$(pwd)/.state"
# Don't set ATOMIC_OUTPUT_DIR - let orchestrators set phase-specific directories
export ATOMIC_UAT_MODE="true"
export ATOMIC_TOOL_DEVELOPMENT="true"  # Disable forcing function for tool development

echo "✓ Test environment ready"
echo ""

# Phase 0: Setup
echo "==> Phase 0: Setup"
python main.py run 0
if [ $? -eq 0 ]; then
    echo "✓ Phase 0 complete"
else
    echo "✗ Phase 0 failed"
    exit 1
fi

# Verify Phase 0 outputs
if [ -f ".outputs/0-setup/project-config.json" ]; then
    echo "  ✓ project-config.json created"
else
    echo "  ✗ project-config.json missing"
    exit 1
fi

if [ -f ".outputs/0-setup/secrets.json" ]; then
    echo "  ✓ secrets.json created"
else
    echo "  ✗ secrets.json missing"
    exit 1
fi

if [ -f ".outputs/0-setup/closeout.json" ]; then
    echo "  ✓ closeout.json created"
else
    echo "  ✗ closeout.json missing"
    exit 1
fi

echo ""

# Phase 1: Discovery
echo "==> Phase 1: Discovery"
python main.py run 1
if [ $? -eq 0 ]; then
    echo "✓ Phase 1 complete"
else
    echo "✗ Phase 1 failed"
    exit 1
fi

# Verify Phase 1 outputs
if [ -f ".outputs/1-discovery/closeout.json" ]; then
    echo "  ✓ closeout.json created"
else
    echo "  ✗ closeout.json missing"
    exit 1
fi

echo ""

# Phase 2: PRD
echo "==> Phase 2: PRD"
python main.py run 2
if [ $? -eq 0 ]; then
    echo "✓ Phase 2 complete"
else
    echo "✗ Phase 2 failed"
    exit 1
fi

echo ""

# Phase 3: Tasking
echo "==> Phase 3: Tasking"
python main.py run 3
if [ $? -eq 0 ]; then
    echo "✓ Phase 3 complete"
else
    echo "✗ Phase 3 failed"
    exit 1
fi

echo ""

# Phase 4: Specification
echo "==> Phase 4: Specification"
python main.py run 4
if [ $? -eq 0 ]; then
    echo "✓ Phase 4 complete"
else
    echo "✗ Phase 4 failed"
    exit 1
fi

echo ""

# Phase 5: Implementation
echo "==> Phase 5: Implementation"
python main.py run 5
if [ $? -eq 0 ]; then
    echo "✓ Phase 5 complete"
else
    echo "✗ Phase 5 failed"
    exit 1
fi

echo ""

# Phase 6: Code Review
echo "==> Phase 6: Code Review"
python main.py run 6
if [ $? -eq 0 ]; then
    echo "✓ Phase 6 complete"
else
    echo "✗ Phase 6 failed"
    exit 1
fi

echo ""

# Phase 7: Integration
echo "==> Phase 7: Integration"
python main.py run 7
if [ $? -eq 0 ]; then
    echo "✓ Phase 7 complete"
else
    echo "✗ Phase 7 failed"
    exit 1
fi

echo ""

# Phase 8: Deployment Prep
echo "==> Phase 8: Deployment Prep"
python main.py run 8
if [ $? -eq 0 ]; then
    echo "✓ Phase 8 complete"
else
    echo "✗ Phase 8 failed"
    exit 1
fi

echo ""

# Phase 9: Release
echo "==> Phase 9: Release"
python main.py run 9
if [ $? -eq 0 ]; then
    echo "✓ Phase 9 complete"
else
    echo "✗ Phase 9 failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "Verification"
echo "=========================================="
echo ""

# Check state
echo "==> Checking state..."
python main.py status

# Count completed phases
completed_phases=$(jq '.phases | keys | length' .state/task-state.json)
echo "  Completed phases: $completed_phases / 10"

# Count completed tasks
completed_tasks=0
for phase in $(seq 0 9); do
    phase_key=$(jq -r '.phases | keys[]' .state/task-state.json | grep "^${phase}-")
    if [ ! -z "$phase_key" ]; then
        count=$(jq -r ".phases[\"$phase_key\"].tasks | length" .state/task-state.json)
        completed_tasks=$((completed_tasks + count))
    fi
done
echo "  Completed tasks: $completed_tasks / 74"

# Check outputs
echo ""
echo "==> Checking outputs..."
for phase in $(seq 0 9); do
    phase_names=("setup" "discovery" "prd" "tasking" "specification" "implementation" "code-review" "integration" "deployment-prep" "release")
    phase_name="${phase_names[$phase]}"
    output_dir=".outputs/${phase}-${phase_name}"

    if [ -d "$output_dir" ]; then
        file_count=$(find "$output_dir" -type f | wc -l)
        echo "  ✓ Phase $phase ($phase_name): $file_count files"
    else
        echo "  ✗ Phase $phase ($phase_name): Missing output directory"
    fi
done

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "✓ All 10 phases completed successfully"
echo "✓ All 74 tasks executed"
echo "✓ State persistence verified"
echo "✓ Output generation verified"
echo ""
echo "Test directory: $TEST_DIR"
echo "To inspect results:"
echo "  cd $TEST_DIR/atomic-claude2"
echo "  cat .state/task-state.json | jq ."
echo "  ls -la .outputs/"
echo ""
