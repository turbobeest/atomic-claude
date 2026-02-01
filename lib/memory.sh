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
MEMORY_LOCAL_DIR="${ATOMIC_ROOT:-.}/.state/memory"

# Source task memory definitions if not already loaded
if [[ -z "${TASK_MEMORY_RECALL[*]:-}" ]]; then
    _MEMORY_DEFS_PATH="${BASH_SOURCE[0]%/*}/task-memory-defs.sh"
    if [[ -f "$_MEMORY_DEFS_PATH" ]]; then
        source "$_MEMORY_DEFS_PATH"
    fi
fi

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
    if [[ -z "${SUPERMEMORY_API_KEY:-}" ]]; then
        return 1
    fi

    # Quick connection check via search endpoint with empty query
    local response
    response=$(curl -s -X POST "${SUPERMEMORY_API_BASE:-https://api.supermemory.ai}/v3/search" \
        -H "x-supermemory-api-key: $SUPERMEMORY_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"q": "connection test"}' 2>/dev/null)

    # Check if we got a valid response (has results field)
    if echo "$response" | jq -e '.results' &>/dev/null; then
        mkdir -p "${ATOMIC_ROOT:-.}/.logs"
        echo "[$(date -Iseconds)] Supermemory connected" >> "${ATOMIC_ROOT:-.}/.logs/memory.log"
        return 0
    fi
    return 1
}

# ============================================================================
# PROJECT IDENTIFICATION
# ============================================================================

