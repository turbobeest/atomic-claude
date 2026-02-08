#!/bin/bash
#
# Comprehensive Test Runner
# Executes all testing phases: Unit, Continuity, Functional, UX/UI
#

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export ATOMIC_TOOL_DEVELOPMENT="true"  # Disable forcing function for tool development

echo "=========================================="
echo "Atomic Claude 2.0 - Comprehensive Testing"
echo "=========================================="
echo ""
echo "This script will run:"
echo "  1. Unit Tests (pytest)"
echo "  2. Continuity Tests (end-to-end pipeline)"
echo "  3. Functional Evaluation (output validation)"
echo "  4. UX/UI Evaluation (interactive)"
echo ""

read -p "Continue? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "Aborted."
    exit 0
fi

# ==============================================================================
# 1. Unit Tests
# ==============================================================================

echo ""
echo "=========================================="
echo "Phase 1: Unit Tests"
echo "=========================================="
echo ""

read -p "Run unit tests? (y/n): " run_unit
if [ "$run_unit" = "y" ]; then
    echo "==> Running unit tests..."
    echo ""

    # Run core tests
    echo "Testing core modules..."
    python -m pytest tests/unit/test_core_*.py -v --tb=short || true

    echo ""
    echo "Testing LLM providers..."
    python -m pytest tests/unit/test_*_provider.py -v --tb=short || true

    echo ""
    echo "Testing phase tasks..."
    python -m pytest tests/unit/test_phase_*.py -v --tb=short -x || true

    echo ""
    echo "✓ Unit tests complete"
else
    echo "Skipping unit tests"
fi

# ==============================================================================
# 2. Integration Tests
# ==============================================================================

echo ""
echo "=========================================="
echo "Phase 2: Integration Tests"
echo "=========================================="
echo ""

read -p "Run integration tests? (y/n): " run_integration
if [ "$run_integration" = "y" ]; then
    echo "==> Running integration tests..."
    echo ""

    python -m pytest tests/integration/ -v --tb=short || true

    echo ""
    echo "✓ Integration tests complete"
else
    echo "Skipping integration tests"
fi

# ==============================================================================
# 3. Continuity Tests
# ==============================================================================

echo ""
echo "=========================================="
echo "Phase 3: Continuity Tests"
echo "=========================================="
echo ""
echo "Continuity tests verify end-to-end pipeline execution."
echo "This will create a test environment and run all 10 phases."
echo ""

read -p "Run continuity tests? (y/n): " run_continuity
if [ "$run_continuity" = "y" ]; then
    echo "==> Running continuity test (Scenario 1: Happy Path)..."
    echo ""

    if [ -f "test/continuity-test-scenario1.sh" ]; then
        bash test/continuity-test-scenario1.sh
    else
        echo "✗ Continuity test script not found"
        echo "  Expected: test/continuity-test-scenario1.sh"
    fi

    echo ""
    echo "✓ Continuity tests complete"
else
    echo "Skipping continuity tests"
fi

# ==============================================================================
# 4. Functional Evaluation
# ==============================================================================

echo ""
echo "=========================================="
echo "Phase 4: Functional Evaluation"
echo "=========================================="
echo ""
echo "Functional evaluation validates output quality."
echo ""

