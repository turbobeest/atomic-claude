#!/bin/bash
#
# Task 103: Import Existing Requirements (Optional)
# Import requirements from existing project documentation
#
# This task is OPTIONAL - for projects with existing requirements docs.
#
# Supported formats:
#   - Sphinx-needs RST files (.. req::, .. spec::, etc.)
#   - Markdown requirements files
#   - CSV/spreadsheet exports
#   - JSON/YAML requirements files
#
# Purpose:
#   If you're bringing in an existing project that already has
#   documented requirements, this task imports them into our
#   structured format for traceability throughout the pipeline.
#
# Note:
#   For NEW projects, requirements will be generated in Phase 2 (PRD)
#   using sphinx-needs format. This task is only for importing
#   existing requirements from legacy documentation.
#

task_103_import_requirements() {
    local needs_dir="$ATOMIC_ROOT/.claude/needs"
    local needs_index="$needs_dir/needs-index.json"
    local output_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE"

    # Check for jq dependency
    if ! command -v jq &>/dev/null; then
        atomic_error "jq is required for requirements import"
        echo -e "  ${DIM}Install with: apt install jq / brew install jq${NC}"
        return 1
    fi

    atomic_step "Import Requirements"

    echo ""
    echo -e "  ${DIM}┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "  ${DIM}│ IMPORT REQUIREMENTS (Optional)                         │${NC}"
    echo -e "  ${DIM}│                                                         │${NC}"
    echo -e "  ${DIM}│ If your project has existing requirements docs, we     │${NC}"
    echo -e "  ${DIM}│ can import them for traceability.                      │${NC}"
    echo -e "  ${DIM}│                                                         │${NC}"
    echo -e "  ${DIM}│ Supported: Sphinx-needs RST, Markdown, CSV, JSON/YAML   │${NC}"
    echo -e "  ${DIM}└─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 1: DETECT RST FILES
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "  ${DIM}Scanning for RST files...${NC}"

    # Collect RST files into array (safe handling of special characters)
    local rst_files=()
    while IFS= read -r -d '' rst_file; do
        rst_files+=("$rst_file")
        # Limit to 100 files
        [[ ${#rst_files[@]} -ge 100 ]] && break
    done < <(find "$ATOMIC_ROOT" \
        -name "*.rst" \
        -type f \
        ! -path "*/\.*" \
        ! -path "*/__pycache__/*" \
        ! -path "*/node_modules/*" \
        ! -path "*/.venv/*" \
        ! -path "*/venv/*" \
        -print0 2>/dev/null)

    local rst_count=${#rst_files[@]}

    if [[ $rst_count -eq 0 ]]; then
        echo -e "  ${DIM}No RST files found.${NC}"
        echo ""
        read -p "  Does your project use Sphinx-Needs? [y/N]: " use_needs

        if [[ "$use_needs" =~ ^[Yy] ]]; then
            echo ""
            echo -e "  ${DIM}Enter paths to RST files (one per line, empty to finish):${NC}"
            declare -A _103_SEEN_MANUAL  # Deduplication for manual paths
            while true; do
                read -p "    Path: " manual_path
                [[ -z "$manual_path" ]] && break
                if [[ -f "$manual_path" ]]; then
                    local abs_path
                    abs_path=$(realpath "$manual_path" 2>/dev/null) || abs_path="$manual_path"
                    if [[ -n "${_103_SEEN_MANUAL[$abs_path]:-}" ]]; then
                        echo -e "    ${YELLOW}!${NC} Already added: $manual_path"
                    else
                        _103_SEEN_MANUAL["$abs_path"]=1
                        rst_files+=("$abs_path")
                        echo -e "    ${GREEN}✓${NC} Added: $manual_path"
                    fi
                else
                    echo -e "    ${RED}✗${NC} File not found: $manual_path"
                fi
            done

            if [[ ${#rst_files[@]} -eq 0 ]]; then
                atomic_info "No RST files provided - skipping"
                return 0
            fi

            rst_count=${#rst_files[@]}
        else
            atomic_info "Sphinx-needs: Skipped (no RST files)"
            return 0
        fi
    fi

    echo -e "  ${GREEN}✓${NC} Found $rst_count RST file(s)"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2: SCAN FOR DIRECTIVES
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "  ${DIM}Checking for sphinx-needs directives...${NC}"

    local files_with_needs=()
    local directive_pattern='^\.\.[[:space:]]+(req|spec|test|need|story|feature)::'

    for rst_file in "${rst_files[@]}"; do
        [[ ! -f "$rst_file" ]] && continue
        if grep -qE "$directive_pattern" "$rst_file" 2>/dev/null; then
            files_with_needs+=("$rst_file")
        fi
    done

    if [[ ${#files_with_needs[@]} -eq 0 ]]; then
        echo -e "  ${DIM}No sphinx-needs directives found in RST files.${NC}"
        echo ""
        atomic_info "Sphinx-needs: No directives found"
        return 0
    fi

    echo -e "  ${GREEN}✓${NC} Found directives in ${#files_with_needs[@]} file(s)"
    echo ""

    # List files with needs
    echo -e "  ${CYAN}Files with needs:${NC}"
    for f in "${files_with_needs[@]}"; do
        local count
        count=$(grep -cE "$directive_pattern" "$f" 2>/dev/null || echo "0")
        echo -e "    ${DIM}•${NC} $(basename "$f") ${DIM}($count needs)${NC}"
    done
    echo ""

    # Confirm parsing
    read -p "  Parse these files? [Y/n]: " do_parse
    if [[ "$do_parse" =~ ^[Nn] ]]; then
        atomic_info "Sphinx-needs: Skipped by user"
        return 0
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 3: PARSE NEEDS
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}PARSING SPHINX-NEEDS${NC}                                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    mkdir -p "$needs_dir"

    # Initialize needs structure
    local needs_json
    needs_json=$(cat <<EOF
{
    "version": "1.0",
    "parsed_at": "$(date -Iseconds)",
    "source_files": [],
    "needs": [],
    "summary": {
        "total": 0,
        "by_type": {}
    }
}
EOF
)

    local total_needs=0
    local seen_ids=()

    for rst_file in "${files_with_needs[@]}"; do
        local file_basename
        file_basename=$(basename "$rst_file")
        local file_relpath
        file_relpath=$(realpath --relative-to="$ATOMIC_ROOT" "$rst_file" 2>/dev/null || echo "$rst_file")

        # Add to source files
        needs_json=$(echo "$needs_json" | jq --arg file "$file_relpath" '.source_files += [$file]')

        echo -e "  ${CYAN}Parsing:${NC} $file_basename"

        local line_num=0
        local in_need=false
        local current_need=""
        local current_type=""
        local current_id=""
        local current_title=""
        local current_attrs="{}"
        local current_content=""
        local need_start_line=0

        # Process file line by line
        while IFS= read -r line || [[ -n "$line" ]]; do
            ((line_num++))

            # Check for new directive
            if [[ "$line" =~ ^\.\.[[:space:]]+(req|spec|test|need|story|feature)::[[:space:]]*(.*)$ ]]; then
                # Save previous need if exists
                if [[ "$in_need" == true && -n "$current_type" ]]; then
                    _103_save_need
                fi

                # Start new need
                in_need=true
                current_type="${BASH_REMATCH[1]}"
                local rest="${BASH_REMATCH[2]}"
                need_start_line=$line_num
                current_attrs="{}"
                current_content=""

                # Parse ID and title from rest
                # Format: .. req:: REQ-001 Title here
                # Or:     .. req:: Title here (no ID)
                if [[ "$rest" =~ ^([A-Z]+-[0-9]+)[[:space:]]*(.*)$ ]]; then
                    current_id="${BASH_REMATCH[1]}"
                    current_title="${BASH_REMATCH[2]}"
                elif [[ "$rest" =~ ^([A-Z]+[0-9]+)[[:space:]]*(.*)$ ]]; then
                    # Also match REQ001 format
                    current_id="${BASH_REMATCH[1]}"
                    current_title="${BASH_REMATCH[2]}"
                else
                    current_id=""
                    current_title="$rest"
                fi

                # Trim whitespace
                current_title=$(echo "$current_title" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

            # Check for attribute line (indented :attr: value)
            elif [[ "$in_need" == true && "$line" =~ ^[[:space:]]+:([a-z_]+):[[:space:]]*(.*)$ ]]; then
                local attr_name="${BASH_REMATCH[1]}"
                local attr_value="${BASH_REMATCH[2]}"
                current_attrs=$(echo "$current_attrs" | jq --arg k "$attr_name" --arg v "$attr_value" '. + {($k): $v}')

            # Check for content line (indented text, not attribute)
            elif [[ "$in_need" == true && "$line" =~ ^[[:space:]]{3,}[^:] ]]; then
                # Content line (at least 3 spaces, not starting with :)
                local content_line
                content_line=$(echo "$line" | sed 's/^[[:space:]]*//')
                if [[ -n "$current_content" ]]; then
                    current_content="$current_content $content_line"
                else
                    current_content="$content_line"
                fi

            # Check for end of need (non-indented line or blank after content)
            elif [[ "$in_need" == true && ! "$line" =~ ^[[:space:]] && -n "$line" ]]; then
                # Save current need
                _103_save_need
                in_need=false

                # Check if this line starts a new directive - process it immediately
                if [[ "$line" =~ ^\.\.[[:space:]]+(req|spec|test|need|story|feature)::[[:space:]]*(.*)$ ]]; then
                    # Start new need (same logic as main directive check above)
                    in_need=true
                    current_type="${BASH_REMATCH[1]}"
                    local rest="${BASH_REMATCH[2]}"
                    need_start_line=$line_num
                    current_attrs="{}"
                    current_content=""

                    # Parse ID and title
                    if [[ "$rest" =~ ^([A-Z]+-[0-9]+)[[:space:]]*(.*)$ ]]; then
                        current_id="${BASH_REMATCH[1]}"
                        current_title="${BASH_REMATCH[2]}"
                    elif [[ "$rest" =~ ^([A-Z]+[0-9]+)[[:space:]]*(.*)$ ]]; then
                        current_id="${BASH_REMATCH[1]}"
                        current_title="${BASH_REMATCH[2]}"
                    else
                        current_id=""
                        current_title="$rest"
                    fi
                    current_title=$(echo "$current_title" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                fi
            fi

        done < "$rst_file"

        # Save final need if file ends while in a need
        if [[ "$in_need" == true && -n "$current_type" ]]; then
            _103_save_need
        fi
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 4: SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Parsed $total_needs needs${NC}"
    echo ""

    # Calculate summary
    needs_json=$(echo "$needs_json" | jq --argjson total "$total_needs" '.summary.total = $total')

    echo -e "  ${CYAN}By Type:${NC}"
    for type in req spec test need story feature; do
        local count
        count=$(echo "$needs_json" | jq "[.needs[] | select(.type == \"$type\")] | length")
        if [[ $count -gt 0 ]]; then
            echo -e "    ${type}: $count"
            needs_json=$(echo "$needs_json" | jq --arg t "$type" --argjson c "$count" '.summary.by_type[$t] = $c')
        fi
    done
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 5: SAVE
    # ═══════════════════════════════════════════════════════════════════════════

    echo "$needs_json" | jq . > "$needs_index"
    echo -e "  ${GREEN}✓${NC} Saved: .claude/needs/needs-index.json"

    # Also save to phase output
    cp "$needs_index" "$output_dir/needs-index.json"
    echo -e "  ${GREEN}✓${NC} Copied to phase output"

    echo ""

    # Record to context
    atomic_context_artifact "needs_index" "$needs_index" "Sphinx-needs index ($total_needs needs)"
    atomic_context_decision "Parsed $total_needs sphinx-needs from ${#files_with_needs[@]} RST files" "needs_parsing"

    atomic_success "Sphinx-needs parsing complete"

    return 0
}

# Helper function to save a need to the JSON
# NOTE: This function uses variables from parent scope (bash limitation):
#   Reads:  current_id, current_type, current_title, current_content,
#           current_attrs, file_relpath, need_start_line, seen_ids
#   Writes: needs_json, total_needs, seen_ids, current_id (for auto-generated IDs)
_103_save_need() {
    # Generate ID if not provided
    if [[ -z "$current_id" ]]; then
        local prefix
        case "$current_type" in
            req)     prefix="REQ" ;;
            spec)    prefix="SPEC" ;;
            test)    prefix="TST" ;;
            need)    prefix="NEED" ;;
            story)   prefix="STORY" ;;
            feature) prefix="FEAT" ;;
            *)       prefix="NEED" ;;
        esac

        # Find next available number
        local num=1
        while printf '%s\n' "${seen_ids[@]}" | grep -q "^${prefix}-$(printf '%03d' $num)$" 2>/dev/null; do
            ((num++))
        done
        current_id="${prefix}-$(printf '%03d' $num)"
    fi

    # Check for duplicate ID
    if printf '%s\n' "${seen_ids[@]}" | grep -q "^${current_id}$" 2>/dev/null; then
        echo -e "    ${YELLOW}!${NC} Duplicate ID: $current_id (skipped)"
        return
    fi

    seen_ids+=("$current_id")

    # Build need object
    local need_obj
    need_obj=$(jq -n \
        --arg id "$current_id" \
        --arg type "$current_type" \
        --arg title "$current_title" \
        --arg content "$current_content" \
        --arg file "$file_relpath" \
        --argjson line "$need_start_line" \
        --argjson attrs "$current_attrs" \
        '{
            id: $id,
            type: $type,
            title: $title,
            content: $content,
            attributes: $attrs,
            source: {
                file: $file,
                line: $line
            }
        }')

    needs_json=$(echo "$needs_json" | jq --argjson need "$need_obj" '.needs += [$need]')
    ((total_needs++))

    # Display
    local display_title="$current_title"
    [[ ${#display_title} -gt 50 ]] && display_title="${display_title:0:47}..."
    echo -e "    ${GREEN}✓${NC} $current_id: $display_title"
}