_memory_get_project_id() {
    # Use git remote or directory name as project ID
    # Priority: git remote > ATOMIC_ORCHESTRATOR > parent of ATOMIC-CLAUDE > ATOMIC_ROOT
    local project_id
    local base_dir="${ATOMIC_ORCHESTRATOR:-${ATOMIC_ROOT:-$(pwd)}}"

    # If we're in an ATOMIC-CLAUDE subdirectory, use the parent project name
    if [[ "$(basename "$base_dir")" == "ATOMIC-CLAUDE" ]]; then
        base_dir=$(dirname "$base_dir")
    fi

    # Try git remote from the project directory
    if git -C "$base_dir" remote get-url origin &>/dev/null 2>&1; then
        project_id=$(git -C "$base_dir" remote get-url origin | sed 's/.*[/:]\([^/]*\/[^/]*\)\.git$/\1/' | tr '/' '-')
    else
        project_id=$(basename "$base_dir")
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
    if [[ -z "${ATOMIC_PHASE:-}" ]] && [[ -z "${CURRENT_PHASE:-}" ]]; then
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
# Supermemory REST API endpoints (v3):
#   - POST /v3/documents - Add memory (content field)
#   - POST /v3/search - Search memories (q field)
#   - Auth: x-supermemory-api-key header
#

SUPERMEMORY_API_BASE="${SUPERMEMORY_API_BASE:-https://api.supermemory.ai}"

# Save content to Supermemory
# Usage: _sm_memory "content to save"
_sm_memory() {
    local content="$1"
    local log_file="${ATOMIC_ROOT:-.}/.logs/memory.log"
    mkdir -p "$(dirname "$log_file")"

    echo "[$(date -Iseconds)] [DEBUG] _sm_memory() ENTER" >> "$log_file"
    echo "  [DEBUG] MEMORY_ENABLED=$MEMORY_ENABLED" >> "$log_file"
    echo "  [DEBUG] API_KEY_SET=$([ -n "$SUPERMEMORY_API_KEY" ] && echo 'yes' || echo 'no')" >> "$log_file"

    if [[ -z "$SUPERMEMORY_API_KEY" ]]; then
        echo "[$(date -Iseconds)] SAVE FAILED: No API key" >> "$log_file"
        return 1
    fi

    # Include project context in the memory
    local project_id
    project_id=$(_memory_get_project_id)
    local enriched_content="[Project: $project_id] $content"

    local payload
    payload=$(jq -n --arg content "$enriched_content" '{content: $content}')

    echo "[$(date -Iseconds)] SAVE: Sending to Supermemory..." >> "$log_file"
    echo "  Content: ${content:0:100}..." >> "$log_file"
    echo "  [DEBUG] API_BASE=$SUPERMEMORY_API_BASE" >> "$log_file"

    # Call Supermemory v3 documents API
    local response
    response=$(curl -s -X POST "${SUPERMEMORY_API_BASE}/v3/documents" \
        -H "x-supermemory-api-key: $SUPERMEMORY_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null)

    echo "  [DEBUG] Response: ${response:0:200}" >> "$log_file"

    # Check for success (response has id and status)
    if echo "$response" | jq -e '.id' &>/dev/null; then
        local doc_id=$(echo "$response" | jq -r '.id')
        echo "[$(date -Iseconds)] SAVE SUCCESS: doc_id=$doc_id" >> "$log_file"
        echo "[$(date -Iseconds)] [DEBUG] _sm_memory() EXIT success" >> "$log_file"
        return 0
    fi

    echo "[$(date -Iseconds)] SAVE FAILED: $response" >> "$log_file"
    echo "[$(date -Iseconds)] [DEBUG] _sm_memory() EXIT failed" >> "$log_file"
    return 1
}

# Search/recall memories from Supermemory
# Usage: _sm_recall "query"
# Returns: Always returns 0 (echoes empty string on failure)
_sm_recall() {
    local query="$1"
    local log_file="${ATOMIC_ROOT:-.}/.logs/memory.log"
    mkdir -p "$(dirname "$log_file")"

    echo "[$(date -Iseconds)] [DEBUG] _sm_recall() ENTER" >> "$log_file"
    echo "  [DEBUG] MEMORY_ENABLED=$MEMORY_ENABLED" >> "$log_file"
    echo "  [DEBUG] API_KEY_SET=$([ -n "$SUPERMEMORY_API_KEY" ] && echo 'yes' || echo 'no')" >> "$log_file"

    if [[ -z "$SUPERMEMORY_API_KEY" ]]; then
        echo "[$(date -Iseconds)] RECALL FAILED: No API key" >> "$log_file"
        echo ""
        return 0
    fi

    # Include project context in the search
    local project_id
    project_id=$(_memory_get_project_id)
    local enriched_query="[Project: $project_id] $query"

    local payload
    payload=$(jq -n --arg q "$enriched_query" '{q: $q}')

    echo "[$(date -Iseconds)] RECALL: Searching Supermemory..." >> "$log_file"
    echo "  Query: $query" >> "$log_file"
    echo "  [DEBUG] API_BASE=$SUPERMEMORY_API_BASE" >> "$log_file"

    # Call Supermemory v3 search API
    local response
    response=$(curl -s -X POST "${SUPERMEMORY_API_BASE}/v3/search" \
        -H "x-supermemory-api-key: $SUPERMEMORY_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null)

    echo "  [DEBUG] Response length: ${#response} chars" >> "$log_file"

    # Return the response (or empty on failure)
    if [[ -n "$response" ]] && echo "$response" | jq -e '.results' &>/dev/null; then
        local result_count=$(echo "$response" | jq '.results | length')
        echo "[$(date -Iseconds)] RECALL SUCCESS: $result_count results found" >> "$log_file"
        echo "[$(date -Iseconds)] [DEBUG] _sm_recall() EXIT success" >> "$log_file"
        echo "$response"
    else
        echo "[$(date -Iseconds)] RECALL: No results or error - response: ${response:0:100}" >> "$log_file"
        echo "[$(date -Iseconds)] [DEBUG] _sm_recall() EXIT empty" >> "$log_file"
        echo ""
    fi
    return 0
}

# Delete a document from Supermemory by ID
# Usage: _sm_delete "doc_id"
_sm_delete() {
    local doc_id="$1"
    local log_file="${ATOMIC_ROOT:-.}/.logs/memory.log"
    mkdir -p "$(dirname "$log_file")"

    if [[ -z "$SUPERMEMORY_API_KEY" ]]; then
        echo "[$(date -Iseconds)] DELETE FAILED: No API key" >> "$log_file"
        return 1
    fi

    echo "[$(date -Iseconds)] DELETE: Removing doc_id=$doc_id from Supermemory..." >> "$log_file"

    local response
    response=$(curl -s -X DELETE "${SUPERMEMORY_API_BASE}/v3/documents/$doc_id" \
        -H "x-supermemory-api-key: $SUPERMEMORY_API_KEY" 2>/dev/null)

    # Check for success
    if [[ -z "$response" ]] || echo "$response" | jq -e '.success // .deleted // true' &>/dev/null; then
        echo "[$(date -Iseconds)] DELETE SUCCESS: doc_id=$doc_id" >> "$log_file"
        return 0
    fi

    echo "[$(date -Iseconds)] DELETE FAILED: $response" >> "$log_file"
    return 1
}

# Search and delete memories matching a query
# Usage: _sm_forget_matching "query"
_sm_forget_matching() {
    local query="$1"
    local log_file="${ATOMIC_ROOT:-.}/.logs/memory.log"
    mkdir -p "$(dirname "$log_file")"

    if [[ -z "$SUPERMEMORY_API_KEY" ]]; then
        echo "[$(date -Iseconds)] FORGET FAILED: No API key" >> "$log_file"
        return 1
    fi

    echo "[$(date -Iseconds)] FORGET: Searching for memories matching: $query" >> "$log_file"

    # Search for matching memories - use broader query without brackets
    local project_id
    project_id=$(_memory_get_project_id)
    # Simpler query - just project + search term
    local search_query="$project_id $query"

    local payload
    payload=$(jq -n --arg q "$search_query" '{q: $q}')

    echo "[$(date -Iseconds)]   Search query: $search_query" >> "$log_file"

    local response
    response=$(curl -s -X POST "${SUPERMEMORY_API_BASE}/v3/search" \
        -H "x-supermemory-api-key: $SUPERMEMORY_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null)

    local result_count
    result_count=$(echo "$response" | jq '.results | length' 2>/dev/null || echo "0")
    echo "[$(date -Iseconds)]   Search returned $result_count results" >> "$log_file"

    # Extract doc IDs and delete each - API returns 'documentId' not 'id'
    local doc_ids deleted_count=0
    doc_ids=$(echo "$response" | jq -r '.results[]?.documentId // empty' 2>/dev/null)

    for doc_id in $doc_ids; do
        if [[ -n "$doc_id" ]]; then
            echo "[$(date -Iseconds)]   Deleting doc_id: $doc_id" >> "$log_file"
            if _sm_delete "$doc_id"; then
                deleted_count=$((deleted_count + 1))
            fi
        fi
    done

    echo "[$(date -Iseconds)] FORGET COMPLETE: Deleted $deleted_count memories" >> "$log_file"
    echo "  Deleted $deleted_count memories from Supermemory"
    return 0
}

# Legacy wrapper for compatibility
_sm_forget() {
    local content="$1"
    _sm_forget_matching "$content"
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

    # Update memory head to target phase
    memory_set_head_phase "$target_phase" ""
    echo ""
    echo -e "  ${GREEN:-}✓${NC:-} Memory head reset to Phase $target_phase"

    # CRITICAL: Also reset task state so tasks actually re-run
    # Without this, tasks would be skipped as "already complete"
    local log_file="${ATOMIC_ROOT:-.}/.logs/memory.log"
    echo "[$(date -Iseconds)] [DEBUG] About to check for _task_state_backtrack_reset" >> "$log_file"
    echo "[$(date -Iseconds)] [DEBUG] type -t result: $(type -t _task_state_backtrack_reset 2>&1 || echo 'NOT FOUND')" >> "$log_file"

    if type -t _task_state_backtrack_reset &>/dev/null; then
        echo "[$(date -Iseconds)] [DEBUG] Function found, calling _task_state_backtrack_reset $target_phase" >> "$log_file"
        _task_state_backtrack_reset "$target_phase"
    else
        echo "[$(date -Iseconds)] [DEBUG] Function NOT found!" >> "$log_file"
        echo -e "  ${YELLOW:-}!${NC:-} Warning: Could not reset task state (function not found)"
    fi
    echo ""

    return 0
}

# Mark checkpoints after phase as invalidated AND clear local memory files
_memory_invalidate_after_phase() {
    local phase="$1"
    local memory_dir="${ATOMIC_ROOT:-.}/.state/memory"

    # Invalidate checkpoints in head file
    if [[ -f "$MEMORY_HEAD_FILE" ]]; then
        local tmp_file
        tmp_file=$(mktemp)

        jq \
            --argjson phase "$phase" \
            '.checkpoints = [.checkpoints[] | if .phase > $phase then .status = "invalidated" else . end]' \
            "$MEMORY_HEAD_FILE" > "$tmp_file"

        mv "$tmp_file" "$MEMORY_HEAD_FILE"
    fi

    # Clear local memory files for target phase and later
    if [[ -d "$memory_dir" ]]; then
        local phase_num
        for phase_num in $(seq "$phase" 9); do
            local phase_memory_dir="$memory_dir/phase-${phase_num}"
            if [[ -d "$phase_memory_dir" ]]; then
                rm -rf "$phase_memory_dir"
                echo -e "  ${DIM:-}Cleared local memory: phase-${phase_num}${NC:-}"
            fi
        done
    fi

    # Clear debug log entries for invalidated phases
    local debug_file="${ATOMIC_ROOT:-.}/.logs/memory-debug.jsonl"
    if [[ -f "$debug_file" ]]; then
        local tmp_debug
        tmp_debug=$(mktemp)
        # Keep only entries for phases before target phase
        while IFS= read -r line; do
            local entry_phase
            entry_phase=$(echo "$line" | jq -r '.phase // ""' 2>/dev/null)
            # Extract phase number (e.g., "0-setup" -> 0)
            local entry_phase_num="${entry_phase%%-*}"
            if [[ "$entry_phase_num" =~ ^[0-9]+$ ]] && [[ "$entry_phase_num" -lt "$phase" ]]; then
                echo "$line" >> "$tmp_debug"
            fi
        done < "$debug_file"
        mv "$tmp_debug" "$debug_file"
        echo -e "  ${DIM:-}Cleared debug log for phases >= ${phase}${NC:-}"
    fi
}

# Delete ALL memories for this project from Supermemory
_memory_forget_all_project() {
    local log_file="${ATOMIC_ROOT:-.}/.logs/memory.log"
    local project_id
    project_id=$(_memory_get_project_id)

    echo "[$(date -Iseconds)] FORGET_ALL: Deleting ALL memories for project $project_id" >> "$log_file"
    echo -e "  ${YELLOW:-}Deleting all project memories from Supermemory...${NC:-}"

    # Search broadly for the project
    local payload response
    payload=$(jq -n --arg q "$project_id" '{q: $q}')

    response=$(curl -s -X POST "${SUPERMEMORY_API_BASE}/v3/search" \
        -H "x-supermemory-api-key: $SUPERMEMORY_API_KEY" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null)

    local result_count deleted_count=0
    result_count=$(echo "$response" | jq '.results | length' 2>/dev/null || echo "0")
    echo "[$(date -Iseconds)]   Found $result_count memories to delete" >> "$log_file"

    # DEBUG: Log the response structure
    echo "[$(date -Iseconds)]   [DEBUG] Response keys: $(echo "$response" | jq -r 'keys | join(", ")' 2>/dev/null)" >> "$log_file"
    echo "[$(date -Iseconds)]   [DEBUG] First result keys: $(echo "$response" | jq -r '.results[0] | keys | join(", ")' 2>/dev/null)" >> "$log_file"
    echo "[$(date -Iseconds)]   [DEBUG] First result: $(echo "$response" | jq -c '.results[0]' 2>/dev/null)" >> "$log_file"

    # API returns 'documentId' - prioritize that field
    local doc_ids
    doc_ids=$(echo "$response" | jq -r '.results[]?.documentId // empty' 2>/dev/null)

    echo "[$(date -Iseconds)]   [DEBUG] Extracted doc_ids: $doc_ids" >> "$log_file"

    for doc_id in $doc_ids; do
        if [[ -n "$doc_id" && "$doc_id" != "null" ]]; then
            echo "[$(date -Iseconds)]   [DEBUG] Attempting to delete: $doc_id" >> "$log_file"
            if _sm_delete "$doc_id"; then
                deleted_count=$((deleted_count + 1))
            fi
        fi
    done

    echo "[$(date -Iseconds)] FORGET_ALL COMPLETE: Deleted $deleted_count of $result_count memories" >> "$log_file"
    echo -e "  ${GREEN:-}✓${NC:-} Deleted $deleted_count memories from Supermemory"
    return 0
}

# Forget memories from target phase onward from Supermemory
# When user chooses "forget" during backtrack, they want a fresh start
_memory_forget_after_phase() {
    local target_phase="$1"
    local log_file="${ATOMIC_ROOT:-.}/.logs/memory.log"

    # If backtracking to Phase 0, just delete everything (fresh start)
    if [[ "$target_phase" -eq 0 ]]; then
        _memory_forget_all_project
        return $?
    fi

    echo "[$(date -Iseconds)] FORGET_AFTER_PHASE: Deleting memories from phase $target_phase onward" >> "$log_file"

    # Phase name mapping for search (memories use these names)
    local -A phase_names=(
        [0]="Setup"
        [1]="Discovery"
        [2]="PRD"
        [3]="Tasking"
        [4]="Specification"
        [5]="Implementation"
        [6]="Code Review"
        [7]="Integration"
        [8]="Deployment"
        [9]="Release"
    )

    # Delete memories for target phase AND all phases after
    local phase_num phase_name
    for phase_num in $(seq $target_phase 9); do
        phase_name="${phase_names[$phase_num]:-Phase$phase_num}"

        # Search for phase closeout memories: "[Phase N: Name]"
        echo -e "  ${DIM:-}Searching for Phase $phase_num ($phase_name) memories...${NC:-}"
        _sm_forget_matching "Phase $phase_num"

        # Search for task-level memories: "[PhaseName]"
        _sm_forget_matching "$phase_name task"
    done

    echo "[$(date -Iseconds)] FORGET_AFTER_PHASE: Complete" >> "$log_file"
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
# Uses DUAL-WRITE: Always save locally, also save to Supermemory if available
_memory_commit_phase() {
    local phase="$1"
    local phase_name="$2"
    local summary="$3"

    # Create local checkpoint first
    local checkpoint_id
    checkpoint_id=$(memory_create_checkpoint "$phase" "$phase_name" "$summary")

    # ALWAYS save closeout to local file storage
    _memory_save_closeout "$phase" "$phase_name" "$summary"
    _memory_log "_memory_commit_phase" "Saved closeout locally for Phase $phase"

    # Format content for supermemory
    local content="[Phase $phase: $phase_name] $summary"

    # Also save to supermemory if available
    if [[ -n "$SUPERMEMORY_API_KEY" ]]; then
        if _sm_memory "$content"; then
            echo ""
            echo -e "  ${GREEN:-}✓${NC:-} Saved to long-term memory (checkpoint: $checkpoint_id)"
            _memory_log "_memory_commit_phase" "Saved to Supermemory"
        else
            echo ""
            echo -e "  ${YELLOW:-}!${NC:-} Saved locally only (Supermemory unavailable)"
            _memory_log "_memory_commit_phase" "Supermemory save failed, local backup exists"
        fi
    else
        echo ""
        echo -e "  ${GREEN:-}✓${NC:-} Saved to local memory (checkpoint: $checkpoint_id)"
        _memory_log "_memory_commit_phase" "Supermemory not configured, saved locally only"
    fi
}

# ============================================================================
# LOCAL MEMORY STORAGE (Graceful Degradation)
# ============================================================================
# Dual-write strategy: Always write locally, also write to Supermemory if available
# Dual-read strategy: Read local first (fast), then Supermemory (cross-session)

# Structured JSON logging for memory operations (parseable by web dashboard)
# Usage: _memory_log "source" "message"
_memory_log() {
    local source="$1"
    local message="$2"
    local log_file="${ATOMIC_ROOT:-.}/.logs/memory.log"
    mkdir -p "$(dirname "$log_file")"

    # JSON-formatted for easy parsing by web UI
    echo "{\"ts\":\"$(date -Iseconds)\",\"src\":\"$source\",\"msg\":\"$message\"}" >> "$log_file"
}

# Enhanced debug logging for web dashboard - richer structured data
# Usage: _memory_debug "operation" "status" "details_json"
# Operations: task_start, task_end, recall_local, recall_remote, inject, save_local, save_remote
# Status: start, success, fail, skip
_memory_debug() {
    local operation="$1"
    local status="$2"
    local details="${3:-{\}}"
    local debug_file="${ATOMIC_ROOT:-.}/.logs/memory-debug.jsonl"
    mkdir -p "$(dirname "$debug_file")"

    # Get current task context
    local phase="${CURRENT_PHASE:-unknown}"
    local task="${CURRENT_TASK_ID:-unknown}"
    local task_name="${CURRENT_TASK_NAME:-unknown}"

    # Build JSON log entry
    local entry
    entry=$(jq -nc \
        --arg ts "$(date -Iseconds)" \
        --arg op "$operation" \
        --arg status "$status" \
        --arg phase "$phase" \
        --arg task "$task" \
        --arg task_name "$task_name" \
        --argjson details "$details" \
        '{
            timestamp: $ts,
            operation: $op,
            status: $status,
            phase: $phase,
            task_id: $task,
            task_name: $task_name,
            details: $details
        }' 2>/dev/null) || entry="{\"timestamp\":\"$(date -Iseconds)\",\"operation\":\"$operation\",\"status\":\"$status\",\"error\":\"json_build_failed\"}"

    echo "$entry" >> "$debug_file"
}

# Helper to truncate content for logging (first 200 chars)
_memory_truncate() {
    local content="$1"
    local max_len="${2:-200}"
    if [[ ${#content} -gt $max_len ]]; then
        echo "${content:0:$max_len}..."
    else
        echo "$content"
    fi
}

# Ensure local memory directory structure exists
_memory_ensure_local_dirs() {
    local phase_num="$1"
    local phase_dir="${MEMORY_LOCAL_DIR}/phase-${phase_num}"
    mkdir -p "$phase_dir"
    echo "$phase_dir"
}

# Save content to LOCAL file storage
# Usage: _memory_save_local <phase_num> <task_id> <save_type> <content>
# Returns: Path to saved file
_memory_save_local() {
    local phase_num="$1"
    local task_id="$2"
    local save_type="$3"
    local content="$4"

    local phase_dir
    phase_dir=$(_memory_ensure_local_dirs "$phase_num")
    local task_file="$phase_dir/task-${task_id}-${save_type}.md"

    cat > "$task_file" << EOF
# Task ${task_id}: ${save_type}
_Saved: $(date -Iseconds)_

$content
EOF

    _memory_log "_memory_save_local" "Wrote ${#content} chars to $task_file"
    echo "$task_file"
}

# Recall content from LOCAL file storage
# Usage: _memory_recall_local <recall_query> <phase_num>
# Returns: Concatenated content from relevant local memory files
_memory_recall_local() {
    local recall_query="$1"
    local current_phase="${2:-}"

    local results=""

    # If memory directory doesn't exist, return empty
    if [[ ! -d "$MEMORY_LOCAL_DIR" ]]; then
        return 0
    fi

    # Strategy: Read files based on query keywords
    # 1. If query mentions "Phase N", read that phase's files
    # 2. If query mentions "closeout", prioritize closeout files
    # 3. Otherwise, grep for relevant keywords

    # Check for phase references in query (e.g., "Phase 0", "Phase 1")
    local phase_match
    if phase_match=$(echo "$recall_query" | grep -oE 'Phase [0-9]' | head -1); then
        local phase_num="${phase_match#Phase }"
        local phase_dir="$MEMORY_LOCAL_DIR/phase-$phase_num"
        if [[ -d "$phase_dir" ]]; then
            # Read all files from that phase, prioritizing closeout
            if [[ -f "$phase_dir/closeout.md" ]]; then
                results+="## Phase $phase_num Closeout\n\n"
                results+="$(cat "$phase_dir/closeout.md")\n\n"
            fi
            for f in "$phase_dir"/task-*.md; do
                if [[ -f "$f" ]]; then
                    results+="$(cat "$f")\n\n"
                fi
            done
        fi
    fi

    # If query mentions specific concepts, grep for them in all files
    if [[ -z "$results" && -n "$recall_query" ]]; then
        # Extract key terms from query (split on spaces, take meaningful words)
        local keywords
        keywords=$(echo "$recall_query" | tr ' ' '\n' | grep -E '^[a-zA-Z]{3,}$' | head -5)

        for keyword in $keywords; do
            local matches
            matches=$(grep -rli "$keyword" "$MEMORY_LOCAL_DIR"/*.md "$MEMORY_LOCAL_DIR"/*/*.md 2>/dev/null | head -3) || true
            for match_file in $matches; do
                if [[ -f "$match_file" ]]; then
                    results+="## From: $(basename "$match_file")\n\n"
                    results+="$(cat "$match_file")\n\n"
                fi
            done
        done
    fi

    # If still no results, try to read the most recent phase's closeout
    if [[ -z "$results" && -n "$current_phase" && "$current_phase" -gt 0 ]]; then
        local prev_phase=$((current_phase - 1))
        local prev_closeout="$MEMORY_LOCAL_DIR/phase-$prev_phase/closeout.md"
        if [[ -f "$prev_closeout" ]]; then
            results+="## Previous Phase Closeout (Phase $prev_phase)\n\n"
            results+="$(cat "$prev_closeout")\n\n"
        fi
    fi

    echo -e "$results"
}

# Save phase closeout to local storage
# Usage: _memory_save_closeout <phase_num> <phase_name> <summary>
_memory_save_closeout() {
    local phase_num="$1"
    local phase_name="$2"
    local summary="$3"

    local phase_dir
    phase_dir=$(_memory_ensure_local_dirs "$phase_num")
    local closeout_file="$phase_dir/closeout.md"

    cat > "$closeout_file" << EOF
# Phase $phase_num: $phase_name - Closeout
_Saved: $(date -Iseconds)_

$summary
EOF

    _memory_log "_memory_save_closeout" "Saved closeout for Phase $phase_num to $closeout_file"
}

# ============================================================================
# CONTENT EXTRACTION FUNCTIONS
# ============================================================================
# Extract meaningful content from output files based on save type

_memory_extract_content() {
    local save_type="$1"
    local phase_num="$2"
    local task_id="$3"

    local output_dir="${ATOMIC_OUTPUT_DIR:-${ATOMIC_ROOT:-.}/.outputs}"
    local content=""

    case "$save_type" in
        mode_selection)
            # Extract setup mode from environment or state
            content="SETUP_MODE: ${SETUP_MODE:-unknown}"
            ;;

        extracted_config)
            local config_file="$output_dir/0-setup/extracted-config.json"
            if [[ -f "$config_file" ]]; then
                content=$(jq -r '
                    "PROJECT: " + (.project.name // "unknown") + " (" + (.project.type // "unknown") + ")\n" +
                    "DESCRIPTION: " + (.project.description // "") + "\n" +
                    "GOAL: " + (.project.primary_goal // "") + "\n" +
                    "LLM: " + (.llm.primary_model // "claude-opus") + " / " + (.llm.fast_model // "claude-haiku") + "\n" +
                    "PROVIDER: " + (.llm.primary_provider // "anthropic") + "\n" +
                    "CONSTRAINTS: " + ((.constraints.technical // []) | join("; "))
                ' "$config_file" 2>/dev/null) || content="Config extraction failed"
            fi
            ;;

        config_approval)
            local config_file="$output_dir/0-setup/project-config.json"
            if [[ -f "$config_file" ]]; then
                content="Config approved. Project: $(jq -r '.project.name // .extracted.project.name // "unknown"' "$config_file" 2>/dev/null)"
            fi
            ;;

        api_providers)
            local secrets_file="$output_dir/0-setup/secrets.json"
            if [[ -f "$secrets_file" ]]; then
                local providers=""
                [[ "$(jq -r '.max_enabled // false' "$secrets_file" 2>/dev/null)" == "true" ]] && providers+="claude-max "
                [[ -n "$(jq -r '.anthropic_api_key // empty' "$secrets_file" 2>/dev/null)" ]] && providers+="anthropic-api "
                [[ -n "$(jq -r '.supermemory_api_key // empty' "$secrets_file" 2>/dev/null)" ]] && providers+="supermemory "
                [[ "$(jq -r '.ollama_hosts | length' "$secrets_file" 2>/dev/null)" -gt 0 ]] && providers+="ollama "
                content="PROVIDERS CONFIGURED: ${providers:-none}"
            fi
            ;;

        material_manifest)
            local manifest="$output_dir/0-setup/material-manifest.json"
            if [[ -f "$manifest" ]]; then
                content=$(jq -r '
                    "FILES: " + (.summary.total_files // 0 | tostring) + "\n" +
                    "LANGUAGES: " + ((.summary.languages // []) | join(", ")) + "\n" +
                    "LOC: " + (.summary.total_loc // 0 | tostring)
                ' "$manifest" 2>/dev/null) || content="Manifest extraction failed"
            fi
            ;;

        reference_materials)
            content="Reference materials linked"
            ;;

        environment_tools)
            local env_file="$output_dir/0-setup/env-validation.json"
            if [[ -f "$env_file" ]]; then
                local passed=$(jq '.summary.passed // 0' "$env_file" 2>/dev/null)
                local failed=$(jq '.summary.failed // 0' "$env_file" 2>/dev/null)
                content="TOOLS VALIDATED: $passed passed, $failed failed"
            fi
            ;;

        repository_config)
            local config_file="$output_dir/0-setup/project-config.json"
            if [[ -f "$config_file" ]]; then
                local agents_path=$(jq -r '.repositories.agents.path // "embedded"' "$config_file" 2>/dev/null)
                content="AGENTS: $agents_path"
            fi
            ;;

        corpus_analysis)
            local corpus_file="$output_dir/1-discovery/corpus.json"
            if [[ -f "$corpus_file" ]]; then
                local count=$(jq '.materials | length' "$corpus_file" 2>/dev/null || echo 0)
                content="CORPUS: $count materials collected"
                local analysis_file="$output_dir/1-discovery/corpus-analysis.md"
                if [[ -f "$analysis_file" ]]; then
                    content+="\n\n$(head -50 "$analysis_file")"
                fi
            fi
            ;;

        dialogue_synthesis)
            local dialogue_file="$output_dir/1-discovery/dialogue.json"
            if [[ -f "$dialogue_file" ]]; then
                content=$(jq -r '
                    "VISION: " + (.synthesis.vision // .vision // "") + "\n" +
                    "IMPACT: " + (.synthesis.impact // .impact // "") + "\n" +
                    "AUDIENCE: " + (.synthesis.audience // .audience // "") + "\n" +
                    "CONSTRAINTS: " + ((.synthesis.constraints // .constraints // []) | if type == "array" then join("; ") else . end)
                ' "$dialogue_file" 2>/dev/null) || content="Dialogue extraction failed"
            fi
            ;;

        selected_agents)
            # Try phase-specific patterns
            for pattern in "$output_dir/${phase_num}-"*/selected-agents.json; do
                if [[ -f "$pattern" ]]; then
                    local agent_count=$(jq '.selected | length' "$pattern" 2>/dev/null || echo 0)
                    local agent_names=$(jq -r '.selected[].name // empty' "$pattern" 2>/dev/null | head -5 | tr '\n' ', ')
                    content="AGENTS SELECTED: $agent_count ($agent_names)"
                    break
                fi
            done
            ;;

        discovery_findings)
            content="Discovery findings captured"
            ;;

        selected_approach)
            local approach_file="$output_dir/1-discovery/selected-approach.json"
            if [[ -f "$approach_file" ]]; then
                content=$(jq -r '
                    "APPROACH: " + (.name // "unknown") + "\n" +
                    "RATIONALE: " + (.rationale // .description // "")
                ' "$approach_file" 2>/dev/null) || content="Approach extraction failed"
            fi
            ;;

        architecture_diagrams)
            local diagrams_dir="$ATOMIC_ROOT/docs/diagrams"
            if [[ -d "$diagrams_dir" ]]; then
                local count=$(find "$diagrams_dir" -name "*.svg" -o -name "*.dot" 2>/dev/null | wc -l | tr -d ' ')
                content="DIAGRAMS GENERATED: $count"
            fi
            ;;

        phase_audit)
            local audit_file="$ATOMIC_ROOT/.outputs/audits/phase-${phase_num}-report.json"
            [[ ! -f "$audit_file" ]] && audit_file="$ATOMIC_ROOT/.claude/audit/phase-0${phase_num}-audit.json"
            if [[ -f "$audit_file" ]]; then
                local passed=$(jq '.summary.passed // 0' "$audit_file" 2>/dev/null)
                local failed=$(jq '.summary.failed // 0' "$audit_file" 2>/dev/null)
                content="AUDIT: $passed passed, $failed failed"
            fi
            ;;

        prd_setup)
            content="PRD template and structure configured"
            ;;

        prd_interview)
            local interview_file="$output_dir/2-prd/prd-interview.json"
            if [[ -f "$interview_file" ]]; then
                content=$(jq -r '
                    "STAKEHOLDERS: " + ((.stakeholders // []) | join(", ")) + "\n" +
                    "SUCCESS_CRITERIA: " + ((.success_criteria // []) | join("; "))
                ' "$interview_file" 2>/dev/null) || content="Interview extraction failed"
            fi
            ;;

        prd_content)
            local prd_file="$output_dir/2-prd/PRD.md"
            if [[ -f "$prd_file" ]]; then
                content="PRD SUMMARY:\n$(head -100 "$prd_file")"
            fi
            ;;

        prd_validation)
            content="PRD validated"
            ;;

        prd_revisions)
            content="PRD revisions applied"
            ;;

        prd_approval)
            local approval_file="$output_dir/2-prd/prd-approved.json"
            if [[ -f "$approval_file" ]]; then
                content="PRD APPROVED: $(jq -r '.approved_at // "unknown"' "$approval_file" 2>/dev/null)"
            fi
            ;;

        tasks_decomposition)
            local tasks_file="$output_dir/3-tasking/tasks.json"
            if [[ -f "$tasks_file" ]]; then
                local count=$(jq '.tasks | length' "$tasks_file" 2>/dev/null || echo 0)
                local priorities=$(jq -r '[.tasks[].priority] | group_by(.) | map({key: .[0], count: length}) | map(.key + ": " + (.count | tostring)) | join(", ")' "$tasks_file" 2>/dev/null) || priorities=""
                content="TASKS: $count total. Priorities: $priorities"
            fi
            ;;

        dependency_analysis)
            content="Task dependencies analyzed"
            ;;

        specs_generated)
            local spec_count=$(find "$output_dir/4-specification" -name "spec-t*.json" 2>/dev/null | wc -l | tr -d ' ')
            content="SPECS GENERATED: $spec_count"
            ;;

        tdd_subtasks)
            content="TDD subtasks injected into tasks"
            ;;

        tdd_setup)
            local setup_file="$output_dir/5-implementation/tdd-setup.json"
            if [[ -f "$setup_file" ]]; then
                content=$(jq -r '
                    "COVERAGE_TARGET: " + (.coverage_target // "80%") + "\n" +
                    "TEST_PYRAMID: " + (.test_pyramid // "standard")
                ' "$setup_file" 2>/dev/null) || content="TDD setup configured"
            fi
            ;;

        tdd_results)
            local progress_file="$output_dir/5-implementation/tdd-progress.json"
            if [[ -f "$progress_file" ]]; then
                local coverage=$(jq '.coverage_percent // 0' "$progress_file" 2>/dev/null)
                local tests=$(jq '.tests_created // 0' "$progress_file" 2>/dev/null)
                content="TDD RESULTS: $coverage% coverage, $tests tests created"
            fi
            ;;

        validation_report)
            local report_file="$output_dir/5-implementation/validation-report.json"
            if [[ -f "$report_file" ]]; then
                content="Validation report generated"
            fi
            ;;

        review_findings)
            local findings_file="$output_dir/6-code-review/findings.json"
            if [[ -f "$findings_file" ]]; then
                local critical=$(jq '.critical | length' "$findings_file" 2>/dev/null || echo 0)
                local major=$(jq '.major | length' "$findings_file" 2>/dev/null || echo 0)
                local minor=$(jq '.minor | length' "$findings_file" 2>/dev/null || echo 0)
                content="REVIEW FINDINGS: $critical critical, $major major, $minor minor"
            fi
            ;;

        refinement_report)
            content="Code refinement completed"
            ;;

        integration_setup)
            local setup_file="$output_dir/7-integration/setup.json"
            if [[ -f "$setup_file" ]]; then
                content="Integration testing configured"
            fi
            ;;

        integration_results)
            local report_file="$output_dir/7-integration/integration-report.json"
            if [[ -f "$report_file" ]]; then
                content="Integration tests completed"
            fi
            ;;

        integration_approval)
            content="Integration approved"
            ;;

        deployment_setup)
            local setup_file="$output_dir/8-deployment-prep/setup.json"
            if [[ -f "$setup_file" ]]; then
                content="Deployment configured"
            fi
            ;;

        deployment_artifacts)
            local artifacts_file="$output_dir/8-deployment-prep/artifacts.json"
            if [[ -f "$artifacts_file" ]]; then
                content="Deployment artifacts generated"
            fi
            ;;

        deployment_approval)
            content="Deployment approved"
            ;;

        release_setup)
            local setup_file="$output_dir/9-release/setup.json"
            if [[ -f "$setup_file" ]]; then
                local version=$(jq -r '.version // "unknown"' "$setup_file" 2>/dev/null)
                content="RELEASE SETUP: version $version"
            fi
            ;;

        release_execution)
            local exec_file="$output_dir/9-release/execution.json"
            if [[ -f "$exec_file" ]]; then
                local url=$(jq -r '.release_url // "unknown"' "$exec_file" 2>/dev/null)
                content="RELEASE: $url"
            fi
            ;;

        release_confirmation)
            content="Release confirmed"
            ;;

        *)
            content="Task completed: $save_type"
            ;;
    esac

    echo "$content"
}

