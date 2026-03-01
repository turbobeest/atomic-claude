"""Tests for skill context injection pipeline.

Covers:
- context_formatter: format_skill_context, ContextVar accessors
- scoring: compute_task_score boundary cases
- TaskMemory: skill_context property and build_metadata extension
- Auto-injection: ContextVar -> FeatureAwareLLMInvoker.invoke()
"""

import pytest
from unittest.mock import MagicMock, patch

from core.skills.models import (
    GravityLevel,
    RiskLevel,
    SkillMetadata,
    SkillSelection,
)
from core.skills.context_formatter import (
    format_skill_context,
    get_active_skill_context,
    set_active_skill_context,
)
from core.skills.scoring import compute_task_score
from orchestration.task_memory import TaskMemory


def _make_skill(id: str, name: str, description: str = "A skill.",
                category: str = "testing", risk_level: RiskLevel = RiskLevel.NONE,
                risk_notes: str = "") -> SkillMetadata:
    """Helper to create a SkillMetadata for tests."""
    return SkillMetadata(
        id=id, name=name, description=description,
        category=category, risk_level=risk_level, risk_notes=risk_notes,
    )


def _make_selection(skills, workflow=None, gravity=GravityLevel.STANDARD) -> SkillSelection:
    return SkillSelection(skills=skills, method="test", gravity=gravity, workflow=workflow)


# ───────────────────────────────────────────────────────────
# format_skill_context
# ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestFormatSkillContext:

    def test_empty_selection_returns_none(self):
        sel = _make_selection(skills=[])
        assert format_skill_context(sel, GravityLevel.STANDARD) is None

    def test_none_selection_returns_none(self):
        assert format_skill_context(None, GravityLevel.STANDARD) is None

    def test_light_max_two_skills(self):
        skills = [_make_skill(f"s{i}", f"Skill {i}") for i in range(5)]
        sel = _make_selection(skills)
        result = format_skill_context(sel, GravityLevel.LIGHT)
        assert result is not None
        # Count skill lines (lines starting with "- ")
        skill_lines = [l for l in result.split("\n") if l.startswith("- ")]
        assert len(skill_lines) == 2

    def test_light_format_under_200_tokens(self):
        skills = [_make_skill("s1", "Format Code", "Auto-format source code.")]
        sel = _make_selection(skills)
        result = format_skill_context(sel, GravityLevel.LIGHT)
        # Rough token estimate: words * 1.3
        word_count = len(result.split())
        assert word_count < 150  # Well under 200 tokens

    def test_light_format_contains_name(self):
        skills = [_make_skill("s1", "Format Code", "Auto-format source code.")]
        sel = _make_selection(skills)
        result = format_skill_context(sel, GravityLevel.LIGHT)
        assert "Format Code" in result

    def test_standard_includes_category_and_description(self):
        skills = [_make_skill("s1", "Lint YAML", "Validate YAML files.", category="validation")]
        sel = _make_selection(skills)
        result = format_skill_context(sel, GravityLevel.STANDARD)
        assert "[validation]" in result
        assert "Validate YAML files." in result

    def test_standard_max_eight_skills(self):
        skills = [_make_skill(f"s{i}", f"Skill {i}") for i in range(12)]
        sel = _make_selection(skills)
        result = format_skill_context(sel, GravityLevel.STANDARD)
        skill_lines = [l for l in result.split("\n") if l.startswith("- ")]
        assert len(skill_lines) == 8

    def test_intensive_includes_risk_notes(self):
        skills = [_make_skill(
            "s1", "Deploy Prod", "Deploy to production.",
            risk_level=RiskLevel.HIGH, risk_notes="Requires approval",
        )]
        sel = _make_selection(skills)
        result = format_skill_context(sel, GravityLevel.INTENSIVE)
        assert "Risk: High" in result
        assert "Requires approval" in result

    def test_intensive_includes_workflow_header(self):
        skills = [_make_skill("s1", "Step 1", "First step.")]
        sel = _make_selection(skills, workflow="CI/CD Pipeline")
        result = format_skill_context(sel, GravityLevel.INTENSIVE)
        assert "Workflow: CI/CD Pipeline" in result

    def test_intensive_max_fifteen_skills(self):
        skills = [_make_skill(f"s{i}", f"Skill {i}") for i in range(20)]
        sel = _make_selection(skills)
        result = format_skill_context(sel, GravityLevel.INTENSIVE)
        # Each skill gets a "- Name" line
        name_lines = [l for l in result.split("\n") if l.startswith("- ")]
        assert len(name_lines) == 15

    def test_header_always_present(self):
        skills = [_make_skill("s1", "Test")]
        sel = _make_selection(skills)
        for gravity in GravityLevel:
            result = format_skill_context(sel, gravity)
            assert result.startswith("[Active Skills]")


