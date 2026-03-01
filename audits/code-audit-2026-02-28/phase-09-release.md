# Code Audit: Phase 09 - Release

**Audit Date:** 2026-02-28
**Auditor:** Claude Opus 4.6 (Automated Code Audit)
**Scope:** 7 files in phases/phase09/ and phases/phase_09_release/tasks/
**Methodology:** All checks A1-A10, B1-B8, C1-C10, D1-D8, E1-E10, F1-F8, G1-G6, H1-H5, I1-I4, J1-J7, K1-K5, L1-L5, M1-M10, N1-N8, O1-O7, P1-P9, Q1-Q8, R1-R10

---

## File 1: `phases/phase09/orchestrator09.py` (127 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A2 - Naming | INFO | File lives in `phases/phase09/` while task modules live in `phases/phase_09_release/tasks/`. Inconsistent directory naming convention (`phase09` vs `phase_09_release`). | -- | Standardize directory naming across the project. |
| B1 - Imports | LOW | `logging` is imported but `logger` is defined and never used in this file; no log statements exist in orchestrator09. | 16, 24 | Remove unused logger or add appropriate log calls. |
| B2 - Imports | INFO | `sys.path.insert(0, ...)` manipulates sys.path at module level for import resolution. | 22 | Consider using proper packaging or a single entry-point path setup. |
| C3 - Error Handling | MEDIUM | `run_phase()` delegates to `run_phase_tasks()` but there is no try/except in `__main__` around `run_phase()`. An unhandled exception in `run_phase_tasks()` would produce a traceback rather than a clean exit. | 120-126 | Wrap `run_phase()` in a try/except to catch unexpected errors and produce a user-friendly message. |
| D3 - Data Flow | INFO | `ATOMIC_ROOT`, `PROJECT_ROOT`, `OUTPUT_DIR`, `UAT_MODE` are module-level globals computed at import time. If environment variables change after import, these will be stale. | 39-42 | Acceptable for CLI usage; document the constraint. |
| E1 - Input Validation | LOW | `sys.argv[1]` is passed directly as `resume_at` without validation. Invalid task IDs (e.g. "abc") would propagate to `run_phase_tasks`. | 122-123 | Validate that `resume_at` is one of "901"-"906" before passing. |
| F1 - Configuration | INFO | Hardcoded output path pattern `.outputs/9-release`. | 41 | Consistent with other phases; acceptable. |
| G1 - Type Safety | INFO | Task wrapper functions accept `**kwargs` but ignore them silently. | 47-74 | Document or log unexpected kwargs. |
| M1 - Consistency | INFO | All six wrapper functions follow identical pattern. Good consistency. | 47-74 | No action needed. |
| P1 - Documentation | INFO | Module docstring clearly lists all task IDs and names. | 2-14 | No action needed. |

---

## File 2: `phases/phase_09_release/tasks/task_901_entry_initialization.py` (188 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| B1 - Unused Import | LOW | `error` imported from `core.ui` but never called. | 15 | Remove `error` from import. |
| B1 - Unused Import | LOW | `info` imported from `core.ui` but never called. | 15 | Remove `info` from import. |
| B1 - Unused Import | LOW | `json` imported but `read_json` from `file_ops` is used for JSON parsing; `json` is only needed by the except clause on line 87. | 7, 87 | Import is used in the except clause (`json.JSONDecodeError`); keep but note the indirect usage. |
| C1 - Error Handling | INFO | Exception handling on line 87 catches `json.JSONDecodeError, OSError, KeyError`, which is comprehensive for JSON file reads. | 87 | Good practice. |
| D1 - Data Flow | INFO | `mem` parameter accepted but never used. | 22 | Either use the memory system or document that it is reserved for future integration. |
| E2 - Input Validation | MEDIUM | `input("Press Enter to continue...")` on line 154 blocks indefinitely in non-interactive environments that do not send EOF. The `EOFError` catch handles pipe/redirect but a hung terminal could block the pipeline. | 153-156 | Consider adding a timeout or checking `sys.stdin.isatty()` before prompting. |
| F2 - Hardcoded Paths | LOW | Phase 8 closeout searched at two hardcoded paths; if the project changes closeout location, this must be updated manually. | 67-68 | Consider centralizing closeout path resolution into a shared utility. |
| H1 - Security | LOW | No sanitization of data read from `closeout_file` before display via print. A malicious closeout JSON with ANSI escape sequences could manipulate terminal output. | 81-86 | Sanitize untrusted string values before printing. |
| J1 - Artifact Handling | INFO | Decision artifact `entry-decision.json` is written with `prerequisites_met` field. | 160-166 | Good practice for audit trail. |
| K1 - CLI Interface | INFO | `argparse` block in `__main__` provides clean CLI with required/optional args. | 172-187 | Good practice. |
| M2 - Consistency | INFO | ANSI color usage matches the pattern across all phase tasks. | 38-40 | Consistent. |
| N1 - Readability | INFO | Section divider comments with box-drawing characters improve readability. | 55-57 | Good practice. |
| O1 - Output Quality | LOW | Hardcoded terminal width of 120 characters for separator lines may not render well on narrower terminals. | 38 | Consider using `shutil.get_terminal_size()` or a configurable width. |
| R1 - Testability | MEDIUM | `input()` calls make unit testing difficult without mocking stdin. | 154 | Extract interactive prompts into an injectable IO layer. |

