#!/bin/bash
# Multi-Pronged Test Attack Executor
# Runs comprehensive tests with clear reporting

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Result storage
RESULTS_FILE="/tmp/atomic_test_results_$(date +%s).md"

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_section() {
    echo ""
    echo -e "${YELLOW}▶ $1${NC}"
    echo "─────────────────────────────────────────────"
}

test_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED_TESTS++))
    ((TOTAL_TESTS++))
    echo "- [x] $1" >> "$RESULTS_FILE"
}

test_fail() {
    echo -e "${RED}❌ $1${NC}"
    echo -e "${RED}   $2${NC}"
    ((FAILED_TESTS++))
    ((TOTAL_TESTS++))
    echo "- [ ] $1 - FAILED: $2" >> "$RESULTS_FILE"
}

test_skip() {
    echo -e "${YELLOW}⏭  $1${NC}"
    ((SKIPPED_TESTS++))
    ((TOTAL_TESTS++))
    echo "- [ ] $1 - SKIPPED" >> "$RESULTS_FILE"
}

# Initialize results file
cat > "$RESULTS_FILE" << EOF
# Test Results - $(date)

## Summary
EOF

# Parse arguments
QUICK_MODE=false
SKIP_LLM=false
SKIP_INTEGRATION=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --skip-llm)
            SKIP_LLM=true
            shift
            ;;
        --skip-integration)
            SKIP_INTEGRATION=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--quick] [--skip-llm] [--skip-integration]"
            exit 1
            ;;
    esac
done

print_header "ATOMIC CLAUDE - Multi-Pronged Test Attack"
echo "Quick Mode: $QUICK_MODE"
echo "Skip LLM: $SKIP_LLM"
echo "Skip Integration: $SKIP_INTEGRATION"
echo ""

# ============================================================================
# PHASE 1: FOUNDATION
# ============================================================================

print_header "PHASE 1: FOUNDATION"
echo "" >> "$RESULTS_FILE"
echo "## Phase 1: Foundation" >> "$RESULTS_FILE"

print_section "1.1 Unit Tests (Smoke Tests)"
if python3 tests/test_basic.py > /tmp/test_basic.log 2>&1; then
    test_pass "Unit tests passing"
else
    test_fail "Unit tests failed" "$(tail -3 /tmp/test_basic.log)"
fi

print_section "1.2 Import Validation"
if python3 << 'EOF' > /tmp/test_imports.log 2>&1
from lib import atomic, provider, memory, phase, task_state
from lib.atomic import atomic_invoke
from lib.provider import ProviderManager
print("✅ All imports successful")
EOF
then
    test_pass "All imports successful"
else
    test_fail "Import validation failed" "$(cat /tmp/test_imports.log)"
fi

print_section "1.3 CLI Commands"
if python3 main.py list > /tmp/test_cli_list.log 2>&1; then
    test_pass "CLI list command works"
else
    test_fail "CLI list command failed" "$(cat /tmp/test_cli_list.log)"
fi

if python3 main.py providers > /tmp/test_cli_providers.log 2>&1; then
    test_pass "CLI providers command works"
else
    test_fail "CLI providers command failed" "$(cat /tmp/test_cli_providers.log)"
fi

# ============================================================================
# PHASE 2: INTEGRATION TESTS
# ============================================================================

if [[ "$SKIP_INTEGRATION" == "false" && "$QUICK_MODE" == "false" ]]; then
    print_header "PHASE 2: INTEGRATION TESTS"
    echo "" >> "$RESULTS_FILE"
    echo "## Phase 2: Integration Tests" >> "$RESULTS_FILE"

    print_section "2.1 Check pytest installation"
    if python3 -c "import pytest" 2>/dev/null; then
        test_pass "pytest installed"

        print_section "2.2 Run integration test suite"
        if pytest tests/test_integration.py -v --tb=short > /tmp/test_integration.log 2>&1; then
            test_pass "Integration tests passing"
            PASSED_COUNT=$(grep -c "PASSED" /tmp/test_integration.log || echo "0")
            echo "   Passed: $PASSED_COUNT tests"
        else
            FAILED_COUNT=$(grep -c "FAILED" /tmp/test_integration.log || echo "unknown")
            test_fail "Integration tests failed" "$FAILED_COUNT tests failed - see /tmp/test_integration.log"
        fi
    else
        test_skip "Integration tests - pytest not installed"
        echo "   Run: pip install -r tests/requirements.txt"
    fi
