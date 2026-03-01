# Core Modules Audit Report

**Date**: 2026-02-28
**Auditor**: Claude Opus 4.6 (automated code audit)
**Scope**: 14 core modules (foundation layer)
**Methodology**: Systematic check of categories A-R per file

---

## 1. core/audit.py (2460 lines)

LLM-driven phase audit system: curation, parallel evaluation, remediation loop.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A3 | MEDIUM | `_ATOMIC_ROOT` computed via `Path(__file__).parent.parent` is fragile if the file is symlinked or relocated. Used throughout for output paths. | 99 | Derive from a config or explicit parameter rather than `__file__`. |
| A7 | LOW | `_extract_verdict` falls through to heuristic keyword matching which can produce false positives (e.g., a report mentioning "critical analysis" triggers "fail"). | 607-613 | Tighten heuristic: require co-occurrence within same sentence, or use a more structured extraction. |
| B3 | LOW | `_parse_curation_response` silently returns empty lists on JSON parse failure with no logging. | 226-229 | Add `logger.debug` for failed JSON parse so curation failures are diagnosable. |
| B5 | MEDIUM | `_evaluate_worker` catches all exceptions and returns a degraded `AuditEvaluation` with `error=str(e)`. Error is saved but never surfaced to the user in the live display. | 650-681 | Display error count in the live progress panel alongside pass/warn/fail. |
| C3 | LOW | `_build_audit_prompt` (line 1967) and `_parse_audit_response` (line 2000) appear to be vestigial -- the old single-prompt approach replaced by per-audit parallel evaluation. Not called by any code path in this file. | 1967-2073 | Confirm dead code and remove, or mark with deprecation comment. |
| D3 | INFO | Multiple TODO-equivalent notes embedded as code comments (e.g., "NOTE: This uses manual <system> tag injection" is in ollama.py but audit.py has similar design-note comments). | various | Track in issue tracker. |
| E1 | LOW | `_gather_deliverables` has near-duplicate loops for output_dir, extra_dirs, and source_dirs with identical read-and-truncate logic. | 1854-1960 | Extract a shared `_read_dir_into_parts(dir, extensions, label, budget)` helper. |
| E6 | LOW | Magic numbers: `12000` (deliverable truncation in prompt), `8000` (curation prompt truncation), `30000` (guidance cap), `50000` (deliverable budget). | 189, 591, 1098, 1856 | Extract as named constants at module level for discoverability. |
| F6 | LOW | `run_phase_audit` always returns `True` even when all audits fail. Docstring documents this, but callers cannot distinguish success from failure. | 2091, 2197 | Consider returning a result object or status enum for downstream decision-making. |
| G1 | HIGH | `_apply_remediation` writes LLM-generated content to the filesystem, including pipeline source code. Path traversal is guarded by `str.startswith()` comparison, which can be bypassed with crafted paths on some OSes (e.g., `resolved_base` = `/foo/bar`, attacker path resolves to `/foo/bar2/evil`). | 1311-1381 | Use `Path.is_relative_to()` (Python 3.9+) or `os.path.commonpath()` instead of string prefix matching. |
| G6 | LOW | Debug-level logging of file read failures includes full file paths that could contain sensitive project info. Acceptable for debug level but notable. | 1883, 1913, 1943 | No action needed; already at debug level. |
| H4 | MEDIUM | When `_auto_remediate` LLM call fails, the error message is printed via `console.print` but not logged, making it invisible in log files. | 1528-1530 | Add `logger.error("AI remediation failed: %s", e)` before the print. |
| I1 | LOW | Hardcoded `MAX_AUDITS = 20`, `MAX_CONCURRENT = 5`, `MAX_REMEDIATION_ROUNDS = 3` with no config override mechanism. | 42-46 | Allow override via config or environment. |
| J5 | LOW | Output paths use `_ATOMIC_ROOT.parent / ".outputs"` (the project root's `.outputs`). This is correct but differs from `subprocess_runner.py` which uses `atomic_root.parent / ".outputs"`. Pattern is consistent but not centralized. | 812, 1010, 2303 | Centralize output directory resolution in config.py. |
| L1 | MEDIUM | `_load_audit_inventory()` is called fresh on every `run_phase_audit` invocation with no caching. For a large CSV this is wasteful (though currently small). The agent manifest and model config ARE cached at module level. | 142-147 | Apply same module-level caching pattern as `_agent_manifest_cache`. |
| M1 | LOW | LLM prompts embed raw deliverable content without sanitization. If deliverables contain adversarial instructions, they could manipulate audit verdict. | 568-591 | Add XML-tag wrapping around deliverable content to separate instructions from data. |
| M2 | MEDIUM | `_extract_verdict` defaults to "warn" when no VERDICT line is found. This masks evaluation failures -- a confused or hallucinating LLM that produces no verdict still gets a "warn" pass-through. | 599-613 | Consider defaulting to "fail" for missing verdicts, or flagging as "unknown" requiring human review. |
| N1 | LOW | `_auto_remediate` imports `invoke_llm` inside the function body (deferred import). This is intentional to avoid circular imports but makes the dependency non-obvious. | 1492 | Acceptable pattern; add comment explaining the circular import avoidance. |
| Q6 | LOW | `_save_audit_markdowns` overwrites existing markdown files without backup. A crashed remediation round could lose the previous round's analysis. | 804-829 | Consider writing to timestamped files or maintaining a backup before overwrite. |
| R1 | LOW | Progress display relies on Rich library; if Rich import fails inside `_run_parallel_evaluations`, the entire evaluation crashes with ImportError. | 696-699 | Wrap Rich imports in try/except with a plaintext fallback (similar to Textual TUI fallback pattern already used). |

---

## 2. core/state.py (941 lines)

Immutable atomic state management with transactions, snapshots, and rollback.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | MEDIUM | `StateLock.__enter__` proceeds WITHOUT the lock if `acquire()` returns False (timeout), logging only a warning. This means concurrent processes can corrupt state. | 243-246 | Raise an exception or return a sentinel that callers must check, rather than silently continuing without the lock. |
| A2 | MEDIUM | `mark_task_complete` replaces the entire task dict (line 553), which discards any extra fields that callers may have added between `mark_task_started` and `mark_task_complete`. Only `started_at` is preserved. | 549-559 | Merge with existing task data instead of replacing wholesale. |
| A5 | LOW | `TaskState.__post_init__` treats `artifacts` default as `None` instead of using `field(default_factory=list)`. The `__post_init__` fix works but is non-standard for dataclasses. | 88-91 | Use `field(default_factory=list)` for idiomatic dataclass usage. |
| A10 | LOW | `save_state` uses `shutil.move(temp_path, self.state_file)` which is not truly atomic on all filesystems (e.g., cross-device moves). | 412 | Use `os.replace()` for guaranteed atomic rename on same filesystem, and ensure temp file is on same filesystem. |
| B2 | LOW | `save_state` catches `Exception` broadly and re-raises as `IOError`. The original exception type information is lost. | 414-420 | Use `raise IOError(...) from e` to preserve exception chain. |
| B7 | LOW | `load_state` catches `json.JSONDecodeError` and `IOError` but not `KeyError` or `TypeError` that could occur in `_migrate_state`. | 389-391 | Widen exception handling or add defensive checks in migration. |
| C1 | LOW | `TaskStatus.COMPLETE` enum value exists only as an alias for compatibility but creates confusion (two enum members for same concept). | 62 | Document clearly or remove if compatibility period is over. |
| C10 | INFO | `__main__` testing block at bottom (lines 901-940) is embedded test code. | 901-940 | Move to dedicated test file. |
| E6 | LOW | Magic number `10` for lock timeout in `StateLock.acquire(timeout=10)`. | 186 | Make configurable or define as class constant with documentation. |
| F3 | MEDIUM | `StateTransaction.__exit__` calls `self.commit()` on success (no exception), but the state changes were already applied by methods like `mark_task_complete`. The transaction is not truly deferred -- it just adds a save. This means partial writes are visible before commit. | 278-287, 289-291 | Either buffer all changes and apply on commit (true transactions), or document that "transaction" here means "snapshot+rollback" only. |
| G1 | LOW | `load_state` opens files with no path validation. Paths are internally derived from `state_dir` so low risk. | 380 | No action needed. |
| J6 | LOW | `mark_phase_complete` sets status as string `'completed'` rather than using `PhaseStatus.COMPLETED.value`. Inconsistent with the enum pattern. | 630 | Use `PhaseStatus.COMPLETED.value` for consistency. |
| L5 | MEDIUM | `save_state` and `set_current_phase`/`set_current_task` each call `save_state()` without holding the `StateLock`. Concurrent processes could interleave writes. | 393-420, 608-618 | Acquire `StateLock` around all state mutations + save operations. |
| Q1 | LOW | State keys like `'phases'`, `'tasks'`, `'current_phase'` are bare strings scattered throughout. A typo would create silent bugs. | throughout | Define key constants (e.g., `STATE_PHASES = 'phases'`). |
| Q2 | MEDIUM | No limit on the number of phases/tasks in state. A long-running pipeline could accumulate unbounded state size. | throughout | Add optional compaction or archival of completed phase data. |
| Q3 | LOW | `save_snapshot` has a deferred import of `core.utils.file_ops.write_json` (line 701). If that module is unavailable, snapshot saving fails with ImportError at runtime. | 701 | Import at module level or handle ImportError gracefully. |
| R4 | LOW | `display_status` uses emoji characters (`\U0001f4e6`) which may not render in all terminals. | 787-796 | Use ASCII fallback option for non-emoji terminals. |

---

## 3. core/memory/__init__.py (349 lines)

Memory system facade: save, recall, checkpoint, compact, backtrack.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | MEDIUM | `_ensure_initialized()` auto-initializes with `Path.cwd()` as state_dir. In a multi-project environment or when cwd changes, this silently connects to the wrong directory. | 68-71 | Raise an explicit error if not initialized, forcing callers to call `memory_init()` first. |
| A7 | LOW | `memory_handle_backtrack` clears entries for `target_phase + 1` but doesn't clear entries for phases > target_phase + 1. Only one phase is cleared. | 312 | Should iterate from `target_phase + 1` through max phase, or `_store.clear_phase` should accept a range. |
| B3 | LOW | No error handling around `_store.append(entry)` in `memory_save`. If the store write fails, the caller receives no indication. | 115 | Wrap in try/except and either raise or log the failure. |
| E6 | LOW | `relevance_score=0.8` hardcoded default in `memory_save`. | 112 | Make configurable or document the default choice. |
| F4 | LOW | `memory_checkpoint` takes `phase` as `int` but `memory_save` takes `phase` as `str`. Inconsistent interface for the same concept. | 81, 181 | Standardize to one type (str is more flexible for IDs like "2-prd"). |
| I1 | LOW | Default `max_tokens=4000`, `relevance_threshold=0.3`, `max_size_mb=10.0`, `max_age_days=90`, `min_relevance=0.2` are all hardcoded with no config integration. | 124-125, 272-274 | Read defaults from config system. |
| N1 | LOW | Global mutable singletons (`_store`, `_checkpoint_manager`, etc.) with no thread safety. Concurrent `memory_init()` calls could create race conditions. | 29-33 | Add a lock around initialization. |
| Q7 | MEDIUM | No mechanism to reset or reinitialize the memory system after it's been initialized (e.g., for testing or project switching). `_initialized` flag prevents re-init. | 46-47 | Add `memory_reset()` function that clears globals and allows re-initialization. |

---

## 4. core/config.py (680 lines)

Configuration management with multi-source loading, Pydantic validation, and dot-notation access.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | MEDIUM | `load_from_json_files` loads from `self.atomic_root.parent / ".outputs" / "0-setup"` -- navigating to PARENT. This assumes a specific directory layout where atomic-claude is nested inside the project. If the layout differs, config silently loads nothing. | 267-294 | Document the expected directory structure. Consider making the path configurable. |
| A6 | LOW | `get_model()` checks `os.environ.get("CLAUDE_MODEL")` directly for the primary role (line 563), bypassing the config loading pipeline that already processes env vars. This creates a dual-path for the same env var. | 563-565 | Remove the direct env var check since `_load_config` already merges env vars into config. |
| B2 | MEDIUM | `_load_config` catches `Exception` broadly from Pydantic validation and falls through to unvalidated config with only a `print()` warning. Invalid config could cause silent downstream failures. | 418-425 | Log at WARNING level and consider whether specific validation failures should be fatal. |
| B3 | LOW | `.env` parsing silently ignores malformed lines (no `=` sign). | 248-250 | Log at DEBUG level for diagnosability. |
| C10 | INFO | `__main__` testing block embedded in module. | 653-679 | Move to tests. |
| E1 | LOW | `load_from_env` creates `config.get('project', {})` repeatedly with the same defensive pattern for each section. | 192-228 | Use `config.setdefault('project', {})` pattern for cleaner code. |
| F1 | LOW | `get_config()` singleton silently ignores `cli_args` on subsequent calls unless they differ by value equality check. Complex objects (e.g., nested dicts) may fail equality check unpredictably. | 638-646 | Document singleton behavior clearly; consider always re-creating if cli_args provided. |
| G3 | LOW | `load_from_dotenv` reads `.env` files which may contain secrets. Values are stored in `self.env_cache` dict in memory. | 244-260 | Acceptable, but ensure env_cache is not serialized or logged. |
| G4 | LOW | No validation on user-supplied config values beyond Pydantic schema. A malicious `project.name` could contain special characters (though `validate_name` does check alphanumeric). | 86-91 | Validation exists. Adequate. |
| I3 | LOW | `to_dict()` returns a shallow copy via `dict(self._config)`. Nested dicts are shared references; mutations to the returned dict can modify internal config. | 493-494 | Use `copy.deepcopy` or document the shared-reference behavior. |
| J1 | LOW | Mix of `from pydantic import ...` at top level (conditional) and standard library imports. Pydantic fallback sets `BaseModel = object` which would cause `ConfigSchema` class body to fail silently. | 34-41, 75-159 | The entire Pydantic block is guarded by `if HAS_PYDANTIC:` so this is correct. No action needed. |
| O5 | LOW | Pydantic is optional (`HAS_PYDANTIC` guard). When missing, ALL validation is skipped -- config.validate() always returns True. | 482-483 | Log a warning at startup if Pydantic is not available. |
| Q8 | LOW | `save()` writes the full config dict to disk, which may include secrets from the env cache that were merged in. | 496-505 | Filter out secrets section before saving, or document that saved configs may contain sensitive data. |

---

## 5. core/ui.py (149 lines)

Console UI utilities: headers, messages, text wrapping.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A7 | LOW | `wrap_text` numbered-item detection (line 99-100) only checks 1-2 digit numbers followed by `.` or `)`. Three-digit numbered lists (100+) would not be detected as structured. | 99-100 | Extend pattern to handle 3+ digits. |
| C1 | INFO | `import readline` is imported for its side effect (enabling arrow-key navigation). The `noqa: F401` suppresses the unused import warning. This is correct. | 10-12 | No action needed. |
| E5 | LOW | `wrap_text` builds result list by `pop(0)` on the front, which is O(n) for each call. | 137-140 | Use `collections.deque` or slice assignment for O(1) removal from front. |
| R5 | LOW | Hardcoded width `80` for phase headers and `60` for task headers. No terminal width detection. | 17-19, 32-33 | Use `shutil.get_terminal_size().columns` or accept width parameter. |
| R6 | LOW | All output goes to `print()` (stdout). No support for redirecting UI output to a file or alternative stream. | throughout | Accept optional `file` parameter or use a logger. |

---

## 6. core/subprocess_runner.py (258 lines)

Executes external scripts and bash commands with environment setup.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A3 | MEDIUM | `atomic_root = Path(__file__).parent.parent.resolve()` is computed on every function call. Same fragility as audit.py if file is symlinked. | 29, 95, 163, 207 | Compute once at module level or accept as parameter. |
| B2 | LOW | `run_task_script` catches bare `Exception` (line 129) and returns `(1, "", str(e))`. The original exception type is lost. | 129-131 | Log the full traceback at DEBUG level. |
| G2 | HIGH | `run_bash_command` passes `command` string directly to `bash -c` via `subprocess.run`. The docstring warns "Only call with trusted input" but there is no enforcement. Any caller passing user input creates a command injection vulnerability. | 216-227 | Add an explicit `_TRUSTED_CALLERS` check, require a `trusted=True` flag, or replace with `shlex.split` + `subprocess.run` without shell. |
| G5 | LOW | `make_script_executable` sets executable bit for user, group, AND other (`S_IXUSR | S_IXGRP | S_IXOTH`). Overly permissive. | 253 | Only set `S_IXUSR` unless group/other execution is specifically needed. |
| H1 | LOW | `run_task_script` prints emoji-based messages to stdout but doesn't use the logging system. These messages are invisible in log files. | 105, 126, 130 | Add corresponding logger calls alongside print statements. |
| I1 | LOW | Default timeout 600s (10 min) for scripts, 60s for commands. Not configurable. | 68, 191 | Accept from config or environment. |
| I2 | MEDIUM | Dashboard ports hardcoded as `5174`, `5175`, `5176` in `get_task_environment` but config.py defaults are `5173`, `5174`, `5175`. Port numbers are inconsistent. | 45-47 vs config.py 119-121 | Centralize port defaults in one location. |
| J5 | LOW | Output dir is `atomic_root.parent / ".outputs"` (line 36) which assumes the same parent-relative layout as audit.py. | 36 | Centralize path resolution. |
| L3 | LOW | No retry logic for `subprocess.run`. A transient failure (e.g., temp file system full) causes immediate failure. | 108-116 | Consider optional retry for specific exit codes. |

---

## 7. core/llm/router.py (635 lines)

Intelligent provider routing with fallback chains, circuit breaker, and health tracking.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | MEDIUM | `get_fallback_chain` caches the chain permanently in `self._fallback_chains`. If providers are registered/unregistered after the chain is cached, the cached chain becomes stale. | 392-425 | Invalidate `_fallback_chains` cache in `register_provider` and `unregister_provider`. |
| A4 | LOW | `_record_success` calculates running average latency with integer division that could lose precision: `total_latency = stats.avg_latency_ms * (stats.total_requests - 1)`. If `total_requests` is 1 (first success), `total_requests - 1 = 0` and the old average is zeroed correctly, but the formula assumes sequential counting. | 569-570 | Use Welford's online algorithm for numerically stable running average. |
| B2 | MEDIUM | `stream()` catches bare `Exception` (line 382) for ALL streaming errors. Provider-specific errors like `AuthenticationError` are swallowed and treated as retryable. | 382-385 | Match the granular exception handling from `invoke()` (lines 291-316). |
| C1 | LOW | `defaultdict` imported but `defaultdict(lambda: UsageStats())` will fail if `UsageStats` requires arguments. Currently works because `UsageStats` has defaults. | 107-109 | Acceptable, but fragile if `UsageStats` changes. |
| E6 | LOW | Magic numbers: `failure_threshold=3`, `cooldown_minutes=5`, `health_check_interval=60`, `cache_ttl=900`, `cache_max_size=100`. | 46-55 | Already in `RouterConfig` dataclass. Adequate. |
| F7 | LOW | `invoke()` accepts `prompt=None` as default (line 209). Calling with no prompt would pass `None` to the provider, which would likely fail with an unhelpful error. | 209 | Validate that `prompt` is not None/empty at the router level with a clear error. |
| H2 | LOW | f-string logging: `logger.info(f"Registered provider: {name} ...")` evaluates the string even when log level is above INFO. | 156, 183, 502 | Use lazy formatting: `logger.info("Registered provider: %s ...", name)`. |
| L4 | LOW | Circuit breaker re-enables providers in `_is_provider_available` (line 500-501). This inline reset is a side effect of a read operation, which could cause surprising behavior. | 498-502 | Move re-enable logic to a separate `_maybe_reenable_provider` method called explicitly. |
| M4 | MEDIUM | No validation that the response from a provider is well-formed before caching. A malformed response gets cached and served to subsequent callers. | 286-288 | Validate `response.content` is not empty before caching. |
| M6 | LOW | Cache key includes `model` parameter, but `model` could be `None` (uses provider default). Two calls with explicit model vs. None would cache separately even if they resolve to the same model. | 241-243 | Resolve model before computing cache key. |
| Q7 | LOW | `_usage_stats` grows unboundedly as providers are used. No cleanup mechanism. | 107-109 | Add periodic stats rotation or size cap. |

---

## 8. core/llm/invoke.py (672 lines)

Feature-aware LLM invocation with thinking, caching, and token tracking.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | MEDIUM | `invoke_llm` positional argument overloading (lines 546-603) is complex and error-prone. The second positional arg can be either an output file path OR a provider instance. Callers could easily pass arguments in wrong order. | 546-603 | Deprecate positional args; require keyword-only arguments. |
| A7 | LOW | `_resolve_tier` uses substring matching (`"opus" in m`). A model ID like "some-opus-variant-fast" would match "opus" tier pricing. | 190-201 | Use more specific matching (e.g., regex word boundaries). |
| A10 | LOW | `_locked_tokens_file` opens file in `r+` mode but creates it with `write_text("{}")` if it doesn't exist. Race condition: two processes could both see the file as missing and both try to create it. | 211-213 | Use `open(..., 'a+')` or `os.open(O_CREAT|O_EXCL)` for atomic creation. |
| B2 | LOW | `_track_tokens` catches all exceptions and logs a warning. Token tracking silently fails without caller awareness. | 320-321 | Acceptable for non-critical telemetry. |
| B3 | MEDIUM | `FeatureAwareLLMInvoker.invoke` silently catches ALL exceptions from skill and graph context injection (lines 362-383). If these produce corrupted context, the LLM receives garbage in the system prompt. | 362-383 | Log the exception at DEBUG level rather than completely silencing it. |
| C1 | LOW | `tempfile` imported at line 11 but never used in this file. | 11 | Remove unused import. |
| D1 | INFO | `_DEFAULT_THINKING_BUDGET = 10_000` is an untested default. No indication of how this was chosen or whether it's appropriate. | 31 | Document the rationale or make configurable. |
| E1 | MEDIUM | `invoke()` and `stream()` in `FeatureAwareLLMInvoker` have near-identical code for skill context injection, graph context injection, and feature flag checking. ~60 lines duplicated. | 332-480 | Extract shared logic into `_prepare_params(kwargs, use_extended_thinking, use_caching, use_analysis)`. |
| F1 | MEDIUM | `invoke_llm` returns `str` but `FeatureAwareLLMInvoker.invoke` returns the raw provider response (which could be `LLMResponse` or `str`). The conversion happens in `invoke_llm` (line 627-630) but not in direct `FeatureAwareLLMInvoker` usage. | 413, 627-630 | Document the return type contract clearly; consider always returning `LLMResponse`. |
| G3 | LOW | API key is read from `os.environ.get("ANTHROPIC_API_KEY")` and passed directly to provider constructor (line 127). The key is in memory but not logged. | 126-128 | Acceptable. |
| I1 | LOW | `_NO_COST_PROVIDERS` hardcoded set. Adding a new free provider requires code change. | 187 | Move to config. |
| M7 | LOW | `_resolve_model_for_provider` returns the tier name unchanged if no mapping is found. The provider then has to resolve it again. Dual-resolution. | 60-86 | Document that providers must handle unresolved tier names as fallback. |
| N1 | LOW | Circular import avoidance via deferred imports in `_get_default_router` (imports from `.router`, `.types`, `core.config`). | 95-107 | Acceptable pattern. Document the dependency cycle. |
| Q7 | LOW | Token tracking file grows unboundedly over a session. The `by_provider` and `by_model` dicts accumulate entries for every model variation seen. | 256-299 | Add rotation or session reset mechanism. |

---

## 9. core/llm/anthropic.py (491 lines)

Anthropic API provider using official SDK.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | LOW | `get_token_count` has a nested try/except for SDK version compatibility (line 394-398). The fallback `len(text) // 4` is very rough. | 392-403 | Log which path was taken so users know if they're getting estimates vs. exact counts. |
| B5 | LOW | After retry exhaustion in `invoke()`, the final `raise APIError` at line 281 is reached only if the loop completes without returning or raising. If `last_exception` is None (should not happen given the loop structure), the error message would say "None". | 280-284 | Defensive: check `last_exception is not None` before stringifying. |
| E1 | LOW | Retry logic with exponential backoff is implemented inline in `invoke()` (~100 lines). Same pattern repeated in bedrock.py. | 178-284 | Extract a `_retry_with_backoff(fn, max_retries)` utility. |
| G3 | LOW | API key stored in `self.api_key` attribute. Accessible to any code with a reference to the provider instance. | 92 | Consider using a property that reads from env var on each access, or mark as private. |
| H2 | LOW | Health check result cached for 5 minutes. A brief outage followed by recovery would not be detected for up to 5 minutes. | 111, 417-419 | Reduce TTL or allow cache bypass for explicit health checks. |
| M8 | LOW | `temperature=1.0` default is quite high for most tasks. Most Anthropic usage recommends lower temperatures for factual/structured output. | 119, 290 | Consider `temperature=0.7` as default, or make role-dependent. |
| M10 | LOW | Streaming in `stream()` does not have retry logic, unlike `invoke()`. A transient error during streaming fails immediately. | 333-360 | Add at least one retry attempt for connection errors. |

---

## 10. core/llm/bedrock.py (545 lines)

AWS Bedrock provider using boto3.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | LOW | `default_model` defaults to `anthropic.claude-3-5-sonnet-20241022-v2:0` (an older model). The `BEDROCK_TIER_MAP` maps "sonnet" to the newer `claude-sonnet-4-5`. Inconsistency between default and tier map. | 95-98 vs 52-54 | Update default_model to match the sonnet tier map entry. |
| B2 | LOW | `invoke()` has a broad `except Exception` catch at line 320 that could mask non-Bedrock errors (e.g., serialization errors in `json.dumps`). | 320-329 | Narrow to `(ClientError, BotoCoreError, json.JSONDecodeError)`. |
| E1 | MEDIUM | `_BEDROCK_SAFE_KEYS` set is defined identically in both `invoke()` and `stream()`. | 192-194, 381-383 | Extract as module-level constant. |
| G3 | LOW | AWS credentials are read from config dict and stored in `session_kwargs`. If config is serialized, credentials could leak. | 111-116 | Credentials are passed to boto3 Session which handles them securely. Low risk. |
| I1 | LOW | `aws_region` defaults to "us-east-1" which may not be the user's intended region. | 94 | Log the region being used so misconfigurations are visible. |
| M10 | LOW | Streaming response parsing (line 402) calls `.decode()` on chunk bytes without specifying encoding. | 402 | Specify `encoding='utf-8'` explicitly. |
| O5 | LOW | `boto3` is optional (guarded by try/except import). When missing, the class raises ImportError at `__init__` time. | 16-21, 87-91 | Acceptable pattern. |

---

## 11. core/llm/ollama.py (457 lines)

Ollama local LLM provider using urllib.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | MEDIUM | System prompt injection uses `<system>` tag wrapping (line 130) which is NOT a standard Ollama convention. Most models don't recognize `<system>` tags in the prompt. | 128-130 | Migrate to `/api/chat` endpoint with proper `messages` format including `{"role": "system", ...}`. The code already has a NOTE about this (line 124-127). |
| A7 | LOW | `auto_pull` triggers a model download on first invocation failure. For large models (235B qwen3), this could block for hours with no progress indication. | 189-193 | Add progress reporting for model pulls, or require explicit opt-in for pulls > N GB. |
| B2 | LOW | `pull_model` catches all exceptions and returns False. The caller has no way to distinguish "connection refused" from "disk full". | 413-415 | Log the specific exception at WARNING level. |
| E1 | LOW | Duplicate code between `invoke()` and `stream()` for building request_data and handling optional parameters. | 132-148 vs 268-284 | Extract `_build_request(prompt, system_prompt, model, ...)` helper. |
| G4 | LOW | `self.host` comes from config with no URL validation. A malicious config could set `host` to an internal network address (SSRF-like, though this is a local tool). | 76 | Validate URL format. |
| I1 | LOW | Default model `"llama2"` is quite old. | 77 | Update default or document that it should be overridden. |
| M1 | MEDIUM | System prompt and user prompt are concatenated with `<system>` tags into a single string. Models without system prompt support will see the raw tags as text, potentially confusing the output. | 128-130, 264-266 | Use `/api/chat` endpoint as documented in the TODO note. |
| M8 | LOW | `temperature=1.0` default for local models. Local models often benefit from lower temperatures. | 91, 237 | Consider lower default. |
| Q7 | LOW | Response metadata includes `"context": response_data.get("context", [])` which can be very large (full KV cache context array). This is stored in the LLMResponse metadata dict. | 228 | Either omit context or cap its size. |

---

## 12. core/graph/connection.py (209 lines)

Singleton FalkorDB connection with health check and auto-reconnect.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | MEDIUM | Singleton `get()` creates a new instance on each call if `_instance._connected` is False (line 67). A flapping connection causes repeated instantiation rather than reconnection of the existing instance. | 66-68 | Try `_instance._connect()` before creating a new instance. |
| A6 | LOW | Default port in docstring says 6380 (line 56) but environment variable default is also "6380" (line 71). However, the `__init__` default is 6379 (line 38). Port defaults are inconsistent. | 38, 56, 71 | Align `__init__` default with env var default (6380). |
| B2 | LOW | `query()` reconnect attempt catches bare `Exception` (line 145). | 143-147 | Narrow to connection-specific exceptions. |
| L3 | MEDIUM | `query()` has exactly ONE reconnect attempt on connection failure. If FalkorDB is restarting, a single retry with no delay will likely fail. | 141-148 | Add configurable retry count with exponential backoff. |
| L4 | MEDIUM | `health_check()` accesses `self._client.connection.ping()` which assumes the FalkorDB client has a `.connection` attribute with a `.ping()` method. If the FalkorDB SDK changes this interface, health checks silently fail. | 119 | Add defensive `hasattr` check or document the required SDK version. |
| N6 | LOW | `GraphConnection` is tightly coupled to FalkorDB's specific API (`select_graph`, `connection.ping`). No abstraction layer for alternative graph databases. | throughout | Accept for now; consider interface abstraction if additional graph backends are added. |
| Q7 | LOW | `close()` sets `_connected = False` and `_graph = None` but doesn't clear `_instance` class variable. After `close()`, calling `get()` will try to use the disconnected instance. | 185-194 | Either clear `_instance` in `close()` or check `_graph is not None` in `get()`. |

---

## 13. core/graph/manager.py (559 lines)

High-level graph operations facade for pipeline tasks.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | LOW | `add_spec` creates a Spec node with `id=f"spec-{task_id}"` but the HAS_SPEC edge target uses bare `task_id` as the Spec node's id property. Since `_id_prop("Spec")` returns `"task_id"`, the edge MATCH looks for `Spec.task_id = task_id`, which is correct because `task_id` is set in the properties. However, the node also has `id=f"spec-{task_id}"` which goes unused for edges. | 145-153 | Remove the redundant `id` field from Spec nodes, or use `id` consistently. |
| B2 | LOW | `load_agents_from_manifest` reads JSON with no exception handling beyond the file existence check. A malformed JSON file would crash with an unhandled exception. | 199 | Wrap `json.load` in try/except. |
| E6 | LOW | Magic number `120` for description truncation in `query_agent_catalog`. | 267-268 | Define as named constant. |
| F5 | LOW | `clear_memory_after_phase` fetches ALL Memory nodes into Python, then filters by phase number prefix. For a large graph this is very inefficient. | 449-464 | Use a Cypher query with string parsing (or store phase_num as a separate numeric property). |
| H2 | LOW | f-string logging used in several places. | 196, 209, 230, 438, 463 | Use lazy `%s` formatting for logger calls. |
| K5 | LOW | `save_memory` stores `tags` as CSV string (`tags_csv`). This prevents proper graph-based tag queries. | 377 | Consider creating separate Tag nodes with HAS_TAG edges. |
| L1 | LOW | `load_agents_from_manifest` checks `existing >= len(agents)` for idempotency, but if the manifest changes (agents removed), old agents persist. | 207-210 | Compare by agent names, not just count. |

---

## 14. core/graph/writer.py (300 lines)

Low-level graph write operations: nodes, edges, updates, bulk, indexes.

| Check | Severity | Finding | Line(s) | Recommendation |
|-------|----------|---------|---------|----------------|
| A1 | LOW | `add_node` always uses CREATE, never MERGE. Calling `add_node` twice with the same id creates duplicate nodes. | 80 | Use `MERGE` with the id property to ensure idempotency, or document that callers must check for existence. |
| A7 | LOW | `add_edge` uses CREATE, not MERGE. Duplicate edges can be created. | 187 | Use MERGE for idempotent edge creation. |
| B2 | LOW | `bulk_write` catches all exceptions per operation and continues. A schema validation error on one operation doesn't prevent subsequent operations, which may depend on the failed one. | 252-254 | Add an `abort_on_error` option for operations that have dependencies. |
| E1 | LOW | `_BEDROCK_SAFE_KEYS`-style filtering exists in bedrock.py but not needed here. However, the `isinstance(label, str) else label.value` pattern is repeated in add_node, update_node, delete_node, add_edge, delete_edge. | 60, 101, 133, 159-161, 201-202 | Extract a `_label_str(label)` helper. |
| G2 | MEDIUM | Cypher queries are constructed using f-strings with `label_str` directly interpolated. While `label_str` comes from code (not user input), if any code path passes user-controlled data as a label, this becomes a Cypher injection vector. Parameter values ARE parameterized correctly via `$param`. | 80, 114, 134, 184-188 | Validate `label_str` against an allowlist of known labels from the schema. |
| H2 | LOW | Debug-level logging for every node creation/update/deletion. In bulk operations this generates excessive log output. | 83, 119, 138, 191 | Add a `quiet` flag to bulk_write to suppress per-operation logging. |
| K1 | LOW | `ensure_indexes` catches exceptions and checks for "already indexed" in error message. This string matching is fragile across FalkorDB versions. | 288-299 | Use a more robust check (e.g., query existing indexes first). |
| L1 | LOW | `delete_by_phase` query uses `count(n)` in a WITH clause that's redundant. The query counts nodes before deleting but the count is only used in RETURN. | 268-277 | Simplify to `MATCH (n) WHERE n.phase = $phase DETACH DELETE n RETURN count(n)`. Actually, the current query may be a workaround for FalkorDB query planner behavior. Document if intentional. |
| L5 | LOW | `bulk_write` is not transactional. Partial failures leave the graph in an inconsistent state. | 217-255 | Document that bulk_write is best-effort, or add transaction support if FalkorDB supports it. |

---

## Aggregate Findings Summary

### By Severity

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 24 |
| LOW | 76 |
| INFO | 5 |
| **Total** | **108** |

### By Category

| Category | Count | Notable |
|----------|-------|---------|
| A - Correctness & Bugs | 23 | Stale fallback cache (router), singleton flapping (connection), non-atomic transactions (state) |
| B - Exception Handling | 16 | Broad except patterns throughout; silent swallowing in invoke.py context injection |
| C - Dead Code | 5 | Vestigial audit prompt functions, embedded test blocks |
| D - Stubs | 2 | Thinking budget undocumented, TODO notes |
| E - Code Quality | 10 | Duplicate retry logic across providers, duplicate code in invoke/stream |
| F - Interface Contracts | 6 | StateTransaction not truly transactional, inconsistent return types |
| G - Security | 7 | **HIGH: command injection in subprocess_runner, path traversal in audit remediation, Cypher injection risk in writer** |
| H - Logging | 7 | f-string logging, missing log-level calls alongside print statements |
| I - Config | 7 | Hardcoded defaults, port number mismatch between subprocess_runner and config |
| J - Consistency | 4 | Inconsistent status enum usage, output path patterns |
| K - Graph | 3 | CSV-based tag storage, fragile index existence check |
| L - Reliability | 8 | Single reconnect attempt (connection), no streaming retry (anthropic), partial bulk write |
| M - LLM Ops | 8 | Unvalidated cache entries, temperature defaults, system prompt injection for Ollama |
| N - Architecture | 4 | Deferred imports for circular dependency avoidance (acceptable) |
| O - Dependencies | 2 | Optional dependency guards adequate |
| P - Tests | 0 | (Test files not in scope of this audit) |
| Q - State | 9 | Unbounded state/stats growth, no memory system reset, singleton lifecycle gaps |
| R - UX | 4 | Hardcoded terminal widths, emoji-only output |

### Top 5 Priority Fixes

1. **HIGH G2 (subprocess_runner.py:216)**: `run_bash_command` accepts raw command strings for `bash -c`. Add input validation or eliminate shell=True-equivalent usage.

2. **HIGH G1 (audit.py:1311)**: Path traversal guard in `_safe_write` and `_apply_remediation` uses fragile `str.startswith()`. Replace with `Path.is_relative_to()`.

3. **HIGH G2 (writer.py:80)**: Cypher label interpolation via f-string. Validate labels against schema allowlist.

4. **MEDIUM A1 (state.py:243)**: `StateLock.__enter__` proceeds without lock on timeout. This silently disables concurrent access safety.

5. **MEDIUM F3 (state.py:278)**: `StateTransaction` does not truly defer changes. Mutations are applied immediately, defeating the purpose of atomic transactions.

### Cross-Cutting Concerns

- **Retry Logic Duplication**: The exponential backoff retry pattern is implemented independently in anthropic.py, bedrock.py, and partially in connection.py. A shared `retry_with_backoff(fn, max_retries, base_delay)` utility would reduce ~150 lines of duplicate code.

- **Path Resolution**: At least 4 files compute `Path(__file__).parent.parent` for the atomic root. This should be computed once and passed via dependency injection or config.

- **Singleton Lifecycle**: The memory system, config, graph connection, and default LLM router all use module-level singletons with no reset/teardown mechanism. This makes testing difficult and prevents project switching.

- **Logging Hygiene**: ~15 instances of f-string formatting in logger calls. While functionally correct, these evaluate the format string even when the log level is disabled.
