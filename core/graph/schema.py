"""
ATOMIC CLAUDE - Graph Ontology Schema

Defines node labels, relationship types, required properties, and validation
rules for the FalkorDB knowledge graph.
"""

from enum import Enum
from typing import Dict, List, Set, Any, Optional


# ============================================================================
# NODE LABELS
# ============================================================================

class NodeLabel(str, Enum):
    """Graph node types."""
    SOURCE = "Source"
    FINDING = "Finding"
    DECISION = "Decision"
    REQUIREMENT = "Requirement"
    FEATURE = "Feature"
    TASK = "Task"
    SPEC = "Spec"
    AGENT = "Agent"
    MEMORY = "Memory"
    PHASE_CHECKPOINT = "PhaseCheckpoint"


# ============================================================================
# RELATIONSHIP TYPES
# ============================================================================

class RelType(str, Enum):
    """Graph relationship types."""
    DERIVED_FROM = "DERIVED_FROM"
    INFORMS = "INFORMS"
    SUPPORTS = "SUPPORTS"
    CONTAINS = "CONTAINS"
    DEPENDS_ON = "DEPENDS_ON"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    IMPLEMENTS = "IMPLEMENTS"
    TASK_DEPENDS_ON = "TASK_DEPENDS_ON"
    HAS_SPEC = "HAS_SPEC"
    SPEC_INTERFACE = "SPEC_INTERFACE"
    TRACED_TO = "TRACED_TO"
    INFORMED_BY = "INFORMED_BY"
    SUPERSEDES = "SUPERSEDES"


# ============================================================================
# PROPERTY SCHEMAS
# ============================================================================

# Required properties per node label (must be present on creation)
REQUIRED_PROPERTIES: Dict[str, List[str]] = {
    NodeLabel.SOURCE: ["id", "type", "title"],
    NodeLabel.FINDING: ["id", "category", "title", "content"],
    NodeLabel.DECISION: ["id", "title", "rationale"],
    NodeLabel.REQUIREMENT: ["id", "type", "title", "content"],
    NodeLabel.FEATURE: ["id", "title"],
    NodeLabel.TASK: ["id", "title", "description"],
    NodeLabel.SPEC: ["id", "task_id"],
    NodeLabel.AGENT: ["id", "name", "tier", "category", "role"],
    NodeLabel.MEMORY: ["id", "phase", "entry_type", "content"],
    NodeLabel.PHASE_CHECKPOINT: ["id", "phase", "phase_name", "summary"],
}

# Valid values for enumerated properties
VALID_VALUES: Dict[str, Dict[str, Set[str]]] = {
    NodeLabel.SOURCE: {
        "type": {"corpus", "dialogue", "interview", "need", "meeting"},
    },
    NodeLabel.FINDING: {
        "category": {
            "vision", "impact", "audience", "constraint",
            "non_negotiable", "open_question", "technical", "research",
        },
    },
    NodeLabel.DECISION: {
        "status": {"proposed", "accepted", "rejected", "superseded"},
    },
    NodeLabel.REQUIREMENT: {
        "type": {"functional", "non_functional", "constraint"},
        "priority": {"high", "medium", "low"},
        "rfc2119_keyword": {"SHALL", "SHOULD", "MAY"},
        "status": {"draft", "approved", "implemented", "tested"},
    },
    NodeLabel.TASK: {
        "status": {"pending", "in_progress", "done", "blocked"},
        "priority": {"high", "medium", "low"},
        "category": {
            "infrastructure", "feature", "testing",
            "documentation", "security",
        },
    },
    NodeLabel.AGENT: {
        "tier": {"expert", "phd", "focused", "pipeline"},
        "role": {"executor", "advisor", "auditor", "architect", "gatekeeper",
                 "analyzer", "validator", "monitor", "controller", "strategist"},
    },
    NodeLabel.MEMORY: {
        "entry_type": {"task_start", "task_end", "task_progress",
                       "phase_closeout", "checkpoint", "user_note",
                       "system_event"},
    },
    NodeLabel.PHASE_CHECKPOINT: {
        "status": {"valid", "invalidated", "superseded"},
    },
}