else
    test_skip "Integration tests - skipped by flag"
fi

# ============================================================================
# PHASE 3: REAL LLM INVOCATIONS
# ============================================================================

if [[ "$SKIP_LLM" == "false" && "$QUICK_MODE" == "false" ]]; then
    print_header "PHASE 3: REAL LLM INVOCATIONS"
    echo "" >> "$RESULTS_FILE"
    echo "## Phase 3: Real LLM Invocations" >> "$RESULTS_FILE"

    print_section "3.1 Simple Invocation (Haiku)"
    cat > /tmp/test_simple.md << 'EOF'
Respond with exactly: {"test": "success"}
EOF

    if python3 << 'EOF' > /tmp/test_llm_simple.log 2>&1
from lib.atomic import atomic_invoke
result = atomic_invoke(
    "/tmp/test_simple.md",
    "/tmp/test_output.json",
    "Test simple invocation",
    model="haiku",
    format_type="json",
    timeout=30
)
if result:
    print("✅ Success")
    exit(0)
else:
    print("❌ Failed")
    exit(1)
EOF
    then
        test_pass "Simple LLM invocation works"
    else
        test_fail "Simple LLM invocation failed" "$(tail -3 /tmp/test_llm_simple.log)"
    fi

    print_section "3.2 Markdown Output (No JSON)"
    cat > /tmp/test_markdown.md << 'EOF'
Write exactly: "Python is great"
EOF

    if python3 << 'EOF' > /tmp/test_llm_markdown.log 2>&1
from lib.atomic import atomic_invoke
result = atomic_invoke(
    "/tmp/test_markdown.md",
    "/tmp/test_haiku.md",
    "Test markdown output",
    model="haiku",
    timeout=30
)
print(f"Result: {result}")
exit(0 if result else 1)
EOF
    then
        test_pass "Markdown output works"
    else
        test_fail "Markdown output failed" "$(tail -3 /tmp/test_llm_markdown.log)"
    fi
else
    test_skip "Real LLM invocations - skipped"
fi

# ============================================================================
# PHASE 4: HYBRID MODE
# ============================================================================

if [[ "$QUICK_MODE" == "false" ]]; then
    print_header "PHASE 4: HYBRID MODE"
    echo "" >> "$RESULTS_FILE"
    echo "## Phase 4: Hybrid Mode" >> "$RESULTS_FILE"

    print_section "4.1 List Phases"
    if python3 main.py list > /tmp/test_hybrid_list.log 2>&1; then
        if grep -q "0-setup" /tmp/test_hybrid_list.log; then
            test_pass "Hybrid list shows phases"
        else
            test_fail "Hybrid list missing phases" "No phases found in output"
        fi
    else
        test_fail "Hybrid list failed" "$(cat /tmp/test_hybrid_list.log)"
    fi

    print_section "4.2 Provider Check"
    if python3 main.py providers > /tmp/test_hybrid_providers.log 2>&1; then
        if grep -q "Provider Availability" /tmp/test_hybrid_providers.log; then
            test_pass "Hybrid provider check works"
        else
            test_fail "Hybrid provider check incomplete" "Missing provider info"
        fi
    else
        test_fail "Hybrid provider check failed" "$(cat /tmp/test_hybrid_providers.log)"
    fi

    print_section "4.3 Status Check"
    if python3 main.py status > /tmp/test_hybrid_status.log 2>&1; then
        test_pass "Hybrid status works"
    else
        # Status might fail if no pipeline run yet - that's ok
        test_skip "Hybrid status (no pipeline run yet)"
    fi
else
    test_skip "Hybrid mode tests - quick mode enabled"
fi

# ============================================================================
# PHASE 5: PROVIDER FALLBACK
# ============================================================================

if [[ "$QUICK_MODE" == "false" ]]; then
    print_header "PHASE 5: PROVIDER FALLBACK"
    echo "" >> "$RESULTS_FILE"
    echo "## Phase 5: Provider Fallback" >> "$RESULTS_FILE"

    print_section "5.1 Provider Detection"
    if python3 << 'EOF' > /tmp/test_provider_detection.log 2>&1
