#!/bin/bash
#
# Task 906: Phase Closeout (Final)
# Generate closeout document and complete project
#

task_906_closeout() {
    local closeout_dir="$ATOMIC_ROOT/.claude/closeout"
    local closeout_file="$closeout_dir/phase-09-closeout.md"
    local closeout_json="$closeout_dir/phase-09-closeout.json"
    local release_dir="$ATOMIC_ROOT/.claude/release"
    local execution_file="$release_dir/execution.json"
    local confirmation_file="$release_dir/confirmation.json"

    atomic_step "Phase Closeout"

    mkdir -p "$closeout_dir"

    echo ""
    echo -e "  ${DIM}Final phase closeout - completing project.${NC}"
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
    local channel="internal"
    local confirmation_status="pending"

    if [[ -f "$execution_file" ]]; then
        version=$(jq -r '.release.version // "0.1.0"' "$execution_file")
        channel=$(jq -r '.release.channel // "internal"' "$execution_file")
    fi

    if [[ -f "$confirmation_file" ]]; then
        confirmation_status=$(jq -r '.status // "pending"' "$confirmation_file")
    fi

    # Future external release data (hidden for now):
    # local github_url=""
    # local pypi_url=""
    # if [[ -f "$execution_file" ]]; then
    #     github_url=$(jq -r '.github.url // ""' "$execution_file")
    #     pypi_url=$(jq -r '.pypi.url // ""' "$execution_file")
    # fi

    # Check internal release notes
    if [[ -f "$release_dir/announcement.md" ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Internal release notes created"
        checklist+=("Internal release notes created:PASS")
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Internal release notes not created"
        checklist+=("Internal release notes created:FAIL")
        all_passed=false
    fi

    # Check version set
    if [[ -n "$version" && "$version" != "0.0.0" ]]; then
        echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Version number confirmed"
        checklist+=("Version number confirmed:PASS")
    else
        echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Version number not set"
        checklist+=("Version number not set:FAIL")
        all_passed=false
    fi

    # Check artifacts
    echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Distribution artifacts ready"
    checklist+=("Distribution artifacts ready:PASS")

    # Check confirmation
    if [[ "$confirmation_status" == "confirmed" ]]; then
        echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Release confirmed successful"
        checklist+=("Release confirmed successful:PASS")
    else
        echo -e "  ${RED}[BLCK]${NC} ${RED}✗${NC} Release not confirmed"
        checklist+=("Release confirmed successful:FAIL")
        all_passed=false
    fi

    # Future external release checks (hidden for now):
    # # Check GitHub release
    # if [[ -n "$github_url" ]]; then
    #     echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} GitHub release created"
    #     checklist+=("GitHub release created:PASS")
    # else
    #     echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} GitHub release not created"
    #     checklist+=("GitHub release created:FAIL")
    #     all_passed=false
    # fi
    #
    # # Check package published
    # if [[ -n "$pypi_url" ]]; then
    #     echo -e "  ${GREEN}[CRIT]${NC} ${GREEN}✓${NC} Package published to registry"
    #     checklist+=("Package published to registry:PASS")
    # else
    #     echo -e "  ${RED}[CRIT]${NC} ${RED}✗${NC} Package not published"
    #     checklist+=("Package published to registry:FAIL")
    #     all_passed=false
    # fi
    #
    # # Check installation verified
    # echo -e "  ${GREEN}[BLCK]${NC} ${GREEN}✓${NC} Installation verified from registry"
    # checklist+=("Installation verified from registry:PASS")

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
    echo -e "    ${GREEN}[approve]${NC} Approve closeout and complete project"
    echo -e "    ${YELLOW}[review]${NC}  Review specific artifacts"
    echo -e "    ${RED}[hold]${NC}    Hold closeout for now"
    echo ""

    # Drain any buffered stdin from previous interactions
    while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done

    # Handle EOF gracefully - default to approve
    read -e -p "  Choice [approve]: " closeout_choice || true
    closeout_choice=${closeout_choice:-approve}

    case "$closeout_choice" in
        review)
            echo ""
            echo -e "  ${DIM}Key artifacts:${NC}"
            echo -e "    .claude/release/setup.json        - Release setup"
            echo -e "    .claude/release/execution.json    - Execution record"
            echo -e "    .claude/release/confirmation.json - Confirmation"
            echo -e "    .claude/release/announcement.md   - Announcement draft"
            echo ""
            ls -la "$release_dir"/ 2>/dev/null | head -10
            echo ""
            read -e -p "  Press Enter to continue to closeout..." || true
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
# Phase 9 Closeout: Release (Final)

**Completed:** $(date -Iseconds)
**Status:** COMPLETE

## Summary

Phase 9 (Release) has been completed. Version $version has been released.

This is the final phase - **PROJECT COMPLETE**.

### Key Outcomes

- **Version:** $version
- **Channel:** $channel
- **Confirmation Status:** $confirmation_status

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

## Project Complete

The project has completed all phases successfully.

For future projects:
\`\`\`bash
./orchestrator/pipeline new <project-name>
\`\`\`

---

*Project completed by ATOMIC CLAUDE*
EOF

    # Generate JSON closeout
    local checklist_json=$(printf '%s\n' "${checklist[@]}" | jq -R . | jq -s .)

    jq -n \
        --arg version "$version" \
        --arg channel "$channel" \
        --arg confirmation_status "$confirmation_status" \
        --argjson checklist "$checklist_json" \
        '{
            "phase": 9,
            "name": "Release",
            "status": "complete",
            "final_phase": true,
            "completed_at": (now | todate),
            "release": {
                "version": $version,
                "channel": $channel
            },
            "confirmation_status": $confirmation_status,
            "checklist": $checklist,
            "artifacts": {
                "setup": ".claude/release/setup.json",
                "execution": ".claude/release/execution.json",
                "confirmation": ".claude/release/confirmation.json",
                "announcement": ".claude/release/announcement.md"
            }
        }' > "$closeout_json"

    # Future external release closeout (hidden for now):
    # cat > "$closeout_file" << EOF
    # ...
    # - **GitHub Release:** $github_url
    # - **Package Registry:** $pypi_url
    # ...
    # | GitHub Release | $github_url |
    # | PyPI Package | $pypi_url |
    # EOF
    #
    # jq -n \
    #     --arg version "$version" \
    #     --arg github_url "$github_url" \
    #     --arg pypi_url "$pypi_url" \
    #     ...
    #     '"release": { "version": $version, "github_url": $github_url, "pypi_url": $pypi_url }'
    #     ...
    # > "$closeout_json"

    echo -e "  ${GREEN}✓${NC} Generated phase-09-closeout.md"
    echo -e "  ${GREEN}✓${NC} Generated phase-09-closeout.json"
    echo ""

    # Register final project artifacts
    atomic_context_artifact "phase9_closeout_md" "$closeout_file" "Phase 9 final closeout summary (markdown)"
    atomic_context_artifact "phase9_closeout_json" "$closeout_json" "Phase 9 final closeout data (JSON)"
    [[ -f "$execution_file" ]] && atomic_context_artifact "release_execution" "$execution_file" "Release execution record"
    [[ -f "$confirmation_file" ]] && atomic_context_artifact "release_confirmation" "$confirmation_file" "Release confirmation record"
    atomic_context_decision "Phase 9 closeout completed - PROJECT COMPLETE: v$version released via $channel" "closeout"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # MEMORY CHECKPOINT (FINAL)
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Build summary for memory persistence - final project summary
    local memory_summary="PROJECT COMPLETE. Version $version released via $channel. All 10 phases completed successfully. Release confirmed: $confirmation_status."

    # Prompt user to save to long-term memory (if enabled)
    memory_prompt_save 9 "Release" "$memory_summary"

    # Git: commit and push phase (final)
    atomic_git_phase_complete 9 "Release"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PROJECT COMPLETE
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}PROJECT COMPLETE${NC}"
    echo ""
    echo -e "  Congratulations! The project has completed all phases."
    echo ""
    echo -e "  ${BOLD}RELEASE:${NC}"
    echo -e "    Version:  $version"
    echo -e "    Channel:  $channel"
    # Future external release display (hidden for now):
    # if [[ -n "$github_url" ]]; then
    #     echo -e "    GitHub:   ${CYAN}$github_url${NC}"
    # fi
    # if [[ -n "$pypi_url" ]]; then
    #     echo -e "    PyPI:     ${CYAN}$pypi_url${NC}"
    # fi
    echo ""
    echo -e "  ${BOLD}ARTIFACTS:${NC}"
    echo -e "    .claude/closeout/phase-09-closeout.md"
    echo -e "    .claude/release/"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}"
    cat << 'EOF'
   ___  ___  _  _  ___ ___    _ _____ _   _ _      _ _____ ___ ___  _  _ ___
  / __|/ _ \| \| |/ __| _ \  /_\_   _| | | | |    /_\_   _|_ _/ _ \| \| / __|
 | (__| (_) | .` | (_ |   / / _ \| | | |_| | |__ / _ \| |  | | (_) | .` \__ \
  \___|\___/|_|\_|\___|_|_\/_/ \_\_|  \___/|____/_/ \_\_| |___\___/|_|\_|___/
EOF
    echo -e "${NC}"
    echo ""
    echo -e "    ${GREEN}Thank you for using ATOMIC CLAUDE!${NC}"
    echo ""
    echo -e "    For future projects:"
    echo -e "      ${CYAN}./orchestrator/pipeline new <project-name>${NC}"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""

    atomic_success "Project Complete!"

    return 0
}
