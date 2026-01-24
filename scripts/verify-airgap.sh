#!/bin/bash
#
# Verify airgapped model availability
# Run this before operating in offline/airgapped mode
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

# Model tiers
REQUIRED_MODELS=(
    "devstral:24b"
    "llama3.2:3b"
)

RECOMMENDED_MODELS=(
    "llama3.1:8b"
    "codellama:13b"
    "phi3:mini"
)

OPTIONAL_MODELS=(
    "llama3.1:70b"
    "qwen2:7b"
    "mixtral:8x7b"
    "codellama:34b"
)

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  AIRGAPPED MODEL VERIFICATION${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check Ollama connectivity
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
echo -e "Checking Ollama at ${DIM}$OLLAMA_HOST${NC}..."

if ! curl -s --connect-timeout 5 "$OLLAMA_HOST/api/tags" >/dev/null 2>&1; then
    echo -e "${RED}ERROR: Ollama not running or not reachable${NC}"
    echo ""
    echo "Start Ollama with: ollama serve"
    echo "Or set OLLAMA_HOST environment variable"
    exit 1
fi

echo -e "${GREEN}✓${NC} Ollama connected"
echo ""

# Get available models
AVAILABLE_MODELS=$(curl -s "$OLLAMA_HOST/api/tags" | jq -r '.models[].name' 2>/dev/null || echo "")

check_model() {
    local model="$1"
    local base_model="${model%%:*}"

    # Check exact match first
    if echo "$AVAILABLE_MODELS" | grep -q "^$model$"; then
        return 0
    fi

    # Check for any version of this model
    if echo "$AVAILABLE_MODELS" | grep -q "^$base_model"; then
        return 0
    fi

    return 1
}

# Check required models
echo -e "${CYAN}Required Models${NC} (must have for basic operation):"
required_missing=0
for model in "${REQUIRED_MODELS[@]}"; do
    if check_model "$model"; then
        echo -e "  ${GREEN}✓${NC} $model"
    else
        echo -e "  ${RED}✗${NC} $model ${DIM}(MISSING)${NC}"
        ((required_missing++))
    fi
done
echo ""

# Check recommended models
echo -e "${CYAN}Recommended Models${NC} (for full capability):"
recommended_missing=0
for model in "${RECOMMENDED_MODELS[@]}"; do
    if check_model "$model"; then
        echo -e "  ${GREEN}✓${NC} $model"
    else
        echo -e "  ${YELLOW}○${NC} $model ${DIM}(optional)${NC}"
        ((recommended_missing++))
    fi
done
echo ""

# Check optional models
echo -e "${CYAN}Optional Models${NC} (for advanced tasks):"
optional_available=0
for model in "${OPTIONAL_MODELS[@]}"; do
    if check_model "$model"; then
        echo -e "  ${GREEN}✓${NC} $model"
        ((optional_available++))
    else
        echo -e "  ${DIM}○ $model${NC}"
    fi
done
echo ""

# Summary
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if [[ $required_missing -gt 0 ]]; then
    echo -e "${RED}AIRGAPPED MODE: NOT READY${NC}"
    echo ""
    echo "Missing required models. Run:"
    for model in "${REQUIRED_MODELS[@]}"; do
        if ! check_model "$model"; then
            echo "  ollama pull $model"
        fi
    done
    exit 1
elif [[ $recommended_missing -gt 0 ]]; then
    echo -e "${YELLOW}AIRGAPPED MODE: PARTIAL${NC}"
    echo ""
    echo "Basic operation available, but consider pulling:"
    for model in "${RECOMMENDED_MODELS[@]}"; do
        if ! check_model "$model"; then
            echo "  ollama pull $model"
        fi
    done
    exit 0
else
    echo -e "${GREEN}AIRGAPPED MODE: READY${NC}"
    echo ""
    echo "All required and recommended models available."
    if [[ $optional_available -lt ${#OPTIONAL_MODELS[@]} ]]; then
        echo -e "${DIM}Optional models can be added for heavy reasoning tasks.${NC}"
    fi
    exit 0
fi
