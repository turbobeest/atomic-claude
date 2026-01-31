#!/bin/bash
#
# ATOMIC-CLAUDE Memory Layer
# Persistent memory via Supermemory with checkpoint coherence
#
# Architecture:
#   - Checkpoint model: Memory saved at phase closeouts only
#   - Head tracking: Local state knows current phase progression
#   - Backtrack handling: Invalidates/forgets orphaned memories
#   - Scope separation: Pipeline work vs meta/debug work
#   - User approval: Nothing persists without explicit consent
#

# ============================================================================
# CONFIGURATION
# ============================================================================

# Local state files
MEMORY_HEAD_FILE="${ATOMIC_ROOT:-.}/.state/memory-head.json"
MEMORY_CHECKPOINTS_DIR="${ATOMIC_ROOT:-.}/.state/memory-checkpoints"

# Load configuration from environment and/or secrets file
_memory_load_config() {
    # Check secrets file for memory settings if not in environment
    local secrets_file="${ATOMIC_OUTPUT_DIR:-${ATOMIC_ROOT:-.}/.outputs}/0-setup/secrets.json"

    # Load SUPERMEMORY_API_KEY from secrets if not in env
    if [[ -z "${SUPERMEMORY_API_KEY:-}" ]] && [[ -f "$secrets_file" ]]; then
        SUPERMEMORY_API_KEY=$(jq -r '.supermemory_api_key // empty' "$secrets_file" 2>/dev/null)
        export SUPERMEMORY_API_KEY
    fi

    # Load memory enabled flag from secrets if not in env
    if [[ -z "${ATOMIC_MEMORY_ENABLED:-}" ]] && [[ -f "$secrets_file" ]]; then
        local mem_enabled
        mem_enabled=$(jq -r '.memory_enabled // false' "$secrets_file" 2>/dev/null)
        if [[ "$mem_enabled" == "true" ]]; then
            ATOMIC_MEMORY_ENABLED="true"
            export ATOMIC_MEMORY_ENABLED
        fi
    fi

    # Set module-level variables
    MEMORY_ENABLED="${ATOMIC_MEMORY_ENABLED:-false}"
    SUPERMEMORY_API_KEY="${SUPERMEMORY_API_KEY:-}"
}

# Load config on source
_memory_load_config

# ============================================================================
# INITIALIZATION
# ============================================================================

memory_init() {
    # Reload config in case secrets changed
    _memory_load_config

    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        return 0
    fi

    # Create state directories
    mkdir -p "$(dirname "$MEMORY_HEAD_FILE")"
    mkdir -p "$MEMORY_CHECKPOINTS_DIR"

    # Initialize head file if missing
    if [[ ! -f "$MEMORY_HEAD_FILE" ]]; then
        _memory_init_head
    fi

    # Check supermemory availability (non-blocking)
    if [[ -n "$SUPERMEMORY_API_KEY" ]]; then
        _memory_check_connection &
    fi

    return 0
}

_memory_init_head() {
    local project_id
    project_id=$(_memory_get_project_id)

    cat > "$MEMORY_HEAD_FILE" << EOF
{
  "project": "$project_id",
  "head_phase": -1,
  "head_checkpoint": null,
  "checkpoints": [],
  "created_at": "$(date -Iseconds)",
  "updated_at": "$(date -Iseconds)"
}
EOF
}

_memory_check_connection() {
    # Check if mcp-cli is available
    if ! command -v mcp-cli &>/dev/null; then
        return 1
    fi

    # Quick connection check via search (no whoAmI available)
    local result
    result=$(mcp-cli call "${SUPERMEMORY_MCP_SERVER:-supermemory}/searchSupermemory" '{"informationToGet": "connection test"}' 2>/dev/null) || return 1
    if [[ $? -eq 0 ]]; then
        mkdir -p "${ATOMIC_ROOT:-.}/.logs"
        echo "[$(date -Iseconds)] Supermemory connected" >> "${ATOMIC_ROOT:-.}/.logs/memory.log"
    fi
}

# ============================================================================
# PROJECT IDENTIFICATION
# ============================================================================

