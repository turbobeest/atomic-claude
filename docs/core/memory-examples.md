# Memory System - Usage Examples

Real-world examples of using the Memory System in atomic-claude2.

## Example 1: Basic Task Memory

```python
from core.memory import memory_init, memory_save, memory_recall

# Initialize memory system
memory_init()

# Task 001: Save configuration
memory_save(
    phase="0-setup",
    task_id="001",
    content="""
    Configuration Completed:
    - Python version: 3.11.5
    - Package manager: pip
    - Virtual environment: .venv
    - Dependencies: 42 packages installed
    """,
    tags=["config", "setup", "python"]
)

# Task 002: Recall previous context
context = memory_recall("configuration python")
print(f"Found {len(context.entries)} relevant entries")
for entry in context.entries:
    print(f"[{entry.phase}:{entry.task_id}] {entry.content[:100]}...")
```

## Example 2: Phase Checkpointing

```python
from core.memory import memory_checkpoint, memory_restore

# Complete Phase 0 - Create comprehensive checkpoint
checkpoint_id = memory_checkpoint(
    phase=0,
    phase_name="Setup",
    summary="""
    Phase 0 (Setup) completed successfully.

    Key Accomplishments:
    - Environment configured and validated
    - Project structure created
    - Dependencies installed
    - Configuration files generated
    """,
    key_decisions=[
        "Selected Python 3.11 for type hint support",
        "Chose pytest for testing framework",
        "Using JSON for configuration storage"
    ],
    artifacts=[
        ".outputs/0-setup/project-config.json",
        ".outputs/0-setup/secrets.json",
        ".outputs/0-setup/env-validation.json"
    ],
    state_snapshot={
        "tasks_completed": 10,
        "tasks_failed": 0,
        "warnings": [],
        "total_duration_seconds": 120
    }
)

print(f"Checkpoint created: {checkpoint_id}")

# Later: Restore checkpoint
checkpoint = memory_restore(checkpoint_id)
if checkpoint:
    print(f"Restored Phase {checkpoint.phase}: {checkpoint.phase_name}")
    print(f"Key decisions: {checkpoint.key_decisions}")
```

## Example 3: Multi-Phase Context Flow

```python
from core.memory import memory_save, memory_recall_phase, memory_checkpoint

# Phase 0: Setup
memory_save(
    phase="0-setup",
    task_id="001",
    content="Environment validated: Python 3.11, pip 23.0",
    tags=["validation", "environment"]
)

memory_checkpoint(
    phase=0,
    phase_name="Setup",
    summary="Setup complete"
)

# Phase 1: Discovery - Recall Phase 0 context
phase0_context = memory_recall_phase(0)
print("Phase 0 Summary:")
for entry in phase0_context.entries:
    print(f"  - {entry.content}")

# Phase 1: Save discovery results
memory_save(
    phase="1-discovery",
    task_id="101",
    content="""
    Corpus Analysis Complete:
    - Total files: 156
    - Languages: Python (80%), JavaScript (15%), Other (5%)
    - LOC: 42,000
    - Test coverage: 72%
    """,
    tags=["analysis", "corpus", "metrics"]
)

# Phase 2: PRD - Recall both Phase 0 and Phase 1
setup_context = memory_recall_phase(0)
discovery_context = memory_recall_phase(1)

print(f"Building on {len(setup_context.entries)} setup decisions")
print(f"Using {len(discovery_context.entries)} discovery insights")
```

## Example 4: Intelligent Context Recall

```python
from core.memory import memory_save, memory_recall

# Save various entries
memory_save(
    phase="0-setup",
    task_id="001",
    content="Database: PostgreSQL 15 configured on port 5432",
    tags=["database", "postgresql", "config"]
)

memory_save(
    phase="0-setup",
    task_id="002",
    content="API Gateway: FastAPI configured with CORS",
    tags=["api", "fastapi", "web"]
)

memory_save(
    phase="1-discovery",
    task_id="101",
    content="Database schema: 15 tables, normalized to 3NF",
    tags=["database", "schema", "design"]
)

# Recall with specific query - gets scored by relevance
context = memory_recall(
    query="database configuration schema",
    max_tokens=2000,
    relevance_threshold=0.4
)

print(f"Found {len(context.entries)} entries (total {context.total_tokens} tokens)")
for entry in context.entries:
    print(f"[Relevance: {entry.relevance_score:.2f}] {entry.content}")
```

