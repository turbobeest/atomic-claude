# Re-Audit: Core Modules (2026-02-28)

Audit of 14 core modules against categories A-R. Only CRITICAL, HIGH, and MEDIUM severity findings are reported. Each finding includes a specific, reproducible trigger scenario.

---

## 1. core/audit.py

### core/audit.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| B (Input Validation) | MEDIUM | `_write_phase_file` in `memory/store.py` constructs filenames from `entry.task_id` without sanitizing path separators or special characters, but `audit.py` itself constructs file paths from `phase_num` (an int) and audit data in `_save_audit_markdowns`. The `_audit_report_filename` function (around line 795) uses `audit_id` from CSV data to build filenames. If the CSV contains an `audit_id` with path separator characters (e.g., `../malicious`), the filename could escape the audit directory. | ~795-830 | Load an `AUDIT-INVENTORY.csv` with an `audit_id` value containing `../` (e.g., `../../etc/exploit`). The `_audit_report_filename` function would produce a filename that, when joined with the audit output directory, writes outside the intended directory. | Sanitize `audit_id` when constructing filenames -- strip or replace path separators (`/`, `\`, null bytes). Alternatively, validate audit_id format at CSV load time. |
| N (Concurrency) | MEDIUM | `_run_parallel_evaluations` uses `ThreadPoolExecutor` with `MAX_CONCURRENT=5` threads, each calling `invoke_llm`. The `_track_tokens` function in `invoke.py` uses file locking for token tracking, but the `_evaluate_worker` function captures exceptions broadly and returns an `AuditEvaluation` with `error` set. If one worker throws an unexpected exception that is not caught by the ThreadPoolExecutor's `future.result()`, it could be silently lost. However, `future.result()` on line 788 re-raises exceptions. The actual issue: the `evaluations` list is pre-allocated as `[None] * len(configs)` and indexed by `future_to_idx`, which is safe. | 688-791 | Not a bug -- reviewed and found no actionable defect. | No action needed. |

After thorough review, the path traversal concern for `_audit_report_filename` is the only concrete finding. The `_safe_write` and `_apply_remediation` functions already have `is_relative_to` guards (lines 1311-1322, 1343-1382), which were recently added and are correctly implemented.

**Net finding: 1 MEDIUM**

---

## 2. core/state.py

### core/state.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| N (Concurrency) | HIGH | `StateLock.release()` deletes the lock file (line 239) after releasing the flock. In a multi-process scenario, Process A holds the lock, Process B is waiting. Process A releases the flock (line 225) then deletes the lock file (line 239). Between the flock release and the unlink, Process B acquires the flock on the same file descriptor. But then Process A deletes the file. Process B now holds a lock on a deleted inode. Process C comes along, creates a NEW lock file (different inode), and acquires its flock successfully -- now B and C both believe they hold the lock, violating mutual exclusion. | 220-241 | Run two concurrent `save_state()` calls from separate processes (e.g., two pipeline tasks running in parallel). The race window between `flock LOCK_UN` and `unlink` allows a third process to create a new lock file and acquire a lock on a different inode, breaking mutual exclusion. | Remove the lock file deletion in `release()` (line 237-241). Lock files should persist. The flock on the file provides the mutual exclusion; deleting the file creates the TOCTOU race. Alternatively, hold the fd open and only unlink on process exit, or simply never unlink. |
| G (Error Handling) | MEDIUM | `save_state()` acquires `StateLock` via the context manager, which raises `TimeoutError` on failure (line 245). However, `mark_task_complete`, `mark_task_started`, `mark_task_failed`, `set_current_phase`, `set_current_task`, and `mark_phase_complete` all call `save_state()`. If the lock times out, the `TimeoutError` propagates up to the caller unhandled, potentially crashing the pipeline mid-task. | 406-436, 510-648 | Call `save_state()` when another process holds the state lock for more than 10 seconds (the default timeout). The `TimeoutError` propagates uncaught through `mark_task_complete` etc. | Either catch `TimeoutError` in `save_state()` and log a warning (degraded but non-crashing), or document the expected behavior and ensure callers handle it. |
| P (Data Integrity) | MEDIUM | `snapshot()` on line 688 hardcodes `status=PhaseStatus.IN_PROGRESS` for all phases regardless of their actual status. The phase dict on disk may have `status: "completed"` or `status: "not_started"`, but the snapshot always creates `PhaseState` with `IN_PROGRESS`. When restored, all phases appear IN_PROGRESS. | 686-705 | Create a snapshot of a state that has some phases marked `completed`. Restore from the snapshot. The restored state will have all phases as `in_progress` instead of `completed`, because line 689 hardcodes `PhaseStatus.IN_PROGRESS`. Note: `PhaseState.to_dict()` (line 141-143) actually strips the status if it equals `NOT_STARTED`, so the data loss is partial -- but `completed` status IS lost. | Read the actual status from `phase_data.get('status', 'in_progress')` instead of hardcoding `PhaseStatus.IN_PROGRESS` on line 689. |

