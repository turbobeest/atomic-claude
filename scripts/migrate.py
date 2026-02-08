#!/usr/bin/env python3
"""
Migration Tool - Bash to Python State Conversion

Migrates existing bash-based atomic-claude state to Python v2 format.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class StateMigrator:
    """Migrates state from v1 (bash) to v2 (Python)."""

    def __init__(self, old_state_dir: Path, new_state_dir: Path):
        """
        Initialize migrator.

        Args:
            old_state_dir: Path to v1 .state directory
            new_state_dir: Path to v2 .state directory
        """
        self.old_state_dir = old_state_dir
        self.new_state_dir = new_state_dir

    def backup_old_state(self) -> Path:
        """
        Backup old state before migration.

        Returns:
            Path to backup directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.old_state_dir.parent / f".state.backup.{timestamp}"

        print(f"Backing up old state to: {backup_dir}")
        shutil.copytree(self.old_state_dir, backup_dir)

        return backup_dir

    def migrate_task_state(self) -> Dict[str, Any]:
        """
        Migrate task-state.json from v1 to v2 format.

        Returns:
            Migrated state dictionary
        """
        old_state_file = self.old_state_dir / "task-state.json"

        if not old_state_file.exists():
            print("No old state file found, creating new state")
            return {"phases": {}, "version": "2.0.0"}

        print(f"Migrating state from: {old_state_file}")

        with open(old_state_file) as f:
            old_state = json.load(f)

        # V2 format
        new_state = {
            "version": "2.0.0",
            "migrated_at": datetime.now().isoformat(),
            "phases": {},
        }

        # Migrate phase data
        if "phases" in old_state:
            for phase_id, phase_data in old_state["phases"].items():
                new_state["phases"][phase_id] = {
                    "started": phase_data.get("started"),
                    "completed": phase_data.get("completed"),
                    "tasks": {},
                }

                # Migrate task data
                if "tasks" in phase_data:
                    for task_id, task_data in phase_data["tasks"].items():
                        new_state["phases"][phase_id]["tasks"][task_id] = {
                            "name": task_data.get("name", f"Task {task_id}"),
                            "status": task_data.get("status", "unknown"),
                            "completed_at": task_data.get("completed_at"),
                        }

        # Migrate current phase
        if "current_phase" in old_state:
            new_state["current_phase"] = old_state["current_phase"]

        return new_state

    def migrate_memory(self):
        """Migrate memory files (if any)."""
        old_memory = self.old_state_dir / "memory"
        new_memory = self.new_state_dir / "memory"

        if old_memory.exists():
            print(f"Migrating memory directory...")
            shutil.copytree(old_memory, new_memory, dirs_exist_ok=True)

    def run_migration(self) -> bool:
        """
        Execute complete migration.

        Returns:
            True if migration successful
        """
        print("=" * 60)
        print("ATOMIC-CLAUDE STATE MIGRATION (v1 → v2)")
        print("=" * 60)
        print()

        try:
            # 1. Backup old state
            backup_dir = self.backup_old_state()
            print(f"✓ Backup created: {backup_dir}")
            print()

            # 2. Create new state directory
            self.new_state_dir.mkdir(parents=True, exist_ok=True)

            # 3. Migrate task state
            print("Migrating task state...")
            new_state = self.migrate_task_state()

            # Save new state
            new_state_file = self.new_state_dir / "task-state.json"
            with open(new_state_file, "w") as f:
                json.dump(new_state, f, indent=2)
            print(f"✓ State migrated: {new_state_file}")
            print()

            # 4. Migrate memory
            print("Migrating memory...")
            self.migrate_memory()
            print("✓ Memory migrated")
            print()

            # 5. Print summary
            print("=" * 60)
            print("MIGRATION COMPLETE")
            print("=" * 60)
            print(f"Phases migrated: {len(new_state.get('phases', {}))}")
            print(f"Backup location: {backup_dir}")
            print(f"New state location: {self.new_state_dir}")
            print()

            return True

        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            return False


def main():
    """Run migration tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate atomic-claude state from v1 (bash) to v2 (Python)"
    )
    parser.add_argument(
        "--old-state",
        type=Path,
        default=Path(".state"),
        help="Path to old state directory (default: .state)",
    )
    parser.add_argument(
        "--new-state",
        type=Path,
        default=Path(".state"),
        help="Path to new state directory (default: .state)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print()

    migrator = StateMigrator(args.old_state, args.new_state)

    if args.dry_run:
        print("Would migrate:")
        print(f"  Old state: {args.old_state}")
        print(f"  New state: {args.new_state}")
        return

    success = migrator.run_migration()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
