"""
Task 002: Configuration Collection

Parses initialization/setup.md with Claude to extract project configuration.

Input: initialization/setup.md (validated by Task 001)
Output: .outputs/0-setup/extracted-config.json with structured configuration
"""

import os
import sys
import json
import subprocess
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
    Execute Task 002: Configuration Collection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir / "project-config.json"
    extracted_file = output_dir / "extracted-config.json"
    project_root = atomic_root.parent
    init_dir = project_root / "initialization"

    print()
    print_cyan("Document Configuration")
    print()

    # Show info box
    _show_info_box()

    # Check if Task 001 already detected a setup file
    setup_file_path = os.environ.get('SETUP_FILE_PATH', '')

    if not setup_file_path or not Path(setup_file_path).exists():
        # Find setup file
        if not uat_mode:
            setup_file_path = _prompt_for_setup_file(init_dir, project_root)
            if not setup_file_path:
                return False
        else:
            # UAT mode - use default path
            setup_file_path = str(init_dir / "setup.md")
            if not Path(setup_file_path).exists():
                print_red("✗ Setup file not found in UAT mode")
                return False

    setup_file = Path(setup_file_path)
    print()
    print_dim(f"Reading setup: {setup_file}")
    print()

    # Validate setup.md format
    if not _validate_setup_format(setup_file):
        return False

    # Read setup content (limited to 500 lines to protect context window)
    setup_content = _read_setup_content(setup_file)

    # Read additional configuration files
    setup_dir = setup_file.parent
    llm_prefs_content = _read_optional_file(setup_dir / "llm-preferences.md")
    agent_plan_content = _read_optional_file(setup_dir / "agent-plan.md")
    audit_plan_content = _read_optional_file(setup_dir / "audit-plan.md")

    # Read reference documents
    reference_content = _read_reference_docs(setup_file, atomic_root)

    # Auto-detect repository URL
    detected_repo = _detect_git_repo()

    # Create extraction prompt
    prompt_file = output_dir / "prompts" / "extract-setup.md"
    ensure_dir(prompt_file.parent)

    _create_extraction_prompt(
        prompt_file,
        setup_content,
        llm_prefs_content,
        agent_plan_content,
        audit_plan_content,
        reference_content,
        detected_repo,
        project_root
    )

    # UAT mode bypass for LLM invocation
    if uat_mode:
        print_yellow("UAT Mode: Creating minimal extracted config")
        _create_minimal_config(extracted_file, project_root)
        _merge_into_config(config_file, extracted_file)
        return True

    print_dim("Claude is extracting configuration...")
    print()

    # Invoke Claude to extract configuration
    if not _invoke_claude_extraction(prompt_file, extracted_file):
        # Extraction failed - offer retry
        if not _handle_extraction_failure(setup_file):
            return False

    # Clean and validate JSON
    if not _clean_and_validate_json(extracted_file):
        return False

    print_green("✓ Configuration extracted successfully")
    print()

    # Merge into main config
    _merge_into_config(config_file, extracted_file)

    return True


def _show_info_box() -> None:
    """Show informational box about configuration files."""
    print_dim("  ┌─────────────────────────────────────────────────────────┐")
    print_dim("  │ Configuration files are in initialization/              │")
    print_dim("  │                                                         │")
    print_dim("  │   setup.md        - Project configuration               │")
    print_dim("  │   agent-plan.md   - Agent assignments                   │")
    print_dim("  │   audit-plan.md   - Audit profiles                      │")
    print_dim("  │                                                         │")
    print_dim("  │ Claude will read these files and extract config.        │")
    print_dim("  │ Fields marked 'infer' will be populated from your       │")
    print_dim("  │ reference materials.                                    │")
    print_dim("  └─────────────────────────────────────────────────────────┘")
    print()


def _prompt_for_setup_file(init_dir: Path, project_root: Path) -> Optional[str]:
    """
    Prompt user for setup file path.

    Args:
        init_dir: Default initialization directory
        project_root: Project root directory

    Returns:
        Path to setup file, or None if not found
    """
    # Check for default path
    default_path = ""
    if (init_dir / "setup.md").exists():
        default_path = str(init_dir / "setup.md")
    else:
        # Check alternate locations
        for check in ["./initialization/setup.md", "./setup.md", "./manifest.md"]:
            check_path = project_root / check
            if check_path.exists():
                default_path = str(check_path)
                break

    # Drain buffered stdin
    clear_input_buffer()

    while True:
        if default_path:
            response = prompt_user(f"Setup file path (default: {default_path}): ").strip()
            setup_path = response or default_path
        else:
            setup_path = prompt_user("Setup file path: ").strip()

        if not setup_path:
            print_red("✗ Path required")
            print()
            continue

        if not Path(setup_path).exists():
            print_red(f"✗ File not found: {setup_path}")
            print()
            continue

        return setup_path


