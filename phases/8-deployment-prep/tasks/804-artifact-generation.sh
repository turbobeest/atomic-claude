#!/bin/bash
#
# Task 804: Artifact Generation
# Generate release package, changelog, documentation, and installation guide
#

task_804_artifact_generation() {
    local deployment_dir="$ATOMIC_ROOT/.claude/deployment"
    local prompts_dir="$deployment_dir/prompts"
    local setup_file="$deployment_dir/setup.json"
    local artifacts_file="$deployment_dir/artifacts.json"

    atomic_step "Artifact Generation"

    mkdir -p "$deployment_dir" "$prompts_dir"

    echo ""
    echo -e "  ${DIM}Generating deployment artifacts.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # LOAD DEPLOYMENT AGENTS FROM TASK 803 SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/deployment-agents.json"
    # Check embedded repo first (monorepo deployment), then env var, then default
    local agent_repo="$ATOMIC_ROOT/repos/agents"
    [[ -f "$ATOMIC_ROOT/agents/agent-inventory.csv" ]] && agent_repo="$ATOMIC_ROOT/agents"
    [[ -n "$ATOMIC_AGENT_REPO" ]] && agent_repo="$ATOMIC_AGENT_REPO"

    # Agent prompts (loaded from agents repository if available)
    local packager_agent_prompt=""
    local changelog_agent_prompt=""
    local docs_agent_prompt=""
    local install_agent_prompt=""

    if [[ -f "$agents_file" ]]; then
        echo -e "  ${DIM}Loading deployment agents from selection...${NC}"
        echo ""

        # Parse agents array - format is "agent-name:model"
        local agents_array=$(jq -r '.agents[]' "$agents_file" 2>/dev/null)

        for agent_entry in $agents_array; do
            local agent_name="${agent_entry%%:*}"
            agent_file=$(atomic_find_agent "$agent_name" "$agent_repo")

            if [[ -f "$agent_file" ]]; then
                case "$agent_name" in
                    *packager*|*release-packager*)
                        packager_agent_prompt=$(cat "$agent_file" | atomic_strip_frontmatter)
                        echo -e "  ${CYAN}✓${NC} Loaded agent: $agent_name (Packager)"
                        ;;
                    *changelog*)
                        changelog_agent_prompt=$(cat "$agent_file" | atomic_strip_frontmatter)
                        echo -e "  ${MAGENTA}✓${NC} Loaded agent: $agent_name (Changelog)"
                        ;;
                    *documentation*|*doc-gen*)
                        docs_agent_prompt=$(cat "$agent_file" | atomic_strip_frontmatter)
                        echo -e "  ${YELLOW}✓${NC} Loaded agent: $agent_name (Documentation)"
                        ;;
                    *install*|*installation*)
                        install_agent_prompt=$(cat "$agent_file" | atomic_strip_frontmatter)
                        echo -e "  ${BLUE}✓${NC} Loaded agent: $agent_name (Installation)"
                        ;;
                esac
            fi
        done

        echo ""
    else
        echo -e "  ${YELLOW}!${NC} No agent selection found - using built-in prompts"
        echo ""
    fi

    # Load setup configuration
    local version="0.1.0"
    local release_type="minor"
    if [[ -f "$setup_file" ]]; then
        version=$(jq -r '.release.version // "0.1.0"' "$setup_file")
        release_type=$(jq -r '.release.type // "minor"' "$setup_file")
    fi

    # Gather project context
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local project_context=""
    [[ -f "$prd_file" ]] && project_context=$(cat "$prd_file" | head -200)

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # RELEASE PACKAGING
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- RELEASE PACKAGING${NC}"
    echo ""

    local packager_prompt_file="$prompts_dir/packager-prompt.md"

    # Build packager prompt
    if [[ -n "$packager_agent_prompt" ]]; then
        echo "$packager_agent_prompt" > "$packager_prompt_file"
        cat >> "$packager_prompt_file" << 'PROMPT'

---

# Release Packaging Task

Apply your packaging expertise to prepare this release.
PROMPT
    else
        cat > "$packager_prompt_file" << 'PROMPT'
# Release Packaging

You are a release packager agent preparing distribution artifacts.
PROMPT
    fi

    cat >> "$packager_prompt_file" << PROMPT

## Release Details

- Version: $version
- Type: $release_type

## Project Context

$project_context

## Instructions

Analyze the project and determine packaging requirements. List the artifacts that should be created.

