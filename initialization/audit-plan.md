# Audit Plan
# ==========
# Configure which audits run at each auditable checkpoint.
#
# ============================================================================
# INITIALIZATION FILES
# ============================================================================
# The initialization/ folder contains three configuration files:
#
#   setup.md        PROJECT CONFIGURATION
#                   Project basics, sandbox, repository, pipeline, LLM
#
#   agent-plan.md   WHO DOES THE WORK
#                   Assign AI agents to each phase. Browse available agents
#                   at https://github.com/turbobeest/agents or define custom
#                   agents inline.
#
#   audit-plan.md   YOU ARE HERE
#                   Configure audit profiles (quick/standard/thorough) and
#                   per-phase overrides. Browse audit dimensions at
#                   https://github.com/turbobeest/audits
#
# ============================================================================
#
# FIELD OPTIONS:
#   - Use a profile name: quick | standard | thorough
#   - Use "default" to accept the recommended profile for that task
#   - Use "custom" and list specific audits below
#   - Use "skip" to skip audits for that task (not recommended)

# ============================================================================
# GLOBAL DEFAULTS
# ============================================================================
# These apply to all auditable tasks unless overridden below.

## Default Profile
# Which audit profile to use when not specified?
# Options: quick | standard | thorough | default [standard]

default

## Default Mode
# How should audit failures be handled?
#   loop-until-pass  - Automatically retry with fixes until all pass
#   gate-all         - Human must approve/reject ANY failure
#   gate-critical    - Human approval only for critical severity
#   gate-high        - Human approval for high+ severity
#   report-only      - Log failures but continue (use with caution)
# Options: [value] | default [gate-high]

default

## Default Severity Filter
# Which severities block progress?
#   all          - critical, high, medium, low - all block
#   critical     - Only critical issues block
#   high+        - Critical and high block
#   medium+      - Critical, high, and medium block
# Options: [value] | default [high+]

default

# ============================================================================
# PHASE 2: PRD VALIDATION
# ============================================================================
# Audits run after PRD is drafted.

## PRD Audit Profile
# Options: quick | standard | thorough | custom | skip | default [standard]

default

## PRD Audit Mode
# Options: loop-until-pass | gate-all | gate-critical | gate-high | report-only | default

default

## PRD Custom Audits (if profile = custom)
# List specific audit IDs from the audits repo.
# Examples:
#   - REQ-001  (Requirements completeness)
#   - REQ-003  (Acceptance criteria defined)
#   - REQ-005  (NFRs specified)


# ============================================================================
# PHASE 4: SPECIFICATION AUDIT
# ============================================================================
# Audits run after technical specifications are complete.

## Specification Audit Profile
# Options: quick | standard | thorough | custom | skip | default [standard]

default

## Specification Audit Mode
# Options: loop-until-pass | gate-all | gate-critical | gate-high | report-only | default

default

## Specification Custom Audits (if profile = custom)
# Examples:
#   - REQ-007  (API contracts defined)
#   - SEC-001  (Security requirements)
#   - PERF-001 (Performance targets)


# ============================================================================
# PHASE 6: CODE REVIEW AUDIT
# ============================================================================
# Audits run during code review phase.

## Code Review Audit Profile
# Options: quick | standard | thorough | custom | skip | default [standard]

default

## Code Review Audit Mode
# Options: loop-until-pass | gate-all | gate-critical | gate-high | report-only | default

default

## Code Review Custom Audits (if profile = custom)
# Examples:
#   - SEC-002  (Input validation)
#   - SEC-003  (Authentication)
#   - MAINT-001 (Code organization)
#   - MAINT-003 (Test coverage)


# ============================================================================
# PHASE 7: INTEGRATION AUDIT
# ============================================================================
# Audits run after integration testing.

## Integration Audit Profile
# Options: quick | standard | thorough | custom | skip | default [standard]

default

## Integration Audit Mode
# Options: loop-until-pass | gate-all | gate-critical | gate-high | report-only | default

default

## Integration Custom Audits (if profile = custom)
# Examples:
#   - INT-001  (E2E flow coverage)
#   - INT-002  (Acceptance criteria validated)
#   - INT-003  (API contracts validated)
#   - PERF-001 (Response time benchmarks)
#   - SEC-005  (OWASP top 10)


# ============================================================================
# AUDIT DIMENSION REFERENCE
# ============================================================================
# Quick reference of available audit categories. Full details in audits repo.
#
# REQ  - Requirements (15 audits)
#        Completeness, clarity, testability, traceability
#
# SEC  - Security (12 audits)
#        Authentication, authorization, encryption, OWASP
#
# PERF - Performance (10 audits)
#        Response time, throughput, scalability, resources
#
# REL  - Reliability (8 audits)
#        Fault tolerance, recovery, availability
#
# INT  - Integration (10 audits)
#        API contracts, data exchange, third-party, E2E
#
# COMP - Compliance (8 audits)
#        GDPR, regulatory, privacy, audit trails
#
# OBS  - Observability (8 audits)
#        Metrics, logging, tracing, alerting
#
# DEP  - Deployment (8 audits)
#        CI/CD, rollback, environments, releases
#
# DATA - Data Management (8 audits)
#        Models, validation, migration, archival
#
# UX   - User Experience (10 audits)
#        Accessibility, usability, responsiveness
#
# MAINT - Maintainability (8 audits)
#         Code organization, documentation, testability
#
# Browse full catalog: https://github.com/turbobeest/audits
# Or locally: cat ../audits/menu/index.json

# ============================================================================
# END OF AUDIT PLAN
# ============================================================================