# ───────────────────────────────────────────────────────────
# ContextVar accessors
# ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestContextVar:

    def test_default_is_none(self):
        # Reset to default
        set_active_skill_context(None)
        assert get_active_skill_context() is None

    def test_set_and_get(self):
        set_active_skill_context("test context")
        assert get_active_skill_context() == "test context"
        # Cleanup
        set_active_skill_context(None)

    def test_clear(self):
        set_active_skill_context("something")
        set_active_skill_context(None)
        assert get_active_skill_context() is None


# ───────────────────────────────────────────────────────────
# compute_task_score
# ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestComputeTaskScore:

    def test_full_success_all_artifacts_rich_memory(self):
        """Perfect task: success + all artifacts + 3+ memory entries = 1.0."""
        score = compute_task_score(
            success=True, task_id="001",
            expected_artifacts=["a.json", "b.json"],
            actual_artifacts=["a.json", "b.json"],
            mem_entry_count=5,
        )
        assert score == 1.0

    def test_success_no_artifacts_no_memory(self):
        """Success with no expected artifacts and no memory = 0.6 + 0.25 + 0.0 = 0.85."""
        score = compute_task_score(
            success=True, task_id="002",
            expected_artifacts=[],
            actual_artifacts=[],
            mem_entry_count=0,
        )
        assert score == pytest.approx(0.85, abs=0.01)

    def test_success_partial_artifacts(self):
        """Success with 1/2 artifacts, no memory = 0.6 + 0.125 + 0.0 = 0.725."""
        score = compute_task_score(
            success=True, task_id="003",
            expected_artifacts=["a.json", "b.json"],
            actual_artifacts=["a.json"],
            mem_entry_count=0,
        )
        assert score == pytest.approx(0.725, abs=0.01)

    def test_failure_no_artifacts(self):
        """Failure with no artifacts = base 0.15."""
        score = compute_task_score(
            success=False, task_id="004",
            expected_artifacts=["a.json"],
            actual_artifacts=[],
            mem_entry_count=0,
        )
        assert score == pytest.approx(0.15, abs=0.01)

    def test_failure_partial_artifacts(self):
        """Failure with 1/2 artifacts = 0.15 + 0.075 = 0.225."""
        score = compute_task_score(
            success=False, task_id="005",
            expected_artifacts=["a.json", "b.json"],
            actual_artifacts=["a.json"],
            mem_entry_count=3,
        )
        assert score == pytest.approx(0.225, abs=0.01)

    def test_floor_at_0_1(self):
        """Score never goes below 0.1."""
        score = compute_task_score(
            success=False, task_id="006",
            expected_artifacts=[],
            actual_artifacts=[],
            mem_entry_count=0,
        )
        assert score >= 0.1

    def test_cap_at_1_0(self):
        """Score never exceeds 1.0."""
        score = compute_task_score(
            success=True, task_id="007",
            expected_artifacts=["a"],
            actual_artifacts=["a", "b", "c"],  # More than expected
            mem_entry_count=100,
        )
        assert score <= 1.0

    def test_memory_bonus_proportional(self):
        """1 memory entry = 1/3 of full bonus."""
        score_0 = compute_task_score(
            success=True, task_id="a",
            expected_artifacts=[], actual_artifacts=[], mem_entry_count=0,
        )
        score_1 = compute_task_score(
            success=True, task_id="b",
            expected_artifacts=[], actual_artifacts=[], mem_entry_count=1,
        )
        score_3 = compute_task_score(
            success=True, task_id="c",
            expected_artifacts=[], actual_artifacts=[], mem_entry_count=3,
        )
        assert score_0 < score_1 < score_3


