# Agent Plan
# ==========
# Assign specialized AI agents to each phase for optimal results.
#
# ============================================================================
# INITIALIZATION FILES
# ============================================================================
# The initialization/ folder contains three configuration files:
#
#   setup.md        PROJECT CONFIGURATION
#                   Project basics, sandbox, repository, pipeline, LLM
#
#   agent-plan.md   YOU ARE HERE
#                   Assign AI agents to each phase. Browse available agents
#                   at https://github.com/turbobeest/agents or define custom
#                   agents inline.
#
#   audit-plan.md   HOW QUALITY IS VERIFIED
#                   Configure audit profiles (quick/standard/thorough) and
#                   per-phase overrides. Browse audit dimensions at
#                   https://github.com/turbobeest/audits
#
# ============================================================================
#
# FIELD OPTIONS:
#   - Use an agent name (filename without .md)
#   - Use "infer" to let Claude recommend based on project context
#   - Use "default" to use the pipeline standard agent
#   - Use "custom" and provide details below

# ============================================================================
# GLOBAL DEFAULTS
# ============================================================================

## Default Model
# Which model tier for agents when not specified?
#   opus    - Most capable, highest cost
#   sonnet  - Balanced capability and cost (recommended)
#   haiku   - Fast and economical
# Options: opus | sonnet | haiku | default [sonnet]

default

## Agent Source
# Where to look for agent definitions?
#   local      - ./agents/ directory only
#   remote     - GitHub turbobeest/agents repo
#   both       - Check local first, fall back to remote
# Options: local | remote | both | default [both]

default

# ============================================================================
# PHASE 0: SETUP
# ============================================================================
# Collects project configuration and validates environment.

## Setup Agent
# Options: [agent-name] | default

default

# ============================================================================
# PHASE 1: IDEATION
# ============================================================================
# Captures idea, explores codebase, understands context.

## Ideation Agent
# Suggested: idea-synthesizer, codebase-mapper, context-analyst
# Options: [agent-name] | infer | default

infer

## Ideation Model Override
# Options: opus | sonnet | haiku | default

default

# ============================================================================
# PHASE 2: DISCOVERY
# ============================================================================
# Deep dive into requirements, constraints, and existing patterns.

## Discovery Agent
# Suggested: requirements-explorer, pattern-analyst, constraint-mapper
# Options: [agent-name] | infer | default

infer

## Discovery Model Override
# Options: opus | sonnet | haiku | default

default

# ============================================================================
# PHASE 3: PRD
# ============================================================================
# Drafts and validates Product Requirements Document.

## PRD Agent
# Suggested: requirements-architect, prd-writer, acceptance-definer
# Options: [agent-name] | infer | default

infer

## PRD Model Override
# Options: opus | sonnet | haiku | default

default

# ============================================================================
# PHASE 4: TASKING
# ============================================================================
# Breaks down PRD into implementable tasks.

## Tasking Agent
# Suggested: task-decomposer, dependency-analyst, complexity-scorer
# Options: [agent-name] | infer | default

infer

## Tasking Model Override
# Options: opus | sonnet | haiku | default

default

# ============================================================================
# PHASE 5: SPECIFICATION
# ============================================================================
# Detailed technical specs for each task.

## Specification Agent
# Suggested: api-designer, interface-specifier, edge-case-finder
# Options: [agent-name] | infer | default

infer

## Specification Model Override
# Options: opus | sonnet | haiku | default

default

# ============================================================================
# PHASE 6: IMPLEMENTATION
# ============================================================================
# TDD cycle - Red/Green/Refactor.

## Implementation Agent
# Suggested: test-driven-dev, code-craftsman, security-minded-dev
# Options: [agent-name] | infer | default

infer

## Implementation Model Override
# Options: opus | sonnet | haiku | default

default

# ============================================================================
# PHASE 7: INTEGRATION
# ============================================================================
# E2E testing, acceptance validation, performance benchmarks.

## Integration Agent
# Suggested: integration-lead, e2e-tester, acceptance-validator
# Options: [agent-name] | infer | default

infer

## Integration Model Override
# Options: opus | sonnet | haiku | default

default

# ============================================================================
# PHASE 8: DEPLOYMENT PREP
# ============================================================================
# Prepare release artifacts, documentation, changelog.

## Deployment Prep Agent
# Suggested: release-packager, documentation-generator, changelog-writer
# Options: [agent-name] | infer | default

infer

## Deployment Prep Model Override
# Options: opus | sonnet | haiku | default

default

# ============================================================================
# PHASE 9: RELEASE
# ============================================================================
# Execute release and confirm success.

## Release Agent
# Suggested: release-engineer, announcement-writer
# Options: [agent-name] | infer | default

infer

## Release Model Override
# Options: opus | sonnet | haiku | default

default

# ============================================================================
# CUSTOM AGENT DEFINITIONS
# ============================================================================
# Define project-specific agents inline. These override any agent with the
# same name from the agents repo.
#
# FORMAT:
# ### agent-name
# **Model:** opus | sonnet | haiku
# **System Prompt:**
# ```
# Your specialized instructions here...
# ```
# **Tools:** Read, Write, Edit, Bash, Glob, Grep, WebFetch
#
# EXAMPLE:
#
# ### my-domain-expert
# **Model:** sonnet
# **System Prompt:**
# ```
# You are an expert in payment processing systems with deep knowledge of
# PCI-DSS compliance requirements. You prioritize security in all decisions
# and always validate input data before processing.
# ```
# **Tools:** Read, Write, Edit, Bash, Glob, Grep


# ============================================================================
# AGENT LIBRARY REFERENCE
# ============================================================================
# Quick reference of agent categories. Full details in agents repo.
#
# IDEATION AGENTS:
#   idea-synthesizer     - Captures and refines project ideas
#   codebase-mapper      - Analyzes existing code structure
#   context-analyst      - Understands project context and constraints
#
# REQUIREMENTS AGENTS:
#   requirements-architect - Structures requirements systematically
#   prd-writer           - Drafts comprehensive PRDs
#   acceptance-definer   - Creates testable acceptance criteria
#
# IMPLEMENTATION AGENTS:
#   test-driven-dev      - Strict TDD methodology
#   code-craftsman       - Clean code principles
#   security-minded-dev  - Security-first implementation
#
# REVIEW AGENTS:
#   code-critic          - Thorough code review
#   security-reviewer    - Security-focused review
#   maintainability-judge - Long-term maintainability focus
#
# INTEGRATION AGENTS:
#   integration-lead     - Orchestrates integration testing
#   e2e-tester           - End-to-end test specialist
#   performance-analyst  - Performance testing and optimization
#
# DEPLOYMENT AGENTS:
#   release-engineer     - Release process management
#   deploy-guardian      - Safe deployment practices
#
# Browse full catalog: https://github.com/turbobeest/agents
# Or locally: ls ./agents/

# ============================================================================
# END OF AGENT PLAN
# ============================================================================
