"""
Memory System Data Types

Pydantic models for memory system data structures.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class MemoryEntryType(str, Enum):
    """Type of memory entry."""
    TASK_START = "task_start"
    TASK_END = "task_end"
    TASK_PROGRESS = "task_progress"
    PHASE_CLOSEOUT = "phase_closeout"
    CHECKPOINT = "checkpoint"
    USER_NOTE = "user_note"
    SYSTEM_EVENT = "system_event"


class MemoryEntry(BaseModel):
    """Single memory entry with content and metadata."""

    id: str = Field(description="Unique entry ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entry_type: MemoryEntryType
    phase: str = Field(description="Phase ID (e.g., '0-setup')")
    task_id: Optional[str] = Field(None, description="Task ID if task-related")
    content: str = Field(description="Memory content")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    relevance_score: float = Field(0.0, ge=0.0, le=1.0)

    @field_serializer('timestamp')
    def serialize_timestamp(self, v: datetime) -> str:
        return v.isoformat()


class CheckpointStatus(str, Enum):
    """Checkpoint status."""
    VALID = "valid"
    INVALIDATED = "invalidated"
    SUPERSEDED = "superseded"


class Checkpoint(BaseModel):
    """Phase/task checkpoint for recovery."""

    checkpoint_id: str
    project: str
    phase: int = Field(ge=0, le=9)
    phase_name: str
    summary: str
    key_decisions: List[str] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list)
    state_snapshot: Dict[str, Any] = Field(default_factory=dict)
    context: List[MemoryEntry] = Field(default_factory=list)
    status: CheckpointStatus = CheckpointStatus.VALID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    previous_checkpoint: Optional[str] = None

    @field_serializer('created_at')
    def serialize_created_at(self, v: datetime) -> str:
        return v.isoformat()


class MemoryContext(BaseModel):
    """Retrieved context for a query."""

    query: str
    entries: List[MemoryEntry] = Field(default_factory=list)
    total_tokens: int = 0
    max_tokens: int = 4000
    relevance_threshold: float = 0.3

    @field_validator("entries")
    @classmethod
    def sort_by_relevance(cls, v):
        """Sort entries by relevance score (descending)."""
        return sorted(v, key=lambda e: e.relevance_score, reverse=True)


class MemoryStats(BaseModel):
    """Memory system statistics."""

    total_entries: int = 0
    total_checkpoints: int = 0
    size_bytes: int = 0
    size_mb: float = 0.0
    oldest_entry: Optional[datetime] = None
    newest_entry: Optional[datetime] = None
    entries_by_phase: Dict[str, int] = Field(default_factory=dict)
    entries_by_type: Dict[str, int] = Field(default_factory=dict)

    @field_serializer('oldest_entry', 'newest_entry')
    def serialize_optional_datetime(self, v: Optional[datetime]) -> Optional[str]:
        return v.isoformat() if v else None


class MemoryHead(BaseModel):
    """Memory system head tracking."""

    project: str
    head_phase: int = -1
    head_checkpoint: Optional[str] = None
    checkpoints: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, v: datetime) -> str:
        return v.isoformat()
