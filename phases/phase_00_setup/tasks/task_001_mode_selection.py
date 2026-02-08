"""
Task 001: Setup File Validation

Ensures initialization/setup.md exists before proceeding.

If setup.md doesn't exist:
  - Creates template from initialization/setup.md or embedded fallback
  - Prompts user to fill it out
  - Waits for confirmation before proceeding

Validates API credentials and creates secrets.json for LLM invocation.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
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


# Embedded template for setup.md
SETUP_TEMPLATE = """# Project Setup
# =============
# Fill in the fields below. Use "infer" to let Claude extract from reference
# materials, "default" for recommended values, or enter a specific value.

## Project Information

**name**: infer
**description**: infer
**type**: default
**primary_goal**: infer

## Repository Configuration

**repository.url**: detect
**repository.default_branch**: default
**repository.pr_strategy**: default
**repository.commit_strategy**: default
**repository.push_strategy**: default
**repository.commit_format**: default

## Sandbox & Security

**sandbox.command_approval_mode**: default
**sandbox.network_mode**: default
**sandbox.network_access**: default

## MCP Servers

**mcp.enabled**: false

## Pipeline Configuration

**pipeline.mode**: default
**pipeline.skip_phases**: []
**pipeline.human_gates**: [0, 2, 5, 9]

## Agent Assignments (optional)

**agents.phase_1**: infer
**agents.phase_2**: infer
**agents.phase_3**: infer
**agents.phase_4**: infer
**agents.phase_5**: infer
**agents.phase_6**: infer
**agents.phase_7**: infer
**agents.phase_8**: infer
**agents.phase_9**: infer

## LLM Configuration

**llm.primary_provider**: default
**llm.primary_model**: default
**llm.fast_model**: default
**llm.local_fallback**: false

## Context Gardener (optional)

**gardener.model**: infer
**gardener.threshold_percent**: 75
**gardener.preserve_recent_exchanges**: 4
**gardener.preserve_opening**: true

## Technical Constraints (optional)

**constraints.technical**: infer
**constraints.infrastructure**: infer
**constraints.compliance**: infer
**constraints.dependencies**: infer

## Reference Materials

List any documentation, specs, or design docs that Claude should read:

- ./README.md
- ./docs/ARCHITECTURE.md

---

## Field Reference

### project.type options:
- new-component: Standalone service/module
- new-frontend: Web/mobile UI application
- new-api: Backend API service
- new-cli: Command-line tool
- new-library: Shared library/package
- new-monorepo: Multi-package repository
- existing: Add to existing codebase
- migration: Technology migration
- refactor: Code modernization

### llm.primary_provider options:
- anthropic: Claude (recommended)
- aws-bedrock: AWS Bedrock
- openai: OpenAI GPT
- ollama: Local models
- google: Google Gemini
- azure: Azure OpenAI
- openrouter: OpenRouter

### pipeline.mode options:
- component: Build and test, no deployment
- full: Complete pipeline including deployment
- library: Minimal for shared packages
- prototype: Quick validation only

