"""
Memory Enrichment - Extract meaningful summaries from task artifacts.

Reads task output artifacts (JSON files) and produces compact, human-readable
summaries for memory entries instead of generic "Task X completed" messages.

Provides two enrichment levels:
1. summarize_task_artifacts() — fast, no LLM, reads files and extracts key fields
2. enrich_memory_with_llm() — uses haiku to summarize all outputs into rich memory
"""

import json
from pathlib import Path
from typing import List, Optional, Dict


def scan_output_files(output_dir: Path, max_depth: int = 2) -> List[Dict]:
    """
    Scan a phase output directory for all generated files.

    Returns list of dicts: [{name, path, size, suffix}]
    Skips secrets.json and node_modules.
    """
    files = []
    if not output_dir.exists():
        return files

    def _walk(d: Path, depth: int, prefix: str = ""):
        if depth > max_depth:
            return
        try:
            for item in sorted(d.iterdir()):
                if item.name in ("node_modules", "__pycache__", ".git"):
                    continue
                rel = f"{prefix}/{item.name}" if prefix else item.name
                if item.is_dir():
                    _walk(item, depth + 1, rel)
                elif item.is_file():
                    if item.name == "secrets.json":
                        continue
                    try:
                        files.append({
                            "name": rel,
                            "path": str(item),
                            "size": item.stat().st_size,
                            "suffix": item.suffix,
                        })
                    except OSError:
                        pass
        except OSError:
            pass

    _walk(output_dir, 0)
    return files


def summarize_task_artifacts(
    artifact_paths: List[str],
    task_id: str,
    task_name: str,
    output_dir: Optional[Path] = None,
) -> str:
    """
    Read task artifact files and produce a meaningful summary.

    Reads each JSON artifact, extracts key fields, and builds a compact
    summary string suitable for memory storage and dashboard display.
    When output_dir is provided, also lists all files generated during the task.

    Args:
        artifact_paths: List of artifact file paths (absolute or relative)
        task_id: Task identifier (e.g., "001")
        task_name: Human-readable task name
        output_dir: Optional phase output directory for file discovery

    Returns:
        Enriched summary string (falls back to generic if artifacts unreadable)
    """
    parts = [f"Task {task_id} ({task_name}) completed."]
    found_content = False

    # If there are task-specific artifacts, skip project-config.json (it's a shared
    # cumulative config that every task updates — not task-specific content)
    paths_to_summarize = artifact_paths
    if len(artifact_paths) > 1:
        specific = [p for p in artifact_paths if not Path(p).name == "project-config.json"]
        if specific:
            paths_to_summarize = specific

    for artifact_path in paths_to_summarize:
        p = Path(artifact_path)
        if not p.exists() or not p.is_file():
            continue

        try:
            if p.suffix == ".json":
                summary = _summarize_json(p)
            elif p.suffix == ".md":
                summary = _summarize_markdown(p)
            else:
                continue

            if summary:
                parts.append(summary)
                found_content = True
        except Exception:
            continue

    # Discover additional output files beyond registered artifacts
    if output_dir:
        all_files = scan_output_files(output_dir)
        artifact_names = {Path(p).name for p in artifact_paths}
        extra_files = [f for f in all_files if Path(f["name"]).name not in artifact_names]
        if extra_files:
            file_summary = _build_file_inventory(extra_files)
            if file_summary:
                parts.append(file_summary)
                found_content = True

    if not found_content:
        return f"Task {task_id} ({task_name}) completed"

    return "\n".join(parts) if any("\n" in p for p in parts) else " ".join(parts)


