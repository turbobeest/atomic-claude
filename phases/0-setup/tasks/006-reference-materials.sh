#!/bin/bash
#
# Task 006: Reference Materials
# Guide user to gather enriching materials for Discovery and PRD phases
#
# Features:
#   - Explains what kinds of materials help the LLM
#   - Suggests folder structure for reference docs
#   - Optionally creates reference folder
#   - Records what materials are available to context
#

task_006_reference_materials() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local reference_dir="$ATOMIC_ROOT/reference"

    atomic_step "Reference Materials"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ Better inputs = better outputs.                         │${NC}"
    echo -e "${DIM}  │                                                         │${NC}"
    echo -e "${DIM}  │ Reference materials help the LLM understand your vision │${NC}"
    echo -e "${DIM}  │ during Discovery and PRD phases.                        │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    echo -e "${CYAN}  HELPFUL REFERENCE MATERIALS:${NC}"
    echo ""
    echo -e "    ${BOLD}Visual References${NC}"
    echo -e "    ${DIM}Screenshots, wireframes, mockups, UI inspiration${NC}"
    echo ""
    echo -e "    ${BOLD}Analogous Systems${NC}"
    echo -e "    ${DIM}Links or docs describing similar products to emulate${NC}"
    echo ""
    echo -e "    ${BOLD}Prior Discovery Work${NC}"
    echo -e "    ${DIM}Chat transcripts, brainstorming notes, LLM conversations${NC}"
    echo ""
    echo -e "    ${BOLD}Requirements & Specs${NC}"
    echo -e "    ${DIM}PRDs, ICDs, API specs, technical requirements${NC}"
    echo ""
    echo -e "    ${BOLD}Vision Documents${NC}"
    echo -e "    ${DIM}Product vision, roadmaps, strategic goals${NC}"
    echo ""

    # Check if reference folder already exists
    local has_reference=false
    local reference_count=0

    if [[ -d "$reference_dir" ]]; then
        reference_count=$(find "$reference_dir" -type f 2>/dev/null | wc -l | tr -d ' ')
        if [[ $reference_count -gt 0 ]]; then
            has_reference=true
        fi
    fi

    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [[ "$has_reference" == "true" ]]; then
        echo -e "  ${GREEN}✓${NC} Found ${BOLD}./reference/${NC} with $reference_count file(s)"
        echo ""
        # Show what's there
        echo -e "  ${DIM}Contents:${NC}"
        find "$reference_dir" -type f -name '*' 2>/dev/null | head -10 | while read -r f; do
            local fname=$(basename "$f")
            echo -e "    ${DIM}$fname${NC}"
        done
        if [[ $reference_count -gt 10 ]]; then
            echo -e "    ${DIM}... and $((reference_count - 10)) more${NC}"
        fi
        echo ""
    else
        echo -e "  ${DIM}No reference folder found.${NC}"
        echo ""
    fi

    echo -e "  ${BOLD}What would you like to do?${NC}"
    echo ""
    echo -e "  ${CYAN}1.${NC} Create ${BOLD}./reference/${NC} folder (I'll add materials)"
    echo -e "  ${CYAN}2.${NC} Point to existing folder"
    echo -e "  ${CYAN}3.${NC} Skip for now (can add later)"
    echo ""

    read -p "  Choice [3]: " ref_choice
    ref_choice=${ref_choice:-3}

    case "$ref_choice" in
        1)
            _006_create_reference_folder "$reference_dir"
            ;;
        2)
            _006_link_existing_folder "$config_file"
            ;;
        3)
            atomic_info "Skipping reference materials"
            atomic_context_decision "Reference materials: skipped (can add later to ./reference/)" "configuration"
            ;;
    esac

    echo ""
    echo -e "  ${DIM}Tip: You can add materials to ./reference/ at any time.${NC}"
    echo -e "  ${DIM}     They'll be available during Discovery and PRD phases.${NC}"
    echo ""

    return 0
}

# Create the reference folder with suggested structure
_006_create_reference_folder() {
    local reference_dir="$1"

    mkdir -p "$reference_dir"

    # Create subdirectories for organization
    mkdir -p "$reference_dir/visuals"
    mkdir -p "$reference_dir/docs"
    mkdir -p "$reference_dir/examples"

    # Create a helpful README
    cat > "$reference_dir/README.md" << 'EOF'
# Reference Materials

Place materials here to enrich Discovery and PRD phases.

## Suggested Organization

- **visuals/** - Screenshots, wireframes, mockups, UI inspiration
- **docs/** - Requirements, specs, ICDs, vision documents
- **examples/** - Links or descriptions of analogous systems

## Tips

- Images (PNG, JPG) will be analyzed visually
- Text files (MD, TXT) will be read directly
- PDFs will be processed for content
- Keep file names descriptive

## Adding Materials Later

You can add materials at any time before or during Discovery.
EOF

    atomic_success "Created ./reference/ with suggested structure"
    echo ""
    echo -e "  ${DIM}Folders created:${NC}"
    echo -e "    ./reference/visuals/   ${DIM}- Screenshots, mockups${NC}"
    echo -e "    ./reference/docs/      ${DIM}- Requirements, specs${NC}"
    echo -e "    ./reference/examples/  ${DIM}- Analogous systems${NC}"
    echo ""

    atomic_context_decision "Reference materials: created ./reference/ folder structure" "configuration"
}

# Link to an existing folder
_006_link_existing_folder() {
    local config_file="$1"

    echo ""
    read -p "  Path to existing folder: " existing_path

    if [[ -z "$existing_path" ]]; then
        atomic_warn "No path provided"
        return 1
    fi

    # Expand ~ if used
    existing_path="${existing_path/#\~/$HOME}"

    if [[ ! -d "$existing_path" ]]; then
        atomic_error "Folder not found: $existing_path"
        return 1
    fi

    local file_count=$(find "$existing_path" -type f 2>/dev/null | wc -l | tr -d ' ')

    # Store the path in config
    local tmp=$(atomic_mktemp)
    jq --arg path "$existing_path" '.reference_path = $path' "$config_file" > "$tmp" && mv "$tmp" "$config_file"

    atomic_success "Linked to $existing_path ($file_count files)"
    atomic_context_decision "Reference materials: linked to $existing_path ($file_count files)" "configuration"
}
