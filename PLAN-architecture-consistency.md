# Plan: Architectural Consistency — Phase 3→4→5 Pipeline Fix

## Context

Phase 5 TDD execution on PRD-403 (Rust project, 118 tasks) produces 70%+ failure rate despite the TDD engine working correctly. Root cause: **tasks and specs have inconsistent project layout assumptions**.

The PRD (Section 7) defines a precise Cargo workspace with 7 crates (`foo-core`, `foo-ffi`, etc.) under `crates/`. But this architecture is never propagated:

- **Phase 3** decomposes per-feature independently → each feature generates its own scaffold "Task 1" → 12 features produce conflicting bootstrap tasks (IDs 1, 44, 93, 106)
- **Phase 3** extracts Sections 2.1, 3, 4, 5, 6 from PRD but **skips Section 7 (Code Structure)** entirely
- **Phase 4** spec generation loads full PRD but doesn't call out the canonical layout → specs reference inconsistent paths (`src/spatial_index/mod.rs` vs `crates/foo-core/src/spatial_index/mod.rs`)
- **Phase 5** library/feature tasks write implementation to isolated task dirs (`.claude/testing/task-N/`) instead of the real project tree → downstream tasks can't import

## Files to Modify

| File | Scope | Changes |
|------|-------|---------|
| `phases/phase_03_tasking/tasks/task_303_task_decomposition.py` | Medium | Extract Section 7, inject architecture into per-feature prompts, deduplicate bootstrap tasks in merge |
| `phases/phase_04_specification/tasks/task_403_openspec_generation.py` | Small | Extract canonical layout from PRD, inject into spec generation prompt |
| `phases/phase_05_implementation/tasks/task_504_tdd_execution.py` | Medium | Library/feature tasks use multi-file output and write to project tree instead of task dirs |

Copy all changed files to PRD-403 operational test after.

---

## Part 1: Phase 3 — Task Decomposition Fix (`task_303`)

### 1A. Extract Section 7 from PRD

In `_extract_prd_sections()` (line ~307), add extraction for Section 7:

```python
# Extract Section 7: Code Structure / Code Organization
match = re.search(r'^#{1,2} 7\. Code (Structure|Organization)(.+?)^#{1,2} 8\.', content, re.MULTILINE | re.DOTALL)
if match:
    sections["code_structure"] = match.group(2).strip()
```

### 1B. Inject Architecture into Per-Feature Prompt

In `_build_decomposition_prompt()` (line ~444), add the architecture constraint section for per-feature mode. This goes BEFORE the feature content and AFTER the Task Generation Rules:

```python
# After the Decomposition Checklist, before PRD Sections:
if "code_structure" in sections:
    prompt += """## Canonical Project Layout (from PRD Section 7)

IMPORTANT: This is the AUTHORITATIVE project structure. ALL tasks you generate MUST reference
paths within this layout. Do NOT generate scaffold, bootstrap, or project-setup tasks —
a single foundation task (Task ID 1) already handles all project scaffolding.

Your tasks should ASSUME this structure exists and specify which module/crate they modify.

"""
    # Include first ~4000 chars of Section 7 (the directory tree + crate architecture)
    code_struct = sections["code_structure"]
    if len(code_struct) > 4000:
        code_struct = code_struct[:4000] + "\n\n... (truncated)"
    prompt += code_struct + "\n\n"
```

Key instruction: "Do NOT generate scaffold/bootstrap tasks" — this prevents each feature from creating its own competing Task 1.

### 1C. Deduplicate Bootstrap Tasks in Merge

In `_merge_feature_tasks()` (line ~379), add a deduplication pass after merging. After the second pass that remaps dependencies:

```python
# Third pass: deduplicate bootstrap/scaffold tasks
# Keep the first one, remove duplicates, remap any deps pointing to removed tasks
bootstrap_keywords = ["scaffold", "project setup", "ci pipeline", "ci foundation",
                      "project layout", "workspace setup", "cargo workspace"]
first_bootstrap_id = None
duplicate_ids = set()

for task in all_tasks:
    title_lower = task.get("title", "").lower()
    category = task.get("category", "").lower()
    is_bootstrap = (
        category == "infrastructure"
        and not task.get("dependencies")
        and any(kw in title_lower for kw in bootstrap_keywords)
    )
    if is_bootstrap:
        if first_bootstrap_id is None:
            first_bootstrap_id = task["id"]
        else:
            duplicate_ids.add(task["id"])

if duplicate_ids:
    # Remove duplicate bootstrap tasks; remap deps pointing to them → first_bootstrap_id
    all_tasks = [t for t in all_tasks if t["id"] not in duplicate_ids]
    for task in all_tasks:
        task["dependencies"] = [
            first_bootstrap_id if d in duplicate_ids else d
            for d in task.get("dependencies", [])
        ]
```

