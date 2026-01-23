#!/bin/bash
#
# ATOMIC CLAUDE - Provider Routing Library
# Hybrid LLM provider routing for cost-optimized operations
#
# Usage:
#   source lib/provider.sh
#   provider_invoke "prompt.md" "output.json" "critical"  # Uses API
#   provider_invoke "prompt.md" "output.json" "bulk"      # Uses Ollama if available
#
# Task Types:
#   critical   - PRD authoring, architecture, human gates (→ Anthropic API)
#   bulk       - Audit execution, code scanning, analysis (→ Ollama preferred)
#   background - File indexing, validation, simple tasks (→ Ollama + smaller model)
#

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

PROVIDER_VERSION="0.1.0"
PROVIDER_CONFIG_FILE="${PROVIDER_CONFIG_FILE:-$ATOMIC_OUTPUT_DIR/0-setup/project-config.json}"
PROVIDER_CACHE_DIR="${PROVIDER_CACHE_DIR:-$ATOMIC_STATE_DIR/provider}"

# Default timeouts (seconds)
PROVIDER_API_TIMEOUT="${PROVIDER_API_TIMEOUT:-300}"
PROVIDER_OLLAMA_TIMEOUT="${PROVIDER_OLLAMA_TIMEOUT:-600}"

# Health check cache TTL (seconds)
PROVIDER_HEALTH_CACHE_TTL="${PROVIDER_HEALTH_CACHE_TTL:-60}"

# ============================================================================
# STATE
# ============================================================================

# Loaded configuration (cached)
declare -A _PROVIDER_CONFIG
_PROVIDER_INITIALIZED=false
_OLLAMA_SERVERS=()
_OLLAMA_HEALTHY_SERVERS=()

# ============================================================================
# INITIALIZATION
# ============================================================================

provider_init() {
    if [[ "$_PROVIDER_INITIALIZED" == "true" ]]; then
        return 0
    fi

    mkdir -p "$PROVIDER_CACHE_DIR"

    # Load configuration from project-config.json
    if [[ -f "$PROVIDER_CONFIG_FILE" ]]; then
        _provider_load_config
    else
        # Default configuration
        _PROVIDER_CONFIG[ollama_enabled]="false"
        _PROVIDER_CONFIG[critical_provider]="primary"
        _PROVIDER_CONFIG[bulk_provider]="primary"
        _PROVIDER_CONFIG[background_provider]="primary"
        _PROVIDER_CONFIG[background_model]="same"
        _PROVIDER_CONFIG[api_fallback_to_ollama]="false"
        _PROVIDER_CONFIG[ollama_fallback_to_api]="true"
        _PROVIDER_CONFIG[offline_mode]="false"
    fi

    _PROVIDER_INITIALIZED=true
}

_provider_load_config() {
    local config="$PROVIDER_CONFIG_FILE"

    # Ollama settings
    _PROVIDER_CONFIG[ollama_enabled]=$(jq -r '.providers.ollama.enabled // false' "$config")
    _PROVIDER_CONFIG[ollama_failover]=$(jq -r '.providers.ollama.failover // true' "$config")
    _PROVIDER_CONFIG[ollama_health_check]=$(jq -r '.providers.ollama.health_check // true' "$config")

    # Routing settings
    _PROVIDER_CONFIG[critical_provider]=$(jq -r '.providers.routing.critical // "primary"' "$config")
    _PROVIDER_CONFIG[bulk_provider]=$(jq -r '.providers.routing.bulk // "primary"' "$config")
    _PROVIDER_CONFIG[background_provider]=$(jq -r '.providers.routing.background // "primary"' "$config")
    _PROVIDER_CONFIG[background_model]=$(jq -r '.providers.routing.background_model // "same"' "$config")

    # Fallback settings (from setup.md parsing - stored in providers)
    _PROVIDER_CONFIG[api_fallback_to_ollama]=$(jq -r '.providers.api_fallback_to_ollama // false' "$config")
    _PROVIDER_CONFIG[ollama_fallback_to_api]=$(jq -r '.providers.ollama_fallback_to_api // true' "$config")
    _PROVIDER_CONFIG[offline_mode]=$(jq -r '.providers.offline_mode // false' "$config")

    # Load Ollama servers
    _OLLAMA_SERVERS=()
    local servers_json=$(jq -c '.providers.ollama.servers // []' "$config")
    local server_count=$(echo "$servers_json" | jq 'length')

    for ((i=0; i<server_count; i++)); do
        local server=$(echo "$servers_json" | jq -c ".[$i]")
        _OLLAMA_SERVERS+=("$server")
    done

    # Preload healthy servers if health check enabled
    if [[ "${_PROVIDER_CONFIG[ollama_health_check]}" == "true" ]]; then
        _provider_refresh_healthy_servers
    else
        _OLLAMA_HEALTHY_SERVERS=("${_OLLAMA_SERVERS[@]}")
    fi
}

