#!/usr/bin/env python3
"""
consolidate_skills.py — Nightly skill consolidation for Atomic Claude.

Runs on cron or manually to maintain skill graph hygiene:
  1. Crystallize workflows — promote recurring skill sequences to Workflow nodes
  2. Decay unused skills — reduce relevance of stale skills
  3. Prune weak edges — remove low-value COMPOSES_WITH edges
  4. Hash check — compare manifest content_hash against graph nodes
  5. Profile re-evaluation — re-compute blocked skills for active profile

Usage:
    python3 scripts/skills/consolidate_skills.py
    python3 scripts/skills/consolidate_skills.py --dry-run
"""

import argparse
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Project root ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MANIFEST_PATH = PROJECT_ROOT / ".claude" / "skills" / "_manifest.yaml"
PROFILES_YAML = PROJECT_ROOT / "config" / "environment-profiles.yaml"
ACTIVE_PROFILE_YAML = PROJECT_ROOT / ".claude" / "active-profile.yaml"

# ── Optional imports with graceful fallback ───────────────────────────────────
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

HAS_GRAPH = False
graph_conn = None

try:
    from core.graph import GraphConnection, GraphUnavailableError
    HAS_GRAPH = True
except ImportError:
    pass


def get_connection():
    """Get a FalkorDB connection, or None if unavailable."""
    global graph_conn
    if not HAS_GRAPH:
        return None
    if graph_conn is not None:
        return graph_conn
    try:
        graph_conn = GraphConnection.get()
        return graph_conn
    except Exception:
        return None


def get_skills_graph():
    """Get the skills graph handle, or None."""
    conn = get_connection()
    if conn is None:
        return None
    try:
        # Skills live in the main atomic-claude graph alongside other nodes
        return conn
    except Exception:
        return None


# ── YAML helpers (works with or without PyYAML) ──────────────────────────────

def read_yaml_file(path):
    """Read a YAML file, returning a dict. Uses PyYAML if available, else minimal parser."""
    if not path.exists():
        return None
    with open(path) as f:
        content = f.read()
    if HAS_YAML:
        return yaml.safe_load(content)
    # Minimal fallback parser for simple YAML structures
    return _minimal_yaml_parse(content)


