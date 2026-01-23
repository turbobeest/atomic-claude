# Project Setup
# =============
# Core project configuration for the ATOMIC CLAUDE pipeline.
#
# ============================================================================
# INITIALIZATION FILES
# ============================================================================
# The initialization/ folder contains three configuration files:
#
#   setup.md        YOU ARE HERE
#                   Project basics, sandbox, repository, pipeline, LLM
#
#   agent-plan.md   WHO DOES THE WORK
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
#   - Fill in a value directly
#   - Use "infer" to let Claude extract from your reference materials
#   - Use "default" to accept the recommended value (shown in brackets)
#   - Leave blank to be prompted during setup

# ============================================================================
# BASIC INFO
# ============================================================================

## Project Name
# Max 24 characters. Letters, numbers, hyphens, underscores only.
# Used for: output directories, log files, git tags, report headers.
# Examples: auth-service, payment-module, api-gateway
# Options: [value] | infer | default [dirname]

infer

## Description
# Single line describing what this project accomplishes.
# Used for: headers, documentation, commit messages.
# Example: "OAuth2 authentication microservice for user identity management"
# Options: [value] | infer | default ["A new software component"]

infer

## Project Type
# What kind of project is this?
#
#   new-monorepo   - New multi-package repository structure
#   new-component  - New standalone service/module/container
#   new-library    - New shared library/package
#   new-api        - New API service
#   new-cli        - New command-line tool
#   existing       - Adding features to existing codebase
#   migration      - Moving between technologies/platforms
#
# Options: [value] | infer | default [new-component]

default

## Primary Goal
# What is the main objective? Be specific about the outcome.
# Example: "Provide JWT-based authentication with refresh token rotation"
# Options: [value] | infer | default ["Build a production-ready component"]

infer

# ============================================================================
# SANDBOX & SAFETY
# ============================================================================
# Define boundaries for Claude's file system access and command execution.

## Allowed Paths (Whitelist)
# Directories Claude CAN access. If specified, Claude ONLY accesses these.
# Leave blank to allow project root and subdirectories (default behavior).
# Examples:
#   - ./src/
#   - ./tests/
#   - ./docs/


## Forbidden Paths (Blacklist)
# Directories Claude must NEVER access, read, or modify.
# Examples:
#   - ./secrets/
#   - ./.env.production
#   - ~/.ssh/
# Options: [list] | default [.env*, secrets/, credentials/, *.pem, *.key]

default

## Forbidden Commands
# Commands that ALWAYS require human approval before execution.
# Default dangerous commands (always blocked):
#   rm -rf *, git push --force, DROP TABLE, sudo *, etc.
# Add additional commands:
# Examples:
#   - npm publish
#   - docker push
#   - kubectl delete
# Options: [list] | default [see above]

default

## Command Approval Mode
# How should Claude handle potentially dangerous commands?
#   strict      - Ask approval for ANY write/delete/modify operation
#   cautious    - Ask approval for commands Claude is uncertain about
#   permissive  - Only ask for explicitly forbidden commands
# Options: [value] | default [cautious]

default

## Network Access
# What external network access is allowed?
#   none        - No external network calls (fully offline)
#   fetch-only  - Can fetch/read from URLs, no POST/PUT/DELETE
#   allowlist   - Only specific domains (list below)
#   blocklist   - Everything except specific domains (list below)
#   full        - Unrestricted network access
# Options: [value] | default [fetch-only]

default

## Allowed Domains (if network = allowlist)
# Examples:
#   - github.com
#   - api.anthropic.com


## Blocked Domains (if network = blocklist)
# Examples:
#   - pastebin.com


## Blocked IPs/Subnets
# IP ranges Claude must NEVER access.
# Options: [list] | default [169.254.169.254/32]

default

# ============================================================================
# MCP (MODEL CONTEXT PROTOCOL) TOOLS
# ============================================================================
# Configure MCP servers and tools available to Claude.
# Documentation: https://modelcontextprotocol.io/introduction

## MCP Enabled
# Options: true | false | default [false]

false

## MCP Servers
# List of MCP servers to connect.
# Examples:
#   - github
#   - postgres | ./mcp/postgres-config.json
#   - filesystem


## MCP Tool Permissions
# Which MCP tools require human approval?
#   all           - Approve every MCP tool invocation
#   write-only    - Approve only tools that modify data
#   dangerous     - Approve only explicitly dangerous tools
#   none          - No approval needed
# Options: [value] | default [write-only]

default

# ============================================================================
# REPOSITORY
# ============================================================================

## Repository URL
# HTTPS or SSH format. Leave blank if not yet created.
# Options: [value] | infer | detect (from git remote)

detect

## Default Branch
# Options: [value] | default [main]

