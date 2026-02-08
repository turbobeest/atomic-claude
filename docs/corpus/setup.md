# Project Setup - Minimal Test Configuration

## Project Information

**name**: test-project
**description**: Automated test project for Phase 00/01 validation
**type**: new-cli
**primary_goal**: Validate phase functionality without LLM token consumption

## Repository Configuration

**repository.url**: detect
**repository.default_branch**: main
**repository.pr_strategy**: feature-branch
**repository.commit_strategy**: per-task
**repository.push_strategy**: on-close
**repository.commit_format**: conventional

## Sandbox & Security

**sandbox.command_approval_mode**: cautious
**sandbox.network_mode**: cui
**sandbox.network_access**: fetch-only

## MCP Servers

**mcp.enabled**: false

## Pipeline Configuration

**pipeline.mode**: full
**pipeline.skip_phases**: []
**pipeline.human_gates**: [0, 2, 5, 9]

## Agent Assignments (optional)

**agents.phase_1**: default
**agents.phase_2**: default

## LLM Configuration

**llm.primary_provider**: anthropic
**llm.primary_model**: sonnet
**llm.fast_model**: haiku
**llm.local_fallback**: false

## Technical Constraints (optional)

**constraints.technical**: Python 3.11+, minimal dependencies
**constraints.infrastructure**: Local development only
**constraints.compliance**: N/A

## Reference Materials

- ./README.md
- ./test/fixtures/README.md
