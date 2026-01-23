#!/bin/bash
#
# Task 106: Discovery Conversation
# Multi-agent deliberation to establish project direction
#
# This is a CONFERENCE TABLE conversation where:
#   - Multiple agents deliberate on approaches
#   - Agents can disagree (healthy!)
#   - Human orchestrates and directs
#   - Haiku provides fast synthesis
#   - Consensus emerges through dialogue
#
# Outputs:
#   - approaches.json        - Generated approaches with agent attributions
#   - deliberation-log.md    - Full conversation transcript
#   - consensus.json         - Agreed positions and next steps
#

task_106_discovery_work() {
    local dialogue_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/dialogue.json"
    local corpus_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/corpus.json"
    local agents_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/selected-agents.json"
    local roster_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/agent-roster.json"
    local approaches_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/approaches.json"
    local consensus_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/consensus.json"
    local deliberation_log="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/deliberation-log.md"
    local context_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/ingested-context.md"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    # Check for jq dependency
    if ! command -v jq &>/dev/null; then
        atomic_error "jq is required for discovery conversation"
        echo -e "  ${DIM}Install with: apt install jq / brew install jq${NC}"
        return 1
    fi

    atomic_step "Discovery Conversation"

    mkdir -p "$prompts_dir"

    # ═══════════════════════════════════════════════════════════════════════════
    # INTRODUCTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}                                                           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}DISCOVERY CONVERSATION${NC}                                   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${DIM}This is where your project takes shape.${NC}                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${DIM}You're about to sit at a conference table with${NC}           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${DIM}specialized agents. They'll deliberate on approaches,${NC}    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${DIM}challenge assumptions, and work toward consensus.${NC}        ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${DIM}You orchestrate. They advise. Disagreement is healthy.${NC}   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                           ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # AGENT ROSTER CONFIRMATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}YOUR PANEL${NC}                                                 ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Load agents from roster/selection
    declare -a panel_agents=()
    declare -A agent_descriptions=()

    # Default discovery agents (always present)
    panel_agents+=("orchestrator")
    agent_descriptions["orchestrator"]="Moderates discussion, drives toward consensus"

    panel_agents+=("discovery-facilitator")
    agent_descriptions["discovery-facilitator"]="Guides exploration, asks probing questions"

    panel_agents+=("first-principles-analyst")
    agent_descriptions["first-principles-analyst"]="Challenges assumptions, identifies fundamentals"

    # Add expert agents from selection
    if [[ -f "$agents_file" ]]; then
        while IFS= read -r expert; do
            [[ -n "$expert" ]] && panel_agents+=("$expert")
            agent_descriptions["$expert"]="Expert agent"
        done < <(jq -r '.selected_experts[]' "$agents_file" 2>/dev/null)
    fi

    echo -e "  ${DIM}These agents will join the conversation:${NC}"
    echo ""

    local i=1
    for agent in "${panel_agents[@]}"; do
        local desc="${agent_descriptions[$agent]:-Specialist}"
        echo -e "    ${GREEN}$i.${NC} ${BOLD}$agent${NC}"
        echo -e "       ${DIM}$desc${NC}"
        ((i++))
    done
    echo ""

    # Allow modifications
    echo -e "  ${CYAN}Modify the panel?${NC}"
    echo ""
    echo -e "    ${GREEN}[enter]${NC}  Start with this panel"
    echo -e "    ${YELLOW}[add]${NC}    Add an agent"
    echo -e "    ${RED}[remove]${NC} Remove an agent"
    echo ""

    read -p "  > " panel_action

    while [[ -n "$panel_action" ]]; do
        case "${panel_action,,}" in
            add)
                echo ""
                echo -e "  ${DIM}Available expert agents (examples):${NC}"
                echo -e "    go-expert, python-expert, rust-expert"
                echo -e "    security-auditor, api-designer, database-architect"
                echo -e "    kubernetes-specialist, devops-engineer"
                echo -e "    Or type any specialist name."
                echo ""
                read -p "  Agent to add: " new_agent
                if [[ -n "$new_agent" ]]; then
                    panel_agents+=("$new_agent")
                    echo -e "  ${GREEN}✓${NC} Added: $new_agent"
                fi
                ;;
            remove)
                echo ""
                echo -e "  ${DIM}Current panel:${NC}"
                local j=1
                for agent in "${panel_agents[@]}"; do
                    echo -e "    $j. $agent"
                    ((j++))
                done
                echo ""
                read -p "  Number to remove: " remove_num
                if [[ "$remove_num" =~ ^[0-9]+$ ]] && [[ $remove_num -ge 1 ]] && [[ $remove_num -le ${#panel_agents[@]} ]]; then
                    local removed="${panel_agents[$((remove_num-1))]}"
                    unset 'panel_agents[$((remove_num-1))]'
                    panel_agents=("${panel_agents[@]}")  # Re-index
                    echo -e "  ${GREEN}✓${NC} Removed: $removed"
                fi
                ;;
            *)
                break
                ;;
        esac
        echo ""
        read -p "  > " panel_action
    done

    echo ""
    echo -e "  ${GREEN}✓${NC} Panel confirmed: ${#panel_agents[@]} agents"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # DEEP INGESTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}INGESTING PROJECT CONTEXT${NC}                                 ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    atomic_waiting "Deep reading project materials..."

    # Build comprehensive context document
    cat > "$context_file" << 'CONTEXT_HEADER'
# Project Context (Ingested Materials)

This document contains all known information about the project.
All agents share this context as their knowledge base.

---

CONTEXT_HEADER

    # Ingest dialogue synthesis
    if [[ -f "$dialogue_file" ]]; then
        echo "## Vision & Goals" >> "$context_file"
        echo "" >> "$context_file"

        local core_problem=$(jq -r '.synthesis.vision.core_problem // "Not specified"' "$dialogue_file")
        local primary_impact=$(jq -r '.synthesis.impact.primary_impact // "Not specified"' "$dialogue_file")
        local audience=$(jq -r '.synthesis.audience.primary // "Not specified"' "$dialogue_file")
        local pain_points=$(jq -r '.synthesis.audience.pain_points // [] | map("- " + .) | join("\n")' "$dialogue_file")
        local non_negotiables=$(jq -r '.synthesis.non_negotiables // [] | map("- " + .) | join("\n")' "$dialogue_file")
        local tech_stack=$(jq -r '.synthesis.constraints.tech_stack // "Flexible"' "$dialogue_file")
        local compliance=$(jq -r '.synthesis.constraints.compliance // [] | map("- " + .) | join("\n")' "$dialogue_file")
        local open_questions=$(jq -r '.synthesis.open_questions // [] | map("- " + .) | join("\n")' "$dialogue_file")

        cat >> "$context_file" << EOF
**Core Problem:** $core_problem

**Primary Impact:** $primary_impact

**Target Audience:** $audience

**Pain Points:**
$pain_points

**Non-Negotiables:**
$non_negotiables

**Tech Stack:** $tech_stack

**Compliance Requirements:**
$compliance

**Open Questions:**
$open_questions

EOF
        echo -e "  ${GREEN}✓${NC} Dialogue synthesis ingested"
    fi

    # Ingest corpus materials
    if [[ -f "$corpus_file" ]]; then
        echo "## Collected Materials" >> "$context_file"
        echo "" >> "$context_file"

        local material_count=$(jq '.materials | length' "$corpus_file")
        echo "Materials collected: $material_count" >> "$context_file"
        echo "" >> "$context_file"

        # Include summaries or excerpts from each material
        jq -r '.materials[] | "### \(.name // .path)\n\n**Source:** \(.source)\n\n\(.content[:2000] // "No content")\n\n---\n"' "$corpus_file" >> "$context_file" 2>/dev/null

        echo -e "  ${GREEN}✓${NC} Corpus materials ingested ($material_count items)"
    fi

    # Ingest any imported requirements
    local needs_file="$ATOMIC_ROOT/.claude/needs/needs-index.json"
    if [[ -f "$needs_file" ]]; then
        local needs_count=$(jq '.needs | length' "$needs_file" 2>/dev/null || echo "0")
        if [[ "$needs_count" -gt 0 ]]; then
            echo "## Imported Requirements" >> "$context_file"
            echo "" >> "$context_file"
            jq -r '.needs[] | "- **\(.id)** (\(.type)): \(.title)"' "$needs_file" >> "$context_file"
            echo "" >> "$context_file"
            echo -e "  ${GREEN}✓${NC} Requirements ingested ($needs_count items)"
        fi
    fi

    echo ""

    # Initialize deliberation log
    cat > "$deliberation_log" << EOF
# Discovery Deliberation Log

**Started:** $(date -Iseconds)
**Panel:** ${panel_agents[*]}

---

EOF

    # Initialize conversation state
    local conversation_json='{
        "started_at": "'$(date -Iseconds)'",
        "panel": [],
        "exchanges": [],
        "approaches": [],
        "consensus": null
    }'

    # Add panel to JSON
    for agent in "${panel_agents[@]}"; do
        conversation_json=$(echo "$conversation_json" | jq --arg a "$agent" '.panel += [$a]')
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # CONVERSATION LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}CONFERENCE TABLE${NC}                                          ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${DIM}Commands:${NC}"
    echo -e "    ${GREEN}@agent${NC}       Direct question to specific agent"
    echo -e "    ${YELLOW}generate${NC}    Generate/refine approaches"
    echo -e "    ${YELLOW}analyze${NC}     First-principles analysis"
    echo -e "    ${YELLOW}challenge${NC}   Ask agents to critique current thinking"
    echo -e "    ${YELLOW}synthesize${NC}  Get quick summary of discussion"
    echo -e "    ${YELLOW}consensus${NC}   Check for areas of agreement"
    echo -e "    ${RED}done${NC}        Conclude deliberation"
    echo ""
    echo -e "  ${DIM}Or just type naturally - the orchestrator will route your input.${NC}"
    echo ""

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Orchestrator opens
    local opening_prompt="$prompts_dir/opening.md"

    # Use smart summarization to protect token budget while preserving key info
    local truncated_context=$(atomic_context_summarize "$context_file" "discovery context" 300)

    cat > "$opening_prompt" << EOF
# Role: Orchestrator

You are moderating a discovery conversation about a software project.

## Project Context (Summary)
$truncated_context

## Your Task

Open the deliberation with:
1. A brief acknowledgment of the project's core problem (1 sentence)
2. A framing question to start discussion (e.g., "What approaches should we consider?")

Keep it concise - 2-3 sentences max. Be warm but professional.
EOF

    local opening_response="$prompts_dir/opening-response.txt"
    if atomic_invoke "$opening_prompt" "$opening_response" "Orchestrator opening" --model=sonnet; then
        local opening=$(cat "$opening_response")
        echo -e "  ${CYAN}orchestrator:${NC}"
        echo ""
        echo "$opening" | fold -s -w 60 | while IFS= read -r line; do
            echo -e "    $line"
        done
        echo ""

        # Log to deliberation
        echo "## Orchestrator (Opening)" >> "$deliberation_log"
        echo "" >> "$deliberation_log"
        echo "$opening" >> "$deliberation_log"
        echo "" >> "$deliberation_log"

        conversation_json=$(echo "$conversation_json" | jq --arg agent "orchestrator" --arg msg "$opening" \
            '.exchanges += [{"agent": $agent, "message": $msg, "timestamp": now | todate}]')
    fi

    # Main conversation loop
    local deliberation_complete=false
    local turn=0
    local approaches_generated=false

    while [[ "$deliberation_complete" == false ]]; do
        echo -e "  ${GREEN}You:${NC}"
        read -p "    " user_input

        # Handle empty input
        [[ -z "$user_input" ]] && continue

        # Log user input
        echo "## Human" >> "$deliberation_log"
        echo "" >> "$deliberation_log"
        echo "$user_input" >> "$deliberation_log"
        echo "" >> "$deliberation_log"

        conversation_json=$(echo "$conversation_json" | jq --arg msg "$user_input" \
            '.exchanges += [{"agent": "human", "message": $msg, "timestamp": now | todate}]')

        ((turn++))

        # Parse command or route naturally
        case "${user_input,,}" in
            done|exit|quit)
                deliberation_complete=true
                break
                ;;

            synthesize|summary)
                _106_synthesize "$context_file" "$conversation_json" "$prompts_dir"
                ;;

            generate|approaches)
                _106_generate_approaches "$context_file" "$conversation_json" "$prompts_dir" "$approaches_file"
                approaches_generated=true
                ;;

            analyze|"first principles"|fp)
                if [[ "$approaches_generated" == true ]]; then
                    _106_first_principles "$context_file" "$approaches_file" "$conversation_json" "$prompts_dir"
                else
                    echo ""
                    echo -e "    ${YELLOW}!${NC} Generate approaches first."
                    echo ""
                fi
                ;;

            challenge|critique)
                _106_challenge "$context_file" "$conversation_json" "$prompts_dir" "${panel_agents[@]}"
                ;;

            consensus|agree)
                _106_check_consensus "$context_file" "$conversation_json" "$prompts_dir"
                ;;

            @*)
                # Direct message to specific agent
                local target_agent="${user_input#@}"
                target_agent="${target_agent%% *}"
                local message="${user_input#*$target_agent}"
                message="${message# }"

                if [[ " ${panel_agents[*]} " =~ " ${target_agent} " ]]; then
                    _106_agent_response "$target_agent" "$message" "$context_file" "$conversation_json" "$prompts_dir" "$deliberation_log"
                else
                    echo ""
                    echo -e "    ${RED}!${NC} Agent '$target_agent' not on panel."
                    echo -e "    ${DIM}Panel: ${panel_agents[*]}${NC}"
                    echo ""
                fi
                ;;

            *)
                # Natural input - orchestrator routes it
                _106_route_input "$user_input" "$context_file" "$conversation_json" "$prompts_dir" "$deliberation_log" "${panel_agents[@]}"
                ;;
        esac

        # Quick synthesis every 5 turns
        if [[ $((turn % 5)) -eq 0 ]] && [[ $turn -gt 0 ]]; then
            echo ""
            echo -e "  ${DIM}── Quick synthesis ──${NC}"
            _106_synthesize "$context_file" "$conversation_json" "$prompts_dir"
        fi
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # FINAL CONSENSUS & OUTPUT
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}CONCLUDING DELIBERATION${NC}                                   ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Generate final consensus document
    # Adjudicate conversation if needed before final synthesis
    local primary_model=$(atomic_get_model primary)
    conversation_json=$(atomic_context_adjudicate "$conversation_json" "Discovery Deliberation" "$primary_model")

    local final_context=$(atomic_context_summarize "$context_file" "deliberation context" 200)
    local final_exchanges=$(echo "$conversation_json" | jq -r '.exchanges[] | "**\(.agent):** \(.message)"')

    cat > "$prompts_dir/final-consensus.md" << EOF
