# Task 205 Dual Generation Architecture - Best of Both Worlds

**Date**: 2026-02-05
**Status**: DESIGN PROPOSAL v2
**Goal**: Run two approaches in parallel, merge best elements

---

## Core Insight

**User's realization**: Pipeline runs 1-100 times total (not thousands). No historical data for A/B testing.

**Better approach**: For each PRD generation:
1. Run **Approach A** (e.g., Sonnet + structured context + claude-mem)
2. Run **Approach B** (e.g., Opus + full context + sqlite)
3. **Audit both** (document-guardian validates each)
4. **Merge best elements** (merge-agent picks winners)

**Result**: Every PRD run teaches us which approach works better through diversity of strategies.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Task 205: PRD Authoring                    │
└─────────────────────────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │   Dual Generation Mode  │
            │    (if enabled)         │
            └────────────┬────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌─────────────────┐            ┌─────────────────┐
│   Approach A    │            │   Approach B    │
│   (Bedrock)     │            │   (Ollama)      │
│                 │            │                 │
│ - claude-mem    │            │ - simple-file   │
│ - structured    │            │ - minimal       │
│ - ollama guard  │            │ - rule-based    │
│ - 8-gen seq     │            │ - 8-gen seq     │
└────────┬────────┘            └────────┬────────┘
         │                               │
         │ PRD-A.md                     │ PRD-B.md
         │                               │
         └───────────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  Audit Process   │
              │  (both PRDs)     │
              └──────────┬───────┘
                         │
                         ▼
              ┌──────────────────┐
              │   Merge Agent    │
              │  (best of both)  │
              └──────────┬───────┘
                         │
                         ▼
                   PRD-FINAL.md
```

---

## Configuration

```yaml
# prd-config.yaml
mode: dual-generation  # or: single-generation

dual_generation:
  approach_a:
    name: "conservative"
    provider: bedrock
    model: claude-sonnet-4-5
    memory: claude-mem
    context: structured
    guardian: ollama-validator

  approach_b:
    name: "experimental"
    provider: bedrock  # Or api, ollama - doesn't matter
    model: claude-opus-4-5  # Different model = different strengths
    memory: sqlite          # Different backend
    context: full           # Different strategy
    guardian: rule-based    # Different validator

  merge:
    agent: merge-master
    provider: bedrock  # Or api, ollama - pick best available
    model: claude-sonnet-4-5
    strategy: best-sections  # or: consensus, weighted
```

---

## Dual Generation Workflow

### Phase 1: Parallel Generation

```python
class DualGenerationOrchestrator:
    """Run both approaches in parallel, collect results"""

    def execute(self, config: DualGenerationConfig) -> DualResult:
        # Start both approaches in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(self.run_approach, config.approach_a)
            future_b = executor.submit(self.run_approach, config.approach_b)

            # Wait for both (with timeout)
            try:
                result_a = future_a.result(timeout=3600)  # 1 hour max
            except TimeoutError:
                atomic_error("Approach A timed out")
                result_a = None

            try:
                result_b = future_b.result(timeout=3600)
            except TimeoutError:
                atomic_error("Approach B timed out")
                result_b = None

        # If one failed, return the successful one
        if result_a is None:
            return result_b
        if result_b is None:
            return result_a

        # Both succeeded, proceed to audit
        return self.audit_and_merge(result_a, result_b, config)
