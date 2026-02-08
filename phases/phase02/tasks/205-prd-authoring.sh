#!/usr/bin/env bash
# Task 205: PRD Authoring - 12-Generation Sequential with Guardian Validation
# Strategy: 15 sections → 12 generations with guardian validation after each
# Guardian prevents drift via context injection and auto-retry

set -euo pipefail

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

_205_select_guardian_model() {
    # Prefer large-context Ollama models (no CLI truncation)
    local model="nemotron_mini_4b:latest"

    if ollama list 2>/dev/null | grep -q "llama3.3:70b"; then
        model="llama3.3:70b"
    elif ollama list 2>/dev/null | grep -q "qwen2.5:72b"; then
        model="qwen2.5:72b"
    elif ollama list 2>/dev/null | grep -q "devstral"; then
        model="devstral:latest"
    fi

    echo "$model"
}

_205_extract_json_from_markdown() {
    local input_file="$1"
    local output_file="$2"

    if [[ ! -f "$input_file" ]]; then
        return 1
    fi

    # Extract JSON from markdown code fences
    if grep -q '```json' "$input_file"; then
        sed -n '/```json/,/```/p' "$input_file" | sed '1d;$d' > "$output_file"
        return 0
    elif grep -q '```' "$input_file"; then
        # Try generic code fence
        sed -n '/```/,/```/p' "$input_file" | sed '1d;$d' > "$output_file"
        return 0
    else
        # No fences, copy as-is
        cp "$input_file" "$output_file"
        return 0
    fi
}

_205_extract_structured_context() {
    local gen_num="$1"
    local prior_sections_file="$2"
    local output_file="$3"

    # Start with section headings to show structure
    {
        echo "# Structured Context from Prior Sections"
        echo ""
        echo "## Section Headings"
        echo ""
        if [[ -f "$prior_sections_file" ]]; then
            grep -E "^#+ [0-9]+\." "$prior_sections_file" || echo "(No section headings found)"
        else
            echo "(No prior sections yet - this is Generation 1)"
        fi
        echo ""

        # For Gen 2+: Extract tech stack table from Section 2
        if [[ $gen_num -ge 2 && -f "$prior_sections_file" ]]; then
            echo "## Tech Stack (from Section 2)"
            echo ""
            # Extract tech stack table (lines between "### 2.1 Tech Stack" and next ### heading)
            if grep -q "### 2.1 Tech Stack" "$prior_sections_file"; then
                sed -n '/### 2.1 Tech Stack/,/^###/p' "$prior_sections_file" | head -30
            else
                echo "(Tech stack not yet defined)"
            fi
            echo ""
        fi

        # For Gen 3+: Extract FR list (IDs only with titles)
        if [[ $gen_num -ge 3 && -f "$prior_sections_file" ]]; then
            echo "## Feature Requirements List (from Section 3)"
            echo ""
            local fr_count=$(grep -cE "^#### FR-[0-9]{3}:" "$prior_sections_file" 2>/dev/null || echo "0")
            echo "**Total FRs**: $fr_count"
            echo ""
            if [[ $fr_count -gt 0 ]]; then
                grep -E "^#### FR-[0-9]{3}:" "$prior_sections_file"
            else
                echo "(No FRs found yet)"
            fi
            echo ""
        fi

        # For Gen 4+: Extract NFR list (IDs only with titles)
        if [[ $gen_num -ge 4 && -f "$prior_sections_file" ]]; then
            echo "## Non-Functional Requirements List (from Section 4)"
            echo ""
            local nfr_count=$(grep -cE "^\| NFR-[0-9]" "$prior_sections_file" 2>/dev/null || echo "0")
            echo "**Total NFRs**: $nfr_count"
            echo ""
            if [[ $nfr_count -gt 0 ]]; then
                grep "^| NFR-[0-9]" "$prior_sections_file" | head -50
            else
                echo "(No NFRs found yet)"
            fi
            echo ""
        fi

        # For Gen 5+: Extract dependency chain references
        if [[ $gen_num -ge 5 && -f "$prior_sections_file" ]]; then
            echo "## Dependency Chain References (from Section 5)"
            echo ""
            if grep -q "## 5. Logical Dependency Chain" "$prior_sections_file"; then
                # Extract just the layer definitions (first 50 lines of section 5)
                sed -n '/## 5. Logical Dependency Chain/,/^## [0-9]/p' "$prior_sections_file" | head -50
            else
                echo "(Dependency chain not yet defined)"
            fi
            echo ""
        fi

        # For Gen 6+: Extract development phases
        if [[ $gen_num -ge 6 && -f "$prior_sections_file" ]]; then
            echo "## Development Phases (from Section 6)"
            echo ""
            if grep -q "## 6. Development Phases" "$prior_sections_file"; then
                sed -n '/## 6. Development Phases/,/^## [0-9]/p' "$prior_sections_file" | head -40
            else
                echo "(Development phases not yet defined)"
            fi
            echo ""
        fi

        # Always include context window: first 100 + last 50 lines
        if [[ -f "$prior_sections_file" ]]; then
            echo "## Context Window (First 100 + Last 50 Lines)"
            echo ""
            echo "### First 100 Lines"
            echo ""
            head -100 "$prior_sections_file"
            echo ""
            echo "..."
            echo ""
            echo "### Last 50 Lines"
            echo ""
            tail -50 "$prior_sections_file"
        fi
    } > "$output_file"
}

_205_recall_discovery_artifacts() {
    local artifact_type="$1"  # "goals", "features", "nfrs", "approach", "all"
    local output_file="$2"

    # Check if memory system is available
    if ! command -v _memory_recall_local >/dev/null 2>&1; then
        echo "# Memory system not available" > "$output_file"
        return 0
    fi

    # Build appropriate query based on artifact type
    local query_keywords=""
    local section_title=""

    case "$artifact_type" in
        "goals")
            query_keywords="goals objectives pain_points problems user_needs requirements vision"
            section_title="Discovery Goals and User Needs (from Phase 1 Memory)"
            ;;
        "features")
            query_keywords="features functionality capabilities requirements feature_list"
            section_title="Discovery Feature Requirements (from Phase 1 Memory)"
            ;;
        "nfrs")
            query_keywords="performance security reliability scalability availability compliance nfr non_functional"
            section_title="Discovery NFR Hints (from Phase 1 Memory)"
            ;;
        "approach")
            query_keywords="approach architecture technical_stack selected_approach technology tech_stack"
            section_title="Discovery Technical Approach (from Phase 1 Memory)"
            ;;
        "all")
            query_keywords="discovery goals features approach architecture requirements"
            section_title="Complete Discovery Context (from Phase 1 Memory)"
            ;;
        *)
            echo "# Unknown artifact type: $artifact_type" > "$output_file"
            return 1
            ;;
    esac

    # Recall from Phase 1 memory
    {
        echo "## $section_title"
        echo ""

        local recall_result
        recall_result=$(_memory_recall_local "$query_keywords" "1" 2>/dev/null)

        if [[ -n "$recall_result" && "$recall_result" != *"No memories found"* ]]; then
            echo "$recall_result"
        else
            echo "(No $artifact_type found in Phase 1 memory)"
            echo ""
            echo "This is expected if:"
            echo "- Phase 1 (Discovery) was not run"
            echo "- Memory system was disabled during Phase 1"
            echo "- Discovery artifacts were not saved to memory"
        fi

        echo ""
    } > "$output_file"
}

_205_detect_model_context_window() {
    local model_name="$1"

    # Model context window mappings (in tokens)
    case "$model_name" in
        # Claude models (large context)
        *"claude-sonnet"*|*"claude-opus"*|*"claude-3"*)
            echo "200000"  # 200K
            ;;
        # Large context Ollama models
        "llama3.3:70b"|"qwen2.5:72b"|"qwen2.5-coder:32b"|"llama3.1:70b")
            echo "128000"  # 128K
            ;;
        # Medium context Ollama models
        "devstral"*|"codestral"*)
            echo "32000"   # 32K
            ;;
        # Small context Ollama models
        "llama3.1:8b"|"llama3.2:3b"|"nemotron"*|"phi3"*|"gemma"*|"codellama"*)
            echo "8000"    # 8K
            ;;
        # Default: assume medium context
        *)
            echo "32000"   # 32K default
            ;;
    esac
}

_205_get_context_strategy() {
    local context_window="$1"

    # Determine context strategy based on window size
    if [[ $context_window -ge 100000 ]]; then
        echo "full"      # Large context: use full prior sections
    elif [[ $context_window -ge 30000 ]]; then
        echo "structured" # Medium context: use structured extraction
    else
        echo "minimal"    # Small context: headings + IDs only
    fi
}