# ============================================================================
# TASK-LEVEL MEMORY (Per-Task Recall/Save)
# ============================================================================
# Every task is a new Claude Code instance - context must be passed via memory
# Uses dual-read (local + Supermemory) and dual-write (local + Supermemory) strategy

# Called at task start - recalls context relevant to this task
# Uses DUAL-READ strategy: local files first (fast), then Supermemory (cross-session)
# Usage: memory_task_start <task_id> <task_name> <phase_name>
memory_task_start() {
    local task_id="$1"
    local task_name="$2"
    local phase_name="${3:-}"

    # Set current task context for debug logging
    export CURRENT_TASK_ID="$task_id"
    export CURRENT_TASK_NAME="$task_name"

    _memory_log "memory_task_start" "ENTER: task_id=$task_id task_name=$task_name phase=$phase_name"
    _memory_debug "task_start" "start" "$(jq -nc --arg tid "$task_id" --arg tn "$task_name" '{task_id:$tid,task_name:$tn}')"

    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        _memory_log "memory_task_start" "SKIPPED: memory not enabled"
        _memory_debug "task_start" "skip" '{"reason":"memory_not_enabled"}'
        return 0
    fi

    # Extract phase number from phase name (e.g., "1-discovery" -> "1")
    local phase_num="${phase_name%%[!0-9]*}"
    [[ -z "$phase_num" ]] && phase_num="${CURRENT_PHASE%%[!0-9]*}"
    [[ -z "$phase_num" ]] && phase_num="0"

    # Get task-specific recall query from definitions
    local task_key="${phase_num}-${task_id}"
    local recall_query="${TASK_MEMORY_RECALL[$task_key]:-}"
    local expected_recall="${TASK_MEMORY_RECALL[$task_key]:-}"
    local expected_save="${TASK_MEMORY_SAVE[$task_key]:-}"

    # If no definition, use generic query
    if [[ -z "$recall_query" ]]; then
        recall_query="$phase_name $task_name context"
        _memory_log "memory_task_start" "No recall definition for $task_key, using generic query"
    else
        _memory_log "memory_task_start" "Using recall query for $task_key: $recall_query"
    fi

    _memory_debug "task_start" "config" "$(jq -nc \
        --arg query "$recall_query" \
        --arg expected_recall "$expected_recall" \
        --arg expected_save "$expected_save" \
        '{recall_query:$query,should_recall:$expected_recall,should_save:$expected_save}')"

    local task_context_file="${ATOMIC_ROOT:-.}/.outputs/task-context.md"
    mkdir -p "$(dirname "$task_context_file")"

    # Start fresh context file
    echo "# Task Context: $task_name" > "$task_context_file"
    echo "" >> "$task_context_file"
    echo "Retrieved: $(date -Iseconds) | Task: ${task_id} | Query: $recall_query" >> "$task_context_file"
    echo "" >> "$task_context_file"

    local has_context=false
    local local_chars=0
    local remote_chars=0
    local local_files=""

    # STEP 1: Read from LOCAL files first (fast, always available)
    _memory_debug "recall_local" "start" "$(jq -nc --arg q "$recall_query" '{query:$q}')"
    local local_context
    local_context=$(_memory_recall_local "$recall_query" "$phase_num") || true

    if [[ -n "$local_context" ]]; then
        echo "## Local Context" >> "$task_context_file"
        echo "" >> "$task_context_file"
        echo -e "$local_context" >> "$task_context_file"
        echo "" >> "$task_context_file"
        has_context=true
        local_chars=${#local_context}
        _memory_log "_memory_recall_local" "Found local context (${local_chars} chars)"
        _memory_debug "recall_local" "success" "$(jq -nc --argjson chars "$local_chars" --arg preview "$(_memory_truncate "$local_context" 150)" '{chars:$chars,preview:$preview}')"
    else
        _memory_debug "recall_local" "success" '{"chars":0,"preview":""}'
    fi

    # STEP 2: Also query Supermemory if API key configured (cross-session context)
    if [[ -n "$SUPERMEMORY_API_KEY" ]]; then
        _memory_log "_sm_recall" "Querying Supermemory: $recall_query"
        _memory_debug "recall_remote" "start" "$(jq -nc --arg q "$recall_query" '{query:$q,provider:"supermemory"}')"

        local recalled
        recalled=$(_sm_recall "$recall_query") || true

        if [[ -n "$recalled" ]] && [[ "$recalled" != "null" ]]; then
            local result_count
            result_count=$(echo "$recalled" | jq '.results | length' 2>/dev/null || echo "0")

            if [[ "$result_count" -gt 0 ]]; then
                local remote_content
                remote_content=$(echo "$recalled" | jq -r '.results[]? | .chunks[]?.content // .content // empty' 2>/dev/null)
                echo "## Supermemory Context" >> "$task_context_file"
                echo "" >> "$task_context_file"
                echo "$remote_content" >> "$task_context_file"
                echo "" >> "$task_context_file"
                has_context=true
                remote_chars=${#remote_content}
                _memory_log "_sm_recall" "Supermemory returned $result_count results"
                _memory_debug "recall_remote" "success" "$(jq -nc --argjson count "$result_count" --argjson chars "$remote_chars" --arg preview "$(_memory_truncate "$remote_content" 150)" '{results:$count,chars:$chars,preview:$preview}')"
            else
                _memory_log "_sm_recall" "Supermemory returned 0 results"
                _memory_debug "recall_remote" "success" '{"results":0,"chars":0}'
            fi
        else
            _memory_debug "recall_remote" "success" '{"results":0,"chars":0}'
        fi
    else
        _memory_log "memory_task_start" "Supermemory not configured, using local only"
        _memory_debug "recall_remote" "skip" '{"reason":"not_configured"}'
    fi

    # Clean up if no context was found
    if [[ "$has_context" != "true" ]]; then
        rm -f "$task_context_file"
        _memory_log "memory_task_start" "No context found, removed empty context file"
        _memory_debug "inject" "skip" '{"reason":"no_context_found"}'
    else
        local char_count=$(wc -c < "$task_context_file" | tr -d ' ')
        _memory_log "inject" "Wrote $char_count chars to task-context.md"
        _memory_debug "inject" "success" "$(jq -nc --argjson total "$char_count" --argjson local "$local_chars" --argjson remote "$remote_chars" '{total_chars:$total,local_chars:$local,remote_chars:$remote,file:"task-context.md"}')"
    fi

    _memory_log "memory_task_start" "EXIT"
    _memory_debug "task_start" "success" "$(jq -nc --argjson has_context "$([[ "$has_context" == "true" ]] && echo true || echo false)" '{has_context:$has_context}')"
    return 0
}

# Called at task end - saves task outcomes/decisions to memory
# Uses DUAL-WRITE strategy: ALWAYS write locally, also write to Supermemory if available
# Usage: memory_task_end <task_id> <task_name> <phase_name> [outcome_summary]
memory_task_end() {
    local task_id="$1"
    local task_name="$2"
    local phase_name="${3:-}"
    local outcome="${4:-}"

    _memory_log "memory_task_end" "ENTER: task_id=$task_id task_name=$task_name phase=$phase_name"
    _memory_debug "task_end" "start" "$(jq -nc --arg tid "$task_id" --arg tn "$task_name" '{task_id:$tid,task_name:$tn}')"

    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        _memory_log "memory_task_end" "SKIPPED: memory not enabled"
        _memory_debug "task_end" "skip" '{"reason":"memory_not_enabled"}'
        return 0
    fi

    # Extract phase number from phase name
    local phase_num="${phase_name%%[!0-9]*}"
    [[ -z "$phase_num" ]] && phase_num="${CURRENT_PHASE%%[!0-9]*}"
    [[ -z "$phase_num" ]] && phase_num="0"

    # Get task-specific save type from definitions
    local task_key="${phase_num}-${task_id}"
    local save_type="${TASK_MEMORY_SAVE[$task_key]:-}"

    # If no save type defined (empty string), skip saving
    if [[ -z "$save_type" ]]; then
        _memory_log "memory_task_end" "No save definition for $task_key, skipping save"
        _memory_debug "task_end" "skip" "$(jq -nc --arg reason "no_save_definition" --arg key "$task_key" '{reason:$reason,task_key:$key}')"
        return 0
    fi

    _memory_log "memory_task_end" "Save type for $task_key: $save_type"
    _memory_debug "save_extract" "start" "$(jq -nc --arg type "$save_type" '{save_type:$type}')"

    # Extract meaningful content based on save type
    local content
    if [[ -n "$outcome" ]]; then
        # If explicit outcome provided, use it
        content="$outcome"
        _memory_log "memory_task_end" "Using provided outcome (${#outcome} chars)"
    else
        # Extract content from output files based on save type
        content=$(_memory_extract_content "$save_type" "$phase_num" "$task_id")
        _memory_log "memory_task_end" "Extracted content for $save_type (${#content} chars)"
    fi

    local content_chars=${#content}
    _memory_debug "save_extract" "success" "$(jq -nc --argjson chars "$content_chars" --arg preview "$(_memory_truncate "$content" 150)" '{chars:$chars,preview:$preview}')"

    # Skip if no meaningful content
    if [[ -z "$content" || "$content" == "Task completed:"* ]]; then
        _memory_log "memory_task_end" "No meaningful content to save, skipping"
        _memory_debug "task_end" "skip" '{"reason":"no_meaningful_content"}'
        return 0
    fi

    # Add task/phase context prefix
    local full_content="[$phase_name] [Task $task_id: $task_name]\n\n$content"

    # STEP 1: ALWAYS write to LOCAL file storage
    _memory_debug "save_local" "start" "$(jq -nc --arg type "$save_type" '{save_type:$type}')"
    local saved_file
    saved_file=$(_memory_save_local "$phase_num" "$task_id" "$save_type" "$content")
    _memory_log "_memory_save_local" "Saved to $saved_file"
    _memory_debug "save_local" "success" "$(jq -nc --arg file "$saved_file" --argjson chars "$content_chars" '{file:$file,chars:$chars}')"

    # STEP 2: Also write to Supermemory if API key configured
    local remote_saved=false
    if [[ -n "$SUPERMEMORY_API_KEY" ]]; then
        _memory_log "_sm_memory" "Saving to Supermemory: ${full_content:0:80}..."
        _memory_debug "save_remote" "start" '{"provider":"supermemory"}'
        if _sm_memory "$full_content"; then
            _memory_log "_sm_memory" "Supermemory save SUCCESS"
            _memory_debug "save_remote" "success" '{"provider":"supermemory"}'
            remote_saved=true
        else
            _memory_log "_sm_memory" "Supermemory save FAILED (local backup exists)"
            _memory_debug "save_remote" "fail" '{"provider":"supermemory","fallback":"local"}'
        fi
    else
        _memory_log "memory_task_end" "Supermemory not configured, saved locally only"
        _memory_debug "save_remote" "skip" '{"reason":"not_configured"}'
    fi

    _memory_log "memory_task_end" "EXIT"
    _memory_debug "task_end" "success" "$(jq -nc --argjson local true --argjson remote "$remote_saved" --argjson chars "$content_chars" '{saved_local:$local,saved_remote:$remote,content_chars:$chars}')"
    return 0
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
        # API returns content in .results[].chunks[].content
        echo "$recalled" | jq -r '.results[]? | .chunks[]?.content // .content // empty' >> "$session_context_file" 2>/dev/null
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
export -f memory_task_start memory_task_end
export -f memory_session_start memory_session_end
export -f _memory_log _memory_save_local _memory_recall_local
export -f _memory_save_closeout _memory_extract_content
export -f _memory_ensure_local_dirs
export -f _memory_debug _memory_truncate
