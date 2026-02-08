## Memory System - Complete Guide

The Memory System provides persistent context storage and recall across phases and sessions in atomic-claude2.

### Overview

The memory system is a pure Python refactor of the original bash `memory.sh` (47KB, 1,500 lines). It maintains behavioral parity while providing better structure, testability, and performance.

**Key Features:**
- Persistent context storage in JSON format
- Intelligent context recall with relevance scoring
- Automatic checkpointing at phase boundaries
- Backtrack detection and handling
- Memory compaction and optimization
- Thread-safe operations with atomic writes

### Architecture

```
core/memory/
├── __init__.py        # Public API
├── types.py          # Pydantic data models
├── store.py          # Persistence layer
├── checkpoint.py     # Checkpoint management
├── recall.py         # Context recall engine
└── compaction.py     # Memory optimization
```

### Quick Start

```python
from core.memory import (
    memory_init,
    memory_save,
    memory_recall,
    memory_checkpoint
)

# Initialize
memory_init()

# Save to memory
memory_save(
    phase="0-setup",
    task_id="001",
    content="Configuration completed successfully",
    tags=["config", "setup"]
)

# Recall context
context = memory_recall("configuration setup")
for entry in context.entries:
    print(f"[{entry.phase}] {entry.content}")

# Create checkpoint
checkpoint_id = memory_checkpoint(
    phase=0,
    phase_name="Setup",
    summary="Phase 0 completed successfully",
    key_decisions=["Used Python 3.11", "Selected PostgreSQL"]
)
```

### Core Concepts

#### 1. Memory Entries

Memory entries are the atomic units of stored context:

```python
entry = MemoryEntry(
    id="uuid-here",
    timestamp=datetime.now(),
    entry_type=MemoryEntryType.TASK_END,
    phase="0-setup",
    task_id="001",
    content="Configuration completed",
    tags=["config", "setup"],
    relevance_score=0.8
)
```

**Entry Types:**
- `TASK_START` - Task started
- `TASK_END` - Task completed
- `PHASE_CLOSEOUT` - Phase summary
- `CHECKPOINT` - Phase checkpoint
- `USER_NOTE` - User annotation
- `SYSTEM_EVENT` - System event

#### 2. Checkpoints

Checkpoints capture phase state for recovery:

```python
checkpoint = Checkpoint(
    checkpoint_id="phase0-20250206-143022",
    project="atomic-claude",
    phase=0,
    phase_name="Setup",
    summary="Phase 0 completed successfully",
    key_decisions=["Decision 1", "Decision 2"],
    artifacts=["/path/to/config.json"],
    state_snapshot={"key": "value"},
    context=[...],  # Relevant memory entries
    status=CheckpointStatus.VALID
)
```

#### 3. Memory Context

Context is returned from recall operations:

```python
context = MemoryContext(
    query="configuration setup",
    entries=[...],  # Sorted by relevance
    total_tokens=1234,
    max_tokens=4000,
    relevance_threshold=0.3
)
```

### API Reference

#### Initialization

```python
memory_init(state_dir: Optional[Path] = None) -> None
```

Initialize the memory system. Call once at startup.

**Args:**
- `state_dir`: State directory (defaults to `.state/`)

#### Saving Memory

```python
memory_save(
    phase: str,
    task_id: Optional[str],
    content: str,
    tags: Optional[List[str]] = None,
    entry_type: MemoryEntryType = MemoryEntryType.TASK_END,
    metadata: Optional[Dict[str, Any]] = None
) -> str
```

Save content to memory.

**Args:**
- `phase`: Phase ID (e.g., "0-setup")
- `task_id`: Task ID (optional)
- `content`: Content to save
- `tags`: Tags for searching
- `entry_type`: Type of entry
- `metadata`: Additional metadata

**Returns:** Entry ID

**Example:**
```python
entry_id = memory_save(
    phase="1-discovery",
    task_id="101",
    content="Completed corpus analysis",
    tags=["analysis", "corpus"],
    metadata={"files_analyzed": 42}
)
```

#### Recalling Memory

```python
memory_recall(
    query: str,
    phase: Optional[str] = None,
    task_id: Optional[str] = None,
    max_tokens: int = 4000,
    relevance_threshold: float = 0.3
) -> MemoryContext
```

Recall relevant context from memory.

**Args:**
- `query`: Search query
- `phase`: Optional phase filter
- `task_id`: Optional task filter
- `max_tokens`: Maximum tokens to return
- `relevance_threshold`: Minimum relevance score (0-1)

**Returns:** `MemoryContext` with ranked entries