# ============================================================================
# HEALTH CHECKING
# ============================================================================

_provider_refresh_healthy_servers() {
    _OLLAMA_HEALTHY_SERVERS=()

    for server in "${_OLLAMA_SERVERS[@]}"; do
        local host=$(echo "$server" | jq -r '.host')
        if _provider_check_ollama_health "$host"; then
            _OLLAMA_HEALTHY_SERVERS+=("$server")
        fi
    done
}

_provider_check_ollama_health() {
    local host="$1"
    local cache_file="$PROVIDER_CACHE_DIR/health_$(echo "$host" | tr ':/' '_').json"

    # Check cache
    if [[ -f "$cache_file" ]]; then
        local cached_at=$(jq -r '.timestamp // 0' "$cache_file")
        local now=$(date +%s)
        local age=$((now - cached_at))

        if [[ $age -lt $PROVIDER_HEALTH_CACHE_TTL ]]; then
            local cached_healthy=$(jq -r '.healthy // false' "$cache_file")
            [[ "$cached_healthy" == "true" ]] && return 0 || return 1
        fi
    fi

    # Perform health check
    local healthy=false
    if curl -s --connect-timeout 3 "http://$host/api/tags" &>/dev/null; then
        healthy=true
    fi

    # Cache result
    cat > "$cache_file" << EOF
{
    "host": "$host",
    "healthy": $healthy,
    "timestamp": $(date +%s)
}
EOF

    [[ "$healthy" == "true" ]] && return 0 || return 1
}

# Invalidate health cache for all servers
provider_invalidate_health_cache() {
    rm -f "$PROVIDER_CACHE_DIR"/health_*.json 2>/dev/null || true
    _provider_refresh_healthy_servers
}

# ============================================================================
# PROVIDER SELECTION
# ============================================================================

