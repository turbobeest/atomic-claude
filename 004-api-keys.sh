#!/usr/bin/env bash
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
    echo -e "  ${DIM}Credentials loaded from .env in Task 001${NC}"
    echo ""

    # Check if already configured by Task 001
    if [[ -f "$secrets_file" ]]; then
        local existing
        existing=$(jq -r 'keys[]' "$secrets_file" 2>/dev/null || true)
        existing=$(echo "$existing" | head -3 | tr '\n' ', ' | sed 's/,$//')
        if [[ -n "$existing" ]]; then
            echo -e "  ${GREEN}✓${NC} Credentials already configured by Task 001"
            echo ""

            # Show what was configured
            local bedrock_enabled=$(jq -r '.bedrock_enabled // false' "$secrets_file")
            local anthropic_key=$(jq -r '.anthropic_api_key // empty' "$secrets_file")
            local ollama_enabled=$(jq -r '.ollama_enabled // false' "$secrets_file")

            if [[ "$bedrock_enabled" == "true" ]]; then
                local aws_profile=$(jq -r '.aws_profile // "default"' "$secrets_file")
                local aws_region=$(jq -r '.aws_region // "us-east-1"' "$secrets_file")
                local bedrock_model=$(jq -r '.bedrock_model // empty' "$secrets_file")
                echo -e "  ${CYAN}AWS Bedrock:${NC}"
                echo -e "    Profile: $aws_profile"
                echo -e "    Region: $aws_region"
                echo -e "    Model: $bedrock_model"
                echo ""
            fi

            if [[ -n "$anthropic_key" ]]; then
                local masked_key="${anthropic_key:0:7}...${anthropic_key: -4}"
                echo -e "  ${CYAN}Anthropic API:${NC}"
                echo -e "    Key: $masked_key"
                echo ""
            fi

            if [[ "$ollama_enabled" == "true" ]]; then
                echo -e "  ${CYAN}Ollama:${NC} localhost:11434"
                echo ""
            fi

            echo -e "  ${DIM}To reconfigure, delete: $secrets_file${NC}"
            echo ""
            atomic_context_decision "API credentials: using configuration from Task 001" "configuration"
            return 0
        fi
    fi

    # If secrets.json doesn't exist or is empty, this is an error
    # Task 001 should have created it
    atomic_error "No credentials configured - Task 001 should have created secrets.json"
    echo ""
    echo -e "  ${BOLD}Troubleshooting:${NC}"
    echo -e "  1. Ensure .env file exists with credentials"
    echo -e "  2. Re-run Phase 0 from Task 001"
    echo ""
    return 1

    # =========================================================================
    # NETWORK MODE SELECTION (CUI vs Internet-enabled)
    # =========================================================================
    # Check if network_mode was pre-configured in setup.md (via project-config.json)
    local preconfigured_mode=""
    if [[ -f "$config_file" ]]; then
        preconfigured_mode=$(jq -r '.extracted.sandbox.network_mode // empty' "$config_file" 2>/dev/null)
    fi

    local network_mode="cui"
    if [[ -n "$preconfigured_mode" && "$preconfigured_mode" != "null" ]]; then
        # Use pre-configured value from setup.md
        network_mode="$preconfigured_mode"
        echo -e "  ${BOLD}Network Access Mode${NC} ${DIM}(from setup.md)${NC}"
        if [[ "$network_mode" == "cui" ]]; then
            echo -e "  ${GREEN}✓${NC} CUI Mode: Claude Code will be sandboxed from internet"
        else
            echo -e "  ${GREEN}✓${NC} Internet Mode: Claude Code can access the web"
        fi
    else
        # Interactive selection
        echo -e "  ${BOLD}Network Access Mode${NC}"
        echo -e "  ${DIM}Controls whether Claude Code can access the internet${NC}"
        echo ""
        echo -e "  ${CYAN}1.${NC} CUI Mode       ${DIM}- No internet access (airgapped/secure)${NC}"
        echo -e "  ${CYAN}2.${NC} Internet Mode  ${DIM}- Full network access (web search, fetch)${NC}"
        echo ""
        # Drain stdin before prompt
        while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done
        read -e -p "  Network mode [1]: " network_choice || true
        network_choice=${network_choice:-1}

        case "$network_choice" in
            1) network_mode="cui" ;;
            2) network_mode="internet" ;;
            *) network_mode="cui" ;;
        esac

        if [[ "$network_mode" == "cui" ]]; then
            echo -e "  ${GREEN}✓${NC} CUI Mode: Claude Code will be sandboxed from internet"
        else
            echo -e "  ${GREEN}✓${NC} Internet Mode: Claude Code can access the web"
        fi
    fi

    # Save network mode to secrets
    local tmp=$(atomic_mktemp)
    jq --arg mode "$network_mode" '.network_mode = $mode' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
    echo ""

    # =========================================================================
    # AUTOMATIC PROVIDER DETECTION
    # =========================================================================
    # Detect available providers from environment variables
    echo -e "  ${BOLD}Detecting available providers...${NC}"
    echo ""

    # Auto-configure based on environment variables
    local configured_any=false

    # Check AWS Bedrock (profile or static keys)
    if [[ -n "${AWS_PROFILE:-}" ]] || [[ -n "${AWS_ACCESS_KEY_ID:-}" && -n "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
        _004_auto_configure_bedrock "$secrets_file"
        configured_any=true
    fi

    # Check Anthropic API
    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
        _004_auto_configure_anthropic "$secrets_file"
        configured_any=true
    fi

    # Check Ollama
    if curl -s --connect-timeout 1 http://localhost:11434/api/tags &>/dev/null; then
        _004_auto_configure_ollama "$secrets_file"
        configured_any=true
    fi

    # Auto-enable local memory
    _004_auto_configure_memory "$secrets_file"

    if [[ "$configured_any" == "false" ]]; then
        echo ""
        atomic_error "No providers detected!"
        echo ""
        echo -e "${BOLD}Please configure credentials in .env:${NC}"
        echo -e "  AWS_ACCESS_KEY_ID=..."
        echo -e "  AWS_SECRET_ACCESS_KEY=..."
        echo -e "  ANTHROPIC_API_KEY=..."
        echo ""
        return 1
    fi

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
    echo -e "  ${DIM}Claude Code will use AWS Bedrock for all LLM calls${NC}"
    echo ""

    # Check for existing AWS config
    local has_credentials=false
    if [[ -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
        echo -e "  ${GREEN}✓${NC} AWS credentials found in environment"
        has_credentials=true
    elif [[ -f ~/.aws/credentials || -f ~/.aws/config ]]; then
        echo -e "  ${GREEN}✓${NC} AWS config found (~/.aws/)"
        has_credentials=true
    fi

    if [[ "$has_credentials" != "true" ]]; then
        atomic_warn "No AWS credentials detected"
        echo -e "  ${DIM}Configure with: aws configure${NC}"
        echo -e "  ${DIM}Or SSO: aws sso login --profile <profile>${NC}"
        echo ""
    fi

    # Region - detect GovCloud vs commercial
    echo -e "  ${DIM}Common regions: us-east-1, us-west-2, us-gov-west-1 (GovCloud)${NC}"
    read -e -p "    AWS Region [us-east-1]: " aws_region || true
    aws_region=${aws_region:-us-east-1}

    # Profile
    read -e -p "    AWS Profile [default]: " aws_profile || true
    aws_profile=${aws_profile:-default}

    # Model - Sonnet 4.5 only (available in Bedrock)
    echo ""
    if [[ "$aws_region" == us-gov-* ]]; then
        # GovCloud uses inference profile format
        bedrock_model="us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0"
        echo -e "  ${GREEN}✓${NC} Model: Claude Sonnet 4.5 (GovCloud inference profile)"
    else
        # Commercial uses global inference profile
        bedrock_model="global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        echo -e "  ${GREEN}✓${NC} Model: Claude Sonnet 4.5"
    fi

    # Save configuration
    local tmp=$(atomic_mktemp)
    jq --arg region "$aws_region" \
       --arg profile "$aws_profile" \
       --arg model "$bedrock_model" \
       '.bedrock_enabled = true | .aws_region = $region | .aws_profile = $profile | .bedrock_model = $model' \
       "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"

    echo ""
    atomic_success "AWS Bedrock configured"
    echo -e "  ${DIM}Region: $aws_region | Profile: $aws_profile${NC}"
    echo -e "  ${DIM}Model: $bedrock_model${NC}"
}

# Local Memory configuration (persistent context across tasks)
_004_collect_memory() {
    local secrets_file="$1"

    echo -e "  ${CYAN}Local Memory${NC}"
    echo -e "  ${DIM}Enables persistent context across ATOMIC-CLAUDE tasks${NC}"
    echo -e "  ${DIM}Memory is stored locally in .state/memory/${NC}"
    echo ""

    read -e -p "    Enable local memory? [Y/n]: " enable_memory || true
    enable_memory=${enable_memory:-Y}

    local tmp=$(atomic_mktemp)
    if [[ "$enable_memory" =~ ^[Yy] ]]; then
        jq '.memory_enabled = true' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
        atomic_success "Local memory enabled"
    else
        jq '.memory_enabled = false' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
        atomic_info "Local memory disabled"
    fi
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

# Auto-configure AWS Bedrock from environment variables
_004_auto_configure_bedrock() {
    local secrets_file="$1"
    local aws_region="${AWS_REGION:-us-east-1}"
    local aws_profile="${AWS_PROFILE:-default}"

    # Use ANTHROPIC_MODEL if set, otherwise determine based on region
    local bedrock_model
    if [[ -n "${ANTHROPIC_MODEL:-}" ]]; then
        bedrock_model="$ANTHROPIC_MODEL"
    elif [[ "$aws_region" == us-gov-* ]]; then
        bedrock_model="us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0"
    else
        bedrock_model="anthropic.claude-sonnet-4-5-20250929-v1:0"
    fi

    # Check if using profile-based auth (SSO or assumed roles)
    local auth_type="static keys"
    if [[ -n "${AWS_PROFILE:-}" ]] && [[ -z "${AWS_ACCESS_KEY_ID:-}" ]]; then
        auth_type="profile (SSO/assumed role)"
    fi

    local tmp=$(atomic_mktemp)
    jq --arg region "$aws_region" \
       --arg profile "$aws_profile" \
       --arg model "$bedrock_model" \
       --argjson use_bedrock "${CLAUDE_CODE_USE_BEDROCK:-1}" \
       '.bedrock_enabled = true | .aws_region = $region | .aws_profile = $profile | .bedrock_model = $model | .use_bedrock = $use_bedrock' \
       "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"

    echo -e "  ${GREEN}✓${NC} AWS Bedrock configured"
    echo -e "    ${DIM}Profile: $aws_profile | Region: $aws_region${NC}"
    echo -e "    ${DIM}Model: $bedrock_model${NC}"
    echo -e "    ${DIM}Auth: $auth_type${NC}"

    # For profile-based auth, check if credentials are valid
    if [[ "$auth_type" == "profile (SSO/assumed role)" ]]; then
        if aws sts get-caller-identity --profile "$aws_profile" &>/dev/null; then
            echo -e "    ${GREEN}✓${NC} ${DIM}Profile authenticated${NC}"
        else
            echo -e "    ${YELLOW}⚠${NC}  ${DIM}Profile not authenticated${NC}"
            echo -e "       ${DIM}Run: aws sso login --profile $aws_profile${NC}"
        fi
    fi
}

# Auto-configure Anthropic API from environment variables
_004_auto_configure_anthropic() {
    local secrets_file="$1"
    local key_name="anthropic_api_key"

    local tmp=$(atomic_mktemp)
    jq --arg key "$key_name" --arg val "$ANTHROPIC_API_KEY" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"

    local masked=$(_004_mask_key "$ANTHROPIC_API_KEY")
    echo -e "  ${GREEN}✓${NC} Anthropic API configured"
    echo -e "    ${DIM}Key: $masked${NC}"
}

# Auto-configure Ollama
_004_auto_configure_ollama() {
    local secrets_file="$1"

    # Detect available models
    local models
    models=$(curl -s http://localhost:11434/api/tags 2>/dev/null | jq -r '.models[].name' 2>/dev/null | head -5 | tr '\n' ', ' | sed 's/,$//')

    local tmp=$(atomic_mktemp)
    jq '.ollama_enabled = true | .ollama_host = "localhost:11434"' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"

    echo -e "  ${GREEN}✓${NC} Ollama configured"
    echo -e "    ${DIM}Host: localhost:11434${NC}"
    if [[ -n "$models" ]]; then
        echo -e "    ${DIM}Models: $models${NC}"
    fi
}

# Auto-configure local memory
_004_auto_configure_memory() {
    local secrets_file="$1"

    local tmp=$(atomic_mktemp)
    jq '.memory_enabled = true' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"

    echo -e "  ${GREEN}✓${NC} Local memory enabled"
}