# Task: Generate Final Consensus

Based on the deliberation, create a consensus document.

## Project Context (Summary)
$final_context

## Deliberation Exchanges
$final_exchanges

## Your Task

Synthesize the deliberation into:

1. **Agreed Direction** - What approach/direction emerged?
2. **Key Decisions Made** - What was decided?
3. **Open Items** - What still needs resolution?
4. **Recommended Next Steps** - What to investigate/prototype first?
5. **Dissenting Views** - Any unresolved disagreements worth noting?

Output as JSON:
{
    "agreed_direction": {
        "approach": "...",
        "rationale": "..."
    },
    "key_decisions": ["..."],
    "open_items": ["..."],
    "next_steps": ["..."],
    "dissenting_views": ["..."]
}
EOF

    atomic_waiting "Generating consensus..."

    if atomic_invoke "$prompts_dir/final-consensus.md" "$consensus_file" "Final consensus" --model=sonnet; then
        if jq -e . "$consensus_file" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Consensus captured"
            echo ""

            # Display consensus
            local direction=$(jq -r '.agreed_direction.approach // "No clear direction"' "$consensus_file")
            local rationale=$(jq -r '.agreed_direction.rationale // ""' "$consensus_file")

            echo -e "  ${CYAN}Agreed Direction:${NC} ${BOLD}$direction${NC}"
            echo -e "  ${DIM}$rationale${NC}"
            echo ""

            local next_steps=$(jq -r '.next_steps[:3] | map("    • " + .) | join("\n")' "$consensus_file")
            if [[ -n "$next_steps" ]]; then
                echo -e "  ${CYAN}Next Steps:${NC}"
                echo "$next_steps"
                echo ""
            fi

            local open_items=$(jq -r '.open_items | length' "$consensus_file")
            local dissent=$(jq -r '.dissenting_views | length' "$consensus_file")

            echo -e "  ${DIM}Open items: $open_items | Dissenting views: $dissent${NC}"
        else
            echo -e "  ${YELLOW}!${NC} Could not structure consensus - see deliberation log"
        fi
    fi

    # Finalize deliberation log
    cat >> "$deliberation_log" << EOF