# Get the provider for a task type
# Returns: "primary" or "ollama"
provider_get_for_task() {
    local task_type="${1:-critical}"

    provider_init

    local provider=""

    case "$task_type" in
        critical)
            provider="${_PROVIDER_CONFIG[critical_provider]}"
            ;;
        bulk)
            provider="${_PROVIDER_CONFIG[bulk_provider]}"
            ;;
        background)
            provider="${_PROVIDER_CONFIG[background_provider]}"
            ;;
        *)
            provider="primary"
            ;;
    esac

    # Check if Ollama is enabled when provider is ollama
    if [[ "$provider" == "ollama" ]]; then
        if [[ "${_PROVIDER_CONFIG[ollama_enabled]}" != "true" ]]; then
            provider="primary"
        elif [[ ${#_OLLAMA_HEALTHY_SERVERS[@]} -eq 0 ]]; then
            # No healthy servers - fallback to primary if allowed
            if [[ "${_PROVIDER_CONFIG[ollama_fallback_to_api]}" == "true" ]]; then
                provider="primary"
            fi
        fi
    fi

    # Check offline mode
    if [[ "${_PROVIDER_CONFIG[offline_mode]}" == "true" ]]; then
        provider="ollama"
    fi

    echo "$provider"
}

# Get the best available Ollama server
# Returns: JSON server object or empty string
provider_get_ollama_server() {
    provider_init

    # Refresh health if needed
    if [[ "${_PROVIDER_CONFIG[ollama_health_check]}" == "true" ]]; then
        _provider_refresh_healthy_servers
    fi

    if [[ ${#_OLLAMA_HEALTHY_SERVERS[@]} -gt 0 ]]; then
        # Return first healthy server (failover order)
        echo "${_OLLAMA_HEALTHY_SERVERS[0]}"
    fi
}

# Get model for task type (handles background model override)
provider_get_model() {
    local task_type="${1:-critical}"

    provider_init

    if [[ "$task_type" == "background" ]]; then
        local override="${_PROVIDER_CONFIG[background_model]}"
        if [[ "$override" != "same" && -n "$override" ]]; then
            echo "$override"
            return
        fi
    fi

    # Return server's configured model
    local server=$(provider_get_ollama_server)
    if [[ -n "$server" ]]; then
        echo "$server" | jq -r '.model'
    fi
}

# ============================================================================
# INVOCATION
# ============================================================================

# provider_invoke <prompt_file|prompt_string> <output_file> <task_type> [options]
# Task types: critical, bulk, background
# Options:
#   --model=<model>     Override model selection
#   --timeout=<seconds> Override timeout
#   --format=json       Expect JSON output
#
provider_invoke() {
    local prompt="$1"
    local output_file="$2"
    local task_type="${3:-critical}"
    shift 3

    provider_init

    local provider=$(provider_get_for_task "$task_type")

    case "$provider" in
        primary)
            _provider_invoke_api "$prompt" "$output_file" "$@"
            ;;
        ollama)
            _provider_invoke_ollama "$prompt" "$output_file" "$task_type" "$@"
            ;;
        *)
            echo "ERROR: Unknown provider: $provider" >&2
            return 1
            ;;
    esac
}

# Invoke via Anthropic API (Claude Code)
_provider_invoke_api() {
    local prompt="$1"
    local output_file="$2"
    shift 2

    local model="$CLAUDE_MODEL"
    local timeout="$PROVIDER_API_TIMEOUT"
    local format=""

    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --model=*) model="${1#*=}"; shift ;;
            --timeout=*) timeout="${1#*=}"; shift ;;
            --format=*) format="${1#*=}"; shift ;;
            *) shift ;;
        esac
    done

    # Use atomic_invoke from atomic.sh
    local opts=""
    [[ -n "$format" ]] && opts="--format=$format"
    [[ -n "$timeout" ]] && opts="$opts --timeout=$timeout"

    atomic_invoke "$prompt" "$output_file" "API task" --model="$model" $opts
}

