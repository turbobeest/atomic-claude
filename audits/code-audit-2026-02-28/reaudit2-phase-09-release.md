# Re-Audit 2: Phase 09 -- Release

**Date:** 2026-02-28
**Auditor:** Claude Opus 4.6
**Scope:** 7 files (orchestrator + 6 task modules)
**Methodology:** Full read of each file, analysis against audit categories A-R. STRICT severity criteria applied: only CRITICAL, HIGH, and MEDIUM findings reported. Every finding includes a specific, reproducible trigger scenario. Previous audit findings that remain unfixed are included; fixed issues are not re-reported.

---

## Files Audited

1. `phases/phase09/orchestrator09.py`
2. `phases/phase_09_release/tasks/task_901_entry_initialization.py`
3. `phases/phase_09_release/tasks/task_902_release_setup.py`
4. `phases/phase_09_release/tasks/task_903_agent_selection.py`
5. `phases/phase_09_release/tasks/task_904_release_execution.py`
6. `phases/phase_09_release/tasks/task_905_release_confirmation.py`
7. `phases/phase_09_release/tasks/task_906_closeout.py`

---

## Correction of Previous Re-Audit Findings

The previous re-audit (reaudit-phase-09-release.md) reported two MEDIUM findings stating that task_905 and task_906 "unconditionally report Distribution artifacts ready as PASS without checking if dist/ directory exists." This is incorrect based on the current code:

- **task_905 line 129**: `dist_ready = project_root is not None and (project_root / "dist").exists()` -- performs a filesystem check and sets `all_criteria_met = False` when `dist/` is absent (lines 133-134).
- **task_906 lines 166-173**: `dist_dir = release_dir.parent.parent / "dist"` followed by `if dist_dir.exists():` -- also performs a filesystem check and sets `all_passed = False` when `dist/` is absent.

Both tasks DO validate `dist/` existence before reporting status. Those two findings are retracted. However, a related but distinct issue exists: the path used for the `dist/` check differs between task_901 and tasks 905/906 (see Finding 1 below).

---

## Findings

### Finding 1: Inconsistent `dist/` directory path between entry validation and confirmation/closeout

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Category** | L -- Data Integrity / M -- Consistency |
| **Files** | `task_901_entry_initialization.py` (line 103), `task_905_release_confirmation.py` (line 129), `task_906_closeout.py` (line 166) |

**Description:** Task 901 checks for the distribution directory at `atomic_root / "dist"` (inside the framework directory), while tasks 905 and 906 check at `project_root / "dist"` (i.e., `atomic_root.parent / "dist"`, inside the target project directory). These are two different filesystem locations. The target project's `dist/` directory is logically located at `project_root`, not inside the atomic-claude framework itself, making the task_901 check point at the wrong path.

**Specific lines:**
- task_901 line 103: `dist_dir = atomic_root / "dist"` -- checks framework-internal path
- task_905 line 129: `(project_root / "dist").exists()` -- checks project path (`atomic_root.parent / "dist"`)
- task_906 line 166: `dist_dir = release_dir.parent.parent / "dist"` -- resolves to `project_root / "dist"`

**Trigger scenario:** Run Phase 9 on any project where `dist/` was created by Phase 8 at the standard project root location (`project_root/dist/`). During task_901 entry validation, the `dist/` advisory check reports "dist/ directory not found" (yellow warning) because it looks inside `atomic_root/dist/` where the directory does not exist. Later, tasks 905 and 906 correctly find `dist/` at `project_root/dist/` and report it as present. The user sees contradictory information: task_901 says dist is missing, but tasks 905/906 say it is present. Conversely, if `dist/` were somehow placed inside `atomic_root/`, task_901 would find it but tasks 905/906 would not, causing the confirmation gate and closeout to report distribution artifacts as missing and blocking progression.

**Impact:** Wrong results displayed to the user during normal operation. In the second scenario (unlikely but possible), the confirmation gate incorrectly blocks release completion.

**Recommendation:** Standardize the `dist/` check path across all three tasks. The correct location is `project_root / "dist"` (consistent with tasks 905/906 and with standard Python packaging conventions). Change task_901 line 103 from `atomic_root / "dist"` to `project_root / "dist"`.

---

### Finding 2: Custom agent name unsanitized, flows into filesystem path construction

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Category** | E -- Input Validation / H -- Security |
| **Files** | `task_903_agent_selection.py` (line 130-132), `task_904_release_execution.py` (lines 40-42, 48) |

**Description:** When a user selects the "custom" agent option in task_903, the agent name is read from `input()` without any validation or sanitization (line 130). This name is written to `release-agents.json` and subsequently used in task_904's `find_agent_prompt()` function as a path component: `agent_repo / "expert-agents" / f"{agent_name}.md"` (lines 40-42). Path traversal characters (`..`, `/`) in the agent name cause the constructed path to resolve outside the intended agent repository directory.

**Specific lines:**
- task_903 line 130: `custom_name = input("  Custom agent name: ").strip()` -- no validation
- task_903 line 132: `selected_agents.append(f"{custom_name}:{custom_model}")` -- stored as-is
- task_904 lines 40-42: `agent_repo / "expert-agents" / f"{agent_name}.md"` -- path traversal possible