def _validate_setup_format(setup_file: Path) -> bool:
    """
    Validate setup.md format.

    Args:
        setup_file: Path to setup.md file

    Returns:
        True if valid format, False otherwise
    """
    try:
        content = read_file(setup_file)
        # Check for field format: **field**: value
        if '**' in content and '**:' in content:
            return True

        print_red("✗ Invalid setup.md format")
        print()
        print_dim("  The setup.md file doesn't contain valid configuration fields.")
        print_dim("  Expected format:")
        print()
        print_dim("  **name**: my-project")
        print_dim("  **type**: webapp")
        print_dim("  **description**: Project description")
        print()
        print_dim(f"  File checked: {setup_file}")
        print()
        return False
    except Exception as e:
        print_red(f"✗ Failed to read setup file: {e}")
        return False


def _read_setup_content(setup_file: Path) -> str:
    """
    Read setup.md content, limited to 500 lines.

    Args:
        setup_file: Path to setup.md file

    Returns:
        Setup file content (potentially truncated)
    """
    content = read_file(setup_file)
    lines = content.split('\n')

    if len(lines) > 500:
        truncated = '\n'.join(lines[:500])
        truncated += f'\n\n[TRUNCATED: Showing 500 of {len(lines)} lines]'
        return truncated

    return content


def _read_optional_file(file_path: Path) -> str:
    """
    Read an optional configuration file.

    Args:
        file_path: Path to file

    Returns:
        File content or empty string if not found
    """
    if file_path.exists():
        print_dim(f"  Reading: {file_path.name}")
        return read_file(file_path)
    return ""


def _read_reference_docs(setup_file: Path, atomic_root: Path) -> str:
    """
    Read reference documents mentioned in setup and auto-detected docs.

    Args:
        setup_file: Path to setup.md file
        atomic_root: Path to atomic-claude root

    Returns:
        Combined reference document content
    """
    reference_content = ""

    # Read docs mentioned in setup.md
    setup_content = read_file(setup_file)
    ref_lines = [line.strip().lstrip('- ') for line in setup_content.split('\n')
                 if line.strip().startswith('- ./')]

    for ref in ref_lines[:5]:  # Limit to 5
        ref_path = Path(ref)
        if ref_path.exists():
            print_dim(f"  Found: {ref}")
            content = read_file(ref_path)
            # Limit each doc to 200 lines
            lines = content.split('\n')[:200]
            reference_content += f"\n=== {ref} ===\n"
            reference_content += '\n'.join(lines)
            reference_content += "\n\n"

    # Auto-scan for common reference files
    auto_refs = []
    for candidate in [
        atomic_root / "README.md",
        atomic_root / "WHITEPAPER.md",
        atomic_root / "DESIGN.md",
        atomic_root / "ARCHITECTURE.md",
        atomic_root / "SPEC.md",
        atomic_root / "docs" / "README.md",
        atomic_root / "docs" / "design.md",
        atomic_root / "docs" / "architecture.md"
    ]:
        if candidate.exists():
            auto_refs.append(candidate)

    if auto_refs:
        print_dim("  Auto-detected reference documents...")
        for ref in auto_refs:
            ref_name = str(ref.relative_to(atomic_root))
            # Skip if already included
            if ref_name not in reference_content:
                print_dim(f"  Found: {ref_name}")
                content = read_file(ref)
                lines = content.split('\n')[:500]  # Limit to 500 lines
                reference_content += f"\n=== {ref_name} ===\n"
                reference_content += '\n'.join(lines)
                reference_content += "\n\n"

    return reference_content


def _detect_git_repo() -> str:
    """
    Detect Git repository URL.

    Returns:
        Repository URL or empty string
    """
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return ""


