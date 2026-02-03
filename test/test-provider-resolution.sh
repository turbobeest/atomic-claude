#!/usr/bin/env bash
#
# Test Provider Chain Resolution
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

source "$ROOT_DIR/lib/atomic.sh"
source "$ROOT_DIR/lib/provider.sh"

echo ""
echo "========================================="
echo "  Provider Chain Resolution Test"
echo "========================================="
echo ""

# Test 1: Check provider availability
echo "Test 1: Provider Availability Detection"
echo "----------------------------------------"

providers=(
    "claude-code:Claude Code"
    "anthropic:Anthropic API"
    "aws-bedrock:AWS Bedrock"
    "ollama:Ollama"
    "openai:OpenAI"
)

for entry in "${providers[@]}"; do
    provider="${entry%%:*}"
    name="${entry#*:}"

    if provider_check_availability "$provider"; then
        echo "  ✓ $name is available"
    else
        echo "  ✗ $name is not available"
    fi
done

echo ""

# Test 2: Provider chain resolution
echo "Test 2: Chain Resolution"
echo "----------------------------------------"

test_chains=(
    "anthropic aws-bedrock ollama:API-first chain"
    "ollama anthropic aws-bedrock:Local-first chain"
    "claude-code aws-bedrock anthropic:Subscription-first chain"
    "nonexistent anthropic aws-bedrock:With invalid provider"
)

for entry in "${test_chains[@]}"; do
    chain="${entry%%:*}"
    description="${entry#*:}"

    echo ""
    echo "Chain: $chain"
    echo "Description: $description"

    resolved=$(provider_resolve_chain "$chain" || echo "NONE")
    if [[ "$resolved" == "NONE" ]]; then
        echo "  Result: No provider available"
    else
        echo "  Result: Using $resolved"
    fi
done

echo ""

# Test 3: Task-type resolution
echo "Test 3: Task-Type Resolution"
echo "----------------------------------------"

# Create a mock config file for testing
PROVIDER_CONFIG_FILE="/tmp/test-provider-config.json"
cat > "$PROVIDER_CONFIG_FILE" << 'EOF'
{
  "providers": {
    "chains": {
      "global": "claude-code aws-bedrock anthropic ollama",
      "critical": "anthropic aws-bedrock",
      "bulk": "ollama aws-bedrock anthropic",
      "quick": "claude-code aws-bedrock"
    }
  }
}
EOF

export PROVIDER_CONFIG_FILE

task_types=("critical" "bulk" "quick" "background")

for task_type in "${task_types[@]}"; do
    echo ""
    echo "Task Type: $task_type"

    chain=$(provider_get_chain "$task_type")
    echo "  Chain: $chain"

    resolved=$(provider_resolve_for_task "$task_type")
    echo "  Resolved: $resolved"
done

echo ""

# Test 4: Simulate atomic_invoke with task-type
echo "Test 4: atomic_invoke Integration"
echo "----------------------------------------"
echo ""
echo "If atomic_invoke is called with --task-type=critical,"
echo "it should resolve to the best available provider from"
echo "the critical chain."
echo ""
echo "Example:"
echo "  atomic_invoke prompt.md out.json \"Description\" --task-type=critical"
echo ""
echo "This would resolve to: $(provider_resolve_for_task 'critical')"
echo ""

# Clean up
rm -f "$PROVIDER_CONFIG_FILE"

echo "========================================="
echo "  Tests Complete"
echo "========================================="
echo ""
