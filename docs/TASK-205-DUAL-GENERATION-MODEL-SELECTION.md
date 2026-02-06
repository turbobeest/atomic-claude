# Task 205 Dual Generation - Dynamic Model Selection

**Date**: 2026-02-05
**Status**: DESIGN PROPOSAL v3
**Goal**: Discover available models, pick two diverse ones

---

## Core Concept

**Don't hardcode models** → Discover what's available, rank by capability, pick diverse pair

```
Runtime Discovery
  ↓
Available Models (bedrock: 3, ollama: 5, api: 2)
  ↓
Rank by Tier (quality, context, speed)
  ↓
Pick Diverse Pair (different tiers/providers)
  ↓
Run Dual Generation
```

---

## Model Discovery

### Detect Available Providers

```python
class ModelDiscovery:
    """Discover available models across all providers"""

    def discover_all(self) -> List[AvailableModel]:
        """Scan all providers, return available models"""
        available = []

        # Check Bedrock
        if self.bedrock_available():
            available.extend(self.discover_bedrock())

        # Check API
        if self.api_available():
            available.extend(self.discover_api())

        # Check Ollama
        if self.ollama_available():
            available.extend(self.discover_ollama())

        return available

    def bedrock_available(self) -> bool:
        """Check if Bedrock is configured and accessible"""
        if not os.getenv('AWS_REGION'):
            return False
        try:
            # Quick test call
            result = subprocess.run(
                ['aws', 'bedrock', 'list-foundation-models'],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def discover_bedrock(self) -> List[AvailableModel]:
        """List available Bedrock models"""
        models = []
        try:
            result = subprocess.run(
                ['aws', 'bedrock', 'list-foundation-models'],
                capture_output=True, text=True
            )
            data = json.loads(result.stdout)

            for model in data.get('modelSummaries', []):
                if 'anthropic.claude' in model['modelId']:
                    models.append(AvailableModel(
                        provider='bedrock',
                        model_id=model['modelId'],
                        name=self.parse_model_name(model['modelId']),
                        context_window=self.detect_context_window(model),
                        tier=self.classify_tier(model['modelId'])
                    ))
        except:
            pass

        return models

    def discover_ollama(self) -> List[AvailableModel]:
        """List available Ollama models"""
        models = []
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True, text=True, timeout=5
            )

            for line in result.stdout.split('\n')[1:]:  # Skip header
                if not line.strip():
                    continue
                parts = line.split()
                model_name = parts[0]

                models.append(AvailableModel(
                    provider='ollama',
                    model_id=model_name,
                    name=model_name,
                    context_window=self.detect_ollama_context(model_name),
                    tier=self.classify_ollama_tier(model_name)
                ))
        except:
            pass

        return models

    def discover_api(self) -> List[AvailableModel]:
        """List API models (if API key configured)"""
        if not os.getenv('ANTHROPIC_API_KEY'):
            return []

        # Anthropic API has fixed model list
        return [
            AvailableModel(
                provider='api',
                model_id='claude-opus-4-20250514',
                name='claude-opus-4',
                context_window=200000,
                tier='premium'
            ),
            AvailableModel(
                provider='api',
                model_id='claude-sonnet-4-20250514',
                name='claude-sonnet-4',
                context_window=200000,
                tier='standard'
            ),
            AvailableModel(
                provider='api',
                model_id='claude-haiku-4-20250401',
                name='claude-haiku-4',
                context_window=200000,
                tier='fast'
            ),
        ]
```

---

## Model Ranking

### Model Tiers

