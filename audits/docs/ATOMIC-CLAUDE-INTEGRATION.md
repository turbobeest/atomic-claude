# Audits Repo Integration with ATOMIC-CLAUDE

This document describes how the `turbobeest/audits` repository integrates with the ATOMIC-CLAUDE development pipeline.

## Overview

The audits repo serves as a **comprehensive audit library** (~2,200 audits across 43 categories) that ATOMIC-CLAUDE references during phase audit tasks. Rather than hardcoding which audits apply to which phase, an AI agent dynamically recommends relevant audits based on:

- Current SDLC phase context
- Project type and tech stack
- Compliance requirements
- Codebase analysis

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  github.com/turbobeest/audits                                       │
│  Complete Library: ~2,200 audits, 43 categories, 6 clusters         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ATOMIC-CLAUDE Phase Audit Task                                     │
│                                                                     │
│  1. Agent gathers context (codebase, phase, artifacts)              │
│  2. Agent fetches AUDIT-MENU.md (GitHub or local)                   │
│  3. Agent recommends 15-25 relevant audits                          │
│  4. User reviews and approves/modifies selection                    │
│  5. Agent downloads full audit files for selected audits            │
│  6. Agent executes audits and generates report                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Output: Audit Report + Pass/Fail Status                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Repository Setup (Phase 0, Task 007)

During ATOMIC-CLAUDE setup, both companion repositories are cloned:

```bash
# Agents repository
git clone https://github.com/turbobeest/agents /path/to/agents

# Audits repository
git clone https://github.com/turbobeest/audits /path/to/audits
```

For **air-gapped environments**, these repos are cloned once and used locally.

## Phase Audit Tasks

The following ATOMIC-CLAUDE tasks use this integration:

| Task | Phase | Purpose |
|------|-------|---------|
| 109 | 1 - Discovery | Audit discovery completeness |
| 207 | 2 - PRD | Audit PRD completeness |
| 305 | 3 - Task Decomposition | Audit task breakdown |
| 405 | 4 - Specification | Audit technical specs |
| 506 | 5 - Implementation | Audit TDD/code quality |
| 605 | 6 - Code Review | Audit code review findings |
| 705 | 7 - Integration | Audit integration testing |

## Agent Recommendation Flow

### Step 1: Context Gathering

The agent analyzes:
- Project configuration from `project-config.json`
- Phase artifacts (PRD, specs, code, test results)
- Detected tech stack
- Compliance requirements from `audit-plan.md`

### Step 2: Menu Fetch

```
Primary:   https://raw.githubusercontent.com/turbobeest/audits/main/AUDIT-MENU.md
Fallback:  /local/path/to/audits/AUDIT-MENU.md
```

### Step 3: AI-Driven Selection

The agent prompt structure:

```
You are conducting a Phase {N} audit for {phase_name}.

CONTEXT:
- Project: {project_description}
- Tech Stack: {detected_stack}
- Compliance: {compliance_requirements}
- Phase Artifacts: {list_of_artifacts}

AUDIT MENU:
{contents_of_AUDIT-MENU.md}

TASK:
1. Analyze the codebase and phase artifacts
2. Select 15-25 most relevant audits from the menu
3. Classify each by dependency status (ready/needs-deps)
4. Explain WHY each audit is relevant
5. Present recommendations to user for approval
```

### Step 4: User Review

```
Phase Audit

Recommended Audits (18 of 2,200):

┌────────────────────────────────────────────────────┐
│ ✓ READY TO RUN (12 audits)                         │
│ ☑ SEC-1.1.01  Session Management Audit             │
│ ☑ SEC-1.1.03  MFA Configuration Audit              │
│ ☑ PERF-2.1.02 Database Query Latency Audit         │
│ ...                                                │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│ ⚠ DEPENDENCIES REQUIRED (6 audits)                 │
│ ☐ SEC-1.1.05  NIST 800-63 Compliance               │
│   └─ Needs: NIST SP 800-63B (2.1 MB)               │
│ ...                                                │
└────────────────────────────────────────────────────┘

1. Accept recommendations
2. Browse full audit menu
3. Add specific audit by ID
4. Remove audit from selection
5. Generate dependency fetch list

Select [1-5]:
```

