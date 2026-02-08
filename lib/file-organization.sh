#!/usr/bin/env bash
# File Organization - Clean up task outputs after completion

# Organize files after task completion
# Usage: organize_task_files <phase_id> <task_id> <output_dir>
organize_task_files() {
    local phase_id="$1"
    local task_id="$2"
    local output_dir="$3"

    [[ ! -d "$output_dir" ]] && return 0

    # Create organized subdirectories
    mkdir -p "$output_dir/prompts" "$output_dir/outputs" "$output_dir/working"

    # Move prompt files to prompts/
    find "$output_dir" -maxdepth 1 -type f \( -name "*prompt*" -o -name "*input*" -o -name "*context*" \) -exec mv {} "$output_dir/prompts/" \; 2>/dev/null

    # Move output files to outputs/
    find "$output_dir" -maxdepth 1 -type f \( -name "*output*" -o -name "*response*" -o -name "*result*" -o -name "*generated*" \) -exec mv {} "$output_dir/outputs/" \; 2>/dev/null

    # Move temporary/working files to working/
    find "$output_dir" -maxdepth 1 -type f \( -name "*.tmp" -o -name "*.tmp.*" -o -name "*-prior.md" \) -exec mv {} "$output_dir/working/" \; 2>/dev/null

    # For PRD tasks with many generation files, organize by generation
    if [[ "$phase_id" == "2-prd" && "$task_id" == "205" ]]; then
        organize_prd_generation_files "$output_dir"
    fi

    return 0
}

# Organize PRD generation files into numbered subdirectories
organize_prd_generation_files() {
    local output_dir="$1"
    local prompts_dir="$output_dir/prompts"

    [[ ! -d "$prompts_dir" ]] && return 0

    # Create generation-specific directories
    for gen_num in {1..8}; do
        local gen_dir="$prompts_dir/generation-$gen_num"
        mkdir -p "$gen_dir"

        # Move generation-specific files
        find "$prompts_dir" -maxdepth 1 -type f -name "*gen-${gen_num}-*" -exec mv {} "$gen_dir/" \; 2>/dev/null
        find "$prompts_dir" -maxdepth 1 -type f -name "*guardian-gen-${gen_num}-*" -exec mv {} "$gen_dir/" \; 2>/dev/null
    done

    # Move context files to context/ subdirectory
    if [[ -d "$prompts_dir/context" ]]; then
        # Already organized
        :
    else
        mkdir -p "$prompts_dir/context"
        find "$prompts_dir" -maxdepth 1 -type f -name "*context*" -o -name "*cumulative*" -exec mv {} "$prompts_dir/context/" \; 2>/dev/null
    fi

    return 0
}

# Export functions
export -f organize_task_files
export -f organize_prd_generation_files
