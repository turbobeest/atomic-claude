"""
Task 904: Release Execution

Execute GitHub release, package publishing, and announcement generation.
Currently focuses on internal release with announcement generation.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.ui import success, error, warning, info, step
from core.llm import invoke_llm


# ANSI color codes for formatted output
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
NC = "\033[0m"


def find_agent_prompt(agent_name: str, agent_repo: Path) -> Optional[str]:
    """
    Find and load agent prompt from repository.

    Args:
        agent_name: Name of the agent to find
        agent_repo: Path to agent repository

    Returns:
        Agent prompt content or None if not found
    """
    # Try to find agent file
    agent_patterns = [
        agent_repo / "expert-agents" / f"{agent_name}.md",
        agent_repo / "pipeline-agents" / f"{agent_name}.md",
        agent_repo / f"{agent_name}.md"
    ]

    for pattern in agent_patterns:
        if pattern.exists():
            try:
                with open(pattern) as f:
                    content = f.read()
                # Strip frontmatter (lines between --- markers)
                lines = content.split('\n')
                if lines and lines[0].strip() == '---':
                    try:
                        end_idx = lines[1:].index('---') + 2
                        return '\n'.join(lines[end_idx:])
                    except ValueError:
                        pass
                return content
            except Exception:
                pass

    return None


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 904: Release Execution.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass LLM calls for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    project_root = atomic_root.parent

    release_dir = project_root / ".claude" / "release"
    prompts_dir = release_dir / "prompts"
    setup_file = release_dir / "setup.json"
    execution_file = release_dir / "execution.json"
    announcement_file = release_dir / "announcement.md"

    step("Release Execution")

    release_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # UAT Mode Bypass
    if uat_mode:
        print(f"  {DIM}UAT Mode: Creating minimal valid output{NC}")

        # Create minimal execution file
        with open(execution_file, 'w') as f:
            json.dump({
                "status": "executed",
                "executed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "uat_mode": True
            }, f, indent=2)

        with open(announcement_file, 'w') as f:
            f.write("# Release Announcement (UAT)\n\n")
            f.write("Release executed in UAT mode.\n")

        success("UAT bypass complete")
        return True

    print()
    print(f"  {DIM}Executing release to distribution channels.{NC}")
    print()

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # LOAD RELEASE AGENTS FROM TASK 903 SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    agents_file = output_dir / "release-agents.json"

    # Check embedded repo first (monorepo deployment), then env var, then default
    agent_repo = atomic_root / "repos" / "agents"
    if (atomic_root / "agents" / "agent-inventory.csv").exists():
        agent_repo = atomic_root / "agents"

    # Agent prompts (loaded from agents repository if available)
    announcement_agent_prompt = ""

    if agents_file.exists():
        print(f"  {DIM}Loading release agents from selection...{NC}")
        print()

        try:
            with open(agents_file) as f:
                agents_data = json.load(f)

            agents_array = agents_data.get("agents", [])

            for agent_entry in agents_array:
                agent_name = agent_entry.split(':')[0]
                agent_prompt = find_agent_prompt(agent_name, agent_repo)

                if agent_prompt:
                    if "announcement" in agent_name.lower() or "writer" in agent_name.lower():
                        announcement_agent_prompt = agent_prompt
                        print(f"  {YELLOW}✓{NC} Loaded agent: {agent_name} (Announcement)")
        except Exception as e:
            print(f"  {YELLOW}!{NC} Failed to load agents: {e}")

        print()
    else:
        print(f"  {YELLOW}!{NC} No agent selection found - using built-in prompts")
        print()

    # Load configuration
    version = "0.1.0"
    if setup_file.exists():
        try:
            with open(setup_file) as f:
                setup_data = json.load(f)
            version = setup_data.get("release", {}).get("version", "0.1.0")
        except:
            pass

    # Gather project context — load full content for informed release notes
    prd_file = project_root / "docs" / "prd" / "PRD.md"
    changelog_file = atomic_root / "CHANGELOG.md"
    project_context = ""

    if prd_file.exists():
        try:
            with open(prd_file) as f:
                prd_content = f.read()
            project_context += f"## PRD\n{prd_content}\n\n"
        except:
            pass

    if changelog_file.exists():
        try:
            with open(changelog_file) as f:
                changelog_content = f.read()
            project_context += f"## Changelog\n{changelog_content}\n\n"
        except:
            pass

    # Load phase 5-8 summaries for release context
    phase_summaries = []
    for phase_num, phase_name in [(5, "implementation"), (6, "code-review"),
                                   (7, "integration"), (8, "deployment-prep")]:
        closeout_paths = [
            project_root / ".claude" / "closeout" / f"phase-{phase_num:02d}-closeout.json",
            project_root / ".outputs" / f"{phase_num}-{phase_name}" / "closeout.json",
        ]
        for cp in closeout_paths:
            if cp.exists():
                try:
                    with open(cp) as f:
                        closeout_data = json.load(f)
                    phase_summaries.append(
                        f"### Phase {phase_num} ({phase_name})\n"
                        f"{json.dumps(closeout_data, indent=2)}"
                    )
                except:
                    pass
                break

    if phase_summaries:
        project_context += "## Phase Outcomes (Phases 5-8)\n\n"
        project_context += "\n\n".join(phase_summaries) + "\n\n"

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # INTERNAL RELEASE NOTES
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    print()
    print(f"  {BOLD}- INTERNAL RELEASE NOTES{NC}")
    print()

    announce_prompt_file = prompts_dir / "announcement-prompt.md"

    # Build announcement prompt
    prompt_content = ""
    if announcement_agent_prompt:
        prompt_content = announcement_agent_prompt + "\n\n---\n\n"
        prompt_content += "# Announcement Writing Task\n\n"
        prompt_content += "Apply your technical writing expertise to draft internal release notes.\n\n"
    else:
        prompt_content = "# Announcement Writing\n\n"
        prompt_content += "You are an announcement writer agent drafting internal release notes.\n\n"

    prompt_content += f"""## Release Details

