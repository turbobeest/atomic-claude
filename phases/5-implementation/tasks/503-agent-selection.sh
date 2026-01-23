#!/bin/bash
#
# Task 503: Agent Selection
# Select agents for TDD execution: test-writer, code-implementer, refactorer, security-scanner
#

task_503_agent_selection() {
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json"
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local specs_dir="$ATOMIC_ROOT/.claude/specs"

    atomic_step "Agent Selection"

    mkdir -p "$(dirname "$agents_file")"

    echo ""
    echo -e "  ${DIM}Selecting specialized agents for each TDD phase.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PROJECT ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PROJECT ANALYSIS${NC}"
    echo ""

    # Analyze project characteristics
    local has_api=false
    local has_db=false
    local has_frontend=false
    local has_cli=false
    local has_async=false

    # Check specs for patterns
    if [[ -d "$specs_dir" ]]; then
        grep -l "api\|endpoint\|REST\|GraphQL" "$specs_dir"/*.json 2>/dev/null && has_api=true
        grep -l "database\|sql\|query\|ORM" "$specs_dir"/*.json 2>/dev/null && has_db=true
        grep -l "component\|render\|DOM\|React\|Vue" "$specs_dir"/*.json 2>/dev/null && has_frontend=true
        grep -l "command\|CLI\|argparse\|argv" "$specs_dir"/*.json 2>/dev/null && has_cli=true
        grep -l "async\|await\|concurrent\|parallel" "$specs_dir"/*.json 2>/dev/null && has_async=true
    fi

    echo -e "  ${DIM}Detected project patterns:${NC}"
    echo ""
    [[ "$has_api" == "true" ]] && echo -e "    ${GREEN}✓${NC} API endpoints"
    [[ "$has_db" == "true" ]] && echo -e "    ${GREEN}✓${NC} Database operations"
    [[ "$has_frontend" == "true" ]] && echo -e "    ${GREEN}✓${NC} Frontend components"
    [[ "$has_cli" == "true" ]] && echo -e "    ${GREEN}✓${NC} CLI interface"
    [[ "$has_async" == "true" ]] && echo -e "    ${GREEN}✓${NC} Async/concurrent code"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TDD AGENT ROLES
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TDD AGENT ROLES${NC}"
    echo ""

    echo -e "  ${DIM}Four agents are needed for the TDD cycle:${NC}"
    echo ""

    # RED phase agent
    echo -e "  ${RED}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}RED: Test Writer${NC}"
    echo ""
    echo -e "    Writes failing tests based on OpenSpec test strategy."
    echo -e "    Must understand testing frameworks, mocking, fixtures."
    echo ""
    echo -e "    ${CYAN}Recommended:${NC} test-writer-phd (sonnet)"
    echo -e "    ${DIM}Alternative:${NC} unit-test-specialist, integration-test-expert"
    echo -e "  ${RED}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # GREEN phase agent
    echo -e "  ${GREEN}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}GREEN: Code Implementer${NC}"
    echo ""
    echo -e "    Writes minimal implementation to make tests pass."
    echo -e "    Focus on correctness, not optimization."
    echo ""
    echo -e "    ${CYAN}Recommended:${NC} code-implementer-phd (opus)"
    echo -e "    ${DIM}Alternative:${NC} backend-engineer, fullstack-developer"
    echo -e "  ${GREEN}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # REFACTOR phase agent
    echo -e "  ${CYAN}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}REFACTOR: Code Reviewer${NC}"
    echo ""
    echo -e "    Improves code quality while maintaining test passage."
    echo -e "    Runs linters, formatters, type checkers."
    echo ""
    echo -e "    ${CYAN}Recommended:${NC} code-reviewer-phd (sonnet)"
    echo -e "    ${DIM}Alternative:${NC} refactoring-specialist, clean-code-expert"
    echo -e "  ${CYAN}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # VERIFY phase agent
    echo -e "  ${MAGENTA}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}VERIFY: Security Scanner${NC}"
    echo ""
    echo -e "    Runs security scans and addresses critical issues."
    echo -e "    Checks for vulnerabilities, insecure patterns."
    echo ""
    echo -e "    ${CYAN}Recommended:${NC} security-scanner (haiku)"
    echo -e "    ${DIM}Alternative:${NC} security-auditor, vulnerability-expert"
    echo -e "  ${MAGENTA}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AGENT SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SELECT AGENTS${NC}"
    echo ""

    # RED agent
    echo -e "  ${RED}RED: Test Writer${NC}"
    echo -e "    ${GREEN}[1]${NC} test-writer-phd (recommended)"
    echo -e "    ${DIM}[2]${NC} unit-test-specialist"
    echo -e "    ${DIM}[3]${NC} integration-test-expert"
    echo ""

    read -p "    Selection [1]: " red_choice
    red_choice=${red_choice:-1}
    case "$red_choice" in
        2) red_agent="unit-test-specialist" ;;
        3) red_agent="integration-test-expert" ;;
        *) red_agent="test-writer-phd" ;;
    esac
    echo ""

    # GREEN agent
    echo -e "  ${GREEN}GREEN: Code Implementer${NC}"
    echo -e "    ${GREEN}[1]${NC} code-implementer-phd (recommended)"
    echo -e "    ${DIM}[2]${NC} backend-engineer"
    echo -e "    ${DIM}[3]${NC} fullstack-developer"
    echo ""

    read -p "    Selection [1]: " green_choice
    green_choice=${green_choice:-1}
    case "$green_choice" in
        2) green_agent="backend-engineer" ;;
        3) green_agent="fullstack-developer" ;;
        *) green_agent="code-implementer-phd" ;;
    esac
    echo ""

    # REFACTOR agent
    echo -e "  ${CYAN}REFACTOR: Code Reviewer${NC}"
    echo -e "    ${GREEN}[1]${NC} code-reviewer-phd (recommended)"
    echo -e "    ${DIM}[2]${NC} refactoring-specialist"
    echo -e "    ${DIM}[3]${NC} clean-code-expert"
    echo ""

    read -p "    Selection [1]: " refactor_choice
    refactor_choice=${refactor_choice:-1}
    case "$refactor_choice" in
        2) refactor_agent="refactoring-specialist" ;;
        3) refactor_agent="clean-code-expert" ;;
        *) refactor_agent="code-reviewer-phd" ;;
    esac
    echo ""

    # VERIFY agent
    echo -e "  ${MAGENTA}VERIFY: Security Scanner${NC}"
    echo -e "    ${GREEN}[1]${NC} security-scanner (recommended)"
    echo -e "    ${DIM}[2]${NC} security-auditor"
    echo -e "    ${DIM}[3]${NC} vulnerability-expert"
    echo ""

    read -p "    Selection [1]: " verify_choice
    verify_choice=${verify_choice:-1}
    case "$verify_choice" in
        2) verify_agent="security-auditor" ;;
        3) verify_agent="vulnerability-expert" ;;
        *) verify_agent="security-scanner" ;;
    esac
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # OPTIONAL: SPECIALIST AGENTS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}OPTIONAL: SPECIALIST AGENTS${NC}"
    echo ""

    echo -e "  ${DIM}Based on project patterns, consider adding specialists:${NC}"
    echo ""

    local specialists=()

    if [[ "$has_api" == "true" ]]; then
        echo -e "    ${CYAN}[api]${NC}      API test specialist (mock endpoints, contract testing)"
    fi
    if [[ "$has_db" == "true" ]]; then
        echo -e "    ${CYAN}[db]${NC}       Database test specialist (fixtures, transactions)"
    fi
    if [[ "$has_frontend" == "true" ]]; then
        echo -e "    ${CYAN}[ui]${NC}       UI test specialist (component testing, snapshots)"
    fi
    if [[ "$has_async" == "true" ]]; then
        echo -e "    ${CYAN}[async]${NC}    Async test specialist (race conditions, timeouts)"
    fi

    echo ""
    echo -e "  ${DIM}Enter comma-separated list of specialists (or Enter to skip):${NC}"
    read -p "    Specialists: " specialist_input

    if [[ -n "$specialist_input" ]]; then
        IFS=',' read -ra specialists <<< "$specialist_input"
        echo ""
        echo -e "  ${GREEN}✓${NC} Added ${#specialists[@]} specialist(s)"
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SELECTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}AGENT SELECTION SUMMARY${NC}"
    echo ""

    echo -e "    ${RED}RED:${NC}       $red_agent"
    echo -e "    ${GREEN}GREEN:${NC}     $green_agent"
    echo -e "    ${CYAN}REFACTOR:${NC}  $refactor_agent"
    echo -e "    ${MAGENTA}VERIFY:${NC}    $verify_agent"
    if [[ ${#specialists[@]} -gt 0 ]]; then
        echo -e "    ${DIM}Specialists:${NC} ${specialists[*]}"
    fi
    echo ""

    # Save agent selection
    local specialists_json=$(printf '%s\n' "${specialists[@]}" | jq -R . | jq -s .)

    jq -n \
        --arg red "$red_agent" \
        --arg green "$green_agent" \
        --arg refactor "$refactor_agent" \
        --arg verify "$verify_agent" \
        --argjson specialists "$specialists_json" \
        '{
            "tdd_agents": {
                "red": { "name": $red, "model": "sonnet", "phase": "RED" },
                "green": { "name": $green, "model": "opus", "phase": "GREEN" },
                "refactor": { "name": $refactor, "model": "sonnet", "phase": "REFACTOR" },
                "verify": { "name": $verify, "model": "haiku", "phase": "VERIFY" }
            },
            "specialists": $specialists,
            "selected_at": (now | todate)
        }' > "$agents_file"

    atomic_context_artifact "$agents_file" "tdd-agents" "Selected TDD agents"
    atomic_context_decision "TDD agents: $red_agent → $green_agent → $refactor_agent → $verify_agent" "agent-selection"

    atomic_success "Agent Selection complete"

    return 0
}
