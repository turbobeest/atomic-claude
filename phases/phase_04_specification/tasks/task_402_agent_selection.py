"""
Task 402: Agent Selection

Select and configure agents for OpenSpec generation from agent inventory.
"""

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user, clear_input_buffer
)
from core.utils.file_ops import ensure_dir, read_file, write_file


def load_agents_from_csv(csv_path: Path, phase_filter: str = "06-09-implementation") -> List[Dict[str, str]]:
    """Load agents from CSV inventory file."""
    agents = []

    if not csv_path.exists():
        return agents

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if agent is for implementation phases
                if row.get('phase', '') == phase_filter:
                    agents.append({
                        'name': row.get('name', ''),
                        'tier': row.get('tier', ''),
                        'model': row.get('model', 'sonnet'),
                        'role': row.get('role', ''),
                        'description': row.get('description', '')[:70]
                    })
    except Exception as e:
        print(print_yellow(f"⚠  Could not parse CSV: {e}"))

    return agents


def analyze_project_characteristics(tasks_file: Path) -> Dict[str, any]:
    """Analyze tasks to determine project characteristics."""
    try:
        tasks_data = json.loads(read_file(tasks_file))
        tasks = tasks_data.get("tasks", [])

        task_count = len(tasks)

        # Check for specific patterns in task titles
        has_api = any('api' in t.get('title', '').lower() or
                     'endpoint' in t.get('title', '').lower() or
                     'service' in t.get('title', '').lower() or
                     'rest' in t.get('title', '').lower() or
                     'graphql' in t.get('title', '').lower()
                     for t in tasks)

        has_auth = any('auth' in t.get('title', '').lower() or
                      'login' in t.get('title', '').lower() or
                      'session' in t.get('title', '').lower() or
                      'token' in t.get('title', '').lower() or
                      'permission' in t.get('title', '').lower()
                      for t in tasks)

        has_data = any('database' in t.get('title', '').lower() or
                      'model' in t.get('title', '').lower() or
                      'schema' in t.get('title', '').lower() or
                      'migration' in t.get('title', '').lower() or
                      'data' in t.get('title', '').lower()
                      for t in tasks)

        complex_count = len([t for t in tasks if t.get('estimated_complexity') == 'complex'])

        return {
            'task_count': task_count,
            'has_api': has_api,
            'has_auth': has_auth,
            'has_data': has_data,
            'complex_count': complex_count
        }
    except Exception as e:
        print(print_red(f"✗ Could not analyze tasks: {e}"))
        return {}


