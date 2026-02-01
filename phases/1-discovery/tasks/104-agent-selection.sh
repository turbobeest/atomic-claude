#!/bin/bash
#
# Task 104: Agent Selection (Conversation 2)
# Select agents to guide the pipeline phases - NOW BEFORE DIALOGUE
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
    local embedded_repo="$ATOMIC_ROOT/agents"
    local default_repo="${ATOMIC_ORCHESTRATOR:-$ATOMIC_ROOT}/agents"

    # Try to load from Phase 0 config
    if [[ -f "$setup_config" ]]; then
        local configured_repo=$(jq -r '.agents.repository // ""' "$setup_config" 2>/dev/null)
        if [[ -n "$configured_repo" && "$configured_repo" != "null" && "$configured_repo" != "builtin" ]]; then
            AGENT_REPO="$configured_repo"
        fi
    fi

    # Check for embedded repo (monorepo deployment)
    if [[ -z "$AGENT_REPO" && -f "$embedded_repo/agent-manifest.json" ]]; then
        AGENT_REPO="$embedded_repo"
    fi

    # Fall back to environment variable or default
    AGENT_REPO="${AGENT_REPO:-${AGENT_REPO_PATH:-$default_repo}}"
    AGENT_MANIFEST="$AGENT_REPO/agent-manifest.json"
    PIPELINE_AGENTS_DIR="$AGENT_REPO/pipeline-agents"
    EXPERT_AGENTS_DIR="$AGENT_REPO/expert-agents"
}

