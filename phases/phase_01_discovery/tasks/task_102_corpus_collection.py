"""
Task 102: Corpus Collection (Conversation 1)

Collect, analyze, and organize all project materials.

Steps:
  1. Scan directory for existing materials
  2. Request additional materials from human
  3. Analyze corpus (LLM)
  4. Conversational reflection with human
  5. Organize into docs/corpus/CORPUS-INDEX.md

Supported: .md, .txt, .rst, .pdf, .json, .yaml, .dot, .svg
"""

import json
import sys
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Set, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.state import StateManager
from core.llm import invoke_llm as invoke
from core.ui import phase_header, success, error, warning, info, step


# Deduplication tracking
SEEN_PATHS: Set[Path] = set()

# Supported file extensions
SUPPORTED_EXTS = {'.md', '.txt', '.rst', '.pdf', '.json', '.yaml', '.yml', '.dot', '.svg'}


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False) -> bool:
    """
    Execute Task 102: Corpus Collection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, skip interactive conversation

    Returns:
        True if collection completed successfully, False otherwise
    """
    global SEEN_PATHS
    SEEN_PATHS.clear()

    project_root = atomic_root.parent  # Project lives one level above the tool directory
    corpus_dir = project_root / "docs" / "corpus"
    corpus_index = corpus_dir / "CORPUS-INDEX.md"
    corpus_json = output_dir / "corpus.json"
    prompts_dir = output_dir / "prompts"

    step("Corpus Collection")

    corpus_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # UAT Mode: Skip interactive collection
    if uat_mode:
        print()
        print("  ⚡ UAT Mode: Using minimal corpus")
        print()

        corpus_data = {
            "materials": [
                {"path": str(atomic_root / "README.md"), "name": "README.md", "type": "file", "source": "uat"}
            ],
            "links": [],
            "scanned_at": datetime.now().isoformat()
        }

        _save_corpus(corpus_json, corpus_index, corpus_data, [])
        success("Corpus collection complete (UAT mode)")
        return True

    print()
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ CONVERSATION 1: CORPUS COLLECTION                       │")
    print("  │                                                         │")
    print("  │ Let's gather all materials relevant to your project:   │")
    print("  │ documents, specs, PRDs, links, references, prior work. │")
    print("  │                                                         │")
    print("  │ Supported: .md .txt .rst .pdf .json .yaml .dot .svg    │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()

    # Initialize corpus tracking
    corpus_data = {
        "materials": [],
        "links": [],
        "scanned_at": datetime.now().isoformat()
    }

    # ═══════════════════════════════════════════════════════════════
    # STEP 1: SCAN DIRECTORY
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ STEP 1: SCANNING FOR EXISTING MATERIALS                   ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    print("  Scanning for documents...")

    found_count = _auto_discover_materials(project_root, atomic_root)

    print()
    print(f"  Auto-discovered {found_count} materials")
    print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 2: REQUEST ADDITIONAL MATERIALS
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ STEP 2: ADDITIONAL MATERIALS                              ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    print("  What other materials should we include?")
    print()
    print("  You can provide:")
    print("    • File paths (relative or absolute)")
    print("    • Directory paths to scan")
    print("    • URLs (stored as references, not fetched)")
    print("    • Supported: .md .txt .rst .pdf .json .yaml .dot .svg")
    print("    • Press Enter when finished")
    print()

    manual_count = _collect_manual_materials(corpus_data, project_root)

    if manual_count > 0:
        print(f"\n  Added {manual_count} materials manually")
    print()

    # Build final materials list
    for path in SEEN_PATHS:
        corpus_data["materials"].append({
            "path": str(path),
            "name": path.name,
            "type": "file",
            "source": "auto"
        })

    # ═══════════════════════════════════════════════════════════════
    # STEP 3: ANALYZE CORPUS (LLM)
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ STEP 3: ANALYZING CORPUS                                  ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    total_materials = len(corpus_data["materials"])
    total_links = len(corpus_data["links"])

    print(f"  Corpus size: {total_materials} materials, {total_links} links")
    print()

    analysis_file = output_dir / "corpus-analysis.md"

    if len(SEEN_PATHS) > 0:
        _analyze_corpus(SEEN_PATHS, analysis_file, prompts_dir, output_dir.parent / "0-setup")
        if analysis_file.exists():
            corpus_data["analysis_file"] = str(analysis_file)

    print()

    # ═══════════════════════════════════════════════════════════════
    # STEP 4: CONVERSATIONAL REFLECTION
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ STEP 4: REFLECTION                                        ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    if analysis_file.exists():
        print("  From the corpus analysis:")
        print()
        with open(analysis_file) as f:
            for i, line in enumerate(f):
                if i >= 40:
                    break
                print(f"  │ {line.rstrip()}")
        print()

    reflection_complete = False
    reflection_turns = 0

    print("  Let's make sure I understand your project correctly.")
    print()

    while not reflection_complete:
        if reflection_turns == 0:
            print("  Does this analysis capture your project accurately?")
            print("  Share any corrections, clarifications, or missing context.")
            print("  (Type 'yes' or press Enter if accurate, or provide feedback)")
        else:
            print("  Anything else to add or clarify? (Enter to continue)")
        print()

        human_feedback = input("  > ").strip()

        if not human_feedback or human_feedback.lower() in ['yes', 'correct', 'accurate', 'good', 'ok', 'y']:
            print()
            print("  ✓ Understanding confirmed")
            reflection_complete = True
        else:
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

    # ═══════════════════════════════════════════════════════════════
    # STEP 5: ORGANIZE CORPUS
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ STEP 5: ORGANIZING CORPUS                                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    copied, skipped = _organize_corpus(SEEN_PATHS, corpus_dir)

    if copied > 0:
        print(f"  ✓ Copied {copied} files to docs/corpus/")
    if skipped > 0:
        print(f"  ○ Skipped {skipped} duplicates")

    # Save corpus
    _save_corpus(corpus_json, corpus_index, corpus_data, analysis_file)

    print()
    print("━" * 60)
    print()
    print("  Corpus Collection Complete")
    print()
    print(f"  Materials: {total_materials}")
    print(f"  Links:     {total_links} (references)")
    print(f"  Location:  docs/corpus/")
    print(f"  Index:     docs/corpus/CORPUS-INDEX.md")
    print()

    success("Corpus collection complete")

    return True


def _auto_discover_materials(project_root: Path, atomic_root: Path) -> int:
    """Auto-discover materials in project directory."""
    found_count = 0

    # Framework directories to exclude
    framework_excludes = {
        'phases', 'lib', 'skills', 'config', 'agents', 'audits', 'tools',
        '.git', '.claude', '.outputs', '.state', '.logs', 'node_modules',
        '__pycache__', '.venv', 'venv'
    }

    # Auto-include initialization/setup.md
    setup_file = atomic_root / "initialization" / "setup.md"
    if setup_file.exists():
        if _add_material(setup_file):
            print(f"    ✓ setup.md (initialization)")
            found_count += 1

    # README files in project root
    for readme in project_root.glob("README*"):
        if readme.is_file() and _should_include(readme, framework_excludes):
            if _add_material(readme):
                rel_path = readme.relative_to(project_root) if readme.is_relative_to(project_root) else readme
                print(f"    ✓ {readme.name} ({rel_path.parent})")
                found_count += 1

    # PRD/spec documents in project root (maxdepth 3)
    for pattern in ['*prd*', '*spec*', '*design*', '*architecture*', '*requirements*']:
        for f in project_root.rglob(pattern):
            if f.is_file() and f.suffix in {'.md', '.txt', '.rst'} and _should_include(f, framework_excludes):
                if _add_material(f):
                    print(f"    ✓ {f.name}")
                    found_count += 1
                if found_count >= 10:
                    break

    # docs/ directory - scan all documentation files
    docs_dir = project_root / "docs"
    if docs_dir.exists():
        docs_added = 0
        for f in docs_dir.rglob("*"):
            if f.is_file() and f.suffix in SUPPORTED_EXTS and _should_include(f, framework_excludes):
                if f.name.startswith("._"):
                    continue
                if _add_material(f):
                    rel_path = f.relative_to(project_root)
                    print(f"    ✓ {f.name} ({rel_path.parent})")
                    found_count += 1
                    docs_added += 1

        if docs_added > 0:
            print(f"    ({docs_added} files from docs/)")

    return found_count


def _should_include(path: Path, excludes: Set[str]) -> bool:
    """Check if path should be included (not in exclusion list)."""
    for exclude in excludes:
        if exclude in path.parts:
            return False
    return True


def _add_material(path: Path) -> bool:
    """Add material to tracking set. Returns True if new, False if duplicate."""
    global SEEN_PATHS
    abs_path = path.resolve()

    if abs_path in SEEN_PATHS:
        return False

    # Check if supported file type
    if abs_path.suffix.lower() not in SUPPORTED_EXTS:
        return False

    SEEN_PATHS.add(abs_path)
    return True


def _collect_manual_materials(corpus_data: Dict[str, Any], project_root: Path) -> int:
    """Collect additional materials from human input."""
    manual_count = 0

    while True:
        material_input = input("  Add material: ").strip()

        if not material_input or material_input.lower() == "done":
            break

        # URL
        if material_input.startswith("http://") or material_input.startswith("https://"):
            corpus_data["links"].append(material_input)
            print(f"    ✓ Link saved: (reference only) {material_input}")
            manual_count += 1

        # Absolute file path
        elif Path(material_input).is_file():
            if _add_material(Path(material_input)):
                print(f"    ✓ File added: {Path(material_input).name}")
                manual_count += 1
            else:
                print(f"    ○ Already included: {Path(material_input).name}")

        # Relative file path
        elif (project_root / material_input).is_file():
            if _add_material(project_root / material_input):
                print(f"    ✓ File added: {Path(material_input).name}")
                manual_count += 1
            else:
                print(f"    ○ Already included: {Path(material_input).name}")

        # Directory
        elif Path(material_input).is_dir() or (project_root / material_input).is_dir():
            dir_path = Path(material_input) if Path(material_input).is_dir() else project_root / material_input
            dir_files = sum(1 for f in dir_path.rglob("*") if f.is_file() and f.suffix in SUPPORTED_EXTS)
            corpus_data["materials"].append({
                "path": str(dir_path),
                "type": "directory",
                "file_count": dir_files
            })
            print(f"    ✓ Directory added: {dir_path} ({dir_files} supported files)")
            manual_count += 1

        # Not found
        else:
            print(f"    ! Not found: {material_input}")
            print("      Store as a reference note? [y/N]")
            store_note = input("      ").strip().lower()
            if store_note == 'y':
                corpus_data["materials"].append({
                    "note": material_input,
                    "type": "reference"
                })
                print("      ✓ Stored as reference")
                manual_count += 1

    return manual_count


def _analyze_corpus(seen_paths: Set[Path], analysis_file: Path, prompts_dir: Path, setup_dir: Path) -> None:
    """Analyze corpus using LLM."""
    # Build corpus content for analysis
    corpus_content = ""
    files_read = 0
    files_truncated = 0
    max_lines = 300
    max_files = 10

    for path in list(seen_paths)[:max_files]:
        if not path.is_file():
            continue

        try:
            line_count = sum(1 for _ in open(path, errors='ignore'))
            truncated_note = ""

            if line_count > max_lines:
                truncated_note = f" [TRUNCATED: showing first {max_lines} of {line_count} lines]"
                files_truncated += 1

            with open(path, errors='ignore') as f:
                lines = [next(f, '') for _ in range(max_lines)]

            corpus_content += f"\n=== FILE: {path.name}{truncated_note} ===\n"
            corpus_content += ''.join(lines)
            corpus_content += "\n"
            files_read += 1

        except Exception:
            continue

    if files_truncated > 0:
        print(f"  Note: {files_truncated} large files were truncated for analysis")
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
    with open(prompt_file, 'w') as f:
        f.write(prompt)

    print("  Claude is analyzing corpus...")

    try:
        result = invoke(
            prompt_file=prompt_file,
            output_file=analysis_file,
            description="Corpus analysis",
            model="sonnet"
        )

        if result:
            success("Corpus analyzed")
        else:
            warning("Corpus analysis failed - continuing")
    except Exception as e:
        warning(f"Corpus analysis failed: {e}")


def _load_project_context(setup_dir: Path) -> str:
    """Load project context from setup config."""
    config_file = setup_dir / "project-config.json"

    if not config_file.exists():
        return ""

    try:
        with open(config_file) as f:
            config_data = json.load(f)

        p_name = config_data.get('project', {}).get('name') or config_data.get('extracted', {}).get('project', {}).get('name', 'Unknown')
        p_desc = config_data.get('project', {}).get('description') or config_data.get('extracted', {}).get('project', {}).get('description', '')

        context = f"## Project Context (from setup configuration)\n\n**Project Name:** {p_name}\n**Description:** {p_desc}\n\n---\n"
        return context

    except Exception:
        return ""


def _organize_corpus(seen_paths: Set[Path], corpus_dir: Path) -> tuple:
    """Copy materials to corpus directory."""
    copied = 0
    skipped = 0

    for path in seen_paths:
        if not path.is_file():
            continue

        dest = corpus_dir / path.name

        # Handle name collisions
        if dest.exists():
            # Check if same file
            if path.read_bytes() == dest.read_bytes():
                skipped += 1
                continue

            # Different file, add suffix
            counter = 1
            stem = path.stem
            suffix = path.suffix
            while (corpus_dir / f"{stem}_{counter}{suffix}").exists():
                counter += 1
            dest = corpus_dir / f"{stem}_{counter}{suffix}"

        try:
            shutil.copy2(path, dest)
            copied += 1
        except Exception:
            pass

    return copied, skipped


def _save_corpus(corpus_json: Path, corpus_index: Path, corpus_data: Dict[str, Any], analysis_file: Path = None) -> None:
    """Save corpus JSON and index."""
    # Save JSON
    with open(corpus_json, 'w') as f:
        json.dump(corpus_data, f, indent=2)
    print(f"  ✓ Saved corpus.json")

    # Generate index
    with open(corpus_index, 'w') as f:
        f.write("# Corpus Index\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write("## Materials\n\n")

        for material in corpus_data.get("materials", []):
            name = material.get("name", material.get("path", material.get("note", "unknown")))
            mat_type = material.get("type", "unknown")
            source = material.get("source", "")
            source_note = " [auto-discovered]" if source == "auto" else ""
            f.write(f"- **{name}** ({mat_type}){source_note}\n")

        # Links
        if corpus_data.get("links"):
            f.write("\n## External Links (References)\n\n")
            f.write("*These URLs are stored for reference but were not fetched during analysis.*\n\n")
            for link in corpus_data["links"]:
                f.write(f"- {link}\n")

        # Analysis summary
        if analysis_file and analysis_file.exists():
            f.write("\n## Analysis Summary\n\n")
            with open(analysis_file) as af:
                for i, line in enumerate(af):
                    if i >= 30:
                        break
                    f.write(line)

        # Human feedback
        if corpus_data.get("human_feedback"):
            f.write("\n## Human Feedback\n\n")
            f.write(corpus_data["human_feedback"])
            f.write("\n")

    print(f"  ✓ Generated CORPUS-INDEX.md")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task 102: Corpus Collection")
    parser.add_argument('--atomic-root', type=Path, default=Path.cwd())
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--uat-mode', action='store_true')

    args = parser.parse_args()

    success_result = execute(args.atomic_root, args.output_dir, args.uat_mode)
    sys.exit(0 if success_result else 1)
