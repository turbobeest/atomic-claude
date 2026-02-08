# Continuity & UX/UI Testing Plan

**Date**: 2026-02-07
**Purpose**: Comprehensive end-to-end and user experience validation
**Status**: Ready to execute

---

## Overview

This document outlines a complete testing strategy for:
1. **Full Continuity Testing** - End-to-end pipeline execution
2. **Functional Evaluation** - Input/output validation with sample data
3. **UX/UI Subjective Evaluation** - User experience assessment

---

## 1. Full Continuity Testing

### Objective

Verify the complete pipeline execution from Phase 0 through Phase 9 with sample data, ensuring:
- All phases execute successfully
- State persists correctly between phases
- Outputs are generated and passed forward
- Resume/backtrack functionality works
- Error recovery behaves correctly

### Test Scenarios

#### Scenario 1: Complete Pipeline (Happy Path)

**Goal**: Execute all 10 phases with minimal sample data

**Sample Project**: "Simple Calculator CLI"
- Small, well-defined scope
- Clear requirements
- Easy to validate outputs

**Test Steps**:
```bash
# 1. Clean environment
rm -rf .state .outputs
export ATOMIC_UAT_MODE=false

# 2. Run Phase 0 (Setup)
python main.py run 0

# Expected:
# - User prompted for project details
# - Config file created (.outputs/0-setup/config.json)
# - Closeout generated (.outputs/0-setup/closeout.json)
# - State updated (Phase 0 complete)

# 3. Run Phase 1 (Discovery)
python main.py run 1

# Expected:
# - Reads Phase 0 config
# - Performs discovery tasks
# - Generates discovery report
# - Closeout created

# 4. Continue through Phase 9
python main.py run 2
python main.py run 3
python main.py run 4
python main.py run 5
python main.py run 6
python main.py run 7
python main.py run 8
python main.py run 9

# 5. Verify complete pipeline
python main.py status
cat .state/task-state.json | jq '.phases | keys'
```

**Success Criteria**:
- ✅ All 10 phases complete
- ✅ All 74 tasks executed
- ✅ 10 closeout files generated
- ✅ State file shows all phases complete
- ✅ No errors or crashes

#### Scenario 2: Resume After Interruption

**Goal**: Verify resume functionality

**Test Steps**:
```bash
# 1. Start Phase 1
python main.py run 1

# 2. Interrupt mid-phase (Ctrl+C after task 103)

# 3. Check state
python main.py status
# Should show Phase 1 in progress, tasks 101-103 complete

# 4. Resume
python main.py run 1
# Should skip 101-103, continue from 104

# 5. Verify completion
python main.py status
# Should show Phase 1 complete
```

**Success Criteria**:
- ✅ Completed tasks not re-executed
- ✅ Resume from correct task
- ✅ State consistency maintained

#### Scenario 3: Resume from Specific Task

**Goal**: Test targeted resume

**Test Steps**:
```bash
# 1. Complete Phase 1
python main.py run 1

# 2. Resume from task 105
python main.py run 1 --resume-at=105

# 3. Check which tasks ran
# Should re-execute 105-110 only
```

**Success Criteria**:
- ✅ Resume from specified task
- ✅ Earlier tasks skipped
- ✅ Later tasks executed

#### Scenario 4: Backtrack and Re-execute

**Goal**: Verify backtrack functionality

**Test Steps**:
```bash
# 1. Complete Phases 0-2
python main.py run 0
python main.py run 1
python main.py run 2

# 2. Backtrack to Phase 1, task 105
python main.py backtrack 1 105

# 3. Check state
python main.py status
# Should show Phase 2 incomplete, Phase 1 at task 105

# 4. Re-execute from 105
python main.py run 1
python main.py run 2

# 5. Verify changes propagated
```

**Success Criteria**:
- ✅ Later phases reset
- ✅ State correctly backtracked
- ✅ Re-execution works
- ✅ Changes propagate forward

#### Scenario 5: Error Recovery

**Goal**: Test error handling and recovery

**Test Steps**:
```bash
# 1. Inject a failure (modify task to fail)
# Edit a task file to return False

# 2. Run phase
python main.py run 1
# Should fail at modified task

# 3. Check state
python main.py status
# Should show partial completion

# 4. Fix the task
# Restore task to working state

# 5. Resume
python main.py run 1
# Should continue from failure point

# 6. Verify completion
```

