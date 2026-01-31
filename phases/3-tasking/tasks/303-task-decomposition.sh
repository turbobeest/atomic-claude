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
    # LOAD SELECTED AGENTS
    # ─────────────────────────────────────────────────────────────────────────────

    local decomposer_prompt=""
    local validator_prompt=""

    # Get agent repo path from Phase 0 config
    # Check embedded repo first (monorepo deployment), then env var, then default
    local agent_repo="$ATOMIC_ROOT/repos/agents"
    [[ -f "$ATOMIC_ROOT/agents/agent-inventory.csv" ]] && agent_repo="$ATOMIC_ROOT/agents"
    [[ -n "$ATOMIC_AGENT_REPO" ]] && agent_repo="$ATOMIC_AGENT_REPO"

    if [[ -f "$agents_file" ]]; then
        # Load decomposition agent prompts from agents repository
        local decomposition_agents=$(jq -r '.decomposition_agents[]?' "$agents_file" 2>/dev/null)

        for agent in $decomposition_agents; do
            agent_file=$(atomic_find_agent "$agent" "$agent_repo")
            if [[ -f "$agent_file" ]]; then
                case "$agent" in
                    *task-decomposer*)
                        decomposer_prompt=$(cat "$agent_file" | atomic_strip_frontmatter)
                        echo -e "  ${GREEN}✓${NC} Loaded agent: $agent"
                        ;;
                    *dependency-mapper*)
                        # Will be used in Task 304
                        echo -e "  ${GREEN}✓${NC} Found agent: $agent (for Task 304)"
                        ;;
                esac
            else
                echo -e "  ${YELLOW}!${NC} Agent file not found: $agent_file"
            fi
        done

        # Load validation agents
        local validation_agents=$(jq -r '.validation_agents[]?' "$agents_file" 2>/dev/null)
        for agent in $validation_agents; do
            agent_file=$(atomic_find_agent "$agent" "$agent_repo")
            if [[ -f "$agent_file" ]]; then
                case "$agent" in
                    *task-validator*)
                        validator_prompt=$(cat "$agent_file" | atomic_strip_frontmatter)
                        echo -e "  ${GREEN}✓${NC} Loaded agent: $agent"
                        ;;
                esac
            fi
        done
        echo ""
    else
        echo -e "  ${DIM}No agent selection found - using built-in decomposition logic${NC}"
        echo ""
    fi

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

    # Extract ONLY relevant PRD sections (4, 5, 6, 10, 11)
    # Section 4: Feature Requirements (primary source of tasks)
    # Section 5: Logical Dependency Chain (task ordering)
    # Section 6: Development Phases (phase grouping)
    # Section 10: Task Decomposition rules (if present)
    # Section 11: Subtask Context (for Phase 4 prep)
    local prd_lines=$(wc -l < "$prd_file")

    # Extract key sections with smart truncation
    local section_4=$(sed -n '/^## 3\. Feature Requirements/,/^## 4\./p' "$prd_file" 2>/dev/null | head -200)
    local section_5=$(sed -n '/^## 4\. Non-Functional/,/^## 5\./p' "$prd_file" 2>/dev/null | head -80)
    local section_deps=$(sed -n '/^## 5\. Logical Dependency/,/^## 6\./p' "$prd_file" 2>/dev/null | head -100)
    local section_phases=$(sed -n '/^## 6\. Development Phases/,/^## 7\./p' "$prd_file" 2>/dev/null | head -80)
    local section_tech=$(sed -n '/### 2\.1 Tech Stack/,/### 2\.2/p' "$prd_file" 2>/dev/null | head -40)

    # Also get project name from PRD metadata or Section 0
    local project_name=$(grep -m1 "^# " "$prd_file" 2>/dev/null | sed 's/^# //' || echo "Project")

    echo -e "  ${GREEN}✓${NC} PRD loaded ($prd_lines lines)"
    echo -e "  ${DIM}  Extracted: Feature Requirements, Dependencies, Phases, Tech Stack${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────
    # TASK GENERATION
    # ─────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TASK GENERATION${NC}"
    echo ""

    # Build the decomposition prompt following PRD-TEMPLATE v3.0 structure
    # If we have a loaded agent prompt, use it; otherwise use built-in logic
    if [[ -n "$decomposer_prompt" ]]; then
        echo "$decomposer_prompt" > "$prompts_dir/task-decomposition.md"
        cat >> "$prompts_dir/task-decomposition.md" << PROMPT_HEADER

---

# Task: PRD to TaskMaster Decomposition

