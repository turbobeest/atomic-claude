# Model Configuration Fix - Summary

## Problem Statement

Anthropic's commercial model "opus" was hardcoded in multiple locations throughout the codebase, causing issues when:
- Claude Max/API is offline or unavailable
- Users want to use AWS Bedrock, Ollama, or other providers
- Users configure different models in setup.md

The warning was: `[WARN] No Ollama fallback available for opus`

## Root Cause

1. **Task 002 (Config Collection)** - Line 343 hardcoded `--model=opus` for extracting configuration from setup.md
2. **lib/atomic.sh** - Line 37 defaulted to `opus` instead of a more widely available model
3. **Multiple Phase Tasks** - Hardcoded `--model=opus` in 10+ task files across phases 2, 3, 5, and lib/audit.sh
4. **No setup.md integration** - The system didn't read the `primary_model` configuration from setup.md

## Solution Implemented

### 1. Added Model Configuration Helpers (lib/atomic.sh)

```bash
# Get the primary model from project config (setup.md)
atomic_get_primary_model() {
    # Reads from .outputs/0-setup/project-config.json
    # Falls back to CLAUDE_MODEL env var
}

# Get the fast model from project config (setup.md)
atomic_get_fast_model() {
    # Reads fast_model from setup.md
    # Falls back to "haiku"
}
```

### 2. Changed Default Model (lib/atomic.sh:39)

**Before:**
```bash
CLAUDE_MODEL="${CLAUDE_MODEL:-opus}"
```

**After:**
```bash
CLAUDE_MODEL="${CLAUDE_MODEL:-sonnet}"
```

**Rationale:** Sonnet is more widely available, cost-effective, and suitable for most tasks.

### 3. Updated atomic_invoke to Use Configured Model (lib/atomic.sh:~1600)

**Before:**
```bash
local model="$CLAUDE_MODEL"
```

**After:**
```bash
# Try to use configured primary model from setup.md, fall back to CLAUDE_MODEL env var
local model
model=$(atomic_get_primary_model 2>/dev/null || echo "$CLAUDE_MODEL")
```

**Effect:** All `atomic_invoke` calls now automatically use the model configured in setup.md.

### 4. Removed Hardcoded --model=opus (Multiple Files)

Removed `--model=opus` from these files (10 instances total):

**Phase 2 - PRD:**
- `phases/2-prd/tasks/205-prd-authoring.sh` (2 instances)
- `phases/2-prd/tasks/206-prd-validation.sh` (1 instance)
- `phases/2-prd/tasks/206b-prd-revision.sh` (1 instance)
- `phases/2-prd/tasks/207-prd-approval.sh` (2 instances)
- `phases/2-prd/tasks/208-phase-audit.sh` (1 instance)

**Phase 3 - Tasking:**
- `phases/3-tasking/tasks/303-task-decomposition.sh` (1 instance)

**Phase 5 - Implementation:**
- `phases/5-implementation/tasks/504-tdd-execution.sh` (1 instance)

**Library:**
- `lib/audit.sh` (1 instance)

### 5. Fixed Task 002 Config Extraction (phases/0-setup/tasks/002-config-collection.sh:343)

**Before:**
```bash
if atomic_invoke "$prompt_file" "$extracted_file" "Extract configuration from setup" --model=opus --no-stream; then
```

**After:**
```bash
# Invoke Claude to extract (use default model from environment/config)
# No model override - let the system use what's available (Claude Max/API/Bedrock/Ollama)
if atomic_invoke "$prompt_file" "$extracted_file" "Extract configuration from setup"; then
```

**Note:** Also removed `--no-stream` flag which was causing the warning `⚠ Unknown option: --no-stream`

## How It Works Now

### Provider Priority Chain

1. **Primary Model from setup.md** (lines 410-416):
   ```
   primary_provider: anthropic | aws-bedrock | openai | ollama | ...
   primary_model: [model-id] | default [claude-opus-4-5-20251101]
   ```

2. **Environment Variable:** `CLAUDE_MODEL=sonnet`

3. **Hardcoded Default:** `sonnet` (in atomic.sh)

### Automatic Fallback

The system automatically falls back through this chain:
1. Try configured provider (Claude Max, API, Bedrock, etc.)
2. If offline and Ollama enabled → Try Ollama with tier-appropriate model
3. Use tier mapping from `config/models.json`:
   - opus → llama3.1:70b, qwen2:72b, mixtral:8x7b
   - sonnet → devstral:24b, llama3.1:70b, codellama:34b
   - haiku → llama3.2:3b, phi3:mini, gemma2:9b

### Task 002 Behavior

Since Task 002 runs BEFORE the config is extracted:
- Uses `CLAUDE_MODEL` environment variable if set
- Otherwise uses default (`sonnet`)
- Provider routing handles availability (max → api → bedrock → ollama)
- No more hardcoded opus requirement

## Testing Recommendations

1. **With Claude Max:**
   ```bash
   ./main.sh run 0
   # Should use claude-opus-4-5-20251101 or claude-sonnet-4-20250514 (per setup.md)
   ```

2. **With AWS Bedrock:**
   ```bash
   # In setup.md, set: primary_provider: aws-bedrock
   ./main.sh run 0
   # Should use Bedrock Sonnet 4.5
   ```

3. **Offline with Ollama:**
   ```bash
   export CLAUDE_PROVIDER=ollama
   export CLAUDE_OLLAMA_HOST=http://localhost:11434
   ./main.sh run 0
   # Should use devstral:24b or llama3.1:8b (whatever is available)
   ```

4. **Custom Model:**
   ```bash
   export CLAUDE_MODEL=haiku
   ./main.sh run 0
   # Should use claude-haiku-4-5-20251101
   ```

## Configuration Examples

### setup.md - Claude API
```markdown
## Primary Provider
anthropic

## Primary Model
default [claude-opus-4-5-20251101]
```

### setup.md - AWS Bedrock
```markdown
## Primary Provider
aws-bedrock

## Primary Model
anthropic.claude-sonnet-4-20250514-v1:0
```

### setup.md - Ollama Only
```markdown
## Primary Provider
ollama

## Primary Model
qwen3-coder:30b

## Enable Ollama
true

## Ollama Servers
local | localhost:11434 | qwen3-coder:30b | 64000 | Local instance
```

## Benefits

1. **setup.md is source of truth** - Model configuration now comes from setup.md
2. **Provider flexibility** - Works with Max, API, Bedrock, Ollama seamlessly
3. **Offline support** - No hard dependency on Claude API
4. **Cost optimization** - Can use free Ollama models for bulk tasks
5. **No hardcoded assumptions** - System adapts to what's available

## Migration Notes

**For existing projects:**
- No action needed - will use new defaults
- To keep opus: Set `CLAUDE_MODEL=opus` or configure in setup.md

**For new projects:**
- Configure provider and model in `initialization/setup.md`
- System will respect your choices

## Files Changed

1. `lib/atomic.sh` - Added helpers, changed default, updated atomic_invoke
2. `phases/0-setup/tasks/002-config-collection.sh` - Removed opus hardcode
3. `phases/2-prd/tasks/*.sh` - Removed opus hardcodes (5 files)
4. `phases/3-tasking/tasks/303-task-decomposition.sh` - Removed opus hardcode
5. `phases/5-implementation/tasks/504-tdd-execution.sh` - Removed opus hardcode
6. `lib/audit.sh` - Removed opus hardcode

**Total Changes:** 10 files, ~15 hardcoded instances removed

## Date

2026-02-02
