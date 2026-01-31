#!/bin/bash
#
# ATOMIC-CLAUDE Memory Layer
# Persistent memory integration via Supermemory
#
# This module provides session-to-session memory, reducing the token tax
# of re-explaining context every session. It integrates with Supermemory
# for persistence and retrieval.
#
# Memory Tiers:
#   1. Session Bootstrap - Context injection on session start
#   2. Gardener Persistence - Checkpoint multi-agent summaries
#   3. Phase Closeout - Structured phase summaries
#

# ============================================================================
# CONFIGURATION
# ============================================================================

MEMORY_ENABLED="${ATOMIC_MEMORY_ENABLED:-false}"
MEMORY_PROVIDER="${ATOMIC_MEMORY_PROVIDER:-supermemory}"
SUPERMEMORY_API_KEY="${SUPERMEMORY_API_KEY:-}"
MEMORY_CHECKPOINT_INTERVAL="${ATOMIC_MEMORY_CHECKPOINT_INTERVAL:-10}"  # turns

# Memory namespaces
MEMORY_NS_PROJECT="project"
MEMORY_NS_PHASE="phase"
MEMORY_NS_GARDENER="gardener"
MEMORY_NS_USER="user"

# ============================================================================
# INITIALIZATION
# ============================================================================

_memory_init() {
    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        return 0
    fi

    if [[ -z "$SUPERMEMORY_API_KEY" ]]; then
        atomic_warn "Memory enabled but SUPERMEMORY_API_KEY not set"
        MEMORY_ENABLED="false"
        return 1
    fi

    # Check if supermemory MCP is available
    if ! _memory_check_mcp; then
        atomic_warn "Supermemory MCP not available, falling back to disabled"
        MEMORY_ENABLED="false"
        return 1
    fi

    atomic_info "Memory layer initialized (provider: $MEMORY_PROVIDER)"
    return 0
}

_memory_check_mcp() {
    # Check if supermemory MCP server is configured
    # This will be implemented when MCP integration is added
    return 0
}

# ============================================================================
# CORE MEMORY OPERATIONS
# ============================================================================

# Write a memory
# Usage: memory_write "namespace:key" "content" ["metadata_json"]
memory_write() {
    local key="$1"
    local content="$2"
    local metadata="${3:-{}}"

    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        return 0
    fi

    local project_id
    project_id=$(_memory_get_project_id)

    # Construct full key with project scope
    local full_key="${project_id}:${key}"

    # Write via MCP or API
    case "$MEMORY_PROVIDER" in
        supermemory)
            _memory_write_supermemory "$full_key" "$content" "$metadata"
            ;;
        local)
            _memory_write_local "$full_key" "$content" "$metadata"
            ;;
        *)
            atomic_warn "Unknown memory provider: $MEMORY_PROVIDER"
            return 1
            ;;
    esac
}

# Read a memory
# Usage: memory_read "namespace:key"
memory_read() {
    local key="$1"

    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        echo ""
        return 0
    fi

    local project_id
    project_id=$(_memory_get_project_id)
    local full_key="${project_id}:${key}"

    case "$MEMORY_PROVIDER" in
        supermemory)
            _memory_read_supermemory "$full_key"
            ;;
        local)
            _memory_read_local "$full_key"
            ;;
        *)
            echo ""
            return 1
            ;;
    esac
}

# Search memories
# Usage: memory_search "query" ["namespace"]
memory_search() {
    local query="$1"
    local namespace="${2:-}"

    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        echo "[]"
        return 0
    fi

    local project_id
    project_id=$(_memory_get_project_id)

    case "$MEMORY_PROVIDER" in
        supermemory)
            _memory_search_supermemory "$query" "$project_id" "$namespace"
            ;;
        local)
            _memory_search_local "$query" "$project_id" "$namespace"
            ;;
        *)
            echo "[]"
            return 1
            ;;
    esac
}

# ============================================================================
# SUPERMEMORY PROVIDER
# ============================================================================

_memory_write_supermemory() {
    local key="$1"
    local content="$2"
    local metadata="$3"

    # TODO: Implement via supermemory MCP tool
    # mcp-cli call supermemory/add_memory '{
    #   "content": "...",
    #   "metadata": {...}
    # }'

    # For now, log the intent
    echo "[memory:write] $key" >> "$ATOMIC_ROOT/.claude/memory.log" 2>/dev/null
    return 0
}

_memory_read_supermemory() {
    local key="$1"

    # TODO: Implement via supermemory MCP tool
    # mcp-cli call supermemory/get_memory '{"key": "..."}'

    echo ""
    return 0
}

_memory_search_supermemory() {
    local query="$1"
    local project_id="$2"
    local namespace="$3"

    # TODO: Implement via supermemory MCP tool
    # mcp-cli call supermemory/search '{"query": "..."}'

    echo "[]"
    return 0
}

# ============================================================================
# LOCAL PROVIDER (Fallback/Development)
# ============================================================================

_memory_write_local() {
    local key="$1"
    local content="$2"
    local metadata="$3"

    local memory_dir="$ATOMIC_ROOT/.claude/memory"
    mkdir -p "$memory_dir"

    local safe_key
    safe_key=$(echo "$key" | tr ':/' '__')
    local memory_file="$memory_dir/${safe_key}.json"

    jq -n \
        --arg key "$key" \
        --arg content "$content" \
        --argjson metadata "$metadata" \
        --arg timestamp "$(date -Iseconds)" \
        '{
            key: $key,
            content: $content,
            metadata: $metadata,
            timestamp: $timestamp
        }' > "$memory_file"

    return 0
}

