# Memory Audit Testing Guide

**Date**: 2026-02-04
**Purpose**: Validate claude-mem integration across all 70 pipeline tasks

---

## Overview

The Memory Audit Runner (`test/memory_audit_runner.py`) validates proper integration of the claude-mem (memory persistence) system across the entire atomic-claude2 pipeline. It ensures that:

1. Memory artifacts are created correctly
2. Memory saves occur at appropriate points
3. Memory recalls function properly
4. Memory file integrity is maintained
5. All phases participate in the memory system

---

## Quick Start

```bash
# Test all phases (0-9) with memory audit
python test/memory_audit_runner.py

# Test specific phase
python test/memory_audit_runner.py --phase 2

# Verbose output with detailed memory operations
python test/memory_audit_runner.py --verbose

# Test multiple specific phases
python test/memory_audit_runner.py --phase 0
python test/memory_audit_runner.py --phase 1
python test/memory_audit_runner.py --phase 2
```

---

## What It Tests

### 1. Memory Artifact Creation

**Validates**:
- Memory files are created in `.state/memory/phase-N/`
- Each phase creates appropriate artifacts
- File structure follows expected patterns

**Example Output**:
```
  Memory Analysis:
    ✓ Created 5 memory artifacts
      - phase-2/task-205-prd-section-1.md
      - phase-2/task-205-prd-section-2.md
      - phase-2/task-205-tech-stack-locked.md
      - phase-2/task-206-validation-report.json
      - phase-2/closeout-summary.md
```

### 2. Memory Operations Detection

**Validates**:
- Tasks call `memory_save()` / `_memory_save_local()`
- Tasks call `memory_recall()` / `_memory_recall_local()`
- Tasks create checkpoints with `memory_checkpoint()`

**Example Output**:
```
    ✓ Detected 8 memory saves
    ✓ Detected 3 memory recalls
    ✓ Detected 1 checkpoints
```

### 3. Memory Integrity Verification

**Validates**:
- Memory artifacts are readable
- Files have non-zero content
- No corrupted or empty files

**Example Output**:
```
  Memory Integrity Checks:
    ✓ Phase 00: 3/3 artifacts valid
    ✓ Phase 01: 7/7 artifacts valid
    ✓ Phase 02: 12/12 artifacts valid
    ⚠ Phase 03: 4/5 artifacts valid
      - Invalid: task-303-incomplete.md
```

### 4. Per-Phase Memory Usage

**Validates**:
- Which phases use memory
- How many artifacts each phase creates
- Memory usage patterns across pipeline

**Example Output**:
```
  Per-Phase Memory Usage:
    ✓ Phase 00: 3 artifacts
    ✓ Phase 01: 7 artifacts
    ✓ Phase 02: 12 artifacts
    ⚠ Phase 03: 0 artifacts (no memory usage)
```

---

## Memory System Architecture

### Memory Directory Structure

```
.state/memory/
├── phase-0-setup/
│   ├── task-002-extracted-config.json
│   ├── task-003-reviewed-config.json
│   └── closeout-summary.md
├── phase-1-discovery/
│   ├── task-104-agent-selection.json
│   ├── task-106-discovery-summary.md
│   └── closeout-summary.md
├── phase-2-prd/
│   ├── task-205-prd-section-1.md
│   ├── task-205-prd-section-2.md
│   ├── task-205-tech-stack-locked.md
│   └── closeout-summary.md
└── ... (phase-3 through phase-9)
```

### Memory Functions

**Core Functions** (from `lib/memory.sh`):
- `memory_init()` - Initialize memory system
- `memory_should_persist()` - Check if enabled
- `_memory_save_local(phase, task, key, content)` - Save artifact
- `_memory_recall_local(query, limit)` - Recall by semantic search
- `memory_task_start(phase, task)` - Task lifecycle start
- `memory_task_end(phase, task)` - Task lifecycle end
- `memory_add_checkpoint(phase, summary)` - Create checkpoint

**Python Wrapper** (from `core/memory.py`):
- `memory_init()` - Initialize
- `memory_should_persist()` - Check enabled
- Wraps bash functions via subprocess

---

## Expected Memory Usage by Phase

| Phase | Expected Artifacts | Key Memory Items |
|-------|-------------------|------------------|
| **Phase 0** | 3-5 | Config, secrets, setup decisions |
| **Phase 1** | 5-10 | Agent selections, corpus analysis, approaches |
| **Phase 2** | 10-15 | PRD sections, tech stack, requirements |
| **Phase 3** | 5-8 | Task decomposition, dependencies |
| **Phase 4** | 8-12 | OpenSpec files, TDD subtasks |
| **Phase 5** | 10-15 | Test results, implementation notes |
| **Phase 6** | 6-10 | Review findings, refinements |
| **Phase 7** | 8-12 | Integration results, test reports |
| **Phase 8** | 5-8 | Deployment artifacts, approval |
| **Phase 9** | 3-5 | Release notes, confirmation |

---

## Understanding the Report

### Overall Assessment Criteria

**✅ EXCELLENT** (100% memory usage):
- All phases create memory artifacts
- All artifacts are valid (readable, non-empty)
- No integrity issues

**⚠️ GOOD** (70%+ memory usage):
- Most phases create memory artifacts
- Minor integrity issues
- Some phases may not use memory (acceptable if appropriate)

**❌ NEEDS IMPROVEMENT** (<70% memory usage):
- Multiple phases missing memory artifacts
- Integrity issues present
- Core phases (1, 2, 3) not using memory

### Example Full Report

