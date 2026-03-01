"""Unit tests for core/graph/schema.py — ontology validation."""
import pytest
from core.graph.schema import (
    NodeLabel, RelType, validate_node_properties, validate_relationship,
    REQUIRED_PROPERTIES, VALID_VALUES, PROPERTY_DEFAULTS,
)


class TestNodeValidation:
    """Test node property validation."""

    def test_valid_source(self):
        props = {"id": "S-001", "type": "corpus", "title": "README.md"}
        assert validate_node_properties("Source", props) is None

    def test_source_missing_required(self):
        props = {"id": "S-001", "type": "corpus"}  # missing title
        error = validate_node_properties("Source", props)
        assert error is not None
        assert "title" in error

    def test_source_invalid_type(self):
        props = {"id": "S-001", "type": "invalid", "title": "Test"}
        error = validate_node_properties("Source", props)
        assert error is not None
        assert "invalid" in error

    def test_valid_finding(self):
        props = {"id": "F-001", "category": "vision", "title": "T", "content": "C"}
        assert validate_node_properties("Finding", props) is None

    def test_finding_invalid_category(self):
        props = {"id": "F-001", "category": "bogus", "title": "T", "content": "C"}
        error = validate_node_properties("Finding", props)
        assert error is not None

    def test_finding_confidence_range(self):
        props = {"id": "F-001", "category": "vision", "title": "T", "content": "C", "confidence": 1.5}
        error = validate_node_properties("Finding", props)
        assert error is not None
        assert "confidence" in error

    def test_finding_confidence_valid(self):
        props = {"id": "F-001", "category": "vision", "title": "T", "content": "C", "confidence": 0.9}
        assert validate_node_properties("Finding", props) is None

    def test_valid_task(self):
        props = {"id": 1, "title": "Setup DB", "description": "Create schema"}
        assert validate_node_properties("Task", props) is None

    def test_task_invalid_status(self):
        props = {"id": 1, "title": "T", "description": "D", "status": "invalid"}
        error = validate_node_properties("Task", props)
        assert error is not None

    def test_task_complexity_range(self):
        props = {"id": 1, "title": "T", "description": "D", "estimated_complexity": 15}
        error = validate_node_properties("Task", props)
        assert error is not None
        assert "complexity" in error

    def test_valid_requirement(self):
        props = {"id": "REQ-001", "type": "functional", "title": "T", "content": "C"}
        assert validate_node_properties("Requirement", props) is None

    def test_valid_decision(self):
        props = {"id": "DEC-001", "title": "Use GraphDB", "rationale": "Better queries"}
        assert validate_node_properties("Decision", props) is None

    def test_valid_feature(self):
        props = {"id": "FEAT-001", "title": "User Auth"}
        assert validate_node_properties("Feature", props) is None

    def test_valid_spec(self):
        props = {"id": "spec-1", "task_id": 1}
        assert validate_node_properties("Spec", props) is None

    def test_valid_agent(self):
        props = {"id": "python-pro", "name": "python-pro", "tier": "expert",
                 "category": "backend-ecosystems", "role": "executor"}
        assert validate_node_properties("Agent", props) is None

    def test_agent_missing_required(self):
        props = {"id": "python-pro", "name": "python-pro"}  # missing tier, category, role
        error = validate_node_properties("Agent", props)
        assert error is not None
        assert "tier" in error or "category" in error or "role" in error

    def test_agent_invalid_tier(self):
        props = {"id": "x", "name": "x", "tier": "bogus",
                 "category": "backend-ecosystems", "role": "executor"}
        error = validate_node_properties("Agent", props)
        assert error is not None
        assert "bogus" in error

    def test_agent_invalid_role(self):
        props = {"id": "x", "name": "x", "tier": "expert",
                 "category": "backend-ecosystems", "role": "hacker"}
        error = validate_node_properties("Agent", props)
        assert error is not None
        assert "hacker" in error

    def test_agent_all_valid_tiers(self):
        for tier in ("expert", "phd", "focused", "pipeline"):
            props = {"id": "x", "name": "x", "tier": tier,
                     "category": "test", "role": "executor"}
            assert validate_node_properties("Agent", props) is None

    # Memory node validation
    def test_valid_memory(self):
        props = {"id": "mem-001", "phase": "1-discovery",
                 "entry_type": "task_end", "content": "Task completed"}
        assert validate_node_properties("Memory", props) is None

    def test_memory_missing_required(self):
        props = {"id": "mem-001"}  # missing phase, entry_type, content
        error = validate_node_properties("Memory", props)
        assert error is not None

    def test_memory_invalid_entry_type(self):
        props = {"id": "mem-001", "phase": "1-discovery",
                 "entry_type": "bogus", "content": "text"}
        error = validate_node_properties("Memory", props)
        assert error is not None
        assert "bogus" in error

    def test_memory_all_valid_entry_types(self):
        for et in ("task_start", "task_end", "task_progress",
                    "phase_closeout", "checkpoint", "user_note", "system_event"):
            props = {"id": "m", "phase": "0-setup", "entry_type": et, "content": "c"}
            assert validate_node_properties("Memory", props) is None

    # PhaseCheckpoint node validation
    def test_valid_phase_checkpoint(self):
        props = {"id": "phase1-20260222", "phase": 1,
                 "phase_name": "discovery", "summary": "Phase 1 complete"}
        assert validate_node_properties("PhaseCheckpoint", props) is None

    def test_checkpoint_missing_required(self):
        props = {"id": "cp-1"}  # missing phase, phase_name, summary
        error = validate_node_properties("PhaseCheckpoint", props)
        assert error is not None

    def test_checkpoint_invalid_status(self):
        props = {"id": "cp-1", "phase": 1, "phase_name": "setup",
                 "summary": "done", "status": "bogus"}
        error = validate_node_properties("PhaseCheckpoint", props)
        assert error is not None
        assert "bogus" in error

    def test_checkpoint_all_valid_statuses(self):
        for status in ("valid", "invalidated", "superseded"):
            props = {"id": "cp-1", "phase": 1, "phase_name": "setup",
                     "summary": "done", "status": status}
            assert validate_node_properties("PhaseCheckpoint", props) is None

    def test_defaults_applied_externally(self):
        """Verify defaults dict exists for each label."""
        for label in NodeLabel:
            assert label.value in PROPERTY_DEFAULTS or label in PROPERTY_DEFAULTS


class TestRelationshipValidation:
    """Test relationship endpoint validation."""

    def test_valid_derived_from(self):
        assert validate_relationship("DERIVED_FROM", "Finding", "Source") is None

    def test_valid_implements(self):
        assert validate_relationship("IMPLEMENTS", "Task", "Requirement") is None

    def test_valid_task_depends_on(self):
        assert validate_relationship("TASK_DEPENDS_ON", "Task", "Task") is None

    def test_invalid_rel_type(self):
        error = validate_relationship("NONEXISTENT", "Task", "Task")
        assert error is not None

    def test_invalid_from_label(self):
        error = validate_relationship("IMPLEMENTS", "Source", "Requirement")
        assert error is not None
        assert "cannot originate" in error

    def test_invalid_to_label(self):
        error = validate_relationship("IMPLEMENTS", "Task", "Source")
        assert error is not None
        assert "cannot target" in error

    def test_all_rel_types_have_valid_endpoints(self):
        """Ensure every RelType is in VALID_RELATIONSHIPS."""
        from core.graph.schema import VALID_RELATIONSHIPS
        for rt in RelType:
            assert rt.value in VALID_RELATIONSHIPS or rt in VALID_RELATIONSHIPS, f"Missing: {rt}"
