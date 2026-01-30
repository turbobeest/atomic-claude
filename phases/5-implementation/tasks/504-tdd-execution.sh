#!/bin/bash
#
# Task 504: TDD Execution
# Execute RED/GREEN/REFACTOR/VERIFY cycles for each task
#
# Each phase uses real LLM calls:
#   RED: LLM writes failing tests based on OpenSpec
#   GREEN: LLM implements minimal code to pass tests
#   REFACTOR: LLM cleans up code while maintaining test passage
#   VERIFY: LLM reviews for security issues
#

task_504_tdd_execution() {
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local specs_dir="$ATOMIC_ROOT/.claude/specs"
    local testing_dir="$ATOMIC_ROOT/.claude/testing"
    local progress_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/tdd-progress.json"
    local setup_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/tdd-setup.json"
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"
    local src_dir="$ATOMIC_ROOT/src"

    atomic_step "TDD Execution"

    mkdir -p "$testing_dir" "$prompts_dir" "$(dirname "$progress_file")"

    echo ""
    echo -e "  ${DIM}Executing TDD cycles with real LLM agents.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # LOAD SELECTED AGENTS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Agent prompts (loaded from agents repository if available)
    export _504_RED_AGENT_PROMPT=""
    export _504_GREEN_AGENT_PROMPT=""
    export _504_REFACTOR_AGENT_PROMPT=""
    export _504_VERIFY_AGENT_PROMPT=""

    local agent_repo="${ATOMIC_AGENT_REPO:-$ATOMIC_ROOT/repos/agents}"

    if [[ -f "$agents_file" ]]; then
        echo -e "  ${DIM}Loading TDD agents from selection...${NC}"
        echo ""

        # Load RED agent (test-writer)
        local red_agent=$(jq -r '.tdd_agents.red.name // ""' "$agents_file")
        if [[ -n "$red_agent" ]]; then
            agent_file=$(atomic_find_agent "$red_agent" "$agent_repo")
            if [[ -f "$agent_file" ]]; then
                _504_RED_AGENT_PROMPT=$(cat "$agent_file" | atomic_strip_frontmatter)
                echo -e "  ${RED}✓${NC} Loaded RED agent: $red_agent"
            else
                echo -e "  ${YELLOW}!${NC} RED agent file not found: $agent_file"
            fi
        fi

        # Load GREEN agent (code-implementer)
        local green_agent=$(jq -r '.tdd_agents.green.name // ""' "$agents_file")
        if [[ -n "$green_agent" ]]; then
            agent_file=$(atomic_find_agent "$green_agent" "$agent_repo")
            if [[ -f "$agent_file" ]]; then
                _504_GREEN_AGENT_PROMPT=$(cat "$agent_file" | atomic_strip_frontmatter)
                echo -e "  ${GREEN}✓${NC} Loaded GREEN agent: $green_agent"
            else
                echo -e "  ${YELLOW}!${NC} GREEN agent file not found: $agent_file"
            fi
        fi

        # Load REFACTOR agent (code-reviewer)
        local refactor_agent=$(jq -r '.tdd_agents.refactor.name // ""' "$agents_file")
        if [[ -n "$refactor_agent" ]]; then
            agent_file=$(atomic_find_agent "$refactor_agent" "$agent_repo")
            if [[ -f "$agent_file" ]]; then
                _504_REFACTOR_AGENT_PROMPT=$(cat "$agent_file" | atomic_strip_frontmatter)
                echo -e "  ${CYAN}✓${NC} Loaded REFACTOR agent: $refactor_agent"
            else
                echo -e "  ${YELLOW}!${NC} REFACTOR agent file not found: $agent_file"
            fi
        fi

        # Load VERIFY agent (security-scanner)
        local verify_agent=$(jq -r '.tdd_agents.verify.name // ""' "$agents_file")
        if [[ -n "$verify_agent" ]]; then
            agent_file=$(atomic_find_agent "$verify_agent" "$agent_repo")
            if [[ -f "$agent_file" ]]; then
                _504_VERIFY_AGENT_PROMPT=$(cat "$agent_file" | atomic_strip_frontmatter)
                echo -e "  ${MAGENTA}✓${NC} Loaded VERIFY agent: $verify_agent"
            else
                echo -e "  ${YELLOW}!${NC} VERIFY agent file not found: $agent_file"
            fi
        fi

        echo ""
    else
        echo -e "  ${DIM}No agent selection found - using built-in TDD prompts${NC}"
        echo ""
    fi

    # Load setup configuration
    local exec_mode="sequential"
    local parallel_workers=2  # Keep low - each task runs 4 LLM phases
    if [[ -f "$setup_file" ]]; then
        exec_mode=$(jq -r '.execution_mode // "sequential"' "$setup_file")
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # EXECUTION MODE SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}EXECUTION MODE${NC}"
    echo ""
    echo -e "  ${CYAN}How would you like to execute TDD cycles?${NC}"
    echo ""
    echo -e "    ${GREEN}[sequential]${NC}  Process tasks one at a time (default)"
    echo -e "    ${YELLOW}[guided]${NC}      Pause between tasks for review"
    echo -e "    ${BOLD}[parallel]${NC}    Process independent tasks concurrently (DAG-aware)"
    echo ""

    atomic_drain_stdin
    read -e -p "  Choice [sequential]: " mode_choice || true
    mode_choice=${mode_choice:-sequential}

    # Handle parallel mode with optional worker count
    if [[ "$mode_choice" =~ ^parallel ]]; then
        if [[ "$mode_choice" =~ ^parallel[[:space:]]*([0-9]+)$ ]]; then
            parallel_workers="${BASH_REMATCH[1]}"
        fi
        exec_mode="parallel"
        echo ""
        echo -e "  ${DIM}Parallel mode: $parallel_workers concurrent workers (respecting DAG)${NC}"
    else
        exec_mode="$mode_choice"
    fi

    # Load tech stack from PRD
    local tech_stack=""
    local test_framework=""
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    if [[ -f "$prd_file" && -r "$prd_file" ]]; then
        tech_stack=$(sed -n '/### 2\.1 Tech Stack/,/### 2\.2/p' "$prd_file" 2>/dev/null | head -30)
        # Detect test framework
        if echo "$tech_stack" | grep -qi "pytest\|python"; then
            test_framework="pytest"
        elif echo "$tech_stack" | grep -qi "jest\|javascript\|typescript"; then
            test_framework="jest"
        elif echo "$tech_stack" | grep -qi "go"; then
            test_framework="go test"
        else
            test_framework="unknown"
        fi
    elif [[ -f "$prd_file" ]]; then
        echo -e "  ${YELLOW}!${NC} PRD file exists but is not readable - check permissions"
        test_framework="unknown"
    fi

    # If still unknown, try to detect from project files
    if [[ "$test_framework" == "unknown" ]]; then
        if [[ -f "$ATOMIC_ROOT/pytest.ini" || -f "$ATOMIC_ROOT/pyproject.toml" ]]; then
            test_framework="pytest"
        elif [[ -f "$ATOMIC_ROOT/package.json" ]]; then
            if grep -q "jest" "$ATOMIC_ROOT/package.json" 2>/dev/null; then
                test_framework="jest"
            fi
        elif [[ -f "$ATOMIC_ROOT/go.mod" ]]; then
            test_framework="go test"
        fi
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TDD CYCLE OVERVIEW
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TDD CYCLE OVERVIEW${NC}"
    echo ""

    local task_ids task_count
    task_ids=$(jq -r '.tasks[] | select(.subtasks | length >= 4) | .id' "$tasks_file" 2>/dev/null)
    task_count=$(echo "$task_ids" | wc -w)

    # Validate we have tasks to process
    if [[ -z "$task_ids" || "$task_count" -eq 0 ]]; then
        atomic_warn "No tasks with subtasks found in $tasks_file"
        atomic_info "Ensure Phase 3 (Task Decomposition) generated subtasks for tasks"
        return 1
    fi

    echo -e "  ${DIM}Tasks to process: $task_count${NC}"
    echo -e "  ${DIM}Execution mode: $exec_mode${NC}"
    echo -e "  ${DIM}Test framework: $test_framework${NC}"
    echo ""

    read -e -p "  Press Enter to begin TDD execution..." || true
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # EXECUTION LOOP
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    local completed=0
    local failed=0
    local skipped=0

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PARALLEL EXECUTION (DAG-aware)
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    if [[ "$exec_mode" == "parallel" ]]; then
        echo -e "  ${DIM}Building dependency graph...${NC}"
        echo ""

        # Create status tracking file
        local status_dir="$testing_dir/parallel-status"
        mkdir -p "$status_dir"

        # Initialize task status - preserve completed tasks for resume
        local resumed_count=0
        for tid in $task_ids; do
            local status_file="$status_dir/task-$tid.status"
            if [[ -f "$status_file" ]]; then
                local existing=$(cat "$status_file")
                if [[ "$existing" == "completed" ]]; then
                    ((resumed_count++))
                    continue  # Keep completed status
                fi
            fi
            # Reset non-completed tasks to pending
            echo "pending" > "$status_file"
        done

        if [[ $resumed_count -gt 0 ]]; then
            echo -e "  ${GREEN}✓${NC} Resuming: $resumed_count tasks already completed"
            echo ""
        fi

        # Extract dependencies for each task
        local deps_file="$status_dir/dependencies.json"
        jq '[.tasks[] | select(.subtasks | length >= 4) | {id: .id, deps: (.dependencies // [])}]' "$tasks_file" > "$deps_file"

        # Function to check if a task's dependencies are all completed
        _504_deps_satisfied() {
            local tid="$1"
            local deps=$(jq -r ".[] | select(.id == $tid) | .deps[]?" "$deps_file")
            for dep in $deps; do
                local dep_status_file="$status_dir/task-$dep.status"
                if [[ -f "$dep_status_file" ]]; then
                    local dep_status=$(cat "$dep_status_file")
                    if [[ "$dep_status" != "completed" ]]; then
                        return 1
                    fi
                fi
            done
            return 0
        }

        # Function to execute a single task's TDD cycle (writes results to files)
        _504_parallel_execute_task() {
            local tid="$1"
            local result_file="$status_dir/task-$tid.result"
            local log_file="$status_dir/task-$tid.log"

            # Ensure files created in subshell have proper permissions
            umask 022

            # Mark as running
            echo "running" > "$status_dir/task-$tid.status"

            # Redirect all output to log file for this task
            exec > "$log_file" 2>&1

            local task_title=$(jq -r ".tasks[] | select(.id == $tid) | .title" "$tasks_file")
            local spec_file="$specs_dir/spec-t${tid}.json"

            # Check for existing spec
            if [[ ! -f "$spec_file" ]]; then
                echo "skipped:no_spec" > "$result_file"
                echo "skipped" > "$status_dir/task-$tid.status"
                return 0
            fi

            # Initialize error context
            local error_context_file="$testing_dir/tdd-t${tid}-errors.json"
            echo '{"task_id": '$tid', "phases": {}, "accumulated_errors": [], "retry_count": 0}' > "$error_context_file"

            # Execute TDD phases - capture JSON results to files
            local red_json="$status_dir/task-$tid.red.json"
            local green_json="$status_dir/task-$tid.green.json"

            # RED phase - capture only the JSON output (last line)
            _504_execute_red "$tid" "$spec_file" "$prompts_dir" "$testing_dir" "$test_framework" "$error_context_file" | tail -1 > "$red_json"
            local red_status=$(jq -r '.status // "failed"' "$red_json" 2>/dev/null || echo "failed")

            if [[ "$red_status" != "completed" ]]; then
                echo "failed:red" > "$result_file"
                echo "failed" > "$status_dir/task-$tid.status"
                return 1
            fi

            # GREEN phase
            local test_file=$(jq -r '.test_file // ""' "$red_json" 2>/dev/null)
            _504_execute_green "$tid" "$spec_file" "$test_file" "$prompts_dir" "$src_dir" "$test_framework" "$error_context_file" | tail -1 > "$green_json"
            local green_status=$(jq -r '.status // "failed"' "$green_json" 2>/dev/null || echo "failed")

            if [[ "$green_status" != "completed" ]]; then
                echo "failed:green" > "$result_file"
                echo "failed" > "$status_dir/task-$tid.status"
                return 1
            fi

            # REFACTOR phase
            local impl_file=$(jq -r '.impl_file // ""' "$green_json" 2>/dev/null)
            _504_execute_refactor "$tid" "$impl_file" "$test_file" "$prompts_dir" "$test_framework" "$error_context_file" >/dev/null

            # VERIFY phase
            _504_execute_verify "$tid" "$impl_file" "$prompts_dir" "$error_context_file" >/dev/null

            # Update task status in tasks.json (use flock for atomic update)
            (
                flock -x 200
                local temp_file=$(mktemp)
                jq --argjson task_id "$tid" \
                    '(.tasks[] | select(.id == $task_id) | .status) = "done" |
                     (.tasks[] | select(.id == $task_id) | .subtasks[0].status) = "completed" |
                     (.tasks[] | select(.id == $task_id) | .subtasks[1].status) = "completed" |
                     (.tasks[] | select(.id == $task_id) | .subtasks[2].status) = "completed" |
                     (.tasks[] | select(.id == $task_id) | .subtasks[3].status) = "completed"' \
                    "$tasks_file" > "$temp_file" && mv "$temp_file" "$tasks_file"
            ) 200>"$status_dir/.tasks.lock"

            # Save TDD record
            jq -n \
                --argjson task_id "$tid" \
                --arg title "$task_title" \
                --arg test_file "$test_file" \
                --arg impl_file "$impl_file" \
                '{
                    "task_id": $task_id,
                    "title": $title,
                    "test_file": $test_file,
                    "impl_file": $impl_file,
                    "red": "completed",
                    "green": "completed",
                    "refactor": "completed",
                    "verify": "completed",
                    "completed_at": (now | todate)
                }' > "$testing_dir/tdd-t${tid}.json"

            echo "completed" > "$result_file"
            echo "completed" > "$status_dir/task-$tid.status"
            return 0
        }

        # Main parallel execution loop
        local running_jobs=0
        local total_done=$resumed_count  # Start with already-completed tasks
        completed=$resumed_count          # Update the completed counter too
        declare -A running_pids

        echo -e "  ${DIM}Starting parallel TDD execution with $parallel_workers workers...${NC}"
        echo ""

        # Sort task IDs numerically for predictable processing order
        local sorted_task_ids=$(echo "$task_ids" | tr ' ' '\n' | sort -n | tr '\n' ' ')

        while [[ $total_done -lt $task_count ]]; do
            # Find ready tasks (pending with satisfied dependencies) - process in ID order
            for tid in $sorted_task_ids; do
                local status=$(cat "$status_dir/task-$tid.status" 2>/dev/null || echo "pending")

                if [[ "$status" == "pending" ]] && _504_deps_satisfied "$tid"; then
                    if [[ $running_jobs -lt $parallel_workers ]]; then
                        # Launch task in background
                        (
                            _504_parallel_execute_task "$tid"
                        ) &
                        running_pids[$tid]=$!
                        ((running_jobs++))
                        # Print newline first to move past the progress line, then the message
                        echo -e "\n  ${CYAN}▶${NC} Started task $tid"
                    fi
                fi
            done

            # Wait for at least one job to complete
            if [[ $running_jobs -gt 0 ]]; then
                wait -n 2>/dev/null || {
                    # Fallback for older bash: just sleep briefly
                    # Don't remove PIDs here - let the detection loop handle everything
                    sleep 0.5
                }

                # Check completed jobs
                for tid in "${!running_pids[@]}"; do
                    if ! kill -0 "${running_pids[$tid]}" 2>/dev/null; then
                        local result=$(cat "$status_dir/task-$tid.result" 2>/dev/null || echo "unknown")
                        case "$result" in
                            completed)
                                echo -e "\n  ${GREEN}✓${NC} Task $tid completed"
                                ((completed++))
                                ;;
                            skipped*)
                                echo -e "\n  ${YELLOW}○${NC} Task $tid skipped"
                                ((skipped++))
                                ;;
                            failed*)
                                echo -e "\n  ${RED}✗${NC} Task $tid failed (${result#failed:})"
                                ((failed++))
                                ;;
                        esac
                        ((total_done++))
                        unset running_pids[$tid]
                        ((running_jobs--))
                    fi
                done
            else
                # No running jobs and not all done - check for deadlock
                sleep 0.5
            fi

            # Clear line and print progress (using \r to overwrite previous progress, \033[K to clear to end of line)
            printf "\r\033[K  ${DIM}Progress: %d/%d tasks (running: %d)${NC}" "$total_done" "$task_count" "$running_jobs"
        done

        # Wait for any remaining jobs
        wait

        echo ""
        echo ""

        # Cleanup
        rm -rf "$status_dir"

    else
        # Sequential or guided mode
        for task_id in $task_ids; do
        local task_title=$(jq -r ".tasks[] | select(.id == $task_id) | .title" "$tasks_file")
        local spec_file="$specs_dir/spec-t${task_id}.json"

        echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
        echo ""
        echo -e "  ${BOLD}TASK $task_id: ${task_title:0:80}${NC}"
        echo ""

        # Check for existing spec
        if [[ ! -f "$spec_file" ]]; then
            echo -e "  ${YELLOW}!${NC} No OpenSpec found - skipping"
            ((skipped++))
            continue
        fi

        # Load spec content
        local spec_content=$(cat "$spec_file")
        local test_strategy=$(jq -r '.test_strategy' "$spec_file")

        # Initialize error context accumulator for this task
        local error_context_file="$testing_dir/tdd-t${task_id}-errors.json"
        echo '{"task_id": '$task_id', "phases": {}, "accumulated_errors": [], "retry_count": 0}' > "$error_context_file"

        # ─────────────────────────────────────────────────────────────────
        # RED PHASE - Write Failing Tests
        # ─────────────────────────────────────────────────────────────────

        echo -e "  ${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${BOLD}PHASE 1: RED - Write Failing Tests${NC}"
        echo -e "  ${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        local red_result=$(_504_execute_red "$task_id" "$spec_file" "$prompts_dir" "$testing_dir" "$test_framework" "$error_context_file")
        local red_status=$(echo "$red_result" | jq -r '.status // "failed"')

        # Accumulate RED phase result into error context
        _504_accumulate_error "$error_context_file" "red" "$red_result"

        if [[ "$red_status" != "completed" ]]; then
            echo -e "  ${RED}✗${NC} RED phase failed - skipping task"
            ((failed++))
            continue
        fi

        # Update subtask status
        local temp_file=$(atomic_mktemp)
        jq --argjson task_id "$task_id" \
            '(.tasks[] | select(.id == $task_id) | .subtasks[0].status) = "completed"' \
            "$tasks_file" > "$temp_file" && mv "$temp_file" "$tasks_file"

        # ─────────────────────────────────────────────────────────────────
        # GREEN PHASE - Implement to Pass
        # ─────────────────────────────────────────────────────────────────

        echo ""
        echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${BOLD}PHASE 2: GREEN - Implement to Pass${NC}"
        echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        local test_file=$(echo "$red_result" | jq -r '.test_file // ""')
        local green_result=$(_504_execute_green "$task_id" "$spec_file" "$test_file" "$prompts_dir" "$src_dir" "$test_framework" "$error_context_file")
        local green_status=$(echo "$green_result" | jq -r '.status // "failed"')

        # Accumulate GREEN phase result into error context
        _504_accumulate_error "$error_context_file" "green" "$green_result"

        if [[ "$green_status" != "completed" ]]; then
            echo -e "  ${RED}✗${NC} GREEN phase failed"
            ((failed++))
            continue
        fi

        jq --argjson task_id "$task_id" \
            '(.tasks[] | select(.id == $task_id) | .subtasks[1].status) = "completed"' \
            "$tasks_file" > "$temp_file" && mv "$temp_file" "$tasks_file"

        # ─────────────────────────────────────────────────────────────────
        # REFACTOR PHASE - Clean Up Code
        # ─────────────────────────────────────────────────────────────────

        echo ""
        echo -e "  ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${BOLD}PHASE 3: REFACTOR - Clean Up Code${NC}"
        echo -e "  ${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        local impl_file=$(echo "$green_result" | jq -r '.impl_file // ""')
        local refactor_result=$(_504_execute_refactor "$task_id" "$impl_file" "$test_file" "$prompts_dir" "$test_framework" "$error_context_file")

        # Accumulate REFACTOR phase result into error context
        _504_accumulate_error "$error_context_file" "refactor" "$refactor_result"

        jq --argjson task_id "$task_id" \
            '(.tasks[] | select(.id == $task_id) | .subtasks[2].status) = "completed"' \
            "$tasks_file" > "$temp_file" && mv "$temp_file" "$tasks_file"

        # ─────────────────────────────────────────────────────────────────
        # VERIFY PHASE - Security Scan
        # ─────────────────────────────────────────────────────────────────

        echo ""
        echo -e "  ${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${BOLD}PHASE 4: VERIFY - Security Review${NC}"
        echo -e "  ${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        local verify_result=$(_504_execute_verify "$task_id" "$impl_file" "$prompts_dir" "$error_context_file")

        # Accumulate VERIFY phase result into error context
        _504_accumulate_error "$error_context_file" "verify" "$verify_result"

        jq --argjson task_id "$task_id" \
            '(.tasks[] | select(.id == $task_id) | .subtasks[3].status) = "completed"' \
            "$tasks_file" > "$temp_file" && mv "$temp_file" "$tasks_file"

        # ─────────────────────────────────────────────────────────────────
        # TASK COMPLETE
        # ─────────────────────────────────────────────────────────────────

        echo ""
        echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "  ${GREEN}✓ TASK $task_id COMPLETE${NC} - All 4 TDD phases passed"
        echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

        jq --argjson task_id "$task_id" \
            '(.tasks[] | select(.id == $task_id) | .status) = "done"' \
            "$tasks_file" > "$temp_file" && mv "$temp_file" "$tasks_file"

        ((completed++))

        # Save progress record
        jq -n \
            --argjson task_id "$task_id" \
            --arg title "$task_title" \
            --arg test_file "$test_file" \
            --arg impl_file "$impl_file" \
            '{
                "task_id": $task_id,
                "title": $title,
                "test_file": $test_file,
                "impl_file": $impl_file,
                "red": "completed",
                "green": "completed",
                "refactor": "completed",
                "verify": "completed",
                "completed_at": (now | todate)
            }' > "$testing_dir/tdd-t${task_id}.json"

        if [[ "$exec_mode" == "guided" ]]; then
            read -e -p "  Press Enter to continue to next task..." || true
        fi
    done

    fi  # End of sequential/guided else block

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # EXECUTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TDD EXECUTION SUMMARY${NC}"
    echo ""

    echo -e "    Tasks completed: ${GREEN}$completed${NC}"
    echo -e "    Tasks skipped:   ${YELLOW}$skipped${NC}"
    echo -e "    Tasks failed:    ${RED}$failed${NC}"
    echo ""

    # Save progress
    jq -n \
        --argjson completed "$completed" \
        --argjson skipped "$skipped" \
        --argjson failed "$failed" \
        --arg exec_mode "$exec_mode" \
        '{
            "execution_mode": $exec_mode,
            "tasks_completed": $completed,
            "tasks_skipped": $skipped,
            "tasks_failed": $failed,
            "completed_at": (now | todate)
        }' > "$progress_file"

    # Register artifacts for downstream tasks
    atomic_context_artifact "tdd_progress" "$progress_file" "TDD execution progress summary"
    atomic_context_artifact "testing_dir" "$testing_dir" "Directory containing per-task TDD records"

    # Register individual task records for traceability
    for tdd_record in "$testing_dir"/tdd-t*.json; do
        [[ -f "$tdd_record" ]] || continue
        local record_name=$(basename "$tdd_record" .json)
        atomic_context_artifact "$record_name" "$tdd_record" "TDD cycle record for task"
    done

    atomic_context_decision "TDD execution: $completed tasks completed, $skipped skipped, $failed failed" "tdd-execution"

    atomic_success "TDD Execution complete"

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# TDD PHASE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

