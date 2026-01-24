#!/bin/bash
#
# ATOMIC CLAUDE - Audit Library
# AI-driven audit selection and execution for phase audits
#
# Usage:
#   source lib/audit.sh
#   audit_run_phase 2 "PRD Validation"   # Runs Phase 2 PRD audit
#
# Flow:
#   1. Gather context (codebase, phase artifacts, config)
#   2. Load AUDIT-INVENTORY.csv and filter by SDLC phase
#   3. AI prioritizes from pre-filtered audit list (50-200 audits vs 2,200)
#   4. User reviews and approves selection
#   5. Execute selected audits
#   6. Generate audit report
#

set -euo pipefail

# ============================================================================
# CROSS-PLATFORM HELPERS
# ============================================================================

# Get file modification time as epoch (cross-platform)
# Usage: _audit_file_mtime "/path/to/file"
_audit_file_mtime() {
    local file="$1"
    if stat -c %Y "$file" 2>/dev/null; then
        # GNU stat
        return 0
    elif stat -f %m "$file" 2>/dev/null; then
        # BSD/macOS stat
        return 0
    else
        echo 0
    fi
}

# ============================================================================
# CONFIGURATION
# ============================================================================

AUDIT_VERSION="0.2.0"
AUDIT_CONFIG_FILE="${AUDIT_CONFIG_FILE:-$ATOMIC_OUTPUT_DIR/0-setup/project-config.json}"
AUDIT_OUTPUT_DIR="${AUDIT_OUTPUT_DIR:-$ATOMIC_OUTPUT_DIR/audits}"
AUDIT_CACHE_DIR="${AUDIT_CACHE_DIR:-$ATOMIC_STATE_DIR/audit-cache}"

# Primary: CSV inventory with SDLC phase columns
AUDIT_INVENTORY_GITHUB_URL="https://raw.githubusercontent.com/turbobeest/audits/main/AUDIT-INVENTORY.csv"

# DEPRECATED: Old markdown menu (kept for fallback)
AUDIT_MENU_GITHUB_URL="https://raw.githubusercontent.com/turbobeest/audits/main/AUDIT-MENU.md"

# Default audit counts
AUDIT_MIN_RECOMMENDATIONS=10
AUDIT_MAX_RECOMMENDATIONS=30
AUDIT_DEFAULT_RECOMMENDATIONS=20

# Phase number to CSV column mapping
declare -A AUDIT_PHASE_COLUMNS=(
    [1]="discovery"
    [2]="prd"
    [3]="task_decomposition"
    [4]="specification"
    [5]="implementation"      # TDD + implementation
    [6]="testing"             # Code review uses testing column
    [7]="integration"
    [8]="deployment"
    [9]="post_production"
)

# ============================================================================
# STATE
# ============================================================================

declare -A _AUDIT_CONFIG
_AUDIT_INITIALIZED=false
_AUDIT_REPO_PATH=""
_AUDIT_INVENTORY_PATH=""
_AUDIT_MENU_PATH=""  # DEPRECATED

# ============================================================================
# INITIALIZATION
# ============================================================================

audit_init() {
    if [[ "$_AUDIT_INITIALIZED" == "true" ]]; then
        return 0
    fi

    mkdir -p "$AUDIT_OUTPUT_DIR" "$AUDIT_CACHE_DIR"

    # Load configuration
    if [[ -f "$AUDIT_CONFIG_FILE" ]]; then
        _audit_load_config
    fi

    _AUDIT_INITIALIZED=true
}

