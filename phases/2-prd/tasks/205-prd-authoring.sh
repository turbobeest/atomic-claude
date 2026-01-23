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
    # GATHER CONTEXT (with truncation for token management)
    # ═══════════════════════════════════════════════════════════════════════════

    local approach_context=""
    local interview_context=""
    local setup_context=""
    local tech_stack_context=""

    # Load Phase 1 approach (summarized)
    if [[ -f "$phase1_dir/selected-approach.json" ]]; then
        approach_context=$(atomic_context_summarize "$phase1_dir/selected-approach.json" "selected approach from Phase 1" 100)
    fi

    # Load interview data (extract key fields, not full dump)
    if [[ -f "$interview_file" ]]; then
        interview_context=$(jq -r '
            "Problem: " + (.problem // "Not specified") + "\n" +
            "Solution: " + (.solution // "Not specified") + "\n" +
            "Users: " + (.target_users // "Not specified") + "\n" +
            "Success Criteria: " + ((.success_criteria // []) | join("; ")) + "\n" +
            "Constraints: " + ((.constraints // []) | join("; "))
        ' "$interview_file" 2>/dev/null || cat "$interview_file" | head -100)
    fi

    # Load setup data (extract key fields)
    if [[ -f "$setup_file" ]]; then
        setup_context=$(jq -r '
            "Project Type: " + (.project_type // "Not specified") + "\n" +
            "Timeline: " + (.timeline // "Not specified") + "\n" +
            "Team Size: " + (.team_size // "Not specified")
        ' "$setup_file" 2>/dev/null || cat "$setup_file" | head -50)
    fi

    # Load tech stack from project config (CRITICAL for TaskMaster compatibility)
    local project_config="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
    if [[ -f "$project_config" ]]; then
        tech_stack_context=$(jq -r '
            .extracted // {} |
            "Languages: " + ((.constraints.technical // []) | join(", ")) + "\n" +
            "Infrastructure: " + (.constraints.infrastructure // "Not specified") + "\n" +
            "Compliance: " + ((.constraints.compliance // []) | join(", "))
        ' "$project_config" 2>/dev/null || echo "Tech stack not specified")
    fi

    # Load corpus for grounding (CRITICAL - was unused before!)
    local corpus_context=""
    if [[ -f "$phase1_dir/corpus.json" ]]; then
        # Extract summaries from first 5 materials
        corpus_context=$(jq -r '
            .materials[:5] // [] | map(
                "- " + (.name // .path // "unnamed") + ": " + ((.summary // .content // "")[:200])
            ) | join("\n")
        ' "$phase1_dir/corpus.json" 2>/dev/null || echo "No corpus materials")
    fi

    # Load dialogue synthesis for vision/goals
    local dialogue_context=""
    if [[ -f "$phase1_dir/dialogue.json" ]]; then
        dialogue_context=$(jq -r '
            .synthesis // {} |
            "Vision: " + (.vision.core_problem // "Not specified") + "\n" +
            "Impact: " + (.impact.primary_impact // "Not specified") + "\n" +
            "Audience: " + (.audience.primary // "Not specified") + "\n" +
            "Non-negotiables: " + ((.non_negotiables // []) | join("; "))
        ' "$phase1_dir/dialogue.json" 2>/dev/null || echo "No dialogue synthesis")
    fi

    # Load consensus document from deliberation (CRITICAL for context)
    local consensus_context=""
    if [[ -f "$phase1_dir/consensus.md" ]]; then
        consensus_context=$(atomic_context_summarize "$phase1_dir/consensus.md" "deliberation consensus" 150)
    fi

    # Load first-principles analysis if available
    local first_principles_context=""
    if [[ -f "$phase1_dir/first-principles.md" ]]; then
        first_principles_context=$(atomic_context_summarize "$phase1_dir/first-principles.md" "first principles analysis" 100)
    fi

    # Load selected approach document for full rationale
    local approach_rationale=""
    if [[ -f "$phase1_dir/selected-approach.md" ]]; then
        approach_rationale=$(atomic_context_summarize "$phase1_dir/selected-approach.md" "approach rationale" 100)
    fi

    # Load Phase 1 closeout for summary metrics
    local closeout_context=""
    local closeout_file="$ATOMIC_ROOT/.claude/closeout/phase-01-closeout.json"
    if [[ -f "$closeout_file" ]]; then
        closeout_context=$(jq -r '
            "Materials collected: " + (.corpus_count // 0 | tostring) + "\n" +
            "Selected approach: " + (.selected_approach // "Not specified") + "\n" +
            "Deliberation completed: " + (.deliberation_status // "unknown")
        ' "$closeout_file" 2>/dev/null || echo "No closeout data")
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

You are a requirements engineer synthesizing project requirements for downstream tool consumption (TaskMaster, OpenSpec).

## Project Context (from Phase 1 Discovery)

### Vision & Goals
$dialogue_context

### Discovery Consensus
$consensus_context

### Selected Approach
$approach_context

### Approach Rationale
$approach_rationale

### First Principles Analysis
$first_principles_context

### Interview Responses
$interview_context

### Project Setup
$setup_context

### Tech Stack (MUST be respected - TaskMaster will enforce these)
$tech_stack_context

### Reference Materials (Corpus)
$corpus_context

### Phase 1 Summary
$closeout_context

## Requirements Format Standards

### RFC 2119 Keywords (REQUIRED)
- **MUST/SHALL**: Absolute requirement
- **SHOULD**: Recommended but not mandatory
- **MAY**: Optional feature

### OpenSpec Scenario Format (REQUIRED for each requirement)
Every functional requirement needs at least one scenario:
\`\`\`
Scenario: <descriptive name>
- WHEN <trigger condition>
- THEN <expected outcome>
\`\`\`

## Example Requirement (follow this format)

{
  "id": "FR-001",
  "name": "User Authentication",
  "description": "The system SHALL authenticate users via JWT tokens",
  "priority": "MUST",
  "scenarios": [
    {
      "name": "Valid credentials",
      "when": "a user submits valid username and password",
      "then": "the system returns a JWT with 1-hour expiry"
    },
    {
      "name": "Invalid credentials",
      "when": "a user submits invalid credentials",
      "then": "the system returns 401 Unauthorized"
    }
  ],
  "acceptance_criteria": "JWT issued within 200ms, token contains user ID and roles"
}

## Output Schema

Generate 10-25 functional requirements and 5-10 non-functional requirements.

{
  "functional_requirements": [
    {
      "id": "FR-001",
      "name": "Short name",
      "description": "The system SHALL/SHOULD/MAY...",
      "priority": "MUST|SHOULD|MAY",
      "scenarios": [{"name": "...", "when": "...", "then": "..."}],
      "acceptance_criteria": "Measurable criteria"
    }
  ],
  "non_functional_requirements": [
    {
      "id": "NFR-001",
      "category": "performance|security|scalability|reliability|usability",
      "description": "The system SHALL...",
      "metric": "Specific measurable target (e.g., <200ms p99 latency)"
    }
  ],
  "constraints": ["Technical constraints that MUST be respected"],
  "assumptions": ["Assumptions we're making"],
  "logical_dependencies": [
    {"requirement": "FR-002", "depends_on": ["FR-001"], "reason": "Auth required before user actions"}
  ]
}

## Quality Criteria

- Every requirement uses SHALL/SHOULD/MAY
- Every functional requirement has at least one scenario
- NFRs have specific, measurable metrics (not "fast" but "<200ms")
- Dependencies are explicit for TaskMaster task ordering

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

    # Extract key counts for guidance
    local fr_count=$(echo "$requirements_json" | jq '.functional_requirements | length' 2>/dev/null || echo "0")
    local nfr_count=$(echo "$requirements_json" | jq '.non_functional_requirements | length' 2>/dev/null || echo "0")

    cat > "$prompts_dir/prd-writing.md" << EOF
# Task: PRD Writing (TaskMaster & OpenSpec Compatible)

You are a PRD writer creating a formal Product Requirements Document that will be consumed by:
1. **TaskMaster** - for automatic task decomposition (needs Logical Dependency Chain, explicit tech stack)
2. **OpenSpec** - for spec-driven development (needs SHALL/SHOULD/MAY language, WHEN/THEN scenarios)

## Synthesized Requirements (from Stage 1)

$requirements_json

## Tech Stack (EXPLICIT - TaskMaster will enforce these)

$tech_stack_context

## Vision Context

$dialogue_context

## Section Depth Guidance

| Section | Target Length | Key Content |
|---------|---------------|-------------|
| 0. Vision | 2-3 paragraphs | Problem, solution concept, why now |
| 1. Executive Summary | 1 paragraph | 30-second overview for stakeholders |
| 2. Technical Architecture | 1-2 pages | Components, tech stack, data flow |
| 3. Feature Requirements | 2-4 pages | All $fr_count FRs with scenarios |
| 4. Non-Functional Reqs | 1 page | All $nfr_count NFRs with metrics |
| 5. Logical Dependency Chain | 1 page | **CRITICAL for TaskMaster** |
| 6. Development Phases | 1 page | Scope-based, NOT time-based |
| 7. Code Structure Map | Half page | Directory structure |
| 8. TDD Strategy | 1 page | Test approach per component |
| 9. Integration Testing | Half page | Integration test strategy |
| 10. Documentation Reqs | Half page | Required docs |
| 11. Operational Readiness | 1 page | Deploy, monitor, support |
| 12. Risks & Assumptions | 1 page | Top 5 risks, key assumptions |
| 13. Success Metrics | Half page | Measurable KPIs |
| 14. Approval | Quarter page | Sign-off checklist |

## Template (FOLLOW THIS STRUCTURE)

# Product Requirements Document (PRD)

## 0. Vision + Problem Statement

**Problem**: [2-3 sentences describing the pain point]

**Solution**: [2-3 sentences describing our approach]

**Why Now**: [Why is this the right time to solve this?]

## 1. Executive Summary

[One paragraph that a stakeholder can read in 30 seconds to understand what we're building and why]

## 2. Technical Architecture

### 2.1 Tech Stack (EXPLICIT)

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Backend | [e.g., Node.js/Express] | [Why this choice] |
| Frontend | [e.g., React] | [Why] |
| Database | [e.g., PostgreSQL] | [Why] |
| Cache | [e.g., Redis] | [Why] |
| Infrastructure | [e.g., AWS ECS] | [Why] |

### 2.2 System Components

[Describe major components and their interactions]

### 2.3 Data Flow

[How data moves through the system]

## 3. Feature Requirements

### 3.1 Core Features (MUST)

For each requirement, use this format (OpenSpec-compatible):

#### FR-001: [Name]

The system **SHALL** [requirement description].

**Scenarios:**
- **WHEN** [trigger condition] **THEN** [expected outcome]
- **WHEN** [another condition] **THEN** [outcome]

**Acceptance Criteria:** [Measurable criteria]

---

[Include all MUST requirements from synthesized data]

### 3.2 Enhanced Features (SHOULD)

[SHOULD requirements with same format]

### 3.3 Optional Features (MAY)

[MAY requirements with same format]

## 4. Non-Functional Requirements

| ID | Category | Requirement | Metric |
|----|----------|-------------|--------|
| NFR-001 | Performance | The system SHALL respond within... | <200ms p99 |
| NFR-002 | Security | The system SHALL encrypt... | AES-256 |

[Include all NFRs from synthesized data]

## 5. Logical Dependency Chain

**CRITICAL FOR TASKMASTER**: This section defines the order in which features MUST be built.

### Foundation Layer (Build First)
1. [Requirement ID]: [Why it's foundational]
2. [Requirement ID]: [Depends on #1 because...]

### Core Layer (Build Second)
3. [Requirement ID]: [Depends on Foundation because...]

### Feature Layer (Build Third)
[Continue the chain...]

### Integration Layer (Build Last)
[Features that tie everything together]

## 6. Development Phases

**NOTE: Phases are defined by SCOPE, not time estimates.**

### Phase 1: Foundation
**Scope**: [What's included]
**Exit Criteria**: [How we know it's done]
**Delivers**: [Usable outcome, even if minimal]

### Phase 2: Core Features
**Scope**: [What's included]
**Exit Criteria**: [Measurable]
**Delivers**: [What users can do after this phase]

### Phase 3: Enhanced Features
[Continue pattern...]

## 7. Code Structure Map

\`\`\`
project/
├── src/
│   ├── api/           # REST endpoints
│   ├── services/      # Business logic
│   ├── models/        # Data models
│   └── utils/         # Shared utilities
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
└── config/
\`\`\`

## 8. TDD Implementation Strategy

### Unit Testing
- Framework: [e.g., Jest, pytest]
- Coverage target: [e.g., 80%]
- Strategy: [Test-first for all business logic]

### Test Categories
| Category | What to Test | Example |
|----------|--------------|---------|
| Unit | Individual functions | Service method returns expected value |
| Integration | Component interactions | API → Service → Database |
| E2E | User workflows | Login → Dashboard → Action |

## 9. Integration Testing Strategy

[How components will be tested together]

## 10. Documentation Requirements

- [ ] README.md with setup instructions
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Architecture decision records (ADRs)
- [ ] Deployment runbook

## 11. Operational Readiness

### Deployment
[How the system will be deployed]

### Monitoring
[What metrics/logs/alerts]

### Support
[Escalation path, on-call expectations]

## 12. Risks and Assumptions

### Top 5 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | High/Med/Low | High/Med/Low | [How we'll handle it] |

### Key Assumptions

1. [Assumption]: [Why we believe this is true]

## 13. Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| [e.g., API Latency] | <200ms p99 | [Monitoring tool] |
| [e.g., User adoption] | 100 DAU in 30 days | [Analytics] |

## 14. Approval and Sign-off

- [ ] Technical Review Complete
- [ ] Product Owner Approval
- [ ] Security Review (if applicable)
- [ ] Stakeholder Sign-off

---
*Generated by ATOMIC CLAUDE - Phase 2 PRD*
*Compatible with TaskMaster and OpenSpec*

## Quality Anti-Patterns (AVOID THESE)

- Vague requirements ("system should be fast" → use specific metrics)
- Missing scenarios (every FR needs WHEN/THEN)
- Implicit tech stack (TaskMaster needs EXPLICIT technologies)
- Timeline-based phases (use scope-based phases instead)
- Missing dependency chain (TaskMaster needs this for task ordering)
- Generic NFRs without metrics

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

**Problem**: [Describe the pain point in 2-3 sentences]

**Solution**: [Describe the approach in 2-3 sentences]

**Why Now**: [Why is this the right time?]

## 1. Executive Summary

[One paragraph overview for stakeholders - what we're building and why]

## 2. Technical Architecture

### 2.1 Tech Stack (EXPLICIT - Required for TaskMaster)

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Backend | [TBD] | [TBD] |
| Frontend | [TBD] | [TBD] |
| Database | [TBD] | [TBD] |
| Infrastructure | [TBD] | [TBD] |

### 2.2 System Components

[To be completed - major components and interactions]

## 3. Feature Requirements

### 3.1 Core Features (MUST)

#### FR-001: [Feature Name]

The system **SHALL** [requirement].

**Scenarios:**
- **WHEN** [condition] **THEN** [outcome]

**Acceptance Criteria:** [Measurable criteria]

### 3.2 Enhanced Features (SHOULD)

[Add SHOULD requirements with same format]

### 3.3 Optional Features (MAY)

[Add MAY requirements with same format]

## 4. Non-Functional Requirements

| ID | Category | Requirement | Metric |
|----|----------|-------------|--------|
| NFR-001 | Performance | The system SHALL... | [Target] |
| NFR-002 | Security | The system SHALL... | [Target] |

## 5. Logical Dependency Chain (CRITICAL for TaskMaster)

### Foundation Layer (Build First)
1. [FR-XXX]: [Why foundational]

### Core Layer (Build Second)
2. [FR-XXX]: [Depends on Foundation]

### Feature Layer (Build Third)
3. [FR-XXX]: [Depends on Core]

## 6. Development Phases (Scope-Based)

### Phase 1: Foundation
**Scope**: [What's included]
**Exit Criteria**: [How we know it's done]

### Phase 2: Core Features
**Scope**: [What's included]
**Exit Criteria**: [Measurable]

## 7. Code Structure Map

```
project/
├── src/
│   ├── api/
│   ├── services/
│   └── models/
├── tests/
│   ├── unit/
│   └── integration/
└── docs/
```

## 8. TDD Implementation Strategy

- Framework: [TBD]
- Coverage target: [TBD]
- Strategy: Test-first for business logic

## 9. Integration Testing Strategy

[To be completed]

## 10. Documentation Requirements

- [ ] README.md
- [ ] API documentation
- [ ] Deployment runbook

## 11. Operational Readiness

[To be completed - deployment, monitoring, support]

## 12. Risks and Assumptions

### Top Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk] | [H/M/L] | [H/M/L] | [Mitigation] |

### Assumptions
1. [Assumption]

## 13. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| [Metric] | [Target] | [How measured] |

## 14. Approval and Sign-off

- [ ] Technical Review
- [ ] Product Owner Approval
- [ ] Security Review
- [ ] Stakeholder Sign-off

---
*Generated by ATOMIC CLAUDE - Phase 2 PRD*
*Compatible with TaskMaster and OpenSpec*
EOF

    atomic_warn "Created fallback PRD template - manual completion required"
}