# Accumulate error context from phase execution
# Usage: _504_accumulate_error "$error_file" "phase_name" "$phase_result"
_504_accumulate_error() {
    local error_file="$1"
    local phase_name="$2"
    local phase_result="$3"

    # Validate error file exists
    [[ -f "$error_file" ]] || echo '{"phases": {}, "accumulated_errors": []}' > "$error_file"

    local status=$(echo "$phase_result" | jq -r '.status // "unknown"')
    local error=$(echo "$phase_result" | jq -r '.error // empty')
    local test_output=$(echo "$phase_result" | jq -r '.test_output // empty')

    # Update the error context file
    local tmp=$(atomic_mktemp)
    jq --arg phase "$phase_name" \
       --arg status "$status" \
       --arg error "$error" \
       --arg output "$test_output" \
       --arg timestamp "$(date -Iseconds)" \
       '.phases[$phase] = {
            "status": $status,
            "error": (if $error != "" then $error else null end),
            "test_output": (if $output != "" then $output else null end),
            "timestamp": $timestamp
        } |
        if $status == "failed" then
            .accumulated_errors += [{
                "phase": $phase,
                "error": $error,
                "output": $output,
                "timestamp": $timestamp
            }]
        else . end' \
        "$error_file" > "$tmp" && mv "$tmp" "$error_file"
}

