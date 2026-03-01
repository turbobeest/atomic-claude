# Phase 00 - Setup: Code Audit Report
**Date**: 2026-02-28
**Auditor**: Claude Opus 4.6

---

## File 1: `phases/phase00/orchestrator00.py` (129 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | INFO | All return paths correctly return `bool` from `run_phase()` via delegation to `run_phase_tasks()`. Wrapper functions (101-123) correctly pass through return values. | 57-96, 101-123 | N/A |
| A2 | INFO | No direct state dict manipulation. State is delegated to `run_phase_tasks`. | - | N/A |
| A3 | LOW | `ATOMIC_ROOT` uses `Path(os.getenv('ATOMIC_ROOT', Path.cwd()))` -- the `Path.cwd()` default is evaluated at import time, not call time. If the CWD changes between import and execution, the default is stale. | 37 | Consider moving `Path.cwd()` into a function or using a string sentinel. |
| A4 | INFO | No unguarded dict/list access. | - | N/A |
| A5 | MEDIUM | `OUTPUT_DIR` on line 39 passes a `Path` object as the second argument to `os.getenv()`, which expects a `str` default. `os.getenv()` returns the `Path` object directly without conversion, but downstream callers may expect a `str`. In practice, `Path(Path(...))` works, so the result is still a `Path`. | 39 | Use `Path(os.getenv('ATOMIC_OUTPUT_DIR', str(PROJECT_ROOT / '.outputs' / '0-setup')))` for type correctness. |
| A6 | INFO | No concurrent operations. | - | N/A |
| A7 | INFO | `resume_at` parameter defaults to `None`, handled by `run_phase_tasks`. | 57 | N/A |
| A8 | INFO | No complex boolean logic. | - | N/A |
| A9 | INFO | Task numbering (001-005) and phase number (0) are consistent. | 68-74 | N/A |
| A10 | INFO | No resource handles opened. | - | N/A |
| B1-B8 | INFO | No exception handling in this file -- all delegated to task functions and `run_phase_tasks`. | - | N/A |
| C1 | LOW | `logging` is imported on line 15 and `logger` defined on line 23, but `logger` is never used in this file. | 15, 23 | Remove unused `logger` or add debug logging. |
| C2-C10 | INFO | No dead code, no commented-out code, no vestigial functions. | - | N/A |
| D1-D8 | INFO | No stubs, no TODOs, no placeholders. | - | N/A |
| E1 | INFO | No duplicate logic. | - | N/A |
| E2 | INFO | Clean delegation pattern. | - | N/A |
| E3-E10 | INFO | N/A -- file is a thin orchestrator. | - | N/A |
| F1 | INFO | `run_phase()` signature matches expected orchestrator interface (`resume_at` parameter). | 57 | N/A |
| F2-F4 | INFO | Task wrapper functions correctly pass `ATOMIC_ROOT`, `OUTPUT_DIR`, `UAT_MODE`, and `mem` to task `execute()` functions. | 101-123 | N/A |
| F5-F8 | INFO | N/A -- no LLM invocation, no agent contract, no memory contract, no audit integration in orchestrator. | - | N/A |
| G1 | INFO | No user-controlled path construction. | - | N/A |
| G2 | INFO | No command execution. | - | N/A |
| G3 | INFO | No secrets handled. | - | N/A |
| G4 | INFO | No external input processed directly. | - | N/A |
| G5-G6 | INFO | N/A. | - | N/A |
| H1-H5 | LOW | `_print_setup_description()` uses raw `print()` for all output. No logging for observability when running non-interactively. | 43-54 | Consider adding `logger.info()` for the phase start event. |
| I1 | INFO | Environment variables (`ATOMIC_ROOT`, `ATOMIC_OUTPUT_DIR`, `ATOMIC_UAT_MODE`) are read via `os.getenv` with defaults. | 37-40 | N/A |
| I2 | LOW | `PROJECT_ROOT = ATOMIC_ROOT.parent` assumes atomic-claude is always one level below the project root. | 38 | Document this assumption or make configurable. |
| I3-I4 | INFO | Config access via env vars with defaults. | - | N/A |
| J1 | INFO | Import ordering follows stdlib > third-party > local pattern. | 15-34 | N/A |
| J2-J7 | INFO | Naming conventions, docstrings, consistent patterns. | - | N/A |
| K1-K5 | INFO | N/A -- no graph operations in orchestrator. | - | N/A |
| L1 | INFO | Phase is re-runnable via `resume_at`. | - | N/A |
| L2-L5 | INFO | N/A -- orchestrator delegates these concerns. | - | N/A |
| M1-M10 | INFO | N/A -- no LLM operations. | - | N/A |
| N1 | INFO | No circular imports. `sys.path.insert` on line 21 is necessary for project structure. | 21 | N/A |
| N2 | INFO | Orchestrator correctly delegates to task modules. | - | N/A |
| N3-N8 | INFO | Clean module boundary. | - | N/A |
| O1-O7 | INFO | N/A -- no external dependencies beyond project internals. | - | N/A |
| P1-P9 | INFO | No test files audited in this pass. | - | N/A |
| Q1-Q8 | INFO | N/A -- no state lifecycle management. | - | N/A |
| R1-R10 | INFO | N/A -- orchestrator delegates UI concerns. | - | N/A |

**Summary**: 0 critical, 0 high, 1 medium, 3 low findings
**Action Items**:
1. Fix `os.getenv()` type mismatch on line 39 -- pass `str()` wrapped default.
2. Remove unused `logger` import or use it for phase lifecycle events.
3. Document the `ATOMIC_ROOT.parent` assumption.

---