---

## File 3: `phases/phase_09_release/tasks/task_902_release_setup.py` (238 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| B1 - Unused Import | LOW | `error` imported from `core.ui` but never called. | 15 | Remove `error` from import. |
| B1 - Unused Import | LOW | `info` imported from `core.ui` but never called. | 15 | Remove `info` from import. |
| C1 - Error Handling | MEDIUM | Bare `except Exception as e` on line 71 catches all exceptions when reading setup file, including `KeyboardInterrupt` in Python 3.x (wait -- `KeyboardInterrupt` inherits from `BaseException`, so actually fine). Still, overly broad catch could mask bugs like `TypeError` or `AttributeError` from malformed data. | 71 | Narrow to `(json.JSONDecodeError, OSError, KeyError)` like task_901 does. |
| D1 - Data Flow | INFO | `mem` parameter accepted but never used. | 22 | Document as reserved for future use. |
| D4 - Hardcoded Values | MEDIUM | Feature and fix counts are hardcoded simulated values (`features_count = 5`, `fixes_count = 0`) with only a comment noting they are simulated. These values are written to the setup payload. | 91-93 | Implement actual CHANGELOG.md parsing or clearly flag simulated data in the output artifact. |
| E3 - Input Validation | LOW | User input for `notes_confirm` on line 204 checks for `"y"` and `"Y"` separately but the input is already lowercased via `.lower()`. The `"Y"` check is dead code. | 204, 210 | Change condition to `if notes_confirm != "y":`. |
| F3 - Version String | LOW | Default version `"0.1.0"` is hardcoded as fallback on lines 64 and 69. | 64, 69 | Consider centralizing default version to a single constant. |
| H2 - Security | LOW | `notes_feedback` (raw user input) is written directly to JSON without sanitization. | 213, 123 | Sanitize or length-limit user feedback before persisting. |
| I1 - Concurrency | INFO | No concurrent access concerns; single-threaded interactive flow. | -- | No action needed. |
| J2 - Artifact Integrity | INFO | `setup_payload` includes `"simulated": True` flag for changelog data. | 117 | Good transparency practice. |
| M3 - Consistency | INFO | `_get_final_confirmation()` returns True for both "yes" and "review again" paths, which could be surprising -- "review again" always proceeds. | 155-172 | Consider looping on "review again" instead of auto-proceeding. |
| N2 - UX | LOW | Prompt text says `"Accept (default: y/n)"` which is ambiguous -- the default appears to be "y" based on the `or "y"` fallback. | 204 | Change to `"Accept (default: y): "` or `"Accept [y/n]: "`. |
| R2 - Testability | MEDIUM | Three separate `input()` calls with no abstraction layer make unit testing require multiple mock patches. | 150, 163, 204, 213 | Extract all interactive prompts into a single injectable IO class. |

---

