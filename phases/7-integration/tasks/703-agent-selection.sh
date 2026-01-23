#!/bin/bash
#
# Task 703: Agent Selection
# Present and select integration testing agents
#

task_703_agent_selection() {
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/integration-agents.json"
    local roster_file="$ATOMIC_ROOT/.claude/agent-roster.json"

    atomic_step "Agent Selection"

    echo ""
    echo -e "  ${DIM}Select agents for integration testing.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INTEGRATION WORKFLOW
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- INTEGRATION WORKFLOW${NC}"
    echo ""

    echo -e "    E2E Test Runner ────────┐"
    echo -e "        ${DIM}(test flows)${NC}        │"
    echo -e "                            ├→  Acceptance Validator  →  Integration Reporter"
    echo -e "    Performance Tester ─────┘      ${DIM}(all criteria)${NC}          ${DIM}(consolidate)${NC}"
    echo -e "        ${DIM}(benchmark NFRs)${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AVAILABLE AGENTS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- AVAILABLE AGENTS${NC}"
    echo ""

    # E2E Test Runner
    echo -e "  ${CYAN}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}E2E TEST RUNNER${NC}"
    echo ""
    echo -e "    Executes end-to-end test suites across all user flows."
    echo -e "    Validates complete system behavior from input to output."
    echo -e "    ${GREEN}Recommended:${NC} e2e-test-runner-phd (sonnet)"
    echo -e "  ${CYAN}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # Acceptance Validator
    echo -e "  ${MAGENTA}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}ACCEPTANCE VALIDATOR${NC}"
    echo ""
    echo -e "    Validates each acceptance criterion from PRD."
    echo -e "    Maps requirements to test evidence."
    echo -e "    ${GREEN}Recommended:${NC} acceptance-validator-phd (sonnet)"
    echo -e "  ${MAGENTA}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # Performance Tester
    echo -e "  ${YELLOW}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}PERFORMANCE TESTER${NC}"
    echo ""
    echo -e "    Benchmarks system against NFR targets."
    echo -e "    Measures response times, memory, throughput."
    echo -e "    ${GREEN}Recommended:${NC} performance-tester-phd (haiku)"
    echo -e "  ${YELLOW}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # Integration Reporter
    echo -e "  ${BLUE}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}INTEGRATION REPORTER${NC}"
    echo ""
    echo -e "    Generates comprehensive integration report."
    echo -e "    Consolidates results from all testing agents."
    echo -e "    ${GREEN}Recommended:${NC} integration-reporter-phd (haiku)"
    echo -e "  ${BLUE}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AGENT SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- AGENT SELECTION${NC}"
    echo ""

    echo -e "  ${DIM}Select agents for each role:${NC}"
    echo ""

    local selected_agents=()

    # E2E Test Runner selection
    echo -e "  ${CYAN}E2E Test Runner:${NC}"
    echo -e "    ${GREEN}[1]${NC} e2e-test-runner-phd (sonnet) - Recommended"
    echo -e "    ${DIM}[2]${NC} e2e-test-runner (haiku) - Fast, standard"
    echo -e "    ${YELLOW}[c]${NC} Custom agent"
    echo ""
    read -p "  Select [1]: " e2e_choice
    e2e_choice=${e2e_choice:-1}

    case "$e2e_choice" in
        1) selected_agents+=("e2e-test-runner-phd:sonnet") ;;
        2) selected_agents+=("e2e-test-runner:haiku") ;;
        c|C)
            read -p "  Custom agent name: " custom_name
            read -p "  Custom agent model [sonnet]: " custom_model
            custom_model=${custom_model:-sonnet}
            selected_agents+=("$custom_name:$custom_model")
            ;;
        *) selected_agents+=("e2e-test-runner-phd:sonnet") ;;
    esac
    echo ""

    # Acceptance Validator selection
    echo -e "  ${MAGENTA}Acceptance Validator:${NC}"
    echo -e "    ${GREEN}[1]${NC} acceptance-validator-phd (sonnet) - Recommended"
    echo -e "    ${DIM}[2]${NC} acceptance-validator (haiku) - Fast, standard"
    echo -e "    ${YELLOW}[c]${NC} Custom agent"
    echo ""
    read -p "  Select [1]: " accept_choice
    accept_choice=${accept_choice:-1}

    case "$accept_choice" in
        1) selected_agents+=("acceptance-validator-phd:sonnet") ;;
        2) selected_agents+=("acceptance-validator:haiku") ;;
        c|C)
            read -p "  Custom agent name: " custom_name
            read -p "  Custom agent model [sonnet]: " custom_model
            custom_model=${custom_model:-sonnet}
            selected_agents+=("$custom_name:$custom_model")
            ;;
        *) selected_agents+=("acceptance-validator-phd:sonnet") ;;
    esac
    echo ""

    # Performance Tester selection
    echo -e "  ${YELLOW}Performance Tester:${NC}"
    echo -e "    ${GREEN}[1]${NC} performance-tester-phd (haiku) - Recommended"
    echo -e "    ${DIM}[2]${NC} performance-tester-deep (sonnet) - Thorough"
    echo -e "    ${YELLOW}[c]${NC} Custom agent"
    echo ""
    read -p "  Select [1]: " perf_choice
    perf_choice=${perf_choice:-1}

    case "$perf_choice" in
        1) selected_agents+=("performance-tester-phd:haiku") ;;
        2) selected_agents+=("performance-tester-deep:sonnet") ;;
        c|C)
            read -p "  Custom agent name: " custom_name
            read -p "  Custom agent model [haiku]: " custom_model
            custom_model=${custom_model:-haiku}
            selected_agents+=("$custom_name:$custom_model")
            ;;
        *) selected_agents+=("performance-tester-phd:haiku") ;;
    esac
    echo ""

    # Integration Reporter selection
    echo -e "  ${BLUE}Integration Reporter:${NC}"
    echo -e "    ${GREEN}[1]${NC} integration-reporter-phd (haiku) - Recommended"
    echo -e "    ${DIM}[2]${NC} integration-reporter-detailed (sonnet) - Comprehensive"
    echo -e "    ${YELLOW}[c]${NC} Custom agent"
    echo ""
    read -p "  Select [1]: " report_choice
    report_choice=${report_choice:-1}

    case "$report_choice" in
        1) selected_agents+=("integration-reporter-phd:haiku") ;;
        2) selected_agents+=("integration-reporter-detailed:sonnet") ;;
        c|C)
            read -p "  Custom agent name: " custom_name
            read -p "  Custom agent model [haiku]: " custom_model
            custom_model=${custom_model:-haiku}
            selected_agents+=("$custom_name:$custom_model")
            ;;
        *) selected_agents+=("integration-reporter-phd:haiku") ;;
    esac
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SELECTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- SELECTION SUMMARY${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}SELECTED AGENTS${NC}"
    echo ""
    for agent in "${selected_agents[@]}"; do
        IFS=':' read -r name model <<< "$agent"
        echo -e "    ${GREEN}✓${NC} $name ($model)"
    done
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # Save agent selection
    local agents_json=$(printf '%s\n' "${selected_agents[@]}" | jq -R . | jq -s .)

    jq -n \
        --argjson agents "$agents_json" \
        '{
            "phase": 7,
            "agents": $agents,
            "selected_at": (now | todate)
        }' > "$agents_file"

    atomic_context_artifact "$agents_file" "integration-agents" "Selected integration agents"
    atomic_context_decision "Integration agents selected: ${#selected_agents[@]} agents" "agents"

    atomic_success "Agent Selection complete"

    return 0
}
