"""ATOMIC CLAUDE - Graph Data Validator

Pre-task validation that checks expected graph data is present for each phase.
Produces extremely visible terminal warnings when graph data is missing or
misaligned, so problems are caught immediately rather than silently degraded.

Usage:
    from core.graph.validator import validate_graph_for_phase

    issues = validate_graph_for_phase(graph, phase_id="2-prd", task_id="205")
    # Returns list of GraphDataIssue; also prints loud warnings to terminal
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GraphDataIssue:
    """A single graph data gap or misalignment."""
    severity: str  # "CRITICAL", "WARNING", "INFO"
    phase: str
    description: str
    expected: str
    actual: str
    fix_hint: str = ""


# ============================================================================
# PHASE EXPECTATIONS
# ============================================================================

# What graph data each phase/task expects to READ.
# Keyed by phase number; each entry lists required node counts,
# expected relationships, and specific property checks.

PHASE_EXPECTATIONS: Dict[int, Dict[str, Any]] = {
    2: {
        "name": "PRD Generation",
        "required_nodes": {
            "Source": {"min": 1, "description": "Discovery sources (dialogues, corpus, imports)"},
            "Finding": {"min": 3, "description": "Discovery findings (vision, audience, constraints, etc.)"},
            "Decision": {"min": 0, "description": "Decisions from deliberation (may be proposed or accepted)"},
        },
        "required_categories": {
            "Finding": {
                "vision": "PRD vision section needs vision findings",
                "audience": "PRD audience section needs audience findings",
            },
        },
        "required_relationships": [],
        "task_specific": {
            "205": {
                "Finding.category=vision": "PRD vision/features sections query vision findings",
                "Finding.category=audience": "PRD audience section queries audience findings",
                "Finding.category=constraint": "PRD constraints section queries constraint findings",
                "Decision.status=accepted": "PRD references accepted decisions (task 106 should mark them)",
            },
        },
    },
    3: {
        "name": "Task Decomposition",
        "required_nodes": {
            "Feature": {"min": 1, "description": "Features from PRD authoring"},
            "Finding": {"min": 3, "description": "Discovery findings for INFORMED_BY edges"},
            "Decision": {"min": 1, "description": "Accepted decisions for task context"},
            "Requirement": {"min": 0, "description": "Requirements from PRD (if extracted)"},
        },
        "required_categories": {},
        "required_relationships": [],
        "task_specific": {
            "303": {
                "Feature": "Task decomposition groups tasks by feature",
                "Decision.status=accepted": "Task context includes accepted decisions",
            },
        },
    },
    4: {
        "name": "Specification",
        "required_nodes": {
            "Task": {"min": 1, "description": "Tasks from decomposition for spec generation"},
            "Feature": {"min": 1, "description": "Features for context"},
            "Finding": {"min": 1, "description": "Findings for INFORMED_BY context"},
        },
        "required_categories": {},
        "required_relationships": [
            ("Task", "TASK_DEPENDS_ON", "Task", "Task dependency edges for topological ordering"),
        ],
        "task_specific": {
            "403": {
                "Task": "Each task gets an OpenSpec; tasks must exist in graph",
                "Task->IMPLEMENTS->Requirement": "Specs reference requirement traceability",
                "Task->INFORMED_BY->Finding": "Specs include relevant research findings",
            },
        },
    },
    5: {
        "name": "Implementation",
        "required_nodes": {
            "Task": {"min": 1, "description": "Tasks to implement"},
            "Spec": {"min": 1, "description": "OpenSpecs guiding implementation"},
        },
        "required_categories": {},
        "required_relationships": [
            ("Task", "HAS_SPEC", "Spec", "Each task must have a linked spec"),
        ],
        "task_specific": {},
    },
    6: {
        "name": "Code Review",
        "required_nodes": {
            "Task": {"min": 1, "description": "Tasks to review"},
            "Spec": {"min": 1, "description": "Specs for review criteria"},
            "Requirement": {"min": 0, "description": "Requirements for VIOLATES edges"},
        },
        "required_categories": {},
        "required_relationships": [
            ("Task", "HAS_SPEC", "Spec", "Specs define review criteria"),
        ],
        "task_specific": {},
    },
}


# ============================================================================
# VALIDATION ENGINE
# ============================================================================

def validate_graph_for_phase(graph, phase_id: str,
                              task_id: str = None) -> List[GraphDataIssue]:
    """Validate that the graph has expected data for a phase/task.

    Args:
        graph: GraphManager instance
        phase_id: Phase identifier (e.g., "2-prd")
        task_id: Optional specific task ID (e.g., "205")

    Returns:
        List of GraphDataIssue objects (also prints warnings to terminal)
    """
    if graph is None:
        issue = GraphDataIssue(
            severity="CRITICAL",
            phase=phase_id,
            description="FalkorDB graph is not available",
            expected="Active graph connection",
            actual="None",
            fix_hint="Start FalkorDB: docker start falkordb",
        )
        _print_issues([issue])
        return [issue]

    try:
        phase_num = int(phase_id.split("-")[0])
    except (ValueError, IndexError):
        logger.warning("Cannot parse phase number from '%s'", phase_id)
        return []

    expectations = PHASE_EXPECTATIONS.get(phase_num)
    if not expectations:
        return []

    issues: List[GraphDataIssue] = []

    # Check required node counts
    for label, spec in expectations.get("required_nodes", {}).items():
        min_count = spec["min"]
        try:
            actual = graph.reader.count_nodes(label)
        except Exception as e:
            issues.append(GraphDataIssue(
                severity="CRITICAL",
                phase=phase_id,
                description=f"Cannot query {label} nodes: {e}",
                expected=f">= {min_count} {label} nodes",
                actual="query failed",
            ))
            continue

        if actual < min_count:
            severity = "CRITICAL" if min_count > 0 else "WARNING"
            issues.append(GraphDataIssue(
                severity=severity,
                phase=phase_id,
                description=f"Missing {label} nodes — {spec['description']}",
                expected=f">= {min_count}",
                actual=str(actual),
                fix_hint=f"Ensure earlier phases wrote {label} nodes to graph",
            ))

    # Check required categories
    for label, categories in expectations.get("required_categories", {}).items():
        for cat, reason in categories.items():
            try:
                count = graph.reader.count_nodes(label, filters={"category": cat})
            except Exception:
                count = 0
            if count == 0:
                issues.append(GraphDataIssue(
                    severity="WARNING",
                    phase=phase_id,
                    description=f"No {label} nodes with category='{cat}'",
                    expected=f">= 1 {label}(category='{cat}')",
                    actual="0",
                    fix_hint=reason,
                ))

    # Check required relationships
    for from_label, rel_type, to_label, reason in expectations.get("required_relationships", []):
        try:
            cypher = (
                f"MATCH (:{from_label})-[:{rel_type}]->(:{to_label}) "
                f"RETURN count(*)"
            )
            result = graph.reader.raw_query(cypher)
            count = result.result_set[0][0] if result.result_set else 0
        except Exception:
            count = 0
        if count == 0:
            issues.append(GraphDataIssue(
                severity="WARNING",
                phase=phase_id,
                description=f"No {rel_type} edges from {from_label} to {to_label}",
                expected=f">= 1 {from_label}-[{rel_type}]->{to_label}",
                actual="0",
                fix_hint=reason,
            ))

    # Task-specific checks
    if task_id:
        task_checks = expectations.get("task_specific", {}).get(task_id, {})
        for check_key, reason in task_checks.items():
            if "." in check_key and "=" in check_key:
                # Property check like "Decision.status=accepted"
                parts = check_key.split(".")
                label = parts[0]
                prop_val = parts[1].split("=")
                prop, val = prop_val[0], prop_val[1]
                try:
                    count = graph.reader.count_nodes(label, filters={prop: val})
                except Exception:
                    count = 0
                if count == 0:
                    issues.append(GraphDataIssue(
                        severity="WARNING",
                        phase=phase_id,
                        description=f"No {label} nodes where {prop}='{val}'",
                        expected=f">= 1 {label}({prop}='{val}')",
                        actual="0",
                        fix_hint=reason,
                    ))
            elif "->" in check_key:
                # Relationship check like "Task->IMPLEMENTS->Requirement"
                parts = check_key.split("->")
                if len(parts) == 3:
                    fl, rt, tl = parts
                    try:
                        cypher = (
                            f"MATCH (:{fl})-[:{rt}]->(:{tl}) "
                            f"RETURN count(*)"
                        )
                        result = graph.reader.raw_query(cypher)
                        count = result.result_set[0][0] if result.result_set else 0
                    except Exception:
                        count = 0
                    if count == 0:
                        issues.append(GraphDataIssue(
                            severity="WARNING",
                            phase=phase_id,
                            description=f"No {rt} edges ({fl} -> {tl})",
                            expected=f">= 1 {fl}-[{rt}]->{tl}",
                            actual="0",
                            fix_hint=reason,
                        ))
            else:
                # Simple node existence check
                try:
                    count = graph.reader.count_nodes(check_key)
                except Exception:
                    count = 0
                if count == 0:
                    issues.append(GraphDataIssue(
                        severity="WARNING",
                        phase=phase_id,
                        description=f"No {check_key} nodes in graph",
                        expected=f">= 1 {check_key}",
                        actual="0",
                        fix_hint=reason,
                    ))

    if issues:
        _print_issues(issues)

    return issues


def _print_issues(issues: List[GraphDataIssue]) -> None:
    """Print graph data issues with extremely visible terminal formatting."""
    try:
        from core.utils.cli_ui import (
            print_red, print_yellow, print_bold, print_dim,
        )
    except ImportError:
        print_red = print_yellow = print_bold = print_dim = str

    critical = [i for i in issues if i.severity == "CRITICAL"]
    warnings = [i for i in issues if i.severity == "WARNING"]
    infos = [i for i in issues if i.severity == "INFO"]

    if critical:
        print()
        print(print_red("=" * 80))
        print(print_red("  GRAPH DATA VALIDATION FAILED"))
        print(print_red("=" * 80))
        for issue in critical:
            print(print_red(f"  CRITICAL: {issue.description}"))
            print(print_red(f"    Expected: {issue.expected}"))
            print(print_red(f"    Actual:   {issue.actual}"))
            if issue.fix_hint:
                print(print_yellow(f"    Fix: {issue.fix_hint}"))
        print(print_red("=" * 80))
        print()

    if warnings:
        print()
        print(print_yellow("  " + "-" * 60))
        print(print_yellow("  GRAPH DATA GAPS DETECTED"))
        print(print_yellow("  " + "-" * 60))
        for issue in warnings:
            print(print_yellow(f"  WARNING: {issue.description}"))
            print(print_dim(f"    Expected: {issue.expected} | Actual: {issue.actual}"))
            if issue.fix_hint:
                print(print_dim(f"    Hint: {issue.fix_hint}"))
        print(print_yellow("  " + "-" * 60))
        print()

    if infos:
        for issue in infos:
            print(print_dim(f"  INFO: {issue.description}"))

    # Log all issues
    for issue in issues:
        if issue.severity == "CRITICAL":
            logger.error("Graph validation [%s]: %s (expected=%s, actual=%s)",
                         issue.phase, issue.description, issue.expected, issue.actual)
        elif issue.severity == "WARNING":
            logger.warning("Graph validation [%s]: %s (expected=%s, actual=%s)",
                           issue.phase, issue.description, issue.expected, issue.actual)
        else:
            logger.info("Graph validation [%s]: %s", issue.phase, issue.description)