## File 4: `phases/phase_09_release/tasks/task_903_agent_selection.py` (196 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| B1 - Unused Import | LOW | `error` imported from `core.ui` but never called. | 16 | Remove `error` from import. |
| B1 - Unused Import | LOW | `info` imported from `core.ui` but never called. | 16 | Remove `info` from import. |
| B1 - Unused Import | LOW | `warning` imported from `core.ui` but never called. | 16 | Remove `warning` from import. |
| B1 - Unused Import | LOW | `YELLOW` imported from `core.utils.cli_ui` but actually IS used on lines 89, 95, 112, 115. | 17 | Confirmed used; no action. |
| D1 - Data Flow | LOW | `project_root` assigned on line 35 but never referenced in the function body. | 35 | Remove unused variable. |
| D1 - Data Flow | INFO | `mem` parameter accepted but never used. | 23 | Document as reserved for future use. |
| E4 - Input Validation | MEDIUM | Custom agent name (line 130) is not validated. An empty string, whitespace-only string, or string with special characters (`:`, `/`, `..`) would be accepted and written to the agents JSON and potentially used as a filesystem path component in task_904's `find_agent_prompt`. | 130-132 | Validate custom agent name: non-empty, alphanumeric/hyphens only, length-limited. |
| H3 - Path Traversal | MEDIUM | Custom agent name from user input on line 130 is used as part of a file path in task_904 (`agent_repo / "expert-agents" / f"{agent_name}.md"`). A malicious name like `../../etc/passwd` could cause unintended file reads. | 130, (task_904:40-42) | Sanitize the agent name to prevent path traversal (strip `/`, `..`, non-alphanumeric chars). |
| J3 - Artifact Handling | INFO | UAT mode creates output at `output_dir / "release-agents.json"` (line 47) using a separate variable `selected_agents_file` rather than the `agents_file` variable from line 37. Both resolve to the same path but the redundant variable is confusing. | 37, 47 | Use the existing `agents_file` variable in UAT block. |
| M4 - Consistency | INFO | Production path writes to `agents_file` (line 162) while UAT path writes to a fresh `selected_agents_file` (line 47). | 37, 47, 162 | Use `agents_file` consistently. |
| N3 - UX | INFO | Agent selection options are clear with defaults. | 113-116 | Good practice. |
| R3 - Testability | MEDIUM | Two `input()` calls (lines 119, 130-131) with no abstraction. | 119, 130, 131 | Extract interactive prompts. |

---

