#!/bin/bash
#
# LLM Availability System
# Real-time tracking of available LLMs across Claude and Ollama providers
#
# Usage:
#   source lib/llm-availability.sh
#   llm_refresh_availability          # Update availability cache
#   llm_get_available_models          # List all available models
#   llm_can_agent_run "agent-name"    # Check if agent's preferred model is available
#   llm_resolve_agent_model "agent"   # Get best available model for agent
#

# ============================================================================
# CONFIGURATION
# ============================================================================

# Cache settings
LLM_CACHE_DIR="${ATOMIC_STATE_DIR:-$ATOMIC_ROOT/.claude}/llm-cache"
LLM_CACHE_TTL="${LLM_CACHE_TTL:-60}"  # Seconds before refresh
LLM_AVAILABILITY_FILE="$LLM_CACHE_DIR/availability.json"

# Ollama discovery
OLLAMA_HOSTS_FILE="${ATOMIC_ROOT}/config/ollama-hosts.json"
OLLAMA_DISCOVERY_TIMEOUT="${OLLAMA_DISCOVERY_TIMEOUT:-3}"

# ============================================================================
# INITIALIZATION
# ============================================================================

_llm_init() {
    mkdir -p "$LLM_CACHE_DIR"

    # Initialize empty availability if not exists
    if [[ ! -f "$LLM_AVAILABILITY_FILE" ]]; then
        echo '{"providers": {}, "models": [], "last_refresh": 0}' > "$LLM_AVAILABILITY_FILE"
    fi
}

# ============================================================================
# CLAUDE AVAILABILITY
# ============================================================================

# Check Claude Max availability
_llm_check_claude_max() {
    local creds_file="$HOME/.claude/.credentials.json"

    if [[ -f "$creds_file" ]]; then
        # Check if credentials are valid (not expired)
        local expiry
        expiry=$(jq -r '.expiry // 0' "$creds_file" 2>/dev/null)
        local now
        now=$(date +%s)

        if [[ "$expiry" -gt "$now" ]] || [[ "$expiry" == "0" ]]; then
            echo "available"
            return 0
        fi
    fi

    echo "unavailable"
    return 1
}

# Check Claude API availability
_llm_check_claude_api() {
    local secrets_file="${ATOMIC_OUTPUT_DIR:-$ATOMIC_ROOT/.outputs}/0-setup/secrets.json"

    if [[ -f "$secrets_file" ]]; then
        local api_key
        api_key=$(jq -r '.anthropic_api_key // empty' "$secrets_file" 2>/dev/null)

        if [[ -n "$api_key" ]]; then
            # Quick validation with API
            local response
            response=$(curl -s --connect-timeout 3 -w "%{http_code}" \
                -H "x-api-key: $api_key" \
                -H "anthropic-version: 2023-06-01" \
                "https://api.anthropic.com/v1/models" 2>/dev/null | tail -1)

            if [[ "$response" == "200" ]]; then
                echo "available"
                return 0
            fi
        fi
    fi

    echo "unavailable"
    return 1
}

# ============================================================================
# OLLAMA DISCOVERY
# ============================================================================

# Get list of Ollama hosts to check
_llm_get_ollama_hosts() {
    local hosts=()

    # Default localhost
    hosts+=("http://localhost:11434")

    # From environment
    if [[ -n "${CLAUDE_OLLAMA_HOST:-}" ]]; then
        hosts+=("$CLAUDE_OLLAMA_HOST")
    fi

    # From hosts file (for LAN servers)
    if [[ -f "$OLLAMA_HOSTS_FILE" ]]; then
        local file_hosts
        file_hosts=$(jq -r '.hosts[]?' "$OLLAMA_HOSTS_FILE" 2>/dev/null)
        while IFS= read -r host; do
            [[ -n "$host" ]] && hosts+=("$host")
        done <<< "$file_hosts"
    fi

    # From secrets file (setup phase)
    local secrets_file="${ATOMIC_OUTPUT_DIR:-$ATOMIC_ROOT/.outputs}/0-setup/secrets.json"
    if [[ -f "$secrets_file" ]]; then
        local secret_hosts
        secret_hosts=$(jq -r '.ollama_hosts[]?' "$secrets_file" 2>/dev/null)
        while IFS= read -r host; do
            [[ -n "$host" ]] && hosts+=("$host")
        done <<< "$secret_hosts"
    fi

    # Deduplicate
    printf '%s\n' "${hosts[@]}" | sort -u
}

