#!/usr/bin/env bash
#
# Simple E2E Test - Direct Pipeline Execution
# No complex monitoring, just run the pipeline and report status
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ATOMIC CLAUDE - Simple E2E Test                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "→ Checking prerequisites..."
if [[ ! -f .env ]]; then
    echo "✗ No .env file found"
    echo "  Create .env with AWS Bedrock credentials"
    exit 1
fi
echo "✓ .env file exists"

if ! aws sts get-caller-identity --profile bedrock-dev &>/dev/null; then
    echo "✗ AWS SSO not authenticated"
    echo "  Run: aws sso login --profile bedrock-dev"
    exit 1
fi
echo "✓ AWS SSO authenticated"

# Clean previous state
echo ""
echo "→ Cleaning previous test state..."
rm -rf .state .outputs .logs .claude
echo "✓ State cleaned"

# Create minimal test setup
echo ""
echo "→ Creating minimal test configuration..."
mkdir -p initialization

cat > initialization/setup.md << 'EOF'
# Test Project Configuration

**name**: atomic-test
**description**: E2E test of ATOMIC-CLAUDE pipeline
**type**: new-component
**primary_goal**: Validate pipeline execution end-to-end

## LLM Configuration
**llm.primary_provider**: aws-bedrock
**llm.primary_model**: null
**llm.fast_model**: null
**llm.local_fallback**: true

## Provider Configuration
**providers.chains.global**: aws-bedrock ollama

## Repository
**repository.url**: null
**repository.default_branch**: main
**repository.pr_strategy**: feature-branch
**repository.commit_strategy**: per-task
**repository.push_strategy**: manual
**repository.commit_format**: conventional

## Sandbox
**sandbox.command_approval_mode**: cautious
**sandbox.network_mode**: cui
**sandbox.network_access**: fetch-only
**sandbox.forbidden_paths**: [".env*", "secrets/", "*.key", "*.pem"]
**sandbox.blocked_ips**: ["169.254.169.254/32"]

## Pipeline
**pipeline.mode**: component
**pipeline.skip_phases**: []
**pipeline.human_gates**: [0]

## Agents
**agents.phase_0**: default
**agents.phase_1**: infer

## Constraints
**constraints.technical**: ["Bash scripting", "Multi-provider LLM"]
**constraints.infrastructure**: Standalone CLI tool
EOF

echo "✓ Test configuration created"

# Run Phase 0
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Starting Phase 0: Setup                                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "This will run through 9 setup tasks."
echo "Expected duration: 5-10 minutes"
echo ""
echo "You can monitor progress at: http://localhost:5173"
echo ""
echo "Press Enter to start, or Ctrl+C to cancel..."
read -r

# Run with auto-continue (feed 'c' for continue at each prompt)
echo ""
echo "→ Launching Phase 0..."
echo ""

# Use expect to auto-continue through prompts
if command -v expect &>/dev/null; then
    expect << 'EXPECT_SCRIPT'
set timeout 600
spawn ./main.sh run 0
expect {
    "Press Enter" {
        send "\r"
        exp_continue
    }
    "Continue" {
        send "c\r"
        exp_continue
    }
    eof
}
EXPECT_SCRIPT
else
    # Fallback: Manual mode
    echo "⚠  'expect' not installed - you'll need to press 'c' + Enter after each task"
    echo ""
    ./main.sh run 0
fi

# Check results
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Test Results                                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [[ -f .outputs/0-setup/closeout.json ]]; then
    echo "✓ Phase 0 completed successfully"
    echo ""
    echo "Generated files:"
    ls -1 .outputs/0-setup/
    echo ""
    echo "Configuration:"
    jq -r '.project.name, .project.description' .outputs/0-setup/project-config.json 2>/dev/null || echo "  (config file not found)"
    echo ""
    exit 0
else
    echo "✗ Phase 0 did not complete"
    echo ""
    echo "Check logs:"
    echo "  .logs/invocations.log"
    echo "  .state/current-task.json"
    echo ""
    exit 1
fi
