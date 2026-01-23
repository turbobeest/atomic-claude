#!/bin/bash
#
# Task 303: Task Decomposition
# Break PRD into TaskMaster-format tasks
#
# Uses task-decomposer agent to:
#   1. Parse PRD feature requirements (Section 4)
#   2. Generate atomic tasks with acceptance criteria
#   3. Create .taskmaster/tasks/tasks.json
#
# Task priorities derived from PRD RFC 2119 keywords:
#   SHALL/MUST → high
#   SHOULD → medium
#   MAY → low
#

task_303_task_decomposition() {
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json"
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local taskmaster_dir="$ATOMIC_ROOT/.taskmaster"
    local tasks_file="$taskmaster_dir/tasks/tasks.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"
    local raw_tasks_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/raw-tasks.json"

    atomic_step "Task Decomposition"

    mkdir -p "$prompts_dir" "$taskmaster_dir/tasks"

    echo ""
    echo -e "  ${DIM}Breaking PRD into atomic, implementable tasks using TaskMaster format.${NC}"
    echo -e "  ${DIM}Output: .taskmaster/tasks/tasks.json${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # PRD EXTRACTION
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PRD EXTRACTION${NC}"
    echo ""

    if [[ ! -f "$prd_file" ]]; then
        atomic_error "PRD file not found: $prd_file"
        return 1
    fi

    # Extract PRD content
    local prd_content
    prd_content=$(cat "$prd_file")
    local prd_lines=$(wc -l < "$prd_file")

    echo -e "  ${GREEN}✓${NC} PRD loaded ($prd_lines lines)"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # TASK GENERATION
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TASK GENERATION${NC}"
    echo ""

    # Build the decomposition prompt following PRD-TEMPLATE v3.0 structure
    cat > "$prompts_dir/task-decomposition.md" << 'PROMPT_HEADER'
# Task: PRD to TaskMaster Decomposition

You are a task-decomposer agent. Your job is to break down the PRD into atomic, implementable tasks following PRD-TEMPLATE v3.0 structure.

## PRD Structure Reference

The PRD follows this structure:
- **Section 4**: Feature Requirements (F1, F2, ...) with FR-* requirements
- **Section 10**: Task Decomposition rules and dependency graph
- **Section 11**: Subtask Context Extraction (for Phase 4)

## Task Generation Rules (from PRD Section 10)

1. **Each Feature** → One top-level task
2. **Each FR** → Details field or subtask (subtasks populated in Phase 4)
3. **Dependencies** → From PRD dependency tables (FR-*-F*.* Blocks/Blocked By)
4. **Priorities** → From RFC 2119 keywords:
   - SHALL/MUST → "high"
   - SHOULD → "medium"
   - MAY → "low"

## TaskMaster JSON Format

Generate tasks in this exact structure:

```json
{
  "meta": {
    "project_name": "<from PRD metadata>",
    "generated_at": "<ISO timestamp>",
    "source": "prd",
    "version": "1.0"
  },
  "tasks": [
    {
      "id": 1,
      "title": "F0: Foundation Setup",
      "description": "Initialize project structure per PRD Section 6",
      "status": "pending",
      "priority": "high",
      "category": "infrastructure",
      "dependencies": [],
      "acceptance_criteria": "From PRD acceptance criteria tables",
      "tags": ["foundation"],
      "estimated_complexity": "simple|moderate|complex",
      "prd_section": "Section reference",
      "subtasks": []
    }
  ]
}
```

## Categories

- **infrastructure**: Setup, CI/CD, project structure (F0)
- **feature**: Core functionality from Section 4 Features
- **testing**: Test infrastructure (not TDD subtasks - those come in Phase 4)
- **documentation**: API docs, guides from Section 12
- **security**: Auth, validation from NFR-2

## Decomposition Checklist

- [ ] All Features (F1, F2, ...) have corresponding tasks
- [ ] Dependencies match PRD dependency tables
- [ ] Acceptance criteria from PRD AC tables
- [ ] No circular dependencies (DAG structure)
- [ ] ID 1 is foundation/setup task

## Output

Generate ONLY valid JSON. No markdown, no explanations.
Start with `{` and end with `}`.

---

## PRD Content

PROMPT_HEADER

    # Append the actual PRD content
    echo "$prd_content" >> "$prompts_dir/task-decomposition.md"

    echo -e "  ${DIM}Invoking task-decomposer agent...${NC}"
    echo ""

    atomic_waiting "task-decomposer generating tasks..."

    if atomic_invoke "$prompts_dir/task-decomposition.md" "$raw_tasks_file" "Task decomposition" --model=opus; then
        # Validate JSON
        if jq -e . "$raw_tasks_file" &>/dev/null; then
            local task_count=$(jq '.tasks | length // 0' "$raw_tasks_file" 2>/dev/null || echo 0)
            echo -e "  ${GREEN}✓${NC} Generated $task_count tasks"
        else
            atomic_warn "Invalid JSON output - attempting repair"
            _303_repair_json "$raw_tasks_file"
        fi
    else
        atomic_warn "Task decomposition failed - creating template"
        _303_create_template_tasks "$raw_tasks_file"
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # TASK VALIDATION
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TASK VALIDATION${NC}"
    echo ""

    local task_count=$(jq '.tasks | length // 0' "$raw_tasks_file" 2>/dev/null || echo 0)
    local with_criteria=$(jq '[.tasks[] | select(.acceptance_criteria != null and .acceptance_criteria != "")] | length' "$raw_tasks_file" 2>/dev/null || echo 0)
    local with_deps=$(jq '[.tasks[] | select(.dependencies | length > 0)] | length' "$raw_tasks_file" 2>/dev/null || echo 0)
    local high_priority=$(jq '[.tasks[] | select(.priority == "high")] | length' "$raw_tasks_file" 2>/dev/null || echo 0)
    local medium_priority=$(jq '[.tasks[] | select(.priority == "medium")] | length' "$raw_tasks_file" 2>/dev/null || echo 0)
    local low_priority=$(jq '[.tasks[] | select(.priority == "low")] | length' "$raw_tasks_file" 2>/dev/null || echo 0)

    echo -e "  ${BOLD}Task Statistics:${NC}"
    echo ""
    echo -e "    Total tasks:         $task_count"
    echo -e "    With criteria:       $with_criteria"
    echo -e "    With dependencies:   $with_deps"
    echo ""
    echo -e "  ${BOLD}Priority Distribution:${NC}"
    echo ""
    echo -e "    High (SHALL/MUST):   $high_priority"
    echo -e "    Medium (SHOULD):     $medium_priority"
    echo -e "    Low (MAY):           $low_priority"
    echo ""

    # Check for issues
    local issues=0

    if [[ $with_criteria -lt $task_count ]]; then
        echo -e "  ${YELLOW}!${NC} $(( task_count - with_criteria )) tasks missing acceptance criteria"
        ((issues++))
    fi

    if [[ $task_count -gt 0 && $with_deps -eq 0 ]]; then
        echo -e "  ${YELLOW}!${NC} No dependencies defined (verify PRD dependency tables)"
    fi

    if [[ $issues -eq 0 ]]; then
        echo -e "  ${GREEN}✓${NC} All validation checks passed"
    fi
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # TASKMASTER INTEGRATION
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TASKMASTER INTEGRATION${NC}"
    echo ""

    cp "$raw_tasks_file" "$tasks_file"
    echo -e "  ${GREEN}✓${NC} Tasks written to .taskmaster/tasks/tasks.json"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # TASK PREVIEW
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TASK PREVIEW${NC}"
    echo ""

    jq -r '.tasks[:5][] | "    [\(.id)] \(.title) (\(.priority))"' "$tasks_file" 2>/dev/null || \
        echo "    (Unable to preview tasks)"
    echo ""

    if [[ $task_count -gt 5 ]]; then
        echo -e "    ${DIM}... and $(( task_count - 5 )) more${NC}"
        echo ""
    fi

    atomic_context_artifact "$raw_tasks_file" "raw-tasks" "Raw task decomposition"
    atomic_context_artifact "$tasks_file" "tasks-json" "TaskMaster tasks file"
    atomic_context_decision "Decomposed PRD into $task_count tasks" "decomposition"

    atomic_success "Task decomposition complete"

    return 0
}

