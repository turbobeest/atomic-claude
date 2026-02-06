# Task Reset & Recovery System

## Overview

A structured system for resetting pipeline state to any task, with impact analysis, user confirmation, and automatic cleanup of generated artifacts.

## Use Cases

### 1. Error Recovery
**Scenario**: Task 205 fails due to expired AWS token
**User Need**: Reset to task 205, re-run after fixing credentials
**System Action**:
- Reset task 205 state to pending
- Delete task 205 output files
- Preserve all prior tasks (201-204)

### 2. Rework After Discovery
**Scenario**: User realizes during task 207 that requirements in task 203 were wrong
**User Need**: Jump back to task 203, redo interview
**System Action**:
- Reset tasks 203-207 to pending
- Delete all outputs from 203-207
- Validate that task 202 outputs still exist (dependency check)
- Show impact: "Will delete PRD draft, validation results, etc."

### 3. Phase Restart
**Scenario**: Phase 2 completed but PRD quality is poor
**User Need**: Restart entire Phase 2
**System Action**:
- Reset all Phase 2 tasks (201-209) to pending
- Delete all Phase 2 outputs
- Preserve Phase 1 artifacts
- Show impact: "Will delete PRD.md, all phase 2 artifacts"

## Architecture

### 1. Artifact Tracking System

#### Current State (Incomplete)
```json
// .claude/task-state.json
{
  "phases": {
    "2-prd": {
      "tasks": {
        "205": {
          "name": "PRD Authoring",
          "status": "completed",
          "artifacts": []  // ← Often empty!
        }
      }
    }
  }
}
```

#### Proposed Enhancement
```json
{
  "phases": {
    "2-prd": {
      "tasks": {
        "205": {
          "name": "PRD Authoring",
          "status": "completed",
          "started_at": "2026-02-03T20:00:00Z",
          "completed_at": "2026-02-03T20:15:00Z",
          "artifacts": {
            "created": [
              ".outputs/2-prd/prd-draft.md",
              ".outputs/2-prd/requirements.json",
              ".outputs/2-prd/prompts/requirements-prompt.md",
              "docs/prd/PRD.md"
            ],
            "modified": [
              ".outputs/2-prd/synthesis.json"
            ],
            "dependencies": [
              ".outputs/1-discovery/selected-approach.json",
              ".outputs/1-discovery/direction-confirmed.json"
            ]
          }
        }
      }
    }
  }
}
```

### 2. Reset Tool (Python)

#### CLI Interface
```bash
# Interactive mode
./scripts/reset-to-task.py 203

# Non-interactive mode (for scripting)
./scripts/reset-to-task.py 203 --confirm --no-prompt

# Dry-run mode (show impact without executing)
./scripts/reset-to-task.py 203 --dry-run

# Phase-level reset
./scripts/reset-to-task.py --phase 2 --start
```

#### Impact Analysis Output
```
╔═══════════════════════════════════════════════════════════════╗
║ TASK RESET IMPACT ANALYSIS                                    ║
╚═══════════════════════════════════════════════════════════════╝

Target: Reset to Task 203 (PRD Interview)

Current State:
  Phase 2 (PRD): 7/10 tasks completed (201-207)

Tasks to Reset:
  ✓ 203  PRD Interview         (completed → pending)
  ✓ 204  Agent Selection        (completed → pending)
  ✓ 205  PRD Authoring          (completed → pending)
  ✓ 206  PRD Validation         (completed → pending)
  ✓ 207  PRD Approval           (completed → pending)

Files to Delete (12 files, 245 KB):
  📄 .outputs/2-prd/prd-interview.json (15 KB)
  📄 .outputs/2-prd/prd-draft.md (180 KB)
  📄 .outputs/2-prd/requirements.json (8 KB)
  📄 .outputs/2-prd/validation-report.json (12 KB)
  📄 docs/prd/PRD.md (30 KB)
  📁 .outputs/2-prd/prompts/ (8 files)

Files to Preserve:
  ✓ .outputs/2-prd/setup.json (task 202)
  ✓ .outputs/1-discovery/* (all Phase 1 artifacts)

Dependencies OK:
  ✓ Task 203 depends on: selected-approach.json (exists)
  ✓ Task 203 depends on: direction-confirmed.json (exists)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  WARNING: This action cannot be undone.

To proceed, type: reset-to-203

Confirmation: _
```

### 3. Implementation Components