---

## 3. core/memory/__init__.py

### core/memory/__init__.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| G (Error Handling) | MEDIUM | `memory_handle_backtrack` on line 315 calls `_store.clear_phase(target_phase + 1)`. Inside `MemoryStore.clear_phase()` (store.py line 471), the phase string is parsed with `int(entry.phase.split('-')[0])`. If any memory entry has a `phase` value that does not follow the `N-name` format (e.g., just `"setup"` or an empty string), `int()` will raise `ValueError`, causing `clear_phase` to crash and lose the entries that should have been kept (the list comprehension is half-evaluated). | 315 (init), store.py:471 | Save a memory entry with `phase="custom"` (no numeric prefix), then call `memory_handle_backtrack(0)`. The `int("custom".split('-')[0])` raises `ValueError`, crashing the backtrack operation. | Wrap the int conversion in a try/except within the list comprehension, defaulting non-parseable phases to 0 (or excluding them from deletion). |

---

## 4. core/config.py

### core/config.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| B (Input Validation) | MEDIUM | `load_from_json_files()` on lines 267-268 navigates to `self.atomic_root.parent / ".outputs" / "0-setup" / "project-config.json"`. The `atomic_root` is user-controlled (passed to constructor or defaults to `Path.cwd()`). The code does not validate that the loaded JSON data is well-formed beyond catching `JSONDecodeError`. If `extracted` contains unexpected nested types (e.g., `project` is a string instead of a dict), the `_deep_merge` would overwrite the defaults dict with a string, causing subsequent `config.get("project.name")` to fail with a non-obvious error since the string is not iterable as a dict. | 262-296 | Place a `project-config.json` file at the expected path with `{"extracted": {"project": "not-a-dict"}}`. Then call `config.get("project.name")`. The `_deep_merge` replaces the `project` dict with the string `"not-a-dict"`. The next `get("project.name")` call on line 456 checks `isinstance(value, dict)`, finds a string, and returns the default -- so it gracefully degrades. | Reviewed further: this actually degrades gracefully (returns default). Not a functional bug. |

No actionable findings meeting the severity criteria.

---

## 5. core/ui.py

### core/ui.py -- Audit

No actionable findings. This module contains only display/formatting functions with no security surface, state management, or error-prone logic.

---

## 6. core/subprocess_runner.py

### core/subprocess_runner.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| A (Security) | MEDIUM | `run_bash_command()` passes `command` to `bash -c` (line 228). The null byte check on line 211 is a good addition but insufficient as a general defense. The docstring warns callers to use `shlex.quote()`, but there is no enforcement. Any caller that passes user-influenced data without quoting enables shell injection. The function itself cannot fix this without knowing which parts are variable, but the API design encourages unsafe usage. | 186-248 | A caller passes `run_bash_command(f"echo {user_input}", ...)` where `user_input` contains `; rm -rf /`. The null byte check passes, and the shell executes the injected command. This requires a caller bug, but the API shape makes it easy to misuse. | Consider adding a variant that accepts a list of arguments (avoiding shell=True semantics entirely), or at minimum add runtime validation that the command does not contain obvious shell metacharacters when the caller signals it should be safe. |

