# LLM Preferences Configuration Guide

## Overview

LLM configuration has been separated from `setup.md` into its own dedicated file for easier management and a cleaner setup experience.

## Files

### setup.md
**Purpose:** Project configuration (name, type, repository, sandbox, pipeline, etc.)
**LLM Section:** Now contains just a reference to `llm-preferences.md`

### llm-preferences.md
**Purpose:** All LLM provider, model, and routing configuration
**Location:** `initialization/llm-preferences.md`

## Why Separate?

**Before:**
- `setup.md` was 600+ lines
- LLM configuration mixed with project settings
- Hard to find and edit model preferences
- Difficult to see the full picture of available models

**After:**
- `setup.md` is clean and focused on project settings
- `llm-preferences.md` is dedicated to LLM configuration
- Easy to uncomment and rearrange your top 30 models
- Clear sections for each configuration aspect

## How It Works

### 1. During Phase 0 Setup

Task 002 (Config Collection) automatically reads **both files**:

```bash
✓ Reading setup: initialization/setup.md
✓ Reading LLM preferences: initialization/llm-preferences.md  # NEW!
✓ Reading agent plan: initialization/agent-plan.md
✓ Reading audit plan: initialization/audit-plan.md
```

### 2. Configuration Extraction

Claude extracts configuration from both files and merges them into a single config:

```json
{
  "project": {...},
  "repository": {...},
  "providers": {      // From llm-preferences.md
    "chains": {...},
    "routing": {...},
    "ollama": {...}
  },
  "gardener": {...}   // From llm-preferences.md
}
```

### 3. No Code Changes Needed

The pipeline automatically handles both files. No changes to your workflow.

## llm-preferences.md Structure

### 1. Primary Provider Chain

Uncomment and rearrange by priority:

```markdown
# claude-code      # Claude Code subscription
aws-bedrock        # AWS Bedrock (active)
# anthropic        # Anthropic API
ollama             # Local Ollama (active)
```

### 2. Model Preferences

#### Cloud Models
```markdown
# Claude 4.5 Series - Latest (Recommended)
us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0     # Primary (active)
# us-gov.anthropic.claude-opus-4-5-20251101-v1:0     # Max quality
# claude-haiku-4-5-20251101                           # Fast tasks

# Claude 3.5 Series
# claude-3-5-sonnet-20241022                          # Sonnet 3.5 V2
# anthropic.claude-3-5-haiku-20241022-v1:0           # Haiku 3.5

# Claude 3.0 & 2.x - See full list in llm-preferences.md
```

#### Local Models (Ollama)
```markdown
OLLAMA_ENABLED: true

# Code-Specialized (uncomment your favorites)
devstral:latest                    # 131K context (active)
granite-code:latest                # 128K context (active)
codestral:latest                   # 32K context (active)
# qwen2.5-coder:32b                # 128K context
```

### 3. Ollama Servers

```markdown
# Local Instance
local | localhost:11434 | devstral:latest | 131072 | Primary

# Remote Instances
# desktop | 192.168.1.100:11434 | qwen2.5-coder:32b | 128000 | RTX 5090
```

### 4. Task Routing

```markdown
## Critical Tasks
Provider: primary         # Use cloud API (highest quality)

## Bulk Tasks
Provider: ollama          # Use local models (cost-free)

## Quick Tasks
Provider: primary         # Use fast models
```

### 5. Context Gardener

```markdown
Gardener Model: infer                    # Auto-select fastest
Threshold: 75                            # Trigger at 75% context
Preserve Exchanges: 4                    # Keep last 4 pairs
```

## Quick Start Workflow

### Initial Setup

1. **Open llm-preferences.md**
   ```bash
   vi initialization/llm-preferences.md
   ```

2. **Uncomment Your Providers**
   ```markdown
   # Before:
   # aws-bedrock

   # After:
   aws-bedrock        # Active!
   ```

3. **Rearrange Models by Preference**
   ```markdown
   # Top choice (tried first)
   devstral:latest

   # Second choice
   granite-code:latest

   # Third choice
   codestral:latest
   ```

4. **Save and Run Phase 0**
   ```bash
   ./main.sh run 0
   ```

### Adjusting Preferences Later

1. **Edit llm-preferences.md**
   ```bash
   vi initialization/llm-preferences.md
   ```

2. **Move Models Up/Down**
   - Top = First choice
   - Bottom = Last resort

3. **Re-run Config Collection**
   ```bash
   ./main.sh run 0 --task=002
   ```

## Configuration Examples

### Example 1: Cost-Optimized (Hybrid)

```markdown
# Provider Chain
aws-bedrock
ollama

# Task Routing
Critical: primary (cloud for quality)
Bulk: ollama (local for cost)
Quick: ollama (local for speed)

# Models
Primary: us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0
Ollama: devstral:latest, granite-code:latest, codestral:latest
```

