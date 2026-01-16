# ATOMIC CLAUDE - Phase Structure

## Overview

10 phases (0-9), each with task range X01-X99.

```
0-Setup → 1-Discovery → 2-PRD → 3-Tasking → 4-Spec → 5-Impl → 6-Review → 7-Integration → 8-Validation → 9-Deploy
```

## Phase Definitions

### Phase 0: Setup (001-099)
**Purpose:** Project configuration, API keys, environment validation

| Task | Name | Type |
|------|------|------|
| 001 | Project Name | Input |
| 002 | Description | Input |
| 003 | Project Type | Menu |
| 004 | GitHub URL | Input + Detection |
| 005 | Summarize Docs | LLM |
| 006 | API Keys | Secure Input |
| 007 | Material Manifest | Deterministic |
| 008 | Validate Environment | Deterministic |

---

### Phase 1: Discovery (101-199)
**Purpose:** Capture idea, explore codebase, understand context

Combines: Ideation + Discovery

| Task | Name | Type |
|------|------|------|
| 101 | Capture Idea | Input |
| 102 | Scan Codebase | Deterministic |
| 103 | Analyze Architecture | LLM |
| 104 | Identify Patterns | LLM |
| 105 | Technical Summary | LLM |
| 106 | Risk Assessment | LLM |

---

### Phase 2: PRD (201-299)
**Purpose:** Draft, validate, and audit Product Requirements Document

Combines: PRD Draft + Validation + Audit

| Task | Name | Type |
|------|------|------|
| 201 | Draft PRD Structure | LLM |
| 202 | Define Requirements | LLM + Input |
| 203 | Acceptance Criteria | LLM |
| 204 | Validate Completeness | LLM |
| 205 | Cross-Reference Check | LLM |
| 206 | Human Review Gate | Gate |
| 207 | Final PRD Audit | LLM |

---

### Phase 3: Tasking (301-399)
**Purpose:** Break down PRD into implementable tasks

| Task | Name | Type |
|------|------|------|
| 301 | Extract Features | LLM |
| 302 | Decompose to Tasks | LLM |
| 303 | Identify Dependencies | LLM |
| 304 | Estimate Complexity | LLM |
| 305 | Prioritize Tasks | LLM + Input |
| 306 | Generate Task Graph | Deterministic |

---

### Phase 4: Specification (401-499)
**Purpose:** Detailed technical specifications for each task

| Task | Name | Type |
|------|------|------|
| 401 | Select Task | Menu |
| 402 | Define Interface | LLM |
| 403 | Specify Behavior | LLM |
| 404 | Edge Cases | LLM |
| 405 | Write Test Spec | LLM |
| 406 | Review Spec | Gate |

---

### Phase 5: Implementation (501-599)
**Purpose:** TDD cycle - Red/Green/Refactor/Verify

| Task | Name | Type |
|------|------|------|
| 501 | Setup Test Environment | Deterministic |
| 510 | RED: Write Failing Test | LLM |
| 520 | GREEN: Implement Code | LLM |
| 530 | REFACTOR: Improve Quality | LLM |
| 540 | VERIFY: Security Scan | LLM |
| 550 | Coverage Check | Deterministic |
| 590 | Next Task or Complete | Control |

---

### Phase 6: Review (601-699)
**Purpose:** Code review and quality assurance

| Task | Name | Type |
|------|------|------|
| 601 | Collect Changes | Deterministic |
| 602 | Static Analysis | Deterministic |
| 603 | Code Review | LLM |
| 604 | Security Review | LLM |
| 605 | Review Findings | Gate |
| 606 | Address Issues | LLM |

---

### Phase 7: Integration (701-799)
**Purpose:** Integrate components, resolve conflicts

| Task | Name | Type |
|------|------|------|
| 701 | Merge Branches | Deterministic |
| 702 | Resolve Conflicts | LLM + Manual |
| 703 | Integration Tests | Deterministic |
| 704 | Verify Integration | LLM |

---

### Phase 8: Validation (801-899)
**Purpose:** End-to-end validation, acceptance testing

| Task | Name | Type |
|------|------|------|
| 801 | E2E Test Suite | Deterministic |
| 802 | Acceptance Tests | Deterministic |
| 803 | Performance Tests | Deterministic |
| 804 | Validate Against PRD | LLM |
| 805 | Final Sign-off | Gate |

---

### Phase 9: Deployment (901-999)
**Purpose:** Deploy to production, rollback readiness

Combines: Deployment + Rollback Readiness

| Task | Name | Type |
|------|------|------|
| 901 | Pre-deploy Checklist | Deterministic |
| 902 | Create Rollback Point | Deterministic |
| 903 | Deploy to Staging | Deterministic |
| 904 | Smoke Tests | Deterministic |
| 905 | Deploy to Production | Deterministic + Gate |
| 906 | Verify Deployment | Deterministic |
| 910 | Rollback Procedure | Documentation |
| 911 | Rollback Test | Deterministic |

---

## Task Numbering Convention

```
XYY
│││
│└┴─ Task number within phase (01-99)
└─── Phase number (0-9)
```

**Examples:**
- `001` → Phase 0 (Setup), Task 1
- `105` → Phase 1 (Discovery), Task 5
- `520` → Phase 5 (Implementation), Task 20 (GREEN step)
- `901` → Phase 9 (Deployment), Task 1

**Gaps are intentional** - allows inserting tasks without renumbering:
- Phase 5 uses 510, 520, 530... for TDD steps
- Can insert 515 between RED and GREEN if needed