**Success Criteria**:
- ✅ Error reported clearly
- ✅ State shows partial progress
- ✅ Resume after fix works
- ✅ No data corruption

---

## 2. Functional Evaluation with Sample Data

### Objective

Validate that each phase produces correct, well-formatted outputs using sample input data.

### Sample Project: "Task Manager API"

**Project Details**:
- **Name**: TaskFlow API
- **Type**: REST API
- **Tech Stack**: Python, FastAPI, PostgreSQL
- **Scope**: CRUD operations for tasks, users, projects
- **Complexity**: Medium (suitable for full pipeline test)

### Phase-by-Phase Validation

#### Phase 0: Setup

**Input**:
```json
{
  "project_name": "TaskFlow API",
  "project_type": "rest_api",
  "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
  "primary_language": "Python",
  "target_audience": "Developers",
  "deployment_target": "Docker + Kubernetes"
}
```

**Expected Outputs**:
- `config.json` - Project configuration
- `closeout.json` - Phase summary

**Validation**:
```bash
# Check config file
cat .outputs/0-setup/config.json | jq .
# Should contain all input fields

# Check closeout
cat .outputs/0-setup/closeout.json | jq .
# Should summarize Phase 0 completion
```

#### Phase 1: Discovery

**Input**: Phase 0 config + reference materials

**Expected Outputs**:
- `discovery-report.md` - Comprehensive discovery findings
- `tech-stack-analysis.md` - Technology assessment
- `architecture-overview.md` - High-level architecture
- `closeout.json`

**Validation**:
```bash
# Check discovery report exists
test -f .outputs/1-discovery/discovery-report.md

# Verify content quality
wc -l .outputs/1-discovery/discovery-report.md
# Should be substantial (500+ lines)

# Check for key sections
grep -i "technical requirements" .outputs/1-discovery/discovery-report.md
grep -i "constraints" .outputs/1-discovery/discovery-report.md
grep -i "recommendations" .outputs/1-discovery/discovery-report.md
```

#### Phase 2: PRD

**Expected Outputs**:
- `prd.md` - Product Requirements Document
- `user-stories.md` - User story definitions
- `acceptance-criteria.md` - Success criteria
- `closeout.json`

**Validation**:
```bash
# Check PRD structure
grep "## " .outputs/2-prd/prd.md
# Should have sections: Overview, Goals, Features, Requirements, etc.

# Verify user stories
grep -c "As a" .outputs/2-prd/user-stories.md
# Should have multiple user stories (10+)

# Check acceptance criteria
test -f .outputs/2-prd/acceptance-criteria.md
```

#### Phase 3: Tasking

**Expected Outputs**:
- `task-breakdown.md` - Detailed task list
- `task-dependencies.md` - Dependency graph
- `effort-estimates.md` - Time/complexity estimates
- `closeout.json`

**Validation**:
```bash
# Count tasks
grep -c "^- \[" .outputs/3-tasking/task-breakdown.md
# Should have 20+ tasks

# Check for dependencies
grep -i "depends on" .outputs/3-tasking/task-dependencies.md

# Verify estimates
grep -i "estimated" .outputs/3-tasking/effort-estimates.md
```

#### Phase 4: Specification

**Expected Outputs**:
- `technical-spec.md` - Detailed technical specification
- `api-spec.yaml` - OpenAPI specification
- `data-models.md` - Data model definitions
- `closeout.json`

**Validation**:
```bash
# Check spec completeness
wc -l .outputs/4-specification/technical-spec.md
# Should be comprehensive (1000+ lines)

# Validate OpenAPI spec
python -c "import yaml; yaml.safe_load(open('.outputs/4-specification/api-spec.yaml'))"
# Should parse without errors

# Check data models
grep -c "class " .outputs/4-specification/data-models.md
```

#### Phase 5: Implementation

**Expected Outputs**:
- `implementation-plan.md` - Implementation strategy
- `code-structure.md` - Directory structure
- `development-guidelines.md` - Coding standards
- `closeout.json`

**Validation**:
```bash
# Check plan exists
test -f .outputs/5-implementation/implementation-plan.md

# Verify directory structure
grep -c "└──" .outputs/5-implementation/code-structure.md
# Should have tree structure

# Check guidelines
grep -i "naming convention" .outputs/5-implementation/development-guidelines.md
```

