# Task Code Audit Checklist

**Purpose**: Systematic audit of every task file in Atomic Claude 2.0 to eliminate bugs,
dead code, stubs, inefficiencies, and technical debt accumulated across 10+ refactorings.

**Scope**: 87 files (75 tasks + 10 orchestrators + 2 orchestration modules) + cross-cutting concerns

**Process**: One file at a time, in order. Every check applied. Findings recorded per-file.
Categories A-L are per-file checks. Categories M-R are cross-cutting concerns evaluated per-file where applicable.

---

## Audit Categories

### A. CORRECTNESS & BUGS

- [ ] **A1. Return value correctness** — Does the function return the expected type? Are all return paths covered? Does it return `True`/`False` correctly for success/failure?
- [ ] **A2. State mutation safety** — Does it modify `state` dict correctly? Are required keys always present before access? Any `KeyError` risk?
- [ ] **A3. File path construction** — Are paths built with `os.path.join()` or `Path()`? Any string concatenation that breaks cross-platform? Hardcoded paths?
- [ ] **A4. Dictionary/list access** — Any unguarded `dict[key]` that should be `dict.get(key)`? Index-out-of-range risks?
- [ ] **A5. Type mismatches** — Are function signatures honored by callers? Any `str` where `int` expected? `None` where `dict` expected?
- [ ] **A6. Race conditions** — File operations without locking? Concurrent state writes? Dashboard sync races?
- [ ] **A7. Edge case handling** — Empty inputs? Missing files? Empty directories? First-run scenarios? No LLM provider available?
- [ ] **A8. Boolean logic errors** — Inverted conditions? `and`/`or` precedence issues? Short-circuit evaluation side effects?
- [ ] **A9. Off-by-one errors** — Loop boundaries? Slice indices? Phase/task numbering (0-indexed vs 1-indexed)?
- [ ] **A10. Resource leaks** — Open files not closed? Missing `with` statements? Subprocess handles not cleaned up?

### B. EXCEPTION HANDLING

- [ ] **B1. Bare `except:`** — Flag every bare except. Must specify exception type. NEVER swallow `SystemExit`/`KeyboardInterrupt`.
- [ ] **B2. Overly broad `except Exception:`** — Should catch specific exceptions. What actually fails here? `OSError`? `ValueError`? `json.JSONDecodeError`?
- [ ] **B3. Silent exception swallowing** — `except: pass` or `except Exception: pass` — the worst pattern. Must at minimum log.
- [ ] **B4. Exception context loss** — `raise X` should be `raise X from e` to preserve traceback chain.
- [ ] **B5. Error recovery logic** — Does the except block actually recover? Or does it just pretend the error didn't happen?
- [ ] **B6. Missing exception handling** — Operations that CAN fail but have NO try/except: file I/O, JSON parsing, network calls, subprocess execution.
- [ ] **B7. Exception type correctness** — Does `except ValueError` actually catch what's thrown? Mismatch between raised and caught types?
- [ ] **B8. Cleanup in finally** — Are temp files, locks, connections cleaned up regardless of exception path?

### C. DEAD CODE & UNUSED CODE

- [ ] **C1. Unused imports** — Imports at top of file that are never referenced in the body.
- [ ] **C2. Unused variables** — Variables assigned but never read. Especially `result = ...` that's never returned or used.
- [ ] **C3. Unreachable code** — Code after `return`, `raise`, `sys.exit()`. Dead branches after always-true/always-false conditions.
- [ ] **C4. Commented-out code** — Blocks of code in `# comments`. Either delete or explain why preserved.
- [ ] **C5. Vestigial functions** — Functions defined but never called from anywhere in the codebase.
- [ ] **C6. Dead conditional branches** — `if` conditions that can never be true given the program flow. Feature flags that are always on/off.
- [ ] **C7. Obsolete compatibility code** — Workarounds for bugs that were fixed. Shims for old APIs that no longer exist.
- [ ] **C8. Leftover debug code** — `print("DEBUG")`, `breakpoint()`, `import pdb`, temporary logging.
- [ ] **C9. Redundant assignments** — Variable assigned, then immediately reassigned. `x = None; x = compute()`.
- [ ] **C10. Copy-paste artifacts** — Code copied from another task that references wrong phase/task numbers, wrong variable names, or wrong paths.

### D. STUBS & INCOMPLETE IMPLEMENTATIONS