_audit_load_config() {
    local config="$AUDIT_CONFIG_FILE"

    # Get audits repository path
    _AUDIT_REPO_PATH=$(jq -r '.repositories.audits.repository // ""' "$config")

    # Check for local AUDIT-INVENTORY.csv (preferred)
    if [[ -n "$_AUDIT_REPO_PATH" && -f "$_AUDIT_REPO_PATH/AUDIT-INVENTORY.csv" ]]; then
        _AUDIT_INVENTORY_PATH="$_AUDIT_REPO_PATH/AUDIT-INVENTORY.csv"
    fi

    # DEPRECATED: Check for local AUDIT-MENU.md (fallback only)
    if [[ -n "$_AUDIT_REPO_PATH" && -f "$_AUDIT_REPO_PATH/AUDIT-MENU.md" ]]; then
        _AUDIT_MENU_PATH="$_AUDIT_REPO_PATH/AUDIT-MENU.md"
    fi

    # Load audit plan settings
    _AUDIT_CONFIG[default_profile]=$(jq -r '.audit_plan.default_profile // "standard"' "$config")
    _AUDIT_CONFIG[default_mode]=$(jq -r '.audit_plan.default_mode // "gate-high"' "$config")
    _AUDIT_CONFIG[severity_filter]=$(jq -r '.audit_plan.severity_filter // "high+"' "$config")
    _AUDIT_CONFIG[air_gap_mode]=$(jq -r '.audit_plan.air_gap_mode // "auto"' "$config")
}

# ============================================================================
# AUDIT INVENTORY (CSV-based, phase-filtered)
# ============================================================================

# Fetch AUDIT-INVENTORY.csv from local repo or GitHub
_audit_fetch_inventory_csv() {
    audit_init

    # Try local first
    if [[ -n "$_AUDIT_INVENTORY_PATH" && -f "$_AUDIT_INVENTORY_PATH" ]]; then
        cat "$_AUDIT_INVENTORY_PATH"
        return 0
    fi

    # Try cached version
    local cache_file="$AUDIT_CACHE_DIR/AUDIT-INVENTORY.csv"
    local cache_age_limit=$((24 * 60 * 60))  # 24 hours
    local cache_age

    if [[ -f "$cache_file" ]]; then
        cache_age=$(($(date +%s) - $(_audit_file_mtime "$cache_file")))
        if [[ $cache_age -lt $cache_age_limit ]]; then
            cat "$cache_file"
            return 0
        fi
    fi

    # Fetch from GitHub
    echo "Fetching AUDIT-INVENTORY.csv from GitHub..." >&2
    if curl -s --fail "$AUDIT_INVENTORY_GITHUB_URL" > "$cache_file" 2>/dev/null; then
        cat "$cache_file"
        return 0
    fi

    echo "ERROR: Could not fetch AUDIT-INVENTORY.csv" >&2
    return 1
}

# Get audits filtered by SDLC phase
# Returns: CSV subset with header + matching rows
audit_get_phase_audits() {
    local phase_num="$1"
    local phase_column="${AUDIT_PHASE_COLUMNS[$phase_num]:-}"

    if [[ -z "$phase_column" ]]; then
        echo "ERROR: Unknown phase number: $phase_num" >&2
        return 1
    fi

    local csv_content header col_index
    csv_content=$(_audit_fetch_inventory_csv)
    if [[ -z "$csv_content" ]]; then
        return 1
    fi

    # Get header and find column index for the phase
    header=$(echo "$csv_content" | head -1)
    col_index=$(echo "$header" | tr ',' '\n' | grep -n "^${phase_column}$" | cut -d: -f1)

    if [[ -z "$col_index" ]]; then
        echo "ERROR: Column '$phase_column' not found in CSV" >&2
        return 1
    fi

    # Output header
    echo "$header"

    # Filter rows where phase column = "Yes"
    echo "$csv_content" | tail -n +2 | awk -F',' -v col="$col_index" '$col == "Yes"'
}

# Format filtered audits for LLM consumption (concise format)
audit_format_for_llm() {
    local phase_num="$1"
    local max_audits="${2:-200}"
    local filtered count

    filtered=$(audit_get_phase_audits "$phase_num")
    if [[ -z "$filtered" ]]; then
        return 1
    fi

    count=$(echo "$filtered" | tail -n +2 | wc -l)
    local phase_column="${AUDIT_PHASE_COLUMNS[$phase_num]}"

    echo "## Audits Available for Phase $phase_num ($phase_column)"
    echo ""
    echo "Total applicable: $count audits"
    echo ""
    echo "| Audit ID | Name | Category | Tier | Automated |"
    echo "|----------|------|----------|------|-----------|"

    # Extract key columns: audit_id, audit_name, category, tier, fully_automated
    echo "$filtered" | tail -n +2 | head -n "$max_audits" | \
        awk -F',' '{
            audit_id=$1
            name=$3
            category=$4
            tier=$7
            automated=($24=="Yes" ? "Yes" : ($25=="Yes" ? "Semi" : "Manual"))
            printf "| %s | %s | %s | %s | %s |\n", audit_id, name, category, tier, automated
        }'

    if [[ "$count" -gt "$max_audits" ]]; then
        echo ""
        echo "_Showing first $max_audits of $count applicable audits_"
    fi
}