def enrich_memory_with_llm(
    artifact_paths: List[str],
    task_id: str,
    task_name: str,
    output_dir: Optional[Path] = None,
    max_input_chars: int = 100_000,
) -> Optional[str]:
    """
    Use a low-cost LLM (haiku) to summarize all task outputs into rich memory.

    Collects artifact content, prompts, and output files, then asks haiku
    to produce a structured summary covering decisions, findings, generated
    files, and key technical details.

    Args:
        artifact_paths: Registered artifact file paths
        task_id: Task identifier
        task_name: Human-readable task name
        output_dir: Phase output directory for file discovery
        max_input_chars: Max chars to feed to the LLM (default 100k tokens ~ 100k chars)

    Returns:
        Rich memory summary string, or None if LLM is unavailable
    """
    try:
        from core.llm.invoke import invoke_llm
    except ImportError:
        return None

    # Gather all content to summarize
    content_parts = []
    total_chars = 0

    # 1. Registered artifacts
    for artifact_path in artifact_paths:
        p = Path(artifact_path)
        if not p.exists() or p.name == "secrets.json":
            continue
        try:
            text = p.read_text(encoding="utf-8")
            label = f"=== {p.name} ({len(text)} chars) ==="
            if total_chars + len(text) + len(label) < max_input_chars:
                content_parts.append(f"{label}\n{text}")
                total_chars += len(text) + len(label)
        except Exception:
            continue

    # 2. Discover additional output files (prompts, markdown, etc.)
    if output_dir:
        all_files = scan_output_files(output_dir)
        artifact_names = {Path(p).name for p in artifact_paths}

        # Prioritize prompts and markdown files (they contain the thought track)
        priority_files = sorted(
            [f for f in all_files if f["suffix"] in (".md", ".txt")],
            key=lambda f: f["size"],
            reverse=True
        )
        json_files = [f for f in all_files
                      if f["suffix"] == ".json" and Path(f["name"]).name not in artifact_names]

        for file_info in priority_files + json_files:
            if total_chars >= max_input_chars:
                break
            try:
                text = Path(file_info["path"]).read_text(encoding="utf-8")
                # Truncate large files to fit budget
                remaining = max_input_chars - total_chars
                if len(text) > remaining:
                    text = text[:remaining] + "\n... (truncated)"
                label = f"=== {file_info['name']} ({file_info['size']} bytes) ==="
                content_parts.append(f"{label}\n{text}")
                total_chars += len(text) + len(label)
            except Exception:
                continue

    if not content_parts:
        return None

    # Build file inventory for reference
    file_list = ""
    if output_dir:
        all_files = scan_output_files(output_dir)
        if all_files:
            file_list = "\n## All Generated Files\n" + "\n".join(
                f"- {f['name']} ({f['size']} bytes)" for f in all_files
            )

    prompt = f"""Summarize the following task outputs into a structured memory entry.
This summary will be stored for future sessions to understand what this task accomplished.

## Task
ID: {task_id}
Name: {task_name}
{file_list}

## Task Output Content
{chr(10).join(content_parts)}

## Instructions
Create a structured summary with these sections (omit empty sections):
- **What was done**: 1-2 sentence summary of the task's purpose and outcome
- **Key decisions**: Important choices made (architecture, tooling, approach)
- **Findings**: What was discovered or analyzed
- **Generated files**: List the most important output files with brief descriptions
- **Technical details**: Specific technical information worth remembering (APIs, schemas, configs)
- **Dependencies & blockers**: What this task depends on or blocks

Keep the total summary under 2000 characters. Be specific and factual — include names, numbers, and paths.
Do NOT include generic boilerplate. Every line should carry information."""

    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            output_file = f.name

        invoke_llm(
            prompt=prompt,
            output_file=output_file,
            model="haiku",
            timeout=120,
        )

        result = Path(output_file).read_text(encoding="utf-8").strip()
        Path(output_file).unlink(missing_ok=True)

        if result and len(result) > 20:
            return f"Task {task_id} ({task_name}) completed.\n\n{result}"

    except Exception:
        pass

    return None


def _build_file_inventory(files: List[Dict]) -> Optional[str]:
    """Build a compact file inventory string."""
    if not files:
        return None

    # Group by directory
    dirs: Dict[str, List[str]] = {}
    for f in files:
        parts = f["name"].split("/")
        if len(parts) > 1:
            dir_name = parts[0]
        else:
            dir_name = "."
        dirs.setdefault(dir_name, []).append(Path(f["name"]).name)

    lines = [f"\nGenerated files ({len(files)} total):"]
    for dir_name, filenames in sorted(dirs.items()):
        if dir_name == ".":
            for fn in filenames[:5]:
                lines.append(f"  {fn}")
        else:
            if len(filenames) <= 3:
                lines.append(f"  {dir_name}/: {', '.join(filenames)}")
            else:
                lines.append(f"  {dir_name}/: {len(filenames)} files")
    if len(files) > 20:
        lines.append(f"  ... and {len(files) - 20} more")

    return "\n".join(lines)


