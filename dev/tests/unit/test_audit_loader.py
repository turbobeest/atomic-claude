"""Tests for audit catalog loader."""

import csv
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from core.graph.audit_loader import (
    _parse_csv_phases,
    _parse_yaml_file,
    _load_csv_lookup,
    query_audits,
    get_audit_stats,
    AUDITS_DIR,
    INVENTORY_CSV,
)


@pytest.fixture
def sample_audit_yaml(tmp_path):
    """Create a sample audit YAML file for testing."""
    audit_data = {
        "audit": {
            "id": "security-trust.secrets-management.hardcoded-secrets",
            "name": "Hardcoded Secrets Audit",
            "version": "1.0.0",
            "status": "active",
            "category": "security-trust",
            "category_number": 1,
            "subcategory": "secrets-management",
            "tier": "phd",
            "estimated_duration": "1.5 hours",
            "completeness": "complete",
            "requires_runtime": False,
            "destructive": False,
        },
        "execution": {
            "automatable": "yes",
            "severity": "critical",
            "scope": "codebase",
            "blocks_phase": True,
            "parallelizable": True,
        },
        "description": {
            "what": "Scans source code for hardcoded secrets including API keys.",
            "why_it_matters": "Hardcoded secrets are a critical vulnerability.",
            "when_to_run": ["On every commit", "During CI/CD"],
        },
        "signals": {
            "critical": [
                {"id": "SEC-CRIT-001", "signal": "AWS key in code"},
                {"id": "SEC-CRIT-002", "signal": "Private key in source"},
            ],
            "high": [
                {"id": "SEC-HIGH-001", "signal": "Hardcoded password"},
            ],
        },
        "relationships": {
            "commonly_combined": [
                "security-trust.secrets-management.secret-storage",
            ],
        },
        "governance": {
            "compliance_frameworks": [
                {"framework": "CWE", "controls": ["CWE-798"]},
                {"framework": "OWASP Top 10", "controls": ["A02:2021"]},
            ],
        },
    }

    yaml_path = tmp_path / "01-security-trust" / "secrets-management"
    yaml_path.mkdir(parents=True)
    file_path = yaml_path / "hardcoded-secrets.yaml"
    with open(file_path, "w") as f:
        yaml.dump(audit_data, f)
    return file_path


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample AUDIT-INVENTORY.csv for testing."""
    csv_path = tmp_path / "AUDIT-INVENTORY.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "audit_id", "file_path", "audit_name", "category",
            "category_number", "subcategory", "tier", "status",
            "automatable", "severity", "estimated_duration",
            "requires_runtime", "requires_physical_access",
            "requires_human_evaluation", "requires_interviews",
            "discovery", "prd", "task_decomposition", "specification",
            "implementation", "testing", "integration", "deployment",
            "post_production",
        ])
        writer.writerow([
            "security-trust.secrets-management.hardcoded-secrets",
            "audits/01-security-trust/secrets-management/hardcoded-secrets.yaml",
            "Hardcoded Secrets Audit", "security-trust", "1",
            "secrets-management", "phd", "active", "yes", "critical",
            "1.5 hours", "false", "false", "false", "false",
            "No", "No", "No", "Yes", "Yes", "Yes", "Yes", "Yes", "Yes",
        ])
    return csv_path


@pytest.mark.unit
class TestParseYaml:
    """Test YAML parsing of audit files."""

    def test_parse_valid_yaml(self, sample_audit_yaml):
        result = _parse_yaml_file(sample_audit_yaml)
        assert result is not None
        assert result["id"] == "security-trust.secrets-management.hardcoded-secrets"
        assert result["name"] == "Hardcoded Secrets Audit"
        assert result["category"] == "security-trust"
        assert result["subcategory"] == "secrets-management"
        assert result["tier"] == "phd"
        assert result["severity"] == "critical"
        assert result["automatable"] == "yes"
        assert result["blocks_phase"] is True

    def test_parse_descriptions(self, sample_audit_yaml):
        result = _parse_yaml_file(sample_audit_yaml)
        assert "hardcoded secrets" in result["description_what"].lower()
        assert "critical vulnerability" in result["description_why"].lower()

    def test_parse_signal_counts(self, sample_audit_yaml):
        result = _parse_yaml_file(sample_audit_yaml)
        assert result["signal_count_critical"] == 2
        assert result["signal_count_high"] == 1

    def test_parse_commonly_combined(self, sample_audit_yaml):
        result = _parse_yaml_file(sample_audit_yaml)
        assert "secret-storage" in result["commonly_combined"]

    def test_parse_compliance_frameworks(self, sample_audit_yaml):
        result = _parse_yaml_file(sample_audit_yaml)
        assert "CWE" in result["compliance_frameworks"]
        assert "OWASP Top 10" in result["compliance_frameworks"]

    def test_parse_nonexistent_file(self, tmp_path):
        result = _parse_yaml_file(tmp_path / "nonexistent.yaml")
        assert result is None

    def test_parse_invalid_yaml(self, tmp_path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text(": invalid: yaml: {{")
        result = _parse_yaml_file(bad_file)
        assert result is None

    def test_parse_yaml_without_audit_key(self, tmp_path):
        no_audit = tmp_path / "no-audit.yaml"
        with open(no_audit, "w") as f:
            yaml.dump({"something_else": True}, f)
        result = _parse_yaml_file(no_audit)
        assert result is None


@pytest.mark.unit
class TestParseCsvPhases:
    """Test SDLC phase extraction from CSV rows."""

    def test_all_phases(self):
        row = {
            "discovery": "Yes", "prd": "Yes", "task_decomposition": "Yes",
            "specification": "Yes", "implementation": "Yes", "testing": "Yes",
            "integration": "Yes", "deployment": "Yes", "post_production": "Yes",
        }
        result = _parse_csv_phases(row)
        assert "discovery" in result
        assert "implementation" in result
        assert result.count(",") == 8

    def test_partial_phases(self):
        row = {
            "discovery": "No", "prd": "No", "task_decomposition": "No",
            "specification": "Yes", "implementation": "Yes", "testing": "Yes",
            "integration": "No", "deployment": "No", "post_production": "No",
        }
        result = _parse_csv_phases(row)
        assert "specification" in result
        assert "implementation" in result
        assert "testing" in result
        assert "discovery" not in result

    def test_empty_row(self):
        result = _parse_csv_phases({})
        assert result == ""


@pytest.mark.unit
class TestQueryAudits:
    """Test audit query functions."""

    def test_query_with_filters(self):
        mock_graph = MagicMock()
        mock_graph.reader.get_nodes.return_value = [
            {"id": "test-1", "category": "security-trust", "severity": "critical"},
        ]
        results = query_audits(mock_graph, category="security-trust")
        assert len(results) == 1
        mock_graph.reader.get_nodes.assert_called_once()

    def test_query_with_search(self):
        mock_graph = MagicMock()
        mock_graph.reader.fulltext_search.return_value = [
            {"id": "test-1", "name": "Secret Audit", "sdlc_phases": "implementation,testing"},
        ]
        results = query_audits(mock_graph, search="secrets")
        assert len(results) == 1

    def test_query_with_sdlc_phase_filter(self):
        mock_graph = MagicMock()
        mock_graph.reader.get_nodes.return_value = [
            {"id": "a1", "sdlc_phases": "implementation,testing"},
            {"id": "a2", "sdlc_phases": "discovery,prd"},
        ]
        results = query_audits(mock_graph, sdlc_phase="implementation")
        assert len(results) == 1
        assert results[0]["id"] == "a1"

    def test_get_audit_stats_empty(self):
        mock_graph = MagicMock()
        mock_graph.reader.count_nodes.return_value = 0
        stats = get_audit_stats(mock_graph)
        assert stats["total"] == 0
        assert stats["loaded"] is False


@pytest.mark.unit
class TestCsvLookup:
    """Test CSV inventory loading."""

    def test_load_csv_lookup(self, sample_csv):
        with patch("core.graph.audit_loader.INVENTORY_CSV", sample_csv):
            lookup = _load_csv_lookup()
            assert len(lookup) == 1
            assert "security-trust.secrets-management.hardcoded-secrets" in lookup

    def test_load_csv_lookup_missing_file(self, tmp_path):
        with patch("core.graph.audit_loader.INVENTORY_CSV", tmp_path / "nope.csv"):
            lookup = _load_csv_lookup()
            assert lookup == {}


@pytest.mark.unit
class TestRealAuditFiles:
    """Test against real audit YAML files if present."""

    @pytest.mark.skipif(
        not AUDITS_DIR.exists() or not list(AUDITS_DIR.glob("**/*.yaml")),
        reason="Audit YAML files not present",
    )
    def test_parse_real_audit_file(self):
        """Parse first available real audit YAML."""
        yaml_files = sorted(AUDITS_DIR.glob("**/*.yaml"))
        yaml_files = [f for f in yaml_files if not f.name.startswith("._")]
        assert len(yaml_files) > 0

        result = _parse_yaml_file(yaml_files[0])
        assert result is not None
        assert result["id"] != ""
        assert result["name"] != ""
        assert result["category"] != ""
        assert result["tier"] in ("focused", "expert", "phd")

    @pytest.mark.skipif(
        not INVENTORY_CSV.exists(),
        reason="AUDIT-INVENTORY.csv not present",
    )
    def test_csv_lookup_has_entries(self):
        lookup = _load_csv_lookup()
        assert len(lookup) > 2000, f"Expected 2000+ entries, got {len(lookup)}"