- [ ] **D1. `pass` in non-abstract methods** — Function body is just `pass`. Is this intentional (abstract base) or a forgotten stub?
- [ ] **D2. `return None` / `return {}` / `return []` stubs** — Functions that return empty results instead of actual computation.
- [ ] **D3. TODO/FIXME/HACK/XXX comments** — Unresolved work items left in code.
- [ ] **D4. Placeholder strings** — `"TODO"`, `"placeholder"`, `"implement me"`, `"not yet"` in string literals.
- [ ] **D5. Hardcoded mock data** — Test data or example data embedded in production code. Should use actual computation or configuration.
- [ ] **D6. `NotImplementedError` raises** — Methods that explicitly declare they're not implemented.
- [ ] **D7. Feature-gated dead code** — Code behind `if False:`, `if 0:`, `if FEATURE_FLAG:` where the flag is always False.
- [ ] **D8. Skeleton functions** — Functions with docstrings but minimal/no implementation body.

### E. CODE QUALITY & EFFICIENCY

- [ ] **E1. Duplicate logic** — Same computation done multiple times within the file or across files. Should be extracted to shared utility.
- [ ] **E2. Unnecessary complexity** — Nested loops/conditions that could be simplified. Over-engineered abstractions for simple operations.
- [ ] **E3. String building anti-patterns** — Repeated `+` concatenation in loops instead of `join()` or f-strings.
- [ ] **E4. Repeated file I/O** — Same file read/written multiple times when once would suffice.
- [ ] **E5. Inefficient data structures** — List where set/dict would be O(1). Linear scan where index lookup works.
- [ ] **E6. Magic numbers/strings** — Unexplained numeric literals or string constants. Should be named constants.
- [ ] **E7. Function length** — Functions over 50 lines. Should be decomposed into smaller, testable units.
- [ ] **E8. Deep nesting** — More than 3 levels of indentation. Refactor with early returns, guard clauses, or extracted functions.
- [ ] **E9. Inconsistent patterns** — Does this task follow the same patterns as sibling tasks? Different error handling? Different state access?
- [ ] **E10. Unnecessary type conversions** — `str(str_var)`, `list(list_var)`, `dict(dict_var)` on already-correct types.

### F. INTERFACE CONTRACT COMPLIANCE

- [ ] **F1. Function signature match** — Does the task's `execute()` function match what the orchestrator expects? Correct parameters?
- [ ] **F2. State contract** — Does the task read the state keys it needs? Does it write the state keys downstream tasks expect?
- [ ] **F3. Output contract** — Does the task produce the output files/artifacts that downstream tasks consume?
- [ ] **F4. Return value contract** — Does the task return `True` for success and `False` for failure consistently?
- [ ] **F5. LLM invocation contract** — Are LLM calls using the correct provider chain? Correct model selection? Proper prompt formatting?
- [ ] **F6. Agent contract** — Is the correct agent selected? Does the agent ID match the manifest? Are agent capabilities matched to task needs?
- [ ] **F7. Memory contract** — Are memory saves/recalls using the correct keys? Is dual-write (file + graph) properly invoked?
- [ ] **F8. Audit integration** — Do phase_audit tasks properly invoke the audit framework? Are results correctly reported?

### G. SECURITY & SAFETY

- [ ] **G1. Path traversal** — Can user/LLM input construct paths outside intended directories? `../` in file paths?
- [ ] **G2. Command injection** — Subprocess calls with unsanitized input? `shell=True` with user data?
- [ ] **G3. Secret exposure** — API keys, tokens, passwords in code or logs? `.env` values logged?
- [ ] **G4. Input validation** — Is LLM output validated before use? Could malformed JSON crash the task?
- [ ] **G5. File permission safety** — Are output files created with appropriate permissions? World-readable secrets?
- [ ] **G6. Logging safety** — Are sensitive values (tokens, keys, user data) excluded from logs?

### H. LOGGING & OBSERVABILITY

- [ ] **H1. Appropriate log levels** — Are errors logged as ERROR, warnings as WARNING, info as INFO? Not using print() for operational messages?
- [ ] **H2. Actionable error messages** — Do error messages include enough context to diagnose? File path, expected vs actual, state at time of failure?
- [ ] **H3. Progress visibility** — Does the task report progress for long operations? Rich status updates?
- [ ] **H4. Silent failures** — Can this task fail without any visible indication to the user or logs?
- [ ] **H5. Structured logging** — Are log messages parseable? Include task ID, phase ID, operation type?