Apply your task decomposition expertise to the PRD below, following PRD-TEMPLATE v3.0 structure.
PROMPT_HEADER
    else
        cat > "$prompts_dir/task-decomposition.md" << PROMPT_HEADER
# Task: PRD to TaskMaster Decomposition

You are a task-decomposer agent. Your job is to break down the PRD into atomic, implementable tasks following PRD-TEMPLATE v3.0 structure.
PROMPT_HEADER
    fi

    cat >> "$prompts_dir/task-decomposition.md" << PROMPT_HEADER

## Token Budget Warning

Your output should be 50-150 tasks typically. Keep descriptions concise (1-2 sentences). Acceptance criteria should be bullet points, not paragraphs.

## Project Context

Project Name: $project_name

## Task Generation Rules

1. **Each Feature (F1, F2, ...)** → One top-level task
2. **Each FR (FR-001, FR-002, ...)** → Details in description or later subtasks (Phase 4)
3. **Dependencies** → From PRD dependency chain section
4. **Priorities** → From RFC 2119 keywords:
   - SHALL/MUST → "high"
   - SHOULD → "medium"
   - MAY → "low"

## Categories

- **infrastructure**: Setup, CI/CD, project structure (F0)
- **feature**: Core functionality from Feature Requirements
- **testing**: Test infrastructure (TDD subtasks come in Phase 4)
- **documentation**: API docs, guides
- **security**: Auth, validation from NFRs

## Complete Example Output

Here is a complete, valid example of the expected output format:

\`\`\`json
{
  "meta": {
    "project_name": "TaskFlow API",
    "generated_at": "2024-01-15T10:30:00Z",
    "source": "prd",
    "version": "1.0"
  },
  "tasks": [
    {
      "id": 1,
      "title": "F0: Foundation Setup",
      "description": "Initialize project structure with Node.js, TypeScript, and Express per tech stack",
      "status": "pending",
      "priority": "high",
      "category": "infrastructure",
      "dependencies": [],
      "acceptance_criteria": "- package.json configured\\n- TypeScript compiles\\n- Express server starts on port 3000",
      "tags": ["setup", "foundation"],
      "estimated_complexity": "simple",
      "prd_section": "Section 6",
      "subtasks": []
    },
    {
      "id": 2,
      "title": "F1: User Authentication",
      "description": "Implement JWT-based authentication per FR-001 through FR-005",
      "status": "pending",
      "priority": "high",
      "category": "feature",
      "dependencies": [1],
      "acceptance_criteria": "- Users can register with email/password\\n- Login returns valid JWT\\n- Protected routes reject invalid tokens",
      "tags": ["auth", "security"],
      "estimated_complexity": "moderate",
      "prd_section": "Section 3.1",
      "subtasks": []
    },
    {
      "id": 3,
      "title": "F2: Task Management Core",
      "description": "Implement CRUD operations for tasks per FR-006 through FR-012",
      "status": "pending",
      "priority": "high",
      "category": "feature",
      "dependencies": [2],
      "acceptance_criteria": "- Create task with title, description, priority\\n- List tasks with pagination\\n- Update task status\\n- Delete task",
      "tags": ["tasks", "crud"],
      "estimated_complexity": "moderate",
      "prd_section": "Section 3.2",
      "subtasks": []
    },
    {
      "id": 4,
      "title": "Test Infrastructure",
      "description": "Configure Jest with TypeScript, set up test utilities",
      "status": "pending",
      "priority": "high",
      "category": "testing",
      "dependencies": [1],
      "acceptance_criteria": "- Jest runs TypeScript tests\\n- Test utilities for API testing\\n- CI integration ready",
      "tags": ["testing"],
      "estimated_complexity": "simple",
      "prd_section": "Section 8",
      "subtasks": []
    }
  ]
}
\`\`\`

## Decomposition Checklist

Before outputting, verify:
- [ ] All Features (F1, F2, ...) from Section 3 have corresponding tasks
- [ ] Dependencies match the Logical Dependency Chain
- [ ] Acceptance criteria are testable (not vague)
- [ ] No circular dependencies (valid DAG)
- [ ] ID 1 is always foundation/setup

## Output Format

Generate ONLY valid JSON. No markdown wrapper, no explanations.
Start with \`{\` and end with \`}\`.

---

## PRD Sections (Extracted)

### Tech Stack
$section_tech

### Feature Requirements (Section 3)
$section_4

### Non-Functional Requirements (Section 4)
$section_5

### Logical Dependency Chain (Section 5)
$section_deps

### Development Phases (Section 6)
$section_phases
PROMPT_HEADER

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
