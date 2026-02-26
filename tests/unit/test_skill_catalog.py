"""Unit tests for core/skills/catalog.py — 64-skill catalog and helpers."""

import pytest
from core.skills.catalog import (
    SKILL_CATALOG, get_skill, get_skills_for_phase,
    get_skills_for_profile, get_skills_by_category, get_catalog_stats,
)
from core.skills.models import RiskLevel


@pytest.mark.unit
class TestCatalogData:
    def test_exactly_64_skills(self):
        assert len(SKILL_CATALOG) == 64

    def test_all_have_required_fields(self):
        for skill in SKILL_CATALOG:
            assert skill.id, f"Skill missing id"
            assert skill.name, f"Skill {skill.id} missing name"
            assert skill.description, f"Skill {skill.id} missing description"
            assert skill.category, f"Skill {skill.id} missing category"
            assert skill.source, f"Skill {skill.id} missing source"

    def test_unique_ids(self):
        ids = [s.id for s in SKILL_CATALOG]
        assert len(ids) == len(set(ids))

    def test_valid_risk_levels(self):
        for skill in SKILL_CATALOG:
            assert skill.risk_level in RiskLevel

    def test_phases_in_range(self):
        for skill in SKILL_CATALOG:
            for phase in skill.sdlc_phases:
                assert 0 <= phase <= 9, f"Skill {skill.id} has invalid phase {phase}"


@pytest.mark.unit
class TestCatalogHelpers:
    def test_get_skill_found(self):
        s = get_skill("format-code")
        assert s is not None
        assert s.id == "format-code"

    def test_get_skill_not_found(self):
        assert get_skill("nonexistent") is None

    def test_get_skills_for_phase(self):
        skills = get_skills_for_phase(5)
        assert len(skills) > 0
        for s in skills:
            assert 5 in s.sdlc_phases

    def test_get_skills_for_profile_development(self):
        allowed, blocked = get_skills_for_profile("development")
        assert len(allowed) == 64  # development allows all
        assert len(blocked) == 0

    def test_get_skills_for_profile_airgapped(self):
        allowed, blocked = get_skills_for_profile("air_gapped")
        assert len(allowed) + len(blocked) == 64
        assert len(blocked) > 0  # some skills require internet

    def test_get_skills_by_category(self):
        security = get_skills_by_category("security")
        assert len(security) > 0
        for s in security:
            assert s.category == "security"

    def test_catalog_stats(self):
        stats = get_catalog_stats()
        assert stats["total_skills"] == 64
        assert "by_category" in stats
        assert "by_risk_level" in stats
