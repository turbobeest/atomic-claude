"""
Task 003: Configuration Review

Human reviews and approves the extracted/collected configuration.

Features:
- Displays all configuration in formatted sections
- 7 editable fields (name, desc, repo, mode, provider, network, cmd mode)
- Shows diff after edits
- Raw JSON view option
- Records all decisions to context
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
    Execute Task 003: Configuration Review.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip interactive prompts

    Returns:
        True if task completed successfully, False otherwise
    """
    config_file = output_dir / "project-config.json"

    print()
    print(print_cyan("Configuration Review"))
    print()

    # Show info box
    _show_info_box()

    # Display configuration
    _display_config(config_file)

    # Prompt for action (approve, edit, view, restart)
    return _prompt_action(config_file, output_dir)


def _show_info_box() -> None:
    """Show informational box about configuration review."""
    print(print_dim("  ┌─────────────────────────────────────────────────────────┐"))
    print(print_dim("  │ Review the extracted configuration below.               │"))
    print(print_dim("  │ You can approve as-is or edit specific fields.         │"))
    print(print_dim("  └─────────────────────────────────────────────────────────┘"))
    print()


def _display_config(config_file: Path) -> None:
    """
    Display the full configuration to user.

    Args:
        config_file: Path to project config file
    """
    # Load config
    config = json.loads(read_file(config_file))
    extracted = config.get('extracted', {})

    # Project section
    print(print_cyan("  PROJECT"))
    project = extracted.get('project', {})
    print(f"    Name:        {project.get('name', 'not set')}")
    print(f"    Description: {project.get('description', 'not set')}")
    print(f"    Type:        {project.get('type', 'not set')}")
    print(f"    Goal:        {project.get('primary_goal', 'not set')}")
    print()

    # Repository section
    print(print_cyan("  REPOSITORY"))
    repository = extracted.get('repository', {})
    print(f"    URL:         {repository.get('url', 'not set')}")
    print(f"    Branch:      {repository.get('default_branch', 'main')}")
    print(f"    PR Strategy: {repository.get('pr_strategy', 'feature-branch')}")
    print(f"    Commits:     {repository.get('commit_strategy', 'per-task')}")
    print(f"    Push:        {repository.get('push_strategy', 'on-close')}")
    print()

    # Pipeline section
    print(print_cyan("  PIPELINE"))
    pipeline = extracted.get('pipeline', {})
    print(f"    Mode:        {pipeline.get('mode', 'component')}")

    # Show human gates with phase names
    gates = pipeline.get('human_gates', [0, 2, 5, 9])
    gate_names = []
    for g in gates:
        gate_map = {
            0: "Setup", 1: "Discovery", 2: "PRD", 3: "Tasking", 4: "Spec",
            5: "Build", 6: "Review", 7: "Integration", 8: "Deploy Prep", 9: "Release"
        }
        if g in gate_map:
            gate_names.append(gate_map[g])

    print(f"    Human Gates: {', '.join(gate_names) if gate_names else 'None'}")
    print()

    # Sandbox section
    print(print_cyan("  SANDBOX"))
    sandbox = extracted.get('sandbox', {})
    print(f"    Network:     {sandbox.get('network_access', 'fetch-only')}")
    print(f"    Cmd Mode:    {sandbox.get('command_approval_mode', 'cautious')}")
    print()

    # LLM Preferences section
    print(print_cyan("  LLM PREFERENCES"))
    providers = extracted.get('providers', {})
    chain = providers.get('chain_priority', [])
    if chain:
        print(f"    Chain:       {' > '.join(chain)}")
    else:
        llm = extracted.get('llm', {})
        print(f"    Provider:    {llm.get('primary_provider', 'anthropic')}")
    model_cfg = providers.get('models', {})
    if model_cfg:
        print(f"    Primary:     {model_cfg.get('primary', 'sonnet')}")
        print(f"    Fast:        {model_cfg.get('fast', 'haiku')}")
        print(f"    Heavyweight: {model_cfg.get('heavyweight', 'opus')}")
    effort = providers.get('effort_level')
    thinking = providers.get('thinking_budget')
    if effort:
        print(f"    Effort:      {effort}")
    if thinking is not None:
        print(f"    Thinking:    {thinking} tokens")
    routing = providers.get('routing', {})
    if routing:
        print(f"    Routing:     critical={routing.get('critical', '?')}, bulk={routing.get('bulk', '?')}")
    fallback = providers.get('fallback', {})
    if fallback:
        fb_parts = []
        if fallback.get('api_to_ollama'):
            fb_parts.append("API->Ollama")
        if fallback.get('ollama_to_api'):
            fb_parts.append("Ollama->API")
        if fallback.get('offline_mode'):
            fb_parts.append("offline")
        print(f"    Fallback:    {', '.join(fb_parts) if fb_parts else 'none'}")
    print()

    # Agent Assignment section
    print(print_cyan("  AGENTS"))
    agents = extracted.get('agents', {})
    if isinstance(agents, dict) and 'default_tier' in agents:
        print(f"    Tier:        {agents.get('default_tier', 'sonnet')}")
        assignments = agents.get('phase_assignments', {})
        custom = [k for k, v in assignments.items() if v not in ('default', 'infer')]
        if custom:
            for k in custom:
                print(f"    {k}:  {assignments[k]}")
        else:
            print(f"    Assignments: auto-select all")
    else:
        print(f"    Config:      default")
    print()

    # Audit Configuration section
    print(print_cyan("  AUDITS"))
    audits = extracted.get('audits', {})
    print(f"    Profile:     {audits.get('default_profile', 'standard')}")
    print(f"    Failure:     {audits.get('failure_mode', 'gate-high')}")
    sev = audits.get('severity_filter', ['critical', 'high'])
    print(f"    Severity:    {', '.join(sev) if isinstance(sev, list) else sev}")
    print()

    # Constraints section
    constraints = extracted.get('constraints', {})
    if constraints and any(constraints.get(k) for k in ('technical', 'infrastructure', 'compliance', 'dependencies')):
        print(print_cyan("  CONSTRAINTS"))
        if constraints.get('technical'):
            tech = constraints['technical']
            if isinstance(tech, list):
                tech = ', '.join(tech)
            print(f"    Technical:   {tech}")
        if constraints.get('infrastructure'):
            print(f"    Infra:       {constraints['infrastructure']}")
        if constraints.get('compliance'):
            comp = constraints['compliance']
            if isinstance(comp, list):
                comp = ', '.join(comp)
            print(f"    Compliance:  {comp}")
        if constraints.get('dependencies'):
            deps = constraints['dependencies']
            if isinstance(deps, list):
                deps = ', '.join(deps)
            print(f"    Deps:        {deps}")
        print()

    # Check for any null/infer values that need attention
    warnings = []
    if not project.get('name') or project.get('name') == 'null':
        warnings.append("Project name not set")
    if not repository.get('url') or repository.get('url') == 'null':
        warnings.append("Repository URL not set (optional)")

    if warnings:
        print(print_yellow("  NOTES:"))
        for w in warnings:
            print(f"    - {w}")
        print()