### I. CONFIGURATION & ENVIRONMENT

- [ ] **I1. Hardcoded values** — Values that should come from config but are hardcoded (URLs, ports, timeouts, limits).
- [ ] **I2. Environment assumptions** — Does the code assume specific directories exist? Specific tools installed? Network available?
- [ ] **I3. Config access pattern** — Is configuration accessed consistently? Using the config system or ad-hoc?
- [ ] **I4. Default values** — Are defaults sensible? Are they documented? Do they match `.env.example`?

### J. CONSISTENCY WITH CODEBASE PATTERNS

- [ ] **J1. Import ordering** — stdlib, third-party, local. Consistent with other tasks?
- [ ] **J2. Naming conventions** — Functions, variables, constants follow project conventions?
- [ ] **J3. State access pattern** — Using `state.get()` with defaults? Consistent key naming?
- [ ] **J4. LLM invocation pattern** — Using `llm_invoke()` or direct provider? Consistent with other tasks?
- [ ] **J5. File output pattern** — Writing to `.outputs/` with correct phase subdirectory?
- [ ] **J6. Task registration** — Is the task properly registered in its phase's `__init__.py`?
- [ ] **J7. Docstrings** — Does the task have a module docstring explaining its purpose and inputs/outputs?

### K. GRAPH INTEGRATION

- [ ] **K1. Graph import pattern** — Uses `from core.graph import get_graph`? Handles `GraphUnavailableError`?
- [ ] **K2. Graph node creation** — Creates appropriate node types? Correct properties?
- [ ] **K3. Graph relationship creation** — Creates correct edges? Bidirectional where needed?
- [ ] **K4. Dead graph guards** — Leftover `if graph:` / `if graph is not None:` checks from when graph was Optional. These are harmless but noisy.
- [ ] **K5. Memory dual-write** — If writing to memory, uses `memory_save()` which dual-writes to graph?

### L. OPERATIONAL RELIABILITY

- [ ] **L1. Idempotency** — Can this task be re-run safely? Does it check for existing artifacts before recreating?
- [ ] **L2. Backtrack safety** — If this task is rolled back, is state properly cleaned? Files removed? Graph nodes deleted?
- [ ] **L3. Timeout handling** — Does the task have appropriate timeouts for LLM calls, subprocess execution, network operations?
- [ ] **L4. Graceful degradation** — If an optional feature fails (graph, dashboard), does the core task still complete?
- [ ] **L5. Atomic operations** — Are multi-step operations (write file + update state + create graph node) atomic? What happens if step 2 fails?

### M. LLM / AI OPERATIONS
*Informed by: `machine-learning-ai.llm-operations.*`, `reliability-resilience.fault-tolerance.*`, `api-integration.*`*

- [ ] **M1. Prompt construction safety** — Are LLM prompts built safely? Any injection risk from user/file content interpolated into prompts without sanitization?
- [ ] **M2. LLM response validation** — Is LLM output validated before use? JSON parsed with error handling? Unexpected format handled gracefully?
- [ ] **M3. Hallucination guards** — Does the task verify LLM-generated file paths, function names, or identifiers actually exist before acting on them?
- [ ] **M4. Provider fallback chain** — Does `llm_invoke()` correctly fall through Claude Code → Anthropic → Bedrock → Ollama? Is the fallback tested for each task's invocation pattern?
- [ ] **M5. Token/cost awareness** — Are prompts sized appropriately? Any risk of sending entire file trees or unbounded content to the LLM? Context window overflow?
- [ ] **M6. Retry and backoff** — Do LLM calls have retry logic with exponential backoff? Rate limit handling? Or does a single API timeout kill the entire phase?
- [ ] **M7. Model capability matching** — Is the right model tier used for the task? Complex reasoning on a cheap model? Simple formatting on an expensive one?
- [ ] **M8. LLM output determinism** — Where reproducibility matters (specs, test generation), is temperature set appropriately? Are seeds used?
- [ ] **M9. Streaming vs batch** — For long LLM responses, is streaming used where appropriate for progress feedback? Or does the user stare at a blank screen?
- [ ] **M10. LLM error messages** — When an LLM call fails, does the error message include: provider attempted, model, prompt size, error type? Or just "LLM call failed"?

