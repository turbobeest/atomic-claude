#!/bin/bash
#
# Task 205: PRD Authoring
# Multi-agent PRD document creation using 15-section template
#
# Agents (sequential):
#   1. requirements-engineer - Synthesize into structured reqs
#   2. prd-writer - Author formal PRD document
#
# Output: docs/prd/PRD.md
#

task_205_prd_authoring() {
    local setup_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-setup.json"
    local interview_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prd-interview.json"
    local phase1_dir="$ATOMIC_OUTPUT_DIR/1-discovery"
    local prd_dir="$ATOMIC_ROOT/docs/prd"
    local prd_file="$prd_dir/PRD.md"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    atomic_step "PRD Authoring"

    mkdir -p "$prd_dir" "$prompts_dir"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ Multi-agent PRD authoring using 15-section template.   │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Sections:                                               │${NC}"
    echo -e "${DIM}  │  0. Vision + Problem       8. Documentation Reqs       │${NC}"
    echo -e "${DIM}  │  1. Executive Summary      9. Operational Readiness    │${NC}"
    echo -e "${DIM}  │  2. System Architecture   10. Risk + Assumptions       │${NC}"
    echo -e "${DIM}  │  3. Feature Reqs (2119)   11. Success Metrics          │${NC}"
    echo -e "${DIM}  │  4. Non-Functional Reqs   12. Task Decomposition       │${NC}"
    echo -e "${DIM}  │  5. Code Structure Map    13. Subtask Extraction       │${NC}"
    echo -e "${DIM}  │  6. TDD Implementation    14. Approval + Sign-off      │${NC}"
    echo -e "${DIM}  │  7. Integration Testing                                │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # GATHER CONTEXT
    # ═══════════════════════════════════════════════════════════════════════════

    local approach_context=""
    local interview_context=""
    local setup_context=""

    # Load Phase 1 approach
    if [[ -f "$phase1_dir/selected-approach.json" ]]; then
        approach_context=$(cat "$phase1_dir/selected-approach.json")
    fi

    # Load interview data
    if [[ -f "$interview_file" ]]; then
        interview_context=$(cat "$interview_file")
    fi

    # Load setup data
    if [[ -f "$setup_file" ]]; then
        setup_context=$(cat "$setup_file")
    fi

    # Load corpus if available
    local corpus_context=""
    if [[ -f "$phase1_dir/corpus.json" ]]; then
        corpus_context=$(jq -c '.materials[:5] // []' "$phase1_dir/corpus.json" 2>/dev/null || echo "[]")
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # STAGE 1: REQUIREMENTS SYNTHESIS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}STAGE 1: REQUIREMENTS SYNTHESIS${NC}                           ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    cat > "$prompts_dir/requirements-synthesis.md" << EOF
# Task: Requirements Synthesis

You are a requirements engineer synthesizing project requirements.

## Context

### Selected Approach (from Phase 1)
$approach_context

### PRD Interview Responses
$interview_context

### PRD Setup
$setup_context

## Your Task

Synthesize the above into structured requirements using:
- RFC 2119 keywords (MUST, SHOULD, MAY)
- EARS syntax where appropriate (When/While/If...then)

Output format:
{
    "functional_requirements": [
        {"id": "FR-001", "description": "...", "priority": "MUST|SHOULD|MAY", "acceptance": "..."}
    ],
    "non_functional_requirements": [
        {"id": "NFR-001", "category": "performance|security|usability|...", "description": "...", "metric": "..."}
    ],
    "constraints": [...],
    "assumptions": [...]
}

Output ONLY valid JSON.
EOF

    atomic_waiting "requirements-engineer synthesizing..."

    local reqs_file="$prompts_dir/requirements.json"
    if atomic_invoke "$prompts_dir/requirements-synthesis.md" "$reqs_file" "Requirements synthesis" --model=sonnet; then
        if jq -e . "$reqs_file" &>/dev/null; then
            local fr_count=$(jq '.functional_requirements | length' "$reqs_file" 2>/dev/null || echo 0)
            local nfr_count=$(jq '.non_functional_requirements | length' "$reqs_file" 2>/dev/null || echo 0)
            echo -e "  ${GREEN}✓${NC} Synthesized $fr_count functional, $nfr_count non-functional requirements"
        else
            atomic_warn "Invalid requirements output - continuing with template"
            echo '{"functional_requirements":[],"non_functional_requirements":[],"constraints":[],"assumptions":[]}' > "$reqs_file"
        fi
    else
        atomic_warn "Requirements synthesis failed - using defaults"
        echo '{"functional_requirements":[],"non_functional_requirements":[],"constraints":[],"assumptions":[]}' > "$reqs_file"
    fi

    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STAGE 2: PRD WRITING
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}STAGE 2: PRD WRITING${NC}                                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local requirements_json=$(cat "$reqs_file")

    cat > "$prompts_dir/prd-writing.md" << EOF
