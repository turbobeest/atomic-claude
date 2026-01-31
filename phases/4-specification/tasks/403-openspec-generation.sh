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
    local roster_file="$ATOMIC_ROOT/.claude/agent-roster.json"

    atomic_step "OpenSpec Generation"

    mkdir -p "$specs_dir" "$prompts_dir" "$(dirname "$progress_file")"

    echo ""
    echo -e "  ${DIM}Generating OpenSpec definitions for each task.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # LOAD SELECTED AGENTS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    local spec_writer_prompt=""
    local interface_definer_prompt=""
    local test_strategist_prompt=""
    local security_specifier_prompt=""
    local edge_case_hunter_prompt=""

    # Get agent repo path from Phase 0 config
    # Check embedded repo first (monorepo deployment), then env var, then default
    local agent_repo="$ATOMIC_ROOT/repos/agents"
    [[ -f "$ATOMIC_ROOT/agents/agent-inventory.csv" ]] && agent_repo="$ATOMIC_ROOT/agents"
    [[ -n "$ATOMIC_AGENT_REPO" ]] && agent_repo="$ATOMIC_AGENT_REPO"

    if [[ -f "$roster_file" ]]; then
        echo -e "  ${DIM}Loading agents from roster...${NC}"
        echo ""

        local selected_agents=$(jq -r '.agents[]?' "$roster_file" 2>/dev/null)

        for agent in $selected_agents; do
            # Use atomic_find_agent to search subdirectories and resolve aliases
            local agent_file
            agent_file=$(atomic_find_agent "$agent" "$agent_repo")

            if [[ -n "$agent_file" ]] && [[ -f "$agent_file" ]]; then
                # Load agent content, stripping YAML frontmatter
                local agent_content
                agent_content=$(cat "$agent_file" | atomic_strip_frontmatter)

                case "$agent" in
                    spec-writer|specification-agent)
                        spec_writer_prompt="$agent_content"
                        echo -e "  ${GREEN}✓${NC} Loaded agent: $agent (from ${agent_file##*/})"
                        ;;
                    interface-definer)
                        interface_definer_prompt="$agent_content"
                        echo -e "  ${GREEN}✓${NC} Loaded agent: $agent (from ${agent_file##*/})"
                        ;;
                    test-strategist)
                        test_strategist_prompt="$agent_content"
                        echo -e "  ${GREEN}✓${NC} Loaded agent: $agent (from ${agent_file##*/})"
                        ;;
                    security-specifier|code-review-gate)
                        security_specifier_prompt="$agent_content"
                        echo -e "  ${GREEN}✓${NC} Loaded agent: $agent (from ${agent_file##*/})"
                        ;;
                    edge-case-hunter)
                        edge_case_hunter_prompt="$agent_content"
                        echo -e "  ${GREEN}✓${NC} Loaded agent: $agent (from ${agent_file##*/})"
                        ;;
                    tdd-structurer|tdd-implementation-agent)
                        # Used in Task 404
                        echo -e "  ${GREEN}✓${NC} Found agent: $agent (for Task 404, from ${agent_file##*/})"
                        ;;
                    *)
                        echo -e "  ${DIM}✓${NC} Agent: $agent (from ${agent_file##*/})"
                        ;;
                esac
            else
                echo -e "  ${YELLOW}!${NC} Agent not found: $agent (searched aliases and subdirectories)"
            fi
        done
        echo ""
    else
        echo -e "  ${DIM}No agent roster found - using built-in specification logic${NC}"
        echo ""
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # GENERATION MODE SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}GENERATION MODE${NC}"
    echo ""

    local task_count=$(jq '.tasks | length // 0' "$tasks_file")
    local existing_specs=$(find "$specs_dir" -name "spec-*.json" 2>/dev/null | wc -l | tr -d ' ')
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
    echo -e "    ${BOLD}[parallel]${NC}   Generate specs in parallel (faster)"
    echo ""

    atomic_drain_stdin
    read -e -p "  Choice [auto]: " gen_mode || true
    gen_mode=${gen_mode:-auto}

    # Handle parallel mode with optional worker count
    local parallel_workers=4
    if [[ "$gen_mode" =~ ^parallel ]]; then
        if [[ "$gen_mode" =~ ^parallel[[:space:]]*([0-9]+)$ ]]; then
            parallel_workers="${BASH_REMATCH[1]}"
        fi
        gen_mode="parallel"
        echo ""
        echo -e "  ${DIM}Parallel mode: $parallel_workers concurrent workers${NC}"
    fi

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
    read -e -p "  Press Enter to begin generation..." || true
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

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PARALLEL MODE EXECUTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    if [[ "$gen_mode" == "parallel" ]]; then
        echo -e "  ${DIM}Phase 1: Generating prompt files...${NC}"
        echo ""

        local pending_tasks=()
        local pending_prompts=()

        # First pass: generate all prompt files for missing specs
        for task_id in $task_ids; do
            local spec_file="$specs_dir/spec-t${task_id}.json"

            # Skip existing specs
            if [[ -f "$spec_file" ]]; then
                ((skipped++))
                continue
            fi

            local task_title=$(jq -r ".tasks[] | select(.id == $task_id) | .title" "$tasks_file")
            local task_desc=$(jq -r ".tasks[] | select(.id == $task_id) | .description // \"\"" "$tasks_file")
            local task_criteria=$(jq -r ".tasks[] | select(.id == $task_id) | .acceptance_criteria // \"\"" "$tasks_file")
            local task_complexity=$(jq -r ".tasks[] | select(.id == $task_id) | .estimated_complexity // \"moderate\"" "$tasks_file")
            local task_deps=$(jq -r ".tasks[] | select(.id == $task_id) | .dependencies // [] | join(\", \")" "$tasks_file")
            local task_category=$(jq -r ".tasks[] | select(.id == $task_id) | .category // \"feature\"" "$tasks_file")
            local task_prd_section=$(jq -r ".tasks[] | select(.id == $task_id) | .prd_section // \"\"" "$tasks_file")

            local prompt_file="$prompts_dir/openspec-t${task_id}.md"

            # Build prompt file (same logic as sequential mode)
            if [[ -n "$spec_writer_prompt" ]]; then
                echo "$spec_writer_prompt" > "$prompt_file"
                cat >> "$prompt_file" << PROMPT

