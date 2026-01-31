#!/bin/bash
#
# ATOMIC-CLAUDE Git Operations
# Auto-commit after tasks, auto-push after phases
#
# Configuration via config/pipeline.json:
#   git.auto_commit: true|false (default: true)
#   git.auto_push: "never"|"phase-end"|"always" (default: "phase-end")
#   git.commit_message_prefix: string (default: "[ATOMIC]")
#   git.push_remote: string (default: "origin")
#

# ============================================================================
# CONFIGURATION
# ============================================================================

_git_ops_config_file="${ATOMIC_ROOT:-$(pwd)}/config/pipeline.json"

_git_ops_get_config() {
    local key="$1"
    local default="$2"

    if [[ -f "$_git_ops_config_file" ]]; then
        local value
        value=$(jq -r "$key // empty" "$_git_ops_config_file" 2>/dev/null)
        if [[ -n "$value" && "$value" != "null" ]]; then
            echo "$value"
            return
        fi
    fi
    echo "$default"
}

# ============================================================================
# COMMIT OPERATIONS
# ============================================================================

# Check if auto-commit is enabled
atomic_git_should_commit() {
    local auto_commit
    auto_commit=$(_git_ops_get_config '.git.auto_commit' 'true')
    [[ "$auto_commit" == "true" ]]
}

# Commit current changes after a task
# Usage: atomic_git_commit_task <phase> <task_id> <task_name> [artifact_list]
atomic_git_commit_task() {
    local phase="$1"
    local task_id="$2"
    local task_name="$3"
    local artifacts="${4:-}"

    if ! atomic_git_should_commit; then
        return 0
    fi

    # Check if we're in a git repo
    if ! git rev-parse --git-dir &>/dev/null; then
        return 0
    fi

    # Check if there are changes to commit
    if git diff --quiet && git diff --cached --quiet; then
        # No changes
        return 0
    fi

    local prefix
    prefix=$(_git_ops_get_config '.git.commit_message_prefix' '[ATOMIC]')

    # Stage tracked files that changed (not untracked)
    git add -u &>/dev/null || true

    # Stage common output directories
    git add "${ATOMIC_ROOT:-.}/.claude/" &>/dev/null 2>&1 || true
    git add "${ATOMIC_ROOT:-.}/.outputs/" &>/dev/null 2>&1 || true
    git add "${ATOMIC_ROOT:-.}/.state/" &>/dev/null 2>&1 || true
    git add "${ATOMIC_ROOT:-.}/docs/" &>/dev/null 2>&1 || true

    # Check again if there's anything to commit after staging
    if git diff --cached --quiet; then
        return 0
    fi

    # Build commit message
    local commit_msg="$prefix Phase $phase / Task $task_id: $task_name"

    if [[ -n "$artifacts" ]]; then
        commit_msg="$commit_msg

Artifacts: $artifacts"
    fi

    # Commit
    git commit -m "$commit_msg" --no-verify &>/dev/null || true

    local log_file="${ATOMIC_ROOT:-.}/.logs/git-ops.log"
    mkdir -p "$(dirname "$log_file")"
    echo "[$(date -Iseconds)] COMMIT: Phase $phase / Task $task_id - $task_name" >> "$log_file"

    return 0
}

# ============================================================================
# PUSH OPERATIONS
# ============================================================================

# Check if auto-push is enabled for the given trigger
# Usage: atomic_git_should_push <trigger>
# Triggers: "task" | "phase-end"
atomic_git_should_push() {
    local trigger="${1:-phase-end}"

    local auto_push
    auto_push=$(_git_ops_get_config '.git.auto_push' 'phase-end')

    case "$auto_push" in
        never)
            return 1
            ;;
        always)
            return 0
            ;;
        phase-end)
            [[ "$trigger" == "phase-end" ]]
            ;;
        *)
            return 1
            ;;
    esac
}

# Push to remote
# Usage: atomic_git_push_phase <phase> <phase_name>
atomic_git_push_phase() {
    local phase="$1"
    local phase_name="$2"

    if ! atomic_git_should_push "phase-end"; then
        return 0
    fi

    # Check if we're in a git repo
    if ! git rev-parse --git-dir &>/dev/null; then
        return 0
    fi

    local remote
    remote=$(_git_ops_get_config '.git.push_remote' 'origin')

    # Get current branch
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

    if [[ -z "$branch" || "$branch" == "HEAD" ]]; then
        # Detached HEAD, skip push
        return 0
    fi

    # Check if remote exists
    if ! git remote get-url "$remote" &>/dev/null; then
        return 0
    fi

    # Check if there are commits to push
    local ahead
    ahead=$(git rev-list --count "$remote/$branch..HEAD" 2>/dev/null || echo "0")

    if [[ "$ahead" == "0" ]]; then
        return 0
    fi

    echo ""
    echo -e "  ${DIM:-}Pushing Phase $phase ($phase_name) to $remote/$branch...${NC:-}"

    if git push "$remote" "$branch" --no-verify 2>/dev/null; then
        echo -e "  ${GREEN:-}✓${NC:-} Pushed $ahead commit(s) to $remote/$branch"

        local log_file="${ATOMIC_ROOT:-.}/.logs/git-ops.log"
        mkdir -p "$(dirname "$log_file")"
        echo "[$(date -Iseconds)] PUSH: Phase $phase ($phase_name) - $ahead commits to $remote/$branch" >> "$log_file"
    else
        echo -e "  ${YELLOW:-}!${NC:-} Push failed (will retry on next phase)"
    fi

    return 0
}

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Called at end of task - commits if enabled
# Usage: atomic_git_task_complete <phase> <task_id> <task_name> [artifacts]
atomic_git_task_complete() {
    atomic_git_commit_task "$@"
}

# Called at phase closeout - commits and pushes if enabled
# Usage: atomic_git_phase_complete <phase> <phase_name>
atomic_git_phase_complete() {
    local phase="$1"
    local phase_name="$2"

    # Final commit for any remaining changes
    atomic_git_commit_task "$phase" "closeout" "$phase_name closeout"

    # Push if configured
    atomic_git_push_phase "$phase" "$phase_name"
}

# ============================================================================
# EXPORTS
# ============================================================================

export -f atomic_git_should_commit atomic_git_commit_task
export -f atomic_git_should_push atomic_git_push_phase
export -f atomic_git_task_complete atomic_git_phase_complete
