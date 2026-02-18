# Claude Code — Complete Features & Capabilities Reference

**Last Updated:** February 7, 2026
**Current Default Model:** Claude Sonnet 4.5 (switchable to Opus 4.6, Haiku 4.5)
**Install:** `npm install -g @anthropic-ai/claude-code` (or via Homebrew/winget)
**Requires:** Node.js 18+

---

## 1. Core Runtime Environments

| Surface | Description |
|---|---|
| **Terminal (CLI)** | The primary experience — run `claude` in any terminal to start a session |
| **VS Code Extension (beta)** | Native IDE integration from the VS Code Marketplace |
| **JetBrains Extension** | IDE integration for IntelliJ-family IDEs |
| **Claude Code on the Web** | Browser-based at `claude.ai/code` and the Claude iOS app — no local setup |
| **Slack Integration** | Tag `@claude` in Slack for code-related tasks |
| **GitHub Integration** | Tag `@claude` on PRs, issues, and comments for automated review/action |
| **Headless / Programmatic (Agent SDK CLI)** | `claude -p "prompt"` for non-interactive use in scripts, CI/CD, and automation |

---

## 2. Supported Models

| Model | Notes |
|---|---|
| **Claude Sonnet 4.5** | Current default in Claude Code — best coding model, parallel tool execution |
| **Claude Opus 4.6** | Most intelligent; frontier reasoning, computer use, agents |
| **Claude Haiku 4.5** | Fastest; ideal for high-volume, latency-sensitive tasks |
| `/model` command | Switch between models mid-session |

---

## 3. Core Capabilities

### Code Intelligence & Generation
- **Build features from descriptions** — natural language → plan → code → validation
- **Multi-file editing** — cross-file refactors with dependency awareness
- **Code understanding & explanation** — ask anything about any codebase; Claude reads and reasons across files
- **Debugging & bug fixing** — describe a bug or paste an error; Claude locates, diagnoses, and patches
- **Code refactoring** — optimize for readability, performance, and modularity
- **Automated testing** — generate and run tests; fix failing tests
- **Code review** — security, performance, quality, architecture review
- **LSP tool for code intelligence** — go-to-definition, find references, hover documentation

### Git & Version Control
- **Commit creation** — generate meaningful commit messages and stage changes
- **Merge conflict resolution** — automated analysis and resolution
- **PR creation & management** — create PRs with descriptions, respond to review comments
- **Git history search** — trace when/how code was introduced or changed
- **Branch management** — create branches, cherry-pick, rebase
- **Automated release notes** — changelog generation from commit history

### Project Understanding
- **200K-token context window** — maintains awareness of entire project structure
- **Full codebase navigation** — understands architecture, dependencies, and patterns
- **Cross-repository awareness** — can reason across multiple repos when configured

---

## 4. Extensibility Building Blocks

### 4a. CLAUDE.md (Memory / Context Files)
The foundational file that gives Claude persistent project knowledge.

| Scope | Location |
|---|---|
| **Project-specific** | `CLAUDE.md` or `.claude/CLAUDE.md` at project root |
| **User-global** | `~/.claude/CLAUDE.md` |
| **Nested/module-level** | `CLAUDE.md` in any subdirectory |

Contents typically include: coding conventions, architecture decisions, tool preferences, workflow rules, tech stack details, and "when to read" pointers to deeper docs.

### 4b. Skills (Agent Skills)
Auto-invoked or manually invoked capability extensions. Follow the open **Agent Skills standard**.

| Feature | Detail |
|---|---|
| **Location** | `.claude/skills/<name>/SKILL.md` |
| **Auto-discovery** | Claude loads skills by matching their `description` against conversation context |
| **Manual invocation** | `/<skill-name>` as a slash command |
| **Frontmatter** | Control invocation (`disable-model-invocation`), allowed tools, context forking, subagent type |
| **Supporting files** | Templates, scripts, patterns alongside SKILL.md |
| **Argument passing** | `$ARGUMENTS` placeholder receives user input |
| **Context forking** | `context: fork` runs the skill in an isolated subagent |
| **Tool restriction** | `allowed-tools` field limits available tools per skill |