---

# Task: Generate OpenSpec for Task $task_id

Apply your specification expertise to create a detailed OpenSpec for TDD implementation.

## Task Details
PROMPT
            else
                cat > "$prompt_file" << PROMPT
# Task: Generate OpenSpec for Task $task_id

You are a specification writer creating a detailed OpenSpec for TDD implementation.

## Task Details
PROMPT
            fi

            cat >> "$prompt_file" << PROMPT

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
PROMPT

            # Add supplementary agent expertise if available
            if [[ -n "$interface_definer_prompt" || -n "$test_strategist_prompt" || -n "$security_specifier_prompt" || -n "$edge_case_hunter_prompt" ]]; then
                cat >> "$prompt_file" << SUPPLEMENTARY

## Additional Expert Guidance

SUPPLEMENTARY
                if [[ -n "$interface_definer_prompt" ]]; then
                    cat >> "$prompt_file" << SUPPLEMENTARY
### Interface Design (from interface-definer agent)
Focus on precise input/output contracts. Define clear validation rules, error conditions, and data types.

SUPPLEMENTARY
                fi
                if [[ -n "$test_strategist_prompt" ]]; then
                    cat >> "$prompt_file" << SUPPLEMENTARY
### Test Strategy (from test-strategist agent)
Design comprehensive test coverage. Include unit, integration, and scenario-based tests with clear priorities.

SUPPLEMENTARY
                fi
                if [[ -n "$security_specifier_prompt" ]]; then
                    cat >> "$prompt_file" << SUPPLEMENTARY
### Security Requirements (from security-specifier agent)
Identify authentication, authorization, input validation, and data protection requirements.

SUPPLEMENTARY
                fi
                if [[ -n "$edge_case_hunter_prompt" ]]; then
                    cat >> "$prompt_file" << SUPPLEMENTARY
