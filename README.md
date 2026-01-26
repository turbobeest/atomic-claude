![atomic-claude](https://github.com/user-attachments/assets/29f568d2-b6e3-4ea9-8775-9feb5edb74a5)

# ATOMIC CLAUDE

**Script-controlled LLM invocations for deterministic software development pipelines.**

```
SCRIPT ──prompt.md──► CLAUDE ──output.json──► SCRIPT ──prompt.md──► CLAUDE ...
   │                                              │
   ▼                                              ▼
[state.json]                                 [state.json]
```

<img width="2816" height="1536" alt="Gemini_Generated_Image_ewch6tewch6tewch" src="https://github.com/user-attachments/assets/deb5bc34-cd3c-42cd-bf0f-ab08f9644215" />



## Philosophy

- **Atomic**: Indivisible units of work. One task, one outcome, no side quests.
- **Claude**: The LLM is a tool, not the orchestrator.

## Core Principles

1. **Script is sovereign** - Bash controls all flow, state, decisions
2. **Claude is stateless** - Each invocation knows only what the prompt tells it
3. **Bounded prompts** - Every Claude call has a markdown file defining exactly what it does
4. **Structured output** - Claude returns parseable results, script validates before proceeding
5. **No context bleed** - Session terminates after each task, fresh start every time
6. **Human gates are script logic** - Not "Claude please ask" but script literally waits

## Quick Start

```bash
# Run the main CLI
./main.sh run 0          # Run Phase 0 (Setup)
./main.sh status         # Check pipeline status
./main.sh list           # List all phases

# The script will:
# 1. Collect configuration (user input)
# 2. Invoke Claude ONLY for non-deterministic tasks
# 3. Validate outputs
# 4. Wait for human approval at gates
# 5. Move to next phase
```

## Hybrid LLM Support

Atomic Claude supports multiple LLM providers with automatic fallback:

| Provider | Mode | Use Case |
|----------|------|----------|
| **Claude Max** | Subscription-based | Primary workhorse (no per-token cost) |
| **Claude API** | Pay-per-token | On-demand / CI environments |
| **Ollama** | Local / Airgapped | Offline operation, fast tasks, cost-free |

Provider routing is configured in `config/models.json`:

```
┌─────────────────────────────────────────────┐
│  Role Routing                               │
│  primary:    max → api → ollama             │
│  fast:       ollama (llama3.2:3b)           │
│  gardener:   ollama (phi3:mini)             │
│  heavyweight: max → api                     │
└─────────────────────────────────────────────┘
```

The **mode bar** displays the active provider and model during LLM invocations:

```
 MAX MODE │ sonnet │ online   ← green bar when connected
 OLLAMA   │ devstral:24b │ airgapped  ← when running offline
```

Fallback is automatic: if Claude Max is unavailable, the system tries Claude API, then Ollama with tier-appropriate model selection (opus → llama3.1:70b, sonnet → devstral:24b, haiku → llama3.2:3b).

## Structure

```
ATOMIC-CLAUDE/
├── main.sh              # CLI entry point
├── lib/
│   ├── atomic.sh        # Core invocation: atomic_invoke(), mode bar UI
│   ├── phase.sh         # Phase lifecycle management
│   ├── provider.sh      # Multi-provider routing & health checks
│   ├── llm-availability.sh  # Model discovery & fallback chains
│   ├── task-state.sh    # Task state machine (pending→running→done)
│   ├── audit.sh         # Phase auditing system
│   └── intro.sh         # Terminal UI effects
│
├── config/
│   └── models.json      # Provider, model & fallback configuration
│
├── skills/
│   └── webapp-testing/  # Playwright E2E patterns (auto-loaded for web projects)
│
├── phases/
│   ├── 0-setup/         # Project initialization
│   ├── 1-discovery/     # Requirements gathering & agent selection
│   ├── 2-prd/           # PRD authoring
│   ├── 3-tasking/       # Task decomposition
│   ├── 4-specification/ # OpenSpec generation
│   ├── 5-implementation/ # TDD cycles
│   ├── 6-code-review/   # Review & refinement
│   ├── 7-integration/   # Integration testing & E2E
│   ├── 8-deployment-prep/ # Release preparation
│   └── 9-release/       # Deployment
│
├── docs/                # Architecture & airgapped model docs
├── .claude/             # Runtime state
├── .outputs/            # Phase outputs
└── .logs/               # Invocation logs
```

## Using the Library

```bash
#!/bin/bash
source lib/phase.sh

phase_start "00-setup" "Project Setup"

# Deterministic task
phase_deterministic "Check environment" check_tools

# LLM task (bounded)
phase_llm_task "Summarize docs" \
    "prompts/summarize.md" \
    "summary.md" \
    --model=haiku

# Human gate
phase_human_gate "Approve configuration?"

phase_complete
```

## Key Function: atomic_invoke

```bash
atomic_invoke <prompt_file|string> <output_file> <description> [options]

Options:
  --model=<model>     sonnet|opus|haiku (default: sonnet)
  --format=json       Validate JSON output
  --timeout=<secs>    Override timeout (default: 300)
  --stdin             Append stdin content to prompt
```

## Design: LLM Tasks Only When Needed

| Category | Example | LLM? |
|----------|---------|------|
| File operations | mkdir, cp, chmod | No |
| Git operations | commit, push, tag | No |
| User input | collect name, menu | No |
| Validation | check file exists | No |
| State management | read/write JSON | No |
| **Analysis** | summarize docs | **Yes** |
| **Synthesis** | generate PRD | **Yes** |
| **Code generation** | write tests | **Yes** |
| **Review** | security audit | **Yes** |

~85% of software development tasks are deterministic. ATOMIC CLAUDE only invokes the LLM for the ~15% that truly require it.

## Skills

Skills are domain-specific knowledge modules loaded at the task level. When a task detects a relevant project type, it automatically injects the corresponding skill content into the LLM prompt.

| Skill | Auto-Detected When | Loaded By |
|-------|-------------------|-----------|
| `webapp-testing` | package.json contains React/Vue/Angular/Svelte/Next/Nuxt/Vite | Task 704 (Testing Execution) |

Skills live in `skills/<name>/SKILL.md` and provide patterns, conventions, and tooling guidance that the LLM uses during generation. They are injected into prompts by the orchestrating task script -- the LLM never decides which skills to load.

## External Repositories

Atomic Claude integrates with two companion repositories for agent selection and audit coverage:

### Agents (`agents/`)

- **Source of truth:** `agent-inventory.csv` (221 agents with category, subcategory, tier, grade, composite score)
- **Generated:** `agent-manifest.json` (via `build-manifest.sh`)
- **Used by:** Task 105 (Agent Selection) during Phase 1 Discovery
- Agents are matched to project needs based on capabilities and graded by composite score

### Audits (`audits/`)

- **Source of truth:** `AUDIT-INVENTORY.csv` (2,186 audits across 43 categories)
- **Generated:** `AUDIT-MENU.md` (via `build-menu.sh`)
- **Used by:** Phase audit system (`lib/audit.sh`) for quality gates
- Categories span security, performance, reliability, accessibility, compliance, and more

## Airgapped / Offline Mode

For environments without internet access, Atomic Claude falls back to Ollama with tiered model selection. See `docs/AIRGAPPED-MODEL-RANKING.md` for the complete agent-to-model mapping.

```bash
# Force offline mode
export ATOMIC_OFFLINE_MODE=true
export ATOMIC_PREFER_LOCAL=true
export CLAUDE_PROVIDER=ollama
```

Minimum pull set for 32GB+ RAM:
```bash
ollama pull devstral:24b   # Primary workhorse
ollama pull llama3.2:3b    # Fast validation tasks
ollama pull llama3.1:8b    # Fallback workhorse
```
