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
        echo -e "  ${DIM}Install with: apt install jq / brew install jq / winget install jqlang.jq${NC}"
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
    # LOAD PROJECT CONTEXT FROM CONFIG
    # ═══════════════════════════════════════════════════════════════════════════

    local project_context=""
    local config_file="$ATOMIC_OUTPUT_DIR/${CURRENT_PHASE:-0-setup}/project-config.json"
    [[ ! -f "$config_file" ]] && config_file="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"

    if [[ -f "$config_file" ]]; then
        local p_name p_desc
        p_name=$(jq -r '.project.name // .extracted.project.name // "Unknown"' "$config_file" 2>/dev/null)
        p_desc=$(jq -r '.project.description // .extracted.project.description // ""' "$config_file" 2>/dev/null)
        local p_goals
        p_goals=$(jq -r '(.project.goals // .extracted.project.goals // []) | if type == "array" then map("- " + .) | join("\n") else . end' "$config_file" 2>/dev/null)

        project_context="## Project Context

**Project:** $p_name
**Description:** $p_desc"
        [[ -n "$p_goals" && "$p_goals" != "null" ]] && project_context+="
**Goals:**
$p_goals"
        project_context+="
"
    fi

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

    local _opening_streamed=false
    if [[ "$has_corpus" == true ]]; then
        # We have corpus - agent opens with observations
        cat > "$prompts_dir/dialogue-opening.md" << EOF
# Task: Open the Dialogue with Insightful Observations

You are the **discovery-facilitator**, a seasoned technical product manager opening a conversation with the human. Your role is to demonstrate understanding through specific observations, not generic praise.

$project_context

## Corpus Summary
$corpus_summary

## Guidelines

Write a warm, professional opening (3-5 sentences) that:
1. Acknowledges you've reviewed their materials (be specific, not generic)
2. Shares 1-2 observations that show genuine understanding
3. Asks ONE probing question to start the dialogue

**Tone**: Curious and professional. NOT sycophantic ("This is amazing!") or generic ("I see you're building software").

## Example Openings

**Good** (specific, curious):
"I've been through your API documentation and the architecture notes. I notice you're using event sourcing for the order system but REST for the inventory service - that's an interesting hybrid. What drove that decision?"

**Bad** (generic, sycophantic):
"Wow, this looks like a great project! I can see you've put a lot of thought into it. Tell me more about what you're building."

## Edge Cases

- If corpus is sparse: "The materials are limited, so I'd love to hear directly from you about..."
- If corpus is contradictory: "I noticed some different approaches mentioned - [X] in one doc and [Y] in another. Which direction are you leaning?"
- If corpus is very technical: Focus on the "why" not the "what"

