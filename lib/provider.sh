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
# INVOCATION (via claude-local wrapper)
# ============================================================================

# provider_invoke <prompt_file|prompt_string> <output_file> <task_type> [options]
# Task types: critical, bulk, background
# Options:
#   --model=<model>     Override model selection
#   --timeout=<seconds> Override timeout
#   --format=json       Expect JSON output
#
# This now routes through atomic_invoke with --provider, which uses the
# claude-local wrapper for unified model access (ollama/api/max).
#
provider_invoke() {
    local prompt="$1"
    local output_file="$2"
    local task_type="${3:-critical}"
    shift 3

    provider_init

    # Get provider for this task type
    local provider=$(provider_get_for_task "$task_type")
    local model=""
    local timeout=""
    local format=""
    local ollama_host=""

    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --model=*) model="${1#*=}"; shift ;;
            --timeout=*) timeout="${1#*=}"; shift ;;
            --format=*) format="${1#*=}"; shift ;;
            --ollama-host=*) ollama_host="${1#*=}"; shift ;;
            *) shift ;;
        esac
    done

    # Map internal provider names to wrapper provider names
    local wrapper_provider
    case "$provider" in
        primary)
            wrapper_provider="${CLAUDE_PROVIDER:-max}"  # Use default provider (max/api)
            ;;
        ollama)
            wrapper_provider="ollama"
            # Get Ollama server host if not specified
            if [[ -z "$ollama_host" ]]; then
                local server=$(provider_get_ollama_server)
                if [[ -n "$server" ]]; then
                    ollama_host="http://$(echo "$server" | jq -r '.host')"
                    # Get model from server config if not specified
                    [[ -z "$model" ]] && model=$(echo "$server" | jq -r '.model')
                fi
            fi
            ;;
        *)
            wrapper_provider="$provider"
            ;;
    esac

    # Handle fallback if no Ollama server available
    if [[ "$wrapper_provider" == "ollama" && -z "$ollama_host" ]]; then
        if [[ "${_PROVIDER_CONFIG[ollama_fallback_to_api]}" == "true" ]]; then
            echo "WARN: No healthy Ollama servers, falling back to API" >&2
            wrapper_provider="${CLAUDE_PROVIDER:-max}"
        else
            echo "ERROR: No healthy Ollama servers and fallback disabled" >&2
            return 1
        fi
    fi

    # Set timeout based on provider if not specified
    if [[ -z "$timeout" ]]; then
        if [[ "$wrapper_provider" == "ollama" ]]; then
            timeout="$PROVIDER_OLLAMA_TIMEOUT"
        else
            timeout="$PROVIDER_API_TIMEOUT"
        fi
    fi

    # Build atomic_invoke options
    local invoke_opts="--provider=$wrapper_provider"
    [[ -n "$model" ]] && invoke_opts="$invoke_opts --model=$model"
    [[ -n "$format" ]] && invoke_opts="$invoke_opts --format=$format"
    [[ -n "$timeout" ]] && invoke_opts="$invoke_opts --timeout=$timeout"
    [[ -n "$ollama_host" ]] && invoke_opts="$invoke_opts --ollama-host=$ollama_host"

    # Invoke through atomic_invoke (which uses claude-local wrapper)
    atomic_invoke "$prompt" "$output_file" "$task_type task" $invoke_opts
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