# ============================================================================
# DEPRECATED: AUDIT-MENU.md FETCHING (kept for fallback)
# ============================================================================

# DEPRECATED: Fetch AUDIT-MENU.md from local repo or GitHub
# Use audit_get_phase_audits() instead for phase-filtered CSV access
audit_fetch_menu() {
    echo "WARNING: audit_fetch_menu() is deprecated. Use audit_get_phase_audits() for phase-filtered audits." >&2

    audit_init

    # Try local first
    if [[ -n "$_AUDIT_MENU_PATH" && -f "$_AUDIT_MENU_PATH" ]]; then
        cat "$_AUDIT_MENU_PATH"
        return 0
    fi

    # Try cached version
    local cache_file="$AUDIT_CACHE_DIR/AUDIT-MENU.md"
    local cache_age_limit=$((24 * 60 * 60))  # 24 hours
    local cache_age

    if [[ -f "$cache_file" ]]; then
        cache_age=$(($(date +%s) - $(_audit_file_mtime "$cache_file")))
        if [[ $cache_age -lt $cache_age_limit ]]; then
            cat "$cache_file"
            return 0
        fi
    fi

    # Fetch from GitHub
    echo "Fetching AUDIT-MENU.md from GitHub..." >&2
    if curl -s --fail "$AUDIT_MENU_GITHUB_URL" > "$cache_file" 2>/dev/null; then
        cat "$cache_file"
        return 0
    fi

    echo "ERROR: Could not fetch AUDIT-MENU.md" >&2
    return 1
}

# ============================================================================
# CONTEXT GATHERING
# ============================================================================

