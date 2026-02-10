# Model Context Protocol (MCP) Configuration

**Last Updated:** February 10, 2026
**Purpose:** Configure external tool integrations for atomic-claude2

---

## What is MCP?

Model Context Protocol (MCP) is a universal adapter that connects Claude Code to external tools and data sources. It exposes these tools as native Claude capabilities.

---

## Configured MCP Servers

### Core Servers (Required)

These MCPs are **required** for atomic-claude2's full functionality:

#### 1. GitHub MCP ⭐
**Purpose:** Native GitHub integration for PR creation, issue management, code review

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-github
```

**Configuration:**
```json
{
  "github": {
    "command": "mcp-server-github",
    "env": {
      "GITHUB_TOKEN": "${GITHUB_TOKEN}"
    }
  }
}
```

**Usage:**
- Phase 1: Fetch repository metadata
- Phase 7: Create integration PRs with test results
- Phase 9: Create releases, generate release notes

**Tools Exposed:**
- `/mcp__github__create_pr`
- `/mcp__github__create_issue`
- `/mcp__github__get_pr`
- `/mcp__github__create_release`

---

#### 2. Filesystem MCP ⭐
**Purpose:** Enhanced file operations with better permission handling

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-filesystem
```

**Configuration:**
```json
{
  "filesystem": {
    "command": "mcp-server-filesystem",
    "args": ["--allowed-paths", "${ATOMIC_ROOT}"]
  }
}
```

**Usage:**
- All phases: Safe file operations with sandboxing
- Phase 1: Corpus collection with better directory traversal

**Tools Exposed:**
- `/mcp__filesystem__read_file`
- `/mcp__filesystem__write_file`
- `/mcp__filesystem__list_directory`
- `/mcp__filesystem__search_files`

---

### Optional Servers (Recommended)

These MCPs **enhance** specific phases but aren't strictly required:

#### 3. Playwright MCP 🎭
**Purpose:** Web testing, E2E test generation

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-playwright
```

**Configuration:**
```json
{
  "playwright": {
    "command": "mcp-server-playwright"
  }
}
```

**Usage:**
- Phase 7: E2E integration testing
- Phase 8: Deployment smoke tests

**Tools Exposed:**
- `/mcp__playwright__navigate`
- `/mcp__playwright__screenshot`
- `/mcp__playwright__click`
- `/mcp__playwright__fill`

---

#### 4. Slack MCP 💬
**Purpose:** Notifications, team communication

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-slack
```

**Configuration:**
```json
{
  "slack": {
    "command": "mcp-server-slack",
    "env": {
      "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}",
      "SLACK_CHANNEL": "${SLACK_CHANNEL}"
    }
  }
}
```

**Usage:**
- Phase 8: Deployment notifications
- Phase 9: Release announcements
- All phases: Error alerts

**Tools Exposed:**
- `/mcp__slack__send_message`
- `/mcp__slack__create_channel`
- `/mcp__slack__list_channels`

---

#### 5. PostgreSQL MCP 🗄️
**Purpose:** Database schema queries, validation

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-postgres
```

**Configuration:**
```json
{
  "postgres": {
    "command": "mcp-server-postgres",
    "env": {
      "DATABASE_URL": "${DATABASE_URL}"
    }
  }
}
```

**Usage:**
- Phase 2: Query existing requirements database
- Phase 4: Validate OpenAPI specs against existing schemas
- Phase 6: Check for SQL injection vulnerabilities

**Tools Exposed:**
- `/mcp__postgres__query`
- `/mcp__postgres__list_tables`
- `/mcp__postgres__describe_table`

---

#### 6. SQLite MCP 💾
**Purpose:** Local database for state persistence, artifacts

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-sqlite
```

**Configuration:**
```json
{
  "sqlite": {
    "command": "mcp-server-sqlite",
    "args": ["--database", "${ATOMIC_ROOT}/.state/atomic.db"]
  }
}
```

