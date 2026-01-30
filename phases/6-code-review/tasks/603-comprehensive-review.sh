#!/bin/bash
#
# Task 603: Comprehensive Review
# Execute parallel code review across all dimensions
#
# Uses 4 specialized review agents:
#   1. Deep Code Review - logic, error handling, security
#   2. Architecture Compliance - patterns, layer separation, dependencies
#   3. Performance Analysis - efficiency, resource usage, bottlenecks
#   4. Documentation Review - comments, docstrings, API docs
#

task_603_comprehensive_review() {
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local review_dir="$ATOMIC_ROOT/.claude/reviews"
    local findings_file="$review_dir/findings.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"
    local src_dir="$ATOMIC_ROOT/src"
    local test_dir="$ATOMIC_ROOT/tests"

    atomic_step "Comprehensive Review"

    mkdir -p "$review_dir" "$prompts_dir"

    echo ""
    echo -e "  ${DIM}Executing parallel code review across all dimensions.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # LOAD REVIEW AGENTS FROM TASK 602 SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/review-agents.json"
    local agent_repo="${ATOMIC_AGENT_REPO:-$ATOMIC_ROOT/repos/agents}"

    # Agent prompts (loaded from agents repository if available)
    export _603_DEEP_CODE_AGENT_PROMPT=""
    export _603_ARCH_AGENT_PROMPT=""
    export _603_PERF_AGENT_PROMPT=""
    export _603_DOC_AGENT_PROMPT=""

    if [[ -f "$agents_file" ]]; then
        echo -e "  ${DIM}Loading review agents from selection...${NC}"
        echo ""

        # Load Deep Code Reviewer agent
        local deep_agent=$(jq -r '.review_agents.deep_code.name // ""' "$agents_file")
        if [[ -n "$deep_agent" ]]; then
            agent_file=$(atomic_find_agent "$deep_agent" "$agent_repo")
            if [[ -f "$agent_file" ]]; then
                _603_DEEP_CODE_AGENT_PROMPT=$(cat "$agent_file" | atomic_strip_frontmatter)
                echo -e "  ${CYAN}✓${NC} Loaded agent: $deep_agent"
            fi
        fi

        # Load Architecture Compliance agent
        local arch_agent=$(jq -r '.review_agents.architecture.name // ""' "$agents_file")
        if [[ -n "$arch_agent" ]]; then
            agent_file=$(atomic_find_agent "$arch_agent" "$agent_repo")
            if [[ -f "$agent_file" ]]; then
                _603_ARCH_AGENT_PROMPT=$(cat "$agent_file" | atomic_strip_frontmatter)
                echo -e "  ${MAGENTA}✓${NC} Loaded agent: $arch_agent"
            fi
        fi

        # Load Performance Analyzer agent
        local perf_agent=$(jq -r '.review_agents.performance.name // ""' "$agents_file")
        if [[ -n "$perf_agent" ]]; then
            agent_file=$(atomic_find_agent "$perf_agent" "$agent_repo")
            if [[ -f "$agent_file" ]]; then
                _603_PERF_AGENT_PROMPT=$(cat "$agent_file" | atomic_strip_frontmatter)
                echo -e "  ${YELLOW}✓${NC} Loaded agent: $perf_agent"
            fi
        fi

        # Load Documentation Reviewer agent
        local doc_agent=$(jq -r '.review_agents.documentation.name // ""' "$agents_file")
        if [[ -n "$doc_agent" ]]; then
            agent_file=$(atomic_find_agent "$doc_agent" "$agent_repo")
            if [[ -f "$agent_file" ]]; then
                _603_DOC_AGENT_PROMPT=$(cat "$agent_file" | atomic_strip_frontmatter)
                echo -e "  ${BLUE}✓${NC} Loaded agent: $doc_agent"
            fi
        fi

        echo ""
    else
        echo -e "  ${YELLOW}!${NC} No agent selection found - using built-in prompts"
        echo ""
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # REVIEW SCOPE DISCOVERY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- REVIEW SCOPE${NC}"
    echo ""

    # Count implemented tasks
    local impl_count=$(jq '[.tasks[] | select(.status == "done")] | length' "$tasks_file" 2>/dev/null || echo 0)

    echo -e "  ${DIM}Tasks implemented: $impl_count${NC}"
    echo ""

    # Gather files to review
    local source_files=""
    local test_files=""
    local config_files=""

    # Find source files (common patterns)
    if [[ -d "$src_dir" ]]; then
        source_files=$(find "$src_dir" -type f \( -name "*.ts" -o -name "*.js" -o -name "*.py" -o -name "*.go" -o -name "*.rs" -o -name "*.java" \) 2>/dev/null | head -50)
    fi

    # Find test files
    if [[ -d "$test_dir" ]]; then
        test_files=$(find "$test_dir" -type f \( -name "*.test.*" -o -name "*_test.*" -o -name "test_*" -o -name "*spec*" \) 2>/dev/null | head -30)
    fi

    # Find config files at project root
    config_files=$(find "$ATOMIC_ROOT" -maxdepth 2 -type f \( -name "*.json" -o -name "*.yaml" -o -name "*.yml" -o -name "*.toml" \) ! -path "*node_modules*" ! -path "*/.git/*" 2>/dev/null | head -20)

    local source_count=$(echo "$source_files" | grep -c . || echo 0)
    local test_count=$(echo "$test_files" | grep -c . || echo 0)
    local config_count=$(echo "$config_files" | grep -c . || echo 0)

    echo -e "  ${DIM}Review scope:${NC}"
    echo -e "    - Source files: $source_count"
    echo -e "    - Test files:   $test_count"
    echo -e "    - Config files: $config_count"
    echo ""

    if [[ "$source_count" -eq 0 ]]; then
        atomic_warn "No source files found in $src_dir - using fallback discovery"
        # Try git to find recently modified files
        source_files=$(git -C "$ATOMIC_ROOT" diff --name-only HEAD~10 2>/dev/null | grep -E '\.(ts|js|py|go|rs|java)$' | head -50)
        source_count=$(echo "$source_files" | grep -c . || echo 0)
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # GATHER CODE CONTEXT
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "  ${DIM}Gathering code context for review agents...${NC}"
    echo ""

    # Create a combined code sample (truncated for token limits)
    local code_sample_file="$prompts_dir/code-sample.txt"
    local max_lines_per_file=100

    echo "# Source Code Sample for Review" > "$code_sample_file"
    echo "" >> "$code_sample_file"

    for file in $source_files; do
        if [[ -f "$ATOMIC_ROOT/$file" || -f "$file" ]]; then
            local filepath="${file#$ATOMIC_ROOT/}"
            [[ -f "$file" ]] && filepath="$file"
            echo "## File: $filepath" >> "$code_sample_file"
            echo '```' >> "$code_sample_file"
            head -n "$max_lines_per_file" "$filepath" 2>/dev/null >> "$code_sample_file" || head -n "$max_lines_per_file" "$ATOMIC_ROOT/$file" 2>/dev/null >> "$code_sample_file"
            echo '```' >> "$code_sample_file"
            echo "" >> "$code_sample_file"
        fi
    done

    # Get test code sample
    local test_sample_file="$prompts_dir/test-sample.txt"
    echo "# Test Code Sample for Review" > "$test_sample_file"
    echo "" >> "$test_sample_file"

    for file in $test_files; do
        if [[ -f "$file" ]]; then
            echo "## File: ${file#$ATOMIC_ROOT/}" >> "$test_sample_file"
            echo '```' >> "$test_sample_file"
            head -n "$max_lines_per_file" "$file" 2>/dev/null >> "$test_sample_file"
            echo '```' >> "$test_sample_file"
            echo "" >> "$test_sample_file"
        fi
    done

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PARALLEL REVIEW EXECUTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- PARALLEL REVIEW EXECUTION${NC}"
    echo ""

    echo -e "  ${DIM}Launching review agents...${NC}"
    echo ""

    # Initialize result files
    local code_result="$prompts_dir/review-code.json"
    local arch_result="$prompts_dir/review-arch.json"
    local perf_result="$prompts_dir/review-perf.json"
    local doc_result="$prompts_dir/review-doc.json"

    # Execute reviews (sequentially - could be parallelized with background jobs)
    echo -e "    Worker 1: ${CYAN}Deep Code Review${NC}         "
    _603_deep_code_review "$code_sample_file" "$code_result"
    local code_status=$?

    echo -e "    Worker 2: ${MAGENTA}Architecture Compliance${NC}  "
    _603_architecture_review "$code_sample_file" "$arch_result"
    local arch_status=$?

    echo -e "    Worker 3: ${YELLOW}Performance Analysis${NC}     "
    _603_performance_review "$code_sample_file" "$perf_result"
    local perf_status=$?

    echo -e "    Worker 4: ${BLUE}Documentation Review${NC}     "
    _603_documentation_review "$code_sample_file" "$test_sample_file" "$doc_result"
    local doc_status=$?

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PARSE AND DISPLAY RESULTS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Parse results with fallbacks
    local code_critical=0 code_major=0 code_minor=0 code_suggestions=0
    local arch_critical=0 arch_major=0 arch_minor=0 arch_suggestions=0
    local perf_critical=0 perf_major=0 perf_minor=0 perf_suggestions=0
    local doc_critical=0 doc_major=0 doc_minor=0 doc_suggestions=0

    if [[ -f "$code_result" ]] && jq -e . "$code_result" &>/dev/null; then
        code_critical=$(jq '.critical // 0' "$code_result")
        code_major=$(jq '.major // 0' "$code_result")
        code_minor=$(jq '.minor // 0' "$code_result")
        code_suggestions=$(jq '.suggestions // 0' "$code_result")
    fi

    if [[ -f "$arch_result" ]] && jq -e . "$arch_result" &>/dev/null; then
        arch_critical=$(jq '.critical // 0' "$arch_result")
        arch_major=$(jq '.major // 0' "$arch_result")
        arch_minor=$(jq '.minor // 0' "$arch_result")
        arch_suggestions=$(jq '.suggestions // 0' "$arch_result")
    fi

    if [[ -f "$perf_result" ]] && jq -e . "$perf_result" &>/dev/null; then
        perf_critical=$(jq '.critical // 0' "$perf_result")
        perf_major=$(jq '.major // 0' "$perf_result")
        perf_minor=$(jq '.minor // 0' "$perf_result")
        perf_suggestions=$(jq '.suggestions // 0' "$perf_result")
    fi

    if [[ -f "$doc_result" ]] && jq -e . "$doc_result" &>/dev/null; then
        doc_critical=$(jq '.critical // 0' "$doc_result")
        doc_major=$(jq '.major // 0' "$doc_result")
        doc_minor=$(jq '.minor // 0' "$doc_result")
        doc_suggestions=$(jq '.suggestions // 0' "$doc_result")
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # DEEP CODE REVIEW FINDINGS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}${CYAN}- DEEP CODE REVIEW FINDINGS${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "    Critical Issues:    ${code_critical:-0}"
    echo -e "    Major Issues:       ${code_major:-0}"
    echo -e "    Minor Issues:       ${code_minor:-0}"
    echo -e "    Suggestions:        ${code_suggestions:-0}"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    if [[ -f "$code_result" ]] && jq -e '.findings' "$code_result" &>/dev/null; then
        local major_findings=$(jq -r '.findings[] | select(.severity == "major") | "    - \(.description)"' "$code_result" 2>/dev/null | head -5)
        if [[ -n "$major_findings" ]]; then
            echo -e "  ${YELLOW}Major findings:${NC}"
            echo "$major_findings"
            echo ""
        fi
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # ARCHITECTURE COMPLIANCE FINDINGS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}${MAGENTA}- ARCHITECTURE COMPLIANCE FINDINGS${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "    Critical Issues:    ${arch_critical:-0}"
    echo -e "    Major Issues:       ${arch_major:-0}"
    echo -e "    Minor Issues:       ${arch_minor:-0}"
    echo -e "    Suggestions:        ${arch_suggestions:-0}"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    if [[ -f "$arch_result" ]] && jq -e '.findings' "$arch_result" &>/dev/null; then
        local major_findings=$(jq -r '.findings[] | select(.severity == "major") | "    - \(.description)"' "$arch_result" 2>/dev/null | head -5)
        if [[ -n "$major_findings" ]]; then
            echo -e "  ${YELLOW}Major findings:${NC}"
            echo "$major_findings"
            echo ""
        fi
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PERFORMANCE ANALYSIS FINDINGS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}${YELLOW}- PERFORMANCE ANALYSIS FINDINGS${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "    Critical Issues:    ${perf_critical:-0}"
    echo -e "    Major Issues:       ${perf_major:-0}"
    echo -e "    Minor Issues:       ${perf_minor:-0}"
    echo -e "    Suggestions:        ${perf_suggestions:-0}"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    if [[ "$perf_major" -eq 0 && "$perf_critical" -eq 0 ]]; then
        echo -e "  ${GREEN}✓${NC} No critical or major performance issues found"
        echo ""
    elif [[ -f "$perf_result" ]] && jq -e '.findings' "$perf_result" &>/dev/null; then
        local major_findings=$(jq -r '.findings[] | select(.severity == "major" or .severity == "critical") | "    - \(.description)"' "$perf_result" 2>/dev/null | head -5)
        if [[ -n "$major_findings" ]]; then
            echo -e "  ${YELLOW}Performance issues:${NC}"
            echo "$major_findings"
            echo ""
        fi
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # DOCUMENTATION REVIEW FINDINGS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}${BLUE}- DOCUMENTATION REVIEW FINDINGS${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "    Critical Issues:    ${doc_critical:-0}"
    echo -e "    Major Issues:       ${doc_major:-0}"
    echo -e "    Minor Issues:       ${doc_minor:-0}"
    echo -e "    Suggestions:        ${doc_suggestions:-0}"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    if [[ -f "$doc_result" ]] && jq -e '.findings' "$doc_result" &>/dev/null; then
        local major_findings=$(jq -r '.findings[] | select(.severity == "major") | "    - \(.description)"' "$doc_result" 2>/dev/null | head -5)
        if [[ -n "$major_findings" ]]; then
            echo -e "  ${YELLOW}Major findings:${NC}"
            echo "$major_findings"
            echo ""
        fi
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # REVIEW SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- REVIEW SUMMARY${NC}"
    echo ""

    local total_critical=$((code_critical + arch_critical + perf_critical + doc_critical))
    local total_major=$((code_major + arch_major + perf_major + doc_major))
    local total_minor=$((code_minor + arch_minor + perf_minor + doc_minor))
    local total_suggestions=$((code_suggestions + arch_suggestions + perf_suggestions + doc_suggestions))

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}TOTAL FINDINGS${NC}"
    echo ""
    if [[ "$total_critical" -eq 0 ]]; then
        echo -e "    Critical:     ${GREEN}$total_critical${NC}      Must fix before release"
    else
        echo -e "    Critical:     ${RED}$total_critical${NC}      Must fix before release"
    fi
    if [[ "$total_major" -eq 0 ]]; then
        echo -e "    Major:        ${GREEN}$total_major${NC}      Should fix before release"
    else
        echo -e "    Major:        ${YELLOW}$total_major${NC}      Should fix before release"
    fi
    echo -e "    Minor:        ${DIM}$total_minor${NC}      Consider fixing"
    echo -e "    Suggestions:  ${DIM}$total_suggestions${NC}      Nice to have improvements"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # Save combined findings
    jq -n \
        --argjson code_critical "$code_critical" \
        --argjson code_major "$code_major" \
        --argjson code_minor "$code_minor" \
        --argjson code_suggestions "$code_suggestions" \
        --argjson arch_critical "$arch_critical" \
        --argjson arch_major "$arch_major" \
        --argjson arch_minor "$arch_minor" \
        --argjson arch_suggestions "$arch_suggestions" \
        --argjson perf_critical "$perf_critical" \
        --argjson perf_major "$perf_major" \
        --argjson perf_minor "$perf_minor" \
        --argjson perf_suggestions "$perf_suggestions" \
        --argjson doc_critical "$doc_critical" \
        --argjson doc_major "$doc_major" \
        --argjson doc_minor "$doc_minor" \
        --argjson doc_suggestions "$doc_suggestions" \
        --argjson total_critical "$total_critical" \
        --argjson total_major "$total_major" \
        --argjson total_minor "$total_minor" \
        --argjson total_suggestions "$total_suggestions" \
        --slurpfile code_findings "$code_result" \
        --slurpfile arch_findings "$arch_result" \
        --slurpfile perf_findings "$perf_result" \
        --slurpfile doc_findings "$doc_result" \
        '{
            "deep_code": {
                "critical": $code_critical,
                "major": $code_major,
                "minor": $code_minor,
                "suggestions": $code_suggestions,
                "findings": ($code_findings[0].findings // [])
            },
            "architecture": {
                "critical": $arch_critical,
                "major": $arch_major,
                "minor": $arch_minor,
                "suggestions": $arch_suggestions,
                "findings": ($arch_findings[0].findings // [])
            },
            "performance": {
                "critical": $perf_critical,
                "major": $perf_major,
                "minor": $perf_minor,
                "suggestions": $perf_suggestions,
                "findings": ($perf_findings[0].findings // [])
            },
            "documentation": {
                "critical": $doc_critical,
                "major": $doc_major,
                "minor": $doc_minor,
                "suggestions": $doc_suggestions,
                "findings": ($doc_findings[0].findings // [])
            },
            "totals": {
                "critical": $total_critical,
                "major": $total_major,
                "minor": $total_minor,
                "suggestions": $total_suggestions
            },
            "reviewed_at": (now | todate)
        }' > "$findings_file" 2>/dev/null || \
    jq -n \
        --argjson total_critical "$total_critical" \
        --argjson total_major "$total_major" \
        --argjson total_minor "$total_minor" \
        --argjson total_suggestions "$total_suggestions" \
        '{
            "totals": {
                "critical": $total_critical,
                "major": $total_major,
                "minor": $total_minor,
                "suggestions": $total_suggestions
            },
            "reviewed_at": (now | todate)
        }' > "$findings_file"

    atomic_context_artifact "$findings_file" "review-findings" "Code review findings"
    atomic_context_decision "Review findings: $total_critical critical, $total_major major, $total_minor minor" "code-review"

    atomic_success "Comprehensive Review complete"

    return 0
}

# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# REVIEW HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

_603_deep_code_review() {
    local code_file="$1"
    local output_file="$2"
    local prompt_file="${output_file%.json}-prompt.md"

    # Use loaded agent prompt if available, otherwise use built-in
    if [[ -n "$_603_DEEP_CODE_AGENT_PROMPT" ]]; then
        echo "$_603_DEEP_CODE_AGENT_PROMPT" > "$prompt_file"
        cat >> "$prompt_file" << 'PROMPT'

---

# Deep Code Review Task

Apply your code review expertise to the following code.
PROMPT
    else
        cat > "$prompt_file" << 'PROMPT'
# Deep Code Review

You are a senior code reviewer performing a thorough code analysis.
PROMPT
    fi

    cat >> "$prompt_file" << 'PROMPT'

## Review Focus Areas

1. **Logic Errors**: Incorrect conditions, off-by-one errors, null checks
2. **Error Handling**: Missing try/catch, unhandled edge cases, error propagation
3. **Security**: Input validation, injection vulnerabilities, auth checks, data exposure
4. **Code Quality**: DRY violations, unclear naming, excessive complexity

## Severity Definitions

- **critical**: Security vulnerability, data loss risk, crash in normal use
- **major**: Incorrect behavior, poor error handling, significant maintainability issue
- **minor**: Style issues, minor inefficiencies, small improvements
- **suggestion**: Nice-to-have improvements, alternative approaches

## Code to Review

PROMPT

    cat "$code_file" >> "$prompt_file"

    cat >> "$prompt_file" << 'PROMPT_END'

## Output Format

Respond with ONLY valid JSON (no markdown wrapper):

{
  "critical": <number>,
  "major": <number>,
  "minor": <number>,
  "suggestions": <number>,
  "findings": [
    {
      "severity": "critical|major|minor|suggestion",
      "category": "logic|error_handling|security|code_quality",
      "file": "filename.ext",
      "line": 42,
      "description": "Brief description of the issue",
      "recommendation": "How to fix it"
    }
  ]
}

Be specific. If no issues found in a category, return 0 for that count.
PROMPT_END

    if atomic_invoke "$prompt_file" "$output_file" "Deep Code Review" --model=sonnet; then
        if jq -e . "$output_file" &>/dev/null; then
            echo -e "████████████████████████████████████████  ${GREEN}Complete${NC}"
            return 0
        else
            # Try to repair JSON
            if grep -q '```json' "$output_file"; then
                sed -n '/```json/,/```/p' "$output_file" | sed '1d;$d' > "${output_file}.tmp"
                if jq -e . "${output_file}.tmp" &>/dev/null; then
                    mv "${output_file}.tmp" "$output_file"
                    echo -e "████████████████████████████████████████  ${GREEN}Complete${NC}"
                    return 0
                fi
                rm -f "${output_file}.tmp"
            fi
        fi
    fi

    # Fallback: create empty result
    echo '{"critical":0,"major":0,"minor":0,"suggestions":0,"findings":[]}' > "$output_file"
    echo -e "████████████████████████████████████████  ${YELLOW}Fallback${NC}"
    return 1
}

_603_architecture_review() {
    local code_file="$1"
    local output_file="$2"
    local prompt_file="${output_file%.json}-prompt.md"

    # Use loaded agent prompt if available, otherwise use built-in
    if [[ -n "$_603_ARCH_AGENT_PROMPT" ]]; then
        echo "$_603_ARCH_AGENT_PROMPT" > "$prompt_file"
        cat >> "$prompt_file" << 'PROMPT'

---

# Architecture Compliance Review Task

Apply your architectural expertise to the following code.
PROMPT
    else
        cat > "$prompt_file" << 'PROMPT'
# Architecture Compliance Review

You are a software architect reviewing code for architectural compliance.
PROMPT
    fi

    cat >> "$prompt_file" << 'PROMPT'

## Review Focus Areas

1. **Layer Separation**: Presentation/business/data layer boundaries
2. **Dependency Direction**: Dependencies should point inward (to domain)
3. **Pattern Compliance**: Consistent use of chosen patterns (MVC, Clean Architecture, etc.)
4. **Module Boundaries**: Clear interfaces, no circular dependencies
5. **Coupling**: Avoid tight coupling between unrelated modules

## Severity Definitions

- **critical**: Circular dependency, layer violation that breaks testability
- **major**: Inconsistent pattern usage, wrong dependency direction
- **minor**: Could be better organized, naming doesn't reflect architecture
- **suggestion**: Alternative architectural approaches

## Code to Review

PROMPT

    cat "$code_file" >> "$prompt_file"

    cat >> "$prompt_file" << 'PROMPT_END'

## Output Format

Respond with ONLY valid JSON (no markdown wrapper):

{
  "critical": <number>,
  "major": <number>,
  "minor": <number>,
  "suggestions": <number>,
  "findings": [
    {
      "severity": "critical|major|minor|suggestion",
      "category": "layer_separation|dependency|pattern|module_boundary|coupling",
      "file": "filename.ext",
      "description": "Brief description of the architectural issue",
      "recommendation": "How to improve the architecture"
    }
  ]
}

Focus on real architectural concerns, not stylistic preferences.
PROMPT_END

    if atomic_invoke "$prompt_file" "$output_file" "Architecture Review" --model=sonnet; then
        if jq -e . "$output_file" &>/dev/null; then
            echo -e "████████████████████████████████████████  ${GREEN}Complete${NC}"
            return 0
        else
            if grep -q '```json' "$output_file"; then
                sed -n '/```json/,/```/p' "$output_file" | sed '1d;$d' > "${output_file}.tmp"
                if jq -e . "${output_file}.tmp" &>/dev/null; then
                    mv "${output_file}.tmp" "$output_file"
                    echo -e "████████████████████████████████████████  ${GREEN}Complete${NC}"
                    return 0
                fi
                rm -f "${output_file}.tmp"
            fi
        fi
    fi

    echo '{"critical":0,"major":0,"minor":0,"suggestions":0,"findings":[]}' > "$output_file"
    echo -e "████████████████████████████████████████  ${YELLOW}Fallback${NC}"
    return 1
}

_603_performance_review() {
    local code_file="$1"
    local output_file="$2"
    local prompt_file="${output_file%.json}-prompt.md"

    # Use loaded agent prompt if available, otherwise use built-in
    if [[ -n "$_603_PERF_AGENT_PROMPT" ]]; then
        echo "$_603_PERF_AGENT_PROMPT" > "$prompt_file"
        cat >> "$prompt_file" << 'PROMPT'

---

# Performance Analysis Review Task

Apply your performance engineering expertise to the following code.
PROMPT
    else
        cat > "$prompt_file" << 'PROMPT'
# Performance Analysis Review

You are a performance engineer reviewing code for efficiency issues.
PROMPT
    fi

    cat >> "$prompt_file" << 'PROMPT'

## Review Focus Areas

1. **Algorithm Complexity**: O(n^2) where O(n) is possible, nested loops
2. **Memory Usage**: Large allocations, memory leaks, unnecessary copies
3. **I/O Operations**: Blocking calls, missing batching, N+1 queries
4. **Caching**: Missing cache opportunities, cache invalidation issues
5. **Concurrency**: Race conditions, deadlock potential, thread safety

## Severity Definitions

- **critical**: Performance will degrade significantly under load (O(n^2) on user data)
- **major**: Noticeable slowdown, resource exhaustion risk
- **minor**: Suboptimal but acceptable, premature optimization candidate
- **suggestion**: Micro-optimizations, monitoring recommendations

## Code to Review

PROMPT

    cat "$code_file" >> "$prompt_file"

    cat >> "$prompt_file" << 'PROMPT_END'

## Output Format

Respond with ONLY valid JSON (no markdown wrapper):

{
  "critical": <number>,
  "major": <number>,
  "minor": <number>,
  "suggestions": <number>,
  "findings": [
    {
      "severity": "critical|major|minor|suggestion",
      "category": "algorithm|memory|io|caching|concurrency",
      "file": "filename.ext",
      "line": 42,
      "description": "Brief description of the performance issue",
      "impact": "Estimated impact (e.g., 'O(n^2) on list size')",
      "recommendation": "How to improve performance"
    }
  ]
}

Only flag real performance concerns. Avoid premature optimization advice.
PROMPT_END

    if atomic_invoke "$prompt_file" "$output_file" "Performance Review" --model=haiku; then
        if jq -e . "$output_file" &>/dev/null; then
            echo -e "████████████████████████████████████████  ${GREEN}Complete${NC}"
            return 0
        else
            if grep -q '```json' "$output_file"; then
                sed -n '/```json/,/```/p' "$output_file" | sed '1d;$d' > "${output_file}.tmp"
                if jq -e . "${output_file}.tmp" &>/dev/null; then
                    mv "${output_file}.tmp" "$output_file"
                    echo -e "████████████████████████████████████████  ${GREEN}Complete${NC}"
                    return 0
                fi
                rm -f "${output_file}.tmp"
            fi
        fi
    fi

    echo '{"critical":0,"major":0,"minor":0,"suggestions":0,"findings":[]}' > "$output_file"
    echo -e "████████████████████████████████████████  ${YELLOW}Fallback${NC}"
    return 1
}

_603_documentation_review() {
    local code_file="$1"
    local test_file="$2"
    local output_file="$3"
    local prompt_file="${output_file%.json}-prompt.md"

    # Use loaded agent prompt if available, otherwise use built-in
    if [[ -n "$_603_DOC_AGENT_PROMPT" ]]; then
        echo "$_603_DOC_AGENT_PROMPT" > "$prompt_file"
        cat >> "$prompt_file" << 'PROMPT'

---

# Documentation Review Task

Apply your technical writing expertise to the following code.
PROMPT
    else
        cat > "$prompt_file" << 'PROMPT'
# Documentation Review

You are a technical writer reviewing code documentation quality.
PROMPT
    fi

    cat >> "$prompt_file" << 'PROMPT'

## Review Focus Areas

1. **Public API Docs**: All public functions/methods have clear documentation
2. **Complex Logic Comments**: Non-obvious code has explanatory comments
3. **Type Annotations**: Parameters and return types are documented
4. **Examples**: Complex APIs have usage examples
5. **Accuracy**: Documentation matches actual behavior

## Severity Definitions

- **critical**: Public API completely undocumented, misleading docs
- **major**: Missing docs on important functions, outdated docs
- **minor**: Could use more detail, minor inaccuracies
- **suggestion**: Style improvements, additional examples

## Source Code

PROMPT

    cat "$code_file" >> "$prompt_file"

    cat >> "$prompt_file" << 'PROMPT_MIDDLE'

## Test Code (for reference)

PROMPT_MIDDLE

    cat "$test_file" >> "$prompt_file"

    cat >> "$prompt_file" << 'PROMPT_END'

## Output Format

Respond with ONLY valid JSON (no markdown wrapper):

{
  "critical": <number>,
  "major": <number>,
  "minor": <number>,
  "suggestions": <number>,
  "findings": [
    {
      "severity": "critical|major|minor|suggestion",
      "category": "api_docs|comments|types|examples|accuracy",
      "file": "filename.ext",
      "function": "functionName",
      "description": "Brief description of the documentation issue",
      "recommendation": "What documentation to add/fix"
    }
  ]
}

Focus on documentation that helps maintainability. Don't require docs for obvious code.
PROMPT_END

    if atomic_invoke "$prompt_file" "$output_file" "Documentation Review" --model=haiku; then
        if jq -e . "$output_file" &>/dev/null; then
            echo -e "████████████████████████████████████████  ${GREEN}Complete${NC}"
            return 0
        else
            if grep -q '```json' "$output_file"; then
                sed -n '/```json/,/```/p' "$output_file" | sed '1d;$d' > "${output_file}.tmp"
                if jq -e . "${output_file}.tmp" &>/dev/null; then
                    mv "${output_file}.tmp" "$output_file"
                    echo -e "████████████████████████████████████████  ${GREEN}Complete${NC}"
                    return 0
                fi
                rm -f "${output_file}.tmp"
            fi
        fi
    fi

    echo '{"critical":0,"major":0,"minor":0,"suggestions":0,"findings":[]}' > "$output_file"
    echo -e "████████████████████████████████████████  ${YELLOW}Fallback${NC}"
    return 1
}
