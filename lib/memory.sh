#!/usr/bin/env bash
#
# ATOMIC-CLAUDE Memory Layer
# Persistent memory via local SQLite storage (via claude-mem hooks)
#
# Architecture:
#   - Checkpoint model: Memory saved at phase closeouts + task-level
#   - Head tracking: Local state knows current phase progression
#   - Backtrack handling: Invalidates orphaned memories
#   - Scope separation: Pipeline work vs meta/debug work
#   - User approval: Nothing persists without explicit consent
#   - Claude-mem integration: Hook-based automatic context capture
#
# Storage Backends:
#   - Local files: .state/memory/ (always available, fast)
#   - Claude-mem: SQLite via hooks (automatic during Claude Code sessions)
#

# ============================================================================
# CONFIGURATION
# ============================================================================

# Local state files
MEMORY_HEAD_FILE="${ATOMIC_ROOT:-.}/.state/memory-head.json"
MEMORY_CHECKPOINTS_DIR="${ATOMIC_ROOT:-.}/.state/memory-checkpoints"
MEMORY_LOCAL_DIR="${ATOMIC_ROOT:-.}/.state/memory"

# Source task memory definitions
_MEMORY_DEFS_PATH="${BASH_SOURCE[0]%/*}/task-memory-defs.sh"
if [[ -f "$_MEMORY_DEFS_PATH" ]]; then
    source "$_MEMORY_DEFS_PATH"
fi

# Load configuration from environment and/or secrets file
_memory_load_config() {
    # Check secrets file for memory settings if not in environment
    local secrets_file="${ATOMIC_OUTPUT_DIR:-${ATOMIC_ROOT:-.}/.outputs}/0-setup/secrets.json"

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
    export MEMORY_ENABLED
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
    mkdir -p "$MEMORY_LOCAL_DIR"

    # Initialize head file if missing
    if [[ ! -f "$MEMORY_HEAD_FILE" ]]; then
        _memory_init_head
    fi

    # Log initialization
    mkdir -p "${ATOMIC_ROOT:-.}/.logs"
    echo "[$(date -Iseconds)] Memory system initialized (local storage)" >> "${ATOMIC_ROOT:-.}/.logs/memory.log"

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
memory_should_persist() {
    # Memory must be enabled
    if [[ "$MEMORY_ENABLED" != "true" ]]; then
        return 1
    fi

    # Must be in pipeline mode (phase context exists)
    if [[ -z "${ATOMIC_PHASE:-}" ]] && [[ -z "${CURRENT_PHASE:-}" ]]; then
        return 1
    fi

    return 0
}

# Check if claude-mem is available (always true when running in Claude Code)
# Legacy function kept for API compatibility
memory_has_remote() {
    # Claude-mem hooks capture context automatically during Claude Code sessions
    # Local files are always used as the primary storage
    return 0
}

# ============================================================================
# MEMORY STORAGE (Local + Claude-mem)
# ============================================================================
#
# Storage strategy:
#   - Local files (.state/memory/): Always used, fast, works offline
#   - Claude-mem hooks: Automatic context capture during Claude Code sessions
#
# Claude-mem integration:
#   - No explicit save needed - hooks capture tool usage automatically
#   - For recall, use local files (claude-mem's mem-search is session-based)
#

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

# Handle backtrack - invalidate orphaned memories
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
    echo -e "  Local memories from phases $((target_phase + 1))-$head_phase will be cleared."
    echo ""
    echo -e "  Options:"
    echo -e "    ${GREEN:-}[continue]${NC:-} Clear local memories and proceed"
    echo -e "    ${RED:-}[abort]${NC:-}    Cancel and stay at current phase"
    echo ""

    local choice
    read -rp "  Choice [continue]: " choice || choice="continue"
    choice=${choice:-continue}

    case "$choice" in
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

    echo ""
    echo -e "  ${BOLD:-}MEMORY CHECKPOINT${NC:-}"
    echo ""
    echo -e "  ${DIM:-}Summary to persist:${NC:-}"
    echo ""
    echo "$summary" | sed 's/^/    /'
    echo ""
    echo -e "  ${CYAN:-}Options:${NC:-}"
    echo -e "    ${GREEN:-}[save]${NC:-} Save to local memory"
    echo -e "    ${YELLOW:-}[edit]${NC:-} Edit summary before saving"
    echo -e "    ${DIM:-}[skip]${NC:-} Don't save"
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
            # Still create local checkpoint
            memory_create_checkpoint "$phase" "$phase_name" "$summary"
            return 1
            ;;
    esac
}

