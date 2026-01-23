#!/bin/bash
#
# Task 207: Phase Audit - PRD Validation
# AI-driven audit selection from turbobeest/audits repository
#
# Features:
#   - AI recommends relevant audits based on PRD content
#   - User reviews and approves audit selection
#   - Supports legacy 94-dimension mode for backward compatibility
#

task_207_phase_audit() {
    source "$ATOMIC_ROOT/lib/audit.sh"
    audit_phase_wrapper 2 "PRD Validation" "_207_legacy_audit"
    return $?
}

# Legacy dimension-based audit for PRD phase
_207_legacy_audit() {
    local audit_dir="$ATOMIC_ROOT/.claude/audit"
    local audit_file="$audit_dir/phase-02-audit.json"
    local prd_file="$ATOMIC_ROOT/docs/prd/PRD.md"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    mkdir -p "$audit_dir" "$prompts_dir"

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}LEGACY PRD AUDIT (60 Dimensions Available)${NC}                   ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Define the 60 PRD audit dimensions organized by category
    # Categories: Structure (S), Requirements (R), Testability (T), Tool-Compat (C), Risk (K), Scope (P)
    local all_dimensions
    all_dimensions=$(_207_get_dimension_definitions)

    # Audit profiles
    echo -e "  ${CYAN}Select audit profile:${NC}"
    echo ""
    echo -e "    ${GREEN}[minimal]${NC}    10 dimensions - Quick structural check"
    echo -e "    ${GREEN}[standard]${NC}   25 dimensions - Balanced review"
    echo -e "    ${GREEN}[thorough]${NC}   40 dimensions - Detailed audit"
    echo -e "    ${GREEN}[exhaustive]${NC} 60 dimensions - Full audit"
    echo ""

    read -p "  Profile [standard]: " profile
    profile=${profile:-standard}

    local dim_count=25
    local selected_dims=""
    case "$profile" in
        minimal)
            dim_count=10
            selected_dims=$(_207_get_dimensions_for_profile "minimal")
            ;;
        standard)
            dim_count=25
            selected_dims=$(_207_get_dimensions_for_profile "standard")
            ;;
        thorough)
            dim_count=40
            selected_dims=$(_207_get_dimensions_for_profile "thorough")
            ;;
        exhaustive)
            dim_count=60
            selected_dims="$all_dimensions"
            ;;
    esac

    echo ""
    echo -e "  ${GREEN}✓${NC} Selected $profile profile ($dim_count dimensions)"
    echo ""

    # Build audit prompt with truncated PRD content
    local prd_content=""
    if [[ -f "$prd_file" ]]; then
        prd_content=$(atomic_context_truncate "$prd_file" 400)
    fi

    cat > "$prompts_dir/prd-audit.md" << EOF
# Task: Phase 2 PRD Audit (Legacy - $dim_count Dimensions)

You are an **independent PRD quality auditor** with expertise in requirements engineering and TDD workflows. Your role is to determine whether this PRD is sufficient for Phase 3 (task decomposition and implementation) - NOT to achieve perfection.

## Your Audit Philosophy

- **Gate, not grade** - checking "sufficient to proceed" not "A+ quality"
- **Tool-aware** - considering downstream parsing by TaskMaster/OpenSpec
- **Evidence-based** - every finding must cite specific PRD content
- **Constructive** - recommendations should be actionable in 1-2 hours

## Audience

You are auditing for:
- Development teams who will implement from this PRD
- TaskMaster/OpenSpec tools that will parse this PRD
- QA teams who will write tests based on acceptance criteria

## PRD Content

$prd_content

## Dimensions to Audit (Profile: $profile)

Each dimension has an ID, name, and specific check criteria. Audit ONLY these dimensions:

$selected_dims

## Scoring Criteria

Use these thresholds consistently:

**PASS**: Clear evidence the requirement is met. The PRD explicitly addresses this dimension. Sufficient for Phase 3.

**WARNING**: Partially met OR evidence is ambiguous OR minor gaps exist. Does NOT block progress but should be noted for improvement.

**CRITICAL**: Clearly not met OR missing essential elements OR would cause implementation failures in Phase 3. Must be addressed.

## Calibration Guidelines

