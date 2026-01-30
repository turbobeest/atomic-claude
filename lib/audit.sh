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

# Default audit counts (can override via environment variables)
AUDIT_MIN_RECOMMENDATIONS="${AUDIT_MIN_RECOMMENDATIONS:-10}"
AUDIT_MAX_RECOMMENDATIONS="${AUDIT_MAX_RECOMMENDATIONS:-50}"
AUDIT_DEFAULT_RECOMMENDATIONS="${AUDIT_DEFAULT_RECOMMENDATIONS:-25}"

# Run ALL applicable audits (bypass LLM selection)
# WARNING: Can be 300-1900 audits depending on phase - very expensive!
AUDIT_RUN_ALL="${AUDIT_RUN_ALL:-false}"

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

    # Fallback 1: check embedded 'external/audits' directory (monorepo deployment)
    if [[ -z "$_AUDIT_REPO_PATH" || ! -d "$_AUDIT_REPO_PATH" ]]; then
        local embedded_repo="$ATOMIC_ROOT/external/audits"
        if [[ -d "$embedded_repo" && -f "$embedded_repo/AUDIT-INVENTORY.csv" ]]; then
            _AUDIT_REPO_PATH=$(cd "$embedded_repo" && pwd)
        fi
    fi

    # Fallback 2: check sibling 'audits' directory
    if [[ -z "$_AUDIT_REPO_PATH" || ! -d "$_AUDIT_REPO_PATH" ]]; then
        local sibling_repo="$ATOMIC_ROOT/../audits"
        if [[ -d "$sibling_repo" && -f "$sibling_repo/AUDIT-INVENTORY.csv" ]]; then
            _AUDIT_REPO_PATH=$(cd "$sibling_repo" && pwd)
        fi
    fi

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

    # Try configured local path first
    if [[ -n "$_AUDIT_INVENTORY_PATH" && -f "$_AUDIT_INVENTORY_PATH" ]]; then
        cat "$_AUDIT_INVENTORY_PATH"
        return 0
    fi

    # Try embedded directory (monorepo deployment)
    local embedded_path="$ATOMIC_ROOT/external/audits/AUDIT-INVENTORY.csv"
    if [[ -f "$embedded_path" ]]; then
        cat "$embedded_path"
        return 0
    fi

    # Try well-known sibling directory (audits repo next to ATOMIC-CLAUDE)
    local sibling_path="$ATOMIC_ROOT/../audits/AUDIT-INVENTORY.csv"
    if [[ -f "$sibling_path" ]]; then
        cat "$sibling_path"
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
        # Phase column not in CSV yet — return all audits unfiltered.
        # The AI recommendation step will prioritize by relevance.
        echo "WARNING: Phase column '$phase_column' not found in CSV; returning all audits unfiltered" >&2
        echo "$csv_content"
        return 0
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

    # Extract key columns: audit_id(1), audit_name(3), category(4), tier(7), automatable(9)
    echo "$filtered" | tail -n +2 | head -n "$max_audits" | \
        awk -F',' '{
            audit_id=$1
            name=$3
            category=$4
            tier=$7
            automated=($9=="yes" ? "Yes" : ($9=="partial" ? "Semi" : "Manual"))
            printf "| %s | %s | %s | %s | %s |\n", audit_id, name, category, tier, automated
        }'

    if [[ "$count" -gt "$max_audits" ]]; then
        echo ""
        echo "_Showing first $max_audits of $count applicable audits_"
    fi
}

# ============================================================================
# CATALOG BROWSER (interactive category-based selection)
# ============================================================================

# Get unique top-level categories from the audit inventory
# Returns: one category per line with count
_audit_get_categories() {
    local phase_num="$1"
    local csv_content

    csv_content=$(audit_get_phase_audits "$phase_num" 2>/dev/null)
    if [[ -z "$csv_content" ]]; then
        return 1
    fi

    # Extract category (column 4) and count occurrences
    echo "$csv_content" | tail -n +2 | \
        awk -F',' '{print $4}' | \
        sort | uniq -c | sort -rn | \
        awk '{printf "%s|%d\n", $2, $1}'
}

# Get audits within a specific category
# Returns: CSV rows matching the category
_audit_get_by_category() {
    local phase_num="$1"
    local category="$2"
    local csv_content

    csv_content=$(audit_get_phase_audits "$phase_num" 2>/dev/null)
    if [[ -z "$csv_content" ]]; then
        return 1
    fi

    # Header
    echo "$csv_content" | head -1

    # Filter by category (column 4)
    echo "$csv_content" | tail -n +2 | awk -F',' -v cat="$category" '$4 == cat'
}

# Search audits by keyword in name or description
_audit_search() {
    local phase_num="$1"
    local keyword="$2"
    local csv_content

    csv_content=$(audit_get_phase_audits "$phase_num" 2>/dev/null)
    if [[ -z "$csv_content" ]]; then
        return 1
    fi

    # Header
    echo "$csv_content" | head -1

    # Search in audit_id (1), audit_name (3), description (5)
    echo "$csv_content" | tail -n +2 | awk -F',' -v kw="$keyword" '
        tolower($1) ~ tolower(kw) || tolower($3) ~ tolower(kw) || tolower($5) ~ tolower(kw)
    '
}

# Interactive catalog browser
# Returns: file path to recommendations JSON on stdout (menu goes to stderr)
audit_browse_catalog() {
    local phase_num="$1"
    local phase_name="$2"

    audit_init

    local selected_audits=()
    local phase_column="${AUDIT_PHASE_COLUMNS[$phase_num]:-prd}"

    while true; do
        {
        echo ""
        echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║${NC} ${BOLD}AUDIT CATALOG BROWSER${NC}                                       ${CYAN}║${NC}"
        echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
        echo ""

        if [[ ${#selected_audits[@]} -gt 0 ]]; then
            echo -e "  ${GREEN}Selected: ${#selected_audits[@]} audits${NC}"
            echo ""
        fi

        echo -e "  ${CYAN}Options:${NC}"
        echo ""
        echo -e "    ${GREEN}[1]${NC} Browse by category"
        echo -e "    ${GREEN}[2]${NC} Search by keyword"
        echo -e "    ${GREEN}[3]${NC} View current selection"
        echo -e "    ${GREEN}[4]${NC} Clear selection"
        echo -e "    ${GREEN}[5]${NC} Done - run selected audits"
        echo -e "    ${GREEN}[6]${NC} Back to mode selection"
        echo ""
        } >&2

        read -e -p "  Select [1]: " browse_choice
        browse_choice=${browse_choice:-1}

        case "$browse_choice" in
            1)
                _audit_browse_categories "$phase_num" selected_audits
                ;;
            2)
                _audit_search_interactive "$phase_num" selected_audits
                ;;
            3)
                _audit_show_selection selected_audits
                ;;
            4)
                selected_audits=()
                echo -e "  ${YELLOW}Selection cleared${NC}" >&2
                ;;
            5)
                if [[ ${#selected_audits[@]} -eq 0 ]]; then
                    echo -e "  ${YELLOW}No audits selected. Select at least one audit.${NC}" >&2
                    continue
                fi
                # Build recommendations JSON from selection - outputs file path to stdout
                _audit_build_recommendations_json "$phase_num" "$phase_name" selected_audits
                return 0
                ;;
            6)
                return 1  # Signal to go back
                ;;
            *)
                echo -e "  ${RED}Invalid choice${NC}" >&2
                ;;
        esac
    done
}