# Optional properties with defaults
PROPERTY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    NodeLabel.SOURCE: {"phase": "1-discovery"},
    NodeLabel.FINDING: {"confidence": 0.8, "phase": "1-discovery"},
    NodeLabel.DECISION: {"status": "proposed"},
    NodeLabel.REQUIREMENT: {"priority": "medium", "status": "draft"},
    NodeLabel.FEATURE: {},
    NodeLabel.TASK: {
        "status": "pending",
        "priority": "medium",
        "estimated_complexity": 5,
    },
    NodeLabel.SPEC: {},
    NodeLabel.AGENT: {"composite_score": 0.0},
    NodeLabel.MEMORY: {"relevance_score": 0.8, "tags_csv": ""},
    NodeLabel.PHASE_CHECKPOINT: {"status": "valid"},
}

# Valid relationship endpoints: {rel_type: (from_labels, to_labels)}
VALID_RELATIONSHIPS: Dict[str, tuple] = {
    RelType.DERIVED_FROM: (
        {NodeLabel.FINDING, NodeLabel.DECISION, NodeLabel.REQUIREMENT},
        {NodeLabel.SOURCE},
    ),
    RelType.INFORMS: (
        {NodeLabel.FINDING},
        {NodeLabel.DECISION},
    ),
    RelType.SUPPORTS: (
        {NodeLabel.DECISION},
        {NodeLabel.FEATURE, NodeLabel.REQUIREMENT},
    ),
    RelType.CONTAINS: (
        {NodeLabel.FEATURE},
        {NodeLabel.REQUIREMENT},
    ),
    RelType.DEPENDS_ON: (
        {NodeLabel.REQUIREMENT},
        {NodeLabel.REQUIREMENT},
    ),
    RelType.CONFLICTS_WITH: (
        {NodeLabel.REQUIREMENT},
        {NodeLabel.REQUIREMENT},
    ),
    RelType.IMPLEMENTS: (
        {NodeLabel.TASK},
        {NodeLabel.REQUIREMENT},
    ),
    RelType.TASK_DEPENDS_ON: (
        {NodeLabel.TASK},
        {NodeLabel.TASK},
    ),
    RelType.HAS_SPEC: (
        {NodeLabel.TASK},
        {NodeLabel.SPEC},
    ),
    RelType.SPEC_INTERFACE: (
        {NodeLabel.SPEC},
        {NodeLabel.SPEC},
    ),
    RelType.TRACED_TO: (
        {NodeLabel.REQUIREMENT},
        {NodeLabel.SPEC},
    ),
    RelType.INFORMED_BY: (
        {NodeLabel.TASK},
        {NodeLabel.FINDING},
    ),
    RelType.SUPERSEDES: (
        # Any node type can supersede any other of same type
        {NodeLabel.SOURCE, NodeLabel.FINDING, NodeLabel.DECISION,
         NodeLabel.REQUIREMENT, NodeLabel.FEATURE, NodeLabel.TASK,
         NodeLabel.SPEC, NodeLabel.AGENT, NodeLabel.MEMORY,
         NodeLabel.PHASE_CHECKPOINT},
        {NodeLabel.SOURCE, NodeLabel.FINDING, NodeLabel.DECISION,
         NodeLabel.REQUIREMENT, NodeLabel.FEATURE, NodeLabel.TASK,
         NodeLabel.SPEC, NodeLabel.AGENT, NodeLabel.MEMORY,
         NodeLabel.PHASE_CHECKPOINT},
    ),
}