Note: The null byte rejection (line 211) and the security docstring (lines 199-201, 224-225) are correct recent additions. The `run_task_script` function properly uses `["bash", str(script_path)]` without shell interpretation of the path, which is safe.

---

## 7. core/llm/router.py

### core/llm/router.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| N (Concurrency) | MEDIUM | `_record_failure()` updates `self._failures[provider_name]` (lines 626-641) outside the `_stats_lock`. The `_stats_lock` only protects `_usage_stats` updates (lines 620-623). The `_failures` dict and `ProviderFailure` dataclass fields (`failure_count`, `last_failure`, `disabled_until`) are modified without synchronization. If two threads concurrently fail on the same provider, both read `failure_count`, increment, and write back -- one increment is lost. This could delay circuit breaker activation. | 612-641 | Two threads invoke the same provider concurrently, both fail. Both read `failure.failure_count=2` (threshold is 3), both increment to 3 and set `disabled_until`. The lost increment means the circuit breaker fires at the correct time (both set it), but the count is wrong (3 instead of 4). More critically, if `failure_threshold=3` and count is 1, two concurrent failures could both read 1, both write 2, and the provider is never disabled despite 3 total failures. | Move `_failures` updates inside the `_stats_lock` context, or use a separate lock for failure tracking. |
| L (Caching) | MEDIUM | `get_fallback_chain()` caches the chain in `self._fallback_chains[role]` on first call (line 452). If providers are registered or unregistered after the chain is cached, the cache is never invalidated. The chain will reference providers that no longer exist (or miss newly registered ones). | 420-453 | Register provider "A" for role "primary". Call `get_fallback_chain("primary")` -- caches `["A"]`. Then register provider "B" for "primary". Call `invoke(role="primary")` -- uses cached chain `["A"]`, never tries "B". If "A" is unregistered, the cached chain contains a dangling reference, though `_is_provider_available` will filter it out. The real impact: newly registered providers are invisible for roles that have been queried. | Invalidate `_fallback_chains` in `register_provider()` and `unregister_provider()`. Add `self._fallback_chains.clear()` to both methods. |

---

## 8. core/llm/invoke.py

### core/llm/invoke.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| P (Data Integrity) | MEDIUM | `_locked_tokens_file()` opens the file with `"r+"` mode (line 213). If the file exists but is empty (0 bytes), `fh.read()` returns `""`, and `json.loads("")` raises `json.JSONDecodeError`. The `raw.strip()` check on line 270 handles this: `json.loads("") if "".strip()` evaluates to `dict(_empty_data)` because `"".strip()` is falsy. However, if the file contains only whitespace (e.g., a single newline from a truncated write), `" \n".strip()` is also falsy, so it falls through correctly. This is actually handled correctly. | 268-270 | N/A -- reviewed and found the handling is correct. | No action needed. |
| B (Input Validation) | MEDIUM | `invoke_llm()` on line 596 attempts to read `prompt_or_file` as a file path. The `Path(str(prompt_or_file)).exists()` check (line 597) will stat arbitrary paths. If `prompt_or_file` is a very long string, `Path()` construction may raise `OSError` (ENAMETOOLONG), which is correctly caught on line 601. However, if the string happens to match an existing file path (e.g., user passes a prompt that starts with `/etc/passwd`), the file content is read and used as the prompt instead. | 594-604 | Call `invoke_llm("/etc/passwd")`. Since `/etc/passwd` exists and is a file, the function reads its content and sends it to the LLM as the prompt, instead of treating the string as prompt text. This is by design for the file-path mode, but it means callers must be aware that any string that resolves to an existing file will be treated as a file path. | Document this behavior prominently. If the intent is to always pass prompt text, callers should use the `prompt=` keyword argument which takes priority (line 591). Consider adding a `prompt_is_file=False` flag to make the behavior explicit. |

