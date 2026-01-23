#!/bin/bash
#
# Task 003: Config Review
# Human reviews and approves the extracted/collected configuration
#
# Features:
#   - Displays all configuration in formatted sections
#   - 7 editable fields (name, desc, repo, mode, provider, network, cmd mode)
#   - Shows diff after edits
#   - Raw JSON view option
#   - Records all decisions to context
#

task_003_config_review() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    atomic_step "Configuration Review"

    _003_display_config "$config_file"
    _003_prompt_action "$config_file"
}

# Display the full configuration
_003_display_config() {
    local config_file="$1"

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ Review the extracted configuration below.               │${NC}"
    echo -e "${DIM}  │ You can approve as-is or edit specific fields.         │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Display extracted config
    local extracted=$(jq '.extracted' "$config_file")

    echo -e "${CYAN}  PROJECT${NC}"
    echo -e "    Name:        $(echo "$extracted" | jq -r '.project.name // "not set"')"
    echo -e "    Description: $(echo "$extracted" | jq -r '.project.description // "not set"')"
    echo -e "    Type:        $(echo "$extracted" | jq -r '.project.type // "not set"')"
    echo -e "    Goal:        $(echo "$extracted" | jq -r '.project.primary_goal // "not set"')"
    echo ""

    echo -e "${CYAN}  REPOSITORY${NC}"
    echo -e "    URL:         $(echo "$extracted" | jq -r '.repository.url // "not set"')"
    echo -e "    Branch:      $(echo "$extracted" | jq -r '.repository.default_branch // "main"')"
    echo -e "    PR Strategy: $(echo "$extracted" | jq -r '.repository.pr_strategy // "feature-branch"')"
    echo -e "    Commits:     $(echo "$extracted" | jq -r '.repository.commit_strategy // "per-task"')"
    echo -e "    Push:        $(echo "$extracted" | jq -r '.repository.push_strategy // "on-close"')"
    echo ""

    echo -e "${CYAN}  PIPELINE${NC}"
    echo -e "    Mode:        $(echo "$extracted" | jq -r '.pipeline.mode // "component"')"
    echo -e "    Human Gates: $(echo "$extracted" | jq -r '.pipeline.human_gates // [0,2,5,9] | join(", ")')"
    echo ""

    echo -e "${CYAN}  SANDBOX${NC}"
    echo -e "    Network:     $(echo "$extracted" | jq -r '.sandbox.network_access // "fetch-only"')"
    echo -e "    Cmd Mode:    $(echo "$extracted" | jq -r '.sandbox.command_approval_mode // "cautious"')"
    echo ""

    echo -e "${CYAN}  LLM PROVIDER${NC}"
    echo -e "    Provider:    $(echo "$extracted" | jq -r '.llm.primary_provider // "anthropic"')"
    echo ""

    # Check for any null/infer values that need attention
    local warnings=()
    [[ $(echo "$extracted" | jq -r '.project.name') == "null" ]] && warnings+=("Project name not set")
    [[ $(echo "$extracted" | jq -r '.repository.url') == "null" ]] && warnings+=("Repository URL not set (optional)")

    if [[ ${#warnings[@]} -gt 0 ]]; then
        echo -e "${YELLOW}  NOTES:${NC}"
        for w in "${warnings[@]}"; do
            echo -e "    - $w"
        done
        echo ""
    fi
}

# Prompt for action (approve, edit, view json, restart)
_003_prompt_action() {
    local config_file="$1"

    echo ""
    echo -e "  ${GREEN}[a]${NC} Approve configuration"
    echo -e "  ${YELLOW}[e]${NC} Edit a field"
    echo -e "  ${CYAN}[j]${NC} View raw JSON"
    echo -e "  ${RED}[r]${NC} Restart configuration"
    echo ""

    while true; do
        read -p "  Choice [a]: " choice
        choice=${choice:-a}

        case "$choice" in
            a|A)
                _003_approve_config "$config_file"
                return 0
                ;;
            e|E)
                _003_edit_field "$config_file"
                # Re-display and prompt again
                _003_display_config "$config_file"
                _003_prompt_action "$config_file"
                return $?
                ;;
            j|J)
                _003_view_json "$config_file"
                # Prompt again after viewing
                _003_prompt_action "$config_file"
                return $?
                ;;
            r|R)
                atomic_context_decision "Configuration review: user requested restart" "user-action"
                atomic_info "Restarting configuration..."
                return 1
                ;;
            *)
                atomic_error "Invalid choice. Enter a, e, j, or r."
                ;;
        esac
    done
}

