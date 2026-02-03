#!/usr/bin/env bash
#
# Task 001: Setup File Validation
# Ensures initialization/setup.md exists before proceeding
#
# If setup.md doesn't exist:
#   - Creates template from initialization/setup.md or embedded fallback
#   - Prompts user to fill it out
#   - Waits for confirmation before proceeding
#

task_001_setup_validation() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local init_dir="$ATOMIC_ROOT/initialization"
    local setup_file="$init_dir/setup.md"
    local orchestrator_template="$ROOT_DIR/initialization/setup.md"
    local file_exists=false

    # Ensure initialization directory exists
    mkdir -p "$init_dir"

    # Check if setup.md already exists
    if [[ -f "$setup_file" ]]; then
        file_exists=true
    fi

    # Always show the guide (whether file exists or not)
    echo ""
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  ATOMIC CLAUDE Setup${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BOLD}Why setup.md is required:${NC}"
    echo ""
    echo -e "  ${CYAN}•${NC} ${BOLD}Single source of truth${NC} for all project configuration"
    echo -e "  ${CYAN}•${NC} Ensures ${BOLD}consistency${NC} across all pipeline phases"
    echo -e "  ${CYAN}•${NC} Enables ${BOLD}deterministic${NC} behavior (same config = same results)"
    echo -e "  ${CYAN}•${NC} Makes projects ${BOLD}reproducible${NC} and shareable"
    echo -e "  ${CYAN}•${NC} Allows ${BOLD}version control${NC} of pipeline configuration"
    echo ""
    echo -e "${BOLD}What setup.md defines:${NC}"
    echo ""
    echo -e "  ${DIM}Project${NC}         Name, type, description, goals"
    echo -e "  ${DIM}LLM${NC}             Provider (Max/API/Bedrock/Ollama), models"
    echo -e "  ${DIM}Repository${NC}      Git strategy, commit format, branch workflow"
    echo -e "  ${DIM}Sandbox${NC}         Network mode, command approval, security"
    echo -e "  ${DIM}Pipeline${NC}        Phases to run, human gates, mode"
    echo -e "  ${DIM}Agents${NC}          Expert assignments for each phase"
    echo -e "  ${DIM}Constraints${NC}     Tech stack, infrastructure, compliance"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Create template if it doesn't exist
    if [[ "$file_exists" == "false" ]]; then
        _001_ensure_setup_template "$setup_file" "$orchestrator_template"
        echo ""
        atomic_success "Created setup template"
    else
        atomic_success "Found setup template"
    fi

    echo ""
    atomic_substep "Location: $setup_file"
    echo ""

    # Show instructions (always, whether file was just created or already exists)
    echo -e "${BOLD}Before continuing:${NC}"
    echo ""
    echo -e "  ${CYAN}1.${NC} Open the file:  ${BOLD}$setup_file${NC}"
    echo -e "  ${CYAN}2.${NC} ${YELLOW}Customize it for your project${NC} (required!)"
    echo -e "  ${CYAN}3.${NC} Replace generic values with your project details"
    echo -e "  ${CYAN}4.${NC} Use these special values:"
    echo -e "     ${DIM}•${NC} ${GREEN}infer${NC}   - Let Claude extract from your docs"
    echo -e "     ${DIM}•${NC} ${GREEN}default${NC} - Use recommended settings"
    echo -e "     ${DIM}•${NC} ${GREEN}detect${NC}  - Auto-detect from environment"
    echo ""
    echo -e "  ${CYAN}5.${NC} ${YELLOW}Create .env file with API credentials${NC} (required!)"
    echo -e "     Location: ${BOLD}$ATOMIC_ROOT/.env${NC}"
    echo -e "     See setup.md for .env template"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Drain stdin before prompt
    while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done

    # Wait for user to confirm setup.md is customized and ready
    while true; do
        echo -e -n "  Press ${BOLD}Enter${NC} when you've customized setup.md (or 'q' to quit): "
        read -e response || true

        case "${response,,}" in
            q|quit)
                atomic_error "Setup aborted"
                return 1
                ;;
            *)
                if [[ -f "$setup_file" ]]; then
                    echo ""
                    atomic_success "Setup file ready"

                    # Check for .env file with credentials
                    _001_validate_env_file

                    break
                else
                    echo ""
                    atomic_error "Setup file not found at $setup_file"
                    echo ""
                fi
                ;;
        esac
    done

    _001_save_config "$config_file" "$setup_file"
    return 0
}