---

## Session Complete

**Ended:** $(date -Iseconds)
**Total exchanges:** $turn

EOF

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Discovery Conversation Complete${NC}"
    echo ""
    echo -e "  Exchanges:      $turn"
    echo -e "  Panel size:     ${#panel_agents[@]} agents"
    echo ""

    atomic_context_artifact "approaches" "$approaches_file" "Generated approaches"
    atomic_context_artifact "consensus" "$consensus_file" "Deliberation consensus"
    atomic_context_artifact "deliberation_log" "$deliberation_log" "Full conversation transcript"
    atomic_context_artifact "ingested_context" "$context_file" "Project context document"
    atomic_context_decision "Discovery deliberation complete with ${#panel_agents[@]} agents over $turn exchanges" "discovery"

    atomic_success "Discovery conversation complete"

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Fast synthesis using Haiku
_106_synthesize() {
    local context_file="$1"
    local conversation_json="$2"
    local prompts_dir="$3"

    cat > "$prompts_dir/synthesize.md" << EOF
# Quick Synthesis

Summarize the discussion so far in 2-3 bullet points.
Focus on: key insights, emerging consensus, open questions.

## Recent Exchanges
$(echo "$conversation_json" | jq -r '.exchanges[-6:] | .[] | "**\(.agent):** \(.message)"')

Be extremely concise. Output plain text, no JSON.
EOF

    echo ""
    if atomic_invoke "$prompts_dir/synthesize.md" "$prompts_dir/synthesis.txt" "Synthesis" --model=haiku; then
        echo -e "  ${DIM}synthesis:${NC}"
        cat "$prompts_dir/synthesis.txt" | fold -s -w 60 | while IFS= read -r line; do
            echo -e "    ${DIM}$line${NC}"
        done
    fi
    echo ""
}

