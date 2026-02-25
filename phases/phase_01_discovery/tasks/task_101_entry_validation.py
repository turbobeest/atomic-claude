"""
Task 101: Entry Validation & Corpus Analysis

Validate Phase 0 completion, load prerequisites, and analyze
collected reference materials.

Checks:
  - phase-00-closeout.md exists
  - project-config.json is valid
  - pipeline-state.json shows Phase 0 complete

Then:
  - Loads materials from docs/reference/ (collected by Task 005)
  - Runs LLM analysis on the corpus
  - Conversational reflection to confirm understanding
  - Saves corpus data for downstream phases
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.llm import invoke_llm as invoke
from core.ui import phase_header, success, error, warning, info, step
from core.utils.file_ops import write_json, write_file

# Supported file extensions for corpus analysis
SUPPORTED_EXTS = {'.md', '.txt', '.rst', '.pdf', '.json', '.yaml', '.yml', '.dot', '.svg'}


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 101: Entry Validation & Corpus Analysis.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, bypass interactive prompts for testing
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if validation passed, False otherwise
    """
    setup_dir = output_dir.parent / "0-setup"
    project_root = atomic_root.parent

    # Phase 1 Welcome Banner
    print()
    print("━" * 80)
    print("""
 ______  _____ _______ _______  _____  _    _ _______  ______ __   __
 |     \\   |   |______ |       |     |  \\  /  |______ |_____/   \\_/
 |_____/ __|__ ______| |_____  |_____|   \\/   |______ |    \\_    |
""")
    print("━" * 80)
    print("                       [ PHASE 01 - DISCOVERY ]")
    print()

    step("Entry Validation")
    print()
    print("  Validating Phase 0 completion...")
    print()

    validation_passed = True
    issues = []

    # ═══════════════════════════════════════════════════════════════
    # CHECK 1: Phase 0 Closeout
    # ═══════════════════════════════════════════════════════════════

    closeout_file = _find_closeout(atomic_root, "0-setup")

    if closeout_file:
        print("  ✓ Phase 0 closeout found")
    else:
        print("  ✗ Phase 0 closeout not found")
        issues.append("Phase 0 closeout missing - run Phase 0 first")
        validation_passed = False

    # ═══════════════════════════════════════════════════════════════
    # CHECK 2: Project Config
    # ═══════════════════════════════════════════════════════════════

    config_file = setup_dir / "project-config.json"
    if config_file.exists():
        try:
            with open(config_file) as f:
                config_data = json.load(f)
            print("  ✓ project-config.json valid")

            # Check if config was flattened (Task 003 approval)
            project_name = config_data.get('project', {}).get('name')
            if not project_name:
                extracted_name = config_data.get('extracted', {}).get('project', {}).get('name')
                if extracted_name:
                    print("  ! Config not flattened - auto-flattening from extracted data")
                    _flatten_config(config_file, config_data)
                    project_name = extracted_name
                    print(f"  ✓ Config flattened: {project_name}")
                else:
                    print("  ! project.name not set")
                    issues.append("Project name not configured")

        except (json.JSONDecodeError, OSError) as e:
            print("  ✗ project-config.json invalid JSON")
            issues.append("Project config is invalid JSON")
            validation_passed = False
    else:
        print("  ✗ project-config.json not found")
        issues.append("Project config missing")
        validation_passed = False

    # ═══════════════════════════════════════════════════════════════
    # CHECK 3: Pipeline State
    # ═══════════════════════════════════════════════════════════════

    state_file = atomic_root / ".state" / "task-state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                state_data = json.load(f)
            raw_phase = state_data.get('current_phase', 0)
            # Phase IDs can be int (0), or str like "1-discovery" — extract leading number
            try:
                current_phase = int(str(raw_phase).split('-')[0])
            except (ValueError, IndexError):
                current_phase = 0
            phase_0_status = state_data.get('phases', {}).get('0', {}).get('status', 'unknown')

            if phase_0_status == "completed" or current_phase >= 1:
                print("  ✓ Pipeline state: Phase 0 complete")
            else:
                print("  ! Pipeline state shows Phase 0 incomplete")
                issues.append("Phase 0 not marked complete in pipeline state")
        except (json.JSONDecodeError, OSError):
            print("  ! pipeline-state.json not found (will create)")
    else:
        print("  ! pipeline-state.json not found (will create)")

    # ═══════════════════════════════════════════════════════════════
    # VALIDATION RESULT
    # ═══════════════════════════════════════════════════════════════

    print()

    if not validation_passed:
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║ VALIDATION FAILED                                         ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print()
        for issue in issues:
            print(f"  • {issue}")
        print()
        error("Cannot proceed - complete Phase 0 first")
        return False

    if issues:
        print("  Warnings:")
        for issue in issues:
            print(f"  • {issue}")
        print()

    # ═══════════════════════════════════════════════════════════════
    # WELCOME MESSAGE
    # ═══════════════════════════════════════════════════════════════

    print()
    print("  Welcome. This is where your project takes shape.")
    print("  We'll explore your vision, gather context, and")
    print("  assemble the right team of agents for the journey.")
    print()

    # Initialize phase output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # ═══════════════════════════════════════════════════════════════
    # CORPUS ANALYSIS
    # ═══════════════════════════════════════════════════════════════

    reference_dir = project_root / "docs" / "reference"
    materials = _load_curated_materials(setup_dir)
    if materials is None:
        # Fallback for old manifests without reference_materials key
        materials = _collect_reference_materials(reference_dir)

    if not materials:
        print("  No reference materials found in docs/reference/")
        print("  (Materials can be added during Task 005 in Phase 0)")
        print()
        if mem:
            mem.finding("Phase 0 validation: all checks passed")
            mem.finding("Corpus: no reference materials found (greenfield project)")
        success("Entry validation passed")
        return True

    print(f"  Found {len(materials)} reference materials for analysis")
    print()

    corpus_data = {
        "materials": [{"path": str(p), "name": p.name, "type": "file"} for p in materials],
        "analyzed_at": datetime.now().isoformat(),
    }

    # LLM Analysis
    analysis_file = output_dir / "corpus-analysis.md"
    prompts_dir = output_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    _analyze_corpus(materials, analysis_file, prompts_dir, setup_dir, uat_mode)

    # Conversational reflection
    if not uat_mode and analysis_file.exists():
        _corpus_reflection(analysis_file, corpus_data)

    # Save corpus data
    _save_corpus(output_dir / "corpus.json", corpus_data, analysis_file)

    # Write to knowledge graph
    if graph:
        for material in corpus_data.get("materials", []):
            graph.add_source(
                id=f"S-101-{material.get('name', 'unknown')[:50]}",
                type="corpus",
                title=material.get("name", "unknown"),
                file_path=material.get("path", ""),
                content_hash=str(hash(material.get("content", "")))[:16],
            )

    # Record substantive memory
    if mem:
        mem.finding("Phase 0 validation: all checks passed")
        mem.finding(f"Corpus: {len(materials)} materials collected")
        if analysis_file.exists():
            try:
                analysis_text = analysis_file.read_text()[:500]
                mem.conversation(f"Corpus analysis summary: {analysis_text.splitlines()[0] if analysis_text else 'N/A'}")
            except Exception as e:
                logger.debug("Failed to read corpus analysis for memory: %s", e)
        feedback = corpus_data.get("human_feedback", "")
        if feedback:
            mem.conversation(f"Human feedback: {feedback}")

    success("Entry validation passed")
    return True


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _find_closeout(atomic_root: Path, phase_id: str) -> Optional[Path]:
    """Find phase closeout file."""
    project_root = atomic_root.parent
    closeout_dir = project_root / ".claude" / "closeout"

    # Try multiple naming patterns
    patterns = [
        f"phase-{phase_id}-closeout.md",
        f"phase-{phase_id}-closeout.json",
        f"{phase_id}-closeout.md",
        "closeout.json",  # Simple pattern used by Phase 0
        "closeout.md",
    ]

    for pattern in patterns:
        closeout_file = closeout_dir / pattern
        if closeout_file.exists():
            return closeout_file

    # Try outputs directory
    outputs_dir = atomic_root.parent / ".outputs" / phase_id
    for pattern in patterns:
        closeout_file = outputs_dir / pattern
        if closeout_file.exists():
            return closeout_file

    return None