- This is Phase 2 (PRD) - requirements should be more precise than Phase 1 Discovery
- CRITICAL should only be used for genuine blockers to implementation
- Prefer WARNING over CRITICAL for "could be more detailed" issues
- PASS doesn't mean perfect - it means "sufficient to proceed"
- Consider downstream tool parsing (TaskMaster, OpenSpec) needs

## Example Findings

**GOOD finding (specific, evidenced, actionable):**
{
  "PRD-R03": {
    "name": "RFC 2119 Keywords",
    "status": "WARNING",
    "finding": "PRD uses RFC 2119 keywords but inconsistently - 'must' appears 12 times without capitalization, 'SHOULD' appears correctly 8 times",
    "evidence": "Section 3.1 uses lowercase 'must' throughout; Section 3.2 correctly uses 'SHALL'",
    "recommendation": "Standardize on uppercase RFC 2119 keywords throughout for tool compatibility"
  }
}

**BAD finding (avoid - vague, no evidence):**
{
  "PRD-R03": {
    "name": "RFC 2119 Keywords",
    "status": "WARNING",
    "finding": "Keywords could be better",
    "evidence": "Looked at PRD",
    "recommendation": "Improve it"
  }
}

**More example findings by status:**

PASS example:
{
  "PRD-S04": {
    "name": "Feature Requirements",
    "status": "PASS",
    "finding": "Section 3 contains 12 FRs (FR-001 through FR-012) with clear acceptance criteria",
    "evidence": "Each FR follows format '### FR-XXX: Title' with bullet-pointed acceptance criteria",
    "recommendation": null
  }
}

CRITICAL example (use sparingly):
{
  "PRD-C01": {
    "name": "TaskMaster Dependency Chain",
    "status": "CRITICAL",
    "finding": "Section 5 (Logical Dependency Chain) is completely missing from the PRD",
    "evidence": "No Section 5 found; TOC jumps from Section 4 to Section 6",
    "recommendation": "Add Section 5 with task dependencies before Phase 3. TaskMaster cannot function without this."
  }
}

## Dimension Criticality Guide

**High criticality** (missing = likely CRITICAL):
- PRD-S04 (Feature Requirements), PRD-S05 (NFRs), PRD-C01 (Dependency Chain)

**Medium criticality** (missing = likely WARNING):
- PRD-R03 (RFC keywords), PRD-T01 (Scenarios), PRD-C02 (Tech Stack)

**Lower criticality** (missing = note but not blocking):
- PRD-P06 (Future Scope), PRD-K10 (Unknown Unknowns), PRD-P09 (Communication Plan)

## Anti-Patterns (avoid these)

- Marking everything PASS without citing specific section/line evidence
- CRITICAL status for stylistic issues rather than substantive gaps
- Vague findings without referencing specific PRD sections
- Ignoring truncation notices when evidence might be in omitted content
- Expecting Phase 2 to have Phase 4 (testing) level detail

## Output Format

For EACH dimension listed above, provide a finding with specific evidence.

Output as JSON:
{
  "audit_timestamp": "$(date -Iseconds)",
  "audit_mode": "legacy",
  "profile": "$profile",
  "dimensions_audited": $dim_count,
  "findings": {
    "PRD-XX": {
      "name": "Dimension Name (from the list)",
      "status": "PASS|WARNING|CRITICAL",
      "finding": "Specific observation with PRD section references",
      "evidence": "Quote or specific reference from PRD, or 'Not found in PRD'",
      "recommendation": "Specific action if not PASS, or null if PASS"
    }
  },
  "summary": {
    "passed": 0,
    "warnings": 0,
    "critical": 0
  },
  "overall_status": "PASS if no CRITICAL, WARNING if any warnings, CRITICAL if any critical",
  "proceed_recommendation": true,
  "proceed_rationale": "Brief explanation of readiness for Phase 3"
}

Output ONLY valid JSON. No markdown, no explanation.
EOF

    atomic_waiting "PRD auditor analyzing..."

    local audit_raw="$prompts_dir/audit-raw.json"
    if atomic_invoke "$prompts_dir/prd-audit.md" "$audit_raw" "PRD audit" --model=sonnet; then
        if jq -e . "$audit_raw" &>/dev/null; then
            cp "$audit_raw" "$audit_file"
            atomic_success "Audit complete"
        else
            atomic_warn "Invalid audit output"
            echo '{"overall_status": "WARNING", "summary": {"passed": 0, "warnings": 1, "critical": 0}}' > "$audit_file"
        fi
    else
        atomic_error "Audit failed"
        return 1
    fi

    # Display results
    _audit_display_results "$audit_file"

    return 0
}

