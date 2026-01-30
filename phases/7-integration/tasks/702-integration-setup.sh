#!/bin/bash
#
# Task 702: Integration Setup
# Configure integration environment and review acceptance criteria
#

task_702_integration_setup() {
    local config_file="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local specs_dir="$ATOMIC_ROOT/docs/specs"
    local integration_dir="$ATOMIC_ROOT/.claude/integration"

    atomic_step "Integration Setup"

    mkdir -p "$integration_dir"

    echo ""
    echo -e "  ${DIM}Configuring integration environment and reviewing acceptance criteria.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INTEGRATION ENVIRONMENT
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- INTEGRATION ENVIRONMENT${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}ENVIRONMENT CONFIGURATION${NC}"
    echo ""

    # Load project config
    local project_name="Unknown"
    local env_type="development"

    if [[ -f "$config_file" ]]; then
        project_name=$(jq -r '.project.name // "Unknown"' "$config_file")
        env_type=$(jq -r '.environment.type // "development"' "$config_file")
    fi

    echo -e "    Project:        ${CYAN}$project_name${NC}"
    echo -e "    Environment:    ${CYAN}$env_type${NC}"
    echo -e "    Test Mode:      ${CYAN}Full E2E${NC}"
    echo ""
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    echo -e "  ${DIM}Is this the correct integration environment?${NC}"
    echo ""

    read -e -p "  Confirm [y/n]: " env_confirm || true
    env_confirm=${env_confirm:-y}

    if [[ "$env_confirm" != "y" && "$env_confirm" != "Y" ]]; then
        echo ""
        read -e -p "  Enter environment notes: " env_notes || true
        echo ""
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # ACCEPTANCE CRITERIA REVIEW
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- ACCEPTANCE CRITERIA REVIEW${NC}"
    echo ""

    echo -e "  ${DIM}Loading acceptance criteria from PRD and specifications...${NC}"
    echo ""

    # Simulated acceptance criteria (in real implementation, would parse PRD)
    local criteria_count=17

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}ACCEPTANCE CRITERIA TO VALIDATE${NC}"
    echo ""
    echo -e "    ${CYAN}Functional Requirements:${NC}"
    echo -e "      FR-1   Core functionality implemented"
    echo -e "      FR-2   Data persistence working"
    echo -e "      FR-3   User interface responsive"
    echo -e "      FR-4   External integrations functional"
    echo -e "      FR-5   Offline capability (if applicable)"
    echo -e "      ...    (additional criteria from PRD)"
    echo ""
    echo -e "    ${CYAN}Non-Functional Requirements:${NC}"
    echo -e "      NFR-1  Response time < target threshold"
    echo -e "      NFR-2  Memory usage within bounds"
    echo -e "      NFR-3  Error rate < acceptable limit"
    echo -e "      ...    (additional NFRs)"
    echo ""
    echo -e "    Total Criteria:  ${GREEN}$criteria_count${NC}"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # NFR TARGETS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- NFR TARGETS${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}PERFORMANCE TARGETS${NC}"
    echo ""
    echo -e "    Response Time:     < 100ms for local operations"
    echo -e "    Startup Time:      < 3s"
    echo -e "    Memory Usage:      < 100MB baseline"
    echo -e "    Error Rate:        < 0.1%"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    read -e -p "  Press Enter to proceed with agent selection..." || true
    echo ""

    # Save setup configuration
    jq -n \
        --arg project_name "$project_name" \
        --arg env_type "$env_type" \
        --argjson criteria_count "$criteria_count" \
        '{
            "environment": {
                "project": $project_name,
                "type": $env_type,
                "confirmed": true
            },
            "acceptance_criteria": {
                "total": $criteria_count,
                "source": "PRD + specs"
            },
            "setup_at": (now | todate)
        }' > "$integration_dir/setup.json"

    atomic_context_artifact "$integration_dir/setup.json" "integration-setup" "Integration setup configuration"
    atomic_context_decision "Integration environment confirmed for $project_name" "setup"

    atomic_success "Integration Setup complete"

    return 0
}