# Browse categories interactively
_audit_browse_categories() {
    local phase_num="$1"
    local -n _selected="$2"

    local categories category_list
    categories=$(_audit_get_categories "$phase_num")

    if [[ -z "$categories" ]]; then
        echo -e "  ${RED}No audits found for this phase${NC}" >&2
        return 1
    fi

    {
    echo ""
    echo -e "  ${BOLD}Categories for Phase $phase_num:${NC}"
    echo ""

    local i=1
    local -a cat_array=()
    while IFS='|' read -r cat count; do
        cat_array+=("$cat")
        printf "    ${GREEN}[%2d]${NC} %-40s ${DIM}(%d audits)${NC}\n" "$i" "$cat" "$count"
        ((i++))
    done <<< "$categories"

    echo ""
    echo -e "    ${GREEN}[a]${NC}  Select ALL audits for this phase"
    echo -e "    ${GREEN}[b]${NC}  Back"
    echo ""
    } >&2

    # Need cat_array in outer scope - rebuild it
    local -a cat_array=()
    while IFS='|' read -r cat count; do
        cat_array+=("$cat")
    done <<< "$categories"

    read -e -p "  Select category: " cat_choice

    if [[ "$cat_choice" == "b" || "$cat_choice" == "B" ]]; then
        return 0
    fi

    if [[ "$cat_choice" == "a" || "$cat_choice" == "A" ]]; then
        # Add all audits
        local all_audits
        all_audits=$(audit_get_phase_audits "$phase_num" | tail -n +2 | awk -F',' '{print $1}')
        while IFS= read -r aid; do
            [[ -z "$aid" ]] && continue
            # Check if already selected
            local found=false
            for existing in "${_selected[@]}"; do
                [[ "$existing" == "$aid" ]] && found=true && break
            done
            [[ "$found" == false ]] && _selected+=("$aid")
        done <<< "$all_audits"
        echo -e "  ${GREEN}Added all audits (${#_selected[@]} total selected)${NC}" >&2
        return 0
    fi

    if ! [[ "$cat_choice" =~ ^[0-9]+$ ]] || [[ "$cat_choice" -lt 1 ]] || [[ "$cat_choice" -gt ${#cat_array[@]} ]]; then
        echo -e "  ${RED}Invalid selection${NC}" >&2
        return 1
    fi

    local selected_category="${cat_array[$((cat_choice-1))]}"
    _audit_browse_category_audits "$phase_num" "$selected_category" _selected
}

# Browse audits within a category
_audit_browse_category_audits() {
    local phase_num="$1"
    local category="$2"
    local -n _cat_selected="$3"

    local audits
    audits=$(_audit_get_by_category "$phase_num" "$category")

    local i=1
    local -a audit_ids=()
    local -a audit_names=()

    # First pass: build arrays
    while IFS=',' read -r aid _ aname _; do
        [[ "$aid" == "audit_id" ]] && continue  # Skip header
        audit_ids+=("$aid")
        audit_names+=("$aname")
    done <<< "$audits"

    {
    echo ""
    echo -e "  ${BOLD}Category: ${CYAN}$category${NC}"
    echo ""

    for ((idx=0; idx<${#audit_ids[@]}; idx++)); do
        local aid="${audit_ids[$idx]}"
        local aname="${audit_names[$idx]}"

        # Check if already selected
        local marker=" "
        for existing in "${_cat_selected[@]}"; do
            [[ "$existing" == "$aid" ]] && marker="✓" && break
        done

        printf "    ${GREEN}[%2d]${NC} %s %-50s\n" "$((idx+1))" "$marker" "${aname:0:50}"
    done

    echo ""
    echo -e "    ${GREEN}[a]${NC}  Select ALL in this category"
    echo -e "    ${GREEN}[#]${NC}  Toggle specific audit (e.g., 1 or 1,3,5)"
    echo -e "    ${GREEN}[b]${NC}  Back to categories"
    echo ""
    } >&2

    read -e -p "  Select: " audit_choice

    if [[ "$audit_choice" == "b" || "$audit_choice" == "B" ]]; then
        return 0
    fi

    if [[ "$audit_choice" == "a" || "$audit_choice" == "A" ]]; then
        for aid in "${audit_ids[@]}"; do
            local found=false
            for existing in "${_cat_selected[@]}"; do
                [[ "$existing" == "$aid" ]] && found=true && break
            done
            [[ "$found" == false ]] && _cat_selected+=("$aid")
        done
        echo -e "  ${GREEN}Added all ${#audit_ids[@]} audits from $category${NC}" >&2
        return 0
    fi

    # Parse comma-separated numbers
    IFS=',' read -ra nums <<< "$audit_choice"
    for num in "${nums[@]}"; do
        num=$(echo "$num" | tr -d ' ')
        if [[ "$num" =~ ^[0-9]+$ ]] && [[ "$num" -ge 1 ]] && [[ "$num" -le ${#audit_ids[@]} ]]; then
            local aid="${audit_ids[$((num-1))]}"
            # Toggle: add if not present, remove if present
            local found=false
            local new_selected=()
            for existing in "${_cat_selected[@]}"; do
                if [[ "$existing" == "$aid" ]]; then
                    found=true
                else
                    new_selected+=("$existing")
                fi
            done
            if [[ "$found" == true ]]; then
                _cat_selected=("${new_selected[@]}")
                echo -e "  ${YELLOW}Removed: ${audit_names[$((num-1))]}${NC}" >&2
            else
                _cat_selected+=("$aid")
                echo -e "  ${GREEN}Added: ${audit_names[$((num-1))]}${NC}" >&2
            fi
        fi
    done
}

# Interactive search
_audit_search_interactive() {
    local phase_num="$1"
    local -n _search_selected="$2"

    echo "" >&2
    read -e -p "  Search keyword: " keyword

    if [[ -z "$keyword" ]]; then
        return 0
    fi

    local results
    results=$(_audit_search "$phase_num" "$keyword")
    local count
    count=$(echo "$results" | tail -n +2 | wc -l)

    if [[ "$count" -eq 0 ]]; then
        echo -e "  ${YELLOW}No audits found matching '$keyword'${NC}" >&2
        return 0
    fi

    local -a result_ids=()
    local -a result_names=()

    # First pass: build arrays
    while IFS=',' read -r aid _ aname _; do
        [[ "$aid" == "audit_id" ]] && continue
        result_ids+=("$aid")
        result_names+=("$aname")
    done <<< "$results"

    {
    echo ""
    echo -e "  ${BOLD}Search results for '${keyword}':${NC} ($count matches)"
    echo ""

    local display_count=0
    for ((idx=0; idx<${#result_ids[@]} && idx<30; idx++)); do
        local aid="${result_ids[$idx]}"
        local aname="${result_names[$idx]}"

        local marker=" "
        for existing in "${_search_selected[@]}"; do
            [[ "$existing" == "$aid" ]] && marker="✓" && break
        done

        printf "    ${GREEN}[%2d]${NC} %s %-50s\n" "$((idx+1))" "$marker" "${aname:0:50}"
        ((display_count++))
    done

    [[ $count -gt 30 ]] && echo -e "    ${DIM}... and $((count - 30)) more${NC}"

    echo ""
    echo -e "    ${GREEN}[a]${NC}  Add all results"
    echo -e "    ${GREEN}[#]${NC}  Toggle specific (e.g., 1 or 1,3,5)"
    echo -e "    ${GREEN}[b]${NC}  Back"
    echo ""
    } >&2

    read -e -p "  Select: " search_choice

    if [[ "$search_choice" == "b" || "$search_choice" == "B" ]]; then
        return 0
    fi

    if [[ "$search_choice" == "a" || "$search_choice" == "A" ]]; then
        for aid in "${result_ids[@]}"; do
            local found=false
            for existing in "${_search_selected[@]}"; do
                [[ "$existing" == "$aid" ]] && found=true && break
            done
            [[ "$found" == false ]] && _search_selected+=("$aid")
        done
        echo -e "  ${GREEN}Added $count audits from search results${NC}" >&2
        return 0
    fi

    # Parse selections
    IFS=',' read -ra nums <<< "$search_choice"
    for num in "${nums[@]}"; do
        num=$(echo "$num" | tr -d ' ')
        if [[ "$num" =~ ^[0-9]+$ ]] && [[ "$num" -ge 1 ]] && [[ "$num" -le ${#result_ids[@]} ]]; then
            local aid="${result_ids[$((num-1))]}"
            local found=false
            local new_selected=()
            for existing in "${_search_selected[@]}"; do
                if [[ "$existing" == "$aid" ]]; then
                    found=true
                else
                    new_selected+=("$existing")
                fi
            done
            if [[ "$found" == true ]]; then
                _search_selected=("${new_selected[@]}")
                echo -e "  ${YELLOW}Removed: ${result_names[$((num-1))]}${NC}" >&2
            else
                _search_selected+=("$aid")
                echo -e "  ${GREEN}Added: ${result_names[$((num-1))]}${NC}" >&2
            fi
        fi
    done
}

# Show current selection
_audit_show_selection() {
    local -n _show_selected="$1"

    {
    echo ""
    if [[ ${#_show_selected[@]} -eq 0 ]]; then
        echo -e "  ${YELLOW}No audits selected yet${NC}"
        return 0
    fi

    echo -e "  ${BOLD}Current selection (${#_show_selected[@]} audits):${NC}"
    echo ""

    local i=1
    for aid in "${_show_selected[@]}"; do
        printf "    %2d. %s\n" "$i" "$aid"
        ((i++))
    done
    echo ""
    } >&2
}

# Build recommendations JSON from manual selection
_audit_build_recommendations_json() {
    local phase_num="$1"
    local phase_name="$2"
    local -n _build_selected="$3"

    local csv_content recommendations=""
    csv_content=$(audit_get_phase_audits "$phase_num" 2>/dev/null)

    local count=0
    for aid in "${_build_selected[@]}"; do
        # Look up audit details from CSV
        local row aname category
        row=$(echo "$csv_content" | awk -F',' -v id="$aid" '$1 == id {print; exit}')
        if [[ -n "$row" ]]; then
            aname=$(echo "$row" | cut -d',' -f3)
            category=$(echo "$row" | cut -d',' -f4)
        else
            aname="$aid"
            category="unknown"
        fi

        [[ $count -gt 0 ]] && recommendations+=","
        recommendations+=$(cat <<AUDIT_JSON
    {
      "audit_id": "$aid",
      "name": "$aname",
      "category": "$category",
      "relevance": "Manually selected",
      "dependency_status": "ready",
      "priority": "high"
    }
AUDIT_JSON
)
        ((count++))
    done

    # Output to file and echo path
    local output_file="$AUDIT_OUTPUT_DIR/phase-$phase_num-recommendations.json"
    cat > "$output_file" <<JSON_OUT
{
  "phase": $phase_num,
  "phase_name": "$phase_name",
  "total_available": $(audit_get_phase_audits "$phase_num" 2>/dev/null | tail -n +2 | wc -l),
  "recommendations": [
$recommendations
  ],
  "summary": "Manually selected $count audits via catalog browser"
}
JSON_OUT

    echo "$output_file"
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

# Generate recommendations for ALL applicable audits (no LLM selection)
# Used when AUDIT_RUN_ALL=true
audit_get_all_recommendations() {
    local phase_num="$1"
    local phase_name="$2"

    audit_init

    local phase_column="${AUDIT_PHASE_COLUMNS[$phase_num]:-}"
    local csv_file
    csv_file=$(_audit_fetch_inventory_csv)

    if [[ -z "$csv_file" || ! -f "$csv_file" ]]; then
        echo '{"error": "Could not fetch audit inventory"}'
        return 1
    fi

    # Get header to find column index
    local header col_idx
    header=$(head -1 "$csv_file")
    col_idx=$(echo "$header" | tr ',' '\n' | grep -n "^${phase_column}$" | cut -d: -f1)

    if [[ -z "$col_idx" ]]; then
        echo '{"error": "Phase column not found: '"$phase_column"'"}'
        return 1
    fi

    # Count all applicable audits
    local audit_count
    audit_count=$(awk -F',' -v col="$col_idx" 'NR>1 && $col == "Yes" {c++} END {print c+0}' "$csv_file")

    echo -e "  ${YELLOW}⚠ AUDIT_RUN_ALL=true: Selecting ALL $audit_count applicable audits${NC}" >&2
    echo -e "  ${DIM}This will run every audit marked for phase $phase_num ($phase_column)${NC}" >&2

    # Generate JSON recommendations for ALL applicable audits
    awk -F',' -v col="$col_idx" -v phase="$phase_num" -v phase_name="$phase_name" -v total="$audit_count" '
    BEGIN {
        print "{"
        print "  \"phase\": " phase ","
        print "  \"phase_name\": \"" phase_name "\","
        print "  \"total_available\": " total ","
        print "  \"run_all\": true,"
        print "  \"recommendations\": ["
        first = 1
    }
    NR > 1 && $col == "Yes" {
        if (!first) print ","
        first = 0

        # Extract fields: audit_id=$1, audit_name=$3, category=$4, tier=$7, automatable=$9
        gsub(/"/, "\\\"", $3)  # Escape quotes in name

        printf "    {\n"
        printf "      \"audit_id\": \"%s\",\n", $1
        printf "      \"name\": \"%s\",\n", $3
        printf "      \"category\": \"%s\",\n", $4
        printf "      \"tier\": \"%s\",\n", $7
        printf "      \"relevance\": \"Phase-applicable audit (run-all mode)\",\n"
        printf "      \"dependency_status\": \"ready\",\n"
        printf "      \"priority\": \"medium\"\n"
        printf "    }"
    }
    END {
        print ""
        print "  ],"
        print "  \"summary\": \"Running ALL " total " audits applicable to phase " phase " (" phase_name "). No LLM prioritization.\""
        print "}"
    }
    ' "$csv_file"
}

# Get AI recommendations for audits (using phase-filtered CSV)
audit_get_recommendations() {
    local phase_num="$1"
    local phase_name="$2"
    local num_recommendations="${3:-$AUDIT_DEFAULT_RECOMMENDATIONS}"

    # Check for run-all mode
    if [[ "$AUDIT_RUN_ALL" == "true" ]]; then
        audit_get_all_recommendations "$phase_num" "$phase_name"
        return $?
    fi

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

Select between $AUDIT_MIN_RECOMMENDATIONS and $num_recommendations audits based on project complexity:
- Simple projects (CLI tools, small APIs): ~$AUDIT_MIN_RECOMMENDATIONS audits
- Medium projects (web apps, services): ~$((num_recommendations - 5)) audits
- Complex projects (trading platforms, distributed systems, financial): ~$num_recommendations audits

Output as JSON:

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
- dependency_status MUST be one of: "ready" (can run immediately), "needs_review" (needs manual review), "needs-deps" (blocked by other audits)
- For fully_automated=Yes audits, set dependency_status to "ready"
- For partially automated or manual audits, set dependency_status to "ready" (they just take longer)
- Output ONLY valid JSON, no markdown

EOF

    local output_file="$AUDIT_CACHE_DIR/recommendations-phase-$phase_num.json"

    # Use provider library for invocation (bulk task)
    source "$ATOMIC_ROOT/lib/provider.sh"
    local invoke_rc=0
    provider_invoke "$prompt_file" "$output_file" "bulk" --format=json >&2 || invoke_rc=$?

    rm -f "$prompt_file"

    if [[ $invoke_rc -ne 0 ]]; then
        echo "ERROR: provider_invoke failed (exit code: $invoke_rc)" >&2
        if [[ -s "${output_file}.err" ]]; then
            echo "  Stderr: $(head -5 "${output_file}.err")" >&2
        fi
        if [[ -s "$output_file" ]]; then
            echo "  Output (first 3 lines): $(head -3 "$output_file")" >&2
        else
            echo "  Output file empty or missing" >&2
        fi
        return 1
    fi

    if [[ -f "$output_file" ]] && jq -e . "$output_file" &>/dev/null; then
        # Normalize dependency_status values (AI might invent non-standard values)
        local normalized
        normalized=$(jq '
            .recommendations |= map(
                .dependency_status = (
                    if .dependency_status == "ready" then "ready"
                    elif .dependency_status == "needs_review" or .dependency_status == "requires_review" then "needs_review"
                    elif .dependency_status == "needs-deps" or .dependency_status == "needs_deps" or .dependency_status == "blocked" then "needs-deps"
                    else "ready"
                    end
                )
            )
        ' "$output_file")
        echo "$normalized" > "$output_file"
        cat "$output_file"
    elif [[ -f "$output_file" ]] && [[ -s "$output_file" ]]; then
        # Try to extract JSON from markdown-wrapped output
        local fixed_json
        fixed_json=$(atomic_json_fix "$output_file")
        if echo "$fixed_json" | jq -e . &>/dev/null; then
            # Normalize dependency_status values here too
            local normalized
            normalized=$(echo "$fixed_json" | jq '
                .recommendations |= map(
                    .dependency_status = (
                        if .dependency_status == "ready" then "ready"
                        elif .dependency_status == "needs_review" or .dependency_status == "requires_review" then "needs_review"
                        elif .dependency_status == "needs-deps" or .dependency_status == "needs_deps" or .dependency_status == "blocked" then "needs-deps"
                        else "ready"
                        end
                    )
                )
            ')
            echo "$normalized" > "$output_file"
            cat "$output_file"
        else
            echo "ERROR: Output is not valid JSON (even after fix attempt)" >&2
            local fsize
            fsize=$(wc -c < "$output_file")
            echo "  File size: ${fsize} bytes" >&2
            echo "  First 5 lines:" >&2
            head -5 "$output_file" >&2
            return 1
        fi
    else
        echo "ERROR: Output file empty or missing: $output_file" >&2
        if [[ -s "${output_file}.err" ]]; then
            echo "  Stderr: $(head -5 "${output_file}.err")" >&2
        fi
        return 1
    fi
}

# ============================================================================
# USER INTERACTION
# ============================================================================

# Resolve a user reference (number, comma-separated numbers, or dotted audit ID) to audit IDs
# Display order: ready → needs_review → needs-deps (matches audit_present_recommendations)
# Usage: local ids=$(_audit_resolve_refs "$recommendations_json" "$user_input")
# Returns newline-separated audit IDs
_audit_resolve_refs() {
    local recs_json="$1"
    local input="$2"

    # Build display-order array (same order as the numbered display)
    local display_order
    display_order=$(echo "$recs_json" | jq -r '
        [(.recommendations[] | select(.dependency_status == "ready")),
         (.recommendations[] | select(.dependency_status == "needs_review")),
         (.recommendations[] | select(.dependency_status == "needs-deps"))]
        | .[].audit_id
    ')

    # If input contains dots, treat as a literal audit ID
    if [[ "$input" == *.* ]]; then
        echo "$input"
        return
    fi

    # Parse comma-separated numbers (e.g. "1,3,5" or "4")
    local IFS=', '
    local nums
    read -ra nums <<< "$input"

    local id_array=()
    readarray -t id_array <<< "$display_order"

    local n
    for n in "${nums[@]}"; do
        n=$(echo "$n" | tr -d ' ')
        if [[ "$n" =~ ^[0-9]+$ ]] && [[ "$n" -ge 1 ]] && [[ "$n" -le "${#id_array[@]}" ]]; then
            echo "${id_array[$((n - 1))]}"
        fi
    done
}

# Present recommendations to user and get approval
audit_present_recommendations() {
    local recommendations_json="$1"
    local ready_count needs_deps_count total_count summary

    ready_count=$(echo "$recommendations_json" | jq '[.recommendations[] | select(.dependency_status == "ready")] | length')
    needs_deps_count=$(echo "$recommendations_json" | jq '[.recommendations[] | select(.dependency_status == "needs-deps")] | length')
    total_count=$(echo "$recommendations_json" | jq '.recommendations | length')

    # All display output to stderr so command substitution only captures the choice
    {
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

    # Build display-order array: ready → needs_review → needs-deps
    # Each entry gets a sequential number for easy reference
    local display_json
    display_json=$(echo "$recommendations_json" | jq '
        [(.recommendations[] | select(.dependency_status == "ready")),
         (.recommendations[] | select(.dependency_status == "needs_review")),
         (.recommendations[] | select(.dependency_status == "needs-deps"))]
        | to_entries | map({num: (.key + 1), id: .value.audit_id, name: .value.name, status: .value.dependency_status})
    ')

    # Ready to run
    if [[ "$ready_count" -gt 0 ]]; then
        echo -e "  ${GREEN}●${NC} ${BOLD}READY TO RUN${NC} ($ready_count audits)"
        echo ""
        echo "$display_json" | jq -r '.[] | select(.status == "ready") | "    ☑ \(.num | tostring | if length < 2 then " " + . else . end). \(.id)  \(.name)"'
        echo ""
    fi

    # Needs review
    local needs_review_count
    needs_review_count=$(echo "$recommendations_json" | jq '[.recommendations[] | select(.dependency_status == "needs_review")] | length')
    if [[ "$needs_review_count" -gt 0 ]]; then
        echo -e "  ${CYAN}◐${NC} ${BOLD}NEEDS REVIEW${NC} ($needs_review_count audits)"
        echo ""
        echo "$display_json" | jq -r '.[] | select(.status == "needs_review") | "    ◻ \(.num | tostring | if length < 2 then " " + . else . end). \(.id)  \(.name)"'
        echo ""
    fi

    # Needs dependencies
    if [[ "$needs_deps_count" -gt 0 ]]; then
        echo -e "  ${YELLOW}○${NC} ${BOLD}DEPENDENCIES REQUIRED${NC} ($needs_deps_count audits)"
        echo ""
        echo "$display_json" | jq -r '.[] | select(.status == "needs-deps") | "    ☐ \(.num | tostring | if length < 2 then " " + . else . end). \(.id)  \(.name)"'
        echo ""
    fi

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  Options:"
    echo ""
    echo -e "    ${GREEN}[1]${NC} Accept recommendations (run ready audits)"
    echo -e "    ${GREEN}[2]${NC} View audit details           ${DIM}(# or ID)${NC}"
    echo -e "    ${GREEN}[3]${NC} Browse & add audits          ${DIM}(from full catalog)${NC}"
    echo -e "    ${GREEN}[4]${NC} Remove from selection        ${DIM}(# or ID, comma-sep)${NC}"
    echo -e "    ${GREEN}[5]${NC} Mark all as ready            ${DIM}(approve needs_review)${NC}"
    echo -e "    ${GREEN}[6]${NC} Skip audits for this phase"
    echo -e "    ${YELLOW}[7]${NC} Run ALL applicable audits    ${DIM}(no LLM selection)${NC}"
    echo ""
    } >&2

    read -e -p "  Select [1]: " choice
    choice=${choice:-1}

    echo "$choice"
}

# ============================================================================
# AUDIT EXECUTION
# ============================================================================

# Extract a JSON result object from Claude's audit output file
# Handles: pure JSON, markdown-wrapped, mixed output with tool-call preamble
# Usage: local json=$(_audit_extract_result_json "$file" "$audit_id" "$audit_name")
_audit_extract_result_json() {
    local output_file="$1"
    local audit_id="$2"
    local audit_name="$3"

    if [[ ! -f "$output_file" ]] || [[ ! -s "$output_file" ]]; then
        _audit_error_json "$audit_id" "$audit_name" "Empty output from audit agent"
        return 0
    fi

    # Check for common error messages before JSON parsing
    local first_line
    first_line=$(head -1 "$output_file" 2>/dev/null)
    if [[ "$first_line" =~ "Reached max turns" ]]; then
        _audit_error_json "$audit_id" "$audit_name" "Audit agent exceeded turn limit (try AUDIT_MAX_TURNS=40)"
        return 0
    fi
    if [[ "$first_line" =~ "Error:" || "$first_line" =~ "error:" ]]; then
        _audit_error_json "$audit_id" "$audit_name" "${first_line:0:100}"
        return 0
    fi

    # 1) Direct JSON parse
    if jq -e '.audit_id' "$output_file" &>/dev/null; then
        cat "$output_file"
        return 0
    fi

    # 2) Try atomic_json_fix (markdown fences, leading text before '{')
    local fixed
    fixed=$(atomic_json_fix "$output_file")
    if echo "$fixed" | jq -e '.audit_id' &>/dev/null; then
        echo "$fixed"
        return 0
    fi

    # 3) Find last JSON object in mixed output (tool-call preamble + JSON at end)
    local obj_start extracted
    obj_start=$(grep -n '^{' "$output_file" | tail -1 | cut -d: -f1)
    if [[ -n "$obj_start" ]]; then
        extracted=$(tail -n +"$obj_start" "$output_file")
        if echo "$extracted" | jq -e '.audit_id' &>/dev/null; then
            echo "$extracted"
            return 0
        fi
    fi

    # Provide diagnostic context for parse failures
    local err_file="${output_file}.err"
    local output_size=0
    [[ -f "$output_file" ]] && output_size=$(wc -c < "$output_file" 2>/dev/null || echo 0)
    {
        echo "[AUDIT PARSE ERROR] $audit_id"
        echo "  Output file: $output_file (${output_size} bytes)"
        echo "  First 3 lines:"
        head -3 "$output_file" 2>/dev/null | sed 's/^/    /'
        if [[ -f "$err_file" ]] && [[ -s "$err_file" ]]; then
            echo "  Stderr (first 3 lines):"
            head -3 "$err_file" | sed 's/^/    /'
        fi
    } >&2

    _audit_error_json "$audit_id" "$audit_name" "Could not parse audit agent output"
}

# Generate a fallback error JSON for a failed audit
_audit_error_json() {
    local audit_id="$1"
    local audit_name="$2"
    local message="${3:-Audit execution failed}"
    cat <<EOF
{
    "audit_id": "$audit_id",
    "name": "$audit_name",
    "status": "error",
    "severity": "low",
    "message": "$message",
    "findings": []
}
EOF
}

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
    local errors=0

    local max_parallel="${AUDIT_PARALLEL:-5}"
    echo -e "  ${DIM}Running $audit_count audit agents ($max_parallel concurrent)${NC}"
    echo ""

    # --- Launch phase: start all agents with concurrency throttle ---
    local -a result_files=()

    # FIFO semaphore for concurrency control
    local sem_fifo="$AUDIT_CACHE_DIR/.audit-sem-$$"
    mkfifo "$sem_fifo"
    exec 3<>"$sem_fifo"
    rm -f "$sem_fifo"
    for ((j=0; j<max_parallel; j++)); do echo >&3; done

    for ((i=0; i<audit_count; i++)); do
        audit=$(echo "$ready_audits" | jq -c ".[$i]")
        audit_id=$(echo "$audit" | jq -r '.audit_id')
        audit_name=$(echo "$audit" | jq -r '.name')

        local rf="$AUDIT_CACHE_DIR/result-phase${phase_num}-${i}.json"
        result_files+=("$rf")
        : > "$rf"  # ensure file exists

        read -u 3  # acquire semaphore slot
        (
            _audit_execute_single "$audit_id" "$audit_name" "$phase_num" > "$rf" 2>"${rf%.json}.log"
            echo >&3  # release slot
        ) &

        echo -e "  ${DIM}[$((i+1))/$audit_count]${NC} $audit_id"
    done

    # --- Wait phase: monitor completion ---
    echo ""
    echo -e "  ${DIM}Waiting for all agents to complete...${NC}"

    local completed=0
    while ((completed < audit_count)); do
        sleep 3
        completed=0
        for ((j=0; j<audit_count; j++)); do
            [[ -s "${result_files[$j]}" ]] && ((completed++))
        done
        echo -ne "\r  ${DIM}Progress: $completed/$audit_count agents completed${NC}   "
    done
    echo ""

    wait
    exec 3>&-  # close semaphore fd

    echo ""

    # --- Results phase: collect and display ---
    for ((i=0; i<audit_count; i++)); do
        audit=$(echo "$ready_audits" | jq -c ".[$i]")
        audit_id=$(echo "$audit" | jq -r '.audit_id')
        audit_name=$(echo "$audit" | jq -r '.name')

        local rf="${result_files[$i]}"
        if [[ -s "$rf" ]]; then
            result=$(cat "$rf")
            # Validate it's JSON
            if ! echo "$result" | jq -e '.status' &>/dev/null; then
                result=$(_audit_error_json "$audit_id" "$audit_name" "Invalid result JSON")
            fi
        else
            result=$(_audit_error_json "$audit_id" "$audit_name" "Agent produced no output")
        fi

        status=$(echo "$result" | jq -r '.status')
        local msg
        msg=$(echo "$result" | jq -r '.message // ""')

        case "$status" in
            pass)
                echo -e "  ${GREEN}✓ PASS${NC}  $audit_id"
                [[ -n "$msg" ]] && echo -e "         ${DIM}$msg${NC}"
                ((passed++))
                ;;
            fail)
                echo -e "  ${RED}✗ FAIL${NC}  $audit_id"
                [[ -n "$msg" ]] && echo -e "         ${DIM}$msg${NC}"
                ((failed++))
                ;;
            warn)
                echo -e "  ${YELLOW}⚠ WARN${NC}  $audit_id"
                [[ -n "$msg" ]] && echo -e "         ${DIM}$msg${NC}"
                ((warnings++))
                ;;
            *)
                echo -e "  ${CYAN}? ERR ${NC}  $audit_id"
                [[ -n "$msg" ]] && echo -e "         ${DIM}$msg${NC}"
                ((errors++))
                ;;
        esac

        results+=("$result")
    done

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Results:${NC} ${GREEN}$passed passed${NC}, ${RED}$failed failed${NC}, ${YELLOW}$warnings warnings${NC}, ${CYAN}$errors errors${NC}"
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
        "warnings": $warnings,
        "errors": $errors
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

# Execute a single audit via Claude agent invocation
# Each audit gets its own Claude session with tool access to investigate the project
_audit_execute_single() {
    local audit_id="$1"
    local audit_name="$2"
    local phase_num="${3:-0}"

    # Look for audit YAML file in repository
    # audit_id format: category.subcategory.audit-name
    # file path:       audits/{NN-category}/{subcategory}/{audit-name}.yaml
    local audit_file=""
    if [[ -n "$_AUDIT_REPO_PATH" ]]; then
        local audit_slug="${audit_id##*.}"  # last segment = filename
        audit_file=$(find "$_AUDIT_REPO_PATH/audits" -name "${audit_slug}.yaml" -type f 2>/dev/null | head -1)
    fi

    if [[ -z "$audit_file" || ! -f "$audit_file" ]]; then
        _audit_error_json "$audit_id" "$audit_name" "Audit YAML not found locally"
        return 0
    fi

    # Build prompt with audit definition + project context
    local prompt_file output_file
    prompt_file=$(atomic_mktemp)
    output_file="$AUDIT_CACHE_DIR/audit-result-$(echo "$audit_id" | tr '.' '-').json"

    cat > "$prompt_file" <<AUDIT_PROMPT_HEADER
# Execute Audit: $audit_id
## $audit_name

You are an expert software auditor. Execute this audit against the project.
Follow the procedure steps, check each signal, and investigate the project using your tools.

## Audit Definition

\`\`\`yaml
$(cat "$audit_file")
\`\`\`

AUDIT_PROMPT_HEADER

    # Append project context
    local config_file="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
    if [[ -f "$config_file" ]]; then
        {
            echo "## Project Configuration"
            echo '```json'
            cat "$config_file"
            echo '```'
            echo ""
        } >> "$prompt_file"
    fi

    local approach_file="$ATOMIC_OUTPUT_DIR/1-discovery/selected-approach.json"
    if [[ -f "$approach_file" ]]; then
        {
            echo "## Architectural Approach"
            echo '```json'
            cat "$approach_file"
            echo '```'
            echo ""
        } >> "$prompt_file"
    fi

    cat >> "$prompt_file" << 'AUDIT_PROMPT_FOOTER'
## Instructions

1. Read the audit YAML above — understand its signals and procedure steps
2. Use your tools to explore the project repository and its artifacts
3. Follow the procedure steps to investigate the project state
4. For each signal, assess whether the project exhibits or addresses it
5. Produce a final JSON result

CRITICAL: You MUST output the JSON result below as your FINAL message. If you are running low on turns, stop investigating and produce the result with what you have. An incomplete result is far better than no result.

## Output Format (REQUIRED)

Output ONLY this JSON object (no markdown fences, no extra text):
{
    "audit_id": "the.audit.id",
    "name": "Audit Name",
    "status": "pass|warn|fail",
    "severity": "critical|high|medium|low",
    "message": "One-line summary of audit result",
    "findings": [
        {
            "signal_id": "SIGNAL-ID-001",
            "finding": "What was found or is missing",
            "severity": "critical|high|medium|low",
            "recommendation": "What to do about it"
        }
    ]
}
AUDIT_PROMPT_FOOTER

    # Invoke Claude agent with tool access and enough turns to investigate
    # Architecture audits need many turns to read files + produce JSON output
    # Disable retries — each attempt is already long; retries just triple the wait
    source "$ATOMIC_ROOT/lib/provider.sh"
    local saved_max_turns="${CLAUDE_MAX_TURNS:-1}"
    local saved_max_retries="${ATOMIC_MAX_RETRIES:-2}"
    # Default 30 turns; complex audits (domain analysis, cohesion) need more exploration
    export CLAUDE_MAX_TURNS="${AUDIT_MAX_TURNS:-30}"
    export ATOMIC_MAX_RETRIES=0
    local invoke_rc=0
    provider_invoke "$prompt_file" "$output_file" "bulk" --format=json --timeout=1200 >&2 || invoke_rc=$?
    export CLAUDE_MAX_TURNS="$saved_max_turns"
    export ATOMIC_MAX_RETRIES="$saved_max_retries"
    rm -f "$prompt_file"

    if [[ $invoke_rc -ne 0 ]]; then
        _audit_error_json "$audit_id" "$audit_name" "Audit agent failed (rc=$invoke_rc)"
        return 0
    fi

    # Extract structured JSON from agent output
    _audit_extract_result_json "$output_file" "$audit_id" "$audit_name"
}

# ============================================================================
# STREAMING AUDIT EXECUTION
# ============================================================================

# Execute audits with streaming results — present findings as each audit completes
# instead of waiting for all audits to finish before showing anything.
#
# Uses dual FIFO approach:
#   FD 3 = semaphore FIFO (concurrency control, same as batch)
#   FD 4 = completion FIFO (audits signal their index when done)
#
# Returns: 0 (accept/apply), 2 (rerun requested)
audit_execute_streaming() {
    local recommendations_json="$1"
    local output_dir="${2:-$AUDIT_OUTPUT_DIR}"

    audit_init
    mkdir -p "$output_dir" "$AUDIT_CACHE_DIR/discuss"

    local phase_num phase_name ready_audits audit_count
    phase_num=$(echo "$recommendations_json" | jq -r '.phase')
    phase_name=$(echo "$recommendations_json" | jq -r '.phase_name // ""')
    ready_audits=$(echo "$recommendations_json" | jq -c '[.recommendations[] | select(.dependency_status == "ready")]')
    audit_count=$(echo "$ready_audits" | jq 'length')

    if [[ $audit_count -eq 0 ]]; then
        echo -e "  ${YELLOW}No ready audits to execute.${NC}"
        return 0
    fi

    local report_file="$output_dir/phase-$phase_num-report.json"

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}EXECUTING AUDITS (streaming)${NC}                                 ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local max_parallel="${AUDIT_PARALLEL:-5}"
    echo -e "  ${DIM}Running $audit_count audit agents ($max_parallel concurrent, streaming results)${NC}"
    echo ""

    # --- FIFO setup ---

    # Semaphore (FD 3) — concurrency control
    local sem_fifo="$AUDIT_CACHE_DIR/.audit-sem-$$"
    mkfifo "$sem_fifo"
    exec 3<>"$sem_fifo"
    rm -f "$sem_fifo"
    for ((j=0; j<max_parallel; j++)); do echo >&3; done

    # Completion FIFO (FD 4) — audits signal their index when done
    local done_fifo="$AUDIT_CACHE_DIR/.audit-done-$$"
    mkfifo "$done_fifo"
    exec 4<>"$done_fifo"
    rm -f "$done_fifo"

    # --- Initialize state BEFORE launch (enables interleaved consumption) ---
    local -a result_files=()
    local audit audit_id audit_name
    local completed=0
    local passed=0 failed=0 warnings=0 errors=0
    local -a results=()

    # Streaming remediation state
    local user_mode="remediate"  # "remediate" | "done" | "accept-rest"
    local resolution_plan=""
    local resolved_count=0
    local skipped_count=0
    local finding_global_index=0

    # Determine artifact path for discuss context
    local artifact_path
    artifact_path=$(_audit_phase_artifact "$phase_num")

    # Helper: process one completion (called from launch loop and drain loop)
    # Reads done_index from caller scope, updates state via caller scope
    _process_one_completion() {
        local done_index="$1"

        # Validate index
        if ! [[ "$done_index" =~ ^[0-9]+$ ]] || ((done_index < 0 || done_index >= audit_count)); then
            return 1  # garbage on FIFO — skip
        fi

        ((completed++))

        # Read result
        local rf="${result_files[$done_index]}"
        audit=$(echo "$ready_audits" | jq -c ".[$done_index]")
        audit_id=$(echo "$audit" | jq -r '.audit_id')
        audit_name=$(echo "$audit" | jq -r '.name')

        local result status msg
        if [[ -s "$rf" ]]; then
            result=$(cat "$rf")
            if ! echo "$result" | jq -e '.status' &>/dev/null; then
                result=$(_audit_error_json "$audit_id" "$audit_name" "Invalid result JSON")
            fi
        else
            result=$(_audit_error_json "$audit_id" "$audit_name" "Agent produced no output")
        fi

        status=$(echo "$result" | jq -r '.status')
        msg=$(echo "$result" | jq -r '.message // ""')
        results+=("$result")

        # Display status line
        case "$status" in
            pass)
                echo -e "  ${GREEN}✓ PASS${NC}  ${DIM}[$completed/$audit_count]${NC}  $audit_id"
                [[ -n "$msg" ]] && echo -e "         ${DIM}$msg${NC}"
                ((passed++))
                ;;
            fail)
                echo -e "  ${RED}✗ FAIL${NC}  ${DIM}[$completed/$audit_count]${NC}  $audit_id"
                [[ -n "$msg" ]] && echo -e "         ${DIM}$msg${NC}"
                ((failed++))
                ;;
            warn)
                echo -e "  ${YELLOW}⚠ WARN${NC}  ${DIM}[$completed/$audit_count]${NC}  $audit_id"
                [[ -n "$msg" ]] && echo -e "         ${DIM}$msg${NC}"
                ((warnings++))
                ;;
            *)
                echo -e "  ${CYAN}? ERR ${NC}  ${DIM}[$completed/$audit_count]${NC}  $audit_id"
                [[ -n "$msg" ]] && echo -e "         ${DIM}$msg${NC}"
                ((errors++))
                ;;
        esac

        # Inline remediation for FAIL/WARN
        if [[ "$status" == "fail" || "$status" == "warn" ]]; then
            case "$user_mode" in
                remediate)
                    _audit_stream_remediate_single "$result" "$audit_id" "$status" \
                        finding_global_index resolution_plan resolved_count skipped_count user_mode \
                        "$artifact_path"
                    ;;
                accept-rest)
                    _audit_stream_auto_accept_single "$result" "$audit_id" "$status" \
                        finding_global_index resolution_plan resolved_count
                    ;;
                done)
                    # User said done — just show status line (already shown above)
                    ;;
            esac
        fi

        echo ""
        return 0
    }

    # --- Launch phase with interleaved consumption ---
    for ((i=0; i<audit_count; i++)); do
        audit=$(echo "$ready_audits" | jq -c ".[$i]")
        audit_id=$(echo "$audit" | jq -r '.audit_id')
        audit_name=$(echo "$audit" | jq -r '.name')

        local rf="$AUDIT_CACHE_DIR/result-phase${phase_num}-${i}.json"
        result_files+=("$rf")
        : > "$rf"  # ensure file exists

        read -u 3  # acquire semaphore slot
        (
            local _i="$i"
            trap 'printf "%d\n" "$_i" >&4; echo >&3' EXIT
            _audit_execute_single "$audit_id" "$audit_name" "$phase_num" \
                > "$rf" 2>"${rf%.json}.log"
        ) &

        echo -e "  ${DIM}[launched $((i+1))/$audit_count]${NC} $audit_id"

        # Non-blocking: process any completions that arrived while launching
        local _done_idx
        while read -t 0 -u 4; do
            if read -u 4 _done_idx; then
                _process_one_completion "$_done_idx"
            fi
        done
    done

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # --- Drain loop: process remaining completions after all launched ---
    while ((completed < audit_count)); do
        # Block until an audit finishes (10-minute timeout)
        local done_index=""
        if ! read -t 600 -u 4 done_index; then
            echo -e "  ${RED}Timeout waiting for audit results. $completed/$audit_count completed.${NC}"
            break
        fi

        _process_one_completion "$done_index"
    done

    # Wait for any remaining background jobs
    wait
    exec 3>&- 2>/dev/null
    exec 4>&- 2>/dev/null

    # --- Generate report ---
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Results:${NC} ${GREEN}$passed passed${NC}, ${RED}$failed failed${NC}, ${YELLOW}$warnings warnings${NC}, ${CYAN}$errors errors${NC}"
    if [[ $resolved_count -gt 0 || $skipped_count -gt 0 ]]; then
        echo -e "  ${BOLD}Inline:${NC}  ${GREEN}$resolved_count resolved${NC}, ${YELLOW}$skipped_count skipped${NC}"
    fi
    echo ""

    local report
    report=$(cat <<EOF
{
    "phase": $phase_num,
    "timestamp": "$(date -Iseconds)",
    "summary": {
        "total": $audit_count,
        "passed": $passed,
        "failed": $failed,
        "warnings": $warnings,
        "errors": $errors
    },
    "results": $(printf '%s\n' "${results[@]}" | jq -s '.'),
    "recommendations": $(echo "$recommendations_json" | jq '.recommendations')
}
EOF
)

    echo "$report" > "$report_file"
    echo -e "  ${GREEN}✓${NC} Report saved: $report_file"

    # Register audit artifacts
    atomic_context_artifact "phase${phase_num}_audit_report" "$report_file" "Phase $phase_num audit results"
    local recommendations_file="$output_dir/phase-$phase_num-recommendations.json"
    [[ -f "$recommendations_file" ]] && atomic_context_artifact "phase${phase_num}_audit_recommendations" "$recommendations_file" "Phase $phase_num audit recommendations"
    atomic_context_decision "Phase $phase_num audit: $passed passed, $failed failed, $warnings warnings" "audit"

    # --- Post-summary menu ---
    _audit_stream_post_summary "$report_file" "$phase_num" "$phase_name" \
        "$resolution_plan" "$resolved_count" "$skipped_count"
    return $?
}

# Present a single audit's findings for inline remediation during streaming.
# Modifies caller variables via namerefs: finding_global_index, resolution_plan,
# resolved_count, skipped_count, user_mode.
_audit_stream_remediate_single() {
    local result_json="$1"
    local audit_id="$2"
    local status="$3"
    local -n _fgi="$4"          # finding_global_index
    local -n _rplan="$5"        # resolution_plan
    local -n _rcount="$6"       # resolved_count
    local -n _scount="$7"       # skipped_count
    local -n _umode="$8"        # user_mode (can be set to "done" or "accept-rest")
    local artifact_path="${9:-}"

    local status_upper
    status_upper=$(echo "$status" | tr '[:lower:]' '[:upper:]')

    # Flatten findings from this single audit result
    local flat_findings
    flat_findings=$(echo "$result_json" | jq -c '
        . as $parent |
        if (.findings | length) == 0 then
            [{
                audit_id: $parent.audit_id,
                status: $parent.status,
                finding: ($parent.message // "No details"),
                f_severity: ($parent.severity // "medium"),
                f_recommendation: "Address the issue as described",
                f_signal: ""
            }]
        else
            [.findings[] | {
                audit_id: $parent.audit_id,
                status: $parent.status,
                finding: (.finding // ""),
                f_severity: (.severity // "medium"),
                f_recommendation: (.recommendation // ""),
                f_signal: (.signal_id // "")
            }]
        end
    ')

    local count
    count=$(echo "$flat_findings" | jq 'length')

    if [[ $count -eq 0 ]]; then
        return 0
    fi

    echo ""
    echo -e "  ${DIM}── Findings for ${BOLD}$audit_id${NC}${DIM} ($count) ──${NC}"

    local auto_accept_this=false

    local f
    for ((f=0; f<count; f++)); do
        local entry
        entry=$(echo "$flat_findings" | jq -c ".[$f]")

        local finding f_severity f_recommendation
        finding=$(echo "$entry" | jq -r '.finding')
        f_severity=$(echo "$entry" | jq -r '.f_severity')
        f_recommendation=$(echo "$entry" | jq -r '.f_recommendation')

        ((_fgi++))

        # Auto-accept remaining for this audit
        if [[ "$auto_accept_this" == true ]]; then
            _rplan+="$_rcount. [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $f_recommendation\n\n"
            ((_rcount++))
            echo -e "    ${GREEN}✓${NC} ${DIM}#$_fgi [${f_severity^^}] auto-accepted${NC}"
            continue
        fi

        local sev_color="${YELLOW}"
        [[ "$f_severity" == "high" || "$f_severity" == "critical" ]] && sev_color="${RED}"
        [[ "$f_severity" == "low" ]] && sev_color="${DIM}"

        echo ""
        echo -e "    ${sev_color}[${f_severity^^}]${NC} ${BOLD}#$_fgi${NC}"
        echo -e "    $finding"
        if [[ -n "$f_recommendation" ]]; then
            echo -e "    ${DIM}Fix: $f_recommendation${NC}"
        fi
        echo ""
        echo -e "    ${DIM}Options: [enter]=accept  [s]kip  [a]ll (this audit)  [accept-rest]  [?]discuss  [done]${NC}"

        local user_response
        read -e -p "  Resolution: " user_response

        case "$user_response" in
            done)
                echo ""
                echo -e "  ${DIM}Stopping inline remediation. Remaining audits will show status only.${NC}"
                _umode="done"
                return 0
                ;;
            accept-rest)
                _rplan+="$_rcount. [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $f_recommendation\n\n"
                ((_rcount++))
                echo -e "    ${GREEN}-> Accepted (+ auto-accepting all remaining)${NC}"
                _umode="accept-rest"
                # Accept remaining findings in THIS audit too
                auto_accept_this=true
                ;;
            skip|s)
                ((_scount++))
                echo -e "    ${DIM}-> Skipped${NC}"
                ;;
            all)
                _rplan+="$_rcount. [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $f_recommendation\n\n"
                ((_rcount++))
                auto_accept_this=true
                echo -e "    ${GREEN}-> Accepted (+ all remaining for this audit)${NC}"
                ;;
            ""|accept|a)
                _rplan+="$_rcount. [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $f_recommendation\n\n"
                ((_rcount++))
                echo -e "    ${GREEN}-> Accepted${NC}"
                ;;
            discuss|"?")
                local discuss_result=""
                local discuss_rc=1
                discuss_result=$(_audit_discuss_finding "$entry" "$audit_id" "$artifact_path")
                discuss_rc=$?
                if [[ $discuss_rc -eq 0 && -n "$discuss_result" ]]; then
                    _rplan+="$_rcount. [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $discuss_result\n\n"
                    ((_rcount++))
                    echo -e "    ${GREEN}-> $discuss_result${NC}"
                else
                    # User exited discussion without resolving — re-prompt
                    echo ""
                    echo -e "    ${DIM}Back to finding #$_fgi${NC}"
                    echo -e "    $finding"
                    if [[ -n "$f_recommendation" ]]; then
                        echo -e "    ${DIM}Fix: $f_recommendation${NC}"
                    fi
                    echo ""
                    echo -e "    ${DIM}Options: [enter]=accept  [s]kip  [done]  or type custom resolution${NC}"
                    # Re-prompt (simple fallback — accept or type)
                    read -e -p "  Resolution: " user_response
                    case "$user_response" in
                        skip|s)
                            ((_scount++))
                            echo -e "    ${DIM}-> Skipped${NC}"
                            ;;
                        done)
                            _umode="done"
                            return 0
                            ;;
                        ""|accept|a)
                            _rplan+="$_rcount. [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $f_recommendation\n\n"
                            ((_rcount++))
                            echo -e "    ${GREEN}-> Accepted${NC}"
                            ;;
                        *)
                            _rplan+="$_rcount. [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $user_response\n\n"
                            ((_rcount++))
                            echo -e "    ${GREEN}-> $user_response${NC}"
                            ;;
                    esac
                fi
                ;;
            *)
                # Custom resolution text
                _rplan+="$_rcount. [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $user_response\n\n"
                ((_rcount++))
                echo -e "    ${GREEN}-> $user_response${NC}"
                ;;
        esac
    done
}

# Silently accept all findings from an audit (for accept-rest mode)
_audit_stream_auto_accept_single() {
    local result_json="$1"
    local audit_id="$2"
    local status="$3"
    local -n _fgi="$4"       # finding_global_index
    local -n _rplan="$5"     # resolution_plan
    local -n _rcount="$6"    # resolved_count

    local status_upper
    status_upper=$(echo "$status" | tr '[:lower:]' '[:upper:]')

    # Flatten findings
    local flat_findings count
    flat_findings=$(echo "$result_json" | jq -c '
        . as $parent |
        if (.findings | length) == 0 then
            [{
                finding: ($parent.message // "No details"),
                f_recommendation: "Address the issue as described"
            }]
        else
            [.findings[] | {
                finding: (.finding // ""),
                f_recommendation: (.recommendation // "")
            }]
        end
    ')
    count=$(echo "$flat_findings" | jq 'length')

    local f
    for ((f=0; f<count; f++)); do
        local entry finding f_recommendation
        entry=$(echo "$flat_findings" | jq -c ".[$f]")
        finding=$(echo "$entry" | jq -r '.finding')
        f_recommendation=$(echo "$entry" | jq -r '.f_recommendation')

        ((_fgi++))
        _rplan+="$_rcount. [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $f_recommendation\n\n"
        ((_rcount++))
    done

    echo -e "         ${DIM}(auto-accepted $count findings)${NC}"
}

# Multi-turn discussion about a specific finding with an AI agent.
# The user can ask questions about the finding, get context-aware responses,
# and optionally resolve the finding from within the discussion.
#
# Returns via stdout: resolution text (if user typed "resolve ...")
# Exit code: 0 = user provided resolution, 1 = user exited without resolving
_audit_discuss_finding() {
    local finding_json="$1"
    local audit_id="$2"
    local artifact_path="${3:-}"

    local finding f_severity f_recommendation
    finding=$(echo "$finding_json" | jq -r '.finding // ""')
    f_severity=$(echo "$finding_json" | jq -r '.f_severity // "medium"')
    f_recommendation=$(echo "$finding_json" | jq -r '.f_recommendation // ""')

    local discuss_dir="$AUDIT_CACHE_DIR/discuss"
    mkdir -p "$discuss_dir"
    local history_file="$discuss_dir/discuss-$(echo "$audit_id" | tr '.' '-')-$$.md"
    local response_file="$discuss_dir/discuss-response-$$.md"

    # Build artifact context excerpt
    local artifact_excerpt=""
    if [[ -n "$artifact_path" && -f "$artifact_path" ]]; then
        artifact_excerpt=$(head -200 "$artifact_path" 2>/dev/null || true)
    fi

    # Initialize conversation history
    : > "$history_file"

    echo "" >&2
    echo -e "  ${CYAN}┌─ DISCUSS: $audit_id${NC}" >&2
    echo -e "  ${DIM}│  Ask questions about this finding. Commands:${NC}" >&2
    echo -e "  ${DIM}│    resolve <text>  — Set resolution and return${NC}" >&2
    echo -e "  ${DIM}│    back / exit     — Return without resolving${NC}" >&2
    echo -e "  ${CYAN}│${NC}" >&2

    while true; do
        local user_input=""
        read -e -p "  │  You: " user_input <&0 2>&2

        # Empty input or exit commands
        if [[ -z "$user_input" || "$user_input" == "back" || "$user_input" == "exit" ]]; then
            echo -e "  ${CYAN}└─${NC}" >&2
            rm -f "$history_file" "$response_file"
            return 1
        fi

        # Resolve command
        if [[ "$user_input" == resolve\ * ]]; then
            local resolution_text="${user_input#resolve }"
            echo -e "  ${CYAN}└─${NC}" >&2
            rm -f "$history_file" "$response_file"
            echo "$resolution_text"
            return 0
        fi

        # Append user question to history
        echo -e "\nUser: $user_input" >> "$history_file"

        # Build prompt for this turn
        local prompt_file
        prompt_file=$(atomic_mktemp)
        cat > "$prompt_file" <<DISCUSS_PROMPT
# Finding Discussion

You are helping a user understand and resolve an audit finding.
Be concise (2-4 paragraphs max). Reference specific sections of the artifact when relevant.

## Finding
Audit: $audit_id
Severity: $f_severity
Finding: $finding
Recommendation: $f_recommendation

DISCUSS_PROMPT

        if [[ -n "$artifact_excerpt" ]]; then
            cat >> "$prompt_file" <<DISCUSS_ARTIFACT
## Artifact Context
\`\`\`
$artifact_excerpt
\`\`\`

DISCUSS_ARTIFACT
        else
            echo -e "## Artifact Context\nNo single artifact for this phase.\n" >> "$prompt_file"
        fi

        echo "## Conversation" >> "$prompt_file"
        cat "$history_file" >> "$prompt_file"

        # Invoke agent (sonnet, fast/cheap)
        source "$ATOMIC_ROOT/lib/provider.sh"
        local saved_turns="${CLAUDE_MAX_TURNS:-10}"
        local saved_retries="${ATOMIC_MAX_RETRIES:-2}"
        export CLAUDE_MAX_TURNS=1
        export ATOMIC_MAX_RETRIES=0
        provider_invoke "$prompt_file" "$response_file" "bulk" --timeout=120 >&2 2>/dev/null || true
        export CLAUDE_MAX_TURNS="$saved_turns"
        export ATOMIC_MAX_RETRIES="$saved_retries"
        rm -f "$prompt_file"

        # Display response
        local agent_response=""
        if [[ -f "$response_file" && -s "$response_file" ]]; then
            agent_response=$(cat "$response_file")
            # Append to history
            echo -e "\nAssistant: $agent_response" >> "$history_file"
            # Display wrapped
            echo -e "  ${CYAN}│${NC}" >&2
            echo "$agent_response" | fold -s -w 72 | while IFS= read -r line; do
                echo -e "  ${CYAN}│${NC}  ${DIM}$line${NC}" >&2
            done
            echo -e "  ${CYAN}│${NC}" >&2
        else
            echo -e "  ${CYAN}│${NC}  ${RED}(Agent did not respond)${NC}" >&2
            echo -e "  ${CYAN}│${NC}" >&2
        fi
    done
}

# Post-streaming summary menu.
# Aware that resolutions were already collected during streaming.
# Returns: 0 (accept/apply done), 2 (rerun requested)
_audit_stream_post_summary() {
    local report_file="$1"
    local phase_num="$2"
    local phase_name="$3"
    local resolution_plan="$4"
    local resolved_count="$5"
    local skipped_count="$6"

    local fail_count warn_count total_findings
    fail_count=$(jq '[.results[] | select(.status == "fail")] | length' "$report_file" 2>/dev/null || echo 0)
    warn_count=$(jq '[.results[] | select(.status == "warn")] | length' "$report_file" 2>/dev/null || echo 0)
    total_findings=$((fail_count + warn_count))

    if [[ $total_findings -eq 0 ]]; then
        echo ""
        echo -e "  ${GREEN}All audits passed. No remediation needed.${NC}"
        echo ""
        return 0
    fi

    while true; do
        echo ""
        echo -e "${CYAN}+----------------------------------------------------------+${NC}"
        local summary_text
        summary_text=$(printf "%-56.56s" "AUDIT SUMMARY — $total_findings audits with findings")
        echo -e "${CYAN}|${NC} ${BOLD}${summary_text}${NC} ${CYAN}|${NC}"
        echo -e "${CYAN}+----------------------------------------------------------+${NC}"
        echo ""

        if [[ $resolved_count -gt 0 ]]; then
            echo -e "  ${GREEN}$resolved_count resolutions collected${NC} during streaming"
            [[ $skipped_count -gt 0 ]] && echo -e "  ${YELLOW}$skipped_count findings skipped${NC}"
            echo ""
            echo -e "    ${GREEN}[apply]${NC}      Apply collected resolutions ${DIM}(default)${NC}"
        else
            echo -e "  ${DIM}No resolutions were collected during streaming.${NC}"
            echo ""
            echo -e "    ${GREEN}[remediate]${NC}  Walk through findings one by one ${DIM}(default)${NC}"
        fi
        echo -e "    ${CYAN}[view]${NC}       View detailed findings"
        echo -e "    ${BOLD}[accept]${NC}     Accept results and continue"
        echo -e "    ${GREEN}[remediate]${NC}  Walk through all findings (batch mode)"
        echo -e "    ${YELLOW}[rerun]${NC}      Re-run all audits"
        echo ""

        local default_choice="apply"
        [[ $resolved_count -eq 0 ]] && default_choice="remediate"

        # Drain any buffered stdin (from fast typing during streaming remediation)
        while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done
        # Also drain from tty if available
        while read -t 0.01 -n 1 _discard </dev/tty 2>/dev/null; do :; done

        # Force prompt to terminal and ensure it's visible
        printf "  Choice [%s]: " "$default_choice" >/dev/tty
        read -e post_choice </dev/tty 2>/dev/null || read -e -p "  Choice [$default_choice]: " post_choice
        post_choice=${post_choice:-$default_choice}

        case "$post_choice" in
            apply|a)
                if [[ $resolved_count -eq 0 ]]; then
                    echo -e "  ${YELLOW}No resolutions to apply. Use 'remediate' to walk through findings.${NC}"
                    continue
                fi

                # Ask for additional instructions
                echo ""
                echo -e "  ${DIM}Any additional instructions for the remediation agent? (Enter to skip):${NC}"
                read -e -p "  > " additional_context

                if [[ -n "$additional_context" ]]; then
                    resolution_plan+="\nADDITIONAL INSTRUCTIONS FROM USER:\n$additional_context\n"
                fi

                # Determine target artifact
                local artifact_path
                artifact_path=$(_audit_phase_artifact "$phase_num")

                if [[ -z "$artifact_path" ]]; then
                    # No single artifact — save resolution plan as notes
                    local notes_file="$AUDIT_OUTPUT_DIR/phase-$phase_num-remediation-notes.md"
                    {
                        echo "# Phase $phase_num Audit Remediation Notes"
                        echo ""
                        echo "Generated: $(date -Iseconds)"
                        echo ""
                        echo "## Resolution Plan ($resolved_count items)"
                        echo ""
                        echo -e "$resolution_plan"
                    } > "$notes_file"
                    echo -e "  ${YELLOW}Phase $phase_num has no single artifact to revise.${NC}"
                    echo -e "  ${GREEN}✓${NC} Resolution plan saved: $notes_file"
                    echo -e "  ${DIM}Apply these notes during the next implementation cycle.${NC}"
                    echo ""
                    atomic_context_artifact "phase${phase_num}_remediation_notes" "$notes_file" "Audit remediation notes for phase $phase_num"
                    atomic_context_decision "Phase $phase_num audit: $resolved_count remediation items noted" "audit-remediation"
                    return 0
                fi

                if [[ -d "$artifact_path" ]]; then
                    local notes_file="$AUDIT_OUTPUT_DIR/phase-$phase_num-remediation-notes.md"
                    {
                        echo "# Phase $phase_num Audit Remediation Notes"
                        echo ""
                        echo "Generated: $(date -Iseconds)"
                        echo "Target directory: $artifact_path"
                        echo ""
                        echo "## Resolution Plan ($resolved_count items)"
                        echo ""
                        echo -e "$resolution_plan"
                    } > "$notes_file"
                    echo -e "  ${YELLOW}Phase $phase_num artifact is a directory ($artifact_path).${NC}"
                    echo -e "  ${GREEN}✓${NC} Resolution plan saved: $notes_file"
                    echo -e "  ${DIM}Apply these notes to the relevant spec files.${NC}"
                    echo ""
                    atomic_context_artifact "phase${phase_num}_remediation_notes" "$notes_file" "Audit remediation notes for phase $phase_num"
                    atomic_context_decision "Phase $phase_num audit: $resolved_count remediation items noted" "audit-remediation"
                    return 0
                fi

                if [[ ! -f "$artifact_path" ]]; then
                    echo -e "  ${YELLOW}Artifact not found: $artifact_path${NC}"
                    local notes_file="$AUDIT_OUTPUT_DIR/phase-$phase_num-remediation-notes.md"
                    {
                        echo "# Phase $phase_num Audit Remediation Notes"
                        echo ""
                        echo "Generated: $(date -Iseconds)"
                        echo "Expected artifact: $artifact_path"
                        echo ""
                        echo "## Resolution Plan ($resolved_count items)"
                        echo ""
                        echo -e "$resolution_plan"
                    } > "$notes_file"
                    echo -e "  ${GREEN}✓${NC} Resolution plan saved: $notes_file"
                    echo ""
                    atomic_context_artifact "phase${phase_num}_remediation_notes" "$notes_file" "Audit remediation notes for phase $phase_num"
                    return 0
                fi

                # Apply remediation via LLM
                _audit_apply_remediation "$artifact_path" "$resolution_plan" "$resolved_count" "$phase_num" "$phase_name"
                return $?
                ;;
            view|v)
                echo ""
                echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                jq -r '.results[] | select(.status == "fail" or .status == "warn") |
                    "\n  [\(.status | ascii_upcase)] \(.audit_id)\n  \(.message)\n" +
                    (if (.findings | length) > 0 then
                        (.findings[] | "    - [\(.severity | ascii_upcase)] \(.finding)\n      Fix: \(.recommendation)")
                    else "" end)' "$report_file" 2>/dev/null
                echo ""
                echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                # Loop back to menu
                ;;
            accept)
                echo ""
                echo -e "  ${YELLOW}Accepting audit results as-is.${NC}"
                echo ""
                return 0
                ;;
            remediate|r)
                audit_remediate_findings "$report_file" "$phase_num" "$phase_name"
                return $?
                ;;
            rerun)
                return 2
                ;;
            *)
                echo -e "  ${RED}Enter apply, view, accept, remediate, or rerun.${NC}"
                ;;
        esac
    done
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
# POST-EXECUTION REMEDIATION
# ============================================================================

# Map phase number to the primary artifact file for remediation
# Usage: local artifact=$(_audit_phase_artifact "$phase_num")
# Returns: path to artifact file, or "" if no single artifact exists
_audit_phase_artifact() {
    local phase_num="$1"
    case "$phase_num" in
        1) echo "$ATOMIC_OUTPUT_DIR/1-discovery/direction-confirmed.json" ;;
        2) echo "$ATOMIC_ROOT/docs/prd/PRD.md" ;;
        3) echo "$ATOMIC_OUTPUT_DIR/3-tasking/tasks.json" ;;
        4) echo "$ATOMIC_ROOT/.claude/specs" ;;  # directory — special handling
        5|6|7|8|9)
            # Code phases — no single artifact; collect as notes
            echo ""
            ;;
    esac
}

# Post-execution decision menu after audit results are shown
# Shows fail/warn counts and offers remediate/view/accept/rerun
# Returns: 0 (accept/remediate done), 2 (rerun requested)
audit_post_execution() {
    local report_file="$1"
    local phase_num="$2"
    local phase_name="$3"

    local fail_count warn_count pass_count total_findings
    fail_count=$(jq '[.results[] | select(.status == "fail")] | length' "$report_file" 2>/dev/null || echo 0)
    warn_count=$(jq '[.results[] | select(.status == "warn")] | length' "$report_file" 2>/dev/null || echo 0)
    pass_count=$(jq '[.results[] | select(.status == "pass")] | length' "$report_file" 2>/dev/null || echo 0)
    total_findings=$((fail_count + warn_count))

    if [[ $total_findings -eq 0 ]]; then
        echo ""
        echo -e "  ${GREEN}All audits passed. No remediation needed.${NC}"
        echo ""
        return 0
    fi

    while true; do
        echo ""
        echo -e "${CYAN}+----------------------------------------------------------+${NC}"
        local remediation_text
        remediation_text=$(printf "%-56.56s" "AUDIT REMEDIATION — $total_findings findings ($fail_count FAIL, $warn_count WARN)")
        echo -e "${CYAN}|${NC} ${BOLD}${remediation_text}${NC} ${CYAN}|${NC}"
        echo -e "${CYAN}+----------------------------------------------------------+${NC}"
        echo ""

        local default_choice="remediate"
        if [[ $fail_count -gt 0 ]]; then
            echo -e "    ${GREEN}[remediate]${NC}  Walk through findings one by one ${DIM}(default)${NC}"
        else
            echo -e "    ${GREEN}[remediate]${NC}  Walk through findings one by one"
        fi
        echo -e "    ${CYAN}[view]${NC}       View detailed findings"
        echo -e "    ${BOLD}[accept]${NC}     Accept results and continue"
        echo -e "    ${YELLOW}[rerun]${NC}      Re-run all audits"
        echo ""

        atomic_drain_stdin
        read -e -p "  Choice [remediate]: " post_choice
        post_choice=${post_choice:-remediate}

        case "$post_choice" in
            remediate|r)
                audit_remediate_findings "$report_file" "$phase_num" "$phase_name"
                return $?
                ;;
            view|v)
                echo ""
                echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                jq -r '.results[] | select(.status == "fail" or .status == "warn") |
                    "\n  [\(.status | ascii_upcase)] \(.audit_id)\n  \(.message)\n" +
                    (if (.findings | length) > 0 then
                        (.findings[] | "    - [\(.severity | ascii_upcase)] \(.finding)\n      Fix: \(.recommendation)")
                    else "" end)' "$report_file" 2>/dev/null
                echo ""
                echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                # Loop back to menu
                ;;
            accept|a)
                echo ""
                echo -e "  ${YELLOW}Accepting audit results as-is.${NC}"
                echo ""
                return 0
                ;;
            rerun)
                return 2
                ;;
            *)
                echo -e "  ${RED}Enter remediate, view, accept, or rerun.${NC}"
                ;;
        esac
    done
}

# Guided Q&A walkthrough for audit findings
# Same pattern as _207_guided_walkthrough: show each finding, collect user decisions
audit_remediate_findings() {
    local report_file="$1"
    local phase_num="$2"
    local phase_name="$3"

    # Extract FAIL results first, then WARN
    local results_json
    results_json=$(jq -c '[.results[] | select(.status == "fail")] + [.results[] | select(.status == "warn")]' "$report_file" 2>/dev/null)

    local total_results
    total_results=$(echo "$results_json" | jq 'length')

    if [[ $total_results -eq 0 ]]; then
        echo -e "  ${YELLOW}No findings to remediate.${NC}"
        return 0
    fi

    # Flatten: build ordered list of individual findings with parent audit context
    # Each entry: { audit_id, status, severity, message, finding, f_severity, f_recommendation }
    local flat_findings
    flat_findings=$(echo "$results_json" | jq -c '
        [.[] | . as $parent |
            if (.findings | length) == 0 then
                [{
                    audit_id: $parent.audit_id,
                    status: $parent.status,
                    audit_severity: ($parent.severity // "medium"),
                    audit_message: ($parent.message // ""),
                    finding: $parent.message,
                    f_severity: ($parent.severity // "medium"),
                    f_recommendation: "Address the issue as described",
                    f_signal: ""
                }]
            else
                [.findings[] | {
                    audit_id: $parent.audit_id,
                    status: $parent.status,
                    audit_severity: ($parent.severity // "medium"),
                    audit_message: ($parent.message // ""),
                    finding: (.finding // ""),
                    f_severity: (.severity // "medium"),
                    f_recommendation: (.recommendation // ""),
                    f_signal: (.signal_id // "")
                }]
            end
        ] | flatten
    ')

    local total_findings
    total_findings=$(echo "$flat_findings" | jq 'length')

    echo ""
    echo -e "${CYAN}+----------------------------------------------------------+${NC}"
    local batch_text
    batch_text=$(printf "%-56.56s" "AUDIT REMEDIATION — $total_findings findings across $total_results audits")
    echo -e "${CYAN}|${NC} ${BOLD}${batch_text}${NC} ${CYAN}|${NC}"
    echo -e "${CYAN}+----------------------------------------------------------+${NC}"
    echo ""
    echo -e "  ${DIM}For each finding you can:${NC}"
    echo -e "    ${GREEN}Enter${NC}       Accept the recommended fix (default)"
    echo -e "    ${CYAN}Type${NC}        Provide your own fix direction"
    echo -e "    ${YELLOW}skip${NC}        Skip this finding"
    echo -e "    ${GREEN}all${NC}         Accept all remaining findings for this audit"
    echo -e "    ${RED}done${NC}        Stop reviewing, apply what you've decided so far"
    echo ""
    echo -e "${DIM}------------------------------------------------------------${NC}"

    local resolution_plan=""
    local resolved_count=0
    local skipped_count=0
    local prev_audit_id=""
    local auto_accept_audit=""

    local i
    for ((i=0; i<total_findings; i++)); do
        local entry
        entry=$(echo "$flat_findings" | jq -c ".[$i]")

        local audit_id status audit_message finding f_severity f_recommendation
        audit_id=$(echo "$entry" | jq -r '.audit_id')
        status=$(echo "$entry" | jq -r '.status')
        audit_message=$(echo "$entry" | jq -r '.audit_message')
        finding=$(echo "$entry" | jq -r '.finding')
        f_severity=$(echo "$entry" | jq -r '.f_severity')
        f_recommendation=$(echo "$entry" | jq -r '.f_recommendation')

        local status_upper
        status_upper=$(echo "$status" | tr '[:lower:]' '[:upper:]')

        local status_color="${YELLOW}"
        [[ "$status" == "fail" ]] && status_color="${RED}"

        # Show audit header when audit changes
        if [[ "$audit_id" != "$prev_audit_id" ]]; then
            auto_accept_audit=""  # reset auto-accept on new audit
            echo ""
            echo -e "${DIM}────────────────────────────────────────────────────────────${NC}"
            echo -e "  ${status_color}[${status_upper}]${NC}  ${BOLD}$audit_id${NC}"
            echo -e "  ${DIM}$audit_message${NC}"
            prev_audit_id="$audit_id"
        fi

        # If user chose "all" for this audit, auto-accept
        if [[ "$auto_accept_audit" == "$audit_id" ]]; then
            resolution_plan+="$((resolved_count + 1)). [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $f_recommendation\n\n"
            ((resolved_count++))
            echo -e "    ${GREEN}✓${NC} ${DIM}($((i+1))/$total_findings)${NC} [${f_severity^^}] auto-accepted"
            continue
        fi

        local sev_color="${YELLOW}"
        [[ "$f_severity" == "high" || "$f_severity" == "critical" ]] && sev_color="${RED}"
        [[ "$f_severity" == "low" ]] && sev_color="${DIM}"

        echo ""
        echo -e "    ${sev_color}[${f_severity^^}]${NC} ${BOLD}($((i+1))/$total_findings)${NC}"
        echo -e "    $finding"
        if [[ -n "$f_recommendation" ]]; then
            echo ""
            echo -e "    ${DIM}Fix: $f_recommendation${NC}"
        fi
        echo ""

        read -e -p "  Resolution [accept]: " user_response

        if [[ "$user_response" == "done" ]]; then
            echo ""
            echo -e "  ${DIM}Stopping review. $((total_findings - i - 1)) findings remaining.${NC}"
            break
        elif [[ "$user_response" == "skip" || "$user_response" == "s" ]]; then
            ((skipped_count++))
            echo -e "    ${DIM}-> Skipped${NC}"
        elif [[ "$user_response" == "all" ]]; then
            # Accept this finding and auto-accept remaining findings for this audit
            resolution_plan+="$((resolved_count + 1)). [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $f_recommendation\n\n"
            ((resolved_count++))
            auto_accept_audit="$audit_id"
            echo -e "    ${GREEN}-> Accepted (+ all remaining for this audit)${NC}"
        elif [[ -z "$user_response" || "$user_response" == "accept" || "$user_response" == "a" ]]; then
            resolution_plan+="$((resolved_count + 1)). [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $f_recommendation\n\n"
            ((resolved_count++))
            echo -e "    ${GREEN}-> Accepted${NC}"
        else
            resolution_plan+="$((resolved_count + 1)). [${status_upper}] $audit_id\n   FINDING: $finding\n   RESOLUTION: $user_response\n\n"
            ((resolved_count++))
            echo -e "    ${GREEN}-> $user_response${NC}"
        fi
    done

    echo ""
    echo -e "${DIM}------------------------------------------------------------${NC}"
    echo ""
    echo -e "  ${BOLD}Review complete:${NC} $resolved_count accepted, $skipped_count skipped"
    echo ""

    if [[ $resolved_count -eq 0 ]]; then
        echo -e "  ${YELLOW}No resolutions to apply.${NC}"
        return 0
    fi

    # Ask for additional instructions
    echo -e "  ${DIM}Any additional instructions for the remediation agent? (Enter to skip):${NC}"
    read -e -p "  > " additional_context

    if [[ -n "$additional_context" ]]; then
        resolution_plan+="\nADDITIONAL INSTRUCTIONS FROM USER:\n$additional_context\n"
    fi

    # Determine target artifact
    local artifact_path
    artifact_path=$(_audit_phase_artifact "$phase_num")

    if [[ -z "$artifact_path" ]]; then
        # No single artifact — save resolution plan as notes
        local notes_file="$AUDIT_OUTPUT_DIR/phase-$phase_num-remediation-notes.md"
        {
            echo "# Phase $phase_num Audit Remediation Notes"
            echo ""
            echo "Generated: $(date -Iseconds)"
            echo ""
            echo "## Resolution Plan ($resolved_count items)"
            echo ""
            echo -e "$resolution_plan"
        } > "$notes_file"
        echo -e "  ${YELLOW}Phase $phase_num has no single artifact to revise.${NC}"
        echo -e "  ${GREEN}✓${NC} Resolution plan saved: $notes_file"
        echo -e "  ${DIM}Apply these notes during the next implementation cycle.${NC}"
        echo ""
        atomic_context_artifact "phase${phase_num}_remediation_notes" "$notes_file" "Audit remediation notes for phase $phase_num"
        atomic_context_decision "Phase $phase_num audit: $resolved_count remediation items noted" "audit-remediation"
        return 0
    fi

    # For spec directory (phase 4), we also save notes rather than LLM-edit
    if [[ -d "$artifact_path" ]]; then
        local notes_file="$AUDIT_OUTPUT_DIR/phase-$phase_num-remediation-notes.md"
        {
            echo "# Phase $phase_num Audit Remediation Notes"
            echo ""
            echo "Generated: $(date -Iseconds)"
            echo "Target directory: $artifact_path"
            echo ""
            echo "## Resolution Plan ($resolved_count items)"
            echo ""
            echo -e "$resolution_plan"
        } > "$notes_file"
        echo -e "  ${YELLOW}Phase $phase_num artifact is a directory ($artifact_path).${NC}"
        echo -e "  ${GREEN}✓${NC} Resolution plan saved: $notes_file"
        echo -e "  ${DIM}Apply these notes to the relevant spec files.${NC}"
        echo ""
        atomic_context_artifact "phase${phase_num}_remediation_notes" "$notes_file" "Audit remediation notes for phase $phase_num"
        atomic_context_decision "Phase $phase_num audit: $resolved_count remediation items noted" "audit-remediation"
        return 0
    fi

    if [[ ! -f "$artifact_path" ]]; then
        echo -e "  ${YELLOW}Artifact not found: $artifact_path${NC}"
        echo -e "  ${DIM}Saving resolution plan as notes instead.${NC}"
        local notes_file="$AUDIT_OUTPUT_DIR/phase-$phase_num-remediation-notes.md"
        {
            echo "# Phase $phase_num Audit Remediation Notes"
            echo ""
            echo "Generated: $(date -Iseconds)"
            echo "Expected artifact: $artifact_path"
            echo ""
            echo "## Resolution Plan ($resolved_count items)"
            echo ""
            echo -e "$resolution_plan"
        } > "$notes_file"
        echo -e "  ${GREEN}✓${NC} Resolution plan saved: $notes_file"
        echo ""
        atomic_context_artifact "phase${phase_num}_remediation_notes" "$notes_file" "Audit remediation notes for phase $phase_num"
        return 0
    fi

    # Apply remediation via LLM
    _audit_apply_remediation "$artifact_path" "$resolution_plan" "$resolved_count" "$phase_num" "$phase_name"
    return $?
}

# Apply collected audit resolutions to a target artifact via LLM
# Same structure as _207_apply_plan()
_audit_apply_remediation() {
    local artifact_path="$1"
    local resolution_plan="$2"
    local resolved_count="$3"
    local phase_num="$4"
    local phase_name="$5"

    local prompts_dir="$AUDIT_OUTPUT_DIR"
    local remediation_prompt="$prompts_dir/phase-$phase_num-remediation-prompt.md"
    local remediation_output="$prompts_dir/phase-$phase_num-remediation-output.md"

    cat > "$remediation_prompt" << 'PROMPT_HEADER'
# Audit Remediation — Applying User-Directed Fixes

You are revising a document to address audit findings. Each item below has been
reviewed by the user who directed how to resolve it.

## CRITICAL OUTPUT RULES

1. Your ENTIRE response must be the revised document text. Nothing else.
2. Do NOT write to any files. Do NOT use any tools. Just output the text.
3. Do NOT wrap output in markdown fences. Start directly with the content.
4. Do NOT include any preamble, summary, or commentary before or after the document.
5. Output the COMPLETE document — every section, even those not affected by fixes.

## Revision Rules

1. Implement EACH resolution exactly as the user directed.
2. Do NOT modify sections unrelated to the resolutions.
3. Preserve all existing formatting and structure.
4. When fixing contradictions, update ALL occurrences in the document.
5. When adding new content, place it in the most appropriate existing section.

PROMPT_HEADER

    {
        echo "## Resolution Plan"
        echo ""
        echo -e "$resolution_plan"
        echo ""
        echo "## Current Document"
        echo ""
        cat "$artifact_path"
    } >> "$remediation_prompt"

    local saved_turns="${CLAUDE_MAX_TURNS:-10}"
    export CLAUDE_MAX_TURNS=25

    echo ""
    atomic_waiting "Applying $resolved_count audit resolutions to $(basename "$artifact_path")..."

    if ! atomic_invoke "$remediation_prompt" "$remediation_output" "Audit remediation (phase $phase_num)" --model=opus --timeout=3600; then
        export CLAUDE_MAX_TURNS="$saved_turns"
        echo -e "  ${RED}Remediation failed. Artifact unchanged.${NC}"
        return 1
    fi
    export CLAUDE_MAX_TURNS="$saved_turns"

    # ── Verify output ──

    if [[ ! -f "$remediation_output" ]]; then
        echo -e "  ${RED}No output. Artifact unchanged.${NC}"
        return 1
    fi

    local output_lines orig_lines
    output_lines=$(wc -l < "$remediation_output" 2>/dev/null || echo 0)
    orig_lines=$(wc -l < "$artifact_path" 2>/dev/null || echo 0)

    if [[ $output_lines -lt $((orig_lines / 2)) ]]; then
        echo -e "  ${RED}Output too short ($output_lines vs $orig_lines lines). Artifact unchanged.${NC}"
        echo -e "  ${DIM}Saved to: $remediation_output${NC}"

        # Fallback: check if LLM wrote directly
        local current_lines
        current_lines=$(wc -l < "$artifact_path" 2>/dev/null || echo 0)
        if [[ $current_lines -gt $orig_lines ]]; then
            echo -e "  ${YELLOW}LLM appears to have modified the artifact directly (+$((current_lines - orig_lines)) lines).${NC}"
            echo -e "  ${DIM}Changes are already applied.${NC}"
            atomic_context_decision "Phase $phase_num audit remediation applied (direct write)" "audit-remediation"
            return 0
        fi
        return 1
    fi

    # Strip fences if wrapped
    if head -1 "$remediation_output" | grep -q '```'; then
        sed -i '1d' "$remediation_output"
        tail -1 "$remediation_output" | grep -q '```' && sed -i '$d' "$remediation_output"
    fi

    # ── Diff & Apply ──

    if diff -q "$artifact_path" "$remediation_output" &>/dev/null; then
        echo -e "  ${YELLOW}No changes detected.${NC}"
        return 0
    fi

    local added removed
    added=$(diff "$artifact_path" "$remediation_output" 2>/dev/null | grep -c '^>' || echo 0)
    removed=$(diff "$artifact_path" "$remediation_output" 2>/dev/null | grep -c '^<' || echo 0)

    echo ""
    echo -e "  ${CYAN}Remediation Summary:${NC}"
    echo -e "    Original:  $orig_lines lines"
    echo -e "    Revised:   $output_lines lines"
    echo -e "    Added:     ${GREEN}+$added lines${NC}"
    echo -e "    Removed:   ${RED}-$removed lines${NC}"
    echo ""
    echo -e "    ${GREEN}[apply]${NC}  Accept    ${CYAN}[diff]${NC}  View diff    ${RED}[discard]${NC}  Reject"
    echo ""

    while true; do
        atomic_drain_stdin
        read -e -p "  Choice [apply]: " ref_choice
        ref_choice=${ref_choice:-apply}

        case "$ref_choice" in
            apply|a)
                cp "$artifact_path" "${artifact_path}.bak"
                cp "$remediation_output" "$artifact_path"
                echo ""
                echo -e "  ${GREEN}✓ Artifact updated.${NC} ${DIM}Backup: $(basename "${artifact_path}").bak${NC}"
                echo ""

                # Log remediation
                {
                    echo "---"
                    echo "timestamp: $(date -Iseconds 2>/dev/null || date)"
                    echo "source: audit-remediation"
                    echo "phase: $phase_num"
                    echo "resolutions: $resolved_count"
                    echo "lines_added: $added"
                    echo "lines_removed: $removed"
                    echo "---"
                } >> "$AUDIT_OUTPUT_DIR/audit-remediation.log"

                atomic_context_decision "Phase $phase_num audit remediation applied (+$added/-$removed lines, $resolved_count items)" "audit-remediation"
                return 0
                ;;
            diff|d)
                echo ""
                echo -e "${DIM}------- DIFF (original -> revised) -------${NC}"
                diff --color=always -u "$artifact_path" "$remediation_output" 2>/dev/null | head -200 \
                    || diff -u "$artifact_path" "$remediation_output" 2>/dev/null | head -200
                echo ""
                echo -e "${DIM}  (first 200 lines)${NC}"
                echo -e "${DIM}------------------------------------------${NC}"
                echo ""
                ;;
            discard|x)
                echo ""
                echo -e "  ${YELLOW}Remediation discarded. Artifact unchanged.${NC}"
                echo -e "  ${DIM}Output preserved at: $remediation_output${NC}"
                echo ""
                return 0
                ;;
            *)
                echo -e "  ${RED}Enter apply, diff, or discard.${NC}"
                ;;
        esac
    done
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
    echo -e "    ${GREEN}[2]${NC} Browse Catalog"
    echo -e "        ${DIM}Select audits manually by category from the full library${NC}"
    echo ""

    local legacy_option=3
    if [[ -n "$legacy_callback" ]] && declare -f "$legacy_callback" > /dev/null 2>&1; then
        echo -e "    ${GREEN}[3]${NC} Legacy Dimensions"
        echo -e "        ${DIM}Static dimension-based audit for Phase $phase_num${NC}"
        echo ""
        legacy_option=3
    fi

    local skip_option=$((legacy_option + 1))
    [[ -z "$legacy_callback" ]] && skip_option=3

    echo -e "    ${GREEN}[$skip_option]${NC} Skip Audit"
    echo -e "        ${DIM}Proceed without audit (not recommended)${NC}"
    echo ""

    read -e -p "  Mode [1]: " mode_choice
    mode_choice=${mode_choice:-1}

    case "$mode_choice" in
        1)
            audit_run_phase "$phase_num" "$phase_name"
            return $?
            ;;
        2)
            # Browse catalog - returns path to recommendations file or fails
            local rec_file
            if rec_file=$(audit_browse_catalog "$phase_num" "$phase_name"); then
                if [[ -f "$rec_file" ]]; then
                    local recommendations
                    recommendations=$(cat "$rec_file")
                    audit_execute_streaming "$recommendations"
                    return $?
                fi
            fi
            # User chose to go back - recurse to show menu again
            audit_phase_wrapper "$phase_num" "$phase_name" "$legacy_callback"
            return $?
            ;;
        3)
            if [[ -n "$legacy_callback" ]] && declare -f "$legacy_callback" > /dev/null 2>&1; then
                "$legacy_callback"
                return $?
            else
                echo -e "  ${YELLOW}!${NC} Skipping audit for Phase $phase_num"
                atomic_context_decision "Phase $phase_num audit skipped by user" "audit"
                return 0
            fi
            ;;
        4)
            if [[ -n "$legacy_callback" ]] && declare -f "$legacy_callback" > /dev/null 2>&1; then
                echo -e "  ${YELLOW}!${NC} Skipping audit for Phase $phase_num"
                atomic_context_decision "Phase $phase_num audit skipped by user" "audit"
                return 0
            else
                audit_run_phase "$phase_num" "$phase_name"
                return $?
            fi
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

    # Get AI recommendations (once — user edits are preserved in the loop)
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

    # Interactive loop — user can view/add/remove without regenerating
    while true; do
        # Present to user
        choice=$(audit_present_recommendations "$recommendations")

        case "$choice" in
            1)
                # Accept and execute (streaming — results appear as each audit completes)
                audit_execute_streaming "$recommendations"
                local stream_rc=$?
                if [[ $stream_rc -eq 2 ]]; then
                    # User requested rerun — loop back to recommendation selection
                    continue
                fi
                return $stream_rc
                ;;
            2)
                # View details — accept a number, ID, or blank for all
                read -e -p "  View # or ID (blank for all): " view_input >&2
                echo "" >&2
                if [[ -z "$view_input" ]]; then
                    echo "$recommendations" | jq -r '.recommendations[] | "[\(.audit_id)] \(.name)\n  Relevance: \(.relevance)\n  Status: \(.dependency_status)\n"' >&2
                else
                    local view_ids
                    view_ids=$(_audit_resolve_refs "$recommendations" "$view_input")
                    if [[ -z "$view_ids" ]]; then
                        echo -e "  ${YELLOW}!${NC} No matching audit for: $view_input" >&2
                    else
                        local vid
                        while IFS= read -r vid; do
                            [[ -z "$vid" ]] && continue
                            echo "$recommendations" | jq -r --arg id "$vid" '.recommendations[] | select(.audit_id == $id) | "[\(.audit_id)] \(.name)\n  Category: \(.category // "-")\n  Relevance: \(.relevance)\n  Status: \(.dependency_status)\n  Priority: \(.priority // "-")\n"' >&2
                        done <<< "$view_ids"
                    fi
                fi
                echo "" >&2
                # Loop back — no regeneration
                ;;
            3)
                # Browse and add audits from catalog
                local add_selection=()
                _audit_browse_categories "$phase_num" add_selection

                if [[ ${#add_selection[@]} -gt 0 ]]; then
                    local csv_content
                    csv_content=$(audit_get_phase_audits "$phase_num" 2>/dev/null)
                    local added_count=0

                    for aid in "${add_selection[@]}"; do
                        # Check if already in recommendations
                        local exists
                        exists=$(echo "$recommendations" | jq -r --arg id "$aid" '.recommendations[] | select(.audit_id == $id) | .audit_id')
                        if [[ -n "$exists" ]]; then
                            echo -e "  ${YELLOW}!${NC} $aid already in recommendations" >&2
                            continue
                        fi

                        # Get audit details from CSV
                        local aname category
                        local row=$(echo "$csv_content" | awk -F',' -v id="$aid" '$1 == id {print; exit}')
                        if [[ -n "$row" ]]; then
                            aname=$(echo "$row" | cut -d',' -f3)
                            category=$(echo "$row" | cut -d',' -f4)
                        else
                            aname="$aid"
                            category="unknown"
                        fi

                        # Add to recommendations
                        local new_recs
                        new_recs=$(echo "$recommendations" | jq --arg id "$aid" --arg name "$aname" --arg cat "$category" '
                            .recommendations += [{
                                "audit_id": $id,
                                "name": $name,
                                "category": $cat,
                                "relevance": "user-added",
                                "dependency_status": "ready",
                                "priority": "medium",
                                "added_manually": true
                            }]
                        ')
                        if [[ $? -eq 0 ]] && echo "$new_recs" | jq -e . &>/dev/null; then
                            recommendations="$new_recs"
                            ((added_count++))
                        fi
                    done

                    if [[ $added_count -gt 0 ]]; then
                        echo -e "  ${GREEN}✓${NC} Added $added_count audits" >&2
                        echo "$recommendations" > "$AUDIT_OUTPUT_DIR/phase-$phase_num-recommendations.json"
                    fi
                fi
                # Loop back — no regeneration
                ;;
            4)
                # Remove audit by number(s) or ID
                read -e -p "  Enter # or ID to remove (comma-separated for multiple): " remove_input
                if [[ -n "$remove_input" ]]; then
                    local resolved_ids
                    resolved_ids=$(_audit_resolve_refs "$recommendations" "$remove_input")
                    if [[ -z "$resolved_ids" ]]; then
                        echo -e "  ${YELLOW}!${NC} No matching audits found for: $remove_input" >&2
                    else
                        local rid
                        while IFS= read -r rid; do
                            [[ -z "$rid" ]] && continue
                            local before_count new_recs
                            before_count=$(echo "$recommendations" | jq '.recommendations | length')
                            new_recs=$(echo "$recommendations" | jq --arg id "$rid" '
                                .recommendations |= map(select(.audit_id != $id))
                            ')
                            if [[ $? -eq 0 ]] && echo "$new_recs" | jq -e . &>/dev/null; then
                                local after_count
                                after_count=$(echo "$new_recs" | jq '.recommendations | length')
                                if [[ "$before_count" -ne "$after_count" ]]; then
                                    recommendations="$new_recs"
                                    echo -e "  ${GREEN}✓${NC} Removed $rid" >&2
                                else
                                    echo -e "  ${YELLOW}!${NC} $rid not found" >&2
                                fi
                            else
                                echo -e "  ${RED}✗${NC} Failed to remove $rid (jq error)" >&2
                            fi
                        done <<< "$resolved_ids"
                        echo "$recommendations" > "$AUDIT_OUTPUT_DIR/phase-$phase_num-recommendations.json"
                    fi
                fi
                # Loop back — no regeneration
                ;;
            5)
                # Mark all audits as ready (approve needs_review and needs-deps)
                local before_ready after_ready
                before_ready=$(echo "$recommendations" | jq '[.recommendations[] | select(.dependency_status == "ready")] | length')
                recommendations=$(echo "$recommendations" | jq '
                    .recommendations |= map(.dependency_status = "ready")
                ')
                after_ready=$(echo "$recommendations" | jq '[.recommendations[] | select(.dependency_status == "ready")] | length')
                echo -e "  ${GREEN}✓${NC} Marked all $after_ready audits as ready" >&2
                echo "$recommendations" > "$AUDIT_OUTPUT_DIR/phase-$phase_num-recommendations.json"
                # Loop back — no regeneration
                ;;
            6)
                # Skip
                echo -e "  ${YELLOW}!${NC} Skipping audits for Phase $phase_num"
                atomic_context_decision "Phase $phase_num audit skipped by user" "audit"
                return 0
                ;;
            7)
                # Run ALL applicable audits (no LLM selection)
                echo "" >&2
                local all_count
                all_count=$(audit_get_phase_audits "$phase_num" 2>/dev/null | tail -n +2 | wc -l)
                echo -e "  ${YELLOW}⚠ WARNING: This will run ALL $all_count applicable audits for phase $phase_num${NC}" >&2
                echo -e "  ${DIM}This can be very expensive in LLM calls and time.${NC}" >&2
                echo "" >&2
                read -e -p "  Type 'yes' to confirm: " confirm >&2
                if [[ "$confirm" == "yes" ]]; then
                    echo "" >&2
                    echo -e "  ${GREEN}✓${NC} Generating all-audit recommendations..." >&2
                    recommendations=$(audit_get_all_recommendations "$phase_num" "$phase_name")
                    if echo "$recommendations" | jq -e '.recommendations' &>/dev/null; then
                        echo "$recommendations" > "$AUDIT_OUTPUT_DIR/phase-$phase_num-recommendations.json"
                        local new_count
                        new_count=$(echo "$recommendations" | jq '.recommendations | length')
                        echo -e "  ${GREEN}✓${NC} Selected $new_count audits (all applicable)" >&2
                    else
                        echo -e "  ${RED}✗${NC} Failed to generate all-audit recommendations" >&2
                    fi
                else
                    echo -e "  ${DIM}Cancelled. Returning to menu.${NC}" >&2
                fi
                ;;
        esac
    done
}