**Example:**
```python
# Basic recall
context = memory_recall("configuration setup")

# With filters
context = memory_recall(
    query="database schema",
    phase="1-discovery",
    max_tokens=2000,
    relevance_threshold=0.5
)

# Process results
for entry in context.entries:
    print(f"Relevance: {entry.relevance_score:.2f}")
    print(f"Content: {entry.content}")
```

#### Phase-Specific Recall

```python
memory_recall_phase(phase_num: int, max_tokens: int = 4000) -> MemoryContext
```

Recall all memory from a specific phase.

**Example:**
```python
phase0_context = memory_recall_phase(0)
for entry in phase0_context.entries:
    print(f"[{entry.task_id}] {entry.content}")
```

#### Recent Recall

```python
memory_recall_recent(count: int = 10) -> MemoryContext
```

Recall N most recent entries.

**Example:**
```python
context = memory_recall_recent(count=5)
```

#### Checkpoints

```python
memory_checkpoint(
    phase: int,
    phase_name: str,
    summary: str,
    key_decisions: Optional[List[str]] = None,
    artifacts: Optional[List[str]] = None,
    state_snapshot: Optional[Dict[str, Any]] = None
) -> str
```

Create a checkpoint.

**Returns:** Checkpoint ID

**Example:**
```python
checkpoint_id = memory_checkpoint(
    phase=0,
    phase_name="Setup",
    summary="Phase 0 completed. All systems configured.",
    key_decisions=[
        "Selected Python 3.11 as runtime",
        "Chose PostgreSQL for persistence"
    ],
    artifacts=[
        ".outputs/0-setup/project-config.json",
        ".outputs/0-setup/secrets.json"
    ],
    state_snapshot={
        "tasks_completed": 10,
        "tasks_failed": 0
    }
)
```

#### Checkpoint Restoration

```python
memory_restore(checkpoint_id: str) -> Optional[Checkpoint]
```

Restore from checkpoint.

**Example:**
```python
checkpoint = memory_restore("phase0-20250206-143022")
if checkpoint:
    print(f"Phase: {checkpoint.phase}")
    print(f"Summary: {checkpoint.summary}")
    print(f"Decisions: {checkpoint.key_decisions}")
```

#### Listing Checkpoints

```python
memory_list_checkpoints(
    phase: Optional[int] = None,
    status: Optional[CheckpointStatus] = None
) -> List[Checkpoint]
```

List checkpoints with optional filters.

**Example:**
```python
# All checkpoints
all_checkpoints = memory_list_checkpoints()

# Phase 0 only
phase0_checkpoints = memory_list_checkpoints(phase=0)

# Valid only
valid_checkpoints = memory_list_checkpoints(
    status=CheckpointStatus.VALID
)
```

#### Latest Checkpoint

```python
memory_get_latest_checkpoint(phase: Optional[int] = None) -> Optional[Checkpoint]
```

Get most recent checkpoint.

**Example:**
```python
latest = memory_get_latest_checkpoint()
if latest:
    print(f"Last checkpoint: Phase {latest.phase}")
```

#### Statistics

```python
memory_stats() -> MemoryStats
```

Get memory statistics.

**Example:**
```python
stats = memory_stats()
print(f"Total entries: {stats.total_entries}")
print(f"Size: {stats.size_mb:.2f} MB")
print(f"Entries by phase: {stats.entries_by_phase}")
print(f"Entries by type: {stats.entries_by_type}")
```

#### Compaction

```python
memory_compact(
    max_size_mb: float = 10.0,
    max_age_days: int = 90,
    min_relevance: float = 0.2
) -> dict
```

Compact memory to size limit.

**Returns:** Compaction statistics

**Example:**
```python
result = memory_compact(
    max_size_mb=5.0,
    max_age_days=60,
    min_relevance=0.3
)

print(f"Removed {result['total_removed']} entries")
print(f"Saved {result['size_reduction_mb']:.2f} MB")
```

#### Backtracking

```python
memory_handle_backtrack(target_phase: int) -> dict
```

Handle backtracking to earlier phase.

**Returns:** Backtrack statistics

**Example:**
```python
result = memory_handle_backtrack(target_phase=0)
print(f"Invalidated {result['invalidated_checkpoints']} checkpoints")
print(f"Cleared {result['cleared_entries']} entries")
```

### Relevance Scoring

Memory recall uses intelligent relevance scoring:

**Scoring Formula:**
```
total_score = 0.5 * keyword_match + 0.3 * recency + 0.2 * phase_relevance
```