def _create_extraction_prompt(
    prompt_file: Path,
    setup_content: str,
    llm_prefs: str,
    agent_plan: str,
    audit_plan: str,
    reference: str,
    detected_repo: str,
    project_root: Path
) -> None:
    """Create the extraction prompt for Claude."""
    # Use embedded prompt template (from bash script)
    prompt = f"""# Task: Extract Configuration from Project Setup

You are a **configuration parser** specializing in extracting structured data from semi-structured documents. Your role is to read project initialization files and output a validated JSON configuration.

## Output Requirements

CRITICAL: Output ONLY raw JSON. Do NOT use markdown code fences.
Do NOT wrap in ```json or ```.
Start your response with `{{` and end with `}}`.
No explanation text before or after.

## Extraction Rules

1. **Explicit values**: Use the exact value from the setup file
2. **"infer" fields**: Analyze reference materials (provided below) to derive a project-specific value.
   - CRITICAL: If no reference materials are provided, use the directory name for project name and use `null` for description/goal
   - NEVER invent or hallucinate project details - only extract from provided materials
3. **"default [X]" fields**: Use the literal value X shown in brackets
4. **"detect" fields**: Use the auto-detected values provided below
5. **Missing required values**: Use `null` (do NOT invent values)
6. **Malformed input**: Extract what you can, use defaults for the rest

## Edge Cases

| Situation | Response |
|-----------|----------|
| Setup file is mostly empty | Use defaults for all fields, note in constraints |
| No reference materials for "infer" | Use directory name for project.name, `null` for project.description and project.primary_goal |
| Conflicting values | Prefer explicit setup.md values over inferred |
| Unknown project type | Default to "new-component" |
| Invalid enum value | Use closest valid option or default |
| Truncated input | Process what's available, don't fail |

## Detected Values:
- Repository URL (from git): {detected_repo or 'not detected'}
- Directory name: {project_root.name}

## Output JSON Schema:

{{
  "project": {{
    "name": "string (max 24 chars)",
    "description": "string",
    "type": "new-component|new-frontend|new-api|new-cli|new-library|new-monorepo|existing|migration|refactor",
    "primary_goal": "string"
  }},
  "repository": {{
    "url": "string or null",
    "default_branch": "string",
    "pr_strategy": "direct|feature-branch|gitflow",
    "commit_strategy": "per-phase|per-task|per-prompt|manual|atomic",
    "push_strategy": "per-phase|per-commit|manual|on-close",
    "commit_format": "conventional|gitmoji|simple|custom"
  }},
  "sandbox": {{
    "allowed_paths": ["array of paths"] or null,
    "forbidden_paths": ["array of paths"],
    "forbidden_commands": ["array of commands"],
    "command_approval_mode": "strict|cautious|permissive",
    "network_mode": "cui|internet",
    "network_access": "none|fetch-only|allowlist|blocklist|full",
    "blocked_ips": ["array of CIDR ranges"]
  }},
  "mcp": {{
    "enabled": boolean,
    "servers": ["array of server names"],
    "tool_permissions": "all|write-only|dangerous|none"
  }},
  "pipeline": {{
    "mode": "full|component|library|prototype",
    "skip_phases": [array of numbers] or [],
    "human_gates": [array of phase numbers]
  }},
  "agents": {{
    "phase_0": "string",
    "phase_1": "string",
    "phase_2": "string",
    "phase_3": "string",
    "phase_4": "string",
    "phase_5": "string",
    "phase_6": "string",
    "phase_7": "string",
    "phase_8": "string",
    "phase_9": "string"
  }},
  "llm": {{
    "primary_provider": "anthropic|openai|aws-bedrock|google|ollama|openrouter|azure",
    "primary_model": "string or null",
    "fast_model": "string or null",
    "local_fallback": boolean
  }},
  "providers": {{
    "chains": {{
      "global": "string (space-separated provider list)",
      "critical": "string or null (override for critical tasks)",
      "bulk": "string or null (override for bulk tasks)",
      "quick": "string or null (override for quick tasks)"
    }},
    "routing": {{
      "critical": "primary|ollama",
      "bulk": "primary|ollama",
      "background": "primary|ollama"
    }},
    "ollama": {{
      "enabled": boolean,
      "servers": [{{"name": "string", "host": "string", "model": "string", "max_context": number}}],
      "failover": boolean,
      "health_check": boolean
    }},
    "fallback": {{
      "api_to_ollama": boolean,
      "ollama_to_api": boolean,
      "offline_mode": boolean
    }}
  }},
  "gardener": {{
    "model": "string or 'infer' (auto-select fastest)",
    "threshold_percent": "number 50-90 (trigger adjudication at this % of context)",
    "fallback_chain": ["array of model names to try if primary fails"],
    "preserve_recent_exchanges": "number 2-8 (exchanges to keep after adjudication)",
    "preserve_opening": "boolean (keep opening messages for continuity)"
  }},
  "constraints": {{
    "technical": ["array of strings"] or null,
    "infrastructure": "string or null",
    "compliance": ["array of strings"] or null,
    "dependencies": ["array of strings"] or null
  }}
}}

## Setup Content (setup.md):

{setup_content}
"""

    if llm_prefs:
        prompt += f"\n\n## LLM Preferences (llm-preferences.md):\n\n{llm_prefs}"

    if agent_plan:
        prompt += f"\n\n## Agent Plan (agent-plan.md):\n\n{agent_plan}"

    if audit_plan:
        prompt += f"\n\n## Audit Plan (audit-plan.md):\n\n{audit_plan}"

    if reference:
        prompt += f"\n\n## Reference Documents:\n\n{reference}"

    write_file(prompt_file, prompt)