#### Phase 6: Code Review

**Expected Outputs**:
- `review-checklist.md` - Review criteria
- `quality-standards.md` - Quality benchmarks
- `review-process.md` - Review workflow
- `closeout.json`

**Validation**:
```bash
# Check checklist
grep -c "- \[" .outputs/6-code-review/review-checklist.md

# Verify standards
test -f .outputs/6-code-review/quality-standards.md

# Check process defined
grep -i "step" .outputs/6-code-review/review-process.md
```

#### Phase 7: Integration

**Expected Outputs**:
- `integration-plan.md` - Integration strategy
- `integration-tests.md` - Test specifications
- `deployment-config.md` - Configuration
- `closeout.json`

**Validation**:
```bash
# Check integration plan
test -f .outputs/7-integration/integration-plan.md

# Verify test specs
grep -c "test_" .outputs/7-integration/integration-tests.md

# Check deployment config
grep -i "environment" .outputs/7-integration/deployment-config.md
```

#### Phase 8: Deployment Prep

**Expected Outputs**:
- `deployment-plan.md` - Deployment strategy
- `infrastructure-spec.md` - Infrastructure requirements
- `runbook.md` - Operations runbook
- `closeout.json`

**Validation**:
```bash
# Check deployment plan
grep -i "deployment step" .outputs/8-deployment-prep/deployment-plan.md

# Verify infrastructure
grep -i "kubernetes" .outputs/8-deployment-prep/infrastructure-spec.md

# Check runbook
grep -i "troubleshooting" .outputs/8-deployment-prep/runbook.md
```

#### Phase 9: Release

**Expected Outputs**:
- `release-notes.md` - Release documentation
- `launch-checklist.md` - Go-live checklist
- `monitoring-plan.md` - Post-launch monitoring
- `closeout.json`

**Validation**:
```bash
# Check release notes
test -f .outputs/9-release/release-notes.md

# Verify checklist
grep -c "- \[" .outputs/9-release/launch-checklist.md

# Check monitoring
grep -i "metrics" .outputs/9-release/monitoring-plan.md
```

### Automated Validation Script

```bash
#!/bin/bash
# validate-outputs.sh

echo "Validating Phase Outputs..."

PHASES=(
  "0-setup:config.json,closeout.json"
  "1-discovery:discovery-report.md,closeout.json"
  "2-prd:prd.md,user-stories.md,closeout.json"
  "3-tasking:task-breakdown.md,closeout.json"
  "4-specification:technical-spec.md,closeout.json"
  "5-implementation:implementation-plan.md,closeout.json"
  "6-code-review:review-checklist.md,closeout.json"
  "7-integration:integration-plan.md,closeout.json"
  "8-deployment-prep:deployment-plan.md,closeout.json"
  "9-release:release-notes.md,closeout.json"
)

for phase_spec in "${PHASES[@]}"; do
  phase="${phase_spec%%:*}"
  files="${phase_spec#*:}"

  echo ""
  echo "Checking Phase $phase..."

  IFS=',' read -ra FILE_LIST <<< "$files"
  for file in "${FILE_LIST[@]}"; do
    path=".outputs/$phase/$file"
    if [[ -f "$path" ]]; then
      size=$(wc -c < "$path")
      echo "  ✓ $file ($size bytes)"
    else
      echo "  ✗ $file MISSING"
    fi
  done
done

echo ""
echo "Validation complete."
```

---

## 3. UX/UI Subjective Evaluation

### Objective

Assess the user experience of interactive components with sample data to ensure:
- Clear, intuitive prompts
- Appropriate menu options
- Helpful feedback messages
- Smooth interaction flow
- Professional presentation

### Interactive Touchpoints

#### Touchpoint 1: Mode Selection (Task 001)

**User Interaction**:
```
============================================================
PHASE 0: SETUP
============================================================

Task 001: Mode Selection

? Select operational mode:
  1. Interactive Mode (manual approval at each step)
  2. UAT Mode (automated with sample data)

Your choice [1-2]:
```

**UX Evaluation Criteria**:
- [ ] Prompt is clear and easy to understand
- [ ] Options are well-explained
- [ ] Default value is sensible
- [ ] Input validation provides helpful error messages
- [ ] Visual formatting is professional (colors, spacing)

