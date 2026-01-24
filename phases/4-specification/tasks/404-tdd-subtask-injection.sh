#!/bin/bash
#
# Task 404: TDD Subtask Injection
# Write RED/GREEN/REFACTOR/VERIFY subtasks into tasks.json
#

task_404_tdd_subtask_injection() {
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local specs_dir="$ATOMIC_ROOT/.claude/specs"
    local backup_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json.pre-tdd-backup"
    local injection_report="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/tdd-injection.json"
    local roster_file="$ATOMIC_ROOT/.claude/agent-roster.json"

    atomic_step "TDD Subtask Injection"

    mkdir -p "$(dirname "$injection_report")"

    echo ""
    echo -e "  ${DIM}Injecting TDD subtasks (RED/GREEN/REFACTOR/VERIFY) into tasks.json.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # LOAD TDD-STRUCTURER AGENT (for future LLM-based enhancement)
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    local tdd_structurer_prompt=""
    local agent_repo="${ATOMIC_AGENT_REPO:-$ATOMIC_ROOT/repos/agents}"

    if [[ -f "$roster_file" ]]; then
        local has_tdd_agent=$(jq -r '.agents[] | select(. == "tdd-structurer")' "$roster_file" 2>/dev/null)
        if [[ -n "$has_tdd_agent" ]]; then
            local agent_file="$agent_repo/pipeline-agents/tdd-structurer.md"
            if [[ -f "$agent_file" ]]; then
                tdd_structurer_prompt=$(cat "$agent_file")
                echo -e "  ${GREEN}✓${NC} Loaded agent: tdd-structurer"
                echo ""
            fi
        fi
    fi
    # Note: tdd_structurer_prompt is available for future LLM-based subtask generation
    # Current implementation uses template-based injection for speed

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TDD CYCLE EDUCATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}THE TDD CYCLE${NC}"
    echo ""
    echo -e "  ${DIM}Each task will receive 4 subtasks forming a dependency chain:${NC}"
    echo ""
    echo -e "    ┌─────────────────────────────────────────────────────────────────┐"
    echo -e "    │                                                                 │"
    echo -e "    │   ${RED}RED${NC}  ────────►  ${GREEN}GREEN${NC}  ────────►  ${CYAN}REFACTOR${NC}  ────────►  ${MAGENTA}VERIFY${NC}   │"
    echo -e "    │                                                                 │"
    echo -e "    │  Write tests    Implement      Clean up        Security       │"
    echo -e "    │  (must FAIL)    (tests PASS)   (still PASS)    scan           │"
    echo -e "    │                                                                 │"
    echo -e "    └─────────────────────────────────────────────────────────────────┘"
    echo ""
    echo -e "  ${BOLD}Subtask Details:${NC}"
    echo ""
    echo -e "    ${RED}1. RED${NC} - Write Failing Tests"
    echo -e "       ${DIM}Acceptance: Tests exist AND fail${NC}"
    echo -e "       ${DIM}Tools: pytest, jest, etc.${NC}"
    echo ""
    echo -e "    ${GREEN}2. GREEN${NC} - Minimal Implementation"
    echo -e "       ${DIM}Acceptance: All tests pass${NC}"
    echo -e "       ${DIM}Focus: Simplest code that works${NC}"
    echo ""
    echo -e "    ${CYAN}3. REFACTOR${NC} - Code Cleanup"
    echo -e "       ${DIM}Acceptance: Linting passes, tests still pass${NC}"
    echo -e "       ${DIM}Tools: ruff, black, mypy, eslint${NC}"
    echo ""
    echo -e "    ${MAGENTA}4. VERIFY${NC} - Security Scan"
    echo -e "       ${DIM}Acceptance: No critical/high issues${NC}"
    echo -e "       ${DIM}Tools: bandit, safety, npm audit${NC}"
    echo ""

    read -p "  Press Enter to continue..."
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PRE-INJECTION BACKUP
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PRE-INJECTION BACKUP${NC}"
    echo ""

    cp "$tasks_file" "$backup_file"
    echo -e "  ${GREEN}✓${NC} Backed up tasks.json → tasks.json.pre-tdd-backup"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INJECTION MODE
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}INJECTION MODE${NC}"
    echo ""

    # Check current state
    local tasks_with_subtasks=$(jq '[.tasks[] | select(.subtasks | length > 0)] | length' "$tasks_file")
    local total_tasks=$(jq '.tasks | length' "$tasks_file")

    echo -e "  ${DIM}Current state:${NC}"
    echo -e "    Tasks with subtasks: $tasks_with_subtasks / $total_tasks"
    echo ""

    if [[ "$tasks_with_subtasks" -gt 0 ]]; then
        echo -e "  ${YELLOW}!${NC} Some tasks already have subtasks."
        echo ""
        echo -e "  ${CYAN}Options:${NC}"
        echo ""
        echo -e "    ${GREEN}[skip]${NC}       Skip tasks that already have subtasks"
        echo -e "    ${YELLOW}[replace]${NC}   Replace existing subtasks"
        echo -e "    ${RED}[abort]${NC}     Abort and review manually"
        echo ""

        read -p "  Choice [skip]: " inject_mode
        inject_mode=${inject_mode:-skip}

        if [[ "$inject_mode" == "abort" ]]; then
            atomic_error "Aborted by user"
            return 1
        fi
    else
        inject_mode="inject"
    fi

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SUBTASK INJECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}INJECTING TDD SUBTASKS${NC}"
    echo ""

    local injected=0
    local skipped=0

    # Process each task
    local task_ids=$(jq -r '.tasks[].id' "$tasks_file")

    for task_id in $task_ids; do
        local task_title=$(jq -r ".tasks[] | select(.id == $task_id) | .title" "$tasks_file")
        local existing_subtasks=$(jq ".tasks[] | select(.id == $task_id) | .subtasks | length // 0" "$tasks_file")

        # Skip if has subtasks and mode is skip
        if [[ "$inject_mode" == "skip" && "$existing_subtasks" -gt 0 ]]; then
            echo -e "  ${DIM}[${task_id}] Skipping (has subtasks): ${task_title:0:50}${NC}"
            ((skipped++))
            continue
        fi

        echo -e "  ${CYAN}[${task_id}]${NC} Injecting: ${task_title:0:60}"

        # Create TDD subtasks
        local subtasks_json=$(jq -n \
            --argjson task_id "$task_id" \
            --arg title "$task_title" \
            '[
                {
                    "id": 1,
                    "title": "RED: Write failing tests for T\($task_id)",
                    "phase": "RED",
                    "status": "pending",
                    "dependencies": [],
                    "acceptance_criteria": "Tests exist and FAIL when run",
                    "description": "Write unit tests and/or integration tests based on the OpenSpec. Tests must fail initially (no implementation yet)."
                },
                {
                    "id": 2,
                    "title": "GREEN: Implement T\($task_id) to pass tests",
                    "phase": "GREEN",
                    "status": "pending",
                    "dependencies": [1],
                    "acceptance_criteria": "All tests PASS",
                    "description": "Write the minimal implementation code to make all tests pass. Focus on correctness, not optimization."
                },
                {
                    "id": 3,
                    "title": "REFACTOR: Clean up T\($task_id) code",
                    "phase": "REFACTOR",
                    "status": "pending",
                    "dependencies": [2],
                    "acceptance_criteria": "Linting passes, tests still PASS",
                    "description": "Refactor the code for clarity, maintainability, and style compliance. Run linters (ruff, black, eslint). Ensure tests still pass."
                },
                {
                    "id": 4,
                    "title": "VERIFY: Security scan T\($task_id)",
                    "phase": "VERIFY",
                    "status": "pending",
                    "dependencies": [3],
                    "acceptance_criteria": "No critical or high security issues",
                    "description": "Run security scanners (bandit, safety, npm audit). Address any critical or high severity issues."
                }
            ]')

        # Update tasks.json with subtasks
        local temp_file=$(atomic_mktemp)
        jq --argjson task_id "$task_id" --argjson subtasks "$subtasks_json" \
            '(.tasks[] | select(.id == $task_id)).subtasks = $subtasks' \
            "$tasks_file" > "$temp_file" && mv "$temp_file" "$tasks_file"

        echo -e "       ${GREEN}✓${NC} Injected 4 TDD subtasks"
        ((injected++))
    done

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INJECTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}INJECTION SUMMARY${NC}"
    echo ""

    echo -e "    Tasks injected: ${GREEN}$injected${NC}"
    echo -e "    Tasks skipped:  ${YELLOW}$skipped${NC}"
    echo ""

    local total_subtasks=$((injected * 4))
    echo -e "    Total subtasks created: ${BOLD}$total_subtasks${NC}"
    echo ""

    # Verify injection
    local final_with_subtasks=$(jq '[.tasks[] | select(.subtasks | length >= 4)] | length' "$tasks_file")
    echo -e "  ${DIM}Verification:${NC}"
    echo -e "    Tasks with TDD subtasks: $final_with_subtasks / $total_tasks"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SAMPLE OUTPUT
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SAMPLE TASK STRUCTURE${NC}"
    echo ""

    # Show first task with subtasks
    jq '.tasks[0] | {id, title, subtasks: [.subtasks[] | {id, title, phase, dependencies}]}' "$tasks_file" 2>/dev/null
    echo ""

    # Save injection report
    jq -n \
        --argjson injected "$injected" \
        --argjson skipped "$skipped" \
        --argjson total_subtasks "$total_subtasks" \
        --argjson final_coverage "$final_with_subtasks" \
        --argjson total_tasks "$total_tasks" \
        '{
            "injection_mode": "'"$inject_mode"'",
            "tasks_injected": $injected,
            "tasks_skipped": $skipped,
            "total_subtasks_created": $total_subtasks,
            "tasks_with_tdd_subtasks": $final_coverage,
            "total_tasks": $total_tasks,
            "backup_file": "tasks.json.pre-tdd-backup",
            "completed_at": (now | todate)
        }' > "$injection_report"

    atomic_context_artifact "$tasks_file" "tasks-with-tdd" "tasks.json with TDD subtasks"
    atomic_context_decision "Injected TDD subtasks into $injected tasks ($total_subtasks total subtasks)" "tdd-structure"

    atomic_success "TDD Subtask Injection complete"

    return 0
}
