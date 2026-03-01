# Re-Audit 2: Core Modules (2026-02-28)

Second-pass audit of 14 core modules against categories A-R. Verifies fixes from the first re-audit, then identifies any remaining or newly introduced CRITICAL, HIGH, and MEDIUM findings. Every finding includes a specific, reproducible trigger scenario.

**Previous audit (reaudit-core-modules.md)** reported 0 CRITICAL, 2 HIGH, 11 MEDIUM. This re-audit verifies those fixes and searches for anything missed.

---

## Verification of Previously Reported Fixes

All 13 previously reported findings have been reviewed against the current code:

| # | Previous Finding | Status | Evidence |
|---|------------------|--------|----------|
| H1 | state.py: StateLock.release() deletes lock file (TOCTOU race) | **FIXED** | Lines 237-240: comment explicitly states "Lock file intentionally NOT deleted" and unlink is removed. |
| H2 | writer.py: Cypher property KEY injection in update_node() | **FIXED** | `_validate_property_key()` (line 40-46) with regex `^[a-zA-Z_][a-zA-Z0-9_]*$` is called in `add_node()` (line 104), `update_node()` (line 140), `add_edge()` (line 208). |
| M1 | audit.py: Filename from CSV audit_id without path sanitization | **FIXED** | Line 801: `re.sub(r"[^a-zA-Z0-9_-]+", "-", ev.audit_id.replace("\x00", "")).strip("-")` sanitizes audit_id. |
| M2 | state.py: TimeoutError from StateLock propagates uncaught | **FIXED** | Lines 440-441: `except TimeoutError: logger.error(...)` catches and logs, skipping the save. |
| M3 | state.py: snapshot() hardcodes PhaseStatus.IN_PROGRESS | **FIXED** | Line 694: `PhaseStatus(phase_data.get('status', 'in_progress'))` reads actual status from phase_data. The default `'in_progress'` only applies when the key is absent. |
| M4 | memory/store.py: clear_phase() crashes on non-numeric phase | **FIXED** | Lines 471-475: `_parse_phase_num()` wraps `int()` in try/except, defaults to 0. |
| M5 | subprocess_runner.py: run_bash_command() shell injection API | **MITIGATED** | Lines 187-228: `reject_shell_meta` parameter added with `_SHELL_META_RE` check. Null byte rejection on line 219. Docstring warns callers. |
| M6 | router.py: Circuit breaker failure tracking not under lock | **FIXED** | Lines 626-647: `_record_failure()` now operates entirely within `self._stats_lock` context. |
| M7 | router.py: Fallback chain cache never invalidated | **FIXED** | Lines 158, 188: `self._fallback_chains.clear()` called in both `register_provider()` and `unregister_provider()`. |
| M8 | anthropic.py: kwargs override critical request parameters | **FIXED** | Lines 174-176 (invoke), 333-335 (stream): `_PROTECTED_KEYS` set filters out `model`, `messages`, `max_tokens`, `temperature`, `system` before merging. |
| M9 | ollama.py: SSRF via unchecked host URL | **FIXED** | Lines 86-120: `_validate_host()` checks scheme (http/https only), blocks metadata IPs and link-local addresses. |
| M10 | writer.py: add_node() key injection | **FIXED** | Same as H2 -- `_validate_property_key()` called at line 104. |
| M11 | writer.py: add_edge() key injection | **FIXED** | Same as H2 -- `_validate_property_key()` called at line 208. |

---

## New Findings

### 1. core/audit.py

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| F1 | P (Data Integrity) | MEDIUM | `_audit_report_filename()` sanitizes `audit_id` but does not guard against the result being empty after sanitization. If `audit_id` consists entirely of special characters (e.g., `"../../"`), the `re.sub(r"[^a-zA-Z0-9_-]+", "-", ...).strip("-")` produces an empty string. The resulting filename becomes `-<safe_name>.md` or just `.md`, which is either a hidden file or a confusing collision. | 801-803 | Load an `AUDIT-INVENTORY.csv` where one row has `audit_id` set to `"../../"`. After sanitization: `re.sub(...)` produces `"-"`, `.strip("-")` produces `""`. `safe_name` for `audit_name` also sanitized. Filename becomes `"-.md"` or `"-some-name.md"`. While not a security issue (path traversal is blocked), multiple rows with all-special-char IDs produce filename collisions, silently overwriting each other's reports. | Add a fallback: if `safe_id` is empty after sanitization, use `"unknown-{hash}"` or raise an error. |

