"""
Task 303: Task Decomposition

Break PRD into TaskMaster-format tasks.

Uses task-decomposer agent to:
  1. Parse PRD feature requirements (Section 4)
  2. Generate atomic tasks with acceptance criteria
  3. Create .taskmaster/tasks/tasks.json

Task priorities derived from PRD RFC 2119 keywords:
  SHALL/MUST → high
  SHOULD → medium
  MAY → low
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.llm import invoke
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user
)
from core.utils.file_ops import ensure_dir, read_file, write_file


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None) -> bool:
    """
    Execute Task 303: Task Decomposition.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing

    Returns:
        True if task completed successfully, False otherwise
    """
    agents_file = output_dir / "selected-agents.json"
    project_root = atomic_root.parent
    prd_file = project_root / "docs" / "prd" / "PRD.md"
    taskmaster_dir = project_root / ".taskmaster"
    tasks_file = taskmaster_dir / "tasks" / "tasks.json"
    prompts_dir = output_dir / "prompts"
    raw_tasks_file = output_dir / "raw-tasks.json"

    ensure_dir(prompts_dir)
    ensure_dir(taskmaster_dir / "tasks")

    print()
    print(print_dim("Breaking PRD into atomic, implementable tasks using TaskMaster format."))
    print(print_dim("Output: .taskmaster/tasks/tasks.json"))
    print()

    # Load Selected Agents
    decomposer_prompt = ""
    agent_repo = _find_agent_repo(atomic_root)

    if agents_file.exists():
        agents_data = json.loads(read_file(agents_file))
        decomposition_agents = agents_data.get("decomposition_agents", [])

        for agent in decomposition_agents:
            if "task-decomposer" in agent:
                agent_file = _find_agent_file(agent, agent_repo)
                if agent_file and agent_file.exists():
                    decomposer_prompt = _strip_frontmatter(read_file(agent_file))
                    print(print_green(f"✓ Loaded agent: {agent}"))
            elif "dependency-mapper" in agent:
                print(print_green(f"✓ Found agent: {agent} (for Task 304)"))

        validation_agents = agents_data.get("validation_agents", [])
        for agent in validation_agents:
            if "task-validator" in agent:
                print(print_green(f"✓ Loaded agent: {agent}"))
        print()
    else:
        print(print_dim("No agent selection found - using built-in decomposition logic"))
        print()

    # PRD Extraction
    print(print_dim("─" * 100))
    print()
    print(print_bold("PRD EXTRACTION"))
    print()

    if not prd_file.exists():
        print(print_red(f"✗ PRD file not found: {prd_file}"))
        return False

    prd_content = read_file(prd_file)
    prd_lines = len(prd_content.splitlines())

    # Extract relevant sections
    sections = _extract_prd_sections(prd_content)
    project_name = _extract_project_name(prd_content)

    # Load corpus analysis for technical context
    corpus_analysis_file = project_root / ".outputs" / "1-discovery" / "corpus-analysis.md"
    if corpus_analysis_file.exists():
        try:
            analysis = read_file(corpus_analysis_file).strip()
            if analysis:
                sections["corpus_analysis"] = analysis
        except Exception:
            pass

    print(print_green(f"✓ PRD loaded ({prd_lines} lines)"))
    print(print_dim("  Extracted: Feature Requirements, Dependencies, Phases, Tech Stack"))
    print()

    # Task Generation
    print(print_dim("─" * 100))
    print()
    print(print_bold("TASK GENERATION"))
    print()

    # Try per-feature decomposition for large PRDs
    features_text = sections.get("features", "")
    feature_list = _split_into_features(features_text) if features_text else []
    use_per_feature = len(feature_list) >= 2 and not uat_mode

    if use_per_feature:
        print(print_dim(f"Large PRD detected — decomposing {len(feature_list)} features individually"))
        print()

        feature_results = []
        failed_features = []

        for i, (feature_id, feature_content) in enumerate(feature_list, 1):
            print(print_dim(f"  [{i}/{len(feature_list)}] Decomposing {feature_id}..."))

            feat_prompt = _build_decomposition_prompt(
                decomposer_prompt,
                project_name,
                sections,
                uat_mode,
                feature=(feature_id, feature_content)
            )

            # Save per-feature prompt for debugging
            feat_prompt_file = prompts_dir / f"task-decomposition-{feature_id}.md"
            write_file(feat_prompt_file, feat_prompt)

            feat_output = output_dir / f"raw-tasks-{feature_id}.json"

            try:
                result = invoke(
                    prompt=feat_prompt,
                    output_file=feat_output,
                    description=f"Decompose {feature_id}",
                    model="opus",
                    timeout=900
                )

                if result and feat_output.exists():
                    raw = read_file(feat_output)
                    try:
                        feat_tasks = json.loads(raw)
                        count = len(feat_tasks.get("tasks", []))
                        print(print_green(f"    ✓ {count} tasks from {feature_id}"))
                        feature_results.append((feature_id, feat_tasks))
                    except json.JSONDecodeError:
                        # Try repair
                        if _repair_json(feat_output):
                            feat_tasks = json.loads(read_file(feat_output))
                            count = len(feat_tasks.get("tasks", []))
                            print(print_green(f"    ✓ {count} tasks from {feature_id} (repaired)"))
                            feature_results.append((feature_id, feat_tasks))
                        else:
                            print(print_yellow(f"    ⚠ {feature_id}: invalid JSON, skipping"))
                            failed_features.append(feature_id)
                else:
                    print(print_yellow(f"    ⚠ {feature_id}: no output, skipping"))
                    failed_features.append(feature_id)
            except Exception as e:
                print(print_yellow(f"    ⚠ {feature_id} error: {e}"))
                failed_features.append(feature_id)

        print()

        if feature_results:
            # Merge all feature tasks
            merged = _merge_feature_tasks(feature_results, project_name)
            write_file(raw_tasks_file, json.dumps(merged, indent=2))
            total = len(merged.get("tasks", []))
            print(print_green(f"✓ Merged {total} tasks from {len(feature_results)} features"))
            if failed_features:
                print(print_yellow(f"⚠ Skipped features: {', '.join(failed_features)}"))
        else:
            print(print_yellow("⚠ All per-feature calls failed — falling back to template"))
            _create_template_tasks(raw_tasks_file)
    else:
        # Single-call path: small PRDs or UAT mode
        prompt_content = _build_decomposition_prompt(
            decomposer_prompt,
            project_name,
            sections,
            uat_mode
        )
        prompt_file = prompts_dir / "task-decomposition.md"
        write_file(prompt_file, prompt_content)

        print(print_dim("Invoking task-decomposer agent..."))
        print()

        # Use longer timeout for monolithic call
        single_timeout = 1800 if not uat_mode else 600

        try:
            result = invoke(
                prompt=prompt_content,
                output_file=raw_tasks_file,
                description="Task decomposition",
                model="opus",
                timeout=single_timeout
            )

            if result and raw_tasks_file.exists():
                try:
                    tasks_data = json.loads(read_file(raw_tasks_file))
                    task_count = len(tasks_data.get("tasks", []))
                    print(print_green(f"✓ Generated {task_count} tasks"))
                except json.JSONDecodeError:
                    print(print_yellow("⚠ Invalid JSON output - attempting repair"))
                    if not _repair_json(raw_tasks_file):
                        _create_template_tasks(raw_tasks_file)
            else:
                print(print_yellow("⚠ Task decomposition failed - creating template"))
                _create_template_tasks(raw_tasks_file)
        except Exception as e:
            print(print_yellow(f"⚠ Task decomposition error: {e}"))
            _create_template_tasks(raw_tasks_file)

    print()

    # Task Validation
    _show_task_validation(raw_tasks_file)

    # TaskMaster Integration
    print(print_dim("─" * 100))
    print()
    print(print_bold("TASKMASTER INTEGRATION"))
    print()

    # Copy to tasks file
    write_file(tasks_file, read_file(raw_tasks_file))
    print(print_green("✓ Tasks written to .taskmaster/tasks/tasks.json"))
    print()

    # Task Preview
    _show_task_preview(tasks_file)

    print(print_green("✓ Task decomposition complete"))
    return True


def _find_agent_repo(atomic_root: Path) -> Path:
    """Find agent repository location."""
    # Check embedded repo first
    if (atomic_root.parent / "agents" / "agent-inventory.csv").exists():
        return atomic_root.parent / "agents"

    # Check environment variable
    import os
    agent_repo = os.environ.get("ATOMIC_AGENT_REPO")
    if agent_repo:
        return Path(agent_repo)

    # Default
    return atomic_root.parent / "repos" / "agents"


def _find_agent_file(agent_name: str, agent_repo: Path) -> Optional[Path]:
    """Find agent file in repository."""
    # Try expert-agents first
    agent_file = agent_repo / "expert-agents" / f"{agent_name}.md"
    if agent_file.exists():
        return agent_file

    # Try pipeline-agents
    agent_file = agent_repo / "pipeline-agents" / f"{agent_name}.md"
    if agent_file.exists():
        return agent_file

    return None


def _strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter from agent file."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content


def _extract_prd_sections(content: str) -> Dict[str, str]:
    """Extract relevant sections from PRD."""
    sections = {}

    # Extract Section 3: Feature Requirements — full content for accurate decomposition
    # Support both "# 3." and "## 3." heading levels
    match = re.search(r'^#{1,2} 3\. Feature Requirements(.+?)^#{1,2} 4\.', content, re.MULTILINE | re.DOTALL)
    if match:
        sections["features"] = match.group(1).strip()

    # Extract Section 4: Non-Functional Requirements
    match = re.search(r'^#{1,2} 4\. Non-Functional(.+?)^#{1,2} 5\.', content, re.MULTILINE | re.DOTALL)
    if match:
        sections["nfrs"] = match.group(1).strip()

    # Extract Section 5: Logical Dependency Chain
    match = re.search(r'^#{1,2} 5\. Logical Dependency(.+?)^#{1,2} 6\.', content, re.MULTILINE | re.DOTALL)
    if match:
        sections["dependencies"] = match.group(1).strip()

    # Extract Section 6: Development Phases
    match = re.search(r'^#{1,2} 6\. Development Phases(.+?)^#{1,2} 7\.', content, re.MULTILINE | re.DOTALL)
    if match:
        sections["phases"] = match.group(1).strip()

    # Extract Tech Stack — support ## 2.1 and ### 2.1 heading levels
    match = re.search(r'^#{2,3} 2\.1 Tech Stack(.+?)^#{2,3} 2\.2', content, re.MULTILINE | re.DOTALL)
    if match:
        sections["tech_stack"] = match.group(1).strip()

    return sections


def _split_into_features(features_text: str) -> List[tuple]:
    """
    Split features section into individual features by sub-headings.

    Supports heading formats:
      ### F1: Title, ### F2: Title
      ### 3.1 Title, ### 3.2 Title
      ## F1: Title, ## F2: Title
      #### F1: Title

    Returns:
        List of (feature_id, feature_content) tuples.
        If no sub-headings found, returns the whole section as one chunk.
    """
    # Match feature sub-headings: ### F1:, ## 3.1, #### F1:, ### Feature 1, etc.
    pattern = r'^(#{2,4})\s+(F\d+[:\s]|3\.\d+\s|\d+\.\d+\s|Feature\s+\d+)'
    splits = list(re.finditer(pattern, features_text, re.MULTILINE))

    if len(splits) < 2:
        # Can't split meaningfully — return whole section
        return [("all", features_text)]

    features = []
    for i, m in enumerate(splits):
        start = m.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(features_text)
        chunk = features_text[start:end].strip()

        # Extract feature ID from the heading
        heading_line = chunk.split("\n", 1)[0]
        # Try to pull F1, F2, 3.1, etc. from the heading
        fid_match = re.search(r'(F\d+|3\.\d+|\d+\.\d+)', heading_line)
        feature_id = fid_match.group(1) if fid_match else f"feature-{i+1}"

        features.append((feature_id, chunk))

    return features


def _merge_feature_tasks(
    feature_results: List[tuple],
    project_name: str
) -> Dict[str, Any]:
    """
    Merge per-feature task lists into one unified task set.

    Args:
        feature_results: List of (feature_id, tasks_data_dict) tuples
        project_name: Project name for meta

    Returns:
        Merged tasks dict with re-numbered IDs and remapped dependencies.
    """
    id_remap = {}  # (feature_idx, old_id) -> new_id
    next_id = 1

    # First pass: assign new sequential IDs and build remap table
    for feat_idx, (feature_id, tasks_data) in enumerate(feature_results):
        tasks = tasks_data.get("tasks", [])
        for task in tasks:
            old_id = task.get("id", 0)
            id_remap[(feat_idx, old_id)] = next_id
            task["id"] = next_id
            # Tag with source feature
            task.setdefault("tags", [])
            if feature_id not in task["tags"]:
                task["tags"].append(feature_id)
            next_id += 1

    # Second pass: remap dependencies and collect tasks
    all_tasks = []
    for feat_idx, (feature_id, tasks_data) in enumerate(feature_results):
        tasks = tasks_data.get("tasks", [])
        for task in tasks:
            old_deps = task.get("dependencies", [])
            new_deps = []
            for dep_id in old_deps:
                # Try same-feature remap first
                new_dep = id_remap.get((feat_idx, dep_id))
                if new_dep is not None:
                    new_deps.append(new_dep)
                # else: cross-feature dep — leave for task 304 dependency mapper
            task["dependencies"] = new_deps
            all_tasks.append(task)

    return {
        "meta": {
            "project_name": project_name,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": "prd-sectional",
            "version": "1.0"
        },
        "tasks": all_tasks
    }


def _extract_project_name(content: str) -> str:
    """Extract project name from PRD."""
    match = re.search(r'^# (.+?)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Project"


def _build_decomposition_prompt(
    agent_prompt: str,
    project_name: str,
    sections: Dict[str, str],
    uat_mode: bool,
    feature: Optional[tuple] = None
) -> str:
    """Build the task decomposition prompt."""
    if agent_prompt:
        prompt = agent_prompt + "\n\n---\n\n"
        prompt += "# Task: PRD to TaskMaster Decomposition\n\n"
        prompt += "Apply your task decomposition expertise to the PRD below, following PRD-TEMPLATE v3.0 structure.\n\n"
    else:
        prompt = "# Task: PRD to TaskMaster Decomposition\n\n"
        prompt += "You are a task-decomposer agent. Your job is to break down the PRD into atomic, implementable tasks following PRD-TEMPLATE v3.0 structure.\n\n"

    # Fast-path constraint
    if uat_mode:
        prompt += "## Token Budget Warning\n\n"
        prompt += "**FAST-PATH MODE**: Generate MAXIMUM 5 tasks only. Focus on:\n"
        prompt += "- 1 infrastructure/setup task\n"
        prompt += "- 1-2 core feature tasks\n"
        prompt += "- 1 testing task\n"
        prompt += "- 1 deployment task\n\n"
        prompt += "Keep it minimal for pipeline testing.\n\n"
    elif feature:
        # Per-feature mode: smaller, focused output
        feature_id, feature_content = feature
        prompt += "## Token Budget Warning\n\n"
        prompt += f"You are decomposing **one feature ({feature_id})** from the PRD.\n"
        prompt += "Generate 3-15 tasks for this feature only. Keep descriptions concise (1-2 sentences). "
        prompt += "Acceptance criteria should be bullet points, not paragraphs.\n"
        prompt += "Start task IDs from 1. Dependencies reference IDs within this feature set only.\n\n"
    else:
        prompt += "## Token Budget Warning\n\n"
        prompt += "Your output should be 50-150 tasks typically. Keep descriptions concise (1-2 sentences). "
        prompt += "Acceptance criteria should be bullet points, not paragraphs.\n\n"

    prompt += f"## Project Context\n\nProject Name: {project_name}\n\n"

    # Add corpus analysis for technical context if available
    if "corpus_analysis" in sections:
        prompt += f"### Technical Landscape (Corpus Analysis)\n{sections['corpus_analysis']}\n\n"

    prompt += """## Task Generation Rules