## File 2: `phases/phase_00_setup/tasks/task_001_environment_bootstrap.py` (784 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | INFO | `execute()` returns `True` on success (line 167), `False` on config write failure (line 154). All paths covered. | 47-167 | N/A |
| A2 | INFO | Uses global counters (`REQUIRED_TOTAL`, etc.) with proper reset at function start. Thread-safety caveat documented. | 40-44, 68-72 | N/A |
| A3 | INFO | All paths constructed with `Path()` objects or `Path /` operator. | - | N/A |
| A4 | MEDIUM | `_check_tool()` line 379: `int(version.split('.')[0])` -- if `version` is the string `"installed"` (returned on line 285 as fallback), `split('.')[0]` yields `"installed"` and `int()` raises `ValueError`. This only affects node where `min_version` is set. In `_show_required_tools` (line 378-383) this would crash. | 378-379 | Wrap in try/except ValueError, or check version format before parsing. |
| A5 | INFO | Function signatures are consistent across all internal calls. | - | N/A |
| A6 | LOW | `_launch_dashboard()` spawns `Popen` with `start_new_session=True` -- the subprocess is intentionally detached. No race condition, but no cleanup on task failure. | 595-601 | Consider storing PID for later cleanup. |
| A7 | INFO | Missing files handled (`dashboard_script.exists()`, `pkg.exists()`, `compose_file.exists()`). | 586, 533, 666 | N/A |
| A8 | INFO | Boolean logic correct throughout. | - | N/A |
| A9 | INFO | No off-by-one issues. | - | N/A |
| A10 | LOW | `Popen` at line 595 creates a detached subprocess. If the dashboard crashes, no handle exists to detect or restart it. The handle itself is not leaked (Python GC), but the process is orphaned by design. | 595 | Document the intentional orphaning; consider a PID file. |
| B1 | INFO | No bare `except` clauses. | - | N/A |
| B2 | MEDIUM | `_recheck_required()` line 423: `except Exception as e` -- overly broad for parsing a version string. Only `ValueError` or `IndexError` is expected. | 423 | `except (ValueError, IndexError)` |
| B3 | LOW | `_check_tool()` line 282-283: `except (subprocess.SubprocessError, OSError, ValueError): pass` -- silently swallows errors and falls through to returning `"installed"` (line 285). If a tool exists but `--version` always fails, it will be reported as installed. | 282-285 | Return `None` instead of falling through to `"installed"`. |
| B4 | INFO | No re-raised exceptions. | - | N/A |
| B5 | INFO | Error recovery in `execute()` is appropriate -- returns `False` on config write failure. | 151-154 | N/A |
| B6 | LOW | `_install_dashboard_deps()` line 556: generic `except Exception as e` catches all failures including KeyboardInterrupt (in Python 3, `KeyboardInterrupt` does not inherit from `Exception`, so this is fine). | 556 | N/A |
| B7 | INFO | Exception types are correct for subprocess operations. | - | N/A |
| B8 | INFO | No `finally` blocks needed -- `with` statements used for file I/O. | - | N/A |
| C1 | LOW | `from typing import ... List` is imported but `List` is only used in the type hint on line 24. The `Optional` type is used. `Dict`, `Any` are used. All imports are utilized. | 24 | N/A |
| C2 | INFO | No unused variables. | - | N/A |
| C3 | INFO | No unreachable code. | - | N/A |
| C4 | INFO | No commented-out code. | - | N/A |
| C5 | LOW | `_check_tool()` has a branch for `task-master` (line 263-264) that returns `"installed"` unconditionally. Comment says "Legacy -- no longer required" but it is still listed nowhere in required/recommended tools. | 263-264 | Remove the dead `task-master` branch or add a comment explaining retention. |
| C6 | INFO | No dead conditional branches beyond `task-master`. | - | N/A |
| C7 | INFO | No obsolete compat code. | - | N/A |
| C8 | INFO | No debug code left in. | - | N/A |
| C9 | INFO | No redundant assignments. | - | N/A |
| C10 | INFO | No copy-paste artifacts. | - | N/A |
| D1-D8 | INFO | No stubs, no TODOs, no placeholders. Fully implemented. | - | N/A |
| E1 | LOW | `_detect_os()` is duplicated between task_001 and task_005 (noted in docstring on line 193). | 189-216 | Consider extracting to `core.utils` if more tasks need it. |
| E2 | INFO | Reasonable complexity. | - | N/A |
| E3 | INFO | No string building anti-patterns. | - | N/A |
| E4 | INFO | Config file read/write consolidated in `_record_environment`. | - | N/A |
| E5 | INFO | Data structures are appropriate. | - | N/A |
| E6 | MEDIUM | Magic numbers: node minimum version `18` hardcoded on lines 364, 421; subprocess timeout `5` repeated throughout; dashboard port `5174` as string default; FalkorDB ports `6379`/`3001`. | 364, 421, 589, 670-671 | Extract as named constants at module level. |
| E7 | LOW | `_check_tool()` is 62 lines (lines 223-285), slightly over the 50-line threshold. It is a single function with many tool-specific branches. | 223-285 | Consider a dispatch table mapping tool names to version-extraction lambdas. |
| E8 | INFO | No nesting deeper than 3 levels. | - | N/A |
| E9 | INFO | Consistent UI patterns across all display functions. | - | N/A |
| E10 | INFO | No unnecessary type conversions. | - | N/A |
| F1 | INFO | `execute()` signature matches the `__init__.py` export (`task_001 = execute`). | 47 | N/A |
| F2 | INFO | Writes to `project-config.json` as specified in orchestrator artifacts. | 62 | N/A |
| F3-F4 | INFO | Returns `bool` as contracted. | - | N/A |
| F5 | INFO | N/A -- no LLM invocation. | - | N/A |
| F6 | INFO | N/A -- no agent contract. | - | N/A |
| F7 | INFO | Memory recording (lines 157-164) calls `mem.finding()` and `mem.configuration()` correctly. | 157-164 | N/A |
| F8 | INFO | N/A -- no audit integration. | - | N/A |
| G1 | INFO | No path traversal risk -- paths derived from `atomic_root` and `output_dir`. | - | N/A |
| G2 | LOW | `subprocess.run(["bash", str(dashboard_script)], ...)` -- `dashboard_script` is constructed from `atomic_root / "dashboard" / "start-dashboard.sh"`, not from user input. Safe. | 596 | N/A |
| G3 | INFO | No secrets handled in this task. | - | N/A |
| G4 | INFO | No external input beyond tool installation status. | - | N/A |
| G5 | INFO | No file permission changes. | - | N/A |
| G6 | INFO | Logging uses `%s` formatting (not f-strings), which is correct for lazy evaluation. | - | N/A |
| H1 | INFO | Appropriate log levels (`logger.debug` for non-critical failures, `logger.error` for config write). | - | N/A |
| H2 | INFO | Error messages include context (file paths, error details). | - | N/A |
| H3 | INFO | Progress visible via print statements for each tool check and dashboard step. | - | N/A |
| H4 | LOW | `_launch_dashboard()` line 633-634: if the dashboard launch fails entirely (outer `except Exception`), only `logger.debug` is called. No user-visible message. | 633-634 | Add a `print(print_yellow(...))` for user visibility. |
| H5 | INFO | N/A -- not using structured logging. | - | N/A |
| I1 | MEDIUM | Hardcoded port defaults: `"5174"` (dashboard, line 589), `"6379"` (graph, line 670), `"3001"` (browser, line 671). These are read from env vars but default values are magic strings. | 589, 670-671 | Extract as module-level constants. |
| I2 | INFO | OS detection handles macOS, Linux variants, Windows. | 189-216 | N/A |
| I3 | INFO | Env vars read via `os.environ.get()` with defaults. | - | N/A |
| I4 | INFO | Defaults are reasonable. | - | N/A |
| J1 | INFO | Import ordering correct. | - | N/A |
| J2-J7 | INFO | Consistent naming, docstrings present. | - | N/A |
| K1-K5 | INFO | N/A -- no graph operations. | - | N/A |
| L1 | MEDIUM | Not fully idempotent: `_install_dashboard_deps` skips if `node_modules` exists, but `_launch_dashboard` always spawns a new process. Re-running could launch duplicate dashboard instances. | 580-635 | Check if dashboard is already running (e.g., PID file or port check) before launching. |
| L2 | INFO | N/A -- no backtrack-specific logic. | - | N/A |
| L3 | INFO | Subprocess timeouts are set (5s for version checks, 120s for npm install, 60s for docker compose). | - | N/A |
| L4 | INFO | Graceful degradation: dashboard launch failure doesn't block task completion. FalkorDB failure doesn't block. | - | N/A |
| L5 | INFO | Config write is not atomic (via `write_file`), but failure is caught and returns False. | - | N/A |
| M1-M10 | INFO | N/A -- no LLM operations. | - | N/A |
| N1 | INFO | `sys.path.insert` at line 30 is necessary for project imports. | 30 | N/A |
| N2 | INFO | No layer violations. | - | N/A |
| N3 | INFO | Minimal state shape coupling -- writes to `config['environment']`. | - | N/A |
| N4 | LOW | `execute()` at 120 lines is a god function by some standards, but the logic is linear and well-sectioned. | 47-167 | Acceptable for a linear pipeline. |
| N5-N8 | INFO | Clean module boundary. | - | N/A |
| O1-O7 | INFO | No external package dependencies beyond stdlib and project internals. | - | N/A |
| P1-P9 | INFO | Not auditing test files in this pass. | - | N/A |
| Q1-Q8 | INFO | State keys are documented. Config file is read-then-merge pattern. | - | N/A |
| R1 | INFO | Progress feedback is excellent -- each tool check, each npm install, dashboard status. | - | N/A |
| R2 | INFO | Error messages are actionable (install commands shown for missing tools). | - | N/A |
| R3 | INFO | N/A -- no destructive actions. | - | N/A |
| R4 | INFO | Consistent use of `print_green`, `print_red`, `print_yellow`, `print_dim`. | - | N/A |
| R5 | INFO | Box drawing assumes 60-char width. | 176-181 | N/A |
| R6 | INFO | `uat_mode` bypasses interactive prompts. | - | N/A |
| R7 | INFO | N/A. | - | N/A |
| R8 | LOW | No explicit `KeyboardInterrupt` handling -- if user presses Ctrl+C during the blocking `prompt_user` loop (line 117), the task will abort without cleanup. | 114-129 | Consider catching `KeyboardInterrupt` for graceful exit. |
| R9-R10 | INFO | N/A. | - | N/A |

