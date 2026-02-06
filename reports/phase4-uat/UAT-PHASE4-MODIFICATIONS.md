# Phase 4 UAT Mode Modifications

## Summary

Added UAT mode bypasses to all Phase 4 (Specification) task scripts to enable automated testing. When `ATOMIC_UAT_MODE=true`, these tasks skip interactive prompts and LLM invocations, creating minimal valid outputs instead.

## Modified Tasks

### Task 401: Entry & Initialization
**File**: `/phases/4-specification/tasks/401-entry-initialization.sh`  
**Bypass Location**: Line 40 (after `atomic_step "Entry & Initialization"`)

**UAT Behavior**:
- Bypasses Phase 3 verification
- Creates minimal `initialization.json` with 3 test tasks
- Sets priority breakdown (2 high, 1 medium, 0 low)
- Skips interactive welcome screens

**Output**: Creates initialization.json with 3 test tasks and UAT mode flag.

---

### Task 402: Agent Selection
**File**: `/phases/4-specification/tasks/402-agent-selection.sh`  
**Bypass Location**: Line 17 (after `atomic_step "Agent Selection"`)

**UAT Behavior**:
- Auto-selects core specification agents
- Skips agent inventory loading and user selection menu
- Creates roster with 2 agents: specification-agent and tdd-implementation-agent

**Output**: Creates agent-roster.json with 2 agents for UAT testing.

---

### Task 403: OpenSpec Generation
**File**: `/phases/4-specification/tasks/403-openspec-generation.sh`  
**Bypass Location**: Line 18 (after `atomic_step "OpenSpec Generation"`)

**UAT Behavior**:
- Generates 3 minimal OpenSpec stub files (TASK-001, TASK-002, TASK-003)
- Skips LLM-based specification generation
- Creates basic test strategies and interface contracts
- Reports 100% coverage (3/3 tasks)

**Output**: Creates 3 OpenSpec JSON files with minimal test specifications.

---

### Task 404: TDD Subtask Injection
**File**: `/phases/4-specification/tasks/404-tdd-subtask-injection.sh`  
**Bypass Location**: Line 17 (after `atomic_step "TDD Subtask Injection"`)

**UAT Behavior**:
- Creates backup of tasks.json
- Generates minimal tasks.json with 3 tasks
- Each task has 4 TDD subtasks: RED, GREEN, REFACTOR, VERIFY
- Total 12 subtasks with proper dependency chains

**Output**: Creates tasks.json with 3 tasks and 12 TDD subtasks.

---

### Task 406: Phase Closeout
**File**: `/phases/4-specification/tasks/406-closeout.sh`  
**Bypass Location**: Line 20 (after `atomic_step "Phase Closeout"`)

**UAT Behavior**:
- Auto-approves closeout without user confirmation
- Generates minimal closeout markdown and JSON
- Skips memory checkpoint prompt
- Reports complete status with all artifacts

**Output**: Creates phase-04-closeout.md and phase-04-closeout.json.

---

## Testing

All modified task scripts pass bash syntax validation:

```
bash -n phases/4-specification/tasks/401-entry-initialization.sh   (OK)
bash -n phases/4-specification/tasks/402-agent-selection.sh        (OK)
bash -n phases/4-specification/tasks/403-openspec-generation.sh    (OK)
bash -n phases/4-specification/tasks/404-tdd-subtask-injection.sh  (OK)
bash -n phases/4-specification/tasks/406-closeout.sh               (OK)
```

## Usage

To run Phase 4 in UAT mode:

```bash
export ATOMIC_UAT_MODE=true
./main.sh run 4
```

## Backups

Pre-modification backups saved to:
- phases/4-specification/tasks/401-entry-initialization.sh.pre-uat

## Artifacts Created in UAT Mode

| Artifact | Location | Purpose |
|----------|----------|---------|
| initialization.json | .outputs/4-specification/ | Phase entry state |
| agent-roster.json | .claude/ | Selected agents |
| spec-TASK-*.json | .claude/specs/ | OpenSpec files (3) |
| spec-progress.json | .outputs/4-specification/ | Generation status |
| tasks.json | .taskmaster/tasks/ | Tasks with TDD subtasks |
| tdd-injection.json | .outputs/4-specification/ | Injection report |
| phase-04-closeout.md | .claude/closeout/ | Closeout summary |
| phase-04-closeout.json | .claude/closeout/ | Closeout data |

---

**Modification Date**: 2026-02-04  
**Purpose**: Enable end-to-end automated testing of Phase 4 Specification
