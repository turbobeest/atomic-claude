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
    """Graph node types for the SDLC pipeline knowledge graph.

    Core pipeline chain: Source -> Finding -> Decision -> Feature ->
    Requirement -> Task -> Spec -> ReviewFinding

    Supporting types: Agent, Memory, Skill, Audit, SDLCPhase, Category
    Reserved (future): Episode, Workflow, PhaseCheckpoint
    """
    SOURCE = "Source"           # Original material (dialogue, corpus, document)
    FINDING = "Finding"         # Insight extracted during discovery
    DECISION = "Decision"       # Accepted/rejected choice with rationale
    REQUIREMENT = "Requirement" # Formal requirement from PRD (SHALL/SHOULD/MAY)
    FEATURE = "Feature"         # Product feature grouping requirements
    TASK = "Task"               # Decomposed work unit implementing requirements
    SPEC = "Spec"               # OpenSpec document guiding task implementation
    AGENT = "Agent"             # Pipeline or expert agent definition
    MEMORY = "Memory"           # Task/phase memory entry for context recall
    PHASE_CHECKPOINT = "PhaseCheckpoint"  # Saved state at phase boundary
    AUDIT = "Audit"             # Audit check definition from catalog
    REVIEW_FINDING = "ReviewFinding"      # Issue found during code review
    SKILL = "Skill"             # Reusable skill definition
    SDLC_PHASE = "SDLCPhase"   # Pipeline phase (0-9) anchor node
    CATEGORY = "Category"       # Taxonomy category for agents/skills/audits
    EPISODE = "Episode"         # (Reserved) Task execution instance for replay
    WORKFLOW = "Workflow"       # (Reserved) Multi-skill workflow composition


# ============================================================================
# RELATIONSHIP TYPES
# ============================================================================

class RelType(str, Enum):
    """Graph relationship types.

    Traceability chain (phases 1-6):
      DERIVED_FROM: Finding/Decision/Requirement -> Source (provenance)
      INFORMS:      Finding -> Decision (discovery insight influences choice)
      SUPPORTS:     Decision -> Feature (decision justifies feature)
      CONTAINS:     Feature -> Requirement (feature decomposes into reqs)
      IMPLEMENTS:   Task -> Requirement (task fulfills requirement)
      INFORMED_BY:  Task -> Finding/Decision (research context for execution)
      TASK_DEPENDS_ON: Task -> Task (execution order dependency)
      HAS_SPEC:     Task -> Spec (implementation specification)
      TRACED_TO:    Requirement -> Spec/Finding (cross-artifact traceability)
      SPEC_INTERFACE: Spec -> Spec (API contract between dependent specs)
      REVIEW_OF:    ReviewFinding -> Task/Spec/Feature (review targets)
      VIOLATES:     ReviewFinding -> Requirement (review finding breaks req)

    Lifecycle:
      SUPERSEDES:   Any -> Same type (version replacement)
      RECORDED_DURING: Memory -> Task/SDLCPhase (when memory was captured)

    Taxonomy:
      BELONGS_TO:    Skill/Agent/Audit/Finding -> SDLCPhase/Category
      APPLICABLE_IN: Agent/Audit -> SDLCPhase (phase applicability)
      SUBCATEGORY_OF: Category -> Category (taxonomy hierarchy)
      AUDIT_COVERS:  Audit -> Task/Requirement/Spec (audit scope)
      COMMONLY_COMBINED: Audit -> Audit (audit co-occurrence)

    Requirements:
      DEPENDS_ON:     Requirement -> Requirement (req-level dependency)
      CONFLICTS_WITH: Requirement -> Requirement (req-level conflict)

    Skills (reserved):
      COMPOSES_WITH:   Skill -> Skill (composition pattern)
      USED_IN:         Skill -> Episode (execution tracking)
      STEP:            Workflow -> Skill (workflow step)
      SKILL_DEPENDS_ON: Skill -> Skill (skill prerequisite)
    """
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
    AUDIT_COVERS = "AUDIT_COVERS"
    COMMONLY_COMBINED = "COMMONLY_COMBINED"
    REVIEW_OF = "REVIEW_OF"
    VIOLATES = "VIOLATES"
    BELONGS_TO = "BELONGS_TO"
    COMPOSES_WITH = "COMPOSES_WITH"
    USED_IN = "USED_IN"
    STEP = "STEP"
    SKILL_DEPENDS_ON = "SKILL_DEPENDS_ON"
    APPLICABLE_IN = "APPLICABLE_IN"
    SUBCATEGORY_OF = "SUBCATEGORY_OF"
    RECORDED_DURING = "RECORDED_DURING"


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
    NodeLabel.AUDIT: ["id", "name", "category", "subcategory", "tier"],
    NodeLabel.REVIEW_FINDING: ["id", "severity", "category", "description"],
    NodeLabel.SKILL: ["id", "name", "category"],
    NodeLabel.SDLC_PHASE: ["id", "name"],
    NodeLabel.CATEGORY: ["id", "name", "domain"],
    NodeLabel.EPISODE: ["id", "task_id"],
    NodeLabel.WORKFLOW: ["id", "name", "task_pattern"],
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
    NodeLabel.AUDIT: {
        "tier": {"focused", "expert", "phd"},
        "status": {"active", "planned", "deprecated"},
        "severity": {"critical", "high", "medium", "low"},
        "automatable": {"yes", "partial", "no", "full", "manual", "none", "minimal"},
    },
    NodeLabel.REVIEW_FINDING: {
        "severity": {"critical", "major", "minor", "suggestion"},
        "category": {
            "logic", "error_handling", "security", "code_quality",
            "layer_separation", "dependency", "pattern", "module_boundary", "coupling",
            "algorithm", "memory", "io", "caching", "concurrency",
            "api_docs", "comments", "types", "examples", "accuracy",
        },
        "status": {"open", "resolved", "wont_fix", "deferred"},
        "review_dimension": {"deep_code", "architecture", "performance", "documentation"},
    },
    NodeLabel.SKILL: {
        "category": {
            "formatting", "validation", "extraction", "git-ops", "file-ops",
            "phase-checks", "doc-gen", "testing", "security", "architecture",
            "deployment", "monitoring", "data", "api", "performance",
            "accessibility", "planning", "debugging", "infrastructure",
            "compliance", "custom",
        },
        "risk_level": {"None", "Low", "Medium", "High"},
        "source": {"anthropic-official", "playbooks", "awesome-claude-code", "community", "tactical-builtin"},
    },
    NodeLabel.CATEGORY: {
        "domain": {"agent", "audit", "skill", "finding"},
    },
    NodeLabel.EPISODE: {
        "outcome": {"success", "partial", "failure"},
    },
}