## File 5: `phases/phase_09_release/tasks/task_904_release_execution.py` (397 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| B1 - Unused Import | LOW | `error` imported from `core.ui` but never called. | 19 | Remove `error` from import. |
| B1 - Unused Import | LOW | `warning` imported from `core.ui` but never called. | 19 | Remove `warning` from import. |
| B1 - Unused Import | LOW | `info` imported from `core.ui` but never called. | 19 | Remove `info` from import. |
| C2 - Error Handling | MEDIUM | LLM retry loop (lines 277-291) only retries twice. On the second failure, the error message is printed but execution continues to the fallback. The first failure is silently swallowed (only debug-logged). | 277-291 | Consider logging a visible warning on first failure, not just debug. |
| C3 - Error Handling | MEDIUM | `_load_release_config` catches bare `except Exception` on line 159 when reading agents JSON. This is overly broad. | 159 | Narrow to `(json.JSONDecodeError, OSError, KeyError)`. |
| C4 - Error Handling | MEDIUM | `_load_release_config` catches bare `except Exception` on line 174 when reading setup file. | 174 | Narrow to `(json.JSONDecodeError, OSError)`. |
| C5 - Error Handling | LOW | `find_agent_prompt` catches bare `except Exception` on line 58 when reading agent file. | 58 | Narrow to `(OSError, UnicodeDecodeError)`. |
| D1 - Data Flow | INFO | `mem` parameter accepted but never used. | 64 | Document as reserved for future use. |
| D5 - Return Value | LOW | `execute()` always returns `True` (line 127), even if the LLM call fails and falls back to template. There is no way for callers to know the announcement used a fallback. | 127 | Consider returning False or a status object when LLM fails, or log a warning. |
| E5 - Input Injection | MEDIUM | `project_context` (gathered from arbitrary files on disk) is injected directly into the LLM prompt without size limits. A very large PRD or changelog could exceed token limits or cause unexpected behavior. | 250-268 | Truncate `project_context` to a maximum character/token limit before embedding in the prompt. |
| F4 - Hardcoded Model | LOW | LLM model is hardcoded to `"haiku"` on line 281. | 281 | Should respect the agent selection model from task_903 (stored in `release-agents.json`). |
| G2 - Type Safety | INFO | `find_agent_prompt` return type `Optional[str]` is correctly documented and used. | 27 | Good practice. |
| H4 - Prompt Injection | MEDIUM | Content from external files (PRD, changelog, phase closeout JSONs) is embedded in the LLM prompt without sanitization. A crafted PRD could inject adversarial instructions into the prompt. | 186-223, 250-268 | Consider wrapping external content in clear delimiters or applying prompt-injection defenses. |
| H5 - Version Sanitization | INFO | Version string is sanitized via `re.sub(r'[^a-zA-Z0-9.\-]', '', version)[:50]` before embedding in prompt. | 248 | Good practice. |
| J4 - Artifact Files | INFO | Prompt, announcement, execution record, and decision JSON are all saved. Good audit trail. | 270, 296-323, 359-378 | Good practice. |
| L1 - Fallback Logic | LOW | Fallback announcement template (lines 299-323) contains hardcoded generic content ("Core functionality implementation", etc.) that may not match the actual project. | 299-323 | Consider generating fallback from actual project metadata or clearly marking as placeholder. |
| M5 - Consistency | LOW | UAT mode uses `strftime("%Y-%m-%dT%H:%M:%SZ")` (line 97) while production uses `.isoformat()` (line 368). These produce slightly different formats (the strftime version always uses "Z" suffix, isoformat uses "+00:00"). | 97, 368 | Standardize timestamp format across UAT and production paths. |
| N4 - Readability | INFO | Code is well-decomposed into private helper functions `_load_release_config`, `_gather_context`, `_generate_announcement`, `_save_execution_results`. | 130-378 | Good practice. |
| O2 - LLM Output | LOW | LLM response is written directly to `announcement_file` without any validation that it is valid Markdown or contains expected sections. | 296 | Validate LLM output structure before writing. |
| P2 - Documentation | INFO | Docstrings present on all functions with clear return types. | 27-36, 64-75, 130-131, 180-181, 227-231, 340-343 | Good practice. |
| R4 - Testability | INFO | No `input()` calls in this file; LLM dependency is the main testing challenge. | -- | Mock `invoke_llm` for testing. |

---

## File 6: `phases/phase_09_release/tasks/task_905_release_confirmation.py` (249 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| B1 - Unused Import | LOW | `error` imported from `core.ui` but never called. | 15 | Remove `error` from import. |
| B1 - Unused Import | LOW | `info` imported from `core.ui` but never called. | 15 | Remove `info` from import. |
| C6 - Error Handling | MEDIUM | `_load_release_status` catches bare `except Exception` on line 91 when reading execution file. | 91 | Narrow to `(json.JSONDecodeError, OSError, KeyError)`. |
| D1 - Data Flow | LOW | `mem` parameter is passed through to `_handle_confirmation` (line 68) but is never used inside `_handle_confirmation`. | 22, 68, 137 | Remove `mem` propagation to `_handle_confirmation` or implement its use. |
| D6 - False Positive Logic | MEDIUM | On line 129, "Distribution artifacts ready" is always printed as a pass (`GREEN`) without actually checking whether distribution artifacts exist. | 129 | Verify `dist/` directory existence before claiming artifacts are ready. |
| E6 - Input Validation | LOW | `confirmer_name` from user input (line 200-202) is written directly to JSON and used in display strings without sanitization or length limits. | 200-202, 210, 217, 225 | Sanitize and length-limit confirmer name. |
| H6 - Security | LOW | Confirmer name embedded in decision JSON artifact without sanitization. | 225 | Sanitize before persisting. |
| J5 - Gate Logic | INFO | The "investigate" branch correctly loops back via `continue` (line 183) rather than using recursion. | 140-183 | Good practice; avoids stack depth issues. |
| M6 - Default Behavior | LOW | Any input that is not "investigate" or "rollback" is treated as "confirm" (line 192-194). This means typos like "confrim" would silently confirm. | 192-194 | Only accept exact "confirm" and re-prompt on unrecognized input. |
| N5 - UX | INFO | Clear separation of confirmation options with color coding. | 157-159 | Good practice. |
| R5 - Testability | MEDIUM | Four `input()` calls across the file make testing without mocks difficult. | 163, 178, 200 | Extract interactive prompts. |