**Usage:**
- All phases: Store structured task state
- Phase 0: Project configuration database
- Phase 9: Artifact metadata storage

**Tools Exposed:**
- `/mcp__sqlite__query`
- `/mcp__sqlite__execute`
- `/mcp__sqlite__list_tables`

---

### Advanced Servers (Optional)

These MCPs are for specialized use cases:

#### 7. Puppeteer MCP 🤖
**Purpose:** Browser automation, screenshot generation

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-puppeteer
```

**Usage:**
- Phase 7: Visual regression testing
- Phase 8: Deployment verification

---

#### 8. Figma MCP 🎨
**Purpose:** Design file access, component specs

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-figma
```

**Usage:**
- Phase 1: Import design specs
- Phase 2: Reference design in PRD

---

#### 9. Jira MCP 📋
**Purpose:** Task tracking integration

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-jira
```

**Usage:**
- Phase 3: Create actual tickets
- Phase 9: Update ticket statuses

---

#### 10. Google Drive MCP 📁
**Purpose:** Documentation access

**Installation:**
```bash
npm install -g @modelcontextprotocol/server-gdrive
```

**Usage:**
- Phase 1: Import existing documentation
- Phase 9: Export final documentation

---

## Installation

### Automatic (Recommended)

Use the atomic-claude2 setup script:

```bash
# Interactive mode (recommended)
./scripts/setup-mcp.sh

# Install all recommended MCPs
./scripts/setup-mcp.sh --all

# Install only core MCPs
./scripts/setup-mcp.sh --minimal
```

**Interactive mode prompts:**
```
🔧 MCP Server Installation

Select MCP servers to install:
  [1] Core only (GitHub + Filesystem) - Required
  [2] Core + Recommended (+ Playwright, Slack, PostgreSQL, SQLite)
  [3] Custom selection
  [4] Skip (I'll install manually later)

Select option [1-4]:
```

**During Phase 0 (Setup)**, Task 001 will remind you to run this script.

### Manual

```bash
# Install specific MCPs
npm install -g @modelcontextprotocol/server-github
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-playwright
npm install -g @modelcontextprotocol/server-slack

# Verify installation
mcp-server-github --version
mcp-server-filesystem --version
```

---

## Configuration File

Atomic-claude2 manages MCP configuration in `.mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "mcp-server-github",
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": ["--allowed-paths", "${ATOMIC_ROOT}"]
    },
    "playwright": {
      "command": "mcp-server-playwright"
    },
    "slack": {
      "command": "mcp-server-slack",
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}",
        "SLACK_CHANNEL": "#atomic-builds"
      }
    }
  }
}
```

**Environment Variables:**

Required for authenticated MCPs (add to `.env`):
```bash
# GitHub
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx

# Slack
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxxxxxxx
SLACK_CHANNEL=#atomic-builds

# PostgreSQL (if used)
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
```

---

## Usage in Task Scripts

### Bash Integration

```bash
#!/usr/bin/env bash
# Task 701: Integration PR Creation

source "$LIB_DIR/atomic.sh"

task_701_create_pr() {
    atomic_step "Create Integration PR"

    # Build PR description
    local pr_body
    pr_body=$(cat <<EOF
## Integration Test Results

- ✅ Unit tests: 127/127 passing
- ✅ Integration tests: 45/45 passing
- ✅ E2E tests: 12/12 passing

## Changes

$(git log --oneline main..integration | head -10)

## Review Checklist

- [ ] Code review completed
- [ ] Security scan passed
- [ ] Documentation updated
EOF
)

    # Use GitHub MCP to create PR
    local prompt
    prompt=$(cat <<EOF
Use the GitHub MCP to create a pull request:

Title: "Phase 7: Integration Testing Complete"
Base: main
Head: integration
Body: $pr_body

Create the PR now.
EOF
)

    atomic_invoke "$prompt" "$output_file" "Create Integration PR"

    # Claude will use: /mcp__github__create_pr
    # Returns PR URL in output

    atomic_success "PR created: $(cat "$output_file" | grep -o 'https://github.com/[^"]*')"
}
```

### Python Integration

```python
# orchestration/github_integration.py

