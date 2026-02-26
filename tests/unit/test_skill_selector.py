"""Unit tests for core/skills/selector.py — gravity-aware skill selection."""

import pytest
from core.skills.models import GravityLevel, SkillSelection
from core.skills.selector import SkillSelector


@pytest.mark.unit
class TestGravityParams:
    def test_light_params(self):
        s = SkillSelector()
        p = s._gravity_params(GravityLevel.LIGHT)
        assert p["max_skills"] == 2
        assert p["skip_workflow"] is True
        assert p["skip_semantic"] is True

    def test_standard_params(self):
        s = SkillSelector()
        p = s._gravity_params(GravityLevel.STANDARD)
        assert p["max_skills"] == 8
        assert p["skip_workflow"] is False

    def test_intensive_params(self):
        s = SkillSelector()
        p = s._gravity_params(GravityLevel.INTENSIVE)
        assert p["max_skills"] == 15
        assert "testing" in p["mandatory_categories"]
        assert "security" in p["mandatory_categories"]


@pytest.mark.unit
class TestFilesystemFallback:
    def test_returns_skill_selection(self):
        s = SkillSelector()
        result = s._filesystem_fallback("format code", "cloud_full", GravityLevel.STANDARD,
                                         s._gravity_params(GravityLevel.STANDARD))
        assert isinstance(result, SkillSelection)
        assert result.method == "filesystem_fallback"

    def test_respects_max_skills(self):
        s = SkillSelector()
        params = s._gravity_params(GravityLevel.LIGHT)
        result = s._filesystem_fallback("validate yaml json markdown", "development",
                                         GravityLevel.LIGHT, params)
        assert len(result.skills) <= params["max_skills"]

    def test_profile_filtering(self):
        s = SkillSelector()
        params = s._gravity_params(GravityLevel.STANDARD)
        result = s._filesystem_fallback("security scan", "air_gapped",
                                         GravityLevel.STANDARD, params)
        # All returned skills should be installable in air_gapped
        for skill in result.skills:
            assert "air_gapped" in skill.installable_in_profiles()