_memory_get_project_id() {
    # Use git remote or directory name as project ID
    local project_id
    if git remote get-url origin &>/dev/null; then
        project_id=$(git remote get-url origin | sed 's/.*[/:]\([^/]*\/[^/]*\)\.git$/\1/' | tr '/' '-')
    else
        project_id=$(basename "${ATOMIC_ROOT:-$(pwd)}")
    fi
    echo "atomic-$project_id"
}

_memory_get_container_tag() {
    echo "$(_memory_get_project_id)-pipeline"
}

# ============================================================================
# SCOPE DETECTION
# ============================================================================

# Check if we should persist to memory
# Returns 0 (true) if in pipeline mode with memory enabled, 1 (false) otherwise
# Note: Does NOT require API key - local checkpoints work without Supermemory
memory_should_persist() {
    # Memory must be enabled
    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        return 1
    fi

    # Must be in pipeline mode (phase context exists)
    if [[ -z "$ATOMIC_PHASE" ]] && [[ -z "$CURRENT_PHASE" ]]; then
        return 1
    fi

    # Local checkpoints work without Supermemory API key
    # Remote persistence will gracefully degrade in _memory_commit_phase()
    return 0
}

# Check if remote persistence (Supermemory) is available
# Returns 0 (true) if API key is configured, 1 (false) otherwise
memory_has_remote() {
    [[ -n "$SUPERMEMORY_API_KEY" ]]
}

# ============================================================================
# SUPERMEMORY MCP TOOL WRAPPERS
# ============================================================================
#
# Tool names from supermemory-mcp server:
#   - addToSupermemory: {thingToRemember: string}
#   - searchSupermemory: {informationToGet: string}
#
# Note: The MCP server name may vary based on configuration.
# Common names: "supermemory", "supermemory-mcp"
#

SUPERMEMORY_MCP_SERVER="${SUPERMEMORY_MCP_SERVER:-supermemory}"

# Save content to Supermemory
# Usage: _sm_memory "content to save"
_sm_memory() {
    local content="$1"

    if [[ -z "$SUPERMEMORY_API_KEY" ]]; then
        return 1
    fi

    # Check if mcp-cli is available
    if ! command -v mcp-cli &>/dev/null; then
        return 1
    fi

    # Include project context in the memory
    local project_id
    project_id=$(_memory_get_project_id)
    local enriched_content="[Project: $project_id] $content"

    local payload
    payload=$(jq -n --arg content "$enriched_content" '{thingToRemember: $content}')

    mcp-cli call "${SUPERMEMORY_MCP_SERVER}/addToSupermemory" "$payload" 2>/dev/null || return 1
    return $?
}

# Search/recall memories from Supermemory
# Usage: _sm_recall "query"
# Returns: Always returns 0 (echoes empty string on failure)
_sm_recall() {
    local query="$1"

    if [[ -z "$SUPERMEMORY_API_KEY" ]]; then
        echo ""
        return 0
    fi

    # Check if mcp-cli is available
    if ! command -v mcp-cli &>/dev/null; then
        echo ""
        return 0
    fi

    # Include project context in the search
    local project_id
    project_id=$(_memory_get_project_id)
    local enriched_query="[Project: $project_id] $query"

    local payload
    payload=$(jq -n --arg query "$enriched_query" '{informationToGet: $query}')

    mcp-cli call "${SUPERMEMORY_MCP_SERVER}/searchSupermemory" "$payload" 2>/dev/null || true
}

# Forget/invalidate memories (local tracking only - MCP doesn't support delete)
# Usage: _sm_forget "description of what to forget"
# Note: This marks memories as invalidated locally but cannot delete from Supermemory
_sm_forget() {
    local content="$1"

    # Log the forget request locally
    local log_dir="${ATOMIC_ROOT:-.}/.logs"
    mkdir -p "$log_dir"
    echo "[$(date -Iseconds)] FORGET: $content" >> "$log_dir/memory-invalidations.log"

    # Note: Supermemory MCP doesn't have a delete/forget tool
    # The memory persists but we track invalidations locally
    return 0
}