# Get all 60 dimension definitions organized by category
_207_get_dimension_definitions() {
    cat << 'DIMENSIONS'
### STRUCTURE DIMENSIONS (PRD-S01 to PRD-S10)

PRD-S01: Vision Statement
- Check: Does Section 0 contain a clear, measurable vision statement?
- Criteria: Problem statement, target audience, success definition

PRD-S02: Executive Summary
- Check: Does Section 1 provide a standalone project overview?
- Criteria: Key objectives, scope summary, critical constraints

PRD-S03: Technical Architecture
- Check: Does Section 2 define the technical foundation?
- Criteria: Tech stack table, system components, data flow

PRD-S04: Feature Requirements
- Check: Does Section 3 enumerate all functional requirements?
- Criteria: FR numbering, priority levels, acceptance criteria

PRD-S05: Non-Functional Requirements
- Check: Does Section 4 specify NFRs with measurable targets?
- Criteria: Performance metrics, security requirements, scalability

PRD-S06: Logical Dependency Chain
- Check: Does Section 5 define task ordering for TaskMaster?
- Criteria: Prerequisite relationships, parallel opportunities

PRD-S07: Development Phases
- Check: Does Section 6 define scope-based (not time-based) phases?
- Criteria: Phase objectives, deliverables, exit criteria

PRD-S08: Code Structure
- Check: Does Section 7 define directory layout?
- Criteria: Folder structure, naming conventions, module organization

PRD-S09: Testing Strategy
- Check: Do Sections 8-9 define TDD and integration testing?
- Criteria: Test types, coverage targets, testing tools

PRD-S10: Operational Readiness
- Check: Do Sections 11-12 cover docs and operations?
- Criteria: Documentation plan, deployment, monitoring

### REQUIREMENTS QUALITY DIMENSIONS (PRD-R01 to PRD-R10)

PRD-R01: Requirement Numbering
- Check: Are all requirements uniquely numbered (FR-001, NFR-001)?
- Criteria: Consistent numbering scheme, no duplicates

PRD-R02: Priority Classification
- Check: Does each requirement have priority (P0/P1/P2)?
- Criteria: Clear priority levels, justification for P0s

PRD-R03: RFC 2119 Keywords
- Check: Are SHALL/SHOULD/MAY used correctly?
- Criteria: Uppercase keywords, consistent usage, no ambiguous "must"

PRD-R04: Acceptance Criteria
- Check: Does each FR have testable acceptance criteria?
- Criteria: Measurable outcomes, specific conditions

PRD-R05: Requirement Atomicity
- Check: Is each requirement focused on one capability?
- Criteria: No compound requirements, clear boundaries

PRD-R06: Requirement Traceability
- Check: Can requirements be traced to Phase 1 Discovery?
- Criteria: References to original goals, stakeholder needs

PRD-R07: Constraint Documentation
- Check: Are limitations and boundaries explicit?
- Criteria: Technical constraints, business constraints, regulatory

PRD-R08: Assumption Documentation
- Check: Are assumptions called out explicitly?
- Criteria: Assumptions section, risk if wrong

PRD-R09: Dependency Declaration
- Check: Are external dependencies documented?
- Criteria: Third-party services, libraries, APIs

PRD-R10: Out of Scope Items
- Check: Is out-of-scope explicitly defined?
- Criteria: Clear exclusions, rationale for exclusions

### TESTABILITY DIMENSIONS (PRD-T01 to PRD-T10)

PRD-T01: WHEN/THEN Scenarios
- Check: Does each FR have WHEN/THEN format scenarios?
- Criteria: Given/When/Then or When/Then patterns

PRD-T02: Measurable Metrics
- Check: Are NFRs quantified with specific numbers?
- Criteria: "<200ms", "99.9%", not "fast" or "reliable"

PRD-T03: Boundary Conditions
- Check: Are edge cases documented in scenarios?
- Criteria: Empty states, max limits, error conditions

PRD-T04: Negative Test Cases
- Check: Are failure scenarios documented?
- Criteria: Invalid input handling, error responses

PRD-T05: Integration Points
- Check: Are system integration test points defined?
- Criteria: API contracts, data exchange formats

PRD-T06: User Journey Coverage
- Check: Are complete user workflows documented?
- Criteria: Happy path, alternative paths

PRD-T07: Gherkin Compatibility
- Check: Can scenarios be converted to Gherkin directly?
- Criteria: Scenario: blocks, Given/When/Then structure

PRD-T08: Test Data Requirements
- Check: Are test data needs specified?
- Criteria: Sample data, data constraints

PRD-T09: Environment Requirements
- Check: Are test environment needs documented?
- Criteria: Dev/staging/prod parity, dependencies

PRD-T10: Coverage Targets
- Check: Are code coverage targets specified?
- Criteria: Unit test %, integration test %, E2E coverage

### TOOL COMPATIBILITY DIMENSIONS (PRD-C01 to PRD-C10)

PRD-C01: TaskMaster Dependency Chain
- Check: Is Section 5 parseable by TaskMaster?
- Criteria: Clear task ordering, dependency arrows or lists

PRD-C02: TaskMaster Tech Stack
- Check: Is tech stack in table format?
- Criteria: Technology | Version | Purpose format

PRD-C03: TaskMaster Phase Scope
- Check: Are phases scope-based, not time-based?
- Criteria: "Phase 1: Core Auth" not "Week 1-2"

PRD-C04: OpenSpec Requirement Format
- Check: Do requirements follow ### Requirement: Name?
- Criteria: Consistent heading levels, parseable format

PRD-C05: OpenSpec Scenario Format
- Check: Are scenarios in #### Scenario: Name format?
- Criteria: Nested under requirements, WHEN/THEN body

PRD-C06: OpenSpec Priority Tags
- Check: Are priorities in parseable format?
- Criteria: [P0], [P1], [P2] or Priority: P0

PRD-C07: Machine-Readable Structure
- Check: Could this PRD be parsed by a script?
- Criteria: Consistent markdown, predictable structure

PRD-C08: Cross-Reference Format
- Check: Are requirement references consistent?
- Criteria: "See FR-003" not "see the auth requirement"

PRD-C09: Version Control Readiness
- Check: Is the PRD diffable and mergeable?
- Criteria: Line-based changes, no embedded binaries

PRD-C10: API Contract Definitions
- Check: Are API contracts defined clearly?
- Criteria: Endpoint, method, request/response schemas

### RISK & FEASIBILITY DIMENSIONS (PRD-K01 to PRD-K10)

PRD-K01: Risk Identification
- Check: Does Section 12 list project risks?
- Criteria: Technical, schedule, resource, external risks

PRD-K02: Risk Mitigation
- Check: Does each risk have a mitigation strategy?
- Criteria: Preventive measures, contingency plans

PRD-K03: Risk Priority
- Check: Are risks prioritized by likelihood/impact?
- Criteria: Risk matrix or priority levels

PRD-K04: Technical Feasibility
- Check: Has technical feasibility been assessed?
- Criteria: Proof of concept references, known patterns

PRD-K05: Resource Feasibility
- Check: Are skill requirements documented?
- Criteria: Team capabilities, learning curve

PRD-K06: Third-Party Dependencies
- Check: Are external risks from dependencies noted?
- Criteria: Vendor stability, license issues, deprecation

PRD-K07: Security Considerations
- Check: Are security risks identified?
- Criteria: OWASP considerations, data protection

PRD-K08: Scalability Assessment
- Check: Are growth risks considered?
- Criteria: 10x load scenarios, bottleneck identification

PRD-K09: Integration Risks
- Check: Are integration failure modes documented?
- Criteria: Fallback strategies, circuit breakers

PRD-K10: Unknown Unknowns
- Check: Is there acknowledgment of uncertainty?
- Criteria: Exploration spikes, proof-of-concept needs

### SCOPE & STAKEHOLDER DIMENSIONS (PRD-P01 to PRD-P10)

PRD-P01: Stakeholder Identification
- Check: Are all stakeholders listed?
- Criteria: Users, operators, developers, business owners

PRD-P02: Stakeholder Needs
- Check: Are stakeholder needs mapped to requirements?
- Criteria: Traceability from stakeholder to FR

PRD-P03: Success Metrics
- Check: Does Section 13 define measurable success?
- Criteria: KPIs, OKRs, acceptance thresholds

PRD-P04: Scope Boundaries
- Check: Is scope clearly bounded?
- Criteria: Explicit inclusions, explicit exclusions

PRD-P05: MVP Definition
- Check: Is minimum viable product defined?
- Criteria: Phase 1 scope, must-have vs nice-to-have

PRD-P06: Future Scope
- Check: Are future phases indicated but deferred?
- Criteria: "Future consideration" items, roadmap hints

PRD-P07: Approval Criteria
- Check: Does Section 14 define approval process?
- Criteria: Sign-off requirements, approval authority

PRD-P08: Change Management
- Check: Is there a process for PRD changes?
- Criteria: Version control, change request process

PRD-P09: Communication Plan
- Check: Are update mechanisms defined?
- Criteria: Stakeholder notifications, review cadence

PRD-P10: Glossary Completeness
- Check: Are domain terms defined?
- Criteria: Terminology section, acronym definitions
DIMENSIONS
}

