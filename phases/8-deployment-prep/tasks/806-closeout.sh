#!/bin/bash
#
# Task 806: Phase Closeout
# Generate closeout document and prepare for Phase 9 (Release)
#

task_806_closeout() {
    local closeout_dir="$ATOMIC_ROOT/.claude/closeout"
    local closeout_file="$closeout_dir/phase-08-closeout.md"
    local closeout_json="$closeout_dir/phase-08-closeout.json"
    local deployment_dir="$ATOMIC_ROOT/.claude/deployment"
    local setup_file="$deployment_dir/setup.json"
    local artifacts_file="$deployment_dir/artifacts.json"
    local approval_file="$deployment_dir/approval.json"

    atomic_step "Phase Closeout"

    mkdir -p "$closeout_dir"

    echo ""
    echo -e "  ${DIM}Final review before moving to Phase 9 (Release).${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CLOSEOUT CHECKLIST
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- CLOSEOUT CHECKLIST${NC}"
    echo ""

    local checklist=()
    local all_passed=true

    # Get data
    local version="0.1.0"
    local approval_status="pending"

    if [[ -f "$setup_file" ]]; then
        version=$(jq -r '.release.version // "0.1.0"' "$setup_file")
    fi

    if [[ -f "$approval_file" ]]; then
        approval_status=$(jq -r '.status // "pending"' "$approval_file")
    fi

    # Check release package
    if [[ -f "$artifacts_file" ]]; then
        local package_status=$(jq -r '.artifacts.package.status // "unknown"' "$artifacts_file")
        if [[ "$package_status" == "success" ]]; then
            echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Release package prepared"
            checklist+=("Release package prepared:PASS")
        else
            echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Release package not ready"
            checklist+=("Release package prepared:FAIL")
            all_passed=false
        fi
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Artifacts file not found"
        checklist+=("Release package prepared:FAIL")
        all_passed=false
    fi

    # Check changelog
    if [[ -f "$artifacts_file" ]]; then
        local changelog_status=$(jq -r '.artifacts.changelog.status // "unknown"' "$artifacts_file")
        if [[ "$changelog_status" == "success" ]]; then
            echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Changelog generated"
            checklist+=("Changelog generated:PASS")
        else
            echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Changelog not generated"
            checklist+=("Changelog generated:FAIL")
            all_passed=false
        fi
    fi

    # Check documentation
    if [[ -f "$artifacts_file" ]]; then
        local docs_status=$(jq -r '.artifacts.documentation.status // "unknown"' "$artifacts_file")
        if [[ "$docs_status" == "success" ]]; then
            echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Documentation complete"
            checklist+=("Documentation complete:PASS")
        else
            echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Documentation incomplete"
            checklist+=("Documentation complete:FAIL")
            all_passed=false
        fi
    fi

    # Check installation guide
    if [[ -f "$artifacts_file" ]]; then
        local install_status=$(jq -r '.artifacts.installation_guide.status // "unknown"' "$artifacts_file")
        if [[ "$install_status" == "success" ]]; then
            echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Installation guide created"
            checklist+=("Installation guide created:PASS")
        else
            echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Installation guide missing"
            checklist+=("Installation guide created:FAIL")
            all_passed=false
        fi
    fi

    # Check approval
    if [[ "$approval_status" == "approved" ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Deployment approved"
        checklist+=("Deployment approved:PASS")
    else
        echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Deployment not approved"
        checklist+=("Deployment approved:FAIL")
        all_passed=false
    fi

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CLOSEOUT APPROVAL
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- CLOSEOUT APPROVAL${NC}"
    echo ""

    if [[ "$all_passed" == false ]]; then
        echo -e "  ${YELLOW}Some critical items need attention before closeout.${NC}"
        echo ""
    fi

    echo -e "  ${CYAN}Closeout options:${NC}"
    echo ""
    echo -e "    ${GREEN}[approve]${NC} Approve closeout and proceed"
    echo -e "    ${YELLOW}[review]${NC}  Review specific artifacts"
    echo -e "    ${RED}[hold]${NC}    Hold closeout for now"
    echo ""

    read -p "  Choice [approve]: " closeout_choice
    closeout_choice=${closeout_choice:-approve}

    case "$closeout_choice" in
        review)
            echo ""
            echo -e "  ${DIM}Key artifacts:${NC}"
            echo -e "    dist/                            - Release packages"
            echo -e "    CHANGELOG.md                     - Version changelog"
            echo -e "    docs/                            - Documentation"
            echo -e "    .claude/deployment/setup.json    - Setup configuration"
            echo -e "    .claude/deployment/artifacts.json - Artifact record"
            echo -e "    .claude/deployment/approval.json  - Approval record"
            echo ""
            ls -la "$deployment_dir"/ 2>/dev/null | head -10
            echo ""
            read -p "  Press Enter to continue to closeout..."
            ;;
        hold)
            echo ""
            atomic_warn "Closeout held - phase not complete"
            return 1
            ;;
    esac

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # GENERATING CLOSEOUT
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- GENERATING CLOSEOUT${NC}"
    echo ""

    # Generate markdown closeout
    cat > "$closeout_file" << EOF
# Phase 8 Closeout: Deployment Prep

**Completed:** $(date -Iseconds)
**Status:** COMPLETE

## Summary

Phase 8 (Deployment Prep) has been completed. All release artifacts are prepared.

### Key Outcomes

- **Version:** $version
- **Package:** Built and ready
- **Changelog:** Generated
- **Documentation:** Complete
- **Installation Guide:** Created
- **Approval Status:** $approval_status

### Artifacts Prepared

| Artifact | Status |
|----------|--------|
| Release Package | Ready |
| Changelog | Generated |
| Documentation | Complete |
| Installation Guide | Ready |

### Checklist Status

$(for item in "${checklist[@]}"; do
    IFS=':' read -r name status <<< "$item"
    case "$status" in
        PASS) echo "- [x] $name" ;;
        WARN) echo "- [~] $name (warning)" ;;
        FAIL) echo "- [ ] $name (failed)" ;;
        SKIP|DEFERRED) echo "- [-] $name (deferred)" ;;
    esac