**Summary**: 0 critical, 0 high, 5 medium, 10 low findings
**Action Items**:
1. (MEDIUM) Fix potential `ValueError` when `_check_tool` returns `"installed"` and node version parsing attempts `int("installed")` (line 379).
2. (MEDIUM) Narrow `except Exception` to specific types in `_recheck_required` (line 423).
3. (MEDIUM) Extract magic port numbers/version numbers as module-level constants.
4. (MEDIUM) Address duplicate dashboard launch on re-run (idempotency issue).
5. (LOW) Fix `_check_tool` fallthrough returning `"installed"` when `--version` fails.

---

## File 3: `phases/phase_00_setup/tasks/task_002_provider_detection.py` (921 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | INFO | `execute()` returns `True` on success (line 185), `False` on credential failure (line 91). | 68-185 | N/A |
| A2 | INFO | No shared mutable state beyond local dicts. | - | N/A |
| A3 | INFO | Paths constructed with `Path()`. | - | N/A |
| A4 | INFO | Dict access uses `.get()` throughout. | - | N/A |
| A5 | INFO | Type annotations consistent. | - | N/A |
| A6 | INFO | No concurrent operations. | - | N/A |
| A7 | INFO | Handles missing `.env`, missing `secrets.json`, empty credentials. | - | N/A |
| A8 | INFO | Boolean logic correct. | - | N/A |
| A9 | INFO | No off-by-one errors. | - | N/A |
| A10 | INFO | File handles properly managed with `with` statements and `open()`. | - | N/A |
| B1 | INFO | No bare `except`. | - | N/A |
| B2 | MEDIUM | `_load_env_file()` line 245: `except Exception as e` -- catches everything including `PermissionError`, `IsADirectoryError`, etc. Should catch `OSError`. | 245 | `except OSError as e:` |
| B3 | INFO | No silent swallowing -- all except blocks either log or print. | - | N/A |
| B4 | INFO | No re-raised exceptions. | - | N/A |
| B5 | INFO | Recovery is appropriate (print warning and continue). | - | N/A |
| B6 | LOW | `_credential_wizard()` line 336: `getpass.getpass()` can raise `EOFError` in non-interactive mode, which is not caught. | 336 | Add `except EOFError` handling. |
| B7 | INFO | Exception types correct for operations. | - | N/A |
| B8 | INFO | No `finally` blocks needed. | - | N/A |
| C1 | INFO | All imports are used. | - | N/A |
| C2 | INFO | No unused variables. | - | N/A |
| C3 | INFO | No unreachable code. | - | N/A |
| C4 | INFO | No commented-out code. | - | N/A |
| C5 | INFO | No vestigial functions. | - | N/A |
| C6 | INFO | No dead branches. | - | N/A |
| C7 | INFO | Provider import `try/except ImportError` blocks (lines 39-65) are valid graceful degradation, not dead code. | 39-65 | N/A |
| C8 | INFO | No debug code. | - | N/A |
| C9 | INFO | No redundant assignments. | - | N/A |
| C10 | INFO | No copy-paste artifacts. | - | N/A |
| D1-D8 | INFO | No stubs, no TODOs. | - | N/A |
| E1 | LOW | `_check_ollama_host` and `_list_ollama_models` both construct the same URL `f"{host}/api/tags"` and make the same HTTP request. The second always re-fetches what the first already validated. | 636-658 | Consider caching the response or combining the two operations. |
| E2 | INFO | Complexity is reasonable. | - | N/A |
| E3 | INFO | No string anti-patterns. | - | N/A |
| E4 | LOW | `_configure_ollama_hosts()` reads `secrets.json` (line 541), and then `_health_check_providers()` reads it again (line 732). Two reads of the same file. | 541, 732 | Pass secrets dict as parameter instead of re-reading. |
| E5 | INFO | Data structures appropriate. | - | N/A |
| E6 | MEDIUM | Magic strings: `"http://localhost:11434"` appears 5 times across the file (lines 278, 386, 553, 601, 830). Port `"11434"` is never configurable. | 278, 386, 553, 601, 830 | Extract `DEFAULT_OLLAMA_HOST = "http://localhost:11434"` as a module constant. |
| E7 | LOW | `_health_check_providers()` is 138 lines (lines 723-899) -- well above the 50-line threshold. | 723-899 | Split into per-provider helper functions. |
| E8 | MEDIUM | `_health_check_providers()` has nesting up to 4 levels deep (line 839-844): `if HAS_OLLAMA > for host > try > if status`). | 832-844 | Extract Ollama health check into a separate function. |
| E9 | INFO | Consistent patterns. | - | N/A |
| E10 | INFO | No unnecessary conversions. | - | N/A |
| F1 | INFO | `execute()` matches expected interface. | 68 | N/A |
| F2 | INFO | Writes `secrets.json`, `provider-inventory.json`, and updates `project-config.json` -- matching orchestrator artifact list. | 81-83, 139 | N/A |
| F3-F4 | INFO | Returns `bool` correctly. | - | N/A |
| F5 | INFO | N/A -- no direct LLM invocation (only health checks). | - | N/A |
| F6 | INFO | N/A. | - | N/A |
| F7 | INFO | Memory recording (lines 164-182) is thorough and correct. | 164-182 | N/A |
| F8 | INFO | N/A. | - | N/A |
| G1 | INFO | No path traversal. | - | N/A |
| G2 | INFO | No command injection -- no subprocess calls with user input. | - | N/A |
| G3 | HIGH | `_credential_wizard()` writes the API key to `.env` in plaintext (line 343). The file permissions are set to 0o600 (line 410), which is good. However, the API key is also written to `secrets.json` (line 460) and `os.environ` (line 419). The API key could appear in logs if debug logging is enabled and an exception includes the env_vars dict. | 343, 460, 419 | Ensure secrets never appear in log messages. Consider masking API keys in any diagnostic output. |
| G4 | LOW | `_credential_wizard()` does not validate the API key format before storing. An empty string after stripping would be caught (line 337-339), but a malformed key would not. | 336-339 | Add basic format validation (e.g., starts with expected prefix). |
| G5 | INFO | File permissions set to 0o600 for `.env` and `secrets.json`. | 410, 472 | N/A |
| G6 | INFO | Logging uses `%s` format (lazy evaluation). | - | N/A |
| H1 | INFO | Appropriate log levels throughout. | - | N/A |
| H2 | INFO | Error messages include context. | - | N/A |
| H3 | INFO | Progress visible with provider health status. | - | N/A |
| H4 | LOW | `_push_provider_to_dashboard()` silently returns on `ImportError` (line 491). No indication to user that dashboard push was skipped. | 491 | Add `logger.debug()` for the ImportError case. |
| H5 | INFO | N/A. | - | N/A |
| I1 | MEDIUM | Hardcoded region defaults: `"us-east-1"` appears 4 times (lines 269, 443, 584, 804). GovCloud model IDs hardcoded (lines 448-450). | 269, 443, 584, 804, 448-450 | Extract as constants. |
| I2 | INFO | Handles multiple OS types (Windows `os.name` check for permissions). | 408, 471 | N/A |
| I3 | INFO | Consistent env var access. | - | N/A |
| I4 | INFO | Defaults are sensible. | - | N/A |
| J1 | INFO | Import ordering correct. | - | N/A |
| J2-J7 | INFO | Consistent patterns and docstrings. | - | N/A |
| K1-K5 | INFO | N/A -- no graph operations. | - | N/A |
| L1 | MEDIUM | Partially idempotent: re-running will re-create `secrets.json` (overwriting any manual edits), but the credential wizard only runs if no credentials found. Ollama hosts accumulate -- the same host could be added multiple times across runs if the user types it again (dedup check on line 613 prevents exact duplicates). | 619-632 | Document idempotency behavior. |
| L2 | INFO | N/A. | - | N/A |
| L3 | INFO | HTTP timeouts set (3s for Ollama checks). | 641, 653 | N/A |
| L4 | INFO | Graceful degradation for all provider SDKs via `try/except ImportError`. | 39-65 | N/A |
| L5 | INFO | File writes via `write_file()` utility. | - | N/A |
| M1-M10 | INFO | N/A -- no LLM invocation (health checks only). | - | N/A |
| N1 | INFO | No circular imports. | - | N/A |
| N2 | INFO | No layer violations. | - | N/A |
| N3 | LOW | Tightly coupled to `secrets.json` shape -- multiple functions independently read/write this file with assumptions about key names. | 431-478, 525-632 | Consider a `SecretsManager` class to centralize access. |
| N4 | LOW | `_health_check_providers()` at 138 lines is a god function. | 723-899 | Refactor into per-provider helpers. |
| N5-N8 | INFO | Acceptable module boundaries. | - | N/A |
| O1-O7 | INFO | Optional dependencies handled gracefully (`HAS_CLAUDE_CODE`, etc.). | - | N/A |
| P1-P9 | INFO | Not auditing test files. | - | N/A |
| Q1 | LOW | `secrets.json` is read/written by multiple functions independently (`_create_secrets_file`, `_configure_ollama_hosts`, `_health_check_providers`). No locking or coordination. | 431-478, 619-632 | Consolidate secrets file management. |
| Q2-Q8 | INFO | N/A. | - | N/A |
| R1 | INFO | Good progress feedback. | - | N/A |
| R2 | INFO | Actionable error messages. | - | N/A |
| R3 | INFO | N/A. | - | N/A |
| R4 | INFO | Consistent formatting. | - | N/A |
| R5 | INFO | N/A. | - | N/A |
| R6 | INFO | UAT mode support. | - | N/A |
| R7 | INFO | Dashboard push for provider info. | - | N/A |
| R8 | LOW | No `KeyboardInterrupt` handling during interactive credential prompts. | 285-428 | N/A -- acceptable for setup wizard. |
| R9-R10 | INFO | N/A. | - | N/A |

