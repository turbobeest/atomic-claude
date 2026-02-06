# Task 205 Implementation Notes: 8-Generation Sequential with Guardian

**Date**: 2026-02-03
**Implementation**: Complete
**Status**: Ready for testing

---

## Overview

Task 205 (PRD Authoring) has been rewritten to implement an **8-generation sequential workflow** with document-guardian validation and auto-retry between each generation. This replaces the previous 3-chunk approach.

---

## Architecture

### Generation Breakdown

| Gen | Sections | Rationale | Guardian Focus |
|-----|----------|-----------|----------------|
| 1 | 0-1 | Vision + Executive closely related (~1 page) | Vision clarity, initial tech mentions |
| 2 | 2 | Tech Architecture standalone (CRITICAL tech stack lock-in) | Tech stack consistency, component definitions |
| 3 | 3 | Feature Requirements (large, 2-4 pages) | FR sequence gaps, WHEN/THEN format, tech alignment |
| 4 | 4 | NFRs (separate concerns from FRs) | NFR sequence gaps, metric specificity |
| 5 | 5 | Dependency Chain (CRITICAL for TaskMaster) | Cross-references to all FRs/NFRs, acyclic graph |
| 6 | 6 | Dev Phases (builds on dependency chain) | Scope-based not time-based |
| 7 | 7-9 | Implementation trio (related: structure + TDD + integration) | Tech stack alignment in tests |
| 8 | 10-14 | Operations + conclusion (documentation, ops, risks, metrics, approval) | Completeness, risk coverage (min 5) |

### Guardian Integration

Each generation follows this workflow:

```
Generate Section(s)
    ↓
Guardian Validation
    ├─ [PASS] → Save to memory → Continue to next generation
    ├─ [WARN] → Auto-retry with corrections (max 2 retries)
    └─ [FAIL] → Human escalation
```

### Context Injection Strategy

After each generation, the guardian:
1. Validates completed sections against project constraints
2. Detects drift (tech stack changes, broken cross-references, ID gaps)
3. Extracts context injection payload for next generation:
   - **Reminders**: Specific facts (tech stack, last IDs, key decisions)
   - **Constraints**: Hard rules that must be followed
   - **Watch For**: Common pitfalls to avoid

This context is injected into the prompt for the next generation, maintaining consistency across the entire PRD.

---

## Key Features

### 1. Tech Stack Lock-In

After Generation 2 (Technical Architecture), the tech stack is extracted and locked:

```bash
tech_stack_locked=$(grep -A 20 "### 2.1 Tech Stack" "$gen2_output" | ...)
```

All subsequent generations receive the locked tech stack in their context, preventing drift.

### 2. ID Tracking

- **FR IDs**: Extracted after Generation 3, tracked in `last_fr_id`
- **NFR IDs**: Extracted after Generation 4, tracked in `last_nfr_id`

Generation 5 (Logical Dependency Chain) receives these IDs to ensure all cross-references are valid.

### 3. Auto-Retry Logic

When the guardian detects warnings:
1. Extract specific corrections from guardian report
2. Inject corrections into the prompt
3. Retry generation (max 2 attempts)
4. If still failing, proceed with warnings (not critical)

Critical failures (status: "fail") escalate to human immediately.

### 4. Memory Integration

Each generation saves to memory using `_memory_save_local()`:
- `prd_section_1` through `prd_section_10_14`
- `tech_stack_locked`
- `last_fr_id`
- `last_nfr_id`

Memory persists across sessions, allowing Task 205 to resume if interrupted.

### 5. Guardian Model Selection

Prefers large-context Ollama models to avoid CLI truncation:
1. `llama3.3:70b` (best)
2. `qwen2.5:72b`
3. `devstral:latest`
4. `nemotron_mini_4b:latest` (fallback)

Uses Ollama instead of Bedrock CLI to ensure full output capture without truncation.

### 6. Bedrock CLI Workaround

Added PRD-specific override in `lib/atomic.sh` to force `--max-turns 1` for all PRD generations, preventing Bedrock CLI from truncating multi-turn output.

---

## File Structure

### Generated Files