1. **Each Feature (F1, F2, ...)** → One top-level task
2. **Each FR (FR-001, FR-002, ...)** → Details in description or later subtasks (Phase 4)
3. **Dependencies** → From PRD dependency chain section
4. **Priorities** → From RFC 2119 keywords:
   - SHALL/MUST → "high"
   - SHOULD → "medium"
   - MAY → "low"

## Categories

- **infrastructure**: Setup, CI/CD, project structure (F0)
- **feature**: Core functionality from Feature Requirements
- **testing**: Test infrastructure (TDD subtasks come in Phase 4)
- **documentation**: API docs, guides
- **security**: Auth, validation from NFRs

## Complete Example Output

Here is a complete, valid example of the expected output format:

```json
{
  "meta": {
    "project_name": "TaskFlow API",
    "generated_at": "2024-01-15T10:30:00Z",
    "source": "prd",
    "version": "1.0"
  },
  "tasks": [
    {
      "id": 1,
      "title": "F0: Foundation Setup",
      "description": "Initialize project structure with Node.js, TypeScript, and Express per tech stack",
      "status": "pending",
      "priority": "high",
      "category": "infrastructure",
      "dependencies": [],
      "acceptance_criteria": "- package.json configured\\n- TypeScript compiles\\n- Express server starts on port 3000",
      "tags": ["setup", "foundation"],
      "estimated_complexity": "simple",
      "prd_section": "Section 6",
      "subtasks": []
    }
  ]
}
```