def _prompt_action(config_file: Path, output_dir: Path) -> bool:
    """
    Prompt for action (approve, edit, view json, restart).

    Args:
        config_file: Path to project config file
        output_dir: Path to phase output directory

    Returns:
        True if approved, False to restart
    """
    print()
    print(print_green("  [a] Approve configuration"))
    print(print_yellow("  [e] Edit a field"))
    print(print_cyan("  [j] View raw JSON"))
    print(print_red("  [r] Restart entire setup from the beginning"))
    print()

    while True:
        clear_input_buffer()
        choice = prompt_user("Choice (default: a): ").strip().lower() or 'a'

        if choice == 'a':
            _approve_config(config_file)
            return True
        elif choice == 'e':
            _edit_field(config_file)
            # Re-display and prompt again
            _display_config(config_file)
            return _prompt_action(config_file, output_dir)
        elif choice == 'j':
            _view_json(config_file)
            # Prompt again after viewing
            return _prompt_action(config_file, output_dir)
        elif choice == 'r':
            print(print_yellow("Restarting configuration..."))
            return False
        else:
            print(print_red("Invalid choice. Enter a, e, j, or r."))


def _approve_config(config_file: Path) -> None:
    """
    Approve and flatten config.

    Args:
        config_file: Path to project config file
    """
    # Load config
    config = json.loads(read_file(config_file))
    extracted = config.get('extracted', {})

    # Flatten extracted into main config
    for key in ('project', 'repository', 'sandbox', 'mcp', 'pipeline',
                'agents', 'llm', 'constraints', 'providers', 'gardener', 'audits'):
        if key in extracted:
            config[key] = extracted[key]
    config['config_approved'] = True
    config['approved_at'] = datetime.now().isoformat()

    # Write back
    write_file(config_file, json.dumps(config, indent=2))

    print(print_green("✓ Configuration approved"))


