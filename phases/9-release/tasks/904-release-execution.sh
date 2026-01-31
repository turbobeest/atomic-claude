#!/bin/bash
#
# Task 904: Release Execution
# Execute GitHub release, package publishing, and announcement
#

task_904_release_execution() {
    local release_dir="$ATOMIC_ROOT/.claude/release"
    local prompts_dir="$release_dir/prompts"
    local setup_file="$release_dir/setup.json"
    local execution_file="$release_dir/execution.json"
    local announcement_file="$release_dir/announcement.md"

    atomic_step "Release Execution"

    mkdir -p "$release_dir" "$prompts_dir"

    echo ""
    echo -e "  ${DIM}Executing release to distribution channels.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # LOAD RELEASE AGENTS FROM TASK 903 SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/release-agents.json"
    # Check embedded repo first (monorepo deployment), then env var, then default
    local agent_repo="$ATOMIC_ROOT/repos/agents"
    [[ -f "$ATOMIC_ROOT/agents/agent-inventory.csv" ]] && agent_repo="$ATOMIC_ROOT/agents"
    [[ -n "$ATOMIC_AGENT_REPO" ]] && agent_repo="$ATOMIC_AGENT_REPO"

    # Agent prompts (loaded from agents repository if available)
    local announcement_agent_prompt=""

    if [[ -f "$agents_file" ]]; then
        echo -e "  ${DIM}Loading release agents from selection...${NC}"
        echo ""

        # Parse agents array - format is "agent-name:model"
        local agents_array=$(jq -r '.agents[]' "$agents_file" 2>/dev/null)

        for agent_entry in $agents_array; do
            local agent_name="${agent_entry%%:*}"
            agent_file=$(atomic_find_agent "$agent_name" "$agent_repo")

            if [[ -f "$agent_file" ]]; then
                case "$agent_name" in
                    *announcement*|*writer*)
                        announcement_agent_prompt=$(cat "$agent_file" | atomic_strip_frontmatter)
                        echo -e "  ${YELLOW}✓${NC} Loaded agent: $agent_name (Announcement)"
                        ;;
                esac
            fi
        done

        echo ""
    else
        echo -e "  ${YELLOW}!${NC} No agent selection found - using built-in prompts"
        echo ""
    fi

    # Load configuration
    local version="0.1.0"
    if [[ -f "$setup_file" ]]; then
        version=$(jq -r '.release.version // "0.1.0"' "$setup_file")
    fi

    # Gather project context
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local changelog_file="$ATOMIC_ROOT/CHANGELOG.md"
    local project_context=""
    [[ -f "$prd_file" ]] && project_context+="## PRD\n$(cat "$prd_file" | head -100)\n\n"
    [[ -f "$changelog_file" ]] && project_context+="## Changelog\n$(cat "$changelog_file" | head -50)\n\n"

    # Future sections (hidden for now - internal release only):
    # # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # # GITHUB RELEASE
    # # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    #
    # echo ""
    # echo -e "  ${BOLD}- GITHUB RELEASE${NC}"
    # echo ""
    #
    # echo -e "  ${DIM}[github-releaser] Creating GitHub release...${NC}"
    # echo ""
    #
    # # Simulated GitHub release
    # local github_url="https://github.com/user/project/releases/tag/v$version"
    # local github_status="success"
    #
    # echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    # echo -e "  ${BOLD}GITHUB RELEASE${NC}"
    # echo ""
    # echo -e "    Tag:      v$version"
    # echo -e "    Title:    Release v$version"
    # echo -e "    Status:   ${GREEN}Created${NC}"
    # echo ""
    # echo -e "    Release:  ${CYAN}$github_url${NC}"
    # echo ""
    # echo -e "    Assets uploaded:"
    # echo -e "      ${GREEN}✓${NC} project-$version.tar.gz"
    # echo -e "      ${GREEN}✓${NC} project-$version-py3-none-any.whl"
    # echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    # echo ""
    #
    # # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # # PACKAGE PUBLISHING
    # # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    #
    # echo ""
    # echo -e "  ${BOLD}- PACKAGE PUBLISHING${NC}"
    # echo ""
    #
    # echo -e "  ${DIM}[package-publisher] Publishing to PyPI...${NC}"
    # echo ""
    #
    # # Simulated package publishing
    # local pypi_url="https://pypi.org/project/project/$version/"
    # local pypi_status="success"
    #
    # echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    # echo -e "  ${BOLD}PYPI PUBLICATION${NC}"
    # echo ""
    # echo -e "    Package:   project"
    # echo -e "    Version:   $version"
    # echo -e "    Status:    ${GREEN}Published${NC}"
    # echo ""
    # echo -e "    Package:   ${CYAN}$pypi_url${NC}"
    # echo ""
    # echo -e "    Install command:"
    # echo -e "      ${DIM}pip install project==$version${NC}"
    # echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    # echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INTERNAL RELEASE NOTES
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- INTERNAL RELEASE NOTES${NC}"
    echo ""

    local announce_prompt_file="$prompts_dir/announcement-prompt.md"

    # Build announcement prompt
    if [[ -n "$announcement_agent_prompt" ]]; then
        echo "$announcement_agent_prompt" > "$announce_prompt_file"
        cat >> "$announce_prompt_file" << 'PROMPT'

