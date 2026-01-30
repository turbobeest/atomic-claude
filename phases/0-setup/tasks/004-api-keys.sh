#!/bin/bash
#
# Task 004: API Keys
# Securely collect provider-specific API credentials
#
# Features:
#   - Environment variable detection (checks existing env vars first)
#   - Key masking display for confirmation
#   - Optional key validation via API test
#   - Support for primary + backup provider
#   - Records configuration to context (not the keys themselves)
#

task_004_api_keys() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local secrets_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/secrets.json"

    atomic_step "API Credentials"

    echo ""
    echo -e "  ${DIM}Keys are stored locally and NEVER committed to git.${NC}"
    echo ""

    # Check if already configured
    if [[ -f "$secrets_file" ]]; then
        local existing
        existing=$(jq -r 'keys[]' "$secrets_file" 2>/dev/null || true)
        existing=$(echo "$existing" | head -3 | tr '\n' ', ' | sed 's/,$//')
        if [[ -n "$existing" ]]; then
            atomic_substep "Existing credentials found: $existing"
            # Drain stdin before prompt
            while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done
            read -e -p "  Reconfigure? [y/N]: " reconfigure || true
            if [[ ! "$reconfigure" =~ ^[Yy] ]]; then
                atomic_info "Keeping existing credentials"
                atomic_context_decision "API credentials: kept existing configuration" "configuration"
                return 0
            fi
        fi
    fi

    mkdir -p "$(dirname "$secrets_file")"
    echo '{}' > "$secrets_file"

    # Show what's available and let user configure what they need
    # Note: Claude Code requires Claude models - only these providers work
    echo -e "  ${BOLD}Which providers do you want to configure?${NC}"
    echo -e "  ${DIM}You can select models from any configured provider per-task.${NC}"
    echo ""
    echo -e "  ${CYAN}1.${NC} Claude Max (subscription - recommended)"
    echo -e "  ${CYAN}2.${NC} Anthropic API (pay-per-token)"
    echo -e "  ${CYAN}3.${NC} AWS Bedrock (Claude via AWS)"
    echo -e "  ${CYAN}4.${NC} Ollama (local/LAN models)"
    echo ""
    echo -e "  ${DIM}Enter numbers separated by spaces (e.g., \"1 4\" for Max + Ollama)${NC}"
    # Drain stdin before prompt
    while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done
    read -e -p "  Configure [1 4]: " provider_choices || true
    provider_choices=${provider_choices:-"1 4"}

    for choice in $provider_choices; do
        echo ""
        case "$choice" in
            1) _004_collect_max "$secrets_file" ;;
            2) _004_collect_anthropic "$secrets_file" ;;
            3) _004_collect_bedrock "$secrets_file" ;;
            4) _004_collect_ollama "$secrets_file" ;;
        esac
    done

    # Secure the file (Unix-like systems only)
    if [[ ! -f "$secrets_file" ]]; then
        atomic_warn "Secrets file not created - configuration may have failed"
        return 1
    fi

    if [[ "$(uname -s)" != MINGW* && "$(uname -s)" != CYGWIN* && "$(uname -s)" != MSYS* ]]; then
        if chmod 600 "$secrets_file" 2>/dev/null; then
            atomic_substep "Credentials file secured (chmod 600)"
        else
            atomic_warn "Could not set file permissions on $secrets_file"
        fi
    else
        atomic_substep "Credentials file saved (Windows: manual permissions recommended)"
    fi

    # Add to gitignore
    _004_update_gitignore

    # Record to context (provider names only, never keys)
    local configured=$(jq -r 'keys | join(", ")' "$secrets_file")
    atomic_context_decision "Credentials configured: $configured" "configuration"

    return 0
}

