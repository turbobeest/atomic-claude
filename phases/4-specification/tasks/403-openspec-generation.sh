#!/bin/bash
#
# Task 403: OpenSpec Generation
# Create detailed specification files for each task
#

task_403_openspec_generation() {
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local specs_dir="$ATOMIC_ROOT/.claude/specs"
    local progress_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/spec-progress.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    atomic_step "OpenSpec Generation"

    mkdir -p "$specs_dir" "$prompts_dir" "$(dirname "$progress_file")"

    echo ""
    echo -e "  ${DIM}Generating OpenSpec definitions for each task.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # GENERATION MODE SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}GENERATION MODE${NC}"
    echo ""

    local task_count=$(jq '.tasks | length // 0' "$tasks_file")
    local existing_specs=$(find "$specs_dir" -name "spec-*.json" 2>/dev/null | wc -l)
    local missing_specs=$((task_count - existing_specs))

    echo -e "  ${DIM}Tasks to specify: $task_count${NC}"
    echo -e "  ${DIM}Existing specs:   $existing_specs${NC}"
    echo -e "  ${DIM}Missing specs:    $missing_specs${NC}"
    echo ""

    echo -e "  ${CYAN}How would you like to proceed?${NC}"
    echo ""
    echo -e "    ${GREEN}[auto]${NC}       Generate all missing specs automatically"
    echo -e "    ${YELLOW}[guided]${NC}    Review and approve each spec"
    echo -e "    ${CYAN}[batch]${NC}      Generate in batches of 5"
    echo -e "    ${MAGENTA}[select]${NC}    Choose specific tasks to specify"
    echo ""

    read -p "  Choice [auto]: " gen_mode
    gen_mode=${gen_mode:-auto}

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # OPENSPEC TEMPLATE PREVIEW
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}OPENSPEC STRUCTURE${NC}"
    echo ""
    echo -e "  ${DIM}Each spec file will contain:${NC}"
    echo ""

    cat << 'TEMPLATE'
    {
      "spec_id": "SPEC-T{id}",
      "task_id": {id},
      "task_title": "...",

      "test_strategy": {
        "unit_tests": [
          { "name": "test_...", "description": "..." }
        ],
        "integration_tests": [...],
        "scenarios": [
          { "given": "...", "when": "...", "then": "..." }
        ]
      },

      "interfaces": {
        "inputs": [
          { "name": "...", "type": "...", "required": true }
        ],
        "outputs": [
          { "name": "...", "type": "...", "description": "..." }
        ],
        "errors": [
          { "code": "...", "condition": "...", "message": "..." }
        ]
      },

      "edge_cases": [
        { "scenario": "...", "expected_behavior": "..." }
      ],

      "security_requirements": [
        { "requirement": "...", "validation": "..." }
      ]
    }
TEMPLATE

    echo ""
    read -p "  Press Enter to begin generation..."
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SPECIFICATION GENERATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}GENERATING SPECIFICATIONS${NC}"
    echo ""

    local generated=0
    local skipped=0
    local failed=0

    # Get task list
    local task_ids=$(jq -r '.tasks[].id' "$tasks_file")

    for task_id in $task_ids; do
        local spec_file="$specs_dir/spec-t${task_id}.json"
        local task_title=$(jq -r ".tasks[] | select(.id == $task_id) | .title" "$tasks_file")
        local task_desc=$(jq -r ".tasks[] | select(.id == $task_id) | .description // \"\"" "$tasks_file")
        local task_criteria=$(jq -r ".tasks[] | select(.id == $task_id) | .acceptance_criteria // \"\"" "$tasks_file")
        local task_complexity=$(jq -r ".tasks[] | select(.id == $task_id) | .estimated_complexity // \"moderate\"" "$tasks_file")

        # Check if spec exists
        if [[ -f "$spec_file" ]]; then
            echo -e "  ${DIM}[${task_id}] Skipping (spec exists): ${task_title:0:50}${NC}"
            ((skipped++))
            continue
        fi

        echo -e "  ${CYAN}[${task_id}]${NC} Generating: ${task_title:0:60}"

        # Build LLM prompt for OpenSpec generation
        local prompt_file="$prompts_dir/openspec-t${task_id}.md"
        local raw_spec="$prompts_dir/openspec-t${task_id}-raw.json"

        # Get task dependencies
        local task_deps=$(jq -r ".tasks[] | select(.id == $task_id) | .dependencies // [] | join(\", \")" "$tasks_file")
        local task_category=$(jq -r ".tasks[] | select(.id == $task_id) | .category // \"feature\"" "$tasks_file")
        local task_prd_section=$(jq -r ".tasks[] | select(.id == $task_id) | .prd_section // \"\"" "$tasks_file")

        cat > "$prompt_file" << PROMPT
