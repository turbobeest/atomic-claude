# Airgapped Model Ranking

Prioritized Ollama model recommendations for each agent type when operating without Claude API access.

## Model Availability Tiers

Before running airgapped, pull models based on your hardware:

### Tier A: High-End (64GB+ RAM, GPU recommended)
```bash
ollama pull devstral:24b        # Best code generation
ollama pull llama3.1:70b        # Best reasoning
ollama pull qwen2:72b           # Best multilingual/analysis
ollama pull codellama:34b       # Deep code understanding
ollama pull deepseek-coder:33b  # Code specialist
```

### Tier B: Mid-Range (32GB RAM)
```bash
ollama pull llama3.1:8b         # Good all-rounder
ollama pull mixtral:8x7b        # Strong MoE reasoning
ollama pull qwen2:7b            # Fast reasoning
ollama pull gemma2:27b          # Good analysis
ollama pull codellama:13b       # Code tasks
```

### Tier C: Minimum (16GB RAM)
```bash
ollama pull llama3.2:3b         # Fast/simple tasks
ollama pull phi3:mini           # Validation/extraction
ollama pull gemma2:9b           # Quick reasoning
ollama pull mistral:7b          # General purpose
ollama pull deepseek-coder:6.7b # Light code tasks
```

---

## Agent-to-Model Mapping

### Critical Path Agents (require high capability)

| Agent | Claude Tier | Ollama Fallback Chain | Min Context |
|-------|-------------|----------------------|-------------|
| system-architect | opus | llama3.1:70b → qwen2:72b → mixtral:8x7b | 32K |
| requirements-engineer | sonnet | devstral:24b → llama3.1:70b → codellama:34b | 16K |
| prd-writer | sonnet | devstral:24b → llama3.1:70b → mixtral:8x7b | 32K |
| code-implementer-phd | sonnet | devstral:24b → codellama:34b → llama3.1:8b | 16K |
| code-reviewer-phd | sonnet | devstral:24b → llama3.1:70b → codellama:34b | 16K |
| deep-code-reviewer-phd | opus | llama3.1:70b → devstral:24b → qwen2:72b | 32K |

### Code Generation Agents

| Agent | Claude Tier | Ollama Fallback Chain | Min Context |
|-------|-------------|----------------------|-------------|
| backend-engineer | sonnet | devstral:24b → codellama:34b → llama3.1:8b | 16K |
| fullstack-developer | sonnet | devstral:24b → codellama:34b → qwen2:7b | 16K |
| test-writer-phd | sonnet | devstral:24b → codellama:34b → codellama:13b | 8K |
| unit-test-specialist | haiku | codellama:13b → deepseek-coder:6.7b → mistral:7b | 8K |
| integration-test-expert | sonnet | devstral:24b → codellama:34b → llama3.1:8b | 16K |

### Review & Analysis Agents

| Agent | Claude Tier | Ollama Fallback Chain | Min Context |
|-------|-------------|----------------------|-------------|
| clean-code-expert | sonnet | devstral:24b → codellama:34b → qwen2:7b | 8K |
| code-quality-expert | sonnet | devstral:24b → llama3.1:70b → codellama:34b | 16K |
| code-refiner-phd | sonnet | devstral:24b → codellama:34b → llama3.1:8b | 16K |
| refactoring-specialist | sonnet | devstral:24b → codellama:34b → qwen2:7b | 8K |
| design-pattern-expert | sonnet | llama3.1:70b → devstral:24b → mixtral:8x7b | 16K |
| arch-compliance-phd | opus | llama3.1:70b → qwen2:72b → mixtral:8x7b | 32K |

### Security Agents

| Agent | Claude Tier | Ollama Fallback Chain | Min Context |
|-------|-------------|----------------------|-------------|
| security-auditor | opus | llama3.1:70b → qwen2:72b → mixtral:8x7b | 32K |
| security-scanner | sonnet | llama3.1:70b → devstral:24b → llama3.1:8b | 16K |
| vulnerability-expert | opus | llama3.1:70b → qwen2:72b → codellama:34b | 32K |

### Performance Agents

| Agent | Claude Tier | Ollama Fallback Chain | Min Context |
|-------|-------------|----------------------|-------------|
| performance-engineer | sonnet | devstral:24b → llama3.1:70b → codellama:34b | 16K |
| perf-analyzer-phd | sonnet | llama3.1:70b → devstral:24b → qwen2:7b | 16K |
| optimization-specialist | sonnet | devstral:24b → codellama:34b → llama3.1:8b | 16K |

### Documentation Agents

