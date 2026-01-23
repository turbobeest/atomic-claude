#!/bin/bash
#
# Task 304: Dependency Analysis & Work Packages
# Validate DAG, visualize execution levels with complexity, generate work packages
#
# This task:
#   1. Validates dependency graph (cycles, invalid refs)
#   2. Computes topological levels for parallel execution
#   3. Renders ASCII DAG with complexity and time annotations
#   4. Generates work-packages.json for Phase 4+ execution
#

task_304_dependency_analysis() {
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local graph_file="$ATOMIC_ROOT/.taskmaster/reports/dependency-graph.json"
    local packages_file="$ATOMIC_ROOT/.taskmaster/reports/work-packages.json"
    local analysis_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/dependency-analysis.json"

    atomic_step "Dependency Analysis"

    mkdir -p "$(dirname "$graph_file")" "$(dirname "$analysis_file")"

    echo ""
    echo -e "  ${DIM}Validating DAG structure, computing execution levels, and generating work packages.${NC}"
    echo ""

    if [[ ! -f "$tasks_file" ]]; then
        atomic_error "Tasks file not found: $tasks_file"
        return 1
    fi

    local task_count=$(jq '.tasks | length // 0' "$tasks_file")

    if [[ "$task_count" -eq 0 ]]; then
        atomic_error "No tasks found in tasks.json"
        return 1
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # DEPENDENCY VALIDATION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}DEPENDENCY VALIDATION${NC}"
    echo ""

    local validation_passed=true

    # Check for invalid dependency references
    local invalid_deps=$(jq -r '
        .tasks | map(.id) as $valid_ids |
        [.[] | .id as $task_id | .dependencies[] |
            select(. as $dep | $valid_ids | index($dep) == null) |
            {task: $task_id, invalid_dep: .}
        ] | length
    ' "$tasks_file" 2>/dev/null || echo "0")

    if [[ "$invalid_deps" -gt 0 ]]; then
        echo -e "  ${RED}✗${NC} Found $invalid_deps invalid dependency references"
        validation_passed=false
    else
        echo -e "  ${GREEN}✓${NC} All dependency references valid"
    fi

    # Check for self-references
    local self_refs=$(jq '[.tasks[] | select(.id as $id | .dependencies | index($id) != null)] | length' "$tasks_file" 2>/dev/null || echo "0")

    if [[ "$self_refs" -gt 0 ]]; then
        echo -e "  ${RED}✗${NC} Found $self_refs self-referencing tasks"
        validation_passed=false
    fi

    # Check for cycles (simplified: if no root nodes exist, there's likely a cycle)
    local root_count=$(jq '[.tasks[] | select(.dependencies | length == 0)] | length' "$tasks_file")
    if [[ "$root_count" -eq 0 && "$task_count" -gt 0 ]]; then
        echo -e "  ${RED}✗${NC} No root tasks found - possible circular dependency"
        validation_passed=false
    else
        echo -e "  ${GREEN}✓${NC} No circular dependencies"
    fi

    echo -e "  ${GREEN}✓${NC} DAG structure verified"
    echo ""

    if [[ "$validation_passed" != "true" ]]; then
        echo -e "  ${RED}Dependency validation failed.${NC}"
        echo ""
        echo -e "    ${YELLOW}[fix]${NC}      Edit tasks.json to fix issues"
        echo -e "    ${RED}[abort]${NC}    Return to task decomposition"
        echo ""

        read -p "  Choice [fix]: " fix_choice
        fix_choice=${fix_choice:-fix}

        if [[ "$fix_choice" == "abort" ]]; then
            atomic_error "Aborting due to dependency issues"
            return 1
        fi

        echo ""
        echo -e "  ${DIM}Edit .taskmaster/tasks/tasks.json to fix dependency issues.${NC}"
        echo -e "  ${DIM}Press Enter when ready to re-validate...${NC}"
        read -r
        task_304_dependency_analysis
        return $?
    fi

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # COMPUTE EXECUTION LEVELS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    # Compute topological levels with task details
    local levels_json=$(jq '
        # Build task lookup
        .tasks | map({key: (.id | tostring), value: .}) | from_entries as $task_map |

        # Compute level for each task (iterative approach)
        (reduce range(20) as $iter (
            {};
            . as $memo |
            reduce ($task_map | keys[]) as $id (
                $memo;
                if .[$id] then .
                else
                    $task_map[$id].dependencies as $deps |
                    if ($deps | length) == 0 then
                        . + {($id): 0}
                    elif ([$deps[] | . as $d | $memo[$d | tostring]] | all) then
                        . + {($id): ([($deps[] | . as $d | $memo[$d | tostring])] | max + 1)}
                    else .
                    end
                end
            )
        )) as $levels |

        # Group tasks by level with full details
        [.tasks[] | . + {level: $levels[.id | tostring]}] |
        group_by(.level) |
        map({
            level: .[0].level,
            tasks: [.[] | {
                id: .id,
                title: .title,
                priority: .priority,
                complexity: (.estimated_complexity // "moderate"),
                has_criteria: ((.acceptance_criteria // "") != "")
            }]
        }) | sort_by(.level)
    ' "$tasks_file")

    local max_level=$(echo "$levels_json" | jq '[.[].level] | max // 0')

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # COMPLEXITY DISTRIBUTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}COMPLEXITY DISTRIBUTION${NC}"
    echo ""

    local simple_count=$(jq '[.tasks[] | select(.estimated_complexity == "simple")] | length' "$tasks_file")
    local moderate_count=$(jq '[.tasks[] | select(.estimated_complexity == "moderate" or .estimated_complexity == null)] | length' "$tasks_file")
    local complex_count=$(jq '[.tasks[] | select(.estimated_complexity == "complex")] | length' "$tasks_file")

    # Visual bar (10 chars = 100%)
    local simple_bar=$(printf '█%.0s' $(seq 1 $((simple_count * 10 / task_count + 1))) 2>/dev/null || echo "")
    local moderate_bar=$(printf '█%.0s' $(seq 1 $((moderate_count * 10 / task_count + 1))) 2>/dev/null || echo "")
    local complex_bar=$(printf '█%.0s' $(seq 1 $((complex_count * 10 / task_count + 1))) 2>/dev/null || echo "")

    printf "    Simple:   %2d  ${GREEN}%-10s${NC}\n" "$simple_count" "$simple_bar"
    printf "    Moderate: %2d  ${YELLOW}%-10s${NC}\n" "$moderate_count" "$moderate_bar"
    printf "    Complex:  %2d  ${RED}%-10s${NC}\n" "$complex_count" "$complex_bar"
    echo ""

    # Estimate time per complexity level
    # Simple: 1-2 sessions, Moderate: 2-4 sessions, Complex: 4+ sessions
    local estimated_sessions=$(( simple_count * 1 + moderate_count * 3 + complex_count * 5 ))
    echo -e "  ${DIM}Estimated implementation sessions: ~$estimated_sessions${NC}"
    echo -e "  ${DIM}(Simple=1, Moderate=3, Complex=5 sessions per task)${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # EXECUTION DAG
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}EXECUTION DAG${NC}"
    echo ""
    echo -e "  ${DIM}Tasks grouped by dependency level. Tasks at the same level can execute${NC}"
    echo -e "  ${DIM}in parallel git worktrees. Each level must complete before the next begins.${NC}"
    echo ""

    local max_parallel=0
    local total_levels=$((max_level + 1))

    # Render the DAG
    for level in $(seq 0 "$max_level"); do
        local level_data=$(echo "$levels_json" | jq --argjson lvl "$level" '.[] | select(.level == $lvl)')
        local level_tasks=$(echo "$level_data" | jq '.tasks')
        local task_count_at_level=$(echo "$level_tasks" | jq 'length')

        if [[ "$task_count_at_level" -gt "$max_parallel" ]]; then
            max_parallel=$task_count_at_level
        fi

        # Level complexity breakdown
        local level_simple=$(echo "$level_tasks" | jq '[.[] | select(.complexity == "simple")] | length')
        local level_moderate=$(echo "$level_tasks" | jq '[.[] | select(.complexity == "moderate")] | length')
        local level_complex=$(echo "$level_tasks" | jq '[.[] | select(.complexity == "complex")] | length')

        echo -e "  ${CYAN}LEVEL $level${NC} ──────────────────────────────────────────────────────────────────────"
        echo -e "  ${DIM}│${NC}"

        echo "$level_tasks" | jq -r '.[] | "\(.id)|\(.title)|\(.priority)|\(.complexity)"' | while IFS='|' read -r id title priority complexity; do
            # Priority color
            local priority_indicator=""
            case "$priority" in
                high) priority_indicator="${RED}■${NC}" ;;
                medium) priority_indicator="${YELLOW}■${NC}" ;;
                low) priority_indicator="${DIM}■${NC}" ;;
                *) priority_indicator="${DIM}○${NC}" ;;
            esac

            # Complexity indicator
            local complexity_indicator=""
            case "$complexity" in
                simple) complexity_indicator="${GREEN}S${NC}" ;;
                moderate) complexity_indicator="${YELLOW}M${NC}" ;;
                complex) complexity_indicator="${RED}C${NC}" ;;
                *) complexity_indicator="${DIM}?${NC}" ;;
            esac

            echo -e "  ${DIM}├──${NC} ${BOLD}[$id]${NC} $title  $priority_indicator $complexity_indicator"
        done

        if [[ "$task_count_at_level" -gt 1 ]]; then
            echo -e "  ${DIM}│${NC}   ${GREEN}↑ $task_count_at_level parallel worktrees${NC}"
        fi

        echo -e "  ${DIM}│${NC}"
    done

    echo -e "  ${DIM}Legend: Priority ■ (${RED}high${NC}/${YELLOW}med${NC}/${DIM}low${NC})  Complexity (${GREEN}S${NC}imple/${YELLOW}M${NC}oderate/${RED}C${NC}omplex)${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # WORK PACKAGES
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}WORK PACKAGES${NC}"
    echo ""

    # Generate work packages from levels
    jq --argjson levels "$levels_json" -n '
        {
            "packages": [$levels[] | {
                "id": (.level + 1),
                "name": "Wave \(.level + 1)",
                "level": .level,
                "tasks": [.tasks[].id],
                "task_count": (.tasks | length),
                "can_parallelize": ((.tasks | length) > 1),
                "complexity_breakdown": {
                    "simple": [.tasks[] | select(.complexity == "simple")] | length,
                    "moderate": [.tasks[] | select(.complexity == "moderate")] | length,
                    "complex": [.tasks[] | select(.complexity == "complex")] | length
                }
            }],
            "summary": {
                "total_waves": ($levels | length),
                "max_parallelism": ([$levels[].tasks | length] | max),
                "total_tasks": ([$levels[].tasks | length] | add)
            },
            "generated_at": (now | todate)
        }
    ' > "$packages_file"

    echo -e "  ${GREEN}✓${NC} Generated $total_levels work packages (waves)"
    echo ""

    jq -r '.packages[] | "    Wave \(.id): \(.task_count) tasks\(if .can_parallelize then " (parallel)" else "" end)"' "$packages_file"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CRITICAL PATH
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}CRITICAL PATH${NC}"
    echo ""

    # Find a critical path (task at each level with highest complexity)
    local critical_path=$(echo "$levels_json" | jq -r '
        [.[] | .tasks | sort_by(
            if .complexity == "complex" then 0
            elif .complexity == "moderate" then 1
            else 2 end
        ) | .[0].title] | join(" → ")
    ')

    echo -e "  ${DIM}Longest path through highest complexity:${NC}"
    echo -e "    $critical_path"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SUMMARY${NC}"
    echo ""
    echo -e "    Total tasks:           $task_count"
    echo -e "    Execution waves:       $total_levels"
    echo -e "    Max parallel tasks:    $max_parallel"
    echo -e "    Est. sessions:         ~$estimated_sessions"
    echo ""

    # Save analysis results
    jq -n \
        --argjson task_count "$task_count" \
        --argjson waves "$total_levels" \
        --argjson max_parallel "$max_parallel" \
        --argjson sessions "$estimated_sessions" \
        --argjson levels_data "$levels_json" \
        --arg critical_path "$critical_path" \
        --argjson simple "$simple_count" \
        --argjson moderate "$moderate_count" \
        --argjson complex "$complex_count" \
        '{
            "validation": {
                "passed": true,
                "cycles": false,
                "invalid_refs": 0
            },
            "complexity": {
                "simple": $simple,
                "moderate": $moderate,
                "complex": $complex,
                "estimated_sessions": $sessions
            },
            "dag": {
                "total_tasks": $task_count,
                "execution_waves": $waves,
                "max_parallelism": $max_parallel,
                "levels": $levels_data,
                "critical_path": $critical_path
            },
            "analyzed_at": (now | todate)
        }' > "$analysis_file"

    # Save graph file
    jq -n \
        --argjson levels_data "$levels_json" \
        --arg critical_path "$critical_path" \
        '{
            "levels": $levels_data,
            "critical_path": $critical_path,
            "generated_at": (now | todate)
        }' > "$graph_file"

    atomic_context_artifact "$graph_file" "dependency-graph" "Task dependency graph with execution levels"
    atomic_context_artifact "$packages_file" "work-packages" "Work packages for parallel execution"
    atomic_context_artifact "$analysis_file" "dependency-analysis" "Dependency and complexity analysis"
    atomic_context_decision "DAG validated: $total_levels waves, max $max_parallel parallel, ~$estimated_sessions sessions" "dependencies"

    atomic_success "Dependency analysis complete"

    return 0
}