### N. ARCHITECTURE & DESIGN
*Informed by: `architecture-design.coupling.*`, `architecture-design.boundaries-modularity.*`, `code-quality-maintainability.design-principles.*`*

- [ ] **N1. Circular imports** — Does this file participate in circular import chains? Lazy imports hiding dependency cycles?
- [ ] **N2. Layer violations** — Does a task directly access things it shouldn't? (e.g., task file importing from another phase's tasks, orchestrator doing task-level work)
- [ ] **N3. Tight coupling to state shape** — Does the task assume specific nested dict structures in `state` that could change? Should use accessor functions?
- [ ] **N4. God function** — Is there a single function doing everything (LLM call + file I/O + state update + graph write + UI output)? Violates SRP.
- [ ] **N5. Dependency direction** — Do dependencies flow correctly? (tasks → core, not core → tasks; orchestrators → tasks, not tasks → orchestrators)
- [ ] **N6. Interface segregation** — Does the task import large modules just to use one function? Could use a narrower interface?
- [ ] **N7. Composition vs inheritance** — Any class hierarchies that should be composition? Over-use of base classes?
- [ ] **N8. Module boundary clarity** — Is it clear what this module's public API is? Or does it expose internals that other modules depend on?

### O. DEPENDENCIES & SUPPLY CHAIN
*Informed by: `security-trust.supply-chain-security.*`, `infrastructure-operations.dependency-management.*`*

- [ ] **O1. Pinned dependencies** — Are all dependencies version-pinned? Could a minor version bump break the pipeline?
- [ ] **O2. Unused dependencies** — Are there packages in requirements that no code actually imports?
- [ ] **O3. Transitive dependency risk** — Any deep dependency trees where a transitive dep could introduce vulnerabilities?
- [ ] **O4. Import-time side effects** — Do any imports trigger network calls, file creation, or heavy computation at import time?
- [ ] **O5. Optional dependency handling** — Are optional deps (boto3 for Bedrock, ollama for local) properly guarded with try/except ImportError?
- [ ] **O6. Vendored vs installed** — Any copy-pasted library code that should be a proper dependency? Drift risk from upstream?
- [ ] **O7. Docker/container dependency** — FalkorDB requires Docker. Is this dependency documented and checked at startup with a clear error message?

### P. TEST SUITE HEALTH
*Informed by: `testing-quality-assurance.test-strategy.*`, `testing-quality-assurance.unit-testing.*`, `testing-quality-assurance.integration-testing.*`*

- [ ] **P1. Test coverage existence** — Does this file have ANY corresponding tests? Many task files have 0% coverage.
- [ ] **P2. Test-code correspondence** — Do existing tests actually test meaningful behavior, or just assert `True`/mock everything?
- [ ] **P3. Mock appropriateness** — Are mocks used for external boundaries only (LLM, filesystem, graph)? Or mocking internal functions, hiding real bugs?
- [ ] **P4. Test isolation** — Can tests run independently and in any order? Or do they depend on shared state, temp files, or execution order?
- [ ] **P5. Missing edge case tests** — Are error paths tested? Empty inputs? Missing files? LLM returning garbage? Network timeout?
- [ ] **P6. Integration test gaps** — Is the interaction between this task and its orchestrator tested? State passing? Output consumption?
- [ ] **P7. Flaky test risk** — Any tests with timing dependencies, network calls, or filesystem races that could intermittently fail?
- [ ] **P8. Test data hygiene** — Are test fixtures minimal and self-contained? Or do tests depend on specific files existing on disk?
- [ ] **P9. Marker compliance** — Do tests use correct pytest markers (`@pytest.mark.unit`, `@pytest.mark.integration`)? Missing markers break CI filtering.

### Q. DATA & STATE LIFECYCLE
*Informed by: `data-state-management.application-state.*`, `reliability-resilience.recovery-continuity.*`, `data-state-management.data-lifecycle.*`*