No other findings meeting MEDIUM+ criteria.

---

### 2. core/state.py

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| F2 | P (Data Integrity) | HIGH | `StateTransaction.__exit__()` calls `self.commit()` on the success path (line 285). However, if `self.commit()` itself raises an exception (e.g., `IOError` from `save_state()` when the disk is full, or `TimeoutError` before the recent fix turned it into a logged skip), the exception propagates out of `__exit__`. The transaction is left in a half-committed state: in-memory mutations from `mark_task_complete(auto_save=False)` have been applied but never persisted, and `self.committed` is never set to `True`. On the next call or process restart, the state on disk does not match what the caller believes happened. More critically, the return value `False` on line 286 does NOT suppress this new exception, so the caller sees the `IOError` rather than any original exception context. | 277-286 | Use a `StateTransaction` context manager. Inside the `with` block, call `txn.mark_task_complete()` (succeeds, mutates in-memory state). The block exits normally. `__exit__` calls `commit()` which calls `save_state()`. If `save_state()` raises `IOError` (disk full), the caller gets `IOError`. The in-memory state now shows the task as completed but the on-disk state does not. If the process continues and another `save_state()` later succeeds, the task is persisted. But if the process crashes, the completion is lost while downstream code already acted on it. | Wrap `self.commit()` in a try/except within `__exit__`. On commit failure, call `self.rollback()` to undo in-memory mutations, then re-raise so the caller knows the transaction failed atomically (not half-applied). |

No other new findings.

---

### 3. core/memory/__init__.py

No actionable findings. All functions guard with `_ensure_initialized()`. The `memory_handle_backtrack` `clear_phase` crash was fixed in `store.py` (verified above, M4).

---

### 4. core/config.py

No actionable findings. Config loading degrades gracefully on malformed input. The `_deep_merge` + `get()` pattern handles unexpected types without crashing.

---

### 5. core/ui.py

No actionable findings. Display-only module with no security surface, state management, or error-prone logic.

---

### 6. core/subprocess_runner.py

No new actionable findings. The `reject_shell_meta` opt-in flag and null byte rejection (M5 mitigation) are correctly implemented. The core design (passing strings to `bash -c`) is inherent to the module's purpose.

---