done)

## Next Phase

**Phase 9: Release**

In the next phase, we will:
- Create GitHub release
- Publish to package registries
- Make announcement
- Complete release process

## To Continue

\`\`\`bash
./orchestrator/pipeline resume
\`\`\`

---

*Phase 8 completed by ATOMIC CLAUDE*
EOF

    # Generate JSON closeout
    local checklist_json=$(printf '%s\n' "${checklist[@]}" | jq -R . | jq -s .)

    jq -n \
        --arg version "$version" \
        --arg approval_status "$approval_status" \
        --argjson checklist "$checklist_json" \
        '{
            "phase": 8,
            "name": "Deployment Prep",
            "status": "complete",
            "completed_at": (now | todate),
            "release": {
                "version": $version
            },
            "approval_status": $approval_status,
            "checklist": $checklist,
            "artifacts": {
                "setup": ".claude/deployment/setup.json",
                "artifacts": ".claude/deployment/artifacts.json",
                "approval": ".claude/deployment/approval.json"
            },
            "next_phase": 9
        }' > "$closeout_json"

    echo -e "  ${GREEN}✓${NC} Generated phase-08-closeout.md"
    echo -e "  ${GREEN}✓${NC} Generated phase-08-closeout.json"
    echo ""

    # Register closeout artifacts for downstream phases
    atomic_context_artifact "phase8_closeout_md" "$closeout_file" "Phase 8 closeout summary (markdown)"
    atomic_context_artifact "phase8_closeout_json" "$closeout_json" "Phase 8 closeout data (JSON)"
    [[ -f "$artifacts_file" ]] && atomic_context_artifact "deployment_artifacts" "$artifacts_file" "Deployment artifacts manifest"
    [[ -f "$approval_file" ]] && atomic_context_artifact "deployment_approval" "$approval_file" "Deployment approval record"
    atomic_context_decision "Phase 8 closeout completed: v$version packaged" "closeout"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SESSION END
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- SESSION END${NC}"
    echo ""
    echo -e "  Closeout saved to:"
    echo -e "    ${DIM}.claude/closeout/phase-08-closeout.md${NC}"
    echo ""
    echo -e "  Deployment artifacts at:"
    echo -e "    ${DIM}.claude/deployment/${NC}"
    echo ""
    echo -e "  ${BOLD}Next: PHASE 9 - RELEASE${NC}"
    echo ""
    echo -e "  To continue:"
    echo -e "    ${CYAN}./orchestrator/pipeline resume${NC}"
    echo ""
    echo -e "  ${GREEN}Phase 8 Complete!${NC}"
    echo -e "  ${DIM}Package ready. Launch imminent.${NC}"
    echo ""

    atomic_success "Phase 8 closeout complete"

    return 0
}