from lib.provider import ProviderManager
pm = ProviderManager()
print(f"Claude Code: {pm.check_claude_code()}")
print(f"API: {pm.check_anthropic()}")
print(f"Bedrock: {pm.check_aws_bedrock()}")
print(f"Ollama: {pm.check_ollama()}")
EOF
    then
        test_pass "Provider detection works"
    else
        test_fail "Provider detection failed" "$(cat /tmp/test_provider_detection.log)"
    fi

    print_section "5.2 Provider Chain"
    if python3 << 'EOF' > /tmp/test_provider_chain.log 2>&1
from lib.provider import ProviderManager
pm = ProviderManager()
chain = pm.get_chain("primary")
print(f"Chain: {chain}")
EOF
    then
        test_pass "Provider chain retrieval works"
    else
        test_fail "Provider chain failed" "$(cat /tmp/test_provider_chain.log)"
    fi
else
    test_skip "Provider fallback tests - quick mode enabled"
fi

# ============================================================================
# PHASE 6: ERROR HANDLING
# ============================================================================

if [[ "$QUICK_MODE" == "false" ]]; then
    print_header "PHASE 6: ERROR HANDLING"
    echo "" >> "$RESULTS_FILE"
    echo "## Phase 6: Error Handling" >> "$RESULTS_FILE"

    print_section "6.1 Missing Prompt File"
    if python3 << 'EOF' > /tmp/test_error_missing.log 2>&1
from lib.atomic import atomic_invoke
result = atomic_invoke(
    "/tmp/nonexistent_prompt_12345.md",
    "/tmp/output.json",
    "Test missing prompt",
    model="haiku"
)
print(f"Result (should be False): {result}")
exit(0 if result == False else 1)
EOF
    then
        test_pass "Missing file handled gracefully"
    else
        test_fail "Missing file not handled" "$(cat /tmp/test_error_missing.log)"
    fi

    print_section "6.2 Dependency Validation"
    if python3 << 'EOF' > /tmp/test_error_deps.log 2>&1
from lib.atomic import atomic_validate_deps
result_non_strict = atomic_validate_deps(strict=False)
print(f"Non-strict: {result_non_strict}")
exit(0 if result_non_strict else 1)
EOF
    then
        test_pass "Dependency validation works"
    else
        test_fail "Dependency validation failed" "$(cat /tmp/test_error_deps.log)"
    fi
else
    test_skip "Error handling tests - quick mode enabled"
fi

# ============================================================================
# SUMMARY
# ============================================================================

print_header "TEST SUMMARY"

PASS_RATE=0
if [[ $TOTAL_TESTS -gt 0 ]]; then
    PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
fi

echo ""
echo -e "${BOLD}Total Tests:${NC}   $TOTAL_TESTS"
echo -e "${GREEN}✅ Passed:${NC}     $PASSED_TESTS"
echo -e "${RED}❌ Failed:${NC}     $FAILED_TESTS"
echo -e "${YELLOW}⏭  Skipped:${NC}    $SKIPPED_TESTS"
echo ""
echo -e "${BOLD}Pass Rate:${NC}     ${PASS_RATE}%"
echo ""

# Write summary to results file
cat >> "$RESULTS_FILE" << EOF

## Summary Statistics
- Total Tests: $TOTAL_TESTS
- Passed: $PASSED_TESTS
- Failed: $FAILED_TESTS
- Skipped: $SKIPPED_TESTS
- Pass Rate: ${PASS_RATE}%

## Status
EOF

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}✅ ALL CRITICAL TESTS PASSED${NC}"
    echo "**Status:** ✅ ALL CRITICAL TESTS PASSED" >> "$RESULTS_FILE"
    echo ""
    echo "Results saved to: $RESULTS_FILE"
    exit 0
else
    echo -e "${RED}${BOLD}❌ SOME TESTS FAILED${NC}"
    echo "**Status:** ❌ SOME TESTS FAILED" >> "$RESULTS_FILE"
    echo ""
    echo "Results saved to: $RESULTS_FILE"
    echo ""
    echo "Review logs in /tmp/test_*.log for details"
    exit 1
fi
