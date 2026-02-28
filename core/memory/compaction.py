"""
Memory Compaction - Memory optimization

Identifies and removes redundant, low-value, or outdated entries.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Set, Tuple
from collections import defaultdict

from .content_signals import detect_signals
from .types import MemoryEntry, MemoryEntryType
from .store import MemoryStore


class MemoryCompactor:
    """Memory optimization and compaction."""

    def __init__(self, store: MemoryStore):
        """
        Initialize compactor.

        Args:
            store: Memory store instance
        """
        self.store = store

    def compact(
        self,
        max_size_mb: float = 10.0,
        max_age_days: int = 90,
        min_relevance: float = 0.2
    ) -> dict:
        """
        Compact memory to size limit.

        Args:
            max_size_mb: Maximum size in MB
            max_age_days: Remove entries older than this
            min_relevance: Remove entries with relevance below this

        Returns:
            Compaction statistics
        """
        stats = self.store.get_stats()
        initial_size = stats.size_mb
        initial_count = stats.total_entries

        # Phase 1: Remove old entries
        removed_old = self.store.compact(
            max_age_days=max_age_days,
            min_relevance=min_relevance
        )

        # Phase 2: Find and remove redundant entries
        redundant = self.find_redundant()
        removed_redundant = len(redundant)

        for entry_id in redundant:
            entry = self.store.get(entry_id)
            if entry:
                # Mark for removal by setting relevance to 0
                entry.relevance_score = 0.0

        # Phase 3: Compact again to remove marked entries
        self.store.compact(min_relevance=0.01)

        # Get final stats
        final_stats = self.store.get_stats()

        return {
            "initial_size_mb": initial_size,
            "final_size_mb": final_stats.size_mb,
            "size_reduction_mb": round(initial_size - final_stats.size_mb, 2),
            "initial_count": initial_count,
            "final_count": final_stats.total_entries,
            "removed_old": removed_old,
            "removed_redundant": removed_redundant,
            "total_removed": initial_count - final_stats.total_entries
        }

    # Cap on pairwise comparisons within a single group to avoid O(n**2) blow-up
    MAX_GROUP_COMPARISONS = 5000

    def find_redundant(self, similarity_threshold: float = 0.85) -> Set[str]:
        """
        Find redundant (duplicate/similar) entries.

        Args:
            similarity_threshold: Similarity threshold (0-1)

        Returns:
            Set of redundant entry IDs
        """
        entries = self.store.query()
        redundant = set()

        # Group entries by phase and type
        groups = defaultdict(list)
        for entry in entries:
            key = (entry.phase, entry.entry_type)
            groups[key].append(entry)

        # Check for duplicates within each group
        for group in groups.values():
            if len(group) < 2:
                continue

            # Compare each pair (capped to avoid runaway cost)
            comparisons = 0
            for i, entry1 in enumerate(group):
                for entry2 in group[i + 1:]:
                    comparisons += 1
                    if comparisons > self.MAX_GROUP_COMPARISONS:
                        break

                    similarity = self._calculate_similarity(entry1, entry2)

                    if similarity >= similarity_threshold:
                        # Keep the newer entry, mark older as redundant
                        if entry1.timestamp < entry2.timestamp:
                            redundant.add(entry1.id)
                        else:
                            redundant.add(entry2.id)
                if comparisons > self.MAX_GROUP_COMPARISONS:
                    break

        return redundant

    def merge_entries(self, entry_ids: List[str]) -> str:
        """
        Merge multiple entries into one.

        Args:
            entry_ids: Entry IDs to merge

        Returns:
            ID of merged entry
        """
        entries = [self.store.get(eid) for eid in entry_ids if self.store.get(eid)]

        if not entries:
            raise ValueError("No entries found to merge")

        # Sort by timestamp
        entries.sort(key=lambda e: e.timestamp)

        # Use most recent entry as base — create a NEW object to avoid mutating
        # the existing entry still referenced in the store
        base = entries[-1]

        # Combine tags from all entries
        all_tags = set()
        for entry in entries:
            all_tags.update(entry.tags)

        # Build merged metadata
        merged_metadata = dict(base.metadata)
        merged_metadata["merged_from"] = [e.id for e in entries[:-1]]
        merged_metadata["merged_at"] = datetime.now(timezone.utc).isoformat()

        # Create a fresh MemoryEntry instead of modifying the original in place
        merged = MemoryEntry(
            id=base.id,
            timestamp=base.timestamp,
            entry_type=base.entry_type,
            phase=base.phase,
            task_id=base.task_id,
            content="\n\n---\n\n".join(e.content for e in entries),
            tags=list(all_tags),
            metadata=merged_metadata,
            relevance_score=base.relevance_score,
        )

        # Save merged entry
        self.store.append(merged)

        # Remove old entries (mark with 0 relevance)
        for entry in entries[:-1]:
            entry.relevance_score = 0.0

        return merged.id

    def prioritize(self) -> List[Tuple[str, float]]:
        """
        Score entry importance.

        Returns:
            List of (entry_id, importance_score) tuples
        """
        entries = self.store.query()
        scored = []

        for entry in entries:
            score = self._calculate_importance(entry)
            scored.append((entry.id, score))

        # Sort by importance (descending)
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored

    def remove_low_value(self, threshold: float = 0.3) -> int:
        """
        Remove low-value entries.

        Args:
            threshold: Importance threshold

        Returns:
            Number of entries removed
        """
        priorities = self.prioritize()

        removed = 0
        for entry_id, importance in priorities:
            if importance < threshold:
                entry = self.store.get(entry_id)
                if entry:
                    # Skip critical entry types
                    if entry.entry_type in [
                        MemoryEntryType.CHECKPOINT,
                        MemoryEntryType.PHASE_CLOSEOUT
                    ]:
                        continue

                    # Mark for removal
                    entry.relevance_score = 0.0
                    removed += 1

        # Compact to remove marked entries
        self.store.compact(min_relevance=0.01)

        return removed

    def _calculate_similarity(self, entry1: MemoryEntry, entry2: MemoryEntry) -> float:
        """
        Calculate similarity between two entries.

        Uses Jaccard similarity on word sets.
        """
        # Extract words
        words1 = set(entry1.content.lower().split())
        words2 = set(entry2.content.lower().split())

        # Jaccard similarity
        if not words1 and not words2:
            return 1.0

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _calculate_importance(self, entry: MemoryEntry) -> float:
        """
        Calculate entry importance.

        Factors:
        - Entry type (checkpoints, closeouts are critical)
        - Recency (newer is more important)
        - Content length (longer entries are often more valuable)
        - Relevance score
        """
        # Base score from entry type
        type_scores = {
            MemoryEntryType.CHECKPOINT: 1.0,
            MemoryEntryType.PHASE_CLOSEOUT: 1.0,
            MemoryEntryType.TASK_END: 0.7,
            MemoryEntryType.TASK_START: 0.3,
            MemoryEntryType.USER_NOTE: 0.8,
            MemoryEntryType.SYSTEM_EVENT: 0.4
        }

        type_score = type_scores.get(entry.entry_type, 0.5)

        # Recency score (entries from last 30 days score higher)
        age_days = (datetime.now(timezone.utc) - entry.timestamp).days
        if age_days < 30:
            recency_score = 1.0
        elif age_days < 90:
            recency_score = 0.5
        else:
            recency_score = 0.2

        # Content length score (normalized)
        content_length = len(entry.content)
        if content_length > 1000:
            length_score = 1.0
        elif content_length > 500:
            length_score = 0.7
        elif content_length > 100:
            length_score = 0.5
        else:
            length_score = 0.3

        # Content signal score (semantic importance markers)
        raw_signal = detect_signals(entry.content).score()
        content_signal_score = max(0.0, min(1.0, (raw_signal + 0.10) / 0.50))

        # Critical entry types get a signal floor to prevent content drag-down
        if entry.entry_type in (MemoryEntryType.CHECKPOINT, MemoryEntryType.PHASE_CLOSEOUT):
            content_signal_score = max(content_signal_score, 0.6)

        # Combine scores (rebalanced with content signal weight)
        importance = (
            0.30 * type_score +
            0.25 * recency_score +
            0.15 * length_score +
            0.10 * entry.relevance_score +
            0.20 * content_signal_score
        )

        return min(1.0, importance)