def _view_json(config_file: Path) -> None:
    """
    View raw JSON.

    Args:
        config_file: Path to project config file
    """
    config = json.loads(read_file(config_file))
    extracted = config.get('extracted', {})

    print()
    print(print_dim("  ─────────────────── RAW JSON ───────────────────"))
    print()
    # Pretty print with indentation
    json_str = json.dumps(extracted, indent=2)
    for line in json_str.split('\n'):
        print(f"    {line}")
    print()
    print(print_dim("  ────────────────────────────────────────────────"))
    print()

    clear_input_buffer()
    prompt_user("Press Enter to continue... ")


def _edit_field(config_file: Path) -> None:
    """
    Edit a specific field.

    Args:
        config_file: Path to project config file
    """
    print()
    print(print_dim("  Edit which field?"))
    print("    1. Project Name")
    print("    2. Description")
    print("    3. Repository URL")
    print("    4. Pipeline Mode")
    print("    5. LLM Provider")
    print("    6. Network Access")
    print("    7. Command Approval Mode")
    print()

    clear_input_buffer()
    field_choice = prompt_user("Field (default: 1-7): ").strip()

    # Load config
    config = json.loads(read_file(config_file))
    extracted = config.get('extracted', {})

    if field_choice == '1':
        _edit_project_name(config_file, extracted)
    elif field_choice == '2':
        _edit_description(config_file, extracted)
    elif field_choice == '3':
        _edit_repository_url(config_file, extracted)
    elif field_choice == '4':
        _edit_pipeline_mode(config_file, extracted)
    elif field_choice == '5':
        _edit_llm_provider(config_file, extracted)
    elif field_choice == '6':
        _edit_network_access(config_file, extracted)
    elif field_choice == '7':
        _edit_command_approval(config_file, extracted)
    else:
        print(print_red("Invalid field selection"))


def _edit_project_name(config_file: Path, extracted: Dict[str, Any]) -> None:
    """Edit project name."""
    old_val = extracted.get('project', {}).get('name', 'not set')
    new_name = prompt_user(f"New project name (default: {old_val}): ").strip() or old_val

    # Validate project name (lowercase, numbers, hyphens only)
    if not new_name.replace('-', '').replace('_', '').replace('.', '').isalnum():
        print(print_red("Invalid name (use lowercase, numbers, hyphens only)"))
        return

    # Update config
    config = json.loads(read_file(config_file))
    if 'project' not in config['extracted']:
        config['extracted']['project'] = {}
    config['extracted']['project']['name'] = new_name
    write_file(config_file, json.dumps(config, indent=2))

    _show_change("Project Name", old_val, new_name)


def _edit_description(config_file: Path, extracted: Dict[str, Any]) -> None:
    """Edit project description."""
    old_val = extracted.get('project', {}).get('description', 'not set')
    new_desc = prompt_user("New description: ").strip() or old_val

    # Update config
    config = json.loads(read_file(config_file))
    if 'project' not in config['extracted']:
        config['extracted']['project'] = {}
    config['extracted']['project']['description'] = new_desc
    write_file(config_file, json.dumps(config, indent=2))

    _show_change("Description", old_val, new_desc)


def _edit_repository_url(config_file: Path, extracted: Dict[str, Any]) -> None:
    """Edit repository URL."""
    old_val = extracted.get('repository', {}).get('url', 'not set')
    new_url = prompt_user(f"New repository URL (default: {old_val}): ").strip() or old_val

    # Update config
    config = json.loads(read_file(config_file))
    if 'repository' not in config['extracted']:
        config['extracted']['repository'] = {}
    config['extracted']['repository']['url'] = new_url
    write_file(config_file, json.dumps(config, indent=2))

    _show_change("Repository URL", old_val, new_url)


