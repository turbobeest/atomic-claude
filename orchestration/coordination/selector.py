"""Pattern Selector — scores coordination patterns against task context.

Applies heuristics based on gravity, roster size, task category, phase,
and feature flags to recommend the best coordination pattern. SEQUENTIAL
always has a floor score of 1.0, so it wins if no other pattern qualifies.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from orchestration.coordination.patterns import (
    CoordinationPattern,
    PatternSpec,
    PATTERN_CATALOG,
)

logger = logging.getLogger(__name__)

# Phase-specific bonuses
_PHASE_BONUSES: Dict[str, Dict[CoordinationPattern, float]] = {
    "6": {CoordinationPattern.REVIEW_LOOP: 3.0},
    "8": {CoordinationPattern.SAGA: 3.0},
    "2": {CoordinationPattern.DEBATE: 2.0},
    "3": {CoordinationPattern.DEBATE: 2.0},
}


@dataclass
class PatternSelection:
    """Result of pattern selection."""

    pattern: CoordinationPattern
    score: float
    reason: str
    all_scores: Dict[str, float] = field(default_factory=dict)


class PatternSelector:
    """Select the best coordination pattern for a task."""

    def __init__(self, enabled_flags: Optional[Set[str]] = None):
        """
        Args:
            enabled_flags: Set of enabled feature flags. If None, only
                           SEQUENTIAL (which has no flag requirements) is available.
        """
        self._enabled_flags = enabled_flags or set()

    def select(
        self,
        gravity: str,
        roster: Optional[List[Tuple]] = None,
        task_id: str = "",
        task_name: str = "",
        task_category: Optional[str] = None,
        has_dependencies: bool = False,
        phase_id: Optional[str] = None,
        graph: Any = None,
    ) -> PatternSelection:
        """Score all patterns and return the best.

        Args:
            gravity: Gravity level (light/standard/intensive).
            roster: Agent roster tuples.
            task_id: Current task ID.
            task_name: Human-readable task name.
            task_category: Optional task category for pattern filtering.
            has_dependencies: Whether this task has unresolved dependencies.
            phase_id: Current phase ID (e.g. "6-code-review").
            graph: Optional GraphManager.

        Returns:
            PatternSelection with the chosen pattern and scores.
        """
        agent_count = len(roster) if roster else 1
        phase_num = self._extract_phase_num(phase_id)

        scores: Dict[str, float] = {}
        reasons: Dict[str, str] = {}

        for pattern, spec in PATTERN_CATALOG.items():
            score, reason = self._score_pattern(
                spec, gravity, agent_count, task_category,
                phase_num, has_dependencies,
            )
            scores[pattern.value] = score
            reasons[pattern.value] = reason

        # Find best pattern
        best_pattern = max(scores, key=scores.get)
        best_enum = CoordinationPattern(best_pattern)

        selection = PatternSelection(
            pattern=best_enum,
            score=scores[best_pattern],
            reason=reasons[best_pattern],
            all_scores=scores,
        )

        if best_enum != CoordinationPattern.SEQUENTIAL:
            logger.info(
                "Task %s pattern selection: %s (score=%.2f) — %s",
                task_id, best_pattern, scores[best_pattern], reasons[best_pattern],
            )

        return selection

    def _score_pattern(
        self,
        spec: PatternSpec,
        gravity: str,
        agent_count: int,
        task_category: Optional[str],
        phase_num: Optional[int],
        has_dependencies: bool,
    ) -> Tuple[float, str]:
        """Score a single pattern against context.

        Returns (score, reason).
        """
        # SEQUENTIAL always scores 1.0 as baseline floor
        if spec.name == CoordinationPattern.SEQUENTIAL:
            return 1.0, "baseline"

        score = 0.0
        reasons = []

        # Gate: gravity compatibility
        if gravity not in spec.compatible_gravity:
            return -1.0, f"incompatible gravity ({gravity})"

        # Gate: feature flags
        for flag in spec.requires_feature_flags:
            if flag not in self._enabled_flags:
                return -1.0, f"missing feature flag ({flag})"

        # Gate: agent count bounds
        if agent_count < spec.min_agents:
            return -1.0, f"too few agents ({agent_count} < {spec.min_agents})"
        if agent_count > spec.max_agents:
            return -1.0, f"too many agents ({agent_count} > {spec.max_agents})"

        # Gate: task category (empty = all)
        if spec.task_categories and task_category and task_category not in spec.task_categories:
            return -1.0, f"task category mismatch ({task_category})"

        # Bonus: INTENSIVE gravity
        if gravity == "intensive":
            score += 2.0
            reasons.append("intensive gravity")

        # Bonus: agent count alignment
        if spec.min_agents <= agent_count <= spec.max_agents:
            alignment = 0.5 * min(agent_count, spec.max_agents) / max(spec.max_agents, 1)
            score += alignment
            reasons.append(f"agent alignment +{alignment:.1f}")

        # Bonus: phase-specific
        if phase_num is not None:
            phase_bonuses = _PHASE_BONUSES.get(str(phase_num), {})
            bonus = phase_bonuses.get(spec.name, 0.0)
            if bonus > 0:
                score += bonus
                reasons.append(f"phase {phase_num} bonus +{bonus:.1f}")

        # Penalty: has dependencies and pattern doesn't support rollback
        if has_dependencies and not spec.supports_rollback:
            score -= 0.5
            reasons.append("no rollback with dependencies")

        # Penalty: high overhead
        if spec.estimated_overhead_factor > 2.0:
            score -= 0.3
            reasons.append(f"high overhead ({spec.estimated_overhead_factor:.1f}x)")

        reason = "; ".join(reasons) if reasons else "qualified"
        return score, reason

    @staticmethod
    def _extract_phase_num(phase_id: Optional[str]) -> Optional[int]:
        """Extract phase number from phase_id like '6-code-review'."""
        if not phase_id:
            return None
        try:
            return int(phase_id.split("-")[0])
        except (ValueError, IndexError):
            return None


def select_pattern(
    gravity: str,
    roster: Optional[List[Tuple]] = None,
    task_id: str = "",
    task_name: str = "",
    phase_id: Optional[str] = None,
    enabled_flags: Optional[Set[str]] = None,
    task_category: Optional[str] = None,
) -> PatternSelection:
    """Convenience function to select a coordination pattern.

    Args:
        gravity: Gravity level string.
        roster: Agent roster.
        task_id: Task identifier.
        task_name: Task display name.
        phase_id: Phase identifier.
        enabled_flags: Enabled feature flags.
        task_category: Optional task category.

    Returns:
        PatternSelection with chosen pattern.
    """
    selector = PatternSelector(enabled_flags=enabled_flags)
    return selector.select(
        gravity=gravity,
        roster=roster,
        task_id=task_id,
        task_name=task_name,
        task_category=task_category,
        phase_id=phase_id,
    )