### 7. core/llm/router.py

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| F3 | N (Concurrency) | MEDIUM | `_is_provider_available()` (lines 512-538) reads and resets `failure.disabled_until` and `failure.failure_count` without holding `_stats_lock`. When the cooldown expires, lines 534-535 set `failure.disabled_until = None` and `failure.failure_count = 0`. If two threads enter `_is_provider_available` concurrently for the same provider whose cooldown just expired, both will execute the reset. This is benign on its own (both set to 0/None). However, a third thread concurrently executing `_record_failure()` (which IS under `_stats_lock`) could increment `failure_count` to 1 between the two resets -- the second reset then clobbers it back to 0, losing a legitimate failure. | 512-538, 618-647 | Thread A calls `_is_provider_available("p1")`, sees cooldown expired, sets `failure_count = 0`. Before Thread A returns, Thread B calls `_record_failure("p1")` under `_stats_lock`, increments `failure_count` to 1. Thread C then calls `_is_provider_available("p1")`, enters the cooldown-expired branch (still sees old `disabled_until` from before Thread A's write propagated), resets `failure_count` back to 0. The failure from Thread B is lost. | Move the cooldown-expiry reset into a method that acquires `_stats_lock`, or check `_is_provider_available` under the lock. |

---

### 8. core/llm/invoke.py

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| F4 | P (Data Integrity) | MEDIUM | `_locked_tokens_file()` context manager (lines 204-235) acquires an exclusive file lock and yields the file handle. The caller (`_track_tokens`) reads, modifies, seeks to 0, truncates, and writes back. However, if `json.loads(raw)` on line 270 raises `json.JSONDecodeError` (e.g., corrupted file from a previous crash that wrote partial JSON), the exception propagates out of the `with _locked_tokens_file(tokens_file) as fh:` block. The lock is released, but the corrupted file remains. Every subsequent LLM call will hit the same `JSONDecodeError`, and token tracking is permanently broken for the session. | 268-270 | Kill the process (SIGKILL) while `_track_tokens` is writing to the tokens file (between `fh.truncate()` on line 318 and `fh.write()` on line 319). On next invocation, the file contains partial/empty JSON. `json.loads(raw)` on line 270 raises `JSONDecodeError`. This is caught by the outer `except Exception` on line 320, which logs a warning. On the NEXT call, the same corrupt file triggers the same error, permanently disabling token tracking. | When `json.loads` fails on a non-empty file, reset to `_empty_data` (treat corruption as "start fresh") and log a warning. This self-heals rather than permanently failing. Currently the outer `except` on line 320 prevents a crash, but it also prevents the data from being repaired since the corrupt file is never overwritten. |

---

### 9. core/llm/anthropic.py

No new actionable findings. The `_PROTECTED_KEYS` fix correctly prevents kwargs override in both `invoke()` and `stream()`.

---

### 10. core/llm/bedrock.py

No actionable findings. The `_BEDROCK_SAFE_KEYS` allowlist with `key not in request_body` guard is correctly implemented in both `invoke()` and `stream()`.

---

### 11. core/llm/ollama.py

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| F5 | A (Security/SSRF) | MEDIUM | `_validate_host()` checks the hostname against `_BLOCKED_HOSTS` and `_BLOCKED_HOST_RE` but does not resolve DNS. An attacker can bypass the SSRF check by using a hostname that resolves to a blocked IP. For example, setting `host` to `http://metadata.attacker.com:11434` where `metadata.attacker.com` has a DNS A record pointing to `169.254.169.254`. The `urlparse` check only examines the string hostname, not the resolved IP. | 100-120 | Set Ollama host config to `http://evil.example.com:11434` where `evil.example.com` DNS-resolves to `169.254.169.254`. `_validate_host()` passes (hostname is not in `_BLOCKED_HOSTS`, doesn't match `_BLOCKED_HOST_RE`). The `urlopen` call connects to `169.254.169.254` and fetches metadata. | Add DNS resolution check: resolve the hostname to IP addresses and validate those IPs against the blocked ranges. Alternatively, if the deployment environment does not expose Ollama config to untrusted users, document the trust boundary. Note: this is a defense-in-depth concern -- the host value typically comes from a config file or env var controlled by the system administrator. |

---

### 12. core/graph/connection.py

No actionable findings. The singleton pattern with `_lock` is thread-safe. The auto-reconnect in `query()` is a reasonable best-effort mechanism. The `ATOMIC_GRAPH_PORT` parsing issue from the previous audit (misleading error message) is not a functional bug.

---

### 13. core/graph/manager.py

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| F6 | P (Data Integrity) | MEDIUM | `add_spec()` on lines 143-153 creates a Spec node with `id = f"spec-{task_id}"` but then creates the `HAS_SPEC` edge from `Task` (identified by `task_id`) to `Spec` (also identified by `task_id` -- not `spec_id`). Since `_id_prop("Spec")` returns `"task_id"` (from `_NODE_ID_PROPERTY` in writer.py line 24), the edge MATCH clause looks for `(b:Spec {task_id: $to_id})` where `$to_id` is the raw `task_id`. This works correctly because the Spec node is created with `task_id: task_id` (inherited from `spec_data` or set explicitly). However, the `id` property (`"spec-{task_id}"`) is set but never used for edge resolution -- it exists only as metadata. This is architecturally confusing but functionally correct. | 143-153 | Not a functional bug. The edge resolution uses `task_id` which matches correctly. | No action needed. Architecture note for future maintainers. |

The previously reported `load_agents_from_manifest()` staleness issue (count-based idempotency check, previous M-finding from first audit's #13) remains present but was not in the list of fixes to verify. Repeating it here:

| # | Cat | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|---|-----|----------|---------|---------|------------------|----------------|
| F7 | P (Data Integrity) | MEDIUM | `load_agents_from_manifest()` line 208 uses `existing >= len(agents)` as an idempotency check. This is a count-based comparison that fails when the manifest is updated (agents added or removed). If the manifest shrinks, loading is skipped entirely; if agents are replaced (same count, different names), stale data persists. | 206-209 | Update the agent manifest: remove 5 agents and add 3 different ones (net count decreases by 2). Call `load_agents_from_manifest()`. Since `existing_count(old) >= len(agents)(new)`, loading is skipped. The graph retains the 5 removed agents and never gets the 3 new ones. | Use MERGE (upsert) instead of CREATE, or compare a hash/set of agent names rather than a count. |

---

### 14. core/graph/writer.py

No new actionable findings. The `_validate_property_key()` fix (H2, M10, M11) correctly guards all three interpolation points: `add_node`, `update_node`, and `add_edge`. The `_validate_label()` function correctly validates node labels against the schema enum.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 5 |

### HIGH Findings (1)

1. **F2 -- core/state.py lines 277-286**: `StateTransaction.__exit__()` calls `commit()` on the success path but does not handle `commit()` failures. If `save_state()` raises (e.g., disk full), in-memory mutations are left applied but not persisted, creating a split-brain state. On commit failure, the transaction should `rollback()` to restore the pre-transaction in-memory state before re-raising.

### MEDIUM Findings (5)

1. **F1 -- core/audit.py lines 801-803**: `_audit_report_filename()` can produce empty or colliding filenames when `audit_id` consists entirely of special characters after sanitization.

2. **F3 -- core/llm/router.py lines 512-538**: Circuit breaker cooldown-expiry reset in `_is_provider_available()` races with `_record_failure()` because the reset runs outside `_stats_lock`, potentially clobbering a concurrent failure increment.

3. **F4 -- core/llm/invoke.py lines 268-270**: Corrupted `session-tokens.json` file causes permanent token tracking failure. The outer exception handler prevents crashes but never repairs the file, so every subsequent call re-triggers the same error.

4. **F5 -- core/llm/ollama.py lines 100-120**: SSRF hostname validation can be bypassed via DNS rebinding (hostname resolving to blocked IP). Defense-in-depth concern; the host config is typically admin-controlled.

5. **F7 -- core/graph/manager.py lines 206-209**: `load_agents_from_manifest()` count-based idempotency check fails when the manifest is updated (agents added/removed/replaced). Previously reported, still unfixed.

### Files With No Actionable Findings

- **core/memory/__init__.py** -- All previous issues fixed. Clean.
- **core/config.py** -- Degrades gracefully on malformed input. Clean.
- **core/ui.py** -- Display-only module. Clean.
- **core/subprocess_runner.py** -- Previous mitigation (`reject_shell_meta`) correctly implemented. No new issues.
- **core/llm/anthropic.py** -- `_PROTECTED_KEYS` fix correctly applied. Clean.
- **core/llm/bedrock.py** -- `_BEDROCK_SAFE_KEYS` allowlist correctly applied. Clean.
- **core/graph/connection.py** -- Thread-safe singleton. Clean.
- **core/graph/writer.py** -- All property key injection fixes verified correct. Clean.

### Previous Fixes Verified Correct

All 13 findings from the first re-audit have been verified as correctly fixed or mitigated. The TOCTOU race fix in `StateLock`, the property key validation in `GraphWriter`, the `_PROTECTED_KEYS` in `AnthropicProvider`, the SSRF validation in `OllamaProvider`, and all other fixes are properly implemented. No regressions detected.