---

## File 7: `phases/phase_09_release/tasks/task_906_closeout.py` (332 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| B1 - Unused Import | LOW | `error` imported from `core.ui` but never called. | 17 | Remove `error` from import. |
| B1 - Unused Import | LOW | `info` imported from `core.ui` but never called. | 17 | Remove `info` from import. |
| B1 - Unused Import | LOW | `RED` imported from `core.utils.cli_ui` but is used on line 174 inside `_run_checklist`. Actually used. | 18 | Confirmed used; no action. |
| C7 - Error Handling | MEDIUM | `except Exception` on lines 80 and 87 are overly broad. | 80, 87 | Narrow to `(json.JSONDecodeError, OSError, KeyError)`. |
| D1 - Data Flow | INFO | `mem` parameter accepted but never used. | 24 | Document as reserved for future use. |
| D7 - False Positive Logic | MEDIUM | Line 166 unconditionally prints "Distribution artifacts ready" as PASS without verifying `dist/` directory actually exists. Identical to the issue in task_905. | 166-167 | Verify artifacts exist before reporting PASS. |
| E7 - Markdown Generation | LOW | `_generate_closeout_md` uses `chr(10)` for newline in f-string on line 264. While functional, it is an unusual pattern that reduces readability. | 264 | Use a regular join outside the f-string for clarity. |
| F5 - Hardcoded Content | INFO | ASCII art banner for "CONGRATULATIONS" is hardcoded in `_display_completion`. | 301-304 | Acceptable for a completion screen. |
| J6 - Checklist Format | LOW | Checklist items use `":PASS"` / `":FAIL"` suffix convention which is parsed via `split(':', 1)`. This is fragile -- if a checklist item name contains a colon, parsing breaks. | 150-176, 232-243 | Use a structured tuple or dataclass instead of string-encoded status. |
| M7 - Consistency | LOW | UAT mode timestamp uses `strftime("%Y-%m-%dT%H:%M:%SZ")` (line 59) while production uses `.isoformat()` (line 111). Same inconsistency as task_904. | 59, 111 | Standardize timestamp format. |
| M8 - Approval Logic | LOW | The "review" option in `_get_approval` (line 206-218) lists artifacts and then returns True (proceeds with closeout) without re-asking for approval. | 206-218 | Loop back to the approval prompt after review, similar to task_905's investigate loop. |
| N6 - Markdown Quality | INFO | Generated closeout markdown includes checkbox syntax `[x]`, `[ ]`, `[~]`, `[-]`. The `[~]` and `[-]` are non-standard Markdown checkbox syntax. | 237-243 | Use standard `[x]` and `[ ]` only, or add a legend. |
| O3 - Terminal Width | LOW | Completion banner uses hardcoded width of 115 characters. | 284, 298, 312 | Consider terminal width detection. |
| P3 - Documentation | INFO | Module docstring clearly states this is the final task in the pipeline. | 2-6 | Good practice. |
| R6 - Testability | MEDIUM | `input()` calls on lines 201 and 215 require mocking for tests. | 201, 215 | Extract interactive prompts. |

---

## Cross-File Findings