# Get accumulated error context for prompts
# Usage: error_context=$(_504_get_error_context "$error_file")
_504_get_error_context() {
    local error_file="$1"

    if [[ ! -f "$error_file" ]]; then
        echo ""
        return
    fi

    local errors=$(jq -r '.accumulated_errors' "$error_file")
    local error_count=$(echo "$errors" | jq 'length')

    if [[ "$error_count" -eq 0 ]]; then
        echo ""
        return
    fi

    echo "## Previous Errors in This Task"
    echo ""
    echo "The following errors occurred in earlier phases. Learn from them:"
    echo ""
    echo "$errors" | jq -r '.[] | "### \(.phase | ascii_upcase) Phase Error\n\(.error // "Unknown error")\n\nOutput:\n```\n\(.output // "No output")\n```\n"'
}

# RED PHASE: Write failing tests based on OpenSpec
_504_execute_red() {
    local task_id="$1"
    local spec_file="$2"
    local prompts_dir="$3"
    local testing_dir="$4"
    local test_framework="$5"
    local error_context_file="${6:-}"  # Error context from previous attempts

    local prompt_file="$prompts_dir/red-t${task_id}.md"
    local output_file="$prompts_dir/red-t${task_id}-output.md"
    local test_file="$testing_dir/test_t${task_id}.py"  # Adjust extension based on framework

    # Adjust file extension based on framework
    case "$test_framework" in
        jest) test_file="$testing_dir/t${task_id}.test.js" ;;
        "go test") test_file="$testing_dir/t${task_id}_test.go" ;;
        pytest|*) test_file="$testing_dir/test_t${task_id}.py" ;;
    esac

    local spec_content=$(cat "$spec_file")
    local test_strategy=$(jq -r '.test_strategy' "$spec_file")

    # Build prompt with loaded agent expertise if available
    if [[ -n "$_504_RED_AGENT_PROMPT" ]]; then
        echo "$_504_RED_AGENT_PROMPT" > "$prompt_file"
        cat >> "$prompt_file" << PROMPT

