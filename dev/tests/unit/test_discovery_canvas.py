"""Tests for Discovery Canvas — PRD coverage tracker."""

import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from core.discovery.canvas import (
    CanvasState,
    PRD_SECTIONS,
    SECTION_IDS,
    SECTION_PROBES,
    render_canvas,
    render_canvas_compact,
    suggest_next_topic,
    classify_exchange,
    generate_prd_preview,
    _parse_classification,
)


# ============================================================================
# CanvasState Data Model Tests
# ============================================================================

@pytest.mark.unit
class TestCanvasState:

    def test_canvas_init_all_zeros(self):
        """Fresh CanvasState has 0.0 for all 12 sections."""
        canvas = CanvasState()
        assert len(canvas.scores) == 12
        for sid in SECTION_IDS:
            assert canvas.scores[sid] == 0.0

    def test_canvas_update_single_section(self):
        """Single classification updates one section score correctly."""
        canvas = CanvasState()
        canvas.update(1, {"vision": 0.8}, "We discussed the project vision")
        assert canvas.scores["vision"] == pytest.approx(0.4)  # 0.8 * (1-0) * 0.5
        assert canvas.scores["architecture"] == 0.0  # Unchanged
        assert len(canvas.evidence["vision"]) == 1
        assert canvas.evidence["vision"][0][0] == 1  # Turn number

    def test_canvas_diminishing_returns(self):
        """Repeated updates to same section approach but never exceed 1.0."""
        canvas = CanvasState()
        for i in range(20):
            canvas.update(i, {"vision": 0.9}, f"More vision discussion turn {i}")
        assert canvas.scores["vision"] < 1.0
        assert canvas.scores["vision"] > 0.8  # Should be high after 20 turns

    def test_canvas_multiple_sections(self):
        """Classification touching 3 sections updates all three."""
        canvas = CanvasState()
        canvas.update(1, {"vision": 0.9, "architecture": 0.5, "risks": 0.3},
                       "Discussed vision, some architecture, mentioned risks")
        assert canvas.scores["vision"] > 0.0
        assert canvas.scores["architecture"] > 0.0
        assert canvas.scores["risks"] > 0.0
        assert canvas.scores["features"] == 0.0  # Not mentioned

    def test_canvas_ignores_low_relevance(self):
        """Relevance < 0.1 does not update score."""
        canvas = CanvasState()
        canvas.update(1, {"vision": 0.05}, "Barely mentioned vision")
        assert canvas.scores["vision"] == 0.0

    def test_canvas_ignores_unknown_sections(self):
        """Unknown section IDs are silently ignored."""
        canvas = CanvasState()
        canvas.update(1, {"unknown_section": 0.9, "vision": 0.5}, "test")
        assert "unknown_section" not in canvas.scores
        assert canvas.scores["vision"] > 0.0


# ============================================================================
# Coverage Properties Tests
# ============================================================================

@pytest.mark.unit
class TestCoverageProperties:

    def test_overall_coverage_empty(self):
        """Fresh canvas has overall_coverage = 0.0."""
        canvas = CanvasState()
        assert canvas.overall_coverage == pytest.approx(0.0)

    def test_overall_coverage_partial(self):
        """6 sections at 0.5 gives overall_coverage = 0.25."""
        canvas = CanvasState()
        for sid in SECTION_IDS[:6]:
            canvas.scores[sid] = 0.5
        # 6 * 0.5 / 12 = 0.25
        assert canvas.overall_coverage == pytest.approx(0.25)

    def test_empty_sections_list(self):
        """Correctly identifies sections with score < 0.05."""
        canvas = CanvasState()
        canvas.scores["vision"] = 0.8
        canvas.scores["architecture"] = 0.04  # Below threshold, still empty
        empty = canvas.empty_sections
        assert "vision" not in empty
        assert "architecture" in empty
        assert len(empty) == 11  # All but vision

    def test_strong_sections_list(self):
        """Correctly identifies sections with score >= 0.5."""
        canvas = CanvasState()
        canvas.scores["vision"] = 0.8
        canvas.scores["risks"] = 0.6
        canvas.scores["architecture"] = 0.3  # Not strong
        strong = canvas.strong_sections
        assert "vision" in strong
        assert "risks" in strong
        assert "architecture" not in strong

    def test_section_labels(self):
        """Score thresholds map to correct labels."""
        canvas = CanvasState()
        assert canvas.get_section_label("vision") == "Empty"  # 0.0
        canvas.scores["vision"] = 0.1
        assert canvas.get_section_label("vision") == "Mentioned"
        canvas.scores["vision"] = 0.3
        assert canvas.get_section_label("vision") == "Thin"
        canvas.scores["vision"] = 0.5
        assert canvas.get_section_label("vision") == "Moderate"
        canvas.scores["vision"] = 0.7
        assert canvas.get_section_label("vision") == "Good"
        canvas.scores["vision"] = 0.9
        assert canvas.get_section_label("vision") == "Strong"


# ============================================================================
# Serialization Tests
# ============================================================================

