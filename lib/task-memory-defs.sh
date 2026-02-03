#!/usr/bin/env bash
#
# ATOMIC-CLAUDE Task Memory Definitions
# Defines what context each task should RECALL at start and SAVE at end
#
# Architecture:
#   - TASK_MEMORY_RECALL: Query strings for recalling relevant context at task start
#   - TASK_MEMORY_SAVE: Content type identifier for extracting meaningful output at task end
#   - Empty string = no recall/save needed for that task
#
# Usage:
#   source lib/task-memory-defs.sh
#   local recall_query="${TASK_MEMORY_RECALL["${phase}-${task_id}"]:-}"
#   local save_type="${TASK_MEMORY_SAVE["${phase}-${task_id}"]:-}"
#

# =============================================================================
# TASK RECALL DEFINITIONS - What context each task needs at START
# =============================================================================
# Key format: "PHASE-TASKID" (e.g., "0-001", "1-102")
# Value: Query string to search for relevant context

declare -gA TASK_MEMORY_RECALL

# ─────────────────────────────────────────────────────────────────────────────
# Phase 0: Setup
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_RECALL["0-001"]=""                                    # First task - no prior context
TASK_MEMORY_RECALL["0-002"]="mode selection setup"               # Needs: mode from 001
TASK_MEMORY_RECALL["0-003"]="extracted config project"           # Needs: config from 002
TASK_MEMORY_RECALL["0-004"]="approved config providers"          # Needs: approval from 003
TASK_MEMORY_RECALL["0-005"]="project config constraints"         # Needs: project context
TASK_MEMORY_RECALL["0-006"]="material manifest files"            # Needs: manifest from 005
TASK_MEMORY_RECALL["0-007"]="project constraints environment"    # Needs: project context
TASK_MEMORY_RECALL["0-008"]="environment tools setup"            # Needs: env from 007
TASK_MEMORY_RECALL["0-009"]="Phase 0 setup config environment"   # Needs: all Phase 0

# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: Discovery
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_RECALL["1-101"]="Phase 0 closeout config"            # Needs: Phase 0 summary
TASK_MEMORY_RECALL["1-102"]="project config goal constraints"    # Needs: project context
TASK_MEMORY_RECALL["1-103"]="corpus materials analysis"          # Needs: corpus from 102
TASK_MEMORY_RECALL["1-104"]="corpus analysis materials"          # Needs: corpus from 102
TASK_MEMORY_RECALL["1-105"]="selected agents corpus project"     # Needs: agents from 104, corpus from 102
TASK_MEMORY_RECALL["1-106"]="dialogue synthesis selected agents" # Needs: dialogue from 105, agents from 104
TASK_MEMORY_RECALL["1-107"]="discovery corpus dialogue"          # Needs: all discovery context
TASK_MEMORY_RECALL["1-108"]="selected approach architecture"     # Needs: approach from 107
TASK_MEMORY_RECALL["1-109"]="Phase 1 discovery outputs"          # Needs: all Phase 1
TASK_MEMORY_RECALL["1-110"]="Phase 1 discovery corpus dialogue approach" # Needs: all Phase 1

# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: PRD
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_RECALL["2-201"]="Phase 1 closeout approach vision"   # Needs: Phase 1 summary
TASK_MEMORY_RECALL["2-202"]="selected approach vision audience"  # Needs: approach
TASK_MEMORY_RECALL["2-203"]="approach vision constraints"        # Needs: context
TASK_MEMORY_RECALL["2-204"]="PRD setup project"                  # Needs: setup
TASK_MEMORY_RECALL["2-205"]="interview approach Phase 1"         # Needs: all prior
TASK_MEMORY_RECALL["2-206"]="PRD requirements"                   # Needs: PRD from 205
TASK_MEMORY_RECALL["2-206b"]="PRD validation findings"           # Needs: validation from 206
TASK_MEMORY_RECALL["2-207"]="PRD final"                          # Needs: final PRD
TASK_MEMORY_RECALL["2-208"]="Phase 2 PRD outputs"                # Needs: all Phase 2
TASK_MEMORY_RECALL["2-209"]="Phase 2 PRD stakeholders scope"     # Needs: all Phase 2

# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Tasking
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_RECALL["3-301"]="Phase 2 closeout PRD requirements"  # Needs: Phase 2 summary
TASK_MEMORY_RECALL["3-302"]="PRD requirements decomposition"     # Needs: PRD context
TASK_MEMORY_RECALL["3-303"]="PRD requirements features"          # Needs: PRD
TASK_MEMORY_RECALL["3-304"]="tasks decomposition"                # Needs: tasks from 303
TASK_MEMORY_RECALL["3-305"]="Phase 3 tasking outputs"            # Needs: all Phase 3
TASK_MEMORY_RECALL["3-306"]="Phase 3 tasks priorities"           # Needs: all Phase 3

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Specification
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_RECALL["4-401"]="Phase 3 closeout tasks"             # Needs: Phase 3 summary
TASK_MEMORY_RECALL["4-402"]="tasks project constraints"          # Needs: tasks
TASK_MEMORY_RECALL["4-403"]="tasks PRD requirements"             # Needs: tasks + PRD
TASK_MEMORY_RECALL["4-404"]="specs test strategies"              # Needs: specs from 403
TASK_MEMORY_RECALL["4-405"]="Phase 4 specification outputs"      # Needs: all Phase 4
TASK_MEMORY_RECALL["4-406"]="Phase 4 specs test strategies"      # Needs: all Phase 4

# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: Implementation
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_RECALL["5-501"]="Phase 4 closeout specs"             # Needs: Phase 4 summary
TASK_MEMORY_RECALL["5-502"]="specs project constraints"          # Needs: specs
TASK_MEMORY_RECALL["5-503"]="TDD setup project"                  # Needs: TDD setup
TASK_MEMORY_RECALL["5-504"]="specs TDD setup agents"             # Needs: all context
TASK_MEMORY_RECALL["5-505"]="TDD progress results"               # Needs: TDD from 504
TASK_MEMORY_RECALL["5-506"]="Phase 5 implementation outputs"     # Needs: all Phase 5
TASK_MEMORY_RECALL["5-507"]="Phase 5 TDD coverage results"       # Needs: all Phase 5

# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: Code Review
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_RECALL["6-601"]="Phase 5 closeout TDD coverage"      # Needs: Phase 5 summary
TASK_MEMORY_RECALL["6-602"]="code TDD results"                   # Needs: code context
TASK_MEMORY_RECALL["6-603"]="code specs TDD"                     # Needs: all context
TASK_MEMORY_RECALL["6-604"]="review findings"                    # Needs: findings from 603
TASK_MEMORY_RECALL["6-605"]="Phase 6 review outputs"             # Needs: all Phase 6
TASK_MEMORY_RECALL["6-606"]="Phase 6 review findings fixes"      # Needs: all Phase 6

# ─────────────────────────────────────────────────────────────────────────────
# Phase 7: Integration
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_RECALL["7-701"]="Phase 6 closeout review"            # Needs: Phase 6 summary
TASK_MEMORY_RECALL["7-702"]="project constraints architecture"   # Needs: project context
TASK_MEMORY_RECALL["7-703"]="integration setup project"          # Needs: setup
TASK_MEMORY_RECALL["7-704"]="specs integration setup"            # Needs: all context
TASK_MEMORY_RECALL["7-705"]="integration results"                # Needs: results from 704
TASK_MEMORY_RECALL["7-706"]="Phase 7 integration outputs"        # Needs: all Phase 7
TASK_MEMORY_RECALL["7-707"]="Phase 7 integration results"        # Needs: all Phase 7

# ─────────────────────────────────────────────────────────────────────────────
# Phase 8: Deployment Prep
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_RECALL["8-801"]="Phase 7 closeout integration"       # Needs: Phase 7 summary
TASK_MEMORY_RECALL["8-802"]="project config infrastructure"      # Needs: config
TASK_MEMORY_RECALL["8-803"]="deployment setup"                   # Needs: setup
TASK_MEMORY_RECALL["8-804"]="project context version"            # Needs: all context
TASK_MEMORY_RECALL["8-805"]="Phase 8 deployment outputs"         # Needs: all Phase 8
TASK_MEMORY_RECALL["8-806"]="deployment artifacts"               # Needs: artifacts from 804
TASK_MEMORY_RECALL["8-807"]="Phase 8 deployment artifacts"       # Needs: all Phase 8

