#!/bin/bash
#
# Task 402: Agent Selection
# Select and configure agents for OpenSpec generation
#

task_402_agent_selection() {
    local roster_file="$ATOMIC_ROOT/.claude/agent-roster.json"
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"

    atomic_step "Agent Selection"

    echo ""
    echo -e "  ${DIM}Selecting agents for OpenSpec generation and TDD subtask creation.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AGENT EDUCATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SPECIFICATION AGENTS${NC}"
    echo ""
    echo -e "  ${DIM}These agents specialize in different aspects of specification writing:${NC}"
    echo ""

    echo -e "  ${CYAN}CORE AGENTS (Required)${NC}"
    echo ""
    echo -e "    ${BOLD}spec-writer${NC} (opus)"
    echo -e "    ${DIM}Creates comprehensive OpenSpec definitions from task descriptions.${NC}"
    echo -e "    ${DIM}Expertise: Test strategies, interface contracts, acceptance criteria.${NC}"
    echo ""
    echo -e "    ${BOLD}tdd-structurer${NC} (sonnet)"
    echo -e "    ${DIM}Generates RED/GREEN/REFACTOR/VERIFY subtask chains.${NC}"
    echo -e "    ${DIM}Expertise: TDD methodology, subtask dependencies, acceptance tests.${NC}"
    echo ""

    echo -e "  ${YELLOW}SPECIALIST AGENTS (Optional)${NC}"
    echo ""
    echo -e "    ${BOLD}interface-definer${NC} (sonnet)"
    echo -e "    ${DIM}Defines precise input/output contracts and error conditions.${NC}"
    echo -e "    ${DIM}Best for: APIs, data models, service boundaries.${NC}"
    echo ""
    echo -e "    ${BOLD}test-strategist${NC} (sonnet)"
    echo -e "    ${DIM}Designs test pyramids and coverage strategies.${NC}"
    echo -e "    ${DIM}Best for: Complex testing requirements, Gherkin scenarios.${NC}"
    echo ""
    echo -e "    ${BOLD}security-specifier${NC} (haiku)"
    echo -e "    ${DIM}Identifies security requirements and validation needs.${NC}"
    echo -e "    ${DIM}Best for: Auth flows, data handling, input validation.${NC}"
    echo ""
    echo -e "    ${BOLD}edge-case-hunter${NC} (haiku)"
    echo -e "    ${DIM}Finds boundary conditions and error scenarios.${NC}"
    echo -e "    ${DIM}Best for: Robust specifications, defensive design.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PROJECT ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PROJECT ANALYSIS${NC}"
    echo ""

    # Analyze task characteristics
    local task_count=$(jq '.tasks | length // 0' "$tasks_file" 2>/dev/null || echo 0)
    local has_api=$(jq '[.tasks[].title | test("API|endpoint|service|REST|GraphQL"; "i")] | any' "$tasks_file" 2>/dev/null || echo "false")
    local has_auth=$(jq '[.tasks[].title | test("auth|login|session|token|permission"; "i")] | any' "$tasks_file" 2>/dev/null || echo "false")
    local has_data=$(jq '[.tasks[].title | test("database|model|schema|migration|data"; "i")] | any' "$tasks_file" 2>/dev/null || echo "false")
    local complex_count=$(jq '[.tasks[] | select(.estimated_complexity == "complex")] | length' "$tasks_file" 2>/dev/null || echo 0)

    echo -e "  ${DIM}Based on your tasks:${NC}"
    echo ""

    local recommended_agents=("spec-writer" "tdd-structurer")
    local recommendation_reasons=()

    if [[ "$has_api" == "true" ]]; then
        echo -e "    ${GREEN}✓${NC} API/service tasks detected → ${BOLD}interface-definer${NC} recommended"
        recommended_agents+=("interface-definer")
        recommendation_reasons+=("API contracts")
    fi

    if [[ "$has_auth" == "true" ]]; then
        echo -e "    ${GREEN}✓${NC} Authentication tasks detected → ${BOLD}security-specifier${NC} recommended"
        recommended_agents+=("security-specifier")
        recommendation_reasons+=("Security requirements")
    fi

    if [[ "$complex_count" -gt 2 ]]; then
        echo -e "    ${GREEN}✓${NC} $complex_count complex tasks → ${BOLD}edge-case-hunter${NC} recommended"
        recommended_agents+=("edge-case-hunter")
        recommendation_reasons+=("Complex edge cases")
    fi

    if [[ "$task_count" -gt 10 ]]; then
        echo -e "    ${GREEN}✓${NC} $task_count tasks → ${BOLD}test-strategist${NC} recommended"
        recommended_agents+=("test-strategist")
        recommendation_reasons+=("Test coverage strategy")
    fi

    if [[ ${#recommendation_reasons[@]} -eq 0 ]]; then
        echo -e "    ${DIM}No specific patterns detected - using core agents only${NC}"
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AGENT SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SELECT AGENT CONFIGURATION${NC}"
    echo ""

    local rec_string=$(IFS=', '; echo "${recommended_agents[*]}")
    echo -e "  ${DIM}Recommended: ${rec_string}${NC}"
    echo ""

    echo -e "  ${CYAN}Options:${NC}"
    echo ""
    echo -e "    ${GREEN}[approve]${NC}    Use recommended agents (${#recommended_agents[@]} agents)"
    echo -e "    ${YELLOW}[core]${NC}       Core agents only (spec-writer, tdd-structurer)"
    echo -e "    ${CYAN}[full]${NC}       All 6 agents (most thorough)"
    echo -e "    ${MAGENTA}[custom]${NC}     Select specific agents"
    echo -e "    ${DIM}[list]${NC}       Show agent details again"
    echo ""

    local selected_agents=()

    while true; do
        read -p "  Choice [approve]: " agent_choice
        agent_choice=${agent_choice:-approve}

        case "$agent_choice" in
            approve)
                selected_agents=("${recommended_agents[@]}")
                break
                ;;
            core)
                selected_agents=("spec-writer" "tdd-structurer")
                break
                ;;
            full)
                selected_agents=("spec-writer" "tdd-structurer" "interface-definer" "test-strategist" "security-specifier" "edge-case-hunter")
                break
                ;;
            custom)
                echo ""
                echo -e "  ${DIM}Available agents:${NC}"
                echo -e "    1. spec-writer (required)"
                echo -e "    2. tdd-structurer (required)"
                echo -e "    3. interface-definer"
                echo -e "    4. test-strategist"
                echo -e "    5. security-specifier"
                echo -e "    6. edge-case-hunter"
                echo ""
                read -p "  Enter numbers (e.g., '1 2 3 5'): " custom_selection

                selected_agents=("spec-writer" "tdd-structurer")  # Always include core
                for num in $custom_selection; do
                    case "$num" in
                        3) selected_agents+=("interface-definer") ;;
                        4) selected_agents+=("test-strategist") ;;
                        5) selected_agents+=("security-specifier") ;;
                        6) selected_agents+=("edge-case-hunter") ;;
                    esac
                done
                break
                ;;
            list)
                echo ""
                echo -e "  ${CYAN}Agent Details:${NC}"
                echo -e "    spec-writer      - Creates OpenSpec JSON from task descriptions"
                echo -e "    tdd-structurer   - Generates RED/GREEN/REFACTOR/VERIFY chains"
                echo -e "    interface-definer - Defines API contracts (inputs/outputs/errors)"
                echo -e "    test-strategist  - Designs test pyramids and Gherkin scenarios"
                echo -e "    security-specifier - Identifies auth and validation requirements"
                echo -e "    edge-case-hunter - Finds boundary conditions and error paths"
                echo ""
                ;;
            *)
                echo -e "  ${RED}Invalid choice. Try again.${NC}"
                ;;
        esac
    done

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CONFIRM ROSTER
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}CONFIRMED ROSTER${NC}"
    echo ""

    for agent in "${selected_agents[@]}"; do
        local model="sonnet"
        [[ "$agent" == "spec-writer" ]] && model="opus"
        [[ "$agent" == "security-specifier" || "$agent" == "edge-case-hunter" ]] && model="haiku"
        echo -e "    ${GREEN}✓${NC} $agent ($model)"
    done
    echo ""

    # Save roster
    mkdir -p "$(dirname "$roster_file")"

    local agents_json=$(printf '%s\n' "${selected_agents[@]}" | jq -R . | jq -s .)

    jq -n \
        --argjson agents "$agents_json" \
        --argjson task_count "$task_count" \
        '{
            "phase": 4,
            "phase_name": "Specification",
            "agents": $agents,
            "task_count": $task_count,
            "confirmed_at": (now | todate)
        }' > "$roster_file"

    atomic_context_artifact "$roster_file" "agent-roster" "Phase 4 agent roster"
    atomic_context_decision "Selected ${#selected_agents[@]} agents for specification: ${selected_agents[*]}" "agents"

    atomic_success "Agent Selection complete"

    return 0
}