def _summarize_json(path: Path) -> Optional[str]:
    """Extract a meaningful summary from a JSON artifact."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(data, dict):
        return None

    filename = path.stem  # e.g., "project-config", "provider-inventory"

    # --- Dispatch to artifact-specific summarizers ---

    if filename == "project-config" or filename == "extracted-config":
        return _summarize_project_config(data)
    elif filename == "provider-inventory":
        return _summarize_provider_inventory(data)
    elif filename == "material-manifest":
        return _summarize_material_manifest(data)
    elif filename == "env-validation":
        return _summarize_env_validation(data)
    elif filename == "secrets":
        return None  # Never summarize secrets
    elif filename == "selected-agents" or filename == "agent-roster":
        return _summarize_agent_selection(data)
    elif filename == "corpus" or filename == "corpus-analysis":
        return _summarize_corpus(data)
    elif filename == "dialogue":
        return _summarize_dialogue(data)
    elif filename == "closeout":
        return None  # Closeout is redundant with the memory entry itself
    else:
        # Generic JSON summary for unknown artifacts
        return _summarize_generic_json(data, filename)


def _summarize_markdown(path: Path) -> Optional[str]:
    """Extract a brief summary from a markdown file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    lines = text.strip().split("\n")
    if not lines:
        return None

    # Use first heading or first non-empty line as a brief descriptor
    for line in lines[:5]:
        line = line.strip()
        if line.startswith("#"):
            return f"{path.name}: {line.lstrip('#').strip()}"
        elif line and not line.startswith("---"):
            return f"{path.name}: {line[:120]}"

    return None


# --- Artifact-specific summarizers ---

def _summarize_project_config(data: dict) -> Optional[str]:
    """Summarize project-config.json or extracted-config.json."""
    parts = []

    project = data.get("project", {})
    if project:
        name = project.get("name", "")
        ptype = project.get("type", "")
        desc = project.get("description", "")
        if name:
            parts.append(f"Project: {name}")
        if ptype:
            parts.append(f"type={ptype}")
        if desc:
            # Truncate long descriptions
            parts.append(f"({desc[:100]}{'...' if len(desc) > 100 else ''})")

    llm = data.get("llm", data.get("providers", {}))
    if llm:
        provider = llm.get("primary_provider", "")
        model = llm.get("primary_model", "")
        if provider or model:
            parts.append(f"LLM: {provider}/{model}" if provider and model else f"LLM: {provider or model}")

    constraints = data.get("constraints", {})
    if constraints:
        tech = constraints.get("technical", [])
        if isinstance(tech, list) and tech:
            parts.append(f"Constraints: {len(tech)} technical requirements")

    pipeline = data.get("pipeline", {})
    if pipeline:
        mode = pipeline.get("mode", "")
        skip = pipeline.get("skip_phases", [])
        if mode:
            parts.append(f"Pipeline: {mode} mode")
        if skip:
            parts.append(f"skip phases {skip}")

    return "; ".join(parts) if parts else None


def _summarize_provider_inventory(data: dict) -> Optional[str]:
    """Summarize provider-inventory.json."""
    parts = []

    detected = data.get("detected_providers", [])
    if detected:
        parts.append(f"Providers: {', '.join(detected)}")

    health = data.get("provider_health", {})
    healthy = [k for k, v in health.items() if isinstance(v, dict) and v.get("status") == "healthy"]
    unavailable = [k for k, v in health.items() if isinstance(v, dict) and v.get("status") == "unavailable"]
    if healthy:
        parts.append(f"healthy=[{', '.join(healthy)}]")
    if unavailable:
        parts.append(f"unavailable=[{', '.join(unavailable)}]")

    creds = data.get("credentials", {})
    active_creds = [k.replace("has_", "") for k, v in creds.items() if v]
    if active_creds:
        parts.append(f"credentials: {', '.join(active_creds)}")

    return "; ".join(parts) if parts else None


def _summarize_material_manifest(data: dict) -> Optional[str]:
    """Summarize material-manifest.json."""
    parts = []

    summary = data.get("summary", {})
    total = summary.get("total", {})
    if total:
        files = total.get("files", 0)
        lines = total.get("lines", 0)
        parts.append(f"Materials: {files} files, {lines} lines")

    docs = summary.get("documentation", {})
    if docs.get("count", 0) > 0:
        parts.append(f"{docs['count']} docs")

    src = summary.get("source_code", {})
    if src.get("count", 0) > 0:
        parts.append(f"{src['count']} source files ({src.get('lines', 0)} lines)")

    files = data.get("files", {})
    ext_refs = files.get("external_references", [])
    if ext_refs:
        parts.append(f"{len(ext_refs)} external references")

    exclusions = data.get("exclusions", {})
    if exclusions:
        all_scanned = files.get("all_scanned", {})
        if all_scanned:
            original = sum(len(v) for v in all_scanned.values())
            current = total.get("files", 0) if total else 0
            excluded = original - current
            if excluded > 0:
                parts.append(f"{excluded} excluded")

    stack = data.get("detected_stack", {})
    langs = stack.get("languages", [])
    frameworks = stack.get("frameworks", [])
    if langs:
        parts.append(f"languages: {', '.join(langs)}")
    if frameworks:
        parts.append(f"frameworks: {', '.join(frameworks)}")

    return "; ".join(parts) if parts else None


