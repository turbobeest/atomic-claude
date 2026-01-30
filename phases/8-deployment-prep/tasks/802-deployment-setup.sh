#!/bin/bash
#
# Task 802: Deployment Setup
# Configure release type, version, and distribution channels
#

task_802_deployment_setup() {
    local config_file="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"
    local deployment_dir="$ATOMIC_ROOT/.claude/deployment"
    local setup_file="$deployment_dir/setup.json"

    atomic_step "Deployment Setup"

    mkdir -p "$deployment_dir"

    echo ""
    echo -e "  ${DIM}Configuring release type and distribution channels.${NC}"
    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # RELEASE TYPE
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- RELEASE TYPE${NC}"
    echo ""

    echo -e "  ${DIM}Select the type of release:${NC}"
    echo ""
    echo -e "    ${GREEN}[1]${NC} Major (x.0.0) - Breaking changes, new architecture"
    echo -e "    ${CYAN}[2]${NC} Minor (0.x.0) - New features, backward compatible"
    echo -e "    ${DIM}[3]${NC} Patch (0.0.x) - Bug fixes, minor improvements"
    echo ""

    read -e -p "  Select [2]: " release_type_choice || true
    release_type_choice=${release_type_choice:-2}

    local release_type="minor"
    case "$release_type_choice" in
        1) release_type="major" ;;
        2) release_type="minor" ;;
        3) release_type="patch" ;;
        *) release_type="minor" ;;
    esac

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # VERSION NUMBER
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- VERSION NUMBER${NC}"
    echo ""

    # Default version based on release type
    local default_version="0.1.0"
    case "$release_type" in
        major) default_version="1.0.0" ;;
        minor) default_version="0.1.0" ;;
        patch) default_version="0.0.1" ;;
    esac

    echo -e "  ${DIM}Enter version number (SemVer format):${NC}"
    echo ""
    read -e -p "  Version [$default_version]: " version_number || true
    version_number=${version_number:-$default_version}

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # DISTRIBUTION CHANNELS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- DISTRIBUTION CHANNELS${NC}"
    echo ""

    echo -e "  ${DIM}Select distribution channel:${NC}"
    echo ""
    # Future channels (hidden for now):
    # echo -e "    ${GREEN}[1]${NC} GitHub Releases"
    # echo -e "    ${CYAN}[2]${NC} PyPI"
    # echo -e "    ${YELLOW}[3]${NC} npm"
    echo -e "    ${GREEN}[1]${NC} Internal only"
    echo ""

    read -e -p "  Select channel [1]: " channel_choice || true
    channel_choice=${channel_choice:-"1"}

    local channels=()
    # Future channel mappings (hidden for now):
    # [[ "$channel_choice" == *"1"* ]] && channels+=("github")
    # [[ "$channel_choice" == *"2"* ]] && channels+=("pypi")
    # [[ "$channel_choice" == *"3"* ]] && channels+=("npm")
    [[ "$channel_choice" == *"1"* ]] && channels+=("internal")

    echo ""

    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    # RELEASE CONFIGURATION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

    echo ""
    echo -e "  ${BOLD}- RELEASE CONFIGURATION${NC}"
    echo ""

    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo -e "  ${BOLD}RELEASE SETTINGS${NC}"
    echo ""
    echo -e "    Release Type:    ${CYAN}$release_type${NC}"
    echo -e "    Version:         ${GREEN}$version_number${NC}"
    echo -e "    Channels:        ${CYAN}${channels[*]}${NC}"
    echo -e "  ──────────────────────────────────────────────────────────────────────────────────────────────────────────"
    echo ""

    echo -e "  ${DIM}Confirm this configuration?${NC}"
    echo ""
    read -e -p "  Confirm [y/n]: " config_confirm || true
    config_confirm=${config_confirm:-y}

    if [[ "$config_confirm" != "y" && "$config_confirm" != "Y" ]]; then
        echo ""
        echo -e "  ${DIM}Re-running setup...${NC}"
        task_802_deployment_setup
        return $?
    fi

    echo ""

    # Save setup configuration
    local channels_json=$(printf '%s\n' "${channels[@]}" | jq -R . | jq -s .)

    jq -n \
        --arg release_type "$release_type" \
        --arg version "$version_number" \
        --argjson channels "$channels_json" \
        '{
            "release": {
                "type": $release_type,
                "version": $version
            },
            "distribution": {
                "channels": $channels
            },
            "configured_at": (now | todate)
        }' > "$setup_file"

    atomic_context_artifact "$setup_file" "deployment-setup" "Deployment configuration"
    atomic_context_decision "Release configured: v$version_number ($release_type) to ${channels[*]}" "setup"

    atomic_success "Deployment Setup complete"

    return 0
}
