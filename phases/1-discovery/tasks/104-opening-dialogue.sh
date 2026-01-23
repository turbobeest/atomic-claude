#!/bin/bash
#
# Task 104: Opening Dialogue (Conversation 2)
# Deep conversational exchange with human about vision, goals, and constraints
#
# This is a TRUE CONVERSATION - not a form to fill out.
#
# Flow:
#   1. Agent reviews corpus (if available) and opens with observations
#   2. If greenfield: ask for initial vision
#   3. Back-and-forth dialogue until mutual understanding
#   4. Capture consensus on impact, audience, success criteria
#   5. Gather constraints through conversation
#
# The conversation continues until:
#   - Human says they're satisfied, OR
#   - Agent has gathered all critical information
#

task_104_opening_dialogue() {
    local corpus_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/corpus.json"
    local corpus_analysis="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/corpus-analysis.md"
    local dialogue_output="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/dialogue.json"
    local conversation_log="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/conversation-log.md"
    local prompts_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts"

    # Check for jq dependency
    if ! command -v jq &>/dev/null; then
        atomic_error "jq is required for dialogue processing"
        echo -e "  ${DIM}Install with: apt install jq / brew install jq${NC}"
        return 1
    fi

    atomic_step "Opening Dialogue"

    mkdir -p "$prompts_dir"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ CONVERSATION 2: OPENING DIALOGUE                        │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ This is a real conversation, not a form.                │${NC}"
    echo -e "${DIM}  │ We'll talk until we both understand the vision.        │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Type 'done' when you feel we've covered enough.        │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Initialize dialogue tracking
    local dialogue='{
        "conversation": [],
        "synthesis": {},
        "constraints": {},
        "timestamp": "'$(date -Iseconds)'",
        "turns": 0
    }'

    # Start conversation log
    cat > "$conversation_log" << 'EOF'
# Opening Dialogue - Conversation Log

EOF

    # ═══════════════════════════════════════════════════════════════════════════
    # DETERMINE CONTEXT: GREENFIELD OR EXISTING PROJECT?
    # ═══════════════════════════════════════════════════════════════════════════

    local has_corpus=false
    local corpus_summary=""

    if [[ -f "$corpus_file" ]]; then
        local material_count
        material_count=$(jq '.materials | length' "$corpus_file" 2>/dev/null || echo "0")
        if [[ "$material_count" -gt 0 ]]; then
            has_corpus=true
            # Get corpus summary if analysis exists (limit to first 200 lines)
            if [[ -f "$corpus_analysis" ]]; then
                corpus_summary=$(head -200 "$corpus_analysis")
                local total_lines
                total_lines=$(wc -l < "$corpus_analysis")
                if [[ $total_lines -gt 200 ]]; then
                    corpus_summary+=$'\n[TRUNCATED: showing first 200 of '"$total_lines"' lines]'
                fi
            fi
        fi
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # CONVERSATION LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}LET'S TALK${NC}                                                ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local turn=0
    local conversation_complete=false
    local gathered_vision=false
    local gathered_impact=false
    local gathered_audience=false
    local gathered_constraints=false

    # Generate opening based on context
    local agent_opening=""

    if [[ "$has_corpus" == true ]]; then
        # We have corpus - agent opens with observations
        cat > "$prompts_dir/dialogue-opening.md" << EOF
# Task: Open the dialogue with insightful observations

You are the discovery-facilitator opening a conversation with the human.
You've reviewed their project materials and have observations to share.

## Corpus Summary
$corpus_summary

## Your Task

Write a warm, professional opening (3-5 sentences) that:
1. Acknowledges you've reviewed their materials
2. Shares 1-2 specific observations that show you understand
3. Asks ONE probing question to start the dialogue