| Agent | Claude Tier | Ollama Fallback Chain | Min Context |
|-------|-------------|----------------------|-------------|
| technical-writer | sonnet | llama3.1:70b → devstral:24b → llama3.1:8b | 16K |
| api-doc-specialist | sonnet | devstral:24b → codellama:34b → qwen2:7b | 8K |
| doc-reviewer-phd | haiku | llama3.1:8b → qwen2:7b → gemma2:9b | 8K |

### Fast/Utility Agents (validation, extraction)

| Agent | Claude Tier | Ollama Fallback Chain | Min Context |
|-------|-------------|----------------------|-------------|
| validator | haiku | llama3.2:3b → phi3:mini → gemma2:9b | 4K |
| extractor | haiku | phi3:mini → llama3.2:3b → mistral:7b | 4K |
| summarizer | haiku | llama3.2:3b → gemma2:9b → phi3:mini | 8K |
| context-gardener | haiku | llama3.2:3b → phi3:mini → mistral:7b | 8K |

---

## Role-Based Defaults

Configure in `config/models.json`:

```json
{
  "providers": {
    "role_routing": {
      "primary": "ollama",
      "fast": "ollama",
      "gardener": "ollama",
      "heavyweight": "ollama"
    },
    "ollama": {
      "enabled": true,
      "host": "http://localhost:11434",
      "default_model": "devstral:24b",
      "context_length": 32768
    }
  }
}
```

---

## Recommended Minimum Pull Set

For a complete airgapped installation with reasonable hardware (32GB+ RAM):

```bash
# Critical (must have)
ollama pull devstral:24b        # Primary workhorse
ollama pull llama3.2:3b         # Fast tasks

# Recommended
ollama pull llama3.1:8b         # Fallback workhorse
ollama pull codellama:13b       # Code specialist
ollama pull phi3:mini           # Validation

# Nice to have (if resources allow)
ollama pull llama3.1:70b        # Heavy reasoning
ollama pull qwen2:7b            # Analysis
```

---

## Model Selection by Task Type

| Task Type | Primary Model | Fallback | Notes |
|-----------|---------------|----------|-------|
| PRD authoring | devstral:24b | llama3.1:70b | Needs structured output |
| Code generation | devstral:24b | codellama:34b | Code-focused |
| Code review | devstral:24b | llama3.1:70b | Needs reasoning |
| Test writing | codellama:13b | devstral:24b | Code patterns |
| Security audit | llama3.1:70b | devstral:24b | Deep analysis |
| Validation | llama3.2:3b | phi3:mini | Speed priority |
| Summarization | llama3.2:3b | gemma2:9b | Fast extraction |
| Context gardening | phi3:mini | llama3.2:3b | Compression |

---

## Performance Expectations

| Model | ~Tokens/sec (CPU) | ~Tokens/sec (GPU) | Memory |
|-------|-------------------|-------------------|--------|
| llama3.2:3b | 25-40 | 80-120 | 4GB |
| phi3:mini | 30-50 | 100-150 | 4GB |
| llama3.1:8b | 15-25 | 60-90 | 8GB |
| codellama:13b | 10-18 | 45-70 | 12GB |
| devstral:24b | 5-10 | 30-50 | 20GB |
| llama3.1:70b | 2-4 | 15-25 | 48GB |

---

## Verification Script

Create `scripts/verify-airgap.sh`:

```bash
#!/bin/bash
# Verify airgapped model availability

REQUIRED_MODELS=(
    "devstral:24b"
    "llama3.2:3b"
)

RECOMMENDED_MODELS=(
    "llama3.1:8b"
    "codellama:13b"
    "phi3:mini"
)

echo "Checking Ollama connectivity..."
if ! curl -s http://localhost:11434/api/tags >/dev/null; then
    echo "ERROR: Ollama not running"
    exit 1
fi

echo ""
echo "Required models:"
for model in "${REQUIRED_MODELS[@]}"; do
    if ollama list | grep -q "$model"; then
        echo "  ✓ $model"
    else
        echo "  ✗ $model (MISSING - run: ollama pull $model)"
    fi
done

echo ""
echo "Recommended models:"
for model in "${RECOMMENDED_MODELS[@]}"; do
    if ollama list | grep -q "$model"; then
        echo "  ✓ $model"
    else
        echo "  ○ $model (optional - run: ollama pull $model)"
    fi
done
```

---

## Environment Configuration

Force airgapped mode:

```bash
export ATOMIC_OFFLINE_MODE=true
export ATOMIC_PREFER_LOCAL=true
export CLAUDE_PROVIDER=ollama
```

Or configure in `config/models.json`:

```json
{
  "providers": {
    "default_provider": "ollama"
  },
  "fallback_behavior": {
    "prefer_local_when_available": true
  }
}
```