# Check a single Ollama host and get its models
_llm_check_ollama_host() {
    local host="$1"

    # Normalize host
    [[ "$host" != http* ]] && host="http://$host"
    [[ "$host" != *:* ]] && host="$host:11434"

    local response
    response=$(curl -s --connect-timeout "$OLLAMA_DISCOVERY_TIMEOUT" "$host/api/tags" 2>/dev/null)

    if [[ -n "$response" ]] && echo "$response" | jq -e '.models' >/dev/null 2>&1; then
        local models
        models=$(echo "$response" | jq -r '.models[].name' 2>/dev/null | tr '\n' ',' | sed 's/,$//')
        echo "{\"host\": \"$host\", \"status\": \"available\", \"models\": [$(echo "$models" | sed 's/\([^,]*\)/"\1"/g')]}"
        return 0
    fi

    echo "{\"host\": \"$host\", \"status\": \"unavailable\", \"models\": []}"
    return 1
}

# ============================================================================
# MAIN AVAILABILITY FUNCTIONS
# ============================================================================

# Refresh all LLM availability (call periodically or on demand)
llm_refresh_availability() {
    _llm_init

    local now
    now=$(date +%s)

    # Build availability JSON
    local availability
    availability=$(cat << EOF
{
    "last_refresh": $now,
    "refresh_ttl": $LLM_CACHE_TTL,
    "providers": {
        "claude_max": {
            "status": "$(_llm_check_claude_max)",
            "models": ["opus", "sonnet"]
        },
        "claude_api": {
            "status": "$(_llm_check_claude_api)",
            "models": ["opus", "sonnet", "haiku"]
        },
        "ollama": {
            "servers": [
EOF
)

    # Check each Ollama host
    local first=true
    while IFS= read -r host; do
        [[ -z "$host" ]] && continue

        if [[ "$first" == true ]]; then
            first=false
        else
            availability+=","
        fi

        availability+=$(_llm_check_ollama_host "$host")
    done < <(_llm_get_ollama_hosts)

    availability+=$(cat << EOF
            ]
        }
    },
    "all_models": $(llm_list_all_models_json)
}
EOF
)

    echo "$availability" | jq '.' > "$LLM_AVAILABILITY_FILE"

    echo "Availability refreshed at $(date -d "@$now" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r "$now" '+%Y-%m-%d %H:%M:%S')"
}

# List all available models as JSON array
llm_list_all_models_json() {
    local models=()

    # Claude models (if available)
    if [[ "$(_llm_check_claude_max)" == "available" ]]; then
        models+=("opus:claude_max" "sonnet:claude_max")
    fi

    if [[ "$(_llm_check_claude_api)" == "available" ]]; then
        models+=("opus:claude_api" "sonnet:claude_api" "haiku:claude_api")
    fi

    # Ollama models
    while IFS= read -r host; do
        [[ -z "$host" ]] && continue

        local host_info
        host_info=$(_llm_check_ollama_host "$host")

        if echo "$host_info" | jq -e '.status == "available"' >/dev/null 2>&1; then
            local host_models
            host_models=$(echo "$host_info" | jq -r '.models[]' 2>/dev/null)
            while IFS= read -r model; do
                [[ -n "$model" ]] && models+=("$model:ollama")
            done <<< "$host_models"
        fi
    done < <(_llm_get_ollama_hosts)

    # Output as JSON array
    printf '%s\n' "${models[@]}" | jq -R . | jq -s .
}

# Get all available models (human readable)
llm_get_available_models() {
    _llm_init

    # Check cache freshness
    local last_refresh
    last_refresh=$(jq -r '.last_refresh // 0' "$LLM_AVAILABILITY_FILE" 2>/dev/null)
    local now
    now=$(date +%s)

    if [[ $((now - last_refresh)) -gt $LLM_CACHE_TTL ]]; then
        llm_refresh_availability >/dev/null
    fi

    # Display availability
    echo ""
    echo "=== LLM Availability ==="
    echo ""

    # Claude providers
    local max_status api_status
    max_status=$(jq -r '.providers.claude_max.status' "$LLM_AVAILABILITY_FILE" 2>/dev/null)
    api_status=$(jq -r '.providers.claude_api.status' "$LLM_AVAILABILITY_FILE" 2>/dev/null)

    echo "Claude Providers:"
    if [[ "$max_status" == "available" ]]; then
        echo "  ● Claude Max: available (opus, sonnet)"
    else
        echo "  ○ Claude Max: unavailable"
    fi

    if [[ "$api_status" == "available" ]]; then
        echo "  ● Claude API: available (opus, sonnet, haiku)"
    else
        echo "  ○ Claude API: unavailable"
    fi

    echo ""
    echo "Ollama Servers:"

    local servers
    servers=$(jq -r '.providers.ollama.servers[]' "$LLM_AVAILABILITY_FILE" 2>/dev/null)

    if [[ -z "$servers" ]]; then
        echo "  (no servers configured)"
    else
        echo "$servers" | jq -r 'if .status == "available" then "  ● \(.host): \(.models | join(", "))" else "  ○ \(.host): unavailable" end'
    fi

    echo ""
}