def _edit_pipeline_mode(config_file: Path, extracted: Dict[str, Any]) -> None:
    """Edit pipeline mode."""
    old_val = extracted.get('pipeline', {}).get('mode', 'component')

    print()
    print(print_dim("    1. component  - Single feature or component"))
    print(print_dim("    2. full       - Full application"))
    print(print_dim("    3. library    - Reusable library/package"))
    print(print_dim("    4. prototype  - Quick prototype (fewer gates)"))

    mode = prompt_user("Mode (default: 1-4): ").strip()

    mode_map = {'1': 'component', '2': 'full', '3': 'library', '4': 'prototype'}
    new_mode = mode_map.get(mode, old_val)

    # Update config
    config = json.loads(read_file(config_file))
    if 'pipeline' not in config['extracted']:
        config['extracted']['pipeline'] = {}
    config['extracted']['pipeline']['mode'] = new_mode
    write_file(config_file, json.dumps(config, indent=2))

    _show_change("Pipeline Mode", old_val, new_mode)


def _edit_llm_provider(config_file: Path, extracted: Dict[str, Any]) -> None:
    """Edit LLM provider."""
    old_val = extracted.get('llm', {}).get('primary_provider', 'anthropic')

    print()
    print(print_dim("    1. anthropic  - Claude (recommended)"))
    print(print_dim("    2. openai     - GPT models"))
    print(print_dim("    3. google     - Gemini models"))
    print(print_dim("    4. local      - Local LLM (ollama, etc)"))

    prov = prompt_user("Provider (default: 1-4): ").strip()

    prov_map = {'1': 'anthropic', '2': 'openai', '3': 'google', '4': 'local'}
    new_provider = prov_map.get(prov, old_val)

    # Update config
    config = json.loads(read_file(config_file))
    if 'llm' not in config['extracted']:
        config['extracted']['llm'] = {}
    config['extracted']['llm']['primary_provider'] = new_provider
    write_file(config_file, json.dumps(config, indent=2))

    _show_change("LLM Provider", old_val, new_provider)


def _edit_network_access(config_file: Path, extracted: Dict[str, Any]) -> None:
    """Edit network access."""
    old_val = extracted.get('sandbox', {}).get('network_access', 'fetch-only')

    print()
    print(print_dim("    1. none       - No network access"))
    print(print_dim("    2. fetch-only - HTTP GET only (recommended)"))
    print(print_dim("    3. full       - Full network access"))

    net = prompt_user("Network access (default: 1-3): ").strip()

    net_map = {'1': 'none', '2': 'fetch-only', '3': 'full'}
    new_network = net_map.get(net, old_val)

    # Update config
    config = json.loads(read_file(config_file))
    if 'sandbox' not in config['extracted']:
        config['extracted']['sandbox'] = {}
    config['extracted']['sandbox']['network_access'] = new_network
    write_file(config_file, json.dumps(config, indent=2))

    _show_change("Network Access", old_val, new_network)


def _edit_command_approval(config_file: Path, extracted: Dict[str, Any]) -> None:
    """Edit command approval mode."""
    old_val = extracted.get('sandbox', {}).get('command_approval_mode', 'cautious')

    print()
    print(print_dim("    1. ask-always - Prompt before every command"))
    print(print_dim("    2. cautious   - Prompt for risky commands (recommended)"))
    print(print_dim("    3. auto       - Auto-approve safe commands"))

    cmd = prompt_user("Command approval (default: 1-3): ").strip()

    cmd_map = {'1': 'ask-always', '2': 'cautious', '3': 'auto'}
    new_cmd = cmd_map.get(cmd, old_val)

    # Update config
    config = json.loads(read_file(config_file))
    if 'sandbox' not in config['extracted']:
        config['extracted']['sandbox'] = {}
    config['extracted']['sandbox']['command_approval_mode'] = new_cmd
    write_file(config_file, json.dumps(config, indent=2))

    _show_change("Command Approval", old_val, new_cmd)


def _show_change(field: str, old_val: str, new_val: str) -> None:
    """
    Show what changed after an edit.

    Args:
        field: Field name
        old_val: Old value
        new_val: New value
    """
    if old_val == new_val:
        print()
        print(print_dim(f"No change to {field}"))
    else:
        print()
        print(print_dim("Changed:"))
        print(print_red(f"    {field}: {old_val}"))
        print(print_green(f"    {field}: {new_val}"))
        print()
        print(print_green(f"✓ Updated {field}"))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 003: Configuration Review")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir)
    sys.exit(0 if success else 1)
