"""
Task 904: Release Execution

Execute GitHub release, package publishing, and announcement generation.
Currently focuses on internal release with announcement generation.
"""

import re
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.ui import success, error, warning, info, step
from core.llm import invoke_llm
from core.utils.cli_ui import CYAN, DIM, BOLD, GREEN, YELLOW, NC
from core.utils.file_ops import read_json, write_json, read_file, write_file

logger = logging.getLogger(__name__)


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
                content = read_file(pattern)
                # Strip frontmatter (lines between --- markers)
                lines = content.split('\n')
                if lines and lines[0].strip() == '---':
                    try:
                        end_idx = lines[1:].index('---') + 2
                        return '\n'.join(lines[end_idx:])
                    except ValueError:
                        logger.debug("No closing frontmatter marker in %s", pattern)
                return content
            except Exception as e:
                logger.debug("Failed to read agent prompt %s: %s", pattern, e)

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
        write_json(execution_file, {
            "status": "executed",
            "executed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "uat_mode": True
        })

        write_file(announcement_file, "# Release Announcement (UAT)\n\nRelease executed in UAT mode.\n")

        success("UAT bypass complete")
        return True

    print()
    print(f"  {DIM}Executing release to distribution channels.{NC}")
    print()

    # Load release configuration and gather context
    version, announcement_agent_prompt = _load_release_config(
        setup_file, output_dir, atomic_root
    )
    project_context = _gather_context(project_root, atomic_root)

    # Generate announcement
    announcement_status = _generate_announcement(
        version, project_context, announcement_agent_prompt,
        prompts_dir, announcement_file
    )

    # Save results
    _save_execution_results(
        version, announcement_status, execution_file, output_dir
    )

    success("Release Execution complete")
    return True


def _load_release_config(setup_file: Path, output_dir: Path, atomic_root: Path) -> tuple:
    """Load release configuration and agent prompts. Returns (version, agent_prompt)."""
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
            agents_data = read_json(agents_file)
            agents_array = agents_data.get("agents", [])

            for agent_entry in agents_array:
                parts = agent_entry.split(':', 1)
                agent_name = parts[0]
                agent_prompt = find_agent_prompt(agent_name, agent_repo)

                if agent_prompt:
                    if "announcement" in agent_name.lower() or "writer" in agent_name.lower():
                        announcement_agent_prompt = agent_prompt
                        print(f"  {YELLOW}✓{NC} Loaded agent: {agent_name} (Announcement)")
        except Exception as e:
            logger.debug("Failed to load agents: %s", e)
            print(f"  {YELLOW}!{NC} Failed to load agents: {e}")

        print()
    else:
        print(f"  {YELLOW}!{NC} No agent selection found - using built-in prompts")
        print()

    # Load configuration
    version = "0.1.0"
    if setup_file.exists():
        try:
            setup_data = read_json(setup_file)
            version = setup_data.get("release", {}).get("version", "0.1.0")
        except Exception as e:
            logger.debug("Failed to read release setup: %s", e)

    return version, announcement_agent_prompt


def _gather_context(project_root: Path, atomic_root: Path) -> str:
    """Gather project context for release notes generation."""
    prd_file = project_root / "docs" / "prd" / "PRD.md"
    changelog_file = atomic_root / "CHANGELOG.md"
    project_context = ""

    if prd_file.exists():
        try:
            prd_content = read_file(prd_file)
            project_context += f"## PRD\n{prd_content}\n\n"
        except Exception as e:
            logger.debug("Failed to read PRD file: %s", e)

    if changelog_file.exists():
        try:
            changelog_content = read_file(changelog_file)
            project_context += f"## Changelog\n{changelog_content}\n\n"
        except Exception as e:
            logger.debug("Failed to read changelog: %s", e)

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
                    closeout_data = read_json(cp)
                    phase_summaries.append(
                        f"### Phase {phase_num} ({phase_name})\n"
                        f"{json.dumps(closeout_data, indent=2)}"
                    )
                except Exception as e:
                    logger.debug("Failed to read closeout %s: %s", cp, e)
                break

    if phase_summaries:
        project_context += "## Phase Outcomes (Phases 5-8)\n\n"
        project_context += "\n\n".join(phase_summaries) + "\n\n"

    return project_context


def _generate_announcement(
    version: str, project_context: str, announcement_agent_prompt: str,
    prompts_dir: Path, announcement_file: Path
) -> str:
    """Generate internal release announcement. Returns status string."""
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

    safe_version = re.sub(r'[^a-zA-Z0-9.\-]', '', version)[:50]

    prompt_content += f"""## Release Details

- Version: {safe_version}
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

    write_file(announce_prompt_file, prompt_content)

    print(f"  {DIM}[announcement-writer] Drafting internal release notes...{NC}")
    print()

    # Call LLM for announcement with retry
    announcement_content = ""
    for attempt in range(2):
        try:
            announcement_content = invoke_llm(
                prompt=prompt_content,
                model="haiku",
                max_tokens=2000
            )
            if announcement_content:
                break
        except Exception as e:
            if attempt == 0:
                logger.debug("LLM attempt 1 failed, retrying: %s", e)
            else:
                print(f"  {YELLOW}⚠{NC}  LLM call failed after 2 attempts: {e}")
                print(f"  {DIM}Using fallback template{NC}")

    # Generate internal release notes (using LLM response or fallback)
    used_fallback = False
    if announcement_content:
        write_file(announcement_file, announcement_content)
    else:
        used_fallback = True
        write_file(announcement_file, f"""# Internal Release Notes - v{version}

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

    return "fallback" if used_fallback else "success"


def _save_execution_results(
    version: str, announcement_status: str,
    execution_file: Path, output_dir: Path
) -> None:
    """Save execution record and decision context."""
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
    write_json(execution_file, {
        "release": {
            "version": version,
            "channel": "internal"
        },
        "announcement": {
            "file": ".claude/release/announcement.md",
            "status": announcement_status
        },
        "executed_at": datetime.now(timezone.utc).isoformat()
    })

    # Save decision to context
    decision_file = output_dir / "execution-decision.json"
    decision_file.parent.mkdir(parents=True, exist_ok=True)
    write_json(decision_file, {
        "decision": f"Release v{version} executed: internal",
        "type": "execution",
        "artifact": str(execution_file)
    })


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