# Approve and flatten config
_003_approve_config() {
    local config_file="$1"

    # Flatten extracted into main config
    local tmp=$(mktemp)
    jq '.project = .extracted.project |
        .repository = .extracted.repository |
        .sandbox = .extracted.sandbox |
        .mcp = .extracted.mcp |
        .pipeline = .extracted.pipeline |
        .agents = .extracted.agents |
        .llm = .extracted.llm |
        .config_approved = true |
        .approved_at = now | todate' "$config_file" > "$tmp" && mv "$tmp" "$config_file"

    # Record approval to context
    local project_name=$(jq -r '.project.name // "unnamed"' "$config_file")
    local pipeline_mode=$(jq -r '.pipeline.mode // "component"' "$config_file")
    atomic_context_decision "Configuration approved: $project_name ($pipeline_mode mode)" "approval"

    atomic_success "Configuration approved"
}

# View raw JSON
_003_view_json() {
    local config_file="$1"

    echo ""
    echo -e "${DIM}  ─────────────────── RAW JSON ───────────────────${NC}"
    echo ""
    jq '.extracted' "$config_file" | sed 's/^/    /'
    echo ""
    echo -e "${DIM}  ────────────────────────────────────────────────${NC}"
    echo ""
    read -p "  Press Enter to continue..." _
}