# Claude Max (subscription) - check for existing login
_004_collect_max() {
    local secrets_file="$1"

    echo -e "  ${CYAN}Claude Max${NC}"
    echo -e "  ${DIM}Uses your existing Claude subscription login${NC}"

    # Check for existing credentials
    local creds_file="$HOME/.claude/.credentials.json"
    if [[ -f "$creds_file" ]]; then
        echo -e "  ${GREEN}✓${NC} Claude login found"
        local tmp=$(atomic_mktemp)
        jq '.max_enabled = true' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
        atomic_success "Claude Max ready"
    else
        echo -e "  ${YELLOW}!${NC} Not logged in"
        echo -e "  ${DIM}Run 'claude' to login first, then re-run setup${NC}"
        read -e -p "    Skip Max for now? [Y/n]: " skip_max || true
        if [[ "$skip_max" =~ ^[Nn] ]]; then
            atomic_warn "Please login with 'claude' command first"
            return 1
        fi
    fi
}

# Anthropic API key collection
_004_collect_anthropic() {
    local secrets_file="$1"
    local key_name="anthropic_api_key"

    echo -e "  ${CYAN}Anthropic API${NC}"

    echo -e "  ${DIM}Pay-per-token API access${NC}"

    # Check environment variable first
    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
        local masked=$(_004_mask_key "$ANTHROPIC_API_KEY")
        echo -e "  ${GREEN}✓${NC} Found in environment: ${DIM}$masked${NC}"
        read -e -p "    Use this key? [Y/n]: " use_env || true
        if [[ ! "$use_env" =~ ^[Nn] ]]; then
            local tmp=$(atomic_mktemp)
            jq --arg key "$key_name" --arg val "$ANTHROPIC_API_KEY" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
            atomic_success "Anthropic API key saved (from env)"
            return 0
        fi
    fi

    echo -e "  ${DIM}Format: sk-ant-...${NC}"
    read -s -p "    Key: " api_key
    echo ""

    if [[ -z "$api_key" ]]; then
        atomic_warn "No key provided"
        return 1
    fi

    # Show masked key for confirmation
    local masked=$(_004_mask_key "$api_key")
    echo -e "    Entered: ${DIM}$masked${NC}"

    # Offer validation
    read -e -p "    Validate key with API test? [y/N]: " do_validate || true
    if [[ "$do_validate" =~ ^[Yy] ]]; then
        if _004_validate_anthropic "$api_key"; then
            atomic_success "Key validated successfully"
        else
            atomic_warn "Validation failed - saving anyway"
        fi
    fi

    local tmp=$(atomic_mktemp)
    jq --arg key "$key_name" --arg val "$api_key" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
    atomic_success "Anthropic key saved"
}

# OpenAI API key collection
_004_collect_openai() {
    local secrets_file="$1"
    local key_name="openai_api_key"

    echo -e "  ${CYAN}OpenAI API${NC}"

    # Check environment variable first
    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
        local masked=$(_004_mask_key "$OPENAI_API_KEY")
        echo -e "  ${GREEN}✓${NC} Found in environment: ${DIM}$masked${NC}"
        read -e -p "    Use this key? [Y/n]: " use_env || true
        if [[ ! "$use_env" =~ ^[Nn] ]]; then
            local tmp=$(atomic_mktemp)
            jq --arg key "$key_name" --arg val "$OPENAI_API_KEY" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
            atomic_success "OpenAI key saved (from env)"
            return 0
        fi
    fi

    echo -e "  ${DIM}Format: sk-...${NC}"
    read -s -p "    Key: " api_key
    echo ""

    if [[ -z "$api_key" ]]; then
        atomic_warn "No key provided"
        return 1
    fi

    local masked=$(_004_mask_key "$api_key")
    echo -e "    Entered: ${DIM}$masked${NC}"

    read -e -p "    Validate key with API test? [y/N]: " do_validate || true
    if [[ "$do_validate" =~ ^[Yy] ]]; then
        if _004_validate_openai "$api_key"; then
            atomic_success "Key validated successfully"
        else
            atomic_warn "Validation failed - saving anyway"
        fi
    fi

    local tmp=$(atomic_mktemp)
    jq --arg key "$key_name" --arg val "$api_key" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
    atomic_success "OpenAI key saved"
}

