#!/bin/bash
#
# Verify LLM availability for airgapped/offline operation
# Supports local and LAN Ollama servers
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Source availability library
source "$ROOT_DIR/lib/llm-availability.sh" 2>/dev/null || {
    echo "ERROR: Could not load llm-availability.sh"
    exit 1
}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# Required models (at least one must be available somewhere)
REQUIRED_CAPABILITIES=(
    "code"      # For implementation
    "reasoning" # For planning/review
    "fast"      # For validation
)

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  LLM AVAILABILITY CHECK${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# ============================================================================
# CHECK CLAUDE PROVIDERS
# ============================================================================

echo -e "${BOLD}Claude Providers${NC}"
echo ""

max_status=$(_llm_check_claude_max)
api_status=$(_llm_check_claude_api)

if [[ "$max_status" == "available" ]]; then
    echo -e "  ${GREEN}●${NC} Claude Max: ${GREEN}available${NC} (opus, sonnet)"
    CLAUDE_AVAILABLE=true
else
    echo -e "  ${DIM}○${NC} Claude Max: unavailable"
    CLAUDE_AVAILABLE=false
fi

if [[ "$api_status" == "available" ]]; then
    echo -e "  ${GREEN}●${NC} Claude API: ${GREEN}available${NC} (opus, sonnet, haiku)"
    CLAUDE_AVAILABLE=true
else
    echo -e "  ${DIM}○${NC} Claude API: unavailable"
fi

echo ""

# ============================================================================
# CHECK OLLAMA SERVERS
# ============================================================================

echo -e "${BOLD}Ollama Servers${NC}"
echo ""

OLLAMA_AVAILABLE=false
AVAILABLE_MODELS=()

while IFS= read -r host; do
    [[ -z "$host" ]] && continue

    host_info=$(_llm_check_ollama_host "$host")
    status=$(echo "$host_info" | jq -r '.status')

    if [[ "$status" == "available" ]]; then
        models=$(echo "$host_info" | jq -r '.models | join(", ")')
        model_count=$(echo "$host_info" | jq -r '.models | length')
        echo -e "  ${GREEN}●${NC} $host: ${GREEN}$model_count models${NC}"
        echo -e "     ${DIM}$models${NC}"
        OLLAMA_AVAILABLE=true

        # Collect models
        while IFS= read -r model; do
            [[ -n "$model" ]] && AVAILABLE_MODELS+=("$model")
        done < <(echo "$host_info" | jq -r '.models[]')
    else
        echo -e "  ${DIM}○${NC} $host: unreachable"
    fi
done < <(_llm_get_ollama_hosts)

if [[ ${#AVAILABLE_MODELS[@]} -eq 0 ]] && [[ "$OLLAMA_AVAILABLE" == "false" ]]; then
    echo -e "  ${DIM}(no servers responding)${NC}"
fi

echo ""

# ============================================================================
# CHECK AGENT READINESS
# ============================================================================

echo -e "${BOLD}Agent Readiness${NC}"
echo ""

# Refresh availability cache
llm_refresh_availability >/dev/null 2>&1

agents_config="$ROOT_DIR/config/agents.json"
if [[ ! -f "$agents_config" ]]; then
    echo -e "  ${YELLOW}!${NC} agents.json not found - skipping agent check"
else
    ready=0
    blocked=0
    blocked_agents=()

    while IFS= read -r agent; do
        if llm_can_agent_run "$agent" 2>/dev/null; then
            ((ready++))
        else
            ((blocked++))
            blocked_agents+=("$agent")
        fi
    done < <(jq -r '.agents | keys[]' "$agents_config")

    if [[ $blocked -eq 0 ]]; then
        echo -e "  ${GREEN}✓${NC} All $ready agents can run with available models"
    else
        echo -e "  ${GREEN}✓${NC} $ready agents ready"
        echo -e "  ${YELLOW}!${NC} $blocked agents blocked (no suitable model):"
        for agent in "${blocked_agents[@]:0:5}"; do
            tier=$(jq -r ".agents[\"$agent\"].model_preference.tier" "$agents_config")
            echo -e "     ${DIM}- $agent (needs: $tier)${NC}"
        done
        if [[ $blocked -gt 5 ]]; then
            echo -e "     ${DIM}... and $((blocked - 5)) more${NC}"
        fi
    fi
fi

echo ""

# ============================================================================
# SUMMARY
# ============================================================================

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if [[ "$CLAUDE_AVAILABLE" == "true" ]]; then
    echo -e "${GREEN}STATUS: FULLY OPERATIONAL${NC}"
    echo ""
    echo "Claude is available. All features supported."
    exit 0
elif [[ "$OLLAMA_AVAILABLE" == "true" ]]; then
    echo -e "${YELLOW}STATUS: AIRGAPPED MODE${NC}"
    echo ""
    echo "Operating with Ollama models only."
    echo "Some agents may have reduced capability."
    echo ""
    echo -e "${DIM}To add more models, run on any Ollama server:${NC}"
    echo "  ollama pull devstral:24b"
    echo "  ollama pull llama3.1:8b"
    exit 0
else
    echo -e "${RED}STATUS: NO LLM AVAILABLE${NC}"
    echo ""
    echo "Neither Claude nor Ollama is accessible."
    echo ""
    echo "Options:"
    echo "  1. Login to Claude: claude login"
    echo "  2. Start local Ollama: ollama serve"
    echo "  3. Add LAN Ollama to: config/ollama-hosts.json"
    exit 1
fi