#### A. `scripts/reset-to-task.py`
```python
#!/usr/bin/env python3
"""
Task Reset & Recovery Tool

Resets pipeline state to a specific task with structured cleanup.
"""

import sys
import json
import os
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass

@dataclass
class ResetPlan:
    target_task: str
    tasks_to_reset: List[str]
    files_to_delete: List[Path]
    files_to_preserve: List[Path]
    dependencies_met: bool
    total_size_kb: int

class TaskResetManager:
    def __init__(self, atomic_root: Path):
        self.atomic_root = atomic_root
        self.task_state_file = atomic_root / ".claude" / "task-state.json"
        self.task_state = self._load_task_state()

    def analyze_reset(self, target_task: str) -> ResetPlan:
        """Analyze impact of resetting to target task."""
        phase_id = self._get_phase_id(target_task)

        # Find all tasks chronologically after target
        tasks_to_reset = self._get_subsequent_tasks(target_task)

        # Collect artifacts to delete
        files_to_delete = []
        for task_id in tasks_to_reset:
            files_to_delete.extend(self._get_task_artifacts(task_id))

        # Check dependencies
        deps_met = self._validate_dependencies(target_task)

        # Calculate total size
        total_size = sum(f.stat().st_size for f in files_to_delete if f.exists())

        return ResetPlan(
            target_task=target_task,
            tasks_to_reset=tasks_to_reset,
            files_to_delete=files_to_delete,
            files_to_preserve=self._get_preserved_files(target_task),
            dependencies_met=deps_met,
            total_size_kb=total_size // 1024
        )

    def execute_reset(self, plan: ResetPlan, confirmed: bool = False):
        """Execute the reset plan."""
        if not confirmed:
            if not self._get_user_confirmation(plan):
                print("Reset cancelled.")
                return False

        # Delete files
        for file_path in plan.files_to_delete:
            if file_path.exists():
                file_path.unlink()
                print(f"  ✓ Deleted: {file_path.relative_to(self.atomic_root)}")

        # Reset task states
        for task_id in plan.tasks_to_reset:
            self._reset_task_state(task_id)

        # Save updated state
        self._save_task_state()

        print(f"\n✅ Reset complete. Pipeline ready from task {plan.target_task}")
        return True

    def _get_user_confirmation(self, plan: ResetPlan) -> bool:
        """Display impact and get user confirmation."""
        self._display_impact(plan)

        print(f"\n⚠️  WARNING: This action cannot be undone.")
        print(f"\nTo proceed, type: reset-to-{plan.target_task}\n")

        user_input = input("Confirmation: ").strip()
        return user_input == f"reset-to-{plan.target_task}"

    def _display_impact(self, plan: ResetPlan):
        """Display formatted impact analysis."""
        print("╔═══════════════════════════════════════════════════════════════╗")
        print("║ TASK RESET IMPACT ANALYSIS                                    ║")
        print("╚═══════════════════════════════════════════════════════════════╝")
        print(f"\nTarget: Reset to Task {plan.target_task}")
        print(f"\nTasks to Reset: {len(plan.tasks_to_reset)} tasks")
        for task_id in plan.tasks_to_reset:
            task = self._get_task_info(task_id)
            print(f"  ✓ {task_id}  {task['name']:<25} ({task['status']} → pending)")

        print(f"\nFiles to Delete: {len(plan.files_to_delete)} files, {plan.total_size_kb} KB")
        for file_path in plan.files_to_delete[:10]:  # Show first 10
            size_kb = file_path.stat().st_size // 1024 if file_path.exists() else 0
            print(f"  📄 {file_path.relative_to(self.atomic_root)} ({size_kb} KB)")
        if len(plan.files_to_delete) > 10:
            print(f"  ... and {len(plan.files_to_delete) - 10} more files")

        print(f"\nDependencies: {'✓ OK' if plan.dependencies_met else '✗ MISSING'}")

# ... rest of implementation
```

#### B. Integration with Phase Menu

Enhance `lib/phase.sh` jump functionality:

```bash
# Current (line 789):
read -e -p "  Choice (default: c): " choice || true

# Enhanced:
case "$choice" in
    j|J)
        echo ""
        read -e -p "  Jump to task: " jump_task || true
        if [[ -n "$jump_task" ]]; then
            # Call Python reset tool with impact analysis
            python3 "$ATOMIC_ROOT/scripts/reset-to-task.py" "$jump_task" --interactive
            if [[ $? -eq 0 ]]; then
                return $TASK_JUMP
            fi
        fi
        ;;
esac
```

#### C. Artifact Tracking Enhancement

Update `lib/atomic.sh` to track artifacts:

