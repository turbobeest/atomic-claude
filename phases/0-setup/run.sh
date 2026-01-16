#!/bin/bash
#
# PHASE 0: SETUP
# Configuration + API Keys + Materials + Environment
#
# Tasks: 001-008 (0xx range)
#
# This phase is 95% deterministic. Claude is only used for:
# - Task 005: Summarizing existing documentation
#
# Navigation: After each task, you can:
#   [c] Continue    - proceed to next task
#   [r] Redo        - run this task again
#   [b] Go back     - return to previous task
#   [q] Quit        - abort the phase
#

set -euo pipefail

PHASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$PHASE_DIR/../.." && pwd)"

# Source libraries
source "$ROOT_DIR/lib/phase.sh"
source "$ROOT_DIR/lib/intro.sh"

# ============================================================================
# TASK DEFINITIONS
# ============================================================================

# Task 001: Collect project name (deterministic + user input)
task_001_project_name() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    # Auto-detect from directory name
    local detected_name=$(basename "$(pwd)")

    atomic_step "Project Name Configuration"
    atomic_substep "Detected from directory: $detected_name"

    read -p "Project name [$detected_name]: " project_name
    project_name=${project_name:-$detected_name}

    # Initialize or update config
    mkdir -p "$(dirname "$config_file")"
    if [[ -f "$config_file" ]]; then
        local tmp=$(mktemp)
        jq ".project.name = \"$project_name\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"
    else
        cat > "$config_file" << EOF
{
  "project": {
    "name": "$project_name"
  }
}
EOF
    fi

    atomic_success "Project name set: $project_name"
    return 0
}

# Task 002: Collect project description (deterministic + user input)
task_002_description() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    atomic_step "Project Description"

    # Show current value if exists
    local current=$(jq -r '.project.description // empty' "$config_file" 2>/dev/null || true)
    if [[ -n "$current" ]]; then
        atomic_substep "Current: $current"
    fi

    read -p "Brief description: " description

    if [[ -n "$description" ]]; then
        local tmp=$(mktemp)
        jq ".project.description = \"$description\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"
        atomic_success "Description saved"
    else
        atomic_warn "No description provided (optional)"
    fi

    return 0
}

# Task 003: Select project type (deterministic menu)
task_003_project_type() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    atomic_step "Project Type"

    # Show current value if exists
    local current=$(jq -r '.project.type // empty' "$config_file" 2>/dev/null || true)
    if [[ -n "$current" ]]; then
        atomic_substep "Current: $current"
    fi

    echo ""
    echo "  1. new        - Brand new project"
    echo "  2. existing   - Enhance existing codebase"
    echo "  3. refactor   - Major restructuring"
    echo "  4. migration  - Technology migration"
    echo ""

    read -p "Select type [1-4]: " choice
    local project_type
    case "$choice" in
        1) project_type="new" ;;
        2) project_type="existing" ;;
        3) project_type="refactor" ;;
        4) project_type="migration" ;;
        *) project_type="new" ;;
    esac

    local tmp=$(mktemp)
    jq ".project.type = \"$project_type\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"

    atomic_success "Project type: $project_type"
    return 0
}

# Task 004: Collect GitHub URL (deterministic + git detection)
task_004_github_url() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    atomic_step "GitHub Configuration"

    # Try to detect from git remote
    local detected_url=""
    detected_url=$(git remote get-url origin 2>/dev/null || true)
    if [[ -n "$detected_url" ]]; then
        atomic_substep "Detected remote: $detected_url"
    fi

    # Show current value if exists
    local current=$(jq -r '.github.repository_url // empty' "$config_file" 2>/dev/null || true)
    if [[ -n "$current" ]]; then
        atomic_substep "Current: $current"
        detected_url="$current"
    fi

    read -p "Repository URL [$detected_url]: " repo_url
    repo_url=${repo_url:-$detected_url}

    if [[ -n "$repo_url" ]]; then
        local tmp=$(mktemp)
        jq ".github.repository_url = \"$repo_url\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"
        atomic_success "GitHub URL configured"
    else
        atomic_warn "No GitHub URL configured (optional)"
    fi

    return 0
}

