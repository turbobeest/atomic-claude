"""Retry Policy — configurable retry strategies per gravity level.

Provides retry policies with cooldown, backoff, and model escalation.
Tasks that exhaust retries are flagged for human review via
ConsecutiveFailureTracker.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Model escalation chain: haiku → sonnet → opus
_ESCALATION_CHAIN = ["haiku", "sonnet", "opus"]


@dataclass(frozen=True)
class RetryPolicy:
    """Retry configuration for a gravity level."""

    max_retries: int
    cooldown_seconds: float
    escalate_on_failure: bool
    backoff_multiplier: float

    def cooldown_for_attempt(self, attempt: int) -> float:
        """Calculate cooldown duration for a given attempt number (0-indexed)."""
        if attempt <= 0:
            return 0.0
        return self.cooldown_seconds * (self.backoff_multiplier ** (attempt - 1))


DEFAULT_POLICIES: Dict[str, RetryPolicy] = {
    "light": RetryPolicy(
        max_retries=1,
        cooldown_seconds=0,
        escalate_on_failure=False,
        backoff_multiplier=1.0,
    ),
    "standard": RetryPolicy(
        max_retries=2,
        cooldown_seconds=5,
        escalate_on_failure=False,
        backoff_multiplier=1.5,
    ),
    "intensive": RetryPolicy(
        max_retries=3,
        cooldown_seconds=10,
        escalate_on_failure=True,
        backoff_multiplier=2.0,
    ),
}


class ConsecutiveFailureTracker:
    """Tracks consecutive task failures and flags for human review.

    A task is flagged when it hits *threshold* consecutive failures.
    A single success resets the counter.
    """

    def __init__(self, threshold: int = 3):
        self._counts: Dict[str, int] = defaultdict(int)
        self._threshold = threshold

    def record_failure(self, task_id: str) -> bool:
        """Record a failure. Returns True if threshold reached."""
        self._counts[task_id] += 1
        reached = self._counts[task_id] >= self._threshold
        if reached:
            logger.warning(
                "Task %s hit %d consecutive failures — flagging for review",
                task_id, self._counts[task_id],
            )
        return reached

    def record_success(self, task_id: str) -> None:
        """Reset failure counter on success."""
        self._counts.pop(task_id, None)

    def get_count(self, task_id: str) -> int:
        """Return current consecutive failure count."""
        return self._counts.get(task_id, 0)


def get_policy(gravity: str) -> RetryPolicy:
    """Look up the retry policy for a gravity level.

    Args:
        gravity: One of "light", "standard", "intensive".

    Returns:
        Matching RetryPolicy (falls back to "standard" if unknown).
    """
    return DEFAULT_POLICIES.get(gravity, DEFAULT_POLICIES["standard"])


def get_escalation_model(current_tier: str, attempt: int) -> str:
    """Determine the model tier for a retry attempt.

    Walks the escalation chain (haiku → sonnet → opus) based on
    the attempt number. If the current tier is already at or above
    the chain position for this attempt, returns the current tier.

    Args:
        current_tier: Current model tier name (e.g. "haiku").
        attempt: Retry attempt number (0 = first try).

    Returns:
        Model tier name for this attempt.
    """
    try:
        current_idx = _ESCALATION_CHAIN.index(current_tier)
    except ValueError:
        current_idx = 0

    target_idx = min(current_idx + attempt, len(_ESCALATION_CHAIN) - 1)
    return _ESCALATION_CHAIN[target_idx]


def execute_with_retry(
    task_func,
    policy: RetryPolicy,
    task_id: str,
    tracker: Optional[ConsecutiveFailureTracker] = None,
    on_retry=None,
) -> bool:
    """Execute a task function with retry logic.

    Args:
        task_func: Callable that returns True/None on success, False on failure,
                   or raises an exception.
        policy: RetryPolicy to apply.
        task_id: Task identifier for tracking.
        tracker: Optional ConsecutiveFailureTracker.
        on_retry: Optional callback(attempt, error) called before each retry.

    Returns:
        True if task succeeded, False if all retries exhausted.
    """
    last_error = None

    for attempt in range(policy.max_retries + 1):
        if attempt > 0:
            cooldown = policy.cooldown_for_attempt(attempt)
            if cooldown > 0:
                logger.info(
                    "Task %s retry %d/%d — cooldown %.1fs",
                    task_id, attempt, policy.max_retries, cooldown,
                )
                time.sleep(cooldown)
            if on_retry:
                on_retry(attempt, last_error)

        try:
            result = task_func()
            # Treat None as success; only explicit False is failure
            if result is not False:
                if tracker:
                    tracker.record_success(task_id)
                return True
            last_error = "returned False"
        except Exception as e:
            last_error = str(e)
            logger.warning(
                "Task %s attempt %d failed: %s", task_id, attempt, e,
            )

    # All retries exhausted
    if tracker:
        tracker.record_failure(task_id)
    return False