# Ensure setup.md template exists, create from orchestrator template if not
_001_ensure_setup_template() {
    local target_file="$1"
    local template_file="$2"

    if [[ -f "$target_file" ]]; then
        return 0
    fi

    mkdir -p "$(dirname "$target_file")"

    if [[ -f "$template_file" ]]; then
        cp "$template_file" "$target_file"
        echo -e "  ${GREEN}✓${NC} Created setup template: $target_file"
    else
        # Fallback: embedded comprehensive template
        cat > "$target_file" << 'TEMPLATE'
# Project Setup
# =============
# Fill in the fields below. Use "infer" to let Claude extract from reference
# materials, "default" for recommended values, or enter a specific value.

## Project Information

**name**: infer
**description**: infer
**type**: default
**primary_goal**: infer

## Repository Configuration

**repository.url**: detect
**repository.default_branch**: default
**repository.pr_strategy**: default
**repository.commit_strategy**: default
**repository.push_strategy**: default
**repository.commit_format**: default

## Sandbox & Security

**sandbox.command_approval_mode**: default
**sandbox.network_mode**: default
**sandbox.network_access**: default

## MCP Servers

**mcp.enabled**: false

## Pipeline Configuration

**pipeline.mode**: default
**pipeline.skip_phases**: []
**pipeline.human_gates**: [0, 2, 5, 9]

## Agent Assignments (optional)

**agents.phase_1**: infer
**agents.phase_2**: infer
**agents.phase_3**: infer
**agents.phase_4**: infer
**agents.phase_5**: infer
**agents.phase_6**: infer
**agents.phase_7**: infer
**agents.phase_8**: infer
**agents.phase_9**: infer

## LLM Configuration

**llm.primary_provider**: default
**llm.primary_model**: default
**llm.fast_model**: default
**llm.local_fallback**: false

## Context Gardener (optional)

**gardener.model**: infer
**gardener.threshold_percent**: 75
**gardener.preserve_recent_exchanges**: 4
**gardener.preserve_opening**: true

## Technical Constraints (optional)

**constraints.technical**: infer
**constraints.infrastructure**: infer
**constraints.compliance**: infer
**constraints.dependencies**: infer

## Reference Materials

List any documentation, specs, or design docs that Claude should read:

- ./README.md
- ./docs/ARCHITECTURE.md

---

## Field Reference

### project.type options:
- new-component: Standalone service/module
- new-frontend: Web/mobile UI application
- new-api: Backend API service
- new-cli: Command-line tool
- new-library: Shared library/package
- new-monorepo: Multi-package repository
- existing: Add to existing codebase
- migration: Technology migration
- refactor: Code modernization

### llm.primary_provider options:
- anthropic: Claude (recommended)
- aws-bedrock: AWS Bedrock
- openai: OpenAI GPT
- ollama: Local models
- google: Google Gemini
- azure: Azure OpenAI
- openrouter: OpenRouter

### pipeline.mode options:
- component: Build and test, no deployment
- full: Complete pipeline including deployment
- library: Minimal for shared packages
- prototype: Quick validation only

### Defaults:
- "default" = Use recommended value
- "infer" = Extract from reference materials
- "detect" = Auto-detect from environment
TEMPLATE
        echo -e "  ${GREEN}✓${NC} Created setup template: $target_file"
    fi
}