### Edge Cases (from edge-case-hunter agent)
Find boundary conditions, error paths, and unusual scenarios that could cause failures.

SUPPLEMENTARY
                fi
            fi

            cat >> "$prompt_file" << PROMPT

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

            pending_tasks+=("$task_id")
            pending_prompts+=("$prompt_file")
            echo -e "    ${DIM}Prepared prompt for task $task_id${NC}"
        done

        local total_pending=${#pending_tasks[@]}
        echo ""
        echo -e "  ${GREEN}✓${NC} Prepared $total_pending prompt files"
        echo -e "  ${DIM}Skipped $skipped existing specs${NC}"
        echo ""

        if [[ "$total_pending" -eq 0 ]]; then
            echo -e "  ${GREEN}✓${NC} All specs already generated"
        else
            echo -e "  ${DIM}Phase 2: Invoking LLM in parallel ($parallel_workers workers)...${NC}"
            echo ""

            # Create a temporary script for parallel execution
            local parallel_script="$prompts_dir/_parallel_invoke.sh"
            cat > "$parallel_script" << 'PARALLEL_SCRIPT'
#!/bin/bash
# Parallel spec generation worker script
# Arguments: task_id prompt_file raw_output_file spec_file

task_id="$1"
prompt_file="$2"
raw_output="$3"
spec_file="$4"
atomic_root="$5"

# Source atomic functions if available
if [[ -f "$atomic_root/lib/atomic.sh" ]]; then
    source "$atomic_root/lib/atomic.sh" 2>/dev/null
fi

# Invoke LLM
if type atomic_invoke &>/dev/null; then
    atomic_invoke "$prompt_file" "$raw_output" "OpenSpec T$task_id" --model=sonnet 2>/dev/null
else
    # Fallback: direct claude invocation
    if command -v claude &>/dev/null; then
        claude -p "$(cat "$prompt_file")" --output-format text --max-turns 10 > "$raw_output" 2>/dev/null
    else
        echo "ERROR: No LLM invocation method available" >&2
        exit 1
    fi
fi

# Validate and process output
if [[ -f "$raw_output" ]] && [[ -s "$raw_output" ]]; then
    if jq -e . "$raw_output" &>/dev/null; then
        cp "$raw_output" "$spec_file"
        echo "OK:$task_id"
    elif grep -q '```json' "$raw_output"; then
        # Try to extract JSON from markdown
        sed -n '/```json/,/```/p' "$raw_output" | sed '1d;$d' > "${raw_output}.tmp"
        if jq -e . "${raw_output}.tmp" &>/dev/null; then
            mv "${raw_output}.tmp" "$spec_file"
            echo "REPAIRED:$task_id"
        else
            rm -f "${raw_output}.tmp"
            echo "FAILED:$task_id:invalid_json_after_repair"
        fi
    else
        echo "FAILED:$task_id:invalid_json"
    fi
else
    echo "FAILED:$task_id:empty_output"
fi
PARALLEL_SCRIPT
            chmod +x "$parallel_script"

            # Run parallel invocations using background job pool
            local results_file="$prompts_dir/_parallel_results.txt"
            > "$results_file"
            local running_jobs=0
            local completed=0

            echo -e "  ${DIM}Starting $total_pending spec generations with $parallel_workers workers...${NC}"
            echo ""

            for i in "${!pending_tasks[@]}"; do
                local tid="${pending_tasks[$i]}"
                local pf="${pending_prompts[$i]}"
                local raw="$prompts_dir/openspec-t${tid}-raw.json"
                local sf="$specs_dir/spec-t${tid}.json"

                # Launch background job
                (
                    "$parallel_script" "$tid" "$pf" "$raw" "$sf" "$ATOMIC_ROOT" >> "$results_file" 2>&1
                ) &

                ((running_jobs++))

                # Wait if we've hit the worker limit
                if [[ "$running_jobs" -ge "$parallel_workers" ]]; then
                    wait -n 2>/dev/null || wait  # wait -n for bash 4.3+, fallback for older
                    ((running_jobs--))
                    ((completed++))
                    # Show progress
                    printf "\r  ${DIM}Progress: %d/%d specs${NC}    " "$completed" "$total_pending"
                fi
            done

            # Wait for remaining jobs
            while [[ "$running_jobs" -gt 0 ]]; do
                wait -n 2>/dev/null || wait
                ((running_jobs--))
                ((completed++))
                printf "\r  ${DIM}Progress: %d/%d specs${NC}    " "$completed" "$total_pending"
            done
            echo ""

            # Process results
            echo ""
            echo -e "  ${DIM}Phase 3: Processing results...${NC}"
            echo ""

            while IFS=: read -r status tid detail; do
                case "$status" in
                    OK)
                        echo -e "    ${GREEN}✓${NC} spec-t${tid}.json"
                        ((generated++))
                        ;;
                    REPAIRED)
                        echo -e "    ${GREEN}✓${NC} spec-t${tid}.json (repaired)"
                        ((generated++))
                        ;;
                    FAILED)
                        echo -e "    ${RED}✗${NC} spec-t${tid}.json ($detail)"
                        ((failed++))
                        ;;
                esac
            done < "$results_file"

            # Cleanup temporary files
            rm -f "$parallel_script" "$results_file"
        fi

        echo ""

    else
        # Sequential mode (auto, guided, batch, select)
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

        # Build prompt with loaded agent expertise if available
        if [[ -n "$spec_writer_prompt" ]]; then
            echo "$spec_writer_prompt" > "$prompt_file"
            cat >> "$prompt_file" << PROMPT

