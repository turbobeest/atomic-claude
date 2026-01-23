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

    atomic_step "API Key Configuration"

    local provider=$(jq -r '.llm.primary_provider // "anthropic"' "$config_file")

    echo ""
    echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${DIM}  │ API keys are stored locally and NEVER committed to git. │${NC}"
    echo -e "${DIM}  │ File will be secured with chmod 600.                    │${NC}"
    echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
    echo ""

    # Check if already configured
    if [[ -f "$secrets_file" ]]; then
        local existing
        existing=$(jq -r 'keys[]' "$secrets_file" 2>/dev/null || true)
        existing=$(echo "$existing" | head -3 | tr '\n' ', ' | sed 's/,$//')
        if [[ -n "$existing" ]]; then
            atomic_substep "Existing keys found: $existing"
            read -p "  Reconfigure? [y/N]: " reconfigure
            if [[ ! "$reconfigure" =~ ^[Yy] ]]; then
                atomic_info "Keeping existing keys"
                atomic_context_decision "API keys: kept existing configuration" "configuration"
                return 0
            fi
        fi
    fi

    mkdir -p "$(dirname "$secrets_file")"
    echo '{}' > "$secrets_file"

    # Configure primary provider
    echo -e "  ${CYAN}Primary Provider: ${BOLD}$provider${NC}"
    echo ""
    _004_configure_provider "$provider" "$secrets_file" "primary"

    # Offer backup provider
    echo ""
    echo -e "  ${DIM}Configure a backup provider? (used if primary fails)${NC}"
    read -p "  Add backup? [y/N]: " add_backup
    if [[ "$add_backup" =~ ^[Yy] ]]; then
        echo ""
        echo -e "    ${DIM}1.${NC} anthropic"
        echo -e "    ${DIM}2.${NC} openai"
        echo -e "    ${DIM}3.${NC} google"
        echo -e "    ${DIM}4.${NC} ollama (local)"
        read -p "  Backup provider [1-4]: " backup_choice
        local backup_provider=""
        case "$backup_choice" in
            1) backup_provider="anthropic" ;;
            2) backup_provider="openai" ;;
            3) backup_provider="google" ;;
            4) backup_provider="ollama" ;;
        esac
        if [[ -n "$backup_provider" && "$backup_provider" != "$provider" ]]; then
            echo ""
            _004_configure_provider "$backup_provider" "$secrets_file" "backup"
            # Update config with backup provider
            local tmp=$(mktemp)
            jq ".llm.backup_provider = \"$backup_provider\"" "$config_file" > "$tmp" && mv "$tmp" "$config_file"
        fi
    fi

    # Secure the file
    chmod 600 "$secrets_file"
    atomic_substep "Secrets file secured (chmod 600)"

    # Add to gitignore
    _004_update_gitignore

    # Record to context (provider names only, never keys)
    local configured_providers=$(jq -r 'keys | map(select(contains("key") or contains("host") or contains("endpoint"))) | length' "$secrets_file")
    atomic_context_decision "API keys configured: $provider (primary)$([ -n "${backup_provider:-}" ] && echo ", $backup_provider (backup)")" "configuration"

    return 0
}

# Configure a specific provider
_004_configure_provider() {
    local provider="$1"
    local secrets_file="$2"
    local role="$3"  # "primary" or "backup"

    case "$provider" in
        anthropic)
            _004_collect_anthropic "$secrets_file" "$role"
            ;;
        openai)
            _004_collect_openai "$secrets_file" "$role"
            ;;
        google)
            _004_collect_google "$secrets_file" "$role"
            ;;
        ollama|local)
            _004_collect_ollama "$secrets_file" "$role"
            ;;
        aws-bedrock)
            _004_collect_bedrock "$secrets_file" "$role"
            ;;
        azure)
            _004_collect_azure "$secrets_file" "$role"
            ;;
        *)
            atomic_warn "Unknown provider: $provider"
            ;;
    esac
}

# Anthropic API key collection
_004_collect_anthropic() {
    local secrets_file="$1"
    local role="$2"
    local key_name="anthropic_api_key"
    [[ "$role" == "backup" ]] && key_name="anthropic_api_key_backup"

    echo -e "  ${CYAN}Anthropic API Key${NC}"

    # Check environment variable first
    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
        local masked=$(_004_mask_key "$ANTHROPIC_API_KEY")
        echo -e "  ${GREEN}✓${NC} Found in environment: ${DIM}$masked${NC}"
        read -p "    Use this key? [Y/n]: " use_env
        if [[ ! "$use_env" =~ ^[Nn] ]]; then
            local tmp=$(mktemp)
            jq --arg key "$key_name" --arg val "$ANTHROPIC_API_KEY" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
            atomic_success "Anthropic key saved (from env)"
            return 0
        fi
    fi

    echo -e "  ${DIM}Format: sk-ant-api03-...${NC}"
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
    read -p "    Validate key with API test? [y/N]: " do_validate
    if [[ "$do_validate" =~ ^[Yy] ]]; then
        if _004_validate_anthropic "$api_key"; then
            atomic_success "Key validated successfully"
        else
            atomic_warn "Validation failed - saving anyway"
        fi
    fi

    local tmp=$(mktemp)
    jq --arg key "$key_name" --arg val "$api_key" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
    atomic_success "Anthropic key saved"
}