# Helper: Save config and record decision
_001_save_config() {
    local config_file="$1"
    local setup_file="$2"

    # Initialize config file
    mkdir -p "$(dirname "$config_file")"
    cat > "$config_file" << EOF
{
  "setup_mode": "document",
  "setup_file": "$setup_file",
  "created_at": "$(date -Iseconds)"
}
EOF

    # Store setup file path for Task 002
    SETUP_FILE_PATH="$setup_file"

    # Record decision to context
    atomic_context_decision "Setup file validated: $SETUP_FILE_PATH" "configuration"

    atomic_success "Setup file: $setup_file"
}

# Validate .env file exists with required credentials
_001_validate_env_file() {
    local env_file="$ATOMIC_ROOT/.env"
    local has_aws=false
    local has_anthropic=false
    local has_ollama=false

    echo ""
    echo -e "${BOLD}Validating API credentials...${NC}"
    echo ""

    # Check if .env file exists
    if [[ ! -f "$env_file" ]]; then
        echo -e "${YELLOW}⚠${NC}  No .env file found at: $env_file"
        echo ""
        echo -e "${DIM}Checking for alternative credential sources...${NC}"

        # Check for AWS credentials (profile, SSO, or static keys)
        if [[ -n "${AWS_PROFILE:-}" ]] || [[ -f ~/.aws/credentials ]] || [[ -f ~/.aws/config ]] || [[ -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
            has_aws=true
            if [[ -n "${AWS_PROFILE:-}" ]]; then
                echo -e "  ${GREEN}✓${NC} AWS profile found: $AWS_PROFILE"
                echo -e "    ${DIM}Ensure authenticated: aws sso login --profile $AWS_PROFILE${NC}"
            else
                echo -e "  ${GREEN}✓${NC} AWS credentials found (CLI or environment)"
            fi
        fi

        # Check for environment variables
        if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
            has_anthropic=true
            echo -e "  ${GREEN}✓${NC} Anthropic API key found in environment"
        fi

        # Check for Ollama
        if curl -s --connect-timeout 1 http://localhost:11434/api/tags &>/dev/null; then
            has_ollama=true
            echo -e "  ${GREEN}✓${NC} Ollama detected on localhost:11434"
        fi

        # If no credentials found, show warning
        if [[ "$has_aws" == "false" && "$has_anthropic" == "false" && "$has_ollama" == "false" ]]; then
            echo ""
            echo -e "${RED}✗${NC} No API credentials found!"
            echo ""
            echo -e "${BOLD}Create .env file with credentials:${NC}"
            echo ""
            echo -e "  ${DIM}# AWS Bedrock${NC}"
            echo -e "  AWS_ACCESS_KEY_ID=your-key"
            echo -e "  AWS_SECRET_ACCESS_KEY=your-secret"
            echo -e "  AWS_REGION=us-gov-west-1"
            echo ""
            echo -e "  ${DIM}# OR Anthropic API${NC}"
            echo -e "  ANTHROPIC_API_KEY=sk-ant-..."
            echo ""
            echo -e "  ${DIM}# OR use: aws configure${NC}"
            echo ""
            atomic_error "Cannot proceed without API credentials"
            return 1
        fi
    else
        # Load .env file
        echo -e "${DIM}Loading credentials from .env...${NC}"
        set -a
        source "$env_file"
        set +a

        # Check what's available
        if [[ -n "${AWS_PROFILE:-}" ]]; then
            has_aws=true
            echo -e "  ${GREEN}✓${NC} AWS Bedrock profile loaded: $AWS_PROFILE"
            echo -e "    ${DIM}Region: ${AWS_REGION:-us-east-1}${NC}"
            if [[ -n "${ANTHROPIC_MODEL:-}" ]]; then
                echo -e "    ${DIM}Model: $ANTHROPIC_MODEL${NC}"
            fi
            # Check if credentials are valid (non-blocking warning)
            if ! aws sts get-caller-identity --profile "$AWS_PROFILE" &>/dev/null; then
                echo -e "    ${YELLOW}⚠${NC}  ${DIM}Profile not authenticated - run: aws sso login --profile $AWS_PROFILE${NC}"
            fi
        elif [[ -n "${AWS_ACCESS_KEY_ID:-}" && -n "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
            has_aws=true
            echo -e "  ${GREEN}✓${NC} AWS Bedrock credentials loaded (static keys)"
        fi

        if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
            has_anthropic=true
            echo -e "  ${GREEN}✓${NC} Anthropic API key loaded"
        fi

        if curl -s --connect-timeout 1 http://localhost:11434/api/tags &>/dev/null; then
            has_ollama=true
            echo -e "  ${GREEN}✓${NC} Ollama available"
        fi

        atomic_success "Credentials loaded from .env"
    fi

    echo ""
    atomic_context_decision "Credentials validated: AWS=$has_aws, Anthropic=$has_anthropic, Ollama=$has_ollama" "configuration"

    # Create secrets.json NOW (before Task 002) so LLM invocations work
    _001_create_secrets_file
}

# Create secrets.json from .env file
_001_create_secrets_file() {
    local secrets_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/secrets.json"
    mkdir -p "$(dirname "$secrets_file")"

    # Start with empty config
    echo '{}' > "$secrets_file"

    # If .env was loaded, configure providers
    if [[ -n "${AWS_PROFILE:-}" ]] || [[ -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
        # Configure AWS Bedrock
        local aws_region="${AWS_REGION:-us-east-1}"
        local aws_profile="${AWS_PROFILE:-default}"
        local bedrock_model="${ANTHROPIC_MODEL:-}"

        # Determine default model if not set
        if [[ -z "$bedrock_model" ]]; then
            if [[ "$aws_region" == us-gov-* ]]; then
                bedrock_model="us-gov.anthropic.claude-sonnet-4-5-20250929-v1:0"
            else
                bedrock_model="anthropic.claude-sonnet-4-5-20250929-v1:0"
            fi
        fi

        local tmp=$(atomic_mktemp)
        jq --arg region "$aws_region" \
           --arg profile "$aws_profile" \
           --arg model "$bedrock_model" \
           --argjson use_bedrock "${CLAUDE_CODE_USE_BEDROCK:-1}" \
           '.bedrock_enabled = true | .aws_region = $region | .aws_profile = $profile | .bedrock_model = $model | .use_bedrock = $use_bedrock' \
           "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"

        echo -e "  ${GREEN}✓${NC} AWS Bedrock configured in secrets.json"
    fi

    # Configure Anthropic API if key present
    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
        local tmp=$(atomic_mktemp)
        jq --arg key "anthropic_api_key" --arg val "$ANTHROPIC_API_KEY" '.[$key] = $val' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
        echo -e "  ${GREEN}✓${NC} Anthropic API configured in secrets.json"
    fi

    # Configure Ollama if available
    if curl -s --connect-timeout 1 http://localhost:11434/api/tags &>/dev/null; then
        local tmp=$(atomic_mktemp)
        jq '.ollama_enabled = true | .ollama_host = "localhost:11434"' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"
        echo -e "  ${GREEN}✓${NC} Ollama configured in secrets.json"
    fi

    # Enable local memory by default
    local tmp=$(atomic_mktemp)
    jq '.memory_enabled = true' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"

    # Set network mode (from .env or default)
    local network_mode="${ATOMIC_NETWORK_MODE:-cui}"
    tmp=$(atomic_mktemp)
    jq --arg mode "$network_mode" '.network_mode = $mode' "$secrets_file" > "$tmp" && mv "$tmp" "$secrets_file"

    # Secure the file
    if [[ "$(uname -s)" != MINGW* && "$(uname -s)" != CYGWIN* && "$(uname -s)" != MSYS* ]]; then
        chmod 600 "$secrets_file" 2>/dev/null || true
    fi

    echo -e "  ${DIM}Secrets file: $secrets_file${NC}"
    echo ""
}