default

## PR Strategy
# How do changes flow into the main branch?
#   direct         - Commit directly to main
#   feature-branch - One branch per feature, PR to main
#   gitflow        - develop/release/hotfix branches
# Options: [value] | default [feature-branch]

default

## Commit Strategy
# When should Claude commit changes?
#   per-phase  - One commit at end of each phase
#   per-task   - Commit after each task
#   per-prompt - Commit after each interaction
#   manual     - Never auto-commit
#   atomic     - Commit each logical change
# Options: [value] | default [per-task]

default

## Push Strategy
# When should Claude push to remote?
#   per-phase  - Push at end of each phase
#   per-commit - Push immediately after each commit
#   manual     - Never auto-push
#   on-close   - Push only on phase closeout
# Options: [value] | default [on-close]

default

## Commit Message Format
#   conventional - feat:, fix:, chore:, etc.
#   gitmoji      - Emoji prefixes
#   simple       - Plain messages
#   custom       - Use template below
# Options: [value] | default [conventional]

default

# ============================================================================
# CI/CD STRATEGY
# ============================================================================

## CI Trigger
#   on-push     - Every push to any branch
#   on-pr       - Only on pull requests
#   on-push-pr  - Both push and PR
#   manual      - Only manual dispatch
# Options: [value] | default [on-push-pr]

default

## CI Checks
# Which checks to run? (comma-separated)
#   lint, typecheck, unit-tests, integration, e2e, security, build, docker
# Options: [list] | default [lint, typecheck, unit-tests, build]

default

## Code Scanning
#   codeql, dependabot, secret-scan, none
# Options: [list] | all | none | default [codeql, dependabot]

default

## Branch Protection
#   require-pr, require-review, require-ci-pass, require-up-to-date
# Options: [list] | all | minimal | none | default [require-pr, require-ci-pass]

default

## Container Registry
#   ghcr | ecr | dockerhub | none
# Options: [value] | default [ghcr]

default

## Deployment Environments
#   dev, staging, production
# Options: [list] | none | default [staging, production]

default

## Release Strategy
#   semantic | manual | calendar | none
# Options: [value] | default [semantic]

default

# ============================================================================
# PIPELINE CONFIGURATION
# ============================================================================

## Pipeline Mode
# How much of the pipeline to run?
#   full       - All phases 0-9 including release
#   component  - Skip release (phases 0-8)
#   library    - Minimal for packages (phases 0,1,2,5,6)
#   prototype  - Quick validation only (phases 0,1,2)
# Options: [value] | infer | default [component]

default

## Skip Phases
# Comma-separated phase numbers to skip.
# Example: 8,9
# Options: [value] | default [none]

default

## Human Gates
# Phases requiring explicit human approval.
# Options: [value] | default [0,2,5,9]

default

# ============================================================================
# CONSTRAINTS & REQUIREMENTS
# ============================================================================

## Technical Constraints
# Examples:
#   - Must run in Docker container
#   - Max 512MB memory footprint
# Options: [value] | infer | default [none]

infer

## Infrastructure Context
# Where will this run? What does it integrate with?
# Examples:
#   - Part of Kubernetes cluster in AWS EKS
#   - Connects to PostgreSQL via internal DNS
# Options: [value] | infer | default [standalone container]

infer

## Compliance Requirements
# Examples: GDPR, HIPAA, SOC2, PCI-DSS
# Options: [value] | infer | default [standard security practices]

default

## Dependencies
# External dependencies or blockers.
# Options: [value] | default [none]

default

# ============================================================================
# REFERENCES & CONTEXT
# ============================================================================

## Existing Documentation
# Paths to docs for Claude to read for context.
# Examples:
#   - ./docs/architecture.md
#   - ./README.md


## Reference Implementations
# Similar projects to learn from.
# Examples:
#   - https://github.com/example/similar-service
#   - ../auth-service/


## External Resources
# Links to external docs, APIs, specs.
# Examples:
#   - https://oauth.net/2/


## Additional Context
# Paste any additional context here.


# ============================================================================
# LLM PROVIDER - PRIMARY (Anthropic API)
# ============================================================================
# The primary provider handles critical tasks: PRD authoring, architecture
# decisions, human gates, and final approvals.

## Primary Provider
# Options: anthropic | openai | aws-bedrock | google | openrouter | azure

anthropic

## Primary Model
# The main model for critical thinking tasks.
# Options: [model-id] | default [claude-sonnet-4-20250514]

default

## Fast Model
# For quick operations (validations, simple checks).
# Options: [model-id] | default [claude-haiku]

default