**Summary**: 0 critical, 1 high, 5 medium, 10 low findings
**Action Items**:
1. (HIGH) Review secret exposure paths -- ensure API keys cannot leak into log output.
2. (MEDIUM) Extract `"http://localhost:11434"` as a module constant (appears 5 times).
3. (MEDIUM) Narrow `except Exception` in `_load_env_file` to `OSError`.
4. (MEDIUM) Reduce nesting in `_health_check_providers` by extracting per-provider helpers.
5. (MEDIUM) Extract hardcoded region defaults as constants.
6. (MEDIUM) Document idempotency behavior for secrets file management.

---

## File 4: `phases/phase_00_setup/tasks/task_003_setup_wizard.py` (1927 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | INFO | `execute()` returns `True` on success (line 344), `False` on abort (line 303). The `_run_wizard` can return `None`, `"RESTART"` (string), or a dict -- all handled by the while loop (lines 298-303). | 253-344 | N/A |
| A2 | INFO | Config dict built incrementally, no shared mutable state. | - | N/A |
| A3 | INFO | Paths constructed with `Path()`. | - | N/A |
| A4 | INFO | Dict access uses `.get()` throughout. | - | N/A |
| A5 | HIGH | `_run_wizard()` return type is `Optional[Dict[str, Any]]` per signature (line 650), but it also returns the string `"RESTART"` (line 1272). The type annotation is incorrect -- it should be `Optional[Union[Dict[str, Any], str]]`. The caller handles this via string comparison (line 299), but type checkers would flag this. | 650, 1272, 298-299 | Update return type annotation to `Optional[Union[Dict[str, Any], str]]` or use a proper sentinel type. |
| A6 | INFO | No concurrent operations. | - | N/A |
| A7 | INFO | Missing `provider-inventory.json` handled (lines 277-286). Empty reference files handled. | 277-286 | N/A |
| A8 | INFO | Boolean logic correct. | - | N/A |
| A9 | INFO | No off-by-one errors in selection prompts (1-based display, 0-based internal). | - | N/A |
| A10 | INFO | No resource leaks. | - | N/A |
| B1 | INFO | No bare `except`. | - | N/A |
| B2 | LOW | `_llm_invoke()` inner `_with_retry()` line 536: `except Exception as e` -- catches all exceptions including non-transient ones. | 536 | More targeted exception handling would be better, but retry-with-fallback pattern mitigates risk. |
| B3 | INFO | No silent swallowing. | - | N/A |
| B4 | INFO | No re-raised exceptions. | - | N/A |
| B5 | INFO | Error recovery appropriate (fallback to defaults on LLM failure). | - | N/A |
| B6 | LOW | `_write_preliminary_config()` line 639: `config_file.write_text()` could raise `PermissionError`, caught by outer `except Exception`. | 633-641 | Acceptable -- failure is logged and non-fatal. |
| B7 | INFO | Exception types appropriate. | - | N/A |
| B8 | INFO | No cleanup needed. | - | N/A |
| C1 | LOW | `import urllib.request` on line 37 is unused -- `_detect_ollama_models` uses it but is imported at module level. Actually used in `_detect_ollama_models` on line 1662. | 37, 1662 | N/A -- actually used. |
| C2 | INFO | No unused variables. | - | N/A |
| C3 | INFO | No unreachable code. | - | N/A |
| C4 | INFO | No commented-out code. | - | N/A |
| C5 | INFO | `_detect_git_remote_url()` (line 1822) duplicates the same logic in `_detect_environment()` (line 362). | 1822-1833, 360-370 | Consolidate into single utility. |
| C6 | INFO | No dead branches. | - | N/A |
| C7 | INFO | No obsolete compat code. | - | N/A |
| C8 | INFO | No debug code. | - | N/A |
| C9 | INFO | No redundant assignments. | - | N/A |
| C10 | INFO | No copy-paste artifacts beyond the duplication noted in C5. | - | N/A |
| D1 | INFO | No stub `pass` statements. | - | N/A |
| D2 | INFO | No `return None/{}` stubs. | - | N/A |
| D3 | INFO | No TODOs. | - | N/A |
| D4 | LOW | `_PROVIDER_PROFILES["ollama"]` sets `models.primary` to `"sonnet"` and `heavyweight` to `"sonnet"` (line 182-183). Ollama cannot run Anthropic's Sonnet model -- these tier names are symbolic not literal, but could confuse downstream consumers expecting actual Ollama model names. | 181-185 | Add a comment clarifying that tiers are symbolic and resolved later. |
| D5 | INFO | No mock data. | - | N/A |
| D6 | INFO | No `NotImplementedError`. | - | N/A |
| D7 | INFO | No feature-gated dead code. | - | N/A |
| D8 | INFO | No skeleton functions. | - | N/A |
| E1 | MEDIUM | `_detect_ollama_models()` (lines 1650-1684) duplicates logic from `task_002._list_ollama_models()` and `task_002._check_ollama_host()`. Both make the same API call to `/api/tags`. | 1650-1684 | Extract shared Ollama utilities to `core.utils`. |
| E2 | LOW | `_run_wizard()` at ~636 lines (lines 644-1277) is extremely long, though the logic is linear step-by-step. | 644-1277 | Consider splitting into per-step functions. |
| E3 | INFO | No string anti-patterns. | - | N/A |
| E4 | LOW | `_load_models_config()` is called 4 times: lines 204, 216, 240, 904. Each call re-reads `config/models.json`. | 204, 216, 240, 904 | Cache the result or pass it as a parameter. |
| E5 | INFO | Data structures appropriate. | - | N/A |
| E6 | MEDIUM | Magic number: `24` for project name max length appears in `_validate_project_name` (line 1894), `_slugify` (line 1907), `_detect_dir_name` (line 1841), and prompt text (line 682). | 682, 1841, 1894, 1907 | Extract as `MAX_PROJECT_NAME_LENGTH = 24`. |
| E7 | HIGH | `_run_wizard()` is 634 lines -- far exceeding the 50-line function length guideline. This is the longest function in the phase. | 644-1277 | Must be refactored into per-step helper functions. |
| E8 | LOW | Some nesting up to 4 levels in the Ollama model display section (lines 988-1001). | 988-1001 | N/A -- visually acceptable. |
| E9 | INFO | Consistent wizard patterns. | - | N/A |
| E10 | INFO | No unnecessary conversions. | - | N/A |
| F1 | INFO | `execute()` matches expected interface. | 253 | N/A |
| F2 | INFO | Writes `project-config.json` and `extracted-config.json` as specified. | 270-271 | N/A |
| F3-F4 | INFO | Returns `bool`. | - | N/A |
| F5 | MEDIUM | LLM invocation in `_llm_invoke()` (lines 520-612) uses `subprocess.run(['claude', '-p', prompt, ...]` which passes the entire prompt as a single argument. For very long prompts (with large reference material), this could exceed OS argument length limits. | 547-549 | Consider piping the prompt via stdin instead of as a CLI argument. |
| F6 | INFO | N/A. | - | N/A |
| F7 | INFO | Memory recording (lines 308-338) is thorough. | 308-338 | N/A |
| F8 | INFO | N/A. | - | N/A |
| G1 | INFO | No path traversal. | - | N/A |
| G2 | LOW | `subprocess.run(['claude', '-p', prompt, ...])` -- `prompt` is constructed internally, not from user input. Safe. | 547-549 | N/A |
| G3 | MEDIUM | `_llm_invoke()` passes `env_vars['ANTHROPIC_API_KEY']` to `AnthropicProvider` config dict (line 566). If LLM invocation fails with an exception that includes the config dict in its message, the API key could be exposed in logs. | 564-567 | Ensure provider constructors don't include secrets in exception messages. |
| G4 | INFO | Project name validated (regex on line 1896). | 1892-1898 | N/A |
| G5 | INFO | N/A. | - | N/A |
| G6 | INFO | Logging uses `%s` format. | - | N/A |
| H1 | INFO | Log levels appropriate. | - | N/A |
| H2 | INFO | User-facing messages are clear. | - | N/A |
| H3 | INFO | Step headers provide clear progress (Step X of Y). | 1287-1298 | N/A |
| H4 | LOW | `_write_preliminary_config()` failure (line 641) only logs at `warning` level with no user-visible message. | 641 | Consider adding a `print_dim` note. |
| H5 | INFO | N/A. | - | N/A |
| I1 | LOW | Hardcoded values: `200` lines max per reference file (line 466), `5` reference files max (line 463), `30` second timeout for Claude CLI (line 549). | 463, 466, 549 | Extract as named constants. |
| I2 | INFO | N/A. | - | N/A |
| I3 | INFO | Config access pattern consistent. | - | N/A |
| I4 | INFO | Defaults are sensible. | - | N/A |
| J1 | INFO | Import ordering correct. | - | N/A |
| J2 | INFO | Consistent naming. | - | N/A |
| J3 | INFO | Config built as dict, consistent pattern. | - | N/A |
| J4 | INFO | LLM invocation follows the fallback chain pattern. | - | N/A |
| J5 | INFO | File output via `write_file`. | - | N/A |
| J6 | INFO | N/A. | - | N/A |
| J7 | INFO | Docstrings present on all public functions. | - | N/A |
| K1-K5 | INFO | N/A -- no graph operations. | - | N/A |
| L1 | MEDIUM | The wizard is not idempotent -- re-running always prompts from scratch. The `RESTART` mechanism (line 1272) only restarts within the same execution. Previous config is not loaded for resume. | 298-303 | Consider loading existing config as defaults when re-running. |
| L2 | INFO | N/A. | - | N/A |
| L3 | INFO | LLM invocation timeouts set (30s for Claude CLI, 30s for Anthropic, 60s for Ollama). | 549, 571, 603 | N/A |
| L4 | INFO | LLM failure falls back to directory-name defaults. | - | N/A |
| L5 | INFO | Config write is sequential (extracted first, then project-config). | - | N/A |
| M1 | INFO | Prompt construction in `_infer_project_defaults` is clean -- reference text is bounded (5 files, 200 lines each). | 461-489 | N/A |
| M2 | MEDIUM | LLM response parsing in `_infer_project_defaults` (line 498-517): strips markdown fences, then `json.loads`. If the LLM returns invalid JSON outside of fences, `json.JSONDecodeError` is caught. However, if the LLM returns valid JSON with unexpected keys or types, no validation occurs. | 498-517 | Add schema validation on the parsed LLM response. |
| M3 | INFO | Hallucination guard: AI suggestions are always shown as defaults that the user confirms. | - | N/A |
| M4 | INFO | Provider fallback chain: Claude CLI > Anthropic > Bedrock > Ollama. | 542-612 | N/A |
| M5 | LOW | No token/cost awareness -- the LLM call has `max_tokens=1024` but no cost estimation. | 571, 588, 603 | Consider logging estimated cost. |
| M6 | INFO | Retry with backoff (1s delay) via `_with_retry`. | 529-540 | N/A |
| M7 | INFO | Uses "haiku" tier for inference suggestions -- appropriate for structured extraction. | 571, 588 | N/A |
| M8 | LOW | LLM output is non-deterministic. `temperature=0.2` mitigates but doesn't eliminate. Results vary between runs. | 571, 588, 603 | Acceptable for suggestion use case. |
| M9 | INFO | Uses batch (non-streaming) invocation. | - | N/A |
| M10 | INFO | LLM errors produce user-visible fallback message. | 611, 516 | N/A |
| N1 | INFO | No circular imports. | - | N/A |
| N2 | LOW | `_run_wizard` line 1077: accesses `_resolver._defaults` (private attribute of the resolver). This is a layer violation. | 1077-1079 | Use public API methods on the resolver. |
| N3 | LOW | Tightly coupled to `provider-inventory.json` schema. | 662-670 | N/A -- expected for downstream consumer. |
| N4 | HIGH | `_run_wizard()` at 634 lines is a god function that handles all 10 wizard steps inline. | 644-1277 | Break into `_step_1_identity()`, `_step_2_type()`, etc. |
| N5-N8 | INFO | N/A. | - | N/A |
| O1 | INFO | LLM provider SDKs are imported lazily inside functions. | 564, 582, 600 | N/A |
| O2-O7 | INFO | N/A. | - | N/A |
| P1-P9 | INFO | Not auditing test files. | - | N/A |
| Q1 | INFO | State keys are well-defined in the output config. | - | N/A |
| Q2 | LOW | The config dict can grow large with all wizard sections, ollama model inventories, and phase assignments. | - | Acceptable for setup phase. |
| Q3-Q8 | INFO | N/A. | - | N/A |
| R1 | INFO | Excellent step-by-step progress with headers. | - | N/A |
| R2 | INFO | Error messages are actionable. | - | N/A |
| R3 | INFO | Quit (`q`) available at every prompt. Restart (`n` at summary) available. | - | N/A |
| R4 | INFO | Consistent formatting. | - | N/A |
| R5 | LOW | Step header padding calculation (line 1293-1294) assumes `print_bold` and `print_dim` don't add visible characters to length. Since these are ANSI escape sequences, the padding may be off. | 1293-1294 | Use the raw text lengths for padding calculation. |
| R6 | INFO | N/A -- wizard is inherently interactive. | - | N/A |
| R7 | INFO | Dashboard updated via preliminary config write. | 712 | N/A |
| R8 | LOW | No `KeyboardInterrupt` handling. | - | N/A -- acceptable for wizard. |
| R9-R10 | INFO | N/A. | - | N/A |