# Get dimensions for a specific profile
_207_get_dimensions_for_profile() {
    local profile="$1"

    case "$profile" in
        minimal)
            # 10 most critical dimensions
            cat << 'DIMS'
PRD-S01: Vision Statement - Check: Clear, measurable vision in Section 0
PRD-S04: Feature Requirements - Check: FRs enumerated with acceptance criteria
PRD-S05: Non-Functional Requirements - Check: NFRs with measurable targets
PRD-R03: RFC 2119 Keywords - Check: SHALL/SHOULD/MAY used correctly
PRD-R04: Acceptance Criteria - Check: Each FR has testable criteria
PRD-T01: WHEN/THEN Scenarios - Check: FRs have scenario format
PRD-C01: TaskMaster Dependency Chain - Check: Section 5 has task ordering
PRD-C02: TaskMaster Tech Stack - Check: Tech stack in table format
PRD-K01: Risk Identification - Check: Section 12 lists project risks
PRD-P04: Scope Boundaries - Check: Explicit inclusions/exclusions
DIMS
            ;;
        standard)
            # 25 dimensions covering all categories
            _207_get_dimension_definitions | grep -E "^PRD-S0[1-5]:|^PRD-R0[1-5]:|^PRD-T0[1-5]:|^PRD-C0[1-5]:|^PRD-K0[1-3]:|^PRD-P0[1-2]:" | head -25
            # Simplified: extract first 5 from each major category
            cat << 'DIMS'
