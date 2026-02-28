"""Tests for orchestration.retry_policy."""

import pytest
from unittest.mock import MagicMock

from orchestration.retry_policy import (
    RetryPolicy,
    DEFAULT_POLICIES,
    ConsecutiveFailureTracker,
    get_policy,
    get_escalation_model,
    execute_with_retry,
)


class TestRetryPolicy:
    """Test RetryPolicy dataclass."""

    def test_light_defaults(self):
        policy = DEFAULT_POLICIES["light"]
        assert policy.max_retries == 1
        assert policy.cooldown_seconds == 0
        assert policy.escalate_on_failure is False
        assert policy.backoff_multiplier == 1.0

    def test_standard_defaults(self):
        policy = DEFAULT_POLICIES["standard"]
        assert policy.max_retries == 2
        assert policy.cooldown_seconds == 5
        assert policy.escalate_on_failure is False
        assert policy.backoff_multiplier == 1.5

    def test_intensive_defaults(self):
        policy = DEFAULT_POLICIES["intensive"]
        assert policy.max_retries == 3
        assert policy.cooldown_seconds == 10
        assert policy.escalate_on_failure is True
        assert policy.backoff_multiplier == 2.0

    def test_cooldown_for_attempt_zero(self):
        policy = DEFAULT_POLICIES["standard"]
        assert policy.cooldown_for_attempt(0) == 0.0

    def test_cooldown_with_backoff(self):
        policy = DEFAULT_POLICIES["standard"]  # cooldown=5, backoff=1.5
        assert policy.cooldown_for_attempt(1) == 5.0        # 5 * 1.5^0
        assert policy.cooldown_for_attempt(2) == 7.5        # 5 * 1.5^1
        assert policy.cooldown_for_attempt(3) == pytest.approx(11.25)  # 5 * 1.5^2

    def test_frozen(self):
        policy = DEFAULT_POLICIES["light"]
        with pytest.raises(AttributeError):
            policy.max_retries = 5


class TestGetPolicy:
    """Test get_policy() lookup."""

    def test_known_gravity(self):
        assert get_policy("light") is DEFAULT_POLICIES["light"]
        assert get_policy("standard") is DEFAULT_POLICIES["standard"]
        assert get_policy("intensive") is DEFAULT_POLICIES["intensive"]

    def test_unknown_gravity_falls_back(self):
        assert get_policy("unknown") is DEFAULT_POLICIES["standard"]


class TestGetEscalationModel:
    """Test model escalation chain."""

    def test_haiku_escalation(self):
        assert get_escalation_model("haiku", 0) == "haiku"
        assert get_escalation_model("haiku", 1) == "sonnet"
        assert get_escalation_model("haiku", 2) == "opus"
        assert get_escalation_model("haiku", 3) == "opus"  # Capped at top

    def test_sonnet_escalation(self):
        assert get_escalation_model("sonnet", 0) == "sonnet"
        assert get_escalation_model("sonnet", 1) == "opus"

    def test_opus_stays_opus(self):
        assert get_escalation_model("opus", 0) == "opus"
        assert get_escalation_model("opus", 5) == "opus"

    def test_unknown_tier_starts_at_haiku(self):
        assert get_escalation_model("unknown", 0) == "haiku"


class TestConsecutiveFailureTracker:
    """Test failure tracking and threshold."""

    def test_initial_count_zero(self):
        tracker = ConsecutiveFailureTracker()
        assert tracker.get_count("task-1") == 0

    def test_record_failure_increments(self):
        tracker = ConsecutiveFailureTracker()
        assert tracker.record_failure("task-1") is False
        assert tracker.get_count("task-1") == 1

    def test_threshold_reached(self):
        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record_failure("task-1")
        tracker.record_failure("task-1")
        reached = tracker.record_failure("task-1")
        assert reached is True

    def test_success_resets(self):
        tracker = ConsecutiveFailureTracker(threshold=3)
        tracker.record_failure("task-1")
        tracker.record_failure("task-1")
        tracker.record_success("task-1")
        assert tracker.get_count("task-1") == 0

    def test_independent_tasks(self):
        tracker = ConsecutiveFailureTracker()
        tracker.record_failure("task-1")
        tracker.record_failure("task-2")
        assert tracker.get_count("task-1") == 1
        assert tracker.get_count("task-2") == 1


class TestExecuteWithRetry:
    """Test the execute_with_retry helper."""

    def test_success_on_first_try(self):
        task = MagicMock(return_value=True)
        policy = RetryPolicy(max_retries=2, cooldown_seconds=0,
                             escalate_on_failure=False, backoff_multiplier=1.0)
        assert execute_with_retry(task, policy, "task-1") is True
        assert task.call_count == 1

    def test_success_on_retry(self):
        task = MagicMock(side_effect=[False, True])
        policy = RetryPolicy(max_retries=1, cooldown_seconds=0,
                             escalate_on_failure=False, backoff_multiplier=1.0)
        assert execute_with_retry(task, policy, "task-1") is True
        assert task.call_count == 2

    def test_all_retries_exhausted(self):
        task = MagicMock(return_value=False)
        policy = RetryPolicy(max_retries=1, cooldown_seconds=0,
                             escalate_on_failure=False, backoff_multiplier=1.0)
        tracker = ConsecutiveFailureTracker()
        result = execute_with_retry(task, policy, "task-1", tracker=tracker)
        assert result is False
        assert task.call_count == 2
        assert tracker.get_count("task-1") == 1

    def test_none_treated_as_success(self):
        task = MagicMock(return_value=None)
        policy = RetryPolicy(max_retries=0, cooldown_seconds=0,
                             escalate_on_failure=False, backoff_multiplier=1.0)
        assert execute_with_retry(task, policy, "task-1") is True

    def test_exception_triggers_retry(self):
        task = MagicMock(side_effect=[RuntimeError("oops"), True])
        policy = RetryPolicy(max_retries=1, cooldown_seconds=0,
                             escalate_on_failure=False, backoff_multiplier=1.0)
        assert execute_with_retry(task, policy, "task-1") is True
        assert task.call_count == 2

    def test_on_retry_callback(self):
        task = MagicMock(side_effect=[False, True])
        policy = RetryPolicy(max_retries=1, cooldown_seconds=0,
                             escalate_on_failure=False, backoff_multiplier=1.0)
        callback = MagicMock()
        execute_with_retry(task, policy, "task-1", on_retry=callback)
        callback.assert_called_once_with(1, "returned False")