def _minimal_yaml_parse(content):
    """Minimal YAML parser for flat and one-level-nested structures."""
    result = {}
    current_key = None
    current_dict = None

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Top-level key: value
        m = re.match(r"^(\w[\w_-]*):\s*(.*)?$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip() if m.group(2) else ""
            if val and not val.startswith("{"):
                result[key] = _parse_yaml_value(val)
                current_key = None
                current_dict = None
            elif not val or val == "{}":
                result[key] = {}
                current_key = key
                current_dict = result[key]
            continue

        # Nested key (2-space indent)
        m = re.match(r"^  (\w[\w_-]*):\s*(.*)?$", line)
        if m and current_key is not None:
            nested_key = m.group(1)
            nested_val = m.group(2).strip() if m.group(2) else ""
            if nested_val:
                current_dict[nested_key] = _parse_yaml_value(nested_val)
            else:
                current_dict[nested_key] = {}
            continue

        # Deeper nesting (4-space indent)
        m = re.match(r"^    (\w[\w_-]*):\s*(.+)$", line)
        if m and current_key is not None:
            # Find the last nested dict
            nested_key = m.group(1)
            nested_val = m.group(2).strip()
            for k in reversed(list(current_dict.keys())):
                if isinstance(current_dict[k], dict):
                    current_dict[k][nested_key] = _parse_yaml_value(nested_val)
                    break

    return result


def _parse_yaml_value(val):
    """Parse a simple YAML value."""
    val = val.strip()
    if val in ("true", "True"):
        return True
    if val in ("false", "False"):
        return False
    if val in ("null", "~", ""):
        return None
    if val.startswith("[") and val.endswith("]"):
        items = val[1:-1].split(",")
        return [i.strip().strip('"').strip("'") for i in items if i.strip()]
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    if val.startswith("'") and val.endswith("'"):
        return val[1:-1]
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


# ============================================================================
# CONSOLIDATION STEPS
# ============================================================================

class ConsolidationReport:
    """Collects actions taken (or would-be-taken in dry-run)."""

    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.actions = []
        self.warnings = []

    def action(self, category, description):
        prefix = "[DRY-RUN] " if self.dry_run else ""
        self.actions.append(f"{prefix}[{category}] {description}")

    def warn(self, description):
        self.warnings.append(f"[WARN] {description}")

    def print_summary(self):
        print("")
        print("=" * 60)
        print(" Skill Consolidation Summary")
        if self.dry_run:
            print(" (DRY RUN — no changes applied)")
        print("=" * 60)
        print("")

        if self.actions:
            print(f"Actions ({len(self.actions)}):")
            for a in self.actions:
                print(f"  {a}")
        else:
            print("No actions taken.")

        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  {w}")

        print("")


# ── Step 1: Crystallize Workflows ─────────────────────────────────────────────

def crystallize_workflows(conn, report):
    """
    Find sequences of 3+ skills used together successfully at least 3 times.
    Promote to Workflow nodes.

    Looks at Episode nodes (task execution records) that reference skill IDs.
    A "workflow" is a set of skills that co-occur in the same Episode.
    """
    print("[1/5] Crystallize workflows...")

    try:
        # Find Episode nodes with skill references
        result = conn.query(
            "MATCH (e:Episode) "
            "WHERE e.skills_used IS NOT NULL AND e.success_score IS NOT NULL "
            "RETURN e.skills_used, toFloat(e.success_score) AS score"
        )
    except Exception as e:
        report.warn(f"No Episode nodes found or query failed: {e}")
        print("  Skipped: No Episode data available.")
        return

    if not result.result_set:
        print("  No Episode data found.")
        return

    # Count co-occurring skill sets (only successful episodes, score >= 0.7)
    sequence_counts = Counter()
    for row in result.result_set:
        skills_csv = row[0]
        score = float(row[1]) if row[1] is not None else 0.0
        if score < 0.7:
            continue

        skills = sorted([s.strip() for s in skills_csv.split(",") if s.strip()])
        if len(skills) >= 3:
            # Use frozenset for unordered comparison
            key = tuple(skills)
            sequence_counts[key] += 1

    # Promote sequences seen >= 3 times
    promoted = 0
    for skill_tuple, count in sequence_counts.items():
        if count < 3:
            continue

        workflow_id = "wf-" + hashlib.md5(",".join(skill_tuple).encode()).hexdigest()[:12]
        workflow_name = f"Auto-workflow ({len(skill_tuple)} skills, {count} uses)"

        # Check if workflow already exists
        try:
            existing = conn.query(
                "MATCH (w:Workflow {id: $wid}) RETURN w.id",
                {"wid": workflow_id},
            )
            if existing.result_set:
                continue
        except Exception:
            pass

        report.action("crystallize", f"Promote workflow {workflow_id}: {', '.join(skill_tuple)}")

        if not report.dry_run:
            try:
                conn.query(
                    "CREATE (:Workflow {"
                    "  id: $wid, name: $name, skills_csv: $skills,"
                    "  occurrence_count: $count, created_at: $ts"
                    "})",
                    {
                        "wid": workflow_id,
                        "name": workflow_name,
                        "skills": ",".join(skill_tuple),
                        "count": count,
                        "ts": datetime.now(timezone.utc).isoformat(),
                    },
                )
                promoted += 1
            except Exception as e:
                report.warn(f"Failed to create workflow {workflow_id}: {e}")

    print(f"  Workflows promoted: {promoted}")


# ── Step 2: Decay Unused Skills ───────────────────────────────────────────────

def decay_unused_skills(conn, report):
    """
    For skills not used in 30+ days, reduce avg_success_score by 5% (multiply by 0.95).
    """
    print("[2/5] Decay unused skills...")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    try:
        # Find skills with a last_used timestamp older than 30 days
        # or skills that have never been used (no last_used property)
        result = conn.query(
            "MATCH (s:Skill) "
            "WHERE (s.last_used IS NOT NULL AND s.last_used < $cutoff) "
            "   OR (s.last_used IS NULL AND s.avg_success_score IS NOT NULL) "
            "RETURN s.id, s.avg_success_score, s.last_used",
            {"cutoff": cutoff},
        )
    except Exception as e:
        report.warn(f"Decay query failed: {e}")
        print("  Skipped: Query failed.")
        return

    if not result.result_set:
        print("  No stale skills found.")
        return

    decayed = 0
    for row in result.result_set:
        sid = row[0]
        score = row[1]
        last_used = row[2]

        if score is None:
            continue

        try:
            current_score = float(score)
        except (ValueError, TypeError):
            continue

        new_score = round(current_score * 0.95, 4)

        # Don't decay below a floor of 0.1
        if new_score < 0.1:
            new_score = 0.1

        if new_score == current_score:
            continue

        report.action(
            "decay",
            f"Skill {sid}: avg_success_score {current_score:.4f} -> {new_score:.4f} "
            f"(last_used: {last_used or 'never'})",
        )

        if not report.dry_run:
            try:
                conn.query(
                    "MATCH (s:Skill {id: $sid}) SET s.avg_success_score = $score",
                    {"sid": sid, "score": str(new_score)},
                )
                decayed += 1
            except Exception as e:
                report.warn(f"Failed to decay skill {sid}: {e}")

    print(f"  Skills decayed: {decayed}")


# ── Step 3: Prune Weak Edges ──────────────────────────────────────────────────

def prune_weak_edges(conn, report):
    """
    Remove COMPOSES_WITH edges with co_occurrence < 2 that are older than 60 days.
    """
    print("[3/5] Prune weak edges...")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()

    try:
        result = conn.query(
            "MATCH (a:Skill)-[r:COMPOSES_WITH]->(b:Skill) "
            "WHERE r.co_occurrence < 2 "
            "  AND (r.created_at IS NOT NULL AND r.created_at < $cutoff) "
            "RETURN a.id, b.id, r.co_occurrence, r.created_at",
            {"cutoff": cutoff},
        )
    except Exception as e:
        report.warn(f"Edge prune query failed: {e}")
        print("  Skipped: Query failed.")
        return

    if not result.result_set:
        print("  No weak edges to prune.")
        return

    pruned = 0
    for row in result.result_set:
        from_id, to_id, co_occ, created = row[0], row[1], row[2], row[3]
        report.action(
            "prune",
            f"Remove COMPOSES_WITH: {from_id} -> {to_id} "
            f"(co_occurrence={co_occ}, created={created})",
        )

        if not report.dry_run:
            try:
                conn.query(
                    "MATCH (a:Skill {id: $from_id})-[r:COMPOSES_WITH]->(b:Skill {id: $to_id}) "
                    "WHERE r.co_occurrence < 2 "
                    "DELETE r",
                    {"from_id": from_id, "to_id": to_id},
                )
                pruned += 1
            except Exception as e:
                report.warn(f"Failed to prune edge {from_id}->{to_id}: {e}")

    print(f"  Edges pruned: {pruned}")


# ── Step 4: Hash Check ───────────────────────────────────────────────────────

def hash_check(conn, report):
    """
    Read .claude/skills/_manifest.yaml, compare content_hash against graph Skill nodes.
    Report any mismatches (skill was modified locally).
    """
    print("[4/5] Hash check (manifest vs graph)...")

    if not MANIFEST_PATH.exists():
        print("  Skipped: No manifest file found.")
        return

    manifest = read_yaml_file(MANIFEST_PATH)
    if not manifest:
        print("  Skipped: Manifest is empty or unreadable.")
        return

    skills = manifest.get("skills", {})
    if not skills or not isinstance(skills, dict):
        print("  No skills in manifest to check.")
        return

    mismatches = 0
    checked = 0

    for sid, info in skills.items():
        if not isinstance(info, dict):
            continue
        manifest_hash = info.get("content_hash")
        if not manifest_hash:
            continue

        try:
            result = conn.query(
                "MATCH (s:Skill {id: $sid}) RETURN s.content_hash",
                {"sid": sid},
            )
        except Exception as e:
            report.warn(f"Hash check query failed for {sid}: {e}")
            continue

        checked += 1

        if result.result_set:
            graph_hash = result.result_set[0][0]
            if graph_hash and graph_hash != manifest_hash:
                mismatches += 1
                report.warn(
                    f"Hash mismatch for {sid}: "
                    f"manifest={manifest_hash}, graph={graph_hash}"
                )
        else:
            report.warn(f"Skill {sid} in manifest but not in graph")

    print(f"  Checked: {checked}, Mismatches: {mismatches}")


# ── Step 5: Profile Re-evaluation ────────────────────────────────────────────

def profile_reevaluation(conn, report):
    """
    Read active profile, re-compute blocked skills, update graph nodes.
    """
    print("[5/5] Profile re-evaluation...")

    # Read active profile
    profile_data = read_yaml_file(ACTIVE_PROFILE_YAML)
    if not profile_data:
        print("  Skipped: No active profile found.")
        return

    profile_name = profile_data.get("profile", "standard")

    # Read profile constraints from profiles YAML
    profiles = read_yaml_file(PROFILES_YAML)
    if not profiles:
        report.warn("Could not read environment-profiles.yaml")
        print("  Skipped: Cannot read profiles config.")
        return

    profile_config = profiles.get("profiles", {}).get(profile_name, {})
    allow_internet = profile_config.get("allow_internet", True)
    allow_saas = profile_config.get("allow_saas", True)
    risk_levels = profile_config.get("acceptable_risk_levels", ["None", "Low", "Medium", "High"])

    print(f"  Active profile: {profile_name}")
    print(f"  Internet: {allow_internet}, SaaS: {allow_saas}, Risk levels: {risk_levels}")

    # Get all skills from graph
    try:
        result = conn.query(
            "MATCH (s:Skill) "
            "RETURN s.id, s.requires_internet, s.requires_saas, "
            "       s.risk_level, s.blocked_by_profile"
        )
    except Exception as e:
        report.warn(f"Profile re-evaluation query failed: {e}")
        print("  Skipped: Query failed.")
        return

    if not result.result_set:
        print("  No Skill nodes in graph.")
        return

    updated = 0
    for row in result.result_set:
        sid = row[0]
        req_inet = str(row[1]).lower() == "true" if row[1] else False
        req_saas = str(row[2]).lower() == "true" if row[2] else False
        risk = row[3] if row[3] else "None"
        current_blocked = str(row[4]).lower() == "true" if row[4] else False

        # Compute whether this skill should be blocked
        should_block = False
        if req_inet and not allow_internet:
            should_block = True
        if req_saas and not allow_saas:
            should_block = True
        if risk not in risk_levels:
            should_block = True

        if should_block != current_blocked:
            new_val = "true" if should_block else "false"
            report.action(
                "profile",
                f"Skill {sid}: blocked_by_profile {current_blocked} -> {should_block}",
            )

            if not report.dry_run:
                try:
                    conn.query(
                        "MATCH (s:Skill {id: $sid}) SET s.blocked_by_profile = $val",
                        {"sid": sid, "val": new_val},
                    )
                    updated += 1
                except Exception as e:
                    report.warn(f"Failed to update blocked status for {sid}: {e}")

    print(f"  Skills re-evaluated: {len(result.result_set)}, Updated: {updated}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Nightly skill consolidation for Atomic Claude",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    args = parser.parse_args()

    report = ConsolidationReport(dry_run=args.dry_run)

    print("=" * 60)
    print(" Atomic Claude — Skill Consolidation")
    print(f" Started: {datetime.now(timezone.utc).isoformat()}Z")
    if args.dry_run:
        print(" Mode: DRY RUN")
    print("=" * 60)
    print("")

    # Check FalkorDB availability
    conn = get_connection()
    if conn is None:
        print("FalkorDB is not available. Cannot run consolidation.")
        print("")
        if not HAS_GRAPH:
            print("  Missing dependency: pip install falkordb")
            print("  Or: core.graph module not importable")
        else:
            print("  FalkorDB server may not be running (localhost:6380)")
        print("")
        print("Consolidation skipped entirely.")
        return 1

    print(f"FalkorDB connected: {conn}")
    print("")

    # Run all 5 consolidation steps
    crystallize_workflows(conn, report)
    decay_unused_skills(conn, report)
    prune_weak_edges(conn, report)
    hash_check(conn, report)
    profile_reevaluation(conn, report)

    # Print summary
    report.print_summary()

    return 0


if __name__ == "__main__":
    sys.exit(main())
