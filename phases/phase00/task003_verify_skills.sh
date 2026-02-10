#!/usr/bin/env bash
#
# Task 003: Verify Skills
# Verifies that tactical and community skills are present and correctly structured
#
# Input: None (checks .claude/skills directory)
# Output: .outputs/0-setup/skills-verified.json with skill counts and status
#

set -euo pipefail
LIB_DIR="${ATOMIC_LIB_DIR:-$(dirname "$0")/../../lib}"
source "$LIB_DIR/atomic.sh"

task_003_verify_skills() {
    local skills_dir="$ATOMIC_ROOT/skills"
    local output_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/skills-verified.json"
    local verification_log="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/skills-verification.log"

    atomic_step "Verifying Skills System"

    # Check main skills directory exists
    if [[ ! -d "$skills_dir" ]]; then
        atomic_error "Skills directory not found: $skills_dir"
        return 1
    fi

    atomic_substep "Checking skills directory structure..."
    echo ""

    # Check tactical skills
    local tactical_dir="$skills_dir/tactical"
    if [[ ! -d "$tactical_dir" ]]; then
        atomic_error "Tactical skills directory not found: $tactical_dir"
        return 1
    fi

    local tactical_count=$(find "$tactical_dir" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
    echo "  Tactical skills: $tactical_count"

    if [[ "$tactical_count" -ne 20 ]]; then
        atomic_warning "Expected 20 tactical skills, found $tactical_count"
        echo "  ⚠️  Tactical skill count mismatch" >> "$verification_log"
    fi

    # Check community skills
    local community_dir="$skills_dir/community"
    if [[ ! -d "$community_dir" ]]; then
        atomic_error "Community skills directory not found: $community_dir"
        return 1
    fi

    local community_count=$(find "$community_dir" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
    echo "  Community skills: $community_count"

    if [[ "$community_count" -ne 65 ]]; then
        atomic_warning "Expected 65 community skills, found $community_count"
        echo "  ⚠️  Community skill count mismatch" >> "$verification_log"
        echo ""
        echo "  If community skills are missing, they may need to be cloned:"
        echo "    cd $community_dir"
        echo "    git clone https://github.com/obra/superpowers.git superpowers"
        echo "    git clone https://github.com/trailofbits/skills.git trailofbits"
        echo "    git clone https://github.com/frankbria/ralph-claude-code.git ralph"
        echo ""
    fi

    local total_skills=$((tactical_count + community_count))
    echo "  Total SKILL.md files: $total_skills"
    echo ""

    # Check for specific critical skills
    atomic_substep "Verifying critical skills..."
    echo ""

    local critical_skills=(
        "tactical/extraction/extract-todos/SKILL.md"
        "tactical/formatting/format-code/SKILL.md"
        "tactical/validation/validate-json/SKILL.md"
        "community/superpowers/skills/brainstorming/SKILL.md"
        "community/superpowers/skills/test-driven-development/SKILL.md"
        "community/trailofbits/plugins/audit-context-building/skills/audit-context-building/SKILL.md"
    )

    local missing_critical=0
    for skill_path in "${critical_skills[@]}"; do
        local full_path="$skills_dir/$skill_path"
        local skill_name=$(basename "$(dirname "$skill_path")")

        if [[ -f "$full_path" ]]; then
            echo "  ✓ $skill_name"
        else
            echo "  ✗ $skill_name (MISSING)"
            missing_critical=$((missing_critical + 1)) || true
            echo "  Missing: $skill_path" >> "$verification_log"
        fi
    done

    echo ""

    # Check for ralph framework
    atomic_substep "Checking Ralph autonomous framework..."
    echo ""

    local ralph_dir="$community_dir/ralph"
    if [[ -d "$ralph_dir" ]]; then
        local ralph_scripts=$(find "$ralph_dir" -maxdepth 1 -name "*.sh" -type f | wc -l | tr -d ' ')
        echo "  ✓ Ralph framework present ($ralph_scripts bash scripts)"
    else
        echo "  ✗ Ralph framework missing"
        missing_critical=$((missing_critical + 1)) || true
        echo "  Missing: Ralph framework" >> "$verification_log"
    fi

    echo ""

    # Create verification report
    local status="verified"
    local warnings=()

    if [[ "$tactical_count" -ne 20 ]]; then
        status="warning"
        warnings+=("Tactical skill count: expected 20, found $tactical_count")
    fi

    if [[ "$community_count" -ne 65 ]]; then
        status="warning"
        warnings+=("Community skill count: expected 65, found $community_count")
    fi

    if [[ "$missing_critical" -gt 0 ]]; then
        status="error"
        warnings+=("Missing $missing_critical critical skills")
    fi

    # Build warnings JSON array
    local warnings_json="[]"
    if [[ ${#warnings[@]} -gt 0 ]]; then
        warnings_json="["
        for i in "${!warnings[@]}"; do
            if [[ $i -gt 0 ]]; then
                warnings_json+=","
            fi
            warnings_json+="\"${warnings[$i]}\""
        done
        warnings_json+="]"
    fi

    cat > "$output_file" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "status": "$status",
  "skills": {
    "tactical": {
      "directory": "skills/tactical",
      "count": $tactical_count,
      "expected": 20,
      "status": $([ "$tactical_count" -eq 20 ] && echo '"ok"' || echo '"mismatch"')
    },
    "community": {
      "directory": "skills/community",
      "count": $community_count,
      "expected": 65,
      "status": $([ "$community_count" -eq 65 ] && echo '"ok"' || echo '"mismatch"'),
      "repositories": {
        "superpowers": $([ -d "$community_dir/superpowers" ] && echo "true" || echo "false"),
        "trailofbits": $([ -d "$community_dir/trailofbits" ] && echo "true" || echo "false"),
        "ralph": $([ -d "$community_dir/ralph" ] && echo "true" || echo "false")
      }
    },
    "total": $total_skills
  },
  "critical_skills": {
    "checked": ${#critical_skills[@]},
    "missing": $missing_critical
  },
  "warnings": $warnings_json
}
EOF

    if [[ "$status" == "verified" ]]; then
        atomic_success "Skills system verified ($total_skills skills)"
        echo ""
        echo "  Skills available:"
        echo "    • Tactical: $tactical_count skills (formatting, validation, extraction, etc.)"
        echo "    • Community: $community_count skills (planning, security, TDD, fuzzing)"
        echo "    • Framework: Ralph autonomous development"
        echo ""
        return 0
    elif [[ "$status" == "warning" ]]; then
        atomic_warning "Skills system has warnings"
        echo ""
        echo "  Issues detected:"
        for warning in "${warnings[@]}"; do
            echo "    ⚠️  $warning"
        done
        echo ""
        echo "  See: $verification_log"
        echo ""
        return 0  # Continue despite warnings
    else
        atomic_error "Skills system verification failed"
        echo ""
        echo "  Critical issues:"
        for warning in "${warnings[@]}"; do
            echo "    ✗ $warning"
        done
        echo ""
        echo "  See: $verification_log"
        echo ""
        return 1
    fi
}

# Execute if run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    task_003_verify_skills
fi