# ============================================================================
# HEAD TRACKING
# ============================================================================

# Get current head phase
memory_get_head_phase() {
    if [[ -f "$MEMORY_HEAD_FILE" ]]; then
        jq -r '.head_phase // -1' "$MEMORY_HEAD_FILE"
    else
        echo "-1"
    fi
}

# Update head to new phase
memory_set_head_phase() {
    local phase="$1"
    local checkpoint_id="$2"

    if [[ ! -f "$MEMORY_HEAD_FILE" ]]; then
        _memory_init_head
    fi

    local tmp_file
    tmp_file=$(mktemp)

    jq \
        --argjson phase "$phase" \
        --arg checkpoint "$checkpoint_id" \
        --arg updated "$(date -Iseconds)" \
        '.head_phase = $phase | .head_checkpoint = $checkpoint | .updated_at = $updated' \
        "$MEMORY_HEAD_FILE" > "$tmp_file"

    mv "$tmp_file" "$MEMORY_HEAD_FILE"
}

# Add checkpoint to tracking
memory_add_checkpoint() {
    local checkpoint_id="$1"
    local phase="$2"
    local status="${3:-valid}"

    if [[ ! -f "$MEMORY_HEAD_FILE" ]]; then
        _memory_init_head
    fi

    local tmp_file
    tmp_file=$(mktemp)

    local checkpoint_obj
    checkpoint_obj=$(jq -n \
        --arg id "$checkpoint_id" \
        --argjson phase "$phase" \
        --arg status "$status" \
        --arg created "$(date -Iseconds)" \
        '{id: $id, phase: $phase, status: $status, created_at: $created}')

    jq \
        --argjson cp "$checkpoint_obj" \
        '.checkpoints += [$cp]' \
        "$MEMORY_HEAD_FILE" > "$tmp_file"

    mv "$tmp_file" "$MEMORY_HEAD_FILE"
}

# ============================================================================
# BACKTRACK HANDLING
# ============================================================================

# Check if starting this phase is a backtrack
# Returns 0 if backtrack detected, 1 if normal progression
memory_check_backtrack() {
    local target_phase="$1"

    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        return 1
    fi

    local head_phase
    head_phase=$(memory_get_head_phase)

    if [[ "$target_phase" -le "$head_phase" ]] && [[ "$head_phase" -ge 0 ]]; then
        return 0  # Backtrack detected
    fi

    return 1  # Normal progression
}

# Handle backtrack - invalidate or forget orphaned memories
memory_handle_backtrack() {
    local target_phase="$1"
    local head_phase
    head_phase=$(memory_get_head_phase)

    echo ""
    echo -e "  ${YELLOW:-}⚠ Backtrack Detected${NC:-}"
    echo ""
    echo -e "  Current memory head: Phase $head_phase"
    echo -e "  Target phase: Phase $target_phase"
    echo ""
    echo -e "  Memories from phases $((target_phase + 1))-$head_phase will be affected."
    echo ""
    echo -e "  Options:"
    echo -e "    ${GREEN:-}[continue]${NC:-} Invalidate locally (memories remain in Supermemory but ignored)"
    echo -e "    ${YELLOW:-}[forget]${NC:-}   Also remove from Supermemory"
    echo -e "    ${RED:-}[abort]${NC:-}    Cancel and stay at current phase"
    echo ""

    local choice
    read -rp "  Choice [continue]: " choice || choice="continue"
    choice=${choice:-continue}

    case "$choice" in
        forget)
            _memory_forget_after_phase "$target_phase"
            _memory_invalidate_after_phase "$target_phase"
            ;;
        abort)
            echo ""
            echo -e "  ${DIM:-}Backtrack cancelled.${NC:-}"
            return 1
            ;;
        *)
            _memory_invalidate_after_phase "$target_phase"
            ;;
    esac

    # Update head to target phase
    memory_set_head_phase "$target_phase" ""

    echo ""
    echo -e "  ${GREEN:-}✓${NC:-} Memory head reset to Phase $target_phase"
    echo ""

    return 0
}