# Commit phase to local memory storage
_memory_commit_phase() {
    local phase="$1"
    local phase_name="$2"
    local summary="$3"

    # Create local checkpoint
    local checkpoint_id
    checkpoint_id=$(memory_create_checkpoint "$phase" "$phase_name" "$summary")

    # Save closeout to local file storage
    _memory_save_closeout "$phase" "$phase_name" "$summary"
    _memory_log "_memory_commit_phase" "Saved closeout locally for Phase $phase"

    echo ""
    echo -e "  ${GREEN:-}✓${NC:-} Saved to local memory (checkpoint: $checkpoint_id)"
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
                [[ "$(jq -r '.memory_enabled // false' "$secrets_file" 2>/dev/null)" == "true" ]] && providers+="local-memory "
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
    # Safely access arrays (may not be available in all contexts)
    local recall_query=""
    local expected_recall=""
    local expected_save=""

    if declare -p TASK_MEMORY_RECALL &>/dev/null; then
        recall_query="${TASK_MEMORY_RECALL[$task_key]:-}"
        expected_recall="${TASK_MEMORY_RECALL[$task_key]:-}"
    fi

    if declare -p TASK_MEMORY_SAVE &>/dev/null; then
        expected_save="${TASK_MEMORY_SAVE[$task_key]:-}"
    fi

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

    # Note: claude-mem captures context automatically via hooks during Claude Code sessions
    # Local files are the primary storage - no external API calls needed

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

    # Note: claude-mem hooks capture context automatically during Claude Code sessions
    # Local files are the primary storage

    _memory_log "memory_task_end" "EXIT"
    _memory_debug "task_end" "success" "$(jq -nc --argjson local true --argjson chars "$content_chars" '{saved_local:$local,content_chars:$chars}')"
    return 0
}

# ============================================================================
# SESSION LIFECYCLE
# ============================================================================

# Called on session start - retrieves relevant context from local storage
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

    # Load context from local memory files
    local has_context=false

    # Add local head state
    if [[ -f "$MEMORY_HEAD_FILE" ]]; then
        local head_phase
        head_phase=$(memory_get_head_phase)
        if [[ "$head_phase" -ge 0 ]]; then
            echo "## Pipeline State" >> "$session_context_file"
            echo "" >> "$session_context_file"
            echo "Current phase progression: Phase $head_phase" >> "$session_context_file"
            echo "" >> "$session_context_file"
            has_context=true
        fi
    fi

    # Load the most recent closeout(s)
    if [[ -d "$MEMORY_LOCAL_DIR" ]]; then
        local closeout_files
        closeout_files=$(find "$MEMORY_LOCAL_DIR" -name "closeout.md" -type f 2>/dev/null | sort -V)
        if [[ -n "$closeout_files" ]]; then
            echo "## Previous Closeouts" >> "$session_context_file"
            echo "" >> "$session_context_file"
            # Include last 2 closeouts for context
            echo "$closeout_files" | tail -2 | while read -r closeout; do
                if [[ -f "$closeout" ]]; then
                    cat "$closeout" >> "$session_context_file"
                    echo "" >> "$session_context_file"
                fi
            done
            has_context=true
        fi
    fi

    if [[ "$has_context" == "true" ]]; then
        echo -e "  ${GREEN:-}✓${NC:-} Session context loaded from local memory"
    else
        echo "_No memories found for this project._" >> "$session_context_file"
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