---

## Part 2: Phase 4 — Spec Generation Fix (`task_403`)

### 2A. Extract Canonical Layout and Include in Spec Prompt

In `_load_project_context()` (line ~82), the full PRD is already loaded. But the spec prompt (`_build_spec_prompt()` at line ~149) needs to explicitly call out the project layout.

Add a new helper to extract just the code structure section from the PRD:

```python
def _extract_canonical_layout(project_root: Path) -> str:
    """Extract the canonical project layout (Section 7) from the approved PRD."""
    prd_file = project_root / "docs" / "prd" / "PRD.md"
    if not prd_file.exists():
        # Try prd-approved.json pointer
        approved = project_root / ".outputs" / "2-prd" / "prd-approved.json"
        if approved.exists():
            try:
                data = json.loads(read_file(approved))
                prd_path = data.get("prd_file", "")
                if prd_path:
                    prd_file = Path(prd_path)
            except Exception:
                pass

    if not prd_file.exists():
        return ""

    try:
        content = read_file(prd_file)
        match = re.search(r'^#{1,2} 7\. Code (Structure|Organization)(.+?)^#{1,2} 8\.',
                         content, re.MULTILINE | re.DOTALL)
        if match:
            layout = match.group(2).strip()
            # Truncate if too long (keep directory tree + crate architecture)
            return layout[:5000] if len(layout) > 5000 else layout
    except Exception:
        pass
    return ""
```

Then modify `_build_spec_prompt()` to include it:

```python
def _build_spec_prompt(task: Dict, project_context: str, canonical_layout: str = "") -> str:
    # ... existing prompt ...

    layout_section = ""
    if canonical_layout:
        layout_section = f"""
## Canonical Project Layout

This project uses the following structure (from PRD Section 7).
ALL file paths, module references, and import paths in your spec MUST align with this layout:

{canonical_layout}

"""

    return f"""Generate an OpenSpec specification for the following task.
IMPORTANT: This is for the user's project described below, NOT for the development tool/framework.

## Project Context
{project_context}
{layout_section}
## Task to Specify
...
```

Thread the `canonical_layout` through `_spec_worker()` to each `_build_spec_prompt()` call.

---

## Part 3: Phase 5 — TDD Execution Fix (`task_504`)

### 3A. All Tasks Use Multi-File Output

Currently, only bootstrap tasks use the `=== FILE: path ===` multi-file format. Library/feature tasks generate a single code block written to `task_dir/task_N_impl.rs`.

**Change**: ALL task classifications use multi-file output and write to the project tree. This way the LLM decides file paths based on the PRD architecture, and files land in the right crate/module.

Modify the GREEN phase prompt for library/feature tasks:

```python
# Instead of:
#   "Output ONLY the {language} implementation code. Wrap in ```{fence_lang} fences."
# Use:
"""Output your implementation using this EXACT format:

=== FILE: path/relative/to/project/root ===
[file content]
=== FILE: another/path ===
[content]
=== END ===

Place files in the correct project location based on the canonical layout.
For example, domain types go in crates/foo-core/src/types/mod.rs.
You may create or modify multiple files. Use paths relative to the project root."""
```

Modify the GREEN phase file-writing logic to use `extract_multi_file_response()` for ALL classifications (not just bootstrap):

```python
# After LLM response, for ALL task types:
files = extract_multi_file_response(response)
if files and "__single_block__" not in files:
    # Multi-file output — write to project tree
    written_files = []
    for rel_path, content in files.items():
        abs_path = project_root / rel_path
        ensure_dir(abs_path.parent)
        write_file(abs_path, content)
        written_files.append(rel_path)
        if source_registry:
            source_registry.register(str(task_id), rel_path, content)
    record["impl_file"] = str(project_root)
    record["files_written"] = written_files
else:
    # Fallback: single code block → write to task dir (legacy behavior)
    code = extract_code_from_response(response, fence_lang)
    write_file(impl_file, code)