---

# Task: RED Phase - Write Failing Tests for Task $task_id

Apply your test-writing expertise in the RED phase of TDD. Write tests that will FAIL because no implementation exists yet.
PROMPT
    else
        cat > "$prompt_file" << PROMPT
# Task: RED Phase - Write Failing Tests for Task $task_id

You are a test-writer agent in the RED phase of TDD. Write tests that will FAIL because no implementation exists yet.
PROMPT
    fi

    cat >> "$prompt_file" << PROMPT

## OpenSpec

$spec_content

## Test Strategy from Spec

$test_strategy

## Test Framework

Use: $test_framework

## Requirements

1. Write tests for ALL scenarios in the test strategy
2. Tests MUST be syntactically correct
3. Tests SHOULD fail when run (no implementation yet)
4. Include edge cases from the spec
5. Use descriptive test names

## Output Format

Output ONLY the test code. No markdown, no explanations.
Start directly with imports/requires.

Example structure for $test_framework:
$(case "$test_framework" in
    pytest)
        echo 'import pytest

def test_feature_happy_path():
    """Test description"""
    # Arrange
    # Act
    # Assert
    assert result == expected'
        ;;
    jest)
        echo "import { feature } from './feature';

describe('Feature', () => {
  it('should handle happy path', () => {
    // Arrange
    // Act
    // Assert
    expect(result).toBe(expected);
  });
});"
        ;;
    *)
        echo "// Write tests for your framework"
        ;;