# Task 005: Summarize existing docs (LLM TASK)
task_005_summarize_docs() {
    local output_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/doc-summary.md"

    # First, scan for existing documentation
    atomic_step "Scanning for existing documentation..."

    local docs_found=$(find . -maxdepth 3 \( -name "*.md" -o -name "*.rst" -o -name "*.txt" \) -type f 2>/dev/null | grep -v node_modules | grep -v .git | head -20 || true)

    if [[ -z "$docs_found" ]]; then
        atomic_info "No documentation found, skipping summarization"
        echo "No documentation files found." > "$output_file"
        return 0
    fi

    local count=$(echo "$docs_found" | wc -l)
    atomic_substep "Found $count documentation files"

    # Build context for Claude
    local context=""
    while IFS= read -r doc; do
        context+="=== $doc ===\n"
        context+=$(head -50 "$doc" 2>/dev/null || true)
        context+="\n\n"
    done <<< "$docs_found"

    # Create dynamic prompt
    local dynamic_prompt="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts/summarize-docs-dynamic.md"
    mkdir -p "$(dirname "$dynamic_prompt")"

    cat > "$dynamic_prompt" << EOF
# Task: Summarize Existing Documentation

Review the following documentation files and provide a brief summary of what this project is about.

## Documentation Found:

$context

## Your Task:

Provide a 3-5 sentence summary of what this project does based on the documentation.
Focus on: purpose, key features, technology stack (if apparent).

Output as plain text, no JSON, no markdown headers.
EOF

    atomic_invoke "$dynamic_prompt" "$output_file" "Summarize existing documentation" --model=haiku

    # Show the summary
    if [[ -f "$output_file" ]]; then
        echo ""
        atomic_output_box "$(cat "$output_file")"
    fi

    return 0
}

# Task 006: Collect API keys (deterministic + secure input)
task_006_api_keys() {
    local secrets_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/secrets.json"

    atomic_step "API Key Configuration"
    atomic_warn "API keys will be stored locally and never committed to git"

    # Check if already configured
    if [[ -f "$secrets_file" ]]; then
        local has_key=$(jq -r '.anthropic_api_key // empty' "$secrets_file" 2>/dev/null || true)
        if [[ -n "$has_key" ]]; then
            atomic_substep "API key already configured (starts with: ${has_key:0:10}...)"
            read -p "Reconfigure? [y/N]: " reconfigure
            if [[ ! "$reconfigure" =~ ^[Yy] ]]; then
                atomic_info "Keeping existing configuration"
                return 0
            fi
        fi
    fi

    echo ""
    read -s -p "Anthropic API Key (sk-ant-...): " anthropic_key
    echo ""

    if [[ -z "$anthropic_key" ]]; then
        atomic_warn "No API key provided"
        return 0
    fi

    # Validate format
    if [[ ! "$anthropic_key" =~ ^sk-ant-.* ]]; then
        atomic_warn "Key doesn't match expected format (sk-ant-*)"
    fi

    # Store securely
    mkdir -p "$(dirname "$secrets_file")"
    cat > "$secrets_file" << EOF
{
  "anthropic_api_key": "$anthropic_key"
}
EOF

    # Secure the file
    chmod 600 "$secrets_file"

    atomic_success "API key saved (file secured with chmod 600)"
    return 0
}

