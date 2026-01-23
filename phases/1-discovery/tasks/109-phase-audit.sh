#!/bin/bash
#
# Task 109: Phase Audit - Discovery
# AI-driven audit selection from turbobeest/audits repository
#
# Features:
#   - AI recommends relevant audits based on phase context
#   - User reviews and approves audit selection
#   - Executes selected audits with dependency awareness
#   - Supports air-gapped environments via dependency manifests
#

task_109_phase_audit() {
    local audit_dir="$ATOMIC_ROOT/.claude/audit"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    atomic_step "Phase Audit"

    mkdir -p "$audit_dir" "$prompts_dir"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ PHASE AUDIT: DISCOVERY                                      │${NC}"
    echo -e "${DIM}  │                                                             │${NC}"
    echo -e "${DIM}  │ An AI-driven audit reviews Phase 1 outputs against the     │${NC}"
    echo -e "${DIM}  │ comprehensive audit library (~2,200 audits).                │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # AUDIT MODE SELECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AUDIT MODE SELECTION${NC}                                        ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${CYAN}Select audit mode:${NC}"
    echo ""
    echo -e "    ${GREEN}[1]${NC} AI-Driven ${DIM}(recommended)${NC}"
    echo -e "        ${DIM}AI recommends audits from 2,200+ library based on context${NC}"
    echo ""
    echo -e "    ${GREEN}[2]${NC} Legacy Dimensions"
    echo -e "        ${DIM}Static 9-dimension audit for Phase 1 Discovery${NC}"
    echo ""
    echo -e "    ${GREEN}[3]${NC} Skip Audit"
    echo -e "        ${DIM}Proceed without audit (not recommended)${NC}"
    echo ""

    read -p "  Mode [1]: " mode_choice
    mode_choice=${mode_choice:-1}

    case "$mode_choice" in
        1)
            _109_ai_driven_audit
            ;;
        2)
            _109_legacy_audit
            ;;
        3)
            echo -e "  ${YELLOW}!${NC} Skipping audit for Phase 1"
            atomic_context_decision "Phase 1 audit skipped by user" "audit"
            ;;
    esac

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# AI-DRIVEN AUDIT (from turbobeest/audits)
# ═══════════════════════════════════════════════════════════════════════════════

_109_ai_driven_audit() {
    # Source the audit library
    source "$ATOMIC_ROOT/lib/audit.sh"

    # Run the AI-driven phase audit
    audit_run_phase 1 "Discovery"

    return $?
}

# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY DIMENSION-BASED AUDIT
# ═══════════════════════════════════════════════════════════════════════════════