# Task: PRD Writing

You are a PRD writer creating a formal Product Requirements Document.

## Context

### Selected Approach
$approach_context

### Interview Responses
$interview_context

### Synthesized Requirements
$requirements_json

## Your Task

Write a complete PRD using the 15-section template below.
Use clear, specific language. Include measurable criteria where possible.

## Template

# Product Requirements Document (PRD)

## 0. Vision + Problem Statement
[What problem are we solving? What's the vision?]

## 1. Executive Summary
[Brief overview for stakeholders]

## 2. System Architecture Overview
[High-level architecture description]

## 3. Feature Requirements
[Detailed functional requirements using RFC 2119]

### 3.1 Core Features
[MUST have features]

### 3.2 Enhanced Features
[SHOULD have features]

### 3.3 Optional Features
[MAY have features]

## 4. Non-Functional Requirements
[Performance, security, scalability, etc.]

## 5. Code Structure Map
[Expected project structure]

## 6. TDD Implementation Strategy
[Test-driven development approach]

## 7. Integration Testing Strategy
[Integration test approach]

## 8. Documentation Requirements
[Required documentation]

## 9. Operational Readiness
[Deployment, monitoring, support]

## 10. Risks and Assumptions
[Known risks and assumptions]

## 11. Success Metrics
[How we measure success]

## 12. Task Decomposition
[High-level task breakdown]

## 13. Subtask Extraction
[Detailed subtasks for implementation]

## 14. Approval and Sign-off
[Approval workflow]

---

Output the complete PRD in markdown format.
EOF

    atomic_waiting "prd-writer authoring document..."

    if atomic_invoke "$prompts_dir/prd-writing.md" "$prd_file" "PRD authoring" --model=sonnet; then
        local line_count=$(wc -l < "$prd_file")
        echo -e "  ${GREEN}✓${NC} PRD document created ($line_count lines)"
    else
        atomic_error "PRD writing failed"
        _205_create_fallback_prd "$prd_file"
    fi

    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}PRD Created:${NC} $prd_file"
    echo ""

    # Quick preview
    echo -e "  ${DIM}Section headers:${NC}"
    grep -E '^##' "$prd_file" 2>/dev/null | head -10 | while read -r line; do
        echo -e "    $line"
    done
    echo ""

    atomic_context_artifact "prd-document" "$prd_file" "Product Requirements Document"
    atomic_context_artifact "requirements-json" "$reqs_file" "Synthesized requirements"
    atomic_context_decision "PRD authored with 15 sections" "authoring"

    atomic_success "PRD authoring complete"

    return 0
}

# Create fallback PRD if LLM fails
_205_create_fallback_prd() {
    local prd_file="$1"

    cat > "$prd_file" << 'EOF'
# Product Requirements Document (PRD)

## 0. Vision + Problem Statement

[To be completed - describe the problem being solved and the vision]

## 1. Executive Summary

[To be completed - brief overview for stakeholders]

## 2. System Architecture Overview

[To be completed - high-level architecture]

## 3. Feature Requirements

### 3.1 Core Features (MUST)

- [ ] Feature 1
- [ ] Feature 2

### 3.2 Enhanced Features (SHOULD)

- [ ] Feature 3

### 3.3 Optional Features (MAY)

- [ ] Feature 4

## 4. Non-Functional Requirements

- Performance: [TBD]
- Security: [TBD]
- Scalability: [TBD]

## 5. Code Structure Map

```
project/
├── src/
├── tests/
└── docs/
```

## 6. TDD Implementation Strategy

[To be completed]

## 7. Integration Testing Strategy

[To be completed]

## 8. Documentation Requirements

- README.md
- API documentation
- User guide

## 9. Operational Readiness

[To be completed]

## 10. Risks and Assumptions

### Risks
- Risk 1: [Description]

### Assumptions
- Assumption 1: [Description]

## 11. Success Metrics

- Metric 1: [Description]

## 12. Task Decomposition

[To be completed]

## 13. Subtask Extraction

[To be completed]

## 14. Approval and Sign-off

- [ ] Technical review
- [ ] Product owner approval
- [ ] Stakeholder sign-off

---
*Generated by ATOMIC CLAUDE - Phase 2 PRD*
EOF

    atomic_warn "Created fallback PRD template - manual completion required"
}