## Decomposition Checklist

Before outputting, verify:
- [ ] All Features (F1, F2, ...) from Section 3 have corresponding tasks
- [ ] Dependencies match the Logical Dependency Chain
- [ ] Acceptance criteria are testable (not vague)
- [ ] No circular dependencies (valid DAG)
- [ ] ID 1 is always foundation/setup

## Output Format

Generate ONLY valid JSON. No markdown wrapper, no explanations.
Start with `{` and end with `}`.

---

## PRD Sections (Extracted)

"""

    if "tech_stack" in sections:
        prompt += f"### Tech Stack\n{sections['tech_stack']}\n\n"

    if feature:
        # Per-feature mode: only include this feature's content
        feature_id, feature_content = feature
        prompt += f"### Feature: {feature_id}\n{feature_content}\n\n"
        # Include trimmed NFRs for context (first 2000 chars)
        if "nfrs" in sections:
            nfrs = sections["nfrs"]
            if len(nfrs) > 2000:
                nfrs = nfrs[:2000] + "\n\n... (truncated)"
            prompt += f"### Non-Functional Requirements (summary)\n{nfrs}\n\n"
        if "dependencies" in sections:
            prompt += f"### Logical Dependency Chain (Section 5)\n{sections['dependencies']}\n\n"
    else:
        # Full mode: include all sections
        if "features" in sections:
            prompt += f"### Feature Requirements (Section 3)\n{sections['features']}\n\n"
        if "nfrs" in sections:
            prompt += f"### Non-Functional Requirements (Section 4)\n{sections['nfrs']}\n\n"
        if "dependencies" in sections:
            prompt += f"### Logical Dependency Chain (Section 5)\n{sections['dependencies']}\n\n"
        if "phases" in sections:
            prompt += f"### Development Phases (Section 6)\n{sections['phases']}\n\n"

    return prompt


def _show_task_validation(tasks_file: Path) -> None:
    """Display task validation statistics."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("TASK VALIDATION"))
    print()

    try:
        tasks_data = json.loads(read_file(tasks_file))
        tasks = tasks_data.get("tasks", [])
        task_count = len(tasks)
        with_criteria = sum(1 for t in tasks if t.get("acceptance_criteria"))
        with_deps = sum(1 for t in tasks if t.get("dependencies"))
        high_priority = sum(1 for t in tasks if t.get("priority") == "high")
        medium_priority = sum(1 for t in tasks if t.get("priority") == "medium")
        low_priority = sum(1 for t in tasks if t.get("priority") == "low")

        print(print_bold("Task Statistics:"))
        print()
        print(f"  Total tasks:         {task_count}")
        print(f"  With criteria:       {with_criteria}")
        print(f"  With dependencies:   {with_deps}")
        print()
        print(print_bold("Priority Distribution:"))
        print()
        print(f"  High (SHALL/MUST):   {high_priority}")
        print(f"  Medium (SHOULD):     {medium_priority}")
        print(f"  Low (MAY):           {low_priority}")
        print()

        issues = 0
        if with_criteria < task_count:
            print(print_yellow(f"! {task_count - with_criteria} tasks missing acceptance criteria"))
            issues += 1

        if task_count > 0 and with_deps == 0:
            print(print_yellow("! No dependencies defined (verify PRD dependency tables)"))

        if issues == 0:
            print(print_green("✓ All validation checks passed"))
        print()

    except Exception as e:
        print(print_yellow(f"⚠ Could not validate tasks: {e}"))
        print()


