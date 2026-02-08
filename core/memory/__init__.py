"""
Memory System

Persistent context storage and recall across phases and sessions.

Pure Python implementation replacing the bash memory.sh (47KB, 1,500 lines).
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import uuid

from .types import (
    MemoryEntry,
    MemoryEntryType,
    MemoryContext,
    MemoryStats,
    Checkpoint,
    CheckpointStatus
)
from .store import MemoryStore
from .checkpoint import CheckpointManager
from .recall import MemoryRecall
from .compaction import MemoryCompactor


# Global instances
_store: Optional[MemoryStore] = None
_checkpoint_manager: Optional[CheckpointManager] = None
_recall_engine: Optional[MemoryRecall] = None
_compactor: Optional[MemoryCompactor] = None
_initialized = False


def memory_init(state_dir: Optional[Path] = None) -> None:
    """
    Initialize memory system.

    Args:
        state_dir: State directory (defaults to .state/)
    """
    global _store, _checkpoint_manager, _recall_engine, _compactor, _initialized

    if _initialized:
        return

    if state_dir is None:
        state_dir = Path.cwd() / ".state"

    # Initialize store
    _store = MemoryStore(state_dir)
    _store.initialize()

    # Initialize checkpoint manager
    _checkpoint_manager = CheckpointManager(state_dir, _store)

    # Initialize recall engine
    _recall_engine = MemoryRecall(_store)

    # Initialize compactor
    _compactor = MemoryCompactor(_store)

    _initialized = True


def _ensure_initialized():
    """Ensure memory system is initialized."""
    if not _initialized:
        memory_init()


def memory_save(
    phase: str,
    task_id: Optional[str],
    content: str,
    tags: Optional[List[str]] = None,
    entry_type: MemoryEntryType = MemoryEntryType.TASK_END,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Save to memory.

    Args:
        phase: Phase ID (e.g., "0-setup")
        task_id: Task ID (optional)
        content: Content to save
        tags: Tags for searching
        entry_type: Type of entry
        metadata: Additional metadata

    Returns:
        Entry ID
    """
    _ensure_initialized()

    # Generate unique ID
    entry_id = str(uuid.uuid4())

    # Create entry
    entry = MemoryEntry(
        id=entry_id,
        timestamp=datetime.now(),
        entry_type=entry_type,
        phase=phase,
        task_id=task_id,
        content=content,
        tags=tags or [],
        metadata=metadata or {},
        relevance_score=0.8  # Default relevance
    )

    # Save to store
    _store.append(entry)

    return entry_id


def memory_recall(
    query: str,
    phase: Optional[str] = None,
    task_id: Optional[str] = None,
    max_tokens: int = 4000,
    relevance_threshold: float = 0.3
) -> MemoryContext:
    """
    Recall context from memory.

    Args:
        query: Search query
        phase: Optional phase filter
        task_id: Optional task filter
        max_tokens: Maximum tokens to return
        relevance_threshold: Minimum relevance score

    Returns:
        Memory context with relevant entries
    """
    _ensure_initialized()

    return _recall_engine.recall(
        query=query,
        phase=phase,
        task_id=task_id,
        max_tokens=max_tokens,
        relevance_threshold=relevance_threshold
    )


def memory_recall_phase(phase_num: int, max_tokens: int = 4000) -> MemoryContext:
    """
    Recall all memory from a specific phase.

    Args:
        phase_num: Phase number (0-9)
        max_tokens: Maximum tokens

    Returns:
        Memory context
    """
    _ensure_initialized()
    return _recall_engine.recall_phase(phase_num, max_tokens)


def memory_recall_recent(count: int = 10) -> MemoryContext:
    """
    Recall N most recent entries.

    Args:
        count: Number of entries

    Returns:
        Memory context
    """
    _ensure_initialized()
    return _recall_engine.recall_recent(count)


def memory_checkpoint(
    phase: int,
    phase_name: str,
    summary: str,
    key_decisions: Optional[List[str]] = None,
    artifacts: Optional[List[str]] = None,
    state_snapshot: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a checkpoint.

    Args:
        phase: Phase number
        phase_name: Phase name
        summary: Checkpoint summary
        key_decisions: Key decisions
        artifacts: Artifact paths
        state_snapshot: State data

    Returns:
        Checkpoint ID
    """
    _ensure_initialized()

    return _checkpoint_manager.create_checkpoint(
        phase=phase,
        phase_name=phase_name,
        summary=summary,
        key_decisions=key_decisions,
        artifacts=artifacts,
        state_snapshot=state_snapshot
    )


def memory_restore(checkpoint_id: str) -> Optional[Checkpoint]:
    """
    Restore from checkpoint.

    Args:
        checkpoint_id: Checkpoint ID

    Returns:
        Checkpoint data or None
    """
    _ensure_initialized()
    return _checkpoint_manager.restore_checkpoint(checkpoint_id)


def memory_list_checkpoints(
    phase: Optional[int] = None,
    status: Optional[CheckpointStatus] = None
) -> List[Checkpoint]:
    """
    List checkpoints.

    Args:
        phase: Filter by phase
        status: Filter by status

    Returns:
        List of checkpoints
    """
    _ensure_initialized()
    return _checkpoint_manager.list_checkpoints(phase, status)


def memory_get_latest_checkpoint(phase: Optional[int] = None) -> Optional[Checkpoint]:
    """
    Get most recent checkpoint.

    Args:
        phase: Filter by phase

    Returns:
        Latest checkpoint or None
    """
    _ensure_initialized()
    return _checkpoint_manager.get_latest_checkpoint(phase)


def memory_stats() -> MemoryStats:
    """
    Get memory statistics.

    Returns:
        Memory statistics
    """
    _ensure_initialized()
    return _store.get_stats()


def memory_compact(
    max_size_mb: float = 10.0,
    max_age_days: int = 90,
    min_relevance: float = 0.2
) -> dict:
    """
    Compact memory to size limit.

    Args:
        max_size_mb: Maximum size in MB
        max_age_days: Maximum age in days
        min_relevance: Minimum relevance score

    Returns:
        Compaction statistics
    """
    _ensure_initialized()

    return _compactor.compact(
        max_size_mb=max_size_mb,
        max_age_days=max_age_days,
        min_relevance=min_relevance
    )


def memory_handle_backtrack(target_phase: int) -> dict:
    """
    Handle backtracking to earlier phase.

    Args:
        target_phase: Phase to backtrack to

    Returns:
        Backtrack statistics
    """
    _ensure_initialized()

    # Invalidate checkpoints after target phase
    invalidated_checkpoints = _checkpoint_manager.invalidate_after_phase(target_phase)

    # Clear memory entries after target phase
    cleared_entries = _store.clear_phase(target_phase + 1)

    return {
        "target_phase": target_phase,
        "invalidated_checkpoints": invalidated_checkpoints,
        "cleared_entries": cleared_entries
    }


# Export all types and functions
__all__ = [
    # Types
    "MemoryEntry",
    "MemoryEntryType",
    "MemoryContext",
    "MemoryStats",
    "Checkpoint",
    "CheckpointStatus",
    # Core functions
    "memory_init",
    "memory_save",
    "memory_recall",
    "memory_recall_phase",
    "memory_recall_recent",
    "memory_checkpoint",
    "memory_restore",
    "memory_list_checkpoints",
    "memory_get_latest_checkpoint",
    "memory_stats",
    "memory_compact",
    "memory_handle_backtrack",
    # Advanced access
    "MemoryStore",
    "CheckpointManager",
    "MemoryRecall",
    "MemoryCompactor"
]