@pytest.mark.unit
class TestSerialization:

    def test_save_load_roundtrip(self):
        """to_dict -> from_dict preserves all state."""
        canvas = CanvasState()
        canvas.update(1, {"vision": 0.8, "architecture": 0.5}, "Discussion about vision")
        canvas.update(2, {"features": 0.6}, "Feature discussion")

        data = canvas.to_dict()
        json_str = json.dumps(data)
        loaded = CanvasState.from_dict(json.loads(json_str))

        for sid in SECTION_IDS:
            assert loaded.scores[sid] == pytest.approx(canvas.scores[sid])
        assert len(loaded.evidence["vision"]) == len(canvas.evidence["vision"])

    def test_evidence_stored_per_section(self):
        """Evidence snippets accumulate with turn numbers."""
        canvas = CanvasState()
        canvas.update(1, {"vision": 0.5}, "First vision point")
        canvas.update(3, {"vision": 0.4}, "Second vision point")
        assert len(canvas.evidence["vision"]) == 2
        assert canvas.evidence["vision"][0][0] == 1
        assert canvas.evidence["vision"][1][0] == 3
        assert "First" in canvas.evidence["vision"][0][1]


# ============================================================================
# Display Tests
# ============================================================================

@pytest.mark.unit
class TestDisplay:

    def test_render_canvas_format(self):
        """Output string contains all 12 section names and progress indicators."""
        canvas = CanvasState()
        canvas.scores["vision"] = 0.8
        output = render_canvas(canvas)
        for section in PRD_SECTIONS:
            assert section["name"] in output
        assert "Coverage:" in output
        assert "DISCOVERY CANVAS" in output

    def test_render_canvas_compact(self):
        """Compact render is a single line with key stats."""
        canvas = CanvasState()
        canvas.scores["vision"] = 0.8
        output = render_canvas_compact(canvas)
        assert "Canvas:" in output
        assert "%" in output
        # Should be a single logical line (no newlines)
        assert "\n" not in output


# ============================================================================
# Suggestion Tests
# ============================================================================

@pytest.mark.unit
class TestSuggestions:

    def test_suggest_next_topic_empty(self):
        """Suggests the first-gen empty section (highest downstream impact)."""
        canvas = CanvasState()
        suggestion = suggest_next_topic(canvas)
        assert suggestion is not None
        # First empty section should be vision (gen 1)
        assert "Vision" in suggestion

    def test_suggest_next_topic_partial(self):
        """With vision covered, suggests next empty section."""
        canvas = CanvasState()
        canvas.scores["vision"] = 0.5
        suggestion = suggest_next_topic(canvas)
        assert suggestion is not None
        assert "Vision" not in suggestion
        # Should suggest architecture (gen 2)
        assert "Architecture" in suggestion or "architecture" in suggestion.lower()

    def test_suggest_next_topic_all_covered(self):
        """Returns None when no sections are empty or thin."""
        canvas = CanvasState()
        for sid in SECTION_IDS:
            canvas.scores[sid] = 0.5
        suggestion = suggest_next_topic(canvas)
        assert suggestion is None


# ============================================================================
# Classification Tests
# ============================================================================

@pytest.mark.unit
class TestClassification:

    def test_classify_exchange_parse(self):
        """Valid JSON response parses to section scores."""
        result = _parse_classification('{"vision": 0.9, "architecture": 0.3}')
        assert result == {"vision": 0.9, "architecture": 0.3}

    def test_classify_exchange_parse_failure(self):
        """Malformed LLM response returns empty dict (no crash)."""
        result = _parse_classification("I think this is about vision and stuff")
        assert result == {}

    def test_classify_exchange_code_fence(self):
        """JSON in markdown code fence is parsed correctly."""
        raw = '```json\n{"vision": 0.7, "risks": 0.4}\n```'
        result = _parse_classification(raw)
        assert result == {"vision": 0.7, "risks": 0.4}

    def test_classify_exchange_filters_invalid(self):
        """Invalid section IDs and out-of-range scores are filtered."""
        raw = '{"vision": 0.8, "nonexistent": 0.5, "architecture": -0.1, "risks": 1.5}'
        result = _parse_classification(raw)
        assert "vision" in result
        assert "nonexistent" not in result
        assert "architecture" not in result  # Negative
        assert "risks" not in result  # > 1.0


# ============================================================================
# PRD Preview Tests
# ============================================================================

@pytest.mark.unit
class TestPrdPreview:

    def test_prd_preview_format(self):
        """Preview contains all 12 sections with labels."""
        canvas = CanvasState()
        canvas.scores["vision"] = 0.8
        canvas.evidence["vision"].append((1, "We discussed the project vision and goals"))
        preview = generate_prd_preview(canvas)
        assert "Vision" in preview
        assert "INFERRED" in preview  # Empty sections show INFERRED
        assert "STRONG" in preview  # Vision should show STRONG

    def test_prd_sections_count(self):
        """PRD_SECTIONS has exactly 12 entries matching task_205."""
        assert len(PRD_SECTIONS) == 12
        # Check gen numbers are 1-12
        gens = [s["gen"] for s in PRD_SECTIONS]
        assert gens == list(range(1, 13))
        # Check all IDs are unique
        assert len(set(SECTION_IDS)) == 12