_205_adaptive_context() {
    local gen_num="$1"
    local prior_sections_file="$2"
    local output_file="$3"
    local model_name="${4:-unknown}"

    # Detect context window and strategy
    local context_window
    context_window=$(_205_detect_model_context_window "$model_name")

    local strategy
    strategy=$(_205_get_context_strategy "$context_window")

    atomic_info "Context strategy: $strategy (model: $model_name, window: $context_window tokens)"

    case "$strategy" in
        "full")
            # Large context: Include full prior sections
            {
                echo "# Prior Sections (Full Content)"
                echo ""
                if [[ -f "$prior_sections_file" ]]; then
                    cat "$prior_sections_file"
                else
                    echo "(No prior sections yet)"
                fi
            } > "$output_file"
            ;;

        "structured")
            # Medium context: Use structured extraction (existing implementation)
            _205_extract_structured_context "$gen_num" "$prior_sections_file" "$output_file"
            ;;

        "minimal")
            # Small context: Headings + IDs only
            {
                echo "# Prior Sections (Minimal Context)"
                echo ""
                echo "## Section Headings"
                echo ""
                if [[ -f "$prior_sections_file" ]]; then
                    grep -E "^#+ [0-9]+\." "$prior_sections_file" || echo "(No headings found)"
                else
                    echo "(No prior sections yet)"
                fi

                # For Gen 3+: Include FR IDs only
                if [[ $gen_num -ge 3 && -f "$prior_sections_file" ]]; then
                    echo ""
                    echo "## FR IDs"
                    local fr_count=$(grep -cE "^#### FR-[0-9]{3}:" "$prior_sections_file" 2>/dev/null || echo "0")
                    echo "**Total**: $fr_count"
                    echo ""
                    grep -oE "FR-[0-9]{3}" "$prior_sections_file" 2>/dev/null | sort -u || echo "(No FRs yet)"
                fi

                # For Gen 4+: Include NFR IDs only
                if [[ $gen_num -ge 4 && -f "$prior_sections_file" ]]; then
                    echo ""
                    echo "## NFR IDs"
                    local nfr_count=$(grep -cE "^\| NFR-[0-9]" "$prior_sections_file" 2>/dev/null || echo "0")
                    echo "**Total**: $nfr_count"
                    echo ""
                    grep -oE "NFR-[0-9]{3}" "$prior_sections_file" 2>/dev/null | sort -u || echo "(No NFRs yet)"
                fi

                # Always include tech stack summary if available (Gen 2+)
                if [[ $gen_num -ge 2 && -f "$prior_sections_file" ]]; then
                    echo ""
                    echo "## Tech Stack (Summary)"
                    echo ""
                    if grep -q "### 2.1 Tech Stack" "$prior_sections_file"; then
                        # Extract just technology names from table
                        sed -n '/### 2.1 Tech Stack/,/^###/p' "$prior_sections_file" | \
                            grep "^|" | grep -v "^| Layer" | \
                            awk -F'|' '{print "- " $3}' | head -10
                    else
                        echo "(Tech stack not yet defined)"
                    fi
                fi
            } > "$output_file"
            ;;
    esac
}

_205_guardian_validate() {
    local gen_num="$1"
    local generated_file="$2"
    local prior_sections_file="$3"
    local guardian_prompt_file="$4"
    local guardian_report_file="$5"
    local guardian_model="$6"
    local project_context="$7"

    atomic_info "Guardian validating Generation $gen_num..."

    # Define expected sections for each generation
    local expected_sections
    local validation_focus
    case "$gen_num" in
        1)
            expected_sections="Sections 0-1 (Vision + Problem Statement, Executive Summary)"
            validation_focus="Vision clarity, executive summary completeness, initial tech stack mentions"
            ;;
        2)
            expected_sections="Sections 0-2 (previous + Technical Architecture)"
            validation_focus="Tech stack defined and locked, component architecture defined, consistency with sections 0-1"
            ;;
        3)
            expected_sections="Sections 0-3 (previous + Feature Requirements)"
            validation_focus="FR sequences start at FR-001 with no gaps, WHEN/THEN format for each FR, tech stack consistency"
            ;;
        4)
            expected_sections="Sections 0-4 (previous + Non-Functional Requirements)"
            validation_focus="NFR sequences start at NFR-001 with no gaps, metrics defined for each NFR, performance/security/reliability covered"
            ;;
        5)
            expected_sections="Sections 0-5 (previous + Logical Dependency Chain)"
            validation_focus="CRITICAL - All FR/NFR IDs cross-referenced exist, dependency graph is acyclic, TaskMaster-ready format"
            ;;
        6)
            expected_sections="Sections 0-6 (previous + Development Phases)"
            validation_focus="Phases are scope-based (not time-based), phases align with dependency chain"
            ;;
        7)
            expected_sections="Sections 0-7 (previous + Code Structure)"
            validation_focus="Directory structure defined, tech stack alignment, proper code organization"
            ;;
        8)
            expected_sections="Sections 0-8 (previous + TDD Strategy)"
            validation_focus="Test-driven development approach clear, test types defined, coverage targets specified"
            ;;
        9)
            expected_sections="Sections 0-9 (previous + Integration Testing)"
            validation_focus="Integration testing strategy defined, testing levels clear, alignment with tech stack"
            ;;
        10)
            expected_sections="Sections 0-11 (previous + Documentation + Operational)"
            validation_focus="Documentation requirements complete, operational readiness criteria defined"
            ;;
        11)
            expected_sections="Sections 0-13 (previous + Risks + Metrics)"
            validation_focus="Minimum 5 risks identified with mitigation, success metrics measurable and specific"
            ;;
        12)
            expected_sections="Sections 0-14 (COMPLETE PRD)"
            validation_focus="Approval section complete, all 15 sections present, final PRD ready"
            ;;
        *)
            expected_sections="Unknown generation"
            validation_focus="General validation"
            ;;
    esac

    # Extract context adaptively based on guardian model capabilities
    local context_file="${guardian_prompt_file%.md}-context.md"
    _205_adaptive_context "$gen_num" "$prior_sections_file" "$context_file" "$guardian_model"

    # Build guardian prompt with generation-specific expectations
    cat > "$guardian_prompt_file" << EOF
# Document Guardian - Generation $gen_num Validation

You are the **document-guardian** validating a PRD generation in a 12-generation sequential workflow.

**IMPORTANT**: This is Generation $gen_num of 12. You are validating ONLY the sections produced in this generation.

## Expected Content for Generation $gen_num

**Sections**: $expected_sections

**Validation Focus**: $validation_focus

## Completed Generation $gen_num

$(cat "$generated_file")

## Prior Sections (for cross-reference validation)

$(cat "$context_file")

## Project Context

$project_context

## Validation Checklist (Generation $gen_num Specific)

EOF

    # Add generation-specific checklist
    case "$gen_num" in
        1)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Section 0 present**: Vision and problem statement clearly defined
2. **Section 1 present**: Executive summary provides project overview
3. **Tech mentions**: Technologies mentioned should align with project context (if provided)
4. **Clarity**: Writing is clear and professional
5. **Completeness**: Both sections are fully written (not truncated or summarized)

**DO NOT expect**: Functional requirements, NFRs, dependency chains, or other sections (these come in later generations)
EOF
            ;;
        2)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Section 2 present**: Technical architecture defined
2. **Tech stack locked**: Technologies explicitly listed (frontend, backend, database, etc.)
3. **Component architecture**: System components and their interactions defined
4. **Consistency**: Tech stack matches mentions in sections 0-1
5. **Completeness**: Architecture section fully detailed

**Extract for context injection**: Locked tech stack list, key architectural decisions
EOF
            ;;
        3)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Section 3 present**: Feature Requirements section exists
2. **FR sequences**: All FRs numbered sequentially starting at FR-001 (no gaps, no duplicates)
3. **WHEN/THEN format**: Each FR has scenario with WHEN (trigger) and THEN (outcome)
4. **Tech alignment**: FR implementations reference locked tech stack from Section 2
5. **Completeness**: All major features covered

**Extract for context injection**: Last FR ID (e.g., FR-024), tech stack usage patterns
EOF
            ;;
        4)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Section 4 present**: Non-Functional Requirements section exists
2. **NFR sequences**: All NFRs numbered sequentially starting at NFR-001 (no gaps, no duplicates)
3. **Metrics defined**: Each NFR has measurable acceptance criteria (e.g., "< 100ms", "99.9% uptime")
4. **Coverage**: Performance, security, reliability, scalability NFRs present
5. **Completeness**: All critical NFRs identified

**Extract for context injection**: Last NFR ID (e.g., NFR-015)
EOF
            ;;
        5)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Section 5 present**: Logical Dependency Chain section exists
2. **CRITICAL - Cross-references**: ALL FR/NFR IDs referenced must exist in prior sections (verify against Sections 3-4)
3. **Acyclic graph**: Dependencies form a valid DAG (no circular dependencies)
4. **TaskMaster format**: Dependency layers properly defined
5. **Completeness**: All FRs/NFRs from Sections 3-4 appear in dependency chain

**This is the most critical validation - broken cross-references will break TaskMaster parsing**
EOF
            ;;
        6)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Section 6 present**: Development Phases section exists
2. **Scope-based phases**: Phases defined by deliverables, NOT time estimates (avoid "Week 1-2" language)
3. **Alignment**: Phases align with dependency chain from Section 5
4. **Progression**: Phases flow logically from foundation to completion
5. **Completeness**: All major milestones captured

**Watch for**: Time-based language (reject if found), misalignment with dependency chain
EOF
            ;;
        7)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Section 7 present**: Code Structure Map section exists
2. **Tech alignment**: Directory structure matches locked tech stack
3. **Completeness**: Code organization fully detailed
4. **Clarity**: Structure is logical and well-organized

**Watch for**: Tech stack drift (introducing new technologies not in Section 2)
EOF
            ;;
        8)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Section 8 present**: TDD Implementation Strategy section exists
2. **Test strategy**: TDD approach clearly defined
3. **Test types**: Unit, integration, and other test types specified
4. **Coverage targets**: Test coverage goals defined
5. **Completeness**: Full testing strategy detailed

**Watch for**: Missing test types, unclear coverage expectations
EOF
            ;;
        9)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Section 9 present**: Integration Testing Strategy section exists
