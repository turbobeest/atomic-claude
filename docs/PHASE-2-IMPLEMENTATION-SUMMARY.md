# Phase 2 Implementation Summary

## Hierarchical Model Routing - Project-Level Configuration

Phase 2 of the model routing architecture has been successfully implemented. The system now supports intelligent provider fallback chains configured at the project level via `setup.md`.

## What Was Implemented

### 1. Extended setup.md Configuration

**New Section: LLM PROVIDER - PREFERENCE CHAIN**

```markdown
## Global Provider Chain
# Ordered list of providers to try for all tasks.
# Format: space-separated list
# Options: default [claude-code anthropic aws-bedrock ollama]

default

## Critical Tasks Provider Chain
# Override chain specifically for critical tasks (PRD, architecture).
# Leave blank to use global chain.

[space-separated provider list]

## Bulk Tasks Provider Chain
# Override chain specifically for bulk tasks (audits, code scanning).
# Leave blank to use global chain.

[space-separated provider list]

## Quick Tasks Provider Chain
# Override chain specifically for quick tasks (validations, checks).
# Leave blank to use global chain.

[space-separated provider list]
```

### 2. Enhanced Provider Resolution Functions

**Added to `lib/provider.sh`:**

- `provider_resolve_chain(chain, context)` - Resolves best provider from a chain
- `provider_get_chain(task_type)` - Gets provider chain for a task type
- `provider_resolve_for_task(task_type, context)` - Resolves best provider for a task

### 3. Updated Config Extraction

**Modified `phases/0-setup/tasks/002-config-collection.sh`:**

Extended JSON schema to include:
```json
{
  "providers": {
    "chains": {
      "global": "string (space-separated provider list)",
      "critical": "string or null",
      "bulk": "string or null",
      "quick": "string or null"
    },
    "routing": {
      "critical": "primary|ollama",
      "bulk": "primary|ollama",
      "background": "primary|ollama"
    },
    "ollama": {
      "enabled": boolean,
      "servers": [...]
    },
    "fallback": {
      "api_to_ollama": boolean,
      "ollama_to_api": boolean,
      "offline_mode": boolean
    }
  }
}
```

### 4. Integrated with atomic_invoke

**Modified `lib/atomic.sh`:**

Added `--task-type` parameter to `atomic_invoke()`:

```bash
atomic_invoke \
  "prompt.md" \
  "output.json" \
  "Extract configuration" \
  --task-type=critical
```

The function now:
1. Loads provider.sh if needed
2. Resolves best provider from the task-type chain
3. Uses that provider for the invocation

## How It Works

### Resolution Algorithm

```
1. User calls atomic_invoke with --task-type=critical
2. System loads provider chain for "critical" tasks from project config
   → If critical-specific chain exists: use it
   → Otherwise: use global chain
3. System tries each provider in chain order:
   → Check provider_check_availability(provider)
   → If available: use it
   → If not: try next in chain
4. First available provider is selected
5. LLM invocation proceeds with selected provider
```

### Example Flows

**Scenario 1: Subscription-First (Development)**
```
Chain: claude-code → aws-bedrock → anthropic → ollama
Available: claude-code ✓, aws-bedrock ✓
Result: Uses claude-code (first available)
```

**Scenario 2: Cloud-First (Production)**
```
Chain: aws-bedrock → anthropic → ollama
Available: aws-bedrock ✓, anthropic ✗, ollama ✗
Result: Uses aws-bedrock (first available)
```

**Scenario 3: Local-First (Cost Optimization)**
```
Chain: ollama → aws-bedrock → anthropic
Available: ollama ✗, aws-bedrock ✓
Result: Uses aws-bedrock (fallback)
```

**Scenario 4: Task-Type Specific**
```
Critical: anthropic → aws-bedrock (high quality)
Bulk: ollama → aws-bedrock (cost savings)
Quick: claude-code → aws-bedrock (speed)
```

## Test Results

Test script: `test/test-provider-resolution.sh`

**Provider Detection:**
- ✓ Claude Code (subscription) - Available
- ✗ Anthropic API - Not configured
- ✓ AWS Bedrock - Available
- ✗ Ollama - Not running

**Chain Resolution:**
- API-first chain `anthropic aws-bedrock ollama` → Resolves to `aws-bedrock`
- Subscription-first chain `claude-code aws-bedrock` → Resolves to `claude-code`
- Local-first chain `ollama aws-bedrock` → Resolves to `aws-bedrock` (fallback)

**Task-Type Resolution:**
- Critical tasks chain `anthropic aws-bedrock` → Resolves to `aws-bedrock`
- Bulk tasks chain `ollama aws-bedrock anthropic` → Resolves to `aws-bedrock`
- Quick tasks chain `claude-code aws-bedrock` → Resolves to `claude-code`

## Benefits

1. **Intelligent Fallback**: Automatic failover across multiple providers
2. **Cost Optimization**: Use cheaper providers for bulk work
3. **Flexibility**: Different chains for different task types
4. **Resilience**: No single point of failure
5. **Environment-Aware**: Detects what's actually available
6. **Easy Configuration**: Simple space-separated provider lists

## Configuration Examples

### Development Environment (Local-First)
```markdown
## Global Provider Chain
ollama claude-code aws-bedrock anthropic
```

### Production Environment (Cloud-First)
```markdown
## Global Provider Chain
aws-bedrock anthropic openai
```

### Cost-Optimized (Hybrid)
```markdown
## Global Provider Chain
claude-code aws-bedrock anthropic

## Critical Tasks Provider Chain
aws-bedrock anthropic

## Bulk Tasks Provider Chain
ollama aws-bedrock

## Quick Tasks Provider Chain
claude-code aws-bedrock
```

### Air-Gapped (Offline Only)
```markdown
## Global Provider Chain
ollama
```

## Next Steps - Phase 3

### Agent-Specific Preferences

Allow individual agents to override provider preferences:

```yaml
# agents/expert-agents/ml-engineer.md
---
model_preferences:
  provider_chain: aws-bedrock anthropic ollama:codellama
  primary_model: claude-opus-4-5
  fallback_model: claude-sonnet-4-5
---
```

### Task-Specific Overrides

Allow tasks to override at invocation:

```bash
atomic_invoke \
  "prompt.md" \
  "output.json" \
  "Critical PRD authoring" \
  --task-type=critical \
  --prefer-chain="anthropic aws-bedrock" \
  --fallback="ollama:qwen3-coder:30b"
```

## Files Modified

### Main Repo
- `lib/provider.sh` - Added chain resolution functions
- `lib/atomic.sh` - Added --task-type parameter
- `initialization/setup.md` - Added preference chain configuration
- `phases/0-setup/tasks/002-config-collection.sh` - Extended config schema
- `docs/MODEL-ROUTING-ARCHITECTURE.md` - Architecture documentation
- `test/test-provider-resolution.sh` - Test suite

### Test Project
- All above files synced

## Status

✅ **Phase 1 Complete** - Provider availability detection
✅ **Phase 2 Complete** - Project-level routing from setup.md
⏳ **Phase 3** - Agent-specific preferences (next)
⏳ **Phase 4** - Task-specific overrides (future)
⏳ **Phase 5** - Cost tracking and optimization (future)