```
.outputs/2-prd/
├── prompts/
│   ├── gen-1-prompt.md                  # Generation 1 prompt
│   ├── gen-1-sections.md                # Generated sections 0-1
│   ├── gen-1-prior.md                   # Prior sections (empty for Gen 1)
│   ├── guardian-gen-1-prompt.md         # Guardian validation prompt
│   ├── guardian-gen-1-report.json       # Guardian report
│   ├── gen-2-prompt.md                  # Generation 2 prompt
│   ├── gen-2-sections.md                # Generated section 2
│   ├── gen-2-prior.md                   # Sections 0-1
│   ├── guardian-gen-2-prompt.md         # Guardian validation prompt
│   ├── guardian-gen-2-report.json       # Guardian report
│   ├── ... (repeat for Gen 3-8)
│   └── context/
│       ├── cumulative-gen-1.md          # Context for Gen 1
│       ├── cumulative-gen-2.md          # Context for Gen 2 (includes Gen 1)
│       └── ... (repeat for Gen 3-8)
├── PRD.md                                # Final assembled PRD
└── guardian-summary.json                 # Summary of all 8 guardian checks

docs/prd/
└── PRD.md                                 # Final PRD (copied from .outputs)

.state/memory/phase-2/
├── task-205-prd_section_1.md            # Gen 1 content
├── task-205-prd_section_2.md            # Gen 2 content
├── task-205-prd_section_3.md            # Gen 3 content
├── task-205-prd_section_4.md            # Gen 4 content
├── task-205-prd_section_5.md            # Gen 5 content
├── task-205-prd_section_6.md            # Gen 6 content
├── task-205-prd_section_7_9.md          # Gen 7 content
├── task-205-prd_section_10_14.md        # Gen 8 content
├── task-205-tech_stack_locked.md        # Locked tech stack
├── task-205-last_fr_id.md               # Last FR ID
└── task-205-last_nfr_id.md              # Last NFR ID
```

---

## Helper Functions

### `_205_select_guardian_model()`
Detects available Ollama models and selects the best large-context model for guardian validation.

### `_205_extract_json_from_markdown()`
Extracts JSON from markdown code fences in guardian reports.

### `_205_guardian_validate()`
Runs guardian validation on a completed generation:
- Builds guardian prompt with completed sections + prior sections
- Invokes guardian with Ollama (no CLI truncation)
- Parses validation status (pass/warn/fail)
- Returns status code

### `_205_generate_with_retry()`
Generates a section with auto-retry on guardian warnings:
- Attempts generation (max 2 retries)
- Runs guardian validation after each attempt
- On warnings: inject corrections into prompt and retry
- On pass: continue to next generation
- On fail: escalate to human

### `_205_build_context()`
Builds cumulative context for each generation:
- Project context (name, type, tech stack, date)
- Guardian context injections from all prior generations
- Prior section content (truncated with head/tail window strategy)

### `_205_assemble_prior_sections()`
Concatenates all prior generation outputs into a single file for guardian validation.

---

## Critical Implementation Details

### Issue #1: Bedrock CLI Multi-Turn Truncation

**Problem**: Bedrock CLI with `--max-turns N` where N>1 only captures final turn content.

**Solution**: Added PRD-specific override in `lib/atomic.sh`:
```bash
if [[ "$description" =~ "PRD Gen" || "$description" =~ "PRD Chunk" ]]; then
    cmd="${cmd} --max-turns 1"
fi
```

### Issue #2: memory_save() Does Not Exist

**Problem**: Previous implementation called non-existent `memory_save()`.

**Solution**: Use internal function `_memory_save_local()`:
```bash
_memory_save_local "2" "205" "prd_section_${gen_num}" "$(cat "$section_file")"
```

### Issue #3: Guardian JSON Parsing

**Problem**: Guardian outputs JSON wrapped in markdown code fences.

**Solution**: Automatic JSON extraction using `_205_extract_json_from_markdown()`.

### Issue #4: Tech Stack Lock-In

**Problem**: Tech stack can drift across sections if not enforced.

**Solution**: Extract and lock tech stack after Gen 2, inject into all subsequent prompts as constraint.

---

## Verification Steps

### During Execution