**Summary**: 0 critical, 3 high, 5 medium, 14 low findings
**Action Items**:
1. (HIGH) Fix `_run_wizard()` return type annotation to include `"RESTART"` string.
2. (HIGH) Refactor `_run_wizard()` (634 lines) into per-step helper functions.
3. (HIGH) `_run_wizard()` god function -- same as above, breaking into steps.
4. (MEDIUM) Extract duplicate Ollama detection logic to shared utility.
5. (MEDIUM) Extract magic number `24` as `MAX_PROJECT_NAME_LENGTH`.
6. (MEDIUM) Validate LLM response schema in `_infer_project_defaults`.
7. (MEDIUM) Consider stdin piping for Claude CLI prompt to avoid argument length limits.
8. (MEDIUM) Improve idempotency -- load existing config as defaults on re-run.

---

## File 5: `phases/phase_00_setup/tasks/task_004_material_scan.py` (1337 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | INFO | `execute()` always returns `True` (line 201). There is no failure path that returns `False`. | 71-201 | Consider if any failure should return `False` (e.g., manifest write failure). |
| A2 | INFO | Manifest dict built incrementally, no shared mutable state. | - | N/A |
| A3 | INFO | Paths constructed with `Path()`. | - | N/A |
| A4 | INFO | Dict access uses `.get()` throughout. | - | N/A |
| A5 | INFO | Type annotations consistent. | - | N/A |
| A6 | INFO | No concurrent operations. | - | N/A |
| A7 | INFO | Handles missing directories, empty scans, missing config files. | - | N/A |
| A8 | INFO | Boolean logic correct. | - | N/A |
| A9 | INFO | No off-by-one errors. | - | N/A |
| A10 | INFO | File handles properly managed in `_count_lines` with `with` statements. | 1312-1321 | N/A |
| B1 | INFO | No bare `except`. | - | N/A |
| B2 | MEDIUM | `_prompt_exclusions()` line 579: `except Exception as e` catches everything including `ImportError` from the multi_select import. The fallback is appropriate but the catch is too broad. | 579 | `except (ImportError, RuntimeError, OSError)` would be more precise. |
| B3 | INFO | No silent swallowing. | - | N/A |
| B4 | INFO | No re-raised exceptions. | - | N/A |
| B5 | INFO | Fallback to text-based UI on curses failure is good recovery. | 579-582 | N/A |
| B6 | LOW | `_record_reference_info()` line 1188: `except (json.JSONDecodeError, FileNotFoundError)` catches `FileNotFoundError` but line 1183 already checks `config_file.exists()`. The `FileNotFoundError` could only occur in a TOCTOU race. | 1183-1189 | Acceptable defensive coding. |
| B7 | INFO | Exception types correct. | - | N/A |
| B8 | INFO | No cleanup needed. | - | N/A |
| C1 | INFO | All imports used. | - | N/A |
| C2 | INFO | No unused variables. | - | N/A |
| C3 | INFO | No unreachable code. | - | N/A |
| C4 | INFO | No commented-out code. | - | N/A |
| C5 | INFO | No vestigial functions. | - | N/A |
| C6 | INFO | No dead branches. | - | N/A |
| C7 | INFO | No obsolete compat code. | - | N/A |
| C8 | INFO | No debug code. | - | N/A |
| C9 | INFO | No redundant assignments. | - | N/A |
| C10 | INFO | No copy-paste artifacts. | - | N/A |
| D1-D8 | INFO | No stubs, no TODOs. | - | N/A |
| E1 | LOW | `SKIP_DIRS` (lines 64-68) and `_NESTED_REPO_MARKERS` (lines 977-980) overlap significantly. Both contain `node_modules`, `.git`, `__pycache__`, `dist`, `build`, `.venv`, `venv`. | 64-68, 977-980 | Consolidate into a single constant. |
| E2 | INFO | Reasonable complexity. | - | N/A |
| E3 | INFO | No string anti-patterns. | - | N/A |
| E4 | LOW | `read_file(config_file)` is called in both `_prompt_additional_paths` (line 835) and `_record_reference_info` (line 1187). Config is read twice for overlapping purposes. | 835, 1187 | Pass config dict as parameter. |
| E5 | INFO | Data structures appropriate. | - | N/A |
| E6 | LOW | Magic numbers: `max_depth=4` (line 365), `max_files=50` (line 365), `15` for tree collapse threshold (line 1304), `20` for reference files limit (line 1212), `10` for display limits (lines 1141, 1143, 1152, 1154). | Various | Extract named constants for the key ones. |
| E7 | INFO | All functions are within reasonable length. | - | N/A |
| E8 | INFO | No deep nesting. | - | N/A |
| E9 | INFO | Consistent patterns throughout. | - | N/A |
| E10 | INFO | No unnecessary conversions. | - | N/A |
| F1 | INFO | `execute()` matches expected interface. | 71 | N/A |
| F2 | INFO | Writes `material-manifest.json` and updates `project-config.json`. | 165-167 | N/A |
| F3 | MEDIUM | `execute()` always returns `True` (line 201) -- there is no way for this task to signal failure. Even if `write_file` fails on the manifest, the exception would propagate uncaught. | 165, 201 | Wrap the final write in try/except and return `False` on failure. |
| F4 | INFO | Returns `bool` type. | - | N/A |
| F5 | INFO | N/A -- no LLM invocation. | - | N/A |
| F6 | INFO | N/A. | - | N/A |
| F7 | INFO | Memory recording (lines 170-194) is thorough. | 170-194 | N/A |
| F8 | INFO | N/A. | - | N/A |
| G1 | MEDIUM | `_prompt_additional_paths()` line 804: `Path(raw).expanduser().resolve()` -- user can provide any path, including paths outside the project. This is by design (external references), but there's no validation that the path doesn't point to sensitive locations (e.g., `/etc/shadow`). | 804 | Consider adding a warning for paths outside the user's home directory. |
| G2 | INFO | No command execution. | - | N/A |
| G3 | INFO | No secrets handled. | - | N/A |
| G4 | LOW | `_prompt_additional_paths()` accepts any path -- a directory path could cause a very long scan if it's `/` or a large directory tree. | 812-816 | Add a file count limit warning for large directories. |
| G5 | INFO | No file permission changes. | - | N/A |
| G6 | INFO | Logging safe. | - | N/A |
| H1 | INFO | Appropriate log levels. | - | N/A |
| H2 | INFO | Error messages include context. | - | N/A |
| H3 | INFO | Progress visible via section headers and file counts. | - | N/A |
| H4 | INFO | No silent failures. | - | N/A |
| H5 | INFO | N/A. | - | N/A |
| I1 | LOW | Hardcoded reference patterns list (lines 42-49) -- adding new file types requires code change. | 42-49 | Acceptable for now; could be configurable. |
| I2 | INFO | N/A. | - | N/A |
| I3 | INFO | Consistent config access. | - | N/A |
| I4 | INFO | Defaults are sensible. | - | N/A |
| J1 | INFO | Import ordering correct. | - | N/A |
| J2-J7 | INFO | Consistent patterns and docstrings. | - | N/A |
| K1-K5 | INFO | N/A -- no graph operations. | - | N/A |
| L1 | INFO | Idempotent: `_offer_organization` wipes `collected/` before re-populating (line 933-934). Scans are fresh each run. | 932-934 | N/A |
| L2 | INFO | Backtrack-safe: collected directory is wiped for clean re-runs. | 60-61, 932-934 | N/A |
| L3 | INFO | N/A -- no network operations. | - | N/A |
| L4 | INFO | Graceful degradation from curses to text-based UI. | 579-582 | N/A |
| L5 | INFO | File operations are sequential, not atomic, but acceptable for setup. | - | N/A |
| M1-M10 | INFO | N/A -- no LLM operations. | - | N/A |
| N1 | INFO | No circular imports. | - | N/A |
| N2 | INFO | No layer violations. | - | N/A |
| N3 | INFO | N/A. | - | N/A |
| N4 | INFO | No god functions -- well-decomposed. | - | N/A |
| N5-N8 | INFO | Clean module boundaries. | - | N/A |
| O1-O7 | INFO | `core.utils.multi_select` is an optional dependency, gracefully handled. | 513-515 | N/A |
| P1-P9 | INFO | Not auditing test files. | - | N/A |
| Q1 | INFO | Manifest schema is well-defined. | - | N/A |
| Q2 | LOW | Manifest could grow large if project has many files (source_code limited to 50, but other categories have varying limits). | 432 | N/A |
| Q3-Q8 | INFO | N/A. | - | N/A |
| R1 | INFO | Good progress feedback with section headers and counts. | - | N/A |
| R2 | INFO | Actionable messages. | - | N/A |
| R3 | INFO | User confirmation before file moves. | 921-927 | N/A |
| R4 | INFO | Consistent formatting. | - | N/A |
| R5 | INFO | N/A. | - | N/A |
| R6 | INFO | UAT mode support. | - | N/A |
| R7 | INFO | N/A. | - | N/A |
| R8 | INFO | N/A. | - | N/A |
| R9-R10 | INFO | N/A. | - | N/A |

