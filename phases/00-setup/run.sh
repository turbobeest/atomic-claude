#!/bin/bash
#
# PHASE 00: SETUP
# Configuration + API Keys + Materials + Environment
#
# This phase is 95% deterministic. Claude is only used for:
# - Summarizing existing documentation (Task 5)
# - Generating material manifest descriptions (Task 7)
#

set -euo pipefail

PHASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$PHASE_DIR/../.." && pwd)"

# Source libraries
source "$ROOT_DIR/lib/phase.sh"

# ============================================================================
# TASK DEFINITIONS
# ============================================================================

# Task 1: Collect project name (deterministic + user input)
task_01_project_name() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    # Auto-detect from directory name
    local detected_name=$(basename "$(pwd)")

    atomic_step "Project Name Configuration"
    atomic_substep "Detected from directory: $detected_name"

    read -p "Project name [$detected_name]: " project_name
    project_name=${project_name:-$detected_name}

    # Initialize config
    cat > "$config_file" << EOF
{
  "project": {
    "name": "$project_name"
  }
}
EOF

    atomic_success "Project name set: $project_name"
    return 0
}

# Task 2: Collect project description (deterministic + user input)
task_02_description() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    atomic_step "Project Description"

    read -p "Brief description: " description

    # Update config
    local tmp=$(mktemp)
    jq ".project.description = \"$description\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"

    atomic_success "Description saved"
    return 0
}

# Task 3: Select project type (deterministic menu)
task_03_project_type() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    atomic_step "Project Type"
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

# Task 4: Collect GitHub URL (deterministic + git detection)
task_04_github_url() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    atomic_step "GitHub Configuration"

    # Try to detect from git remote
    local detected_url=""
    if git remote get-url origin 2>/dev/null; then
        detected_url=$(git remote get-url origin 2>/dev/null || true)
        atomic_substep "Detected remote: $detected_url"
    fi

    read -p "Repository URL [$detected_url]: " repo_url
    repo_url=${repo_url:-$detected_url}

    local tmp=$(mktemp)
    jq ".github.repository_url = \"$repo_url\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"

    atomic_success "GitHub URL configured"
    return 0
}

# Task 5: Summarize existing docs (LLM TASK)
task_05_summarize_docs() {
    local prompt_file="$PHASE_DIR/prompts/summarize-docs.md"
    local output_file="doc-summary.md"

    # First, scan for existing documentation
    atomic_step "Scanning for existing documentation..."

    local docs_found=$(find . -maxdepth 3 -name "*.md" -o -name "*.rst" -o -name "*.txt" 2>/dev/null | head -20)

    if [[ -z "$docs_found" ]]; then
        atomic_info "No documentation found, skipping summarization"
        return 0
    fi

    atomic_substep "Found $(echo "$docs_found" | wc -l) documentation files"

    # Build context for Claude
    local context=""
    for doc in $docs_found; do
        context+="=== $doc ===\n"
        context+=$(head -50 "$doc" 2>/dev/null || true)
        context+="\n\n"
    done

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

Output as plain text, no JSON.
EOF

    phase_llm_task "Summarize existing documentation" "$dynamic_prompt" "$output_file" --model=haiku
}

# Task 6: Collect API keys (deterministic + secure input)
task_06_api_keys() {
    local secrets_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/secrets.json"

    atomic_step "API Key Configuration"
    atomic_warn "API keys will be stored locally and never committed to git"

    echo ""
    read -s -p "Anthropic API Key (sk-ant-...): " anthropic_key
    echo ""

    # Validate format
    if [[ ! "$anthropic_key" =~ ^sk-ant-.* ]]; then
        atomic_warn "Key doesn't match expected format (sk-ant-*)"
    fi

    # Store securely
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

# Task 7: Generate material manifest (LLM TASK)
task_07_material_manifest() {
    atomic_step "Scanning project materials..."

    # Deterministic scan
    local materials=$(find . -maxdepth 4 \( -name "*.md" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) 2>/dev/null | head -50)

    if [[ -z "$materials" ]]; then
        atomic_info "No materials found"
        return 0
    fi

    local count=$(echo "$materials" | wc -l)
    atomic_substep "Found $count material files"

    # For a small number, we can just list them (no LLM needed)
    if [[ $count -lt 10 ]]; then
        local manifest_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/material-manifest.json"
        echo '{"materials": [' > "$manifest_file"
        local first=true
        for file in $materials; do
            [[ "$first" == "true" ]] || echo "," >> "$manifest_file"
            first=false
            echo "  {\"path\": \"$file\", \"type\": \"${file##*.}\"}" >> "$manifest_file"
        done
        echo ']}' >> "$manifest_file"

        atomic_success "Material manifest created (deterministic)"
        return 0
    fi

    # For larger sets, use LLM to categorize
    phase_llm_task "Categorize project materials" \
        "$PHASE_DIR/prompts/categorize-materials.md" \
        "material-manifest.json" \
        --model=haiku \
        --format=json \
        --stdin <<< "$materials"
}

# Task 8: Validate environment (deterministic)
task_08_validate_env() {
    local report_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/env-validation.json"

    atomic_step "Environment Validation"

    local checks=()
    local all_pass=true

    # Check required tools
    for tool in git jq bash node; do
        if command -v $tool &> /dev/null; then
            checks+=("{\"tool\": \"$tool\", \"status\": \"pass\", \"version\": \"$(${tool} --version 2>&1 | head -1)\"}")
            atomic_success "$tool: installed"
        else
            checks+=("{\"tool\": \"$tool\", \"status\": \"fail\", \"version\": null}")
            atomic_error "$tool: NOT FOUND"
            all_pass=false
        fi
    done

    # Check Claude CLI
    if command -v claude &> /dev/null; then
        checks+=("{\"tool\": \"claude\", \"status\": \"pass\", \"version\": \"$(claude --version 2>&1 || echo 'unknown')\"}")
        atomic_success "claude: installed"
    else
        checks+=("{\"tool\": \"claude\", \"status\": \"fail\", \"version\": null}")
        atomic_error "claude: NOT FOUND (required!)"
        all_pass=false
    fi

    # Write report
    echo "{\"checks\": [$(IFS=,; echo "${checks[*]}")], \"all_pass\": $all_pass}" > "$report_file"

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
    phase_start "00-setup" "Project Setup"

    # Deterministic tasks
    phase_task "01" "Project Name" task_01_project_name || exit 1
    phase_task "02" "Description" task_02_description || exit 1
    phase_task "03" "Project Type" task_03_project_type || exit 1
    phase_task "04" "GitHub URL" task_04_github_url || exit 1

    # LLM task (optional - only if docs exist)
    phase_task "05" "Summarize Documentation" task_05_summarize_docs || true

    # Human gate before collecting sensitive info
    phase_human_gate "Ready to collect API keys?" || exit 1

    # Secure data collection
    phase_task "06" "API Keys" task_06_api_keys || exit 1

    # Material indexing
    phase_task "07" "Material Manifest" task_07_material_manifest || true

    # Environment validation
    phase_task "08" "Environment Validation" task_08_validate_env || exit 1

    # Final human gate
    phase_human_gate "Configuration complete. Proceed to Phase 01 (Ideation)?" || exit 1

    phase_complete

    echo ""
    atomic_info "Next: Run ./phases/01-ideation/run.sh"
}

main "$@"