```

### 3B. Inject Project Tree Manifest After Bootstrap

After the first bootstrap task completes, scan the actual project tree and include it in subsequent prompts:

```python
def _scan_project_tree(project_root: Path, stack: str, max_depth: int = 4) -> str:
    """Scan actual project tree and return a manifest for LLM context."""
    if stack == "rust":
        # List Cargo.toml + all .rs files
        files = sorted(project_root.rglob("*.rs"))
        tomls = sorted(project_root.rglob("Cargo.toml"))
        manifest_lines = [str(f.relative_to(project_root)) for f in tomls + files
                         if "target" not in str(f)]
    elif stack == "python":
        files = sorted(project_root.rglob("*.py"))
        manifest_lines = [str(f.relative_to(project_root)) for f in files
                         if "__pycache__" not in str(f)]
    else:
        return ""

    if len(manifest_lines) > 100:
        manifest_lines = manifest_lines[:100] + [f"... and {len(manifest_lines) - 100} more"]
    return "\n".join(manifest_lines)
```

Add this manifest to the dependency context section in GREEN/RED prompts:

```python
if project_manifest:
    dep_section += f"""
## Actual Project Tree
These files currently exist in the project. Place your code in the correct location:

{project_manifest}
"""
```

### 3C. RED Phase for Library/Feature Also Uses Multi-File

For the RED phase, test files should go to the project's test directory (e.g., `tests/` for Rust, `tests/` for Python) using multi-file format. This ensures `cargo test` can discover them:

```python
# RED prompt for library/feature tasks:
"""Generate test files for this task. Output using this EXACT format:

=== FILE: path/relative/to/project/root ===
[test content]
=== END ===

For Rust, place unit tests in the source file (#[cfg(test)] mod tests)
or integration tests in tests/test_{module}.rs.
"""
```

**Fallback**: If the LLM doesn't produce multi-file output, fall back to writing tests to the task dir (current behavior). This ensures backward compatibility.

---

## Implementation Sequence

| Step | File | What | Depends On |
|------|------|------|------------|
| 1 | task_303 | Add Section 7 extraction to `_extract_prd_sections()` | — |
| 2 | task_303 | Add architecture injection to `_build_decomposition_prompt()` | Step 1 |
| 3 | task_303 | Add bootstrap deduplication to `_merge_feature_tasks()` | — |
| 4 | task_403 | Add `_extract_canonical_layout()` helper | — |
| 5 | task_403 | Modify `_build_spec_prompt()` to include layout | Step 4 |
| 6 | task_504 | Modify GREEN prompt to use multi-file output for all tasks | — |
| 7 | task_504 | Modify GREEN phase file-writing to use multi-file for all tasks | Step 6 |
| 8 | task_504 | Add `_scan_project_tree()` and inject into prompts | — |
| 9 | All | `python -m py_compile` all changed files | Steps 1-8 |
| 10 | All | Copy to PRD-403 | Step 9 |

Steps 1-5 can be done in parallel. Steps 6-8 can be done in parallel. Step 9-10 sequential after all.

## Verification

1. `python -m py_compile` all 3 changed files
2. Copy to PRD-403
3. **Phase 3 re-run**: `python main.py backtrack 3 303` → `python main.py run 3`
   - Verify: Section 7 extracted and included in per-feature prompts
   - Verify: per-feature prompt says "Do NOT generate scaffold/bootstrap tasks"
   - Verify: merged task list has only ONE bootstrap task (not 4+)
4. **Phase 4 re-run**: `python main.py backtrack 4 403` → `python main.py run 4`
   - Verify: spec prompts include canonical layout
   - Verify: generated specs reference consistent paths (`crates/foo-core/...`)
5. **Phase 5 re-run**: `python main.py backtrack 5 502` → `python main.py run 5`
   - Verify: library/feature tasks write to project tree (not task dirs)
   - Verify: subsequent tasks see actual project files in prompts
   - Verify: failure rate drops significantly

## Risk Assessment

- **Phase 3 re-run cost**: ~12 LLM calls (one per feature) at Opus. Moderate token spend (~$10-15) but produces much better task list.
- **Phase 4 re-run cost**: ~118 spec generation calls at Sonnet. Moderate (~$5-10).
- **Phase 5 re-run cost**: 118 TDD cycles. This was already the plan.
- **Backward compatibility**: All changes are additive. If Section 7 is absent, falls back to current behavior. If multi-file parsing fails, falls back to single-file.