def _show_task_preview(tasks_file: Path) -> None:
    """Display preview of generated tasks."""
    print(print_dim("─" * 100))
    print()
    print(print_bold("TASK PREVIEW"))
    print()

    try:
        tasks_data = json.loads(read_file(tasks_file))
        tasks = tasks_data.get("tasks", [])
        preview_count = min(5, len(tasks))

        for task in tasks[:preview_count]:
            task_id = task.get("id", "?")
            title = task.get("title", "Untitled")
            priority = task.get("priority", "medium")
            print(f"  [{task_id}] {title} ({priority})")

        print()
        if len(tasks) > preview_count:
            print(print_dim(f"  ... and {len(tasks) - preview_count} more"))
            print()
    except Exception as e:
        print(print_dim("  (Unable to preview tasks)"))
        print()


def _repair_json(file_path: Path) -> bool:
    """Attempt to repair malformed JSON."""
    content = read_file(file_path)

    # Try to extract JSON from markdown code blocks
    if "```json" in content:
        match = re.search(r'```json\s*(.+?)\s*```', content, re.DOTALL)
        if match:
            json_content = match.group(1)
            try:
                json.loads(json_content)
                write_file(file_path, json_content)
                print(print_green("✓ JSON repaired from markdown"))
                return True
            except:
                pass

    # Try to find JSON object
    if "{" in content:
        start = content.index("{")
        json_content = content[start:]
        try:
            json.loads(json_content)
            write_file(file_path, json_content)
            print(print_green("✓ JSON extracted from output"))
            return True
        except:
            pass

    return False