### 4c. Slash Commands
Explicit user-triggered shortcuts for common prompts/workflows.

| Feature | Detail |
|---|---|
| **Project-scoped** | `.claude/commands/<name>.md` |
| **User-global** | `~/.claude/commands/<name>.md` |
| **Invocation** | `/<command-name>` in the session |
| **Arguments** | Passed via `$ARGUMENTS` in the markdown template |
| **Can orchestrate** | Can invoke subagents, reference skills, pipeline multi-step workflows |

### 4d. Subagents
Isolated Claude instances that handle delegated tasks with their own context window.

| Feature | Detail |
|---|---|
| **Built-in types** | `Explore` (read-only codebase scanning), `Code` (full tool access), `claude-code-guide` (docs lookup) |
| **Custom subagents** | `.claude/agents/<name>.md` or `agents/` in plugins |
| **Frontmatter config** | `name`, `description`, `tools`, `model`, `skills` |
| **Parallel execution** | Multiple subagents can run simultaneously on different tasks |
| **Async agents** | Fire off a subagent, continue working, receive results when done |
| **Context isolation** | Subagent work doesn't pollute the main conversation context |
| **Preloaded skills** | Skills can be injected into a subagent at startup |

### 4e. Hooks
Event-driven automation triggered at specific lifecycle points.

| Hook Event | When It Fires |
|---|---|
| **PreToolUse** | Before Claude uses a tool (e.g., before writing a file) |
| **PostToolUse** | After Claude uses a tool |
| **Setup** | At repository setup / session initialization |
| **Stop** | When Claude attempts to exit |

| Feature | Detail |
|---|---|
| **Location** | `.claude/hooks/hooks.json` or `hooks/hooks.json` in plugins |
| **Use cases** | Linting gates, formatters, type-checkers, notifications, security checks, auto-commit rules |
| **Timeout** | Configurable (default 10 minutes) |
| **Script execution** | Can run arbitrary shell scripts |

### 4f. Model Context Protocol (MCP)
Universal adapter for connecting Claude Code to external tools and data sources.

| Feature | Detail |
|---|---|
| **Add servers** | `claude mcp add <name> <command>` |
| **Scoping** | `--scope user` (global), `--scope project` (per-repo) |
| **Config file** | `.mcp.json` at project root or `~/.claude/.mcp.json` |
| **Popular integrations** | GitHub, PostgreSQL, Slack, Figma, Jira, Google Drive, Playwright, Puppeteer, filesystem, SQLite, and hundreds more |
| **Tool access** | MCP server tools appear as native slash commands (`/mcp__<server>__<tool>`) |

### 4g. Plugins
Distributable packages that bundle all building blocks together.

| Feature | Detail |
|---|---|
| **Structure** | `.claude-plugin/plugin.json` + `commands/`, `agents/`, `skills/`, `hooks/`, `.mcp.json` |
| **Install** | `/plugin install <github-url>` or `/plugin install <local-path>` |
| **Discovery** | Plugin marketplaces, GitHub repos, community lists |
| **Manifest** | `plugin.json` with `name`, `version`, `description`, `author` |
| **SDK support** | Programmatic plugin loading via the Agent SDK |

---

## 5. Session & Context Management

| Feature | Detail |
|---|---|
| **`/clear`** | Clear conversation context and start fresh |
| **`/compact`** | Compress/summarize context to reclaim token space |
| **`/context`** | View token usage breakdown — see what's consuming your context window; grouped by source with token counts |
| **`/catchup` (custom)** | Common user pattern: re-read changed files after clearing |
| **`--continue`** | Resume previous session with cached context |
| **`--resume`** | Resume a specific named session |
| **Named sessions** | Persist and switch between multiple named sessions |
| **Auto-compaction** | Automatic context compression when nearing limits |
| **Searchable prompt history** | `Ctrl+R` to search and reuse previous prompts |
| **`.claudeignore`** | Exclude files/dirs from Claude's awareness (like `.gitignore`) |
| **`@`-file references** | `@path/to/file` to explicitly pull files into context |