# ─────────────────────────────────────────────────────────────────────────────
# Phase 9: Release
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_RECALL["9-901"]="Phase 8 closeout deployment"        # Needs: Phase 8 summary
TASK_MEMORY_RECALL["9-902"]="project version changelog"          # Needs: version info
TASK_MEMORY_RECALL["9-903"]="release setup"                      # Needs: setup
TASK_MEMORY_RECALL["9-904"]="release context all"                # Needs: all context
TASK_MEMORY_RECALL["9-905"]="release execution"                  # Needs: execution from 904
TASK_MEMORY_RECALL["9-906"]="ALL phases complete project"        # Needs: EVERYTHING


# =============================================================================
# TASK SAVE DEFINITIONS - What content each task should SAVE at END
# =============================================================================
# Key format: "PHASE-TASKID" (e.g., "0-001", "1-102")
# Value: Content type identifier used by _memory_extract_content()
# Empty string = no save needed for that task

declare -gA TASK_MEMORY_SAVE

# ─────────────────────────────────────────────────────────────────────────────
# Phase 0: Setup
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_SAVE["0-001"]="mode_selection"      # Save: SETUP_MODE value
TASK_MEMORY_SAVE["0-002"]="extracted_config"    # Save: Full extracted-config.json summary
TASK_MEMORY_SAVE["0-003"]="config_approval"     # Save: Approved config fields
TASK_MEMORY_SAVE["0-004"]="api_providers"       # Save: Which providers configured
TASK_MEMORY_SAVE["0-005"]="material_manifest"   # Save: File counts, languages
TASK_MEMORY_SAVE["0-006"]="reference_materials" # Save: Reference paths
TASK_MEMORY_SAVE["0-007"]="environment_tools"   # Save: Tools installed
TASK_MEMORY_SAVE["0-008"]="repository_config"   # Save: Agents/audits paths
TASK_MEMORY_SAVE["0-009"]=""                    # Save handled by closeout code

# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: Discovery
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_SAVE["1-101"]=""                    # Entry validation - nothing meaningful to save
TASK_MEMORY_SAVE["1-102"]="corpus_analysis"     # Save: Corpus summary
TASK_MEMORY_SAVE["1-103"]=""                    # Corpus index - part of 102
TASK_MEMORY_SAVE["1-104"]="selected_agents"     # Save: Agent selections
TASK_MEMORY_SAVE["1-105"]="dialogue_synthesis"  # Save: Vision, impact, constraints
TASK_MEMORY_SAVE["1-106"]="discovery_findings"  # Save: Findings, recommendations
TASK_MEMORY_SAVE["1-107"]="selected_approach"   # Save: Approach and rationale
TASK_MEMORY_SAVE["1-108"]="architecture_diagrams" # Save: Diagram descriptions
TASK_MEMORY_SAVE["1-109"]="phase_audit"         # Save: Audit findings
TASK_MEMORY_SAVE["1-110"]=""                    # Save handled by closeout code

# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: PRD
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_SAVE["2-201"]=""                    # Entry validation
TASK_MEMORY_SAVE["2-202"]="prd_setup"           # Save: PRD structure
TASK_MEMORY_SAVE["2-203"]="prd_interview"       # Save: Stakeholders, criteria, scope
TASK_MEMORY_SAVE["2-204"]="selected_agents"     # Save: Agent selections
TASK_MEMORY_SAVE["2-205"]="prd_content"         # Save: PRD summary
TASK_MEMORY_SAVE["2-206"]="prd_validation"      # Save: Validation findings
TASK_MEMORY_SAVE["2-206b"]="prd_revisions"      # Save: What was revised
TASK_MEMORY_SAVE["2-207"]="prd_approval"        # Save: Approval status
TASK_MEMORY_SAVE["2-208"]="phase_audit"         # Save: Audit findings
TASK_MEMORY_SAVE["2-209"]=""                    # Save handled by closeout code

# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Tasking
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_SAVE["3-301"]=""                    # Entry validation
TASK_MEMORY_SAVE["3-302"]=""                    # Part of 303
TASK_MEMORY_SAVE["3-303"]="tasks_decomposition" # Save: Task list summary
TASK_MEMORY_SAVE["3-304"]="dependency_analysis" # Save: Dependencies, critical path
TASK_MEMORY_SAVE["3-305"]="phase_audit"         # Save: Audit findings
TASK_MEMORY_SAVE["3-306"]=""                    # Save handled by closeout code

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Specification
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_SAVE["4-401"]=""                    # Entry validation
TASK_MEMORY_SAVE["4-402"]="selected_agents"     # Save: Agent selections
TASK_MEMORY_SAVE["4-403"]="specs_generated"     # Save: Spec summaries
TASK_MEMORY_SAVE["4-404"]="tdd_subtasks"        # Save: Subtask injection
TASK_MEMORY_SAVE["4-405"]="phase_audit"         # Save: Audit findings
TASK_MEMORY_SAVE["4-406"]=""                    # Save handled by closeout code

# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: Implementation
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_SAVE["5-501"]=""                    # Entry validation
TASK_MEMORY_SAVE["5-502"]="tdd_setup"           # Save: Coverage targets, pyramid
TASK_MEMORY_SAVE["5-503"]="selected_agents"     # Save: Agent selections
TASK_MEMORY_SAVE["5-504"]="tdd_results"         # Save: TDD results, coverage
TASK_MEMORY_SAVE["5-505"]="validation_report"   # Save: Quality metrics
TASK_MEMORY_SAVE["5-506"]="phase_audit"         # Save: Audit findings
TASK_MEMORY_SAVE["5-507"]=""                    # Save handled by closeout code

# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: Code Review
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_SAVE["6-601"]=""                    # Entry validation
TASK_MEMORY_SAVE["6-602"]="selected_agents"     # Save: Agent selections
TASK_MEMORY_SAVE["6-603"]="review_findings"     # Save: Findings summary
TASK_MEMORY_SAVE["6-604"]="refinement_report"   # Save: What was fixed
TASK_MEMORY_SAVE["6-605"]="phase_audit"         # Save: Audit findings
TASK_MEMORY_SAVE["6-606"]=""                    # Save handled by closeout code

# ─────────────────────────────────────────────────────────────────────────────
# Phase 7: Integration
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_SAVE["7-701"]=""                    # Entry validation
TASK_MEMORY_SAVE["7-702"]="integration_setup"   # Save: Scope, targets
TASK_MEMORY_SAVE["7-703"]="selected_agents"     # Save: Agent selections
TASK_MEMORY_SAVE["7-704"]="integration_results" # Save: Test results
TASK_MEMORY_SAVE["7-705"]="integration_approval" # Save: Approval status
TASK_MEMORY_SAVE["7-706"]="phase_audit"         # Save: Audit findings
TASK_MEMORY_SAVE["7-707"]=""                    # Save handled by closeout code

# ─────────────────────────────────────────────────────────────────────────────
# Phase 8: Deployment Prep
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_SAVE["8-801"]=""                    # Entry validation
TASK_MEMORY_SAVE["8-802"]="deployment_setup"    # Save: Targets, CI/CD
TASK_MEMORY_SAVE["8-803"]="selected_agents"     # Save: Agent selections
TASK_MEMORY_SAVE["8-804"]="deployment_artifacts" # Save: Package, changelog
TASK_MEMORY_SAVE["8-805"]="phase_audit"         # Save: Audit findings
TASK_MEMORY_SAVE["8-806"]="deployment_approval" # Save: Approval status
TASK_MEMORY_SAVE["8-807"]=""                    # Save handled by closeout code

# ─────────────────────────────────────────────────────────────────────────────
# Phase 9: Release
# ─────────────────────────────────────────────────────────────────────────────
TASK_MEMORY_SAVE["9-901"]=""                    # Entry validation
TASK_MEMORY_SAVE["9-902"]="release_setup"       # Save: Version, channels
TASK_MEMORY_SAVE["9-903"]="selected_agents"     # Save: Agent selections
TASK_MEMORY_SAVE["9-904"]="release_execution"   # Save: Release URL, packages
TASK_MEMORY_SAVE["9-905"]="release_confirmation" # Save: Confirmed status
TASK_MEMORY_SAVE["9-906"]=""                    # Final closeout - handled separately


# =============================================================================
# EXPORTS
# =============================================================================

export TASK_MEMORY_RECALL
export TASK_MEMORY_SAVE
