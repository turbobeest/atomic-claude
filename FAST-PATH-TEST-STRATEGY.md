# Fast-Path Testing Strategy

**Goal**: Test full pipeline (Phases 0-9) exhaustively for UXUI/workflow structure while minimizing token consumption and not expecting fully coded output.

---

## Token Consumption Analysis

### Current Token Usage (Full Pipeline)

| Phase | Task Count | Avg Tokens/Task | Total Tokens | Time |
|-------|-----------|-----------------|--------------|------|
| **0-setup** | 9 | 500 | ~4,500 | 5 min |
| **1-discovery** | 10 | 2,000 | ~20,000 | 10 min |
| **2-prd** | 1 (8 gens) | 50,000 | ~50,000 | 15 min |
| **3-tasking** | 1 | 10,000 | ~10,000 | 5 min |
| **4-specification** | 30 tasks | 8,000 | ~240,000 | 60 min |
| **5-implementation** | 30 tasks | 15,000 | ~450,000 | 120 min |
| **6-code-review** | 1 | 20,000 | ~20,000 | 10 min |
| **7-integration** | 1 | 10,000 | ~10,000 | 5 min |
| **8-deployment-prep** | 1 | 5,000 | ~5,000 | 3 min |
| **9-release** | 1 | 3,000 | ~3,000 | 2 min |
| **TOTAL** | - | - | **~812,500** | **~235 min** |

**Problem**: Phases 4-5 consume 85% of tokens and time.

---

## Fast-Path Strategy

### Key Principle: Stub Heavy, Validate Structure

**What we TEST**:
- ✅ Phase transitions and gates
- ✅ Task state machine (pending → in_progress → completed)
- ✅ File organization after each task
- ✅ Dashboard display and updates
- ✅ Memory persistence across phases
- ✅ Provider fallback (Bedrock → Ollama)
- ✅ Guardian validation (if enabled)
- ✅ Audit selection and execution
- ✅ Closeout generation
- ✅ All 10 phases execute end-to-end

**What we SKIP**:
- ❌ Elaborate content generation (stub outputs)
- ❌ Full task decomposition (3-5 tasks max)
- ❌ Complete OpenSpec for all tasks
- ❌ Actual code implementation
- ❌ Exhaustive code review
- ❌ Complex test plans

---

## Phase-by-Phase Fast-Path Configuration

### Phase 0: Setup (NO CHANGE)
**Approach**: Run normally
**Token usage**: ~4,500
**Time**: 5 min
**Why**: Setup is already fast and needed for context

---

### Phase 1: Discovery (MINIMAL CONTENT)
**Approach**: Stub corpus, minimal agent selection
**Token usage**: ~5,000 (75% reduction)
**Time**: 3 min

**Changes**:
- Task 102: Return "0 materials" immediately
- Task 103: Skip corpus enrichment
- Task 104: Select 1-2 agents max (not 5-10)
- Task 106: Minimal discovery report (1 paragraph)
- Task 108: Skip diagrams OR generate 1 simple diagram
- Task 109: Run 1 audit only

**Implementation**:
```bash
export ATOMIC_FAST_PATH=true
export ATOMIC_MAX_AGENTS=2
export ATOMIC_SKIP_DIAGRAMS=true
```

---

### Phase 2: PRD (ALREADY DONE)
**Approach**: Keep 8-generation workflow
**Token usage**: ~50,000
**Time**: 15 min
**Why**: PRD structure is core to pipeline - we need to test this fully

**Note**: This is where we invest tokens for quality structure testing.

---

### Phase 3: Tasking (MINIMAL TASKS)
**Approach**: Generate 3-5 tasks max (not 20-40)
**Token usage**: ~3,000 (70% reduction)
**Time**: 2 min

**Changes**:
- Task 302: Select 1 agent only
- Task 303: Limit to 5 tasks maximum
  - Modify prompt: "Generate a MINIMAL task breakdown with 3-5 core tasks only"
  - Focus on: 1 backend task, 1 frontend task, 1 test task, 1 deployment task

**Implementation**:
```bash
export ATOMIC_MAX_TASKS=5
```

**Task 303 Prompt Override**:
```markdown
# FAST-PATH MODE: Generate 3-5 core tasks only

Your task breakdown should include:
1. One backend API task
2. One frontend UI task
3. One testing task
4. One deployment task
5. (Optional) One integration task

DO NOT decompose into 20+ tasks. Keep it minimal for testing purposes.
```

---

### Phase 4: Specification (STUB OPENSPEC)
**Approach**: Generate minimal OpenSpec for 3-5 tasks
**Token usage**: ~15,000 (94% reduction)
**Time**: 8 min

**Changes**:
- Task 403: Generate stub OpenSpec for each task:
  - 1 paragraph description
  - 2-3 acceptance criteria
  - Stub technical approach (1 sentence)
  - No elaborate scenarios

**Implementation**:
```bash
export ATOMIC_STUB_OPENSPEC=true
```