---

## 6. Checkpoints & Safety

| Feature | Detail |
|---|---|
| **Automatic checkpoints** | Code state auto-saved before every AI-made change |
| **Rewind** | `Esc Esc` (double-tap) or `/rewind` to roll back |
| **Granular restore** | Choose to restore code only, conversation only, or both |
| **Version control complementary** | Checkpoints apply to Claude's edits; use alongside git |
| **Permission system** | Claude asks before modifying files or running commands |
| **Tool allowlists** | Configure which tools Claude can use without asking |

---

## 7. Headless Mode & CI/CD (Agent SDK CLI)

| Feature | Detail |
|---|---|
| **`-p` / `--print` flag** | Non-interactive execution; pipe in/out of other tools |
| **`--output-format`** | `text`, `json`, `stream-json` for structured output |
| **`--max-turns`** | Limit execution depth |
| **`--allowedTools`** | Restrict which tools are available in headless runs |
| **Stdin piping** | `cat file.ts \| claude -p "Review this"` |
| **GitHub Actions** | Official integration for automated PR reviews, code fixes, security checks |
| **Pre-commit hooks** | Run Claude as a git pre-commit check |
| **CI/CD pipelines** | Embed Claude in any CI system (GitHub Actions, GitLab, Bitbucket, etc.) |
| **Scripting composition** | Chain Claude calls in bash scripts, process files in loops |

---

## 8. Claude Agent SDK (formerly Claude Code SDK)

| Feature | Detail |
|---|---|
| **Languages** | Python and TypeScript packages |
| **Same internals** | Same tools, agent loop, and context management as Claude Code |
| **Structured outputs** | Native message objects with typed responses |
| **Tool approval callbacks** | Programmatic control over tool permission grants |
| **Subagent support** | SDK support for spawning and managing subagents |
| **Hook support** | SDK support for lifecycle hooks |
| **Plugin loading** | Programmatic loading of plugins from local directories |
| **Custom agent building** | Build custom agentic experiences on the same foundation as Claude Code |
| **Use cases** | Financial compliance agents, cybersecurity agents, debugging agents, etc. |

---

## 9. Enterprise & Security

| Feature | Detail |
|---|---|
| **Amazon Bedrock** | Run Claude Code through your existing Bedrock deployment |
| **Google Cloud Vertex AI** | Run Claude Code through your existing Vertex AI deployment |
| **Local execution** | Runs locally in your terminal — no remote code index or backend server |
| **Permission prompts** | Explicit approval required before file changes or command execution |
| **Data privacy** | Feedback data is not used for model training |
| **SOC 2 compliance** | Enterprise-grade security and compliance |
| **VPC / on-premises** | Custom deployments for enterprise tier |
| **Team configuration sharing** | Share `settings.json` and plugins across the team via repos |

---

## 10. Built-in Slash Commands (Interactive Mode)

| Command | Purpose |
|---|---|
| `/help` | Show help and available commands |
| `/model` | Switch between Opus, Sonnet, Haiku |
| `/clear` | Clear conversation state |
| `/compact` | Compress context |
| `/context` | View context token breakdown |
| `/rewind` | Roll back to a checkpoint |
| `/stats` | View session statistics |
| `/bug` | Report a bug to Anthropic |
| `/theme` | Change terminal theme; `Ctrl+T` toggles syntax highlighting |
| `/statusline` | Customize terminal status line |
| `/terminal-setup` | Configure terminal (supports iTerm, Kitty, Alacritty, Zed, Warp) |
| `/plugin` | Install, list, and manage plugins |
| `/plugins discover` | Browse available plugins |
| `!<command>` | Run a shell command directly, bypassing conversational mode |

---

## 11. Terminal & UX Features