**Sample Test**:
```bash
# Test 1: Valid input
echo "1" | python main.py run 0

# Test 2: Invalid input
echo "5" | python main.py run 0
# Should show error and re-prompt

# Test 3: Empty input (should use default)
echo "" | python main.py run 0
```

#### Touchpoint 2: Config Collection (Task 002)

**User Interaction**:
```
Task 002: Configuration Collection

Please provide project details:

? Project name: TaskFlow API
? Project type (web_app/api/cli/library): api
? Primary language: Python
? Tech stack (comma-separated): FastAPI, PostgreSQL, Docker
? Target audience: Developers
? Deployment target: Kubernetes

Confirm these settings? (y/n):
```

**UX Evaluation Criteria**:
- [ ] Questions are logically ordered
- [ ] Examples/hints are provided
- [ ] Input validation is helpful, not annoying
- [ ] Confirmation summary is clear
- [ ] Easy to correct mistakes

**Sample Test**:
```bash
# Create sample input file
cat > sample-config-input.txt << EOF
TaskFlow API
api
Python
FastAPI, PostgreSQL, Docker
Developers
Kubernetes
y
EOF

# Test with sample input
cat sample-config-input.txt | python main.py run 0
```

#### Touchpoint 3: Config Review (Task 003)

**User Interaction**:
```
Task 003: Configuration Review

Current Configuration:
┌─────────────────────┬──────────────────────────────────┐
│ Field               │ Value                            │
├─────────────────────┼──────────────────────────────────┤
│ Project Name        │ TaskFlow API                     │
│ Project Type        │ REST API                         │
│ Primary Language    │ Python                           │
│ Tech Stack          │ FastAPI, PostgreSQL, Docker      │
│ Target Audience     │ Developers                       │
│ Deployment Target   │ Kubernetes                       │
└─────────────────────┴──────────────────────────────────┘

? Is this configuration correct?
  1. Yes, continue
  2. Edit configuration
  3. Start over

Your choice [1-3]:
```

**UX Evaluation Criteria**:
- [ ] Configuration displayed clearly (table format)
- [ ] All fields visible at once
- [ ] Edit options are obvious
- [ ] Visual formatting is professional
- [ ] Navigation is intuitive

#### Touchpoint 4: API Key Setup (Task 004)

**User Interaction**:
```
Task 004: API Key Setup

LLM Provider Configuration:

? Select LLM provider:
  1. Anthropic (Claude API)
  2. AWS Bedrock (Claude via AWS)
  3. Ollama (Local models)

Your choice [1-3]: 1

? Anthropic API key (or press Enter to use existing):
[                                                      ]

? Primary model role:
  1. opus (most capable, expensive)
  2. sonnet (balanced, recommended)
  3. haiku (fast, economical)

Your choice [1-3]: 2

✓ Configuration saved to .env
✓ API key validated
```

**UX Evaluation Criteria**:
- [ ] Provider options clearly explained
- [ ] API key input is masked/hidden
- [ ] Existing keys can be kept
- [ ] Model selection has helpful descriptions
- [ ] Validation feedback is immediate
- [ ] Success confirmation is clear

#### Touchpoint 5: Reference Material Selection (Task 006)

**User Interaction**:
```
Task 006: Reference Material Selection

Available reference materials:
┌────┬───────────────────────────────┬──────────┬────────────┐
│ #  │ File                          │ Type     │ Size       │
├────┼───────────────────────────────┼──────────┼────────────┤
│ 1  │ api-design-guidelines.pdf     │ PDF      │ 2.4 MB     │
│ 2  │ fastapi-best-practices.md     │ Markdown │ 156 KB     │
│ 3  │ database-schema.sql           │ SQL      │ 45 KB      │
│ 4  │ existing-codebase/            │ Dir      │ 12.3 MB    │
│ 5  │ requirements.txt              │ Text     │ 2 KB       │
└────┴───────────────────────────────┴──────────┴────────────┘

? Select materials to include (comma-separated, or 'all'):
[1,2,3,5]

Selected materials:
  ✓ api-design-guidelines.pdf
  ✓ fastapi-best-practices.md
  ✓ database-schema.sql
  ✓ requirements.txt

? Proceed with these selections? (y/n): y

✓ Reference materials copied to .outputs/0-setup/references/
```