# Optional properties with defaults
PROPERTY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    NodeLabel.SOURCE: {"phase": "1-discovery", "created_at": "", "content_hash": "", "file_path": ""},
    NodeLabel.FINDING: {"confidence": 0.8, "phase": "1-discovery", "created_at": ""},
    NodeLabel.DECISION: {"status": "proposed", "confidence": 0.7, "alternatives_json": "", "phase": "1-discovery", "created_at": ""},
    NodeLabel.REQUIREMENT: {"priority": "medium", "status": "draft", "created_at": ""},
    NodeLabel.FEATURE: {"created_at": ""},
    NodeLabel.TASK: {
        "status": "pending",
        "priority": "medium",
        "estimated_complexity": 5,
    },
    NodeLabel.SPEC: {},
    NodeLabel.AGENT: {"composite_score": 0.0, "description": "", "grade": "", "phase": "", "subcategory": "", "created_at": ""},
    NodeLabel.MEMORY: {"relevance_score": 0.8, "tags_csv": "", "priority": "P2", "task_id": "", "created_at": ""},
    NodeLabel.PHASE_CHECKPOINT: {"status": "valid", "key_decisions_csv": "", "artifacts_csv": "", "created_at": ""},
    NodeLabel.AUDIT: {
        "status": "active",
        "severity": "medium",
        "automatable": "no",
        "category_number": 0,
    },
    NodeLabel.REVIEW_FINDING: {
        "status": "open",
        "phase": "6-code-review",
        "shadow_finding": False,
    },
    NodeLabel.SKILL: {
        "installed": False,
        "requires_internet": False,
        "requires_saas": False,
        "risk_level": "None",
        "source": "community",
        "times_used": 0,
        "avg_success_score": 0.0,
        "description": "",
        "blocked_by_profile": "",
        "content_hash": "",
        "created_at": "",
    },
    NodeLabel.SDLC_PHASE: {"phase_number": 0, "created_at": ""},
    NodeLabel.CATEGORY: {"created_at": ""},
    NodeLabel.EPISODE: {
        "success_score": 0.0,
        "tokens_consumed": 0,
        "duration_ms": 0,
    },
    NodeLabel.WORKFLOW: {
        "times_used": 0,
        "avg_success": 0.0,
    },
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
        {NodeLabel.SPEC, NodeLabel.FINDING},
    ),
    RelType.INFORMED_BY: (
        {NodeLabel.TASK},
        {NodeLabel.FINDING, NodeLabel.DECISION},
    ),
    RelType.SUPERSEDES: (
        # Any node type can supersede any other of same type
        {NodeLabel.SOURCE, NodeLabel.FINDING, NodeLabel.DECISION,
         NodeLabel.REQUIREMENT, NodeLabel.FEATURE, NodeLabel.TASK,
         NodeLabel.SPEC, NodeLabel.AGENT, NodeLabel.MEMORY,
         NodeLabel.PHASE_CHECKPOINT, NodeLabel.AUDIT, NodeLabel.REVIEW_FINDING,
         NodeLabel.SKILL, NodeLabel.SDLC_PHASE, NodeLabel.CATEGORY,
         NodeLabel.EPISODE, NodeLabel.WORKFLOW},
        {NodeLabel.SOURCE, NodeLabel.FINDING, NodeLabel.DECISION,
         NodeLabel.REQUIREMENT, NodeLabel.FEATURE, NodeLabel.TASK,
         NodeLabel.SPEC, NodeLabel.AGENT, NodeLabel.MEMORY,
         NodeLabel.PHASE_CHECKPOINT, NodeLabel.AUDIT, NodeLabel.REVIEW_FINDING,
         NodeLabel.SKILL, NodeLabel.SDLC_PHASE, NodeLabel.CATEGORY,
         NodeLabel.EPISODE, NodeLabel.WORKFLOW},
    ),
    RelType.AUDIT_COVERS: (
        {NodeLabel.AUDIT},
        {NodeLabel.TASK, NodeLabel.REQUIREMENT, NodeLabel.SPEC},
    ),
    RelType.COMMONLY_COMBINED: (
        {NodeLabel.AUDIT},
        {NodeLabel.AUDIT},
    ),
    RelType.REVIEW_OF: (
        {NodeLabel.REVIEW_FINDING},
        {NodeLabel.TASK, NodeLabel.SPEC, NodeLabel.FEATURE},
    ),
    RelType.VIOLATES: (
        {NodeLabel.REVIEW_FINDING},
        {NodeLabel.REQUIREMENT},
    ),
    RelType.BELONGS_TO: (
        {NodeLabel.SKILL, NodeLabel.AGENT, NodeLabel.AUDIT, NodeLabel.FINDING,
         NodeLabel.PHASE_CHECKPOINT},
        {NodeLabel.SDLC_PHASE, NodeLabel.CATEGORY},
    ),
    RelType.APPLICABLE_IN: (
        {NodeLabel.AGENT, NodeLabel.AUDIT},
        {NodeLabel.SDLC_PHASE},
    ),
    RelType.SUBCATEGORY_OF: (
        {NodeLabel.CATEGORY},
        {NodeLabel.CATEGORY},
    ),
    RelType.RECORDED_DURING: (
        {NodeLabel.MEMORY},
        {NodeLabel.TASK, NodeLabel.SDLC_PHASE},
    ),
    RelType.COMPOSES_WITH: (
        {NodeLabel.SKILL},
        {NodeLabel.SKILL},
    ),
    RelType.USED_IN: (
        {NodeLabel.SKILL},
        {NodeLabel.EPISODE},
    ),
    RelType.STEP: (
        {NodeLabel.WORKFLOW},
        {NodeLabel.SKILL},
    ),
    RelType.SKILL_DEPENDS_ON: (
        {NodeLabel.SKILL},
        {NodeLabel.SKILL},
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
    RelType.COMPOSES_WITH: ["co_occurrence", "avg_combined_success"],
    RelType.USED_IN: ["success_score"],
    RelType.STEP: ["order", "optional"],
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
    ("Source", "phase"),
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
    # Audit lookups
    ("Audit", "id"),
    ("Audit", "category"),
    ("Audit", "subcategory"),
    ("Audit", "tier"),
    ("Audit", "severity"),
    ("Audit", "category_number"),
    # ReviewFinding lookups
    ("ReviewFinding", "id"),
    ("ReviewFinding", "severity"),
    ("ReviewFinding", "category"),
    ("ReviewFinding", "status"),
    ("ReviewFinding", "review_dimension"),
    # Skill lookups
    ("Skill", "id"),
    ("Skill", "category"),
    ("Skill", "risk_level"),
    ("Skill", "installed"),
    ("Skill", "source"),
    # SDLCPhase lookups
    ("SDLCPhase", "id"),
    # Category lookups
    ("Category", "id"),
    ("Category", "domain"),
    # Episode lookups
    ("Episode", "id"),
    ("Episode", "task_id"),
    # Workflow lookups
    ("Workflow", "id"),
]

FULLTEXT_INDEX_DEFINITIONS = [
    ("Finding", ["content"]),
    ("Requirement", ["content", "acceptance_criteria"]),
    ("Task", ["title", "description"]),
    ("Agent", ["name", "description"]),
    ("Memory", ["content", "tags_csv"]),
    ("Audit", ["name", "description_what", "description_why"]),
    ("ReviewFinding", ["description", "recommendation"]),
    ("Skill", ["name", "description"]),
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

    # Check confidence range for Decision
    if label_str == NodeLabel.DECISION:
        confidence = properties.get("confidence")
        if confidence is not None and not (0.0 <= confidence <= 1.0):
            return f"Decision.confidence must be 0.0-1.0, got {confidence}"

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

    # SUPERSEDES must connect nodes of the same type
    if rel_str == RelType.SUPERSEDES and from_str != to_str:
        return (
            f"SUPERSEDES requires same-type nodes, got "
            f"{from_str} -> {to_str}"
        )

    return None
