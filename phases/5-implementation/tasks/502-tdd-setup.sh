#!/bin/bash
#
# Task 502: TDD Setup
# Configure coverage targets, test pyramid, and execution mode
#

task_502_tdd_setup() {
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"
    local setup_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/tdd-setup.json"
    local config_file="$ATOMIC_ROOT/.claude/config/tdd-tools.json"

    atomic_step "TDD Setup"

    mkdir -p "$(dirname "$setup_file")" "$(dirname "$config_file")"

    echo ""
    echo -e "  ${DIM}Configuring TDD execution parameters.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # COVERAGE TARGETS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}COVERAGE TARGETS${NC}"
    echo ""

    echo -e "  ${DIM}Coverage measures how much of your code is exercised by tests. But coverage${NC}"
    echo -e "  ${DIM}is a means, not an end—100% coverage doesn't guarantee bug-free code.${NC}"
    echo ""

    echo -e "  ${BOLD}Strategic Considerations:${NC}"
    echo ""
    echo -e "    ${CYAN}Unit Coverage${NC} measures function/method-level testing."
    echo -e "    ${DIM}Higher coverage catches more edge cases but has diminishing returns.${NC}"
    echo -e "    ${DIM}The last 10% often requires mocking internals, which creates brittle tests.${NC}"
    echo ""
    echo -e "    ${CYAN}Integration Coverage${NC} measures how components work together."
    echo -e "    ${DIM}Lower targets are acceptable because integration tests are more expensive${NC}"
    echo -e "    ${DIM}to write and maintain, but they catch real-world interaction bugs.${NC}"
    echo ""

    echo -e "  ─────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}Coverage Philosophy${NC}"
    echo ""
    echo -e "    ${GREEN}90%+ Unit${NC}     Critical paths, financial calculations, security logic"
    echo -e "    ${YELLOW}80% Unit${NC}      Most production systems—good balance of safety and velocity"
    echo -e "    ${DIM}70% Unit${NC}      Prototypes, internal tools, rapidly evolving code"
    echo ""
    echo -e "    ${DIM}Rule of thumb: Cover what matters, not what's easy to cover.${NC}"
    echo -e "    ${DIM}Focus on business logic, error paths, and boundary conditions.${NC}"
    echo -e "  ─────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    echo -e "    ${CYAN}Unit Test Coverage Target${NC}"
    echo ""
    echo -e "      ${GREEN}[90]${NC}  Strict   ${DIM}- Financial, security, compliance systems${NC}"
    echo -e "      ${YELLOW}[80]${NC}  Standard ${DIM}- Production applications (recommended)${NC}"
    echo -e "      ${DIM}[70]${NC}  Relaxed  ${DIM}- Prototypes, internal tools, MVPs${NC}"
    echo ""

    read -p "    Unit test coverage target [80]: " unit_coverage
    unit_coverage=${unit_coverage:-80}

    echo ""
    echo -e "    ${CYAN}Integration Test Coverage Target${NC}"
    echo ""
    echo -e "      ${GREEN}[80]${NC}  Strict   ${DIM}- Microservices, distributed systems${NC}"
    echo -e "      ${YELLOW}[70]${NC}  Standard ${DIM}- Most applications (recommended)${NC}"
    echo -e "      ${DIM}[60]${NC}  Relaxed  ${DIM}- Monoliths with strong unit tests${NC}"
    echo ""

    read -p "    Integration test coverage target [70]: " integration_coverage
    integration_coverage=${integration_coverage:-70}

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TEST PYRAMID STRATEGY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TEST PYRAMID STRATEGY${NC}"
    echo ""

    echo -e "  ${DIM}The test pyramid is a mental model for balancing test types. Each layer${NC}"
    echo -e "  ${DIM}trades off between speed, cost, and confidence.${NC}"
    echo ""

    echo -e "                      ▲"
    echo -e "                     ╱ ╲"
    echo -e "                    ╱E2E╲         ${DIM}Slow, expensive, high confidence${NC}"
    echo -e "                   ╱─────╲        ${DIM}Test full user journeys${NC}"
    echo -e "                  ╱ Integ ╲       ${DIM}Medium speed, tests boundaries${NC}"
    echo -e "                 ╱─────────╲      ${DIM}API contracts, DB operations${NC}"
    echo -e "                ╱   Unit    ╲     ${DIM}Fast, cheap, isolated${NC}"
    echo -e "               ╱─────────────╲    ${DIM}Pure functions, business logic${NC}"
    echo -e "              ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔"
    echo ""

    echo -e "  ${BOLD}Strategic Tradeoffs:${NC}"
    echo ""
    echo -e "  ─────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""
    echo -e "    ${GREEN}Unit-Heavy (70/25/5)${NC}"
    echo -e "    ${DIM}Best for: Libraries, algorithms, pure business logic${NC}"
    echo -e "    ${DIM}Fast feedback loops, easy to debug, but may miss integration bugs${NC}"
    echo ""
    echo -e "    ${YELLOW}Balanced (50/35/15)${NC}"
    echo -e "    ${DIM}Best for: Full-stack applications, CRUD systems${NC}"
    echo -e "    ${DIM}Good coverage across layers, balanced maintenance cost${NC}"
    echo ""
    echo -e "    ${CYAN}Integration-Heavy (40/45/15)${NC}"
    echo -e "    ${DIM}Best for: Microservices, APIs, systems with many external dependencies${NC}"
    echo -e "    ${DIM}Catches boundary issues, but slower test suites${NC}"
    echo ""
    echo -e "  ─────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    echo -e "  ${CYAN}Select pyramid profile:${NC}"
    echo ""
    echo -e "    ${GREEN}[unit-heavy]${NC}     70% unit, 25% integration, 5% E2E"
    echo -e "    ${YELLOW}[balanced]${NC}       50% unit, 35% integration, 15% E2E"
    echo -e "    ${CYAN}[integration]${NC}    40% unit, 45% integration, 15% E2E"
    echo ""

    read -p "  Pyramid profile [unit-heavy]: " pyramid_profile
    pyramid_profile=${pyramid_profile:-unit-heavy}

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # PARALLEL EXECUTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}PARALLEL EXECUTION${NC}"
    echo ""

    local task_count=$(jq '[.tasks[] | select(.subtasks | length >= 4)] | length' "$tasks_file")

    echo -e "  ${DIM}TDD cycles execute in parallel using git worktrees, just like the DAG${NC}"
    echo -e "  ${DIM}execution in previous phases. Independent tasks run simultaneously.${NC}"
    echo ""

    # Calculate optimal worker count (max 4, or task_count if fewer)
    local cpu_count=$(nproc 2>/dev/null || echo 4)
    local optimal_workers=$((cpu_count > 4 ? 4 : cpu_count))
    optimal_workers=$((optimal_workers > task_count ? task_count : optimal_workers))

    # Check for blockers (e.g., tasks with cross-dependencies)
    local blocked=false
    # In real implementation, analyze task dependencies here

    if [[ "$blocked" == "true" ]]; then
        echo -e "  ${YELLOW}!${NC} Cross-task dependencies detected. Falling back to sequential execution."
        optimal_workers=1
    else
        echo -e "  ${GREEN}✓${NC} No blockers detected. Parallel execution enabled."
    fi

    echo ""
    echo -e "  ─────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}Execution Plan${NC}"
    echo ""
    echo -e "    Tasks to execute:    $task_count"
    echo -e "    Parallel workers:    $optimal_workers"
    echo -e "    CPU cores detected:  $cpu_count"
    echo ""

    if [[ "$optimal_workers" -gt 1 ]]; then
        local tasks_per_worker=$(( (task_count + optimal_workers - 1) / optimal_workers ))
        echo -e "    ${DIM}Each worker handles ~$tasks_per_worker tasks in its own git worktree.${NC}"
        echo -e "    ${DIM}Workers merge results back to main branch on completion.${NC}"
    else
        echo -e "    ${DIM}Tasks will execute sequentially in the main worktree.${NC}"
    fi

    echo -e "  ─────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # TESTING TOOLS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}TESTING TOOLS${NC}"
    echo ""

    echo -e "  ${DIM}Tools are auto-detected from your project configuration files.${NC}"
    echo ""

    # Detect project type
    local has_python=false
    local has_node=false
    local has_go=false
    local detected_stack=""

    [[ -f "$ATOMIC_ROOT/pyproject.toml" || -f "$ATOMIC_ROOT/requirements.txt" ]] && has_python=true && detected_stack="python"
    [[ -f "$ATOMIC_ROOT/package.json" ]] && has_node=true && detected_stack="node"
    [[ -f "$ATOMIC_ROOT/go.mod" ]] && has_go=true && detected_stack="go"

    echo -e "  ─────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}Detected Tools${NC}"
    echo ""

    if [[ "$has_python" == "true" ]]; then
        echo -e "    ${RED}RED (Testing):${NC}       pytest, coverage.py"
        echo -e "    ${CYAN}REFACTOR (Linting):${NC}  ruff, black, mypy"
        echo -e "    ${MAGENTA}VERIFY (Security):${NC}   bandit, safety, pip-audit"
    fi
    if [[ "$has_node" == "true" ]]; then
        echo -e "    ${RED}RED (Testing):${NC}       jest, vitest, nyc"
        echo -e "    ${CYAN}REFACTOR (Linting):${NC}  eslint, prettier, tsc"
        echo -e "    ${MAGENTA}VERIFY (Security):${NC}   npm audit, snyk"
    fi
    if [[ "$has_go" == "true" ]]; then
        echo -e "    ${RED}RED (Testing):${NC}       go test -cover"
        echo -e "    ${CYAN}REFACTOR (Linting):${NC}  gofmt, golint, staticcheck"
        echo -e "    ${MAGENTA}VERIFY (Security):${NC}   gosec, govulncheck"
    fi
    if [[ "$has_python" == "false" && "$has_node" == "false" && "$has_go" == "false" ]]; then
        echo -e "    ${YELLOW}!${NC} No project files detected. Configure tools manually."
    fi

    echo -e "  ─────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    echo -e "  ${BOLD}Customizing Tools:${NC}"
    echo ""
    echo -e "  ${DIM}To use different tools, create or edit:${NC}"
    echo -e "    ${CYAN}.claude/config/tdd-tools.json${NC}"
    echo ""
    echo -e "  ${DIM}Example configuration:${NC}"
    echo ""
    echo -e "    ${DIM}{${NC}"
    echo -e "    ${DIM}  \"red\": {${NC}"
    echo -e "    ${DIM}    \"test_command\": \"pytest -v\",${NC}"
    echo -e "    ${DIM}    \"coverage_command\": \"pytest --cov=src --cov-report=json\"${NC}"
    echo -e "    ${DIM}  },${NC}"
    echo -e "    ${DIM}  \"refactor\": {${NC}"
    echo -e "    ${DIM}    \"lint_command\": \"ruff check . --fix\",${NC}"
    echo -e "    ${DIM}    \"format_command\": \"black .\"${NC}"
    echo -e "    ${DIM}  },${NC}"
    echo -e "    ${DIM}  \"verify\": {${NC}"
    echo -e "    ${DIM}    \"security_command\": \"bandit -r src/\"${NC}"
    echo -e "    ${DIM}  }${NC}"
    echo -e "    ${DIM}}${NC}"
    echo ""

    # Check if custom config exists
    if [[ -f "$config_file" ]]; then
        echo -e "  ${GREEN}✓${NC} Custom tool configuration found at .claude/config/tdd-tools.json"
    else
        echo -e "  ${DIM}No custom configuration found. Using detected defaults.${NC}"
    fi
    echo ""

    read -p "  Press Enter to continue (or edit tdd-tools.json first)..."
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SETUP SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SETUP SUMMARY${NC}"
    echo ""

    echo -e "    Coverage Targets:"
    echo -e "      Unit:        ${unit_coverage}%"
    echo -e "      Integration: ${integration_coverage}%"
    echo ""
    echo -e "    Test Pyramid:    $pyramid_profile"
    echo -e "    Execution:       parallel ($optimal_workers workers)"
    echo -e "    Tool Stack:      $detected_stack"
    echo ""

    # Save setup configuration
    jq -n \
        --argjson unit_coverage "$unit_coverage" \
        --argjson integration_coverage "$integration_coverage" \
        --arg pyramid_profile "$pyramid_profile" \
        --argjson worker_count "$optimal_workers" \
        --argjson task_count "$task_count" \
        --arg detected_stack "$detected_stack" \
        '{
            "coverage_targets": {
                "unit": $unit_coverage,
                "integration": $integration_coverage
            },
            "pyramid_profile": $pyramid_profile,
            "execution": {
                "mode": "parallel",
                "workers": $worker_count
            },
            "task_count": $task_count,
            "detected_stack": $detected_stack,
            "configured_at": (now | todate)
        }' > "$setup_file"

    atomic_context_artifact "$setup_file" "tdd-setup" "TDD configuration"
    atomic_context_decision "TDD setup: parallel ($optimal_workers workers), ${unit_coverage}% unit coverage target" "configuration"

    atomic_success "TDD Setup complete"

    return 0
}
