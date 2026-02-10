# Parallel Subagents - Implementation Example

**Date:** February 10, 2026
**Function:** `atomic_invoke_parallel` in `lib/atomic.sh`
**Example:** Phase 1 Task 102 (Corpus Collection)

---

## Overview

Parallel subagents allow multiple Claude invocations to run simultaneously, dramatically speeding up I/O-bound tasks.

**Key Constraint:** Only premium models (Sonnet/Opus) are used. Haiku is automatically blocked to ensure quality.

---

## Function Signature

```bash
atomic_invoke_parallel "overall_description" \
    "task1_name:prompt1.md:output1.json" \
    "task2_name:prompt2.md:output2.json" \
    "task3_name:prompt3.md:output3.json"
```

**Parameters:**
- `$1` - Overall description (for logging/UI)
- `$2+` - Task specifications in format: `name:prompt_file:output_file`

**Returns:**
- `0` if all tasks succeed
- `N` (count of failures) if any tasks fail

---

## Example: Phase 1 Task 102 Refactor

### Before (Sequential)

```bash
#!/usr/bin/env bash
# Task 102: Corpus Collection - Sequential (SLOW)

task_102_corpus_collection() {
    atomic_step "Corpus Collection"

    # Collect source files (2-3 minutes)
    atomic_invoke "prompts/collect-source.md" \
        ".outputs/1-discovery/corpus-source.json" \
        "Collect Source Files"

    # Collect test files (1-2 minutes)
    atomic_invoke "prompts/collect-tests.md" \
        ".outputs/1-discovery/corpus-tests.json" \
        "Collect Test Files"

    # Collect config files (1 minute)
    atomic_invoke "prompts/collect-configs.md" \
        ".outputs/1-discovery/corpus-configs.json" \
        "Collect Config Files"

    # Collect documentation (1-2 minutes)
    atomic_invoke "prompts/collect-docs.md" \
        ".outputs/1-discovery/corpus-docs.json" \
        "Collect Documentation"

    # Total time: 5-8 minutes (sequential)
    atomic_success "Corpus collection complete"
}
```

### After (Parallel)

```bash
#!/usr/bin/env bash
# Task 102: Corpus Collection - Parallel (FAST)

task_102_corpus_collection() {
    atomic_step "Corpus Collection"

    # Launch all collection tasks in parallel
    atomic_invoke_parallel "Corpus Collection" \
        "source:prompts/collect-source.md:.outputs/1-discovery/corpus-source.json" \
        "tests:prompts/collect-tests.md:.outputs/1-discovery/corpus-tests.json" \
        "configs:prompts/collect-configs.md:.outputs/1-discovery/corpus-configs.json" \
        "docs:prompts/collect-docs.md:.outputs/1-discovery/corpus-docs.json"

    local exit_code=$?

    # Total time: 2-3 minutes (parallel)
    # Speedup: 2.5-3x faster!

    if [[ $exit_code -eq 0 ]]; then
        atomic_success "Corpus collection complete (parallel execution)"
        return 0
    else
        atomic_error "Corpus collection failed: $exit_code tasks failed"
        return 1
    fi
}
```

**Time Savings:** 5-8 minutes → 2-3 minutes (**2.5-3x speedup**)

---

## Output Example

```
┌─────────────────────────────────────────────────────────────┐
│  Step: Corpus Collection (Parallel Execution)              │
└─────────────────────────────────────────────────────────────┘

ℹ  Launching 4 subagents with model: sonnet

  └── [1/4] Launching: source
  └── [2/4] Launching: tests
  └── [3/4] Launching: configs
  └── [4/4] Launching: docs

ℹ  All 4 subagents launched, waiting for completion...

    [source] Step: Collect Source Files
    [tests] Step: Collect Test Files
    [configs] Step: Collect Config Files
    [docs] Step: Collect Documentation

    [configs] ✓ Claude completed task (45s)
    [tests] ✓ Claude completed task (67s)
    [source] ✓ Claude completed task (89s)
    [docs] ✓ Claude completed task (92s)

✓ [configs] Complete (45s)
✓ [tests] Complete (67s)
✓ [source] Complete (89s)
✓ [docs] Complete (92s)

✓ Corpus Collection: All 4 subagents completed successfully
```

---

## Quality Enforcement

The function automatically enforces premium models:

```bash
# User configures Haiku
export ATOMIC_SUBAGENT_MODEL="haiku"

# atomic_invoke_parallel detects and overrides:
# "⚠  Subagents require premium models for quality assurance"
# "⚠  Forcing sonnet (was: haiku)"

# All subagents run with sonnet instead
```

---

## Error Handling

### Scenario 1: One task fails

```bash
atomic_invoke_parallel "Corpus Collection" \
    "source:prompts/collect-source.md:.outputs/corpus-source.json" \
    "tests:prompts/MISSING.md:.outputs/corpus-tests.json"  # Bad path
```

**Output:**
```
✗ atomic_invoke_parallel: Prompt file not found: prompts/MISSING.md
```

**Returns:** `1` (immediate failure)

### Scenario 2: Task produces no output

```bash
# Task completes but writes nothing to output file
```

**Output:**
```
✓ [source] Complete (45s)
✗ [tests] Failed: No output generated
✓ [configs] Complete (52s)

✗ Corpus Collection: 1/3 subagents failed
```

**Returns:** `1` (count of failures)

### Scenario 3: Process error

