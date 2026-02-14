"""
Task 004: API Keys

Securely collect provider-specific API credentials.

Features:
- Environment variable detection (checks existing env vars first)
- Key masking display for confirmation
- Optional key validation via API test
- Support for primary + backup provider
- Records configuration to context (not the keys themselves)
"""

import os
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
    Execute Task 004: API Keys.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir / "project-config.json"
    secrets_file = output_dir / "secrets.json"

    print()
    print(print_cyan("API Credentials"))
    print()

    print(print_dim("  Credentials loaded from .env in Task 001"))
    print()

    # Check if already configured by Task 001
    if secrets_file.exists():
        existing_keys = list(json.loads(read_file(secrets_file)).keys())
        if existing_keys:
            print(print_green("  ✓ Credentials already configured by Task 001"))
            print()

            # Show what was configured
            _show_configured_providers(secrets_file)

            print(print_dim(f"  To reconfigure, delete: {secrets_file}"))
            print()
            return True

    # If secrets.json doesn't exist or is empty, this is an error
    # Task 001 should have created it
    print(print_red("✗ No credentials configured - Task 001 should have created secrets.json"))
    print()
    print(print_bold("Troubleshooting:"))
    print("  1. Ensure .env file exists with credentials")
    print("  2. Re-run Phase 0 from Task 001")
    print()
    return False


def _show_configured_providers(secrets_file: Path) -> None:
    """
    Show configured providers with masked keys.

    Args:
        secrets_file: Path to secrets file
    """
    secrets = json.loads(read_file(secrets_file))

    # AWS Bedrock
    if secrets.get('bedrock_enabled'):
        aws_profile = secrets.get('aws_profile', 'default')
        aws_region = secrets.get('aws_region', 'us-east-1')
        bedrock_model = secrets.get('bedrock_model', '')
        print(print_cyan("  AWS Bedrock:"))
        print(f"    Profile: {aws_profile}")
        print(f"    Region: {aws_region}")
        print(f"    Model: {bedrock_model}")
        print()

    # Anthropic API
    anthropic_key = secrets.get('anthropic_api_key')
    if anthropic_key:
        masked_key = _mask_key(anthropic_key)
        print(print_cyan("  Anthropic API:"))
        print(f"    Key: {masked_key}")
        print()

    # Ollama
    if secrets.get('ollama_enabled'):
        print(print_cyan("  Ollama:"))
        print("    localhost:11434")
        print()


def _mask_key(key: str) -> str:
    """
    Mask a key for display (show first 7 and last 4 chars).

    Args:
        key: API key to mask

    Returns:
        Masked key string
    """
    if len(key) < 15:
        return "***"

    prefix = key[:7]
    suffix = key[-4:]
    return f"{prefix}***...***{suffix}"


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 004: API Keys")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