**Result:**
- Critical tasks → AWS Bedrock Sonnet
- Bulk tasks → Local devstral (free)
- Quick tasks → Local granite-code (free)

### Example 2: Quality-First (Cloud Only)

```markdown
# Provider Chain
claude-code
anthropic
aws-bedrock

# Task Routing
Critical: primary
Bulk: primary
Quick: primary

# Models
Primary: claude-opus-4-5-20251101
Fast: claude-haiku-4-5-20251101
```

**Result:**
- All tasks use cloud API
- Best quality everywhere
- Higher cost

### Example 3: Offline-Only (Air-Gapped)

```markdown
# Provider Chain
ollama

# Task Routing
Critical: ollama
Bulk: ollama
Quick: ollama

# Models
Ollama: devstral:latest, granite-code:latest, codestral:latest

# Offline Mode
Offline Mode: true
```

**Result:**
- 100% local operation
- No internet required
- Free (after initial download)

## Model Selection Tips

### For Critical Tasks (PRD, Architecture)

**Best:**
- `claude-opus-4-5-20251101` - Maximum reasoning
- `us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0` - Strong balance

**Good:**
- `devstral:latest` - Local, large context
- `granite-code:latest` - IBM flagship

### For Bulk Tasks (Audits, Scanning)

**Best:**
- `devstral:latest` - 131K context, code specialist
- `granite-code:latest` - 128K context, reliable
- `qwen2.5-coder:32b` - Strong code understanding

**Good:**
- `codestral:latest` - 32K context, specialized
- `codellama:latest` - Meta flagship

### For Quick Tasks (Validations, Checks)

**Best:**
- `claude-haiku-4-5-20251101` - Fast, accurate
- `starcoder2:latest` - Compact, code-focused
- `codegemma:latest` - Small, efficient

**Good:**
- `llama3.2:3b` - Fast general purpose
- `gemma3:4b` - Compact

## Advanced Features

### Provider Chain Overrides

Override the global chain for specific task types:

```markdown
## Global Chain
claude-code aws-bedrock anthropic ollama

## Critical Tasks Chain (override)
aws-bedrock anthropic

## Bulk Tasks Chain (override)
ollama aws-bedrock
```

### Fallback Behavior

```markdown
# API → Ollama Fallback
true        # If API fails, try Ollama

# Ollama → API Fallback
true        # If Ollama fails, try API

# Offline Mode
false       # Allow API calls
```

### Context Gardener Configuration

```markdown
Gardener Model: claude-haiku-4-5-20251101   # Specific model
Threshold: 75                                # Compress at 75%
Fallback: mistral:7b, phi3:medium            # If primary fails
Preserve Exchanges: 4                        # Keep last 4 pairs
Preserve Opening: true                       # Keep context
```

## API Credentials

API keys are **NOT** stored in llm-preferences.md for security. They're collected during Phase 0, Task 004.

### Pre-Configuration (Recommended)

Set credentials before running Phase 0:

**AWS Bedrock:**
```bash
# AWS CLI (best)
aws configure

# Or environment variables
export AWS_ACCESS_KEY_ID='your-key'
export AWS_SECRET_ACCESS_KEY='your-secret'
export AWS_REGION='us-gov-west-1'
```

**Anthropic API:**
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```

Phase 0 will detect these and skip interactive prompts.

## Troubleshooting

### "No providers available"

**Solution:** Uncomment at least one provider in llm-preferences.md

### "Bedrock unavailable, falling back to Ollama"

**Solution:** Configure AWS credentials before running pipeline:
1. Run `aws configure` and enter credentials
2. Or set environment variables (see API Credentials above)
3. Restart Phase 0

### "Ollama connection failed"

**Solution:**
1. Check Ollama is running: `curl localhost:11434`
2. Verify server config in llm-preferences.md
3. Enable health check: `Health Check: true`

### "Model not found"

**Solution:**
1. Pull model: `ollama pull devstral:latest`
2. Verify model name matches exactly
3. Check available models: `ollama list`

### Changes not taking effect

**Solution:**
1. Re-run Phase 0: `./main.sh run 0`
2. Or just Task 002: `./main.sh run 0 --task=002`

## Migration from Old setup.md

If you have an old setup.md with inline LLM configuration:

1. **Your old setup.md still works** - Config extraction handles both formats
2. **To migrate:**
   - Copy your LLM settings to llm-preferences.md
   - Delete LLM section from setup.md
   - Keep the reference block

## Summary

✅ **Cleaner setup.md** - Focused on project settings
✅ **Dedicated LLM config** - All model preferences in one place
✅ **Easy to manage** - Uncomment and rearrange models
✅ **Automatic integration** - No workflow changes needed
✅ **Backward compatible** - Old setup.md format still works

The separation makes it much easier to see all your model options and configure complex routing without getting lost in a 600-line file.
