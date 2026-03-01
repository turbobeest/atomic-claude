"""
Unit Tests for Core Audit System (LLM-driven)

Tests CSV loading, phase filtering, LLM invocation, response parsing,
report saving, backward-compat wrappers, agent assignment, per-audit
evaluation, parallel execution, and remediation loop.
"""

import json
import pytest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.audit import (
    run_audit,
    select_audit,
    run_phase_audit,
    AuditManager,
    AuditConfig,
    AuditEvaluation,
    _load_audit_inventory,
    _select_audits_for_phase,
    _curate_audit_selection,
    _build_audit_roster,
    _parse_curation_response,
    _gather_deliverables,
    _build_audit_prompt,
    _parse_audit_response,
    _load_agent_manifest,
    _assign_agent,
    _build_audit_configs,
    _get_provider_default_tier,
    _build_single_audit_prompt,
    _parse_single_audit_response,
    _extract_verdict,
    _evaluate_worker,
    _run_parallel_evaluations,
    _display_rich_results,
    _remediation_loop,
    _synthesize_findings,
    _extract_remediation_guidance,
    _build_remediation_prompt,
    _parse_remediation_response,
    _apply_remediation,
    _auto_remediate,
    PHASE_CSV_COLUMN,
    MAX_AUDITS,
    AUDIT_AGENT_MAP,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_csv(tmp_path: Path, rows: list[dict]) -> Path:
    """Write a minimal AUDIT-INVENTORY.csv and return its path."""
    csv_dir = tmp_path / "audits"
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = csv_dir / "AUDIT-INVENTORY.csv"

    # Build header from PHASE_CSV_COLUMN values + fixed fields
    phase_cols = list(PHASE_CSV_COLUMN.values())
    header = ["audit_id", "audit_name", "severity", "category", "subcategory", "tier"] + phase_cols
    lines = [",".join(header)]
    for r in rows:
        line = ",".join(r.get(h, "") for h in header)
        lines.append(line)
    csv_path.write_text("\n".join(lines))
    return csv_path


def _sample_rows(phase_col: str = "discovery", count: int = 3) -> list[dict]:
    """Generate sample audit rows applicable to a given phase column."""
    severities = ["critical", "high", "medium"]
    rows = []
    for i in range(count):
        row = {
            "audit_id": f"test-audit-{i+1}",
            "audit_name": f"Test Audit {i+1}",
            "severity": severities[i % len(severities)],
            "category": "security-trust",
            "subcategory": "application-security",
            "tier": "expert",
            phase_col: "Yes",
        }
        rows.append(row)
    return rows


def _llm_json_response(results: list[dict]) -> str:
    """Return a JSON string like the LLM would produce."""
    return json.dumps(results)


def _make_audit_dict(**overrides) -> dict:
    """Create a standard audit dict with optional overrides."""
    base = {
        "audit_id": "test-1",
        "audit_name": "Test Audit",
        "severity": "high",
        "category": "security-trust",
        "subcategory": "application-security",
        "tier": "expert",
    }
    base.update(overrides)
    return base


def _make_eval(**overrides) -> AuditEvaluation:
    """Create a standard AuditEvaluation with optional overrides."""
    defaults = dict(
        audit_id="test-1",
        audit_name="Test Audit",
        category="security-trust",
        severity="high",
        tier="expert",
        status="pass",
        model_used="sonnet",
        agent_used="code-reviewer",
        provider_used="anthropic",
        analysis="Analysis text",
        evidence="Evidence text",
        gaps="",
        recommendations="",
        confidence="high",
        duration_seconds=2.5,
    )
    defaults.update(overrides)
    return AuditEvaluation(**defaults)


# ---------------------------------------------------------------------------
# CSV LOADING
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLoadAuditInventory:
    """Test _load_audit_inventory."""

    def test_loads_csv(self, temp_dir):
        """Load rows from a well-formed CSV."""
        rows = _sample_rows("discovery", 2)
        _make_csv(temp_dir, rows)

        with patch("core.audit._ATOMIC_ROOT", temp_dir):
            loaded = _load_audit_inventory()

        assert len(loaded) == 2
        assert loaded[0]["audit_id"] == "test-audit-1"

    def test_missing_csv_returns_empty(self, temp_dir):
        """Return [] when CSV does not exist."""
        with patch("core.audit._ATOMIC_ROOT", temp_dir):
            loaded = _load_audit_inventory()
        assert loaded == []


# ---------------------------------------------------------------------------
# PHASE FILTERING
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSelectAuditsForPhase:
    """Test _select_audits_for_phase."""

    def test_filters_by_phase_column(self):
        """Only audits with 'Yes' in the phase column are selected."""
        rows = [
            {"audit_id": "a1", "severity": "high", "discovery": "Yes"},
            {"audit_id": "a2", "severity": "high", "discovery": "No"},
            {"audit_id": "a3", "severity": "high", "discovery": "Yes"},
        ]
        result = _select_audits_for_phase(rows, 1)
        assert [r["audit_id"] for r in result] == ["a1", "a3"]

    def test_sorts_by_severity(self):
        """Critical before high before medium before low."""
        rows = [
            {"audit_id": "low", "severity": "low", "prd": "Yes"},
            {"audit_id": "crit", "severity": "critical", "prd": "Yes"},
            {"audit_id": "med", "severity": "medium", "prd": "Yes"},
            {"audit_id": "high", "severity": "high", "prd": "Yes"},
        ]
        result = _select_audits_for_phase(rows, 2)
        assert [r["audit_id"] for r in result] == ["crit", "high", "med", "low"]

    def test_returns_all_applicable(self):
        """Returns all applicable audits (cap applied later in run_phase_audit)."""
        rows = [
            {"audit_id": f"a{i}", "severity": "medium", "discovery": "Yes"}
            for i in range(MAX_AUDITS + 10)
        ]
        result = _select_audits_for_phase(rows, 1)
        assert len(result) == MAX_AUDITS + 10

    def test_phase_0_returns_empty(self):
        """Phase 0 has no CSV column — returns empty list."""
        rows = [{"audit_id": "a1", "severity": "high", "discovery": "Yes"}]
        result = _select_audits_for_phase(rows, 0)
        assert result == []

    def test_unknown_phase_returns_empty(self):
        """Phase 99 has no CSV column — returns empty list."""
        result = _select_audits_for_phase([], 99)
        assert result == []


# ---------------------------------------------------------------------------
# CURATION HELPERS
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildAuditRoster:
    """Test _build_audit_roster."""

    def test_builds_one_line_per_audit(self):
        audits = [
            {"audit_id": "sec-1", "audit_name": "SQL Injection", "severity": "critical", "category": "security"},
            {"audit_id": "qual-1", "audit_name": "Code Coverage", "severity": "medium", "category": "quality"},
        ]
        roster = _build_audit_roster(audits)
        lines = roster.strip().split("\n")
        assert len(lines) == 2
        assert "sec-1" in lines[0]
        assert "SQL Injection" in lines[0]
        assert "qual-1" in lines[1]


@pytest.mark.unit
class TestParseCurationResponse:
    """Test _parse_curation_response."""

    def test_valid_json(self):
        resp = json.dumps({"selected": ["a1", "a2"], "rationale": "Good coverage."})
        ids, rationale = _parse_curation_response(resp)
        assert ids == ["a1", "a2"]
        assert "coverage" in rationale

    def test_markdown_fenced(self):
        resp = '```json\n{"selected": ["x1"], "rationale": "ok"}\n```'
        ids, rationale = _parse_curation_response(resp)
        assert ids == ["x1"]

    def test_malformed_returns_empty(self):
        ids, rationale = _parse_curation_response("not json at all")
        assert ids == []
        assert rationale == ""

    def test_empty_selected_returns_empty(self):
        resp = json.dumps({"selected": [], "rationale": "none"})
        ids, _ = _parse_curation_response(resp)
        assert ids == []


# ---------------------------------------------------------------------------
# CURATE AUDIT SELECTION
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCurateAuditSelection:
    """Test _curate_audit_selection."""

    def _make_audits(self, count=5):
        return [
            {
                "audit_id": f"a{i}",
                "audit_name": f"Audit {i}",
                "severity": "high",
                "category": f"cat-{i % 3}",
            }
            for i in range(1, count + 1)
        ]

    def test_empty_audits_returns_empty(self):
        result = _curate_audit_selection([], "deliverables", 1, "1-discovery")
        assert result == []

    @patch("core.utils.cli_ui.clear_input_buffer")
    @patch("core.utils.cli_ui.prompt_user", return_value="")
    @patch("core.llm.invoke.invoke_llm")
    def test_llm_recommends_user_accepts(self, mock_llm, _prompt, _clear):
        """LLM recommends subset, user presses enter to accept."""
        audits = self._make_audits(5)
        mock_llm.return_value = json.dumps({
            "selected": ["a1", "a3", "a5"],
            "rationale": "Multi-domain coverage.",
        })
        result = _curate_audit_selection(audits, "deliverables", 1, "1-discovery")
        assert len(result) == 3
        assert [a["audit_id"] for a in result] == ["a1", "a3", "a5"]

    @patch("core.utils.cli_ui.clear_input_buffer")
    @patch("core.utils.cli_ui.prompt_user", return_value="1,3")
    @patch("core.llm.invoke.invoke_llm")
    def test_user_overrides_with_numbers(self, mock_llm, _prompt, _clear):
        """User picks specific audits by number from the displayed list."""
        audits = self._make_audits(5)
        mock_llm.return_value = json.dumps({
            "selected": ["a1", "a2", "a3"],
            "rationale": "Reason.",
        })
        result = _curate_audit_selection(audits, "deliverables", 1, "1-discovery")
        # User picked items 1 and 3 from the LLM's 3-item recommendation
        assert len(result) == 2

    @patch("core.utils.cli_ui.clear_input_buffer")
    @patch("core.utils.cli_ui.prompt_user", return_value="all")
    @patch("core.llm.invoke.invoke_llm")
    def test_user_types_all(self, mock_llm, _prompt, _clear):
        """User types 'all' returns curated selection, not full pool."""
        audits = self._make_audits(5)
        mock_llm.return_value = json.dumps({
            "selected": ["a1"],
            "rationale": "Just one.",
        })
        result = _curate_audit_selection(audits, "deliverables", 1, "1-discovery")
        # "all" now returns the curated selection, not the full pool
        assert len(result) == 1
        assert result[0]["audit_id"] == "a1"

    @patch("core.utils.cli_ui.clear_input_buffer")
    @patch("core.utils.cli_ui.prompt_user", return_value="skip")
    @patch("core.llm.invoke.invoke_llm")
    def test_user_types_skip(self, mock_llm, _prompt, _clear):
        """User types 'skip' to skip audits entirely."""
        audits = self._make_audits(5)
        mock_llm.return_value = json.dumps({
            "selected": ["a1"],
            "rationale": "One.",
        })
        result = _curate_audit_selection(audits, "deliverables", 1, "1-discovery")
        assert result == []

    @patch("core.utils.cli_ui.clear_input_buffer")
    @patch("core.utils.cli_ui.prompt_user", return_value="skip")
    @patch("core.llm.invoke.invoke_llm", side_effect=RuntimeError("No provider"))
    def test_llm_failure_falls_back_to_manual(self, _llm, _prompt, _clear):
        """LLM failure → falls back to _fallback_category_selection."""
        audits = self._make_audits(3)
        # Fallback prompts user, who types "skip"
        result = _curate_audit_selection(audits, "deliverables", 1, "1-discovery")
        assert result == []

    @patch("core.utils.cli_ui.clear_input_buffer")
    @patch("core.utils.cli_ui.prompt_user", return_value="")
    @patch("core.llm.invoke.invoke_llm")
    def test_llm_returns_bad_ids_falls_back(self, mock_llm, _prompt, _clear):
        """LLM returns IDs that don't match any audit → fallback."""
        audits = self._make_audits(3)
        mock_llm.return_value = json.dumps({
            "selected": ["nonexistent-1", "nonexistent-2"],
            "rationale": "Bad IDs.",
        })
        # Fallback shows category table, user accepts all with enter
        result = _curate_audit_selection(audits, "deliverables", 1, "1-discovery")
        assert result == audits  # fallback default is all


# ---------------------------------------------------------------------------
# GATHER DELIVERABLES
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGatherDeliverables:
    """Test _gather_deliverables."""

    def test_reads_md_and_json(self, temp_dir):
        """Picks up .md and .json files."""
        out = temp_dir / "outputs"
        out.mkdir()
        (out / "readme.md").write_text("# Hello")
        (out / "data.json").write_text('{"key": 1}')
        (out / "image.png").write_bytes(b"\x89PNG")  # should be skipped

        text = _gather_deliverables(out)
        assert "Hello" in text
        assert '"key"' in text
        assert "PNG" not in text

    def test_nonexistent_dir(self, temp_dir):
        """Returns placeholder for missing directory."""
        text = _gather_deliverables(temp_dir / "nope")
        assert "No deliverables" in text

    def test_empty_dir(self, temp_dir):
        """Returns placeholder when dir exists but has no matching files."""
        out = temp_dir / "empty"
        out.mkdir()
        text = _gather_deliverables(out)
        assert "No deliverables" in text

    def test_respects_max_chars(self, temp_dir):
        """Truncates when deliverables exceed max_chars."""
        out = temp_dir / "big"
        out.mkdir()
        (out / "big.txt").write_text("x" * 10_000)
        text = _gather_deliverables(out, max_chars=500)
        assert len(text) <= 600  # some overhead for header + truncation marker


# ---------------------------------------------------------------------------
# PROMPT BUILDING (legacy batch prompt)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildAuditPrompt:
    """Test _build_audit_prompt."""

    def test_includes_audit_criteria(self):
        audits = [
            {"audit_id": "sec-1", "severity": "critical", "audit_name": "SQL Injection"},
            {"audit_id": "sec-2", "severity": "high", "audit_name": "XSS"},
        ]
        prompt = _build_audit_prompt(audits, "some code", 5, "5-implementation")
        assert "sec-1" in prompt
        assert "SQL Injection" in prompt
        assert "Phase 5" in prompt

    def test_includes_deliverables(self):
        audits = [{"audit_id": "a1", "severity": "low", "audit_name": "Test"}]
        prompt = _build_audit_prompt(audits, "MY_DELIVERABLE_CONTENT", 1, "1-discovery")
        assert "MY_DELIVERABLE_CONTENT" in prompt


# ---------------------------------------------------------------------------
# RESPONSE PARSING (legacy batch parse)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestParseAuditResponse:
    """Test _parse_audit_response."""

    def test_valid_json(self):
        """Parse well-formed JSON array."""
        results = [
            {"audit_id": "a1", "status": "pass", "finding": "OK"},
            {"audit_id": "a2", "status": "fail", "finding": "Missing"},
        ]
        parsed = _parse_audit_response(json.dumps(results), [])
        assert len(parsed) == 2
        assert parsed[0]["status"] == "pass"
        assert parsed[1]["status"] == "fail"

    def test_markdown_wrapped_json(self):
        """Parse JSON wrapped in ```json ... ``` fences."""
        results = [{"audit_id": "a1", "status": "warn", "finding": "Maybe"}]
        raw = "```json\n" + json.dumps(results) + "\n```"
        parsed = _parse_audit_response(raw, [])
        assert len(parsed) == 1
        assert parsed[0]["status"] == "warn"

    def test_malformed_response_falls_back(self):
        """Malformed response → all audits marked warn."""
        audits = [
            {"audit_id": "a1"},
            {"audit_id": "a2"},
        ]
        parsed = _parse_audit_response("this is not json", audits)
        assert len(parsed) == 2
        assert all(r["status"] == "warn" for r in parsed)
        assert "Could not parse" in parsed[0]["finding"]

    def test_empty_array_falls_back(self):
        """Empty JSON array → fallback to warn."""
        audits = [{"audit_id": "a1"}]
        parsed = _parse_audit_response("[]", audits)
        assert len(parsed) == 1
        assert parsed[0]["status"] == "warn"


# ---------------------------------------------------------------------------
# AUDIT CONFIG DATACLASS
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAuditConfig:
    """Test AuditConfig dataclass."""

    def test_defaults(self):
        cfg = AuditConfig(audit={"audit_id": "a1"})
        assert cfg.agent == ""
        assert cfg.model == "sonnet"
        assert cfg.provider == "anthropic"
        assert cfg.context_window == 200000
        assert cfg.effort == "max"
        assert cfg.enabled is True

    def test_custom_values(self):
        cfg = AuditConfig(
            audit={"audit_id": "a1"},
            agent="code-reviewer",
            model="opus",
            provider="bedrock",
            context_window=128000,
            effort="high",
            enabled=False,
        )
        assert cfg.model == "opus"
        assert cfg.provider == "bedrock"
        assert cfg.context_window == 128000
        assert cfg.enabled is False

    def test_mutable(self):
        """AuditConfig fields are mutable for TUI editing."""
        cfg = AuditConfig(audit={"audit_id": "a1"})
        cfg.model = "opus"
        cfg.enabled = False
        assert cfg.model == "opus"
        assert cfg.enabled is False


# ---------------------------------------------------------------------------
# AUDIT EVALUATION DATACLASS
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAuditEvaluation:
    """Test AuditEvaluation dataclass."""

    def test_construction(self):
        ev = _make_eval()
        assert ev.audit_id == "test-1"
        assert ev.status == "pass"
        assert ev.error is None

    def test_with_error(self):
        ev = _make_eval(status="warn", error="LLM timeout")
        assert ev.status == "warn"
        assert ev.error == "LLM timeout"


# ---------------------------------------------------------------------------
# AGENT ASSIGNMENT
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAssignAgent:
    """Test _assign_agent and _load_agent_manifest."""

    def test_loads_manifest(self):
        """Manifest loads successfully from disk."""
        # Clear cache
        import core.audit
        core.audit._agent_manifest_cache = None
        manifest = _load_agent_manifest()
        # Should return dict (possibly empty in test env, populated in real env)
        assert isinstance(manifest, dict)

    def test_assign_known_category(self):
        """Audit with known category maps to matching agent."""
        import core.audit
        core.audit._agent_manifest_cache = {
            "agents": [
                {"name": "security-auditor", "category": "security-compliance",
                 "subcategory": "app-sec", "composite_score": 9.0},
            ]
        }
        audit = _make_audit_dict(category="security-trust")
        agent = _assign_agent(audit)
        assert agent == "security-auditor"

    def test_assign_unknown_category_fallback(self):
        """Audit with unknown category falls back to default agent."""
        import core.audit
        core.audit._agent_manifest_cache = {"agents": []}
        audit = _make_audit_dict(category="nonexistent-category")
        agent = _assign_agent(audit)
        assert agent == "agent-quality-auditor"

    def test_assign_empty_manifest_fallback(self):
        """Empty manifest → fallback agent."""
        import core.audit
        core.audit._agent_manifest_cache = {"agents": []}
        audit = _make_audit_dict()
        agent = _assign_agent(audit)
        assert agent == "agent-quality-auditor"

    def test_subcategory_matching(self):
        """Agent with matching subcategory is preferred."""
        import core.audit
        core.audit._agent_manifest_cache = {
            "agents": [
                {"name": "generic-sec", "category": "security-compliance",
                 "subcategory": "general", "composite_score": 9.0},
                {"name": "app-sec-expert", "category": "security-compliance",
                 "subcategory": "application-security", "composite_score": 8.0},
            ]
        }
        audit = _make_audit_dict(
            category="security-trust",
            subcategory="application-security"
        )
        agent = _assign_agent(audit)
        assert agent == "app-sec-expert"

    def test_build_audit_configs(self):
        """_build_audit_configs creates configs with agent and provider-default model."""
        import core.audit
        core.audit._agent_manifest_cache = {
            "agents": [
                {"name": "sec-agent", "category": "security-compliance",
                 "subcategory": "", "composite_score": 9.0},
            ]
        }
        # Inject a known model config for predictable provider default
        core.audit._model_config_cache = {
            "provider_defaults": {
                "anthropic": {"tier": "opus"},
            }
        }
        audits = [
            _make_audit_dict(audit_id="a1", tier="expert"),
            _make_audit_dict(audit_id="a2", tier="phd"),
        ]
        with patch("core.audit._detect_default_provider", return_value="anthropic"):
            configs = _build_audit_configs(audits)
        assert len(configs) == 2
        # All audits use the same provider-default model
        assert configs[0].model == "opus"
        assert configs[1].model == "opus"
        assert configs[0].agent == "sec-agent"

    def test_get_provider_default_tier(self):
        """_get_provider_default_tier reads from config/models.json."""
        import core.audit
        core.audit._model_config_cache = {
            "provider_defaults": {
                "anthropic": {"tier": "opus"},
                "aws-bedrock": {"tier": "sonnet"},
                "ollama": {"tier": "large"},
            }
        }
        assert _get_provider_default_tier("anthropic") == "opus"
        assert _get_provider_default_tier("aws-bedrock") == "sonnet"
        assert _get_provider_default_tier("ollama") == "large"
        # Unknown provider falls back to "opus"
        assert _get_provider_default_tier("unknown") == "opus"

    def test_get_provider_default_tier_empty_config(self):
        """Falls back to 'opus' when config has no provider_defaults."""
        import core.audit
        core.audit._model_config_cache = {}
        assert _get_provider_default_tier("anthropic") == "opus"


# ---------------------------------------------------------------------------
# SINGLE AUDIT PROMPT + PARSE
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildSingleAuditPrompt:
    """Test _build_single_audit_prompt."""

    def test_contains_audit_metadata(self):
        cfg = AuditConfig(
            audit=_make_audit_dict(audit_name="SQL Injection Check"),
            agent="security-auditor",
            model="sonnet",
        )
        prompt = _build_single_audit_prompt(cfg, "deliverable text", 5, "5-impl")
        assert "SQL Injection Check" in prompt
        assert "security-auditor" in prompt
        assert "Phase 5" in prompt
        assert "deliverable text" in prompt

    def test_truncates_deliverables(self):
        cfg = AuditConfig(audit=_make_audit_dict(), agent="a")
        big_deliverables = "x" * 20000
        prompt = _build_single_audit_prompt(cfg, big_deliverables, 1, "1-disc")
        # Prompt should not include full 20K (capped at 12K)
        assert len(prompt) < 15000


@pytest.mark.unit
class TestParseSingleAuditResponse:
    """Test _parse_single_audit_response with free-form markdown."""

    def test_verdict_pass(self):
        cfg = AuditConfig(
            audit=_make_audit_dict(),
            agent="code-reviewer",
            model="sonnet",
        )
        response = (
            "# Analysis\n\nThe code looks good.\n\n"
            "## Findings\n\nNo issues found.\n\n"
            "VERDICT: PASS — All requirements met."
        )
        ev = _parse_single_audit_response(response, cfg)
        assert ev.status == "pass"
        assert "The code looks good" in ev.analysis
        assert ev.agent_used == "code-reviewer"
        assert ev.model_used == "sonnet"
        assert ev.error is None

    def test_verdict_fail(self):
        cfg = AuditConfig(audit=_make_audit_dict(), agent="a")
        response = (
            "# Architecture Review\n\nMultiple SRP violations found.\n\n"
            "VERDICT: FAIL — Critical coupling issues prevent clean separation."
        )
        ev = _parse_single_audit_response(response, cfg)
        assert ev.status == "fail"

    def test_verdict_warn_explicit(self):
        cfg = AuditConfig(audit=_make_audit_dict(), agent="a")
        response = "Some concerns noted.\n\nVERDICT: WARN — Minor gaps in documentation."
        ev = _parse_single_audit_response(response, cfg)
        assert ev.status == "warn"

    def test_no_verdict_defaults_to_warn(self):
        """When no VERDICT line is present, defaults to warn."""
        cfg = AuditConfig(audit=_make_audit_dict(), agent="a")
        response = "This is a long analysis with no explicit verdict line."
        ev = _parse_single_audit_response(response, cfg)
        assert ev.status == "warn"

    def test_full_markdown_stored_in_analysis(self):
        """The entire markdown response is stored in the analysis field."""
        cfg = AuditConfig(audit=_make_audit_dict(), agent="a")
        response = "# Full Report\n\nDetailed analysis here.\n\nVERDICT: PASS — OK"
        ev = _parse_single_audit_response(response, cfg)
        assert ev.analysis == response.strip()

    def test_heuristic_pass(self):
        """Heuristic: 'no issues' signals pass when no VERDICT line."""
        cfg = AuditConfig(audit=_make_audit_dict(), agent="a")
        response = "After thorough review, no issues were identified."
        ev = _parse_single_audit_response(response, cfg)
        assert ev.status == "pass"

    def test_heuristic_fail(self):
        """Heuristic: 'critical' + 'missing' signals fail when no VERDICT line."""
        cfg = AuditConfig(audit=_make_audit_dict(), agent="a")
        response = "Critical requirements are missing from this deliverable. This is a failure."
        ev = _parse_single_audit_response(response, cfg)
        assert ev.status == "fail"


# ---------------------------------------------------------------------------
# EVALUATE WORKER
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEvaluateWorker:
    """Test _evaluate_worker."""

    @patch("core.llm.invoke.invoke_llm")
    def test_success(self, mock_llm):
        """Successful evaluation returns populated AuditEvaluation."""
        mock_llm.return_value = (
            "# Test Audit\n\nLooks good.\n\n"
            "VERDICT: PASS — All requirements met."
        )
        cfg = AuditConfig(
            audit=_make_audit_dict(audit_id="a1", audit_name="Test"),
            agent="code-reviewer",
            model="sonnet",
        )
        ev = _evaluate_worker(cfg, "deliverables", 1, "1-disc")
        assert ev.status == "pass"
        assert ev.audit_id == "a1"
        assert ev.duration_seconds > 0

    @patch("core.llm.invoke.invoke_llm", side_effect=RuntimeError("No provider"))
    def test_llm_exception_returns_warn(self, _mock):
        """LLM exception → warn evaluation with error message."""
        cfg = AuditConfig(
            audit=_make_audit_dict(audit_id="a1"),
            agent="a",
            model="sonnet",
        )
        ev = _evaluate_worker(cfg, "deliverables", 1, "1-disc")
        assert ev.status == "warn"
        assert "No provider" in ev.error
        assert ev.duration_seconds >= 0

    @patch("core.llm.invoke.invoke_llm")
    def test_model_from_config(self, mock_llm):
        """Worker uses the model from audit_config."""
        mock_llm.return_value = "All good.\n\nVERDICT: PASS — OK"
        cfg = AuditConfig(
            audit=_make_audit_dict(),
            agent="a",
            model="opus",
        )
        _evaluate_worker(cfg, "deliverables", 1, "1-disc")
        call_kwargs = mock_llm.call_args
        assert call_kwargs.kwargs.get("model") == "opus"


# ---------------------------------------------------------------------------
# PARALLEL EVALUATIONS
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRunParallelEvaluations:
    """Test _run_parallel_evaluations."""

    @patch("core.audit._evaluate_worker")
    def test_returns_all_evaluations(self, mock_worker):
        """All configs produce evaluations, order preserved."""
        configs = [
            AuditConfig(audit=_make_audit_dict(audit_id=f"a{i}"), agent="a")
            for i in range(3)
        ]
        # Use a function side_effect so return matches input config
        def worker_side_effect(cfg, *args, **kwargs):
            aid = cfg.audit["audit_id"]
            status_map = {"a0": "pass", "a1": "warn", "a2": "fail"}
            return _make_eval(audit_id=aid, status=status_map.get(aid, "warn"))

        mock_worker.side_effect = worker_side_effect
        results = _run_parallel_evaluations(configs, "deliverables", 1, "1-disc")
        assert len(results) == 3
        # Order preserved (matching config order)
        assert results[0].audit_id == "a0"
        assert results[0].status == "pass"
        assert results[1].audit_id == "a1"
        assert results[1].status == "warn"
        assert results[2].audit_id == "a2"
        assert results[2].status == "fail"

    @patch("core.audit._evaluate_worker")
    def test_error_isolation(self, mock_worker):
        """One worker exception doesn't crash the batch."""
        configs = [
            AuditConfig(audit=_make_audit_dict(audit_id="a0"), agent="a"),
            AuditConfig(audit=_make_audit_dict(audit_id="a1"), agent="a"),
        ]
        def worker_side_effect(cfg, *args, **kwargs):
            aid = cfg.audit["audit_id"]
            if aid == "a0":
                return _make_eval(audit_id="a0", status="pass")
            return _make_eval(audit_id="a1", status="warn", error="boom")

        mock_worker.side_effect = worker_side_effect
        results = _run_parallel_evaluations(configs, "deliverables", 1, "1-disc")
        assert len(results) == 2
        assert results[0].status == "pass"
        assert results[1].status == "warn"


# ---------------------------------------------------------------------------
# AI REMEDIATION FUNCTIONS
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestExtractRemediationGuidance:
    """Test _extract_remediation_guidance."""

    def test_extracts_gaps_and_recommendations(self):
        """Extracts ## Gaps and ## Recommendations sections."""
        ev = _make_eval(
            status="fail",
            analysis=(
                "# Audit Report\n\n"
                "## Analysis\nSome analysis.\n\n"
                "## Gaps\nMissing error handling.\nNo input validation.\n\n"
                "## Recommendations\n1. Add try/except blocks.\n2. Validate inputs.\n\n"
                "VERDICT: FAIL — Critical gaps."
            ),
        )
        guidance = _extract_remediation_guidance([ev])
        assert "Missing error handling" in guidance
        assert "Add try/except" in guidance
        assert "FAIL" in guidance  # header includes status

    def test_extracts_numbered_headings(self):
        """Handles numbered heading style: ## 3. Gaps."""
        ev = _make_eval(
            status="warn",
            analysis=(
                "# Report\n\n"
                "## 1. Analysis\nStuff.\n\n"
                "## 3. Gaps\nNo tests for edge cases.\n\n"
                "## 4. Recommendations\nAdd unit tests.\n"
            ),
        )
        guidance = _extract_remediation_guidance([ev])
        assert "No tests for edge cases" in guidance
        assert "Add unit tests" in guidance

    def test_fallback_when_no_headings(self):
        """Falls back to last 1000 chars when no Gaps/Recommendations headings."""
        analysis = "A" * 500 + "important finding at end"
        ev = _make_eval(status="fail", analysis=analysis)
        guidance = _extract_remediation_guidance([ev])
        assert "important finding at end" in guidance

    def test_skips_passing_audits(self):
        """Only includes failed/warned audits, not passing ones."""
        pass_ev = _make_eval(audit_id="pass-1", status="pass", analysis="## Gaps\nNone.")
        fail_ev = _make_eval(audit_id="fail-1", status="fail", analysis="## Gaps\nBroken stuff.")
        guidance = _extract_remediation_guidance([pass_ev, fail_ev])
        assert "Broken stuff" in guidance
        assert "None." not in guidance

    def test_empty_evaluations(self):
        """Empty evaluations list returns empty string."""
        assert _extract_remediation_guidance([]) == ""

    def test_skips_empty_analysis(self):
        """Skips evaluations with empty analysis."""
        ev = _make_eval(status="fail", analysis="")
        assert _extract_remediation_guidance([ev]) == ""


@pytest.mark.unit
class TestBuildRemediationPrompt:
    """Test _build_remediation_prompt."""

    def test_includes_guidance_and_deliverables(self, temp_dir):
        prompt = _build_remediation_prompt(
            "## Gaps\nMissing tests.",
            "# PRD\nProject requirements.",
            temp_dir,
        )
        assert "Missing tests" in prompt
        assert "Project requirements" in prompt
        assert "=== FILE:" in prompt
        assert "=== END FILE ===" in prompt
        assert "=== SUMMARY ===" in prompt

    def test_includes_format_instructions(self, temp_dir):
        prompt = _build_remediation_prompt("guidance", "deliverables", temp_dir)
        assert "TODO" in prompt
        assert "Preserve correct existing content" in prompt


@pytest.mark.unit
class TestParseRemediationResponse:
    """Test _parse_remediation_response."""

    def test_single_file(self):
        response = (
            "=== FILE: prd.md ===\n"
            "# Updated PRD\nNew content.\n"
            "=== END FILE ===\n\n"
            "=== SUMMARY ===\nUpdated PRD with missing sections.\n=== END SUMMARY ==="
        )
        files, summary = _parse_remediation_response(response)
        assert "prd.md" in files
        assert "Updated PRD" in files["prd.md"]
        assert "Updated PRD with missing sections" in summary

    def test_multiple_files(self):
        response = (
            "=== FILE: file1.md ===\nContent 1\n=== END FILE ===\n"
            "=== FILE: sub/file2.json ===\n{\"key\": 1}\n=== END FILE ===\n"
            "=== SUMMARY ===\nFixed two files.\n=== END SUMMARY ==="
        )
        files, summary = _parse_remediation_response(response)
        assert len(files) == 2
        assert "file1.md" in files
        assert "sub/file2.json" in files
        assert "Fixed two files" in summary

    def test_empty_response(self):
        files, summary = _parse_remediation_response("")
        assert files == {}
        assert summary == ""

    def test_no_file_blocks(self):
        """Response with text but no FILE blocks returns empty."""
        files, summary = _parse_remediation_response("Just some text with no blocks.")
        assert files == {}

    def test_summary_only(self):
        response = "=== SUMMARY ===\nNothing to fix.\n=== END SUMMARY ==="
        files, summary = _parse_remediation_response(response)
        assert files == {}
        assert "Nothing to fix" in summary


@pytest.mark.unit
class TestApplyRemediation:
    """Test _apply_remediation."""

    def test_writes_files(self, temp_dir):
        """Writes file updates to disk."""
        out = temp_dir / "outputs"
        out.mkdir()
        (out / "existing.md").write_text("old content")

        updates = {
            "existing.md": "new content",
            "new-file.md": "brand new file",
        }
        changes = _apply_remediation(updates, out)
        assert len(changes) == 2

        assert (out / "existing.md").read_text() == "new content"
        assert (out / "new-file.md").read_text() == "brand new file"

        # Check size reporting
        existing_change = [c for c in changes if c[0] == "existing.md"][0]
        assert existing_change[1] == len("old content")  # old size
        assert existing_change[2] == len("new content")  # new size

    def test_rejects_path_traversal(self, temp_dir):
        """Rejects paths that escape output_dir."""
        out = temp_dir / "outputs"
        out.mkdir()
        updates = {"../secret.txt": "hacked"}
        changes = _apply_remediation(updates, out)
        assert len(changes) == 0
        assert not (temp_dir / "secret.txt").exists()

    def test_creates_subdirectories(self, temp_dir):
        """Creates parent directories for nested paths."""
        out = temp_dir / "outputs"
        out.mkdir()
        updates = {"sub/deep/file.md": "nested content"}
        changes = _apply_remediation(updates, out)
        assert len(changes) == 1
        assert (out / "sub" / "deep" / "file.md").read_text() == "nested content"

    def test_new_file_old_size_zero(self, temp_dir):
        """New files report old_size as 0."""
        out = temp_dir / "outputs"
        out.mkdir()
        updates = {"brand-new.md": "content"}
        changes = _apply_remediation(updates, out)
        assert changes[0][1] == 0  # old_size


@pytest.mark.unit
class TestAutoRemediate:
    """Test _auto_remediate end-to-end."""

    @patch("core.llm.invoke.invoke_llm")
    def test_success(self, mock_llm, temp_dir):
        """Successful remediation: LLM returns file updates, files written."""
        out = temp_dir / "outputs"
        out.mkdir()
        (out / "prd.md").write_text("# Old PRD")

        mock_llm.return_value = (
            "=== FILE: prd.md ===\n# Fixed PRD\nWith improvements.\n=== END FILE ===\n"
            "=== SUMMARY ===\nFixed PRD gaps.\n=== END SUMMARY ==="
        )

        evals = [_make_eval(
            status="fail",
            analysis="## Gaps\nPRD missing error handling section.",
        )]
        result = _auto_remediate(evals, out, 1, "1-discovery")
        assert result is True
        assert "Fixed PRD" in (out / "prd.md").read_text()

    @patch("core.llm.invoke.invoke_llm", side_effect=RuntimeError("No provider"))
    def test_llm_failure_returns_false(self, _mock, temp_dir):
        """LLM exception → returns False without raising."""
        out = temp_dir / "outputs"
        out.mkdir()
        evals = [_make_eval(
            status="fail",
            analysis="## Gaps\nSomething wrong.",
        )]
        result = _auto_remediate(evals, out, 1, "1-discovery")
        assert result is False

    def test_no_guidance_returns_false(self, temp_dir):
        """No actionable guidance (all passing) → returns False."""
        out = temp_dir / "outputs"
        out.mkdir()
        evals = [_make_eval(status="pass")]
        result = _auto_remediate(evals, out, 1, "1-discovery")
        assert result is False

    @patch("core.llm.invoke.invoke_llm")
    def test_llm_returns_no_files(self, mock_llm, temp_dir):
        """LLM returns text but no FILE blocks → returns False."""
        out = temp_dir / "outputs"
        out.mkdir()
        mock_llm.return_value = "I analyzed the issues but couldn't determine fixes."

        evals = [_make_eval(status="fail", analysis="## Gaps\nBroken.")]
        result = _auto_remediate(evals, out, 1, "1-discovery")
        assert result is False


# ---------------------------------------------------------------------------
# REMEDIATION LOOP
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRemediationLoop:
    """Test _remediation_loop."""

    def test_all_pass_skips(self, temp_dir):
        """All pass → returns immediately, no user prompt."""
        evals = [_make_eval(status="pass"), _make_eval(audit_id="a2", status="pass")]
        configs = [AuditConfig(audit=_make_audit_dict(audit_id="test-1"), agent="a")]
        result = _remediation_loop(evals, configs, 1, "1-disc", temp_dir)
        assert result == evals

    @patch("core.utils.cli_ui.prompt_menu", return_value="accept")
    def test_user_accepts(self, _menu, temp_dir):
        """User selects Accept → results returned as-is."""
        evals = [_make_eval(status="fail")]
        configs = [AuditConfig(audit=_make_audit_dict(), agent="a")]
        result = _remediation_loop(evals, configs, 1, "1-disc", temp_dir)
        assert len(result) == 1
        assert result[0].status == "fail"

    @patch("core.utils.cli_ui.prompt_menu", return_value="skip")
    def test_user_skips(self, _menu, temp_dir):
        """User selects Skip → evaluations unchanged."""
        evals = [_make_eval(status="warn")]
        configs = [AuditConfig(audit=_make_audit_dict(), agent="a")]
        result = _remediation_loop(evals, configs, 1, "1-disc", temp_dir)
        assert result[0].status == "warn"

    @patch("core.audit._save_audit_markdowns")
    @patch("core.audit._display_rich_results")
    @patch("core.audit._run_parallel_evaluations")
    @patch("core.audit._auto_remediate", return_value=True)
    @patch("core.utils.cli_ui.prompt_menu", side_effect=["remediate", "accept"])
    def test_user_reaudits(self, _menu, _auto_rem, mock_parallel,
                            _display, _save, temp_dir):
        """User selects Remediate → AI fixes, re-audit, then accepts."""
        evals = [_make_eval(audit_id="test-1", status="fail")]
        configs = [AuditConfig(audit=_make_audit_dict(audit_id="test-1"), agent="a")]

        # Re-evaluation returns pass
        mock_parallel.return_value = [_make_eval(audit_id="test-1", status="pass")]
        _save.return_value = temp_dir

        result = _remediation_loop(evals, configs, 1, "1-disc", temp_dir)
        assert result[0].status == "pass"
        assert mock_parallel.call_count == 1
        _auto_rem.assert_called_once()


# ---------------------------------------------------------------------------
# RUN PHASE AUDIT (main function — new pipeline)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRunPhaseAudit:
    """Test run_phase_audit end-to-end (with mocked pipeline stages)."""

    @patch("core.audit._load_audit_inventory", return_value=[])
    def test_empty_inventory(self, _mock, temp_dir, capsys):
        result = run_phase_audit(1, "1-discovery", temp_dir)
        assert result is True
        assert "not found or empty" in capsys.readouterr().out

    @patch("core.audit._load_audit_inventory")
    def test_no_applicable_audits(self, mock_load, temp_dir, capsys):
        mock_load.return_value = [
            {"audit_id": "a1", "severity": "high", "discovery": "No"},
        ]
        result = run_phase_audit(1, "1-discovery", temp_dir)
        assert result is True
        assert "No applicable" in capsys.readouterr().out

    @patch("core.audit._load_audit_inventory")
    def test_phase_0_no_column(self, mock_load, temp_dir, capsys):
        mock_load.return_value = [{"audit_id": "a1"}]
        result = run_phase_audit(0, "0-setup", temp_dir)
        assert result is True
        assert "No audit column" in capsys.readouterr().out

    @patch("core.audit._load_existing_evaluations", return_value=([], []))
    @patch("core.audit._remediation_loop",
           side_effect=lambda evals, *a, **kw: evals)
    @patch("core.audit._display_rich_results")
    @patch("core.audit._run_parallel_evaluations")
    @patch("core.audit._display_audit_plan",
           side_effect=lambda configs, phase_num: configs)
    @patch("core.audit._curate_audit_selection",
           side_effect=lambda a, d, pn, pid: a)
    @patch("core.audit._load_audit_inventory")
    def test_successful_audit(self, mock_load, _curation, _plan, mock_parallel,
                              _display, _remediation, _existing, temp_dir, capsys):
        """Full audit: CSV → filter → curation → plan → evaluate → report."""
        mock_load.return_value = [
            {"audit_id": "a1", "audit_name": "Test", "severity": "high",
             "category": "security-trust", "tier": "expert", "discovery": "Yes"},
            {"audit_id": "a2", "audit_name": "Test2", "severity": "medium",
             "category": "security-trust", "tier": "expert", "discovery": "Yes"},
        ]
        mock_parallel.return_value = [
            _make_eval(audit_id="a1", status="pass"),
            _make_eval(audit_id="a2", status="warn"),
        ]

        out = temp_dir / "outputs"
        out.mkdir()
        (out / "notes.md").write_text("# Phase notes")

        # _ATOMIC_ROOT.parent is used for .outputs/ — set _ATOMIC_ROOT to a
        # subdirectory so that .parent resolves back to temp_dir.
        atomic_subdir = temp_dir / "atomic"
        atomic_subdir.mkdir()
        with patch("core.audit._ATOMIC_ROOT", atomic_subdir):
            result = run_phase_audit(1, "1-discovery", out)

        assert result is True
        output = capsys.readouterr().out
        assert "WARNING" in output

        report_path = temp_dir / ".outputs" / "audits" / "phase-1" / "report.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text())
        assert report["phase_num"] == 1
        assert report["summary"]["passed"] == 1
        assert report["summary"]["warnings"] == 1
        assert report["overall_status"] == "WARNING"
        # Enhanced report has evaluations array
        assert "evaluations" in report
        assert len(report["evaluations"]) == 2
        # Backward-compat results array
        assert "results" in report
        assert len(report["results"]) == 2

    @patch("core.audit._load_existing_evaluations", return_value=([], []))
    @patch("core.audit._remediation_loop",
           side_effect=lambda evals, *a, **kw: evals)
    @patch("core.audit._display_rich_results")
    @patch("core.audit._run_parallel_evaluations")
    @patch("core.audit._display_audit_plan",
           side_effect=lambda configs, phase_num: configs)
    @patch("core.audit._curate_audit_selection",
           side_effect=lambda a, d, pn, pid: a)
    @patch("core.audit._load_audit_inventory")
    def test_all_pass(self, mock_load, _curation, _plan, mock_parallel,
                      _display, _remediation, _existing, temp_dir):
        """All pass → overall PASS."""
        mock_load.return_value = [
            {"audit_id": "a1", "audit_name": "T", "severity": "high",
             "category": "security-trust", "tier": "expert", "discovery": "Yes"},
        ]
        mock_parallel.return_value = [
            _make_eval(audit_id="a1", status="pass"),
        ]

        atomic_subdir = temp_dir / "atomic"
        atomic_subdir.mkdir()
        with patch("core.audit._ATOMIC_ROOT", atomic_subdir):
            run_phase_audit(1, "1-discovery", temp_dir)

        report = json.loads(
            (temp_dir / ".outputs" / "audits" / "phase-1" / "report.json").read_text()
        )
        assert report["overall_status"] == "PASS"

    @patch("core.audit._load_existing_evaluations", return_value=([], []))
    @patch("core.audit._remediation_loop",
           side_effect=lambda evals, *a, **kw: evals)
    @patch("core.audit._display_rich_results")
    @patch("core.audit._run_parallel_evaluations")
    @patch("core.audit._display_audit_plan",
           side_effect=lambda configs, phase_num: configs)
    @patch("core.audit._curate_audit_selection",
           side_effect=lambda a, d, pn, pid: a)
    @patch("core.audit._load_audit_inventory")
    def test_has_failure(self, mock_load, _curation, _plan, mock_parallel,
                         _display, _remediation, _existing, temp_dir):
        """Any fail → overall FAIL."""
        mock_load.return_value = [
            {"audit_id": "a1", "audit_name": "T", "severity": "high",
             "category": "security-trust", "tier": "expert", "discovery": "Yes"},
        ]
        mock_parallel.return_value = [
            _make_eval(audit_id="a1", status="fail"),
        ]

        atomic_subdir = temp_dir / "atomic"
        atomic_subdir.mkdir()
        with patch("core.audit._ATOMIC_ROOT", atomic_subdir):
            run_phase_audit(1, "1-discovery", temp_dir)

        report = json.loads(
            (temp_dir / ".outputs" / "audits" / "phase-1" / "report.json").read_text()
        )
        assert report["overall_status"] == "FAIL"

    @patch("core.audit._display_audit_plan",
           side_effect=lambda configs, phase_num: configs)
    @patch("core.audit._curate_audit_selection",
           side_effect=lambda a, d, pn, pid: a)
    @patch("core.audit._load_audit_inventory")
    def test_llm_exception_non_blocking(self, mock_load, _curation, _plan,
                                        temp_dir, capsys):
        """LLM failure in parallel eval → returns True, prints warning."""
        mock_load.return_value = [
            {"audit_id": "a1", "audit_name": "T", "severity": "high",
             "category": "security-trust", "tier": "expert", "discovery": "Yes"},
        ]
        with patch("core.audit._run_parallel_evaluations",
                    side_effect=RuntimeError("No provider")):
            result = run_phase_audit(1, "1-discovery", temp_dir)

        assert result is True
        assert "LLM audit failed" in capsys.readouterr().out

    @patch("core.audit._curate_audit_selection",
           side_effect=lambda a, d, pn, pid: a)
    @patch("core.audit._load_audit_inventory")
    def test_user_skips_plan(self, mock_load, _curation, temp_dir, capsys):
        """User skips in audit plan TUI → returns True."""
        mock_load.return_value = [
            {"audit_id": "a1", "audit_name": "T", "severity": "high",
             "category": "security-trust", "tier": "expert", "discovery": "Yes"},
        ]
        with patch("core.audit._display_audit_plan", return_value=[]):
            result = run_phase_audit(1, "1-discovery", temp_dir)

        assert result is True
        assert "skipped by user" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# BACKWARD-COMPATIBLE WRAPPERS
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRunAudit:
    """Test run_audit backward-compat wrapper."""

    @patch("core.audit.run_phase_audit", return_value=True)
    def test_delegates_to_run_phase_audit(self, mock_rpa, temp_dir):
        run_audit("whatever", "3-task_decomposition", temp_dir)
        mock_rpa.assert_called_once_with(3, "3-task_decomposition", temp_dir)

    def test_bad_phase_id(self, temp_dir, capsys):
        result = run_audit("test", "invalid", temp_dir)
        assert result is True
        assert "Could not parse" in capsys.readouterr().out


@pytest.mark.unit
class TestSelectAudit:
    """Test select_audit backward-compat wrapper."""

    def test_phase_0_returns_none(self, temp_dir):
        assert select_audit(0, temp_dir) is None

    def test_valid_phase_returns_name(self, temp_dir):
        assert select_audit(5, temp_dir) == "phase-5-audit"


# ---------------------------------------------------------------------------
# AUDIT MANAGER
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAuditManager:
    """Test AuditManager class."""

    def test_init(self, temp_dir):
        manager = AuditManager(atomic_root=temp_dir, output_dir=temp_dir / ".outputs")
        assert manager.atomic_root == temp_dir
        assert manager.output_dir == temp_dir / ".outputs"

    @patch("core.audit.run_phase_audit", return_value=True)
    def test_delegates(self, mock_rpa, temp_dir):
        manager = AuditManager(atomic_root=temp_dir, output_dir=temp_dir / "out")
        manager.run_phase_audit(2, "2-prd")
        mock_rpa.assert_called_once_with(2, "2-prd", temp_dir / "out")


# ---------------------------------------------------------------------------
# NON-BLOCKING BEHAVIOR
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestNonBlocking:
    """Every code path must return True."""

    @patch("core.audit._load_audit_inventory", return_value=[])
    def test_missing_csv(self, _m, temp_dir):
        assert run_phase_audit(1, "1-discovery", temp_dir) is True

    def test_phase_0(self, temp_dir):
        with patch("core.audit._load_audit_inventory", return_value=[{"audit_id": "a"}]):
            assert run_phase_audit(0, "0-setup", temp_dir) is True

    @patch("core.audit._display_audit_plan",
           side_effect=lambda configs, phase_num: configs)
    @patch("core.audit._curate_audit_selection",
           side_effect=lambda a, d, pn, pid: a)
    @patch("core.audit._run_parallel_evaluations",
           side_effect=Exception("boom"))
    @patch("core.audit._load_audit_inventory")
    def test_llm_failure(self, mock_load, _parallel, _curation, _plan, temp_dir):
        mock_load.return_value = [
            {"audit_id": "a1", "audit_name": "T", "severity": "high",
             "category": "security-trust", "tier": "expert", "discovery": "Yes"},
        ]
        assert run_phase_audit(1, "1-discovery", temp_dir) is True

    def test_run_audit_bad_phase_id(self, temp_dir):
        assert run_audit("x", "bogus", temp_dir) is True