# Task 007: Generate material manifest (mostly deterministic)
task_007_material_manifest() {
    local manifest_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/material-manifest.json"

    atomic_step "Scanning project materials..."

    # Deterministic scan
    local materials=$(find . -maxdepth 4 \( -name "*.md" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) -type f 2>/dev/null | grep -v node_modules | grep -v .git | head -50 || true)

    if [[ -z "$materials" ]]; then
        atomic_info "No materials found"
        echo '{"materials": [], "count": 0}' > "$manifest_file"
        return 0
    fi

    local count=$(echo "$materials" | wc -l)
    atomic_substep "Found $count material files"

    # Build manifest (deterministic - no LLM needed for simple listing)
    echo '{"materials": [' > "$manifest_file"
    local first=true
    while IFS= read -r file; do
        [[ "$first" == "true" ]] || echo "," >> "$manifest_file"
        first=false
        local ext="${file##*.}"
        echo "  {\"path\": \"$file\", \"type\": \"$ext\"}" >> "$manifest_file"
    done <<< "$materials"
    echo '], "count": '"$count"'}' >> "$manifest_file"

    atomic_success "Material manifest created: $count files indexed"
    return 0
}

# Task 008: Validate environment (deterministic)
task_008_validate_env() {
    local report_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/env-validation.json"

    atomic_step "Environment Validation"

    local checks='[]'
    local all_pass=true

    # Check required tools
    for tool in git jq bash; do
        if command -v $tool &> /dev/null; then
            local version=$($tool --version 2>&1 | head -1 || echo "unknown")
            checks=$(echo "$checks" | jq ". + [{\"tool\": \"$tool\", \"status\": \"pass\", \"version\": \"$version\"}]")
            atomic_success "$tool: installed"
        else
            checks=$(echo "$checks" | jq ". + [{\"tool\": \"$tool\", \"status\": \"fail\", \"version\": null}]")
            atomic_error "$tool: NOT FOUND"
            all_pass=false
        fi
    done

    # Check Claude CLI
    if command -v claude &> /dev/null; then
        local version=$(claude --version 2>&1 || echo "unknown")
        checks=$(echo "$checks" | jq ". + [{\"tool\": \"claude\", \"status\": \"pass\", \"version\": \"$version\"}]")
        atomic_success "claude: installed"
    else
        checks=$(echo "$checks" | jq ". + [{\"tool\": \"claude\", \"status\": \"fail\", \"version\": null}]")
        atomic_error "claude: NOT FOUND (required!)"
        all_pass=false
    fi

    # Write report
    echo "{\"checks\": $checks, \"all_pass\": $all_pass}" > "$report_file"

    if $all_pass; then
        atomic_success "Environment validation passed"
        return 0
    else
        atomic_error "Environment validation failed"
        return 1
    fi
}

# ============================================================================
# MAIN WORKFLOW
# ============================================================================

main() {
    # Check for --skip-intro flag
    local skip_intro=false
    for arg in "$@"; do
        [[ "$arg" == "--skip-intro" ]] && skip_intro=true
    done

    # Show the WarGames-style intro
    if ! $skip_intro; then
        wopr_intro
    fi

    phase_start "0-setup" "Setup"

    echo ""
    echo -e "${DIM}Navigation: After each task you can:${NC}"
    echo -e "${DIM}  [c] Continue  [r] Redo  [b] Go back  [q] Quit${NC}"
    echo ""

    # Run all tasks with interactive navigation
    # Task IDs: 001-008 (Phase 0 = 0xx range)
    phase_run_tasks \
        task_001_project_name \
        task_002_description \
        task_003_project_type \
        task_004_github_url \
        task_005_summarize_docs \
        task_006_api_keys \
        task_007_material_manifest \
        task_008_validate_env

    local result=$?

    if [[ $result -ne 0 ]]; then
        atomic_error "Phase aborted"
        exit 1
    fi

    # Final review
    echo ""
    atomic_header "Configuration Summary"
    echo ""

    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    if [[ -f "$config_file" ]]; then
        echo "Project Configuration:"
        jq '.' "$config_file"
    fi

    # Final human gate
    phase_human_gate "Configuration complete. Ready to proceed?" || exit 1

    phase_complete

    echo ""
    atomic_info "Next: Run ./phases/01-ideation/run.sh (when available)"
}

main "$@"