# Edit a specific field
_003_edit_field() {
    local config_file="$1"

    echo ""
    echo -e "  ${DIM}Edit which field?${NC}"
    echo -e "    1. Project Name"
    echo -e "    2. Description"
    echo -e "    3. Repository URL"
    echo -e "    4. Pipeline Mode"
    echo -e "    5. LLM Provider"
    echo -e "    6. Network Access"
    echo -e "    7. Command Approval Mode"
    echo ""
    read -p "  Field [1-7]: " field_choice

    local extracted=$(jq '.extracted' "$config_file")

    case "$field_choice" in
        1)
            local old_val=$(echo "$extracted" | jq -r '.project.name // "not set"')
            read -p "  New project name [$old_val]: " new_name
            new_name=${new_name:-$old_val}
            if atomic_validate_project_name "$new_name" >/dev/null 2>&1; then
                local tmp=$(mktemp)
                jq --arg val "$new_name" '.extracted.project.name = $val' "$config_file" > "$tmp" && mv "$tmp" "$config_file"
                _003_show_change "Project Name" "$old_val" "$new_name"
            else
                atomic_error "Invalid name (use lowercase, numbers, hyphens only)"
            fi
            ;;
        2)
            local old_val=$(echo "$extracted" | jq -r '.project.description // "not set"')
            read -p "  New description: " new_desc
            new_desc=${new_desc:-$old_val}
            local tmp=$(mktemp)
            jq --arg val "$new_desc" '.extracted.project.description = $val' "$config_file" > "$tmp" && mv "$tmp" "$config_file"
            _003_show_change "Description" "$old_val" "$new_desc"
            ;;
        3)
            local old_val=$(echo "$extracted" | jq -r '.repository.url // "not set"')
            read -p "  New repository URL [$old_val]: " new_url
            new_url=${new_url:-$old_val}
            local tmp=$(mktemp)
            jq --arg val "$new_url" '.extracted.repository.url = $val' "$config_file" > "$tmp" && mv "$tmp" "$config_file"
            _003_show_change "Repository URL" "$old_val" "$new_url"
            ;;
        4)
            local old_val=$(echo "$extracted" | jq -r '.pipeline.mode // "component"')
            echo ""
            echo -e "    ${DIM}1.${NC} component  ${DIM}- Single feature or component${NC}"
            echo -e "    ${DIM}2.${NC} full       ${DIM}- Full application${NC}"
            echo -e "    ${DIM}3.${NC} library    ${DIM}- Reusable library/package${NC}"
            echo -e "    ${DIM}4.${NC} prototype  ${DIM}- Quick prototype (fewer gates)${NC}"
            read -p "  Mode [1-4]: " mode
            local new_mode="$old_val"
            case "$mode" in
                1) new_mode="component" ;;
                2) new_mode="full" ;;
                3) new_mode="library" ;;
                4) new_mode="prototype" ;;
            esac
            local tmp=$(mktemp)
            jq ".extracted.pipeline.mode = \"$new_mode\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"
            _003_show_change "Pipeline Mode" "$old_val" "$new_mode"
            ;;
        5)
            local old_val=$(echo "$extracted" | jq -r '.llm.primary_provider // "anthropic"')
            echo ""
            echo -e "    ${DIM}1.${NC} anthropic  ${DIM}- Claude (recommended)${NC}"
            echo -e "    ${DIM}2.${NC} openai     ${DIM}- GPT models${NC}"
            echo -e "    ${DIM}3.${NC} google     ${DIM}- Gemini models${NC}"
            echo -e "    ${DIM}4.${NC} local      ${DIM}- Local LLM (ollama, etc)${NC}"
            read -p "  Provider [1-4]: " prov
            local new_provider="$old_val"
            case "$prov" in
                1) new_provider="anthropic" ;;
                2) new_provider="openai" ;;
                3) new_provider="google" ;;
                4) new_provider="local" ;;
            esac
            local tmp=$(mktemp)
            jq ".extracted.llm.primary_provider = \"$new_provider\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"
            _003_show_change "LLM Provider" "$old_val" "$new_provider"
            ;;
        6)
            local old_val=$(echo "$extracted" | jq -r '.sandbox.network_access // "fetch-only"')
            echo ""
            echo -e "    ${DIM}1.${NC} none       ${DIM}- No network access${NC}"
            echo -e "    ${DIM}2.${NC} fetch-only ${DIM}- HTTP GET only (recommended)${NC}"
            echo -e "    ${DIM}3.${NC} full       ${DIM}- Full network access${NC}"
            read -p "  Network access [1-3]: " net
            local new_network="$old_val"
            case "$net" in
                1) new_network="none" ;;
                2) new_network="fetch-only" ;;
                3) new_network="full" ;;
            esac
            local tmp=$(mktemp)
            jq ".extracted.sandbox.network_access = \"$new_network\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"
            _003_show_change "Network Access" "$old_val" "$new_network"
            ;;
        7)
            local old_val=$(echo "$extracted" | jq -r '.sandbox.command_approval_mode // "cautious"')
            echo ""
            echo -e "    ${DIM}1.${NC} ask-always ${DIM}- Prompt before every command${NC}"
            echo -e "    ${DIM}2.${NC} cautious   ${DIM}- Prompt for risky commands (recommended)${NC}"
            echo -e "    ${DIM}3.${NC} auto       ${DIM}- Auto-approve safe commands${NC}"
            read -p "  Command approval [1-3]: " cmd
            local new_cmd="$old_val"
            case "$cmd" in
                1) new_cmd="ask-always" ;;
                2) new_cmd="cautious" ;;
                3) new_cmd="auto" ;;
            esac
            local tmp=$(mktemp)
            jq ".extracted.sandbox.command_approval_mode = \"$new_cmd\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"
            _003_show_change "Command Approval" "$old_val" "$new_cmd"
            ;;
        *)
            atomic_error "Invalid field selection"
            ;;
    esac
}

# Show what changed after an edit
_003_show_change() {
    local field="$1"
    local old_val="$2"
    local new_val="$3"

    if [[ "$old_val" == "$new_val" ]]; then
        atomic_info "No change to $field"
    else
        echo ""
        echo -e "  ${DIM}Changed:${NC}"
        echo -e "    $field: ${RED}$old_val${NC} → ${GREEN}$new_val${NC}"
        echo ""
        atomic_success "Updated $field"

        # Record edit to context
        atomic_context_decision "Config edit: $field changed from '$old_val' to '$new_val'" "user-edit"
    fi
}