def _summarize_env_validation(data: dict) -> Optional[str]:
    """Summarize env-validation.json."""
    parts = []

    summary = data.get("summary", {})
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    warnings = summary.get("warnings", 0)
    parts.append(f"Environment: {passed} passed, {failed} failed, {warnings} warnings")

    caps = data.get("capabilities", {})
    cpu = caps.get("cpu", {})
    mem = caps.get("memory", {})
    if cpu:
        arch = cpu.get("architecture", "")
        cores = cpu.get("cores", "")
        if arch and cores:
            parts.append(f"system: {arch}/{cores} cores")
    if mem:
        total_mb = mem.get("total_mb", 0)
        if total_mb:
            parts.append(f"{total_mb}MB RAM")

    return "; ".join(parts) if parts else None


def _summarize_agent_selection(data: dict) -> Optional[str]:
    """Summarize selected-agents.json or agent-roster.json."""
    parts = []

    # Handle both formats: {agents: [...]} and {selected_experts: [...]}
    agents = data.get("agents", data.get("selected_experts", []))
    if isinstance(agents, list) and agents:
        parts.append(f"Agents: {', '.join(str(a) for a in agents[:5])}")
        if len(agents) > 5:
            parts.append(f"(+{len(agents) - 5} more)")

    # TDD agents format
    tdd = data.get("tdd_agents", {})
    if tdd:
        roles = []
        for role, info in tdd.items():
            if isinstance(info, dict):
                roles.append(f"{role}={info.get('name', '?')}")
        if roles:
            parts.append(f"TDD: {', '.join(roles)}")

    total = data.get("total_experts", len(agents) if isinstance(agents, list) else 0)
    if total and not parts:
        parts.append(f"total={total}")

    return "; ".join(parts) if parts else None


def _summarize_corpus(data: dict) -> Optional[str]:
    """Summarize corpus.json."""
    materials = data.get("materials", [])
    if materials:
        names = [m.get("name", "unknown") for m in materials[:5]]
        summary = f"Corpus: {len(materials)} materials ({', '.join(names)}"
        if len(materials) > 5:
            summary += f", +{len(materials) - 5} more"
        summary += ")"
        return summary
    return None


def _summarize_dialogue(data: dict) -> Optional[str]:
    """Summarize dialogue.json."""
    parts = []

    # Count exchanges
    exchanges = data.get("exchanges", data.get("messages", []))
    if isinstance(exchanges, list):
        parts.append(f"Dialogue: {len(exchanges)} exchanges")

    # Look for topics or decisions
    topics = data.get("topics", data.get("key_topics", []))
    if isinstance(topics, list) and topics:
        parts.append(f"topics: {', '.join(str(t) for t in topics[:3])}")

    decisions = data.get("decisions", data.get("key_decisions", []))
    if isinstance(decisions, list) and decisions:
        parts.append(f"{len(decisions)} decisions")

    return "; ".join(parts) if parts else None


def _summarize_generic_json(data: dict, filename: str) -> Optional[str]:
    """Generic summary for unrecognized JSON artifacts."""
    parts = [f"{filename}:"]

    # Look for common summary/status fields
    for key in ("status", "result", "summary", "outcome"):
        val = data.get(key)
        if val:
            if isinstance(val, str):
                parts.append(f"{key}={val[:80]}")
            elif isinstance(val, dict):
                parts.append(f"{key}={json.dumps(val, default=str)[:80]}")
            break

    # Count top-level keys for context
    if len(parts) == 1:  # Only have filename so far
        keys = [k for k in data.keys() if k not in ("timestamp", "created_at", "updated_at", "version")]
        if keys:
            parts.append(f"keys=[{', '.join(keys[:6])}]")

    return " ".join(parts) if len(parts) > 1 else None