def _flatten_config(config_file: Path, config_data: Dict[str, Any]) -> None:
    """Flatten extracted config data into main config."""
    extracted = config_data.get('extracted', {})

    # Flatten extracted fields
    for key in ['project', 'repository', 'sandbox', 'mcp', 'pipeline', 'agents', 'llm']:
        if key in extracted and extracted[key]:
            config_data[key] = extracted[key]

    # Mark as approved
    config_data['config_approved'] = True
    config_data['approved_at'] = datetime.now().isoformat()

    # Save flattened config
    write_json(config_file, config_data)


def _load_curated_materials(setup_dir: Path) -> Optional[List[Path]]:
    """Load pre-curated reference materials from the Phase 0 manifest.

    Returns a list of Path objects for files that still exist on disk,
    or None if the manifest lacks a 'reference_materials' key (backward
    compat with older manifests).
    """
    manifest_file = setup_dir / "material-manifest.json"
    if not manifest_file.exists():
        return None

    try:
        with open(manifest_file) as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    ref_list = manifest.get('reference_materials')
    if ref_list is None:
        return None

    # Validate each path still exists
    materials = []
    for path_str in ref_list:
        p = Path(path_str)
        if p.is_file():
            materials.append(p)

    return materials


# ---------------------------------------------------------------------------
# Corpus analysis (merged from former Task 102)
# ---------------------------------------------------------------------------

