#!/bin/bash
#
# Task 105: Agent Selection (Conversation 3)
# Select agents to guide the pipeline phases
#
# This is a TRUE CONVERSATION about agent selection.
#
# Flow:
#   1. Load agents from turbobeest/agents repository
#   2. Present pipeline agents (phase-specific)
#   3. Suggest expert agents based on project context
#   4. Conversational selection with category browsing
#   5. Map selected agents to pipeline phases
#
# The conversation continues until:
#   - Human has reviewed and approved agent assignments
#   - Or typed 'done' to accept suggestions
#

# ═══════════════════════════════════════════════════════════════════════════════
# AGENT REPOSITORY CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# These will be set from config or defaults
AGENT_REPO=""
AGENT_MANIFEST=""
PIPELINE_AGENTS_DIR=""
EXPERT_AGENTS_DIR=""

# Load agent repo path from Phase 0 config or use defaults
_105_load_agent_config() {
    local setup_config="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
    local default_repo="$ATOMIC_ROOT/repos/agents"

    # Try to load from Phase 0 config
    if [[ -f "$setup_config" ]]; then
        local configured_repo=$(jq -r '.agents.repository // ""' "$setup_config" 2>/dev/null)
        if [[ -n "$configured_repo" && "$configured_repo" != "null" && "$configured_repo" != "builtin" ]]; then
            AGENT_REPO="$configured_repo"
        fi
    fi

    # Fall back to environment variable or default
    AGENT_REPO="${AGENT_REPO:-${AGENT_REPO_PATH:-$default_repo}}"
    AGENT_MANIFEST="$AGENT_REPO/agent-manifest.json"
    PIPELINE_AGENTS_DIR="$AGENT_REPO/pipeline-agents/atomic-claude"
    EXPERT_AGENTS_DIR="$AGENT_REPO/expert-agents"
}