- [ ] **Q1. State key hygiene** — Are state keys documented? Does this task introduce new keys without documenting them for downstream consumers?
- [ ] **Q2. State size growth** — Does the state dict grow unboundedly? Large LLM responses stored in state? Memory pressure over multi-phase runs?
- [ ] **Q3. Checkpoint completeness** — Does the checkpoint capture enough state to resume from? Or would resuming after a crash lose work?
- [ ] **Q4. Rollback data integrity** — When backtracking, is graph data cleaned up consistently with file data? Can rollback leave orphan graph nodes?
- [ ] **Q5. File vs graph consistency** — For dual-write operations (memory, agents), can file and graph get out of sync? What's the reconciliation strategy?
- [ ] **Q6. Output file lifecycle** — Are `.outputs/` files cleaned up on phase re-run? Or do stale outputs from previous runs confuse current execution?
- [ ] **Q7. Concurrent state access** — If dashboard sync reads state while a task is writing it, can it see partial/corrupt data?
- [ ] **Q8. Sensitive data in state** — Are API keys, tokens, or user credentials ever stored in the state dict or `.state/` files?

### R. UX & INTERFACE QUALITY
*Informed by: `usability-interaction.*`, `accessibility-inclusion.perceivable-visual.*`, `emotional-design-trust.error-failure-emotion.*`*

- [ ] **R1. Progress feedback for long operations** — Do LLM calls, bulk graph loads, and file scans show a Rich spinner/progress bar? Or does the terminal go silent for 30+ seconds?
- [ ] **R2. Error message actionability** — When a task fails, does the user know WHAT failed, WHY, and WHAT TO DO? Or just a traceback?
- [ ] **R3. Destructive action safeguards** — Do `backtrack` and `reset` commands confirm before deleting state/outputs? Can a typo wipe hours of work?
- [ ] **R4. Color/formatting consistency** — Do all tasks use the same Rich styles for success (green), warning (yellow), error (red)? Or is styling ad-hoc per task?
- [ ] **R5. Terminal width handling** — Do Rich tables and panels degrade gracefully on narrow terminals (80 columns)? Or do they wrap/break?
- [ ] **R6. Non-interactive mode** — Can the pipeline run headlessly (CI/CD, scripts)? Or do tasks block on interactive prompts with no timeout/default?
- [ ] **R7. Dashboard data freshness** — Does the web dashboard (port 5174) show stale data? Is SSE reconnection handled? Does the UI indicate connection loss?
- [ ] **R8. Keyboard interrupt handling** — Does Ctrl+C during a task leave state in a consistent, resumable state? Or does it corrupt the pipeline?
- [ ] **R9. Audit browser accuracy** — Does the SvelteKit audit browser correctly load all 2,186 audits? Are category counts accurate? Do YAML detail modals render correctly?
- [ ] **R10. CLI help completeness** — Do `--help` flags on all Click commands document all options with examples? Or are some undocumented?

---

## Severity Classification

**Reporting threshold**: Only report CRITICAL, HIGH, and MEDIUM findings. Do NOT report LOW or INFO.

A finding MUST meet the concrete criteria below to qualify for its severity level. When in doubt, downgrade. The goal is zero false positives at CRITICAL/HIGH — every finding at those levels must be a confirmed, reproducible defect with a specific code path that demonstrates the problem.

### CRITICAL — Confirmed runtime failure, data loss, or exploitable security vulnerability

A finding is CRITICAL **only if** ALL of these are true:
- You can describe a **specific, reproducible scenario** (not hypothetical) where the code fails
- The failure causes **runtime crash, data loss, data corruption, or security exploit**
- The failure occurs on a **normal code path** (not an obscure edge case requiring adversarial input from a trusted internal caller)

**CRITICAL examples:**
- `json.loads(response)` with no try/except where `response` is raw LLM output (will crash on malformed JSON — reproducible every time the LLM returns non-JSON)
- `state["key"]` where `key` is provably never set on a reachable code path (confirmed KeyError)
- Path traversal guard using `startswith()` that is demonstrably bypassable with a concrete exploit string

**NOT CRITICAL (downgrade or omit):**
- "No tests for this module" — lack of tests is not a runtime failure
- "God function is 400 lines" — code quality, not a defect
- "Bare `except`" — bad practice, but the code runs
- "Could theoretically crash if..." without a concrete trigger scenario
- Missing `KeyboardInterrupt` handling — expected developer behavior, not a bug

### HIGH — Confirmed incorrect behavior in production

A finding is HIGH **only if** ALL of these are true:
- You can describe a **specific scenario** where the code produces **wrong results, wrong state, or wrong output**
- The scenario occurs on a **reachable code path** during normal or UAT operation
- The impact is **functional** (wrong data, skipped logic, broken pipeline flow) not cosmetic