```

### Phase 2: Audit Process

```python
class DualAuditor:
    """Audit both PRD outputs, identify strengths/weaknesses"""

    def audit_both(self, prd_a: PRD, prd_b: PRD) -> AuditReport:
        """Audit both PRDs independently"""

        # Audit Approach A
        audit_a = self.audit_single(prd_a, approach_name="Bedrock")

        # Audit Approach B
        audit_b = self.audit_single(prd_b, approach_name="Ollama")

        # Compare
        comparison = self.compare_audits(audit_a, audit_b)

        return AuditReport(
            audit_a=audit_a,
            audit_b=audit_b,
            comparison=comparison
        )

    def audit_single(self, prd: PRD, approach_name: str) -> SingleAudit:
        """Audit single PRD for quality"""

        issues = []
        scores = {}

        # Structure validation
        scores['structure'] = self.check_structure(prd)
        if scores['structure'] < 0.9:
            issues.append(f"{approach_name}: Missing sections or formatting issues")

        # Content quality
        scores['clarity'] = self.check_clarity(prd)
        scores['completeness'] = self.check_completeness(prd)
        scores['consistency'] = self.check_consistency(prd)

        # Discovery alignment (if memory available)
        scores['discovery_alignment'] = self.check_discovery_alignment(prd)

        # Cross-reference validation (critical for TaskMaster)
        scores['cross_references'] = self.check_cross_references(prd)
        if scores['cross_references'] < 0.95:
            issues.append(f"{approach_name}: Broken FR/NFR references in dependency chain")

        return SingleAudit(
            approach=approach_name,
            scores=scores,
            overall_score=sum(scores.values()) / len(scores),
            issues=issues
        )

    def compare_audits(self, audit_a: SingleAudit, audit_b: SingleAudit) -> Comparison:
        """Compare two audits, identify which is better per dimension"""

        winners = {}
        for dimension in ['structure', 'clarity', 'completeness', 'consistency',
                          'discovery_alignment', 'cross_references']:
            score_a = audit_a.scores[dimension]
            score_b = audit_b.scores[dimension]

            if abs(score_a - score_b) < 0.05:
                winners[dimension] = 'tie'
            elif score_a > score_b:
                winners[dimension] = 'approach_a'
            else:
                winners[dimension] = 'approach_b'

        return Comparison(
            winners=winners,
            score_diff=audit_a.overall_score - audit_b.overall_score,
            recommendation=self.make_recommendation(audit_a, audit_b)
        )
```

### Phase 3: Merge Agent

```python
class MergeAgent:
    """Intelligent merge of two PRD outputs"""

    def merge(self, prd_a: PRD, prd_b: PRD, audit_report: AuditReport) -> PRD:
        """Merge best elements from both PRDs"""

        strategy = self.config.merge.strategy

        if strategy == 'best-sections':
            return self.merge_best_sections(prd_a, prd_b, audit_report)
        elif strategy == 'consensus':
            return self.merge_consensus(prd_a, prd_b)
        elif strategy == 'weighted':
            return self.merge_weighted(prd_a, prd_b, audit_report)
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")

    def merge_best_sections(self, prd_a: PRD, prd_b: PRD,
                            audit_report: AuditReport) -> PRD:
        """Pick best section from each PRD based on audit scores"""

        merged_sections = {}

        for section_num in range(15):
            # Get audit scores for this section from both PRDs
            score_a = self.score_section(prd_a.sections[section_num], audit_report.audit_a)
            score_b = self.score_section(prd_b.sections[section_num], audit_report.audit_b)

            # Pick winner
            if score_a > score_b:
                merged_sections[section_num] = prd_a.sections[section_num]
                source = 'approach_a'
            else:
                merged_sections[section_num] = prd_b.sections[section_num]
                source = 'approach_b'

            atomic_info(f"Section {section_num}: Using {source} (score: {max(score_a, score_b):.2f})")

        # Assemble final PRD
        return PRD(sections=merged_sections, metadata={
            'merge_strategy': 'best-sections',
            'audit_report': audit_report
        })

    def merge_consensus(self, prd_a: PRD, prd_b: PRD) -> PRD:
        """Use LLM to generate consensus PRD from both inputs"""

        prompt = f"""
You are the merge-agent. You have two PRD outputs for the same project:

## PRD from Approach A (Bedrock)
{prd_a.full_text}

## PRD from Approach B (Ollama)
{prd_b.full_text}

## Task
Generate a FINAL PRD that takes the best elements from both:
- Use the clearer vision statement
- Use the more complete feature requirements
- Use the better technical architecture
- Ensure all cross-references are valid
- Maintain 15-section structure

Output ONLY the merged PRD markdown.
"""

        # Call Ollama (free!) for merge
        result = atomic_invoke_ollama(prompt, model='llama3.3:70b')

        return PRD.from_markdown(result)