```bash
# Claude process crashes mid-execution
```

**Output:**
```
✗ [source] Failed: Process error

✗ Corpus Collection: 1/4 subagents failed
```

**Returns:** `1`

---

## When to Use Parallel Subagents

### ✅ Good Use Cases

1. **Independent Data Collection**
   - Collecting source files, tests, configs (no dependencies)
   - Each task reads from filesystem, writes to separate output

2. **Multi-Perspective Review**
   - Security review, performance review, architecture review
   - Each review is independent, can run simultaneously

3. **Multi-File Generation**
   - Generate backend files, frontend files, test files
   - Each generation is independent

4. **Bulk Analysis**
   - Analyze API endpoints, database schemas, user flows
   - Each analysis is independent

### ❌ Bad Use Cases

1. **Sequential Dependencies**
   ```bash
   # BAD: Task 2 needs Task 1's output
   atomic_invoke_parallel "Bad Example" \
       "analyze:prompt1.md:analysis.json" \
       "generate:prompt2.md:code.py"  # Needs analysis.json
   ```

2. **Shared State Mutation**
   ```bash
   # BAD: Both tasks modify same file
   atomic_invoke_parallel "Bad Example" \
       "update1:prompt1.md:config.json" \
       "update2:prompt2.md:config.json"  # Race condition!
   ```

3. **Resource Constraints**
   - Running 50 parallel tasks will exhaust system resources
   - Keep to 4-8 tasks max for stability

---

## Performance Guidelines

| # Tasks | Expected Speedup | Recommended For |
|---------|------------------|-----------------|
| 2-3 tasks | 1.5-2x | Small parallelization |
| 4-6 tasks | 2-3x | Ideal range (Phase 1, 6) |
| 7-10 tasks | 3-4x | Large workloads (Phase 5) |
| 11+ tasks | 3-5x | Diminishing returns, may hit limits |

**Bottleneck:** LLM API rate limits, not local CPU/memory.

---

## Phase-Specific Applications

### Phase 1: Discovery (Task 102)
```bash
atomic_invoke_parallel "Corpus Collection" \
    "source:.../corpus-source.json" \
    "tests:.../corpus-tests.json" \
    "configs:.../corpus-configs.json" \
    "docs:.../corpus-docs.json"
```
**Speedup:** 2.5-3x (5-8 min → 2-3 min)

### Phase 5: Implementation
```bash
atomic_invoke_parallel "Code Generation" \
    "backend:.../backend-files.json" \
    "frontend:.../frontend-files.json" \
    "tests:.../test-files.json" \
    "migrations:.../migration-files.json"
```
**Speedup:** 3-4x (15-20 min → 4-6 min)

### Phase 6: Code Review
```bash
atomic_invoke_parallel "Multi-Perspective Review" \
    "security:.../security-review.md" \
    "performance:.../performance-review.md" \
    "architecture:.../architecture-review.md" \
    "testing:.../testing-review.md"
```
**Speedup:** 3-5x (20-30 min → 5-8 min)

### Phase 7: Integration Testing
```bash
atomic_invoke_parallel "Test Execution" \
    "unit:.../unit-test-results.json" \
    "integration:.../integration-test-results.json" \
    "e2e:.../e2e-test-results.json"
```
**Speedup:** 2-3x (10-15 min → 4-6 min)

---

## Monitoring

Check logs for parallel execution:

```bash
tail -f .logs/atomic.log | grep "atomic_invoke_parallel"
```

Output:
```
[2026-02-10T08:45:00] [atomic_invoke_parallel] Launching 4 subagents
[2026-02-10T08:45:01] [source] task="Collect Source Files" model=sonnet
[2026-02-10T08:45:01] [tests] task="Collect Test Files" model=sonnet
[2026-02-10T08:45:01] [configs] task="Collect Config Files" model=sonnet
[2026-02-10T08:45:01] [docs] task="Collect Documentation" model=sonnet
[2026-02-10T08:46:33] [atomic_invoke_parallel] All 4 subagents complete (92s)
```

---

## Testing

Test the parallel function:

```bash
# Create test prompts
mkdir -p test/parallel-test

echo "List 5 programming languages" > test/parallel-test/prompt1.md
echo "List 5 countries" > test/parallel-test/prompt2.md
echo "List 5 colors" > test/parallel-test/prompt3.md

# Run parallel test
source lib/atomic.sh

atomic_invoke_parallel "Parallel Test" \
    "languages:test/parallel-test/prompt1.md:test/parallel-test/output1.txt" \
    "countries:test/parallel-test/prompt2.md:test/parallel-test/output2.txt" \
    "colors:test/parallel-test/prompt3.md:test/parallel-test/output3.txt"

# Check outputs
cat test/parallel-test/output*.txt
```

---

## Configuration

Control parallel behavior with environment variables:

```bash
# Force specific model for subagents (default: $CLAUDE_MODEL or "sonnet")
export ATOMIC_SUBAGENT_MODEL="opus"  # Use opus for all subagents

# Haiku is always blocked regardless of config
export ATOMIC_SUBAGENT_MODEL="haiku"  # Will be overridden to sonnet
```

---

## Next Steps

1. ✅ Function implemented in `lib/atomic.sh`
2. Update Phase 1 Task 102 to use parallel execution
3. Update Phase 5 Implementation tasks
4. Update Phase 6 Review tasks
5. Benchmark and measure actual speedup

---

*Documentation created February 10, 2026*