Output ONLY your opening message, no formatting or meta-commentary.
EOF

        atomic_waiting "Preparing opening..."

        if atomic_invoke "$prompts_dir/dialogue-opening.md" "$prompts_dir/opening-response.txt" "Generate opening"; then
            agent_opening=$(cat "$prompts_dir/opening-response.txt")
            [[ "${ATOMIC_STREAM:-true}" == "true" && -t 2 ]] && _opening_streamed=true
        else
            agent_opening="I've reviewed the materials you've gathered. I see some interesting patterns and have questions. What's the core problem you're trying to solve?"
        fi
    else
        # Greenfield - ask for initial vision
        agent_opening="This looks like a fresh start - exciting! Before we dive in, I'd love to hear your vision in your own words. What are you trying to build, and why does it matter to you?"
    fi

    # Display agent opening (skip content if streaming already showed it)
    echo -e "  ${CYAN}Agent:${NC}"
    echo ""
    if [[ "$_opening_streamed" != true ]]; then
        echo "$agent_opening" | fold -s -w 60 | while IFS= read -r line; do
            echo -e "    $line"
        done
        echo ""
    fi

    # Log the opening
    echo "## Turn 1" >> "$conversation_log"
    echo "" >> "$conversation_log"
    echo "**Agent:** $agent_opening" >> "$conversation_log"
    echo "" >> "$conversation_log"

    dialogue=$(echo "$dialogue" | jq --arg msg "$agent_opening" '.conversation += [{"role": "agent", "content": $msg}]')
    ((turn++))

    # Main conversation loop
    while [[ "$conversation_complete" == false ]]; do

        # Input collection with redo/undo support
        local human_response=""
        local input_accepted=false

        while [[ "$input_accepted" == false ]]; do
            echo -e "  ${GREEN}You:${NC}"
            echo ""

            # Multi-line input
            human_response=""
            local empty_count=0
            while true; do
                read -e -p "    " line || true
                if [[ -z "$line" ]]; then
                    ((empty_count++))
                    [[ $empty_count -ge 1 ]] && break
                else
                    empty_count=0
                    human_response+="$line"$'\n'
                fi
            done

            # Trim whitespace for command checking
            local trimmed_response
            trimmed_response=$(echo "$human_response" | tr -d '[:space:]')

            # Check for undo command
            if [[ "${trimmed_response,,}" == "undo" ]]; then
                if [[ $turn -gt 1 ]]; then
                    # Remove last agent message from dialogue
                    dialogue=$(echo "$dialogue" | jq '.conversation = .conversation[:-1]')
                    ((turn--))
                    echo ""
                    echo -e "  ${YELLOW}↩${NC}  Last exchange undone. Conversation rolled back."
                    echo ""
                    # Show the current last message (previous agent response)
                    local prev_msg
                    prev_msg=$(echo "$dialogue" | jq -r '.conversation[-1].content // empty')
                    if [[ -n "$prev_msg" ]]; then
                        echo -e "  ${CYAN}Agent:${NC} ${DIM}(restored)${NC}"
                        echo ""
                        echo "$prev_msg" | fold -s -w 60 | while IFS= read -r _l; do echo -e "    $_l"; done
                        echo ""
                    fi
                    continue
                else
                    echo -e "  ${YELLOW}!${NC} Nothing to undo"
                    continue
                fi
            fi

            # Check for exit commands or empty input
            if [[ "${trimmed_response,,}" =~ ^(done|finished|thatsit|exit|quit)$ ]] || [[ -z "$trimmed_response" ]]; then
                if [[ $turn -lt 3 ]]; then
                    echo ""
                    echo -e "    ${YELLOW}We should talk a bit more to ensure I understand your vision.${NC}"
                    echo -e "    ${DIM}Please share your thoughts, or type 'skip' to force exit.${NC}"
                    echo ""

                    read -e -p "    " force_response || true
                    if [[ "${force_response,,}" == "skip" ]]; then
                        conversation_complete=true
                        input_accepted=true
                        break
                    fi
                    human_response="$force_response"$'\n'
                    input_accepted=true
                else
                    conversation_complete=true
                    input_accepted=true
                    break
                fi
            else
                # Confirm before sending
                echo -e "  ${DIM}[Enter] send  [r] redo  [u] undo last${NC}"
                local _confirm
                read -e -p "  " _confirm || true
                case "${_confirm,,}" in
                    r|redo)
                        echo ""
                        continue  # back to input collection
                        ;;
                    u|undo)
                        if [[ $turn -gt 1 ]]; then
                            dialogue=$(echo "$dialogue" | jq '.conversation = .conversation[:-1]')
                            ((turn--))
                            echo ""
                            echo -e "  ${YELLOW}↩${NC}  Last exchange undone."
                            echo ""
                            local prev_msg2
                            prev_msg2=$(echo "$dialogue" | jq -r '.conversation[-1].content // empty')
                            if [[ -n "$prev_msg2" ]]; then
                                echo -e "  ${CYAN}Agent:${NC} ${DIM}(restored)${NC}"
                                echo ""
                                echo "$prev_msg2" | fold -s -w 60 | while IFS= read -r _l; do echo -e "    $_l"; done
                                echo ""
                            fi
                        else
                            echo -e "  ${YELLOW}!${NC} Nothing to undo"
                        fi
                        continue
                        ;;
                    *)
                        input_accepted=true
                        ;;
                esac
            fi
        done

        # If conversation was completed via exit command, break
        [[ "$conversation_complete" == true ]] && break

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
        # First, check if conversation needs adjudication (context gardener)
        local primary_model=$(atomic_get_model primary)
        dialogue=$(atomic_context_adjudicate "$dialogue" "Opening Dialogue" "$primary_model")

        local conversation_so_far
        conversation_so_far=$(jq -r '.conversation | map("\(.role): \(.content)") | join("\n\n")' <<< "$dialogue")

        cat > "$prompts_dir/dialogue-continue.md" << EOF
# Task: Continue the Discovery Dialogue

You are the **discovery-facilitator** in an ongoing conversation. Your role is to gather understanding through genuine curiosity, not interrogation.

$project_context

## Conversation So Far
$conversation_so_far

## Current Focus Area
$probe_focus

## Response Guidelines

