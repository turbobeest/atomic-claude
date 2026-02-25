"""ATOMIC CLAUDE - Audit Catalog Loader

Loads 2,186 audit definitions from YAML files into a dedicated FalkorDB graph
('atomic-audits') for searchable audit selection during phase audit tasks.

Usage:
    from core.graph.audit_loader import get_audit_graph, load_audit_catalog

    audit_graph = get_audit_graph()
    loaded = load_audit_catalog(audit_graph)
    results = query_audits(audit_graph, category="security-trust", severity="critical")
"""

import csv
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default paths
AUDITS_DIR = Path(__file__).parent.parent.parent / "audits" / "audits"
INVENTORY_CSV = Path(__file__).parent.parent.parent / "audits" / "AUDIT-INVENTORY.csv"
AUDIT_GRAPH_NAME = "atomic-audits"

# Try to import YAML parser
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None


def get_audit_graph(host: str = None, port: int = None):
    """
    Get a GraphManager connected to the dedicated 'atomic-audits' graph.

    This is separate from the main 'atomic-claude' pipeline graph.
    Audit data is static reference material, not pipeline state.

    Raises:
        GraphUnavailableError: If FalkorDB is not running
    """
    from .connection import GraphConnection
    from .manager import GraphManager

    _host = host or os.environ.get("ATOMIC_GRAPH_HOST", "localhost")
    _port = port or int(os.environ.get("ATOMIC_GRAPH_PORT", "6380"))

    conn = GraphConnection(_host, _port, AUDIT_GRAPH_NAME)
    conn._connect()
    mgr = GraphManager(conn, phase_id="audit-catalog")
    mgr.ensure_schema()
    return mgr


def _parse_csv_phases(row: dict) -> str:
    """Extract applicable SDLC phases from CSV row into comma-separated string."""
    phase_columns = [
        "discovery", "prd", "task_decomposition", "specification",
        "implementation", "testing", "integration", "deployment",
        "post_production",
    ]
    phases = []
    for col in phase_columns:
        val = row.get(col, "").strip()
        if val.lower() in ("yes", "true", "1"):
            phases.append(col)
    return ",".join(phases)