**UX Evaluation Criteria**:
- [ ] File list is easy to scan (table format)
- [ ] File types and sizes shown
- [ ] Multiple selection is intuitive
- [ ] Confirmation shows what was selected
- [ ] 'all' option is available
- [ ] Progress feedback for large operations

#### Touchpoint 6: Agent Selection (Task 201 - PRD Creation)

**User Interaction**:
```
Task 201: PRD Creation

? Select PRD creation approach:
  1. Use specialized agent (recommended)
  2. Use standard prompt
  3. Manual creation (skip automation)

Your choice [1-3]: 1

Available agents for PRD creation:
┌────┬─────────────────────────────────┬─────────────────┐
│ #  │ Agent                           │ Expertise       │
├────┼─────────────────────────────────┼─────────────────┤
│ 1  │ prd-architect                   │ PRD design      │
│ 2  │ product-requirements-expert     │ Requirements    │
│ 3  │ technical-specification-writer  │ Tech specs      │
└────┴─────────────────────────────────┴─────────────────┘

? Select agent [1-3]: 1

✓ Agent 'prd-architect' selected
⚙ Invoking agent...
⚙ Processing discovery outputs...
⚙ Generating PRD...
✓ PRD generated: .outputs/2-prd/prd.md (2,456 lines)
```

**UX Evaluation Criteria**:
- [ ] Agent selection is optional (can use standard)
- [ ] Agent descriptions are helpful
- [ ] Progress indicators during long operations
- [ ] Success message shows output location
- [ ] File size/metrics provided

#### Touchpoint 7: Audit Selection (Task 210 - PRD Audit)

**User Interaction**:
```
Task 210: PRD Audit

? Run quality audit on PRD?
  1. Yes, select audit (recommended)
  2. Skip audit
  3. Batch audit (multiple audits)

Your choice [1-3]: 1

Available audits:
┌────┬─────────────────────────────────────────────────────┐
│ #  │ Audit                                               │
├────┼─────────────────────────────────────────────────────┤
│ 1  │ prd-completeness-check                              │
│ 2  │ requirements-validation                             │
│ 3  │ technical-feasibility-review                        │
│ 4  │ stakeholder-alignment-check                         │
│ 5  │ acceptance-criteria-validation                      │
└────┴─────────────────────────────────────────────────────┘

? Select audit [1-5]: 1

✓ Audit 'prd-completeness-check' selected
⚙ Running audit...
⚙ Analyzing PRD structure...
⚙ Checking completeness...

Audit Results:
┌────────────────────────────┬─────────┬────────────────────┐
│ Criterion                  │ Status  │ Notes              │
├────────────────────────────┼─────────┼────────────────────┤
│ Executive Summary          │ ✓ Pass  │ Well-defined       │
│ Goals & Objectives         │ ✓ Pass  │ Clear, measurable  │
│ User Stories               │ ⚠ Warn  │ Need more detail   │
│ Acceptance Criteria        │ ✓ Pass  │ Comprehensive      │
│ Technical Requirements     │ ✓ Pass  │ Detailed           │
│ Constraints                │ ✗ Fail  │ Missing section    │
└────────────────────────────┴─────────┴────────────────────┘

Overall: 4/6 passed, 1 warning, 1 failure

? Action:
  1. Continue (warnings/failures noted)
  2. Review and fix issues
  3. Re-run audit

Your choice [1-3]:
```

**UX Evaluation Criteria**:
- [ ] Audit purpose is clear
- [ ] Can skip if desired
- [ ] Audit results are easy to understand
- [ ] Pass/warn/fail indicators are clear
- [ ] Can take action on results
- [ ] Detailed feedback helps fix issues

### UX/UI Test Script

Create a test script that exercises all interactive touchpoints:

```bash
#!/bin/bash
# uxui-test.sh - Interactive UX/UI evaluation

echo "=========================================="
echo "UX/UI Interactive Evaluation"
echo "=========================================="
echo ""
echo "This script will walk through all user interaction points."
echo "Please evaluate the user experience at each step."
echo ""

# Phase 0 interactions
echo "=== PHASE 0: SETUP ==="
echo ""
echo "1. Mode Selection"
echo "   Evaluate: Clarity, options, validation"
read -p "Press Enter to continue..."
python main.py run 0 --task=001

echo ""
echo "2. Config Collection"
echo "   Evaluate: Questions, flow, validation"
read -p "Press Enter to continue..."
python main.py run 0 --task=002

echo ""
echo "3. Config Review"
echo "   Evaluate: Display format, edit options"
read -p "Press Enter to continue..."
python main.py run 0 --task=003

# ... continue for all interactive touchpoints
```