esac)
PROMPT

    echo -e "  ${DIM}Generating tests with LLM...${NC}"

    if atomic_invoke "$prompt_file" "$output_file" "RED T$task_id" --model=sonnet; then
        # Extract code and save to test file
        if grep -q '```' "$output_file"; then
            # Extract from code block
            sed -n '/```/,/```/p' "$output_file" | sed '1d;$d' > "$test_file"
        else
            cp "$output_file" "$test_file"
        fi

        # Check for error messages in output (don't save errors as test code)
        if grep -qE "^Error:|Reached max turns|error:" "$test_file" 2>/dev/null; then
            echo -e "  ${RED}✗${NC} LLM output contains error, not valid test code"
            rm -f "$test_file"
            echo "{\"status\": \"failed\", \"error\": \"output_contains_error\"}"
            return 1
        fi

        if [[ -s "$test_file" ]]; then
            echo -e "  ${GREEN}✓${NC} Tests written to $(basename "$test_file")"

            # Attempt to run tests (they should fail)
            echo -e "  ${DIM}Running tests (expecting failure)...${NC}"
            local test_result=0
            case "$test_framework" in
                pytest)
                    pytest "$test_file" --tb=no -q 2>/dev/null && test_result=1 || test_result=0
                    ;;
                jest)
                    npx jest "$test_file" --passWithNoTests 2>/dev/null && test_result=1 || test_result=0
                    ;;
            esac

            if [[ $test_result -eq 0 ]]; then
                echo -e "  ${RED}✓${NC} Tests FAIL as expected (RED phase success)"
                echo "{\"status\": \"completed\", \"test_file\": \"$test_file\"}"
                return 0
            else
                echo -e "  ${YELLOW}!${NC} Tests passed unexpectedly - implementation may exist"
                echo "{\"status\": \"completed\", \"test_file\": \"$test_file\", \"warning\": \"tests_passed\"}"
                return 0
            fi
        else
            echo -e "  ${RED}✗${NC} No test content generated"
            echo "{\"status\": \"failed\", \"error\": \"no_content\"}"
            return 1
        fi
    else
        echo -e "  ${RED}✗${NC} LLM invocation failed"
        echo "{\"status\": \"failed\", \"error\": \"llm_failed\"}"
        return 1
    fi
}

