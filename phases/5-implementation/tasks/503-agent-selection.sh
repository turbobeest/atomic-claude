#!/bin/bash
#
# Task 503: Agent Selection
# Select agents for TDD execution: test-writer, code-implementer, refactorer, security-scanner
#

task_503_agent_selection() {
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json"
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local specs_dir="$ATOMIC_ROOT/.claude/specs"
    # Check embedded repo first (monorepo deployment), then env var, then default
    local agent_repo="$ATOMIC_ROOT/repos/agents"
    [[ -f "$ATOMIC_ROOT/external/agents/agent-inventory.csv" ]] && agent_repo="$ATOMIC_ROOT/external/agents"
    [[ -n "$ATOMIC_AGENT_REPO" ]] && agent_repo="$ATOMIC_AGENT_REPO"
    local csv_path="$agent_repo/agent-inventory.csv"

    atomic_step "Agent Selection"

    mkdir -p "$(dirname "$agents_file")"

    echo ""
    echo -e "  ${DIM}Selecting specialized agents for each TDD phase from agent-inventory.csv.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # LOAD AVAILABLE AGENTS FROM CSV
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}AVAILABLE IMPLEMENTATION AGENTS${NC} (from agent-inventory.csv)"
    echo ""

    if [[ -f "$csv_path" ]]; then
        echo -e "  ${DIM}Agents in 06-09-implementation category:${NC}"
        echo ""
        awk -F',' 'NR > 1 && $6 == "06-09-implementation" {
            name = $1
            tier = $3
            model = $4
            role = $11
            printf "    %-28s [%-6s %-6s %s]\n", name, tier, model, role
        }' "$csv_path"
        echo ""
    else
        echo -e "  ${YELLOW}!${NC} Agent inventory not found - using defaults"
        echo ""
    fi

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
    # TDD AGENT ROLES (mapped to CSV agents)
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TDD AGENT ROLES${NC}"
    echo ""

    echo -e "  ${DIM}Four agents are needed for the TDD cycle (using agents from inventory):${NC}"
    echo ""

    # RED phase agent
    echo -e "  ${RED}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}RED: Test Strategist${NC}"
    echo ""
    echo -e "    Writes failing tests based on OpenSpec test strategy."
    echo -e "    Must understand testing frameworks, mocking, fixtures."
    echo ""
    echo -e "    ${CYAN}Recommended:${NC} test-strategist (expert, opus)"
    echo -e "  ${RED}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # GREEN phase agent
    echo -e "  ${GREEN}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}GREEN: TDD Implementation${NC}"
    echo ""
    echo -e "    Writes minimal implementation to make tests pass."
    echo -e "    Focus on correctness, not optimization."
    echo ""
    echo -e "    ${CYAN}Recommended:${NC} tdd-implementation-agent (phd, opus)"
    echo -e "  ${GREEN}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # REFACTOR phase agent
    echo -e "  ${CYAN}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}REFACTOR: Code Review Gate${NC}"
    echo ""
    echo -e "    Improves code quality while maintaining test passage."
    echo -e "    Runs linters, formatters, type checkers."
    echo ""
    echo -e "    ${CYAN}Recommended:${NC} code-review-gate (expert, opus)"
    echo -e "  ${CYAN}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # VERIFY phase agent
    echo -e "  ${MAGENTA}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}VERIFY: Plan Guardian${NC}"
    echo ""
    echo -e "    Verifies implementation against PRD and spec drift."
    echo -e "    Computes alignment scores and triggers gates."
    echo ""
    echo -e "    ${CYAN}Recommended:${NC} plan-guardian (phd, opus)"
    echo -e "  ${MAGENTA}─────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AGENT SELECTION (from CSV inventory)
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SELECT AGENTS${NC}"
    echo ""

    # Drain any buffered stdin before agent selection
    atomic_drain_stdin

    # Get models from CSV for each agent
    get_csv_model() {
        local agent="$1"
        if [[ -f "$csv_path" ]]; then
            grep "^${agent}," "$csv_path" | cut -d',' -f4
        else
            echo "opus"
        fi
    }

    # RED agent (test-strategist from CSV)
    echo -e "  ${RED}RED: Test Strategy${NC}"
    echo -e "    ${GREEN}[1]${NC} test-strategist (recommended - from inventory)"
    echo -e "    ${DIM}[2]${NC} specification-agent"
    echo ""

    read -e -p "    Selection [1]: " red_choice || true
    red_choice=${red_choice:-1}
    case "$red_choice" in
        2) red_agent="specification-agent" ;;
        *) red_agent="test-strategist" ;;
    esac
    red_model=$(get_csv_model "$red_agent")
    echo ""

    # GREEN agent (tdd-implementation-agent from CSV)
    echo -e "  ${GREEN}GREEN: TDD Implementation${NC}"
    echo -e "    ${GREEN}[1]${NC} tdd-implementation-agent (recommended - from inventory)"
    echo -e "    ${DIM}[2]${NC} specification-agent"
    echo ""

    read -e -p "    Selection [1]: " green_choice || true
    green_choice=${green_choice:-1}
    case "$green_choice" in
        2) green_agent="specification-agent" ;;
        *) green_agent="tdd-implementation-agent" ;;
    esac
    green_model=$(get_csv_model "$green_agent")
    echo ""

    # REFACTOR agent (code-review-gate from CSV)
    echo -e "  ${CYAN}REFACTOR: Code Review${NC}"
    echo -e "    ${GREEN}[1]${NC} code-review-gate (recommended - from inventory)"
    echo -e "    ${DIM}[2]${NC} plan-guardian"
    echo ""

    read -e -p "    Selection [1]: " refactor_choice || true
    refactor_choice=${refactor_choice:-1}
    case "$refactor_choice" in
        2) refactor_agent="plan-guardian" ;;
        *) refactor_agent="code-review-gate" ;;
    esac
    refactor_model=$(get_csv_model "$refactor_agent")
    echo ""

    # VERIFY agent (plan-guardian from CSV)
    echo -e "  ${MAGENTA}VERIFY: Drift Monitor${NC}"
    echo -e "    ${GREEN}[1]${NC} plan-guardian (recommended - from inventory)"
    echo -e "    ${DIM}[2]${NC} code-review-gate"
    echo ""

    read -e -p "    Selection [1]: " verify_choice || true
    verify_choice=${verify_choice:-1}
    case "$verify_choice" in
        2) verify_agent="code-review-gate" ;;
        *) verify_agent="plan-guardian" ;;
    esac
    verify_model=$(get_csv_model "$verify_agent")
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # OPTIONAL: EXPERT AGENTS FROM INVENTORY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}OPTIONAL: EXPERT AGENTS${NC}"
    echo ""

    echo -e "  ${DIM}Based on project patterns, consider adding expert agents from inventory:${NC}"
    echo ""

    local specialists=()

    # Show relevant expert agents from CSV based on detected patterns
    if [[ -f "$csv_path" ]]; then
        if [[ "$has_api" == "true" ]]; then
            echo -e "    ${CYAN}[api]${NC}      api-tester - API testing specialist"
        fi
        if [[ "$has_db" == "true" ]]; then
            echo -e "    ${CYAN}[db]${NC}       database-optimizer - Database operations"
        fi
        if [[ "$has_frontend" == "true" ]]; then
            echo -e "    ${CYAN}[ui]${NC}       frontend-developer - UI components"
        fi
        if [[ "$has_async" == "true" ]]; then
            echo -e "    ${CYAN}[async]${NC}    debugger - Async debugging"
        fi
    fi

    echo ""
    echo -e "  ${DIM}Enter comma-separated list of specialists (or Enter to skip):${NC}"
    read -e -p "    Specialists: " specialist_input || true

    if [[ -n "$specialist_input" ]]; then
        IFS=',' read -ra specialist_keys <<< "$specialist_input"
        # Map keys to actual agent names
        for key in "${specialist_keys[@]}"; do
            key=$(echo "$key" | tr -d ' ')
            case "$key" in
                api) specialists+=("api-tester") ;;
                db) specialists+=("database-optimizer") ;;
                ui) specialists+=("frontend-developer") ;;
                async) specialists+=("debugger") ;;
                *) specialists+=("$key") ;;  # Allow direct agent names
            esac
        done
        echo ""
        echo -e "  ${GREEN}✓${NC} Added ${#specialists[@]} specialist(s): ${specialists[*]}"
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SELECTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}AGENT SELECTION SUMMARY${NC} (from agent-inventory.csv)"
    echo ""

    echo -e "    ${RED}RED:${NC}       $red_agent ($red_model)"
    echo -e "    ${GREEN}GREEN:${NC}     $green_agent ($green_model)"
    echo -e "    ${CYAN}REFACTOR:${NC}  $refactor_agent ($refactor_model)"
    echo -e "    ${MAGENTA}VERIFY:${NC}    $verify_agent ($verify_model)"
    if [[ ${#specialists[@]} -gt 0 ]]; then
        echo -e "    ${DIM}Specialists:${NC} ${specialists[*]}"
    fi
    echo ""

    # Save agent selection with models from CSV
    local specialists_json=$(printf '%s\n' "${specialists[@]}" | jq -R . | jq -s .)

    jq -n \
        --arg red "$red_agent" \
        --arg red_model "$red_model" \
        --arg green "$green_agent" \
        --arg green_model "$green_model" \
        --arg refactor "$refactor_agent" \
        --arg refactor_model "$refactor_model" \
        --arg verify "$verify_agent" \
        --arg verify_model "$verify_model" \
        --argjson specialists "$specialists_json" \
        '{
            "tdd_agents": {
                "red": { "name": $red, "model": $red_model, "phase": "RED" },
                "green": { "name": $green, "model": $green_model, "phase": "GREEN" },
                "refactor": { "name": $refactor, "model": $refactor_model, "phase": "REFACTOR" },
                "verify": { "name": $verify, "model": $verify_model, "phase": "VERIFY" }
            },
            "specialists": $specialists,
            "source": "agent-inventory.csv",
            "selected_at": (now | todate)
        }' > "$agents_file"

    atomic_context_artifact "$agents_file" "tdd-agents" "Selected TDD agents"
    atomic_context_decision "TDD agents: $red_agent → $green_agent → $refactor_agent → $verify_agent" "agent-selection"

    atomic_success "Agent Selection complete"

    return 0
}