Based on what they just said:
1. **Acknowledge** their point (briefly, genuinely - avoid "That's great!" or "Absolutely!")
2. **Connect** to something specific they said (shows you're listening)
3. **Probe** with a follow-up about: $probe_focus

If you have enough on this topic:
- Briefly summarize your understanding and confirm
- Transition naturally to the next area

## Example Responses

**Good** (specific, builds on their input):
"The three-tier compliance requirement makes sense given the healthcare context. When you say 'fast iteration,' are we talking days or weeks between releases? That'll affect how we approach the testing strategy."

**Bad** (generic, doesn't build):
"That's really helpful. Can you tell me more about the constraints?"

## Conversation Flow

- Keep responses to 2-4 sentences
- Ask ONE question per turn (not a list)
- If they seem stuck, offer a concrete option: "Would [X] or [Y] be closer to what you're thinking?"
- If they're verbose, gently focus: "Lots of good points there. Let me make sure I caught the key one..."

## Edge Cases

- **User is brief/terse**: Ask more specific questions, offer examples
- **User is verbose**: Summarize and confirm understanding
- **User seems uncertain**: Offer options or examples to react to
- **Topic change**: Acknowledge the shift, file away the previous context

Output ONLY your response, no formatting or meta-commentary.
EOF

        atomic_waiting "Thinking..."

        local agent_response=""
        local _response_streamed=false
        if atomic_invoke "$prompts_dir/dialogue-continue.md" "$prompts_dir/continue-response.txt" "Continue dialogue"; then
            agent_response=$(cat "$prompts_dir/continue-response.txt")
            [[ "${ATOMIC_STREAM:-true}" == "true" && -t 2 ]] && _response_streamed=true
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

    # Check if conversation was adjudicated - include those summaries for complete picture
    local adjudication_context=""
    if echo "$dialogue" | jq -e '.adjudication_history | length > 0' &>/dev/null; then
        adjudication_context=$(echo "$dialogue" | jq -r '
            .adjudication_history | map(
                "### Captured at adjudication:\n" +
                "Decisions: " + (.decisions_made | join("; ")) + "\n" +
                "Open threads: " + (.open_threads | join("; ")) + "\n" +
                "Key context: " + (.key_context // "N/A")
            ) | join("\n\n")
        ')
    fi

    cat > "$prompts_dir/dialogue-synthesis.md" << 'EOF'
# Task: Synthesize Dialogue into Structured Output

You are a **synthesis specialist** extracting structured data from a natural conversation. Your role is to capture what was actually said, not infer or embellish.

## Extraction Principles

1. **Quote when possible**: Use the human's actual words for key concepts
2. **Mark uncertainty**: If something wasn't discussed, use "Not discussed" not a guess
3. **Preserve nuance**: If they said "maybe" or "probably," don't convert to certainty
4. **Capture open questions**: Things that need follow-up are valuable to track

## Conversation
EOF
    echo "$full_conversation" >> "$prompts_dir/dialogue-synthesis.md"

    # Include adjudication history if conversation was compressed
    if [[ -n "$adjudication_context" ]]; then
        cat >> "$prompts_dir/dialogue-synthesis.md" << EOF

## Earlier Context (from conversation compression)
$adjudication_context
EOF
    fi

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

## Example Output

{
    "vision": {
        "core_problem": "Small businesses struggle to track inventory across multiple sales channels",
        "solution_concept": "Unified dashboard that syncs with Shopify, Amazon, and POS systems",
        "why_now": "Post-COVID e-commerce boom created this multi-channel challenge"
    },
    "impact": {
        "primary_impact": "Reduce stockouts by 80% and over-ordering by 50%",
        "success_metrics": ["Time to reconcile inventory < 5 min/day", "Zero oversells", "NPS > 50"],
        "timeline_to_value": "MVP in 3 months, measurable impact by month 6"
    },
    "audience": {
        "primary": "Small retail businesses (5-50 employees) selling on 2+ channels",
        "secondary": ["Warehouse staff", "Accountants needing inventory reports"],
        "pain_points": ["Manual spreadsheet updates", "Overselling during sales events", "No real-time visibility"]
    },
    "constraints": {
        "tech_stack": "Must integrate with Shopify API; prefer TypeScript",
        "timeline": "Beta by Q2, launch by Q3",
        "team_size": "2 developers",
        "budget": "Not discussed",
        "compliance": ["PCI for payment data if stored"],
        "other": ["Must work offline for POS sync"]
    },
    "non_negotiables": ["Real-time sync - no batch updates", "Mobile-friendly dashboard"],
    "open_questions": ["How to handle returns across channels?", "Pricing model not finalized"]
}

## Edge Cases

- **Short conversation**: Fill in what you have, use "Not discussed" liberally
- **Contradictory statements**: Note the contradiction in open_questions
- **Vague answers**: Quote the vague answer rather than interpreting

Output ONLY valid JSON, no markdown wrapper.
EOF

    atomic_waiting "Synthesizing..."

    if atomic_invoke "$prompts_dir/dialogue-synthesis.md" "$prompts_dir/synthesis.json" "Synthesize dialogue"; then
        # Extract JSON from Claude output (strips preamble text and code fences)
        atomic_extract_json "$prompts_dir/synthesis.json" "$prompts_dir/synthesis.json" 2>/dev/null
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
            read -e -p "  > " confirm || true

            if [[ "${confirm,,}" =~ ^n ]]; then
                echo ""
                echo -e "  ${DIM}What should be corrected?${NC}"
                read -e -p "  > " corrections || true
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