## Example 5: Backtracking Scenario

```python
from core.memory import (
    memory_save,
    memory_checkpoint,
    memory_handle_backtrack,
    memory_list_checkpoints,
    CheckpointStatus
)

# Create checkpoints for multiple phases
for phase in range(3):
    memory_save(
        phase=f"{phase}-phase",
        task_id=f"{phase}01",
        content=f"Phase {phase} work completed"
    )
    memory_checkpoint(
        phase=phase,
        phase_name=f"Phase {phase}",
        summary=f"Phase {phase} done"
    )

# Oops - need to backtrack to Phase 0
print("Backtracking to Phase 0...")
result = memory_handle_backtrack(target_phase=0)

print(f"Invalidated {result['invalidated_checkpoints']} checkpoints")
print(f"Cleared {result['cleared_entries']} memory entries")

# Check checkpoint statuses
checkpoints = memory_list_checkpoints()
for cp in checkpoints:
    status = "✓" if cp.status == CheckpointStatus.VALID else "✗"
    print(f"{status} Phase {cp.phase}: {cp.status}")
```

## Example 6: Memory Compaction

```python
from core.memory import memory_save, memory_stats, memory_compact
from datetime import datetime, timedelta

# Simulate old, low-value entries
for i in range(100):
    memory_save(
        phase="0-setup",
        task_id=f"{i:03d}",
        content=f"Minor entry {i}",
        tags=[]
    )

# Check initial stats
initial_stats = memory_stats()
print(f"Initial: {initial_stats.total_entries} entries, {initial_stats.size_mb} MB")

# Compact aggressively
result = memory_compact(
    max_size_mb=1.0,      # Target size
    max_age_days=30,      # Remove entries older than 30 days
    min_relevance=0.5     # Keep only relevant entries
)

# Check final stats
final_stats = memory_stats()
print(f"Final: {final_stats.total_entries} entries, {final_stats.size_mb} MB")
print(f"Removed: {result['total_removed']} entries")
print(f"Saved: {result['size_reduction_mb']} MB")
```

## Example 7: Task-Level Memory Pattern

```python
from core.memory import memory_save, memory_recall
from core.memory.types import MemoryEntryType

def task_102_corpus_analysis() -> bool:
    """Execute task 102: Corpus Analysis."""

    # Recall context from previous tasks
    context = memory_recall(
        query="corpus files languages",
        phase="1-discovery",
        max_tokens=2000
    )

    print("Previous context:")
    for entry in context.entries:
        print(f"  - {entry.content[:80]}...")

    # Perform analysis
    result = analyze_corpus()

    # Save results to memory
    if result.success:
        memory_save(
            phase="1-discovery",
            task_id="102",
            content=f"""
            Corpus Analysis Complete:
            - Files analyzed: {result.file_count}
            - Languages detected: {', '.join(result.languages)}
            - Total LOC: {result.loc}
            - Key patterns: {', '.join(result.patterns)}
            """,
            tags=["corpus", "analysis", "complete"],
            entry_type=MemoryEntryType.TASK_END,
            metadata={
                "file_count": result.file_count,
                "languages": result.languages,
                "duration_seconds": result.duration
            }
        )
        return True

    return False
```

## Example 8: Cross-Phase Decision Tracking

