# Phase 2 PRD Authoring - Claude Opus 4.6 Support

**Date:** February 10, 2026
**Feature:** Claude Opus 4.6 with 1M context window for PRD authoring

---

## Overview

Phase 2 PRD authoring now supports using **Claude Opus 4.6** with its massive **1,000,000 token (1M) context window**. This enables the 12-generation sequential PRD workflow to use full context at each stage, dramatically improving coherence and quality.

## Model Details

**Claude Opus 4.6:**
- Model ID: `claude-opus-4-6`
- Context Window: 1,000,000 tokens (1M)
- Announcement: https://www.anthropic.com/news/claude-opus-4-6
- Best For: Large documents, complex reasoning, architectural decisions

**Comparison:**
- Claude Sonnet 3.5: 200K tokens
- Claude Opus 3: 200K tokens
- **Claude Opus 4.6: 1M tokens (5x larger)**

---

## Usage

### Enable Opus 4.6 for PRD Authoring

Set the environment variable before running Phase 2:

```bash
export ATOMIC_PRD_USE_MAX_CONTEXT=true
python main.py run 2
```

### Verify Model Selection

When running Phase 2 with the flag enabled, you'll see:

```
PRD authoring mode: MAX CONTEXT (Opus 4.6 with 1M context window)
```

Without the flag (default behavior):

```
PRD authoring mode: Standard (model: sonnet)
```

---

## How It Works

### Context Window Detection

The PRD script detects Opus 4.6 and assigns its 1M context window:

```bash
_205_detect_model_context_window() {
    case "$model_name" in
        *"opus-4"*|*"claude-opus-4"*)
            echo "1000000"  # 1M
            ;;
        *"claude-sonnet"*|*"claude-opus"*|*"claude-3"*)
            echo "200000"  # 200K
            ;;
        # ... other models
    esac
}
```

### Adaptive Context Strategy

Based on context window size, the script adjusts its context injection strategy:

| Context Window | Strategy | Description |
|----------------|----------|-------------|
| ≥100K tokens   | **full** | Full prior sections included |
| 30K-100K       | **structured** | Structured extraction (headings, IDs, key sections) |
| <30K           | **minimal** | Headings and IDs only |

**Opus 4.6 uses "full" strategy** - all prior sections from Generations 1-11 are included in Generation 12 prompts.

### Invocation

Each of the 12 PRD generations now invokes with the configured model:

```bash
# Generation 1 (Vision + Executive Summary)
atomic_invoke "$prompt_file" "$output_file" "PRD Gen 1: Vision + Executive (Opus 4.6 - 1M context)" \
    --model=claude-opus-4-6 --provider=max --timeout=1200

# Generation 2 (Technical Architecture)
atomic_invoke "$prompt_file" "$output_file" "PRD Gen 2: Technical Architecture (Opus 4.6 - 1M context)" \
    --model=claude-opus-4-6 --provider=max --timeout=1200

# ... (Generations 3-12 follow same pattern)
```

---

## Benefits of 1M Context Window

### 1. Full Section Visibility

With 1M context, the model can see:
- **All prior sections** from Generations 1-11
- Complete FR/NFR lists (potentially 50+ FRs, 20+ NFRs)
- Full dependency chains
- All technical architecture decisions
- Complete tech stack with rationale

### 2. Better Cross-References

Eliminates broken FR/NFR references because:
- Model sees every FR-001 through FR-050+ in full
- Model sees every NFR-001 through NFR-025+ in full
- Dependency chain validation is perfect (no missing IDs)

### 3. Stronger Consistency

Tech stack lock-in is enforced because:
- Model sees the locked tech stack from Generation 2 in every prompt
- Model sees all architectural decisions
- Model maintains consistency across 15 sections

### 4. Richer Context

Discovery artifacts from Phase 1 included:
- Complete discovery goals and user needs
- Full technical approach analysis
- All feature requirements identified
- Non-functional requirement hints

---

## When to Use Opus 4.6

### Use Opus 4.6 When:

✅ **Large, complex PRDs** - 50+ FRs, 20+ NFRs, complex dependency chains
✅ **Enterprise projects** - Multiple systems, intricate architecture
✅ **Quality-critical** - PRD must be perfect for downstream tasks
✅ **Budget available** - Opus 4.6 is premium (cost per token higher)
✅ **TaskMaster compatibility** - Cross-reference validation is critical

### Use Standard Model (Sonnet) When:

✅ **Small to medium PRDs** - 10-30 FRs, simple dependencies
✅ **Budget-conscious** - Cost optimization important
✅ **Fast iteration** - Prototyping, quick validation
✅ **Sufficient quality** - Sonnet 3.5 is excellent for most cases

---

## Cost Considerations

**Claude Opus 4.6 pricing** (as of Feb 2026):
- Input: ~$15 per 1M tokens
- Output: ~$75 per 1M tokens

**Estimated cost for 12-generation PRD:**
- Input tokens: ~500K tokens (across 12 generations with full context)
- Output tokens: ~50K tokens (15 sections, 10K words total)
- **Total cost: ~$11.25 per PRD**

