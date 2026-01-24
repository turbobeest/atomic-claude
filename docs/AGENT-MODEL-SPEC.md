# Agent Model Specification

This document defines how agents in the `agents` repository should specify model requirements and fallbacks for airgapped/offline environments.

## Agent YAML Frontmatter

Each agent markdown file should include a YAML frontmatter block specifying model requirements:

```yaml
---
name: requirements-engineer
description: Synthesizes requirements into structured format using RFC 2119 + EARS syntax
version: 1.0.0

# Model specification with fallbacks
model:
  # Preferred Claude tier (opus | sonnet | haiku)
  primary: sonnet

  # Ollama fallback chain (tried in order)
  fallbacks:
    - devstral:24b      # Best for structured output
    - llama3.1:70b      # Good reasoning capability
    - codellama:34b     # Acceptable code/structure
    - qwen2:7b          # Minimum viable

  # Minimum requirements
  requirements:
    context_window: 16000
    capabilities:
      - reasoning
      - code

# Task routing hints
routing:
  task_type: critical    # critical | bulk | background
  cost_tier: medium      # high | medium | low | free
---

# Requirements Engineer Agent

You are a requirements engineer...
```

## Model Tier Mapping

| Claude Tier | Best Ollama Fallbacks | Use Case |
|-------------|----------------------|----------|
| opus | llama3.1:70b, qwen2:72b | Architecture, complex reasoning |
| sonnet | devstral:24b, llama3.1:70b, codellama:34b | PRD authoring, code generation |
| haiku | llama3.2:3b, phi3:mini, gemma2:9b | Validation, extraction, fast tasks |

## Fallback Selection Logic

1. **Check Claude availability** (5s timeout)
2. **If Claude unavailable:**
   - Read agent's `model.fallbacks` list
   - Query Ollama for available models
   - Select first available fallback that meets `requirements`
3. **If no fallback available:**
   - Warn user
   - Fail gracefully with actionable message

## Global Configuration

`config/models.json` defines system-wide fallback behavior:

```json
{
  "fallback_behavior": {
    "enabled": true,
    "auto_detect_offline": true,
    "offline_detection_timeout": 5,
    "prefer_local_when_available": false,
    "log_fallback_events": true
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ATOMIC_SKIP_FALLBACK` | false | Disable fallback resolution |
| `ATOMIC_OFFLINE_MODE` | false | Force offline mode (use Ollama) |
| `ATOMIC_PREFER_LOCAL` | false | Prefer Ollama even when Claude available |

## Implementation Notes

### For Agent Authors

1. Always specify a `primary` Claude tier
2. List 3-5 Ollama fallbacks in preference order
3. Start with best models, end with widely-available smaller models
4. Specify minimum `context_window` needed
5. List required `capabilities`

### For Pipeline Tasks

When invoking agents, use tier-based model specification:

```bash
# Good - tier-based (supports fallback)
atomic_invoke "$prompt" "$output" "PRD authoring" --model=sonnet

# Avoid - hardcoded model (no fallback)
atomic_invoke "$prompt" "$output" "PRD authoring" --model=claude-sonnet-4-20250514
```

### For Airgapped Environments

1. Pre-pull required Ollama models:
   ```bash
   ollama pull devstral:24b
   ollama pull llama3.1:70b
   ollama pull llama3.2:3b
   ```

2. Configure offline mode in setup:
   ```json
   {
     "providers": {
       "offline_mode": true
     }
   }
   ```

3. Verify fallback chain:
   ```bash
   ./scripts/verify-models.sh
   ```

## Agent Repository Structure

```
agents/
├── pipeline-agents/
│   ├── requirements-engineer.md    # With model frontmatter
│   ├── prd-writer.md
│   ├── prd-validator.md
│   └── ...
├── discovery-agents/
│   └── ...
├── audit-agents/
│   └── ...
└── custom/
    └── ...                          # Project-specific agents
```

## Example: Full Agent Definition

```yaml
---
name: prd-writer
description: Authors formal PRD documents using 15-section template
version: 1.0.0

model:
  primary: sonnet
  fallbacks:
    - devstral:24b
    - llama3.1:70b
    - mixtral:8x7b
    - codellama:34b
  requirements:
    context_window: 32000
    capabilities:
      - reasoning
      - code
      - analysis

routing:
  task_type: critical
  cost_tier: medium

inputs:
  - requirements.json
  - dialogue.json
  - corpus.json

outputs:
  - PRD.md

quality_criteria:
  - All 15 sections populated
  - RFC 2119 keywords used
  - WHEN/THEN scenarios present
  - TaskMaster compatible structure
---

# PRD Writer Agent

You are a PRD writer creating a formal Product Requirements Document...
```