_109_legacy_audit() {
    local audit_dir="$ATOMIC_ROOT/.claude/audit"
    local audit_file="$audit_dir/phase-01-audit.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}LEGACY AUDIT (9 Dimensions)${NC}                                 ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Define dimensions
    declare -A dimensions=(
        ["ID-01"]="Corpus Completeness|Are all relevant materials collected?"
        ["ID-02"]="Vision Clarity|Is the project vision clear and actionable?"
        ["ID-03"]="Constraint Definition|Are constraints well-defined and realistic?"
        ["ID-04"]="Approach Viability|Is the selected approach feasible?"
        ["ID-05"]="First Principles Validity|Have assumptions been properly challenged?"
        ["ID-06"]="Stakeholder Coverage|Are all stakeholders identified?"
        ["ID-07"]="Risk Awareness|Are key risks identified and considered?"
        ["ID-08"]="Deliberation Quality|Was the multi-agent discussion productive?"
        ["ID-09"]="Scope Boundaries|Are scope boundaries clear?"
    )

    echo -e "  ${CYAN}Available Dimensions:${NC}"
    echo ""
    for id in $(echo "${!dimensions[@]}" | tr ' ' '\n' | sort); do
        IFS='|' read -r name desc <<< "${dimensions[$id]}"
        echo -e "    ${GREEN}$id${NC}: $name"
        echo -e "         ${DIM}$desc${NC}"
    done
    echo ""

    echo -e "  ${CYAN}Audit Profile:${NC}"
    echo -e "    ${GREEN}[quick]${NC}  Top 5 dimensions (fast)"
    echo -e "    ${GREEN}[custom]${NC} Select specific dimensions"
    echo -e "    ${GREEN}[all]${NC}    All 9 dimensions (thorough)"
    echo ""

    read -p "  Profile [quick]: " audit_profile
    audit_profile=${audit_profile:-quick}

    local selected_dims=()

    case "$audit_profile" in
        quick)
            selected_dims=("ID-01" "ID-02" "ID-04" "ID-07" "ID-09")
            ;;
        custom)
            echo ""
            echo -e "  ${DIM}Enter dimension IDs (space-separated):${NC}"
            read -p "  > " custom_selection
            selected_dims=($custom_selection)
            ;;
        all)
            selected_dims=($(echo "${!dimensions[@]}" | tr ' ' '\n' | sort))
            ;;
    esac

    echo ""
    echo -e "  ${GREEN}✓${NC} Selected ${#selected_dims[@]} dimensions"
    echo ""

    # Execute audit
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}EXECUTING LEGACY AUDIT${NC}                                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Gather phase artifacts with smart truncation
    local artifacts=""
    local artifact_count=0
    local skipped_count=0

    for f in "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE"/*.json "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE"/*.md; do
        [[ -f "$f" ]] || continue

        local filename=$(basename "$f")
        local filesize=$(wc -c < "$f")
        local filelines=$(wc -l < "$f")

        # Skip very large files (>50KB), summarize instead
        if [[ $filesize -gt 51200 ]]; then
            artifacts+="### $filename\n"
            artifacts+="[Large file: ${filelines} lines, $(( filesize / 1024 ))KB - showing structure only]\n"
            if [[ "$f" == *.json ]]; then
                artifacts+="Top-level keys: $(jq -r 'keys | join(", ")' "$f" 2>/dev/null || echo "unable to parse")\n"
            else
                artifacts+="First 20 lines:\n$(head -20 "$f")\n"
            fi
            artifacts+="\n"
            ((skipped_count++))
            continue
        fi

        # Different limits by file type
        local max_lines=150
        [[ "$f" == *.json ]] && max_lines=200  # JSON needs more for structure
        [[ "$filename" == *"log"* ]] && max_lines=100  # Logs can be shorter

        artifacts+="### $filename\n"

        if [[ $filelines -le $max_lines ]]; then
            artifacts+="$(cat "$f")\n"
        else
            artifacts+="$(head -$max_lines "$f")\n"
            artifacts+="\n[TRUNCATED: Showing $max_lines of $filelines lines]\n"
        fi
        artifacts+="\n---\n\n"
        ((artifact_count++))
    done

    [[ $skipped_count -gt 0 ]] && echo -e "  ${DIM}Note: $skipped_count large files summarized${NC}"

    # Build audit prompt
    cat > "$prompts_dir/phase-audit.md" << EOF
# Task: Phase 1 Discovery Audit (Legacy Mode)

You are an **independent quality auditor** with expertise in SDLC gate reviews. Your role is to determine whether Phase 1 (Discovery) outputs are sufficient to proceed to Phase 2 (PRD authoring) - NOT to achieve perfection.

## Your Audit Philosophy

- **Discovery is exploratory** - expect ambiguity and iteration
- **Gate, not grade** - you're checking "sufficient to proceed" not "A+ quality"
- **Evidence-based** - every finding must cite specific artifact content
- **Constructive** - recommendations should be actionable in 1-2 hours

## Artifacts to Review

**Note**: If an expected artifact is missing, note it explicitly. If a file shows [TRUNCATED], evidence may be in omitted content - note this uncertainty.

$artifacts

## Missing Artifact Handling

If critical artifacts are absent (e.g., no dialogue.json, no corpus.json):
- Mark the relevant dimension as WARNING (not CRITICAL) if the gap is recoverable
- Mark as CRITICAL only if PRD authoring would be impossible without this content
- Recommend what minimal content is needed before proceeding

## Dimensions to Audit

$(for dim in "${selected_dims[@]}"; do
    IFS='|' read -r name desc <<< "${dimensions[$dim]}"
    echo "### $dim: $name"
    echo "$desc"
    echo ""
done)

## Scoring Criteria and Thresholds

**PASS** (proceed freely):
- Clear evidence in artifacts supporting the dimension
- Sufficient detail for PRD author to work with
- Example: "Vision statement in dialogue.json specifies problem, audience, and desired outcome"

**WARNING** (proceed with note):
- Partially met OR evidence is ambiguous OR minor gaps exist
- PRD author can work around it or clarify during Phase 2
- Does NOT block progress
- Example: "Constraints mentioned in conversation but not formally captured in synthesis"

**CRITICAL** (must address before proceeding):
- Would cause PRD author to be blocked or make incorrect assumptions
- Missing essential elements that cannot be inferred
- Example: "No vision or problem statement exists - PRD cannot be written"
- **Use sparingly**: Most Discovery gaps are WARNING, not CRITICAL

## Threshold for Proceeding

- **Proceed**: 0 CRITICAL findings
- **Proceed with caution**: 0 CRITICAL + any number of WARNINGs
- **Do not proceed**: 1+ CRITICAL findings

## Calibration Guidelines

- This is Phase 1 (Discovery) - some ambiguity is EXPECTED and acceptable
- Don't mark CRITICAL unless it would genuinely block Phase 2 (PRD authoring)
- Prefer WARNING over CRITICAL for "could be clearer" issues
- PASS doesn't mean perfect - it means "sufficient to proceed"
- Discovery is exploratory; don't expect the precision of later phases

## Example Findings

**GOOD finding (specific, evidenced, actionable):**
{
  "status": "WARNING",
  "finding": "Vision statement exists but lacks measurable success criteria",
  "evidence": "dialogue.json contains vision.core_problem ('reduce deployment time') but synthesis.impact.success_metrics array is empty",
  "recommendation": "Add 2-3 quantifiable success metrics (e.g., 'reduce deployment time from 2 hours to 15 minutes') before PRD phase"
}

**BAD finding (avoid this - vague, no evidence):**
{
  "status": "WARNING",
  "finding": "Could be better",
  "evidence": "Looked at files",
  "recommendation": "Improve it"
}

## Anti-Patterns (avoid these)

- Marking everything PASS without citing specific evidence
- Being overly critical of exploratory content that's naturally ambiguous
- Expecting Phase 1 outputs to have Phase 3 (implementation) precision
- Vague findings without specific artifact/field references
- CRITICAL status for stylistic issues rather than substantive gaps
- Ignoring truncation notices when evidence might be in omitted content

## Output Format

For EACH dimension, provide a finding with specific evidence from the artifacts.

Output as JSON:
{
  "audit_timestamp": "$(date -Iseconds)",
  "audit_mode": "legacy",
  "phase": "1-discovery",
  "dimensions_audited": ${#selected_dims[@]},
  "findings": {
    "ID-XX": {
      "name": "Dimension Name",
      "status": "PASS|WARNING|CRITICAL",
      "finding": "Specific observation about this dimension",
      "evidence": "artifact.json field X contains Y, or 'No evidence found in artifacts'",
      "recommendation": "Specific action if not PASS, or null if PASS"
    }
  },
  "summary": {
    "passed": 0,
    "warnings": 0,
    "critical": 0
  },
  "overall_status": "PASS if no CRITICAL, WARNING if any warnings, CRITICAL if any critical",
  "proceed_recommendation": true,
  "proceed_rationale": "Brief explanation of why it's safe (or not) to proceed to Phase 2"
}

Output ONLY valid JSON. No markdown, no explanation.
EOF

    atomic_waiting "auditor analyzing..."

    local audit_raw="$prompts_dir/audit-raw.json"
    if atomic_invoke "$prompts_dir/phase-audit.md" "$audit_raw" "Phase 1 audit" --model=sonnet; then
        if jq -e . "$audit_raw" &>/dev/null; then
            cp "$audit_raw" "$audit_file"
            atomic_success "Audit complete"
        else
            atomic_warn "Invalid audit output"
            echo '{"overall_status": "WARNING", "summary": {"passed": 0, "warnings": 1, "critical": 0}}' > "$audit_file"
        fi
    else
        atomic_error "Audit failed"
        echo '{"overall_status": "WARNING", "summary": {"passed": 0, "warnings": 1, "critical": 0}, "error": "Audit execution failed"}' > "$audit_file"
    fi

    # Display findings
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AUDIT FINDINGS${NC}                                               ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local passed=$(jq -r '.summary.passed // 0' "$audit_file")
    local warnings=$(jq -r '.summary.warnings // 0' "$audit_file")
    local critical=$(jq -r '.summary.critical // 0' "$audit_file")
    local overall=$(jq -r '.overall_status // "UNKNOWN"' "$audit_file")

    local status_color="${GREEN}"
    [[ "$overall" == "WARNING" ]] && status_color="${YELLOW}"
    [[ "$overall" == "CRITICAL" ]] && status_color="${RED}"

    echo -e "  ${status_color}Overall Status: $overall${NC}"
    echo ""
    echo -e "  ${GREEN}PASSED:${NC}   $passed"
    echo -e "  ${YELLOW}WARNINGS:${NC} $warnings"
    echo -e "  ${RED}CRITICAL:${NC} $critical"
    echo ""

    # Show individual findings
    jq -r '.findings | to_entries[] | "\(.key): \(.value.status) - \(.value.finding)"' "$audit_file" 2>/dev/null | \
    while IFS= read -r finding; do
        if [[ "$finding" == *"PASS"* ]]; then
            echo -e "  ${GREEN}✓${NC} $finding"
        elif [[ "$finding" == *"WARNING"* ]]; then
            echo -e "  ${YELLOW}!${NC} $finding"
        elif [[ "$finding" == *"CRITICAL"* ]]; then
            echo -e "  ${RED}✗${NC} $finding"
        fi
    done

    echo ""

    # Handle warnings/critical
    if [[ $warnings -gt 0 ]] || [[ $critical -gt 0 ]]; then
        echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo -e "  ${CYAN}How would you like to proceed?${NC}"
        echo ""
        echo -e "    ${GREEN}[accept]${NC}    Accept findings and continue"
        echo -e "    ${YELLOW}[address]${NC}   Address issues before continuing"
        echo -e "    ${BLUE}[defer]${NC}     Defer issues to later phases"
        echo ""

        read -p "  Choice [accept]: " review_choice
        review_choice=${review_choice:-accept}

        case "$review_choice" in
            address)
                echo ""
                echo -e "  ${DIM}Please address the issues and run the audit again.${NC}"
                return 1
                ;;
            defer)
                local tmp=$(mktemp)
                jq '.deferred = true | .deferred_by = "human"' "$audit_file" > "$tmp"
                mv "$tmp" "$audit_file"
                echo -e "  ${GREEN}✓${NC} Issues deferred"
                ;;
        esac
    fi

    atomic_context_artifact "phase_audit" "$audit_file" "Phase 1 legacy audit results"
    atomic_context_decision "Legacy audit complete: $passed passed, $warnings warnings, $critical critical" "audit"

    atomic_success "Phase audit complete"

    return 0
}
