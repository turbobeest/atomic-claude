"""
Memory Store - Persistent storage layer

JSON-based storage with atomic writes, indexing, and compression.
"""

import json
import logging
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

from .types import (
    MemoryEntry,
    MemoryEntryType,
    MemoryStats,
    MemoryHead
)


class MemoryStore:
    """Persistent storage for memory entries."""

    def __init__(self, state_dir: Path, graph=None):
        """
        Initialize memory store.

        Args:
            state_dir: Directory for state files (.state/)
            graph: Optional GraphManager for dual-write to FalkorDB
        """
        self.state_dir = Path(state_dir)
        self.memory_dir = self.state_dir / "memory"
        self.memory_file = self.state_dir / "memory.json"
        self.head_file = self.state_dir / "memory-head.json"
        self.index_file = self.state_dir / "memory-index.json"
        self._graph = graph

        # In-memory cache
        self._entries: List[MemoryEntry] = []
        self._index: Dict[str, int] = {}  # entry_id -> list index
        self._loaded = False

    def initialize(self) -> None:
        """Create memory store structure."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(exist_ok=True)

        # Initialize empty memory file if needed
        if not self.memory_file.exists():
            self._write_atomic(self.memory_file, {"entries": []})

        # Initialize head file if needed
        if not self.head_file.exists():
            head = MemoryHead(
                project="atomic-claude",
                head_phase=-1,
                head_checkpoint=None
            )
            self._write_atomic(self.head_file, head.dict())

        # Initialize index
        if not self.index_file.exists():
            self._write_atomic(self.index_file, {})

        self._load()

    def _write_atomic(self, path: Path, data: Dict[str, Any]) -> None:
        """
        Write JSON atomically using temp file.

        Args:
            path: Target file path
            data: Data to write
        """
        # Write to temp file in same directory
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=path.parent,
            prefix=f'.{path.name}.',
            suffix='.tmp',
            delete=False,
            encoding='utf-8'
        ) as tmp:
            json.dump(data, tmp, indent=2, default=str)
            tmp_path = tmp.name

        # Atomic move
        shutil.move(tmp_path, path)

    def _load(self) -> None:
        """Load memory entries from disk."""
        if not self.memory_file.exists():
            return

        with open(self.memory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._entries = [
            MemoryEntry(**entry) for entry in data.get("entries", [])
        ]

        # Rebuild index
        self._index = {
            entry.id: idx for idx, entry in enumerate(self._entries)
        }

        self._loaded = True

    def _save(self) -> None:
        """Save memory entries to disk."""
        data = {
            "entries": [entry.dict() for entry in self._entries],
            "updated_at": datetime.now().isoformat()
        }
        self._write_atomic(self.memory_file, data)

        # Save index
        self._write_atomic(self.index_file, self._index)

    def append(self, entry: MemoryEntry) -> None:
        """
        Add memory entry.

        Args:
            entry: Memory entry to add
        """
        if not self._loaded:
            self._load()

        # Add to list
        self._entries.append(entry)

        # Update index
        self._index[entry.id] = len(self._entries) - 1

        # Save immediately (append-only log)
        self._save()

        # Write phase-based markdown file for dashboard consumption
        self._write_phase_file(entry)

        # Dual-write to graph if available
        if self._graph:
            try:
                self._graph.save_memory(
                    entry_id=entry.id,
                    phase=entry.phase,
                    content=entry.content,
                    entry_type=entry.entry_type.value if hasattr(entry.entry_type, 'value') else str(entry.entry_type),
                    task_id=entry.task_id,
                    tags=entry.tags,
                    relevance_score=entry.relevance_score,
                )
            except Exception as e:
                logger.warning(f"Graph memory write failed (non-blocking): {e}")

    def _write_phase_file(self, entry: MemoryEntry) -> None:
        """
        Write a markdown file for the entry into the phase-based directory
        structure that the dashboard reads.

        Files are written to .state/memory/phase-{N}/ and appended to
        so that multiple memory entries for the same task accumulate.

        Args:
            entry: Memory entry to write
        """
        try:
            # Extract phase number from entry.phase (e.g., "0-setup" -> "0")
            phase_num = entry.phase.split('-')[0]

            # Create phase directory if needed
            phase_dir = self.memory_dir / f"phase-{phase_num}"
            phase_dir.mkdir(parents=True, exist_ok=True)

            # Determine filename based on task_id presence
            if entry.task_id:
                filename = f"task_{entry.task_id}.md"
            else:
                filename = f"phase_{phase_num}.md"

            file_path = phase_dir / filename

            # Format the markdown content
            timestamp_str = entry.timestamp.isoformat() if hasattr(entry.timestamp, 'isoformat') else str(entry.timestamp)
            entry_type_str = entry.entry_type.value if hasattr(entry.entry_type, 'value') else str(entry.entry_type)

            lines = []
            lines.append(f"## {entry_type_str} - {timestamp_str}")
            lines.append("")
            lines.append(entry.content)
            lines.append("")
            if entry.tags:
                lines.append(f"Tags: {', '.join(entry.tags)}")
                lines.append("")
            lines.append("---")
            lines.append("")

            md_content = "\n".join(lines)

            # Append to existing file (or create new)
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(md_content)

        except Exception:
            # Never block the main memory operation
            pass

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve entry by ID.

        Args:
            entry_id: Entry ID

        Returns:
            Memory entry or None if not found
        """
        if not self._loaded:
            self._load()

        idx = self._index.get(entry_id)
        if idx is not None and 0 <= idx < len(self._entries):
            return self._entries[idx]
        return None

    def query(
        self,
        tags: Optional[List[str]] = None,
        phase: Optional[str] = None,
        task_id: Optional[str] = None,
        entry_type: Optional[MemoryEntryType] = None,
        limit: Optional[int] = None,
        min_relevance: float = 0.0
    ) -> List[MemoryEntry]:
        """
        Query entries with filters.

        Args:
            tags: Filter by tags (any match)
            phase: Filter by phase
            task_id: Filter by task ID
            entry_type: Filter by entry type
            limit: Maximum results
            min_relevance: Minimum relevance score

        Returns:
            List of matching entries
        """
        if not self._loaded:
            self._load()

        results = []

        for entry in self._entries:
            # Apply filters
            if phase and entry.phase != phase:
                continue

            if task_id and entry.task_id != task_id:
                continue

            if entry_type and entry.entry_type != entry_type:
                continue

            if tags and not any(tag in entry.tags for tag in tags):
                continue

            if entry.relevance_score < min_relevance:
                continue

            results.append(entry)

        # Sort by timestamp (newest first)
        results.sort(key=lambda e: e.timestamp, reverse=True)

        # Limit results
        if limit:
            results = results[:limit]

        return results

    def compact(self, max_age_days: int = 90, min_relevance: float = 0.2) -> int:
        """
        Remove old or low-value entries.

        Args:
            max_age_days: Remove entries older than this
            min_relevance: Remove entries with relevance below this

        Returns:
            Number of entries removed
        """
        if not self._loaded:
            self._load()

        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        initial_count = len(self._entries)

        # Keep entries that are:
        # 1. Recent enough OR
        # 2. Important enough (high relevance) OR
        # 3. Checkpoints (always keep)
        kept_entries = [
            entry for entry in self._entries
            if (
                entry.timestamp >= cutoff_date or
                entry.relevance_score >= min_relevance or
                entry.entry_type == MemoryEntryType.CHECKPOINT or
                entry.entry_type == MemoryEntryType.PHASE_CLOSEOUT
            )
        ]

        removed_count = initial_count - len(kept_entries)

        if removed_count > 0:
            self._entries = kept_entries

            # Rebuild index
            self._index = {
                entry.id: idx for idx, entry in enumerate(self._entries)
            }

            self._save()

        return removed_count

    def get_stats(self) -> MemoryStats:
        """
        Get memory statistics.

        Returns:
            Memory statistics
        """
        if not self._loaded:
            self._load()

        # Count by phase
        entries_by_phase = defaultdict(int)
        for entry in self._entries:
            entries_by_phase[entry.phase] += 1

        # Count by type
        entries_by_type = defaultdict(int)
        for entry in self._entries:
            entries_by_type[entry.entry_type.value] += 1

        # Calculate size
        size_bytes = 0
        if self.memory_file.exists():
            size_bytes = self.memory_file.stat().st_size

        # Find date range
        oldest = min((e.timestamp for e in self._entries), default=None)
        newest = max((e.timestamp for e in self._entries), default=None)

        return MemoryStats(
            total_entries=len(self._entries),
            size_bytes=size_bytes,
            size_mb=round(size_bytes / (1024 * 1024), 2),
            oldest_entry=oldest,
            newest_entry=newest,
            entries_by_phase=dict(entries_by_phase),
            entries_by_type=dict(entries_by_type)
        )

    def export(self, path: Path) -> None:
        """
        Export memory to file.

        Args:
            path: Export file path
        """
        if not self._loaded:
            self._load()

        data = {
            "exported_at": datetime.now().isoformat(),
            "entries": [entry.dict() for entry in self._entries]
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

    def import_data(self, path: Path) -> int:
        """
        Import memory from file.

        Args:
            path: Import file path

        Returns:
            Number of entries imported
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        entries = [MemoryEntry(**entry) for entry in data.get("entries", [])]

        if not self._loaded:
            self._load()

        # Add entries (skip duplicates)
        existing_ids = set(self._index.keys())
        imported = 0

        for entry in entries:
            if entry.id not in existing_ids:
                self.append(entry)
                imported += 1

        return imported

    def clear_phase(self, phase_num: int) -> int:
        """
        Clear all entries for a phase and later phases.

        Args:
            phase_num: Phase number

        Returns:
            Number of entries removed
        """
        if not self._loaded:
            self._load()

        initial_count = len(self._entries)

        # Keep entries before target phase
        self._entries = [
            entry for entry in self._entries
            if int(entry.phase.split('-')[0]) < phase_num
        ]

        removed_count = initial_count - len(self._entries)

        if removed_count > 0:
            # Rebuild index
            self._index = {
                entry.id: idx for idx, entry in enumerate(self._entries)
            }
            self._save()

        # Also clear graph memory nodes
        if self._graph:
            try:
                self._graph.clear_memory_after_phase(phase_num - 1)
            except Exception:
                pass  # Non-blocking

        return removed_count
