#!/bin/bash
#
# Task 401: Entry & Initialization
# Verify Phase 3 artifacts exist and initialize specification directory
#

task_401_entry_initialization() {
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local packages_file="$ATOMIC_ROOT/.taskmaster/reports/work-packages.json"
    local specs_dir="$ATOMIC_ROOT/.claude/specs"
    local phase3_closeout=$(atomic_find_closeout "3-tasking")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 4 WELCOME
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  PHASE 04 - SPECIFICATION${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}"
    cat << 'EOF'
           _______  _____  _______ __   _ _______ _____  _______  _______
           |     | |_____] |______ | \  | |______ |_____] |______ |
           |_____| |       |______ |  \_| ______| |       |______ |_____

     _______ _____  _______ _______ _____  _______ _____  _______ _______ _____  _____  __   _
     |______ |_____] |______ |         |   |______   |   |       |_____|   |   |     | | \  |
     ______| |       |______ |_____  __|__ |       __|__ |_____  |     |   |   |_____| |  \_|
EOF
    echo -e "${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${DIM}Verifying Phase 3 artifacts and preparing for OpenSpec generation.${NC}"
    echo ""

    atomic_step "Entry & Initialization"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PHASE 3 VERIFICATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PHASE 3 VERIFICATION${NC}"
    echo ""

    local verification_passed=true

    # Check Phase 3 closeout
    if [[ -f "$phase3_closeout" ]]; then
        local phase3_status=$(jq -r '.status // "unknown"' "$phase3_closeout")
        if [[ "$phase3_status" == "complete" ]]; then
            echo -e "  ${GREEN}✓${NC} Phase 3 closeout verified"
        else
            echo -e "  ${YELLOW}!${NC} Phase 3 closeout status: $phase3_status"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Phase 3 closeout not found (continuing anyway)"
    fi

    # Check tasks.json
    if [[ -f "$tasks_file" ]]; then
        local task_count=$(jq '.tasks | length // 0' "$tasks_file" 2>/dev/null || echo 0)
        if [[ "$task_count" -gt 0 ]]; then
            echo -e "  ${GREEN}✓${NC} tasks.json found ($task_count tasks)"
        else
            echo -e "  ${RED}✗${NC} tasks.json is empty"
            verification_passed=false
        fi
    else
        echo -e "  ${RED}✗${NC} tasks.json not found"
        verification_passed=false
    fi

    # Check work packages
    if [[ -f "$packages_file" ]]; then
        local pkg_count=$(jq '.packages | length // 0' "$packages_file" 2>/dev/null || echo 0)
        echo -e "  ${GREEN}✓${NC} work-packages.json found ($pkg_count packages)"
    else
        echo -e "  ${YELLOW}!${NC} work-packages.json not found (optional)"
    fi

    echo ""

    if [[ "$verification_passed" != "true" ]]; then
        echo -e "  ${RED}Phase 3 artifacts missing. Cannot proceed.${NC}"
        echo ""
        echo -e "  ${DIM}Run Phase 3 (Tasking) first to generate tasks.json${NC}"
        echo ""
        return 1
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TASK SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TASK SUMMARY${NC}"
    echo ""

    # Display task overview
    local high_priority=$(jq '[.tasks[] | select(.priority == "high")] | length' "$tasks_file" 2>/dev/null || echo 0)
    local medium_priority=$(jq '[.tasks[] | select(.priority == "medium")] | length' "$tasks_file" 2>/dev/null || echo 0)
    local low_priority=$(jq '[.tasks[] | select(.priority == "low")] | length' "$tasks_file" 2>/dev/null || echo 0)

    echo -e "    Total tasks:     $task_count"
    echo -e "    High priority:   $high_priority"
    echo -e "    Medium priority: $medium_priority"
    echo -e "    Low priority:    $low_priority"
    echo ""

    # Show first few tasks
    echo -e "  ${DIM}First 5 tasks:${NC}"
    jq -r '.tasks[:5][] | "    [\(.id)] \(.title)"' "$tasks_file" 2>/dev/null
    if [[ "$task_count" -gt 5 ]]; then
        echo -e "    ${DIM}... and $((task_count - 5)) more${NC}"
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INITIALIZE SPEC DIRECTORY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}INITIALIZE SPEC DIRECTORY${NC}"
    echo ""

    mkdir -p "$specs_dir"

    # Check for existing specs
    local existing_specs=$(find "$specs_dir" -name "spec-*.json" 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$existing_specs" -gt 0 ]]; then
        echo -e "  ${YELLOW}!${NC} Found $existing_specs existing spec files"
        echo ""
        echo -e "  ${CYAN}Options:${NC}"
        echo ""
        echo -e "    ${GREEN}[keep]${NC}     Keep existing specs, generate missing"
        echo -e "    ${YELLOW}[replace]${NC}  Replace all specs"
        echo -e "    ${RED}[abort]${NC}    Abort and review manually"
        echo ""

    atomic_drain_stdin
        read -e -p "  Choice [keep]: " spec_choice || true
        spec_choice=${spec_choice:-keep}

        case "$spec_choice" in
            replace)
                rm -f "$specs_dir"/spec-*.json
                echo -e "  ${GREEN}✓${NC} Cleared existing specs"
                ;;
            abort)
                atomic_error "Aborted by user"
                return 1
                ;;
            *)
                echo -e "  ${GREEN}✓${NC} Keeping existing specs"
                ;;
        esac
    else
        echo -e "  ${GREEN}✓${NC} Spec directory initialized: .claude/specs/"
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # OPENSPEC INTRODUCTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}WHAT IS OPENSPEC?${NC}"
    echo ""
    echo -e "  ${DIM}OpenSpec expands each task into a detailed specification containing:${NC}"
    echo ""
    echo -e "    ${CYAN}1. Test Strategy${NC}     - Unit tests, integration tests, Gherkin scenarios"
    echo -e "    ${CYAN}2. Interface Contracts${NC} - Inputs, outputs, error conditions"
    echo -e "    ${CYAN}3. Edge Cases${NC}        - Boundary conditions, error handling"
    echo -e "    ${CYAN}4. Security Requirements${NC} - Auth, validation, data protection"
    echo ""
    echo -e "  ${DIM}Then it creates 4 TDD subtasks for each task:${NC}"
    echo ""
    echo -e "    ${RED}RED${NC}       → Write failing tests (tests exist and FAIL)"
    echo -e "    ${GREEN}GREEN${NC}     → Minimal implementation (tests PASS)"
    echo -e "    ${CYAN}REFACTOR${NC}  → Clean up code (linting passes, tests still pass)"
    echo -e "    ${MAGENTA}VERIFY${NC}    → Security scan (no critical issues)"
    echo ""
    echo -e "  ${DIM}Each subtask depends on the previous: RED→GREEN→REFACTOR→VERIFY${NC}"
    echo ""

    read -e -p "  Press Enter to continue..." || true

    # Save initialization state
    local init_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/initialization.json"
    mkdir -p "$(dirname "$init_file")"

    jq -n \
        --argjson task_count "$task_count" \
        --argjson high "$high_priority" \
        --argjson medium "$medium_priority" \
        --argjson low "$low_priority" \
        --argjson existing_specs "$existing_specs" \
        '{
            "phase3_verified": true,
            "task_count": $task_count,
            "priority_breakdown": {
                "high": $high,
                "medium": $medium,
                "low": $low
            },
            "existing_specs": $existing_specs,
            "initialized_at": (now | todate)
        }' > "$init_file"

    atomic_context_artifact "$init_file" "initialization" "Phase 4 initialization state"
    atomic_context_decision "Phase 4 initialized with $task_count tasks to specify" "initialization"

    atomic_success "Entry & Initialization complete"

    return 0
}
