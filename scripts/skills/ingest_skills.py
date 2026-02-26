#!/usr/bin/env python3
"""
Skill Catalog Ingestion Pipeline

Reads the skill catalog, resolves the active profile, and ingests all
skills into FalkorDB as Skill nodes with SDLCPhase linkage.

Usage:
    python scripts/skills/ingest_skills.py
    python scripts/skills/ingest_skills.py --catalog-file /path/to/catalog.json
    python scripts/skills/ingest_skills.py --profile cloud_full

The script is idempotent: it uses MERGE (not CREATE) for all nodes and edges.
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

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.graph import get_graph, GraphUnavailableError  # noqa: E402
from core.graph.schema import NodeLabel, RelType  # noqa: E402
from core.skills.catalog import SKILL_CATALOG  # noqa: E402
from core.skills.models import PROFILE_SKILL_RULES  # noqa: E402

logger = logging.getLogger(__name__)

# SDLC phase definitions are derived from the catalog skills' sdlc_phases.
# Kept here for SDLCPhase node creation in the graph.
_SDLC_PHASES = {
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

# Known skill compositions: pairs of skills that work well together.
# Each entry is (skill_a_id, skill_b_id, co_occurrence_count, avg_combined_success).
# These are seeded into COMPOSES_WITH edges; runtime discovery happens via
# core.skills.learning.SkillLearning.discover_compositions().
KNOWN_COMPOSITIONS = [
    # Formatting + validation is a common pairing
    ("fmt-markdown", "validate-yaml", 15, 0.92),
    ("fmt-markdown", "validate-json", 12, 0.89),
    # Git operations compose naturally
    ("git-commit-msg", "git-branch-naming", 20, 0.95),
    # Testing + security
    ("test-coverage", "security-scan", 8, 0.85),
    # Doc generation + validation
    ("doc-gen-readme", "validate-markdown", 10, 0.90),
]


def resolve_active_profile(override: str = None) -> str:
    """
    Resolve the active environment profile.

    Priority:
    1. Explicit override from --profile argument
    2. .claude/active-profile.yaml file
    3. ATOMIC_PROFILE environment variable
    4. Default: "cloud_full"
    """
    import os

    if override:
        return override

    # Try .claude/active-profile.yaml
    profile_path = PROJECT_ROOT / ".claude" / "active-profile.yaml"
    if profile_path.exists():
        try:
            with open(profile_path) as f:
                data = yaml.safe_load(f)
            if data and isinstance(data, dict) and "profile" in data:
                return data["profile"]
        except Exception as e:
            logger.debug("Failed to read active-profile.yaml: %s", e)

    # Try environment variable
    env_profile = os.environ.get("ATOMIC_PROFILE")
    if env_profile:
        return env_profile

    return "cloud_full"


def load_skill_catalog(catalog_file: str = None) -> list:
    """
    Load the skill catalog from a file or from core.skills.catalog.

    Args:
        catalog_file: Optional path to a JSON catalog file.

    Returns:
        List of skill dicts.
    """
    if catalog_file:
        path = Path(catalog_file)
        if not path.exists():
            print(f"ERROR: Catalog file not found: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else data.get("skills", [])

    # Import from core.skills.catalog (the single source of truth)
    try:
        from core.skills.catalog import SKILL_CATALOG as catalog
        # Convert SkillMetadata instances to dicts for graph ingestion
        return [s.model_dump() if hasattr(s, "model_dump") else s for s in catalog]
    except ImportError:
        pass

    # Try loading from a default JSON location as last resort
    default_paths = [
        PROJECT_ROOT / "scripts" / "skills" / "skill_catalog.json",
        PROJECT_ROOT / "config" / "skill_catalog.json",
        PROJECT_ROOT / "skills" / "skill_catalog.json",
    ]
    for path in default_paths:
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            return data if isinstance(data, list) else data.get("skills", [])

    print("WARNING: No skill catalog found. Using empty catalog.", file=sys.stderr)
    print("  Searched:", file=sys.stderr)
    for p in default_paths:
        print(f"    {p}", file=sys.stderr)
    return []


def ingest(catalog_file: str = None, profile_override: str = None,
           verbose: bool = False):
    """
    Main ingestion pipeline.
    """
    profile = resolve_active_profile(profile_override)
    print(f"Active profile: {profile}")

    # Load catalog
    skills = load_skill_catalog(catalog_file)
    print(f"Loaded {len(skills)} skills from catalog")

    if not skills:
        print("No skills to ingest. Exiting.")
        return

    # Connect to FalkorDB
    print("Connecting to FalkorDB...")
    graph = get_graph(phase_id="skill-ingest")
    conn = graph.conn
    print(f"Connected: {conn}")

    # Step 1: Create SDLCPhase nodes (0-9)
    print("\n--- Creating SDLCPhase nodes ---")
    for phase_num, phase_name in _SDLC_PHASES.items():
        phase_id = f"phase-{phase_num}"
        cypher = (
            "MERGE (p:SDLCPhase {id: $id}) "
            "SET p.name = $name, p.phase_number = $num"
        )
        conn.query(cypher, {"id": phase_id, "name": phase_name, "num": phase_num})
        if verbose:
            print(f"  Phase {phase_num}: {phase_name}")
    print(f"  Created/updated {len(_SDLC_PHASES)} SDLCPhase nodes")

    # Step 2: Ingest skills
    print("\n--- Ingesting Skill nodes ---")
    ingested = 0
    phase_edges = 0

    for skill in skills:
        skill_id = skill.get("id", "")
        if not skill_id:
            logger.warning("Skipping skill with no id: %s", skill)
            continue

        # Compute installable profiles using core model method
        installable = skill.get("installable_in_profiles")
        if callable(installable):
            installable = installable()
        if not installable:
            # Fallback: compute from PROFILE_SKILL_RULES
            from core.skills.models import SkillMetadata as _SM
            try:
                sm = _SM(**{k: v for k, v in skill.items()
                           if k in _SM.model_fields})
                installable = sm.installable_in_profiles()
            except Exception:
                installable = ["cloud_full", "development"]

        installable_csv = ",".join(installable)

        # Determine installed/blocked for current profile
        is_installed = profile in installable
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

        # MERGE skill node (idempotent)
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
        conn.query(cypher_skill, props)

        # Create BELONGS_TO edges to relevant phases
        phases = skill.get("sdlc_phases") or skill.get("phases", [])
        for phase_num in phases:
            phase_id = f"phase-{phase_num}"
            cypher_bt = (
                "MATCH (s:Skill {id: $skill_id}), (p:SDLCPhase {id: $phase_id}) "
                "MERGE (s)-[:BELONGS_TO]->(p)"
            )
            conn.query(cypher_bt, {"skill_id": skill_id, "phase_id": phase_id})
            phase_edges += 1

        ingested += 1
        if verbose:
            status = "installed" if is_installed else f"blocked ({blocked_by})"
            print(f"  [{ingested}] {skill_id}: {skill.get('name', '')} [{status}]")
        elif ingested % 25 == 0:
            print(f"  ... {ingested}/{len(skills)} skills ingested")

    print(f"  Ingested {ingested} skill nodes, {phase_edges} BELONGS_TO edges")

    # Step 3: Create known composition edges
    print("\n--- Creating composition edges ---")
    comp_count = 0
    for skill_a, skill_b, co_occur, avg_success in KNOWN_COMPOSITIONS:
        cypher_comp = (
            "MATCH (a:Skill {id: $a_id}), (b:Skill {id: $b_id}) "
            "MERGE (a)-[r:COMPOSES_WITH]->(b) "
            "SET r.co_occurrence = $co_occur, "
            "r.avg_combined_success = $avg_success"
        )
        try:
            conn.query(cypher_comp, {
                "a_id": skill_a,
                "b_id": skill_b,
                "co_occur": co_occur,
                "avg_success": avg_success,
            })
            comp_count += 1
            if verbose:
                print(f"  {skill_a} --COMPOSES_WITH--> {skill_b}")
        except Exception as e:
            # Skills might not exist in catalog yet
            logger.debug("Skipping composition %s->%s: %s", skill_a, skill_b, e)

    print(f"  Created {comp_count} COMPOSES_WITH edges")

    # Step 4: Ensure indexes
    print("\n--- Ensuring indexes ---")
    graph.writer.ensure_indexes()
    print("  All indexes created/verified")

    # Step 5: Verification summary
    print("\n=== Verification Summary ===")
    counts = {}
    for label in ["Skill", "SDLCPhase", "Episode", "Workflow"]:
        cypher = f"MATCH (n:{label}) RETURN count(n)"
        result = conn.query(cypher)
        counts[label] = result.result_set[0][0] if result.result_set else 0
        print(f"  {label} nodes: {counts[label]}")

    # Installed vs blocked
    cypher_inst = "MATCH (s:Skill) WHERE s.installed = true RETURN count(s)"
    result = conn.query(cypher_inst)
    installed = result.result_set[0][0] if result.result_set else 0

    cypher_blk = "MATCH (s:Skill) WHERE s.blocked_by_profile <> '' RETURN count(s)"
    result = conn.query(cypher_blk)
    blocked = result.result_set[0][0] if result.result_set else 0

    print(f"  Skills installed: {installed}")
    print(f"  Skills blocked: {blocked}")

    # Edge counts
    cypher_bt = "MATCH ()-[r:BELONGS_TO]->() RETURN count(r)"
    result = conn.query(cypher_bt)
    bt_count = result.result_set[0][0] if result.result_set else 0
    print(f"  BELONGS_TO edges: {bt_count}")

    cypher_cw = "MATCH ()-[r:COMPOSES_WITH]->() RETURN count(r)"
    result = conn.query(cypher_cw)
    cw_count = result.result_set[0][0] if result.result_set else 0
    print(f"  COMPOSES_WITH edges: {cw_count}")

    print(f"\nIngestion complete. Profile: {profile}")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest skill catalog into FalkorDB graph"
    )
    parser.add_argument(
        "--catalog-file",
        help="Path to skill catalog JSON file (default: auto-detect)",
    )
    parser.add_argument(
        "--profile",
        help="Override environment profile (default: auto-detect, fallback: cloud_full)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print details for each skill",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    try:
        ingest(
            catalog_file=args.catalog_file,
            profile_override=args.profile,
            verbose=args.verbose,
        )
    except GraphUnavailableError as e:
        print(f"ERROR: FalkorDB unavailable: {e}", file=sys.stderr)
        print("  Make sure FalkorDB is running: docker compose up -d falkordb",
              file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
