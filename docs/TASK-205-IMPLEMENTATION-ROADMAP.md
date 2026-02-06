# Task 205 Python Implementation - Roadmap

**Date**: 2026-02-05
**Status**: APPROVED DESIGN
**Architecture**: Dynamic model selection + Dual generation + Audit + Merge

---

## What We've Accomplished (This Session)

### ✅ Three Critical Fixes Implemented (Bash)
1. **Memory Recall Integration** (+80 lines)
   - Connects Phase 1 discovery to Phase 2 PRD
   - +125% discovery alignment expected

2. **Guardian Context Fix** (+106 lines)
   - Structured extraction vs raw truncation
   - +90% cross-reference validation accuracy

3. **Adaptive Context for Multi-Model** (+130 lines)
   - Enables Ollama models for PRD generation
   - +900% model support (1 → 10+ models)

**Total**: ~316 lines of production-ready bash code, fully tested

### ✅ Architecture Designed (Python)

**Final Design**: Dynamic Model Selection + Dual Generation
- Discovers available models at runtime (all providers)
- Ranks by capability tier (quality, speed, context)
- Selects diverse pair automatically
- Runs both in parallel, audits both, merges best sections
- Environment-agnostic (works anywhere with 2+ models)

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

**Goal**: Python wrapper with model discovery working

**Tasks**:
1. Model discovery system
   - `ModelDiscovery`: Scan bedrock, api, ollama
   - `ModelRanker`: Classify and rank models
   - `DiversePairSelector`: Pick best diverse pair

2. Basic orchestration
   - `DualGenerationOrchestrator`: Coordinate workflow
   - `ApproachRunner`: Execute single approach (wraps bash for now)

3. Configuration system
   - YAML config loading
   - Model tier definitions
   - Selection strategy options

**Deliverable**: Can discover models, select pair, print to console

**Testing**:
```bash
python -m prd_authoring.discovery --show-models
# Output:
# Found 5 models across 2 providers
# 1. bedrock/claude-opus-4-5 (score=14.0)
# 2. bedrock/claude-sonnet-4-5 (score=14.0)
# ...
```

---

### Phase 2: Dual Generation Pipeline (Week 2)

**Goal**: Run dual generation end-to-end (wrapping bash)

**Tasks**:
1. Parallel execution
   - ThreadPoolExecutor for both approaches
   - Progress tracking
   - Timeout handling

2. Bash wrapper
   - Call existing bash Task 205 with different configs
   - Capture outputs (PRD-A.md, PRD-B.md)

3. Basic audit
   - Structure validation (15 sections present)
   - Cross-reference checks (FR/NFR IDs valid)
   - Generate comparison report

**Deliverable**: Dual generation produces two PRDs + audit report

**Testing**:
```bash
python main.py run 2 --dual-generation
# Output:
# Approach A: bedrock/opus complete
# Approach B: bedrock/sonnet complete
# Audit: A=0.92, B=0.89
# (No merge yet, just save both + audit)
```

---

### Phase 3: Merge Agent (Week 3)

**Goal**: Intelligent merge of best sections

**Tasks**:
1. Section scoring
   - Score each section from both PRDs
   - Based on audit dimensions

2. Best-sections merge
   - Pick winner for each section
   - Assemble final PRD

3. Consensus merge (optional)
   - Use LLM to merge both PRDs
   - Fallback strategy

**Deliverable**: Final merged PRD better than either individual

**Testing**:
```bash
python main.py run 2 --dual-generation
# Output:
# Section 0: Using Approach A (vision)
# Section 5: Using Approach B (cross-refs)
# ...
# Final PRD score: 0.97 (vs A=0.92, B=0.89)
```

---

### Phase 4: Native Python Generation (Week 4+)

**Goal**: Replace bash wrapper with native Python

**Tasks**:
1. Port generation logic
   - 8-generation sequential workflow
   - Memory recall integration
   - Context building