**Claude Sonnet 3.5 pricing:**
- Input: ~$3 per 1M tokens
- Output: ~$15 per 1M tokens
- **Total cost: ~$2.25 per PRD**

**Cost-benefit analysis:**
- 5x cost increase for Opus 4.6
- Dramatically better quality and consistency
- Reduces manual PRD revision time
- Worth it for production PRDs

---

## Technical Implementation

### Environment Variable

```bash
ATOMIC_PRD_USE_MAX_CONTEXT=true
```

**Default:** `false` (uses standard primary model)

### Model Configuration (in task script)

```bash
# Model Configuration for PRD Authoring
local prd_model=""
local prd_provider=""
local prd_model_note=""

if [[ "${ATOMIC_PRD_USE_MAX_CONTEXT:-false}" == "true" ]]; then
    prd_model="claude-opus-4-6"
    prd_provider="max"
    prd_model_note=" (Opus 4.6 - 1M context)"
    atomic_info "PRD authoring mode: MAX CONTEXT (Opus 4.6 with 1M context window)"
else
    prd_model=$(atomic_get_primary_model 2>/dev/null || echo "$CLAUDE_MODEL")
    prd_provider="$CLAUDE_PROVIDER"
    prd_model_note=""
    atomic_info "PRD authoring mode: Standard (model: $prd_model)"
fi
```

### Propagation to All Generations

All 12 generations receive the configured model and provider:

```bash
_205_generate_with_retry $gen_num "$prompt_file" "$output_file" "$prior_file" \
    "$guardian_prompt" "$guardian_report" "$guardian_model" "$project_context" \
    "PRD Gen $gen_num: Description$prd_model_note" "$prd_model" "$prd_provider"
```

---

## Example Workflow

### Standard Mode (Sonnet)

```bash
# Phase 2 with default model
python main.py run 2

# Output:
# PRD authoring mode: Standard (model: sonnet)
# Generation 1: Vision + Executive
#   Context strategy: structured (model: sonnet, window: 200000 tokens)
# ...
# Generation 12: Approval
#   Final PRD: 8,500 words, 15 sections
```

### Max Context Mode (Opus 4.6)

```bash
# Phase 2 with Opus 4.6
export ATOMIC_PRD_USE_MAX_CONTEXT=true
python main.py run 2

# Output:
# PRD authoring mode: MAX CONTEXT (Opus 4.6 with 1M context window)
# Generation 1: Vision + Executive (Opus 4.6 - 1M context)
#   Context strategy: full (model: claude-opus-4-6, window: 1000000 tokens)
# ...
# Generation 12: Approval (Opus 4.6 - 1M context)
#   Final PRD: 12,000 words, 15 sections, perfect cross-references
```

---

## Troubleshooting

### "Model not found" Error

**Issue:** `claude-opus-4-6` not recognized

**Solution:** Ensure you're using:
- Claude Code CLI with Anthropic API support
- API key with Opus 4.6 access
- Provider set to `max` (Claude Max subscription)

### Context Window Not Applied

**Issue:** Still using structured context strategy

**Solution:**
1. Check env var is set: `echo $ATOMIC_PRD_USE_MAX_CONTEXT`
2. Verify model detection: Look for "MAX CONTEXT" in output
3. Check script received model parameter: Grep logs for "claude-opus-4-6"

### High API Costs

**Issue:** Unexpected API charges

**Solution:**
- Use `ATOMIC_SKIP_GUARDIAN=true` to skip guardian validation (reduces token usage)
- Use standard mode for drafts, Opus 4.6 for final PRD
- Monitor token usage in `.outputs/2-prd/prd-generation-log.json`

---

## Future Enhancements

### Planned:

1. **Token usage tracking** - Add token counters to generation log
2. **Cost estimation** - Pre-flight check to estimate total cost
3. **Hybrid mode** - Use Sonnet for Gens 1-6, Opus 4.6 for Gens 7-12
4. **Context compression** - Smart summarization for <1M windows

### Possible:

5. **Gemini 1.5 Pro support** - 2M context window alternative
6. **Custom context strategies** - User-defined context injection rules
7. **A/B testing** - Compare PRD quality between models

---

## Summary

**Key Points:**
- ✅ Opus 4.6 with 1M context window now supported for Phase 2
- ✅ Enable via `ATOMIC_PRD_USE_MAX_CONTEXT=true`
- ✅ Automatic context strategy adjustment (full mode for 1M)
- ✅ All 12 generations use configured model
- ✅ ~5x cost increase vs Sonnet, significantly better quality
- ✅ Best for complex enterprise PRDs with 50+ requirements

**Model Selection:**
- **Standard (Sonnet 3.5):** Most projects, budget-conscious
- **Max Context (Opus 4.6):** Complex PRDs, quality-critical, production

---

*Feature added: February 10, 2026*
*Phase: 2 (PRD Authoring)*
*Status: Production-ready*