task_104_agent_selection() {
    local dialogue_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/dialogue.json"
    local corpus_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/corpus.json"
    local agents_output="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json"
    local roster_output="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/agent-roster.json"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"
    local conversation_log="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/agent-selection-log.md"
    local -a selected_experts=()  # Array to hold selected SME experts

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
    echo -e "${DIM}  │ CONVERSATION 2: AGENT SELECTION                         │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Let's select the right agents for your pipeline.       │${NC}"
    echo -e "${DIM}  │ We'll discuss options and assign agents to each phase. │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Type 'done' when you're satisfied with selections.     │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Show agents dashboard reference
    atomic_ref_agents "Browse the full agent library in the web dashboard"

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
                    PIPELINE_AGENTS_DIR="$AGENT_REPO/pipeline-agents"
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

    # Load manifest metadata (count from actual agents array)
    local total_agents=$(jq -r '.agents | length' "$AGENT_MANIFEST" 2>/dev/null || echo "unknown")
    local total_categories=$(jq -r '[.agents[].category] | unique | length' "$AGENT_MANIFEST" 2>/dev/null || echo "unknown")

    echo -e "  ${GREEN}✓${NC} Agent repository found: $AGENT_REPO"
    echo -e "    ${DIM}Total agents: $total_agents${NC}"
    echo -e "    ${DIM}Categories: $total_categories${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2: SHOW DEFAULT PIPELINE AGENTS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}PIPELINE AGENTS${NC}                                            ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${DIM}Pipeline agents execute each phase of the development workflow.${NC}"
    echo -e "  ${DIM}Here are the defaults - we'll tailor them to your project.${NC}"
    echo ""

    # Initialize roster structure
    local roster='{"version": "1.0", "timestamp": "'$(date -Iseconds)'", "phases": {}}'

    # Define default pipeline agents per phase
    declare -A default_pipeline_agents=(
        ["1-Discovery"]="discovery-agent,ideation-agent"
        ["2-PRD"]="prd-validator,prd-auditor"
        ["3-Tasks"]="task-decomposer"
        ["4-Specification"]="specification-agent,coupling-analyzer"
        ["5-Implementation"]="tdd-implementation-agent"
        ["6-Code-Review"]="code-review-gate"
        ["7-Integration"]="integration-testing-gate"
        ["8-Validation"]="plan-guardian"
        ["9-Deployment"]="deployment-gate"
    )

    # Display default assignments
    echo -e "  ${BOLD}Default Pipeline Agents:${NC}"
    echo ""
    for phase in "1-Discovery" "2-PRD" "3-Tasks" "4-Specification" "5-Implementation" "6-Code-Review" "7-Integration" "8-Validation" "9-Deployment"; do
        local agents="${default_pipeline_agents[$phase]}"
        echo -e "    ${CYAN}$phase:${NC} ${DIM}$agents${NC}"
    done
    echo ""

    # Build list of available pipeline agents for LLM
    local available_pipeline_agents=""
    for group_dir in "$PIPELINE_AGENTS_DIR"/*/; do
        [[ -d "$group_dir" ]] || continue
        local group_name=$(basename "$group_dir")
        for agent_file in "$group_dir"*.md; do
            [[ -f "$agent_file" ]] || continue
            local agent_name=$(grep -m1 '^name:' "$agent_file" | sed 's/name:[[:space:]]*//')
            local agent_desc=$(grep -m1 '^description:' "$agent_file" | sed 's/description:[[:space:]]*//' | cut -c1-80)
            [[ -z "$agent_name" ]] && continue
            available_pipeline_agents+="- $agent_name ($group_name): $agent_desc
"
        done
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 3: LLM RECOMMENDS PIPELINE AGENT CHANGES
    # ═══════════════════════════════════════════════════════════════════════════

    # Gather project context
    local tech_stack=""
    local compliance=""
    local project_domain=""
    local project_goal=""

    if [[ -f "$corpus_file" ]]; then
        project_goal=$(jq -r '.project.primary_goal // ""' "$corpus_file" 2>/dev/null)
    fi

    local setup_config="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
    if [[ -f "$setup_config" ]]; then
        tech_stack=$(jq -r '.extracted.constraints.technical // [] | join(", ")' "$setup_config" 2>/dev/null)
        project_domain=$(jq -r '.extracted.project.description // ""' "$setup_config" 2>/dev/null)
        project_goal=$(jq -r '.extracted.project.primary_goal // ""' "$setup_config" 2>/dev/null)
    fi

    # Build pipeline agent recommendation prompt
    local pipeline_prompt="$prompts_dir/pipeline-agent-recommendation.md"

    cat > "$pipeline_prompt" << EOF
# Task: Recommend Pipeline Agent Changes

You are reviewing the default pipeline agent assignments for a project. Based on the project context, recommend any changes to better fit this specific project's needs.

## Project Context

**Project Goal**: ${project_goal:-"Not specified"}
**Tech Stack/Constraints**: ${tech_stack:-"Not specified"}
**Domain**: ${project_domain:-"General software development"}

## Default Pipeline Agent Assignments

$(for phase in "1-Discovery" "2-PRD" "3-Tasks" "4-Specification" "5-Implementation" "6-Code-Review" "7-Integration" "8-Validation" "9-Deployment"; do
    echo "- $phase: ${default_pipeline_agents[$phase]}"
done)

## Available Pipeline Agents

$available_pipeline_agents

## Your Task

Review the defaults and suggest changes ONLY if strongly warranted by the project context.
Be conservative - the defaults work well for most projects.

Output JSON:
\`\`\`json
{
    "recommendations": [
        {"phase": "phase-name", "action": "add|remove|swap", "agent": "agent-name", "reason": "brief reason"}
    ],
    "summary": "One sentence summary of changes, or 'Defaults are appropriate for this project'"
}
\`\`\`

If no changes needed, return: {"recommendations": [], "summary": "Defaults are appropriate for this project"}
EOF

    local pipeline_rec_file="$prompts_dir/pipeline-recommendations.json"
    local pipeline_recommendations=""

    # Suppress streaming for this quick analysis - we'll show a clean summary
    echo -ne "  ${DIM}Analyzing project for pipeline recommendations...${NC} "
    if ATOMIC_QUIET=true ATOMIC_STREAM=false atomic_invoke "$pipeline_prompt" "$pipeline_rec_file" "Pipeline agent review" --model=haiku --format=json >/dev/null 2>&1; then
        echo -e "${GREEN}done${NC}"
        echo ""
        # Extract JSON from response
        local raw_rec=$(cat "$pipeline_rec_file")
        if echo "$raw_rec" | grep -q '```json'; then
            pipeline_recommendations=$(echo "$raw_rec" | sed -n '/```json/,/```/p' | sed '1d;$d')
        else
            pipeline_recommendations="$raw_rec"
        fi

        # Display recommendations
        local summary=$(echo "$pipeline_recommendations" | jq -r '.summary // "No changes recommended"' 2>/dev/null)
        echo -e "  ${GREEN}✓${NC} ${BOLD}Pipeline Analysis:${NC} $summary"
        echo ""

        # Show any recommended changes
        local rec_count=$(echo "$pipeline_recommendations" | jq -r '.recommendations | length' 2>/dev/null)
        if [[ "$rec_count" -gt 0 && "$rec_count" != "null" ]]; then
            echo -e "  ${BOLD}Recommended changes:${NC}"
            echo "$pipeline_recommendations" | jq -r '.recommendations[] | "    • \(.phase): \(.action) \(.agent) - \(.reason)"' 2>/dev/null
            echo ""
        fi
    else
        echo -e "${YELLOW}skipped${NC}"
        echo -e "  ${DIM}Using default pipeline agents${NC}"
        echo ""
    fi

    # Ask user to confirm or customize
    echo -e "  ${DIM}Would you like to:${NC}"
    echo -e "    ${GREEN}[1]${NC} Accept pipeline agents (with any recommendations above)"
    echo -e "    ${GREEN}[2]${NC} Customize pipeline agent assignments"
    echo -e "    ${GREEN}[3]${NC} Use defaults only (ignore recommendations)"
    echo ""
    atomic_drain_stdin
    read -e -p "  Choice [1]: " pipeline_choice || true
    pipeline_choice=${pipeline_choice:-1}

    # Apply recommendations if accepted
    if [[ "$pipeline_choice" == "1" && -n "$pipeline_recommendations" ]]; then
        # Apply LLM recommendations to defaults
        echo "$pipeline_recommendations" | jq -r '.recommendations[]? | "\(.phase):\(.action):\(.agent)"' 2>/dev/null | while IFS=: read -r phase action agent; do
            case "$action" in
                add)
                    default_pipeline_agents[$phase]="${default_pipeline_agents[$phase]},$agent"
                    ;;
                remove)
                    default_pipeline_agents[$phase]=$(echo "${default_pipeline_agents[$phase]}" | sed "s/$agent,//g; s/,$agent//g; s/^$agent$//g")
                    ;;
                swap)
                    # For swap, we'd need old:new format - simplified for now
                    ;;
            esac
        done
        echo -e "  ${GREEN}✓${NC} Pipeline agents configured"
    elif [[ "$pipeline_choice" == "2" ]]; then
        echo ""
        echo -e "  ${DIM}Enter customizations (e.g., '5-Implementation: add security-auditor' or 'done'):${NC}"
        while true; do
            read -e -p "  > " customization || true
            [[ "$customization" == "done" || -z "$customization" ]] && break
            # Parse and apply customization
            if [[ "$customization" =~ ^([0-9]-[A-Za-z-]+):\ *(add|remove)\ +(.+)$ ]]; then
                local phase="${BASH_REMATCH[1]}"
                local action="${BASH_REMATCH[2]}"
                local agent="${BASH_REMATCH[3]}"
                case "$action" in
                    add)
                        default_pipeline_agents[$phase]="${default_pipeline_agents[$phase]},$agent"
                        echo -e "    ${GREEN}✓${NC} Added $agent to $phase"
                        ;;
                    remove)
                        default_pipeline_agents[$phase]=$(echo "${default_pipeline_agents[$phase]}" | sed "s/$agent,//g; s/,$agent//g")
                        echo -e "    ${GREEN}✓${NC} Removed $agent from $phase"
                        ;;
                esac
            else
                echo -e "    ${YELLOW}!${NC} Format: 'PHASE: add|remove AGENT' (e.g., '5-Implementation: add security-auditor')"
            fi
        done
        echo -e "  ${GREEN}✓${NC} Pipeline agents customized"
    else
        echo -e "  ${GREEN}✓${NC} Using default pipeline agents"
    fi
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 4: SUGGEST SME EXPERTS BASED ON PROJECT CONTEXT
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}SME EXPERTS FOR YOUR PROJECT${NC}                               ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${DIM}Subject Matter Experts provide domain knowledge that gets${NC}"
    echo -e "  ${DIM}injected into pipeline agent prompts at each phase.${NC}"
    echo ""

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