# Generate approaches with panel input
_106_generate_approaches() {
    local context_file="$1"
    local conversation_json="$2"
    local prompts_dir="$3"
    local approaches_file="$4"

    # Summarize context and use sliding window for exchanges
    local ctx_summary=$(atomic_context_summarize "$context_file" "approach generation context" 250)
    local recent_discussion=$(echo "$conversation_json" | jq -r '.exchanges[-12:] | .[] | "**\(.agent):** \(.message)"')

    cat > "$prompts_dir/generate-approaches.md" << EOF
# Generate Approaches

Based on the project context and discussion, generate 2-3 meaningfully different approaches.

## Project Context
$ctx_summary

## Discussion So Far (Recent)
$recent_discussion

## Output Format

For each approach:
- Name (memorable, descriptive)
- Summary (2-3 sentences)
- Key decisions that define it
- Tradeoffs (what you gain, what you give up)
- Unknowns (what needs investigation)
- Complexity: simple | moderate | complex | exploratory

Output as JSON:
{
    "approaches": [
        {
            "id": "A",
            "name": "...",
            "summary": "...",
            "key_decisions": ["..."],
            "tradeoffs": {"gains": ["..."], "gives_up": ["..."]},
            "unknowns": ["..."],
            "complexity": "..."
        }
    ]
}
EOF

    echo ""
    atomic_waiting "Generating approaches..."

    if atomic_invoke "$prompts_dir/generate-approaches.md" "$approaches_file" "Generate approaches" --model=sonnet; then
        if jq -e . "$approaches_file" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Approaches generated"
            echo ""
            jq -r '.approaches[] | "  \u001b[36m[\(.id)]\u001b[0m \u001b[1m\(.name)\u001b[0m (\(.complexity))\n      \(.summary)\n"' "$approaches_file"
        fi
    fi
}