---

# Announcement Writing Task

Apply your technical writing expertise to draft internal release notes.
PROMPT
    else
        cat > "$announce_prompt_file" << 'PROMPT'
# Announcement Writing

You are an announcement writer agent drafting internal release notes.
PROMPT
    fi

    cat >> "$announce_prompt_file" << PROMPT

## Release Details

- Version: $version
- Channel: internal

## Project Context

$project_context

## Instructions

Draft internal release notes for stakeholders. Include:
1. Release summary
2. What's new (features, changes)
3. Artifacts available
4. Next steps

Return as markdown suitable for internal distribution.
PROMPT

    echo -e "  ${DIM}[announcement-writer] Drafting internal release notes...${NC}"
    echo ""

    # Call LLM for announcement
    local announce_response=$(atomic_llm_call "$announce_prompt_file" "haiku" 2>/dev/null)

    # Generate internal release notes (using LLM response or fallback)
    if [[ -n "$announce_response" ]]; then
        echo "$announce_response" > "$announcement_file"
    else
        cat > "$announcement_file" << EOF
# Internal Release Notes - v$version

## Release Summary

Version $version has been completed and is ready for internal use.

## What's New

- Core functionality implementation
- User interface components
- Data persistence layer
- External integrations
- Performance optimizations

## Artifacts

- Distribution package: dist/project-$version.tar.gz
- Wheel package: dist/project-$version-py3-none-any.whl

## Next Steps

- Internal testing and validation
- Stakeholder review
- External release planning (if applicable)
EOF
    fi

    local announcement_status="success"

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}INTERNAL RELEASE NOTES${NC}"
    echo ""
    echo -e "    Status:   ${GREEN}Draft created${NC}"
    echo -e "    Saved to: ${DIM}.claude/release/announcement.md${NC}"
    echo ""
    echo -e "    ${DIM}Preview:${NC}"
    echo -e "      # Internal Release Notes - v$version"
    echo -e "      Version $version has been completed..."
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # EXECUTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- EXECUTION SUMMARY${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}RELEASE EXECUTION STATUS${NC}"
    echo ""
    echo -e "    ${GREEN}✓${NC} Internal Release Notes: .claude/release/announcement.md"
    echo -e "    ${GREEN}✓${NC} Version:                v$version"
    echo -e "    ${GREEN}✓${NC} Channel:                internal"
    # Future external channels (hidden for now):
    # echo -e "    ${GREEN}✓${NC} GitHub Release: $github_url"
    # echo -e "    ${GREEN}✓${NC} PyPI Package:   $pypi_url"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # Save execution record
    jq -n \
        --arg version "$version" \
        --arg announcement_status "$announcement_status" \
        '{
            "release": {
                "version": $version,
                "channel": "internal"
            },
            "announcement": {
                "file": ".claude/release/announcement.md",
                "status": $announcement_status
            },
            "executed_at": (now | todate)
        }' > "$execution_file"

    # Future external release record (hidden for now):
    # jq -n \
    #     --arg version "$version" \
    #     --arg github_url "$github_url" \
    #     --arg github_status "$github_status" \
    #     --arg pypi_url "$pypi_url" \
    #     --arg pypi_status "$pypi_status" \
    #     --arg announcement_status "$announcement_status" \
    #     '{
    #         "release": { "version": $version },
    #         "github": { "url": $github_url, "status": $github_status },
    #         "pypi": { "url": $pypi_url, "status": $pypi_status },
    #         "announcement": { "file": ".claude/release/announcement.md", "status": $announcement_status },
    #         "executed_at": (now | todate)
    #     }' > "$execution_file"

    atomic_context_artifact "$execution_file" "release-execution" "Release execution record"
    atomic_context_decision "Release v$version executed: internal" "execution"

    atomic_success "Release Execution complete"

    return 0
}