2. **Integration approach**: Clear integration testing methodology
3. **Testing levels**: Component, system, and end-to-end tests defined
4. **Tech alignment**: Testing approach uses locked tech stack
5. **Completeness**: Integration strategy fully detailed

**Watch for**: Inconsistency with Section 8 TDD strategy
EOF
            ;;
        10)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Sections 10-11 present**: Documentation Requirements, Operational Readiness
2. **Documentation complete**: All documentation types defined
3. **Operational criteria**: Readiness criteria clearly specified
4. **Completeness**: Both sections fully detailed

**Watch for**: Missing critical documentation types or operational criteria
EOF
            ;;
        11)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Sections 12-13 present**: Risks and Assumptions, Success Metrics
2. **Minimum 5 risks**: At least 5 risks with mitigation strategies
3. **Measurable metrics**: Specific, quantifiable success metrics
4. **Coverage**: Technical and business risks covered
5. **Completeness**: Both sections fully detailed

**This is critical - risks and metrics drive project success**
EOF
            ;;
        12)
            cat >> "$guardian_prompt_file" << 'EOF'
1. **Section 14 present**: Approval and Sign-off section exists
2. **Stakeholder section**: Stakeholder sign-off table defined
3. **Completeness**: This is the final generation - PRD should now be complete (15 sections total)
4. **Format**: Proper closing with generation metadata

**This is the final validation before assembly**
EOF
            ;;
    esac

    cat >> "$guardian_prompt_file" << 'EOF'

## Output Format

Return JSON only (no markdown fences):

{
  "validation": {
    "status": "pass|warn|fail",
    "drift_detected": true|false,
    "issues": [
      {
        "severity": "critical|warning|info",
        "category": "tech_stack|id_sequence|cross_reference|format|completeness",
        "message": "Description of issue",
        "location": "Section X, FR-YYY",
        "recommendation": "How to fix"
      }
    ]
  },
  "context_injection": {
    "reminders": [
      "Specific reminders for next generation (tech stack, last IDs, key decisions)"
    ],
    "constraints": [
      "Hard constraints that must be followed"
    ],
    "watch_for": [
      "Common pitfalls to avoid in next generation"
    ]
  }
}
EOF

    # Invoke guardian with Ollama (no CLI truncation)
    if ! atomic_invoke "$guardian_prompt_file" "$guardian_report_file" "Guardian: Gen $gen_num" \
        --provider=ollama --model="$guardian_model" --format=json --timeout=180; then
        atomic_warn "Guardian invocation failed"
        return 2  # Unknown status
    fi

    # Extract JSON from markdown fences
    local clean_report="${guardian_report_file}.clean"
    if _205_extract_json_from_markdown "$guardian_report_file" "$clean_report"; then
        mv "$clean_report" "$guardian_report_file"
    fi

    # Parse validation status
    local status
    status=$(jq -r '.validation.status // "unknown"' "$guardian_report_file" 2>/dev/null || echo "unknown")

    case "$status" in
        "pass")
            atomic_success "Guardian: PASS"
            return 0
            ;;
        "warn")
            atomic_warn "Guardian: WARNINGS detected"
            jq -r '.validation.issues[]? | "  - [\(.severity)] \(.message)"' "$guardian_report_file" 2>/dev/null || true
            return 1
            ;;
        "fail")
            atomic_error "Guardian: FAIL - Critical drift detected"
            jq -r '.validation.issues[]? | "  - [\(.severity)] \(.message)"' "$guardian_report_file" 2>/dev/null || true
            return 2
            ;;
        *)
            atomic_warn "Guardian: Unknown status ($status)"
            return 2
            ;;
    esac
}

_205_generate_with_retry() {
    local gen_num="$1"
    local prompt_file="$2"
    local output_file="$3"
    local prior_sections_file="$4"
    local guardian_prompt_file="$5"
    local guardian_report_file="$6"
    local guardian_model="$7"
    local project_context="$8"
    local description="$9"

    local max_retries=2
    local attempt=1

    while [[ $attempt -le $max_retries ]]; do
        atomic_info "Generation $gen_num - Attempt $attempt/$max_retries"

        # Generate section(s)
        if ! atomic_invoke "$prompt_file" "$output_file" "$description" --timeout=1200; then
            atomic_error "Generation $gen_num failed"
            return 1
        fi

        # Skip guardian validation if ATOMIC_SKIP_GUARDIAN is set
        if [[ "${ATOMIC_SKIP_GUARDIAN:-false}" == "true" ]]; then
            atomic_info "Guardian validation skipped (ATOMIC_SKIP_GUARDIAN=true)"
            return 0
        fi

        # Guardian validation
        local guardian_status
        _205_guardian_validate "$gen_num" "$output_file" "$prior_sections_file" \
            "$guardian_prompt_file" "$guardian_report_file" "$guardian_model" "$project_context"
        guardian_status=$?

        case $guardian_status in
            0)
                # Pass - continue
                atomic_success "Generation $gen_num approved by guardian"
                return 0
                ;;
            1)
                # Warn - check if retry needed
                if [[ $attempt -lt $max_retries ]]; then
                    # Extract corrections from guardian report
                    local corrections
                    corrections=$(jq -r '.validation.issues[]? | "- [\(.severity)] \(.message) → \(.recommendation)"' \
                        "$guardian_report_file" 2>/dev/null || echo "General quality issues detected")

                    # Inject corrections into retry prompt
                    cat >> "$prompt_file" << EOF

---

## CORRECTIONS REQUIRED (from document-guardian validation)

The previous generation had these issues:

$corrections

Please regenerate with these corrections applied. Maintain all existing content but fix the specific issues mentioned above.
EOF
                    atomic_info "Retrying Generation $gen_num with corrections..."
                    ((attempt++))
                else
                    atomic_warn "Max retries reached for Generation $gen_num, proceeding with warnings"
                    return 0
                fi
                ;;
            2)
                # Fail - critical drift
                atomic_error "Generation $gen_num has CRITICAL drift - human intervention required"
                return 1
                ;;
        esac
    done

    # Should not reach here
    return 1
}

_205_build_context() {
    local gen_num="$1"
    local output_dir="$2"
    local project_name="$3"
    local project_type="$4"
    local tech_stack="$5"
    local current_date="$6"

    local context_file="$output_dir/prompts/context/cumulative-gen-${gen_num}.md"
    mkdir -p "$(dirname "$context_file")"

    # Start with project context
    cat > "$context_file" << EOF
# Project Context for Generation $gen_num

**Name**: $project_name
**Type**: $project_type
**Date**: $current_date

## Tech Stack
$tech_stack

EOF

    # Append guardian context injections from prior generations
    local has_guardian_context=false
    for ((i=1; i<gen_num; i++)); do
        local report="$output_dir/prompts/guardian-gen-${i}-report.json"
        if [[ -f "$report" ]]; then
            has_guardian_context=true
            echo "## Guardian Context from Generation $i" >> "$context_file"
            echo "" >> "$context_file"

            echo "**Reminders**:" >> "$context_file"
            jq -r '.context_injection.reminders[]? | "- \(.)"' "$report" 2>/dev/null >> "$context_file" || true
            echo "" >> "$context_file"

            echo "**Constraints**:" >> "$context_file"
            jq -r '.context_injection.constraints[]? | "- \(.)"' "$report" 2>/dev/null >> "$context_file" || true
            echo "" >> "$context_file"

            echo "**Watch For**:" >> "$context_file"
            jq -r '.context_injection.watch_for[]? | "- \(.)"' "$report" 2>/dev/null >> "$context_file" || true
            echo "" >> "$context_file"
        fi
    done

    if [[ "$has_guardian_context" == "false" && $gen_num -gt 1 ]]; then
        echo "No guardian context available from prior generations." >> "$context_file"
        echo "" >> "$context_file"
    fi

    # Append prior section content (truncated)
    if [[ $gen_num -gt 1 ]]; then
        echo "## Prior Sections Summary" >> "$context_file"
        echo "" >> "$context_file"

        for ((i=1; i<gen_num; i++)); do
            local section_file="$output_dir/prompts/gen-${i}-sections.md"
            if [[ -f "$section_file" ]]; then
                echo "### From Generation $i (excerpt)" >> "$context_file"
                # First 50 lines and last 30 lines (window strategy)
                head -50 "$section_file" >> "$context_file"
                echo "" >> "$context_file"
                echo "..." >> "$context_file"
                echo "" >> "$context_file"
                tail -30 "$section_file" >> "$context_file"
                echo "" >> "$context_file"
            fi
        done
    fi

    echo "$context_file"
}

_205_assemble_prior_sections() {
    local gen_num="$1"
    local output_dir="$2"
    local prior_sections_file="$3"

    # Concatenate all prior generation outputs
    > "$prior_sections_file"

    for ((i=1; i<gen_num; i++)); do
        local section_file="$output_dir/prompts/gen-${i}-sections.md"
        if [[ -f "$section_file" ]]; then
            cat "$section_file" >> "$prior_sections_file"
            echo "" >> "$prior_sections_file"
            echo "---" >> "$prior_sections_file"
            echo "" >> "$prior_sections_file"
        fi
    done
}

# =============================================================================
# MAIN TASK
# =============================================================================