Be genuine and curious. Don't be sycophantic.
Output ONLY your opening message, no formatting.
EOF

        atomic_waiting "Preparing opening..."

        if atomic_invoke "$prompts_dir/dialogue-opening.md" "$prompts_dir/opening-response.txt" "Generate opening" --model=sonnet; then
            agent_opening=$(cat "$prompts_dir/opening-response.txt")
        else
            agent_opening="I've reviewed the materials you've gathered. I see some interesting patterns and have questions. What's the core problem you're trying to solve?"
        fi
    else
        # Greenfield - ask for initial vision
        agent_opening="This looks like a fresh start - exciting! Before we dive in, I'd love to hear your vision in your own words. What are you trying to build, and why does it matter to you?"
    fi

    # Display agent opening
    echo -e "  ${CYAN}Agent:${NC}"
    echo ""
    echo "$agent_opening" | fold -s -w 60 | while IFS= read -r line; do
        echo -e "    $line"
    done
    echo ""

    # Log the opening
    echo "## Turn 1" >> "$conversation_log"
    echo "" >> "$conversation_log"
    echo "**Agent:** $agent_opening" >> "$conversation_log"
    echo "" >> "$conversation_log"

    dialogue=$(echo "$dialogue" | jq --arg msg "$agent_opening" '.conversation += [{"role": "agent", "content": $msg}]')
    ((turn++))

    # Main conversation loop
    while [[ "$conversation_complete" == false ]]; do
        echo -e "  ${GREEN}You:${NC}"
        echo ""

        # Multi-line input
        local human_response=""
        local empty_count=0
        while true; do
            read -p "    " line
            if [[ -z "$line" ]]; then
                ((empty_count++))
                [[ $empty_count -ge 1 ]] && break
            else
                empty_count=0
                human_response+="$line"$'\n'
            fi
        done

        # Trim whitespace for exit command checking
        local trimmed_response
        trimmed_response=$(echo "$human_response" | tr -d '[:space:]')

        # Check for exit commands or empty input
        if [[ "${trimmed_response,,}" =~ ^(done|finished|thatsit|exit|quit)$ ]] || [[ -z "$trimmed_response" ]]; then
            if [[ $turn -lt 3 ]]; then
                echo ""
                echo -e "    ${YELLOW}We should talk a bit more to ensure I understand your vision.${NC}"
                echo -e "    ${DIM}Please share your thoughts, or type 'skip' to force exit.${NC}"
                echo ""

                read -p "    " force_response
                if [[ "${force_response,,}" == "skip" ]]; then
                    conversation_complete=true
                    break
                fi
                human_response="$force_response"$'\n'
            else
                conversation_complete=true
                break
            fi
        fi

        # Log human response
        echo "**Human:** $human_response" >> "$conversation_log"
        echo "" >> "$conversation_log"

        dialogue=$(echo "$dialogue" | jq --arg msg "$human_response" '.conversation += [{"role": "human", "content": $msg}]')
        ((turn++))

        # Determine what to probe for next
        local probe_focus=""
        if [[ "$gathered_vision" == false ]]; then
            probe_focus="vision and core problem"
            gathered_vision=true
        elif [[ "$gathered_impact" == false ]]; then
            probe_focus="desired impact and success metrics"
            gathered_impact=true
        elif [[ "$gathered_audience" == false ]]; then
            probe_focus="target audience and stakeholders"
            gathered_audience=true
        elif [[ "$gathered_constraints" == false ]]; then
            probe_focus="constraints (tech, timeline, team, compliance)"
            gathered_constraints=true
        else
            probe_focus="anything unclear or worth exploring deeper"
        fi

        # Generate agent response
        local conversation_so_far
        conversation_so_far=$(jq -r '.conversation | map("\(.role): \(.content)") | join("\n\n")' <<< "$dialogue")

        cat > "$prompts_dir/dialogue-continue.md" << EOF
# Task: Continue the dialogue

You are the discovery-facilitator in conversation with the human.

## Conversation So Far
$conversation_so_far

## What to probe for
$probe_focus

## Your Task

Based on what they just said:
1. Acknowledge their point (briefly, genuinely - not sycophantically)
2. Share a relevant insight or observation if appropriate
3. Ask a follow-up question to probe: $probe_focus

If you feel you have enough information about this topic, you can:
- Summarize your understanding and ask for confirmation
- Move to the next topic naturally

Keep your response concise (2-4 sentences). Be curious and genuine.
Output ONLY your response, no formatting.
EOF

        atomic_waiting "Thinking..."

        local agent_response=""
        if atomic_invoke "$prompts_dir/dialogue-continue.md" "$prompts_dir/continue-response.txt" "Continue dialogue" --model=sonnet; then
            agent_response=$(cat "$prompts_dir/continue-response.txt")
        else
            # Fallback responses based on probe focus
            case "$probe_focus" in
                *vision*) agent_response="That's helpful context. What would success look like for this project in 6 months?" ;;
                *impact*) agent_response="I understand the goal. Who benefits most from this, and how will we measure that impact?" ;;
                *audience*) agent_response="Got it. What constraints are we working within - technology, timeline, team size, compliance?" ;;
                *constraints*) agent_response="Thanks for sharing those constraints. Is there anything else important I should know before we move on?" ;;
                *) agent_response="That's clear. Shall we move forward, or is there anything else you want to discuss?" ;;
            esac
        fi

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

        dialogue=$(echo "$dialogue" | jq --arg msg "$agent_response" '.conversation += [{"role": "agent", "content": $msg}]')
        ((turn++))

        # Check if we have enough after several turns
        if [[ $turn -ge 10 ]] && [[ "$gathered_constraints" == true ]]; then
            echo ""
            echo -e "    ${DIM}(We've covered a lot. Type 'done' if you're satisfied, or continue...)${NC}"
            echo ""
        fi
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # SYNTHESIZE CONVERSATION
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}SYNTHESIZING CONVERSATION${NC}                                 ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local full_conversation
    full_conversation=$(jq -r '.conversation | map("\(.role): \(.content)") | join("\n\n")' <<< "$dialogue")

    cat > "$prompts_dir/dialogue-synthesis.md" << 'EOF'
