# Corpus Index

Generated: 2026-02-07T10:59:37-05:00

## Materials

- **PHASE-1-AGENT-4-COMPLETE.md** (file) [auto-discovered]
- **STEP-3-COMPLETE.md** (file) [auto-discovered]
- **continuity-runner.md** (file) [auto-discovered]
- **manifest.json** (file) [auto-discovered]
- **anthropic-provider.md** (file) [auto-discovered]
- **OLLAMA-TEST-REPORT.md** (file) [auto-discovered]
- **UAT-TEST-RESULTS.md** (file) [auto-discovered]
- **PHASE-6-7-MIGRATION.md** (file) [auto-discovered]
- **task-examples.md** (file) [auto-discovered]
- **PHASE-1-FOUNDATION-COMPLETE.md** (file) [auto-discovered]
- **REFACTORING-PLAN.md** (file) [auto-discovered]
- **PHASE-00-01-EXTRACTION.md** (file) [auto-discovered]
- **PHASE-2-3-MIGRATION-COMPLETE.md** (file) [auto-discovered]
- **functional-runner.md** (file) [auto-discovered]
- **BUG-PATTERNS.md** (file) [auto-discovered]
- **PRD.md** (file) [auto-discovered]
- **setup.md** (file) [auto-discovered]
- **PHASE-4-5-MIGRATION.md** (file) [auto-discovered]
- **uat-runner.md** (file) [auto-discovered]
- **PHASE-1-DELIVERABLES.md** (file) [auto-discovered]
- **PHASE-2-CORE-SYSTEMS-COMPLETE.md** (file) [auto-discovered]
- **PROVIDER-IMPLEMENTATION-REPORT.md** (file) [auto-discovered]
- **PROJECT-STRUCTURE.md** (file) [auto-discovered]
- **EXTRACTION-PROGRESS.md** (file) [auto-discovered]
- **PHASE-2-3-UAT-COMPLETE.md** (file) [auto-discovered]
- **TASK-ENGINE-DELIVERABLES.md** (file) [auto-discovered]
- **PHASE-3-ORCHESTRATION-COMPLETE.md** (file) [auto-discovered]
- **PHASE-2-3-MIGRATION.md** (file) [auto-discovered]
- **task-engine.md** (file) [auto-discovered]
- **PHASE-4-IMPLEMENTATIONS-COMPLETE.md** (file) [auto-discovered]
- **QUICK-START.md** (file) [auto-discovered]
- **memory-examples.md** (file) [auto-discovered]
- **adding-providers.md** (file) [auto-discovered]
- **SUMMARY.md** (file) [auto-discovered]
- **REFACTORING-PLAN-V2.md** (file) [auto-discovered]
- **FORCING-FUNCTION.md** (file) [auto-discovered]
- **MEMORY-SYSTEM-REPORT.md** (file) [auto-discovered]
- **memory-architecture.md** (file) [auto-discovered]
- **memory-system.md** (file) [auto-discovered]
- **UAT-RUNNER-COMPLETE.md** (file) [auto-discovered]
- **MEMORY-AUDIT-TESTING.md** (file) [auto-discovered]
- **UAT-PHASES-0-3-RESULTS.md** (file) [auto-discovered]
- **DAY-1-PROGRESS-SUMMARY.md** (file) [auto-discovered]
- **PACKAGING-COMPLETE.md** (file) [auto-discovered]
- **DASHBOARD-UAT-GUIDE.md** (file) [auto-discovered]
- **ollama-provider.md** (file) [auto-discovered]
- **testing-providers.md** (file) [auto-discovered]
- **PHASE-8-9-MIGRATION.md** (file) [auto-discovered]
- **functional-quickstart.md** (file) [auto-discovered]
- **bedrock-provider.md** (file) [auto-discovered]
- **EXTRACTION-STRATEGY.md** (file) [auto-discovered]

## Analysis Summary

# Corpus Analysis

## 1. Project Understanding

This project is **atomic-claude2**, a complete Python refactoring of the original bash-based "Atomic Claude" system. It's an LLM-orchestrated software development pipeline that guides projects through 10 structured phases (Setup → Discovery → PRD → Tasking → Specification → Implementation → Code Review → Integration → Deployment → Release), maintaining a hybrid Python-Bash architecture where Python handles orchestration/state and Bash executes LLM-invoked tasks.

## 2. Key Themes

- **Hybrid Python-Bash architecture**: Python orchestrators (orchestratorNN.py) call Bash task scripts (taskNNN.sh) via subprocess_runner.py bridge
- **Phase-based workflow with state persistence**: 10 discrete phases, task completion tracked in `.state/task-state.json`, prerequisite validation enforces phase ordering
- **Multi-provider LLM integration**: Supports Anthropic (Claude), AWS Bedrock, Ollama local models with automatic routing and fallback
- **Test-driven migration strategy**: Three test runners (Continuity, UAT, Functional) validate each phase before progression, targeting 90%+ coverage
- **Agent-based task delegation**: 221 specialized agents (186 domain experts + 35 pipeline agents) selected dynamically per phase/task
- **UAT mode for rapid validation**: Prescribed inputs and bypasses enable full pipeline testing without human interaction

## 3. Technical Indicators

- **Technologies**: Python 3.9+ (orchestration), Bash 4.0+ (task execution), pytest/pytest-cov (testing), jq (JSON processing), Claude API/AWS Bedrock/Ollama (LLM providers)
- **Architecture**: Pipeline pattern with numbered phases (phase00-phase09), StateManager for persistence, subprocess bridge for Python↔Bash communication, closeout.json files chain phases
- **Constraints**: 
  - macOS compatibility required (arithmetic with `set -e` requires `|| true` workaround)
  - Directory purity enforced (no project artifacts in atomic-claude2 root)
  - 90%+ code coverage requirement for functional tests
  - UAT mode must complete Phases 0-7 chain without interaction

## 4. Gaps & Questions

- **Phase 8-9 UAT failures**: What mock output files do Phases 8-9 expect that aren't created in UAT mode? (integration-agents.json, integration-report.json mentioned)
- **Real LLM testing coverage**: Only mock-based tests passing; what's the strategy for validating real Anthropic/Bedrock/Ollama integration end-to-end?
- **Error recovery strategy**: If a mid-phase task fails in production (not UAT), what's the backtracking/resume UX for users?