**Summary**: 0 critical, 0 high, 3 medium, 6 low findings
**Action Items**:
1. (MEDIUM) Add error handling around manifest write so `execute()` can return `False` on failure.
2. (MEDIUM) Narrow the `except Exception` in `_prompt_exclusions` to specific types.
3. (MEDIUM) Consider path validation/warnings for external reference paths in `_prompt_additional_paths`.
4. (LOW) Consolidate `SKIP_DIRS` and `_NESTED_REPO_MARKERS` constants.

---

## File 6: `phases/phase_00_setup/tasks/task_005_repository_setup.py` (1083 lines)

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | INFO | `execute()` returns `True` on success (line 205-206), `False` on validation failure (line 200), and `True` if user chooses to continue (line 1062). | 48-207 | N/A |
| A2 | MEDIUM | Global mutable state: `CHECKS_PASS`, `CHECKS_FAIL`, `CHECKS_WARN` (lines 43-45) plus `_report_cache` and `_report_cache_file` (lines 871-872). These are module-level globals modified by multiple functions. If `execute()` were called concurrently, these would be corrupted. Thread-safety note is present (line 42). | 43-45, 77-79, 871-872 | Acceptable for single-threaded use. Consider encapsulating in a class for testability. |
| A3 | INFO | Paths constructed with `Path()`. | - | N/A |
| A4 | INFO | Dict access uses `.get()` throughout. | - | N/A |
| A5 | INFO | Type annotations consistent. | - | N/A |
| A6 | INFO | No concurrent operations (documented). | 42 | N/A |
| A7 | INFO | Handles missing agent manifest, missing audit menu, missing skills. | - | N/A |
| A8 | INFO | Boolean logic correct. | - | N/A |
| A9 | INFO | No off-by-one errors. | - | N/A |
| A10 | INFO | `/proc/cpuinfo` and `/proc/meminfo` opened with `with` statements. | 605, 718 | N/A |
| B1 | INFO | No bare `except`. | - | N/A |
| B2 | LOW | `_get_report_cache()` line 881: `except Exception:` -- overly broad. Should catch `json.JSONDecodeError` and `OSError`. | 881 | `except (json.JSONDecodeError, OSError):` |
| B3 | INFO | No silent swallowing -- fallback dict provided on exception. | 881-882 | N/A |
| B4 | INFO | No re-raised exceptions. | - | N/A |
| B5 | INFO | Recovery appropriate throughout. | - | N/A |
| B6 | LOW | `_show_summary()` line 1024: `report = json.loads(read_file(report_file))` -- no exception handling. If the report file is corrupt or missing, this will crash. | 1024 | Wrap in try/except with fallback to empty report. |
| B7 | INFO | Exception types correct. | - | N/A |
| B8 | INFO | No cleanup needed. | - | N/A |
| C1 | LOW | `from typing import ... Tuple` -- `Tuple` is used in `_verify_agents` and `_verify_skills` return types. All imports verified used. | 20 | N/A |
| C2 | INFO | No unused variables. | - | N/A |
| C3 | INFO | No unreachable code. | - | N/A |
| C4 | INFO | No commented-out code. | - | N/A |
| C5 | INFO | No vestigial functions. | - | N/A |
| C6 | INFO | No dead branches. | - | N/A |
| C7 | INFO | No obsolete compat code. | - | N/A |
| C8 | INFO | No debug code. | - | N/A |
| C9 | INFO | No redundant assignments. | - | N/A |
| C10 | INFO | No copy-paste artifacts. | - | N/A |
| D1-D8 | INFO | No stubs, no TODOs. | - | N/A |
| E1 | LOW | `_detect_os()` (lines 567-581) is a simplified duplicate of `task_001._detect_os()`. Documented in docstring. | 567-581 | Consider shared utility, but duplication is minor. |
| E2 | INFO | Reasonable complexity. | - | N/A |
| E3 | INFO | No string anti-patterns. | - | N/A |
| E4 | MEDIUM | Report file is written at line 87, then `_add_check` and `_update_report_capability` use an in-memory cache that is flushed at line 138. However, `_save_configuration` at line 944 re-reads the file. Between lines 87 and 138, the on-disk file and cache may be out of sync if anything reads the file before flush. The initial write (line 87) writes an empty report, then the cache lazily loads it -- this works, but the pattern is fragile. | 87, 138, 944 | Document the read-modify-write-flush pattern clearly. |
| E5 | INFO | Data structures appropriate. | - | N/A |
| E6 | LOW | Magic numbers: `15` for health check attempts (line 694), `50` GB storage threshold (line 790), `10` GB low storage (line 792), core count thresholds `8`/`4` (lines 618-622), RAM thresholds `32`/`16`/`8` (lines 748-754). | Various | Extract as named constants. |
| E7 | INFO | All functions are within reasonable length (the longest is `execute()` at ~160 lines). | - | N/A |
| E8 | INFO | No deep nesting. | - | N/A |
| E9 | INFO | Consistent patterns. | - | N/A |
| E10 | INFO | No unnecessary conversions. | - | N/A |
| F1 | INFO | `execute()` matches expected interface. | 48 | N/A |
| F2 | INFO | Writes `env-validation.json` and updates `project-config.json`. | 67 | N/A |
| F3-F4 | INFO | Returns `bool`. | - | N/A |
| F5 | INFO | N/A -- no LLM invocation. | - | N/A |
| F6 | INFO | N/A. | - | N/A |
| F7 | INFO | Memory recording (lines 172-196) includes system capabilities and git info. | 172-196 | N/A |
| F8 | INFO | N/A. | - | N/A |
| G1 | INFO | No path traversal. | - | N/A |
| G2 | LOW | `subprocess.run(["git", "remote", "add", "origin", remote_url], ...)` -- `remote_url` comes from user input (line 526). A malicious URL could contain shell metacharacters, but since `subprocess.run` with a list does not invoke a shell, this is safe. | 536-538 | N/A -- safe as-is. |
| G3 | INFO | No secrets handled. | - | N/A |
| G4 | INFO | N/A. | - | N/A |
| G5 | INFO | No file permission changes. | - | N/A |
| G6 | INFO | Logging safe. | - | N/A |
| H1 | INFO | Appropriate log levels. | - | N/A |
| H2 | INFO | Error messages include context. | - | N/A |
| H3 | INFO | Good progress with section headers and check results. | - | N/A |
| H4 | LOW | `_assess_gpu()` line 660-661: GPU detection failure on macOS silently sets `has_metal = True` and `gpu_name = "Unknown"`. No indication to user that detection failed. | 660-662 | Add a `logger.debug` note. Already present on line 659 actually. |
| H5 | INFO | N/A. | - | N/A |
| I1 | LOW | Hardcoded timeout `5` for all subprocess calls. Cloudflare test URL `"https://speed.cloudflare.com/"` hardcoded. | Various, 820 | Extract as constants. |
| I2 | INFO | Handles macOS, Linux, Windows for system capability detection. | - | N/A |
| I3 | INFO | Consistent config access. | - | N/A |
| I4 | INFO | Defaults are sensible. | - | N/A |
| J1 | INFO | Import ordering correct. | - | N/A |
| J2-J7 | INFO | Consistent patterns and docstrings. | - | N/A |
| K1-K5 | INFO | N/A -- no graph operations. | - | N/A |
| L1 | MEDIUM | Not fully idempotent: `_validate_git_remote` could fail if `origin` already exists from a previous run. The error message handles this case (line 546-548), but the check is recorded as `warn` not `pass`. | 536-548 | Check for existing remote before attempting `git remote add`. |
| L2 | INFO | Report is initialized fresh on each run. | 82-87 | N/A |
| L3 | INFO | Subprocess timeouts set (5s for git, 10s for system_profiler). | - | N/A |
| L4 | INFO | Graceful degradation: sandbox generation failure doesn't block. | 159-160 | N/A |
| L5 | INFO | N/A. | - | N/A |
| M1-M10 | INFO | N/A -- no LLM operations. | - | N/A |
| N1 | INFO | No circular imports. | - | N/A |
| N2 | INFO | No layer violations. | - | N/A |
| N3 | MEDIUM | `_save_configuration` uses `config['providers'].update(providers_config)` which could overwrite keys set by task_003. The comment on line 965-966 acknowledges this concern and the use of `update` (merge) is intentional, but `routing` and `ollama_enabled` from task_005 will overwrite any same-named keys from task_003. | 965-969 | Verify task_005's `providers_config` keys don't conflict with task_003's `providers` keys. |
| N4 | INFO | No god functions. | - | N/A |
| N5-N8 | INFO | Clean module boundaries. | - | N/A |
| O1 | INFO | `core.sandbox` is optional, handled with `try/except ImportError`. | 32-36 | N/A |
| O2-O7 | INFO | N/A. | - | N/A |
| P1-P9 | INFO | Not auditing test files. | - | N/A |
| Q1 | INFO | Report keys well-defined. | - | N/A |
| Q2 | INFO | Report size is bounded. | - | N/A |
| Q3-Q8 | INFO | N/A. | - | N/A |
| R1 | INFO | Good progress feedback. | - | N/A |
| R2 | INFO | Actionable messages for git and system issues. | - | N/A |
| R3 | INFO | Validation failure offers retry or continue options. | 1041-1064 | N/A |
| R4 | INFO | Consistent formatting. | - | N/A |
| R5 | INFO | N/A. | - | N/A |
| R6 | INFO | UAT mode support. | - | N/A |
| R7 | INFO | N/A. | - | N/A |
| R8 | LOW | `_handle_validation_failure()` has an infinite `while True` loop (line 1052) that only breaks on valid input. No `KeyboardInterrupt` handling. | 1052-1064 | Add `KeyboardInterrupt` handling or a max-retry count. |
| R9-R10 | INFO | N/A. | - | N/A |