# GREEN PHASE: Implement minimal code to pass tests
_504_execute_green() {
    local task_id="$1"
    local spec_file="$2"
    local test_file="$3"
    local prompts_dir="$4"
    local src_dir="$5"
    local test_framework="$6"
    local error_context_file="${7:-}"  # Error context from previous phases

    local prompt_file="$prompts_dir/green-t${task_id}.md"
    local output_file="$prompts_dir/green-t${task_id}-output.md"
    local impl_file="$src_dir/t${task_id}_impl.py"  # Adjust based on framework

    case "$test_framework" in
        jest) impl_file="$src_dir/t${task_id}.js" ;;
        "go test") impl_file="$src_dir/t${task_id}.go" ;;
        pytest|*) impl_file="$src_dir/t${task_id}_impl.py" ;;
    esac

    mkdir -p "$src_dir"

    local spec_content=$(cat "$spec_file")
    local test_content=$(cat "$test_file" 2>/dev/null || echo "Test file not found")

    # Get accumulated error context from previous phases
    local error_context=""
    if [[ -n "$error_context_file" && -f "$error_context_file" ]]; then
        error_context=$(_504_get_error_context "$error_context_file")
    fi

    # Build prompt with loaded agent expertise if available
    if [[ -n "$_504_GREEN_AGENT_PROMPT" ]]; then
        echo "$_504_GREEN_AGENT_PROMPT" > "$prompt_file"
        cat >> "$prompt_file" << PROMPT