```python
@dataclass
class AvailableModel:
    provider: str          # 'bedrock', 'api', 'ollama'
    model_id: str          # Full model ID
    name: str              # Human-readable name
    context_window: int    # Tokens
    tier: ModelTier        # Classification

@dataclass
class ModelTier:
    quality: int     # 1-5 (5 = best reasoning)
    speed: int       # 1-5 (5 = fastest)
    context: int     # 1-5 (5 = largest window)
    overall: int     # Computed score

class ModelRanker:
    """Rank models by capability"""

    # Tier definitions (quality, speed, context)
    TIER_MAP = {
        # Claude models
        'opus': ModelTier(quality=5, speed=1, context=5, overall=11),
        'sonnet': ModelTier(quality=4, speed=4, context=5, overall=13),
        'haiku': ModelTier(quality=3, speed=5, context=5, overall=13),

        # Ollama large models
        'llama3.3:70b': ModelTier(quality=4, speed=2, context=4, overall=10),
        'qwen2.5:72b': ModelTier(quality=4, speed=2, context=4, overall=10),
        'llama3.1:70b': ModelTier(quality=4, speed=2, context=4, overall=10),

        # Ollama medium models
        'devstral': ModelTier(quality=3, speed=3, context=2, overall=8),
        'codestral': ModelTier(quality=3, speed=3, context=2, overall=8),

        # Ollama small models
        'llama3.1:8b': ModelTier(quality=2, speed=4, context=1, overall=7),
        'llama3.2:3b': ModelTier(quality=2, speed=5, context=1, overall=8),
        'nemotron_mini_4b': ModelTier(quality=2, speed=5, context=1, overall=8),
    }

    def rank(self, models: List[AvailableModel]) -> List[RankedModel]:
        """Rank available models by capability"""
        ranked = []

        for model in models:
            tier = self.classify_model(model)
            ranked.append(RankedModel(
                model=model,
                tier=tier,
                rank_score=self.compute_rank_score(model, tier)
            ))

        # Sort by rank score (higher = better)
        ranked.sort(key=lambda m: m.rank_score, reverse=True)

        return ranked

    def classify_model(self, model: AvailableModel) -> ModelTier:
        """Classify model into tier"""
        # Try exact match first
        for pattern, tier in self.TIER_MAP.items():
            if pattern in model.name.lower():
                return tier

        # Default tier for unknown models
        return ModelTier(quality=2, speed=3, context=2, overall=7)

    def compute_rank_score(self, model: AvailableModel, tier: ModelTier) -> float:
        """Compute overall ranking score"""
        # Base score from tier
        score = tier.overall

        # Provider preference (slight bias toward Claude)
        if model.provider == 'bedrock':
            score += 1.0
        elif model.provider == 'api':
            score += 0.5

        # Context window bonus
        if model.context_window >= 200000:
            score += 2.0
        elif model.context_window >= 100000:
            score += 1.0

        return score
```

---

## Diverse Pair Selection

### Selection Strategies

```python
class DiversePairSelector:
    """Select two diverse models for dual generation"""

    def select_diverse_pair(self, ranked_models: List[RankedModel],
                           strategy: str = 'quality-spread') -> Tuple[RankedModel, RankedModel]:
        """Pick two models with maximum diversity"""

        if len(ranked_models) < 2:
            raise ValueError("Need at least 2 models for dual generation")

        if strategy == 'quality-spread':
            return self.select_quality_spread(ranked_models)
        elif strategy == 'provider-diversity':
            return self.select_provider_diversity(ranked_models)
        elif strategy == 'tier-diversity':
            return self.select_tier_diversity(ranked_models)
        else:
            # Default: top 2 by rank
            return ranked_models[0], ranked_models[1]

    def select_quality_spread(self, ranked: List[RankedModel]) -> Tuple[RankedModel, RankedModel]:
        """Pick best quality model + best speed model for diversity"""

        # Pick #1 overall (usually best quality)
        model_a = ranked[0]

        # Find model with different strength (high speed, not just #2)
        model_b = None
        for model in ranked[1:]:
            # Look for model that's fast OR from different provider
            if (model.tier.speed >= 4 or
                model.model.provider != model_a.model.provider):
                model_b = model
                break

        # Fallback to #2 if no diversity found
        if model_b is None:
            model_b = ranked[1]

        return model_a, model_b

    def select_provider_diversity(self, ranked: List[RankedModel]) -> Tuple[RankedModel, RankedModel]:
        """Pick models from different providers if possible"""

        model_a = ranked[0]

        # Find best model from different provider
        model_b = None
        for model in ranked[1:]:
            if model.model.provider != model_a.model.provider:
                model_b = model
                break

        # Fallback to same provider
        if model_b is None:
            model_b = ranked[1]

        return model_a, model_b

    def select_tier_diversity(self, ranked: List[RankedModel]) -> Tuple[RankedModel, RankedModel]:
        """Pick models from different quality tiers"""

        model_a = ranked[0]  # Highest quality

        # Find model with significantly different tier
        model_b = None
        for model in ranked[1:]:
            quality_diff = abs(model.tier.quality - model_a.tier.quality)
            if quality_diff >= 2:  # At least 2-tier difference
                model_b = model
                break

        if model_b is None:
            model_b = ranked[1]

        return model_a, model_b
```