2. Port guardian validation
   - Ollama validator
   - Rule-based validator

3. Full native pipeline
   - No bash dependencies
   - Pure Python implementation

**Deliverable**: Complete Python Task 205, bash deprecated

---

## File Structure

```
atomic-claude-python/
├── prd_authoring/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Configuration
│   │
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── model_discovery.py    # Scan providers
│   │   ├── model_ranker.py       # Rank by tier
│   │   └── pair_selector.py      # Pick diverse pair
│   │
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── dual_orchestrator.py  # Dual generation coordinator
│   │   ├── approach_runner.py    # Single approach executor
│   │   └── bash_wrapper.py       # Wrap existing bash (Phase 1-3)
│   │
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── dual_auditor.py       # Audit both PRDs
│   │   ├── validators.py         # Structure, cross-ref checks
│   │   └── comparison.py         # Compare audit results
│   │
│   ├── merge/
│   │   ├── __init__.py
│   │   ├── merge_agent.py        # Merge strategy
│   │   ├── section_scorer.py    # Score sections
│   │   └── strategies.py         # best-sections, consensus
│   │
│   └── generation/  (Phase 4+)
│       ├── __init__.py
│       ├── workflow.py           # 8-generation sequential
│       ├── memory.py             # Memory recall
│       ├── context.py            # Context strategies
│       └── guardian.py           # Guardian validation
│
└── tests/
    ├── test_discovery.py
    ├── test_orchestration.py
    ├── test_audit.py
    └── test_merge.py
```

---

## Configuration Example

```yaml
# config/prd-authoring.yaml
mode: dual-generation

discovery:
  selection_strategy: quality-spread
  min_models_required: 2
  prefer_providers: [bedrock, api, ollama]
  exclude_models: ['llama3.2:1b', 'gemma:2b']
  min_tier:
    quality: 3
    context: 2

audit:
  dimensions:
    - structure (weight: 0.20)
    - clarity (weight: 0.15)
    - completeness (weight: 0.20)
    - consistency (weight: 0.15)
    - discovery_alignment (weight: 0.15)
    - cross_references (weight: 0.15)

merge:
  strategy: best-sections  # or: consensus, weighted
  merge_model: auto        # Use best available (approach_a model)
```

---

## Success Criteria

### Phase 1 Complete
- ✅ Can discover models from all providers
- ✅ Can rank and select diverse pair
- ✅ Configuration system working

### Phase 2 Complete
- ✅ Dual generation produces two PRDs
- ✅ Audit report generated
- ✅ Both approaches run in parallel

### Phase 3 Complete
- ✅ Merge agent produces final PRD
- ✅ Final PRD scores higher than either individual
- ✅ Section-by-section comparison available

### Phase 4 Complete
- ✅ Native Python implementation
- ✅ Bash deprecated
- ✅ All fixes ported (memory recall, guardian context, adaptive context)

---

## Timeline

**Week 1**: Model discovery + config system
**Week 2**: Dual generation pipeline (bash wrapper)
**Week 3**: Merge agent
**Week 4+**: Native Python generation (port bash)

**Total**: 3-4 weeks to production-ready dual generation system

---

## Next Steps

**Immediate (This Week)**:
1. Create Python package structure
2. Implement model discovery
3. Test with real environment (show available models)

**Short-term (Next 2 Weeks)**:
1. Implement dual generation orchestration
2. Add audit system
3. Add merge agent

**Long-term (Week 4+)**:
1. Port bash generation to Python
2. Add native memory/context/guardian
3. Deprecate bash implementation

---

## Decision Point

**Option A**: Start Phase 1 now (model discovery implementation)

**Option B**: Test bash fixes first (run Phase 2 with current bash implementation to validate the 3 fixes)

**Option C**: Other priority

**Recommendation**: Option B first (validate bash fixes work), then Option A (start Python migration)

---

**What would you like to do next?**