**Trigger scenario:** User runs Phase 9 interactively, selects option `[c]` for custom agent, and enters `../../etc/hostname` as the agent name. In task_904, `find_agent_prompt` constructs `agent_repo / "expert-agents" / "../../etc/hostname.md"`, which Python's `Path` resolves to `agent_repo_parent / "etc/hostname.md"`. If this file exists, its content is read and injected as an LLM prompt prefix. While the `.md` extension limits exposure and the read content goes into an LLM prompt rather than being executed, it enables reading arbitrary `.md` files from the filesystem and leaking their contents into the LLM call.

**Recommendation:** Sanitize the custom agent name in task_903 to reject or strip path separator characters, `..` sequences, and non-alphanumeric characters other than hyphens. A minimal fix: `custom_name = re.sub(r'[^a-zA-Z0-9_-]', '', custom_name)` before appending to the agents list.

---

### Finding 3: Empty custom agent name accepted, produces malformed agent entry

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Category** | E -- Input Validation |
| **Files** | `task_903_agent_selection.py` (lines 130-132) |

**Description:** When the user selects the custom agent option and presses Enter without typing a name, `custom_name` becomes an empty string after `.strip()`. This produces a malformed agent entry `":haiku"` (empty name, colon, model) that is written to `release-agents.json`. In task_904, this empty name is passed to `find_agent_prompt("")`, which constructs paths like `agent_repo / "expert-agents" / ".md"` -- a file that would not normally exist. The subsequent agent-matching check on line 156 (`if "announcement" in agent_name.lower() or "writer" in agent_name.lower()`) fails because the name is empty, so the agent prompt is silently discarded.

**Specific lines:**
- task_903 line 130: `custom_name = input("  Custom agent name: ").strip()` -- allows empty string
- task_903 line 132: `selected_agents.append(f"{custom_name}:{custom_model}")` -- stores `":haiku"`
- task_904 line 156: `if "announcement" in agent_name.lower()` -- never matches empty string

**Trigger scenario:** User selects custom agent and presses Enter without typing a name. The `release-agents.json` artifact records `":haiku"` as a selected agent. In task_904, the empty agent name fails to match any agent file and fails the `"announcement" in agent_name` check, so no agent prompt is loaded. The system falls through to the built-in prompt without any indication that the user's custom agent selection was silently discarded.

**Impact:** The user's explicit choice to use a custom agent is silently ignored with no error or warning. The release proceeds with a built-in prompt instead of the intended custom agent, producing different output than the user expected.

**Recommendation:** Validate that `custom_name` is non-empty after stripping. If empty, either re-prompt or fall back to the default agent with a warning message.

---

## Per-File Summary

### phases/phase09/orchestrator09.py

No actionable findings. Wrapper functions correctly pass `(ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, mem=mem)` to the underlying task `execute` functions, matching their signatures. The `run_phase` delegation to `run_phase_tasks` is correct.

### phases/phase_09_release/tasks/task_901_entry_initialization.py

**Finding 1 (partial)**: The `dist/` directory check on line 103 uses `atomic_root / "dist"` instead of `project_root / "dist"`, inconsistent with the path used in tasks 905 and 906. See Finding 1 above.

### phases/phase_09_release/tasks/task_902_release_setup.py

No actionable findings meeting MEDIUM or higher severity threshold. The `notes_confirm not in ["y", "Y"]` check on line 210 contains dead code (the `"Y"` branch is unreachable because input was already lowercased on line 204), but this does not cause incorrect behavior -- the logic still works correctly because lowercase `"y"` is checked first.

### phases/phase_09_release/tasks/task_903_agent_selection.py

**Finding 2**: Custom agent name is unsanitized, enabling path traversal in task_904's `find_agent_prompt()`.
**Finding 3**: Empty custom agent name is accepted, producing a malformed agent entry that is silently discarded in task_904.

### phases/phase_09_release/tasks/task_904_release_execution.py

**Finding 2 (partial)**: The `find_agent_prompt` function uses unsanitized agent names in path construction (lines 40-42). See Finding 2 above.

No other actionable findings. The LLM retry loop with fallback template, version sanitization, and frontmatter stripping logic are all sound.

### phases/phase_09_release/tasks/task_905_release_confirmation.py

**Finding 1 (partial)**: Uses `project_root / "dist"` for the dist check, which is correct but inconsistent with task_901. See Finding 1 above.

No other actionable findings. The confirmation loop correctly uses `while True` with `continue`/`break` instead of recursion. The dist check does perform proper filesystem validation.

### phases/phase_09_release/tasks/task_906_closeout.py

**Finding 1 (partial)**: Uses `release_dir.parent.parent / "dist"` (resolves to `project_root / "dist"`) for the dist check, which is correct but inconsistent with task_901. See Finding 1 above.

No other actionable findings. The checklist item parsing via `split(':', 1)` is fragile but none of the current checklist item names contain colons, so no incorrect behavior occurs in practice.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |

**Total actionable findings: 3**

- **1 HIGH**: Inconsistent `dist/` directory path between task_901 (`atomic_root/dist`) and tasks 905/906 (`project_root/dist`), causing contradictory information shown to the user during normal operation.
- **2 MEDIUM**: Unsanitized custom agent name input (path traversal in filesystem operations) and acceptance of empty custom agent names (silently discarded with no user feedback).