def _load_csv_lookup() -> Dict[str, dict]:
    """Load AUDIT-INVENTORY.csv into a lookup dict keyed by audit_id."""
    if not INVENTORY_CSV.exists():
        logger.warning(f"Audit inventory CSV not found: {INVENTORY_CSV}")
        return {}

    lookup = {}
    with open(INVENTORY_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            audit_id = row.get("audit_id", "").strip()
            if audit_id:
                lookup[audit_id] = row
    return lookup


def _parse_yaml_file(yaml_path: Path) -> Optional[dict]:
    """Parse a single audit YAML file and extract key properties."""
    if not HAS_YAML:
        return None

    try:
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.debug(f"Failed to parse {yaml_path}: {e}")
        return None

    if not data or "audit" not in data:
        return None

    audit = data["audit"]
    desc = data.get("description", {})
    execution = data.get("execution", {})
    relationships = data.get("relationships", {})
    governance = data.get("governance", {})

    # Extract compliance frameworks
    frameworks = []
    for mapping in governance.get("compliance_frameworks", []):
        fw = mapping.get("framework", "")
        if fw:
            frameworks.append(fw)
    # Also check compliance_mappings (alternate key name)
    for mapping in governance.get("compliance_mappings", []):
        fw = mapping.get("framework", "")
        if fw:
            frameworks.append(fw)

    # Extract commonly combined audit IDs
    combined = relationships.get("commonly_combined", [])

    # Count signals by severity
    signals = data.get("signals", {})
    signal_counts = {}
    for level in ("critical", "high", "medium", "low", "positive"):
        items = signals.get(level, [])
        if items:
            signal_counts[f"signal_count_{level}"] = len(items)

    return {
        "id": audit.get("id", ""),
        "name": audit.get("name", ""),
        "category": audit.get("category", ""),
        "category_number": audit.get("category_number", 0),
        "subcategory": audit.get("subcategory", ""),
        "tier": audit.get("tier", "expert"),
        "status": audit.get("status", "active"),
        "estimated_duration": str(audit.get("estimated_duration", "")),
        "completeness": audit.get("completeness", ""),
        "requires_runtime": bool(audit.get("requires_runtime", False)),
        "destructive": bool(audit.get("destructive", False)),
        # Execution
        "severity": execution.get("severity", "medium"),
        "automatable": execution.get("automatable", "no"),
        "scope": execution.get("scope", ""),
        "blocks_phase": bool(execution.get("blocks_phase", False)),
        "parallelizable": bool(execution.get("parallelizable", True)),
        # Descriptions (critical for fulltext search)
        "description_what": desc.get("what", ""),
        "description_why": desc.get("why_it_matters", ""),
        "when_to_run": ",".join(desc.get("when_to_run", [])) if isinstance(desc.get("when_to_run"), list) else str(desc.get("when_to_run", "")),
        # Relationships
        "commonly_combined": ",".join(combined) if combined else "",
        "compliance_frameworks": ",".join(frameworks) if frameworks else "",
        # Signal counts
        **signal_counts,
        # File reference for on-demand full YAML loading
        "file_path": str(yaml_path),
    }


def load_audit_catalog(graph, audits_dir: Path = None,
                       force_reload: bool = False) -> int:
    """
    Load audit catalog into the 'atomic-audits' FalkorDB graph.

    Parses YAML files for rich descriptions and signals. Falls back to
    CSV-only loading if PyYAML is not installed.

    Args:
        graph: GraphManager instance connected to atomic-audits graph
        audits_dir: Path to audits/audits/ directory (default: auto-detected)
        force_reload: If True, clear existing audits before loading

    Returns:
        Number of audit nodes created
    """
    _dir = audits_dir or AUDITS_DIR

    if force_reload:
        # Clear existing audit nodes
        try:
            graph.conn.query("MATCH (n:Audit) DETACH DELETE n")
            logger.info("Cleared existing audit nodes for reload")
        except Exception as e:
            logger.warning(f"Failed to clear audit nodes: {e}")

    # Check idempotency
    existing = graph.reader.count_nodes("Audit")
    if existing > 0 and not force_reload:
        logger.info(f"Audit catalog already loaded ({existing} audits)")
        return 0

    # Load CSV lookup for SDLC phase applicability
    csv_lookup = _load_csv_lookup()
    logger.info(f"Loaded {len(csv_lookup)} rows from audit inventory CSV")

    # Find all YAML files
    yaml_files = sorted(_dir.glob("**/*.yaml"))
    yaml_files = [f for f in yaml_files if not f.name.startswith("._")]

    if not yaml_files:
        logger.warning(f"No YAML audit files found in {_dir}")
        # Fall back to CSV-only loading
        return _load_from_csv_only(graph, csv_lookup)

    if not HAS_YAML:
        logger.warning("PyYAML not installed — falling back to CSV-only loading. "
                       "pip install pyyaml for full audit descriptions.")
        return _load_from_csv_only(graph, csv_lookup)

    logger.info(f"Parsing {len(yaml_files)} YAML audit files...")

    ops = []
    parsed = 0
    for yaml_path in yaml_files:
        props = _parse_yaml_file(yaml_path)
        if not props:
            continue

        # Enrich with CSV data (SDLC phase applicability)
        audit_id = props["id"]
        csv_row = csv_lookup.get(audit_id, {})
        if csv_row:
            props["sdlc_phases"] = _parse_csv_phases(csv_row)
        else:
            props["sdlc_phases"] = ""

        ops.append({"op": "add_node", "label": "Audit", "properties": props})
        parsed += 1

    if not ops:
        logger.warning("No valid audit YAML files parsed")
        return 0

    # Bulk write in batches of 200 to avoid memory pressure
    total_loaded = 0
    batch_size = 200
    for i in range(0, len(ops), batch_size):
        batch = ops[i:i + batch_size]
        loaded = graph.writer.bulk_write(batch)
        total_loaded += loaded
        if (i + batch_size) % 1000 == 0:
            logger.info(f"  Loaded {total_loaded}/{len(ops)} audits...")

    logger.info(f"Loaded {total_loaded} audits from YAML into graph "
                f"(parsed {parsed}, skipped {len(yaml_files) - parsed})")

    # Create COMMONLY_COMBINED edges between audits
    _create_combination_edges(graph, ops)

    return total_loaded


def _load_from_csv_only(graph, csv_lookup: Dict[str, dict]) -> int:
    """Fallback: load audit metadata from CSV only (no descriptions)."""
    if not csv_lookup:
        return 0

    ops = []
    for audit_id, row in csv_lookup.items():
        props = {
            "id": audit_id,
            "name": row.get("audit_name", ""),
            "category": row.get("category", ""),
            "category_number": int(row.get("category_number", 0) or 0),
            "subcategory": row.get("subcategory", ""),
            "tier": row.get("tier", "expert"),
            "status": row.get("status", "active"),
            "severity": row.get("severity", "medium"),
            "automatable": row.get("automatable", "no"),
            "estimated_duration": row.get("estimated_duration", ""),
            "file_path": row.get("file_path", ""),
            "sdlc_phases": _parse_csv_phases(row),
            "description_what": "",
            "description_why": "",
        }
        ops.append({"op": "add_node", "label": "Audit", "properties": props})

    total_loaded = 0
    batch_size = 200
    for i in range(0, len(ops), batch_size):
        batch = ops[i:i + batch_size]
        total_loaded += graph.writer.bulk_write(batch)

    logger.info(f"Loaded {total_loaded} audits from CSV into graph (no descriptions)")
    return total_loaded


def _create_combination_edges(graph, ops: List[dict]) -> int:
    """Create COMMONLY_COMBINED edges between audits that reference each other."""
    # Build set of loaded audit IDs for validation
    loaded_ids = {op["properties"]["id"] for op in ops}

    edge_ops = []
    for op in ops:
        props = op["properties"]
        combined = props.get("commonly_combined", "")
        if not combined:
            continue
        for target_id in combined.split(","):
            target_id = target_id.strip()
            if target_id and target_id in loaded_ids:
                edge_ops.append({
                    "op": "add_edge",
                    "rel_type": "COMMONLY_COMBINED",
                    "from_label": "Audit",
                    "from_id": props["id"],
                    "to_label": "Audit",
                    "to_id": target_id,
                })

    if edge_ops:
        created = graph.writer.bulk_write(edge_ops)
        logger.info(f"Created {created} COMMONLY_COMBINED edges between audits")
        return created
    return 0


# ============================================================================
# QUERY FUNCTIONS
# ============================================================================

def query_audits(graph, category: str = None, subcategory: str = None,
                 tier: str = None, severity: str = None,
                 sdlc_phase: str = None, search: str = None,
                 limit: int = 50) -> List[dict]:
    """
    Query audits from the audit graph with flexible filters.

    Args:
        graph: GraphManager connected to atomic-audits graph
        category: Filter by category (e.g., "security-trust")
        subcategory: Filter by subcategory (e.g., "secrets-management")
        tier: Filter by tier (focused/expert/phd)
        severity: Filter by severity (critical/high/medium/low)
        sdlc_phase: Filter by SDLC phase applicability (e.g., "implementation")
        search: Fulltext search query
        limit: Max results

    Returns:
        List of audit node dicts
    """
    if search:
        try:
            results = graph.reader.fulltext_search("Audit", search, limit=limit)
        except Exception as e:
            logger.debug("Audit fulltext search failed: %s", e)
            results = []
    else:
        filters = {}
        if category:
            filters["category"] = category
        if subcategory:
            filters["subcategory"] = subcategory
        if tier:
            filters["tier"] = tier
        if severity:
            filters["severity"] = severity
        results = graph.reader.get_nodes(
            "Audit", filters=filters if filters else None, limit=limit,
        )

    # Post-filter by SDLC phase (stored as CSV string)
    if sdlc_phase:
        results = [
            r for r in results
            if sdlc_phase in (r.get("sdlc_phases", "") or "").split(",")
        ]

    return results[:limit]


def query_audits_for_task(graph, task_context: str,
                          phase: str = None, limit: int = 20) -> str:
    """
    Find relevant audits for a given task context, formatted for LLM consumption.

    Uses fulltext search on audit descriptions + phase filtering.

    Args:
        graph: GraphManager connected to atomic-audits graph
        task_context: Description of what the task does
        phase: SDLC phase to filter by
        limit: Max results

    Returns:
        Formatted markdown string of matching audits
    """
    results = query_audits(graph, search=task_context, sdlc_phase=phase, limit=limit)

    if not results:
        return ""

    # Group by category
    by_category = defaultdict(list)
    for a in results:
        by_category[a.get("category", "uncategorized")].append(a)

    parts = [f"## Relevant Audits ({len(results)} found)\n"]
    for cat in sorted(by_category.keys()):
        cat_audits = by_category[cat]
        parts.append(f"### {cat} ({len(cat_audits)} audits)")
        for a in sorted(cat_audits, key=lambda x: x.get("severity", "medium")):
            severity = a.get("severity", "medium").upper()
            tier = a.get("tier", "expert")
            name = a.get("name", a.get("id", ""))
            auto = a.get("automatable", "no")
            duration = a.get("estimated_duration", "")
            desc = (a.get("description_what", "") or "")[:150]
            if len(desc) == 150:
                desc += "..."
            parts.append(
                f"- **[{severity}]** {name} (tier: {tier}, auto: {auto}, ~{duration})"
            )
            if desc:
                parts.append(f"  {desc}")
        parts.append("")

    return "\n".join(parts)


def get_audit_stats(graph) -> dict:
    """Get summary statistics for the loaded audit catalog."""
    try:
        total = graph.reader.count_nodes("Audit")
    except Exception as e:
        logger.debug("Failed to get audit stats: %s", e)
        return {"total": 0, "loaded": False}

    if total == 0:
        return {"total": 0, "loaded": False}

    # Count by tier
    by_tier = {}
    for tier in ("focused", "expert", "phd"):
        by_tier[tier] = graph.reader.count_nodes("Audit", filters={"tier": tier})

    # Count by severity
    by_severity = {}
    for sev in ("critical", "high", "medium", "low"):
        by_severity[sev] = graph.reader.count_nodes("Audit", filters={"severity": sev})

    return {
        "total": total,
        "loaded": True,
        "by_tier": by_tier,
        "by_severity": by_severity,
    }