**HIGH examples:**
- UAT mode writes `{"version": "0.1.0"}` but downstream task reads `setup_data["release"]["version"]` — confirmed schema mismatch that breaks UAT runs
- Task writes output to `review-report.md` but tests assert `review-report.json` — tests are provably broken
- `run_integration_tests()` returns hardcoded passing results — phase is functionally hollow, masking real failures
- User-controlled input interpolated into `bash -c` or Cypher query without sanitization — exploitable injection with a concrete payload

**NOT HIGH (downgrade or omit):**
- "Function too long" — code quality, not incorrect behavior
- "Unused parameter `mem`" — dead code, not wrong behavior
- "Broad `except Exception`" — may mask bugs but is not itself a bug
- "No `isatty()` check on `input()`" — environment assumption, not wrong results
- "Duplicate code across files" — maintainability concern, not a defect

### MEDIUM — Confirmed code defect that degrades reliability or correctness under specific conditions

A finding is MEDIUM **only if** ALL of these are true:
- There is a **concrete code defect** (not a style preference or missing feature)
- The defect **could cause incorrect behavior** under conditions that are plausible but not guaranteed on every run
- You can identify the **specific lines** and **triggering condition**

**MEDIUM examples:**
- `except Exception: pass` silently swallows a failure in a code path where the caller checks the return value for success — downstream logic proceeds on bad data
- File written non-atomically (write then rename) where a crash between steps leaves corrupt state that the resume logic cannot recover from
- LLM prompt truncation at character boundary that can break mid-JSON-instruction — triggers when prompt exceeds 50k chars
- Race condition between two functions accessing the same file where one uses locking and the other doesn't

**NOT MEDIUM (omit entirely):**
- Style issues (import ordering, naming conventions, missing docstrings)
- "Should use `dict.get()` instead of `dict[]`" without proving the key can be absent
- "Magic number 5174" — hardcoded but correct and stable
- "Function could be decomposed" — opinion, not a defect
- Theoretical concerns without a concrete triggering condition
- Duplicate code that is correct in all copies
- Missing features or missing tests (unless tests exist and are provably wrong)

### Omit entirely (do not report):