# OpenAI API key collection
_004_collect_openai() {
    local secrets_file="$1"
    local role="$2"
    local key_name="openai_api_key"
    [[ "$role" == "backup" ]] && key_name="openai_api_key_backup"

    echo -e "  ${CYAN}OpenAI API Key${NC}"

    # Check environment variable first
    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
        local masked=$(_004_mask_key "$OPENAI_API_KEY")
        echo -e "  ${GREEN}✓${NC} Found in environment: ${DIM}$masked${NC}"
        read -p "    Use this key? [Y/n]: " use_env
        if [[ ! "$use_env" =~ ^[Nn] ]]; then
            local tmp=$(mktemp)
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

    read -p "    Validate key with API test? [y/N]: " do_validate
    if [[ "$do_validate" =~ ^[Yy] ]]; then
        if _004_validate_openai "$api_key"; then
            atomic_success "Key validated successfully"
        else
            atomic_warn "Validation failed - saving anyway"
        fi
    fi

    local tmp=$(mktemp)
    jq --arg key "$key_name" --arg val "$api_key" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
    atomic_success "OpenAI key saved"
}

# Google AI API key collection
_004_collect_google() {
    local secrets_file="$1"
    local role="$2"
    local key_name="google_api_key"
    [[ "$role" == "backup" ]] && key_name="google_api_key_backup"

    echo -e "  ${CYAN}Google AI API Key${NC}"

    # Check environment variable
    if [[ -n "${GOOGLE_API_KEY:-}" ]]; then
        local masked=$(_004_mask_key "$GOOGLE_API_KEY")
        echo -e "  ${GREEN}✓${NC} Found in environment: ${DIM}$masked${NC}"
        read -p "    Use this key? [Y/n]: " use_env
        if [[ ! "$use_env" =~ ^[Nn] ]]; then
            local tmp=$(mktemp)
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

    local tmp=$(mktemp)
    jq --arg key "$key_name" --arg val "$api_key" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
    atomic_success "Google AI key saved"
}

# Ollama (local) configuration
_004_collect_ollama() {
    local secrets_file="$1"
    local role="$2"

    echo -e "  ${CYAN}Ollama Configuration${NC}"
    echo -e "  ${DIM}Ollama runs locally - no API key needed${NC}"

    # Check if ollama is running
    if command -v ollama &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Ollama binary found"
        if curl -s http://localhost:11434/api/tags &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Ollama server is running"
            local models=$(curl -s http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null | head -3 | tr '\n' ', ' | sed 's/,$//')
            [[ -n "$models" ]] && echo -e "  ${DIM}Available models: $models${NC}"
        else
            atomic_warn "Ollama server not running (start with: ollama serve)"
        fi
    else
        atomic_warn "Ollama not installed"
    fi

    read -p "    Ollama host [http://localhost:11434]: " ollama_host
    ollama_host=${ollama_host:-http://localhost:11434}

    local tmp=$(mktemp)
    jq --arg val "$ollama_host" '.ollama_host = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
    atomic_success "Ollama configured"
}

# AWS Bedrock configuration
_004_collect_bedrock() {
    local secrets_file="$1"
    local role="$2"

    echo -e "  ${CYAN}AWS Bedrock Configuration${NC}"
    echo -e "  ${DIM}Uses AWS credentials from environment or ~/.aws/credentials${NC}"

    # Check for existing AWS config
    if [[ -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
        echo -e "  ${GREEN}✓${NC} AWS credentials found in environment"
    elif [[ -f ~/.aws/credentials ]]; then
        echo -e "  ${GREEN}✓${NC} AWS credentials file found"
    else
        atomic_warn "No AWS credentials detected"
    fi

    read -p "    AWS Region [us-east-1]: " aws_region
    aws_region=${aws_region:-us-east-1}
    read -p "    AWS Profile [default]: " aws_profile
    aws_profile=${aws_profile:-default}

    local tmp=$(mktemp)
    jq --arg region "$aws_region" --arg profile "$aws_profile" \
        '.aws_region = $region | .aws_profile = $profile' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
    atomic_success "AWS Bedrock configured"
}

# Azure OpenAI configuration
_004_collect_azure() {
    local secrets_file="$1"
    local role="$2"

    echo -e "  ${CYAN}Azure OpenAI Configuration${NC}"

    read -p "    Endpoint URL: " azure_endpoint
    read -p "    Deployment Name: " azure_deployment
    read -s -p "    API Key: " azure_key
    echo ""

    if [[ -n "$azure_key" ]]; then
        local masked=$(_004_mask_key "$azure_key")
        echo -e "    Entered: ${DIM}$masked${NC}"
    fi

    local tmp=$(mktemp)
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