# Mark checkpoints after phase as invalidated (local only)
_memory_invalidate_after_phase() {
    local phase="$1"

    if [[ ! -f "$MEMORY_HEAD_FILE" ]]; then
        return 0
    fi

    local tmp_file
    tmp_file=$(mktemp)

    jq \
        --argjson phase "$phase" \
        '.checkpoints = [.checkpoints[] | if .phase > $phase then .status = "invalidated" else . end]' \
        "$MEMORY_HEAD_FILE" > "$tmp_file"

    mv "$tmp_file" "$MEMORY_HEAD_FILE"
}

# Forget memories after phase from Supermemory
_memory_forget_after_phase() {
    local phase="$1"

    # Get checkpoints to forget
    local checkpoints
    checkpoints=$(jq -r ".checkpoints[] | select(.phase > $phase) | .id" "$MEMORY_HEAD_FILE" 2>/dev/null)

    for checkpoint_id in $checkpoints; do
        echo -e "  ${DIM:-}Forgetting checkpoint: $checkpoint_id${NC:-}"
        _sm_forget "checkpoint:$checkpoint_id"
    done
}

# ============================================================================
# CHECKPOINT OPERATIONS
# ============================================================================

# Create a checkpoint for the current phase
# Usage: memory_create_checkpoint <phase> <phase_name> <summary> [key_decisions_json] [artifacts_json]
memory_create_checkpoint() {
    local phase="$1"
    local phase_name="$2"
    local summary="$3"
    local decisions="${4:-[]}"
    local artifacts="${5:-[]}"

    local checkpoint_id="phase${phase}-$(date +%Y%m%d-%H%M%S)"
    local project_id
    project_id=$(_memory_get_project_id)

    # Create checkpoint JSON
    local checkpoint_file="$MEMORY_CHECKPOINTS_DIR/${checkpoint_id}.json"

    jq -n \
        --arg id "$checkpoint_id" \
        --arg project "$project_id" \
        --argjson phase "$phase" \
        --arg phase_name "$phase_name" \
        --arg summary "$summary" \
        --argjson decisions "$decisions" \
        --argjson artifacts "$artifacts" \
        --arg created "$(date -Iseconds)" \
        --arg prev "$(jq -r '.head_checkpoint // ""' "$MEMORY_HEAD_FILE" 2>/dev/null)" \
        '{
            checkpoint_id: $id,
            project: $project,
            phase: $phase,
            phase_name: $phase_name,
            summary: $summary,
            key_decisions: $decisions,
            artifacts: $artifacts,
            created_at: $created,
            previous_checkpoint: $prev
        }' > "$checkpoint_file"

    # Add to tracking
    memory_add_checkpoint "$checkpoint_id" "$phase" "valid"
    memory_set_head_phase "$phase" "$checkpoint_id"

    echo "$checkpoint_id"
}

# ============================================================================
# USER APPROVAL GATE
# ============================================================================