```python
from core.memory import memory_save, memory_recall

# Phase 0: Record architectural decision
memory_save(
    phase="0-setup",
    task_id="003",
    content="""
    Architectural Decision: Microservices

    Rationale:
    - Need for independent scaling
    - Team size supports distributed development
    - Domain boundaries are well-defined

    Implications:
    - API Gateway required
    - Service mesh for inter-service communication
    - Distributed tracing needed
    """,
    tags=["architecture", "decision", "microservices"]
)

# Phase 2: PRD references the decision
context = memory_recall("architecture microservices decision")
print("Architectural decisions:")
for entry in context.entries:
    if "Architectural Decision" in entry.content:
        print(entry.content)

# Use in PRD
memory_save(
    phase="2-prd",
    task_id="201",
    content=f"""
    PRD Section: System Architecture

    Based on Phase 0 decision (microservices):
    - Service breakdown: Auth, Users, Orders, Payments
    - Communication: REST + Message Queue
    - Data: PostgreSQL per service
    """,
    tags=["prd", "architecture"]
)
```

## Example 9: Recent Activity Tracking

```python
from core.memory import memory_save, memory_recall_recent

# Simulate recent activity
activities = [
    ("Ran tests", "All 42 tests passed"),
    ("Updated config", "Added CORS settings"),
    ("Fixed bug", "Resolved race condition in cache"),
    ("Added feature", "Implemented user authentication"),
    ("Reviewed code", "Approved PR #123")
]

for title, details in activities:
    memory_save(
        phase="5-implementation",
        task_id="501",
        content=f"{title}: {details}",
        tags=["activity"]
    )

# Show recent activity log
recent = memory_recall_recent(count=5)
print("Recent Activity:")
for i, entry in enumerate(recent.entries, 1):
    print(f"{i}. [{entry.timestamp.strftime('%H:%M:%S')}] {entry.content}")
```

## Example 10: Error Recovery Pattern

```python
from core.memory import (
    memory_save,
    memory_recall,
    memory_checkpoint,
    memory_restore,
    memory_get_latest_checkpoint
)
from core.memory.types import MemoryEntryType

def execute_risky_task():
    """Execute task with checkpoint-based recovery."""

    # Create checkpoint before risky operation
    checkpoint_id = memory_checkpoint(
        phase=5,
        phase_name="Implementation",
        summary="Before database migration",
        state_snapshot={
            "database_version": "1.0",
            "tables": ["users", "orders"]
        }
    )

    try:
        # Risky operation
        run_database_migration()

        # Success - save to memory
        memory_save(
            phase="5-implementation",
            task_id="501",
            content="Database migration successful",
            tags=["migration", "success"],
            entry_type=MemoryEntryType.SYSTEM_EVENT
        )

        return True

    except Exception as e:
        # Error - save error and restore checkpoint
        memory_save(
            phase="5-implementation",
            task_id="501",
            content=f"Migration failed: {str(e)}",
            tags=["migration", "error"],
            entry_type=MemoryEntryType.SYSTEM_EVENT
        )

        # Restore from checkpoint
        checkpoint = memory_restore(checkpoint_id)
        print(f"Restored to checkpoint: {checkpoint.summary}")
        print(f"Database version: {checkpoint.state_snapshot['database_version']}")

        return False
```

## Performance Considerations

```python
from core.memory import memory_recall
import time

# Efficient: Specific query with filters
start = time.time()
context = memory_recall(
    query="database schema configuration",
    phase="0-setup",
    max_tokens=1000,
    relevance_threshold=0.5
)
print(f"Filtered recall: {time.time() - start:.3f}s")

# Less efficient: Broad query without filters
start = time.time()
context = memory_recall(
    query="anything",
    max_tokens=10000,
    relevance_threshold=0.1
)
print(f"Broad recall: {time.time() - start:.3f}s")

# Most efficient: Phase-specific recall
start = time.time()
context = memory_recall_phase(0)
print(f"Phase recall: {time.time() - start:.3f}s")
```

## Best Practices Summary

1. **Tag comprehensively** - More tags = better recall
2. **Use specific queries** - "database schema config" > "stuff"
3. **Set appropriate token limits** - Balance completeness vs performance
4. **Create checkpoints at boundaries** - Phase completion, major milestones
5. **Compact regularly** - After each phase
6. **Include metadata** - Structured data for later analysis
7. **Save task outcomes** - What happened, not just what was planned
8. **Reference previous decisions** - Build on past context
9. **Handle errors gracefully** - Save error info for debugging
10. **Test recall queries** - Verify you get expected results