---

## Configuration

```yaml
# prd-config.yaml
mode: dual-generation

dual_generation:
  selection_strategy: quality-spread  # or: provider-diversity, tier-diversity
  min_models_required: 2

  # Optional: Explicit model preferences (override auto-selection)
  prefer_providers: [bedrock, api, ollama]  # Preference order

  # Optional: Exclude specific models
  exclude_models: ['llama3.2:1b', 'gemma:2b']  # Too small

  # Optional: Minimum tier requirements
  min_tier:
    quality: 3  # Don't use quality < 3
    context: 2  # Don't use context < 2 (8K)

merge:
  strategy: best-sections
  # Merge model: use best available (usually model_a)
```

---

## Execution Flow

```python
class DualGenerationOrchestrator:
    """Orchestrate dual generation with dynamic model selection"""

    def execute(self, config: DualGenerationConfig) -> PRD:
        # 1. Discover available models
        atomic_info("Discovering available models...")
        discovery = ModelDiscovery()
        available = discovery.discover_all()

        if len(available) < config.min_models_required:
            atomic_error(f"Need {config.min_models_required} models, found {len(available)}")
            atomic_info("Available models:")
            for model in available:
                atomic_info(f"  - {model.provider}/{model.name}")
            return None

        # 2. Rank models
        atomic_info("Ranking models by capability...")
        ranker = ModelRanker()
        ranked = ranker.rank(available)

        # Show ranking
        atomic_info("Model ranking:")
        for i, model in enumerate(ranked[:5], 1):  # Top 5
            atomic_info(f"  {i}. {model.model.provider}/{model.model.name} "
                       f"(quality={model.tier.quality}, speed={model.tier.speed}, "
                       f"context={model.tier.context}, score={model.rank_score:.1f})")

        # 3. Select diverse pair
        atomic_info(f"Selecting diverse pair (strategy: {config.selection_strategy})...")
        selector = DiversePairSelector()
        model_a, model_b = selector.select_diverse_pair(ranked, config.selection_strategy)

        atomic_info(f"Approach A: {model_a.model.provider}/{model_a.model.name}")
        atomic_info(f"Approach B: {model_b.model.provider}/{model_b.model.name}")

        # 4. Configure approaches
        approach_a_config = self.create_approach_config(model_a, "approach_a")
        approach_b_config = self.create_approach_config(model_b, "approach_b")

        # 5. Run dual generation
        return self.run_dual_generation(approach_a_config, approach_b_config)

    def create_approach_config(self, ranked_model: RankedModel, name: str) -> ApproachConfig:
        """Create approach config based on model capabilities"""

        model = ranked_model.model

        # Adapt strategy based on model context window
        if model.context_window >= 100000:
            context_strategy = 'full'
        elif model.context_window >= 30000:
            context_strategy = 'structured'
        else:
            context_strategy = 'minimal'

        return ApproachConfig(
            name=name,
            provider=model.provider,
            model=model.model_id,
            context=context_strategy,
            # Other settings use defaults
        )
```

---

## Example Scenarios

### Scenario 1: Cloud Environment (Bedrock + API)

**Available**:
```
bedrock/claude-opus-4-5      (quality=5, speed=1, context=5, score=14.0)
bedrock/claude-sonnet-4-5    (quality=4, speed=4, context=5, score=14.0)
api/claude-sonnet-4          (quality=4, speed=4, context=5, score=13.5)
api/claude-haiku-4           (quality=3, speed=5, context=5, score=13.5)
```

**Selected (quality-spread)**:
- Approach A: `bedrock/claude-opus-4-5` (best quality)
- Approach B: `bedrock/claude-sonnet-4-5` (best speed)