### Structure (5)
PRD-S01: Vision Statement - Check: Clear, measurable vision in Section 0
PRD-S02: Executive Summary - Check: Standalone project overview in Section 1
PRD-S03: Technical Architecture - Check: Tech stack and system components
PRD-S04: Feature Requirements - Check: FRs enumerated with acceptance criteria
PRD-S05: Non-Functional Requirements - Check: NFRs with measurable targets

### Requirements Quality (5)
PRD-R01: Requirement Numbering - Check: FR-001, NFR-001 format
PRD-R02: Priority Classification - Check: P0/P1/P2 for each requirement
PRD-R03: RFC 2119 Keywords - Check: SHALL/SHOULD/MAY used correctly
PRD-R04: Acceptance Criteria - Check: Each FR has testable criteria
PRD-R05: Requirement Atomicity - Check: Each requirement focused on one thing

### Testability (5)
PRD-T01: WHEN/THEN Scenarios - Check: FRs have scenario format
PRD-T02: Measurable Metrics - Check: NFRs quantified (<200ms, 99.9%)
PRD-T03: Boundary Conditions - Check: Edge cases documented
PRD-T04: Negative Test Cases - Check: Failure scenarios included
PRD-T07: Gherkin Compatibility - Check: Scenarios convertible to Gherkin

### Tool Compatibility (5)
PRD-C01: TaskMaster Dependency Chain - Check: Section 5 parseable
PRD-C02: TaskMaster Tech Stack - Check: Tech stack table format
PRD-C03: TaskMaster Phase Scope - Check: Scope-based, not time-based
PRD-C04: OpenSpec Requirement Format - Check: ### Requirement: Name
PRD-C05: OpenSpec Scenario Format - Check: #### Scenario: Name

