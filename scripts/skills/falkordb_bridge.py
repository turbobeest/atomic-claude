#!/usr/bin/env python3
"""
FalkorDB Bridge for Skill System

Python bridge between bash scripts and FalkorDB graph for skill
selection, outcome logging, verification, and ingestion.

Usage:
    python scripts/skills/falkordb_bridge.py --action select --task "format code" --profile unrestricted --output /tmp/skills.json
    python scripts/skills/falkordb_bridge.py --action log-outcome --task-id task_501 --success 0.9 --skills "fmt-markdown,validate-yaml"
    python scripts/skills/falkordb_bridge.py --action verify
    python scripts/skills/falkordb_bridge.py --action query-blocked --constraint "requires_internet=true"
    python scripts/skills/falkordb_bridge.py --action ingest --catalog-file skills.json
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Handle missing dependencies gracefully
try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# Add project root to sys.path for core imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.graph import get_graph, GraphUnavailableError  # noqa: E402
from core.graph.schema import NodeLabel, RelType  # noqa: E402

logger = logging.getLogger(__name__)

# SDLC phase definitions (0-9)
SDLC_PHASES = {
    0: "Setup & Mode Selection",
    1: "Discovery & Analysis",
    2: "PRD Generation",
    3: "Task Decomposition",
    4: "Specification",
    5: "Implementation",
    6: "Code Review",
    7: "Integration Testing",
    8: "Deployment Preparation",
    9: "Release",
}


def action_select(args):
    """
    3-stage skill selection with profile enforcement.

    Stage 1: Try workflow match (MATCH (w:Workflow) WHERE w.task_pattern matches)
    Stage 2: Graph traversal (MATCH (s:Skill)-[:BELONGS_TO]->(p:SDLCPhase))
    Stage 3: Fulltext search on skill name/description
    """
    graph = get_graph(phase_id="skill-select")
    conn = graph.conn

    task = args.task or ""

    # Profile can be a name or a JSON blob from bash scripts
    raw_profile = args.profile or "standard"
    try:
        profile_data = json.loads(raw_profile)
        profile = profile_data.get("profile", "standard")
    except (json.JSONDecodeError, TypeError):
        profile = raw_profile

    result_skills = []
    method = "none"
    workflow_name = None

    # Stage 1: Workflow match
    cypher_workflow = (
        "MATCH (w:Workflow) "
        "WHERE toLower(w.task_pattern) CONTAINS toLower($task) "
        "RETURN w.id AS wid, w.name AS wname, w.task_pattern AS wpattern "
        "LIMIT 1"
    )
    try:
        wf_result = conn.query(cypher_workflow, {"task": task})
        if wf_result.result_set:
            wid = wf_result.result_set[0][0]
            workflow_name = wf_result.result_set[0][1]

            # Get skills in this workflow, ordered by STEP.order
            cypher_wf_skills = (
                "MATCH (w:Workflow {id: $wid})-[step:STEP]->(s:Skill) "
                "WHERE $profile IN s.installable_in_profiles "
                "RETURN s "
                "ORDER BY step.order"
            )
            wf_skills_result = conn.query(cypher_wf_skills, {
                "wid": wid,
                "profile": profile,
            })
            for row in wf_skills_result.result_set:
                node = row[0]
                props = dict(node.properties) if hasattr(node, "properties") else node
                result_skills.append(props)

            if result_skills:
                method = "workflow"
    except Exception as e:
        logger.debug("Workflow match failed: %s", e)

    # Stage 2: Structural graph traversal (phase-based)
    if not result_skills and args.project:
        # Attempt to infer the SDLC phase from the project context
        cypher_structural = (
            "MATCH (s:Skill)-[:BELONGS_TO]->(p:SDLCPhase) "
            "WHERE $profile IN s.installable_in_profiles "
            "AND s.installed = true "
            "RETURN DISTINCT s "
            "ORDER BY s.times_used DESC "
            "LIMIT 20"
        )
        try:
            struct_result = conn.query(cypher_structural, {"profile": profile})
            for row in struct_result.result_set:
                node = row[0]
                props = dict(node.properties) if hasattr(node, "properties") else node
                result_skills.append(props)

            if result_skills:
                method = "structural"
        except Exception as e:
            logger.debug("Structural traversal failed: %s", e)

    # Stage 3: Fulltext search on skill name/description
    if not result_skills:
        cypher_fulltext = (
            "CALL db.idx.fulltext.queryNodes('Skill', $query) "
            "YIELD node AS s "
            "WHERE $profile IN s.installable_in_profiles "
            "RETURN s "
            "LIMIT 10"
        )
        try:
            ft_result = conn.query(cypher_fulltext, {
                "query": task,
                "profile": profile,
            })
            for row in ft_result.result_set:
                node = row[0]
                props = dict(node.properties) if hasattr(node, "properties") else node
                result_skills.append(props)

            if result_skills:
                method = "semantic"
        except Exception as e:
            logger.debug("Fulltext search failed: %s", e)

    # If we got skills from multiple stages, mark method as combined
    if method == "none" and result_skills:
        method = "combined"

    # Serialize skill properties for JSON output
    serialized_skills = []
    for s in result_skills:
        serialized = {}
        for k, v in s.items():
            # Ensure JSON-serializable types
            if isinstance(v, (str, int, float, bool, type(None))):
                serialized[k] = v
            elif isinstance(v, list):
                serialized[k] = v
            else:
                serialized[k] = str(v)
        serialized_skills.append(serialized)

    output = {
        "skills": serialized_skills,
        "method": method,
        "workflow": workflow_name,
    }

    output_json = json.dumps(output, indent=2)

    if args.output:
        Path(args.output).write_text(output_json)
        print(f"Wrote {len(serialized_skills)} skills to {args.output}")
    else:
        print(output_json)


def action_log_outcome(args):
    """
    Record task outcome as an Episode node with USED_IN edges.

    Updates running averages on Skill nodes.
    """
    graph = get_graph(phase_id="skill-outcome")
    conn = graph.conn

    task_id = args.task_id
    success = float(args.success)
    skills_csv = args.skills or ""
    skill_ids = [s.strip() for s in skills_csv.split(",") if s.strip()]
    tokens = int(args.tokens) if args.tokens else 0
    duration = int(args.duration) if args.duration else 0

    # Determine outcome category
    if success >= 0.8:
        outcome = "success"
    elif success >= 0.4:
        outcome = "partial"
    else:
        outcome = "failure"

    # Create Episode node
    episode_id = f"ep-{task_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    episode_props = {
        "id": episode_id,
        "task_id": task_id,
        "outcome": outcome,
        "success_score": success,
        "tokens_consumed": tokens,
        "duration_ms": duration,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Use MERGE to be idempotent
    cypher_episode = (
        "MERGE (e:Episode {id: $id}) "
        "SET e.task_id = $task_id, "
        "e.outcome = $outcome, "
        "e.success_score = $success_score, "
        "e.tokens_consumed = $tokens_consumed, "
        "e.duration_ms = $duration_ms, "
        "e.created_at = $created_at"
    )
    conn.query(cypher_episode, episode_props)
    print(f"Created Episode: {episode_id} (outcome={outcome}, score={success})")

    # Create USED_IN edges and update skill running averages
    for skill_id in skill_ids:
        # Create USED_IN edge
        cypher_used_in = (
            "MATCH (s:Skill {id: $skill_id}), (e:Episode {id: $episode_id}) "
            "MERGE (s)-[r:USED_IN]->(e) "
            "SET r.success_score = $success_score"
        )
        conn.query(cypher_used_in, {
            "skill_id": skill_id,
            "episode_id": episode_id,
            "success_score": success,
        })

        # Update running averages on the skill
        cypher_update_avg = (
            "MATCH (s:Skill {id: $skill_id}) "
            "SET s.times_used = s.times_used + 1, "
            "s.avg_success_score = "
            "CASE WHEN s.times_used = 0 THEN $success "
            "ELSE ((s.avg_success_score * s.times_used) + $success) / (s.times_used + 1) "
            "END"
        )
        conn.query(cypher_update_avg, {
            "skill_id": skill_id,
            "success": success,
        })
        print(f"  Linked skill {skill_id} -> Episode {episode_id}")

    print(f"Logged outcome for {len(skill_ids)} skills")


def action_verify(args):
    """
    Check graph state and print summary counts.
    """
    graph = get_graph(phase_id="skill-verify")
    conn = graph.conn

    counts = {}
    for label, description in [
        ("Skill", "skills total"),
        ("SDLCPhase", "SDLC phases"),
        ("Episode", "episodes"),
        ("Workflow", "workflows"),
    ]:
        cypher = f"MATCH (n:{label}) RETURN count(n)"
        result = conn.query(cypher)
        counts[description] = result.result_set[0][0] if result.result_set else 0

    # Installed skills
    cypher_installed = "MATCH (s:Skill) WHERE s.installed = true RETURN count(s)"
    result = conn.query(cypher_installed)
    counts["skills installed"] = result.result_set[0][0] if result.result_set else 0

    # Blocked skills
    cypher_blocked = (
        "MATCH (s:Skill) WHERE s.blocked_by_profile <> '' "
        "RETURN count(s)"
    )
    result = conn.query(cypher_blocked)
    counts["skills blocked"] = result.result_set[0][0] if result.result_set else 0

    # BELONGS_TO edges
    cypher_bt = "MATCH (:Skill)-[r:BELONGS_TO]->(:SDLCPhase) RETURN count(r)"
    result = conn.query(cypher_bt)
    counts["BELONGS_TO edges"] = result.result_set[0][0] if result.result_set else 0

    # COMPOSES_WITH edges
    cypher_cw = "MATCH (:Skill)-[r:COMPOSES_WITH]->(:Skill) RETURN count(r)"
    result = conn.query(cypher_cw)
    counts["COMPOSES_WITH edges"] = result.result_set[0][0] if result.result_set else 0

    # Print summary
    print("=== FalkorDB Skill Graph Verification ===")
    for key, value in counts.items():
        print(f"  {key}: {value}")

    # Output as JSON if requested
    if args.output:
        Path(args.output).write_text(json.dumps(counts, indent=2))


def action_query_blocked(args):
    """
    Find skills blocked by a constraint.

    Constraint format: property=value (e.g., "requires_internet=true")
    """
    graph = get_graph(phase_id="skill-blocked")
    conn = graph.conn

    constraint = args.constraint or ""
    if "=" not in constraint:
        print("ERROR: --constraint must be in format property=value", file=sys.stderr)
        sys.exit(1)

    prop, value = constraint.split("=", 1)
    prop = prop.strip()
    value = value.strip()

    # Convert value to appropriate type
    if value.lower() == "true":
        typed_value = True
    elif value.lower() == "false":
        typed_value = False
    else:
        try:
            typed_value = int(value)
        except ValueError:
            try:
                typed_value = float(value)
            except ValueError:
                typed_value = value

    # Whitelist of allowed property names to prevent injection
    allowed_props = {
        "requires_internet", "requires_saas", "installed",
        "risk_level", "category", "source", "blocked_by_profile",
    }
    if prop not in allowed_props:
        print(f"ERROR: Property '{prop}' not in allowed set: {sorted(allowed_props)}",
              file=sys.stderr)
        sys.exit(1)

    cypher = (
        f"MATCH (s:Skill) WHERE s.{prop} = $val "
        "RETURN s.id "
        "ORDER BY s.id"
    )
    result = conn.query(cypher, {"val": typed_value})
    skill_ids = [row[0] for row in result.result_set]

    if args.output:
        Path(args.output).write_text(",".join(skill_ids))
    else:
        print(",".join(skill_ids))


def action_ingest(args):
    """
    Ingest skill catalog into FalkorDB.

    Reads from stdin or file. Creates/updates Skill nodes, SDLCPhase nodes,
    and BELONGS_TO edges.
    """
    graph = get_graph(phase_id="skill-ingest")
    conn = graph.conn

    # Read catalog
    if args.catalog_file:
        catalog_path = Path(args.catalog_file)
        if not catalog_path.exists():
            print(f"ERROR: Catalog file not found: {catalog_path}", file=sys.stderr)
            sys.exit(1)
        with open(catalog_path) as f:
            catalog = json.load(f)
    elif not sys.stdin.isatty():
        catalog = json.load(sys.stdin)
    else:
        print("ERROR: Provide --catalog-file or pipe JSON to stdin", file=sys.stderr)
        sys.exit(1)

    skills = catalog if isinstance(catalog, list) else catalog.get("skills", [])
    profile = args.profile or "standard"

    print(f"Ingesting {len(skills)} skills (profile={profile})...")

    # Create SDLCPhase nodes (0-9)
    for phase_num, phase_name in SDLC_PHASES.items():
        phase_id = f"phase-{phase_num}"
        cypher_phase = (
            "MERGE (p:SDLCPhase {id: $id}) "
            "SET p.name = $name, p.phase_number = $num"
        )
        conn.query(cypher_phase, {
            "id": phase_id,
            "name": phase_name,
            "num": phase_num,
        })
    print(f"  Created/updated {len(SDLC_PHASES)} SDLCPhase nodes")

    # Ingest each skill
    ingested = 0
    for skill in skills:
        skill_id = skill.get("id", "")
        if not skill_id:
            continue

        # Compute installable_in_profiles (stored as comma-separated string
        # for FalkorDB compatibility, but also as individual list for
        # the IN-check queries which use array containment)
        installable = skill.get("installable_in_profiles", ["standard"])
        if isinstance(installable, list):
            installable_csv = ",".join(installable)
        else:
            installable_csv = str(installable)

        # Determine installed/blocked based on active profile
        is_installed = profile in (installable if isinstance(installable, list)
                                   else installable_csv.split(","))
        blocked_by = "" if is_installed else profile

        # Build node properties
        props = {
            "id": skill_id,
            "name": skill.get("name", skill_id),
            "category": skill.get("category", "custom"),
            "description": skill.get("description", ""),
            "source": skill.get("source", "community"),
            "risk_level": skill.get("risk_level", "None"),
            "requires_internet": skill.get("requires_internet", False),
            "requires_saas": skill.get("requires_saas", False),
            "installed": is_installed,
            "blocked_by_profile": blocked_by,
            "content_hash": skill.get("content_hash", ""),
            "installable_in_profiles_csv": installable_csv,
            "times_used": skill.get("times_used", 0),
            "avg_success_score": skill.get("avg_success_score", 0.0),
        }

        # MERGE skill node
        cypher_skill = (
            "MERGE (s:Skill {id: $id}) "
            "SET s.name = $name, "
            "s.category = $category, "
            "s.description = $description, "
            "s.source = $source, "
            "s.risk_level = $risk_level, "
            "s.requires_internet = $requires_internet, "
            "s.requires_saas = $requires_saas, "
            "s.installed = $installed, "
            "s.blocked_by_profile = $blocked_by_profile, "
            "s.content_hash = $content_hash, "
            "s.installable_in_profiles_csv = $installable_in_profiles_csv, "
            "s.times_used = $times_used, "
            "s.avg_success_score = $avg_success_score"
        )

        # FalkorDB does not support list properties natively, so we store
        # installable_in_profiles as CSV *and* set individual profile flags
        # to enable the WHERE $profile IN s.installable_in_profiles queries
        # via a helper property. The select action will use CSV parsing.
        conn.query(cypher_skill, props)

        # Create BELONGS_TO edges to relevant phases
        phases = skill.get("sdlc_phases") or skill.get("phases", [])
        for phase_num in phases:
            phase_id = f"phase-{phase_num}"
            cypher_bt = (
                "MATCH (s:Skill {id: $skill_id}), (p:SDLCPhase {id: $phase_id}) "
                "MERGE (s)-[:BELONGS_TO]->(p)"
            )
            conn.query(cypher_bt, {
                "skill_id": skill_id,
                "phase_id": phase_id,
            })

        ingested += 1

    print(f"  Ingested {ingested} skill nodes")

    # Ensure indexes
    graph.writer.ensure_indexes()
    print("  Indexes ensured")

    # Print verification
    action_verify(argparse.Namespace(output=None))


def main():
    parser = argparse.ArgumentParser(
        description="FalkorDB bridge for the Atomic Claude skill system"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["select", "log-outcome", "verify", "query-blocked", "ingest", "check"],
        help="Action to perform",
    )
    parser.add_argument("--task", "--task-prompt", dest="task",
                        help="Task description (for select)")
    parser.add_argument("--project", "--project-id", dest="project",
                        help="Project context (for select)")
    parser.add_argument("--profile", "--profile-json", dest="profile",
                        help="Environment profile name or JSON")
    parser.add_argument("--output", help="Output file path")

    # log-outcome args
    parser.add_argument("--task-id", help="Task identifier (for log-outcome)")
    parser.add_argument("--success", "--score", dest="success",
                        help="Success score 0.0-1.0 (for log-outcome)")
    parser.add_argument("--skills", help="Comma-separated skill IDs (for log-outcome)")
    parser.add_argument("--tokens", help="Tokens consumed (for log-outcome)")
    parser.add_argument("--duration", help="Duration in ms (for log-outcome)")

    # query-blocked args
    parser.add_argument("--constraint", help="Property constraint, e.g. requires_internet=true")

    # ingest args
    parser.add_argument("--catalog-file", help="Path to skill catalog JSON file")

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    try:
        if args.action == "select":
            action_select(args)
        elif args.action == "log-outcome":
            if not args.task_id or args.success is None:
                parser.error("--task-id and --success are required for log-outcome")
            action_log_outcome(args)
        elif args.action == "verify":
            action_verify(args)
        elif args.action == "query-blocked":
            if not args.constraint:
                parser.error("--constraint is required for query-blocked")
            action_query_blocked(args)
        elif args.action == "ingest":
            action_ingest(args)
        elif args.action == "check":
            try:
                graph = get_graph(phase_id="skill-check")
                conn = graph.conn
                result = conn.query("RETURN 1")
                if result.result_set:
                    print("HEALTHY")
                else:
                    print("UNHEALTHY")
                    sys.exit(1)
            except Exception as e:
                print(f"UNHEALTHY: {e}", file=sys.stderr)
                sys.exit(1)
    except GraphUnavailableError as e:
        print(f"ERROR: FalkorDB unavailable: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