def recommend_agents(characteristics: Dict[str, any]) -> Tuple[List[str], List[str]]:
    """Recommend agents based on project characteristics."""
    # Core agents always recommended
    recommended = ["specification-agent", "tdd-implementation-agent"]
    reasons = []

    if characteristics.get('has_api'):
        reasons.append("API contracts")

    if characteristics.get('has_auth'):
        recommended.append("code-review-gate")
        reasons.append("Security requirements")

    complex_count = characteristics.get('complex_count', 0)
    if complex_count > 2:
        recommended.append("test-strategist")
        reasons.append("Complex edge cases")

    task_count = characteristics.get('task_count', 0)
    if task_count > 10:
        if "test-strategist" not in recommended:
            recommended.append("test-strategist")
        reasons.append("Test coverage strategy")

    if task_count > 5:
        recommended.append("plan-guardian")
        reasons.append("Drift monitoring")

    return recommended, reasons


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 402: Agent Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, auto-select agents for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    roster_file = atomic_root / ".claude" / "agent-roster.json"
    tasks_file = atomic_root / ".taskmaster" / "tasks" / "tasks.json"

    # Determine agent repo location
    agent_repo = atomic_root / "repos" / "agents"
    if (atomic_root / "agents" / "agent-inventory.csv").exists():
        agent_repo = atomic_root / "agents"

    csv_path = agent_repo / "agent-inventory.csv"

    # UAT Mode: Auto-select agents
    if uat_mode:
        print()
        print(print_yellow("⚡ UAT Mode: Auto-selecting specification agents"))
        print()
        ensure_dir(output_dir)
        write_file(output_dir / "selected-agents.json", json.dumps({
            "agents": ["specification-agent", "tdd-agent"],
            "mode": "uat"
        }, indent=2))
        print(print_green("✓ Agent selection complete (UAT mode)"))
        return True

    print()
    print(print_dim("  Selecting agents for OpenSpec generation and TDD subtask creation."))
    print()

    # Load agents from CSV inventory
    print(print_dim("─" * 109))
    print()
    print(print_bold("SPECIFICATION AGENTS (from agent-inventory.csv)"))
    print()

    agents = load_agents_from_csv(csv_path)

    if agents:
        print(print_dim("  Available agents from inventory:"))
        print()

        for agent in agents:
            role = agent.get('role', '')
            symbol = {
                'executor': f"\033[32m●\033[0m",      # Green
                'gatekeeper': f"\033[36m●\033[0m",   # Cyan
                'strategist': f"\033[33m●\033[0m",   # Yellow
            }.get(role, f"\033[2m●\033[0m")          # Dim

            name = agent.get('name', '')
            tier = agent.get('tier', '')
            model = agent.get('model', '')
            desc = agent.get('description', '')

            print(f"    {symbol} \033[1m{name}\033[0m [{tier}, {model}]")
            print(f"      \033[2m{desc}...\033[0m")
            print()
    else:
        print(print_yellow(f"  ! Agent inventory not found at {csv_path}"))
        print(print_dim("  Using fallback agent list"))
        print()
        print(f"    \033[1mspecification-agent\033[0m - Creates OpenSpec definitions")
        print(f"    \033[1mtdd-implementation-agent\033[0m - TDD methodology implementation")
        print(f"    \033[1mtest-strategist\033[0m - Test pyramid and coverage design")
        print(f"    \033[1mcode-review-gate\033[0m - Code quality validation")
        print(f"    \033[1mplan-guardian\033[0m - Implementation drift monitoring")
        print()

    # Project Analysis
    print(print_dim("─" * 109))
    print()
    print(print_bold("PROJECT ANALYSIS"))
    print()

    characteristics = analyze_project_characteristics(tasks_file)
    recommended_agents, reasons = recommend_agents(characteristics)

    print(print_dim("  Based on your tasks:"))
    print()

    if characteristics.get('has_api'):
        print(print_green("    ✓ API/service tasks detected → specification-agent for interface contracts"))

    if characteristics.get('has_auth'):
        print(print_green("    ✓ Authentication tasks detected → code-review-gate for security review"))

    complex_count = characteristics.get('complex_count', 0)
    if complex_count > 2:
        print(print_green(f"    ✓ {complex_count} complex tasks → test-strategist for edge cases"))

    task_count = characteristics.get('task_count', 0)
    if task_count > 10:
        print(print_green(f"    ✓ {task_count} tasks → test-strategist for coverage strategy"))

    if not reasons:
        print(print_dim("    No specific patterns detected - using core agents only"))
    print()

    # Agent Selection
    print(print_dim("─" * 109))
    print()
    print(print_bold("SELECT AGENT CONFIGURATION"))
    print()

    rec_string = ', '.join(recommended_agents)
    print(print_dim(f"  Recommended: {rec_string}"))
    print()

    # Build list of all available agents
    all_impl_agents = [a['name'] for a in agents] if agents else [
        "specification-agent", "tdd-implementation-agent", "test-strategist",
        "code-review-gate", "plan-guardian"
    ]

    print(print_cyan("Options:"))
    print()
    print(print_green(f"  [approve]    Use recommended agents ({len(recommended_agents)} agents)"))
    print(print_yellow("  [core]       Core agents only (specification-agent, tdd-implementation-agent)"))
    print(print_cyan(f"  [full]       All {len(all_impl_agents)} implementation agents"))
    print("\033[35m  [custom]     Select specific agents from inventory\033[0m")  # Magenta
    print(print_dim("  [list]       Show agent inventory again"))
    print()

    selected_agents = []

    while True:
        clear_input_buffer()
        agent_choice = prompt_user("  Choice (default: approve): ").strip().lower() or "approve"

        if agent_choice == "approve":
            selected_agents = recommended_agents[:]
            break
        elif agent_choice == "core":
            selected_agents = ["specification-agent", "tdd-implementation-agent"]
            break
        elif agent_choice == "full":
            selected_agents = all_impl_agents[:]
            break
        elif agent_choice == "custom":
            print()
            print(print_dim("  Available agents from inventory:"))
            for idx, agent_name in enumerate(all_impl_agents, 1):
                if agent_name in ["specification-agent", "tdd-implementation-agent"]:
                    print(f"    {idx}. {agent_name} (required)")
                else:
                    print(f"    {idx}. {agent_name}")
            print()
            custom_selection = prompt_user("  Enter numbers (e.g., '1 2 3'): ").strip()

            # Always include core agents
            selected_agents = ["specification-agent", "tdd-implementation-agent"]
            for num_str in custom_selection.split():
                try:
                    num = int(num_str)
                    if 1 <= num <= len(all_impl_agents):
                        selected = all_impl_agents[num - 1]
                        if selected not in selected_agents:
                            selected_agents.append(selected)
                except ValueError:
                    pass
            break
        elif agent_choice == "list":
            print()
            print(print_cyan("Agent Inventory (06-09-implementation):"))
            for agent in agents:
                name = agent.get('name', '')
                tier = agent.get('tier', '')
                role = agent.get('role', '')
                desc = agent.get('description', '')
                print(f"    {name:25} [{tier}, {role}] {desc}")
            print()
        else:
            print(print_red("  Invalid choice. Try again."))

    print()

    # Confirm Roster
    print(print_dim("─" * 109))
    print()
    print(print_bold("CONFIRMED ROSTER"))
    print()

    # Load models from CSV
    agent_models = {}
    for agent in agents:
        agent_models[agent['name']] = agent.get('model', 'sonnet')

    for agent in selected_agents:
        model = agent_models.get(agent, 'sonnet')
        print(print_green(f"    ✓ {agent} ({model})"))
    print()

    # Save roster with model info
    ensure_dir(roster_file.parent)

    agents_with_models = [f"{agent}:{agent_models.get(agent, 'sonnet')}"
                          for agent in selected_agents]

    roster_data = {
        "phase": 4,
        "phase_name": "Specification",
        "agents": agents_with_models,
        "task_count": task_count,
        "source": "agent-inventory.csv",
        "confirmed_at": str(Path(__file__).stat().st_mtime)
    }

    write_file(roster_file, json.dumps(roster_data, indent=2))

    print(print_green("✓ Agent Selection complete"))

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 402: Agent Selection")
    parser.add_argument('--atomic-root', type=Path, required=True,
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (auto-select agents)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
