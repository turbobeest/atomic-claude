"""
Memory Recall - Context retrieval with relevance scoring

Intelligent context search with semantic matching and recency weighting.
"""

import logging
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

from .content_signals import detect_signals
from .types import MemoryEntry, MemoryContext, MemoryEntryType
from .store import MemoryStore


class MemoryRecall:
    """Intelligent context recall from memory."""

    def __init__(self, store: MemoryStore, graph=None):
        """
        Initialize recall engine.

        Args:
            store: Memory store instance
            graph: Optional GraphManager for fulltext search
        """
        self.store = store
        self._graph = graph

    def recall(
        self,
        query: str,
        phase: Optional[str] = None,
        task_id: Optional[str] = None,
        max_tokens: int = 4000,
        relevance_threshold: float = 0.3
    ) -> MemoryContext:
        """
        Recall relevant context.

        Uses graph fulltext search when available (better relevance),
        falls back to file-based keyword matching.

        Args:
            query: Search query
            phase: Optional phase filter
            task_id: Optional task filter
            max_tokens: Maximum tokens to return
            relevance_threshold: Minimum relevance score

        Returns:
            Memory context with ranked entries
        """
        # Try graph-based recall first (fulltext search is superior)
        if self._graph:
            try:
                graph_results = self._graph.recall_memory(
                    query=query, phase=phase, task_id=task_id, limit=30,
                )
                if graph_results:
                    entries = [self._graph_result_to_entry(r) for r in graph_results]
                    selected = self._select_within_token_limit(entries, max_tokens)
                    total_tokens = sum(self._estimate_tokens(e.content) for e in selected)
                    return MemoryContext(
                        query=query,
                        entries=selected,
                        total_tokens=total_tokens,
                        max_tokens=max_tokens,
                        relevance_threshold=relevance_threshold,
                    )
            except Exception as e:
                logger.debug("Graph fulltext recall failed, falling back to file-based: %s", e)

        # File-based recall (fallback)
        entries = self.store.query(phase=phase, task_id=task_id)

        # Score each entry
        scored_entries = []
        for entry in entries:
            score = self._score_entry(entry, query, phase)

            if score >= relevance_threshold:
                # Update relevance score
                entry.relevance_score = score
                scored_entries.append(entry)

        # Sort by relevance (descending)
        scored_entries.sort(key=lambda e: e.relevance_score, reverse=True)

        # Select entries within token limit
        selected_entries = self._select_within_token_limit(
            scored_entries,
            max_tokens
        )

        # Calculate total tokens
        total_tokens = sum(self._estimate_tokens(e.content) for e in selected_entries)

        return MemoryContext(
            query=query,
            entries=selected_entries,
            total_tokens=total_tokens,
            max_tokens=max_tokens,
            relevance_threshold=relevance_threshold
        )

    def recall_phase(self, phase_num: int, max_tokens: int = 4000) -> MemoryContext:
        """
        Get all memory from a specific phase.

        Args:
            phase_num: Phase number
            max_tokens: Maximum tokens

        Returns:
            Memory context
        """
        # Find matching phase IDs (e.g., "0-setup", "1-discovery")
        entries = self.store.query()
        phase_entries = [
            e for e in entries
            if e.phase.startswith(f"{phase_num}-")
        ]

        # Sort by timestamp
        phase_entries.sort(key=lambda e: e.timestamp)

        # Select within token limit
        selected = self._select_within_token_limit(phase_entries, max_tokens)

        total_tokens = sum(self._estimate_tokens(e.content) for e in selected)

        return MemoryContext(
            query=f"Phase {phase_num}",
            entries=selected,
            total_tokens=total_tokens,
            max_tokens=max_tokens
        )

    def recall_recent(self, count: int = 10) -> MemoryContext:
        """
        Get N most recent entries.

        Args:
            count: Number of entries

        Returns:
            Memory context
        """
        entries = self.store.query(limit=count)

        total_tokens = sum(self._estimate_tokens(e.content) for e in entries)

        return MemoryContext(
            query="Recent entries",
            entries=entries,
            total_tokens=total_tokens,
            max_tokens=100000  # No limit for recent
        )

    def _score_entry(
        self,
        entry: MemoryEntry,
        query: str,
        current_phase: Optional[str] = None
    ) -> float:
        """
        Score entry relevance.

        Scoring:
        - 50% keyword match
        - 30% recency
        - 20% phase relevance

        Args:
            entry: Memory entry
            query: Search query
            current_phase: Current phase

        Returns:
            Relevance score (0-1)
        """
        # Extract keywords from query
        keywords = self._extract_keywords(query)

        # Keyword match score
        keyword_score = self._keyword_match_score(entry, keywords)

        # Recency score (exponential decay)
        recency_score = self._recency_score(entry.timestamp)

        # Phase relevance score
        phase_score = self._phase_relevance_score(entry.phase, current_phase)

        # Content signal boost
        signal_boost = 0.1 * detect_signals(entry.content).score()

        # Weighted combination
        total_score = (
            0.5 * keyword_score +
            0.3 * recency_score +
            0.2 * phase_score +
            signal_boost
        )

        return min(1.0, max(0.0, total_score))

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text."""
        # Convert to lowercase
        text = text.lower()

        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)

        # Split into words
        words = text.split()

        # Remove short words and common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was',
            'be', 'been', 'has', 'have', 'had', 'do', 'does', 'did'
        }

        keywords = {
            word for word in words
            if len(word) >= 3 and word not in stop_words
        }

        return keywords

    def _keyword_match_score(self, entry: MemoryEntry, keywords: Set[str]) -> float:
        """Calculate keyword match score."""
        if not keywords:
            return 0.5  # Neutral score

        # Check content and tags
        content_lower = entry.content.lower()
        entry_keywords = self._extract_keywords(content_lower)

        # Add tags as keywords
        for tag in entry.tags:
            entry_keywords.update(self._extract_keywords(tag))

        # Calculate match ratio
        matches = keywords & entry_keywords
        if not keywords:
            return 0.5

        return len(matches) / len(keywords)

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        """Return a timezone-aware datetime; assumes UTC if naive."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _recency_score(self, timestamp: datetime) -> float:
        """
        Calculate recency score with exponential decay.

        Recent entries score higher.
        """
        now = datetime.now(timezone.utc)
        age = now - self._ensure_aware(timestamp)

        # Exponential decay: score = e^(-decay_rate * age_days)
        # halflife = 7 days, decay_rate = ln(2) / halflife
        halflife_days = 7.0
        decay_rate = math.log(2) / halflife_days
        age_days = age.total_seconds() / 86400.0

        score = math.exp(-decay_rate * age_days)

        return min(1.0, score)

    def _phase_relevance_score(
        self,
        entry_phase: str,
        current_phase: Optional[str]
    ) -> float:
        """
        Calculate phase relevance score.

        Current phase = 1.0
        Adjacent phase = 0.7
        Distant phase = 0.3
        """
        if not current_phase:
            return 0.5

        # Extract phase numbers
        try:
            entry_phase_num = int(entry_phase.split('-')[0])
            current_phase_num = int(current_phase.split('-')[0])
        except (ValueError, IndexError):
            return 0.5

        # Calculate distance
        distance = abs(entry_phase_num - current_phase_num)

        if distance == 0:
            return 1.0  # Same phase
        elif distance == 1:
            return 0.7  # Adjacent phase
        else:
            return 0.3  # Distant phase

    def _graph_result_to_entry(self, node_dict: dict) -> MemoryEntry:
        """Convert a graph Memory node dict to a MemoryEntry."""
        entry_type_str = node_dict.get("entry_type", "task_end")
        try:
            entry_type = MemoryEntryType(entry_type_str)
        except ValueError:
            entry_type = MemoryEntryType.TASK_END

        tags_csv = node_dict.get("tags_csv", "")
        tags = [t.strip() for t in tags_csv.split(",") if t.strip()] if tags_csv else []

        return MemoryEntry(
            id=node_dict.get("id", ""),
            timestamp=datetime.fromisoformat(node_dict["created_at"]) if node_dict.get("created_at") else datetime.now(timezone.utc),
            entry_type=entry_type,
            phase=node_dict.get("phase", ""),
            task_id=node_dict.get("task_id") or None,
            content=node_dict.get("content", ""),
            tags=tags,
            relevance_score=float(node_dict.get("relevance_score", 0.8)),
        )

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count.

        Rough approximation: 1 token ≈ 4 characters
        """
        return len(text) // 4

    def _select_within_token_limit(
        self,
        entries: List[MemoryEntry],
        max_tokens: int
    ) -> List[MemoryEntry]:
        """
        Select entries within token limit.

        Args:
            entries: List of entries (should be pre-sorted)
            max_tokens: Maximum tokens

        Returns:
            Selected entries
        """
        selected = []
        total_tokens = 0

        for entry in entries:
            entry_tokens = self._estimate_tokens(entry.content)

            if total_tokens + entry_tokens <= max_tokens:
                selected.append(entry)
                total_tokens += entry_tokens
            else:
                # Stop when we hit the limit
                break

        return selected