def _collect_reference_materials(reference_dir: Path) -> List[Path]:
    """Collect materials from docs/reference/ (populated by Task 005).

    Skips:
      - macOS resource fork files (._*)
      - Directories that are clearly full source repos (node_modules, .git, etc.)
      - Symlinks to directories (avoids pulling in entire trees)
    """
    if not reference_dir.exists():
        return []

    # Directories to skip when encountered during traversal
    _skip_dirs = {
        'node_modules', '.git', '__pycache__', 'dist', 'build',
        '.venv', 'venv', '.tox', '.mypy_cache', '.pytest_cache',
    }

    materials = []
    for f in sorted(reference_dir.rglob("*")):
        # Skip macOS resource fork files
        if f.name.startswith('._'):
            continue
        # Skip files inside excluded directory trees
        if any(part in _skip_dirs for part in f.parts):
            continue
        # Skip symlinks that point to directories (avoids pulling in entire trees)
        if f.is_symlink() and f.resolve().is_dir():
            continue
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
            materials.append(f)

    return materials


def _analyze_corpus(
    materials: List[Path],
    analysis_file: Path,
    prompts_dir: Path,
    setup_dir: Path,
    uat_mode: bool = False,
) -> None:
    """Analyze reference materials using LLM."""
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ CORPUS ANALYSIS                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    print(f"  Corpus size: {len(materials)} materials")
    print()

    # Determine context budget and model from resolver
    try:
        from core.llm.resolver import resolve_model
        rm = resolve_model(phase_id="1-discovery", task_id="101")
        context_tokens = rm.context_window or 200_000
        corpus_model = rm.tier  # Use the resolved tier for the invoke call
    except Exception as e:
        logger.debug("Model resolution failed, using defaults: %s", e)
        context_tokens = 200_000
        corpus_model = "sonnet"
    # Use 50% of context for corpus (~4 chars/token).
    # 50% leaves room for the prompt template, Claude Code system prompt,
    # and the model's response.
    max_chars = int(context_tokens * 0.5 * 4)

    # --- Pass 1: measure file sizes ---
    file_sizes = []  # [(path, char_count), ...]
    for path in materials:
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size  # bytes ≈ chars for text
            file_sizes.append((path, size))
        except OSError:
            continue

    total_chars = sum(s for _, s in file_sizes)

    if total_chars > max_chars:
        budget_k = max_chars // 1000
        total_k = total_chars // 1000
        print(f"  Total corpus: ~{total_k:,}K chars  |  Context budget: ~{budget_k:,}K chars")
        print(f"  (Large files will be truncated to fit)")
        print()

    # --- Pass 2: build corpus content ---
    corpus_content = ""
    chars_used = 0
    files_read = 0
    files_truncated = 0
    files_skipped = 0

    for path, _ in file_sizes:
        if chars_used >= max_chars:
            files_skipped += 1
            continue

        try:
            text = path.read_text(errors='ignore')
            header = f"\n=== FILE: {path.name} ===\n"
            remaining = max_chars - chars_used - len(header) - 1

            if remaining <= 0:
                files_skipped += 1
                continue

            if len(text) > remaining:
                orig_len = len(text)
                text = text[:remaining]
                files_truncated += 1
                header = f"\n=== FILE: {path.name} [TRUNCATED: {remaining:,} of {orig_len:,} chars] ===\n"

            corpus_content += header + text + "\n"
            chars_used += len(header) + len(text) + 1
            files_read += 1

        except Exception as e:
            logger.debug("Failed to read corpus file %s: %s", path.name, e)
            continue

    if files_truncated > 0:
        print(f"  Note: {files_truncated} file(s) truncated to fit context budget")
        print()
    if files_skipped > 0:
        print(f"  Note: {files_skipped} file(s) skipped (context budget full)")
        print()

    if files_read == 0:
        print("  No readable files found - skipping LLM analysis")
        return

    # Extract project context
    project_context = _load_project_context(setup_dir)

    # Create analysis prompt
    prompt = f"""# Task: Analyze Project Corpus

You are a **technical analyst** specializing in software project discovery. Your role is to synthesize scattered documentation into a coherent understanding that will guide the PRD authoring phase.

**IMPORTANT:** Analyze these materials in the context of the project described below. These are the project's own documents, NOT the framework/tool that orchestrates development.

## Token Budget

This analysis should be concise (500-800 words). Focus on actionable insights, not exhaustive summaries.

{project_context}

## Materials Collected

**Note:** Large files may be truncated (marked with [TRUNCATED]). Analyze what's provided and note if critical information might be missing from truncated sections.

{corpus_content}

## Your Task

Provide a concise analysis:

1. **Project Understanding** (2-3 sentences)
   - What is this project about?
   - What problem does it solve?

2. **Key Themes** (3-5 bullets)
   - Main concepts and themes found

3. **Technical Indicators**
   - Technologies mentioned
   - Architecture patterns detected
   - Constraints identified

4. **Gaps & Questions** (3-5 bullets)
   - What's unclear or missing?
   - What should we ask the human?

5. **Recommended Focus Areas**
   - Where should discovery focus?

Be specific to THIS project. Output as markdown.
"""

    prompt_file = prompts_dir / "corpus-analysis.md"
    write_file(prompt_file, prompt)

    print("  Claude is analyzing corpus...")

    try:
        result = invoke(
            prompt_file=prompt_file,
            output_file=analysis_file,
            description="Corpus analysis",
            model=corpus_model,
        )

        if result:
            success("Corpus analyzed")
        else:
            warning("Corpus analysis failed - continuing")
            # Remove stale analysis file so reflection doesn't show old data
            if analysis_file.exists():
                analysis_file.unlink()
    except Exception as e:
        warning(f"Corpus analysis failed: {e}")
        # Remove stale analysis file so reflection doesn't show old data
        if analysis_file.exists():
            analysis_file.unlink()