# Attempt to repair malformed JSON
_303_repair_json() {
    local file="$1"

    # Try to extract JSON from markdown code blocks
    if grep -q '```json' "$file"; then
        sed -n '/```json/,/```/p' "$file" | sed '1d;$d' > "${file}.tmp"
        if jq -e . "${file}.tmp" &>/dev/null; then
            mv "${file}.tmp" "$file"
            echo -e "  ${GREEN}✓${NC} JSON repaired from markdown"
            return 0
        fi
        rm -f "${file}.tmp"
    fi

    # Try to find JSON object
    if grep -q '^{' "$file"; then
        local start_line=$(grep -n '^{' "$file" | head -1 | cut -d: -f1)
        tail -n +$start_line "$file" > "${file}.tmp"
        if jq -e . "${file}.tmp" &>/dev/null; then
            mv "${file}.tmp" "$file"
            echo -e "  ${GREEN}✓${NC} JSON extracted from output"
            return 0
        fi
        rm -f "${file}.tmp"
    fi

    # Fall back to template
    _303_create_template_tasks "$file"
    return 1
}

# Create template tasks when generation fails
_303_create_template_tasks() {
    local file="$1"

    jq -n '{
        "meta": {
            "project_name": "Project",
            "generated_at": (now | todate),
            "source": "template",
            "version": "1.0"
        },
        "tasks": [
            {
                "id": 1,
                "title": "F0: Foundation Setup",
                "description": "Initialize project structure and development environment",
                "status": "pending",
                "priority": "high",
                "category": "infrastructure",
                "dependencies": [],
                "acceptance_criteria": "Project builds successfully, tests run",
                "tags": ["setup", "foundation"],
                "estimated_complexity": "simple",
                "prd_section": "Section 6: Code Structure",
                "subtasks": []
            },
            {
                "id": 2,
                "title": "F1: Core Feature Implementation",
                "description": "Implement primary feature from PRD Section 4",
                "status": "pending",
                "priority": "high",
                "category": "feature",
                "dependencies": [1],
                "acceptance_criteria": "Feature works as specified in PRD",
                "tags": ["core", "feature"],
                "estimated_complexity": "moderate",
                "prd_section": "Section 4: Feature Requirements",
                "subtasks": []
            },
            {
                "id": 3,
                "title": "Test Infrastructure",
                "description": "Set up testing framework per PRD Section 7",
                "status": "pending",
                "priority": "high",
                "category": "testing",
                "dependencies": [1],
                "acceptance_criteria": "Test framework configured, sample test runs",
                "tags": ["testing", "infrastructure"],
                "estimated_complexity": "simple",
                "prd_section": "Section 7: TDD Implementation Guide",
                "subtasks": []
            },
            {
                "id": 4,
                "title": "Documentation",
                "description": "Write documentation per PRD Section 12",
                "status": "pending",
                "priority": "medium",
                "category": "documentation",
                "dependencies": [2],
                "acceptance_criteria": "README complete, API documented",
                "tags": ["docs"],
                "estimated_complexity": "simple",
                "prd_section": "Section 12: Documentation Requirements",
                "subtasks": []
            }
        ]
    }' > "$file"

    atomic_warn "Created template tasks - manual refinement required"
}