**Configuration**:
```yaml
approach_a:
  provider: bedrock
  model: claude-opus-4-5
  context: full  # 200K window

approach_b:
  provider: bedrock
  model: claude-sonnet-4-5
  context: full  # 200K window
```

---

### Scenario 2: Airgapped Environment (Ollama Only)

**Available**:
```
ollama/llama3.3:70b      (quality=4, speed=2, context=4, score=10.0)
ollama/devstral:latest   (quality=3, speed=3, context=2, score=8.0)
ollama/llama3.1:8b       (quality=2, speed=4, context=1, score=7.0)
```

**Selected (quality-spread)**:
- Approach A: `ollama/llama3.3:70b` (best quality)
- Approach B: `ollama/devstral:latest` (faster, different tier)

**Configuration**:
```yaml
approach_a:
  provider: ollama
  model: llama3.3:70b
  context: full  # 128K window

approach_b:
  provider: ollama
  model: devstral:latest
  context: structured  # 32K window
```

---

### Scenario 3: Hybrid Environment (Bedrock + Ollama)

**Available**:
```
bedrock/claude-sonnet-4-5  (quality=4, speed=4, context=5, score=14.0)
ollama/llama3.3:70b        (quality=4, speed=2, context=4, score=10.0)
ollama/devstral:latest     (quality=3, speed=3, context=2, score=8.0)
```

**Selected (provider-diversity)**:
- Approach A: `bedrock/claude-sonnet-4-5` (best overall)
- Approach B: `ollama/llama3.3:70b` (different provider)

**Configuration**:
```yaml
approach_a:
  provider: bedrock
  model: claude-sonnet-4-5
  context: full

approach_b:
  provider: ollama
  model: llama3.3:70b
  context: full
```

---

## CLI Output

```bash
$ python main.py run 2 --dual-generation

=== PRD Authoring (Dual Generation Mode) ===

Discovering available models...
Found 5 models across 2 providers

Ranking models by capability...
Model ranking:
  1. bedrock/claude-opus-4-5 (quality=5, speed=1, context=5, score=14.0)
  2. bedrock/claude-sonnet-4-5 (quality=4, speed=4, context=5, score=14.0)
  3. ollama/llama3.3:70b (quality=4, speed=2, context=4, score=10.0)
  4. ollama/devstral:latest (quality=3, speed=3, context=2, score=8.0)
  5. ollama/llama3.1:8b (quality=2, speed=4, context=1, score=7.0)

Selecting diverse pair (strategy: quality-spread)...
Approach A: bedrock/claude-opus-4-5 (best quality)
Approach B: bedrock/claude-sonnet-4-5 (best speed)

Configuring approaches...
  Approach A: full context (200K window)
  Approach B: full context (200K window)

[============================] Approach A: Gen 1/8 complete (180s)
[============================] Approach B: Gen 1/8 complete (120s)
...

✅ Approach A complete: 45 minutes
✅ Approach B complete: 25 minutes

=== Audit & Merge ===
...
```

---

## Benefits

1. **Environment-agnostic**: Works with any provider combination
2. **No hardcoded assumptions**: Discovers what's actually available
3. **Automatic adaptation**: Context strategy matches model capabilities
4. **True diversity**: Picks models with different strengths
5. **Graceful degradation**: Works with 2+ models of any type

---

## Fallback Behavior

**If only 1 model available**:
```
⚠️  Only 1 model found, dual generation requires 2+
Falling back to single-generation mode with: bedrock/claude-sonnet-4-5
```

**If no models available**:
```
❌ No models discovered
Please configure at least one provider:
  - Bedrock: Set AWS_REGION
  - API: Set ANTHROPIC_API_KEY
  - Ollama: Install and start ollama
```

---

## Summary

**Key Innovation**: Don't assume specific models exist → Discover and rank dynamically

**Process**:
1. Discover available models (all providers)
2. Rank by capability tier (quality, speed, context)
3. Select diverse pair (different strengths)
4. Adapt configuration to model capabilities
5. Run dual generation

**Result**: Works in any environment (cloud, airgapped, hybrid) with any model combination

---

**This is the right approach?** Now we're truly flexible - no assumptions about what models are available, just discover and pick the best diverse pair.
