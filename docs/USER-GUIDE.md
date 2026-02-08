# Atomic Claude 2.0 - User Guide

Complete guide for using atomic-claude2 to build software projects with AI assistance.

Version: 2.0
Last Updated: 2026-02-07

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Running Phases](#running-phases)
6. [Phase Overview](#phase-overview)
7. [Monitoring Progress](#monitoring-progress)
8. [Resuming & Backtracking](#resuming--backtracking)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)
11. [Best Practices](#best-practices)

---

## Introduction

**Atomic Claude 2.0** is an AI-assisted SDLC (Software Development Life Cycle) pipeline that guides you through building complete software projects from requirements gathering to deployment preparation.

### What It Does

- **Phase 0: Setup** - Configure project, API keys, and environment
- **Phase 1: Discovery** - Gather requirements, select approach
- **Phase 2: PRD** - Generate Product Requirements Document
- **Phase 3: Tasking** - Break down work into tasks
- **Phase 4: Specification** - Create technical specifications
- **Phase 5: Implementation** - Generate code
- **Phase 6: Code Review** - Automated code review
- **Phase 7: Integration** - Integration testing
- **Phase 8: Deployment Prep** - Deployment artifacts
- **Phase 9: Release** - Release documentation

### Key Features

- **Automated Task Execution** - AI-driven task completion
- **State Persistence** - Resume anytime, never lose progress
- **Multi-Provider Support** - Claude, Ollama, AWS Bedrock, OpenAI
- **Cost Optimization** - Route tasks to optimal LLM provider
- **Real-Time Dashboard** - Monitor progress visually
- **Clean Organization** - Enforced directory structure
- **Git Integration** - Automatic commit prompts

---

## Installation

### Prerequisites

- **Python 3.10+**
- **Git**
- **Claude CLI** (for Claude providers)
- **Ollama** (optional, for local LLM)
- **jq** (JSON processor)

### Install Claude CLI

Choose one provider:

**Option 1: Claude Code (Subscription)**
```bash
# Install via Homebrew (macOS)
brew install --cask claude

# Or download from https://claude.ai/download
```

**Option 2: Anthropic API**
```bash
# Set API key
export ANTHROPIC_API_KEY=sk-ant-...
```

**Option 3: AWS Bedrock**
```bash
# Configure AWS credentials
aws configure

# Set region
export AWS_REGION=us-gov-west-1
```

**Option 4: Ollama (Local)**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull mistral
ollama pull llama3

# Start server
ollama serve
```

### Install Atomic Claude 2.0

```bash
# Clone repository
git clone https://github.com/yourusername/atomic-claude2.git
cd atomic-claude2

# Install dependencies
pip install -r requirements.txt

# Verify installation
python main.py --help
```

---

## Quick Start

### 1. Initialize Project

```bash
# Create project directory
mkdir my-project
cd my-project

# Initialize atomic-claude2
git clone https://github.com/yourusername/atomic-claude2.git ATOMIC-CLAUDE

# Create project structure
mkdir -p src tests docs
```

### 2. Configure Environment

Create `.env` file:

```bash
# Copy example
cp ATOMIC-CLAUDE/.env.example ATOMIC-CLAUDE/.env

# Edit with your settings
vim ATOMIC-CLAUDE/.env
```

Minimum configuration:

```bash
# Choose provider: max, api, ollama, bedrock
CLAUDE_PROVIDER=max

# Choose model: opus, sonnet, haiku
CLAUDE_MODEL=sonnet

# API key (if using 'api' provider)
# ANTHROPIC_API_KEY=sk-ant-...

# Network mode: cui (no internet), internet (full access)
ATOMIC_NETWORK_MODE=cui
```

### 3. Run Setup Phase

```bash
cd ATOMIC-CLAUDE
python main.py run 0
```

This will:
- Collect project configuration
- Validate API keys
- Scan reference materials
- Set up environment

### 4. Continue Through Phases

```bash
# Run each phase in order
python main.py run 1  # Discovery
python main.py run 2  # PRD
python main.py run 3  # Tasking
# ... and so on
```

---

## Configuration

### Configuration Files

Atomic Claude uses multiple configuration sources:

1. **Environment Variables** (`.env`)
2. **CLI Arguments**
3. **Phase 0 Outputs** (`.outputs/0-setup/`)
4. **Config Files** (`config/models.json`)

### Priority Order

Highest to lowest:
1. CLI arguments
2. Environment variables
3. `.env` file
4. JSON config files
5. Defaults

### Core Settings

#### Project Configuration

Set in Phase 0, stored in `.outputs/0-setup/project-config.json`:

```json
{
  "project": {
    "name": "my-project",
    "type": "web-application",
    "description": "Project description",
    "version": "0.1.0"
  }
}
```

#### LLM Configuration

```bash
# Provider (max, api, ollama, bedrock)
CLAUDE_PROVIDER=max

# Primary model
CLAUDE_MODEL=sonnet

# Fast model (for quick tasks)
CLAUDE_FAST_MODEL=haiku

# Heavyweight model (for complex tasks)
CLAUDE_HEAVYWEIGHT_MODEL=opus

# Timeout (seconds)
CLAUDE_TIMEOUT=1200

# Max conversation turns
CLAUDE_MAX_TURNS=30
```

#### Ollama Configuration

```bash
# Ollama host
CLAUDE_OLLAMA_HOST=http://localhost:11434

# Context window
CLAUDE_OLLAMA_CONTEXT=65536

# Default model
CLAUDE_OLLAMA_MODEL=mistral
```

#### AWS Bedrock Configuration

```bash
# Enable Bedrock
CLAUDE_CODE_USE_BEDROCK=1

# AWS region
AWS_REGION=us-gov-west-1

# AWS profile (optional)
AWS_PROFILE=default

# Model ID
ANTHROPIC_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
```

#### Network Configuration

```bash
# Network mode
ATOMIC_NETWORK_MODE=cui  # cui, internet, restricted

# Dashboard ports
ATOMIC_TASKS_PORT=5173
ATOMIC_AGENTS_PORT=5174
ATOMIC_AUDITS_PORT=5175
```

### Advanced Configuration

#### Provider Chains

Configure fallback providers in `.outputs/0-setup/project-config.json`:

```json
{
  "providers": {
    "chains": {
      "critical": ["claude-code", "anthropic", "aws-bedrock"],
      "bulk": ["ollama", "anthropic"],
      "quick": ["ollama", "claude-code"]
    }
  }
}
```

#### Model Routing

Route different task types to different models:

```json
{
  "llm": {
    "primary_provider": "max",
    "fast_provider": "ollama",
    "heavyweight_provider": "max",
    "gardener_provider": "ollama",

    "primary_model": "sonnet",
    "fast_model": "haiku",
    "heavyweight_model": "opus",
    "gardener_model": "mistral"
  }
}
```

---

## Running Phases

### Basic Usage

```bash
# Run a phase
python main.py run <phase>

# Examples
python main.py run 0  # Setup
python main.py run 1  # Discovery
python main.py run 2  # PRD
```

### Resume from Task

```bash
# Resume from specific task
python main.py run <phase> --resume-at=<task>

# Examples
python main.py run 2 --resume-at=205
python main.py run 1 --resume-at=106
```

### Check Status

```bash
# View pipeline status
python main.py status
```

Output:
```
📦 0-setup
   ✓ Task 001: Mode Selection
   ✓ Task 002: Config Collection
   ✓ Task 003: Config Review
   ...

📦 1-discovery
   ✓ Task 101: Entry Validation
   ✓ Task 102: Corpus Collection
   ○ Task 103: Import Requirements
   ...
```

### Backtrack

```bash
# Backtrack to earlier phase/task
python main.py backtrack <phase> [<task>]

# Examples
python main.py backtrack 2        # Reset to Phase 2
python main.py backtrack 2 205    # Reset to Task 205
```

### Reset Pipeline

```bash
# Reset entire pipeline
python main.py reset
```

---

## Phase Overview

### Phase 0: Setup

**Purpose**: Initial configuration and environment setup

**Tasks**:
1. **Mode Selection** - Choose document/guided/quick mode
2. **Config Collection** - Gather project configuration
3. **Config Review** - Review and confirm config
4. **API Keys** - Configure LLM providers
5. **Material Scan** - Scan for reference materials
6. **Reference Materials** - Import reference docs
7. **Environment Setup** - Set up directories
8. **Repository Setup** - Initialize Git repo
9. **Environment Check** - Validate setup

**Outputs**:
- `.outputs/0-setup/project-config.json` - Project configuration
- `.outputs/0-setup/secrets.json` - API keys (git-ignored)
- `.outputs/0-setup/materials.json` - Reference materials list

**Time**: 10-15 minutes

### Phase 1: Discovery

**Purpose**: Requirements gathering and approach selection

**Tasks**:
1. **Entry Validation** - Validate Phase 0 outputs
2. **Corpus Collection** - Gather all input materials
3. **Import Requirements** - Import user requirements
4. **Agent Selection** - Select domain expert agent
5. **Opening Dialogue** - Initial requirements discussion
6. **Discovery Work** - Deep dive into requirements
7. **Approach Selection** - Choose technical approach
8. **Discovery Diagrams** - Create architecture diagrams
9. **Phase Audit** - Validate completeness
10. **Closeout** - Phase summary

**Outputs**:
- `.outputs/1-discovery/requirements.md` - Requirements document
- `.outputs/1-discovery/approach.md` - Technical approach
- `.outputs/1-discovery/diagrams/` - Architecture diagrams

**Time**: 30-60 minutes

### Phase 2: PRD

**Purpose**: Generate comprehensive Product Requirements Document

**Tasks**:
1. **Entry Validation** - Validate Phase 1 outputs
2. **Corpus Import** - Import discovery materials
3. **Agent Selection** - Select PRD specialist
4. **Opening Dialogue** - PRD discussion
5. **PRD Authoring** - Generate PRD
6. **PRD Review** - Review and refine
7. **Acceptance Criteria** - Define success criteria
8. **Phase Audit** - Validate PRD
9. **Closeout** - Phase summary

**Outputs**:
- `.outputs/2-prd/prd.md` - Product Requirements Document
- `.outputs/2-prd/acceptance-criteria.md` - Acceptance criteria

**Time**: 45-90 minutes

### Phase 3: Tasking

**Purpose**: Break down work into implementable tasks

**Tasks**:
1. **Entry Validation** - Validate Phase 2 outputs
2. **Corpus Import** - Import PRD materials
3. **Agent Selection** - Select tasking specialist
4. **Task Breakdown** - Create task list
5. **Task Dependencies** - Define task dependencies
6. **Task Estimation** - Estimate effort
7. **Phase Audit** - Validate task breakdown
8. **Closeout** - Phase summary

**Outputs**:
- `.outputs/3-tasking/tasks.json` - Task breakdown
- `.outputs/3-tasking/dependencies.json` - Task dependencies

**Time**: 30-45 minutes

### Phase 4: Specification

**Purpose**: Create technical specifications for implementation

**Tasks**:
1. **Entry Validation** - Validate Phase 3 outputs
2. **Corpus Import** - Import tasking materials
3. **Agent Selection** - Select specification specialist
4. **Tech Stack Selection** - Choose technologies
5. **Architecture Design** - Design system architecture
6. **API Specification** - Define APIs
7. **Database Schema** - Design data models
8. **Component Specs** - Component specifications
9. **Phase Audit** - Validate specifications
10. **Closeout** - Phase summary

**Outputs**:
- `.outputs/4-specification/tech-stack.md` - Technology choices
- `.outputs/4-specification/architecture.md` - Architecture document
- `.outputs/4-specification/api-spec.yaml` - API specification
- `.outputs/4-specification/schema.sql` - Database schema

**Time**: 60-120 minutes

### Phase 5: Implementation

**Purpose**: Generate production-quality code

**Tasks**:
1. **Entry Validation** - Validate Phase 4 outputs
2. **Corpus Import** - Import specification materials
3. **Code Generation** - Generate source code
4. **Test Generation** - Generate unit tests
5. **Documentation** - Generate code documentation
6. **Phase Audit** - Validate code quality
7. **Closeout** - Phase summary

**Outputs**:
- `../src/` - Generated source code
- `../tests/` - Generated test suite
- `../docs/` - API documentation

**Time**: 90-180 minutes (depends on project size)

### Phase 6: Code Review

**Purpose**: Automated code review and quality checks

**Tasks**:
1. **Entry Validation** - Validate Phase 5 outputs
2. **Static Analysis** - Run linters and analyzers
3. **Security Scan** - Security vulnerability scan
4. **Test Coverage** - Check test coverage
5. **Code Review** - AI-assisted code review
6. **Issue Resolution** - Fix identified issues
7. **Phase Audit** - Final quality check
8. **Closeout** - Phase summary

**Outputs**:
- `.outputs/6-code-review/review-report.md` - Code review report
- `.outputs/6-code-review/issues.json` - Issues to fix

**Time**: 30-60 minutes

### Phase 7: Integration

**Purpose**: Integration testing and system validation

**Tasks**:
1. **Entry Validation** - Validate Phase 6 outputs
2. **Test Plan** - Create integration test plan
3. **Test Execution** - Run integration tests
4. **Performance Testing** - Performance benchmarks
5. **Issue Resolution** - Fix integration issues
6. **Phase Audit** - Validate integration
7. **Closeout** - Phase summary

**Outputs**:
- `.outputs/7-integration/test-report.md` - Test results
- `.outputs/7-integration/performance.json` - Performance metrics

**Time**: 45-90 minutes

### Phase 8: Deployment Prep

**Purpose**: Prepare for deployment

**Tasks**:
1. **Entry Validation** - Validate Phase 7 outputs
2. **Deployment Config** - Generate deployment configs
3. **CI/CD Pipeline** - Create pipeline configs
4. **Docker Images** - Create Dockerfiles
5. **Infrastructure Code** - Infrastructure as Code
6. **Deployment Docs** - Deployment documentation
7. **Phase Audit** - Validate deployment artifacts
8. **Closeout** - Phase summary

**Outputs**:
- `.outputs/8-deployment-prep/Dockerfile` - Docker configuration
- `.outputs/8-deployment-prep/ci-cd.yaml` - CI/CD pipeline
- `.outputs/8-deployment-prep/terraform/` - Infrastructure code

**Time**: 45-75 minutes

### Phase 9: Release

**Purpose**: Final release preparation

**Tasks**:
1. **Entry Validation** - Validate Phase 8 outputs
2. **Release Notes** - Generate release notes
3. **User Documentation** - Create user guides
4. **API Documentation** - Generate API docs
5. **Migration Guides** - Create migration guides
6. **Release Checklist** - Final checklist
7. **Phase Audit** - Final validation
8. **Closeout** - Phase summary

**Outputs**:
- `.outputs/9-release/RELEASE-NOTES.md` - Release notes
- `.outputs/9-release/USER-GUIDE.md` - User documentation
- `.outputs/9-release/API-DOCS.md` - API documentation

**Time**: 30-60 minutes

---

## Monitoring Progress

### Command Line Status

```bash
python main.py status
```

### Real-Time Dashboard

Open in browser:
```bash
# Tasks dashboard
open http://localhost:5173

# Agents dashboard
open http://localhost:5174

# Audits dashboard
open http://localhost:5175
```

### State File

View raw state:
```bash
cat .state/task-state.json | jq .
```

### Logs

```bash
# View main log
tail -f .logs/atomic.log

# View specific date
tail -f .logs/atomic-2026-02-07.log
```

---

## Resuming & Backtracking

### Resume After Failure

If a task fails, fix the issue and resume:

```bash
# Resume from failed task
python main.py run 2 --resume-at=205
```

### Skip Completed Tasks

Already-completed tasks are automatically skipped:

```bash
# This will skip tasks 001-004 if already complete
python main.py run 0
```

### Backtrack to Earlier Point

Reset to earlier phase/task:

```bash
# Backtrack to Phase 2 start
python main.py backtrack 2

# Backtrack to Task 205 in Phase 2
python main.py backtrack 2 205
```

This will:
1. Clear state after target point
2. Delete artifacts after target point
3. Clear memory after target point
4. Prompt to clear generated code

### Manual State Reset

```python
from core.state import StateManager

state = StateManager()

# Clear specific task
state._state['phases']['2-prd']['tasks'].pop('205', None)
state.save_state()

# Clear entire phase
state.reset_phase('2-prd')

# Reset everything
state.reset_all()
```

---

## Troubleshooting

### Issue: "Task failed with exit code 1"

**Cause**: Task script error or LLM invocation failed

**Solution**:
1. Check logs: `cat .logs/atomic.log`
2. Check task error: `cat .outputs/2-prd/task205-output.json.err`
3. Retry task: `python main.py run 2 --resume-at=205`

### Issue: "API key not found"

**Cause**: ANTHROPIC_API_KEY not set

**Solution**:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Or set in .env file
```

### Issue: "Ollama server not available"

**Cause**: Ollama not running

**Solution**:
```bash
# Start Ollama
ollama serve

# Verify
curl http://localhost:11434/api/tags
```

### Issue: "Directory purity violation"

**Cause**: Project files in ATOMIC-CLAUDE directory

**Solution**:
```bash
# View violations
cd ATOMIC-CLAUDE
python orchestration/pre_task_validation.py

# Auto-fix
python orchestration/pre_task_validation.py cleanup
```

### Issue: "Task timeout"

**Cause**: Task taking too long

**Solution**:
```bash
# Increase timeout in .env
CLAUDE_TIMEOUT=3600  # 1 hour

# Or use heavyweight model
CLAUDE_MODEL=opus
```

### Issue: "Closeout file not found"

**Cause**: Previous phase incomplete

**Solution**:
```bash
# Check phase status
python main.py status

# Complete previous phase
python main.py run 1
```

### Issue: "State file corrupted"

**Cause**: Invalid JSON in state file

**Solution**:
```bash
# Backup current state
cp .state/task-state.json .state/task-state.json.backup

# Restore from snapshot
cp .state/snapshots/latest.json .state/task-state.json

# Or reset
python main.py reset
```

---

## FAQ

### Q: Can I use multiple LLM providers?

**A**: Yes! Configure provider chains in project config:

```json
{
  "providers": {
    "chains": {
      "critical": ["claude-code", "anthropic"],
      "bulk": ["ollama", "anthropic"]
    }
  }
}
```

### Q: Can I pause and resume later?

**A**: Yes! State is persisted automatically. Just run the same command again.

### Q: Can I run multiple projects?

**A**: Yes! Each project has its own ATOMIC-CLAUDE directory with isolated state.

### Q: Can I customize task prompts?

**A**: Yes! Edit task scripts in `phases/phaseNN/` or create custom tasks.

### Q: Can I skip phases?

**A**: No, phases must run in order. Each phase depends on previous phase outputs.

### Q: Can I use my own models?

**A**: Yes! Configure Ollama with any compatible model:

```bash
ollama pull custom-model
# Set in config
CLAUDE_OLLAMA_MODEL=custom-model
```

### Q: How much does it cost?

**A**: Depends on provider:
- **Claude Code**: Subscription ($20/month)
- **Anthropic API**: Pay per token (~$15-100 per project)
- **AWS Bedrock**: Pay per token (~$10-80 per project)
- **Ollama**: Free (local)

### Q: What if I disagree with AI outputs?

**A**: Edit outputs directly in `.outputs/` directory, then continue.

### Q: Can I add custom phases?

**A**: Yes! See [Developer Guide](DEVELOPER-GUIDE.md) for details.

### Q: Does it work offline?

**A**: Yes with Ollama! Set `CLAUDE_PROVIDER=ollama`.

### Q: What languages are supported?

**A**: All major languages. Specify in project configuration.

---

## Best Practices

### 1. Start with Quick Mode

Use quick mode for initial setup:
```
Mode: quick
```

This skips lengthy dialogues and gets you started faster.

### 2. Provide Good Reference Materials

Place reference docs in parent directory before Phase 0:
```
my-project/
├── docs/
│   ├── requirements.md
│   ├── wireframes.pdf
│   └── api-examples.json
└── ATOMIC-CLAUDE/
```

### 3. Review Outputs After Each Phase

Check outputs before continuing:
```bash
# Review PRD
cat .outputs/2-prd/prd.md

# Continue if good
python main.py run 3
```

### 4. Use Git Commits

Commit after each phase:
```bash
cd ..
git add .
git commit -m "Phase 2 complete: PRD generated"
```

### 5. Monitor Costs

Track API usage:
```bash
# View logs for token counts
grep "tokens=" .logs/atomic.log
```

### 6. Use Ollama for Drafts

Use Ollama for quick iterations, then Claude for final:
```bash
# Draft with Ollama
CLAUDE_PROVIDER=ollama python main.py run 2

# Refine with Claude
python main.py backtrack 2 205
CLAUDE_PROVIDER=max python main.py run 2 --resume-at=205
```

### 7. Keep State Backups

Snapshot important states:
```bash
cp .state/task-state.json .state/backups/phase-2-complete.json
```

### 8. Validate Phase Outputs

Always check closeout files:
```bash
cat .outputs/2-prd/closeout.json
```

### 9. Use Quick Tasks for Simple Work

Configure fast model for quick tasks:
```bash
CLAUDE_FAST_MODEL=haiku
```

### 10. Document Customizations

If you customize tasks, document changes:
```bash
# Add to project README
echo "## Customizations" >> ../README.md
echo "- Task 205: Modified prompt for domain specifics" >> ../README.md
```

---

## Next Steps

1. **Complete all phases** for your project
2. **Review generated code** in `../src/`
3. **Run tests** in `../tests/`
4. **Deploy** using artifacts from Phase 8
5. **Iterate** - Backtrack and refine as needed

---

## Resources

- [API Reference](API-REFERENCE.md) - Complete API documentation
- [Developer Guide](DEVELOPER-GUIDE.md) - Extending atomic-claude2
- [CLAUDE.md](../CLAUDE.md) - Guidance for Claude Code
- [GitHub](https://github.com/yourusername/atomic-claude2) - Source code & issues

---

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/atomic-claude2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/atomic-claude2/discussions)
- **Email**: support@atomic-claude.com

---

## License

MIT License - See [LICENSE](../LICENSE) for details

---

**Happy Building!** 🚀