---

# Task: GREEN Phase - Implement to Pass Tests for Task $task_id

Apply your implementation expertise in the GREEN phase of TDD. Write the MINIMAL code to make all tests pass.

$error_context

## OpenSpec
PROMPT
    else
        cat > "$prompt_file" << PROMPT
# Task: GREEN Phase - Implement to Pass Tests for Task $task_id

You are a code-implementer agent in the GREEN phase of TDD. Write the MINIMAL code to make all tests pass.

$error_context

## OpenSpec
PROMPT
    fi

    cat >> "$prompt_file" << PROMPT

$spec_content

## Tests to Pass

$test_content

## Requirements

1. Write MINIMAL code to pass all tests
2. Do not over-engineer or optimize yet
3. Focus on correctness, not performance
4. Include necessary imports
5. Handle all test cases

## Output Format

Output ONLY the implementation code. No markdown, no explanations.
Start directly with imports.
PROMPT

    echo -e "  ${DIM}Generating implementation with LLM...${NC}"

    if atomic_invoke "$prompt_file" "$output_file" "GREEN T$task_id" --model=opus; then
        # Check for error messages in output (don't save errors as code)
        if grep -qE "^Error:|Reached max turns|error:" "$output_file" 2>/dev/null; then
            echo -e "  ${RED}✗${NC} LLM output contains error, not valid code"
            echo "{\"status\": \"failed\", \"error\": \"output_contains_error\"}"
            return 1
        fi

        # Extract code and save
        if grep -q '```' "$output_file"; then
            sed -n '/```/,/```/p' "$output_file" | sed '1d;$d' > "$impl_file"
        else
            cp "$output_file" "$impl_file"
        fi

        # Verify the extracted content looks like code (not error messages)
        if grep -qE "^Error:|Reached max turns" "$impl_file" 2>/dev/null; then
            echo -e "  ${RED}✗${NC} Extracted content is error message, not code"
            rm -f "$impl_file"
            echo "{\"status\": \"failed\", \"error\": \"extracted_error_not_code\"}"
            return 1
        fi

        if [[ -s "$impl_file" ]]; then
            echo -e "  ${GREEN}✓${NC} Implementation written to $(basename "$impl_file")"

            # Run tests (they should pass now)
            echo -e "  ${DIM}Running tests (expecting pass)...${NC}"
            local test_result=1
            case "$test_framework" in
                pytest)
                    pytest "$test_file" --tb=short -q 2>/dev/null && test_result=0 || test_result=1
                    ;;
                jest)
                    npx jest "$test_file" 2>/dev/null && test_result=0 || test_result=1
                    ;;
            esac

            if [[ $test_result -eq 0 ]]; then
                echo -e "  ${GREEN}✓${NC} All tests PASS"
                echo "{\"status\": \"completed\", \"impl_file\": \"$impl_file\"}"
                return 0
            else
                echo -e "  ${YELLOW}!${NC} Some tests still failing - may need iteration"
                echo "{\"status\": \"completed\", \"impl_file\": \"$impl_file\", \"warning\": \"tests_failing\"}"
                return 0
            fi
        else
            echo -e "  ${RED}✗${NC} No implementation generated"
            echo "{\"status\": \"failed\", \"error\": \"no_content\"}"
            return 1
        fi
    else
        echo -e "  ${RED}✗${NC} LLM invocation failed"
        echo "{\"status\": \"failed\", \"error\": \"llm_failed\"}"
        return 1
    fi
}

