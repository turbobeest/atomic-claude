"""Tests for core.shadow_agent."""

import pytest
from unittest.mock import MagicMock, patch
from concurrent.futures import Future

from core.shadow_agent import ShadowAgent, ShadowContext, ShadowFinding


class TestShouldActivate:
    """Test gravity gating."""

    def test_light_inactive(self):
        assert ShadowAgent.should_activate("light") is False

    def test_standard_active(self):
        assert ShadowAgent.should_activate("standard") is True

    def test_intensive_active(self):
        assert ShadowAgent.should_activate("intensive") is True

    def test_unknown_inactive(self):
        assert ShadowAgent.should_activate("unknown") is False


class TestParseFindings:
    """Test _parse_findings() response parsing."""

    def test_no_findings(self):
        agent = ShadowAgent()
        ctx = ShadowContext(
            task_id="001", task_name="Test", phase_id="0-setup", content="ok",
        )
        findings = agent._parse_findings("NO_FINDINGS", ctx)
        assert findings == []

    def test_single_finding(self):
        agent = ShadowAgent()
        ctx = ShadowContext(
            task_id="001", task_name="Test", phase_id="0-setup", content="ok",
        )
        response = "FINDING: major|security|SQL injection in user input handler"
        findings = agent._parse_findings(response, ctx)
        assert len(findings) == 1
        assert findings[0].severity == "major"
        assert findings[0].category == "security"
        assert "SQL injection" in findings[0].description

    def test_multiple_findings(self):
        agent = ShadowAgent()
        ctx = ShadowContext(
            task_id="001", task_name="Test", phase_id="0-setup", content="ok",
        )
        response = (
            "FINDING: critical|security|Auth bypass in API\n"
            "FINDING: minor|code_quality|Unused import\n"
            "FINDING: suggestion|naming|Consider renaming variable"
        )
        findings = agent._parse_findings(response, ctx)
        assert len(findings) == 3
        assert findings[0].severity == "critical"
        assert findings[2].severity == "suggestion"

    def test_invalid_severity_defaults(self):
        agent = ShadowAgent()
        ctx = ShadowContext(
            task_id="001", task_name="Test", phase_id="0-setup", content="ok",
        )
        response = "FINDING: unknown_severity|cat|desc"
        findings = agent._parse_findings(response, ctx)
        assert len(findings) == 1
        assert findings[0].severity == "suggestion"

    def test_malformed_line_skipped(self):
        agent = ShadowAgent()
        ctx = ShadowContext(
            task_id="001", task_name="Test", phase_id="0-setup", content="ok",
        )
        response = "FINDING: incomplete"
        findings = agent._parse_findings(response, ctx)
        assert findings == []


class TestEvaluate:
    """Test evaluate() with mocked LLM."""

    @patch("core.shadow_agent.ShadowAgent._run_audit")
    def test_evaluate_returns_findings(self, mock_audit):
        finding = ShadowFinding(
            id="shadow-001", severity="minor", category="quality",
            description="test", task_id="001", phase_id="0-setup",
        )
        mock_audit.return_value = [finding]

        agent = ShadowAgent()
        ctx = ShadowContext(
            task_id="001", task_name="Test", phase_id="0-setup", content="code",
        )
        findings = agent.evaluate(ctx)
        assert len(findings) == 1

    @patch("core.shadow_agent.ShadowAgent._get_criteria")
    def test_no_criteria_returns_empty(self, mock_criteria):
        mock_criteria.return_value = []
        agent = ShadowAgent()
        ctx = ShadowContext(
            task_id="001", task_name="Test", phase_id="0-setup", content="code",
        )
        findings = agent.evaluate(ctx)
        assert findings == []


class TestEvaluateAsync:
    """Test non-blocking async evaluation."""

    @patch("core.shadow_agent.ShadowAgent.evaluate")
    def test_returns_future(self, mock_eval):
        mock_eval.return_value = []
        agent = ShadowAgent()
        ctx = ShadowContext(
            task_id="001", task_name="Test", phase_id="0-setup", content="code",
        )
        future = agent.evaluate_async(ctx)
        assert isinstance(future, Future)
        result = future.result(timeout=5)
        assert result == []


class TestPersistFinding:
    """Test graph persistence of findings."""

    def test_writes_review_finding_node(self):
        graph = MagicMock()
        agent = ShadowAgent(graph=graph)
        finding = ShadowFinding(
            id="shadow-001", severity="major", category="security",
            description="XSS vulnerability", task_id="001", phase_id="0-setup",
        )
        agent._persist_finding(finding)

        graph.writer.create_node.assert_called_once()
        call_args = graph.writer.create_node.call_args
        assert call_args[0][0] == "ReviewFinding"
        props = call_args[0][1]
        assert props["shadow_finding"] is True
        assert props["severity"] == "major"

    def test_creates_review_of_relationship(self):
        graph = MagicMock()
        agent = ShadowAgent(graph=graph)
        finding = ShadowFinding(
            id="shadow-001", severity="minor", category="quality",
            description="test", task_id="001", phase_id="0-setup",
        )
        agent._persist_finding(finding)
        graph.writer.create_relationship.assert_called_once()

    def test_no_graph_no_op(self):
        agent = ShadowAgent(graph=None)
        finding = ShadowFinding(
            id="shadow-001", severity="minor", category="quality",
            description="test", task_id="001", phase_id="0-setup",
        )
        # Should not raise
        agent._persist_finding(finding)
