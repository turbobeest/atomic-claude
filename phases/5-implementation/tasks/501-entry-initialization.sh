#!/bin/bash
#
# Task 501: Entry & Initialization
# Verify Phase 4 artifacts exist and prepare for TDD implementation
#

task_501_entry_initialization() {
    local phase4_closeout="$ATOMIC_ROOT/.claude/closeout/phase-04-closeout.json"
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local specs_dir="$ATOMIC_ROOT/.claude/specs"
    local testing_dir="$ATOMIC_ROOT/.claude/testing"

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 5 WELCOME
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PHASE 05 - IMPLEMENTATION${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}"
    cat << 'EOF'
                                _______ ______  ______
                                   |    |     \ |     \
                                   |    |_____/ |_____/

      _____ _______  _____         _______ _______ _______ __   _ _______ _______ _______ _____  _____  __   _
        |   |  |  | |_____] |      |______ |  |  | |______ | \  |    |    |_____|    |      |   |     | | \  |
      __|__ |  |  | |       |_____ |______ |  |  | |______ |  \_|    |    |     |    |    __|__ |_____| |  \_|
EOF
    echo -e "${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${DIM}Executing RED/GREEN/REFACTOR/VERIFY cycles for all tasks.${NC}"
    echo ""

    atomic_step "Entry & Initialization"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PHASE 4 VERIFICATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PHASE 4 VERIFICATION${NC}"
    echo ""

    local verification_passed=true

    # Check Phase 4 closeout
    if [[ -f "$phase4_closeout" ]]; then
        local phase4_status=$(jq -r '.status // "unknown"' "$phase4_closeout")
        if [[ "$phase4_status" == "complete" ]]; then
            echo -e "  ${GREEN}✓${NC} Phase 4 closeout verified"
        else
            echo -e "  ${YELLOW}!${NC} Phase 4 closeout status: $phase4_status"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Phase 4 closeout not found (continuing anyway)"
    fi

    # Check tasks.json has TDD subtasks
    if [[ -f "$tasks_file" ]]; then
        local tasks_with_tdd=$(jq '[.tasks[] | select(.subtasks | length >= 4)] | length' "$tasks_file" 2>/dev/null || echo 0)
        local total_tasks=$(jq '.tasks | length' "$tasks_file" 2>/dev/null || echo 0)
        if [[ "$tasks_with_tdd" -gt 0 ]]; then
            echo -e "  ${GREEN}✓${NC} TDD subtasks found ($tasks_with_tdd / $total_tasks tasks)"
        else
            echo -e "  ${RED}✗${NC} No TDD subtasks found"
            verification_passed=false
        fi
    else
        echo -e "  ${RED}✗${NC} tasks.json not found"
        verification_passed=false
    fi

    # Check OpenSpec files
    if [[ -d "$specs_dir" ]]; then
        local spec_count=$(find "$specs_dir" -name "spec-*.json" 2>/dev/null | wc -l)
        if [[ "$spec_count" -gt 0 ]]; then
            echo -e "  ${GREEN}✓${NC} OpenSpec files found ($spec_count specs)"
        else
            echo -e "  ${RED}✗${NC} No OpenSpec files found"
            verification_passed=false
        fi
    else
        echo -e "  ${RED}✗${NC} Specs directory not found"
        verification_passed=false
    fi

    echo ""

    if [[ "$verification_passed" != "true" ]]; then
        echo -e "  ${RED}Phase 4 artifacts missing. Cannot proceed.${NC}"
        echo ""
        echo -e "  ${DIM}Run Phase 4 (Specification) first to generate OpenSpecs and TDD subtasks.${NC}"
        echo ""
        return 1
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TDD SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TDD SUMMARY${NC}"
    echo ""

    local total_subtasks=$(jq '[.tasks[].subtasks | length] | add // 0' "$tasks_file" 2>/dev/null || echo 0)

    echo -e "    Tasks with TDD:      $tasks_with_tdd"
    echo -e "    Total subtasks:      $total_subtasks"
    echo -e "    TDD cycles to run:   $tasks_with_tdd"
    echo ""

    # Show TDD cycle structure
    echo -e "  ${DIM}Each task will go through:${NC}"
    echo ""
    echo -e "    ${RED}RED${NC}       → Write failing tests"
    echo -e "    ${GREEN}GREEN${NC}     → Minimal implementation"
    echo -e "    ${CYAN}REFACTOR${NC}  → Clean up code"
    echo -e "    ${MAGENTA}VERIFY${NC}    → Security scan"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INITIALIZE TESTING DIRECTORY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}INITIALIZE TESTING DIRECTORY${NC}"
    echo ""

    mkdir -p "$testing_dir"
    echo -e "  ${GREEN}✓${NC} Testing directory initialized: .claude/testing/"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TDD INTRODUCTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TDD METHODOLOGY${NC}"
    echo ""
    echo -e "  ${DIM}Test-Driven Development ensures code quality through:${NC}"
    echo ""
    echo -e "    ─────────────────────────────────────────────────────────────────"
    echo ""
    echo -e "    ${RED}RED${NC}  ────────►  ${GREEN}GREEN${NC}  ────────►  ${CYAN}REFACTOR${NC}  ────────►  ${MAGENTA}VERIFY${NC}"
    echo ""
    echo -e "    Write tests    Implement      Clean up        Security"
    echo -e "    (must FAIL)    (tests PASS)   (still PASS)    scan"
    echo ""
    echo -e "    ─────────────────────────────────────────────────────────────────"
    echo ""
    echo -e "  ${BOLD}Key Principles:${NC}"
    echo ""
    echo -e "    1. Never write implementation code without a failing test"
    echo -e "    2. Write only enough code to pass the test"
    echo -e "    3. Refactor while keeping tests green"
    echo -e "    4. Security scan before marking complete"
    echo ""

    read -p "  Press Enter to continue..."

    # Save initialization state
    local init_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/initialization.json"
    mkdir -p "$(dirname "$init_file")"

    jq -n \
        --argjson tasks_with_tdd "$tasks_with_tdd" \
        --argjson total_subtasks "$total_subtasks" \
        --argjson spec_count "$spec_count" \
        '{
            "phase4_verified": true,
            "tasks_with_tdd": $tasks_with_tdd,
            "total_subtasks": $total_subtasks,
            "spec_count": $spec_count,
            "initialized_at": (now | todate)
        }' > "$init_file"

    atomic_context_artifact "$init_file" "initialization" "Phase 5 initialization state"
    atomic_context_decision "Phase 5 initialized with $tasks_with_tdd TDD cycles to execute" "initialization"

    atomic_success "Entry & Initialization complete"

    return 0
}