# Invoke via Ollama
_provider_invoke_ollama() {
    local prompt="$1"
    local output_file="$2"
    local task_type="$3"
    shift 3

    local timeout="$PROVIDER_OLLAMA_TIMEOUT"
    local format=""
    local model_override=""

    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --model=*) model_override="${1#*=}"; shift ;;
            --timeout=*) timeout="${1#*=}"; shift ;;
            --format=*) format="${1#*=}"; shift ;;
            *) shift ;;
        esac
    done

    # Get server and model
    local server=$(provider_get_ollama_server)
    if [[ -z "$server" ]]; then
        # No healthy servers - try fallback
        if [[ "${_PROVIDER_CONFIG[ollama_fallback_to_api]}" == "true" ]]; then
            echo "WARN: No healthy Ollama servers, falling back to API" >&2
            _provider_invoke_api "$prompt" "$output_file" "$@"
            return $?
        else
            echo "ERROR: No healthy Ollama servers and fallback disabled" >&2
            return 1
        fi
    fi

    local host=$(echo "$server" | jq -r '.host')
    local model=$(echo "$server" | jq -r '.model')

    # Apply model override
    if [[ -n "$model_override" ]]; then
        model="$model_override"
    elif [[ "$task_type" == "background" ]]; then
        local bg_model=$(provider_get_model "background")
        [[ -n "$bg_model" ]] && model="$bg_model"
    fi

    # Read prompt
    local prompt_content=""
    if [[ -f "$prompt" ]]; then
        prompt_content=$(cat "$prompt")
    else
        prompt_content="$prompt"
    fi

    # Build request (Anthropic Messages API format - supported by Ollama 0.14+)
    local request=$(cat <<EOF
{
    "model": "$model",
    "max_tokens": 8192,
    "messages": [
        {
            "role": "user",
            "content": $(echo "$prompt_content" | jq -Rs .)
        }
    ]
}
EOF
)

    # Invoke Ollama
    local response
    response=$(curl -s --max-time "$timeout" \
        -H "Content-Type: application/json" \
        -d "$request" \
        "http://$host/v1/messages" 2>&1)

    local curl_exit=$?

    if [[ $curl_exit -ne 0 ]]; then
        echo "ERROR: Ollama request failed (exit $curl_exit)" >&2

        # Try fallback
        if [[ "${_PROVIDER_CONFIG[ollama_fallback_to_api]}" == "true" ]]; then
            echo "WARN: Falling back to API" >&2
            _provider_invoke_api "$prompt" "$output_file" "$@"
            return $?
        fi
        return 1
    fi

    # Extract content from response
    local content=$(echo "$response" | jq -r '.content[0].text // .content // .message.content // empty')

    if [[ -z "$content" ]]; then
        echo "ERROR: Empty response from Ollama" >&2
        echo "$response" >&2
        return 1
    fi

    # Write output
    mkdir -p "$(dirname "$output_file")"
    echo "$content" > "$output_file"

    # Validate JSON if required
    if [[ "$format" == "json" ]]; then
        if ! jq -e . "$output_file" &>/dev/null; then
            echo "WARN: Output is not valid JSON" >&2
        fi
    fi

    return 0
}

# ============================================================================
# UTILITIES
# ============================================================================

# Show provider status
provider_status() {
    provider_init

    echo "Provider Configuration:"
    echo "  Ollama enabled:     ${_PROVIDER_CONFIG[ollama_enabled]}"
    echo "  Offline mode:       ${_PROVIDER_CONFIG[offline_mode]}"
    echo ""
    echo "Task Routing:"
    echo "  Critical tasks:     ${_PROVIDER_CONFIG[critical_provider]}"
    echo "  Bulk tasks:         ${_PROVIDER_CONFIG[bulk_provider]}"
    echo "  Background tasks:   ${_PROVIDER_CONFIG[background_provider]}"
    echo "  Background model:   ${_PROVIDER_CONFIG[background_model]}"
    echo ""

    if [[ "${_PROVIDER_CONFIG[ollama_enabled]}" == "true" ]]; then
        echo "Ollama Servers:"
        for server in "${_OLLAMA_SERVERS[@]}"; do
            local name=$(echo "$server" | jq -r '.name')
            local host=$(echo "$server" | jq -r '.host')
            local model=$(echo "$server" | jq -r '.model')

            local status="○ unreachable"
            for healthy in "${_OLLAMA_HEALTHY_SERVERS[@]}"; do
                local healthy_name=$(echo "$healthy" | jq -r '.name')
                if [[ "$healthy_name" == "$name" ]]; then
                    status="● healthy"
                    break
                fi
            done

            echo "  $status  $name ($host) - $model"
        done
    fi
}

# List available models on a server
provider_list_models() {
    local server="${1:-}"

    if [[ -z "$server" ]]; then
        server=$(provider_get_ollama_server)
    fi

    if [[ -z "$server" ]]; then
        echo "No Ollama server available" >&2
        return 1
    fi

    local host
    if [[ "$server" =~ ^\{ ]]; then
        host=$(echo "$server" | jq -r '.host')
    else
        host="$server"
    fi

    curl -s "http://$host/api/tags" | jq -r '.models[].name' 2>/dev/null
}