def _load_project_context(setup_dir: Path) -> str:
    """Load project context from setup config."""
    config_file = setup_dir / "project-config.json"

    if not config_file.exists():
        return ""

    try:
        with open(config_file) as f:
            config_data = json.load(f)

        p_name = (
            config_data.get('project', {}).get('name')
            or config_data.get('extracted', {}).get('project', {}).get('name', 'Unknown')
        )
        p_desc = (
            config_data.get('project', {}).get('description')
            or config_data.get('extracted', {}).get('project', {}).get('description', '')
        )

        return f"## Project Context (from setup configuration)\n\n**Project Name:** {p_name}\n**Description:** {p_desc}\n\n---\n"

    except Exception as e:
        logger.debug("Failed to load project context: %s", e)
        return ""


def _corpus_reflection(analysis_file: Path, corpus_data: Dict[str, Any]) -> None:
    """Conversational reflection to confirm corpus understanding."""
    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ REFLECTION                                                ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Show analysis preview
    print("  From the corpus analysis:")
    print()
    with open(analysis_file) as f:
        for i, line in enumerate(f):
            if i >= 40:
                break
            print(f"  │ {line.rstrip()}")
    print()

    print("  Let's make sure I understand your project correctly.")
    print()

    reflection_turns = 0

    while True:
        if reflection_turns == 0:
            print("  Does this analysis capture your project accurately?")
            print("  Share any corrections, clarifications, or missing context.")
            print("  (Type 'yes' or press Enter if accurate, or provide feedback)")
        else:
            print("  Anything else to add or clarify? (Enter to continue)")
        print()

        human_feedback = input("  > ").strip()

        if not human_feedback or human_feedback.lower() in ('yes', 'correct', 'accurate', 'good', 'ok', 'y'):
            print()
            print("  ✓ Understanding confirmed")
            break

        # Store feedback
        if "human_feedback" not in corpus_data:
            corpus_data["human_feedback"] = ""
        corpus_data["human_feedback"] += "\n" + human_feedback
        corpus_data["human_feedback"] = corpus_data["human_feedback"].lstrip("\n")
        print()
        print("  ✓ Feedback noted")
        print()
        reflection_turns += 1

        if reflection_turns >= 3:
            print("  (We've captured several pieces of feedback. Enter to proceed, or continue adding.)")

    print()


