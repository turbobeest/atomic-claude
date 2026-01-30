#!/bin/bash
#
# Task 402: Agent Selection
# Select and configure agents for OpenSpec generation
#

task_402_agent_selection() {
    local roster_file="$ATOMIC_ROOT/.claude/agent-roster.json"
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local agent_repo="${ATOMIC_AGENT_REPO:-$ATOMIC_ROOT/repos/agents}"
    local csv_path="$agent_repo/agent-inventory.csv"

    atomic_step "Agent Selection"

    echo ""
    echo -e "  ${DIM}Selecting agents for OpenSpec generation and TDD subtask creation.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # LOAD AGENTS FROM CSV INVENTORY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SPECIFICATION AGENTS${NC} (from agent-inventory.csv)"
    echo ""

    # Get agents for implementation phases (06-09 covers specification work)
    local impl_agents=""
    if [[ -f "$csv_path" ]]; then
        impl_agents=$(awk -F',' 'NR > 1 && $6 == "06-09-implementation" {print $1}' "$csv_path")
        echo -e "  ${DIM}Available agents from inventory:${NC}"
        echo ""

        while IFS= read -r agent_name; do
            [[ -z "$agent_name" ]] && continue
            local csv_line=$(grep "^${agent_name}," "$csv_path")
            local tier=$(echo "$csv_line" | cut -d',' -f3)
            local model=$(echo "$csv_line" | cut -d',' -f4)
            local role=$(echo "$csv_line" | cut -d',' -f11)
            # Extract description (field 8)
            local desc=$(echo "$csv_line" | cut -d',' -f8 | sed 's/^"//;s/"$//' | head -c 70)

            case "$role" in
                executor) echo -e "    ${GREEN}●${NC} ${BOLD}$agent_name${NC} [$tier, $model]" ;;
                gatekeeper) echo -e "    ${CYAN}●${NC} ${BOLD}$agent_name${NC} [$tier, $model]" ;;
                strategist) echo -e "    ${YELLOW}●${NC} ${BOLD}$agent_name${NC} [$tier, $model]" ;;
                *) echo -e "    ${DIM}●${NC} ${BOLD}$agent_name${NC} [$tier, $model]" ;;
            esac
            echo -e "      ${DIM}${desc}...${NC}"
            echo ""
        done <<< "$impl_agents"
    else
        echo -e "  ${YELLOW}!${NC} Agent inventory not found at $csv_path"
        echo -e "  ${DIM}Using fallback agent list${NC}"
        echo ""
        echo -e "    ${BOLD}specification-agent${NC} - Creates OpenSpec definitions"
        echo -e "    ${BOLD}tdd-implementation-agent${NC} - TDD methodology implementation"
        echo -e "    ${BOLD}test-strategist${NC} - Test pyramid and coverage design"
        echo -e "    ${BOLD}code-review-gate${NC} - Code quality validation"
        echo -e "    ${BOLD}plan-guardian${NC} - Implementation drift monitoring"
        echo ""
    fi

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

    # Core agents from CSV (always recommended for specification phase)
    local recommended_agents=("specification-agent" "tdd-implementation-agent")
    local recommendation_reasons=()

    if [[ "$has_api" == "true" ]]; then
        echo -e "    ${GREEN}✓${NC} API/service tasks detected → ${BOLD}specification-agent${NC} for interface contracts"
        recommendation_reasons+=("API contracts")
    fi

    if [[ "$has_auth" == "true" ]]; then
        echo -e "    ${GREEN}✓${NC} Authentication tasks detected → ${BOLD}code-review-gate${NC} for security review"
        recommended_agents+=("code-review-gate")
        recommendation_reasons+=("Security requirements")
    fi

    if [[ "$complex_count" -gt 2 ]]; then
        echo -e "    ${GREEN}✓${NC} $complex_count complex tasks → ${BOLD}test-strategist${NC} for edge cases"
        recommended_agents+=("test-strategist")
        recommendation_reasons+=("Complex edge cases")
    fi

    if [[ "$task_count" -gt 10 ]]; then
        echo -e "    ${GREEN}✓${NC} $task_count tasks → ${BOLD}test-strategist${NC} for coverage strategy"
        if [[ ! " ${recommended_agents[*]} " =~ " test-strategist " ]]; then
            recommended_agents+=("test-strategist")
        fi
        recommendation_reasons+=("Test coverage strategy")
    fi

    # Always recommend plan-guardian for drift monitoring on larger projects
    if [[ "$task_count" -gt 5 ]]; then
        recommended_agents+=("plan-guardian")
        recommendation_reasons+=("Drift monitoring")
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

    # Build list of all available agents from CSV
    local all_impl_agents=()
    if [[ -f "$csv_path" ]]; then
        while IFS= read -r agent; do
            [[ -n "$agent" ]] && all_impl_agents+=("$agent")
        done < <(awk -F',' 'NR > 1 && $6 == "06-09-implementation" {print $1}' "$csv_path")
    else
        all_impl_agents=("specification-agent" "tdd-implementation-agent" "test-strategist" "code-review-gate" "plan-guardian")
    fi

    echo -e "  ${CYAN}Options:${NC}"
    echo ""
    echo -e "    ${GREEN}[approve]${NC}    Use recommended agents (${#recommended_agents[@]} agents)"
    echo -e "    ${YELLOW}[core]${NC}       Core agents only (specification-agent, tdd-implementation-agent)"
    echo -e "    ${CYAN}[full]${NC}       All ${#all_impl_agents[@]} implementation agents"
    echo -e "    ${MAGENTA}[custom]${NC}     Select specific agents from inventory"
    echo -e "    ${DIM}[list]${NC}       Show agent inventory again"
    echo ""

    local selected_agents=()

    while true; do
        atomic_drain_stdin
        read -e -p "  Choice [approve]: " agent_choice || true
        agent_choice=${agent_choice:-approve}

        case "$agent_choice" in
            approve)
                selected_agents=("${recommended_agents[@]}")
                break
                ;;
            core)
                selected_agents=("specification-agent" "tdd-implementation-agent")
                break
                ;;
            full)
                selected_agents=("${all_impl_agents[@]}")
                break
                ;;
            custom)
                echo ""
                echo -e "  ${DIM}Available agents from inventory:${NC}"
                local idx=1
                for agent in "${all_impl_agents[@]}"; do
                    if [[ "$agent" == "specification-agent" || "$agent" == "tdd-implementation-agent" ]]; then
                        echo -e "    $idx. $agent (required)"
                    else
                        echo -e "    $idx. $agent"
                    fi
                    ((idx++))
                done
                echo ""
                read -e -p "  Enter numbers (e.g., '1 2 3'): " custom_selection || true

                # Always include core agents
                selected_agents=("specification-agent" "tdd-implementation-agent")
                for num in $custom_selection; do
                    local agent_idx=$((num - 1))
                    if [[ $agent_idx -ge 0 && $agent_idx -lt ${#all_impl_agents[@]} ]]; then
                        local selected="${all_impl_agents[$agent_idx]}"
                        # Avoid duplicates
                        if [[ ! " ${selected_agents[*]} " =~ " ${selected} " ]]; then
                            selected_agents+=("$selected")
                        fi
                    fi
                done
                break
                ;;
            list)
                echo ""
                echo -e "  ${CYAN}Agent Inventory (06-09-implementation):${NC}"
                if [[ -f "$csv_path" ]]; then
                    awk -F',' 'NR > 1 && $6 == "06-09-implementation" {
                        name = $1
                        tier = $3
                        role = $11
                        # Extract first 60 chars of description
                        desc = $8
                        gsub(/^"|"$/, "", desc)
                        if(length(desc) > 60) desc = substr(desc, 1, 57) "..."
                        printf "    %-25s [%s, %s] %s\n", name, tier, role, desc
                    }' "$csv_path"
                else
                    echo -e "    ${DIM}(inventory not available)${NC}"
                fi
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
        # Look up model from CSV
        local model="sonnet"
        if [[ -f "$csv_path" ]]; then
            local csv_model=$(grep "^${agent}," "$csv_path" | cut -d',' -f4)
            [[ -n "$csv_model" ]] && model="$csv_model"
        fi
        echo -e "    ${GREEN}✓${NC} $agent ($model)"
    done
    echo ""

    # Save roster with model info from CSV
    mkdir -p "$(dirname "$roster_file")"

    # Build agents array with model info
    local agents_with_models="["
    local first=true
    for agent in "${selected_agents[@]}"; do
        local model="sonnet"
        if [[ -f "$csv_path" ]]; then
            local csv_model=$(grep "^${agent}," "$csv_path" | cut -d',' -f4)
            [[ -n "$csv_model" ]] && model="$csv_model"
        fi
        if [[ "$first" == "true" ]]; then
            first=false
        else
            agents_with_models+=","
        fi
        agents_with_models+="\"${agent}:${model}\""
    done
    agents_with_models+="]"

    jq -n \
        --argjson agents "$agents_with_models" \
        --argjson task_count "$task_count" \
        '{
            "phase": 4,
            "phase_name": "Specification",
            "agents": $agents,
            "task_count": $task_count,
            "source": "agent-inventory.csv",
            "confirmed_at": (now | todate)
        }' > "$roster_file"

    atomic_context_artifact "$roster_file" "agent-roster" "Phase 4 agent roster"
    atomic_context_decision "Selected ${#selected_agents[@]} agents for specification: ${selected_agents[*]}" "agents"

    atomic_success "Agent Selection complete"

    return 0
}