**IMPORTANT**: Suggest 15-20 high-impact agents. Quality over quantity.

Prioritize agents that:
1. Match the PRIMARY tech stack (main language, main framework - not every library)
2. Address compliance needs (e.g., security-auditor for SOC2 projects)
3. Cover critical development phases (testing, code review, deployment)

**CONSOLIDATION RULE**: ONE agent per domain. Do NOT suggest multiple agents that overlap:
- Audio/voice work? Pick ONE: realtime-audio-phd-expert OR voice-systems-expert. NOT both, and NOT separate VAD/codec/streaming specialists.
- Performance work? Pick ONE: performance-engineer. NOT separate latency/memory/CPU specialists.
- API streaming? Pick ONE: grpc-expert OR websocket-expert OR webrtc-expert based on what the project actually needs. NOT all three "just in case".
- ML/AI deployment? Pick ONE: ml-engineer OR the specific framework expert. NOT both plus every sub-specialty.

**NEVER SUGGEST** these over-granular patterns:
- "-threshold-tuning-expert" (too specific - parent agent handles this)
- "-latency-hiding-expert" (performance-engineer covers this)
- "-verification-phd-expert" for basic state machines (overkill)
- Multiple streaming protocol experts (pick the one the project uses)
- Hardware experts (jetson, cuda, etc.) unless explicitly in requirements
- Sub-component experts when a parent agent exists (silero-vad-expert when audio-expert exists)