**Summary**: 0 critical, 0 high, 4 medium, 8 low findings
**Action Items**:
1. (MEDIUM) Fix fragile report cache pattern -- document the read-modify-flush lifecycle.
2. (MEDIUM) Verify `providers_config` key overlap with task_003's `providers` section.
3. (MEDIUM) Address global mutable state (`CHECKS_PASS/FAIL/WARN`, `_report_cache`) -- consider encapsulating.
4. (MEDIUM) Handle `_validate_git_remote` idempotency for `origin` already-exists case.
5. (LOW) Add exception handling in `_show_summary()` for corrupt report file.

---

## Phase 00 Aggregate

| Metric | Count |
|--------|-------|
| Files audited | 6 |
| Total lines | ~5,281 |
| Critical | 0 |
| High | 4 |
| Medium | 23 |
| Low | 51 |
| Info | ~350+ |

### High-Severity Summary

| # | File | Check | Finding |
|---|------|-------|---------|
| H1 | task_002_provider_detection.py | G3 | API keys could leak into log output via exception messages containing config dicts |
| H2 | task_003_setup_wizard.py | A5 | `_run_wizard()` return type annotation incorrect -- returns `str` ("RESTART") not documented in `Optional[Dict]` |
| H3 | task_003_setup_wizard.py | E7 | `_run_wizard()` is 634 lines -- massive function length violation |
| H4 | task_003_setup_wizard.py | N4 | `_run_wizard()` is a god function handling all 10 wizard steps inline |