# Task: Generate OpenSpec for Task $task_id

You are a specification writer creating a detailed OpenSpec for TDD implementation.

## Task Details

- **ID**: $task_id
- **Title**: $task_title
- **Category**: $task_category
- **Complexity**: $task_complexity
- **Dependencies**: ${task_deps:-None}
- **PRD Section**: ${task_prd_section:-Not specified}

## Description

$task_desc

## Acceptance Criteria

$task_criteria

## Tech Stack Context

$(cat "$ATOMIC_ROOT/docs/prd/PRD.md" 2>/dev/null | sed -n '/### 2\.1 Tech Stack/,/### 2\.2/p' | head -30 || echo "Tech stack not available")

## OpenSpec Requirements

Generate a detailed specification that includes:

1. **Test Strategy**: Specific unit tests and integration tests with descriptive names
2. **Scenarios**: Given/When/Then format for each acceptance criterion
3. **Interfaces**: Input parameters, output types, error codes
4. **Edge Cases**: At least 3-5 realistic edge cases
5. **Security Requirements**: Input validation, authorization checks if applicable

## Quality Checklist

- [ ] Test names are specific (not "test_basic")
- [ ] Scenarios cover all acceptance criteria
- [ ] Edge cases are realistic for this task type
- [ ] Error codes are specific (not generic INVALID_INPUT)
- [ ] Security requirements match task category

## Output Format

Generate ONLY valid JSON matching this structure:

{
  "spec_id": "SPEC-T$task_id",
  "task_id": $task_id,
  "task_title": "$task_title",
  "task_description": "...",
  "acceptance_criteria": "...",
  "complexity": "$task_complexity",
  "test_strategy": {
    "unit_tests": [
      {"name": "test_specific_behavior", "description": "...", "priority": "high|medium|low"}
    ],
    "integration_tests": [
      {"name": "test_integration_with_x", "description": "...", "dependencies": ["component"]}
    ],
    "scenarios": [
      {"name": "Descriptive scenario name", "given": "...", "when": "...", "then": "..."}
    ]
  },
  "interfaces": {
    "inputs": [{"name": "param", "type": "string", "required": true, "validation": "..."}],
    "outputs": [{"name": "result", "type": "object", "description": "..."}],
    "errors": [{"code": "SPECIFIC_ERROR", "condition": "...", "message": "...", "http_status": 400}]
  },
  "edge_cases": [
    {"scenario": "Specific edge case", "expected_behavior": "Detailed expected behavior"}
  ],
  "security_requirements": [
    {"requirement": "Specific requirement", "validation": "How to verify", "severity": "high|medium|low"}
  ],
  "generated_at": "$(date -Iseconds)",
  "status": "draft"
}