---

## 4. Test Execution Plan

### Timeline

**Week 1: Continuity Testing**
- Day 1-2: Scenario 1 (Happy path)
- Day 3: Scenarios 2-3 (Resume)
- Day 4: Scenario 4 (Backtrack)
- Day 5: Scenario 5 (Error recovery)

**Week 2: Functional Evaluation**
- Day 1-2: Phases 0-4 output validation
- Day 3-4: Phases 5-9 output validation
- Day 5: Automated validation script

**Week 3: UX/UI Evaluation**
- Day 1: Setup touchpoints (Tasks 001-009)
- Day 2: Discovery touchpoints (Tasks 101-110)
- Day 3: PRD touchpoints (Tasks 201-210)
- Day 4: Implementation touchpoints (Tasks 301-609)
- Day 5: UX/UI report and improvements

### Resources Needed

**Environment**:
- Clean test environment (separate from development)
- Sample data sets prepared
- LLM API access (or UAT mode)

**Personnel**:
- 1 Test Engineer (continuity testing)
- 1 QA Analyst (functional validation)
- 1 UX Designer (UX/UI evaluation)
- 1 Developer (bug fixes)

**Tools**:
- Test automation scripts
- Output validation scripts
- Screen recording (for UX evaluation)
- Feedback collection forms

---

## 5. Success Criteria

### Continuity Testing

- [ ] All 5 scenarios pass without errors
- [ ] State consistency maintained throughout
- [ ] Resume/backtrack work correctly
- [ ] Error recovery is graceful
- [ ] No data loss or corruption

### Functional Evaluation

- [ ] All phases generate expected outputs
- [ ] Output quality is acceptable (manual review)
- [ ] File formats are correct
- [ ] Content is relevant and useful
- [ ] Closeout files are properly formatted

### UX/UI Evaluation

- [ ] All prompts are clear and intuitive
- [ ] Input validation is helpful
- [ ] Error messages are actionable
- [ ] Visual formatting is professional
- [ ] Navigation is smooth
- [ ] No confusing or misleading interfaces

---

## 6. Deliverables

1. **Continuity Test Report**
   - Scenario execution results
   - State consistency validation
   - Performance metrics
   - Issues identified

2. **Functional Test Report**
   - Phase-by-phase output validation
   - Sample data test results
   - Output quality assessment
   - Recommendations

3. **UX/UI Evaluation Report**
   - Touchpoint-by-touchpoint assessment
   - Screenshots/recordings
   - User experience ratings
   - Improvement recommendations

4. **Bug/Issue Log**
   - Issues found during testing
   - Severity/priority
   - Reproduction steps
   - Fix status

5. **Test Automation Suite**
   - Automated validation scripts
   - Sample data generators
   - Output checkers
   - Regression test suite

---

## Next Steps

To execute this test plan:

1. **Prepare Test Environment**
   ```bash
   # Create test directory
   mkdir -p /tmp/atomic-claude2-test
   cd /tmp/atomic-claude2-test

   # Copy atomic-claude2
   cp -r /path/to/atomic-claude2 .
   cd atomic-claude2

   # Setup environment
   cp .env.example .env
   # Edit .env with test API keys
   ```

2. **Run Unit Tests First**
   ```bash
   # Verify all unit tests pass
   python -m pytest tests/unit/ -v
   ```

3. **Execute Continuity Tests**
   ```bash
   # Run Scenario 1 (Happy Path)
   ./test-continuity-scenario1.sh
   ```

4. **Perform Functional Evaluation**
   ```bash
   # Run with sample data
   ./functional-test-taskflow-api.sh
   ```

5. **Conduct UX/UI Evaluation**
   ```bash
   # Interactive evaluation
   ./uxui-interactive-test.sh
   ```

6. **Collect and Analyze Results**
   ```bash
   # Generate reports
   ./generate-test-reports.sh
   ```

---

**Status**: Ready to execute
**Estimated Duration**: 3 weeks
**Prerequisites**: All unit tests passing, clean test environment
