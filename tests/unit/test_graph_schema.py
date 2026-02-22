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
