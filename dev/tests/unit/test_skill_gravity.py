"""Unit tests for core/skills/gravity.py — 5-signal gravity classifier."""

import pytest
from core.skills.gravity import GravityClassifier, extract_keywords
from core.skills.models import GravityLevel


@pytest.mark.unit
class TestGravityClassifier:
    @pytest.fixture
    def classifier(self):
        return GravityClassifier()

    # --- Light tasks ---
    def test_typo_in_readme(self, classifier):
        result = classifier.assess("Fix the typo in README.md")
        assert result.gravity == GravityLevel.LIGHT

    def test_add_log_statement(self, classifier):
        result = classifier.assess("Add a debug log in processOrder")
        assert result.gravity == GravityLevel.LIGHT

    def test_update_gitignore(self, classifier):
        result = classifier.assess("Add node_modules to .gitignore")
        assert result.gravity == GravityLevel.LIGHT

    # --- Standard tasks ---
    def test_new_api_endpoint(self, classifier):
        result = classifier.assess("Build a REST endpoint for listing user projects with pagination")
        assert result.gravity == GravityLevel.STANDARD

    def test_react_component(self, classifier):
        result = classifier.assess("Create a React component for user settings with form validation")
        assert result.gravity == GravityLevel.STANDARD

    # --- Intensive tasks ---
    def test_jwt_auth(self, classifier):
        result = classifier.assess("Implement JWT authentication with refresh token rotation")
        assert result.gravity == GravityLevel.INTENSIVE

    def test_database_migration(self, classifier):
        result = classifier.assess("Create a migration to split users into users and profiles tables")
        assert result.gravity == GravityLevel.INTENSIVE

    def test_payment_processing(self, classifier):
        result = classifier.assess("Integrate Stripe payment processing for subscriptions")
        assert result.gravity == GravityLevel.INTENSIVE

    def test_rate_limiter(self, classifier):
        result = classifier.assess("Build a rate limiter that must handle 10k rps with zero data loss")
        assert result.gravity == GravityLevel.INTENSIVE

    def test_encryption(self, classifier):
        result = classifier.assess("Implement AES-256 encryption for user PII at rest")
        assert result.gravity == GravityLevel.INTENSIVE

    # --- Edge cases ---
    def test_domain_floor_overrides_casual(self, classifier):
        result = classifier.assess("Just get OAuth working, dont overthink it")
        assert result.gravity != GravityLevel.LIGHT

    def test_typo_in_migration_not_light(self, classifier):
        result = classifier.assess("Fix a typo in the SQL migration for payments table")
        assert result.gravity != GravityLevel.LIGHT

    def test_ambiguous_defaults_to_standard(self, classifier):
        result = classifier.assess("Fix the thing in the module")
        assert result.gravity == GravityLevel.STANDARD

    def test_user_override_always_wins(self, classifier):
        result = classifier.assess("Update README", user_override=GravityLevel.INTENSIVE)
        assert result.gravity == GravityLevel.INTENSIVE
        assert result.confidence == 1.0
        assert result.method == "user_override"

    # --- Signal structure ---
    def test_assessment_has_signals(self, classifier):
        result = classifier.assess("Implement payment gateway")
        assert len(result.signals) == 5
        assert result.reasoning

    def test_assessment_has_confidence(self, classifier):
        result = classifier.assess("Fix typo")
        assert 0.0 <= result.confidence <= 1.0


@pytest.mark.unit
class TestExtractKeywords:
    def test_removes_stop_words(self):
        kws = extract_keywords("the quick brown fox jumps over the lazy dog")
        assert "the" not in kws
        assert "over" not in kws
        assert "quick" in kws

    def test_lowercases(self):
        kws = extract_keywords("Build REST Endpoint")
        assert all(kw == kw.lower() for kw in kws)

    def test_unique(self):
        kws = extract_keywords("test test test duplicate duplicate")
        assert len(set(kws)) == len(kws)
