#!/bin/bash
#
# Task 601: Entry & Initialization
# Welcome to Phase 6, verify Phase 5 completion, display review overview
#

task_601_entry_initialization() {
    local closeout_file="$ATOMIC_ROOT/.claude/closeout/phase-05-closeout.json"
    local validation_file="$ATOMIC_ROOT/.claude/testing/validation-report.json"

    clear
    echo ""
    echo -e "${DIM}──────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}${CYAN}"
    echo "   ██████╗ ██████╗ ██████╗ ███████╗    ██████╗ ███████╗██╗   ██╗██╗███████╗██╗    ██╗"
    echo "  ██╔════╝██╔═══██╗██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║██║██╔════╝██║    ██║"
    echo "  ██║     ██║   ██║██║  ██║█████╗      ██████╔╝█████╗  ██║   ██║██║█████╗  ██║ █╗ ██║"
    echo "  ██║     ██║   ██║██║  ██║██╔══╝      ██╔══██╗██╔══╝  ╚██╗ ██╔╝██║██╔══╝  ██║███╗██║"
    echo "  ╚██████╗╚██████╔╝██████╔╝███████╗    ██║  ██║███████╗ ╚████╔╝ ██║███████╗╚███╔███╔╝"
    echo "   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝    ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚═╝╚══════╝ ╚══╝╚══╝ "
    echo -e "${NC}"
    echo ""
    echo -e "${DIM}──────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    atomic_step "Entry & Initialization"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PHASE 5 VERIFICATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}──────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PHASE 5 VERIFICATION${NC}"
    echo ""

    if [[ ! -f "$closeout_file" ]]; then
        echo -e "  ${RED}✗${NC} Phase 5 closeout not found"
        echo ""
        atomic_error "Phase 5 must be completed before starting Phase 6"
        return 1
    fi

    local phase5_status=$(jq -r '.status // "unknown"' "$closeout_file")
    local tasks_completed=$(jq -r '.tasks_completed // 0' "$closeout_file")
    local total_tasks=$(jq -r '.total_tasks // 0' "$closeout_file")
    local tests_passing=$(jq -r '.tests.passing // 0' "$closeout_file")
    local total_tests=$(jq -r '.tests.total // 0' "$closeout_file")
    local unit_coverage=$(jq -r '.coverage.unit // 0' "$closeout_file")

    if [[ "$phase5_status" != "complete" ]]; then
        echo -e "  ${RED}✗${NC} Phase 5 status: $phase5_status"
        echo ""
        atomic_error "Phase 5 must be complete before starting Phase 6"
        return 1
    fi

    echo -e "  ${GREEN}✓${NC} Phase 5 complete"
    echo -e "  ${GREEN}✓${NC} TDD cycles completed: $tasks_completed / $total_tasks"
    echo -e "  ${GREEN}✓${NC} Tests passing: $tests_passing / $total_tests"
    echo -e "  ${GREEN}✓${NC} Unit coverage: ${unit_coverage}%"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CODE REVIEW OVERVIEW
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}──────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}CODE REVIEW OVERVIEW${NC}"
    echo ""

    echo -e "  ${DIM}Phase 6 performs comprehensive code review across multiple dimensions:${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}CODE REVIEW PROCESS${NC}"
    echo ""
    echo -e "    ${CYAN}Deep Code Review${NC}  ───►"
    echo -e "                            ╲"
    echo -e "    ${CYAN}Architecture${NC}      ───►  ╲"
    echo -e "    ${CYAN}Compliance${NC}               ╲"
    echo -e "                              ────►  ${GREEN}Code Refiner${NC}"
    echo -e "    ${CYAN}Performance${NC}       ───►  ╱        ${GREEN}(Refinement)${NC}"
    echo -e "    ${CYAN}Analysis${NC}               ╱"
    echo -e "                            ╱"
    echo -e "    ${CYAN}Documentation${NC}     ───►"
    echo -e "    ${CYAN}Review${NC}"
    echo ""
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # REVIEW DIMENSIONS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}──────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}REVIEW DIMENSIONS${NC}"
    echo ""

    echo -e "  ${CYAN}1. Deep Code Review${NC}"
    echo -e "     ${DIM}Logic correctness, error handling, edge cases, code clarity${NC}"
    echo ""
    echo -e "  ${CYAN}2. Architecture Compliance${NC}"
    echo -e "     ${DIM}Pattern adherence, dependency management, separation of concerns${NC}"
    echo ""
    echo -e "  ${CYAN}3. Performance Analysis${NC}"
    echo -e "     ${DIM}Algorithmic complexity, resource usage, potential bottlenecks${NC}"
    echo ""
    echo -e "  ${CYAN}4. Documentation Review${NC}"
    echo -e "     ${DIM}Code comments, API docs, README completeness${NC}"
    echo ""
    echo -e "  ${CYAN}5. Code Refinement${NC}"
    echo -e "     ${DIM}Address findings, apply improvements, maintain test coverage${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PHASE 6 TASKS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}──────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PHASE 6 TASKS${NC}"
    echo ""

    echo -e "    ${DIM}601${NC} Entry & Initialization      ${GREEN}◄ current${NC}"
    echo -e "    ${DIM}602${NC} Agent Selection"
    echo -e "    ${DIM}603${NC} Comprehensive Review"
    echo -e "    ${DIM}604${NC} Refinement"
    echo -e "    ${DIM}605${NC} Phase Audit"
    echo -e "    ${DIM}606${NC} Closeout"
    echo ""

    read -p "  Press Enter to begin Code Review..."
    echo ""

    atomic_success "Entry & Initialization complete"

    return 0
}
