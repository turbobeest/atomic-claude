"""
Task 903: Agent Selection

Present and select release agents for announcement writing.
"""

import re
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.ui import success, warning, step
from core.utils.cli_ui import CYAN, DIM, BOLD, GREEN, YELLOW, NC
from core.utils.file_ops import write_json

logger = logging.getLogger(__name__)


def execute(atomic_root: Path, output_dir: Path, mem=None) -> bool:
    """
    Execute Task 903: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory

    Returns:
        True if task completed successfully, False otherwise
    """
    agents_file = output_dir / "release-agents.json"

    step("Agent Selection")

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
    except (EOFError, KeyboardInterrupt):
        logger.debug("Non-interactive mode: defaulting to '1'")
        ann_choice = "1"

    if ann_choice == "1":
        selected_agents.append("announcement-writer-phd:haiku")
    elif ann_choice == "2":
        selected_agents.append("announcement-writer-detailed:sonnet")
    elif ann_choice.lower() in ["c", "custom"]:
        try:
            custom_name = input("  Custom agent name: ").strip()
            if not custom_name:
                print("  ⚠  Empty agent name. Defaulting to announcement-writer-phd:haiku")
                selected_agents.append("announcement-writer-phd:haiku")
            elif not re.match(r'^[A-Za-z0-9_-]+$', custom_name):
                print(f"  ⚠  Invalid agent name '{custom_name}'. Only alphanumeric, hyphens, and underscores allowed.")
                print("  Defaulting to announcement-writer-phd:haiku")
                selected_agents.append("announcement-writer-phd:haiku")
            else:
                custom_model = input("  Custom agent model (default: haiku): ").strip() or "haiku"
                selected_agents.append(f"{custom_name}:{custom_model}")
        except (EOFError, KeyboardInterrupt):
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
        parts = agent.split(':', 1)
        name = parts[0]
        model = parts[1] if len(parts) > 1 else "sonnet"
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
    args = parser.parse_args()

    result = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if result else 1)
