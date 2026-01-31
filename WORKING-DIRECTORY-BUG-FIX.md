# ATOMIC-CLAUDE Working Directory Bug Fix

## Problem Summary

**Bug**: Cross-project artifact contamination when running ATOMIC-CLAUDE pipelines on different target projects.

**Symptom**: When running ATOMIC-CLAUDE against a new project (e.g., "acapella"), the LLM would generate artifacts containing references to a previously-processed project (e.g., "atomicgrok"). Project names, descriptions, and context from prior sessions would "bleed" into new project runs.

**Root Cause**: The `_atomic_build_invoke_cmd()` function in `lib/atomic.sh` was setting the working directory (`cwd`) to the **wrapper tool's location** instead of the **target project's location** (`ATOMIC_ROOT`).

---

## Technical Details

### The Bug

When ATOMIC-CLAUDE invokes Claude CLI (via the `claude-local` wrapper), it needs to:
1. Find and execute the Python launcher module
2. Set the correct working directory so Claude CLI sees the right project context

The original code did this:

```bash
# BUGGY: This cd's into the wrapper directory, NOT the project directory
local cmd="cd '${escaped_wrapper_path}' && python -m local_launcher"
```

This meant Claude CLI's working directory was `claude-local/` (the wrapper tool), not the actual target project directory. Claude CLI reads project context from its working directory, including:
- `CLAUDE.md` files
- `.claude/` artifacts
- Git repository context
- Session state

### Why This Caused Artifact Bleed

1. User runs ATOMIC-CLAUDE on Project A (atomicgrok)
2. Claude CLI's cwd = `claude-local/` (wrong, but works because atomicgrok context exists somewhere)
3. Session artifacts, context, and memory get associated with `claude-local/` directory
4. User runs ATOMIC-CLAUDE on Project B (acapella)
5. Claude CLI's cwd = `claude-local/` again (same wrong directory)
6. Claude picks up stale context/artifacts from the previous Project A run
7. Project B outputs contain Project A references

### The Fix

```bash
# FIXED: Use PYTHONPATH to find local_launcher, but keep CWD as ATOMIC_ROOT
# so Claude CLI sees the correct project context (not the wrapper's directory)
local cmd="cd '${escaped_atomic_root}' && PYTHONPATH='${escaped_wrapper_path}:${PYTHONPATH}' python -m local_launcher"
```

This separates two concerns:
- **PYTHONPATH**: Where Python finds the `local_launcher` module (the wrapper directory)
- **CWD**: What Claude CLI sees as the project context (the target project directory)

---

## Code Diff

```diff
 _atomic_build_invoke_cmd() {
     # ... earlier code ...

     # Escape wrapper path for shell
     local escaped_wrapper_path
     escaped_wrapper_path=$(printf '%s' "$wrapper_path" | sed "s/'/'\\\\''/g")

+    # Escape ATOMIC_ROOT for shell (Claude CLI working directory)
+    local escaped_atomic_root
+    escaped_atomic_root=$(printf '%s' "$ATOMIC_ROOT" | sed "s/'/'\\\\''/g")
+
     # Build command with proper quoting
-    local cmd="cd '${escaped_wrapper_path}' && python -m local_launcher"
+    # CRITICAL: Use PYTHONPATH to find local_launcher, but keep CWD as ATOMIC_ROOT
+    # so Claude CLI sees the correct project context (not the wrapper's directory)
+    local cmd="cd '${escaped_atomic_root}' && PYTHONPATH='${escaped_wrapper_path}:\${PYTHONPATH}' python -m local_launcher"
     cmd="${cmd} --provider '${provider}'"
     cmd="${cmd} --model '${model}'"
     # ... rest of command building ...
 }
```

---

## Identifying Similar Patterns

When auditing forked repos, look for these anti-patterns:

### 1. Wrong Working Directory for CLI Tools

```bash
# BAD: cd to tool location before invoking
cd "$TOOL_PATH" && tool --options

# GOOD: Stay in project directory, use PATH/PYTHONPATH for tool discovery
PYTHONPATH="$TOOL_PATH" tool --options
```

### 2. Hardcoded or Leaked Paths

Search for:
```bash
grep -r "cd.*&&.*python\|claude\|llm" lib/
grep -r "ATOMIC_ROOT\|PROJECT_ROOT\|CWD" lib/
```

### 3. Session/Context Pollution Points

Check anywhere the codebase:
- Invokes external LLM CLIs (claude, ollama, etc.)
- Writes to `.claude/`, `.outputs/`, or similar state directories
- Reads `CLAUDE.md` or project configuration

### 4. Relative vs Absolute Path Confusion

```bash
# BAD: Relative paths depend on cwd
./scripts/run.sh

# GOOD: Absolute paths are explicit
"$ATOMIC_ROOT/scripts/run.sh"
```

---

## Files Changed

| File | Change |
|------|--------|
| `lib/atomic.sh` | Fixed `_atomic_build_invoke_cmd()` to use `ATOMIC_ROOT` as cwd |
| `tools/dashboard.py` | Removed hardcoded "ATOMICGROK" example from help text |

---

## Testing the Fix

After applying the fix:

1. Run ATOMIC-CLAUDE on Project A
2. Run ATOMIC-CLAUDE on Project B
3. Verify Project B outputs contain NO references to Project A
4. Check that `.outputs/` and `.claude/` in each project are isolated

---

## Related Commits

- `5705a5e` - fix: Remove atomicgrok reference from dashboard help text
- (pending) - fix: Use ATOMIC_ROOT as Claude CLI working directory

---

## Applicability to Forked Repos

If your fork has diverged, search for:

```bash
# Find the problematic pattern
grep -n "cd.*wrapper_path.*&&.*python" lib/*.sh

# Find all LLM invocation points
grep -rn "python -m local_launcher\|claude -p\|atomic_invoke" lib/ phases/
```

The fix principle applies to any code that invokes Claude CLI or similar tools: **always ensure the working directory is the target project, not the tool's installation location**.