### Defaults:
- "default" = Use recommended value
- "infer" = Extract from reference materials
- "detect" = Auto-detect from environment
"""


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 001: Setup File Validation.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir / "project-config.json"
    project_root = atomic_root.parent
    init_dir = project_root / "initialization"
    setup_file = init_dir / "setup.md"

    # Ensure initialization directory exists
    ensure_dir(init_dir)

    # Check if setup.md already exists
    file_exists = setup_file.exists()

    # Show the guide (whether file exists or not)
    _show_setup_guide()

    # Create template if it doesn't exist
    if not file_exists:
        if not ensure_setup_template(setup_file, atomic_root):
            return False
        print()
        print_green("✓ Created setup template")
    else:
        print_green("✓ Found setup template")

    print()
    print_dim(f"Location: {setup_file}")
    print()

    # Show instructions
    _show_instructions(setup_file, atomic_root, uat_mode)

    # UAT mode bypass
    if uat_mode:
        print_yellow("UAT Mode: Skipping interactive prompts")
        # Create minimal valid setup.md for UAT
        if not file_exists:
            write_file(setup_file, SETUP_TEMPLATE)

        # Create minimal secrets.json
        secrets_file = output_dir / "secrets.json"
        write_file(secrets_file, json.dumps({
            "memory_enabled": True,
            "network_mode": "cui",
            "uat_mode": True
        }, indent=2))

        # Save config
        save_config(config_file, setup_file)
        return True

    # Wait for user to confirm setup.md is customized
    clear_input_buffer()

    while True:
        response = prompt_user(
            "Press Enter when you've customized setup.md (or 'q' to quit): "
        ).strip().lower()

        if response in ['q', 'quit']:
            print_red("✗ Setup aborted")
            return False

        if setup_file.exists():
            print()
            print_green("✓ Setup file ready")

            # Validate .env file with credentials
            creds_valid = validate_env_file(atomic_root, output_dir)
            if not creds_valid:
                return False

            break
        else:
            print()
            print_red(f"✗ Setup file not found at {setup_file}")
            print()

    # Save config
    save_config(config_file, setup_file)
    return True


def _show_setup_guide() -> None:
    """Display the setup guide explaining why setup.md is required."""
    print()
    print_cyan("━" * 60)
    print_bold("  ATOMIC CLAUDE Setup")
    print_cyan("━" * 60)
    print()
    print_bold("Why setup.md is required:")
    print()
    print_cyan("  • ") + "Single source of truth for all project configuration"
    print_cyan("  • ") + "Ensures consistency across all pipeline phases"
    print_cyan("  • ") + "Enables deterministic behavior (same config = same results)"
    print_cyan("  • ") + "Makes projects reproducible and shareable"
    print_cyan("  • ") + "Allows version control of pipeline configuration"
    print()
    print_bold("What setup.md defines:")
    print()
    print_dim("  Project      ") + "  Name, type, description, goals"
    print_dim("  LLM          ") + "  Provider (Max/API/Bedrock/Ollama), models"
    print_dim("  Repository   ") + "  Git strategy, commit format, branch workflow"
    print_dim("  Sandbox      ") + "  Network mode, command approval, security"
    print_dim("  Pipeline     ") + "  Phases to run, human gates, mode"
    print_dim("  Agents       ") + "  Expert assignments for each phase"
    print_dim("  Constraints  ") + "  Tech stack, infrastructure, compliance"
    print()
    print_yellow("━" * 60)
    print()


def _show_instructions(setup_file: Path, atomic_root: Path, uat_mode: bool) -> None:
    """Display instructions for customizing setup.md."""
    if uat_mode:
        return

    print_bold("Before continuing:")
    print()
    print_cyan("  1. ") + f"Open the file:  {print_bold(str(setup_file))}"
    print_cyan("  2. ") + print_yellow("Customize it for your project") + " (required!)"
    print_cyan("  3. ") + "Replace generic values with your project details"
    print_cyan("  4. ") + "Use these special values:"
    print_dim("     • ") + print_green("infer") + "   - Let Claude extract from your docs"
    print_dim("     • ") + print_green("default") + " - Use recommended settings"
    print_dim("     • ") + print_green("detect") + "  - Auto-detect from environment"
    print()
    print_cyan("  5. ") + print_yellow("Create .env file with API credentials") + " (required!)"
    print("     Location: " + print_bold(str(atomic_root / ".env")))
    print("     See setup.md for .env template")
    print()
    print_yellow("━" * 60)
    print()


def ensure_setup_template(target_file: Path, atomic_root: Path) -> bool:
    """
    Ensure setup.md template exists.

    Args:
        target_file: Target path for setup.md
        atomic_root: Path to atomic-claude root

    Returns:
        True if template created/exists, False on error
    """
    if target_file.exists():
        return True

    ensure_dir(target_file.parent)

    # Check for orchestrator template
    template_file = atomic_root / "initialization" / "setup.md"

    if template_file.exists():
        try:
            content = read_file(template_file)
            write_file(target_file, content)
            print_green(f"  ✓ Created setup template: {target_file}")
            return True
        except Exception as e:
            print_red(f"  ✗ Failed to copy template: {e}")
            return False
    else:
        # Use embedded template
        write_file(target_file, SETUP_TEMPLATE)
        print_green(f"  ✓ Created setup template: {target_file}")
        return True


def validate_env_file(atomic_root: Path, output_dir: Path) -> bool:
    """
    Validate .env file exists with required credentials.

    Args:
        atomic_root: Path to atomic-claude root
        output_dir: Path to phase output directory

    Returns:
        True if credentials valid, False otherwise
    """
    env_file = atomic_root / ".env"
    has_aws = False
    has_anthropic = False
    has_ollama = False

    print()
    print_bold("Validating API credentials...")
    print()

    # Load environment variables
    env_vars = dict(os.environ)

    # Load .env file if it exists
    if env_file.exists():
        print_dim("Loading credentials from .env...")
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            print_yellow(f"⚠  Failed to load .env: {e}")

    # Check for AWS credentials
    if (env_vars.get('AWS_PROFILE') or
        env_vars.get('AWS_ACCESS_KEY_ID') or
        Path.home().joinpath('.aws', 'credentials').exists()):
        has_aws = True
        if env_vars.get('AWS_PROFILE'):
            print_green(f"  ✓ AWS profile found: {env_vars['AWS_PROFILE']}")
            print_dim(f"    Region: {env_vars.get('AWS_REGION', 'us-east-1')}")
        else:
            print_green("  ✓ AWS credentials found (CLI or environment)")

    # Check for Anthropic API key
    if env_vars.get('ANTHROPIC_API_KEY'):
        has_anthropic = True
        print_green("  ✓ Anthropic API key loaded")

    # Check for Ollama
    try:
        result = subprocess.run(
            ['curl', '-s', '--connect-timeout', '1', 'http://localhost:11434/api/tags'],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            has_ollama = True
            print_green("  ✓ Ollama available")
    except:
        pass

    # If no credentials found, show error
    if not has_aws and not has_anthropic and not has_ollama:
        print()
        print_red("✗ No API credentials found!")
        print()
        print_bold("Create .env file with credentials:")
        print()
        print_dim("  # AWS Bedrock")
        print("  AWS_ACCESS_KEY_ID=your-key")
        print("  AWS_SECRET_ACCESS_KEY=your-secret")
        print("  AWS_REGION=us-gov-west-1")
        print()
        print_dim("  # OR Anthropic API")
        print("  ANTHROPIC_API_KEY=sk-ant-...")
        print()
        print_dim("  # OR use: aws configure")
        print()
        print_red("✗ Cannot proceed without API credentials")
        return False

    print()
    print_green("✓ Credentials validated")

    # Create secrets.json
    create_secrets_file(output_dir, env_vars, has_aws, has_anthropic, has_ollama)
    return True


def create_secrets_file(
    output_dir: Path,
    env_vars: Dict[str, str],
    has_aws: bool,
    has_anthropic: bool,
    has_ollama: bool
) -> bool:
    """
    Create secrets.json from environment variables.

    Args:
        output_dir: Path to phase output directory
        env_vars: Environment variables dictionary
        has_aws: Whether AWS credentials available
        has_anthropic: Whether Anthropic API key available
        has_ollama: Whether Ollama available

    Returns:
        True if secrets file created successfully
    """
    secrets_file = output_dir / "secrets.json"
    secrets = {}

    # Configure AWS Bedrock if available
    if has_aws:
        aws_region = env_vars.get('AWS_REGION', 'us-east-1')
        aws_profile = env_vars.get('AWS_PROFILE', 'default')
        bedrock_model = env_vars.get('ANTHROPIC_MODEL', '')

        # Determine default model if not set
        if not bedrock_model:
            if aws_region.startswith('us-gov-'):
                bedrock_model = "us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0"
            else:
                bedrock_model = "anthropic.claude-sonnet-4-5-20250929-v1:0"

        secrets.update({
            "bedrock_enabled": True,
            "aws_region": aws_region,
            "aws_profile": aws_profile,
            "bedrock_model": bedrock_model,
            "use_bedrock": int(env_vars.get('CLAUDE_CODE_USE_BEDROCK', '1'))
        })
        print_green("  ✓ AWS Bedrock configured in secrets.json")

    # Configure Anthropic API if available
    if has_anthropic:
        secrets["anthropic_api_key"] = env_vars.get('ANTHROPIC_API_KEY')
        print_green("  ✓ Anthropic API configured in secrets.json")

    # Configure Ollama if available
    if has_ollama:
        secrets.update({
            "ollama_enabled": True,
            "ollama_host": "localhost:11434"
        })
        print_green("  ✓ Ollama configured in secrets.json")

    # Enable local memory by default
    secrets["memory_enabled"] = True

    # Set network mode
    secrets["network_mode"] = env_vars.get('ATOMIC_NETWORK_MODE', 'cui')

    # Write secrets file
    write_file(secrets_file, json.dumps(secrets, indent=2))

    # Secure the file (Unix only)
    if os.name != 'nt':
        try:
            os.chmod(secrets_file, 0o600)
        except:
            pass

    print_dim(f"  Secrets file: {secrets_file}")
    print()
    return True


def save_config(config_file: Path, setup_file: Path) -> None:
    """
    Save configuration and record decision.

    Args:
        config_file: Path to config file
        setup_file: Path to setup.md file
    """
    ensure_dir(config_file.parent)

    config = {
        "setup_mode": "document",
        "setup_file": str(setup_file),
        "created_at": datetime.now().isoformat()
    }

    write_file(config_file, json.dumps(config, indent=2))
    print_green(f"✓ Setup file: {setup_file}")


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 001: Setup File Validation")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