read -p "Run functional evaluation? (y/n): " run_functional
if [ "$run_functional" = "y" ]; then
    echo "==> Running functional evaluation..."
    echo ""

    # Check if test outputs exist
    if [ -d ".outputs" ]; then
        echo "Validating phase outputs..."

        # Phase 0
        if [ -f ".outputs/0-setup/config.json" ]; then
            echo "  ✓ Phase 0: config.json"
            jq . .outputs/0-setup/config.json > /dev/null 2>&1 && echo "    Valid JSON" || echo "    ✗ Invalid JSON"
        else
            echo "  ✗ Phase 0: config.json missing"
        fi

        if [ -f ".outputs/0-setup/closeout.json" ]; then
            echo "  ✓ Phase 0: closeout.json"
        else
            echo "  ✗ Phase 0: closeout.json missing"
        fi

        # Check all phases
        for phase in $(seq 0 9); do
            phase_names=("setup" "discovery" "prd" "tasking" "specification" "implementation" "code-review" "integration" "deployment-prep" "release")
            phase_name="${phase_names[$phase]}"
            output_dir=".outputs/${phase}-${phase_name}"

            if [ -d "$output_dir" ]; then
                file_count=$(find "$output_dir" -type f | wc -l)
                echo "  ✓ Phase $phase ($phase_name): $file_count files"
            else
                echo "  ⚠ Phase $phase ($phase_name): No outputs yet"
            fi
        done
    else
        echo "  No outputs directory found (.outputs/)"
        echo "  Run continuity tests first to generate outputs"
    fi

    echo ""
    echo "✓ Functional evaluation complete"
else
    echo "Skipping functional evaluation"
fi

# ==============================================================================
# 5. UX/UI Evaluation
# ==============================================================================

echo ""
echo "=========================================="
echo "Phase 5: UX/UI Evaluation"
echo "=========================================="
echo ""
echo "UX/UI evaluation is interactive and subjective."
echo "You'll rate each user interaction touchpoint."
echo ""

read -p "Run UX/UI evaluation? (y/n): " run_uxui
if [ "$run_uxui" = "y" ]; then
    echo "==> UX/UI evaluation is interactive and manual"
    echo ""
    echo "To run UX/UI evaluation:"
    echo "  1. Run: ./test/run-uxui-evaluation.sh"
    echo "  2. Run: python main.py run 0"
    echo "  3. Rate using: test/UXUI-EVALUATION-GUIDE.md"
    echo ""
    echo "See: test/README-UXUI-EVAL.md for details"
    echo ""

    read -p "Open UX/UI guide now? (y/n): " open_guide
    if [ "$open_guide" = "y" ]; then
        if command -v open &> /dev/null; then
            open test/README-UXUI-EVAL.md
        else
            cat test/README-UXUI-EVAL.md
        fi
    fi
else
    echo "Skipping UX/UI evaluation"
fi

# ==============================================================================
# Summary
# ==============================================================================

echo ""
echo "=========================================="
echo "Testing Complete"
echo "=========================================="
echo ""
echo "Test Results:"
echo ""

# Unit tests
if [ "$run_unit" = "y" ]; then
    echo "✓ Unit Tests: Completed"
else
    echo "- Unit Tests: Skipped"
fi

# Integration tests
if [ "$run_integration" = "y" ]; then
    echo "✓ Integration Tests: Completed"
else
    echo "- Integration Tests: Skipped"
fi

# Continuity tests
if [ "$run_continuity" = "y" ]; then
    echo "✓ Continuity Tests: Completed"
else
    echo "- Continuity Tests: Skipped"
fi

# Functional evaluation
if [ "$run_functional" = "y" ]; then
    echo "✓ Functional Evaluation: Completed"
else
    echo "- Functional Evaluation: Skipped"
fi

# UX/UI evaluation
if [ "$run_uxui" = "y" ]; then
    echo "✓ UX/UI Evaluation: Completed"
    if [ -f "test/uxui-evaluation-results.txt" ]; then
        echo ""
        echo "UX/UI Results:"
        cat test/uxui-evaluation-results.txt | grep "^Touchpoint" | sed 's/^/  /'
    fi
else
    echo "- UX/UI Evaluation: Skipped"
fi

echo ""
echo "For detailed results, see:"
echo "  - Unit Tests: pytest output above"
echo "  - Continuity: /tmp/atomic-claude2-test-*/atomic-claude2/"
echo "  - Functional: .outputs/ directories"
echo "  - UX/UI: test/uxui-evaluation-results.txt"
echo ""