Output ONLY the JSON, no markdown wrapper.
PROMPT

        # Call LLM to generate spec
        if atomic_invoke "$prompt_file" "$raw_spec" "OpenSpec T$task_id" --model=sonnet; then
            # Validate and copy if valid JSON
            if jq -e . "$raw_spec" &>/dev/null; then
                cp "$raw_spec" "$spec_file"
                echo -e "       ${GREEN}✓${NC} Created spec-t${task_id}.json"
                ((generated++))
            else
                echo -e "       ${YELLOW}!${NC} Invalid JSON - attempting repair"
                # Try to extract JSON from markdown
                if grep -q '```json' "$raw_spec"; then
                    sed -n '/```json/,/```/p' "$raw_spec" | sed '1d;$d' > "${raw_spec}.tmp"
                    if jq -e . "${raw_spec}.tmp" &>/dev/null; then
                        mv "${raw_spec}.tmp" "$spec_file"
                        echo -e "       ${GREEN}✓${NC} Repaired and created spec-t${task_id}.json"
                        ((generated++))
                    else
                        rm -f "${raw_spec}.tmp"
                        echo -e "       ${RED}✗${NC} Could not repair JSON"
                        ((failed++))
                    fi
                else
                    echo -e "       ${RED}✗${NC} Invalid output format"
                    ((failed++))
                fi
            fi
        else
            echo -e "       ${RED}✗${NC} LLM invocation failed"
            ((failed++))
        fi

        # In guided mode, pause for review
        if [[ "$gen_mode" == "guided" ]]; then
            echo ""
            echo -e "  ${DIM}Preview:${NC}"
            jq '.test_strategy.scenarios[0], .edge_cases[0]' "$spec_file" 2>/dev/null
            echo ""
            read -p "  [Enter] continue, [e]dit, [s]kip: " review_choice
            case "$review_choice" in
                e|edit)
                    echo -e "  ${DIM}Edit the spec file: $spec_file${NC}"
                    read -p "  Press Enter when done editing..."
                    ;;
                s|skip)
                    rm -f "$spec_file"
                    ((generated--))
                    ((skipped++))
                    ;;
            esac
        fi

        # In batch mode, pause every 5
        if [[ "$gen_mode" == "batch" && $((generated % 5)) -eq 0 && "$generated" -gt 0 ]]; then
            echo ""
            echo -e "  ${DIM}Batch of 5 complete. $generated generated so far.${NC}"
            read -p "  Press Enter to continue..."
            echo ""
        fi
    done

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # GENERATION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}GENERATION SUMMARY${NC}"
    echo ""

    echo -e "    Generated:  ${GREEN}$generated${NC}"
    echo -e "    Skipped:    ${YELLOW}$skipped${NC}"
    echo -e "    Failed:     ${RED}$failed${NC}"
    echo ""

    local total_specs=$(find "$specs_dir" -name "spec-*.json" | wc -l)
    local coverage=$((total_specs * 100 / task_count))

    echo -e "    Total specs:    $total_specs / $task_count"
    echo -e "    Coverage:       ${coverage}%"
    echo ""

    if [[ "$coverage" -lt 100 ]]; then
        echo -e "  ${YELLOW}!${NC} Not all tasks have specifications."
        echo -e "  ${DIM}You can re-run this task to generate missing specs.${NC}"
        echo ""
    fi

    # Save progress
    jq -n \
        --argjson generated "$generated" \
        --argjson skipped "$skipped" \
        --argjson failed "$failed" \
        --argjson total_specs "$total_specs" \
        --argjson task_count "$task_count" \
        --argjson coverage "$coverage" \
        '{
            "generation_mode": "'"$gen_mode"'",
            "generated": $generated,
            "skipped": $skipped,
            "failed": $failed,
            "total_specs": $total_specs,
            "task_count": $task_count,
            "coverage_percent": $coverage,
            "completed_at": (now | todate)
        }' > "$progress_file"

    atomic_context_artifact "$specs_dir" "openspec-dir" "OpenSpec definitions directory"
    atomic_context_decision "Generated $generated specs (${coverage}% coverage)" "specification"

    atomic_success "OpenSpec Generation complete"

    return 0
}
