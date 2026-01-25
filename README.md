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

## Structure

```
ATOMIC-CLAUDE/
├── main.sh            # CLI entry point
├── lib/
│   ├── atomic.sh      # Core invocation: atomic_invoke()
│   ├── phase.sh       # Phase lifecycle management
│   ├── audit.sh       # Phase auditing system
│   └── intro.sh       # Terminal UI effects
│
├── config/
│   └── models.json    # Provider & model configuration
│
├── phases/
│   ├── 0-setup/       # Project initialization
│   ├── 1-discovery/   # Requirements gathering
│   ├── 2-prd/         # PRD authoring
│   ├── 3-tasking/     # Task decomposition
│   ├── 4-specification/ # OpenSpec generation
│   ├── 5-implementation/ # TDD cycles
│   ├── 6-code-review/ # Review & refinement
│   ├── 7-integration/ # Integration testing
│   ├── 8-deployment-prep/ # Release preparation
│   └── 9-release/     # Deployment
│
├── .claude/           # Runtime state
├── .outputs/          # Phase outputs
└── .logs/             # Invocation logs
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