# Google AI API key collection
_004_collect_google() {
    local secrets_file="$1"
    local key_name="google_api_key"

    echo -e "  ${CYAN}Google AI API${NC}"

    # Check environment variable
    if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
        local masked=$(_004_mask_key "$GOOGLE_API_KEY")
        echo -e "  ${GREEN}✓${NC} Found in environment: ${DIM}$masked${NC}"
        read -e -p "    Use this key? [Y/n]: " use_env || true
        if [[ ! "$use_env" =~ ^[Nn] ]]; then
            local tmp=$(atomic_mktemp)
            jq --arg key "$key_name" --arg val "$GOOGLE_API_KEY" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
            atomic_success "Google AI key saved (from env)"
            return 0
        fi
    fi

    read -s -p "    Key: " api_key
    echo ""

    if [[ -z "$api_key" ]]; then
        atomic_warn "No key provided"
        return 1
    fi

    local masked=$(_004_mask_key "$api_key")
    echo -e "    Entered: ${DIM}$masked${NC}"

    local tmp=$(atomic_mktemp)
    jq --arg key "$key_name" --arg val "$api_key" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
    atomic_success "Google AI key saved"
}

# Ollama (local/LAN) configuration
_004_collect_ollama() {
    local secrets_file="$1"

    echo -e "  ${CYAN}Ollama (Local/LAN)${NC}"
    echo -e "  ${DIM}Free local inference - no API key needed${NC}"

    local hosts_found=()
    local models_found=()

    # Check localhost first
    echo -e "  ${DIM}Scanning for Ollama servers...${NC}"
    if curl -s --connect-timeout 2 http://localhost:11434/api/tags &>/dev/null; then
        hosts_found+=("http://localhost:11434")
        local models=$(curl -s http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null | head -5)
        echo -e "  ${GREEN}✓${NC} localhost:11434"
        for m in $models; do
            echo -e "      ${DIM}$m${NC}"
            models_found+=("$m")
        done
    fi

    # Report findings
    if [[ ${#hosts_found[@]} -eq 0 ]]; then
        echo -e "  ${YELLOW}!${NC} No Ollama servers found on localhost"
        echo -e "  ${DIM}Start Ollama with: ollama serve${NC}"
    fi

    # Allow adding custom hosts
    echo ""
    echo -e "  ${DIM}Add additional Ollama hosts? (LAN servers, etc.)${NC}"
    echo -e "  ${DIM}Enter hosts one per line, blank line to finish:${NC}"
    while true; do
        read -e -p "    Host: " custom_host || true
        [[ -z "$custom_host" ]] && break

        # Add http:// if missing
        [[ "$custom_host" != http* ]] && custom_host="http://$custom_host"
        # Add port if missing
        [[ "$custom_host" != *:* ]] && custom_host="$custom_host:11434"

        if curl -s --connect-timeout 2 "$custom_host/api/tags" &>/dev/null; then
            echo -e "    ${GREEN}✓${NC} $custom_host responding"
            hosts_found+=("$custom_host")
        else
            echo -e "    ${YELLOW}!${NC} $custom_host not responding (saved anyway)"
            hosts_found+=("$custom_host")
        fi
    done

    # Save all hosts
    local tmp=$(atomic_mktemp)
    local hosts_json=$(printf '%s\n' "${hosts_found[@]}" | jq -R . | jq -s .)
    jq --argjson hosts "$hosts_json" '.ollama_hosts = $hosts' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"

    atomic_success "Ollama configured (${#hosts_found[@]} host(s))"
}

# AWS Bedrock configuration
_004_collect_bedrock() {
    local secrets_file="$1"

    echo -e "  ${CYAN}AWS Bedrock${NC}"
    echo -e "  ${DIM}Uses AWS credentials from environment or ~/.aws/credentials${NC}"

    # Check for existing AWS config
    if [[ -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
        echo -e "  ${GREEN}✓${NC} AWS credentials found in environment"
    elif [[ -f ~/.aws/credentials ]]; then
        echo -e "  ${GREEN}✓${NC} AWS credentials file found"
    else
        atomic_warn "No AWS credentials detected"
    fi

    read -e -p "    AWS Region [us-east-1]: " aws_region || true
    aws_region=${aws_region:-us-east-1}
    read -e -p "    AWS Profile [default]: " aws_profile || true
    aws_profile=${aws_profile:-default}

    local tmp=$(atomic_mktemp)
    jq --arg region "$aws_region" --arg profile "$aws_profile" \
        '.aws_region = $region | .aws_profile = $profile' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
    atomic_success "AWS Bedrock configured"
}

# Azure OpenAI configuration
_004_collect_azure() {
    local secrets_file="$1"

    echo -e "  ${CYAN}Azure OpenAI${NC}"

    read -e -p "    Endpoint URL: " azure_endpoint || true
    read -e -p "    Deployment Name: " azure_deployment || true
    read -s -p "    API Key: " azure_key
    echo ""

    if [[ -n "$azure_key" ]]; then
        local masked=$(_004_mask_key "$azure_key")
        echo -e "    Entered: ${DIM}$masked${NC}"
    fi

    local tmp=$(atomic_mktemp)
    jq --arg endpoint "$azure_endpoint" --arg deployment "$azure_deployment" --arg key "$azure_key" \
        '.azure_endpoint = $endpoint | .azure_deployment = $deployment | .azure_api_key = $key' \
        "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
    atomic_success "Azure OpenAI configured"
}

# Mask a key for display (show first 7 and last 4 chars)
_004_mask_key() {
    local key="$1"
    local len=${#key}

    if [[ $len -lt 15 ]]; then
        echo "***"
        return
    fi

    local prefix="${key:0:7}"
    local suffix="${key: -4}"
    echo "${prefix}***...***${suffix}"
}

# Validate Anthropic API key
_004_validate_anthropic() {
    local key="$1"

    echo -e "    ${DIM}Testing API connection...${NC}"

    local response=$(curl -s -w "\n%{http_code}" \
        -H "x-api-key: $key" \
        -H "anthropic-version: 2023-06-01" \
        -H "content-type: application/json" \
        -d '{"model":"claude-3-haiku-20240307","max_tokens":1,"messages":[{"role":"user","content":"Hi"}]}' \
        "https://api.anthropic.com/v1/messages" 2>/dev/null)

    local http_code=$(echo "$response" | tail -1)

    if [[ "$http_code" == "200" ]]; then
        return 0
    elif [[ "$http_code" == "401" ]]; then
        atomic_error "Invalid API key"
        return 1
    else
        atomic_warn "API returned HTTP $http_code"
        return 1
    fi
}

# Validate OpenAI API key
_004_validate_openai() {
    local key="$1"

    echo -e "    ${DIM}Testing API connection...${NC}"

    local response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $key" \
        "https://api.openai.com/v1/models" 2>/dev/null)

    local http_code=$(echo "$response" | tail -1)

    if [[ "$http_code" == "200" ]]; then
        return 0
    elif [[ "$http_code" == "401" ]]; then
        atomic_error "Invalid API key"
        return 1
    else
        atomic_warn "API returned HTTP $http_code"
        return 1
    fi
}

# Update .gitignore to exclude secrets
_004_update_gitignore() {
    local gitignore=".gitignore"

    if [[ -f "$gitignore" ]]; then
        if ! grep -q "secrets.json" "$gitignore"; then
            echo "" >> "$gitignore"
            echo "# ATOMIC CLAUDE secrets" >> "$gitignore"
            echo ".outputs/*/secrets.json" >> "$gitignore"
            atomic_substep "Added to .gitignore"
        fi
    else
        # Create gitignore if it doesn't exist
        cat > "$gitignore" << 'EOF'
# ATOMIC CLAUDE secrets
.outputs/*/secrets.json
EOF
        atomic_substep "Created .gitignore"
    fi
}