# ───────────────────────────────────────────────────────────
# TaskMemory skill context integration
# ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestTaskMemorySkillContext:

    def test_skill_context_default_none(self):
        mem = TaskMemory("0-setup", "001", "Test")
        assert mem.skill_context is None
        assert mem.skill_selection is None
        assert mem.gravity_level is None

    def test_set_skill_context(self):
        mem = TaskMemory("0-setup", "001", "Test")
        sel = _make_selection([_make_skill("s1", "Foo")])
        mem.set_skill_context("formatted text", sel, "standard")
        assert mem.skill_context == "formatted text"
        assert mem.skill_selection is sel
        assert mem.gravity_level == "standard"

    def test_build_metadata_includes_skills_when_set(self):
        mem = TaskMemory("0-setup", "001", "Test")
        sel = _make_selection([_make_skill("s1", "Foo"), _make_skill("s2", "Bar")])
        mem.set_skill_context("ctx", sel, "intensive")
        mem.finding("something")  # Need at least one entry

        meta = mem.build_metadata()
        assert meta["skills_used"] == ["s1", "s2"]
        assert meta["gravity"] == "intensive"

    def test_build_metadata_no_skills_when_not_set(self):
        mem = TaskMemory("0-setup", "001", "Test")
        mem.finding("something")
        meta = mem.build_metadata()
        assert "skills_used" not in meta
        assert "gravity" not in meta


# ───────────────────────────────────────────────────────────
# Auto-injection via FeatureAwareLLMInvoker
# ───────────────────────────────────────────────────────────

@pytest.mark.unit
class TestAutoInjection:

    def test_invoke_prepends_skill_context(self):
        """When context var is set, invoke() should prepend to system_prompt."""
        set_active_skill_context("[Active Skills]\n- Test Skill: Do the thing.")
        try:
            mock_provider = MagicMock()
            mock_provider.provider_name = "test"
            mock_provider.invoke.return_value = "response"

            from core.llm.invoke import FeatureAwareLLMInvoker
            invoker = FeatureAwareLLMInvoker(mock_provider)
            invoker.invoke("hello", system_prompt="You are helpful.")

            # Check that provider.invoke was called with merged system_prompt
            call_kwargs = mock_provider.invoke.call_args
            sys_prompt = call_kwargs.kwargs.get("system_prompt") or call_kwargs[1].get("system_prompt", "")
            assert "[Active Skills]" in sys_prompt
            assert "You are helpful." in sys_prompt
        finally:
            set_active_skill_context(None)

    def test_invoke_sets_system_prompt_when_none(self):
        """When no existing system_prompt, skill context becomes the system_prompt."""
        set_active_skill_context("[Active Skills]\n- Skill A: desc.")
        try:
            mock_provider = MagicMock()
            mock_provider.provider_name = "test"
            mock_provider.invoke.return_value = "response"

            from core.llm.invoke import FeatureAwareLLMInvoker
            invoker = FeatureAwareLLMInvoker(mock_provider)
            invoker.invoke("hello")

            call_kwargs = mock_provider.invoke.call_args
            sys_prompt = call_kwargs.kwargs.get("system_prompt") or call_kwargs[1].get("system_prompt", "")
            assert "[Active Skills]" in sys_prompt
        finally:
            set_active_skill_context(None)

    def test_invoke_no_injection_when_context_cleared(self):
        """When context var is None, no skill context is injected."""
        set_active_skill_context(None)

        mock_provider = MagicMock()
        mock_provider.provider_name = "test"
        mock_provider.invoke.return_value = "response"

        from core.llm.invoke import FeatureAwareLLMInvoker
        invoker = FeatureAwareLLMInvoker(mock_provider)
        invoker.invoke("hello", system_prompt="Original prompt.")

        call_kwargs = mock_provider.invoke.call_args
        sys_prompt = call_kwargs.kwargs.get("system_prompt") or call_kwargs[1].get("system_prompt", "")
        assert "[Active Skills]" not in sys_prompt
        assert "Original prompt." in sys_prompt
