# Atomic Claude 2.0 - Tool Development Configuration

## Project Information

**name**: atomic-claude2
**description**: Next-generation LLM orchestration system with Python core
**type**: system
**primary_goal**: Develop a deterministic, state-driven SDLC pipeline orchestrator

## LLM Configuration

**llm.primary_provider**: bedrock
**llm.primary_model**: sonnet
**llm.fast_model**: haiku
**llm.local_fallback**: true

## Pipeline Configuration

**pipeline.mode**: full
**pipeline.skip_phases**: []
**pipeline.human_gates**: [0, 2, 5]

## Sandbox & Security

**sandbox.command_approval_mode**: cautious
**sandbox.network_mode**: cui
**sandbox.network_access**: fetch-only

## Repository Configuration

**repository.default_branch**: main
**repository.commit_strategy**: per-task
**repository.commit_format**: conventional

## MCP Servers

**mcp.enabled**: false

## Constraints

**constraints.technical**: Python 3.9+, Bash 5.0+, JSON schemas
**constraints.infrastructure**: Local development, AWS Bedrock, Ollama
