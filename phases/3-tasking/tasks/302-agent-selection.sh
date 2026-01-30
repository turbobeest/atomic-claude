#!/bin/bash
#
# Task 302: Agent Selection
# Analyze PRD and select agents for task decomposition
#
# This task:
#   1. Analyzes the PRD to understand project characteristics
#   2. Provides contextual guidance on agent selection
#   3. Recommends additional agents based on project specifics
#   4. Allows customization of agent composition
#
# Core agents (always included):
#   - task-decomposer (opus) - Break PRD into tasks
#   - dependency-mapper (sonnet) - Map task dependencies, build DAG
#   - work-packager (sonnet) - Group tasks for parallel execution
#
# Validation agents (always included):
#   - task-validator (sonnet) - Validate task quality
#   - coverage-checker (haiku) - Verify PRD coverage
#

task_302_agent_selection() {
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json"
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local analysis_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-analysis.json"

    atomic_step "Agent Selection"

    echo ""
    echo -e "  ${DIM}Analyzing your PRD to recommend the best agent composition.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # PRD ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PRD ANALYSIS${NC}"
    echo ""

    # Analyze PRD characteristics
    local has_api=false
    local has_auth=false
    local has_database=false
    local has_ui=false
    local has_testing=false
    local has_security=false
    local has_integration=false
    local has_performance=false
    local feature_count=0
    local nfr_count=0

    if [[ -f "$prd_file" ]]; then
        # Count features
        feature_count=$(grep -cE '^## Feature F[0-9]+' "$prd_file" 2>/dev/null || echo 0)

        # Count NFRs
        nfr_count=$(grep -cE '^## NFR-[0-9]+' "$prd_file" 2>/dev/null || echo 0)

        # Detect API patterns
        if grep -qiE 'api|endpoint|rest|graphql|grpc|webhook' "$prd_file" 2>/dev/null; then
            has_api=true
        fi

        # Detect authentication/authorization
        if grep -qiE 'auth|authentication|authorization|oauth|jwt|token|login|rbac|permission' "$prd_file" 2>/dev/null; then
            has_auth=true
        fi

        # Detect database patterns
        if grep -qiE 'database|sql|postgres|mysql|mongo|redis|schema|migration|orm' "$prd_file" 2>/dev/null; then
            has_database=true
        fi

        # Detect UI patterns
        if grep -qiE 'ui|interface|component|frontend|react|vue|angular|css|responsive' "$prd_file" 2>/dev/null; then
            has_ui=true
        fi

        # Detect testing emphasis
        if grep -qiE 'test coverage|unit test|integration test|e2e|tdd|pytest|vitest|jest' "$prd_file" 2>/dev/null; then
            has_testing=true
        fi

        # Detect security requirements
        if grep -qiE 'security|encryption|audit|compliance|vulnerability|sast|sca|owasp' "$prd_file" 2>/dev/null; then
            has_security=true
        fi

        # Detect external integrations
        if grep -qiE 'integration|third-party|external api|webhook|event|message queue|kafka|rabbitmq' "$prd_file" 2>/dev/null; then
            has_integration=true
        fi

        # Detect performance requirements
        if grep -qiE 'latency|throughput|performance|p99|p95|scalability|load|benchmark' "$prd_file" 2>/dev/null; then
            has_performance=true
        fi

        echo -e "  ${DIM}Scanned PRD for project characteristics...${NC}"
        echo ""
        echo -e "  ${BOLD}Project Profile:${NC}"
        echo ""
        echo -e "    Features:     $feature_count defined"
        echo -e "    NFRs:         $nfr_count defined"
        echo ""
        echo -e "  ${BOLD}Detected Patterns:${NC}"
        echo ""
        [[ "$has_api" == true ]] && echo -e "    ${GREEN}✓${NC} API/Endpoints"
        [[ "$has_auth" == true ]] && echo -e "    ${GREEN}✓${NC} Authentication/Authorization"
        [[ "$has_database" == true ]] && echo -e "    ${GREEN}✓${NC} Database/Data Layer"
        [[ "$has_ui" == true ]] && echo -e "    ${GREEN}✓${NC} User Interface"
        [[ "$has_testing" == true ]] && echo -e "    ${GREEN}✓${NC} Testing Emphasis"
        [[ "$has_security" == true ]] && echo -e "    ${GREEN}✓${NC} Security Requirements"
        [[ "$has_integration" == true ]] && echo -e "    ${GREEN}✓${NC} External Integrations"
        [[ "$has_performance" == true ]] && echo -e "    ${GREEN}✓${NC} Performance Requirements"

        # Check if nothing detected
        if [[ "$has_api" == false && "$has_auth" == false && "$has_database" == false && \
              "$has_ui" == false && "$has_security" == false && "$has_integration" == false ]]; then
            echo -e "    ${DIM}(No specific patterns detected - using core agents)${NC}"
        fi
        echo ""
    else
        echo -e "  ${YELLOW}!${NC} PRD not found - using default agent configuration"
        echo ""
    fi

    # Save analysis
    mkdir -p "$(dirname "$analysis_file")"

    jq -n \
        --argjson features "$feature_count" \
        --argjson nfrs "$nfr_count" \
        --argjson api "$has_api" \
        --argjson auth "$has_auth" \
        --argjson database "$has_database" \
        --argjson ui "$has_ui" \
        --argjson testing "$has_testing" \
        --argjson security "$has_security" \
        --argjson integration "$has_integration" \
        --argjson performance "$has_performance" \
        '{
            feature_count: $features,
            nfr_count: $nfrs,
            patterns: {
                api: $api,
                auth: $auth,
                database: $database,
                ui: $ui,
                testing: $testing,
                security: $security,
                integration: $integration,
                performance: $performance
            },
            analyzed_at: (now | todate)
        }' > "$analysis_file"

    # ─────────────────────────────────────────────────────────────────────────────
    # CORE AGENTS
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}CORE AGENTS${NC} ${DIM}(always included)${NC}"
    echo ""
    echo -e "  These agents form the backbone of task decomposition. They transform your"
    echo -e "  PRD into a structured task graph following the DAG (Directed Acyclic Graph)"
    echo -e "  pattern, enabling parallel execution in git worktrees."
    echo ""
    echo -e "    ${GREEN}task-decomposer${NC} (opus)"
    echo -e "      ${DIM}Parses PRD Section 4 (Features) and Section 10 (Task Decomposition).${NC}"
    echo -e "      ${DIM}Generates atomic tasks with acceptance criteria from EARS requirements.${NC}"
    echo -e "      ${DIM}Maps RFC 2119 keywords (SHALL/SHOULD/MAY) to task priorities.${NC}"
    echo ""
    echo -e "    ${GREEN}dependency-mapper${NC} (sonnet)"
    echo -e "      ${DIM}Builds the DAG from PRD dependency tables and task relationships.${NC}"
    echo -e "      ${DIM}Detects cycles, validates ordering, identifies critical path.${NC}"
    echo -e "      ${DIM}Enables parallel worktree execution for independent tasks.${NC}"
    echo ""
    echo -e "    ${GREEN}work-packager${NC} (sonnet)"
    echo -e "      ${DIM}Groups tasks into parallel execution packages based on DAG analysis.${NC}"
    echo -e "      ${DIM}Assigns tasks to worktrees, respects dependency constraints.${NC}"
    echo ""
    echo -e "    ${GREEN}task-validator${NC} (sonnet)"
    echo -e "      ${DIM}Validates task clarity, completeness, and actionability.${NC}"
    echo -e "      ${DIM}Ensures acceptance criteria are testable.${NC}"
    echo ""
    echo -e "    ${GREEN}coverage-checker${NC} (haiku)"
    echo -e "      ${DIM}Verifies all PRD features have corresponding tasks.${NC}"
    echo -e "      ${DIM}Maps tasks back to requirements for traceability.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # RECOMMENDED ADDITIONS
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}RECOMMENDED ADDITIONS${NC} ${DIM}(based on your PRD)${NC}"
    echo ""

    local recommendations=()
    local rec_reasons=()

    # API specialist
    if [[ "$has_api" == true ]]; then
        recommendations+=("api-task-specialist")
        rec_reasons+=("Your PRD includes API/endpoint definitions. This agent ensures API tasks include proper request/response validation, error handling, and versioning considerations.")
    fi

    # Security analyst
    if [[ "$has_auth" == true || "$has_security" == true ]]; then
        recommendations+=("security-task-analyst")
        rec_reasons+=("Your PRD includes authentication or security requirements. This agent adds security-focused subtasks and ensures OWASP considerations are addressed.")
    fi

    # Test strategy planner
    if [[ "$has_testing" == true || $feature_count -gt 5 ]]; then
        recommendations+=("test-strategy-planner")
        rec_reasons+=("Your PRD emphasizes testing or has many features. This agent pre-plans test approaches and ensures TDD phases (RED/GREEN/REFACTOR/VERIFY) are well-scoped.")
    fi

    # Data architect
    if [[ "$has_database" == true ]]; then
        recommendations+=("data-task-architect")
        rec_reasons+=("Your PRD includes database/data layer requirements. This agent ensures tasks properly sequence schema changes, migrations, and data access patterns.")
    fi

    # Integration specialist
    if [[ "$has_integration" == true ]]; then
        recommendations+=("integration-task-specialist")
        rec_reasons+=("Your PRD includes external integrations. This agent ensures integration tasks include proper error handling, retry logic, and fallback strategies.")
    fi

    if [[ ${#recommendations[@]} -eq 0 ]]; then
        echo -e "  ${DIM}No specific additions recommended - core agents are sufficient for this project.${NC}"
        echo ""
    else
        for i in "${!recommendations[@]}"; do
            echo -e "    ${YELLOW}${recommendations[$i]}${NC} (sonnet)"
            echo -e "      ${DIM}${rec_reasons[$i]}${NC}"
            echo ""
        done
    fi

    # ─────────────────────────────────────────────────────────────────────────────
    # SELECTION
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SELECTION${NC}"
    echo ""

    local decomposition_agents='["task-decomposer", "dependency-mapper", "work-packager"]'
    local validation_agents='["task-validator", "coverage-checker"]'
    local additional_agents='[]'

    if [[ ${#recommendations[@]} -gt 0 ]]; then
        echo -e "    ${GREEN}approve${NC}     Use core agents + recommendations (${#recommendations[@]} suggested)"
        echo -e "    ${CYAN}core${NC}        Use core agents only"
        echo -e "    ${YELLOW}custom${NC}      Customize agent selection"
        echo ""

        local agent_choice=""
        while [[ ! "$agent_choice" =~ ^(approve|core|custom)$ ]]; do
    atomic_drain_stdin
            read -e -p "  Choice [approve]: " agent_choice || true
            agent_choice=${agent_choice:-approve}
            if [[ ! "$agent_choice" =~ ^(approve|core|custom)$ ]]; then
                echo -e "  ${RED}Invalid choice.${NC} Enter: approve, core, or custom"
            fi
        done

        case "$agent_choice" in
            approve)
                for agent in "${recommendations[@]}"; do
                    additional_agents=$(echo "$additional_agents" | jq --arg a "$agent" '. += [$a]')
                done
                ;;
            custom)
                echo ""
                echo -e "  ${DIM}Select additional agents (space-separated numbers, or 'none'):${NC}"
                for i in "${!recommendations[@]}"; do
                    echo -e "    $((i+1)). ${recommendations[$i]}"
                done
                echo ""
                read -e -p "  > " custom_selection || true

                if [[ "$custom_selection" != "none" && -n "$custom_selection" ]]; then
                    for num in $custom_selection; do
                        local idx=$((num-1))
                        if [[ $idx -ge 0 && $idx -lt ${#recommendations[@]} ]]; then
                            additional_agents=$(echo "$additional_agents" | jq --arg a "${recommendations[$idx]}" '. += [$a]')
                        fi
                    done
                fi
                ;;
        esac
    else
        echo -e "    ${GREEN}approve${NC}     Use core agents"
        echo -e "    ${YELLOW}custom${NC}      Add custom agents"
        echo ""

        local agent_choice=""
        while [[ ! "$agent_choice" =~ ^(approve|custom)$ ]]; do
    atomic_drain_stdin
            read -e -p "  Choice [approve]: " agent_choice || true
            agent_choice=${agent_choice:-approve}
            if [[ ! "$agent_choice" =~ ^(approve|custom)$ ]]; then
                echo -e "  ${RED}Invalid choice.${NC} Enter: approve or custom"
            fi
        done

        if [[ "$agent_choice" == "custom" ]]; then
            echo ""
            echo -e "  ${DIM}Available additional agents:${NC}"
            echo -e "    1. api-task-specialist"
            echo -e "    2. security-task-analyst"
            echo -e "    3. test-strategy-planner"
            echo -e "    4. data-task-architect"
            echo -e "    5. integration-task-specialist"
            echo ""
            read -e -p "  Select (space-separated numbers): " custom_selection || true

            for num in $custom_selection; do
                case "$num" in
                    1) additional_agents=$(echo "$additional_agents" | jq '. += ["api-task-specialist"]') ;;
                    2) additional_agents=$(echo "$additional_agents" | jq '. += ["security-task-analyst"]') ;;
                    3) additional_agents=$(echo "$additional_agents" | jq '. += ["test-strategy-planner"]') ;;
                    4) additional_agents=$(echo "$additional_agents" | jq '. += ["data-task-architect"]') ;;
                    5) additional_agents=$(echo "$additional_agents" | jq '. += ["integration-task-specialist"]') ;;
                esac
            done
        fi
    fi

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}FINAL AGENT ROSTER${NC}"
    echo ""
    echo -e "  ${DIM}Decomposition Pipeline (sequential):${NC}"
    echo "$decomposition_agents" | jq -r '.[]' | while read -r agent; do
        echo -e "    • $agent"
    done
    echo ""
    echo -e "  ${DIM}Validation (parallel):${NC}"
    echo "$validation_agents" | jq -r '.[]' | while read -r agent; do
        echo -e "    • $agent"
    done
    if [[ "$additional_agents" != "[]" ]]; then
        echo ""
        echo -e "  ${DIM}Additional Specialists:${NC}"
        echo "$additional_agents" | jq -r '.[]' | while read -r agent; do
            echo -e "    • $agent"
        done
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # SAVE SELECTION
    # ─────────────────────────────────────────────────────────────────────────────

    mkdir -p "$(dirname "$agents_file")"

    jq -n \
        --argjson decomposition "$decomposition_agents" \
        --argjson validation "$validation_agents" \
        --argjson additional "$additional_agents" \
        --slurpfile analysis "$analysis_file" \
        '{
            phase: 3,
            phase_name: "Tasking",
            decomposition_agents: $decomposition,
            validation_agents: $validation,
            additional_agents: $additional,
            agent_pipeline: {
                sequential: $decomposition,
                parallel: $validation
            },
            prd_analysis: $analysis[0],
            selected_at: (now | todate)
        }' > "$agents_file"

    atomic_context_artifact "$agents_file" "selected-agents" "Phase 3 agent selection"
    atomic_context_artifact "$analysis_file" "prd-analysis" "PRD analysis for agent selection"
    atomic_context_decision "Agents selected based on PRD analysis" "agents"

    atomic_success "Agent selection complete"

    return 0
}
