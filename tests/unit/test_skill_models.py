"""Unit tests for core/skills/models.py — Pydantic models and profile rules."""

import pytest
from core.skills.models import (
    SkillMetadata, GravityAssessment, GravityLevel, GravitySignal,
    RiskLevel, SkillSelection, PROFILE_SKILL_RULES, risk_at_most,
)


@pytest.mark.unit
class TestSkillMetadata:
    def test_defaults(self):
        s = SkillMetadata(id="test", name="Test")
        assert s.risk_level == RiskLevel.NONE
        assert s.requires_internet is False
        assert s.times_used == 0

    def test_installable_in_all_profiles(self):
        s = SkillMetadata(id="safe", name="Safe", requires_internet=False, requires_saas=False, risk_level=RiskLevel.NONE)
        profiles = s.installable_in_profiles()
        assert "development" in profiles
        assert "cloud_full" in profiles
        assert "enterprise_secure" in profiles
        assert "air_gapped" in profiles

    def test_internet_blocked_in_airgapped(self):
        s = SkillMetadata(id="net", name="Net", requires_internet=True, risk_level=RiskLevel.NONE)
        assert "air_gapped" not in s.installable_in_profiles()
        assert "cloud_full" in s.installable_in_profiles()

    def test_saas_blocked_in_enterprise(self):
        s = SkillMetadata(id="saas", name="SaaS", requires_saas=True, risk_level=RiskLevel.NONE)
        assert "enterprise_secure" not in s.installable_in_profiles()
        assert "air_gapped" not in s.installable_in_profiles()

    def test_high_risk_only_in_development(self):
        s = SkillMetadata(id="risky", name="Risky", risk_level=RiskLevel.HIGH)
        profiles = s.installable_in_profiles()
        assert profiles == ["development"]

    def test_medium_risk_in_cloud_and_dev(self):
        s = SkillMetadata(id="med", name="Med", risk_level=RiskLevel.MEDIUM)
        profiles = s.installable_in_profiles()
        assert "cloud_full" in profiles
        assert "development" in profiles
        assert "enterprise_secure" not in profiles


@pytest.mark.unit
class TestRiskAtMost:
    def test_none_at_most_low(self):
        assert risk_at_most(RiskLevel.NONE, RiskLevel.LOW)

    def test_high_not_at_most_medium(self):
        assert not risk_at_most(RiskLevel.HIGH, RiskLevel.MEDIUM)

    def test_same_level(self):
        assert risk_at_most(RiskLevel.MEDIUM, RiskLevel.MEDIUM)


@pytest.mark.unit
class TestGravityAssessment:
    def test_defaults(self):
        a = GravityAssessment(gravity=GravityLevel.STANDARD, confidence=0.8)
        assert a.method == "multi_signal_classifier"
        assert a.gravity_floor == GravityLevel.LIGHT

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            GravityAssessment(gravity=GravityLevel.LIGHT, confidence=1.5)


@pytest.mark.unit
class TestSkillSelection:
    def test_defaults(self):
        ss = SkillSelection()
        assert ss.gravity == GravityLevel.STANDARD
        assert ss.profile == "cloud_full"
        assert ss.skills == []


@pytest.mark.unit
class TestProfileRules:
    def test_all_four_profiles_exist(self):
        assert set(PROFILE_SKILL_RULES.keys()) == {"air_gapped", "enterprise_secure", "cloud_full", "development"}

    def test_airgapped_no_internet(self):
        assert PROFILE_SKILL_RULES["air_gapped"]["allow_internet"] is False

    def test_development_allows_all(self):
        rules = PROFILE_SKILL_RULES["development"]
        assert rules["allow_internet"] is True
        assert rules["allow_saas"] is True
        assert rules["max_risk"] == RiskLevel.HIGH