| Feature | Detail |
|---|---|
| **Refreshed terminal interface** | Improved status visibility, progress indicators |
| **Searchable prompt history** | `Ctrl+R` to search past prompts |
| **Vim mode** | Vim keybindings in the terminal |
| **Clickable file path hyperlinks** | OSC 8 support in compatible terminals (e.g., iTerm) |
| **Syntax highlighting** | Toggle with `Ctrl+T` in `/theme` |
| **Customizable status line** | `/statusline` to configure your prompt display |
| **Image drag-and-drop** | Drag images onto the terminal with source path metadata |
| **Background tasks** | Long-running processes (dev servers) stay active without blocking Claude |
| **Ecomode** | Token-efficient execution path (30–50% token savings) |
| **`/stats`** | View token usage, cost, and session metrics |

---

## 12. Output & Formatting

| Feature | Detail |
|---|---|
| **Output styles** | Configurable output formatting preferences |
| **Stream-JSON output** | Real-time structured output for programmatic consumption |
| **Markdown rendering** | Rich terminal output |
| **Progress indicators** | Tick boxes and step-by-step status during complex tasks |

---

## 13. Web Search & External Knowledge

| Feature | Detail |
|---|---|
| **Built-in web search** | Claude can search the web for up-to-date information |
| **Documentation lookup** | Built-in subagent (`claude-code-guide`) for Claude Code's own docs |
| **URL fetching** | Read and process content from URLs |

---

## 14. Authentication & Access

| Tier | Access |
|---|---|
| **Claude Pro** | ~10–40 prompts / 5 hours, Sonnet 4.5 |
| **Claude Max** | 5× usage, all models including Opus 4.6, API access |
| **API (pay-as-you-go)** | Direct API key, full model access, usage-based billing |
| **Enterprise** | Custom deployments, SLAs, dedicated support, Bedrock/Vertex |

---

## 15. Key CLI Flags & Options

| Flag | Purpose |
|---|---|
| `-p` / `--print` | Headless mode (non-interactive) |
| `--output-format` | `text`, `json`, `stream-json` |
| `--max-turns` | Limit agent execution turns |
| `--allowedTools` | Restrict available tools |
| `--continue` | Resume last session |
| `--resume` | Resume a named session |
| `--dangerously-skip-permissions` | Skip all permission prompts (use with extreme caution) |
| `--verbose` | Debug output |
| `--api-key` | Specify API key inline |

---

## 16. Advanced Patterns & Workflows

| Pattern | Description |
|---|---|
| **Director Mode** | Give high-level direction; let Claude plan and execute multi-step implementations |
| **Document & Clear** | Dump plan/progress to `.md`, `/clear`, start new session reading that `.md` |
| **Parallel subagent orchestration** | Farm out research, implementation, testing to concurrent subagents |
| **Skill-command-subagent pipelines** | Chain: slash command triggers → skill activates → subagent executes |
| **Exponential backoff monitoring** | Have Claude check CI/build status with increasing intervals |
| **Ralph loops** | Autonomous iteration loops where Claude works on a task until completion |
| **Multi-repo refactors** | Coordinated agents working across codebases |
| **PR review automation** | Specialized parallel review agents (security, quality, architecture, tests) |

---

## Changelog / What's New (Recent Highlights)

| Date | Feature |
|---|---|
| **Jan 2026** | Opus 4.6 released — industry-leading for agentic coding; new default `claude-opus-4-6` |
| **Nov 2025** | Opus 4.5 released — most intelligent model, $5/$25 per million tokens; Agent Skills in API; advanced tool use (Tool Search, Programmatic Tool Calling, Tool Use Examples) |
| **Oct 2025** | LSP tool for code intelligence; `/terminal-setup` for Kitty, Alacritty, Zed, Warp; `/context` visualization improvements |
| **Sep 2025** | Claude Sonnet 4.5 + Claude Code 2.0 — checkpoints, VS Code extension, refreshed terminal UI, subagents, hooks, Agent SDK, `/rewind`, searchable prompt history |
| **Aug 2025** | Customizable status line (`/statusline`); background commands |
| **Feb 2025** | Claude Code initial launch — terminal-based agentic coding tool |

---

*This document is intended as a living reference. Update it as Anthropic ships new features. Check the [official docs](https://code.claude.com/docs/en/overview), the [changelog](https://claudelog.com/claude-code-changelog/), and the [GitHub repo](https://github.com/anthropics/claude-code) for the latest.*