```

---

## Audit Dimensions

The audit process evaluates both PRDs on:

### 1. Structure (Weight: 20%)
- ✅ All 15 sections present
- ✅ Correct section numbering
- ✅ Proper markdown formatting
- ✅ Section ordering correct

### 2. Clarity (Weight: 15%)
- ✅ Vision statement is clear
- ✅ Requirements are unambiguous
- ✅ Technical terms defined
- ✅ No jargon without explanation

### 3. Completeness (Weight: 20%)
- ✅ All required subsections present
- ✅ FR count: 10-30 (not too few, not too many)
- ✅ NFR count: 8-15
- ✅ Tech stack fully specified
- ✅ Dependency chain covers all FRs/NFRs

### 4. Consistency (Weight: 15%)
- ✅ Tech stack doesn't change across sections
- ✅ Terminology consistent throughout
- ✅ FR/NFR IDs sequential (no gaps)
- ✅ References use same IDs

### 5. Discovery Alignment (Weight: 15%)
- ✅ Vision reflects Phase 1 goals
- ✅ FRs trace to discovery features
- ✅ Tech stack matches discovery recommendations
- ✅ NFRs address discovery constraints

### 6. Cross-References (Weight: 15%)
- ✅ Section 5 dependency chain: All FR/NFR IDs exist
- ✅ Section 6 development phases: All FR/NFR references valid
- ✅ Section 9 integration tests: Valid FR references
- **CRITICAL**: Broken cross-refs = TaskMaster failure

**Overall Score**: Weighted average of all dimensions

---

## Example Scenario

### Inputs

**Approach A (Sonnet 4.5 + claude-mem + structured context)**:
- Generation time: 25 minutes
- Model: claude-sonnet-4-5 (balanced speed/quality)
- Strengths: Excellent vision, complete FRs, good discovery alignment
- Weaknesses: Tech stack has 2 inconsistencies, Section 5 has 3 broken cross-refs

**Approach B (Opus 4.5 + sqlite + full context)**:
- Generation time: 45 minutes
- Model: claude-opus-4-5 (maximum reasoning)
- Strengths: Perfect cross-references, tech stack 100% consistent, Section 5 is excellent
- Weaknesses: Vision is generic (overthinks), FRs less detailed, missing 2 NFRs

### Audit Scores

| Dimension | Approach A | Approach B | Winner |
|-----------|-----------|-----------|---------|
| Structure | 1.0 | 1.0 | Tie |
| Clarity | 0.95 | 0.85 | A |
| Completeness | 0.90 | 0.80 | A |
| Consistency | 0.85 | 1.0 | **B** |
| Discovery Alignment | 0.95 | 0.70 | A |
| Cross-References | 0.85 | 1.0 | **B** |
| **Overall** | **0.92** | **0.89** | A |

### Merge Decision (Best-Sections Strategy)

```
Section 0 (Vision): Use Approach A (better discovery alignment)
Section 1 (Executive): Use Approach A (clearer)
Section 2 (Tech Architecture): Use Approach B (consistent tech stack)
Section 3 (FRs): Use Approach A (more complete)
Section 4 (NFRs): Use Approach A (covers more dimensions)
Section 5 (Dependency Chain): Use Approach B (perfect cross-refs) ✅ CRITICAL
Section 6 (Dev Phases): Use Approach B (references valid)
Section 7-9 (Implementation): Use Approach A (more detailed)
Section 10-14 (Operations): Use Approach B (better risk coverage)

Final PRD: Hybrid of both approaches
Overall Score: 0.97 (better than either individual)
```

### Insights for Next Run

**Learned**:
- Opus is better at cross-reference consistency
- Sonnet is better at discovery alignment and content quality
- Full context works better for structural sections (5-6)
- Structured context sufficient for content sections (0-4)

**Next time**:
- Try: Sonnet for Gen 1-4, Opus for Gen 5-8 (hybrid workflow)
- Or: Try different memory backends (sqlite vs claude-mem)
- Or: Stay dual permanently if merge consistently produces better results

---

## Diversity Examples

### Example 1: Model Diversity

```yaml
approach_a:
  model: claude-sonnet-4-5  # Fast, balanced
  strengths: Speed, good general quality

approach_b:
  model: claude-opus-4-5    # Slow, maximum reasoning
  strengths: Complex logic, cross-references, consistency