**OpenSpec Stub Template**:
```yaml
task_id: "TASK-001"
description: "[Brief 1-paragraph description]"
acceptance_criteria:
  - "Criterion 1"
  - "Criterion 2"
  - "Criterion 3"
technical_approach: "Use [technology] to implement [feature]."
estimated_complexity: "Medium"
```

---

### Phase 5: Implementation (MOCK TDD)
**Approach**: Generate file stubs, no actual code
**Token usage**: ~20,000 (96% reduction)
**Time**: 10 min

**Changes**:
- Task 504: For each task, generate:
  - File structure (directory tree)
  - Stub test files (with `# TODO: Implement test`)
  - Stub implementation files (with `# TODO: Implement`)
  - Skip actual code generation

**Implementation**:
```bash
export ATOMIC_MOCK_IMPLEMENTATION=true
```

**Example Stub Output**:
```python
# src/api/products.py
# TODO: Implement product catalog API endpoint

def get_products():
    """
    Retrieve all products from database.

    Returns:
        List of product objects
    """
    pass  # Implementation stub for testing
```

---

### Phase 6: Code Review (QUICK VALIDATION)
**Approach**: Validate file structure, skip code review
**Token usage**: ~2,000 (90% reduction)
**Time**: 2 min

**Changes**:
- Task 604: Quick structural validation:
  - Check files exist
  - Verify directory structure
  - Count stub functions
  - Skip actual code quality review

**Implementation**:
```bash
export ATOMIC_QUICK_REVIEW=true
```

---

### Phase 7: Integration Testing (MINIMAL PLAN)
**Approach**: Generate basic test plan, no execution
**Token usage**: ~3,000 (70% reduction)
**Time**: 2 min

**Changes**:
- Task 704: Generate 5-line test plan:
  - List test types (unit, integration, e2e)
  - Name test frameworks
  - Skip detailed test scenarios

---

### Phase 8: Deployment Prep (CHECKLIST ONLY)
**Approach**: Generate deployment checklist
**Token usage**: ~2,000 (60% reduction)
**Time**: 2 min

**Changes**:
- Task 804: Generate simple checklist:
  - Environment variables
  - Database migrations
  - Build commands
  - Skip detailed deployment scripts

---

### Phase 9: Release (MINIMAL NOTES)
**Approach**: Generate 1-paragraph release notes
**Token usage**: ~1,000 (67% reduction)
**Time**: 1 min

**Changes**:
- Task 905: Generate minimal release notes:
  - Version number
  - 3-5 bullet points of changes
  - Skip detailed changelog

---

## Fast-Path Token Budget

| Phase | Normal Tokens | Fast-Path Tokens | Reduction |
|-------|--------------|------------------|-----------|
| 0-setup | 4,500 | 4,500 | 0% |
| 1-discovery | 20,000 | 5,000 | 75% |
| 2-prd | 50,000 | 50,000 | 0% |
| 3-tasking | 10,000 | 3,000 | 70% |
| 4-specification | 240,000 | 15,000 | 94% |
| 5-implementation | 450,000 | 20,000 | 96% |
| 6-code-review | 20,000 | 2,000 | 90% |
| 7-integration | 10,000 | 3,000 | 70% |
| 8-deployment-prep | 5,000 | 2,000 | 60% |
| 9-release | 3,000 | 1,000 | 67% |
| **TOTAL** | **812,500** | **105,500** | **87%** |

**Time reduction**: 235 min → 50 min (79% faster)

---

## Implementation: Environment Variables

Create `.env.fast-path` file:
```bash
# Fast-path testing mode
ATOMIC_FAST_PATH=true

# Discovery limits
ATOMIC_MAX_AGENTS=2
ATOMIC_SKIP_DIAGRAMS=true

# Tasking limits
ATOMIC_MAX_TASKS=5

# Specification stubs
ATOMIC_STUB_OPENSPEC=true

# Implementation mocking
ATOMIC_MOCK_IMPLEMENTATION=true

# Review shortcuts
ATOMIC_QUICK_REVIEW=true

# Keep output token limit for PRD
CLAUDE_CODE_MAX_OUTPUT_TOKENS=8192
```

**Usage**:
```bash
cd /Users/jamesterbeest/dev/test-project2
source .env.fast-path
./run-atomic.sh run 0  # Start from phase 0
```

---

## Code Changes Required

### 1. Detect Fast-Path Mode

Add to `lib/atomic.sh`:
```bash
is_fast_path_mode() {
    [[ "${ATOMIC_FAST_PATH:-false}" == "true" ]]
}
```

### 2. Modify Task 303 (Tasking)

**File**: `phases/3-tasking/tasks/303-task-decomposition.sh`

```bash
task_303_task_decomposition() {
    atomic_step "Task Decomposition"

    local max_tasks=40  # Default

    if is_fast_path_mode; then
        max_tasks="${ATOMIC_MAX_TASKS:-5}"
        atomic_info "Fast-path mode: limiting to $max_tasks tasks"
    fi

    # Inject constraint into prompt
    cat >> "$prompt_file" << EOF

**CONSTRAINT**: Generate a maximum of $max_tasks tasks. Focus on core features only.
EOF

    # ... rest of task
}
```