def _create_template_tasks(file_path: Path) -> None:
    """Create template tasks when generation fails."""
    template = {
        "meta": {
            "project_name": "Project",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source": "template",
            "version": "1.0"
        },
        "tasks": [
            {
                "id": 1,
                "title": "F0: Foundation Setup",
                "description": "Initialize project structure and development environment",
                "status": "pending",
                "priority": "high",
                "category": "infrastructure",
                "dependencies": [],
                "acceptance_criteria": "Project builds successfully, tests run",
                "tags": ["setup", "foundation"],
                "estimated_complexity": "simple",
                "prd_section": "Section 6: Code Structure",
                "subtasks": []
            },
            {
                "id": 2,
                "title": "F1: Core Feature Implementation",
                "description": "Implement primary feature from PRD Section 4",
                "status": "pending",
                "priority": "high",
                "category": "feature",
                "dependencies": [1],
                "acceptance_criteria": "Feature works as specified in PRD",
                "tags": ["core", "feature"],
                "estimated_complexity": "moderate",
                "prd_section": "Section 4: Feature Requirements",
                "subtasks": []
            },
            {
                "id": 3,
                "title": "Test Infrastructure",
                "description": "Set up testing framework per PRD Section 7",
                "status": "pending",
                "priority": "high",
                "category": "testing",
                "dependencies": [1],
                "acceptance_criteria": "Test framework configured, sample test runs",
                "tags": ["testing", "infrastructure"],
                "estimated_complexity": "simple",
                "prd_section": "Section 7: TDD Implementation Guide",
                "subtasks": []
            }
        ]
    }

    write_file(file_path, json.dumps(template, indent=2))
    print(print_yellow("⚠ Created template tasks - manual refinement required"))


if __name__ == "__main__":
    # CLI execution support
    import argparse

    parser = argparse.ArgumentParser(description="Task 303: Task Decomposition")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (skip interactive prompts)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