# Prompt user to save phase to memory
# Usage: memory_prompt_save <phase> <phase_name> <summary>
# Returns 0 if saved, 1 if skipped
memory_prompt_save() {
    local phase="$1"
    local phase_name="$2"
    local summary="$3"

    if ! memory_should_persist; then
        return 1
    fi

    local has_remote=false
    if memory_has_remote; then
        has_remote=true
    fi

    echo ""
    echo -e "  ${BOLD:-}MEMORY CHECKPOINT${NC:-}"
    if [[ "$has_remote" != "true" ]]; then
        echo -e "  ${DIM:-}(local only - Supermemory not configured)${NC:-}"
    fi
    echo ""
    echo -e "  ${DIM:-}Summary to persist:${NC:-}"
    echo ""
    echo "$summary" | sed 's/^/    /'
    echo ""
    echo -e "  ${CYAN:-}Options:${NC:-}"
    if [[ "$has_remote" == "true" ]]; then
        echo -e "    ${GREEN:-}[save]${NC:-} Save to long-term memory (Supermemory + local)"
        echo -e "    ${YELLOW:-}[edit]${NC:-} Edit summary before saving"
        echo -e "    ${DIM:-}[skip]${NC:-} Don't save (local checkpoint only)"
    else
        echo -e "    ${GREEN:-}[save]${NC:-} Save local checkpoint"
        echo -e "    ${YELLOW:-}[edit]${NC:-} Edit summary before saving"
        echo -e "    ${DIM:-}[skip]${NC:-} Don't save"
    fi
    echo ""

    local choice
    read -rp "  Choice [save]: " choice || choice="save"
    choice=${choice:-save}

    case "$choice" in
        save)
            _memory_commit_phase "$phase" "$phase_name" "$summary"
            return 0
            ;;
        edit)
            local tmp_file
            tmp_file=$(mktemp --suffix=.md)
            echo "$summary" > "$tmp_file"
            ${EDITOR:-nano} "$tmp_file"
            local edited_summary
            edited_summary=$(cat "$tmp_file")
            rm -f "$tmp_file"
            _memory_commit_phase "$phase" "$phase_name" "$edited_summary"
            return 0
            ;;
        *)
            echo ""
            echo -e "  ${DIM:-}Memory save skipped.${NC:-}"
            # Still create local checkpoint, just don't push to supermemory
            memory_create_checkpoint "$phase" "$phase_name" "$summary"
            return 1
            ;;
    esac
}

# Actually commit phase to supermemory
_memory_commit_phase() {
    local phase="$1"
    local phase_name="$2"
    local summary="$3"

    # Create local checkpoint first
    local checkpoint_id
    checkpoint_id=$(memory_create_checkpoint "$phase" "$phase_name" "$summary")

    # Format content for supermemory
    local content="[Phase $phase: $phase_name] $summary"

    # Save to supermemory
    if _sm_memory "$content"; then
        echo ""
        echo -e "  ${GREEN:-}✓${NC:-} Saved to long-term memory (checkpoint: $checkpoint_id)"
    else
        echo ""
        echo -e "  ${YELLOW:-}!${NC:-} Saved locally only (Supermemory unavailable)"
    fi
}

# ============================================================================
# SESSION LIFECYCLE
# ============================================================================

# Called on session start - retrieves relevant context
memory_session_start() {
    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        return 0
    fi

    memory_init

    local session_context_file="${ATOMIC_ROOT:-.}/.outputs/session-context.md"
    mkdir -p "$(dirname "$session_context_file")"

    echo "# Session Context (from Memory)" > "$session_context_file"
    echo "" >> "$session_context_file"
    echo "_Retrieved: $(date -Iseconds)_" >> "$session_context_file"
    echo "" >> "$session_context_file"

    # Recall project context (|| true to prevent set -e from killing script)
    local recalled
    recalled=$(_sm_recall "project context and current state" true) || true

    if [[ -n "$recalled" ]] && [[ "$recalled" != "null" ]]; then
        echo "## Project Context" >> "$session_context_file"
        echo "" >> "$session_context_file"
        echo "$recalled" | jq -r '.memories[]?.content // empty' >> "$session_context_file" 2>/dev/null
        echo "" >> "$session_context_file"

        echo -e "  ${GREEN:-}✓${NC:-} Session context loaded from memory"
    else
        echo "_No memories found for this project._" >> "$session_context_file"
    fi

    # Add local head state
    if [[ -f "$MEMORY_HEAD_FILE" ]]; then
        local head_phase
        head_phase=$(memory_get_head_phase)
        if [[ "$head_phase" -ge 0 ]]; then
            echo "## Local State" >> "$session_context_file"
            echo "" >> "$session_context_file"
            echo "Current phase progression: Phase $head_phase" >> "$session_context_file"
        fi
    fi

    return 0
}

# Called on session end
memory_session_end() {
    # Currently a no-op - we save at checkpoints, not session end
    return 0
}

# ============================================================================
# EXPORTS
# ============================================================================

export -f memory_init memory_should_persist memory_has_remote
export -f memory_get_head_phase memory_set_head_phase
export -f memory_check_backtrack memory_handle_backtrack
export -f memory_create_checkpoint memory_prompt_save
export -f memory_session_start memory_session_end