def _invoke_claude_extraction(prompt_file: Path, output_file: Path) -> bool:
    """
    Invoke Claude to extract configuration.

    Args:
        prompt_file: Path to prompt file
        output_file: Path to output file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Use claude CLI to invoke extraction
        result = subprocess.run(
            ['claude', 'chat', '--file', str(prompt_file), '--output', str(output_file)],
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        print_red(f"✗ Claude invocation failed: {e}")
        return False


def _handle_extraction_failure(setup_file: Path) -> bool:
    """
    Handle extraction failure with retry option.

    Args:
        setup_file: Path to setup file

    Returns:
        True if retry successful, False to abort
    """
    print()
    print_yellow("Extraction failed. Would you like to:")
    print()
    print_green("  [r] Retry (edit setup.md and try again)")
    print_red("  [q] Quit")
    print()

    clear_input_buffer()
    choice = prompt_user("Choice (default: r): ").strip().lower() or 'r'

    if choice in ['q', 'quit']:
        print_red("✗ Setup aborted by user")
        return False

    # Retry
    print()
    print_yellow("Please edit your setup.md file and press Enter to retry")
    clear_input_buffer()
    prompt_user("Press Enter when ready... ")

    # Recursive retry
    return execute(
        atomic_root=setup_file.parent.parent / "atomic-claude2",
        output_dir=setup_file.parent.parent / ".outputs" / "0-setup",
        uat_mode=False
    )


def _clean_and_validate_json(json_file: Path) -> bool:
    """
    Clean markdown fences from JSON and validate.

    Args:
        json_file: Path to JSON file

    Returns:
        True if valid JSON, False otherwise
    """
    content = read_file(json_file)

    # Check for markdown code fences
    if '```json' in content or '```' in content:
        print_dim("  Removing markdown code fences...")
        # Extract JSON from fences
        lines = content.split('\n')
        json_lines = []
        in_fence = False
        for line in lines:
            if line.strip() == '```json' or line.strip() == '```':
                in_fence = not in_fence
                continue
            if in_fence or (not in_fence and '{' in line):
                json_lines.append(line)

        content = '\n'.join(json_lines)
        write_file(json_file, content)

    # Validate JSON
    try:
        data = json.loads(content)
        # Re-write formatted
        write_file(json_file, json.dumps(data, indent=2))
        return True
    except json.JSONDecodeError as e:
        print_red(f"✗ Failed to parse extracted JSON: {e}")
        return False


def _merge_into_config(config_file: Path, extracted_file: Path) -> None:
    """
    Merge extracted config into main config file.

    Args:
        config_file: Path to main config file
        extracted_file: Path to extracted config file
    """
    # Load both files
    if config_file.exists():
        config = json.loads(read_file(config_file))
    else:
        config = {}

    extracted = json.loads(read_file(extracted_file))

    # Merge extracted into config under 'extracted' key
    config['extracted'] = extracted

    # Write back
    write_file(config_file, json.dumps(config, indent=2))


def _create_minimal_config(extracted_file: Path, project_root: Path) -> None:
    """
    Create minimal config for UAT mode.

    Args:
        extracted_file: Path to extracted config file
        project_root: Project root directory
    """
    minimal = {
        "project": {
            "name": "uat-test-project",
            "description": "UAT test project",
            "type": "new-component",
            "primary_goal": "Test UAT flow"
        },
        "repository": {
            "url": None,
            "default_branch": "main",
            "pr_strategy": "feature-branch",
            "commit_strategy": "per-task",
            "push_strategy": "on-close",
            "commit_format": "conventional"
        },
        "sandbox": {
            "allowed_paths": None,
            "forbidden_paths": [".env*", "secrets/"],
            "forbidden_commands": ["rm -rf /"],
            "command_approval_mode": "cautious",
            "network_mode": "cui",
            "network_access": "fetch-only",
            "blocked_ips": ["169.254.169.254/32"]
        },
        "mcp": {"enabled": False, "servers": [], "tool_permissions": "none"},
        "pipeline": {"mode": "component", "skip_phases": [], "human_gates": [0, 2, 5]},
        "agents": {f"phase_{i}": "default" for i in range(10)},
        "llm": {
            "primary_provider": "anthropic",
            "primary_model": None,
            "fast_model": None,
            "local_fallback": False
        },
        "providers": {
            "chains": {"global": "claude-code anthropic", "critical": None, "bulk": None, "quick": None},
            "routing": {"critical": "primary", "bulk": "primary", "background": "primary"},
            "ollama": {"enabled": False, "servers": [], "failover": True, "health_check": True},
            "fallback": {"api_to_ollama": False, "ollama_to_api": True, "offline_mode": False}
        },
        "gardener": {
            "model": "infer",
            "threshold_percent": 75,
            "fallback_chain": [],
            "preserve_recent_exchanges": 4,
            "preserve_opening": True
        },
        "constraints": {"technical": None, "infrastructure": None, "compliance": None, "dependencies": None}
    }

    write_file(extracted_file, json.dumps(minimal, indent=2))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 002: Configuration Collection")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