### 3. Modify Task 403 (OpenSpec Generation)

**File**: `phases/4-specification/tasks/403-openspec-generation.sh`

```bash
task_403_openspec_generation() {
    atomic_step "OpenSpec Generation"

    if [[ "${ATOMIC_STUB_OPENSPEC:-false}" == "true" ]]; then
        atomic_info "Fast-path mode: generating stub OpenSpec"

        # Generate stub specs instead of full specs
        for task_id in "${task_list[@]}"; do
            cat > "$output_dir/openspec-${task_id}.yaml" << EOF
task_id: "${task_id}"
description: "Implementation of task ${task_id}"
acceptance_criteria:
  - "Core functionality works"
  - "Tests pass"
technical_approach: "Standard implementation approach"
estimated_complexity: "Medium"
EOF
        done

        return 0
    fi

    # ... normal OpenSpec generation
}
```

### 4. Modify Task 504 (Implementation)

**File**: `phases/5-implementation/tasks/504-tdd-execution.sh`

```bash
task_504_tdd_execution() {
    atomic_step "TDD Execution"

    if [[ "${ATOMIC_MOCK_IMPLEMENTATION:-false}" == "true" ]]; then
        atomic_info "Fast-path mode: generating file stubs"

        # Generate stub files instead of real code
        for task_id in "${task_list[@]}"; do
            mkdir -p "$output_dir/code/$task_id"

            cat > "$output_dir/code/$task_id/implementation.py" << EOF
# Task $task_id Implementation Stub
# TODO: Implement actual functionality

def main():
    """Stub implementation for testing pipeline"""
    pass
EOF

            cat > "$output_dir/code/$task_id/test_implementation.py" << EOF
# Task $task_id Test Stub
# TODO: Implement actual tests

def test_main():
    """Stub test for testing pipeline"""
    pass
EOF
        done

        return 0
    fi

    # ... normal implementation
}
```

---

## Testing Checklist

After running fast-path mode, verify:

### UXUI Testing ✅
- [ ] Dashboard shows all 10 phases
- [ ] Each phase transitions correctly (Planned → In Progress → Complete)
- [ ] Task count displays correctly for each phase
- [ ] File organization happens after each task
- [ ] Memory flow indicators work (recalled/saved badges)
- [ ] Current task box updates in real-time
- [ ] Provider/model display shows correct values
- [ ] Staleness detection works (>60s no update)
- [ ] Session banner updates correctly
- [ ] Clicking tasks shows file details (inputs/outputs)

### Workflow Testing ✅
- [ ] All phases complete without errors
- [ ] Closeout generated for each phase
- [ ] Task state persists across runs
- [ ] `--resume-at` flag works correctly
- [ ] Human gates work (if enabled)
- [ ] Audit selection and execution works
- [ ] Phase 2 PRD has all 15 sections
- [ ] Phase 3 generates 3-5 tasks (not 40)
- [ ] Phase 4 has stub OpenSpec for all tasks
- [ ] Phase 5 has stub code files
- [ ] Phases 6-9 complete quickly

### File Structure Testing ✅
- [ ] `.outputs/` organized by phase
- [ ] Each phase has `prompts/` and `outputs/` subdirs
- [ ] Guardian reports present (if enabled)
- [ ] Closeout.md in each phase directory
- [ ] Final artifacts in correct locations
- [ ] No orphaned tmp files

---

## Estimated Execution Time

**Full pipeline with fast-path mode**:
- Phase 0: 5 min
- Phase 1: 3 min
- Phase 2: 15 min (already running)
- Phase 3: 2 min
- Phase 4: 8 min
- Phase 5: 10 min
- Phase 6: 2 min
- Phase 7: 2 min
- Phase 8: 2 min
- Phase 9: 1 min

**Total**: ~50 minutes (vs 235 minutes normal)

---

## Next Steps

1. ✅ Wait for Phase 2 to complete (~5 min)
2. 📝 Implement fast-path environment variables
3. 🔧 Add fast-path detection to tasks 303, 403, 504
4. 🚀 Run phases 3-9 in fast-path mode
5. ✅ Validate UXUI exhaustively
6. 📊 Document any issues found
7. 🔄 Refactor Python scripts based on learnings

---

## Alternative: Even Faster "Smoke Test" Mode

If 50 minutes is still too long, we can create an **ultra-fast smoke test**:

**Approach**: Skip phases 4-5 entirely
- Phase 0: Setup
- Phase 1: Discovery (minimal)
- Phase 2: PRD (full 8-generation)
- Phase 3: Tasking (3 tasks)
- **SKIP Phase 4**: No OpenSpec
- **SKIP Phase 5**: No implementation
- Phase 6: Validate structure only (no code to review)
- Phase 7: Minimal test plan
- Phase 8: Deployment checklist
- Phase 9: Release notes

**Time**: ~30 minutes
**Tokens**: ~75,000

**Use case**: Quick validation that phase transitions work, not full pipeline test.