No actionable findings meeting MEDIUM+ criteria after review (both issues above are either handled correctly or by-design behavior).

---

## 9. core/llm/anthropic.py

### core/llm/anthropic.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| A (Security) | MEDIUM | `invoke()` on line 174 calls `request_kwargs.update(kwargs)`. Any caller-supplied `**kwargs` can override previously set keys including `model`, `messages`, `max_tokens`, and `temperature`. A caller could pass `messages=[{"role": "user", "content": "injected"}]` in kwargs to completely replace the message array, bypassing the prompt parameter. | 154-174 | Call `provider.invoke("safe prompt", messages=[{"role": "assistant", "content": "I will now..."}])`. The `request_kwargs.update(kwargs)` on line 174 overwrites the `messages` key, replacing the user prompt entirely. | Filter `kwargs` through an allowlist of safe additional parameters before merging, or merge kwargs first and then set required keys to prevent override. E.g., set `messages` and `model` AFTER the `update(kwargs)` call. |

---

## 10. core/llm/bedrock.py

### core/llm/bedrock.py -- Audit

No actionable findings. The Bedrock provider correctly filters kwargs through `_BEDROCK_SAFE_KEYS` allowlist (lines 200-202) with the `key not in request_body` guard, preventing override of already-set keys. This is notably safer than the Anthropic provider's approach. The retry logic, error handling, and model resolution are all correctly implemented.

---

## 11. core/llm/ollama.py

### core/llm/ollama.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| A (Security/SSRF) | MEDIUM | The `host` configuration is taken from `self.config.get("host", "http://localhost:11434")` (line 76) and used directly in URL construction (line 152: `f"{self.host}/api/generate"`). If a user or config file sets `host` to an internal network address (e.g., `http://169.254.169.254` for AWS metadata), the provider will make HTTP requests to that address. This is an SSRF vector if the host value comes from untrusted input. | 76, 152, 288, 367, 398, 425 | Set `OLLAMA_HOST` environment variable (or config) to `http://169.254.169.254/latest/meta-data/` and invoke the Ollama provider. The `urllib.request.urlopen` call will fetch AWS instance metadata. | Validate the host URL against an allowlist of acceptable schemes and hosts (localhost, 127.0.0.1, or explicitly configured internal hosts). At minimum, reject non-http(s) schemes and link-local/metadata addresses. |

---

## 12. core/graph/connection.py

### core/graph/connection.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| G (Error Handling) | MEDIUM | `GraphConnection.get()` reads `ATOMIC_GRAPH_PORT` from the environment and casts it to `int` (line 71). If the env var contains a non-numeric value (e.g., `ATOMIC_GRAPH_PORT=abc`), `int("abc")` raises `ValueError`, which is not caught by the `except Exception` on line 79 (it IS caught, since `ValueError` is a subclass of `Exception`). The error message will be `FalkorDB unavailable at localhost:abc: invalid literal for int()` which is misleading -- it suggests a connection failure rather than a configuration error. | 71 | Set `ATOMIC_GRAPH_PORT=notanumber` in the environment and call `GraphConnection.get()`. The `ValueError` from `int()` is caught by the generic `except Exception` and wrapped in `GraphUnavailableError`, making it look like a connection failure instead of a config error. | Add explicit validation: `try: _port = int(...)` with a catch for `ValueError` that raises a more descriptive error like `GraphUnavailableError("Invalid ATOMIC_GRAPH_PORT: must be an integer")`. |

---

## 13. core/graph/manager.py