```
================================================================================
  MEMORY AUDIT REPORT
================================================================================

  Phases Tested: 10
  Phases Using Memory: 9/10
  Total Memory Artifacts: 87

  Per-Phase Memory Usage:
    ✓ Phase 00: 3 artifacts
    ✓ Phase 01: 9 artifacts
    ✓ Phase 02: 14 artifacts
    ✓ Phase 03: 7 artifacts
    ✓ Phase 04: 11 artifacts
    ✓ Phase 05: 13 artifacts
    ✓ Phase 06: 9 artifacts
    ✓ Phase 07: 12 artifacts
    ✓ Phase 08: 6 artifacts
    ⚠ Phase 09: 0 artifacts

  Memory Integrity Checks:
    ✓ Phase 00: 3/3 artifacts valid
    ✓ Phase 01: 9/9 artifacts valid
    ✓ Phase 02: 14/14 artifacts valid
    ✓ Phase 03: 7/7 artifacts valid
    ✓ Phase 04: 11/11 artifacts valid
    ✓ Phase 05: 13/13 artifacts valid
    ✓ Phase 06: 9/9 artifacts valid
    ✓ Phase 07: 12/12 artifacts valid
    ✓ Phase 08: 6/6 artifacts valid

  Overall Assessment:
    ⚠️ GOOD - Most phases use memory

  Memory Storage:
    Location: /path/to/.state/memory
    Total Files: 84
    Total Size: 1,247,829 bytes (1218.6 KB)

  Detailed report saved: test/reports/memory-audit-20260204-143022.json
```

---

## Detailed Report Format

The runner saves a JSON report to `test/reports/memory-audit-YYYYMMDD-HHMMSS.json`:

```json
{
  "timestamp": "2026-02-04T14:30:22.123456",
  "phases_tested": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  "memory_saves": {
    "phase-0": [
      "phase-0-setup/task-002-extracted-config.json",
      "phase-0-setup/task-003-reviewed-config.json",
      "phase-0-setup/closeout-summary.md"
    ],
    "phase-1": [
      "phase-1-discovery/task-104-agent-selection.json",
      "phase-1-discovery/task-106-discovery-summary.md",
      ...
    ],
    ...
  },
  "memory_recalls": {
    "phase-2": ["tech_stack", "requirements"],
    "phase-5": ["FR-001", "NFR-003"],
    ...
  },
  "summary": {
    "phases_with_memory": 9,
    "total_artifacts": 87
  }
}
```

---

## Troubleshooting

### No Memory Artifacts Created

**Symptoms**:
```
  Memory Analysis:
    ⚠ No memory artifacts created
```

**Possible Causes**:
1. Memory system not enabled (check `ATOMIC_MEMORY_ENABLED=true`)
2. UAT mode bypassing memory saves
3. Tasks don't have memory integration yet

**Solutions**:
- Verify environment: `echo $ATOMIC_MEMORY_ENABLED`
- Check task scripts have `memory_save()` calls
- Review memory initialization in phase orchestrators

### Invalid Memory Artifacts

**Symptoms**:
```
  Memory Integrity Checks:
    ⚠ Phase 02: 11/12 artifacts valid
      - Invalid: task-205-incomplete.md
```

**Possible Causes**:
1. Task failed mid-execution
2. Memory save called with empty content
3. File corruption

**Solutions**:
- Check task exit codes
- Review task logs for errors
- Re-run phase to regenerate artifacts

### Missing Expected Artifacts

**Symptoms**:
```
  Per-Phase Memory Usage:
    ⚠ Phase 03: 0 artifacts
```

**Possible Causes**:
1. Phase doesn't use memory (may be intentional)
2. Memory saves not implemented in phase tasks
3. Memory system disabled

**Solutions**:
- Review phase design (some phases may not need memory)
- Check if tasks have `_memory_save_local()` calls
- Verify memory system is initialized

---

## Integration with UAT Testing

The memory audit runner works alongside the UAT runner:

```bash
# First: Run UAT to ensure phases work
python test/uat_runner.py

# Then: Run memory audit to validate persistence
python test/memory_audit_runner.py

# Or run both for complete validation
python test/uat_runner.py && python test/memory_audit_runner.py
```

---

## Memory Audit Best Practices

### When to Run

1. **After major changes** to memory system
2. **After adding new phases** to pipeline
3. **Before releases** to ensure memory integrity
4. **During development** when working on memory features
5. **Weekly** as part of regression testing

### What to Look For

**Good Patterns**:
- ✅ All phases create at least 1 memory artifact
- ✅ Critical phases (1, 2, 3) have substantial memory usage
- ✅ 100% artifact integrity
- ✅ Memory grows consistently across phases

**Bad Patterns**:
- ❌ Zero memory usage in core phases
- ❌ Invalid/corrupted artifacts
- ❌ Memory size doesn't grow (suggests saves not working)
- ❌ Sudden drops in artifact count between phases

---

## Future Enhancements

Planned improvements for memory audit runner:

1. **Semantic search validation**: Test memory recalls with actual queries
2. **Cross-phase references**: Validate memory links between phases
3. **Performance metrics**: Measure memory save/recall latency
4. **Memory compression**: Test memory size optimization
5. **Remote memory**: Validate claude.ai sync (when implemented)

---

## Related Documentation

- `docs/BUG-PATTERNS.md` - Common memory-related bugs
- `lib/memory.sh` - Memory system implementation
- `core/memory.py` - Python memory wrapper
- `docs/PHASE-*-MIGRATION.md` - Phase-specific memory usage

---

*Last updated: 2026-02-04*
*Memory audit runner version: 1.0*