task_105_agent_selection() {
    local dialogue_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/dialogue.json"
    local corpus_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/corpus.json"
    local agents_output="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json"
    local roster_output="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/agent-roster.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"
    local conversation_log="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/agent-selection-log.md"

    # Check for jq dependency
    if ! command -v jq &>/dev/null; then
        atomic_error "jq is required for agent selection"
        echo -e "  ${DIM}Install with: apt install jq / brew install jq / winget install jqlang.jq${NC}"
        return 1
    fi

    atomic_step "Agent Selection"

    # Load agent configuration from Phase 0 or defaults
    _105_load_agent_config

    mkdir -p "$prompts_dir"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ CONVERSATION 3: AGENT SELECTION                         │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Let's select the right agents for your pipeline.       │${NC}"
    echo -e "${DIM}  │ We'll discuss options and assign agents to each phase. │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Type 'done' when you're satisfied with selections.     │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Start conversation log
    cat > "$conversation_log" << 'EOF'
# Agent Selection - Conversation Log

EOF

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 1: VERIFY AGENT REPOSITORY
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AGENT REPOSITORY${NC}                                          ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [[ ! -f "$AGENT_MANIFEST" ]]; then
        echo -e "  ${YELLOW}!${NC} Agent manifest not found at: $AGENT_MANIFEST"
        echo ""
        echo -e "  ${DIM}Would you like to:${NC}"
        echo -e "    ${GREEN}[1]${NC} Clone the agents repository"
        echo -e "    ${GREEN}[2]${NC} Specify a different path"
        echo -e "    ${GREEN}[3]${NC} Continue with built-in defaults"
        echo ""
    atomic_drain_stdin
        read -e -p "  Choice [3]: " repo_choice || true
        repo_choice=${repo_choice:-3}

        case "$repo_choice" in
            1)
                echo ""
                echo -e "  ${DIM}Cloning agents repository...${NC}"
                # Get configured URL or use default
                local agent_repo_url=$(jq -r '.agents.repository_url // "https://github.com/turbobeest/agents"' "$setup_config" 2>/dev/null || echo "https://github.com/turbobeest/agents")
                git clone "$agent_repo_url" "$AGENT_REPO" 2>/dev/null
                if [[ $? -ne 0 ]]; then
                    echo -e "  ${YELLOW}!${NC} Clone failed - using defaults"
                    _105_use_builtin_agents
                    return 0
                fi
                ;;
            2)
                echo ""
                read -e -p "  Agent repository path: " custom_path || true
                if [[ -f "$custom_path/agent-manifest.json" ]]; then
                    AGENT_REPO="$custom_path"
                    AGENT_MANIFEST="$AGENT_REPO/agent-manifest.json"
                    PIPELINE_AGENTS_DIR="$AGENT_REPO/pipeline-agents/atomic-claude"
                    EXPERT_AGENTS_DIR="$AGENT_REPO/expert-agents"
                else
                    echo -e "  ${YELLOW}!${NC} Manifest not found - using defaults"
                    _105_use_builtin_agents
                    return 0
                fi
                ;;
            3)
                _105_use_builtin_agents
                return 0
                ;;
        esac
    fi

    # Load manifest metadata
    local total_agents=$(jq -r '.metadata.totalAgents // "unknown"' "$AGENT_MANIFEST")
    local total_categories=$(jq -r '.metadata.totalCategories // "unknown"' "$AGENT_MANIFEST")

    echo -e "  ${GREEN}✓${NC} Agent repository found: $AGENT_REPO"
    echo -e "    ${DIM}Total agents: $total_agents${NC}"
    echo -e "    ${DIM}Categories: $total_categories${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2: LOAD PIPELINE AGENTS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}PIPELINE AGENTS${NC}                                            ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${DIM}These agents are designed for specific pipeline phases:${NC}"
    echo ""

    # Initialize roster structure
    local roster='{"version": "1.0", "timestamp": "'$(date -Iseconds)'", "phases": {}}'

    # Phase groups from pipeline-agents directory
    declare -A phase_groups=(
        ["01-02-ideation-discovery"]="1:Discovery"
        ["03-05-validation-planning"]="2:PRD,3:Tasks,4:Spec,5:TDD-Planning"
        ["06-09-implementation"]="6:Review,7:Integration,8:Validation"
        ["10-testing"]="9:Testing"
        ["11-12-deployment"]="10:Deployment"
    )

    # Load and display pipeline agents by phase group
    for group_dir in "${!phase_groups[@]}"; do
        local full_path="$PIPELINE_AGENTS_DIR/$group_dir"
        if [[ -d "$full_path" ]]; then
            echo -e "  ${CYAN}$group_dir:${NC}"

            for agent_file in "$full_path"/*.md; do
                [[ -f "$agent_file" ]] || continue

                local agent_name=$(grep -m1 '^name:' "$agent_file" | sed 's/name:[[:space:]]*//')
                local agent_desc=$(grep -m1 '^description:' "$agent_file" | sed 's/description:[[:space:]]*//' | cut -c1-60)
                local agent_model=$(grep -m1 '^model:' "$agent_file" | sed 's/model:[[:space:]]*//')
                local agent_tier=$(grep -m1 '^tier:' "$agent_file" | sed 's/tier:[[:space:]]*//')

                [[ -z "$agent_name" ]] && continue

                echo -e "    ${GREEN}•${NC} ${BOLD}$agent_name${NC} ${DIM}($agent_model, $agent_tier)${NC}"
                [[ -n "$agent_desc" ]] && echo -e "      ${DIM}$agent_desc...${NC}"
            done
            echo ""
        fi
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 3: SUGGEST AGENTS BASED ON PROJECT CONTEXT
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}SUGGESTED AGENTS FOR YOUR PROJECT${NC}                         ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Gather project context from dialogue
    local tech_stack=""
    local compliance=""
    local project_domain=""

    if [[ -f "$dialogue_file" ]]; then
        tech_stack=$(jq -r '.synthesis.constraints.tech_stack // ""' "$dialogue_file" 2>/dev/null)
        compliance=$(jq -r '.synthesis.constraints.compliance // [] | join(",")' "$dialogue_file" 2>/dev/null)
        project_domain=$(jq -r '.synthesis.vision.solution_concept // ""' "$dialogue_file" 2>/dev/null)
    fi

    # Build agent suggestion prompt
    local suggestion_prompt="$prompts_dir/agent-suggestion.md"

    # Extract full agent list from manifest, grouped by category/subcategory
    local agent_list=""
    if [[ -f "$AGENT_MANIFEST" ]]; then
        agent_list=$(jq -r '
            .agents | group_by(.category) | map(
                "### " + .[0].category + "\n" +
                (group_by(.subcategory) | map(
                    (if .[0].subcategory != "" then "**" + .[0].subcategory + ":**\n" else "" end) +
                    (map("- " + .name + " (" + .tier + "): " + (.description | .[0:70])) | join("\n"))
                ) | join("\n\n"))
            ) | join("\n\n---\n\n")
        ' "$AGENT_MANIFEST" 2>/dev/null)
    fi

    # Fallback if manifest parsing fails
    if [[ -z "$agent_list" ]]; then
        agent_list="(Agent manifest not available - suggest based on common patterns)"
    fi

    cat > "$suggestion_prompt" << EOF
# Task: Suggest Expert Agents for Development Pipeline

You are an **agent-selector** specializing in matching project requirements to available AI agents. Your role is to analyze project context and recommend the most valuable agents from the available catalog.

## Project Context

**Tech Stack**: ${tech_stack:-"Not specified"}
**Compliance Requirements**: ${compliance:-"None specified"}
**Project Domain**: ${project_domain:-"General software development"}

## Available Expert Agents

**CRITICAL**: You may ONLY suggest agents from this list. Do not invent agent names.
If the list is empty or says "not available", suggest common agent types with a note that they need verification.

$agent_list

## Selection Criteria

Prioritize agents that:
1. Match the tech stack (e.g., if using Go, suggest Go-specific agents)
2. Address compliance needs (e.g., security-auditor for SOC2 projects)
3. Cover critical development phases (testing, code review, deployment)
4. Fill gaps in the default pipeline agents

## Output Format

Output ONLY valid JSON (no markdown wrapper, no explanation text):

\`\`\`json
{
    "suggested_agents": [
        {"name": "exact-agent-name-from-list", "reason": "Why relevant to THIS project"}
    ],
    "gaps": ["Description of capability gaps not covered"]
}
\`\`\`

## Example Output

For a Node.js e-commerce project with PCI compliance:

{
    "suggested_agents": [
        {"name": "security-auditor", "reason": "PCI compliance requires security validation"},
        {"name": "api-designer", "reason": "E-commerce needs well-designed REST APIs"},
        {"name": "performance-analyst", "reason": "Transaction throughput is critical"},
        {"name": "test-strategist", "reason": "Payment flows need comprehensive test coverage"},
        {"name": "code-reviewer", "reason": "Quality gate for financial code"}
    ],
    "gaps": ["No PCI-DSS specific compliance agent available"]
}

## Edge Cases

- If agent list is empty: Return {"suggested_agents": [], "gaps": ["Agent manifest unavailable"]}
- If project context is vague: Suggest general-purpose agents (code-reviewer, test-strategist)
- If tech stack is unusual: Note in gaps that specialized agents may be needed
EOF

    echo -e "  ${DIM}Analyzing project context for agent suggestions...${NC}"
    echo ""

    local suggested_agents_json=""
    local suggestion_file="$prompts_dir/suggested-agents.json"

    if atomic_invoke "$suggestion_prompt" "$suggestion_file" "Suggest agents" --format=json; then
        # Try to parse JSON response
        if jq -e '.suggested_agents' "$suggestion_file" &>/dev/null; then
            suggested_agents_json=$(cat "$suggestion_file")

            # Only display formatted summary if not already streamed
            if [[ "${ATOMIC_STREAM:-true}" != "true" || ! -t 2 ]]; then
                echo -e "  ${GREEN}Recommended agents:${NC}"
                echo ""

                # Display each suggested agent
                echo "$suggested_agents_json" | jq -r '.suggested_agents[] | "    \u001b[32m•\u001b[0m \u001b[1m\(.name)\u001b[0m: \(.reason)"'

                # Display gaps if any
                local gaps=$(echo "$suggested_agents_json" | jq -r '.gaps[]? // empty')
                if [[ -n "$gaps" ]]; then
                    echo ""
                    echo -e "  ${YELLOW}Capability gaps identified:${NC}"
                    echo "$suggested_agents_json" | jq -r '.gaps[] | "    ! \(.)"'
                fi
            fi

            # Pre-populate selected_experts from suggestions
            while IFS= read -r agent_name; do
                [[ -n "$agent_name" ]] && selected_experts+=("$agent_name")
            done < <(echo "$suggested_agents_json" | jq -r '.suggested_agents[].name')
        else
            # JSON parsing failed, try to extract from text
            echo -e "  ${YELLOW}!${NC} Parsing suggestions..."
            cat "$suggestion_file" | head -20 | while IFS= read -r line; do
                echo -e "    $line"
            done
        fi
    else
        # Fallback suggestions
        echo -e "  ${DIM}Using default suggestions based on common patterns...${NC}"
        echo ""
        echo -e "    ${GREEN}•${NC} ${BOLD}code-reviewer${NC}: Code quality validation"
        echo -e "    ${GREEN}•${NC} ${BOLD}security-auditor${NC}: Security validation"
        echo -e "    ${GREEN}•${NC} ${BOLD}test-strategist${NC}: Test coverage planning"
        echo -e "    ${GREEN}•${NC} ${BOLD}tdd-implementation-agent${NC}: Test-driven development"

        # Add fallback defaults to selected
        selected_experts+=("code-reviewer" "security-auditor" "test-strategist" "tdd-implementation-agent")
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 4: CONVERSATIONAL AGENT SELECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AGENT SELECTION CONVERSATION${NC}                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local conversation_complete=false
    local turn=0
    local selected_experts=()

    # Agent opens with a question
    local agent_opening="Based on your project, I've suggested some expert agents above. Would you like to:

1. Accept these suggestions and proceed to phase mapping
2. Browse agent categories to explore options
3. Search for specific agent types
4. Tell me what kind of expertise you need

What would work best for you?"

    echo -e "  ${CYAN}Agent:${NC}"
    echo ""
    echo "$agent_opening" | fold -s -w 60 | while IFS= read -r line; do
        echo -e "    $line"
    done
    echo ""

    # Log opening
    echo "## Turn 1" >> "$conversation_log"
    echo "" >> "$conversation_log"
    echo "**Agent:** $agent_opening" >> "$conversation_log"
    echo "" >> "$conversation_log"

    while [[ "$conversation_complete" == false ]]; do
        echo -e "  ${GREEN}You:${NC}"
        read -e -p "    " human_response || true

        # Check for exit
        if [[ "${human_response,,}" =~ ^(done|finished|accept|1)$ ]]; then
            conversation_complete=true
            break
        fi

        # Log human response
        echo "**Human:** $human_response" >> "$conversation_log"
        echo "" >> "$conversation_log"
        ((turn++))

        # Handle browse request
        if [[ "${human_response,,}" =~ (browse|categories|explore|2) ]]; then
            _105_browse_categories
            continue
        fi

        # Handle search request
        if [[ "${human_response,,}" =~ (search|find|3) ]]; then
            echo ""
            read -e -p "    Search term: " search_term || true
            _105_search_agents "$search_term"
            continue
        fi

        # Generate agent response based on human input
        # Include actual agent names so LLM can make valid suggestions
        local available_agents_list=""
        if [[ -f "$AGENT_MANIFEST" ]]; then
            available_agents_list=$(jq -r '
                [.categories[].subcategories[].agents[]] | unique | sort | join(", ")
            ' "$AGENT_MANIFEST" 2>/dev/null)
        fi

        cat > "$prompts_dir/agent-response.md" << EOF
# Task: Continue Agent Selection Conversation

You are an **agent-selector assistant** helping a developer choose agents for their pipeline. Be conversational, helpful, and specific.

## Human Input

"$human_response"

## Current State

- Already selected agents: $(printf '%s\n' "${selected_experts[@]}" | paste -sd, - || echo "none yet")
- Phase: Agent selection for development pipeline

## Available Agents (ONLY suggest from this list)

$available_agents_list

## Response Guidelines

1. **If they describe a need**: Suggest 1-3 SPECIFIC agents from the list with brief reasons
2. **If they mention an agent name**: Confirm it exists in the list (or note if it doesn't)
3. **If they're unsure**: Offer to browse categories or explain agent types
4. **If they want to proceed**: Confirm their selections and offer to move to phase mapping

## Response Format

Keep response concise (3-5 sentences). Format agent suggestions as:
"I recommend **agent-name** because [specific reason for THIS project]."

## Example Responses

User says "I need help with security":
"For security, I recommend **security-auditor** for vulnerability scanning and **penetration-tester** for active testing. Would you like to add these to your selection?"

User says "what's a code-reviewer do":
"The **code-reviewer** agent analyzes code changes for quality, patterns, and potential issues before merge. It's useful in Phase 6 (Code Review). Want me to add it?"

User mentions unknown agent:
"I don't see 'magic-fixer' in the available agents. Did you mean **bug-fixer** or **auto-repair**? Or I can search for similar agents."
EOF

        atomic_waiting "Thinking..."

        local agent_response=""
        local _response_streamed=false
        if atomic_invoke "$prompts_dir/agent-response.md" "$prompts_dir/response.txt" "Generate response"; then
            agent_response=$(cat "$prompts_dir/response.txt")
            [[ "${ATOMIC_STREAM:-true}" == "true" && -t 2 ]] && _response_streamed=true
        else
            agent_response="I can help with that. Would you like me to suggest agents for that specific need, or would you prefer to browse the available categories?"
        fi

        echo ""
        echo -e "  ${CYAN}Agent:${NC}"
        echo ""
        if [[ "$_response_streamed" != true ]]; then
            echo "$agent_response" | fold -s -w 60 | while IFS= read -r line; do
                echo -e "    $line"
            done
            echo ""
        fi

        # Log agent response
        echo "## Turn $((turn + 1))" >> "$conversation_log"
        echo "" >> "$conversation_log"
        echo "**Agent:** $agent_response" >> "$conversation_log"
        echo "" >> "$conversation_log"

        # Check for agent additions - validate against manifest
        if [[ "${human_response,,}" =~ (add|select|want|yes|include) ]]; then
            # Get all valid agent names from manifest
            local valid_agents=""
            if [[ -f "$AGENT_MANIFEST" ]]; then
                valid_agents=$(jq -r '[.categories[].subcategories[].agents[]] | unique | .[]' "$AGENT_MANIFEST" 2>/dev/null)
            fi

            # Check each word in response against valid agents
            for word in $human_response; do
                # Normalize: lowercase, remove punctuation
                local normalized=$(echo "$word" | tr '[:upper:]' '[:lower:]' | tr -d '.,!?')

                # Check if it's a valid agent name
                if echo "$valid_agents" | grep -qx "$normalized"; then
                    # Not already selected?
                    if ! printf '%s\n' "${selected_experts[@]}" | grep -q "^${normalized}$"; then
                        selected_experts+=("$normalized")
                        echo -e "    ${GREEN}✓${NC} Added: $normalized"
                    fi
                fi
            done
        fi

        ((turn++))

        # Suggest wrapping up after several turns
        if [[ $turn -ge 6 ]]; then
            echo ""
            echo -e "    ${DIM}(We've discussed several options. Type 'done' to proceed to phase mapping)${NC}"
            echo ""
        fi
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 5: PHASE MAPPING
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}PHASE MAPPING${NC}                                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${DIM}Assigning agents to pipeline phases...${NC}"
    echo ""

    # Define default phase-to-agent mapping
    declare -A default_phase_agents=(
        ["1"]="discovery-agent,ideation-agent"
        ["2"]="prd-validator,prd-auditor"
        ["3"]="task-decomposer"
        ["4"]="specification-agent,coupling-analyzer"
        ["5"]="test-strategist,tdd-implementation-agent"
        ["6"]="code-review-gate"
        ["7"]="plan-guardian"
        ["8"]="integration-testing-gate"
        ["9"]="e2e-testing-gate"
        ["10"]="deployment-gate"
    )

    declare -A phase_names=(
        ["1"]="Discovery"
        ["2"]="PRD"
        ["3"]="Tasks"
        ["4"]="Specification"
        ["5"]="TDD Planning"
        ["6"]="Code Review"
        ["7"]="Integration"
        ["8"]="Validation"
        ["9"]="Testing"
        ["10"]="Deployment"
    )

    # Build roster JSON
    for phase_num in {1..10}; do
        local agents="${default_phase_agents[$phase_num]:-}"
        local phase_name="${phase_names[$phase_num]}"

        echo -e "  ${CYAN}Phase $phase_num - $phase_name:${NC}"

        IFS=',' read -ra agent_list <<< "$agents"
        for agent in "${agent_list[@]}"; do
            [[ -z "$agent" ]] && continue
            echo -e "    ${GREEN}•${NC} $agent"
        done

        # Add selected experts to relevant phases
        if [[ $phase_num -ge 5 && $phase_num -le 8 ]]; then
            for expert in "${selected_experts[@]}"; do
                echo -e "    ${GREEN}•${NC} $expert ${DIM}(expert)${NC}"
                agents="$agents,$expert"
            done
        fi

        # Add to roster JSON
        roster=$(echo "$roster" | jq --arg phase "$phase_num" --arg name "$phase_name" --arg agents "$agents" \
            '.phases[$phase] = {"name": $name, "agents": ($agents | split(",") | map(select(length > 0)))}')

        echo ""
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 6: REVIEW AND CONFIRM
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}ROSTER REVIEW${NC}                                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${DIM}Here's your agent roster for the pipeline:${NC}"
    echo ""

    # Display roster summary
    echo "$roster" | jq -r '.phases | to_entries[] | "  Phase \(.key) (\(.value.name)): \(.value.agents | join(", "))"'
    echo ""

    echo -e "  ${DIM}Does this roster look good? [Y/n]${NC}"
    read -e -p "  > " confirm || true

    if [[ "${confirm,,}" =~ ^n ]]; then
        echo ""
        echo -e "  ${DIM}What would you like to change?${NC}"
        read -e -p "  > " changes || true

        # Record the requested changes
        roster=$(echo "$roster" | jq --arg changes "$changes" '.human_feedback = $changes')
        echo -e "  ${GREEN}✓${NC} Changes noted for review"
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 7: SAVE OUTPUTS
    # ═══════════════════════════════════════════════════════════════════════════

    # Build selected agents output
    local agents_json
    agents_json=$(jq -n \
        --argjson core '[{"name": "orchestrator", "description": "Pipeline orchestration", "model": "opus"}, {"name": "agent-selector", "description": "Agent assignment", "model": "opus"}]' \
        --argjson experts "$(printf '%s\n' "${selected_experts[@]}" | jq -R . | jq -s .)" \
        --arg timestamp "$(date -Iseconds)" \
        '{
            "version": "1.0",
            "timestamp": $timestamp,
            "core": $core,
            "selected_experts": $experts,
            "total_experts": ($experts | length)
        }')

    echo "$agents_json" | jq . > "$agents_output"
    echo "$roster" | jq . > "$roster_output"

    # Summary
    local core_count=$(echo "$agents_json" | jq '.core | length')
    local expert_count=$(echo "$agents_json" | jq '.selected_experts | length')

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Agent Selection Complete${NC}"
    echo ""
    echo -e "  Core agents:      $core_count"
    echo -e "  Expert agents:    $expert_count"
    echo -e "  Phases mapped:    10"
    echo ""

    atomic_context_artifact "selected_agents" "$agents_output" "Selected agents for pipeline"
    atomic_context_artifact "agent_roster" "$roster_output" "Agent roster by phase"
    atomic_context_artifact "agent_conversation" "$conversation_log" "Agent selection conversation"
    atomic_context_decision "Selected $expert_count expert agents and mapped to 10 phases" "agent_selection"

    atomic_success "Agent selection complete"

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_105_browse_categories() {
    echo ""
    echo -e "  ${CYAN}Agent Categories:${NC}"
    echo ""

    local categories=$(jq -r '.categories | to_entries | .[] | "\(.key)|\(.value.title)"' "$AGENT_MANIFEST")
    local i=1

    while IFS='|' read -r key title; do
        echo -e "    ${GREEN}[$i]${NC} $title"
        ((i++))
    done <<< "$categories"

    echo ""
    read -e -p "    Select category [1-8]: " cat_choice || true

    # Get the category key by index
    local cat_key=$(jq -r ".categories | keys[$((cat_choice - 1))]" "$AGENT_MANIFEST")

    if [[ -n "$cat_key" && "$cat_key" != "null" ]]; then
        echo ""
        echo -e "  ${CYAN}Agents in $(jq -r ".categories[\"$cat_key\"].title" "$AGENT_MANIFEST"):${NC}"
        echo ""

        # List subcategories and their agents
        jq -r ".categories[\"$cat_key\"].subcategories | to_entries[] | \"  \\(.value.title):\n\" + (.value.agents | map(\"    • \" + .) | join(\"\n\"))" "$AGENT_MANIFEST"
    fi
    echo ""
}

_105_search_agents() {
    local search_term="$1"
    echo ""
    echo -e "  ${DIM}Searching for '$search_term'...${NC}"
    echo ""

    # Search in manifest
    local results=$(jq -r --arg term "$search_term" '
        .categories | to_entries[] |
        .value.subcategories | to_entries[] |
        .value.agents[] | select(. | test($term; "i"))
    ' "$AGENT_MANIFEST" 2>/dev/null | sort -u)

    if [[ -n "$results" ]]; then
        echo -e "  ${GREEN}Found:${NC}"
        echo "$results" | while read -r agent; do
            echo -e "    • $agent"
        done
    else
        echo -e "  ${DIM}No agents found matching '$search_term'${NC}"
    fi
    echo ""
}

_105_use_builtin_agents() {
    echo ""
    echo -e "  ${DIM}Using built-in agent definitions...${NC}"
    echo ""

    # Simplified agent selection without external repository
    local agents_output="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json"
    local roster_output="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/agent-roster.json"

    # Built-in core agents
    local agents_json='{
        "version": "1.0",
        "timestamp": "'$(date -Iseconds)'",
        "core": [
            {"name": "orchestrator", "description": "Pipeline orchestration", "model": "opus"},
            {"name": "discovery-facilitator", "description": "Guides discovery process", "model": "sonnet"},
            {"name": "first-principles-analyst", "description": "Challenges assumptions", "model": "sonnet"}
        ],
        "selected_experts": [],
        "note": "Using built-in defaults - external agent repository not available"
    }'

    local roster='{
        "version": "1.0",
        "timestamp": "'$(date -Iseconds)'",
        "phases": {
            "1": {"name": "Discovery", "agents": ["discovery-facilitator", "first-principles-analyst"]},
            "2": {"name": "PRD", "agents": ["prd-writer", "validator"]},
            "3": {"name": "Tasks", "agents": ["task-decomposer"]},
            "4": {"name": "Specification", "agents": ["spec-writer"]},
            "5": {"name": "TDD Planning", "agents": ["test-strategist"]},
            "6": {"name": "Code Review", "agents": ["code-reviewer"]},
            "7": {"name": "Integration", "agents": ["integrator"]},
            "8": {"name": "Validation", "agents": ["validator"]},
            "9": {"name": "Testing", "agents": ["tester"]},
            "10": {"name": "Deployment", "agents": ["deployer"]}
        },
        "note": "Default roster - customize in phase 1"
    }'

    echo "$agents_json" | jq . > "$agents_output"
    echo "$roster" | jq . > "$roster_output"

    echo -e "  ${GREEN}✓${NC} Created default agent selection"
    echo -e "  ${GREEN}✓${NC} Created default phase roster"
    echo ""

    atomic_context_artifact "selected_agents" "$agents_output" "Default agent selection"
    atomic_context_artifact "agent_roster" "$roster_output" "Default agent roster"

    atomic_success "Agent selection complete (defaults)"

    return 0
}
