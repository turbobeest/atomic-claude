#!/bin/bash
#
# Task 403: OpenSpec Generation
# Create detailed specification files for each task
#

task_403_openspec_generation() {
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local specs_dir="$ATOMIC_ROOT/.claude/specs"
    local progress_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/spec-progress.json"

    atomic_step "OpenSpec Generation"

    mkdir -p "$specs_dir" "$(dirname "$progress_file")"

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

        # Generate spec (in real implementation, this would call an LLM)
        # For now, create a template that can be filled in

        jq -n \
            --argjson id "$task_id" \
            --arg title "$task_title" \
            --arg desc "$task_desc" \
            --arg criteria "$task_criteria" \
            --arg complexity "$task_complexity" \
            '{
                "spec_id": "SPEC-T\($id)",
                "task_id": $id,
                "task_title": $title,
                "task_description": $desc,
                "acceptance_criteria": $criteria,
                "complexity": $complexity,

                "test_strategy": {
                    "unit_tests": [
                        {
                            "name": "test_\($title | gsub("[^a-zA-Z0-9]"; "_") | ascii_downcase)_basic",
                            "description": "Verify basic functionality",
                            "priority": "high"
                        }
                    ],
                    "integration_tests": [],
                    "scenarios": [
                        {
                            "name": "Happy path",
                            "given": "Valid input conditions",
                            "when": "The operation is performed",
                            "then": "Expected outcome occurs"
                        }
                    ]
                },

                "interfaces": {
                    "inputs": [],
                    "outputs": [],
                    "errors": [
                        {
                            "code": "INVALID_INPUT",
                            "condition": "Invalid input provided",
                            "message": "The provided input is invalid"
                        }
                    ]
                },

                "edge_cases": [
                    {
                        "scenario": "Empty input",
                        "expected_behavior": "Handle gracefully with appropriate error"
                    },
                    {
                        "scenario": "Maximum input size",
                        "expected_behavior": "Process within acceptable time limits"
                    }
                ],

                "security_requirements": [
                    {
                        "requirement": "Input validation",
                        "validation": "All inputs must be validated before processing"
                    }
                ],

                "generated_at": (now | todate),
                "status": "draft"
            }' > "$spec_file"

        if [[ -f "$spec_file" ]]; then
            echo -e "       ${GREEN}✓${NC} Created spec-t${task_id}.json"
            ((generated++))
        else
            echo -e "       ${RED}✗${NC} Failed to create spec"
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
