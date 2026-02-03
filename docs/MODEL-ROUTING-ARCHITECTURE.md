# Model Routing Architecture

## Overview

ATOMIC CLAUDE uses a sophisticated hierarchical model routing system that allows preferences to cascade from global defaults down to agent-specific overrides, with intelligent fallback chains.

## Routing Hierarchy (Highest to Lowest Priority)

```
┌─────────────────────────────────────┐
│  1. Agent-Specific Preferences      │ ← Highest Priority
│     (agents/*/AGENT.md)             │
├─────────────────────────────────────┤
│  2. Task-Specific Overrides         │
│     (phases/*/tasks/*.sh)           │
├─────────────────────────────────────┤
│  3. Project Configuration           │
│     (initialization/setup.md)       │
├─────────────────────────────────────┤
│  4. Global Defaults with Fallback   │ ← Lowest Priority
│     (Auto-detect best available)    │
└─────────────────────────────────────┘
```

## 1. Agent-Specific Preferences

Agents can specify their preferred models in their definition files:

```yaml
# agents/expert-agents/data-intelligence/machine-learning/ml-engineer.md
---
model_preferences:
  primary: claude-opus-4-5-20251101
  providers:
    - aws-bedrock
    - anthropic
    - ollama:codellama
  fallback: claude-sonnet-4-5-20251101
---
```

**Use cases:**
- ML agents might prefer models with stronger math/reasoning
- Code review agents might prefer sonnet for balance of speed/quality
- Audit agents might use local Ollama models to save costs

## 2. Task-Specific Overrides

Tasks can override provider/model for specific operations:

```bash
# phases/2-prd/tasks/205-prd-authoring.sh

atomic_invoke \
  "prompts/write-prd.md" \
  "$output_file" \
  "Draft PRD document" \
  --model="opus" \
  --provider="anthropic" \
  --fallback="aws-bedrock:claude-opus"
```

**Use cases:**
- Critical tasks (PRD authoring, architecture) use opus
- Quick validations use haiku
- Bulk operations (audit scans) use Ollama

## 3. Project Configuration

Defined in `initialization/setup.md`:

```markdown
## Primary Provider
aws-bedrock

## Primary Model
claude-opus-4-5-20251101

## Fast Model
claude-haiku-4-5-20251101

## Provider Preference Chain
1. aws-bedrock
2. anthropic
3. ollama

## Task Type Routing
**critical_tasks**: opus @ aws-bedrock
**bulk_tasks**: codellama @ ollama
**quick_tasks**: haiku @ aws-bedrock
```

## 4. Global Defaults with Smart Fallback

The system auto-detects available providers in this order:

```bash
1. Claude Code Subscription
   - Check: claude --version
   - Models: Latest Claude models
   - Cost: Included in subscription

2. Anthropic API
   - Check: ANTHROPIC_API_KEY env var
   - Models: claude-opus-*, claude-sonnet-*, claude-haiku-*
   - Cost: Pay-per-token

3. AWS Bedrock
   - Check: AWS credentials + bedrock access
   - Models: anthropic.claude-* on Bedrock
   - Cost: AWS pricing

4. Ollama (Local)
   - Check: curl localhost:11434
   - Models: codellama, mistral, etc.
   - Cost: Free (local compute)
```

## Implementation

### Core Functions

**`atomic_resolve_model(context, requested_model, requested_provider)`**
```bash
# Resolves the best provider+model combination given:
# - Context: agent_id, task_id, phase_id, task_type
# - Requested preferences
# - Available providers
# Returns: provider, model, fallback_chain
```

**`atomic_check_provider_availability(provider)`**
```bash
# Checks if a provider is available and authenticated
# Returns: 0 (available) or 1 (unavailable)
```

**`atomic_get_agent_preferences(agent_id)`**
```bash
# Extracts model preferences from agent definition
# Returns: JSON with preferred providers and models
```

**`atomic_get_project_routing()`**
```bash
# Extracts routing rules from setup.md
# Returns: JSON with provider chains and task routing
```

### Resolution Algorithm

