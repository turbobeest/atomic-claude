# Setup Guide

Quick reference for `setup.md` fields. Each field accepts a specific value, `default`, `infer` (extract from your docs), or `detect` (read from environment).

---

## Project Information

| Field | What it controls | Recommendation |
|-------|-----------------|----------------|
| `name` | Project identifier used in state, logs, commits | Use repo name or short codename |
| `description` | One-liner fed to agents for context | Be specific: "REST API for invoice processing" not "a backend service" |
| `type` | Selects phase templates and task shapes | See options below |
| `primary_goal` | Anchors all PRD and tasking decisions | State the deliverable, not the process |

**project.type options:**

| Value | When to use |
|-------|------------|
| `new-component` | Standalone service or module |
| `new-frontend` | Web/mobile UI |
| `new-api` | Backend API service |
| `new-cli` | Command-line tool |
| `new-library` | Shared package/SDK |
| `new-monorepo` | Multi-package repository |
| `existing` | Adding features to existing codebase |
| `migration` | Technology migration (framework, language, infra) |
| `refactor` | Restructuring without feature changes |

---

## LLM Configuration

| Field | What it controls | Notes |
|-------|-----------------|-------|
| `primary_provider` | Which LLM backend to use | `anthropic` (direct API), `aws-bedrock` (enterprise/GovCloud), `ollama` (local/air-gapped) |
| `primary_model` | Model for complex tasks (PRD, code review, architecture) | `default` = Claude Sonnet 4.5. Override for Opus on critical projects |
| `fast_model` | Model for simple tasks (formatting, validation, status) | `default` = Claude Haiku 3.5. Saves cost on high-volume ops |
| `local_fallback` | Fall back to Ollama if primary fails | `true` if Ollama is running, otherwise `false` |

**Credentials go in `.env`, not here.** See `.env.example` in the atomic-claude root. Quick setup:

```bash
# Direct API
ANTHROPIC_API_KEY=sk-ant-...

# OR AWS Bedrock (SSO)
AWS_PROFILE=your-profile
AWS_REGION=us-east-1
CLAUDE_CODE_USE_BEDROCK=1

# OR Bedrock (GovCloud)
AWS_PROFILE=govcloud-profile
AWS_REGION=us-gov-west-1
ANTHROPIC_MODEL=us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0
```

---

## Repository Configuration

| Field | What it controls | Notes |
|-------|-----------------|-------|
| `repository.url` | `detect` reads from `git remote` | Only set manually if remote isn't configured yet |
| `default_branch` | Target for PRs and release tags | `default` = `main` |
| `pr_strategy` | How branches/PRs are created | `default` = feature branches with squash merge |
| `commit_strategy` | Commit granularity | `default` = one commit per task. `atomic` = one per subtask |
| `push_strategy` | When to push | `default` = push after each phase completes |
| `commit_format` | Commit message style | `default` = conventional commits (`feat:`, `fix:`, `chore:`) |

---

## Sandbox & Security

| Field | What it controls | Notes |
|-------|-----------------|-------|
| `command_approval_mode` | Whether shell commands require human approval | `default` = auto-approve safe commands, prompt for destructive ones |
| `network_mode` | Network access restrictions | `default` = `cui` (restricted). Use `open` if agents need to fetch packages, call APIs, etc. |
| `network_access` | Specific allowed domains/ports | Only relevant if `network_mode` is `cui` |

> **Air-gapped environments:** Set `network_mode: cui`, `network_access: none`, and use `ollama` as provider.

---

## Pipeline Configuration

| Field | What it controls | Notes |
|-------|-----------------|-------|
| `pipeline.mode` | Which phases run and at what depth | See below |
| `skip_phases` | Phases to skip entirely | Array of phase numbers, e.g. `[8, 9]` to skip deployment/release |
| `human_gates` | Phases requiring manual approval before proceeding | `[0, 2, 5, 9]` = approve setup, PRD, implementation, release |

**pipeline.mode options:**

| Value | Phases active | Use case |
|-------|--------------|----------|
| `full` | 0-9 | Production delivery with deployment and release |
| `component` | 0-7 | Build and test, skip deployment/release |
| `library` | 0-6 | Shared packages: no integration/deployment phases |
| `prototype` | 0-5 | Quick validation: stop after implementation |

---

## Agent Assignments

| Field | What it controls |
|-------|-----------------|
| `agents.phase_1` through `agents.phase_9` | Which expert agent leads each phase |

Set to `infer` and the pipeline's agent-selector will match agents based on your project type, tech stack, and constraints. Override only if you know you want a specific agent (e.g., `agents.phase_5: rust-pro` for a Rust project).

Browse available agents: run the dashboard and check the Agents tab, or see `agents/agent-inventory.csv`.

---

## Context Gardener

Controls automatic context window management during long-running phases.

| Field | What it controls | Notes |
|-------|-----------------|-------|
| `gardener.model` | Model used for context summarization | `infer` = use fast_model |
| `threshold_percent` | Context usage % that triggers compaction | `75` is safe. Lower = more aggressive pruning |
| `preserve_recent_exchanges` | Number of recent turns to keep verbatim | `4` preserves immediate working context |
| `preserve_opening` | Keep the original system prompt intact | Always `true` unless you know what you're doing |

---

## Technical Constraints

All optional. Set to `infer` to extract from your reference materials, or specify explicitly.

| Field | Example | Purpose |
|-------|---------|---------|
| `constraints.technical` | `"Python 3.11+, FastAPI, PostgreSQL"` | Tech stack guardrails for code generation |
| `constraints.infrastructure` | `"AWS GovCloud, no public endpoints"` | Deployment target constraints |
| `constraints.compliance` | `"SOC2, HIPAA"` | Compliance frameworks affecting design decisions |
| `constraints.dependencies` | `"no GPL, pin all versions"` | Dependency policy |

---

## Reference Materials

List paths (relative to project root) to docs the pipeline should read during Discovery:

```markdown
- ./README.md
- ./docs/ARCHITECTURE.md
- ./docs/API-SPEC.yaml
- ./requirements.md
```

These are ingested in Phase 1 and used to inform PRD generation, task decomposition, and agent selection. More context = better output. Include architecture docs, API specs, design docs, and existing READMEs.