**RATIONALE CHECK**: For each agent, ask: "Could a broader agent already in my list handle this?" If yes, don't add it.

## Gaps Guidance

**BE EXTREMELY CONSERVATIVE with gaps.** Most projects have ZERO gaps.

A valid gap requires ALL of these:
1. A genuinely novel domain with NO existing coverage
2. Cannot be handled by combining 2-3 existing agents
3. Would require specialized knowledge an existing expert couldn't acquire

**NOT VALID GAPS** (common mistakes):
- "Multi-tenant isolation" → backend-architect + kubernetes-agent cover this
- "Protocol design" → relevant protocol expert + backend-architect cover this
- "Threshold tuning" → the domain expert + performance-engineer cover this
- Any "-specific" variant of an existing category

If you identify more than 1 gap, you're probably being too granular. Return empty gaps: []

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
        # Extract JSON from markdown response (Claude may include text before/after JSON block)
        local raw_content
        raw_content=$(cat "$suggestion_file")

        # Try to extract JSON block from markdown code fence, or use raw content if already JSON
        if echo "$raw_content" | grep -q '```json'; then
            suggested_agents_json=$(echo "$raw_content" | sed -n '/```json/,/```/p' | sed '1d;$d')
        elif echo "$raw_content" | grep -q '```'; then
            suggested_agents_json=$(echo "$raw_content" | sed -n '/```/,/```/p' | sed '1d;$d')
        else
            suggested_agents_json="$raw_content"
        fi

        # Try to parse the extracted JSON
        if echo "$suggested_agents_json" | jq -e '.suggested_agents' &>/dev/null; then
            # Show a clean, non-duplicate summary (streaming already showed raw output)
            echo ""
            echo -e "  ${GREEN}✓${NC} ${BOLD}SME Experts for your project:${NC}"
            echo ""

            # Display each suggested agent in a clean format
            echo "$suggested_agents_json" | jq -r '.suggested_agents[] | "    • \(.name): \(.reason)"' | while IFS= read -r line; do
                echo -e "    ${GREEN}•${NC} ${line#    • }"
            done

            # Display gaps if any
            local gaps
            gaps=$(echo "$suggested_agents_json" | jq -r '.gaps[]? // empty' 2>/dev/null)
            if [[ -n "$gaps" ]]; then
                echo ""
                echo -e "  ${YELLOW}Capability gaps identified:${NC}"
                echo "$suggested_agents_json" | jq -r '.gaps[]' 2>/dev/null | while IFS= read -r gap; do
                    echo -e "    ${YELLOW}!${NC} $gap"
                done
            fi

            # Pre-populate selected_experts from suggestions
            while IFS= read -r agent_name; do
                [[ -n "$agent_name" ]] && selected_experts+=("$agent_name")
            done < <(echo "$suggested_agents_json" | jq -r '.suggested_agents[].name')
        else
            # JSON parsing still failed after extraction
            echo -e "  ${YELLOW}!${NC} Could not parse agent suggestions"
            echo -e "  ${DIM}Using default expert agents...${NC}"
            selected_experts+=("code-reviewer" "security-auditor" "test-strategist")
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
    # STEP 5: CONVERSATIONAL AGENT SELECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}AGENT SELECTION CONVERSATION${NC}                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local conversation_complete=false
    local turn=0
    # Note: selected_experts array is populated earlier from LLM suggestions

    # Show current suggestions clearly before conversation starts
    if [[ ${#selected_experts[@]} -gt 0 ]]; then
        echo -e "  ${BOLD}Current SME Suggestions:${NC}"
        echo ""
        local count=0
        for expert in "${selected_experts[@]}"; do
            if [[ -n "$expert" ]]; then
                count=$((count + 1))
                echo -e "    ${GREEN}$count.${NC} $expert"
            fi
        done
        echo ""
        echo -e "  ${DIM}────────────────────────────────────────────────────────${NC}"
        echo ""
    fi

    # Agent opens with a question
    local agent_opening="Based on your project, I've suggested ${#selected_experts[@]} expert agents (listed above). Would you like to:

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
        # Disable streaming - we format the conversational output ourselves
        if ATOMIC_QUIET=true ATOMIC_STREAM=false atomic_invoke "$prompts_dir/agent-response.md" "$prompts_dir/response.txt" "Generate response"; then
            agent_response=$(cat "$prompts_dir/response.txt")
        else
            agent_response="I can help with that. Would you like me to suggest agents for that specific need, or would you prefer to browse the available categories?"
        fi

        # Always display the response - streaming output can be unreliable
        echo ""
        echo -e "  ${CYAN}Agent:${NC}"
        echo ""
        echo "$agent_response" | fold -s -w 60 | while IFS= read -r line; do
            echo -e "    $line"
        done
        echo ""

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
    # STEP 6: BUILD FINAL ROSTER (combining pipeline agents + SME experts)
    # ═══════════════════════════════════════════════════════════════════════════

    # Map phase keys to display names
    declare -A phase_display_names=(
        ["1-Discovery"]="Discovery"
        ["2-PRD"]="PRD"
        ["3-Tasks"]="Tasks"
        ["4-Specification"]="Specification"
        ["5-Implementation"]="Implementation"
        ["6-Code-Review"]="Code Review"
        ["7-Integration"]="Integration"
        ["8-Validation"]="Validation"
        ["9-Deployment"]="Deployment"
    )

    # Build roster JSON from configured pipeline agents
    local phase_num=1
    for phase_key in "1-Discovery" "2-PRD" "3-Tasks" "4-Specification" "5-Implementation" "6-Code-Review" "7-Integration" "8-Validation" "9-Deployment"; do
        local agents="${default_pipeline_agents[$phase_key]:-}"
        local phase_name="${phase_display_names[$phase_key]}"

        # Add selected SME experts to implementation phases (5-8)
        if [[ $phase_num -ge 5 && $phase_num -le 8 ]]; then
            for expert in "${selected_experts[@]}"; do
                [[ -n "$expert" ]] && agents="$agents,$expert"
            done
        fi

        # Add to roster JSON
        roster=$(echo "$roster" | jq --arg phase "$phase_num" --arg name "$phase_name" --arg agents "$agents" \
            '.phases[$phase] = {"name": $name, "agents": ($agents | split(",") | map(select(length > 0)))}')

        ((phase_num++))
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 7: REVIEW AND CONFIRM
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}ROSTER REVIEW${NC}                                              ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${BOLD}SME Experts${NC} ${DIM}(provide domain context to all phases):${NC}"
    local expert_count=${#selected_experts[@]}
    if [[ $expert_count -gt 0 ]]; then
        printf "    %s\n" "${selected_experts[@]}" | paste -sd', ' -
    else
        echo -e "    ${DIM}(none selected)${NC}"
    fi
    echo ""

    echo -e "  ${BOLD}Pipeline Executors${NC} ${DIM}(run each phase with SME context):${NC}"
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
    # STEP 8: SAVE OUTPUTS
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