```bash
resolve_model() {
  local context=$1
  local requested=$2

  # 1. Check agent-specific preferences
  agent_prefs=$(atomic_get_agent_preferences "$context.agent_id")

  # 2. Check task-specific overrides
  task_prefs=$(atomic_get_task_overrides "$context.task_id")

  # 3. Check project configuration
  project_prefs=$(atomic_get_project_routing)

  # 4. Merge preferences (highest priority wins)
  merged=$(merge_preferences "$agent_prefs" "$task_prefs" "$project_prefs")

  # 5. Build fallback chain
  for provider in $merged.provider_chain; do
    if atomic_check_provider_availability "$provider"; then
      echo "$provider:$merged.model"
      return 0
    fi
  done

  # 6. Last resort: Ollama
  echo "ollama:codellama"
}
```

## Configuration Schema

### setup.md Extensions

```markdown
# ============================================================================
# MODEL ROUTING - HIERARCHICAL PREFERENCES
# ============================================================================

## Global Provider Chain
# Ordered list of providers to try (first available wins)
# Options: claude-code | anthropic | aws-bedrock | ollama | openai | azure

1. claude-code
2. aws-bedrock
3. anthropic
4. ollama

## Task Type Routing
# Override providers for specific task types

### Critical Tasks
# PRD authoring, architecture decisions, human gates
**provider**: aws-bedrock
**model**: claude-opus-4-5-20251101
**fallback**: anthropic:claude-opus-4-5-20251101

### Bulk Tasks
# Audit scans, code analysis, deep inspection
**provider**: ollama
**model**: codellama:latest
**fallback**: aws-bedrock:claude-sonnet

### Quick Tasks
# Validations, simple checks, status updates
**provider**: aws-bedrock
**model**: claude-haiku-4-5-20251101
**fallback**: anthropic:claude-haiku-4-5-20251101

## Agent Overrides
# Allow agents to specify their own preferences?
**enabled**: true

## Cost Control
# Fallback to cheaper providers after N tokens?
**token_threshold**: 1000000
**fallback_after_threshold**: ollama
```

### Agent Definition Schema

```yaml
---
name: ML Engineer
phase: 5
tier: expert
model_preferences:
  primary_model: claude-opus-4-5-20251101
  provider_chain:
    - aws-bedrock
    - anthropic
    - ollama:codellama
  task_type_overrides:
    critical: opus
    bulk: sonnet
    quick: haiku
  cost_conscious: false
---
```

## Benefits

1. **Flexibility**: Different tasks use different models optimally
2. **Cost Optimization**: Bulk operations use cheaper/local models
3. **Resilience**: Automatic fallback if primary provider unavailable
4. **Agent Specialization**: Agents can request models suited to their role
5. **Project Control**: Teams can enforce provider policies per project
6. **Development/Production Parity**: Easy to switch between local and cloud

## Migration Path

1. **Phase 1**: Implement provider availability detection
2. **Phase 2**: Add project-level routing in setup.md
3. **Phase 3**: Add task-specific override flags
4. **Phase 4**: Add agent-specific preferences
5. **Phase 5**: Add cost tracking and threshold-based fallback

## Example Scenarios

### Scenario 1: Development (Local-First)
```markdown
Provider Chain: ollama → claude-code → aws-bedrock
- Fast iteration with local models
- Falls back to cloud for complex tasks
```

### Scenario 2: Production (Cloud-First)
```markdown
Provider Chain: aws-bedrock → anthropic → ollama
- Reliable cloud providers
- Local fallback only if cloud unavailable
```

### Scenario 3: Cost-Optimized (Hybrid)
```markdown
Critical Tasks: opus @ aws-bedrock
Bulk Tasks: codellama @ ollama
Quick Tasks: haiku @ aws-bedrock
- Optimize cost vs. quality per task type
```

### Scenario 4: Air-Gapped (Offline)
```markdown
Provider Chain: ollama
- 100% local operation
- No external dependencies
```

## Testing Strategy

```bash
# Test provider availability detection
./test/test-provider-detection.sh

# Test routing resolution
./test/test-model-routing.sh

# Test fallback chains
./test/test-fallback.sh

# Test cost optimization
./test/test-cost-threshold.sh
```

## Future Enhancements

1. **Dynamic model selection**: Choose model based on prompt complexity
2. **Load balancing**: Distribute across multiple Ollama servers
3. **Performance tracking**: Log latency/cost per provider
4. **A/B testing**: Compare model outputs across providers
5. **Budget enforcement**: Hard limits on API spending
6. **Multi-provider consensus**: Run critical tasks on 2+ models, compare outputs
