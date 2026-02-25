"""
Task 903: Agent Selection

Present and select release agents for announcement writing.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.ui import success, error, warning, info, step
from core.utils.file_ops import write_json

logger = logging.getLogger(__name__)


# ANSI color codes for formatted output
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
NC = "\033[0m"


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 903: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent

    agents_file = output_dir / "release-agents.json"
    roster_file = project_root / ".claude" / "agent-roster.json"

    step("Agent Selection")

    # UAT Mode Bypass
    if uat_mode:
        print(f"  {DIM}UAT Mode: Creating minimal valid output{NC}")

        # Create minimal output that satisfies downstream tasks
        output_dir.mkdir(parents=True, exist_ok=True)
        selected_agents_file = output_dir / "selected-agents.json"
        write_json(selected_agents_file, {
            "agents": ["announcement-writer-phd:haiku"],
            "count": 1
        })

        success("UAT bypass complete")
        return True

    print()
    print(f"  {DIM}Select agents for release execution.{NC}")
    print()

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # RELEASE WORKFLOW
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    print()
    print(f"  {BOLD}- RELEASE WORKFLOW{NC}")
    print()

    print(f"    Announcement Writer ────→  Release Confirmation")
    print(f"        {DIM}(internal notes){NC}          {DIM}(human gate){NC}")
    print()

    # Future workflow with external channels (hidden for now):
    # print(f"    GitHub Releaser ─────────┐")
    # print(f"        {DIM}(create tag){NC}         │")
    # print(f"    Package Publisher ───────┼→  Release Confirmation")
    # print(f"        {DIM}(registry upload){NC}    │       {DIM}(human gate){NC}")
    # print(f"    Announcement Writer ─────┘")
    # print(f"        {DIM}(stakeholder comms){NC}")

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AVAILABLE AGENTS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    print()
    print(f"  {BOLD}- AVAILABLE AGENTS{NC}")
    print()

    # Announcement Writer
    print(f"  {YELLOW}{'─' * 110}{NC}")
    print(f"  {BOLD}ANNOUNCEMENT WRITER{NC}")
    print()
    print(f"    Drafts internal release notes for stakeholders.")
    print(f"    Documents version changes and highlights.")
    print(f"    {GREEN}Recommended:{NC} announcement-writer-phd (haiku)")
    print(f"  {YELLOW}{'─' * 110}{NC}")
    print()

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AGENT SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    print()
    print(f"  {BOLD}- AGENT SELECTION{NC}")
    print()

    print(f"  {DIM}Select agents for each role:{NC}")
    print()

    selected_agents: List[str] = []

    # Announcement Writer selection
    print(f"  {YELLOW}Announcement Writer:{NC}")
    print(f"    {GREEN}[1]{NC} announcement-writer-phd (haiku) - Recommended")
    print(f"    {DIM}[2]{NC} announcement-writer-detailed (sonnet) - Comprehensive")
    print(f"    {YELLOW}[c]{NC} Custom agent")
    print()

    try:
        ann_choice = input("  Select (default: 1): ").strip() or "1"
    except EOFError:
        logger.debug("Non-interactive mode: defaulting to '1'")
        ann_choice = "1"

    if ann_choice == "1":
        selected_agents.append("announcement-writer-phd:haiku")
    elif ann_choice == "2":
        selected_agents.append("announcement-writer-detailed:sonnet")
    elif ann_choice.lower() in ["c", "custom"]:
        try:
            custom_name = input("  Custom agent name: ").strip()
            custom_model = input("  Custom agent model (default: haiku): ").strip() or "haiku"
            selected_agents.append(f"{custom_name}:{custom_model}")
        except EOFError:
            logger.debug("Non-interactive mode: defaulting to announcement-writer-phd:haiku")
            selected_agents.append("announcement-writer-phd:haiku")
    else:
        selected_agents.append("announcement-writer-phd:haiku")

    print()

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SELECTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    print()
    print(f"  {BOLD}- SELECTION SUMMARY{NC}")
    print()

    print(f"  {'─' * 110}")
    print(f"  {BOLD}SELECTED AGENTS{NC}")
    print()
    for agent in selected_agents:
        name, model = agent.split(':')
        print(f"    {GREEN}✓{NC} {name} ({model})")
    print(f"  {'─' * 110}")
    print()

    # Save agent selection
    agents_file.parent.mkdir(parents=True, exist_ok=True)
    write_json(agents_file, {
        "phase": 9,
        "agents": selected_agents,
        "selected_at": datetime.now(timezone.utc).isoformat()
    })

    # Save decision to context
    decision_file = output_dir / "agents-decision.json"
    write_json(decision_file, {
        "decision": f"Release agents selected: {len(selected_agents)} agents",
        "type": "agents",
        "artifact": str(agents_file)
    })

    success("Agent Selection complete")
    return True


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 903: Agent Selection")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    result = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if result else 1)
