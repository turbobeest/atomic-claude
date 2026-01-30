#!/bin/bash
#
# Task 602: Agent Selection
# Select agents for code review: deep-code-reviewer, arch-compliance, perf-analyzer, doc-reviewer, code-refiner
#

task_602_agent_selection() {
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/review-agents.json"
    local tasks_file="$ATOMIC_ROOT/.taskmaster/tasks/tasks.json"

    atomic_step "Agent Selection"

    mkdir -p "$(dirname "$agents_file")"

    echo ""
    echo -e "  ${DIM}Selecting specialized agents for code review.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # CODE REVIEW AGENT ROLES
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}──────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}CODE REVIEW AGENT ROLES${NC}"
    echo ""

    echo -e "  ${DIM}Five agents work together for comprehensive code review:${NC}"
    echo ""

    # Deep Code Reviewer
    echo -e "  ${CYAN}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}DEEP CODE REVIEWER${NC}"
    echo ""
    echo -e "    Reviews code for correctness, clarity, and maintainability."
    echo -e "    Checks logic, error handling, edge cases, and code smells."
    echo ""
    echo -e "    ${GREEN}Recommended:${NC} deep-code-reviewer-phd (opus)"
    echo -e "    ${DIM}Alternative:${NC} senior-engineer, code-quality-expert"
    echo -e "  ${CYAN}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # Architecture Compliance
    echo -e "  ${MAGENTA}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}ARCHITECTURE COMPLIANCE${NC}"
    echo ""
    echo -e "    Verifies adherence to architectural patterns and design decisions."
    echo -e "    Checks dependency direction, layer separation, coupling."
    echo ""
    echo -e "    ${GREEN}Recommended:${NC} arch-compliance-phd (sonnet)"
    echo -e "    ${DIM}Alternative:${NC} system-architect, design-pattern-expert"
    echo -e "  ${MAGENTA}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # Performance Analyzer
    echo -e "  ${YELLOW}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}PERFORMANCE ANALYZER${NC}"
    echo ""
    echo -e "    Identifies performance bottlenecks and optimization opportunities."
    echo -e "    Reviews algorithmic complexity, memory usage, I/O patterns."
    echo ""
    echo -e "    ${GREEN}Recommended:${NC} perf-analyzer-phd (sonnet)"
    echo -e "    ${DIM}Alternative:${NC} performance-engineer, optimization-specialist"
    echo -e "  ${YELLOW}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # Documentation Reviewer
    echo -e "  ${BLUE}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}DOCUMENTATION REVIEWER${NC}"
    echo ""
    echo -e "    Reviews code comments, API documentation, and README files."
    echo -e "    Ensures documentation matches implementation."
    echo ""
    echo -e "    ${GREEN}Recommended:${NC} doc-reviewer-phd (haiku)"
    echo -e "    ${DIM}Alternative:${NC} technical-writer, api-doc-specialist"
    echo -e "  ${BLUE}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # Code Refiner
    echo -e "  ${GREEN}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "  ${BOLD}CODE REFINER${NC}"
    echo ""
    echo -e "    Applies refinements based on review findings."
    echo -e "    Ensures tests continue to pass after changes."
    echo ""
    echo -e "    ${GREEN}Recommended:${NC} code-refiner-phd (opus)"
    echo -e "    ${DIM}Alternative:${NC} refactoring-specialist, clean-code-expert"
    echo -e "  ${GREEN}──────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # AGENT SELECTION
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}──────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}SELECT AGENTS${NC}"
    echo ""

    # Drain any buffered stdin before agent selection
    atomic_drain_stdin

    # Deep Code Reviewer
    echo -e "  ${CYAN}Deep Code Reviewer${NC}"
    echo -e "    ${GREEN}[1]${NC} deep-code-reviewer-phd (recommended)"
    echo -e "    ${DIM}[2]${NC} senior-engineer"
    echo -e "    ${DIM}[3]${NC} code-quality-expert"
    echo -e "    ${DIM}[c]${NC} Custom agent name"
    echo ""

    read -e -p "    Selection [1]: " deep_choice || true
    deep_choice=${deep_choice:-1}
    case "$deep_choice" in
        2) deep_agent="senior-engineer" ;;
        3) deep_agent="code-quality-expert" ;;
        c|C)
            read -e -p "    Enter custom agent name: " deep_agent || true
            ;;
        *) deep_agent="deep-code-reviewer-phd" ;;
    esac
    echo ""

    # Architecture Compliance
    echo -e "  ${MAGENTA}Architecture Compliance${NC}"
    echo -e "    ${GREEN}[1]${NC} arch-compliance-phd (recommended)"
    echo -e "    ${DIM}[2]${NC} system-architect"
    echo -e "    ${DIM}[3]${NC} design-pattern-expert"
    echo -e "    ${DIM}[c]${NC} Custom agent name"
    echo ""

    read -e -p "    Selection [1]: " arch_choice || true
    arch_choice=${arch_choice:-1}
    case "$arch_choice" in
        2) arch_agent="system-architect" ;;
        3) arch_agent="design-pattern-expert" ;;
        c|C)
            read -e -p "    Enter custom agent name: " arch_agent || true
            ;;
        *) arch_agent="arch-compliance-phd" ;;
    esac
    echo ""

    # Performance Analyzer
    echo -e "  ${YELLOW}Performance Analyzer${NC}"
    echo -e "    ${GREEN}[1]${NC} perf-analyzer-phd (recommended)"
    echo -e "    ${DIM}[2]${NC} performance-engineer"
    echo -e "    ${DIM}[3]${NC} optimization-specialist"
    echo -e "    ${DIM}[c]${NC} Custom agent name"
    echo ""

    read -e -p "    Selection [1]: " perf_choice || true
    perf_choice=${perf_choice:-1}
    case "$perf_choice" in
        2) perf_agent="performance-engineer" ;;
        3) perf_agent="optimization-specialist" ;;
        c|C)
            read -e -p "    Enter custom agent name: " perf_agent || true
            ;;
        *) perf_agent="perf-analyzer-phd" ;;
    esac
    echo ""

    # Documentation Reviewer
    echo -e "  ${BLUE}Documentation Reviewer${NC}"
    echo -e "    ${GREEN}[1]${NC} doc-reviewer-phd (recommended)"
    echo -e "    ${DIM}[2]${NC} technical-writer"
    echo -e "    ${DIM}[3]${NC} api-doc-specialist"
    echo -e "    ${DIM}[c]${NC} Custom agent name"
    echo ""

    read -e -p "    Selection [1]: " doc_choice || true
    doc_choice=${doc_choice:-1}
    case "$doc_choice" in
        2) doc_agent="technical-writer" ;;
        3) doc_agent="api-doc-specialist" ;;
        c|C)
            read -e -p "    Enter custom agent name: " doc_agent || true
            ;;
        *) doc_agent="doc-reviewer-phd" ;;
    esac
    echo ""

    # Code Refiner
    echo -e "  ${GREEN}Code Refiner${NC}"
    echo -e "    ${GREEN}[1]${NC} code-refiner-phd (recommended)"
    echo -e "    ${DIM}[2]${NC} refactoring-specialist"
    echo -e "    ${DIM}[3]${NC} clean-code-expert"
    echo -e "    ${DIM}[c]${NC} Custom agent name"
    echo ""

    read -e -p "    Selection [1]: " refiner_choice || true
    refiner_choice=${refiner_choice:-1}
    case "$refiner_choice" in
        2) refiner_agent="refactoring-specialist" ;;
        3) refiner_agent="clean-code-expert" ;;
        c|C)
            read -e -p "    Enter custom agent name: " refiner_agent || true
            ;;
        *) refiner_agent="code-refiner-phd" ;;
    esac
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # SELECTION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo -e "${DIM}──────────────────────────────────────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    echo -e "  ${BOLD}AGENT SELECTION SUMMARY${NC}"
    echo ""

    echo -e "    ${CYAN}Deep Code:${NC}    $deep_agent"
    echo -e "    ${MAGENTA}Architecture:${NC} $arch_agent"
    echo -e "    ${YELLOW}Performance:${NC}  $perf_agent"
    echo -e "    ${BLUE}Documentation:${NC} $doc_agent"
    echo -e "    ${GREEN}Refiner:${NC}      $refiner_agent"
    echo ""

    # Save agent selection
    jq -n \
        --arg deep "$deep_agent" \
        --arg arch "$arch_agent" \
        --arg perf "$perf_agent" \
        --arg doc "$doc_agent" \
        --arg refiner "$refiner_agent" \
        '{
            "review_agents": {
                "deep_code": { "name": $deep, "model": "opus", "dimension": "code_quality" },
                "architecture": { "name": $arch, "model": "sonnet", "dimension": "architecture" },
                "performance": { "name": $perf, "model": "sonnet", "dimension": "performance" },
                "documentation": { "name": $doc, "model": "haiku", "dimension": "documentation" },
                "refiner": { "name": $refiner, "model": "opus", "dimension": "refinement" }
            },
            "selected_at": (now | todate)
        }' > "$agents_file"

    atomic_context_artifact "$agents_file" "review-agents" "Selected code review agents"
    atomic_context_decision "Review agents: $deep_agent, $arch_agent, $perf_agent, $doc_agent, $refiner_agent" "agent-selection"

    atomic_success "Agent Selection complete"

    return 0
}
