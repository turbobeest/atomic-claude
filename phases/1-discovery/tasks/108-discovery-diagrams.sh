#!/bin/bash
#
# Task 108: Discovery Diagrams
# Generate standard software architecture diagrams in DOT format
#
# Diagram types:
#   - System Context (C4 Level 1)
#   - Container/Component View (C4 Level 2)
#   - Data Flow Diagram
#   - Sequence Diagrams (key flows)
#   - State Diagram (if applicable)
#   - Deployment/Operational View
#   - Entity Relationship Diagram
#
# Output: docs/diagrams/*.dot + *.svg
#

task_108_discovery_diagrams() {
    local phase1_dir="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE"
    local diagrams_dir="$ATOMIC_ROOT/docs/diagrams"
    local prompts_dir="$phase1_dir/prompts"

    atomic_step "Discovery Diagrams"

    mkdir -p "$diagrams_dir" "$prompts_dir"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ DISCOVERY DIAGRAMS                                      │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Generate standard architecture diagrams based on the   │${NC}"
    echo -e "${DIM}  │ selected approach. DOT files will be converted to SVG  │${NC}"
    echo -e "${DIM}  │ for human review.                                       │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # CHECK PREREQUISITES
    # ═══════════════════════════════════════════════════════════════════════════

    # Check for graphviz
    if ! command -v dot &>/dev/null; then
        echo -e "  ${YELLOW}!${NC} graphviz not installed - SVG generation will be skipped"
        echo -e "    ${DIM}Install with: sudo apt install graphviz${NC}"
        echo ""
        local has_graphviz=false
    else
        local has_graphviz=true
        local dot_version=$(dot -V 2>&1 | head -1)
        echo -e "  ${GREEN}✓${NC} graphviz available ($dot_version)"
        echo ""
    fi

    # Load approach context
    local approach_file="$phase1_dir/selected-approach.json"
    local approach_name="unknown"
    local approach_summary=""

    if [[ -f "$approach_file" ]]; then
        approach_name=$(jq -r '.name // "unnamed"' "$approach_file")
        approach_summary=$(jq -r '.summary // ""' "$approach_file")
        echo -e "  ${GREEN}✓${NC} Loaded approach: $approach_name"
    else
        echo -e "  ${YELLOW}!${NC} No selected approach found - using generic diagrams"
    fi

    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # DIAGRAM TYPE SELECTION
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}DIAGRAM TYPE SELECTION${NC}                                    ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${DIM}Select diagrams to generate (space-separated numbers):${NC}"
    echo ""
    echo -e "    ${BOLD}1.${NC} System Context     ${DIM}- C4 Level 1: System + external actors${NC}"
    echo -e "    ${BOLD}2.${NC} Container View     ${DIM}- C4 Level 2: High-level components${NC}"
    echo -e "    ${BOLD}3.${NC} Component View     ${DIM}- C4 Level 3: Internal structure${NC}"
    echo -e "    ${BOLD}4.${NC} Data Flow          ${DIM}- How data moves through system${NC}"
    echo -e "    ${BOLD}5.${NC} Sequence Diagram   ${DIM}- Key interaction flows${NC}"
    echo -e "    ${BOLD}6.${NC} State Diagram      ${DIM}- State machine for key entities${NC}"
    echo -e "    ${BOLD}7.${NC} Deployment View    ${DIM}- Infrastructure/operational${NC}"
    echo -e "    ${BOLD}8.${NC} ER Diagram         ${DIM}- Entity relationships/data model${NC}"
    echo ""
    echo -e "    ${GREEN}[all]${NC}  Generate all applicable diagrams"
    echo -e "    ${YELLOW}[minimal]${NC}  System Context + Container only"
    echo -e "    ${CYAN}[standard]${NC}  Context + Container + Data Flow + Deployment"
    echo ""

    read -p "  Selection [standard]: " diagram_selection
    diagram_selection=${diagram_selection:-standard}

    local selected_diagrams=()

    case "$diagram_selection" in
        all)
            selected_diagrams=("system-context" "container" "component" "data-flow" "sequence" "state" "deployment" "er-diagram")
            ;;
        minimal)
            selected_diagrams=("system-context" "container")
            ;;
        standard)
            selected_diagrams=("system-context" "container" "data-flow" "deployment")
            ;;
        *)
            # Parse space-separated numbers
            for num in $diagram_selection; do
                case "$num" in
                    1) selected_diagrams+=("system-context") ;;
                    2) selected_diagrams+=("container") ;;
                    3) selected_diagrams+=("component") ;;
                    4) selected_diagrams+=("data-flow") ;;
                    5) selected_diagrams+=("sequence") ;;
                    6) selected_diagrams+=("state") ;;
                    7) selected_diagrams+=("deployment") ;;
                    8) selected_diagrams+=("er-diagram") ;;
                esac
            done
            ;;
    esac

    echo ""
    echo -e "  ${GREEN}✓${NC} Selected: ${selected_diagrams[*]}"
    echo ""

    # ═══════════════════════════════════════════════════════════════════════════
    # GATHER CONTEXT FOR DIAGRAMS
    # ═══════════════════════════════════════════════════════════════════════════

    # Load additional context
    local dialogue_context=""
    if [[ -f "$phase1_dir/dialogue.json" ]]; then
        dialogue_context=$(jq -r '.vision // ""' "$phase1_dir/dialogue.json")
    fi

    local corpus_context=""
    if [[ -f "$phase1_dir/corpus.json" ]]; then
        corpus_context=$(jq -c '.materials[:3] // []' "$phase1_dir/corpus.json" 2>/dev/null || echo "[]")
    fi

    local direction_context=""
    if [[ -f "$phase1_dir/direction-confirmed.json" ]]; then
        # Extract only key fields needed for diagrams, not full JSON
        direction_context=$(jq -r '
            "Approach: " + (.approach // "unspecified") + "\n" +
            "Key Components: " + ((.components // []) | join(", ")) + "\n" +
            "Architecture Style: " + (.architecture_style // "unspecified") + "\n" +
            "Key Decisions: " + ((.key_decisions // [])[:5] | join("; "))
        ' "$phase1_dir/direction-confirmed.json" 2>/dev/null || echo "Direction details not available")
    fi

    # Load tech stack from project config for accurate naming
    local tech_stack_context=""
    local project_config="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
    if [[ -f "$project_config" ]]; then
        tech_stack_context=$(jq -r '
            .extracted.constraints // {} |
            "Tech Stack:\n" +
            "- Infrastructure: " + (.infrastructure // "unspecified") + "\n" +
            "- Technologies: " + ((.technical // []) | join(", "))
        ' "$project_config" 2>/dev/null || echo "")
    fi

    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATE DIAGRAMS
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}GENERATING DIAGRAMS${NC}                                       ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    local generated_count=0
    local failed_count=0

    for diagram_type in "${selected_diagrams[@]}"; do
        echo -e "  ${DIM}[$diagram_type]${NC}"

        # Generate DOT file
        if _108_generate_diagram "$diagram_type" "$diagrams_dir" "$prompts_dir" \
            "$approach_name" "$approach_summary" "$dialogue_context" "$direction_context" "$tech_stack_context"; then

            local dot_file="$diagrams_dir/$diagram_type.dot"

            if [[ -f "$dot_file" ]]; then
                echo -e "    ${GREEN}✓${NC} Generated $diagram_type.dot"
                ((generated_count++))

                # Convert to SVG if graphviz available
                if [[ "$has_graphviz" == true ]]; then
                    if dot -Tsvg "$dot_file" -o "$diagrams_dir/$diagram_type.svg" 2>/dev/null; then
                        echo -e "    ${GREEN}✓${NC} Generated $diagram_type.svg"
                    else
                        echo -e "    ${YELLOW}!${NC} SVG conversion failed"
                    fi
                fi
            else
                echo -e "    ${RED}✗${NC} Failed to generate"
                ((failed_count++))
            fi
        else
            echo -e "    ${RED}✗${NC} Generation failed"
            ((failed_count++))
        fi

        echo ""
    done

    # ═══════════════════════════════════════════════════════════════════════════
    # DIAGRAM MANIFEST
    # ═══════════════════════════════════════════════════════════════════════════

    local manifest_file="$diagrams_dir/manifest.json"

    # Build diagrams array
    local diagrams_json="[]"
    for diagram_type in "${selected_diagrams[@]}"; do
        local dot_file="$diagrams_dir/$diagram_type.dot"
        local svg_file="$diagrams_dir/$diagram_type.svg"

        if [[ -f "$dot_file" ]]; then
            local has_svg="false"
            [[ -f "$svg_file" ]] && has_svg="true"

            diagrams_json=$(echo "$diagrams_json" | jq \
                --arg type "$diagram_type" \
                --arg dot "$dot_file" \
                --arg svg "$svg_file" \
                --argjson has_svg "$has_svg" \
                '. += [{
                    "type": $type,
                    "dot_file": $dot,
                    "svg_file": $svg,
                    "has_svg": $has_svg
                }]')
        fi
    done

    jq -n \
        --arg approach "$approach_name" \
        --argjson diagrams "$diagrams_json" \
        --argjson generated "$generated_count" \
        --argjson failed "$failed_count" \
        '{
            "approach": $approach,
            "diagrams": $diagrams,
            "summary": {
                "generated": $generated,
                "failed": $failed
            },
            "generated_at": (now | todate)
        }' > "$manifest_file"

    # ═══════════════════════════════════════════════════════════════════════════
    # HUMAN REVIEW
    # ═══════════════════════════════════════════════════════════════════════════

    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}DIAGRAM REVIEW${NC}                                            ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "  ${BOLD}Generated: $generated_count${NC} diagrams"
    [[ $failed_count -gt 0 ]] && echo -e "  ${YELLOW}Failed: $failed_count${NC}"
    echo ""
    echo -e "  ${DIM}Location: $diagrams_dir${NC}"
    echo ""

    # List generated files
    echo -e "  ${CYAN}Files:${NC}"
    for diagram_type in "${selected_diagrams[@]}"; do
        local dot_file="$diagrams_dir/$diagram_type.dot"
        local svg_file="$diagrams_dir/$diagram_type.svg"

        if [[ -f "$dot_file" ]]; then
            local dot_lines=$(wc -l < "$dot_file")
            if [[ -f "$svg_file" ]]; then
                echo -e "    ${GREEN}●${NC} $diagram_type.dot ($dot_lines lines) + .svg"
            else
                echo -e "    ${YELLOW}●${NC} $diagram_type.dot ($dot_lines lines) ${DIM}(no SVG)${NC}"
            fi
        fi
    done
    echo ""

    # Review options
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${CYAN}Review options:${NC}"
    echo ""
    echo -e "    ${GREEN}[approve]${NC}   Accept diagrams and continue"
    echo -e "    ${YELLOW}[view]${NC}      View a specific diagram"
    echo -e "    ${CYAN}[open]${NC}      Open SVGs in browser (if available)"
    echo -e "    ${MAGENTA}[regenerate]${NC} Regenerate a specific diagram"
    echo ""

    while true; do
        read -p "  Choice [approve]: " review_choice
        review_choice=${review_choice:-approve}

        case "$review_choice" in
            approve|a)
                break
                ;;
            view|v)
                echo ""
                echo -e "  ${DIM}Available: ${selected_diagrams[*]}${NC}"
                read -p "  Which diagram? " view_name

                local view_file="$diagrams_dir/$view_name.dot"
                if [[ -f "$view_file" ]]; then
                    echo ""
                    echo -e "${DIM}━━━━━━━━━━ $view_name.dot ━━━━━━━━━━${NC}"
                    head -50 "$view_file" | sed 's/^/  /'
                    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                else
                    echo -e "  ${RED}File not found${NC}"
                fi
                echo ""
                ;;
            open|o)
                if [[ "$has_graphviz" == true ]]; then
                    # Try to open SVGs
                    local svg_files=("$diagrams_dir"/*.svg)
                    if [[ -f "${svg_files[0]}" ]]; then
                        if command -v xdg-open &>/dev/null; then
                            xdg-open "$diagrams_dir" 2>/dev/null &
                            echo -e "  ${GREEN}✓${NC} Opened diagram directory"
                        elif command -v open &>/dev/null; then
                            open "$diagrams_dir" 2>/dev/null &
                            echo -e "  ${GREEN}✓${NC} Opened diagram directory"
                        else
                            echo -e "  ${YELLOW}!${NC} Cannot open - view files at: $diagrams_dir"
                        fi
                    else
                        echo -e "  ${YELLOW}!${NC} No SVG files found"
                    fi
                else
                    echo -e "  ${YELLOW}!${NC} No SVG files - graphviz not installed"
                fi
                echo ""
                ;;
            regenerate|r)
                echo ""
                echo -e "  ${DIM}Available: ${selected_diagrams[*]}${NC}"
                read -p "  Which diagram? " regen_name

                if _108_generate_diagram "$regen_name" "$diagrams_dir" "$prompts_dir" \
                    "$approach_name" "$approach_summary" "$dialogue_context" "$direction_context" "$tech_stack_context"; then
                    echo -e "  ${GREEN}✓${NC} Regenerated $regen_name.dot"

                    if [[ "$has_graphviz" == true ]]; then
                        dot -Tsvg "$diagrams_dir/$regen_name.dot" -o "$diagrams_dir/$regen_name.svg" 2>/dev/null
                        echo -e "  ${GREEN}✓${NC} Regenerated $regen_name.svg"
                    fi
                else
                    echo -e "  ${RED}✗${NC} Regeneration failed"
                fi
                echo ""
                ;;
            *)
                echo -e "  ${DIM}Invalid choice${NC}"
                ;;
        esac
    done

    echo ""

    atomic_context_artifact "discovery-diagrams" "$manifest_file" "Architecture diagrams manifest"
    atomic_context_decision "Generated $generated_count discovery diagrams" "diagrams"

    atomic_success "Discovery diagrams complete"

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# DIAGRAM GENERATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_108_generate_diagram() {
    local diagram_type="$1"
    local output_dir="$2"
    local prompts_dir="$3"
    local approach_name="$4"
    local approach_summary="$5"
    local vision="$6"
    local direction="$7"
    local tech_stack="${8:-}"

    local prompt_file="$prompts_dir/diagram-$diagram_type.md"
    local output_file="$output_dir/$diagram_type.dot"

    # Complexity guidance per diagram type
    local complexity_guidance=""
    case "$diagram_type" in
        system-context) complexity_guidance="Target: 3-8 nodes. Show system + external actors/systems only." ;;
        container) complexity_guidance="Target: 5-15 nodes. Show major containers, not internal details." ;;
        component) complexity_guidance="Target: 8-20 nodes. Show internal structure of ONE container." ;;
        data-flow) complexity_guidance="Target: 5-12 nodes. Focus on main data paths, not edge cases." ;;
        sequence) complexity_guidance="Target: 3-6 lifelines, 5-15 messages. Show ONE key flow." ;;
        state) complexity_guidance="Target: 4-10 states. Show main states, not every edge case." ;;
        deployment) complexity_guidance="Target: 6-15 nodes. Show infrastructure, not app internals." ;;
        er-diagram) complexity_guidance="Target: 4-12 entities. Show core domain, not audit fields." ;;
    esac

    # Get diagram-specific instructions with mini-example
    local diagram_instructions=""
    case "$diagram_type" in
        system-context)
            diagram_instructions="Create a C4 System Context diagram showing:
- The main system as a central box
- External users/actors (stick figures or boxes)
- External systems that interact with this system
- Relationships with labeled arrows
Use: digraph, subgraph for grouping, node shapes (box, ellipse)"
            ;;
        container)
            diagram_instructions="Create a C4 Container diagram showing:
- Major containers/services within the system boundary
- Databases, APIs, web apps, microservices
- Communication protocols on arrows (HTTP, gRPC, etc.)
- External system boundaries
Use: subgraph cluster_ for system boundaries, different shapes for different container types"
            ;;
        component)
            diagram_instructions="Create a C4 Component diagram showing:
- Internal components within a key container
- Classes, modules, or packages
- Dependencies between components
- Interfaces/ports
Use: record shapes for detailed components, dashed lines for interfaces"
            ;;
        data-flow)
            diagram_instructions="Create a Data Flow Diagram (DFD) showing:
- Data sources and sinks
- Processes that transform data
- Data stores
- Data flows with labels describing what data moves
Use: ellipses for processes, open rectangles for external entities, parallel lines for stores"
            ;;
        sequence)
            diagram_instructions="Create a sequence-like diagram showing:
- Key actors/components as vertical lifelines
- Messages/calls between them in order
- Return values
Note: DOT isn't ideal for sequence diagrams, use ranked subgraphs to show order"
            ;;
        state)
            diagram_instructions="Create a State Diagram showing:
- States as rounded boxes
- Transitions with event/condition labels
- Initial and final states
- Guard conditions in brackets
Use: node [shape=ellipse] for states, edge labels for transitions"
            ;;
        deployment)
            diagram_instructions="Create a Deployment/Infrastructure diagram showing:
- Physical or cloud infrastructure
- Servers, containers, load balancers
- Network zones (DMZ, private, etc.)
- Deployment artifacts
Use: subgraph cluster_ for zones, box3d shape for servers"
            ;;
        er-diagram)
            diagram_instructions="Create an Entity-Relationship diagram showing:
- Entities as boxes with attributes
- Relationships with cardinality (1:1, 1:N, N:M)
- Primary keys and foreign keys
- Relationship labels
Use: record shape for entities with fields, edge labels for relationships"
            ;;
    esac

    # Build context section, handling empty values gracefully
    local context_section=""
    [[ -n "$approach_name" && "$approach_name" != "unknown" ]] && context_section+="**Approach:** $approach_name"$'\n'
    [[ -n "$approach_summary" ]] && context_section+="$approach_summary"$'\n\n'
    [[ -n "$vision" ]] && context_section+="**Vision:** $vision"$'\n\n'
    [[ -n "$direction" ]] && context_section+="**Direction:**"$'\n'"$direction"$'\n\n'
    [[ -n "$tech_stack" ]] && context_section+="$tech_stack"$'\n'

    # Default context if nothing available
    [[ -z "$context_section" ]] && context_section="No specific project context provided. Create a representative diagram for a typical software system."

    cat > "$prompt_file" << EOF
# Task: Generate $diagram_type Diagram

You are a software architect creating a DOT (Graphviz) diagram that will be reviewed by developers, architects, and stakeholders. The diagram should be understandable in 30 seconds.

## Project Context

$context_section

## Diagram Type: $diagram_type

$diagram_instructions

## Complexity Guidance

$complexity_guidance

## Quality Checklist (follow these)

- [ ] All nodes have clear, specific labels (not generic "Service" or "Component")
- [ ] All edges have meaningful labels describing the relationship/protocol
- [ ] Logical groupings use subgraphs with descriptive labels
- [ ] Node count is appropriate (see complexity guidance above)
- [ ] No orphan nodes - everything connects to something
- [ ] Labels use actual names from tech stack when provided

## Anti-Patterns (avoid these)

- Generic labels like "Service A", "Component 1", "Database" without specifics
- Unlabeled edges (every arrow should explain what flows/happens)
- More than 3 levels of subgraph nesting
- Mixing concerns (don't put deployment details in a data flow diagram)
- Too many nodes (causes visual overload) or too few (lacks useful detail)
- Missing the system boundary for context/container diagrams

## DOT Format Requirements

1. Start with: digraph ${diagram_type//-/_} {
2. Include: rankdir, splines=ortho, nodesep, ranksep
3. Define node defaults: node [shape=..., style=..., fontname="Arial"]
4. Define edge defaults: edge [fontname="Arial", fontsize=10]
5. Use subgraph cluster_X for grouping (cluster_ prefix required for boxes)
6. Use snake_case node IDs that are meaningful
7. Add // comments to organize sections

## Output

Output ONLY valid DOT code. No markdown fences, no explanation, no preamble.

## Good Example

digraph example {
    // Graph settings
    rankdir=TB
    splines=ortho
    nodesep=0.8
    ranksep=1.0

    // Node defaults
    node [shape=box, style="rounded,filled", fillcolor="#E8E8E8", fontname="Arial"]
    edge [fontname="Arial", fontsize=10]

    // External actors
    subgraph cluster_external {
        label="External"
        style=dashed
        user [label="End User", shape=ellipse]
    }

    // System boundary
    subgraph cluster_system {
        label="Order Management System"
        style=filled
        fillcolor="#F5F5F5"
        order_api [label="Order API\\n[Node.js]"]
        order_db [label="Orders DB\\n[PostgreSQL]", shape=cylinder]
    }

    // Relationships with labels
    user -> order_api [label="REST/HTTPS"]
    order_api -> order_db [label="SQL queries"]
}

## Bad Example (DO NOT do this)

digraph bad {
    // No graph settings
    a -> b -> c -> d  // Generic labels, no context
    service [label="Service"]  // Vague - which service?
    db [label="Database"]  // Vague - what database?
    service -> db  // No label - what flows here?
    // Missing system boundary
    // No technology annotations
}

## Error Recovery

If you're unsure about something:
- Use placeholder text like "[TBD: specific service name]" rather than generic "Service"
- For unknown tech, use "[Technology TBD]" in the label
- If relationships are unclear, add "?" to the label: "calls? (verify)"

Always output SYNTACTICALLY valid DOT even if the content needs refinement.
EOF

    # Use atomic_invoke if available, otherwise create template
    if type atomic_invoke &>/dev/null; then
        atomic_invoke "$prompt_file" "$output_file" "Generate $diagram_type diagram" --model=sonnet
        return $?
    else
        # Fallback: create template diagram
        _108_create_template_diagram "$diagram_type" "$output_file" "$approach_name"
        return 0
    fi
}

# Create template diagram when LLM not available
_108_create_template_diagram() {
    local diagram_type="$1"
    local output_file="$2"
    local approach_name="$3"

    case "$diagram_type" in
        system-context)
            cat > "$output_file" << 'EOF'
digraph system_context {
    rankdir=TB
    splines=ortho
    nodesep=1.0
    ranksep=1.2

    // Styling
    node [shape=box, style="rounded,filled", fillcolor="#438DD5", fontcolor=white, fontname="Arial"]
    edge [fontname="Arial", fontsize=10]

    // External Users
    subgraph cluster_users {
        label=""
        style=invis
        user [label="User", shape=ellipse, fillcolor="#08427B"]
        admin [label="Admin", shape=ellipse, fillcolor="#08427B"]
    }

    // Main System
    system [label="System\n[Software System]\n\nMain application", shape=box, width=3, height=1.5]

    // External Systems
    subgraph cluster_external {
        label="External Systems"
        style=dashed
        color=gray
        external_api [label="External API\n[External System]", fillcolor="#999999"]
        database [label="Database\n[Database]", shape=cylinder, fillcolor="#438DD5"]
    }

    // Relationships
    user -> system [label="Uses"]
    admin -> system [label="Administers"]
    system -> external_api [label="API calls"]
    system -> database [label="Reads/Writes"]
}
EOF
            ;;
        container)
            cat > "$output_file" << 'EOF'
digraph container {
    rankdir=TB
    splines=ortho
    nodesep=0.8
    ranksep=1.0
    compound=true

    node [shape=box, style="rounded,filled", fontname="Arial"]
    edge [fontname="Arial", fontsize=10]

    // System Boundary
    subgraph cluster_system {
        label="System Boundary"
        style="rounded,filled"
        fillcolor="#F5F5F5"
        color="#438DD5"

        web_app [label="Web Application\n[Container: React]\n\nUser interface", fillcolor="#438DD5", fontcolor=white]
        api [label="API Server\n[Container: Node.js]\n\nBusiness logic", fillcolor="#438DD5", fontcolor=white]
        worker [label="Background Worker\n[Container: Node.js]\n\nAsync processing", fillcolor="#438DD5", fontcolor=white]
        db [label="Database\n[Container: PostgreSQL]\n\nData storage", shape=cylinder, fillcolor="#438DD5", fontcolor=white]
        cache [label="Cache\n[Container: Redis]\n\nSession/cache", shape=cylinder, fillcolor="#438DD5", fontcolor=white]
    }

    // External
    user [label="User", shape=ellipse, fillcolor="#08427B", fontcolor=white]

    // Relationships
    user -> web_app [label="HTTPS"]
    web_app -> api [label="JSON/REST"]
    api -> db [label="SQL"]
    api -> cache [label="Redis protocol"]
    api -> worker [label="Message queue"]
    worker -> db [label="SQL"]
}
EOF
            ;;
        data-flow)
            cat > "$output_file" << 'EOF'
digraph data_flow {
    rankdir=LR
    splines=ortho
    nodesep=0.8

    node [fontname="Arial"]
    edge [fontname="Arial", fontsize=10]

    // External Entities
    user [label="User", shape=box, style=filled, fillcolor="#E8E8E8"]
    external [label="External\nSystem", shape=box, style=filled, fillcolor="#E8E8E8"]

    // Processes
    process1 [label="1.0\nProcess\nInput", shape=ellipse, style=filled, fillcolor="#B5D8EB"]
    process2 [label="2.0\nTransform\nData", shape=ellipse, style=filled, fillcolor="#B5D8EB"]
    process3 [label="3.0\nOutput\nResults", shape=ellipse, style=filled, fillcolor="#B5D8EB"]

    // Data Stores
    store1 [label="D1 | Main Data Store", shape=record, style=filled, fillcolor="#FFE599"]

    // Data Flows
    user -> process1 [label="Input data"]
    process1 -> store1 [label="Store raw"]
    store1 -> process2 [label="Retrieve"]
    process2 -> process3 [label="Processed"]
    process3 -> user [label="Results"]
    external -> process2 [label="External data"]
}
EOF
            ;;
        deployment)
            cat > "$output_file" << 'EOF'
digraph deployment {
    rankdir=TB
    splines=ortho
    nodesep=0.6
    ranksep=0.8

    node [shape=box3d, style=filled, fontname="Arial"]
    edge [fontname="Arial", fontsize=10]

    // Cloud/Infrastructure
    subgraph cluster_cloud {
        label="Cloud Infrastructure"
        style="rounded,filled"
        fillcolor="#E8F4E8"
        color="#228B22"

        // Load Balancer
        lb [label="Load Balancer\n[nginx]", shape=box, fillcolor="#90EE90"]

        // Application Tier
        subgraph cluster_app {
            label="Application Tier"
            style=filled
            fillcolor="#F0F0F0"
            app1 [label="App Server 1\n[Docker]", fillcolor="#87CEEB"]
            app2 [label="App Server 2\n[Docker]", fillcolor="#87CEEB"]
        }

        // Data Tier
        subgraph cluster_data {
            label="Data Tier"
            style=filled
            fillcolor="#F0F0F0"
            db_primary [label="DB Primary\n[PostgreSQL]", shape=cylinder, fillcolor="#DDA0DD"]
            db_replica [label="DB Replica\n[PostgreSQL]", shape=cylinder, fillcolor="#DDA0DD"]
            cache [label="Cache\n[Redis]", shape=cylinder, fillcolor="#FFB6C1"]
        }
    }

    // Connections
    lb -> app1
    lb -> app2
    app1 -> db_primary
    app2 -> db_primary
    db_primary -> db_replica [label="replication", style=dashed]
    app1 -> cache
    app2 -> cache
}
EOF
            ;;
        *)
            # Generic template for other types
            cat > "$output_file" << EOF
digraph $diagram_type {
    rankdir=TB
    splines=ortho
    nodesep=0.8
    ranksep=1.0

    node [shape=box, style="rounded,filled", fillcolor="#E8E8E8", fontname="Arial"]
    edge [fontname="Arial", fontsize=10]

    // Template for: $diagram_type
    // Approach: $approach_name

    subgraph cluster_main {
        label="$diagram_type Diagram"
        style="rounded,filled"
        fillcolor="#F5F5F5"

        component_a [label="Component A"]
        component_b [label="Component B"]
        component_c [label="Component C"]
    }

    component_a -> component_b [label="relates to"]
    component_b -> component_c [label="uses"]

    // TODO: Replace with actual $diagram_type content
}
EOF
            ;;
    esac
}