# ============================================================================
# AGENT MODEL RESOLUTION
# ============================================================================

# Check if an agent can run with available models
# Usage: llm_can_agent_run "security-auditor"
# Returns: 0 if runnable, 1 if not
llm_can_agent_run() {
    local agent_name="$1"
    local agents_config="$ATOMIC_ROOT/config/agents.json"

    if [[ ! -f "$agents_config" ]]; then
        echo "ERROR: agents.json not found" >&2
        return 1
    fi

    # Get agent's model preference
    local tier fallbacks
    tier=$(jq -r ".agents[\"$agent_name\"].model_preference.tier // empty" "$agents_config")
    fallbacks=$(jq -r ".agents[\"$agent_name\"].model_preference.fallback_chain[]?" "$agents_config")

    if [[ -z "$tier" ]]; then
        echo "ERROR: Agent '$agent_name' not found in registry" >&2
        return 1
    fi

    # Check if Claude tier is available
    local max_status api_status
    max_status=$(jq -r '.providers.claude_max.status' "$LLM_AVAILABILITY_FILE" 2>/dev/null)
    api_status=$(jq -r '.providers.claude_api.status' "$LLM_AVAILABILITY_FILE" 2>/dev/null)

    if [[ "$max_status" == "available" ]] || [[ "$api_status" == "available" ]]; then
        return 0  # Claude available, can run preferred tier
    fi

    # Check fallback models on Ollama
    local available_ollama
    available_ollama=$(jq -r '.providers.ollama.servers[] | select(.status == "available") | .models[]' "$LLM_AVAILABILITY_FILE" 2>/dev/null)

    for fallback in $fallbacks; do
        local base_model="${fallback%%:*}"
        if echo "$available_ollama" | grep -q "^$base_model"; then
            return 0  # Fallback available
        fi
    done

    return 1  # No suitable model available
}

# Resolve the best available model for an agent
# Usage: model=$(llm_resolve_agent_model "security-auditor")
# Returns: "model:provider" string
llm_resolve_agent_model() {
    local agent_name="$1"
    local agents_config="$ATOMIC_ROOT/config/agents.json"

    if [[ ! -f "$agents_config" ]]; then
        echo "ERROR: agents.json not found" >&2
        return 1
    fi

    # Get agent's model preference
    local tier fallbacks
    tier=$(jq -r ".agents[\"$agent_name\"].model_preference.tier // empty" "$agents_config")
    fallbacks=$(jq -r ".agents[\"$agent_name\"].model_preference.fallback_chain[]?" "$agents_config")

    if [[ -z "$tier" ]]; then
        echo "ERROR: Agent '$agent_name' not found" >&2
        return 1
    fi

    # Try Claude Max first
    local max_status
    max_status=$(jq -r '.providers.claude_max.status' "$LLM_AVAILABILITY_FILE" 2>/dev/null)
    if [[ "$max_status" == "available" ]]; then
        echo "$tier:claude_max"
        return 0
    fi

    # Try Claude API
    local api_status
    api_status=$(jq -r '.providers.claude_api.status' "$LLM_AVAILABILITY_FILE" 2>/dev/null)
    if [[ "$api_status" == "available" ]]; then
        echo "$tier:claude_api"
        return 0
    fi

    # Try Ollama fallbacks in order
    local available_ollama
    available_ollama=$(jq -r '.providers.ollama.servers[] | select(.status == "available") | .models[]' "$LLM_AVAILABILITY_FILE" 2>/dev/null)

    for fallback in $fallbacks; do
        local base_model="${fallback%%:*}"
        local matched
        matched=$(echo "$available_ollama" | grep "^$base_model" | head -1)
        if [[ -n "$matched" ]]; then
            echo "$matched:ollama"
            return 0
        fi
    done

    echo "NONE:unavailable"
    return 1
}

# ============================================================================
# STATUS DISPLAY
# ============================================================================

# Show comprehensive LLM status
llm_status() {
    llm_get_available_models

    echo "=== Agent Readiness ==="
    echo ""

    local agents_config="$ATOMIC_ROOT/config/agents.json"
    if [[ ! -f "$agents_config" ]]; then
        echo "  (agents.json not found)"
        return
    fi

    local agents
    agents=$(jq -r '.agents | keys[]' "$agents_config")

    local ready=0
    local blocked=0

    for agent in $agents; do
        if llm_can_agent_run "$agent" 2>/dev/null; then
            ((ready++))
        else
            ((blocked++))
            echo "  ✗ $agent (no model available)"
        fi
    done

    echo ""
    echo "Summary: $ready agents ready, $blocked blocked"
}

# ============================================================================
# INITIALIZATION
# ============================================================================

_llm_init