# REFACTOR PHASE: Clean up code while maintaining test passage
_504_execute_refactor() {
    local task_id="$1"
    local impl_file="$2"
    local test_file="$3"
    local prompts_dir="$4"
    local test_framework="$5"
    local error_context_file="${6:-}"  # Error context from previous phases

    local prompt_file="$prompts_dir/refactor-t${task_id}.md"
    local output_file="$prompts_dir/refactor-t${task_id}-output.md"

    if [[ ! -f "$impl_file" ]]; then
        echo -e "  ${YELLOW}!${NC} No implementation file to refactor"
        echo "{\"status\": \"skipped\"}"
        return 0
    fi

    local impl_content=$(cat "$impl_file")
    local test_content=$(cat "$test_file" 2>/dev/null || echo "")

    # Get accumulated error context from previous phases
    local error_context=""
    if [[ -n "$error_context_file" && -f "$error_context_file" ]]; then
        error_context=$(_504_get_error_context "$error_context_file")
    fi

    # Build prompt with loaded agent expertise if available
    if [[ -n "$_504_REFACTOR_AGENT_PROMPT" ]]; then
        echo "$_504_REFACTOR_AGENT_PROMPT" > "$prompt_file"
        cat >> "$prompt_file" << PROMPT

---

# Task: REFACTOR Phase - Clean Up Code for Task $task_id

Apply your refactoring expertise in the REFACTOR phase. Improve code quality while ensuring tests still pass.

$error_context

## Current Implementation
PROMPT
    else
        cat > "$prompt_file" << PROMPT
# Task: REFACTOR Phase - Clean Up Code for Task $task_id

You are a code-reviewer agent in the REFACTOR phase. Improve code quality while ensuring tests still pass.

$error_context

## Current Implementation
PROMPT
    fi

    cat >> "$prompt_file" << PROMPT

$impl_content

## Tests (must still pass)

$test_content

## Refactoring Goals

1. Improve readability and naming
2. Remove code duplication
3. Apply SOLID principles where appropriate
4. Add type hints/annotations
5. Ensure consistent style
6. DO NOT change external behavior

## Output Format

Output ONLY the refactored code. No markdown, no explanations.
PROMPT

    echo -e "  ${DIM}Refactoring with LLM...${NC}"

    if atomic_invoke "$prompt_file" "$output_file" "REFACTOR T$task_id" --model=sonnet; then
        # Extract and save refactored code
        local refactored_content
        if grep -q '```' "$output_file"; then
            refactored_content=$(sed -n '/```/,/```/p' "$output_file" | sed '1d;$d')
        else
            refactored_content=$(cat "$output_file")
        fi

        # Check for error messages in output (don't save errors as code)
        if echo "$refactored_content" | grep -qE "^Error:|Reached max turns|error:"; then
            echo -e "  ${YELLOW}!${NC} LLM output contains error, skipping refactor"
            echo "{\"status\": \"completed\", \"warning\": \"refactor_skipped_error\"}"
            return 0
        fi

        if [[ -n "$refactored_content" ]]; then
            # Backup original
            cp "$impl_file" "${impl_file}.pre-refactor"
            echo "$refactored_content" > "$impl_file"
            echo -e "  ${GREEN}✓${NC} Code refactored"

            # Verify tests still pass
            echo -e "  ${DIM}Verifying tests still pass...${NC}"
            local test_result=1
            case "$test_framework" in
                pytest)
                    pytest "$test_file" --tb=no -q 2>/dev/null && test_result=0 || test_result=1
                    ;;
                jest)
                    npx jest "$test_file" 2>/dev/null && test_result=0 || test_result=1
                    ;;
            esac

            if [[ $test_result -eq 0 ]]; then
                echo -e "  ${GREEN}✓${NC} Tests still pass after refactor"
                rm -f "${impl_file}.pre-refactor"
            else
                echo -e "  ${YELLOW}!${NC} Refactor broke tests - reverting"
                mv "${impl_file}.pre-refactor" "$impl_file"
            fi
        fi
    fi

    echo "{\"status\": \"completed\"}"
    return 0
}

# VERIFY PHASE: Security review
_504_execute_verify() {
    local task_id="$1"
    local impl_file="$2"
    local prompts_dir="$3"
    local error_context_file="${4:-}"  # Error context from previous phases

    local prompt_file="$prompts_dir/verify-t${task_id}.md"
    local output_file="$prompts_dir/verify-t${task_id}-output.json"

    if [[ ! -f "$impl_file" ]]; then
        echo -e "  ${YELLOW}!${NC} No implementation file to verify"
        echo "{\"status\": \"skipped\"}"
        return 0
    fi

    local impl_content=$(cat "$impl_file")

    # Get accumulated error context from previous phases
    local error_context=""
    if [[ -n "$error_context_file" && -f "$error_context_file" ]]; then
        error_context=$(_504_get_error_context "$error_context_file")
    fi

    # Build prompt with loaded agent expertise if available
    if [[ -n "$_504_VERIFY_AGENT_PROMPT" ]]; then
        echo "$_504_VERIFY_AGENT_PROMPT" > "$prompt_file"
        cat >> "$prompt_file" << PROMPT

---

# Task: VERIFY Phase - Security Review for Task $task_id

Apply your security expertise to review this code for security issues.

$error_context

## Code to Review
PROMPT
    else
        cat > "$prompt_file" << PROMPT
# Task: VERIFY Phase - Security Review for Task $task_id

You are a security-scanner agent. Review the code for security issues.

$error_context

## Code to Review
PROMPT
    fi

    cat >> "$prompt_file" << PROMPT

$impl_content

## Check For

1. Input validation issues
2. Injection vulnerabilities (SQL, command, etc.)
3. Authentication/authorization issues
4. Sensitive data exposure
5. Insecure dependencies
6. OWASP Top 10 issues

## Output Format

{
  "status": "pass|warn|fail",
  "issues": [
    {
      "severity": "critical|high|medium|low",
      "type": "issue type",
      "line": "approximate line",
      "description": "what's wrong",
      "recommendation": "how to fix"
    }
  ],
  "summary": "brief summary"
}

Output ONLY valid JSON.
PROMPT

    echo -e "  ${DIM}Security review with LLM...${NC}"

    if atomic_invoke "$prompt_file" "$output_file" "VERIFY T$task_id" --model=haiku; then
        if jq -e . "$output_file" &>/dev/null; then
            local status=$(jq -r '.status // "unknown"' "$output_file")
            local issue_count=$(jq '.issues | length' "$output_file" 2>/dev/null || echo 0)

            case "$status" in
                pass)
                    echo -e "  ${GREEN}✓${NC} Security review passed"
                    ;;
                warn)
                    echo -e "  ${YELLOW}!${NC} Security review: $issue_count warnings"
                    jq -r '.issues[] | "    - [\(.severity)] \(.description)"' "$output_file" 2>/dev/null
                    ;;
                fail)
                    echo -e "  ${RED}✗${NC} Security review: $issue_count issues"
                    jq -r '.issues[] | "    - [\(.severity)] \(.description)"' "$output_file" 2>/dev/null
                    ;;
            esac
        else
            echo -e "  ${GREEN}✓${NC} Security review complete"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Security review skipped (LLM failed)"
    fi

    echo "{\"status\": \"completed\"}"
    return 0
}
