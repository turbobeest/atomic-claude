#!/bin/bash
#
# Task 102: Corpus Collection (Conversation 1)
# Collect, analyze, and organize all project materials
#
# Steps:
#   1. Scan directory for existing materials
#   2. Request additional materials from human
#   3. Analyze corpus (LLM)
#   4. Conversational reflection with human
#   5. Organize into docs/corpus/CORPUS-INDEX.md
#
# Supported file types: .md, .txt, .rst, .pdf, .json, .yaml, .yml
#

# Track seen paths for deduplication
declare -A _102_SEEN_PATHS

task_102_corpus_collection() {
    local corpus_dir="$ATOMIC_ROOT/docs/corpus"
    local corpus_index="$corpus_dir/CORPUS-INDEX.md"
    local corpus_json="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/corpus.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    atomic_step "Corpus Collection"

    mkdir -p "$corpus_dir" "$prompts_dir"

    # Reset deduplication tracking
    _102_SEEN_PATHS=()

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ CONVERSATION 1: CORPUS COLLECTION                       │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Let's gather all materials relevant to your project:   │${NC}"
    echo -e "${DIM}  │ documents, specs, PRDs, links, references, prior work. │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Supported: .md .txt .rst .pdf .json .yaml              │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Initialize corpus tracking
    local corpus='{"materials": [], "links": [], "scanned_at": "'$(date -Iseconds)'"}'

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 1: SCAN DIRECTORY
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}STEP 1: SCANNING FOR EXISTING MATERIALS${NC}                   ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local found_count=0

    echo -e "  ${CYAN}Scanning for documents...${NC}"

    # README files (safe while-read pattern)
    while IFS= read -r -d '' readme; do
        if _102_add_material "$readme" "auto"; then
            local rel_path="${readme#$ATOMIC_ROOT/}"
            echo -e "    ${GREEN}✓${NC} $(basename "$readme") ${DIM}(${rel_path%/*})${NC}"
            ((found_count++))
        fi
    done < <(find "$ATOMIC_ROOT" -maxdepth 3 -name "README*" -type f -print0 2>/dev/null | head -z -n 10)

    # PRD/spec documents (safe while-read pattern)
    while IFS= read -r -d '' doc; do
        if _102_add_material "$doc" "auto"; then
            echo -e "    ${GREEN}✓${NC} $(basename "$doc")"
            ((found_count++))
        fi
    done < <(find "$ATOMIC_ROOT" -maxdepth 3 \( -name "*.md" -o -name "*.txt" -o -name "*.rst" \) -type f -print0 2>/dev/null | grep -zE -i "(prd|spec|design|architecture|requirements)" | head -z -n 10)

    # docs/ directory
    if [[ -d "$ATOMIC_ROOT/docs" ]]; then
        local doc_count
        doc_count=$(find "$ATOMIC_ROOT/docs" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.rst" \) 2>/dev/null | wc -l)
        if [[ $doc_count -gt 0 ]]; then
            echo -e "    ${GREEN}✓${NC} docs/ directory: $doc_count files available"
        fi
    fi

    # Existing corpus
    if [[ -d "$corpus_dir" ]] && [[ "$(ls -A "$corpus_dir" 2>/dev/null)" ]]; then
        local existing_count
        existing_count=$(find "$corpus_dir" -type f 2>/dev/null | wc -l)
        echo -e "    ${GREEN}✓${NC} Existing corpus: $existing_count files"
    fi

    echo ""
    echo -e "  ${DIM}Auto-discovered $found_count materials${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2: REQUEST ADDITIONAL MATERIALS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}STEP 2: ADDITIONAL MATERIALS${NC}                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${CYAN}What other materials should we include?${NC}"
    echo ""
    echo -e "  ${DIM}You can provide:${NC}"
    echo -e "    • File paths (relative or absolute)"
    echo -e "    • Directory paths to scan"
    echo -e "    • URLs ${DIM}(stored as references, not fetched)${NC}"
    echo -e "    • Press Enter when finished"
    echo ""

    local manual_count=0
    while true; do
        read -p "  Add material: " material_input

        # Empty input means done
        [[ -z "$material_input" ]] && break

        # Explicit done command
        [[ "${material_input,,}" == "done" ]] && break

        # Determine type
        if [[ "$material_input" =~ ^https?:// ]]; then
            # URL - store as reference (not fetched)
            corpus=$(echo "$corpus" | jq --arg url "$material_input" '.links += [$url]')
            echo -e "    ${GREEN}✓${NC} Link saved: ${DIM}(reference only)${NC} $material_input"
            ((manual_count++))

        elif [[ -f "$material_input" ]]; then
            # Absolute file path
            if _102_add_material "$material_input" "manual"; then
                echo -e "    ${GREEN}✓${NC} File added: $(basename "$material_input")"
                ((manual_count++))
            else
                echo -e "    ${DIM}○${NC} Already included: $(basename "$material_input")"
            fi

        elif [[ -f "$ATOMIC_ROOT/$material_input" ]]; then
            # Relative file path
            if _102_add_material "$ATOMIC_ROOT/$material_input" "manual"; then
                echo -e "    ${GREEN}✓${NC} File added: $(basename "$material_input")"
                ((manual_count++))
            else
                echo -e "    ${DIM}○${NC} Already included: $(basename "$material_input")"
            fi

        elif [[ -d "$material_input" ]] || [[ -d "$ATOMIC_ROOT/$material_input" ]]; then
            # Directory
            local dir_path="$material_input"
            [[ ! -d "$dir_path" ]] && dir_path="$ATOMIC_ROOT/$material_input"

            local dir_files
            dir_files=$(find "$dir_path" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.rst" -o -name "*.pdf" -o -name "*.json" -o -name "*.yaml" -o -name "*.yml" \) 2>/dev/null | wc -l)

            corpus=$(echo "$corpus" | jq --arg path "$dir_path" --argjson count "$dir_files" \
                '.materials += [{"path": $path, "type": "directory", "file_count": $count}]')
            echo -e "    ${GREEN}✓${NC} Directory added: $dir_path ($dir_files supported files)"
            ((manual_count++))

        else
            echo -e "    ${YELLOW}!${NC} Not found: $material_input"
            echo -e "      ${DIM}Store as a reference note? [y/N]${NC}"
            read -p "      " store_note
            if [[ "${store_note,,}" == "y" ]]; then
                corpus=$(echo "$corpus" | jq --arg note "$material_input" \
                    '.materials += [{"note": $note, "type": "reference"}]')
                echo -e "      ${GREEN}✓${NC} Stored as reference"
                ((manual_count++))
            fi
        fi
    done

    [[ $manual_count -gt 0 ]] && echo -e "\n  ${DIM}Added $manual_count materials manually${NC}"
    echo ""

    # Build final materials list from tracked paths
    for path in "${!_102_SEEN_PATHS[@]}"; do
        local source="${_102_SEEN_PATHS[$path]}"
        corpus=$(echo "$corpus" | jq --arg path "$path" --arg name "$(basename "$path")" --arg src "$source" \
            '.materials += [{"path": $path, "name": $name, "type": "file", "source": $src}]')
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 3: ANALYZE CORPUS (LLM)
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}STEP 3: ANALYZING CORPUS${NC}                                  ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local total_materials=$(echo "$corpus" | jq '.materials | length')
    local total_links=$(echo "$corpus" | jq '.links | length')

    echo -e "  ${CYAN}Corpus size:${NC} $total_materials materials, $total_links links"
    echo ""

    local analysis_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/corpus-analysis.md"

    if [[ ${#_102_SEEN_PATHS[@]} -gt 0 ]]; then
        # Build corpus content for analysis
        local corpus_content=""
        local files_read=0
        local files_truncated=0
        local max_lines=300
        local max_files=10

        for path in "${!_102_SEEN_PATHS[@]}"; do
            [[ $files_read -ge $max_files ]] && break

            if [[ -f "$path" ]]; then
                local line_count
                line_count=$(wc -l < "$path" 2>/dev/null || echo "0")
                local truncated=""

                if [[ $line_count -gt $max_lines ]]; then
                    truncated=" [TRUNCATED: showing first $max_lines of $line_count lines]"
                    ((files_truncated++))
                fi

                corpus_content+="
=== FILE: $(basename "$path")$truncated ===
$(head -$max_lines "$path" 2>/dev/null)
"
                ((files_read++))
            fi
        done

        if [[ $files_truncated -gt 0 ]]; then
            echo -e "  ${DIM}Note: $files_truncated large files were truncated for analysis${NC}"
            echo ""
        fi

        if [[ $files_read -gt 0 ]]; then
            # Create analysis prompt
            cat > "$prompts_dir/corpus-analysis.md" << EOF
# Task: Analyze Project Corpus

You are a **technical analyst** specializing in software project discovery. Your role is to synthesize scattered documentation into a coherent understanding that will guide the PRD authoring phase.

## Token Budget

This analysis should be concise (500-800 words). Focus on actionable insights, not exhaustive summaries.

## Materials Collected

**Note:** Large files may be truncated (marked with [TRUNCATED]). Analyze what's provided and note if critical information might be missing from truncated sections.

$corpus_content

## Analysis Guidelines

- If materials are sparse or low-quality, explicitly state what's missing
- If materials contradict each other, note the conflicts
- If the project scope is unclear, list the ambiguities
- Focus on what will help the PRD author, not general observations

## Your Task

Provide a concise analysis:

1. **Project Understanding** (2-3 sentences)
   - What is this project about?
   - What problem does it solve?

2. **Key Themes** (3-5 bullets)
   - Main concepts and themes found

3. **Technical Indicators**
   - Technologies mentioned
   - Architecture patterns detected
   - Constraints identified

4. **Gaps & Questions** (3-5 bullets)
   - What's unclear or missing?
   - What should we ask the human?

5. **Recommended Focus Areas**
   - Where should discovery focus?

Be specific to THIS project. Output as markdown.

## Example Output (Full System)

# Corpus Analysis

## 1. Project Understanding
This project is a CLI tool for automating software development workflows through LLM-assisted phases. It solves the problem of inconsistent project setup and manual orchestration across discovery, planning, implementation, and release stages.

## 2. Key Themes
- Phase-based workflow orchestration (10 phases from setup to release)
- LLM-assisted code generation and review
- Human-in-the-loop gates at critical decision points
- Agent-based task delegation
- Artifact generation and audit trails

## 3. Technical Indicators
- **Technologies**: Bash scripting, jq for JSON processing, Claude API integration
- **Architecture**: Pipeline pattern with discrete phases, each containing ordered tasks
- **Constraints**: Must support offline/local LLM fallback, sandbox restrictions for security

## 4. Gaps & Questions
- How should failed LLM calls be retried or recovered?
- What's the expected project size/complexity this tool should handle?
- Are there specific compliance requirements for generated artifacts?
- How do agents coordinate when multiple are assigned to a phase?

## 5. Recommended Focus Areas
- Error handling and recovery strategies across phases
- Context management to stay within LLM token limits
- Human gate UX for approval workflows

---

## Example Output (Component/Module)

# Corpus Analysis

## 1. Project Understanding
This project is a containerized authentication service designed to support the platform's microservices architecture by providing centralized JWT validation and session management. It serves as the security boundary between public-facing APIs and internal services.

## 2. Key Themes
- Stateless token validation for horizontal scaling
- Integration with existing LDAP/AD identity providers
- Rate limiting and brute-force protection
- Audit logging for compliance

## 3. Technical Indicators
- **Technologies**: Go, Redis for session cache, PostgreSQL for audit logs
- **Architecture**: Sidecar pattern, deployed alongside API gateway
- **Constraints**: Must meet SOC2 requirements, <10ms p99 latency for token validation

## 4. Gaps & Questions
- What's the token refresh strategy when the identity provider is unavailable?
- Should this service handle authorization (RBAC) or only authentication?
- What existing services will consume this component first?
- Are there legacy session-based services that need migration support?

## 5. Recommended Focus Areas
- Failure modes when Redis cache is unavailable
- Migration path for services currently using embedded auth
- Observability and alerting thresholds

---

## Edge Case Handling

If you encounter these situations, handle them as follows:

| Situation | Response |
|-----------|----------|
| No readable content | State "Insufficient materials" and list what's needed |
| All files truncated | Analyze what's visible, note "Full context unavailable" |
| Contradictory information | List conflicts under "Gaps & Questions" |
| Missing tech details | Ask specific questions in "Gaps & Questions" |
| Unclear project scope | Provide your best interpretation with caveats |

Output ONLY the analysis in markdown format. Do not include meta-commentary.
EOF

            atomic_waiting "Claude is analyzing corpus..."

            if atomic_invoke "$prompts_dir/corpus-analysis.md" "$analysis_file" "Corpus analysis" --model=sonnet; then
                corpus=$(echo "$corpus" | jq --arg analysis "$analysis_file" '.analysis_file = $analysis')
                atomic_success "Corpus analyzed"
            else
                atomic_warn "Corpus analysis failed - continuing"
            fi
        else
            echo -e "  ${DIM}No readable files found - skipping LLM analysis${NC}"
        fi
    else
        echo -e "  ${DIM}No materials collected - skipping analysis${NC}"
    fi

    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 4: CONVERSATIONAL REFLECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}STEP 4: REFLECTION${NC}                                        ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Show analysis if available
    if [[ -f "$analysis_file" ]]; then
        echo -e "  ${CYAN}From the corpus analysis:${NC}"
        echo ""
        head -40 "$analysis_file" | while IFS= read -r line; do
            echo -e "  │ $line"
        done
        echo ""
    fi

    # Conversational reflection loop
    local reflection_complete=false
    local reflection_turns=0

    echo -e "  ${CYAN}Let's make sure I understand your project correctly.${NC}"
    echo ""

    while [[ "$reflection_complete" == false ]]; do
        if [[ $reflection_turns -eq 0 ]]; then
            echo -e "  ${DIM}Does this analysis capture your project accurately?${NC}"
            echo -e "  ${DIM}Share any corrections, clarifications, or missing context.${NC}"
            echo -e "  ${DIM}(Type 'yes' or press Enter if accurate, or provide feedback)${NC}"
        else
            echo -e "  ${DIM}Anything else to add or clarify? (Enter to continue)${NC}"
        fi
        echo ""

        read -p "  > " human_feedback

        if [[ -z "$human_feedback" ]] || [[ "${human_feedback,,}" =~ ^(yes|correct|accurate|good|ok|y)$ ]]; then
            echo ""
            echo -e "  ${GREEN}✓${NC} Understanding confirmed"
            reflection_complete=true
        else
            # Store feedback
            corpus=$(echo "$corpus" | jq --arg fb "$human_feedback" \
                '.human_feedback = ((.human_feedback // "") + "\n" + $fb) | .human_feedback |= ltrimstr("\n")')
            echo ""
            echo -e "  ${GREEN}✓${NC} Feedback noted"
            echo ""
            ((reflection_turns++))

            # After a few turns, offer to proceed
            if [[ $reflection_turns -ge 3 ]]; then
                echo -e "  ${DIM}(We've captured several pieces of feedback. Enter to proceed, or continue adding.)${NC}"
            fi
        fi
    done

    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 5: ORGANIZE CORPUS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}STEP 5: ORGANIZING CORPUS${NC}                                 ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Copy materials to corpus directory
    local copied=0
    local skipped=0

    for path in "${!_102_SEEN_PATHS[@]}"; do
        if [[ -f "$path" ]]; then
            local basename
            basename=$(basename "$path")
            local dest="$corpus_dir/$basename"

            # Handle name collisions
            if [[ -f "$dest" ]]; then
                # Check if same file
                if cmp -s "$path" "$dest" 2>/dev/null; then
                    ((skipped++))
                    continue
                fi
                # Different file, add suffix
                local counter=1
                local name="${basename%.*}"
                local ext="${basename##*.}"
                while [[ -f "$corpus_dir/${name}_${counter}.${ext}" ]]; do
                    ((counter++))
                done
                dest="$corpus_dir/${name}_${counter}.${ext}"
            fi

            if cp "$path" "$dest" 2>/dev/null; then
                ((copied++))
            fi
        fi
    done

    [[ $copied -gt 0 ]] && echo -e "  ${GREEN}✓${NC} Copied $copied files to docs/corpus/"
    [[ $skipped -gt 0 ]] && echo -e "  ${DIM}○${NC} Skipped $skipped duplicates"

    # Generate CORPUS-INDEX.md
    cat > "$corpus_index" << EOF
# Corpus Index

Generated: $(date -Iseconds)

## Materials

EOF

    # List materials
    echo "$corpus" | jq -r '.materials[] | "- **\(.name // .path // .note)** (\(.type))\(.source | if . == "auto" then " [auto-discovered]" else "" end)"' >> "$corpus_index"

    # List links
    local link_count
    link_count=$(echo "$corpus" | jq '.links | length')
    if [[ $link_count -gt 0 ]]; then
        cat >> "$corpus_index" << EOF

## External Links (References)

*These URLs are stored for reference but were not fetched during analysis.*

EOF
        echo "$corpus" | jq -r '.links[] | "- \(.)"' >> "$corpus_index"
    fi

    # Add analysis summary if available
    if [[ -f "$analysis_file" ]]; then
        cat >> "$corpus_index" << EOF

## Analysis Summary

EOF
        head -30 "$analysis_file" >> "$corpus_index"
    fi

    # Add human feedback if provided
    local feedback
    feedback=$(echo "$corpus" | jq -r '.human_feedback // empty')
    if [[ -n "$feedback" ]]; then
        cat >> "$corpus_index" << EOF

## Human Feedback

$feedback
EOF
    fi

    echo -e "  ${GREEN}✓${NC} Generated CORPUS-INDEX.md"

    # Save corpus JSON
    echo "$corpus" | jq . > "$corpus_json"
    echo -e "  ${GREEN}✓${NC} Saved corpus.json"

    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Corpus Collection Complete${NC}"
    echo ""
    echo -e "  Materials: $total_materials"
    echo -e "  Links:     $total_links (references)"
    echo -e "  Location:  docs/corpus/"
    echo -e "  Index:     docs/corpus/CORPUS-INDEX.md"
    echo ""

    atomic_context_artifact "corpus" "$corpus_json" "Collected project corpus"
    atomic_context_artifact "corpus_index" "$corpus_index" "Corpus index document"
    atomic_context_decision "Corpus collected: $total_materials materials, $total_links links" "corpus_collection"

    atomic_success "Corpus collection complete"

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Add a material path with deduplication
# Returns 0 if added, 1 if already exists
_102_add_material() {
    local path="$1"
    local source="${2:-manual}"

    # Get absolute path
    local abs_path
    abs_path=$(realpath "$path" 2>/dev/null) || return 1

    # Check if already seen
    if [[ -n "${_102_SEEN_PATHS[$abs_path]:-}" ]]; then
        return 1
    fi

    # Check if it's a supported file type
    local ext="${abs_path##*.}"
    case "${ext,,}" in
        md|txt|rst|pdf|json|yaml|yml)
            _102_SEEN_PATHS["$abs_path"]="$source"
            return 0
            ;;
        *)
            # Not a supported type, skip silently for auto-discovery
            [[ "$source" == "auto" ]] && return 1
            # For manual, warn user
            echo -e "    ${YELLOW}!${NC} Unsupported file type: .$ext"
            return 1
            ;;
    esac
}
