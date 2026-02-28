#!/bin/bash
#
# UX/UI Evaluation Setup Script
# Prepares environment for interactive Phase 0 evaluation
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "UX/UI Evaluation - Setup"
echo "=========================================="
echo ""
echo "This script prepares your environment for"
echo "a real UX evaluation of atomic-claude."
echo ""
echo "You will:"
echo "  1. Create a sample setup.md"
echo "  2. Run Phase 0 interactively"
echo "  3. Rate each touchpoint using the guide"
echo ""
echo "Guide: test/UXUI-EVALUATION-GUIDE.md"
echo ""

read -p "Press Enter to begin setup..."

cd "$PROJECT_ROOT"

# Check for .env file
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  No .env file found"
    echo ""
    echo "You need API credentials to run Phase 0."
    echo ""
    echo "Create .env with one of:"
    echo "  ANTHROPIC_API_KEY=sk-ant-..."
    echo "  or"
    echo "  AWS_PROFILE=default"
    echo "  AWS_REGION=us-east-1"
    echo ""
    read -p "Press Enter after creating .env..."
fi

# Clean state
echo ""
echo "==> Cleaning previous state..."
rm -rf .state .outputs .logs

# Set environment
export ATOMIC_TOOL_DEVELOPMENT="true"  # Disable forcing function
export ATOMIC_UAT_MODE="false"         # Interactive mode
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export ATOMIC_ROOT="$PROJECT_ROOT"

echo "✓ Environment configured"
echo ""

# Create sample setup.md
echo "==> Creating sample setup.md..."
mkdir -p initialization

cat > initialization/setup.md << 'EOF'
# Project Setup
# =============
# Fill in the fields below for your test project.
# This is a sample configuration for UX evaluation.

## Project Information

**name**: TaskFlow API
**description**: RESTful API for task management with user authentication
**type**: new-api
**primary_goal**: Build a production-ready task management API

## Repository Configuration

**repository.url**: detect
**repository.default_branch**: main
**repository.pr_strategy**: feature-branch
**repository.commit_strategy**: per-task
**repository.push_strategy**: on-close
**repository.commit_format**: conventional

## Sandbox & Security

**sandbox.command_approval_mode**: cautious
**sandbox.network_mode**: internet
**sandbox.network_access**: fetch-only

## MCP Servers

**mcp.enabled**: false

## Pipeline Configuration

**pipeline.mode**: full
**pipeline.skip_phases**: []
**pipeline.human_gates**: [0, 2, 5, 9]

## Agent Assignments

**agents.phase_1**: infer
**agents.phase_2**: infer
**agents.phase_3**: infer
**agents.phase_4**: infer
**agents.phase_5**: infer
**agents.phase_6**: infer
**agents.phase_7**: infer
**agents.phase_8**: infer
**agents.phase_9**: infer

## LLM Configuration

**llm.primary_provider**: anthropic
**llm.primary_model**: claude-sonnet-4-5
**llm.fast_model**: claude-haiku-4
**llm.local_fallback**: false

## Context Gardener

**gardener.model**: infer
**gardener.threshold_percent**: 75
**gardener.preserve_recent_exchanges**: 4
**gardener.preserve_opening**: true

## Technical Constraints

**constraints.technical**: Python 3.11+, FastAPI, PostgreSQL, Docker
**constraints.infrastructure**: Kubernetes deployment on AWS
**constraints.compliance**: GDPR compliant data handling
**constraints.dependencies**: Redis for caching, Celery for background tasks
EOF

echo "✓ Created initialization/setup.md"
echo ""
echo "Sample project: TaskFlow API"
echo "You can edit this file to test different scenarios."
echo ""

# Show guide location
echo "=========================================="
echo "Ready for Evaluation"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Open the evaluation guide:"
echo "     test/UXUI-EVALUATION-GUIDE.md"
echo ""
echo "  2. Run Phase 0 interactively:"
echo "     python main.py run 0"
echo ""
echo "  3. Rate each touchpoint using the guide"
echo ""
echo "  4. Save your ratings in:"
echo "     test/uxui-evaluation-results-$(date +%Y-%m-%d).md"
echo ""
echo "Guide explains what to observe at each step."
echo ""

read -p "Press Enter to open the guide, or Ctrl-C to exit..."

# Open guide (macOS)
if command -v open &> /dev/null; then
    open test/UXUI-EVALUATION-GUIDE.md
else
    cat test/UXUI-EVALUATION-GUIDE.md
fi

echo ""
echo "Ready to run: python main.py run 0"
echo ""