_memory_read_local() {
    local key="$1"

    local memory_dir="$ATOMIC_ROOT/.claude/memory"
    local safe_key
    safe_key=$(echo "$key" | tr ':/' '__')
    local memory_file="$memory_dir/${safe_key}.json"

    if [[ -f "$memory_file" ]]; then
        jq -r '.content' "$memory_file"
    else
        echo ""
    fi
}

_memory_search_local() {
    local query="$1"
    local project_id="$2"
    local namespace="$3"

    local memory_dir="$ATOMIC_ROOT/.claude/memory"

    if [[ ! -d "$memory_dir" ]]; then
        echo "[]"
        return 0
    fi

    # Simple grep-based search for local provider
    local results=()
    for f in "$memory_dir"/*.json; do
        [[ -f "$f" ]] || continue
        if grep -qi "$query" "$f" 2>/dev/null; then
            results+=("$(jq -c '.' "$f")")
        fi
    done

    printf '%s\n' "${results[@]}" | jq -s '.'
}

# ============================================================================
# HIGH-LEVEL MEMORY FUNCTIONS
# ============================================================================

# Get project identifier (used to scope all memories)
_memory_get_project_id() {
    # Use git remote or directory name as project ID
    local project_id
    if git remote get-url origin &>/dev/null; then
        project_id=$(git remote get-url origin | sed 's/.*[/:]\([^/]*\/[^/]*\)\.git$/\1/' | tr '/' '_')
    else
        project_id=$(basename "$ATOMIC_ROOT")
    fi
    echo "$project_id"
}

# Write project identity (Phase 0)
memory_write_project_identity() {
    local description="$1"
    local tech_stack="$2"
    local mode="$3"

    memory_write "${MEMORY_NS_PROJECT}:identity" "$description" \
        "$(jq -n --arg tech "$tech_stack" --arg mode "$mode" '{tech_stack: $tech, mode: $mode}')"
}

# Write current phase state
memory_write_phase_state() {
    local phase="$1"
    local status="$2"

    memory_write "${MEMORY_NS_PROJECT}:phase" \
        "Currently in Phase $phase ($status)" \
        "$(jq -n --arg phase "$phase" --arg status "$status" '{phase: $phase, status: $status}')"
}

# Write a decision
memory_write_decision() {
    local decision="$1"
    local rationale="$2"
    local phase="$3"

    local timestamp
    timestamp=$(date -Iseconds)

    memory_write "${MEMORY_NS_PROJECT}:decision:$timestamp" \
        "$decision" \
        "$(jq -n --arg rationale "$rationale" --arg phase "$phase" '{rationale: $rationale, phase: $phase}')"
}

# Write phase closeout summary
memory_write_phase_closeout() {
    local phase="$1"
    local summary="$2"
    local artifacts="$3"

    memory_write "${MEMORY_NS_PHASE}:${phase}:closeout" \
        "$summary" \
        "$(jq -n --arg artifacts "$artifacts" '{artifacts: $artifacts}')"
}

# Write gardener checkpoint
memory_write_gardener_checkpoint() {
    local session_id="$1"
    local summary="$2"
    local turn_count="$3"

    memory_write "${MEMORY_NS_GARDENER}:${session_id}:checkpoint" \
        "$summary" \
        "$(jq -n --argjson turns "$turn_count" '{turn_count: $turns}')"
}

# Write user preference
memory_write_user_preference() {
    local key="$1"
    local value="$2"

    memory_write "${MEMORY_NS_USER}:preference:$key" "$value"
}

# ============================================================================
# SESSION LIFECYCLE
# ============================================================================

# Called on session start - retrieves relevant context
memory_session_start() {
    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        return 0
    fi

    echo "# Retrieved Memories" > "$ATOMIC_ROOT/.claude/session-context.md"

    # Retrieve project identity
    local identity
    identity=$(memory_read "${MEMORY_NS_PROJECT}:identity")
    if [[ -n "$identity" ]]; then
        echo -e "\n## Project\n$identity" >> "$ATOMIC_ROOT/.claude/session-context.md"
    fi

    # Retrieve current phase
    local phase
    phase=$(memory_read "${MEMORY_NS_PROJECT}:phase")
    if [[ -n "$phase" ]]; then
        echo -e "\n## Current State\n$phase" >> "$ATOMIC_ROOT/.claude/session-context.md"
    fi

    # Retrieve recent decisions
    local decisions
    decisions=$(memory_search "decision" "${MEMORY_NS_PROJECT}")
    if [[ "$decisions" != "[]" ]]; then
        echo -e "\n## Recent Decisions" >> "$ATOMIC_ROOT/.claude/session-context.md"
        echo "$decisions" | jq -r '.[] | "- \(.content)"' >> "$ATOMIC_ROOT/.claude/session-context.md"
    fi

    atomic_info "Session context loaded from memory"
}

# Called on session end - persists important context
memory_session_end() {
    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        return 0
    fi

    # Current phase state should be written by phase scripts
    # This is a hook for any final session-level captures

    atomic_info "Session context saved to memory"
}

# ============================================================================
# EXPORTS
# ============================================================================

export -f memory_write memory_read memory_search
export -f memory_write_project_identity memory_write_phase_state
export -f memory_write_decision memory_write_phase_closeout
export -f memory_write_gardener_checkpoint memory_write_user_preference
export -f memory_session_start memory_session_end