---

# Task: Generate OpenSpec for Task $task_id

Apply your specification expertise to create a detailed OpenSpec for TDD implementation.

## Task Details
PROMPT
        else
            cat > "$prompt_file" << PROMPT
# Task: Generate OpenSpec for Task $task_id

You are a specification writer creating a detailed OpenSpec for TDD implementation.

## Task Details
PROMPT
        fi

        cat >> "$prompt_file" << PROMPT

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
PROMPT

        # Add supplementary agent expertise if available
        if [[ -n "$interface_definer_prompt" || -n "$test_strategist_prompt" || -n "$security_specifier_prompt" || -n "$edge_case_hunter_prompt" ]]; then
            cat >> "$prompt_file" << SUPPLEMENTARY

## Additional Expert Guidance

SUPPLEMENTARY
            if [[ -n "$interface_definer_prompt" ]]; then
                cat >> "$prompt_file" << SUPPLEMENTARY
### Interface Design (from interface-definer agent)
Focus on precise input/output contracts. Define clear validation rules, error conditions, and data types.

SUPPLEMENTARY
            fi
            if [[ -n "$test_strategist_prompt" ]]; then
                cat >> "$prompt_file" << SUPPLEMENTARY
### Test Strategy (from test-strategist agent)
Design comprehensive test coverage. Include unit, integration, and scenario-based tests with clear priorities.

SUPPLEMENTARY
            fi
            if [[ -n "$security_specifier_prompt" ]]; then
                cat >> "$prompt_file" << SUPPLEMENTARY
### Security Requirements (from security-specifier agent)
Identify authentication, authorization, input validation, and data protection requirements.

SUPPLEMENTARY
            fi
            if [[ -n "$edge_case_hunter_prompt" ]]; then
                cat >> "$prompt_file" << SUPPLEMENTARY
### Edge Cases (from edge-case-hunter agent)
Find boundary conditions, error paths, and unusual scenarios that could cause failures.

SUPPLEMENTARY
            fi
        fi

        cat >> "$prompt_file" << PROMPT

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
            read -e -p "  [Enter] continue, [e]dit, [s]kip: " review_choice || true
            case "$review_choice" in
                e|edit)
                    echo -e "  ${DIM}Edit the spec file: $spec_file${NC}"
                    read -e -p "  Press Enter when done editing..." || true
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
            read -e -p "  Press Enter to continue..." || true
            echo ""
        fi
    done

    echo ""

    fi  # End of sequential mode else block

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

    local total_specs=$(find "$specs_dir" -name "spec-*.json" | wc -l | tr -d ' ')
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
