"""
Task 101: Entry Validation

Validate Phase 0 completion and load prerequisites.

Checks:
  - phase-00-closeout.md exists
  - project-config.json is valid
  - pipeline-state.json shows Phase 0 complete
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.ui import phase_header, success, error, warning, info, step


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 101: Entry Validation.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass some checks for testing

    Returns:
        True if validation passed, False otherwise
    """
    setup_dir = output_dir.parent / "0-setup"

    # Phase 1 Welcome Banner
    print()
    print("━" * 80)
    print("""
 ______  _____ _______ _______  _____  _    _ _______  ______ __   __
 |     \\   |   |______ |       |     |  \\  /  |______ |_____/   \\_/
 |_____/ __|__ ______| |_____  |_____|   \\/   |______ |    \\_    |
""")
    print("━" * 80)
    print("                       [ PHASE 01 - DISCOVERY ]")
    print()

    step("Entry Validation")
    print()
    print("  Validating Phase 0 completion...")
    print()

    validation_passed = True
    issues = []

    # ═══════════════════════════════════════════════════════════════
    # CHECK 1: Phase 0 Closeout
    # ═══════════════════════════════════════════════════════════════

    closeout_file = _find_closeout(atomic_root, "0-setup")

    if closeout_file:
        print("  ✓ Phase 0 closeout found")
    else:
        print("  ✗ Phase 0 closeout not found")
        issues.append("Phase 0 closeout missing - run Phase 0 first")
        validation_passed = False

    # ═══════════════════════════════════════════════════════════════
    # CHECK 2: Project Config
    # ═══════════════════════════════════════════════════════════════

    config_file = setup_dir / "project-config.json"
    if config_file.exists():
        try:
            with open(config_file) as f:
                config_data = json.load(f)
            print("  ✓ project-config.json valid")

            # Check if config was flattened (Task 003 approval)
            project_name = config_data.get('project', {}).get('name')
            if not project_name:
                extracted_name = config_data.get('extracted', {}).get('project', {}).get('name')
                if extracted_name:
                    print("  ! Config not flattened - auto-flattening from extracted data")
                    _flatten_config(config_file, config_data)
                    project_name = extracted_name
                    print(f"  ✓ Config flattened: {project_name}")
                else:
                    print("  ! project.name not set")
                    issues.append("Project name not configured")

        except (json.JSONDecodeError, OSError) as e:
            print("  ✗ project-config.json invalid JSON")
            issues.append("Project config is invalid JSON")
            validation_passed = False
    else:
        print("  ✗ project-config.json not found")
        issues.append("Project config missing")
        validation_passed = False

    # ═══════════════════════════════════════════════════════════════
    # CHECK 3: Pipeline State
    # ═══════════════════════════════════════════════════════════════

    state_file = atomic_root / ".claude" / "pipeline-state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                state_data = json.load(f)
            current_phase = state_data.get('current_phase', 0)
            phase_0_status = state_data.get('phases', {}).get('0', {}).get('status', 'unknown')

            if phase_0_status == "completed" or current_phase >= 1:
                print("  ✓ Pipeline state: Phase 0 complete")
            else:
                print("  ! Pipeline state shows Phase 0 incomplete")
                issues.append("Phase 0 not marked complete in pipeline state")
        except (json.JSONDecodeError, OSError):
            print("  ! pipeline-state.json not found (will create)")
    else:
        print("  ! pipeline-state.json not found (will create)")

    # ═══════════════════════════════════════════════════════════════
    # VALIDATION RESULT
    # ═══════════════════════════════════════════════════════════════

    print()

    if not validation_passed:
        print("╔═══════════════════════════════════════════════════════╗")
        print("║ VALIDATION FAILED                                     ║")
        print("╚═══════════════════════════════════════════════════════╝")
        print()
        for issue in issues:
            print(f"  • {issue}")
        print()
        error("Cannot proceed - complete Phase 0 first")
        return False

    if issues:
        print("  Warnings:")
        for issue in issues:
            print(f"  • {issue}")
        print()

    # ═══════════════════════════════════════════════════════════════
    # WELCOME MESSAGE
    # ═══════════════════════════════════════════════════════════════

    print()
    print("  Welcome. This is where your project takes shape.")
    print("  We'll explore your vision, gather context, and")
    print("  assemble the right team of agents for the journey.")
    print()

    # Initialize phase output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    success("Entry validation passed")
    return True


def _find_closeout(atomic_root: Path, phase_id: str) -> Optional[Path]:
    """Find phase closeout file."""
    closeout_dir = atomic_root / ".claude" / "closeout"

    # Try multiple naming patterns
    patterns = [
        f"phase-{phase_id}-closeout.md",
        f"phase-{phase_id}-closeout.json",
        f"{phase_id}-closeout.md",
        "closeout.json",  # Simple pattern used by Phase 0
        "closeout.md",
    ]

    for pattern in patterns:
        closeout_file = closeout_dir / pattern
        if closeout_file.exists():
            return closeout_file

    # Try outputs directory
    outputs_dir = atomic_root / ".outputs" / phase_id
    for pattern in patterns:
        closeout_file = outputs_dir / pattern
        if closeout_file.exists():
            return closeout_file

    return None


def _flatten_config(config_file: Path, config_data: Dict[str, Any]) -> None:
    """Flatten extracted config data into main config."""
    extracted = config_data.get('extracted', {})

    # Flatten extracted fields
    for key in ['project', 'repository', 'sandbox', 'mcp', 'pipeline', 'agents', 'llm']:
        if key in extracted and extracted[key]:
            config_data[key] = extracted[key]

    # Mark as approved
    config_data['config_approved'] = True
    config_data['approved_at'] = datetime.now().isoformat()

    # Save flattened config
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 101: Entry Validation")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (bypass some checks)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