# First principles analysis
_106_first_principles() {
    local context_file="$1"
    local approaches_file="$2"
    local conversation_json="$3"
    local prompts_dir="$4"

    # Summarize context, approaches file is usually small
    local ctx_summary=$(atomic_context_summarize "$context_file" "first principles context" 150)
    local approaches_content=$(atomic_context_summarize "$approaches_file" "solution approaches" 200)

    cat > "$prompts_dir/first-principles.md" << EOF
# First Principles Analysis

Role: first-principles-analyst

You challenge assumptions, identify fundamentals, and ask "what's the simplest thing that could work?"

## Your Approach
- Question every assumption explicitly
- Break problems down to basic truths
- Identify unnecessary complexity
- Suggest simpler alternatives where possible

## Project Context
$ctx_summary

## Current Approaches
$approaches_content

Respond conversationally as the first-principles-analyst. Be direct, challenge assumptions, identify fundamentals.
Keep it to 3-5 key points. Plain text, not JSON.
EOF

    echo ""
    if atomic_invoke "$prompts_dir/first-principles.md" "$prompts_dir/fp-response.txt" "First principles" --model=sonnet; then
        echo -e "  ${CYAN}first-principles-analyst:${NC}"
        echo ""
        cat "$prompts_dir/fp-response.txt" | fold -s -w 60 | while IFS= read -r line; do
            echo -e "    $line"
        done
    fi
    echo ""
}