### core/graph/manager.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| P (Data Integrity) | MEDIUM | `load_agents_from_manifest()` on line 208 compares `existing >= len(agents)` to decide if agents are already loaded. If some agents were loaded from a previous version of the manifest with MORE agents, and the manifest is updated with FEWER agents, the check `existing >= len(agents)` returns True and skips loading -- the new agents from the updated manifest are never added, and removed agents persist. | 206-209 | Load a manifest with 50 agents. Later, update the manifest to have 40 agents (removing 10 and adding none). Call `load_agents_from_manifest()`. Since `existing(50) >= len(agents)(40)`, loading is skipped entirely. The graph retains stale agent data. | Use a content-based check (e.g., compare a hash of agent names/IDs) rather than a count-based check, or always upsert (MERGE instead of CREATE) to handle manifest changes idempotently. |
| B (Input Validation) | MEDIUM | `clear_memory_after_phase()` on line 453 parses `m.get("phase", "0").split("-")[0]` to extract phase number. If a Memory node's `phase` property is stored as an integer (not a string) in FalkorDB, calling `.split("-")` on an integer raises `AttributeError`. | 449-456 | Store a Memory node in FalkorDB with `phase` property as integer `2` instead of string `"2-prd"`. Call `clear_memory_after_phase(1)`. The `int(m.get("phase", "0").split("-")[0])` calls `.split()` on integer `2`, raising `AttributeError`, which is caught by the `except (ValueError, AttributeError)` on line 456. | The existing `except (ValueError, AttributeError)` on line 456 handles this case correctly. No action needed. |

Net finding for manager.py: 1 MEDIUM (the idempotency/staleness issue).

---

## 14. core/graph/writer.py

### core/graph/writer.py -- Audit

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| A (Security) | HIGH | `update_node()` on lines 123-128 constructs SET clauses using property keys directly from the `updates` dict: `f"n.{key} = ${param_name}"`. The property VALUES are parameterized (safe), but the property KEYS are interpolated directly into the Cypher string. If `updates` contains a key with Cypher injection characters (e.g., `"status} SET n.admin = true WITH n MATCH (m) SET m.{x"`), it would inject arbitrary Cypher. This is exploitable if any caller passes user-controlled property names. | 123-128 | Call `writer.update_node("Task", 1, {"status} RETURN n//": "x"})`. The generated Cypher becomes `MATCH (n:Task {id: $node_id}) SET n.status} RETURN n// = $u0 RETURN n`, which either errors or executes injected clauses depending on the payload. Property keys come from code (not user input) in the current codebase, but this is a latent injection vector. | Validate property keys against a strict allowlist regex (e.g., `^[a-zA-Z_][a-zA-Z0-9_]*$`) before interpolation. Apply the same validation in `add_node()` (line 92) and `add_edge()` (line 192) where keys are also interpolated. |
| A (Security) | MEDIUM | `add_node()` on line 92 also interpolates property keys directly into Cypher: `f"{key}: ${param_name}"`. Same injection vector as `update_node()` but through CREATE rather than SET. | 88-96 | Call `writer.add_node("Task", {"id": 1, "title": "test", "description": "test", "status}) RETURN n//": "injected"})`. The Cypher string includes the injected key verbatim. | Same fix: validate all property keys with a regex allowlist before string interpolation. |
| A (Security) | MEDIUM | `add_edge()` on line 192 interpolates relationship property keys: `f"{key}: ${param_name}"`. Same pattern as the node operations. | 190-196 | Call `writer.add_edge("DERIVED_FROM", "Finding", 1, "Source", 2, {"name} RETURN r//": "x"})`. The key is interpolated into the Cypher CREATE clause. | Same fix: validate relationship property keys. |
| N (Concurrency) | MEDIUM | `ensure_indexes()` on lines 307-308 constructs index creation Cypher by interpolating `label` and `prop` from `INDEX_DEFINITIONS`: `f"CREATE INDEX FOR (n:{label}) ON (n.{prop})"`. These values come from the hardcoded `schema.py` constants, so this is not exploitable. However, `ensure_indexes()` for fulltext indexes (line 316) uses `f"'{f}'"` to quote field names, and `f"'{label}'"` to quote the label. If any schema constant contained a single quote, this would break. | 301-321 | Not exploitable with current schema constants, which are all simple alphanumeric strings. | No action needed -- schema constants are code-controlled. Note for future: if schema becomes dynamic, these need parameterized queries. |

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 11 |

