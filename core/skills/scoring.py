"""Multi-signal task outcome scoring.

Replaces the flat 1.0/0.3 binary scoring with a richer signal that
accounts for artifact completeness and memory richness.

Score ranges:
    success=True:  base=0.6 + artifact_bonus(0-0.25) + memory_bonus(0-0.15) = [0.6, 1.0]
    success=False: base=0.15 + partial_artifact_credit(0-0.15)              = [0.1, 0.3]

Floor of 0.1 -- even failures contribute data to the learning system.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def compute_task_score(
    *,
    success: bool,
    task_id: str,
    expected_artifacts: List[str],
    actual_artifacts: List[str],
    mem_entry_count: int = 0,
    gravity: str = "standard",
) -> float:
    """Compute a multi-signal task outcome score.

    Args:
        success: Whether the task succeeded (True) or failed (False).
        task_id: Task identifier (for logging).
        expected_artifacts: List of expected artifact filenames.
        actual_artifacts: List of actually-produced artifact paths.
        mem_entry_count: Number of TaskMemory entries recorded.
        gravity: Gravity level string (for logging context).

    Returns:
        Score between 0.1 and 1.0.
    """
    if success:
        base = 0.6

        # Artifact completeness bonus (0 to 0.25)
        if expected_artifacts:
            ratio = min(1.0, len(actual_artifacts) / len(expected_artifacts))
            artifact_bonus = ratio * 0.25
        else:
            # No expected artifacts -- full bonus if task declared success
            artifact_bonus = 0.25

        # Memory richness bonus (0 to 0.15)
        # 3+ entries = full bonus; fewer = proportional
        memory_bonus = min(1.0, mem_entry_count / 3.0) * 0.15

        score = base + artifact_bonus + memory_bonus
    else:
        base = 0.15

        # Partial artifact credit (0 to 0.15)
        if expected_artifacts and actual_artifacts:
            ratio = min(1.0, len(actual_artifacts) / len(expected_artifacts))
            partial_credit = ratio * 0.15
        else:
            partial_credit = 0.0

        score = base + partial_credit

    # Floor at 0.1, cap at 1.0
    score = max(0.1, min(1.0, score))

    logger.debug(
        "Task %s score: %.2f (success=%s, artifacts=%d/%d, mem_entries=%d, gravity=%s)",
        task_id, score, success,
        len(actual_artifacts), len(expected_artifacts),
        mem_entry_count, gravity,
    )
    return score