# Task: Synthesize the conversation into structured output

Based on this dialogue, extract the key information.

## Conversation
EOF
    echo "$full_conversation" >> "$prompts_dir/dialogue-synthesis.md"

    cat >> "$prompts_dir/dialogue-synthesis.md" << 'EOF'

## Extract into JSON

{
    "vision": {
        "core_problem": "What problem are we solving?",
        "solution_concept": "High-level approach",
        "why_now": "Why is this important now?"
    },
    "impact": {
        "primary_impact": "One sentence describing main outcome",
        "success_metrics": ["How we'll measure success"],
        "timeline_to_value": "When will impact be realized?"
    },
    "audience": {
        "primary": "Main beneficiary",
        "secondary": ["Other stakeholders"],
        "pain_points": ["What they struggle with today"]
    },
    "constraints": {
        "tech_stack": "Required/preferred technologies",
        "timeline": "Key milestones or deadlines",
        "team_size": "Number of people",
        "budget": "Budget constraints if any",
        "compliance": ["Regulatory requirements"],
        "other": ["Any other constraints"]
    },
    "non_negotiables": ["Things that must be true"],
    "open_questions": ["Things still unclear"]
}

Output ONLY valid JSON.
EOF

    atomic_waiting "Synthesizing..."

    if atomic_invoke "$prompts_dir/dialogue-synthesis.md" "$prompts_dir/synthesis.json" "Synthesize dialogue" --model=sonnet; then
        if jq -e . "$prompts_dir/synthesis.json" &>/dev/null; then
            local synthesis
            synthesis=$(cat "$prompts_dir/synthesis.json")
            dialogue=$(echo "$dialogue" | jq --argjson syn "$synthesis" '.synthesis = $syn')

            # Display synthesis
            echo -e "  ${GREEN}✓${NC} Conversation synthesized"
            echo ""
            echo -e "  ${CYAN}Summary:${NC}"
            echo ""
            echo -e "    ${BOLD}Vision:${NC} $(jq -r '.vision.core_problem // "Not captured"' <<< "$synthesis")"
            echo -e "    ${BOLD}Impact:${NC} $(jq -r '.impact.primary_impact // "Not captured"' <<< "$synthesis")"
            echo -e "    ${BOLD}Audience:${NC} $(jq -r '.audience.primary // "Not captured"' <<< "$synthesis")"
            echo -e "    ${BOLD}Timeline:${NC} $(jq -r '.constraints.timeline // "Not captured"' <<< "$synthesis")"
            echo ""

            # Confirm with human
            echo -e "  ${DIM}Does this capture our conversation accurately? [Y/n]${NC}"
            read -p "  > " confirm

            if [[ "${confirm,,}" =~ ^n ]]; then
                echo ""
                echo -e "  ${DIM}What should be corrected?${NC}"
                read -p "  > " corrections
                dialogue=$(echo "$dialogue" | jq --arg corr "$corrections" '.synthesis.corrections = $corr')
                echo -e "  ${GREEN}✓${NC} Corrections noted"
            fi
        else
            echo -e "  ${YELLOW}!${NC} Synthesis had issues - using conversation log"
        fi
    else
        echo -e "  ${YELLOW}!${NC} Could not synthesize - conversation log saved"
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # SAVE DIALOGUE
    # ═══════════════════════════════════════════════════════════════════════════

    dialogue=$(echo "$dialogue" | jq --argjson turns "$turn" '.turns = $turns')
    echo "$dialogue" | jq . > "$dialogue_output"

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${BOLD}Opening Dialogue Complete${NC}"
    echo -e "  ${DIM}Turns: $turn${NC}"
    echo ""

    atomic_context_artifact "dialogue" "$dialogue_output" "Opening dialogue capture ($turn turns)"
    atomic_context_artifact "conversation_log" "$conversation_log" "Conversation transcript"

    atomic_success "Opening dialogue complete"

    return 0
}