### Risk & Scope (5)
PRD-K01: Risk Identification - Check: Section 12 lists risks
PRD-K02: Risk Mitigation - Check: Each risk has mitigation
PRD-P03: Success Metrics - Check: Section 13 has KPIs
PRD-P04: Scope Boundaries - Check: Clear inclusions/exclusions
PRD-P05: MVP Definition - Check: Phase 1 scope defined
DIMS
            ;;
        thorough)
            # 40 dimensions - all structure, requirements, testability, tool-compat, plus key risk/scope
            cat << 'DIMS'
### Structure (10)
PRD-S01: Vision Statement - Check: Clear, measurable vision
PRD-S02: Executive Summary - Check: Standalone project overview
PRD-S03: Technical Architecture - Check: Tech stack and components
PRD-S04: Feature Requirements - Check: FRs with acceptance criteria
PRD-S05: Non-Functional Requirements - Check: NFRs with targets
PRD-S06: Logical Dependency Chain - Check: Task ordering for TaskMaster
PRD-S07: Development Phases - Check: Scope-based phases
PRD-S08: Code Structure - Check: Directory layout defined
PRD-S09: Testing Strategy - Check: TDD and integration testing
PRD-S10: Operational Readiness - Check: Docs and deployment

### Requirements Quality (10)
PRD-R01: Requirement Numbering - Check: FR-001 format
PRD-R02: Priority Classification - Check: P0/P1/P2 levels
PRD-R03: RFC 2119 Keywords - Check: SHALL/SHOULD/MAY
PRD-R04: Acceptance Criteria - Check: Testable criteria
PRD-R05: Requirement Atomicity - Check: One capability each
PRD-R06: Requirement Traceability - Check: Links to Phase 1
PRD-R07: Constraint Documentation - Check: Limitations explicit
PRD-R08: Assumption Documentation - Check: Assumptions stated
PRD-R09: Dependency Declaration - Check: External deps listed
PRD-R10: Out of Scope Items - Check: Exclusions defined

### Testability (10)
PRD-T01: WHEN/THEN Scenarios - Check: Scenario format
PRD-T02: Measurable Metrics - Check: Quantified NFRs
PRD-T03: Boundary Conditions - Check: Edge cases
PRD-T04: Negative Test Cases - Check: Failure scenarios
PRD-T05: Integration Points - Check: API test points
PRD-T06: User Journey Coverage - Check: Complete workflows
PRD-T07: Gherkin Compatibility - Check: Gherkin-ready
PRD-T08: Test Data Requirements - Check: Data needs
PRD-T09: Environment Requirements - Check: Env needs
PRD-T10: Coverage Targets - Check: Coverage %

### Tool Compatibility (5)
PRD-C01: TaskMaster Dependency Chain - Check: Parseable deps
PRD-C02: TaskMaster Tech Stack - Check: Table format
PRD-C03: TaskMaster Phase Scope - Check: Scope-based
PRD-C04: OpenSpec Requirement Format - Check: ### Requirement:
PRD-C05: OpenSpec Scenario Format - Check: #### Scenario:

### Risk & Scope (5)
PRD-K01: Risk Identification - Check: Risks listed
PRD-K02: Risk Mitigation - Check: Mitigations exist
PRD-K03: Risk Priority - Check: Risks prioritized
PRD-P03: Success Metrics - Check: KPIs defined
PRD-P04: Scope Boundaries - Check: Scope clear
DIMS
            ;;
    esac
}

# Shared results display function
_audit_display_results() {
    local audit_file="$1"

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AUDIT FINDINGS${NC}                                               ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local passed=$(jq -r '.summary.passed // 0' "$audit_file")
    local warnings=$(jq -r '.summary.warnings // 0' "$audit_file")
    local critical=$(jq -r '.summary.critical // 0' "$audit_file")
    local overall=$(jq -r '.overall_status // "UNKNOWN"' "$audit_file")

    local status_color="${GREEN}"
    [[ "$overall" == "WARNING" ]] && status_color="${YELLOW}"
    [[ "$overall" == "CRITICAL" ]] && status_color="${RED}"

    echo -e "  ${status_color}Overall Status: $overall${NC}"
    echo ""
    echo -e "  ${GREEN}PASSED:${NC}   $passed"
    echo -e "  ${YELLOW}WARNINGS:${NC} $warnings"
    echo -e "  ${RED}CRITICAL:${NC} $critical"
    echo ""

    atomic_context_artifact "phase_audit" "$audit_file" "Phase 2 audit results"
    atomic_success "Phase audit complete"
}