**Keyword Match (50%):**
- Extracts keywords from query
- Matches against content and tags
- Ratio of matched keywords

**Recency (30%):**
- Exponential decay with 7-day half-life
- Recent entries score higher
- Formula: `e^(-age_days/7)`

**Phase Relevance (20%):**
- Current phase: 1.0
- Adjacent phase: 0.7
- Distant phase: 0.3

### Performance

**Target Performance:**
- Memory save: < 10ms
- Recall: < 50ms
- Checkpoint creation: < 100ms
- Compaction (10MB): < 1s

**Optimizations:**
- In-memory caching
- Atomic writes with temp files
- Indexed lookups
- Lazy loading

### Storage Format

Memory is stored in JSON format:

**memory.json:**
```json
{
  "entries": [
    {
      "id": "uuid",
      "timestamp": "2025-02-06T14:30:22",
      "entry_type": "task_end",
      "phase": "0-setup",
      "task_id": "001",
      "content": "Configuration completed",
      "tags": ["config"],
      "relevance_score": 0.8
    }
  ],
  "updated_at": "2025-02-06T14:30:22"
}
```

**Checkpoint format:**
```json
{
  "checkpoint_id": "phase0-20250206-143022",
  "project": "atomic-claude",
  "phase": 0,
  "phase_name": "Setup",
  "summary": "Phase completed",
  "key_decisions": [...],
  "artifacts": [...],
  "state_snapshot": {...},
  "context": [...],
  "status": "valid",
  "created_at": "2025-02-06T14:30:22"
}
```

### Best Practices

**1. Tag Everything**
```python
# Good
memory_save(
    phase="0-setup",
    task_id="001",
    content="Config completed",
    tags=["config", "setup", "success"]
)

# Poor
memory_save(
    phase="0-setup",
    task_id="001",
    content="Config completed",
    tags=[]
)
```

**2. Use Specific Queries**
```python
# Good
context = memory_recall("database schema configuration")

# Poor
context = memory_recall("stuff")
```

**3. Create Checkpoints at Phase Boundaries**
```python
# Good - comprehensive checkpoint
memory_checkpoint(
    phase=0,
    phase_name="Setup",
    summary="All setup tasks completed successfully",
    key_decisions=decisions,
    artifacts=artifacts
)
```

**4. Set Appropriate Token Limits**
```python
# For summarization
context = memory_recall("summary", max_tokens=1000)

# For detailed analysis
context = memory_recall("details", max_tokens=8000)
```

**5. Regular Compaction**
```python
# After each phase
if phase_complete:
    memory_compact(max_age_days=90, min_relevance=0.3)
```

### Integration with Orchestrators

```python
def task_001_setup() -> bool:
    """Execute task 001."""
    # Task logic here
    success = run_task()

    if success:
        # Save to memory
        memory_save(
            phase="0-setup",
            task_id="001",
            content="Setup validation completed successfully",
            tags=["validation", "setup"]
        )

    return success


def run_phase(phase_id: str) -> bool:
    """Execute phase tasks."""
    # Recall context from previous phases
    context = memory_recall_phase(phase_num - 1)

    # Execute tasks...

    # Create checkpoint
    memory_checkpoint(
        phase=phase_num,
        phase_name=phase_name,
        summary=generate_summary(),
        key_decisions=extract_decisions()
    )

    return True
```

### Troubleshooting

**Memory Not Persisting:**
```python
# Check initialization
memory_init()

# Verify state directory exists
stats = memory_stats()
print(f"Entries: {stats.total_entries}")
```

**Poor Recall Results:**
```python
# Lower relevance threshold
context = memory_recall("query", relevance_threshold=0.2)

# Increase token limit
context = memory_recall("query", max_tokens=8000)

# Use specific phase filter
context = memory_recall("query", phase="0-setup")
```

**Memory Growing Too Large:**
```python
# Check stats
stats = memory_stats()
print(f"Size: {stats.size_mb} MB")

# Compact aggressively
memory_compact(
    max_size_mb=5.0,
    max_age_days=30,
    min_relevance=0.5
)
```

### Testing

See comprehensive test suite:
- `tests/unit/test_memory_store.py` (15 tests)
- `tests/unit/test_checkpoint.py` (12 tests)
- `tests/unit/test_recall.py` (15 tests)
- `tests/unit/test_compaction.py` (8 tests)
- `tests/integration/test_memory_integration.py` (15 tests)

**Total: 65 tests**

Run tests:
```bash
pytest tests/unit/test_memory_*.py -v
pytest tests/integration/test_memory_integration.py -v
```