```bash
atomic_register_artifact() {
    local task_id="$1"
    local file_path="$2"
    local artifact_type="${3:-created}"  # created|modified|dependency

    # Append to task state
    local tmp=$(atomic_mktemp)
    jq --arg task "$task_id" \
       --arg file "$file_path" \
       --arg type "$artifact_type" \
       ".phases[env.CURRENT_PHASE].tasks[$task].artifacts[$type] += [$file]" \
       "$TASK_STATE_FILE" > "$tmp"
    mv "$tmp" "$TASK_STATE_FILE"
}

# Auto-track on file creation
atomic_create_output() {
    local file_path="$1"
    local task_id="${CURRENT_TASK:-unknown}"

    # Create file (existing logic)
    # ...

    # Track artifact
    atomic_register_artifact "$task_id" "$file_path" "created"
}
```

### 4. Safety Features

#### A. Backup Before Reset
```bash
# Create backup before destructive operation
atomic_backup_before_reset() {
    local target_task="$1"
    local backup_dir=".state/backups/reset-$(date +%Y%m%d-%H%M%S)"

    mkdir -p "$backup_dir"

    # Backup task state
    cp .claude/task-state.json "$backup_dir/"

    # Backup artifacts that will be deleted
    # ...

    echo "Backup created: $backup_dir"
}
```

#### B. Rollback Capability
```python
def rollback_reset(backup_id: str):
    """Rollback a reset operation using backup."""
    backup_dir = f".state/backups/{backup_id}"

    # Restore task state
    shutil.copy(f"{backup_dir}/task-state.json", ".claude/task-state.json")

    # Restore files
    # ...
```

### 5. Documentation & User Guidance

#### A. Error Recovery Guide

Create `docs/ERROR-RECOVERY.md`:

```markdown
# Error Recovery Guide

## Common Scenarios

### AWS Token Expired
**Error**: "Token is expired. To refresh this SSO session run 'aws sso login'"

**Recovery**:
1. Refresh token: `aws sso login --profile bedrock-dev`
2. Reset current task: `./scripts/reset-to-task.py <task-id>`
3. Continue: Choose `[c] Continue`

### Task Failed Mid-Execution
**Error**: Task 205 failed, partial outputs created

**Recovery**:
1. Analyze impact: `./scripts/reset-to-task.py 205 --dry-run`
2. Reset task: `./scripts/reset-to-task.py 205`
3. Fix underlying issue
4. Retry: `./main.sh run 2 --resume-at=205`

### Want to Rework Requirements
**Scenario**: Realized requirements in task 203 need changes

**Recovery**:
1. Check impact: `./scripts/reset-to-task.py 203 --dry-run`
2. Confirm reset: `./scripts/reset-to-task.py 203`
3. Rework: Continue from task 203
```

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. ✅ Design spec (this document)
2. Create `scripts/reset-to-task.py` skeleton
3. Implement `TaskResetManager.analyze_reset()`
4. Add basic artifact tracking to `lib/atomic.sh`

### Phase 2: Core Features (Week 2)
1. Implement `execute_reset()` with file deletion
2. Add user confirmation flow
3. Create impact display formatter
4. Add dependency validation

### Phase 3: Integration (Week 3)
1. Hook into `[j] Jump to` menu
2. Add `--reset-from` CLI flag
3. Enhance all tasks to register artifacts
4. Test end-to-end recovery flows

### Phase 4: Safety & UX (Week 4)
1. Add backup/rollback system
2. Create error recovery documentation
3. Add dry-run mode
4. Add unit tests

## Testing Strategy

### Test Cases
1. Reset single task (205 → 205)
2. Reset range (203 → 207)
3. Reset entire phase (201 → 210)
4. Reset with missing dependencies (should fail)
5. Reset with orphaned artifacts
6. Rollback after reset

### Integration Tests
```python
def test_reset_single_task():
    # Complete task 205
    complete_task("205")
    assert task_state("205") == "completed"

    # Reset task 205
    reset_to_task("205")
    assert task_state("205") == "pending"
    assert not exists("outputs/2-prd/prd-draft.md")

def test_reset_preserves_dependencies():
    complete_task("203")
    reset_to_task("203")

    # Task 202 artifacts should still exist
    assert exists("outputs/2-prd/setup.json")
```

## Future Enhancements

1. **Smart Reset**: AI-driven suggestion of reset point based on error
2. **Partial Reset**: Reset only specific sections of a task
3. **Reset Templates**: Pre-defined reset scenarios
4. **Collaborative Reset**: Handle multi-user scenarios
5. **Cloud Backup**: Backup state to S3 before reset

## Success Metrics

1. **User Confidence**: Users comfortable jumping back without fear
2. **Recovery Time**: < 30 seconds to analyze and execute reset
3. **Error Rate**: Zero accidental data loss
4. **Documentation**: Clear recovery path for every error type

---

**Status**: 📋 Design Complete - Ready for Implementation
**Owner**: TBD
**Priority**: HIGH (blocking production use)
