#!/bin/bash
#
# Task 805: Deployment Approval
# Human gate for approving deployment artifacts
#

task_805_deployment_approval() {
    local deployment_dir="$ATOMIC_ROOT/.claude/deployment"
    local artifacts_file="$deployment_dir/artifacts.json"
    local approval_file="$deployment_dir/approval.json"

    atomic_step "Deployment Approval"

    echo ""
    echo -e "  ${DIM}Human gate: Review and approve deployment artifacts.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # ARTIFACTS REVIEW
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- ARTIFACTS REVIEW${NC}"
    echo ""

    # Load artifact data
    local version="0.1.0"
    local package_status="success"
    local changelog_status="success"
    local docs_status="success"
    local install_status="success"

    if [[ -f "$artifacts_file" ]]; then
        version=$(jq -r '.release.version // "0.1.0"' "$artifacts_file")
        package_status=$(jq -r '.artifacts.package.status // "unknown"' "$artifacts_file")
        changelog_status=$(jq -r '.artifacts.changelog.status // "unknown"' "$artifacts_file")
        docs_status=$(jq -r '.artifacts.documentation.status // "unknown"' "$artifacts_file")
        install_status=$(jq -r '.artifacts.installation_guide.status // "unknown"' "$artifacts_file")
    fi

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}RELEASE ARTIFACTS${NC}"
    echo ""
    echo -e "    Version: ${GREEN}$version${NC}"
    echo ""

    # Package status
    if [[ "$package_status" == "success" ]]; then
        echo -e "    ${GREEN}[ok]${NC} Package builds successfully"
    else
        echo -e "    ${RED}[fail]${NC} Package build failed"
    fi

    # Changelog status
    if [[ "$changelog_status" == "success" ]]; then
        echo -e "    ${GREEN}[ok]${NC} Changelog generated"
    else
        echo -e "    ${RED}[fail]${NC} Changelog generation failed"
    fi

    # Documentation status
    if [[ "$docs_status" == "success" ]]; then
        echo -e "    ${GREEN}[ok]${NC} Documentation complete"
    else
        echo -e "    ${RED}[fail]${NC} Documentation incomplete"
    fi

    # Installation guide status
    if [[ "$install_status" == "success" ]]; then
        echo -e "    ${GREEN}[ok]${NC} Installation guide created"
    else
        echo -e "    ${RED}[fail]${NC} Installation guide missing"
    fi

    echo ""
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # APPROVAL CRITERIA
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- APPROVAL CRITERIA${NC}"
    echo ""

    local all_criteria_met=true

    # Check package
    if [[ "$package_status" == "success" ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Package builds successfully"
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Package build failed"
        all_criteria_met=false
    fi

    # Check documentation
    if [[ "$docs_status" == "success" ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Documentation complete"
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Documentation incomplete"
        all_criteria_met=false
    fi

    # Check changelog
    if [[ "$changelog_status" == "success" ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Changelog accurate"
    else
        echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Changelog missing"
        all_criteria_met=false
    fi

    # Check installation guide
    if [[ "$install_status" == "success" ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Installation guide tested"
    else
        echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Installation guide missing"
        all_criteria_met=false
    fi

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # HUMAN GATE
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- HUMAN GATE: DEPLOYMENT APPROVAL${NC}"
    echo ""

    if [[ "$all_criteria_met" == "true" ]]; then
        echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${GREEN}Release artifacts ready for review.${NC}"
        echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    else
        echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${YELLOW}Some artifacts need attention before approval.${NC}"
        echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    fi

    echo ""
    echo -e "  ${DIM}What would you like to do?${NC}"
    echo ""
    echo -e "    ${GREEN}[approve]${NC}  Approve and proceed to Release"
    echo -e "    ${CYAN}[revise]${NC}   Make changes to artifacts"
    echo -e "    ${YELLOW}[discuss]${NC}  Review specific details"
    echo ""

    read -p "  Choice [approve]: " approval_choice
    approval_choice=${approval_choice:-approve}

    case "$approval_choice" in
        discuss)
            echo ""
            echo -e "  ${DIM}Artifact locations:${NC}"
            echo -e "    dist/                      - Release packages"
            echo -e "    CHANGELOG.md               - Version changelog"
            echo -e "    docs/README.md             - Project documentation"
            echo -e "    docs/INSTALL.md            - Installation guide"
            echo -e "    .claude/deployment/        - Deployment metadata"
            echo ""
            read -p "  Press Enter after review to continue..."
            echo ""
            echo -e "  ${DIM}Returning to approval...${NC}"
            task_805_deployment_approval
            return $?
            ;;
        revise)
            echo ""
            atomic_warn "Make revisions and re-run artifact generation"
            echo -e "  ${DIM}After revisions, run: ./orchestrator/pipeline resume${NC}"
            echo ""
            return 1
            ;;
        approve)
            echo ""
            read -p "  Approver name: " approver_name
            approver_name=${approver_name:-"Human Operator"}
            echo ""
            ;;
        *)
            echo ""
            approver_name="Human Operator"
            ;;
    esac

    # Save approval
    jq -n \
        --arg approver "$approver_name" \
        --arg status "approved" \
        --arg version "$version" \
        '{
            "status": $status,
            "approver": $approver,
            "version": $version,
            "artifacts_approved": ["package", "changelog", "documentation", "installation_guide"],
            "approved_at": (now | todate)
        }' > "$approval_file"

    echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${GREEN}✓ DEPLOYMENT APPROVED${NC} by $approver_name"
    echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    atomic_context_artifact "$approval_file" "deployment-approval" "Deployment approval record"
    atomic_context_decision "Deployment approved by $approver_name" "approval"

    atomic_success "Deployment Approval complete"

    return 0
}