```

**Insight**: Sonnet excels at content, Opus excels at structure

### Example 2: Context Strategy Diversity

```yaml
approach_a:
  context: structured  # Tech stack + FR/NFR lists
  strengths: Efficient, includes key elements

approach_b:
  context: full        # Complete prior sections
  strengths: Maximum context, can reference any detail
```

**Insight**: Full context produces more coherent narrative

### Example 3: Memory Backend Diversity

```yaml
approach_a:
  memory: claude-mem   # Semantic search
  strengths: Finds relevant memories intelligently

approach_b:
  memory: sqlite       # Full-text search
  strengths: Fast keyword retrieval, no false positives
```

**Insight**: claude-mem better for fuzzy matching, sqlite better for exact references

---

## Implementation Strategy

### Option 1: Dual Mode Always Enabled (Recommended)

```yaml
# Default config
mode: dual-generation

# Why: Same cost, better results, continuous learning
```

**Benefits**:
- Every PRD run validates which approach is better
- Merge produces better output than either alone
- No extra cost (Ollama is free)
- Builds intuition about what works

**Drawback**: Takes longer (both run in parallel, but slower approach determines total time)

### Option 2: Dual Mode for First N PRDs

```yaml
mode: dual-generation
dual_until: 10  # Switch to single after 10 PRDs

# After 10 PRDs, have data to pick winner
```

**Benefits**:
- Fast learning (10 comparisons = clear pattern)
- Can switch to single-generation with confidence

### Option 3: User-Controlled Dual Mode

```bash
# Dual generation (thorough)
python main.py run 2 --dual-generation

# Single generation (fast)
python main.py run 2

# Default: single (fast iteration)
```

---

## Modular Architecture (Simplified)

Since we're doing within-task comparison (not long-term A/B testing), architecture simplifies:

```python
# prd_authoring/orchestrator.py
class PRDOrchestrator:
    """Main entry point"""

    def execute(self, config: PRDConfig) -> PRD:
        if config.mode == 'dual-generation':
            return self.dual_generation(config)
        else:
            return self.single_generation(config)

    def single_generation(self, config: PRDConfig) -> PRD:
        """Run one approach (fast)"""
        approach = ApproachRunner(config.approach_a)
        return approach.run()

    def dual_generation(self, config: DualGenerationConfig) -> PRD:
        """Run both approaches, merge best (thorough)"""

        # Run both in parallel
        results = self.run_parallel(config.approach_a, config.approach_b)

        # Audit both
        audit_report = DualAuditor().audit_both(results.prd_a, results.prd_b)

        # Show comparison to user
        self.display_comparison(audit_report)

        # Merge best elements
        merged_prd = MergeAgent().merge(results.prd_a, results.prd_b, audit_report)

        # Save all artifacts
        self.save_artifacts(results, audit_report, merged_prd)

        return merged_prd

# prd_authoring/approach_runner.py
class ApproachRunner:
    """Runs a single approach (configurable components)"""

    def __init__(self, config: ApproachConfig):
        self.memory = get_memory_backend(config.memory)
        self.context = get_context_strategy(config.context)
        self.guardian = get_guardian_validator(config.guardian)
        self.workflow = get_workflow(config.workflow)

    def run(self) -> PRD:
        """Execute PRD generation with configured components"""
        return self.workflow.execute(
            memory=self.memory,
            context=self.context,
            guardian=self.guardian
        )
```

**Key difference from v1**:
- ❌ Remove long-term metrics, historical comparison, experiment runners
- ✅ Keep plugin system (approach_a and approach_b have different configs)
- ✅ Add audit + merge layer
- ✅ Focus on diversity of approaches, not cost optimization

---

## User Experience

### CLI Output (Dual Generation Mode)

```bash
$ python main.py run 2 --dual-generation

=== PRD Authoring (Dual Generation Mode) ===

Approach A: Sonnet 4.5 + claude-mem + structured context
Approach B: Opus 4.5 + sqlite + full context

[============================] Approach A: Gen 1/8 complete (120s)
[=================           ] Approach B: Gen 1/8 running...
[============================] Approach A: Gen 2/8 complete (95s)
[============================] Approach B: Gen 1/8 complete (180s)
...