# ============================================================================
# LLM PROVIDER - OLLAMA SERVERS (Local/Network)
# ============================================================================
# Ollama servers handle bulk tasks: audit execution, code scanning, deep
# inspection, and background analysis. This saves API costs significantly.
#
# SETUP INSTRUCTIONS:
#   1. Install Ollama: https://ollama.com/download
#   2. Start Ollama: ollama serve
#   3. Pull a model: ollama pull qwen3-coder:30b
#   4. Add server below with IP:PORT
#
# For air-gapped/offline operation, Ollama is REQUIRED.

## Enable Ollama
# Use Ollama servers for bulk/background tasks?
# Options: true | false | default [false]

false

## Ollama Servers
# List your Ollama servers. First available server is used (failover).
# Format: name | host:port | model | max_context | description
#
# EXAMPLES:
#   local | localhost:11434 | qwen3-coder:30b | 64000 | This machine
#   desktop | 192.168.1.100:11434 | qwen3-coder:30b | 128000 | RTX 5090 Desktop
#   server | 10.0.0.50:11434 | deepseek-r1:32b | 64000 | Lab server
#
# RECOMMENDED MODELS (requires 64k+ context):
#   qwen3-coder:30b   - Best for code analysis (24GB+ VRAM)
#   deepseek-r1:32b   - Best for reasoning/debugging (24GB+ VRAM)
#   qwen3:8b          - Lightweight background tasks (8GB VRAM)
#   qwen3-coder:7b    - Lightweight code tasks (8GB VRAM)
#
# Add one server per line below:

local | localhost:11434 | qwen3-coder:30b | 64000 | Local Ollama instance

## Ollama Failover
# If primary Ollama server unavailable, try next in list?
# Options: true | false | default [true]

default

## Ollama Health Check
# Verify server connectivity before assigning tasks?
# Options: true | false | default [true]

default

# ============================================================================
# LLM PROVIDER - TASK ROUTING
# ============================================================================
# Configure which provider handles which task types.
# This enables cost optimization: expensive API for critical tasks,
# free local models for bulk work.

## Critical Tasks Provider
# PRD authoring, architecture decisions, human gates, approvals.
# Options: primary | ollama | default [primary]

default

## Bulk Tasks Provider
# Audit execution, code scanning, deep analysis (high token volume).
# Options: primary | ollama | default [ollama if enabled, else primary]

default

## Background Tasks Provider
# File indexing, pattern matching, simple validations.
# Options: primary | ollama | default [ollama if enabled, else primary]

default

## Background Model Override
# Use a smaller/faster model for background tasks?
# Options: [model-name] | same | default [qwen3:8b if ollama, else same]

default

# ============================================================================
# LLM PROVIDER - FALLBACK BEHAVIOR
# ============================================================================

## API Fallback to Ollama
# If Anthropic API fails (rate limit, outage), fall back to Ollama?
# Options: true | false | default [true if ollama enabled]

default

## Ollama Fallback to API
# If all Ollama servers fail, fall back to Anthropic API?
# Options: true | false | default [true]

default

## Offline Mode
# Force offline-only operation (no API calls)?
# Requires Ollama with local models.
# Options: true | false | default [false]

false

# ============================================================================
# CONTEXT GARDENER
# ============================================================================
# The Context Gardener is a background agent that monitors conversation length
# during multi-turn dialogues and intelligently compresses context when token
# thresholds are exceeded. This prevents context overflow while preserving
# critical decisions and continuity.

## Gardener Model
# Which model handles context adjudication/compression?
# Use "infer" to auto-select the fastest available model.
# Recommended: haiku (API) or phi3:medium / mistral:7b (local)
# Options: [model-name] | infer | default [infer]

infer

## Threshold Percent
# Trigger adjudication when conversation reaches this % of model's context window.
# Lower = more aggressive compression, higher = less interruption.
# Range: 50-90, recommended: 70
# Options: [value] | default [70]

default

## Fallback Chain
# If primary gardener model fails, try these models in order.
# Comma-separated list. First available model is used.
# Options: [list] | default [haiku, mistral:7b, phi3:medium, llama3.1:8b]

default

## Preserve Recent Exchanges
# After adjudication, always keep the last N message pairs (human + agent).
# Higher = more immediate context, lower = more room for summary.
# Range: 2-8, recommended: 4
# Options: [value] | default [4]

default

## Preserve Opening
# Always keep the opening 2 messages (initial context) after adjudication?
# This helps maintain conversation continuity and original framing.
# Options: true | false | default [true]

default

# ============================================================================
# END OF SETUP
# ============================================================================
# This file lives in: initialization/setup.md
# Also configure: initialization/agent-plan.md, initialization/audit-plan.md
#
# To start the pipeline:
#   ./orchestrator/pipeline init
#
# The orchestrator will read these files and guide you through setup.
