#!/usr/bin/env python3
"""
consolidate_skills.py -- Nightly skill consolidation for Atomic Claude.

Thin CLI wrapper around core.skills.consolidation.SkillConsolidation.

Runs on cron or manually to maintain skill graph hygiene:
  1. Crystallize workflows -- promote recurring skill sequences to Workflow nodes
  2. Decay unused skills -- reduce relevance of stale skills
  3. Prune weak edges -- remove low-value COMPOSES_WITH edges
  4. Calibrate gravity -- track false-light rates

Usage:
    python3 scripts/skills/consolidate_skills.py
    python3 scripts/skills/consolidate_skills.py --dry-run
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.skills.consolidation import SkillConsolidation  # noqa: E402


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

    print("=" * 60)
    print(" Atomic Claude -- Skill Consolidation")
    print(f" Started: {datetime.now(timezone.utc).isoformat()}Z")
    if args.dry_run:
        print(" Mode: DRY RUN")
    print("=" * 60)
    print("")

    consolidation = SkillConsolidation(dry_run=args.dry_run)
    report = consolidation.run_all()

    # Print summary
    print("")
    print("=" * 60)
    print(" Skill Consolidation Summary")
    if args.dry_run:
        print(" (DRY RUN -- no changes applied)")
    print("=" * 60)
    print("")

    actions = report.get("actions", [])
    warnings = report.get("warnings", [])

    if actions:
        print(f"Actions ({len(actions)}):")
        for a in actions:
            print(f"  {a}")
    else:
        print("No actions taken.")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")

    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