✅ Approach A complete: 25 minutes
✅ Approach B complete: 45 minutes

=== Audit Results ===

Approach A (Sonnet 4.5):
  Structure:           ✅ 1.00
  Clarity:             ✅ 0.95
  Completeness:        ✅ 0.90
  Consistency:         ⚠️  0.85 (tech stack has 2 inconsistencies)
  Discovery Alignment: ✅ 0.95
  Cross-References:    ⚠️  0.85 (3 broken refs in Section 5)
  Overall:             ✅ 0.92

Approach B (Opus 4.5):
  Structure:           ✅ 1.00
  Clarity:             ⚠️  0.85 (overly verbose)
  Completeness:        ⚠️  0.80 (missing 2 NFRs)
  Consistency:         ✅ 1.00
  Discovery Alignment: ⚠️  0.70 (generic vision)
  Cross-References:    ✅ 1.00 (perfect!)
  Overall:             ✅ 0.89

Winner by dimension:
  - Vision/Clarity: Approach A
  - Tech Stack Consistency: Approach B
  - Cross-References: Approach B ✅ (critical for TaskMaster)

=== Merging Best Elements ===

Section 0: Using Approach A (better vision)
Section 1: Using Approach A (clearer executive summary)
Section 2: Using Approach B (consistent tech stack)
Section 3: Using Approach A (more complete FRs)
Section 4: Using Approach A (better NFR coverage)
Section 5: Using Approach B (perfect cross-refs) ✅ CRITICAL
Section 6: Using Approach B (valid phase references)
Sections 7-9: Using Approach A (detailed implementation)
Sections 10-14: Using Approach B (better risk analysis)

✅ Final PRD created: docs/prd/PRD.md
   Overall score: 0.97 (better than either individual)

=== Artifacts Saved ===
- .outputs/2-prd/PRD-approach-a.md (Bedrock output)
- .outputs/2-prd/PRD-approach-b.md (Ollama output)
- .outputs/2-prd/PRD-audit-report.json (detailed audit)
- .outputs/2-prd/PRD-comparison.md (human-readable comparison)
- docs/prd/PRD.md (final merged output)

=== Key Learnings ===
✅ Opus excels at structural consistency and cross-references
✅ Sonnet excels at content quality and discovery alignment
💡 Consider: Sonnet for content-heavy sections (0-4), Opus for structural sections (5-8)
```

---

## Benefits of This Approach

### 1. Diversity of Perspectives
- Different models have different strengths
- Sonnet: Fast, balanced, good content
- Opus: Slow, deep reasoning, structural consistency
- Merge combines strengths of both

### 2. Continuous Learning
- Every PRD run teaches which approach is better
- Build intuition after 5-10 PRD generations
- Can confidently pick winner or stay dual

### 3. Risk Mitigation
- If Approach A has issues → Approach B result available
- If Approach B produces poor output → Approach A result available
- Merge can salvage both

### 4. Safe Experimentation
- Try different strategies (context, memory, guardian)
- One approach provides safety net
- Merge picks best elements

### 5. TaskMaster Reliability
- Cross-reference validation from both approaches
- Merge agent prioritizes structural correctness
- Phase 3 parsing more reliable

---

## Summary

**Key Innovation**: Run two approaches in parallel for SAME PRD, merge best elements

**Approaches**:
- **Approach A**: One configuration (e.g., Sonnet + structured context + claude-mem)
- **Approach B**: Different configuration (e.g., Opus + full context + sqlite)
- **Key**: Diversity of strategies, not cost savings

**Process**:
1. Generate both PRDs in parallel (~45 min total, limited by slower approach)
2. Audit both independently (structure, clarity, completeness, consistency, discovery, cross-refs)
3. Merge best sections (intelligent section-by-section selection)

**Result**: Better PRD than either approach alone, continuous learning about what works

**Recommendation**: Enable dual-generation by default, review comparison reports to build intuition

---

**Ready to implement?** This is much simpler than v1 (no long-term metrics, just audit + merge), and addresses your core concern: experiment safely without accumulating tech debt through diversity of approaches.