from core.subprocess_runner import run_task_script_streaming

def create_release_via_mcp(version: str, changelog: str) -> str:
    """Use GitHub MCP to create release."""

    prompt = f"""
Use the GitHub MCP to create a release:

Tag: v{version}
Name: Release v{version}
Body:
{changelog}

Mark as latest release.
Create the release now.
"""

    # Claude will use: /mcp__github__create_release
    exit_code = run_task_script_streaming(
        prompt=prompt,
        phase_id="9-release",
        task_id="901",
        timeout=300
    )

    return exit_code == 0
```

---

## Phase-Specific MCP Usage

### Phase 0: Setup
- **Filesystem MCP**: Validate directory structure
- **SQLite MCP**: Initialize project database

### Phase 1: Discovery
- **GitHub MCP**: Fetch repository metadata, contributor stats
- **Filesystem MCP**: Enhanced corpus collection
- **Google Drive MCP**: Import existing docs (if available)

### Phase 2: PRD
- **PostgreSQL MCP**: Query requirements database (if exists)
- **Figma MCP**: Reference design specs (if available)

### Phase 3: Tasking
- **Jira MCP**: Create actual tickets (optional)
- **SQLite MCP**: Store task dependency graph

### Phase 4: Specification
- **PostgreSQL MCP**: Validate specs against existing schemas

### Phase 5: Implementation
- **Filesystem MCP**: Safe multi-file generation

### Phase 6: Code Review
- **GitHub MCP**: Create review comments on PR (if exists)

### Phase 7: Integration
- **Playwright MCP**: E2E testing
- **GitHub MCP**: Create integration PR
- **Slack MCP**: Send test results notification

### Phase 8: Deployment Prep
- **Slack MCP**: Send deployment readiness notification
- **SQLite MCP**: Record deployment artifacts

### Phase 9: Release
- **GitHub MCP**: Create release, generate notes
- **Slack MCP**: Announce release
- **SQLite MCP**: Archive release metadata

---

## Troubleshooting

### MCP Server Not Found
```
Error: mcp-server-github: command not found
```

**Fix:**
```bash
npm install -g @modelcontextprotocol/server-github
```

### Authentication Errors
```
Error: GitHub token invalid or expired
```

**Fix:**
```bash
# Generate new token at https://github.com/settings/tokens
# Add to .env:
echo "GITHUB_TOKEN=ghp_newtoken" >> .env
```

### Permission Denied
```
Error: Filesystem MCP denied access to /path/outside/project
```

**Fix:**
```json
{
  "filesystem": {
    "args": ["--allowed-paths", "${ATOMIC_ROOT},/other/allowed/path"]
  }
}
```

---

## Security Considerations

1. **Token Storage**: Always use environment variables, never commit tokens
2. **Path Restrictions**: Filesystem MCP should only allow project paths
3. **Network Mode**: In CUI mode, disable network-accessing MCPs
4. **Audit Logging**: All MCP tool uses are logged to `.logs/mcp.log`

---

## Future MCPs

Planned for future atomic-claude2 versions:

- **Docker MCP**: Container management
- **Kubernetes MCP**: K8s deployment management
- **AWS MCP**: CloudFormation, Lambda, S3 operations
- **Terraform MCP**: Infrastructure as code validation

---

## Resources

- [MCP Specification](https://modelcontextprotocol.io)
- [Available MCP Servers](https://github.com/modelcontextprotocol/servers)
- [Building Custom MCPs](https://docs.anthropic.com/en/docs/build-with-claude/mcp)

---

*Generated for atomic-claude2 on February 10, 2026*