# Challenge current thinking
_106_challenge() {
    local context_file="$1"
    local conversation_json="$2"
    local prompts_dir="$3"
    shift 3
    local panel_agents=("$@")

    # Pick a random agent to challenge
    local challenger="${panel_agents[$((RANDOM % ${#panel_agents[@]}))]}"

    cat > "$prompts_dir/challenge.md" << EOF
# Challenge the Discussion

Role: $challenger

Look at the discussion so far and raise a challenge, concern, or alternative viewpoint.
Be constructive but don't hold back. Healthy disagreement moves things forward.

## Discussion
$(echo "$conversation_json" | jq -r '.exchanges[-8:] | .[] | "**\(.agent):** \(.message)"')

Respond as $challenger. 2-4 sentences. Plain text.
EOF

    echo ""
    if atomic_invoke "$prompts_dir/challenge.md" "$prompts_dir/challenge-response.txt" "Challenge" --model=sonnet; then
        echo -e "  ${CYAN}$challenger:${NC}"
        echo ""
        cat "$prompts_dir/challenge-response.txt" | fold -s -w 60 | while IFS= read -r line; do
            echo -e "    $line"
        done
    fi
    echo ""
}

# Check for consensus
_106_check_consensus() {
    local context_file="$1"
    local conversation_json="$2"
    local prompts_dir="$3"

    # Use sliding window - consensus check needs recent context, not full history
    local recent_exchanges=$(echo "$conversation_json" | jq -r '.exchanges[-15:] | .[] | "**\(.agent):** \(.message)"')

    # Include any adjudication summaries for full picture
    local adjudication_context=""
    if echo "$conversation_json" | jq -e '.adjudication_history | length > 0' &>/dev/null; then
        adjudication_context=$(echo "$conversation_json" | jq -r '
            "## Earlier Discussion Summary\n" +
            (.adjudication_history | map(.level_set) | join("\n"))
        ')
    fi

    cat > "$prompts_dir/consensus-check.md" << EOF
# Consensus Check

Review the discussion and identify:
1. Areas of agreement
2. Areas of disagreement
3. What would help reach consensus

$adjudication_context

## Recent Discussion
$recent_exchanges

Be concise. Plain text, 3-5 bullet points.
EOF

    echo ""
    if atomic_invoke "$prompts_dir/consensus-check.md" "$prompts_dir/consensus-response.txt" "Consensus check" --model=haiku; then
        echo -e "  ${DIM}consensus check:${NC}"
        echo ""
        cat "$prompts_dir/consensus-response.txt" | fold -s -w 60 | while IFS= read -r line; do
            echo -e "    $line"
        done
    fi
    echo ""
}

# Direct response from specific agent
_106_agent_response() {
    local agent="$1"
    local message="$2"
    local context_file="$3"
    local conversation_json="$4"
    local prompts_dir="$5"
    local deliberation_log="$6"

    # Get agent persona based on name
    local agent_persona=""
    case "$agent" in
        orchestrator) agent_persona="You moderate discussion, drive toward consensus, and keep the conversation productive. You synthesize viewpoints and identify next steps." ;;
        discovery-facilitator) agent_persona="You guide exploration by asking probing questions. You help draw out requirements and ensure all perspectives are considered." ;;
        first-principles-analyst) agent_persona="You challenge assumptions and identify fundamentals. You ask 'why' and 'what's the simplest solution that could work?'" ;;
        *security*|*auditor*) agent_persona="You focus on security implications, threat modeling, and compliance. You identify risks and suggest mitigations." ;;
        *api*|*backend*) agent_persona="You specialize in API design, backend architecture, and service patterns. You consider scalability and maintainability." ;;
        *test*|*tdd*) agent_persona="You focus on testing strategies, testability, and quality assurance. You advocate for test-driven approaches." ;;
        *) agent_persona="You are an expert in ${agent//-/ }. Draw on your specialized knowledge to provide insights." ;;
    esac

    # Use summarized context and recent exchanges
    local ctx_summary=$(atomic_context_summarize "$context_file" "direction confirmation context" 150)
    local recent_exchanges=$(echo "$conversation_json" | jq -r '.exchanges[-6:] | .[] | "**\(.agent):** \(.message)"')

    cat > "$prompts_dir/agent-direct.md" << EOF
