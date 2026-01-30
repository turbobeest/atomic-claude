#!/bin/bash
#
# Task 201: Entry Validation
# Validate Phase 1 artifacts exist and load context
#
# Required artifacts from Phase 1:
#   - phase-01-closeout.json
#   - selected-approach.json
#   - direction-confirmed.json
#   - corpus.json
#

task_201_entry_validation() {
    local phase1_dir="$ATOMIC_OUTPUT_DIR/1-discovery"

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2 WELCOME
    # ═══════════════════════════════════════════════════════════════════════════

    echo ""
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}"
    cat << 'EOF'
                    _____   ______  _____  ______  _     _ _______ _______
                   |_____] |_____/ |     | |     \ |     | |          |
                   |       |    \_ |_____| |_____/ |_____| |_____     |

 ______ _______  _____  _     _ _____  ______ _______ _______ _______ __   _ _______ _______
|_____/ |______ |   __| |     |   |   |_____/ |______ |  |  | |______ | \  |    |    |______
|    \_ |______ |____\| |_____| __|__ |    \_ |______ |  |  | |______ |  \_|    |    ______|

                  ______   _____  _______ _     _ _______ _______ __   _ _______
                 |     \ |     | |       |     | |  |  | |______ | \  |    |
                 |_____/ |_____| |_____  |_____| |  |  | |______ |  \_|    |
EOF
    echo -e "${NC}"
    echo -e "${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "                                   ${BOLD}[ PHASE 02 - PRD ]${NC}"
    echo ""

    atomic_step "Entry Validation"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ Validating Phase 1 artifacts before proceeding...      │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    local all_valid=true
    local missing=()

    # Check Phase 1 closeout
    echo -e "  ${CYAN}Phase 1 Closeout:${NC}"
    local closeout_file=$(atomic_find_closeout "1-discovery")
    if [[ -n "$closeout_file" ]]; then
        local status=$(jq -r '.status // "unknown"' "$closeout_file")
        if [[ "$status" == "complete" ]]; then
            echo -e "    ${GREEN}✓${NC} Phase 1 closeout found (status: complete)"
        else
            echo -e "    ${YELLOW}!${NC} Phase 1 closeout (status: $status)"
            all_valid=false
        fi
    else
        echo -e "    ${RED}✗${NC} Phase 1 closeout - NOT FOUND"
        missing+=("Phase 1 closeout")
        all_valid=false
    fi

    echo ""
    echo -e "  ${CYAN}Phase 1 Artifacts:${NC}"

    # Check selected approach
    if [[ -f "$phase1_dir/selected-approach.json" ]]; then
        local approach=$(jq -r '.name // "unnamed"' "$phase1_dir/selected-approach.json")
        echo -e "    ${GREEN}✓${NC} selected-approach.json ($approach)"
    else
        echo -e "    ${RED}✗${NC} selected-approach.json - NOT FOUND"
        missing+=("selected-approach.json")
        all_valid=false
    fi

    # Check direction confirmed
    if [[ -f "$phase1_dir/direction-confirmed.json" ]]; then
        echo -e "    ${GREEN}✓${NC} direction-confirmed.json"
    else
        echo -e "    ${RED}✗${NC} direction-confirmed.json - NOT FOUND"
        missing+=("direction-confirmed.json")
        all_valid=false
    fi

    # Check corpus (optional but recommended)
    if [[ -f "$phase1_dir/corpus.json" ]]; then
        local material_count=$(jq '.materials | length // 0' "$phase1_dir/corpus.json" 2>/dev/null || echo 0)
        echo -e "    ${GREEN}✓${NC} corpus.json ($material_count materials)"
    else
        echo -e "    ${YELLOW}○${NC} corpus.json - not found (optional)"
    fi

    # Check dialogue
    if [[ -f "$phase1_dir/dialogue.json" ]]; then
        echo -e "    ${GREEN}✓${NC} dialogue.json"
    else
        echo -e "    ${YELLOW}○${NC} dialogue.json - not found (optional)"
    fi

    echo ""

    # Handle missing artifacts
    if [[ "$all_valid" == false ]]; then
        echo -e "  ${RED}Missing required artifacts:${NC}"
        for item in "${missing[@]}"; do
            echo -e "    • $item"
        done
        echo ""
        echo -e "  ${YELLOW}Options:${NC}"
        echo -e "    ${DIM}[b]${NC} Go back to Phase 1"
        echo -e "    ${DIM}[c]${NC} Continue anyway (not recommended)"
        echo ""

    atomic_drain_stdin
        read -e -p "  Choice [b]: " choice || true
        choice=${choice:-b}

        case "$choice" in
            c|C)
                atomic_warn "Continuing with missing artifacts"
                ;;
            *)
                atomic_error "Phase 1 incomplete - run Phase 1 first"
                return 1
                ;;
        esac
    fi

    # Load context from Phase 1
    _201_load_context "$phase1_dir"

    atomic_context_decision "Phase 2 entry validated" "validation"
    atomic_success "Entry validation passed"

    return 0
}

# Load context from Phase 1 artifacts
_201_load_context() {
    local phase1_dir="$1"

    echo -e "  ${DIM}Loading context from Phase 1...${NC}"

    # Extract key information for Phase 2
    if [[ -f "$phase1_dir/selected-approach.json" ]]; then
        local approach_name=$(jq -r '.name // "unnamed"' "$phase1_dir/selected-approach.json")
        local approach_summary=$(jq -r '.summary // ""' "$phase1_dir/selected-approach.json")

        atomic_context_decision "Selected approach: $approach_name" "context"
    fi

    if [[ -f "$phase1_dir/direction-confirmed.json" ]]; then
        local vision=$(jq -r '.vision // ""' "$phase1_dir/direction-confirmed.json")
        local constraints=$(jq -r '.constraints | length' "$phase1_dir/direction-confirmed.json" 2>/dev/null || echo 0)

        [[ -n "$vision" ]] && atomic_context_decision "Vision confirmed with $constraints constraints" "context"
    fi

    echo -e "  ${GREEN}✓${NC} Context loaded"
    echo ""
}