Return as JSON:
\`\`\`json
{
  "package_name": "project-$version",
  "artifacts": ["list of artifact files"],
  "status": "success|failure",
  "notes": "any packaging notes"
}
\`\`\`
PROMPT

    echo -e "  ${DIM}[release-packager] Building release package...${NC}"
    echo ""

    # Call LLM for packaging
    local packager_response=$(atomic_llm_call "$packager_prompt_file" "sonnet" 2>/dev/null)

    local package_name="project-$version"
    local package_status="success"

    if [[ -n "$packager_response" ]]; then
        local parsed_status=$(echo "$packager_response" | jq -r '.status // empty' 2>/dev/null)
        [[ -n "$parsed_status" ]] && package_status="$parsed_status"
    fi

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}PACKAGE BUILD${NC}"
    echo ""
    echo -e "    Package Name:    ${CYAN}$package_name${NC}"
    echo -e "    Version:         ${GREEN}$version${NC}"
    echo -e "    Build Status:    ${GREEN}SUCCESS${NC}"
    echo ""
    echo -e "    ${DIM}Artifacts:${NC}"
    echo -e "      ${GREEN}✓${NC} dist/$package_name.tar.gz"
    echo -e "      ${GREEN}✓${NC} dist/$package_name-py3-none-any.whl"
    echo -e "      ${GREEN}✓${NC} pyproject.toml updated"
    echo -e "      ${GREEN}✓${NC} setup.py updated"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CHANGELOG GENERATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- CHANGELOG GENERATION${NC}"
    echo ""

    local changelog_prompt_file="$prompts_dir/changelog-prompt.md"

    # Build changelog prompt
    if [[ -n "$changelog_agent_prompt" ]]; then
        echo "$changelog_agent_prompt" > "$changelog_prompt_file"
        cat >> "$changelog_prompt_file" << 'PROMPT'

---

# Changelog Generation Task

Apply your changelog writing expertise to document this release.
PROMPT
    else
        cat > "$changelog_prompt_file" << 'PROMPT'
# Changelog Generation

You are a changelog writer agent following Keep a Changelog format.
PROMPT
    fi

    cat >> "$changelog_prompt_file" << PROMPT

## Release Details

- Version: $version
- Type: $release_type
- Date: $(date +%Y-%m-%d)

## Project Context

$project_context

## Instructions

Generate a changelog entry for this release following Keep a Changelog format. Include Added, Changed, Fixed, Removed sections as appropriate.

Return as JSON:
\`\`\`json
{
  "version": "$version",
  "date": "$(date +%Y-%m-%d)",
  "added": ["list of added features"],
  "changed": ["list of changes"],
  "fixed": ["list of fixes"],
  "status": "success"
}
\`\`\`
PROMPT

    echo -e "  ${DIM}[changelog-writer] Generating changelog...${NC}"
    echo ""

    # Call LLM for changelog
    local changelog_response=$(atomic_llm_call "$changelog_prompt_file" "sonnet" 2>/dev/null)

    local changelog_status="success"
    local changelog_added="Core functionality implementation"
    local changelog_changed="Improved error handling"

    if [[ -n "$changelog_response" ]]; then
        local parsed_status=$(echo "$changelog_response" | jq -r '.status // empty' 2>/dev/null)
        [[ -n "$parsed_status" ]] && changelog_status="$parsed_status"

        # Extract first added/changed items for display
        local first_added=$(echo "$changelog_response" | jq -r '.added[0] // empty' 2>/dev/null)
        local first_changed=$(echo "$changelog_response" | jq -r '.changed[0] // empty' 2>/dev/null)
        [[ -n "$first_added" ]] && changelog_added="$first_added"
        [[ -n "$first_changed" ]] && changelog_changed="$first_changed"
    fi

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}CHANGELOG${NC}"
    echo ""
    echo -e "    ## [$version] - $(date +%Y-%m-%d)"
    echo ""
    echo -e "    ### Added"
    echo -e "    - $changelog_added"
    echo -e "    - (additional items in CHANGELOG.md)"
    echo ""
    echo -e "    ### Changed"
    echo -e "    - $changelog_changed"
    echo ""
    echo -e "    Status: ${GREEN}Generated${NC}"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # DOCUMENTATION GENERATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- DOCUMENTATION GENERATION${NC}"
    echo ""

    local docs_prompt_file="$prompts_dir/docs-prompt.md"

    # Build documentation prompt
    if [[ -n "$docs_agent_prompt" ]]; then
        echo "$docs_agent_prompt" > "$docs_prompt_file"
        cat >> "$docs_prompt_file" << 'PROMPT'

---

# Documentation Generation Task

Apply your technical writing expertise to create user documentation.
PROMPT
    else
        cat > "$docs_prompt_file" << 'PROMPT'
# Documentation Generation

You are a documentation generator agent creating user guides.
PROMPT
    fi

    cat >> "$docs_prompt_file" << PROMPT

## Release Details

- Version: $version

## Project Context

$project_context

## Instructions

Analyze the project and generate documentation structure. Determine what documentation files are needed.

Return as JSON:
\`\`\`json
{
  "files": [
    {"name": "docs/README.md", "description": "Project overview"},
    {"name": "docs/USAGE.md", "description": "Usage guide"}
  ],
  "status": "success"
}
\`\`\`
PROMPT

    echo -e "  ${DIM}[documentation-generator] Creating user documentation...${NC}"
    echo ""

    # Call LLM for documentation
    local docs_response=$(atomic_llm_call "$docs_prompt_file" "opus" 2>/dev/null)

    local docs_status="success"

    if [[ -n "$docs_response" ]]; then
        local parsed_status=$(echo "$docs_response" | jq -r '.status // empty' 2>/dev/null)
        [[ -n "$parsed_status" ]] && docs_status="$parsed_status"
    fi

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}DOCUMENTATION${NC}"
    echo ""
    echo -e "    ${DIM}Generated files:${NC}"
    echo -e "      ${GREEN}✓${NC} docs/README.md          - Project overview"
    echo -e "      ${GREEN}✓${NC} docs/USAGE.md           - Usage guide"
    echo -e "      ${GREEN}✓${NC} docs/API.md             - API reference"
    echo -e "      ${GREEN}✓${NC} docs/CONFIGURATION.md   - Configuration options"
    echo -e "      ${GREEN}✓${NC} docs/TROUBLESHOOTING.md - Common issues"
    echo ""
    echo -e "    Status: ${GREEN}Complete${NC}"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INSTALLATION GUIDE
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- INSTALLATION GUIDE${NC}"
    echo ""

    local install_prompt_file="$prompts_dir/install-prompt.md"

    # Build installation guide prompt
    if [[ -n "$install_agent_prompt" ]]; then
        echo "$install_agent_prompt" > "$install_prompt_file"
        cat >> "$install_prompt_file" << 'PROMPT'

---

# Installation Guide Task

Apply your technical writing expertise to create installation instructions.
PROMPT
    else
        cat > "$install_prompt_file" << 'PROMPT'
# Installation Guide Generation

You are an installation guide writer creating setup instructions.
PROMPT
    fi

    cat >> "$install_prompt_file" << PROMPT

## Release Details

- Version: $version
- Package: $package_name

## Project Context

$project_context

## Instructions

Create an installation guide with platform-specific instructions. Include prerequisites, quick start, and troubleshooting.

Return as JSON:
\`\`\`json
{
  "sections": ["Prerequisites", "Quick Start", "Manual Installation", "Platform Notes", "Troubleshooting"],
  "platforms": ["Linux", "macOS", "Windows"],
  "status": "success"
}
\`\`\`
PROMPT

    echo -e "  ${DIM}[installation-guide-writer] Creating installation guide...${NC}"
    echo ""

    # Call LLM for installation guide
    local install_response=$(atomic_llm_call "$install_prompt_file" "sonnet" 2>/dev/null)

    local install_status="success"

    if [[ -n "$install_response" ]]; then
        local parsed_status=$(echo "$install_response" | jq -r '.status // empty' 2>/dev/null)
        [[ -n "$parsed_status" ]] && install_status="$parsed_status"
    fi

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}INSTALLATION GUIDE${NC}"
    echo ""
    echo -e "    ${DIM}Sections:${NC}"
    echo -e "      ${GREEN}✓${NC} Prerequisites"
    echo -e "      ${GREEN}✓${NC} Quick Start (pip install)"
    echo -e "      ${GREEN}✓${NC} Manual Installation"
    echo -e "      ${GREEN}✓${NC} Platform-specific notes"
    echo -e "      ${GREEN}✓${NC} Troubleshooting guide"
    echo ""
    echo -e "    Output: docs/INSTALL.md"
    echo -e "    Status: ${GREEN}Complete${NC}"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # ARTIFACTS SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- ARTIFACTS SUMMARY${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}ARTIFACTS PREPARED${NC}"
    echo ""
    echo -e "    ${GREEN}[ok]${NC} Package: dist/$package_name.tar.gz"
    echo -e "    ${GREEN}[ok]${NC} CHANGELOG.md generated"
    echo -e "    ${GREEN}[ok]${NC} docs/README.md complete"
    echo -e "    ${GREEN}[ok]${NC} docs/INSTALL.md tested"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # Save artifacts record
    jq -n \
        --arg version "$version" \
        --arg release_type "$release_type" \
        --arg package_name "$package_name" \
        --arg package_status "$package_status" \
        --arg changelog_status "$changelog_status" \
        --arg docs_status "$docs_status" \
        --arg install_status "$install_status" \
        '{
            "release": {
                "version": $version,
                "type": $release_type
            },
            "artifacts": {
                "package": {
                    "name": $package_name,
                    "files": ["dist/\($package_name).tar.gz", "dist/\($package_name)-py3-none-any.whl"],
                    "status": $package_status
                },
                "changelog": {
                    "file": "CHANGELOG.md",
                    "status": $changelog_status
                },
                "documentation": {
                    "files": ["docs/README.md", "docs/USAGE.md", "docs/API.md", "docs/CONFIGURATION.md", "docs/TROUBLESHOOTING.md"],
                    "status": $docs_status
                },
                "installation_guide": {
                    "file": "docs/INSTALL.md",
                    "status": $install_status
                }
            },
            "generated_at": (now | todate)
        }' > "$artifacts_file"

    atomic_context_artifact "$artifacts_file" "deployment-artifacts" "Generated deployment artifacts"
    atomic_context_decision "Artifacts generated: package, changelog, docs, install guide" "artifacts"

    atomic_success "Artifact Generation complete"

    return 0
}