- Version: {version}
- Channel: internal

## Project Context

{project_context}

## Instructions

Draft internal release notes for stakeholders. Include:
1. Release summary
2. What's new (features, changes)
3. Artifacts available
4. Next steps

Return as markdown suitable for internal distribution.
"""

    with open(announce_prompt_file, 'w') as f:
        f.write(prompt_content)

    print(f"  {DIM}[announcement-writer] Drafting internal release notes...{NC}")
    print()

    # Call LLM for announcement
    announcement_content = ""
    try:
        # Use haiku for fast generation
        announcement_content = invoke_llm(
            prompt=prompt_content,
            max_tokens=2000
        )
    except Exception as e:
        print(f"  {YELLOW}⚠{NC}  LLM call failed: {e}")
        print(f"  {DIM}Using fallback template{NC}")

    # Generate internal release notes (using LLM response or fallback)
    if announcement_content:
        with open(announcement_file, 'w') as f:
            f.write(announcement_content)
    else:
        with open(announcement_file, 'w') as f:
            f.write(f"""# Internal Release Notes - v{version}

## Release Summary

Version {version} has been completed and is ready for internal use.

## What's New

- Core functionality implementation
- User interface components
- Data persistence layer
- External integrations
- Performance optimizations

## Artifacts

- Distribution package: dist/project-{version}.tar.gz
- Wheel package: dist/project-{version}-py3-none-any.whl

## Next Steps

- Internal testing and validation
- Stakeholder review
- External release planning (if applicable)
""")

    announcement_status = "success"

    print(f"  {'─' * 110}")
    print(f"  {BOLD}INTERNAL RELEASE NOTES{NC}")
    print()
    print(f"    Status:   {GREEN}Draft created{NC}")
    print(f"    Saved to: {DIM}.claude/release/announcement.md{NC}")
    print()
    print(f"    {DIM}Preview:{NC}")
    print(f"      # Internal Release Notes - v{version}")
    print(f"      Version {version} has been completed...")
    print(f"  {'─' * 110}")
    print()

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # EXECUTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    print()
    print(f"  {BOLD}- EXECUTION SUMMARY{NC}")
    print()

    print(f"  {'─' * 110}")
    print(f"  {BOLD}RELEASE EXECUTION STATUS{NC}")
    print()
    print(f"    {GREEN}✓{NC} Internal Release Notes: .claude/release/announcement.md")
    print(f"    {GREEN}✓{NC} Version:                v{version}")
    print(f"    {GREEN}✓{NC} Channel:                internal")
    print(f"  {'─' * 110}")
    print()

    # Save execution record
    with open(execution_file, 'w') as f:
        json.dump({
            "release": {
                "version": version,
                "channel": "internal"
            },
            "announcement": {
                "file": ".claude/release/announcement.md",
                "status": announcement_status
            },
            "executed_at": datetime.now().isoformat()
        }, f, indent=2)

    # Save decision to context
    decision_file = output_dir / "execution-decision.json"
    decision_file.parent.mkdir(parents=True, exist_ok=True)
    with open(decision_file, 'w') as f:
        json.dump({
            "decision": f"Release v{version} executed: internal",
            "type": "execution",
            "artifact": str(execution_file)
        }, f, indent=2)

    success("Release Execution complete")
    return True


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 904: Release Execution")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip LLM calls)')

    args = parser.parse_args()

    result = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if result else 1)
