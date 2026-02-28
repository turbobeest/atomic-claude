"""Tests for core.memory.content_signals."""

import pytest

from core.memory.content_signals import ContentSignals, detect_signals, assign_priority


class TestDetectSignals:
    """Test detect_signals() pattern matching."""

    def test_empty_string(self):
        signals = detect_signals("")
        assert not signals.has_code_block
        assert not signals.has_decision_keywords
        assert not signals.has_error_keywords
        assert not signals.has_question_markers
        assert not signals.has_routine_keywords
        assert signals.score() == 0.0

    def test_code_block(self):
        signals = detect_signals("Here is code:\n```python\nprint('hi')\n```")
        assert signals.has_code_block
        assert signals.score() == pytest.approx(0.15)

    def test_decision_keywords(self):
        for keyword in ["decided", "selected", "chose", "approved", "rejected"]:
            signals = detect_signals(f"We {keyword} to use Python")
            assert signals.has_decision_keywords, f"Failed for keyword: {keyword}"

    def test_error_keywords(self):
        for keyword in ["failed", "error", "bug", "vulnerability", "breaking"]:
            signals = detect_signals(f"The test {keyword} due to timeout")
            assert signals.has_error_keywords, f"Failed for keyword: {keyword}"

    def test_question_markers(self):
        signals = detect_signals("Is this the right approach?")
        assert signals.has_question_markers

        signals = detect_signals("Status: TBD")
        assert signals.has_question_markers

        signals = detect_signals("TODO: fix later")
        assert signals.has_question_markers

    def test_routine_keywords(self):
        for keyword in ["acknowledged", "skipping", "already complete", "no changes"]:
            signals = detect_signals(f"Task {keyword}")
            assert signals.has_routine_keywords, f"Failed for keyword: {keyword}"

    def test_combined_positive_signals(self):
        text = "We decided to fix the error with ```code```"
        signals = detect_signals(text)
        assert signals.has_code_block
        assert signals.has_decision_keywords
        assert signals.has_error_keywords
        # 0.15 + 0.10 + 0.10 = 0.35
        assert signals.score() == pytest.approx(0.35)

    def test_routine_offset(self):
        text = "Already complete, no changes needed"
        signals = detect_signals(text)
        assert signals.has_routine_keywords
        assert signals.score() == pytest.approx(-0.10)

    def test_mixed_positive_and_routine(self):
        text = "We decided to skip this (already complete)"
        signals = detect_signals(text)
        assert signals.has_decision_keywords
        assert signals.has_routine_keywords
        # 0.10 - 0.10 = 0.0
        assert signals.score() == pytest.approx(0.0)

    def test_score_range(self):
        """Score should be in [-0.10, +0.40] range."""
        # Maximum: all positive signals
        max_text = "We decided? ```code``` failed error TBD"
        signals = detect_signals(max_text)
        assert signals.score() <= 0.40

        # Minimum: only routine
        min_text = "acknowledged, no changes"
        signals = detect_signals(min_text)
        assert signals.score() >= -0.10

    def test_case_insensitive(self):
        signals = detect_signals("DECIDED to use FAILED approach")
        assert signals.has_decision_keywords
        assert signals.has_error_keywords


class TestAssignPriority:
    """Test assign_priority() classification."""

    def test_p0_error_with_checkpoint(self):
        assert assign_priority("Test failed with critical error", "checkpoint") == "P0"
        assert assign_priority("Security vulnerability found", "phase_closeout") == "P0"

    def test_p1_decision_keywords(self):
        assert assign_priority("We decided to use Python", "task_progress") == "P1"

    def test_p1_task_end(self):
        assert assign_priority("Task completed normally", "task_end") == "P1"

    def test_p2_default(self):
        assert assign_priority("Some normal content here", "task_progress") == "P2"

    def test_p3_task_start(self):
        assert assign_priority("Starting task execution", "task_start") == "P3"

    def test_p3_routine_with_other_signals(self):
        # Routine but also has code blocks → P3 (not P4)
        assert assign_priority("Skipping ```code``` block", "task_progress") == "P3"

    def test_p4_pure_routine(self):
        assert assign_priority("acknowledged, no changes", "system_event") == "P4"