task_205_prd_authoring() {
    atomic_step "PRD Authoring (12-Generation Sequential + Guardian)"

    local output_dir="$ATOMIC_OUTPUT_DIR/2-prd"
    local prompts_dir="$output_dir/prompts"
    local context_dir="$prompts_dir/context"
    local prd_file="$output_dir/PRD.md"

    mkdir -p "$prompts_dir" "$context_dir"

    # =========================================================================
    # UAT MODE BYPASS
    # =========================================================================
    if [[ "${ATOMIC_UAT_MODE:-false}" == "true" ]]; then
        atomic_info "UAT mode: Creating minimal PRD..."

        mkdir -p docs/prd

        # Create minimal but valid PRD with 10+ sections
        cat > docs/prd/PRD.md << 'EOF'
# Product Requirements Document (PRD)

## 0. Vision + Problem Statement

This project aims to solve a critical problem in the target domain through innovative technology solutions.

## 1. Executive Summary

This is a minimal viable PRD created for UAT testing purposes. It contains all required sections but with simplified content.

## 2. Technical Architecture

### 2.1 Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Node.js | Modern runtime |
| Database | PostgreSQL | Relational data |
| Frontend | React | UI framework |

## 3. Feature Requirements

### FR-001: Core Feature
**Priority**: SHALL
**WHEN**: User accesses the system
**THEN**: System responds correctly

### FR-002: Secondary Feature
**Priority**: SHOULD
**WHEN**: User performs action
**THEN**: Expected outcome occurs

## 4. Non-Functional Requirements

| ID | Category | Requirement | Metric | Priority |
|----|----------|-------------|--------|----------|
| NFR-001 | Performance | Response time | < 200ms | SHALL |

## 5. Logical Dependency Chain

### Layer 0: Foundation
- FR-001: Core Feature
- NFR-001: Performance baseline

### Layer 1: Enhancement
- FR-002: Secondary Feature (depends on FR-001)

## 6. Development Phases

### Phase 1: Foundation
**Scope**: Core infrastructure and FR-001
**Deliverables**: FR-001, NFR-001

## 7. Code Structure Map

```
src/
  core/
  utils/
tests/
  unit/
  integration/
```

## 8. TDD Implementation Strategy

Red-Green-Refactor approach with unit tests covering all features.

## 9. Integration Testing Strategy

End-to-end tests using standard testing frameworks.

## 10. Documentation Requirements

- README
- API documentation
- User guides

---

*Generated by ATOMIC CLAUDE - UAT Mode*
*Date: $(date +%Y-%m-%d)*
EOF

        # Create minimal generation log
        cat > "$output_dir/prd-generation-log.json" << EOF
{
  "mode": "uat",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "sections_generated": 10,
  "validation": "minimal"
}
EOF

        atomic_success "UAT mode: Minimal PRD created at docs/prd/PRD.md"
        return 0
    fi

    # -------------------------------------------------------------------------
    # NORMAL MODE - Continue with full 12-generation PRD authoring
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Load project context
    # -------------------------------------------------------------------------

    local project_config="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
    local interview_file="$output_dir/prd-interview.json"
    local discovery_closeout="$ATOMIC_OUTPUT_DIR/1-discovery/closeout.md"

    if [[ ! -f "$project_config" ]]; then
        atomic_error "Project config not found: $project_config"
        return 1
    fi

    local project_name
    local project_type
    local tech_stack
    project_name=$(jq -r '.name // "unknown"' "$project_config")
    project_type=$(jq -r '.type // "webapp"' "$project_config")
    tech_stack=$(jq -r '.tech_stack // "not specified"' "$project_config")

    atomic_info "Project: $project_name ($project_type)"
    atomic_info "Tech stack: $tech_stack"

    # Load interview data if available
    local interview_context=""
    if [[ -f "$interview_file" ]]; then
        interview_context=$(cat "$interview_file")
    fi

    # Load discovery closeout if available
    local discovery_context=""
    if [[ -f "$discovery_closeout" ]]; then
        discovery_context=$(head -100 "$discovery_closeout")
    fi

    local current_date
    current_date=$(date +%Y-%m-%d)

    # Select guardian model
    local guardian_model
    guardian_model=$(_205_select_guardian_model)
    atomic_info "Guardian model: $guardian_model"

    # Project context for guardian
    local project_context
    project_context=$(cat << EOF
**Project**: $project_name
**Type**: $project_type
**Tech Stack**: $tech_stack
**Date**: $current_date
EOF
)

    # -------------------------------------------------------------------------
    # GENERATION 1: Sections 0-1 (Vision + Executive Summary)
    # -------------------------------------------------------------------------

    atomic_info "Generation 1: Sections 0-1 (Vision + Executive Summary)"

    local gen1_context
    gen1_context=$(_205_build_context 1 "$output_dir" "$project_name" "$project_type" "$tech_stack" "$current_date")

    # Recall discovery goals from memory
    local discovery_memory_file="$prompts_dir/discovery-memory-goals.md"
    atomic_info "Recalling discovery goals from memory..."
    _205_recall_discovery_artifacts "goals" "$discovery_memory_file"

    cat > "$prompts_dir/gen-1-prompt.md" << 'EOF_GEN1'
# PRD Generation 1: Vision + Executive Summary

You are the **prd-writer** agent generating sections 0-1 of a 15-section Product Requirements Document.

## Task

Generate **Sections 0-1**:
- **Section 0**: Vision + Problem Statement
- **Section 1**: Executive Summary

## Context

EOF_GEN1
    cat "$gen1_context" >> "$prompts_dir/gen-1-prompt.md"

    cat >> "$prompts_dir/gen-1-prompt.md" << 'EOF_GEN1_2'

## Interview Data

EOF_GEN1_2
    echo "$interview_context" >> "$prompts_dir/gen-1-prompt.md"

    cat >> "$prompts_dir/gen-1-prompt.md" << 'EOF_GEN1_3'

## Discovery Context

EOF_GEN1_3
    echo "$discovery_context" >> "$prompts_dir/gen-1-prompt.md"

    # Inject discovery memory (goals and user needs from Phase 1)
    echo "" >> "$prompts_dir/gen-1-prompt.md"
    cat "$discovery_memory_file" >> "$prompts_dir/gen-1-prompt.md"

    cat >> "$prompts_dir/gen-1-prompt.md" << 'EOF_GEN1_4'

## Instructions

1. Follow the standard 15-section PRD template
2. Section 0 should capture the vision and problem statement concisely
3. Section 1 should provide an executive summary of the project
4. Use clear, professional language
5. Mention key technologies from the tech stack where relevant

## Output Format

Output ONLY the markdown content for sections 0-1. Start with:

```markdown
# Product Requirements Document (PRD)

## 0. Vision + Problem Statement

...
```

**CRITICAL**: Output complete sections. Do NOT summarize or truncate.
EOF_GEN1_4

    local gen1_output="$prompts_dir/gen-1-sections.md"
    local gen1_prior="$prompts_dir/gen-1-prior.md"
    local gen1_guardian_prompt="$prompts_dir/guardian-gen-1-prompt.md"
    local gen1_guardian_report="$prompts_dir/guardian-gen-1-report.json"

    # No prior sections for Gen 1
    touch "$gen1_prior"

    if ! _205_generate_with_retry 1 "$prompts_dir/gen-1-prompt.md" "$gen1_output" "$gen1_prior" \
        "$gen1_guardian_prompt" "$gen1_guardian_report" "$guardian_model" "$project_context" \
        "PRD Gen 1: Vision + Executive"; then
        atomic_error "Generation 1 failed"
        return 1
    fi

    # Save to memory
    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_1" "$(cat "$gen1_output")" 2>/dev/null || true
    fi

    atomic_success "Generation 1 complete: $(wc -w < "$gen1_output") words"

    # -------------------------------------------------------------------------
    # GENERATION 2: Section 2 (Technical Architecture)
    # -------------------------------------------------------------------------

    atomic_info "Generation 2: Section 2 (Technical Architecture)"

    local gen2_context
    gen2_context=$(_205_build_context 2 "$output_dir" "$project_name" "$project_type" "$tech_stack" "$current_date")

    local gen2_prior="$prompts_dir/gen-2-prior.md"
    _205_assemble_prior_sections 2 "$output_dir" "$gen2_prior"

    # Recall technical approach from memory
    local approach_memory_file="$prompts_dir/discovery-memory-approach.md"
    atomic_info "Recalling technical approach from memory..."
    _205_recall_discovery_artifacts "approach" "$approach_memory_file"

    cat > "$prompts_dir/gen-2-prompt.md" << 'EOF_GEN2'
# PRD Generation 2: Technical Architecture

You are the **prd-writer** agent continuing the PRD.

## Task

Generate **Section 2**: Technical Architecture

This is a CRITICAL section where you LOCK IN the tech stack. All subsequent sections must use only the technologies specified here.

## Context

EOF_GEN2
    cat "$gen2_context" >> "$prompts_dir/gen-2-prompt.md"

    cat >> "$prompts_dir/gen-2-prompt.md" << 'EOF_GEN2_2'

## Prior Sections

EOF_GEN2_2
    head -100 "$gen2_prior" >> "$prompts_dir/gen-2-prompt.md"

    # Inject discovery memory (technical approach from Phase 1)
    echo "" >> "$prompts_dir/gen-2-prompt.md"
    cat "$approach_memory_file" >> "$prompts_dir/gen-2-prompt.md"

    cat >> "$prompts_dir/gen-2-prompt.md" << 'EOF_GEN2_3'

## Instructions

1. Create a comprehensive technical architecture section
2. Define the tech stack in a table format (Layer | Technology | Rationale)
3. Use ONLY technologies from the project tech stack
4. Define system components and their relationships
5. This locks in the tech stack for all remaining sections

## Output Format

Output ONLY the markdown content for section 2. Start with:

```markdown
## 2. Technical Architecture

...
```

**CRITICAL**: Output complete section. Do NOT summarize or truncate.
EOF_GEN2_3

    local gen2_output="$prompts_dir/gen-2-sections.md"
    local gen2_guardian_prompt="$prompts_dir/guardian-gen-2-prompt.md"
    local gen2_guardian_report="$prompts_dir/guardian-gen-2-report.json"

    if ! _205_generate_with_retry 2 "$prompts_dir/gen-2-prompt.md" "$gen2_output" "$gen2_prior" \
        "$gen2_guardian_prompt" "$gen2_guardian_report" "$guardian_model" "$project_context" \
        "PRD Gen 2: Technical Architecture"; then
        atomic_error "Generation 2 failed"
        return 1
    fi

    # Extract and lock tech stack
    local tech_stack_locked
    tech_stack_locked=$(grep -A 20 "### 2.1 Tech Stack\|## 2.1 Tech Stack" "$gen2_output" | \
        grep "^|" | grep -v "^| Layer" | \
        awk -F'|' '{print $3}' | tr '\n' ', ' | sed 's/, $//' || echo "$tech_stack")

    if [[ -n "$tech_stack_locked" ]]; then
        atomic_info "Tech stack locked: $tech_stack_locked"
        project_context=$(cat << EOF
**Project**: $project_name
**Type**: $project_type
**Tech Stack (LOCKED)**: $tech_stack_locked
**Date**: $current_date
EOF
)
        if command -v _memory_save_local >/dev/null 2>&1; then
            _memory_save_local "2" "205" "tech_stack_locked" "$tech_stack_locked" 2>/dev/null || true
        fi
    fi

    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_2" "$(cat "$gen2_output")" 2>/dev/null || true
    fi

    atomic_success "Generation 2 complete: $(wc -w < "$gen2_output") words"

    # -------------------------------------------------------------------------
    # GENERATION 3: Section 3 (Feature Requirements)
    # -------------------------------------------------------------------------

    atomic_info "Generation 3: Section 3 (Feature Requirements)"

    local gen3_context
    gen3_context=$(_205_build_context 3 "$output_dir" "$project_name" "$project_type" "$tech_stack_locked" "$current_date")

    local gen3_prior="$prompts_dir/gen-3-prior.md"
    _205_assemble_prior_sections 3 "$output_dir" "$gen3_prior"

    # Recall feature requirements from memory
    local features_memory_file="$prompts_dir/discovery-memory-features.md"
    atomic_info "Recalling feature requirements from memory..."
    _205_recall_discovery_artifacts "features" "$features_memory_file"

    cat > "$prompts_dir/gen-3-prompt.md" << 'EOF_GEN3'
# PRD Generation 3: Feature Requirements

You are the **prd-writer** agent continuing the PRD.

## Task

Generate **Section 3**: Feature Requirements

This section defines all functional requirements using OpenSpec format (WHEN/THEN scenarios).

## Context

EOF_GEN3
    cat "$gen3_context" >> "$prompts_dir/gen-3-prompt.md"

    cat >> "$prompts_dir/gen-3-prompt.md" << 'EOF_GEN3_2'

## Prior Sections (excerpt)

EOF_GEN3_2
    head -150 "$gen3_prior" >> "$prompts_dir/gen-3-prompt.md"
    echo "" >> "$prompts_dir/gen-3-prompt.md"
    echo "..." >> "$prompts_dir/gen-3-prompt.md"
    echo "" >> "$prompts_dir/gen-3-prompt.md"
    tail -100 "$gen3_prior" >> "$prompts_dir/gen-3-prompt.md"

    # Inject discovery memory (feature requirements from Phase 1)
    echo "" >> "$prompts_dir/gen-3-prompt.md"
    cat "$features_memory_file" >> "$prompts_dir/gen-3-prompt.md"

    cat >> "$prompts_dir/gen-3-prompt.md" << 'EOF_GEN3_3'

## Instructions

1. Define all functional requirements with sequential IDs: FR-001, FR-002, FR-003, etc.
2. Use RFC 2119 keywords: SHALL (must have), SHOULD (important), MAY (optional)
3. Use OpenSpec WHEN/THEN format for each FR
4. Maintain tech stack consistency (use only locked tech stack)
5. Aim for 10-20 functional requirements

## Output Format

Output ONLY the markdown content for section 3. Start with:

```markdown
## 3. Feature Requirements

### 3.1 Core Requirements

#### FR-001: [Title]
**Priority**: SHALL
**WHEN**: [trigger condition]
**THEN**: [expected behavior]
...
```

**CRITICAL**: Output complete section with all FRs. Do NOT summarize or truncate.
EOF_GEN3_3

    local gen3_output="$prompts_dir/gen-3-sections.md"
    local gen3_guardian_prompt="$prompts_dir/guardian-gen-3-prompt.md"
    local gen3_guardian_report="$prompts_dir/guardian-gen-3-report.json"

    if ! _205_generate_with_retry 3 "$prompts_dir/gen-3-prompt.md" "$gen3_output" "$gen3_prior" \
        "$gen3_guardian_prompt" "$gen3_guardian_report" "$guardian_model" "$project_context" \
        "PRD Gen 3: Feature Requirements"; then
        atomic_error "Generation 3 failed"
        return 1
    fi

    # Extract last FR ID
    local last_fr_id
    last_fr_id=$(grep -o "FR-[0-9]\{3\}" "$gen3_output" | sort -u | tail -1 || echo "FR-000")
    atomic_info "Last FR ID: $last_fr_id"

    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_3" "$(cat "$gen3_output")" 2>/dev/null || true
        _memory_save_local "2" "205" "last_fr_id" "$last_fr_id" 2>/dev/null || true
    fi

    atomic_success "Generation 3 complete: $(wc -w < "$gen3_output") words"

    # -------------------------------------------------------------------------
    # GENERATION 4: Section 4 (Non-Functional Requirements)
    # -------------------------------------------------------------------------

    atomic_info "Generation 4: Section 4 (Non-Functional Requirements)"

    local gen4_context
    gen4_context=$(_205_build_context 4 "$output_dir" "$project_name" "$project_type" "$tech_stack_locked" "$current_date")

    local gen4_prior="$prompts_dir/gen-4-prior.md"
    _205_assemble_prior_sections 4 "$output_dir" "$gen4_prior"

    # Recall NFR hints from memory
    local nfrs_memory_file="$prompts_dir/discovery-memory-nfrs.md"
    atomic_info "Recalling NFR hints from memory..."
    _205_recall_discovery_artifacts "nfrs" "$nfrs_memory_file"

    cat > "$prompts_dir/gen-4-prompt.md" << 'EOF_GEN4'
# PRD Generation 4: Non-Functional Requirements

You are the **prd-writer** agent continuing the PRD.

## Task

Generate **Section 4**: Non-Functional Requirements

## Context

EOF_GEN4
    cat "$gen4_context" >> "$prompts_dir/gen-4-prompt.md"

    cat >> "$prompts_dir/gen-4-prompt.md" << 'EOF_GEN4_2'

## Prior Sections (excerpt)

EOF_GEN4_2
    tail -150 "$gen4_prior" >> "$prompts_dir/gen-4-prompt.md"

    # Inject discovery memory (NFR hints from Phase 1)
    echo "" >> "$prompts_dir/gen-4-prompt.md"
    cat "$nfrs_memory_file" >> "$prompts_dir/gen-4-prompt.md"

    cat >> "$prompts_dir/gen-4-prompt.md" << 'EOF_GEN4_3'

## Instructions

1. Define NFRs with sequential IDs: NFR-001, NFR-002, etc.
2. Include specific, measurable metrics (not "fast" or "responsive")
3. Cover: performance, security, reliability, scalability, usability
4. Use RFC 2119 keywords (SHALL/SHOULD/MAY)
5. Aim for 8-15 NFRs

## Output Format

Output ONLY the markdown content for section 4. Start with:

```markdown
## 4. Non-Functional Requirements

| ID | Category | Requirement | Metric | Priority |
|----|----------|-------------|--------|----------|
| NFR-001 | Performance | ... | < 200ms response time | SHALL |
...
```

**CRITICAL**: Output complete section. Do NOT summarize or truncate.
EOF_GEN4_3

    local gen4_output="$prompts_dir/gen-4-sections.md"
    local gen4_guardian_prompt="$prompts_dir/guardian-gen-4-prompt.md"
    local gen4_guardian_report="$prompts_dir/guardian-gen-4-report.json"

    if ! _205_generate_with_retry 4 "$prompts_dir/gen-4-prompt.md" "$gen4_output" "$gen4_prior" \
        "$gen4_guardian_prompt" "$gen4_guardian_report" "$guardian_model" "$project_context" \
        "PRD Gen 4: Non-Functional Requirements"; then
        atomic_error "Generation 4 failed"
        return 1
    fi

    # Extract last NFR ID
    local last_nfr_id
    last_nfr_id=$(grep -o "NFR-[0-9]\{3\}" "$gen4_output" | sort -u | tail -1 || echo "NFR-000")
    atomic_info "Last NFR ID: $last_nfr_id"

    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_4" "$(cat "$gen4_output")" 2>/dev/null || true
        _memory_save_local "2" "205" "last_nfr_id" "$last_nfr_id" 2>/dev/null || true
    fi

    atomic_success "Generation 4 complete: $(wc -w < "$gen4_output") words"

    # -------------------------------------------------------------------------
    # GENERATION 5: Section 5 (Logical Dependency Chain) - CRITICAL
    # -------------------------------------------------------------------------

    atomic_info "Generation 5: Section 5 (Logical Dependency Chain) - CRITICAL for TaskMaster"

    local gen5_context
    gen5_context=$(_205_build_context 5 "$output_dir" "$project_name" "$project_type" "$tech_stack_locked" "$current_date")

    local gen5_prior="$prompts_dir/gen-5-prior.md"
    _205_assemble_prior_sections 5 "$output_dir" "$gen5_prior"

    cat > "$prompts_dir/gen-5-prompt.md" << 'EOF_GEN5'
# PRD Generation 5: Logical Dependency Chain

You are the **prd-writer** agent continuing the PRD.

## Task

Generate **Section 5**: Logical Dependency Chain

**CRITICAL**: This section is essential for TaskMaster. It defines the dependency graph for all requirements.

## Context

EOF_GEN5
    cat "$gen5_context" >> "$prompts_dir/gen-5-prompt.md"

    cat >> "$prompts_dir/gen-5-prompt.md" << 'EOF_GEN5_2'

## Prior Sections (excerpt - focus on FR/NFR definitions)

EOF_GEN5_2
    # Extract FR/NFR sections specifically
    grep -A 5 "^#### FR-\|^| NFR-" "$gen5_prior" | head -200 >> "$prompts_dir/gen-5-prompt.md"

    cat >> "$prompts_dir/gen-5-prompt.md" << 'EOF_GEN5_3'

## Instructions

1. Reference ALL FRs and NFRs defined in sections 3-4
2. Organize into dependency layers (Layer 0 = no dependencies, Layer 1 = depends on Layer 0, etc.)
3. Cross-reference every FR/NFR by ID
4. Ensure acyclic dependency graph (no circular dependencies)
5. Validate that all FR/NFR IDs exist in prior sections

## Output Format

Output ONLY the markdown content for section 5. Start with:

```markdown
## 5. Logical Dependency Chain

### Layer 0: Foundation (No Dependencies)
- FR-001: [description]
- FR-002: [description]
- NFR-001: [description]

### Layer 1: Core Features (Depends on Layer 0)
- FR-003: [description] (depends on FR-001, FR-002)
...
```

**CRITICAL**: Output complete section with ALL FR/NFR cross-references. Do NOT summarize or truncate.
EOF_GEN5_3

    local gen5_output="$prompts_dir/gen-5-sections.md"
    local gen5_guardian_prompt="$prompts_dir/guardian-gen-5-prompt.md"
    local gen5_guardian_report="$prompts_dir/guardian-gen-5-report.json"

    # Override project context with critical validation note
    local gen5_project_context
    gen5_project_context=$(cat << EOF
**Project**: $project_name
**Type**: $project_type
**Tech Stack (LOCKED)**: $tech_stack_locked
**Last FR ID**: $last_fr_id
**Last NFR ID**: $last_nfr_id
**Date**: $current_date

**CRITICAL VALIDATION**: This section MUST reference all FRs ($last_fr_id) and NFRs ($last_nfr_id).
Any missing or invalid cross-references will break TaskMaster compatibility.
EOF
)

    if ! _205_generate_with_retry 5 "$prompts_dir/gen-5-prompt.md" "$gen5_output" "$gen5_prior" \
        "$gen5_guardian_prompt" "$gen5_guardian_report" "$guardian_model" "$gen5_project_context" \
        "PRD Gen 5: Logical Dependency Chain"; then
        atomic_error "Generation 5 failed - CRITICAL section incomplete"
        return 1
    fi

    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_5" "$(cat "$gen5_output")" 2>/dev/null || true
    fi

    atomic_success "Generation 5 complete: $(wc -w < "$gen5_output") words"

    # -------------------------------------------------------------------------
    # GENERATION 6: Section 6 (Development Phases)
    # -------------------------------------------------------------------------

    atomic_info "Generation 6: Section 6 (Development Phases)"

    local gen6_context
    gen6_context=$(_205_build_context 6 "$output_dir" "$project_name" "$project_type" "$tech_stack_locked" "$current_date")

    local gen6_prior="$prompts_dir/gen-6-prior.md"
    _205_assemble_prior_sections 6 "$output_dir" "$gen6_prior"

    cat > "$prompts_dir/gen-6-prompt.md" << 'EOF_GEN6'
# PRD Generation 6: Development Phases

You are the **prd-writer** agent continuing the PRD.

## Task

Generate **Section 6**: Development Phases

## Context

EOF_GEN6
    cat "$gen6_context" >> "$prompts_dir/gen-6-prompt.md"

    cat >> "$prompts_dir/gen-6-prompt.md" << 'EOF_GEN6_2'

## Prior Sections (excerpt - focus on dependency layers)

EOF_GEN6_2
    tail -200 "$gen6_prior" >> "$prompts_dir/gen-6-prompt.md"

    cat >> "$prompts_dir/gen-6-prompt.md" << 'EOF_GEN6_3'

## Instructions

1. Define development phases based on SCOPE, not time
2. Align phases with dependency layers from Section 5
3. Each phase should have clear deliverables (reference FRs/NFRs)
4. Typical structure: Foundation → Core Features → Advanced Features → Polish
5. No time estimates (scope-based only)

## Output Format

Output ONLY the markdown content for section 6. Start with:

```markdown
## 6. Development Phases

### Phase 1: Foundation
**Scope**: [description]
**Deliverables**:
- FR-001, FR-002, NFR-001
...
```

**CRITICAL**: Output complete section. Do NOT summarize or truncate.
EOF_GEN6_3

    local gen6_output="$prompts_dir/gen-6-sections.md"
    local gen6_guardian_prompt="$prompts_dir/guardian-gen-6-prompt.md"
    local gen6_guardian_report="$prompts_dir/guardian-gen-6-report.json"

    if ! _205_generate_with_retry 6 "$prompts_dir/gen-6-prompt.md" "$gen6_output" "$gen6_prior" \
        "$gen6_guardian_prompt" "$gen6_guardian_report" "$guardian_model" "$project_context" \
        "PRD Gen 6: Development Phases"; then
        atomic_error "Generation 6 failed"
        return 1
    fi

    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_6" "$(cat "$gen6_output")" 2>/dev/null || true
    fi

    atomic_success "Generation 6 complete: $(wc -w < "$gen6_output") words"

    # -------------------------------------------------------------------------
    # GENERATION 7: Section 7 (Code Structure)
    # -------------------------------------------------------------------------

    atomic_info "Generation 7: Section 7 (Code Structure Map)"

    local gen7_context
    gen7_context=$(_205_build_context 7 "$output_dir" "$project_name" "$project_type" "$tech_stack_locked" "$current_date")

    local gen7_prior="$prompts_dir/gen-7-prior.md"
    _205_assemble_prior_sections 7 "$output_dir" "$gen7_prior"

    cat > "$prompts_dir/gen-7-prompt.md" << 'EOF_GEN7'
# PRD Generation 7: Code Structure Map

You are the **prd-writer** agent continuing the PRD.

## Task

Generate **Section 7**: Code Structure Map

This section defines the directory structure and code organization for the project.

## Context

EOF_GEN7
    cat "$gen7_context" >> "$prompts_dir/gen-7-prompt.md"

    cat >> "$prompts_dir/gen-7-prompt.md" << 'EOF_GEN7_2'

## Prior Sections (excerpt - focus on tech architecture)

EOF_GEN7_2
    tail -150 "$gen7_prior" >> "$prompts_dir/gen-7-prompt.md"

    cat >> "$prompts_dir/gen-7-prompt.md" << 'EOF_GEN7_3'

## Instructions

1. Define directory structure aligned with locked tech stack
2. Organize code by functional areas
3. Include test directories
4. Specify configuration locations
5. Maintain tech stack consistency

## Output Format

Output ONLY the markdown content for section 7. Start with:

```markdown
## 7. Code Structure Map

...
```

**CRITICAL**: Output complete section. Do NOT summarize or truncate.
EOF_GEN7_3

    local gen7_output="$prompts_dir/gen-7-sections.md"
    local gen7_guardian_prompt="$prompts_dir/guardian-gen-7-prompt.md"
    local gen7_guardian_report="$prompts_dir/guardian-gen-7-report.json"

    if ! _205_generate_with_retry 7 "$prompts_dir/gen-7-prompt.md" "$gen7_output" "$gen7_prior" \
        "$gen7_guardian_prompt" "$gen7_guardian_report" "$guardian_model" "$project_context" \
        "PRD Gen 7: Code Structure"; then
        atomic_error "Generation 7 failed"
        return 1
    fi

    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_7" "$(cat "$gen7_output")" 2>/dev/null || true
    fi

    atomic_success "Generation 7 complete: $(wc -w < "$gen7_output") words"

    # -------------------------------------------------------------------------
    # GENERATION 8: Section 8 (TDD Strategy)
    # -------------------------------------------------------------------------

    atomic_info "Generation 8: Section 8 (TDD Implementation Strategy)"

    local gen8_context
    gen8_context=$(_205_build_context 8 "$output_dir" "$project_name" "$project_type" "$tech_stack_locked" "$current_date")

    local gen8_prior="$prompts_dir/gen-8-prior.md"
    _205_assemble_prior_sections 8 "$output_dir" "$gen8_prior"

    cat > "$prompts_dir/gen-8-prompt.md" << 'EOF_GEN8'
# PRD Generation 8: TDD Implementation Strategy

You are the **prd-writer** agent continuing the PRD.

## Task

Generate **Section 8**: TDD Implementation Strategy

This section defines the test-driven development approach for the project.

## Context

EOF_GEN8
    cat "$gen8_context" >> "$prompts_dir/gen-8-prompt.md"

    cat >> "$prompts_dir/gen-8-prompt.md" << 'EOF_GEN8_2'

## Prior Sections (excerpt - focus on code structure and FRs)

EOF_GEN8_2
    tail -150 "$gen8_prior" >> "$prompts_dir/gen-8-prompt.md"

    cat >> "$prompts_dir/gen-8-prompt.md" << 'EOF_GEN8_3'

## Instructions

1. Define TDD workflow (Red-Green-Refactor)
2. Specify test types (unit, integration, e2e)
3. Define coverage targets
4. Align testing approach with tech stack
5. Reference FRs/NFRs for testable requirements

## Output Format

Output ONLY the markdown content for section 8. Start with:

```markdown
## 8. TDD Implementation Strategy

...
```

**CRITICAL**: Output complete section. Do NOT summarize or truncate.
EOF_GEN8_3

    local gen8_output="$prompts_dir/gen-8-sections.md"
    local gen8_guardian_prompt="$prompts_dir/guardian-gen-8-prompt.md"
    local gen8_guardian_report="$prompts_dir/guardian-gen-8-report.json"

    if ! _205_generate_with_retry 8 "$prompts_dir/gen-8-prompt.md" "$gen8_output" "$gen8_prior" \
        "$gen8_guardian_prompt" "$gen8_guardian_report" "$guardian_model" "$project_context" \
        "PRD Gen 8: TDD Strategy"; then
        atomic_error "Generation 8 failed"
        return 1
    fi

    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_8" "$(cat "$gen8_output")" 2>/dev/null || true
    fi

    atomic_success "Generation 8 complete: $(wc -w < "$gen8_output") words"

    # -------------------------------------------------------------------------
    # GENERATION 9: Section 9 (Integration Testing)
    # -------------------------------------------------------------------------

    atomic_info "Generation 9: Section 9 (Integration Testing Strategy)"

    local gen9_context
    gen9_context=$(_205_build_context 9 "$output_dir" "$project_name" "$project_type" "$tech_stack_locked" "$current_date")

    local gen9_prior="$prompts_dir/gen-9-prior.md"
    _205_assemble_prior_sections 9 "$output_dir" "$gen9_prior"

    cat > "$prompts_dir/gen-9-prompt.md" << 'EOF_GEN9'
# PRD Generation 9: Integration Testing Strategy

You are the **prd-writer** agent continuing the PRD.

## Task

Generate **Section 9**: Integration Testing Strategy

This section defines how components will be tested together.

## Context

EOF_GEN9
    cat "$gen9_context" >> "$prompts_dir/gen-9-prompt.md"

    cat >> "$prompts_dir/gen-9-prompt.md" << 'EOF_GEN9_2'

## Prior Sections (excerpt - focus on TDD strategy and FRs)

EOF_GEN9_2
    tail -150 "$gen9_prior" >> "$prompts_dir/gen-9-prompt.md"

    cat >> "$prompts_dir/gen-9-prompt.md" << 'EOF_GEN9_3'

## Instructions

1. Define integration testing levels (component, system, e2e)
2. Specify integration testing tools
3. Define integration test scenarios
4. Align with TDD strategy from Section 8
5. Reference NFRs for integration test criteria

## Output Format

Output ONLY the markdown content for section 9. Start with:

```markdown
## 9. Integration Testing Strategy

...
```

**CRITICAL**: Output complete section. Do NOT summarize or truncate.
EOF_GEN9_3

    local gen9_output="$prompts_dir/gen-9-sections.md"
    local gen9_guardian_prompt="$prompts_dir/guardian-gen-9-prompt.md"
    local gen9_guardian_report="$prompts_dir/guardian-gen-9-report.json"

    if ! _205_generate_with_retry 9 "$prompts_dir/gen-9-prompt.md" "$gen9_output" "$gen9_prior" \
        "$gen9_guardian_prompt" "$gen9_guardian_report" "$guardian_model" "$project_context" \
        "PRD Gen 9: Integration Testing"; then
        atomic_error "Generation 9 failed"
        return 1
    fi

    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_9" "$(cat "$gen9_output")" 2>/dev/null || true
    fi

    atomic_success "Generation 9 complete: $(wc -w < "$gen9_output") words"

    # -------------------------------------------------------------------------
    # GENERATION 10: Sections 10-11 (Documentation + Operations)
    # -------------------------------------------------------------------------

    atomic_info "Generation 10: Sections 10-11 (Documentation + Operational)"

    local gen10_context
    gen10_context=$(_205_build_context 10 "$output_dir" "$project_name" "$project_type" "$tech_stack_locked" "$current_date")

    local gen10_prior="$prompts_dir/gen-10-prior.md"
    _205_assemble_prior_sections 10 "$output_dir" "$gen10_prior"

    cat > "$prompts_dir/gen-10-prompt.md" << 'EOF_GEN10'
# PRD Generation 10: Documentation + Operations

You are the **prd-writer** agent continuing the PRD.

## Task

Generate **Sections 10-11**:
- **Section 10**: Documentation Requirements
- **Section 11**: Operational Readiness

## Context

EOF_GEN10
    cat "$gen10_context" >> "$prompts_dir/gen-10-prompt.md"

    cat >> "$prompts_dir/gen-10-prompt.md" << 'EOF_GEN10_2'

## Prior Sections (summary)

EOF_GEN10_2
    echo "### Sections 0-1 (excerpt)" >> "$prompts_dir/gen-10-prompt.md"
    head -50 "$output_dir/prompts/gen-1-sections.md" >> "$prompts_dir/gen-10-prompt.md" 2>/dev/null || true
    echo "" >> "$prompts_dir/gen-10-prompt.md"
    echo "### Tech Stack (from Section 2)" >> "$prompts_dir/gen-10-prompt.md"
    tail -50 "$output_dir/prompts/gen-2-sections.md" >> "$prompts_dir/gen-10-prompt.md" 2>/dev/null || true
    echo "" >> "$prompts_dir/gen-10-prompt.md"

    cat >> "$prompts_dir/gen-10-prompt.md" << 'EOF_GEN10_3'

## Instructions

1. Define all documentation requirements (README, API docs, user guides)
2. Specify operational readiness criteria
3. Include deployment documentation needs
4. Define monitoring and logging requirements
5. Maintain tech stack consistency

## Output Format

Output ONLY the markdown content for sections 10-11. Start with:

```markdown
## 10. Documentation Requirements

...

## 11. Operational Readiness

...
```

**CRITICAL**: Output complete sections. Do NOT summarize or truncate.
EOF_GEN10_3

    local gen10_output="$prompts_dir/gen-10-sections.md"
    local gen10_guardian_prompt="$prompts_dir/guardian-gen-10-prompt.md"
    local gen10_guardian_report="$prompts_dir/guardian-gen-10-report.json"

    if ! _205_generate_with_retry 10 "$prompts_dir/gen-10-prompt.md" "$gen10_output" "$gen10_prior" \
        "$gen10_guardian_prompt" "$gen10_guardian_report" "$guardian_model" "$project_context" \
        "PRD Gen 10: Documentation + Operations"; then
        atomic_error "Generation 10 failed"
        return 1
    fi

    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_10_11" "$(cat "$gen10_output")" 2>/dev/null || true
    fi

    atomic_success "Generation 10 complete: $(wc -w < "$gen10_output") words"

    # -------------------------------------------------------------------------
    # GENERATION 11: Sections 12-13 (Risks + Metrics)
    # -------------------------------------------------------------------------

    atomic_info "Generation 11: Sections 12-13 (Risks + Success Metrics)"

    local gen11_context
    gen11_context=$(_205_build_context 11 "$output_dir" "$project_name" "$project_type" "$tech_stack_locked" "$current_date")

    local gen11_prior="$prompts_dir/gen-11-prior.md"
    _205_assemble_prior_sections 11 "$output_dir" "$gen11_prior"

    cat > "$prompts_dir/gen-11-prompt.md" << 'EOF_GEN11'
# PRD Generation 11: Risks + Success Metrics

You are the **prd-writer** agent continuing the PRD.

## Task

Generate **Sections 12-13**:
- **Section 12**: Risks and Assumptions
- **Section 13**: Success Metrics

## Context

EOF_GEN11
    cat "$gen11_context" >> "$prompts_dir/gen-11-prompt.md"

    cat >> "$prompts_dir/gen-11-prompt.md" << 'EOF_GEN11_2'

## Prior Sections (summary)

EOF_GEN11_2
    echo "### Vision (from Section 0)" >> "$prompts_dir/gen-11-prompt.md"
    head -30 "$output_dir/prompts/gen-1-sections.md" >> "$prompts_dir/gen-11-prompt.md" 2>/dev/null || true
    echo "" >> "$prompts_dir/gen-11-prompt.md"
    echo "### NFRs (from Section 4)" >> "$prompts_dir/gen-11-prompt.md"
    tail -50 "$output_dir/prompts/gen-4-sections.md" >> "$prompts_dir/gen-11-prompt.md" 2>/dev/null || true
    echo "" >> "$prompts_dir/gen-11-prompt.md"

    cat >> "$prompts_dir/gen-11-prompt.md" << 'EOF_GEN11_3'

## Instructions

1. Identify minimum 5 risks with mitigation strategies
2. Cover technical, operational, and business risks
3. Define specific, measurable success metrics
4. Align metrics with NFRs and project goals
5. Include both quantitative and qualitative metrics

## Output Format

Output ONLY the markdown content for sections 12-13. Start with:

```markdown
## 12. Risks and Assumptions

...

## 13. Success Metrics

...
```

**CRITICAL**: Output complete sections. Do NOT summarize or truncate.
EOF_GEN11_3

    local gen11_output="$prompts_dir/gen-11-sections.md"
    local gen11_guardian_prompt="$prompts_dir/guardian-gen-11-prompt.md"
    local gen11_guardian_report="$prompts_dir/guardian-gen-11-report.json"

    if ! _205_generate_with_retry 11 "$prompts_dir/gen-11-prompt.md" "$gen11_output" "$gen11_prior" \
        "$gen11_guardian_prompt" "$gen11_guardian_report" "$guardian_model" "$project_context" \
        "PRD Gen 11: Risks + Metrics"; then
        atomic_error "Generation 11 failed"
        return 1
    fi

    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_12_13" "$(cat "$gen11_output")" 2>/dev/null || true
    fi

    atomic_success "Generation 11 complete: $(wc -w < "$gen11_output") words"

    # -------------------------------------------------------------------------
    # GENERATION 12: Section 14 (Approval)
    # -------------------------------------------------------------------------

    atomic_info "Generation 12: Section 14 (Approval and Sign-off)"

    local gen12_context
    gen12_context=$(_205_build_context 12 "$output_dir" "$project_name" "$project_type" "$tech_stack_locked" "$current_date")

    local gen12_prior="$prompts_dir/gen-12-prior.md"
    _205_assemble_prior_sections 12 "$output_dir" "$gen12_prior"

    cat > "$prompts_dir/gen-12-prompt.md" << 'EOF_GEN12'
# PRD Generation 12: Approval and Sign-off

You are the **prd-writer** agent completing the PRD.

## Task

Generate **Section 14**: Approval and Sign-off (FINAL SECTION)

This is the final section of the PRD.

## Context

EOF_GEN12
    cat "$gen12_context" >> "$prompts_dir/gen-12-prompt.md"

    cat >> "$prompts_dir/gen-12-prompt.md" << 'EOF_GEN12_2'

## Prior Sections (summary)

EOF_GEN12_2
    echo "### Project Overview" >> "$prompts_dir/gen-12-prompt.md"
    head -30 "$output_dir/prompts/gen-1-sections.md" >> "$prompts_dir/gen-12-prompt.md" 2>/dev/null || true
    echo "" >> "$prompts_dir/gen-12-prompt.md"

    cat >> "$prompts_dir/gen-12-prompt.md" << 'EOF_GEN12_3'

## Instructions

1. Create stakeholder approval section
2. Include sign-off table with roles and dates
3. Add document metadata (version, generation date)
4. Include ATOMIC CLAUDE attribution
5. Mark as TaskMaster and OpenSpec compatible

## Output Format

Output ONLY the markdown content for section 14. Start with:

```markdown
## 14. Approval and Sign-off

...

---

*Generated by ATOMIC CLAUDE - Phase 2 PRD*
*Compatible with TaskMaster and OpenSpec*
EOF_GEN12_3
    echo "*Date: $current_date*" >> "$prompts_dir/gen-12-prompt.md"
    cat >> "$prompts_dir/gen-12-prompt.md" << 'EOF_GEN12_4'
```

**CRITICAL**: Output complete section. Do NOT summarize or truncate.
EOF_GEN12_4

    local gen12_output="$prompts_dir/gen-12-sections.md"
    local gen12_guardian_prompt="$prompts_dir/guardian-gen-12-prompt.md"
    local gen12_guardian_report="$prompts_dir/guardian-gen-12-report.json"

    if ! _205_generate_with_retry 12 "$prompts_dir/gen-12-prompt.md" "$gen12_output" "$gen12_prior" \
        "$gen12_guardian_prompt" "$gen12_guardian_report" "$guardian_model" "$project_context" \
        "PRD Gen 12: Approval"; then
        atomic_error "Generation 12 failed"
        return 1
    fi

    if command -v _memory_save_local >/dev/null 2>&1; then
        _memory_save_local "2" "205" "prd_section_14" "$(cat "$gen12_output")" 2>/dev/null || true
    fi

    atomic_success "Generation 12 complete: $(wc -w < "$gen12_output") words"

    # -------------------------------------------------------------------------
    # FINAL ASSEMBLY AND VALIDATION
    # -------------------------------------------------------------------------

    atomic_info "Assembling final PRD from 12 generations..."

    # Assemble full PRD
    cat "$output_dir/prompts/gen-1-sections.md" > "$prd_file"
    echo "" >> "$prd_file"
    cat "$output_dir/prompts/gen-2-sections.md" >> "$prd_file"
    echo "" >> "$prd_file"
    cat "$output_dir/prompts/gen-3-sections.md" >> "$prd_file"
    echo "" >> "$prd_file"
    cat "$output_dir/prompts/gen-4-sections.md" >> "$prd_file"
    echo "" >> "$prd_file"
    cat "$output_dir/prompts/gen-5-sections.md" >> "$prd_file"
    echo "" >> "$prd_file"
    cat "$output_dir/prompts/gen-6-sections.md" >> "$prd_file"
    echo "" >> "$prd_file"
    cat "$output_dir/prompts/gen-7-sections.md" >> "$prd_file"
    echo "" >> "$prd_file"
    cat "$output_dir/prompts/gen-8-sections.md" >> "$prd_file"
    echo "" >> "$prd_file"
    cat "$output_dir/prompts/gen-9-sections.md" >> "$prd_file"
    echo "" >> "$prd_file"
    cat "$output_dir/prompts/gen-10-sections.md" >> "$prd_file"
    echo "" >> "$prd_file"
    cat "$output_dir/prompts/gen-11-sections.md" >> "$prd_file"
    echo "" >> "$prd_file"
    cat "$output_dir/prompts/gen-12-sections.md" >> "$prd_file"

    local prd_word_count
    local prd_line_count
    prd_word_count=$(wc -w < "$prd_file")
    prd_line_count=$(wc -l < "$prd_file")

    atomic_success "Full PRD assembled: $prd_word_count words, $prd_line_count lines"

    # Final guardian validation
    atomic_info "Running final guardian validation on complete PRD..."

    cat > "$prompts_dir/guardian-final-prompt.md" << EOF
# Document Guardian - Final PRD Validation

## Complete PRD (excerpt)

$(head -500 "$prd_file")

...

$(tail -300 "$prd_file")

## Validation Task

Perform final check:
1. All 15 sections present (0-14)
2. No broken cross-references (all FR/NFR IDs valid)
3. Tech stack consistent throughout
4. TaskMaster-ready (Section 5 complete with dependency chain)
5. OpenSpec-compliant (WHEN/THEN scenarios in FRs)

Return JSON with validation status.
EOF

    local guardian_final="$prompts_dir/guardian-final-report.json"

    if atomic_invoke "$prompts_dir/guardian-final-prompt.md" "$guardian_final" "Guardian: Final validation" \
        --provider=ollama --model="$guardian_model" --format=json --timeout=180; then

        # Extract JSON
        local clean_final="${guardian_final}.clean"
        if _205_extract_json_from_markdown "$guardian_final" "$clean_final"; then
            mv "$clean_final" "$guardian_final"
        fi

        if jq -e '.validation.status == "fail"' "$guardian_final" > /dev/null 2>&1; then
            atomic_warn "Guardian found issues in final PRD:"
            jq -r '.validation.issues[]? | "  - [\(.severity)] \(.message)"' "$guardian_final" 2>/dev/null || true
        else
            atomic_success "Guardian approved final PRD"
        fi
    fi

    # Generate guardian summary
    cat > "$output_dir/guardian-summary.json" << EOF
{
  "total_generations": 12,
  "guardian_model": "$guardian_model",
  "validations": [
EOF

    for ((i=1; i<=12; i++)); do
        local report="$prompts_dir/guardian-gen-${i}-report.json"
        if [[ -f "$report" ]]; then
            local status
            status=$(jq -r '.validation.status // "unknown"' "$report" 2>/dev/null || echo "unknown")
            local drift
            drift=$(jq -r '.validation.drift_detected // false' "$report" 2>/dev/null || echo "false")

            cat >> "$output_dir/guardian-summary.json" << EOF
    {
      "generation": $i,
      "status": "$status",
      "drift_detected": $drift
    }$(if [[ $i -lt 12 ]]; then echo ","; fi)
EOF
        fi
    done

    cat >> "$output_dir/guardian-summary.json" << EOF

  ],
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

    # Copy to project docs
    mkdir -p docs/prd
    cp "$prd_file" docs/prd/PRD.md

    atomic_success "PRD generation complete (12-generation sequential workflow)"
    atomic_info "Location: docs/prd/PRD.md"
    atomic_info "Stats: $prd_word_count words, $prd_line_count lines"
    atomic_info "Guardian summary: $output_dir/guardian-summary.json"

    return 0
}

# Execute if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/atomic.sh"
    if [[ -f "$(dirname "${BASH_SOURCE[0]}")/../../../lib/memory.sh" ]]; then
        source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/memory.sh"
    fi
    task_205_prd_authoring
fi