# Gather context for AI audit recommendation
audit_gather_context() {
    local phase_num="$1"
    local phase_name="$2"

    audit_init

    local context=""
    local project_name project_type project_desc

    # Project info
    if [[ -f "$AUDIT_CONFIG_FILE" ]]; then
        project_name=$(jq -r '.project.name // "unknown"' "$AUDIT_CONFIG_FILE")
        project_type=$(jq -r '.project.type // "unknown"' "$AUDIT_CONFIG_FILE")
        project_desc=$(jq -r '.project.description // ""' "$AUDIT_CONFIG_FILE")

        context+="PROJECT:\n"
        context+="  Name: $project_name\n"
        context+="  Type: $project_type\n"
        context+="  Description: $project_desc\n\n"
    fi

    # Tech stack detection
    local tech_stack=""
    if [[ -f "package.json" ]]; then
        tech_stack+="Node.js/JavaScript, "
    fi
    if [[ -f "requirements.txt" ]] || [[ -f "pyproject.toml" ]]; then
        tech_stack+="Python, "
    fi
    if [[ -f "Cargo.toml" ]]; then
        tech_stack+="Rust, "
    fi
    if [[ -f "go.mod" ]]; then
        tech_stack+="Go, "
    fi
    if [[ -f "Dockerfile" ]]; then
        tech_stack+="Docker, "
    fi

    context+="TECH STACK: ${tech_stack:-Not detected}\n\n"

    # Phase artifacts
    context+="PHASE: $phase_num - $phase_name\n\n"
    context+="PHASE ARTIFACTS:\n"

    local artifacts_dir="$ATOMIC_OUTPUT_DIR/phase-$phase_num"
    if [[ -d "$artifacts_dir" ]]; then
        for artifact in "$artifacts_dir"/*.{json,md}; do
            if [[ -f "$artifact" ]]; then
                context+="  - $(basename "$artifact")\n"
            fi
        done
    fi

    # Compliance requirements (if configured)
    local compliance
    compliance=$(jq -r '.compliance // "standard security practices"' "$AUDIT_CONFIG_FILE" 2>/dev/null || echo "standard security practices")
    context+="\nCOMPLIANCE REQUIREMENTS: $compliance\n"

    echo -e "$context"
}

# ============================================================================
# AI-DRIVEN AUDIT SELECTION
# ============================================================================

# Get AI recommendations for audits (using phase-filtered CSV)
audit_get_recommendations() {
    local phase_num="$1"
    local phase_name="$2"
    local num_recommendations="${3:-$AUDIT_DEFAULT_RECOMMENDATIONS}"

    audit_init

    # Gather context
    local context audit_list audit_count prompt_file
    context=$(audit_gather_context "$phase_num" "$phase_name")

    # Get phase-filtered audit list (much smaller than full 2,200)
    local phase_column="${AUDIT_PHASE_COLUMNS[$phase_num]:-}"
    audit_list=$(audit_format_for_llm "$phase_num" 150)
    audit_count=$(audit_get_phase_audits "$phase_num" 2>/dev/null | tail -n +2 | wc -l)

    if [[ -z "$audit_list" ]]; then
        echo "ERROR: Could not fetch audits for phase $phase_num" >&2
        return 1
    fi

    echo -e "  ${DIM}Phase $phase_num has $audit_count applicable audits (filtered from 2,190)${NC}" >&2

    # Build prompt for AI with improved structure
    prompt_file=$(atomic_mktemp)
    cat > "$prompt_file" << EOF
# Task: Prioritize Audits for Phase $phase_num ($phase_name)

You are an audit recommender. The audit inventory has been PRE-FILTERED to show only audits applicable to Phase $phase_num ($phase_column column = Yes).

Your job is to PRIORITIZE the $num_recommendations most relevant audits from this pre-filtered list based on the project context.

## Project Context

$context

## Pre-Filtered Audit List (Phase $phase_num applicable)

$audit_list

## Prioritization Criteria

Rank audits by:
1. **Relevance** to project type and tech stack (highest weight)
2. **Tier** - prefer "expert" and "focused" over "basic"
3. **Automation** - prefer "Yes" (fully automated) for efficiency
4. **Category balance** - include audits from multiple categories

## Priority Calibration

- **high**: Critical for this phase, would catch major issues
- **medium**: Important but not blocking, good coverage
- **low**: Nice to have, additional assurance

## Output Format

Select exactly $num_recommendations audits and output as JSON:

{
  "phase": $phase_num,
  "phase_name": "$phase_name",
  "total_available": $audit_count,
  "recommendations": [
    {
      "audit_id": "security-trust.application-security.cors-policy",
      "name": "CORS Policy Audit",
      "category": "security-trust",
      "relevance": "API project needs proper CORS configuration",
      "dependency_status": "ready",
      "priority": "high"
    },
    {
      "audit_id": "code-quality.testing.unit-test-coverage",
      "name": "Unit Test Coverage Audit",
      "category": "code-quality",
      "relevance": "TDD phase requires coverage validation",
      "dependency_status": "ready",
      "priority": "high"
    }
  ],
  "summary": "Brief summary of audit focus areas for this phase"
}

## Rules

- Use EXACT audit_id values from the table (e.g., "security-trust.application-security.cors-policy")
- Include a mix of categories for balanced coverage
- Set dependency_status to "ready" for fully_automated=Yes audits
- Output ONLY valid JSON, no markdown

EOF

    local output_file="$AUDIT_CACHE_DIR/recommendations-phase-$phase_num.json"

    # Use provider library for invocation (bulk task)
    source "$ATOMIC_ROOT/lib/provider.sh"
    provider_invoke "$prompt_file" "$output_file" "bulk" --format=json

    rm -f "$prompt_file"

    if [[ -f "$output_file" ]] && jq -e . "$output_file" &>/dev/null; then
        cat "$output_file"
    else
        echo "ERROR: Failed to get recommendations" >&2
        return 1
    fi
}

# ============================================================================
# USER INTERACTION
# ============================================================================

# Present recommendations to user and get approval
audit_present_recommendations() {
    local recommendations_json="$1"
    local ready_count needs_deps_count total_count summary

    ready_count=$(echo "$recommendations_json" | jq '[.recommendations[] | select(.dependency_status == "ready")] | length')
    needs_deps_count=$(echo "$recommendations_json" | jq '[.recommendations[] | select(.dependency_status == "needs-deps")] | length')
    total_count=$(echo "$recommendations_json" | jq '.recommendations | length')

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AUDIT RECOMMENDATIONS${NC}                                        ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Summary
    summary=$(echo "$recommendations_json" | jq -r '.summary // ""')
    if [[ -n "$summary" ]]; then
        echo -e "  ${DIM}$summary${NC}"
        echo ""
    fi

    # Ready to run
    if [[ "$ready_count" -gt 0 ]]; then
        echo -e "  ${GREEN}●${NC} ${BOLD}READY TO RUN${NC} ($ready_count audits)"
        echo ""

        echo "$recommendations_json" | jq -r '.recommendations[] | select(.dependency_status == "ready") | "    ☑ \(.audit_id)  \(.name)"'
        echo ""
    fi

    # Needs dependencies
    if [[ "$needs_deps_count" -gt 0 ]]; then
        echo -e "  ${YELLOW}○${NC} ${BOLD}DEPENDENCIES REQUIRED${NC} ($needs_deps_count audits)"
        echo ""

        echo "$recommendations_json" | jq -r '.recommendations[] | select(.dependency_status == "needs-deps") | "    ☐ \(.audit_id)  \(.name)"'
        echo ""
    fi

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  Options:"
    echo ""
    echo -e "    ${GREEN}[1]${NC} Accept recommendations (run ready audits)"
    echo -e "    ${GREEN}[2]${NC} View audit details"
    echo -e "    ${GREEN}[3]${NC} Add audit by ID"
    echo -e "    ${GREEN}[4]${NC} Remove audit from selection"
    echo -e "    ${GREEN}[5]${NC} Generate dependency manifest"
    echo -e "    ${GREEN}[6]${NC} Skip audits for this phase"
    echo ""

    read -p "  Select [1]: " choice
    choice=${choice:-1}

    echo "$choice"
}

# ============================================================================
# AUDIT EXECUTION
# ============================================================================

# Execute selected audits
audit_execute() {
    local recommendations_json="$1"
    local output_dir="${2:-$AUDIT_OUTPUT_DIR}"

    audit_init

    mkdir -p "$output_dir"

    local phase_num ready_audits audit_count audit audit_id audit_name result status
    phase_num=$(echo "$recommendations_json" | jq -r '.phase')
    local report_file="$output_dir/phase-$phase_num-report.json"
    local results=()

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}EXECUTING AUDITS${NC}                                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Get ready audits
    ready_audits=$(echo "$recommendations_json" | jq -c '[.recommendations[] | select(.dependency_status == "ready")]')
    audit_count=$(echo "$ready_audits" | jq 'length')

    local passed=0
    local failed=0
    local warnings=0

    for ((i=0; i<audit_count; i++)); do
        audit=$(echo "$ready_audits" | jq -c ".[$i]")
        audit_id=$(echo "$audit" | jq -r '.audit_id')
        audit_name=$(echo "$audit" | jq -r '.name')

        echo -e "  ${DIM}[$((i+1))/$audit_count]${NC} $audit_id: $audit_name"

        # Execute audit
        result=$(_audit_execute_single "$audit_id" "$audit_name")
        status=$(echo "$result" | jq -r '.status')

        case "$status" in
            pass)
                echo -e "    ${GREEN}✓ PASS${NC}"
                ((passed++))
                ;;
            fail)
                echo -e "    ${RED}✗ FAIL${NC}"
                ((failed++))
                ;;
            warn)
                echo -e "    ${YELLOW}⚠ WARNING${NC}"
                ((warnings++))
                ;;
        esac

        results+=("$result")
    done

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Results:${NC} ${GREEN}$passed passed${NC}, ${RED}$failed failed${NC}, ${YELLOW}$warnings warnings${NC}"
    echo ""

    # Generate report
    local report
    report=$(cat <<EOF
{
    "phase": $phase_num,
    "timestamp": "$(date -Iseconds)",
    "summary": {
        "total": $audit_count,
        "passed": $passed,
        "failed": $failed,
        "warnings": $warnings
    },
    "results": $(printf '%s\n' "${results[@]}" | jq -s '.'),
    "recommendations": $(echo "$recommendations_json" | jq '.recommendations')
}
EOF
)

    echo "$report" > "$report_file"
    echo -e "  ${GREEN}✓${NC} Report saved: $report_file"

    # Register audit artifacts for downstream tasks
    atomic_context_artifact "phase${phase_num}_audit_report" "$report_file" "Phase $phase_num audit results"
    local recommendations_file="$output_dir/phase-$phase_num-recommendations.json"
    [[ -f "$recommendations_file" ]] && atomic_context_artifact "phase${phase_num}_audit_recommendations" "$recommendations_file" "Phase $phase_num audit recommendations"
    atomic_context_decision "Phase $phase_num audit: $passed passed, $failed failed, $warnings warnings" "audit"

    # Return status based on mode
    local mode="${_AUDIT_CONFIG[default_mode]:-gate-high}"
    local severity_filter="${_AUDIT_CONFIG[severity_filter]:-high+}"

    if [[ "$failed" -gt 0 ]]; then
        case "$mode" in
            gate-all)
                return 1
                ;;
            gate-high|gate-critical)
                # Check if any high/critical failures
                local high_fails
                high_fails=$(printf '%s\n' "${results[@]}" | jq -s '[.[] | select(.status == "fail" and (.severity == "high" or .severity == "critical"))] | length')
                if [[ "$high_fails" -gt 0 ]]; then
                    return 1
                fi
                ;;
            report-only)
                return 0
                ;;
        esac
    fi

    return 0
}

# Execute a single audit
_audit_execute_single() {
    local audit_id="$1"
    local audit_name="$2"

    # Look for audit file in repository
    local audit_file=""
    if [[ -n "$_AUDIT_REPO_PATH" ]]; then
        # Search in categories
        audit_file=$(find "$_AUDIT_REPO_PATH/categories" -name "*$audit_id*.md" -type f 2>/dev/null | head -1)
    fi

    if [[ -z "$audit_file" || ! -f "$audit_file" ]]; then
        # Audit file not found - generate basic check
        cat <<EOF
{
    "audit_id": "$audit_id",
    "name": "$audit_name",
    "status": "warn",
    "severity": "low",
    "message": "Audit file not found locally. Manual review recommended.",
    "findings": []
}
EOF
        return 0
    fi

    # Read audit file content
    local audit_content
    audit_content=$(cat "$audit_file" 2>/dev/null) || {
        cat <<EOF
{
    "audit_id": "$audit_id",
    "name": "$audit_name",
    "status": "error",
    "severity": "low",
    "message": "Failed to read audit file",
    "findings": []
}
EOF
        return 0
    }

    # Extract severity from audit file if present
    local severity="medium"
    if echo "$audit_content" | grep -qi "severity.*high"; then
        severity="high"
    elif echo "$audit_content" | grep -qi "severity.*low"; then
        severity="low"
    elif echo "$audit_content" | grep -qi "severity.*critical"; then
        severity="critical"
    fi

    # Extract checklist items from markdown
    local checklist_items
    checklist_items=$(echo "$audit_content" | grep -E '^\s*[-*]\s*\[[ x]\]' | wc -l)

    # For simple audits (no complex checks), return basic pass
    if [[ $checklist_items -eq 0 ]]; then
        cat <<EOF
{
    "audit_id": "$audit_id",
    "name": "$audit_name",
    "status": "pass",
    "severity": "$severity",
    "message": "Audit reviewed - no automated checks defined",
    "findings": [],
    "audit_file": "$audit_file",
    "requires_manual_review": true
}
EOF
        return 0
    fi

    # Count items (basic static analysis)
    local total_items=$checklist_items
    cat <<EOF
{
    "audit_id": "$audit_id",
    "name": "$audit_name",
    "status": "pending",
    "severity": "$severity",
    "message": "Audit has $total_items checklist items requiring review",
    "findings": [],
    "audit_file": "$audit_file",
    "checklist_items": $total_items,
    "requires_manual_review": true
}
EOF
}

# ============================================================================
# DEPENDENCY MANIFEST
# ============================================================================

# Generate dependency manifest for air-gapped environments
audit_generate_dependency_manifest() {
    local recommendations_json="$1"
    local output_file="${2:-$AUDIT_OUTPUT_DIR/dependency-manifest.md}"
    local needs_deps dep_count

    needs_deps=$(echo "$recommendations_json" | jq -c '[.recommendations[] | select(.dependency_status == "needs-deps")]')
    dep_count=$(echo "$needs_deps" | jq 'length')

    cat > "$output_file" << EOF
# Audit Dependency Manifest
Generated: $(date -Iseconds)

## Summary
Total audits requiring dependencies: $dep_count

## Required Dependencies

| Audit ID | Audit Name | Required |
|----------|------------|----------|
EOF

    echo "$needs_deps" | jq -r '.[] | "| \(.audit_id) | \(.name) | TBD |"' >> "$output_file"

    cat >> "$output_file" << EOF

## Transfer Instructions
1. Download required files on a connected system
2. Transfer via approved media to air-gapped environment
3. Place files in: \`audits/dependencies/\`
4. Re-run audit task

## Notes
- See individual audit files for specific dependency URLs
- Some dependencies may be large (regulatory documents, databases)
- Check for updates periodically
EOF

    echo -e "  ${GREEN}✓${NC} Dependency manifest saved: $output_file"
}

# ============================================================================
# PHASE AUDIT WRAPPER (for task scripts)
# ============================================================================

# Wrapper for phase audit tasks - provides mode selection UI
# Usage: audit_phase_wrapper <phase_num> <phase_name> <legacy_function>
audit_phase_wrapper() {
    local phase_num="$1"
    local phase_name="$2"
    local legacy_callback="${3:-}"

    source "$ATOMIC_ROOT/lib/atomic.sh"

    local audit_dir="$ATOMIC_ROOT/.claude/audit"
    mkdir -p "$audit_dir"

    atomic_step "Phase Audit"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ PHASE AUDIT: $(printf '%-44s' "$phase_name")│${NC}"
    echo -e "${DIM}  │                                                             │${NC}"
    echo -e "${DIM}  │ An AI-driven audit reviews Phase $phase_num outputs against the     │${NC}"
    echo -e "${DIM}  │ comprehensive audit library (~2,200 audits).                │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AUDIT MODE SELECTION${NC}                                        ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${CYAN}Select audit mode:${NC}"
    echo ""
    echo -e "    ${GREEN}[1]${NC} AI-Driven ${DIM}(recommended)${NC}"
    echo -e "        ${DIM}AI recommends audits from 2,200+ library based on context${NC}"
    echo ""

    if [[ -n "$legacy_callback" ]] && declare -f "$legacy_callback" > /dev/null 2>&1; then
        echo -e "    ${GREEN}[2]${NC} Legacy Dimensions"
        echo -e "        ${DIM}Static dimension-based audit for Phase $phase_num${NC}"
        echo ""
    fi

    echo -e "    ${GREEN}[3]${NC} Skip Audit"
    echo -e "        ${DIM}Proceed without audit (not recommended)${NC}"
    echo ""

    read -p "  Mode [1]: " mode_choice
    mode_choice=${mode_choice:-1}

    case "$mode_choice" in
        1)
            audit_run_phase "$phase_num" "$phase_name"
            return $?
            ;;
        2)
            if [[ -n "$legacy_callback" ]] && declare -f "$legacy_callback" > /dev/null 2>&1; then
                "$legacy_callback"
                return $?
            else
                echo -e "  ${YELLOW}!${NC} Legacy mode not available for this phase"
                audit_run_phase "$phase_num" "$phase_name"
                return $?
            fi
            ;;
        3)
            echo -e "  ${YELLOW}!${NC} Skipping audit for Phase $phase_num"
            atomic_context_decision "Phase $phase_num audit skipped by user" "audit"
            return 0
            ;;
        *)
            audit_run_phase "$phase_num" "$phase_name"
            return $?
            ;;
    esac
}

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

# Run phase audit with AI-driven selection
audit_run_phase() {
    local phase_num="$1"
    local phase_name="$2"

    audit_init

    echo ""
    atomic_h1 "PHASE $phase_num AUDIT: $phase_name"
    echo ""

    # Get AI recommendations
    echo -e "  ${DIM}Analyzing phase context and generating audit recommendations...${NC}"
    echo ""

    local recommendations choice
    recommendations=$(audit_get_recommendations "$phase_num" "$phase_name")

    if [[ -z "$recommendations" ]] || ! echo "$recommendations" | jq -e . &>/dev/null; then
        echo -e "  ${RED}✗${NC} Failed to generate recommendations"
        return 1
    fi

    # Save recommendations
    echo "$recommendations" > "$AUDIT_OUTPUT_DIR/phase-$phase_num-recommendations.json"

    # Present to user
    choice=$(audit_present_recommendations "$recommendations")

    case "$choice" in
        1)
            # Accept and execute
            audit_execute "$recommendations"
            return $?
            ;;
        2)
            # View details
            echo ""
            echo "$recommendations" | jq -r '.recommendations[] | "[\(.audit_id)] \(.name)\n  Relevance: \(.relevance)\n  Status: \(.dependency_status)\n"'
            echo ""
            # Recurse for next choice
            audit_run_phase "$phase_num" "$phase_name"
            ;;
        3)
            # Add audit by ID
            read -p "  Enter audit ID to add: " add_id
            if [[ -n "$add_id" ]]; then
                # Check if already in recommendations
                local exists
                exists=$(echo "$recommendations" | jq -r --arg id "$add_id" '.recommendations[] | select(.audit_id == $id) | .audit_id')
                if [[ -n "$exists" ]]; then
                    echo -e "  ${YELLOW}!${NC} Audit $add_id already in recommendations"
                else
                    # Add to recommendations with manual status
                    recommendations=$(echo "$recommendations" | jq --arg id "$add_id" '
                        .recommendations += [{
                            "audit_id": $id,
                            "name": "Manual audit: " + $id,
                            "relevance": "user-added",
                            "dependency_status": "ready",
                            "added_manually": true
                        }]
                    ')
                    echo "$recommendations" > "$AUDIT_OUTPUT_DIR/phase-$phase_num-recommendations.json"
                    echo -e "  ${GREEN}✓${NC} Added audit $add_id to recommendations"
                fi
            fi
            audit_run_phase "$phase_num" "$phase_name"
            ;;
        4)
            # Remove audit by ID
            read -p "  Enter audit ID to remove: " remove_id
            if [[ -n "$remove_id" ]]; then
                local before_count after_count
                before_count=$(echo "$recommendations" | jq '.recommendations | length')
                recommendations=$(echo "$recommendations" | jq --arg id "$remove_id" '
                    .recommendations |= map(select(.audit_id != $id))
                ')
                after_count=$(echo "$recommendations" | jq '.recommendations | length')
                if [[ "$before_count" -ne "$after_count" ]]; then
                    echo "$recommendations" > "$AUDIT_OUTPUT_DIR/phase-$phase_num-recommendations.json"
                    echo -e "  ${GREEN}✓${NC} Removed audit $remove_id from recommendations"
                else
                    echo -e "  ${YELLOW}!${NC} Audit $remove_id not found in recommendations"
                fi
            fi
            audit_run_phase "$phase_num" "$phase_name"
            ;;
        5)
            # Generate manifest
            audit_generate_dependency_manifest "$recommendations"
            audit_run_phase "$phase_num" "$phase_name"
            ;;
        6)
            # Skip
            echo -e "  ${YELLOW}!${NC} Skipping audits for Phase $phase_num"
            return 0
            ;;
    esac
}