## Air-Gap Support

### Dependency Classification

Each audit is classified by offline capability:

| Status | Meaning |
|--------|---------|
| `full` | Completely self-contained, runs offline |
| `partial` | Core audit works, some checks need references |
| `none` | Requires online resources (APIs, databases) |

### Dependency Types

| Type | Description | Example |
|------|-------------|---------|
| `reference` | Documentation/standards | NIST SP 800-63B |
| `tool` | External scanning tool | OWASP ZAP |
| `api` | Online API call | NVD CVE database |
| `database` | Vulnerability database | CVE/CWE lists |

### Dependency Fetch Manifest

For air-gapped environments, the agent generates a manifest:

```markdown
# Audit Dependency Manifest
Generated: 2026-01-18
Project: my-project

## Required Dependencies (6 files, ~15 MB)

| File | Source URL | Size | For Audit |
|------|------------|------|-----------|
| sp800-63b.pdf | https://pages.nist.gov/... | 2.1 MB | SEC-1.1.05 |
| ASVS-5.0.pdf | https://github.com/OWASP/... | 1.8 MB | COMP-24.2.01 |

## Transfer Instructions
1. Download on connected system
2. Transfer via approved media
3. Place in: audits/dependencies/
4. Re-run audit task
```

### Local Cache Structure

```
audits/
├── AUDIT-MENU.md
├── categories/
├── dependencies/           # Local cache (gitignored)
│   ├── nist/
│   │   └── sp800-63b.pdf
│   ├── owasp/
│   │   └── asvs-5.0.pdf
│   └── manifest.json       # Tracks cached deps
└── .gitignore
```

## Audit File Schema

Each audit `.md` file includes dependency metadata in frontmatter:

```yaml
---
id: SEC-1.1.05
name: "NIST 800-63 Digital Identity Compliance"
category: Security > Authentication
severity: high
scope: [prd, code, integration]

offline_capable: partial
dependencies:
  - id: nist-800-63b
    name: "NIST SP 800-63B"
    type: reference
    required: true
    cacheable: true
    url: "https://pages.nist.gov/800-63-3/sp800-63b.html"
    local_path: "dependencies/nist/sp800-63b.pdf"
    size_mb: 2.1
    update_frequency: yearly
---

# NIST 800-63 Digital Identity Compliance Audit

## Purpose
...

## Checklist
...
```

## Configuration via audit-plan.md

Users configure audit behavior in `initialization/audit-plan.md`:

```markdown
## Default Profile
# Starting point for AI recommendations
# Options: quick | standard | thorough
standard

## Default Mode
# How to handle failures
# Options: loop-until-pass | gate-all | gate-high | report-only
gate-high

## Severity Filter
# Which severities block progress
# Options: all | critical | high+ | medium+
high+

## Air-Gap Mode
# Options: auto | online | offline
auto
```

## Integration Points

### ATOMIC-CLAUDE Files Modified

| File | Change |
|------|--------|
| `phases/0-setup/tasks/007-repository-setup.sh` | Clone audits repo |
| `phases/*/tasks/*-phase-audit.sh` | New AI-driven audit flow |
| `initialization/audit-plan.md` | User configuration |
| `lib/audit.sh` | Shared audit functions |

### Data Flow

```
audit-plan.md (user config)
        │
        ▼
Phase Audit Task
        │
        ├──► AUDIT-MENU.md (fetch)
        │
        ├──► Agent Recommendation
        │
        ├──► User Approval
        │
        ├──► Download Selected Audits
        │
        ├──► Execute Audits
        │
        └──► Generate Report
                │
                ▼
        .claude/audits/phase-{N}-report.json
```

## Related Documentation

- [AUDIT-MENU.md](../AUDIT-MENU.md) - Master audit index
- [README.md](../README.md) - Audits repo overview
- [ATOMIC-CLAUDE docs](https://github.com/turbobeest/ATOMIC-CLAUDE) - Pipeline documentation
