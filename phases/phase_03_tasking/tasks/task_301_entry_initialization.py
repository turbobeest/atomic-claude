"""
Task 301: Entry & Initialization

Verify Phase 2 artifacts and initialize TaskMaster structure.

Validates:
  - docs/prd/PRD.md (from Phase 2)
  - prd-approved.json (PRD approval record)
  - phase-02-closeout.json (Phase 2 complete)

Initializes:
  - .taskmaster/ directory structure
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 301: Entry & Initialization.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent
    prd_file = project_root / "docs" / "prd" / "PRD.md"
    approval_file = output_dir.parent / "2-prd" / "prd-approved.json"
    closeout_file = output_dir.parent / "2-prd" / "phase-02-closeout.json"
    validation_file = output_dir / "entry-validation.json"
    taskmaster_dir = project_root / ".taskmaster"

    # UAT Mode: Auto-pass validation
    if uat_mode:
        print()
        print(print_yellow("⚡ UAT Mode: Auto-passing entry validation"))
        print()

        ensure_dir(taskmaster_dir / "tasks")
        ensure_dir(taskmaster_dir / "reports")

        validation_data = {
            "phase2_closeout": "pass",
            "prd_exists": "pass",
            "validation": "pass",
            "mode": "uat"
        }
        write_file(validation_file, json.dumps(validation_data, indent=2))
        print(print_green("✓ Entry validation complete (UAT mode)"))
        return True

    # Phase 3 Welcome
    _show_phase_welcome()

    checks_passed = 0
    checks_failed = 0
    checks_warned = 0
    validation_data: Dict[str, Any] = {}

    # Phase 2 Closeout Check
    print(print_dim("─" * 100))
    print()
    print(print_bold("PHASE 2 CLOSEOUT"))
    print()

    if closeout_file.exists():
        closeout = json.loads(read_file(closeout_file))
        phase2_status = closeout.get("status", "unknown")
        if phase2_status == "complete":
            print(print_green(f"✓ Phase 2 closeout found (status: complete)"))
            checks_passed += 1
            validation_data["phase2_closeout"] = "pass"
        else:
            print(print_yellow(f"! Phase 2 closeout status: {phase2_status}"))
            checks_warned += 1
            validation_data["phase2_closeout"] = phase2_status
    else:
        print(print_red("✗ Phase 2 closeout not found"))
        print(print_dim(f"  Expected: {closeout_file}"))
        checks_failed += 1
        validation_data["phase2_closeout"] = "missing"
    print()

    # PRD Document Check
    print(print_dim("─" * 100))
    print()
    print(print_bold("PRD DOCUMENT"))
    print()

    if prd_file.exists():
        prd_lines = len(read_file(prd_file).splitlines())
        print(print_green(f"✓ PRD document found ({prd_lines} lines)"))
        print(print_dim("  Task decomposition follows PRD-TEMPLATE v3.0 structure"))
        checks_passed += 1
        validation_data["prd_document"] = {"status": "pass", "lines": prd_lines}
    else:
        print(print_red("✗ PRD document not found"))
        print(print_dim(f"  Expected: {prd_file}"))
        checks_failed += 1
        validation_data["prd_document"] = {"status": "missing"}
    print()

    # PRD Approval Check
    print(print_dim("─" * 100))
    print()
    print(print_bold("PRD APPROVAL"))
    print()

    if approval_file.exists():
        approval = json.loads(read_file(approval_file))
        approval_status = approval.get("status", "unknown")
        approver = approval.get("approver", "unknown")
        approved_at = approval.get("approved_at", "unknown")

        if approval_status == "approved":
            print(print_green("✓ PRD approved"))
            print(print_dim(f"  Approver: {approver}"))
            print(print_dim(f"  Date: {approved_at}"))
            checks_passed += 1
            validation_data["prd_approval"] = {"status": "approved", "approver": approver}
        else:
            print(print_yellow(f"! PRD approval status: {approval_status}"))
            checks_warned += 1
            validation_data["prd_approval"] = {"status": approval_status}
    else:
        print(print_red("✗ PRD approval record not found"))
        print(print_dim(f"  Expected: {approval_file}"))
        checks_failed += 1
        validation_data["prd_approval"] = {"status": "missing"}
    print()

    # TaskMaster Initialization
    print(print_dim("─" * 100))
    print()
    print(print_bold("TASKMASTER INITIALIZATION"))
    print()

    if taskmaster_dir.exists():
        print(print_green("✓ TaskMaster directory exists"))
        print(print_dim(f"  {taskmaster_dir}"))
    else:
        print(print_dim("Creating TaskMaster directory structure..."))
        ensure_dir(taskmaster_dir / "tasks")
        ensure_dir(taskmaster_dir / "reports")
        ensure_dir(taskmaster_dir / "history")
        print(print_green("✓ Created .taskmaster/"))
        print(print_dim("  ├── tasks/"))
        print(print_dim("  ├── reports/"))
        print(print_dim("  └── history/"))

    # Configure TaskMaster for Bedrock if enabled
    _configure_taskmaster_provider(taskmaster_dir, output_dir, atomic_root)
    print()

    # Summary
    print(print_dim("─" * 100))
    print()
    print(print_bold("SUMMARY"))
    print()
    print(f"  Passed:   {print_green(str(checks_passed))}")
    if checks_warned > 0:
        print(f"  Warnings: {print_yellow(str(checks_warned))}")
    if checks_failed > 0:
        print(f"  Failed:   {print_red(str(checks_failed))}")
    print()

    # Save validation results
    overall_status = "pass"
    if checks_warned > 0:
        overall_status = "warning"
    if checks_failed > 0:
        overall_status = "fail"

    validation_data.update({
        "overall_status": overall_status,
        "checks_passed": checks_passed,
        "checks_warned": checks_warned,
        "checks_failed": checks_failed,
        "validated_at": datetime.utcnow().isoformat() + "Z"
    })

    ensure_dir(validation_file.parent)
    write_file(validation_file, json.dumps(validation_data, indent=2))

    # Decision Point
    if checks_failed > 0:
        print(print_dim("─" * 100))
        print()
        print(print_red("Entry validation failed."))
        print()
        print(print_yellow("  continue  ") + "Proceed anyway (not recommended)")
        print(print_red("  abort     ") + "Return to Phase 2")
        print()

        clear_input_buffer()
        entry_choice = prompt_user("Choice (default: abort): ").strip().lower()
        if not entry_choice:
            entry_choice = "abort"

        if entry_choice != "continue":
            print(print_red("✗ Entry validation failed - returning to Phase 2"))
            return False

        print(print_yellow("⚠ Proceeding despite failed validation"))
        print()

    print(print_green("✓ Entry and initialization complete"))
    return True


def _show_phase_welcome() -> None:
    """Display Phase 3 welcome banner."""
    print()
    print(print_dim("━" * 100))
    print(print_cyan("  PHASE 03 - TASKING"))
    print(print_dim("━" * 100))
    print(print_cyan("""
                      _______ _______ _______ _     _
                         |    |_____| |______ |____/
                         |    |     | ______| |    \\_

     ______  _______ _______  _____  _______  _____   _____  _______ _____ _______ _____  _____  __   _
     |     \\ |______ |       |     | |  |  | |_____] |     | |______   |      |      |   |     | | \\  |
     |_____/ |______ |_____  |_____| |  |  | |       |_____| ______| __|__    |    __|__ |_____| |  \\_|
    """))
    print(print_dim("━" * 100))
    print()
    print(print_dim("Verifying Phase 2 artifacts and initializing TaskMaster."))
    print()


def _configure_taskmaster_provider(
    taskmaster_dir: Path,
    output_dir: Path,
    atomic_root: Path
) -> None:
    """
    Configure TaskMaster to use the same provider as atomic-claude.

    Args:
        taskmaster_dir: Path to .taskmaster directory
        output_dir: Path to phase output directory
        atomic_root: Path to atomic-claude root
    """
    config_file = taskmaster_dir / "config.json"
    secrets_file = output_dir.parent / "0-setup" / "secrets.json"

    # Check if secrets exist
    if not secrets_file.exists():
        print(print_dim("No provider configuration found - TaskMaster will use defaults"))
        return

    try:
        secrets = json.loads(read_file(secrets_file))
    except Exception:
        print(print_dim("Could not read secrets.json - TaskMaster will use defaults"))
        return

    # Check if Bedrock is enabled
    bedrock_enabled = secrets.get("bedrock_enabled", False)

    if bedrock_enabled:
        aws_region = secrets.get("aws_region", "us-east-1")
        aws_profile = secrets.get("aws_profile", "default")
        bedrock_model = secrets.get("bedrock_model", "")

        # Extract model ID from inference profile
        model_id = "claude-sonnet-4-5-20250929"
        if bedrock_model:
            # Extract model name from inference profile
            import re
            match = re.search(r'anthropic\.([^:]+)', bedrock_model)
            if match:
                model_id = re.sub(r'-v\d+$', '', match.group(1))

        print(print_dim("Configuring TaskMaster for AWS Bedrock..."))

        # Create TaskMaster config for Bedrock
        config = {
            "models": {
                "main": {
                    "provider": "bedrock",
                    "modelId": model_id,
                    "maxTokens": 64000,
                    "temperature": 0.2
                },
                "research": {
                    "provider": "bedrock",
                    "modelId": model_id,
                    "maxTokens": 32000,
                    "temperature": 0.1
                },
                "fallback": {
                    "provider": "bedrock",
                    "modelId": model_id,
                    "maxTokens": 64000,
                    "temperature": 0.2
                }
            },
            "global": {
                "logLevel": "info",
                "debug": False,
                "defaultSubtasks": 5,
                "defaultPriority": "medium",
                "projectName": atomic_root.parent.name
            }
        }

        write_file(config_file, json.dumps(config, indent=2))
        print(print_green("✓ TaskMaster configured for AWS Bedrock"))
        print(print_dim(f"  Region: {aws_region} | Profile: {aws_profile}"))
        print(print_dim(f"  Model: {model_id}"))

        # Create .env file for TaskMaster
        env_file = atomic_root.parent / ".env"
        if not env_file.exists() or "AWS_REGION" not in read_file(env_file):
            env_content = f"\n# AWS Bedrock Configuration (auto-generated by ATOMIC-CLAUDE)\n"
            env_content += f"AWS_REGION={aws_region}\n"
            env_content += f"AWS_PROFILE={aws_profile}\n"

            if env_file.exists():
                existing = read_file(env_file)
                write_file(env_file, existing + env_content)
            else:
                write_file(env_file, env_content)

            print(print_green("✓ Created .env with AWS credentials"))

            # Add .env to .gitignore
            gitignore = atomic_root.parent / ".gitignore"
            if gitignore.exists():
                content = read_file(gitignore)
                if ".env" not in content:
                    write_file(gitignore, content + "\n.env\n")
            else:
                write_file(gitignore, ".env\n")
    else:
        print(print_dim("Using TaskMaster default provider configuration"))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 301: Entry & Initialization")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