### HIGH Findings (2)

1. **core/state.py line 239** -- `StateLock.release()` deletes the lock file after releasing flock, creating a TOCTOU race that breaks mutual exclusion in multi-process scenarios. Fix: stop deleting the lock file.

2. **core/graph/writer.py lines 123-128** -- Cypher property KEY injection in `update_node()`. Property keys from the `updates` dict are interpolated directly into Cypher strings without validation. Fix: validate keys against `^[a-zA-Z_][a-zA-Z0-9_]*$`.

### MEDIUM Findings (11)

1. **core/audit.py ~line 795** -- Audit report filenames constructed from CSV `audit_id` without path separator sanitization.
2. **core/state.py lines 406-436** -- `TimeoutError` from `StateLock` propagates uncaught through state mutation methods.
3. **core/state.py line 689** -- `snapshot()` hardcodes `PhaseStatus.IN_PROGRESS` for all phases, losing actual phase status on snapshot/restore.
4. **core/memory/store.py line 471** -- `clear_phase()` crashes with `ValueError` on memory entries with non-numeric phase prefixes.
5. **core/subprocess_runner.py line 228** -- `run_bash_command()` API encourages shell injection by accepting raw command strings for `bash -c`.
6. **core/llm/router.py lines 626-641** -- Circuit breaker failure tracking not protected by lock, allowing lost increments under concurrency.
7. **core/llm/router.py lines 420-453** -- Fallback chain cache never invalidated when providers are registered/unregistered.
8. **core/llm/anthropic.py line 174** -- `request_kwargs.update(kwargs)` allows callers to override critical request parameters including `messages`.
9. **core/llm/ollama.py line 76** -- SSRF vector: Ollama host URL from config/env used without validation against internal/metadata addresses.
10. **core/graph/writer.py lines 88-96** -- Cypher property key injection in `add_node()` (same pattern as HIGH #2).
11. **core/graph/writer.py lines 190-196** -- Cypher property key injection in `add_edge()` (same pattern as HIGH #2).

### Files With No Actionable Findings

- **core/config.py** -- No actionable findings. Config loading degrades gracefully on malformed input.
- **core/ui.py** -- No actionable findings. Display-only module.
- **core/llm/invoke.py** -- No actionable findings. Token tracking locking is correct; prompt-as-file behavior is by design.
- **core/llm/bedrock.py** -- No actionable findings. Kwargs filtered through `_BEDROCK_SAFE_KEYS` allowlist with override prevention.
- **core/graph/connection.py** -- One minor error message quality issue (env var parsing) but no functional bug.

### Verification of Recent Fixes

The following recently added security/reliability fixes were verified as correctly implemented:

1. **Path traversal guards (`is_relative_to`)** in `audit.py` `_safe_write()` (line 1317) and `_apply_remediation()` (lines 1351, 1365, 1373) -- **Correct**. Both the output target and canonical targets are validated independently.

2. **Null byte rejection** in `subprocess_runner.py` `run_bash_command()` (line 211) -- **Correct**. Rejects `\x00` before passing to `bash -c`.

3. **StateLock improvements** -- Partially correct. The acquire/release logic and context manager `TimeoutError` raising (line 245) are good additions. However, the lock file deletion in `release()` introduces the TOCTOU race documented as HIGH #1.

4. **Cypher label allowlists** in `writer.py` `_validate_label()` (lines 36-43) -- **Correct**. Labels are validated against the `NodeLabel` enum. Relationship types are validated via `validate_relationship()`. These prevent label injection.

5. **Schema validation** in `writer.py` `add_node()` -- **Correct**. Properties are validated against `REQUIRED_PROPERTIES` and `VALID_VALUES` before Cypher execution. However, the property KEY injection issue (HIGH #2) is a separate vector not covered by schema validation.