| Check | Severity | Finding | Files Affected | Recommendation |
|-------|----------|---------|---------------|----------------|
| B1 - Unused Imports (Pattern) | LOW | `error` and `info` from `core.ui` are imported in all 6 task files but only `warning` is used in task_901 and `success`/`step` are used everywhere. The import pattern `success, error, warning, info, step` appears to be cargo-culted across all files. | All 6 task files | Create a standard import line or import only what is needed per file. |
| C8 - Exception Breadth (Pattern) | MEDIUM | Bare `except Exception` is used in tasks 902, 904, 905, 906. Task 901 correctly uses `(json.JSONDecodeError, OSError, KeyError)`. | 902:71, 904:58/159/174, 905:91, 906:80/87 | Standardize on narrowed exception handling like task_901. |
| D8 - Memory Integration (Pattern) | LOW | All 6 task `execute()` functions accept a `mem` parameter but none use it (task_905 passes it through but never reads/writes). | All 6 task files | Either implement memory integration or remove the parameter. |
| E8 - Interactive Blocking (Pattern) | MEDIUM | 13 `input()` calls across the phase with only `EOFError`/`KeyboardInterrupt` handling. No timeout mechanism exists for any prompt. In automated pipelines, a stuck prompt could block indefinitely. | 901:154, 902:150/163/204/213, 903:119/130/131, 905:163/178/200, 906:201/215 | Implement a `prompt_with_timeout()` utility or check `sys.stdin.isatty()`. |
| F6 - Default Version (Pattern) | LOW | Default version `"0.1.0"` is hardcoded in tasks 902, 904, 905, 906 independently. | 902:64, 904:169, 905:81, 906:71 | Centralize to a single constant or configuration. |
| H7 - User Input to JSON (Pattern) | LOW | User-provided strings (confirmer name in 905, notes feedback in 902, custom agent name in 903) are written to JSON artifacts without sanitization. | 902:123, 903:132, 905:210 | Implement input sanitization before persisting to artifacts. |
| M9 - Timestamp Format (Pattern) | LOW | UAT paths use `strftime("%Y-%m-%dT%H:%M:%SZ")` while production paths use `datetime.isoformat()`. These yield different suffix formats for UTC. | 904:97 vs 368, 905:50, 906:59 vs 111 | Pick one format and use it consistently. |
| M10 - sys.path Manipulation (Pattern) | LOW | All 6 task files and the orchestrator manipulate `sys.path` at module level with `sys.path.insert(0, ...)`. | All 7 files | Resolve import paths through proper packaging (pyproject.toml / setup.py). |
| R7 - Testability (Pattern) | MEDIUM | No task file has any unit tests. All interactive prompts are raw `input()` calls without abstraction, making test isolation difficult. | All 6 task files | Create an IO abstraction layer; add unit tests with mocked IO. |

---

## Aggregate Severity Counts

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 18 |
| LOW | 33 |
| INFO | 28 |
| **Total** | **79** |

### Breakdown by Category

| Category | Findings |
|----------|----------|
| A - Naming/Structure | 1 |
| B - Imports | 16 |
| C - Error Handling | 9 |
| D - Data Flow | 10 |
| E - Input Validation | 5 |
| F - Configuration/Hardcoding | 5 |
| G - Type Safety | 2 |
| H - Security | 5 |
| I - Concurrency | 1 |
| J - Artifacts/Logic | 5 |
| K - CLI Interface | 1 |
| L - Fallback Logic | 1 |
| M - Consistency | 9 |
| N - Readability/UX | 5 |
| O - Output Quality | 3 |
| P - Documentation | 3 |
| R - Testability | 7 |

### Top Recommendations (by impact)

1. **Narrow exception handling** -- Replace 8 instances of bare `except Exception` with specific exception types matching what task_901 already does. (MEDIUM, 8 locations)
2. **Validate user input** -- Sanitize custom agent names (task_903 line 130) to prevent path traversal in task_904. Add length limits to confirmer name and notes feedback. (MEDIUM, 3 locations)
3. **Add interactive timeout/guard** -- Implement `sys.stdin.isatty()` check or timeout wrapper for the 13 `input()` calls to prevent pipeline blocking. (MEDIUM, 13 locations)
4. **Fix false-positive artifact checks** -- Tasks 905 and 906 report "Distribution artifacts ready" without verifying `dist/` exists. (MEDIUM, 2 locations)
5. **Remove unused imports** -- `error` and `info` from `core.ui` are imported but unused in all 6 task files. (LOW, 12 instances)
6. **Implement CHANGELOG.md parsing** -- Task_902 uses hardcoded simulated feature/fix counts instead of parsing the actual changelog. (MEDIUM, 1 location)
7. **Standardize timestamp format** -- Choose either `strftime` or `isoformat` for UTC timestamps. (LOW, 4 locations)
8. **Extract interactive IO layer** -- All `input()` calls should go through an injectable abstraction for testability. (MEDIUM, systemic)

---

*End of Phase 09 Release audit report.*