### Cross-File Patterns

1. **Duplicate `_detect_os()`**: Both `task_001` (line 189) and `task_005` (line 567) implement OS detection. The task_001 version is more detailed (distinguishes debian/redhat/arch). Extract to `core.utils.platform`.

2. **Duplicate Ollama utilities**: `task_002._check_ollama_host()`, `task_002._list_ollama_models()`, and `task_003._detect_ollama_models()` all make the same HTTP call to `/api/tags`. Extract to `core.utils.ollama` or `core.llm.ollama_utils`.

3. **Global mutable counters**: Both `task_001` and `task_005` use module-level global counters (`REQUIRED_TOTAL`, `CHECKS_PASS`, etc.) with manual reset. Consider using a dataclass or simple counter object.

4. **Magic strings and numbers**: Across all files, port numbers, timeout values, threshold constants, and URL strings are hardcoded. Extract the most frequently repeated ones as module-level constants.

5. **`secrets.json` management**: `task_002` reads and writes `secrets.json` from 3+ different functions with no coordination. A `SecretsManager` class would reduce the TOCTOU risk and improve testability.

6. **No `KeyboardInterrupt` handling**: None of the interactive tasks handle `Ctrl+C` gracefully. The pipeline would abort without cleanup messages.

7. **Consistent error handling**: Most exception handling is appropriate, but there are 4 instances of `except Exception` that should be narrowed to specific types.

### Top Recommendations (Priority Order)

1. **Refactor `_run_wizard()` in task_003** (HIGH): Split 634-line function into per-step helpers. This is the single largest code quality issue in Phase 00.

2. **Fix return type annotation** (HIGH): `_run_wizard()` returns `str` ("RESTART") but annotated as `Optional[Dict]`.

3. **Audit secret exposure paths** (HIGH): Ensure API keys in `env_vars` dicts cannot appear in exception messages or log output.

4. **Extract shared utilities** (MEDIUM): `_detect_os()`, Ollama HTTP helpers, and `SKIP_DIRS` constants are duplicated across files.

5. **Add failure returns to task_004** (MEDIUM): `execute()` always returns `True` -- should handle manifest write failures.

6. **Improve idempotency** (MEDIUM): Dashboard re-launch in task_001, secrets overwrite in task_002, and git remote add in task_005 have idempotency issues.

7. **Extract magic constants** (MEDIUM): Port numbers, timeouts, thresholds, and URL strings should be module-level constants.