# Direct Question to $agent

## Your Role
$agent_persona

## The Question
The human asked you directly: "$message"

## Project Context
$ctx_summary

## Recent Discussion
$recent_exchanges

Respond as $agent. Be helpful, specific, and draw on your expertise.
2-5 sentences. Plain text.
EOF

    echo ""
    if atomic_invoke "$prompts_dir/agent-direct.md" "$prompts_dir/agent-response.txt" "$agent response" --model=sonnet; then
        echo -e "  ${CYAN}$agent:${NC}"
        echo ""
        cat "$prompts_dir/agent-response.txt" | fold -s -w 60 | while IFS= read -r line; do
            echo -e "    $line"
        done

        # Log to deliberation
        echo "## $agent" >> "$deliberation_log"
        echo "" >> "$deliberation_log"
        cat "$prompts_dir/agent-response.txt" >> "$deliberation_log"
        echo "" >> "$deliberation_log"
    fi
    echo ""
}

# Route natural input through orchestrator
_106_route_input() {
    local user_input="$1"
    local context_file="$2"
    local conversation_json="$3"
    local prompts_dir="$4"
    local deliberation_log="$5"
    shift 5
    local panel_agents=("$@")

    # Build agent roster with descriptions for routing decision
    local agent_roster=""
    for agent in "${panel_agents[@]}"; do
        local desc=""
        case "$agent" in
            orchestrator) desc="Moderates discussion, drives toward consensus, keeps conversation on track" ;;
            discovery-facilitator) desc="Guides exploration, asks probing questions, draws out requirements" ;;
            first-principles-analyst) desc="Challenges assumptions, identifies fundamentals, simplifies" ;;
            *security*|*auditor*) desc="Security expertise, threat modeling, compliance considerations" ;;
            *api*|*backend*) desc="API design, backend architecture, service patterns" ;;
            *frontend*|*ui*) desc="Frontend architecture, user experience, client-side concerns" ;;
            *database*|*data*) desc="Data modeling, storage strategies, query optimization" ;;
            *devops*|*infrastructure*) desc="Deployment, CI/CD, infrastructure concerns" ;;
            *test*|*tdd*) desc="Testing strategies, quality assurance, test architecture" ;;
            *) desc="Specialist in ${agent//-/ }" ;;
        esac
        agent_roster+="- **$agent**: $desc"$'\n'
    done

    # Orchestrator decides who should respond
    cat > "$prompts_dir/route.md" << EOF
# Route Input

The human said: "$user_input"

## Available Panel Members

$agent_roster

## Routing Criteria

Choose the agent whose expertise BEST matches the human's input:
- Technical questions → relevant technical specialist
- Process/approach questions → orchestrator or discovery-facilitator
- "Why" questions or challenges → first-principles-analyst
- Security concerns → security-related agent
- General exploration → discovery-facilitator

Output ONLY the exact agent name (e.g., "discovery-facilitator"), nothing else.
EOF

    local responder="discovery-facilitator"  # default
    if atomic_invoke "$prompts_dir/route.md" "$prompts_dir/route-response.txt" "Route" --model=haiku; then
        local suggested=$(cat "$prompts_dir/route-response.txt" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
        for agent in "${panel_agents[@]}"; do
            if [[ "${agent,,}" == "$suggested" ]]; then
                responder="$agent"
                break
            fi
        done
    fi

    # Get response from chosen agent
    _106_agent_response "$responder" "$user_input" "$context_file" "$conversation_json" "$prompts_dir" "$deliberation_log"
}