- LOW: Style, consistency, naming, formatting, import order, missing docstrings, unused imports, dead parameters, code length opinions
- INFO: Observations, suggestions, "this is clean", N/A confirmations
- Hypothetical risks without concrete trigger scenarios
- Code quality opinions (function length, nesting depth, complexity metrics)
- Missing tests (unless existing tests are provably broken — that's MEDIUM+)
- Accepted patterns (broad exception handling in pipeline code that must not crash)

---

## Audit Execution Order

### Phase 00 - Setup (5 tasks + 1 orchestrator)
1. [ ] `phases/phase00/orchestrator00.py`
2. [ ] `phases/phase_00_setup/tasks/task_001_environment_bootstrap.py`
3. [ ] `phases/phase_00_setup/tasks/task_002_provider_detection.py`
4. [ ] `phases/phase_00_setup/tasks/task_003_setup_wizard.py`
5. [ ] `phases/phase_00_setup/tasks/task_004_material_scan.py`
6. [ ] `phases/phase_00_setup/tasks/task_005_repository_setup.py`

### Phase 01 - Discovery (9 tasks + 1 orchestrator)
7. [ ] `phases/phase01/orchestrator01.py`
8. [ ] `phases/phase_01_discovery/tasks/task_101_entry_validation.py`
9. [ ] `phases/phase_01_discovery/tasks/task_102_import_requirements.py`
10. [ ] `phases/phase_01_discovery/tasks/task_103_agent_selection.py`
11. [ ] `phases/phase_01_discovery/tasks/task_104_opening_dialogue.py`
12. [ ] `phases/phase_01_discovery/tasks/task_105_discovery_work.py`
13. [ ] `phases/phase_01_discovery/tasks/task_106_approach_selection.py`
14. [ ] `phases/phase_01_discovery/tasks/task_107_discovery_diagrams.py`
15. [ ] `phases/phase_01_discovery/tasks/task_108_phase_audit.py`
16. [ ] `phases/phase_01_discovery/tasks/task_109_closeout.py`

### Phase 02 - PRD (10 tasks + 1 orchestrator)
17. [ ] `phases/phase02/orchestrator02.py`
18. [ ] `phases/phase_02_prd/tasks/task_201_entry_validation.py`
19. [ ] `phases/phase_02_prd/tasks/task_202_prd_setup.py`
20. [ ] `phases/phase_02_prd/tasks/task_203_prd_interview.py`
21. [ ] `phases/phase_02_prd/tasks/task_204_agent_selection.py`
22. [ ] `phases/phase_02_prd/tasks/task_205_prd_authoring.py`
23. [ ] `phases/phase_02_prd/tasks/task_206_prd_validation.py`
24. [ ] `phases/phase_02_prd/tasks/task_206b_prd_revision.py`
25. [ ] `phases/phase_02_prd/tasks/task_207_prd_approval.py`
26. [ ] `phases/phase_02_prd/tasks/task_208_phase_audit.py`
27. [ ] `phases/phase_02_prd/tasks/task_209_closeout.py`

### Phase 03 - Tasking (6 tasks + 1 orchestrator)
28. [ ] `phases/phase03/orchestrator03.py`
29. [ ] `phases/phase_03_tasking/tasks/task_301_entry_initialization.py`
30. [ ] `phases/phase_03_tasking/tasks/task_302_agent_selection.py`
31. [ ] `phases/phase_03_tasking/tasks/task_303_task_decomposition.py`
32. [ ] `phases/phase_03_tasking/tasks/task_304_dependency_analysis.py`
33. [ ] `phases/phase_03_tasking/tasks/task_305_phase_audit.py`
34. [ ] `phases/phase_03_tasking/tasks/task_306_closeout.py`

### Phase 04 - Specification (6 tasks + 1 orchestrator)
35. [ ] `phases/phase04/orchestrator04.py`
36. [ ] `phases/phase_04_specification/tasks/task_401_entry_initialization.py`
37. [ ] `phases/phase_04_specification/tasks/task_402_agent_selection.py`
38. [ ] `phases/phase_04_specification/tasks/task_403_openspec_generation.py`
39. [ ] `phases/phase_04_specification/tasks/task_404_tdd_subtask_injection.py`
40. [ ] `phases/phase_04_specification/tasks/task_405_phase_audit.py`
41. [ ] `phases/phase_04_specification/tasks/task_406_closeout.py`

### Phase 05 - Implementation (7 tasks + 1 orchestrator)
42. [ ] `phases/phase05/orchestrator05.py`
43. [ ] `phases/phase_05_implementation/tasks/task_501_entry_initialization.py`
44. [ ] `phases/phase_05_implementation/tasks/task_502_tdd_setup.py`
45. [ ] `phases/phase_05_implementation/tasks/task_503_agent_selection.py`
46. [ ] `phases/phase_05_implementation/tasks/task_504_tdd_execution.py`
47. [ ] `phases/phase_05_implementation/tasks/task_505_validation.py`
48. [ ] `phases/phase_05_implementation/tasks/task_506_phase_audit.py`
49. [ ] `phases/phase_05_implementation/tasks/task_507_closeout.py`

### Phase 06 - Code Review (6 tasks + 1 orchestrator)
50. [ ] `phases/phase06/orchestrator06.py`
51. [ ] `phases/phase_06_code_review/tasks/task_601_entry_initialization.py`
52. [ ] `phases/phase_06_code_review/tasks/task_602_agent_selection.py`
53. [ ] `phases/phase_06_code_review/tasks/task_603_comprehensive_review.py`
54. [ ] `phases/phase_06_code_review/tasks/task_604_refinement.py`
55. [ ] `phases/phase_06_code_review/tasks/task_605_phase_audit.py`
56. [ ] `phases/phase_06_code_review/tasks/task_606_closeout.py`

### Phase 07 - Integration (7 tasks + 1 orchestrator)
57. [ ] `phases/phase07/orchestrator07.py`
58. [ ] `phases/phase_07_integration/tasks/task_701_entry_initialization.py`
59. [ ] `phases/phase_07_integration/tasks/task_702_integration_setup.py`
60. [ ] `phases/phase_07_integration/tasks/task_703_agent_selection.py`
61. [ ] `phases/phase_07_integration/tasks/task_704_testing_execution.py`
62. [ ] `phases/phase_07_integration/tasks/task_705_integration_approval.py`
63. [ ] `phases/phase_07_integration/tasks/task_706_phase_audit.py`
64. [ ] `phases/phase_07_integration/tasks/task_707_closeout.py`

### Phase 08 - Deployment Prep (7 tasks + 1 orchestrator)
65. [ ] `phases/phase08/orchestrator08.py`
66. [ ] `phases/phase_08_deployment_prep/tasks/task_801_entry_initialization.py`
67. [ ] `phases/phase_08_deployment_prep/tasks/task_802_deployment_setup.py`
68. [ ] `phases/phase_08_deployment_prep/tasks/task_803_agent_selection.py`
69. [ ] `phases/phase_08_deployment_prep/tasks/task_804_artifact_generation.py`
70. [ ] `phases/phase_08_deployment_prep/tasks/task_805_phase_audit.py`
71. [ ] `phases/phase_08_deployment_prep/tasks/task_806_deployment_approval.py`
72. [ ] `phases/phase_08_deployment_prep/tasks/task_807_closeout.py`

### Phase 09 - Release (6 tasks + 1 orchestrator)
73. [ ] `phases/phase09/orchestrator09.py`
74. [ ] `phases/phase_09_release/tasks/task_901_entry_initialization.py`
75. [ ] `phases/phase_09_release/tasks/task_902_release_setup.py`
76. [ ] `phases/phase_09_release/tasks/task_903_agent_selection.py`
77. [ ] `phases/phase_09_release/tasks/task_904_release_execution.py`
78. [ ] `phases/phase_09_release/tasks/task_905_release_confirmation.py`
79. [ ] `phases/phase_09_release/tasks/task_906_closeout.py`

### Orchestration Modules
80. [ ] `orchestration/pipeline.py`
81. [ ] `orchestration/task_display.py`
82. [ ] `orchestration/task_memory.py`
83. [ ] `orchestration/pre_task_validation.py`
84. [ ] `orchestration/dashboard_sync.py`
85. [ ] `orchestration/backtrack.py`
86. [ ] `orchestration/memory_enrichment.py`

### Core Modules (bonus — audit if time permits)
87. [ ] `core/audit.py`
88. [ ] `core/state.py`
89. [ ] `core/memory.py`
90. [ ] `core/config.py`
91. [ ] `core/ui.py`
92. [ ] `core/subprocess_runner.py`
93. [ ] `core/llm/router.py`
94. [ ] `core/llm/invoke.py`
95. [ ] `core/llm/anthropic.py`
96. [ ] `core/llm/bedrock.py`
97. [ ] `core/llm/ollama.py`
98. [ ] `core/graph/connection.py`
99. [ ] `core/graph/manager.py`
100. [ ] `core/graph/writer.py`

---

## Finding Template

Only include findings that meet CRITICAL, HIGH, or MEDIUM criteria above. Every finding must include a concrete trigger scenario.

```markdown
### [FILE_PATH] — Audit #N

**Date**: YYYY-MM-DD
**Auditor**: Claude Opus 4.6

| Check | Severity | Finding | Line(s) | Trigger Scenario | Recommendation |
|-------|----------|---------|---------|------------------|----------------|
| G1    | CRITICAL | Path traversal guard uses startswith() | 1311 | Input `/foo/bar2/../secret` bypasses `/foo/bar` base check | Use Path.is_relative_to() |
| F2    | HIGH     | UAT writes flat JSON, consumer reads nested | 61-74, 73 | Run full pipeline in UAT mode; task_303 gets empty agent list | Align UAT schema to production schema |
| ...   | ...      | ...     | ...     | ...              | ...            |

**Summary**: X critical, Y high, Z medium findings (only actionable defects)
**Action Items**:
1. ...
2. ...
```

---

## Aggregate Tracking

Only CRITICAL, HIGH, and MEDIUM counts. Every entry must meet the concrete criteria above.

| Phase | Files | Critical | High | Medium | Status |
|-------|-------|----------|------|--------|--------|
| 00    | 6     |          |      |        | Pending |
| 01    | 10    |          |      |        | Pending |
| 02    | 11    |          |      |        | Pending |
| 03    | 7     |          |      |        | Pending |
| 04    | 7     |          |      |        | Pending |
| 05    | 8     |          |      |        | Pending |
| 06    | 7     |          |      |        | Pending |
| 07    | 8     |          |      |        | Pending |
| 08    | 8     |          |      |        | Pending |
| 09    | 7     |          |      |        | Pending |
| Orch  | 7     |          |      |        | Pending |
| Core  | 14    |          |      |        | Pending |
| **Total** | **100** |    |      |        |         |