# Relationship properties
RELATIONSHIP_PROPERTIES: Dict[str, List[str]] = {
    RelType.DERIVED_FROM: ["confidence"],
    RelType.CONTAINS: ["order"],
    RelType.DEPENDS_ON: ["type"],  # logical|temporal
    RelType.CONFLICTS_WITH: ["description"],
    RelType.SPEC_INTERFACE: ["name", "direction", "schema_hash"],
    RelType.SUPERSEDES: ["superseded_at", "reason"],
}


# ============================================================================
# INDEX DEFINITIONS
# ============================================================================

INDEX_DEFINITIONS = [
    # Primary lookups
    ("Source", "id"),
    ("Finding", "id"),
    ("Decision", "id"),
    ("Requirement", "id"),
    ("Feature", "id"),
    ("Task", "id"),
    ("Spec", "task_id"),
    # Phase-scoped queries
    ("Finding", "phase"),
    ("Finding", "category"),
    ("Requirement", "type"),
    ("Requirement", "section"),
    ("Task", "category"),
    ("Task", "status"),
    # Agent lookups
    ("Agent", "id"),
    ("Agent", "category"),
    ("Agent", "tier"),
    # Memory lookups
    ("Memory", "id"),
    ("Memory", "phase"),
    ("Memory", "task_id"),
    ("Memory", "entry_type"),
    # Checkpoint lookups
    ("PhaseCheckpoint", "id"),
    ("PhaseCheckpoint", "phase"),
]

FULLTEXT_INDEX_DEFINITIONS = [
    ("Finding", ["content"]),
    ("Requirement", ["content", "acceptance_criteria"]),
    ("Task", ["title", "description"]),
    ("Agent", ["name", "description"]),
    ("Memory", ["content", "tags_csv"]),
]


# ============================================================================
# VALIDATION
# ============================================================================

def validate_node_properties(label: str, properties: Dict[str, Any]) -> Optional[str]:
    """
    Validate node properties against schema.

    Args:
        label: Node label
        properties: Property dict to validate

    Returns:
        Error message string, or None if valid
    """
    label_str = label if isinstance(label, str) else label.value

    # Check required properties
    required = REQUIRED_PROPERTIES.get(label_str, [])
    for prop in required:
        if prop not in properties:
            return f"{label_str} missing required property: {prop}"

    # Check enumerated values
    valid = VALID_VALUES.get(label_str, {})
    for prop, allowed in valid.items():
        if prop in properties and properties[prop] not in allowed:
            return (
                f"{label_str}.{prop} value '{properties[prop]}' "
                f"not in {sorted(allowed)}"
            )

    # Check complexity range for Task
    if label_str == NodeLabel.TASK:
        complexity = properties.get("estimated_complexity")
        if complexity is not None and not (1 <= complexity <= 10):
            return f"Task.estimated_complexity must be 1-10, got {complexity}"

    # Check confidence range for Finding
    if label_str == NodeLabel.FINDING:
        confidence = properties.get("confidence")
        if confidence is not None and not (0.0 <= confidence <= 1.0):
            return f"Finding.confidence must be 0.0-1.0, got {confidence}"

    return None


def validate_relationship(rel_type: str, from_label: str, to_label: str) -> Optional[str]:
    """
    Validate that a relationship type is valid between two node labels.

    Returns:
        Error message string, or None if valid
    """
    rel_str = rel_type if isinstance(rel_type, str) else rel_type.value
    from_str = from_label if isinstance(from_label, str) else from_label.value
    to_str = to_label if isinstance(to_label, str) else to_label.value

    valid = VALID_RELATIONSHIPS.get(rel_str)
    if valid is None:
        return f"Unknown relationship type: {rel_str}"

    from_labels, to_labels = valid
    from_values = {l.value if hasattr(l, 'value') else l for l in from_labels}
    to_values = {l.value if hasattr(l, 'value') else l for l in to_labels}

    if from_str not in from_values:
        return f"{rel_str} cannot originate from {from_str}"
    if to_str not in to_values:
        return f"{rel_str} cannot target {to_str}"

    return None