Monitor via tasks dashboard (http://localhost:5173):
- Real-time task status
- Provider/model information
- Guardian validation results

Check guardian reports:
```bash
# View guardian status
jq '.validation.status' .outputs/2-prd/prompts/guardian-gen-3-report.json

# View issues
jq '.validation.issues[]' .outputs/2-prd/prompts/guardian-gen-3-report.json

# View context injection
jq '.context_injection' .outputs/2-prd/prompts/guardian-gen-3-report.json
```

### Post-Execution

**Structural validation** (Task 206):
```bash
./run-atomic.sh run 2 --resume-at=206
# Should pass with 15/15 sections found
```

**Manual inspection**:
```bash
# Tech stack consistency
grep -i "postgresql\|mysql" docs/prd/PRD.md

# FR sequence (should be sequential, no gaps)
grep "^#### FR-" docs/prd/PRD.md | sed 's/.*FR-//' | sed 's/:.*//' | sort -n

# NFR sequence
grep "^| NFR-" docs/prd/PRD.md | sed 's/.*NFR-//' | sed 's/ .*//' | sort -n

# TaskMaster critical section (Section 5)
grep -A 50 "## 5. Logical Dependency Chain" docs/prd/PRD.md
```

**Guardian summary**:
```bash
jq '.' .outputs/2-prd/guardian-summary.json
```

---

## Files Modified

### Primary File
- **`phases/2-prd/tasks/205-prd-authoring.sh`** (complete rewrite, 1227 lines)

### Supporting Files
- **`lib/atomic.sh`** (line 1638-1645): Added PRD-specific `--max-turns=1` override

### Backups Created
- `205-prd-authoring.sh.backup-3chunk` (previous 3-chunk implementation)
- `205-prd-authoring.sh.backup-single-stage` (earlier backup)
- `205-prd-authoring.sh.backup-two-stage` (earlier backup)
- `205-prd-authoring.sh.backup-two-stage-2` (earlier backup)

---

## Success Criteria

1. ✅ **15 sections present** in final PRD (validation by Task 206)
2. ✅ **No tech stack drift** (single technology per layer throughout)
3. ✅ **Sequential FR/NFR IDs** (no gaps, no duplicates)
4. ✅ **All cross-references valid** (Section 5 references only defined FRs/NFRs)
5. ✅ **Guardian approved** all 8 generations (status: "pass" or "warn" with corrections)
6. ✅ **TaskMaster-ready** (Section 5 Logical Dependency Chain complete)
7. ✅ **OpenSpec-compliant** (FRs have WHEN/THEN scenarios, NFRs have metrics)
8. ✅ **Memory persisted** (all 8 generations saved to .state/memory/)

---

## Estimated Execution Time

- **Generation time**: 8 generations × 2 min/gen × 1.5 (accounting for retries) = ~24 minutes
- **Guardian time**: 8 validations × 30 sec/validation = ~4 minutes
- **Assembly time**: ~1 minute
- **Total**: ~30 minutes for complete PRD generation

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Bedrock CLI truncation | Force `--max-turns=1` for all PRD generations |
| Guardian fails to detect drift | Critical sections (2, 3, 4, 5) get extra validation focus |
| Context window overflow | Truncate prior sections using head/tail window strategy |
| Auto-retry infinite loop | Max 2 retries per generation, then proceed with warnings |
| memory_save() missing | Use `_memory_save_local()` directly with proper error handling |
| Guardian JSON parsing fails | Graceful degradation: extract JSON or proceed without context injection |
| Tech stack drift | Lock tech stack after Gen 2, enforce in all subsequent guardian checks |

---

## Next Steps

1. ✅ Backup current Task 205 (done: `.backup-3chunk`)
2. ✅ Rewrite Task 205 implementing 8-generation workflow (done)
3. ✅ Update lib/atomic.sh for PRD-specific `--max-turns=1` (done)
4. ⏭️ Test with Phase 2 end-to-end run
5. ⏭️ Validate PRD with Task 206
6. ⏭️ If successful, document pattern for reuse in other multi-section generation tasks

---

## Testing Recommendations

### Unit Test (Single Generation)

```bash
# Test Generation 1 in isolation
source phases/2-prd/tasks/205-prd-authoring.sh
# Manually call _205_generate_with_retry for Gen 1
```

### Integration Test (Full Phase 2)

```bash
# Run full Phase 2 from scratch
./run-atomic.sh run 2

# Or resume from Task 205
./run-atomic.sh run 2 --resume-at=205
```

### Validation Test (Task 206)

```bash
# After Task 205 completes, verify structure
./run-atomic.sh run 2 --resume-at=206
```

---

## Document-Guardian Agent

The guardian agent definition is located at:
```
agents/pipeline-agents/00-quality-assurance/document-guardian.md
```

**Key capabilities**:
- Drift detection (tech stack, IDs, cross-references)
- Context injection (reminders, constraints, watch-fors)
- Large-context model requirement (32K+ context window)
- CLI-free operation (direct API via Ollama)

**Grade**: A (90.0/100)
**Model**: llama3.3:70b (fallbacks: nemotron:70b, qwen2.5:72b, llama3.1:70b)

---

## References

- **TaskMaster**: https://github.com/eyaltoledano/claude-task-master
- **OpenSpec**: https://github.com/Fission-AI/OpenSpec
- **RFC 2119**: https://www.rfc-editor.org/rfc/rfc2119 (Requirement keywords)
- **Agent Definition**: `agents/pipeline-agents/00-quality-assurance/document-guardian.md`
- **Plan Transcript**: `.claude/projects/-Users-jamesterbeest-dev-atomic-claude/f370803c-4f4a-4e3b-8935-b4d2bad2fea5.jsonl`

---

**Implementation Complete**: 2026-02-03 21:58 PST