def _save_corpus(corpus_json: Path, corpus_data: Dict[str, Any], analysis_file: Path = None) -> None:
    """Save corpus JSON and summary."""
    # Save JSON
    write_json(corpus_json, corpus_data)
    print(f"  ✓ Saved corpus.json")

    # Generate index alongside corpus.json
    index_file = corpus_json.parent / "CORPUS-INDEX.md"
    index_parts = []
    index_parts.append("# Corpus Index\n\n")
    index_parts.append(f"Generated: {datetime.now().isoformat()}\n\n")
    index_parts.append("## Materials\n\n")

    for material in corpus_data.get("materials", []):
        name = material.get("name", "unknown")
        index_parts.append(f"- **{name}**\n")

    # Analysis summary
    if analysis_file and analysis_file.exists():
        index_parts.append("\n## Analysis Summary\n\n")
        try:
            with open(analysis_file) as af:
                for i, line in enumerate(af):
                    if i >= 30:
                        break
                    index_parts.append(line)
        except OSError as e:
            logger.debug("Failed to read analysis file for index: %s", e)

    # Human feedback
    if corpus_data.get("human_feedback"):
        index_parts.append("\n## Human Feedback\n\n")
        index_parts.append(corpus_data["human_feedback"])
        index_parts.append("\n")

    write_file(index_file, "".join(index_parts))

    print(f"  ✓ Generated CORPUS-INDEX.md")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 101: Entry Validation & Corpus Analysis")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd(),
                       help='Path to atomic-claude root directory')
    parser.add_argument('--output-dir', type=Path, required=True,
                       help='Path to phase output directory')
    parser.add_argument('--uat-mode', action='store_true',
                       help='Run in UAT mode (bypass some checks)')

    args = parser.parse_args()

    success = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success else 1)
