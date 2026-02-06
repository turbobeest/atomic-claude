#!/bin/bash
# Git Dual-Repo Sync Helper for python-bash branch

# Current setup:
# - origin: https://github.com/turbobeest/atomic-claude.git (PUBLIC)
# - internal: https://github.boozallencsn.com/TerBeest-James/atomic-claude.git (PRIVATE)

# ============================================
# Quick Sync Commands
# ============================================

# Pull from BOTH repos and merge (run this frequently)
sync-pull() {
    echo "Fetching from both remotes..."
    git fetch origin python-bash
    git fetch internal python-bash
    
    # Check for conflicts
    if ! git merge-base --is-ancestor origin/python-bash HEAD; then
        echo "⚠️  origin/python-bash has new commits"
        git log HEAD..origin/python-bash --oneline
    fi
    
    if ! git merge-base --is-ancestor internal/python-bash HEAD; then
        echo "⚠️  internal/python-bash has new commits"
        git log HEAD..internal/python-bash --oneline
    fi
    
    echo ""
    echo "To merge updates:"
    echo "  git merge origin/python-bash    # Merge from public"
    echo "  git merge internal/python-bash  # Merge from Booz Allen"
}

# Push to BOTH repos (after committing locally)
sync-push() {
    echo "Pushing to both remotes..."
    git push origin python-bash && echo "✅ Pushed to PUBLIC (origin)" || echo "❌ Failed to push to origin"
    git push internal python-bash && echo "✅ Pushed to PRIVATE (internal)" || echo "❌ Failed to push to internal"
}

# Sync FROM one repo TO the other (when one is ahead)
sync-origin-to-internal() {
    echo "Syncing PUBLIC → PRIVATE..."
    git fetch origin python-bash
    git push internal origin/python-bash:python-bash
    echo "✅ Synced origin/python-bash to internal/python-bash"
}

sync-internal-to-origin() {
    echo "Syncing PRIVATE → PUBLIC..."
    git fetch internal python-bash
    git push origin internal/python-bash:python-bash
    echo "✅ Synced internal/python-bash to origin/python-bash"
}

# Check sync status
sync-status() {
    echo "=== Sync Status ==="
    echo ""
    echo "Local branch: $(git branch --show-current)"
    echo "Tracking: $(git rev-parse --abbrev-ref --symbolic-full-name @{upstream} 2>/dev/null || echo 'none')"
    echo ""
    
    git fetch origin python-bash 2>/dev/null
    git fetch internal python-bash 2>/dev/null
    
    echo "Commits on origin/python-bash not on local:"
    git log HEAD..origin/python-bash --oneline 2>/dev/null | wc -l | xargs echo
    
    echo "Commits on internal/python-bash not on local:"
    git log HEAD..internal/python-bash --oneline 2>/dev/null | wc -l | xargs echo
    
    echo "Commits on local not on origin/python-bash:"
    git log origin/python-bash..HEAD --oneline 2>/dev/null | wc -l | xargs echo
    
    echo "Commits on local not on internal/python-bash:"
    git log internal/python-bash..HEAD --oneline 2>/dev/null | wc -l | xargs echo
}

# Show this help
sync-help() {
    echo "Git Dual-Repo Sync Commands"
    echo "============================"
    echo ""
    echo "Source this file to use these functions:"
    echo "  source .git-sync-config.sh"
    echo ""
    echo "Commands:"
    echo "  sync-status              - Check sync status"
    echo "  sync-pull                - Fetch from both repos and show differences"
    echo "  sync-push                - Push local commits to BOTH repos"
    echo "  sync-origin-to-internal  - Sync PUBLIC → PRIVATE"
    echo "  sync-internal-to-origin  - Sync PRIVATE → PUBLIC"
    echo ""
    echo "Typical workflow (when working locally):"
    echo "  1. sync-status           # Check what's changed"
    echo "  2. sync-pull             # Fetch updates from both"
    echo "  3. [make changes and commit]"
    echo "  4. sync-push             # Push to both repos"
    echo ""
    echo "When one repo is ahead (e.g., edited on GitHub web):"
    echo "  sync-origin-to-internal  # Copy public changes to private"
    echo "  sync-internal-to-origin  # Copy private changes to public"
}

# Auto-display help when sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "This script should be sourced, not executed."
    echo "Run: source .git-sync-config.sh"
    exit 1
else
    sync-help
fi
