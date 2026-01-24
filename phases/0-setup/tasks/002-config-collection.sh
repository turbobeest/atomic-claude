#!/bin/bash
#
# Task 002: Config Collection
# Collects project configuration via one of three modes:
#   - DOCUMENT: Parse initialization/ files with Claude (1 LLM call)
#   - GUIDED:   Interactive Q&A, step by step
#   - QUICK:    Minimal input, sensible defaults
#

# Document mode: parse initialization files with Claude
task_002_config_document() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"
    local extracted_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/extracted-config.json"
    local init_dir="$ATOMIC_ROOT/initialization"

    atomic_step "Document Configuration"

    # Check if Task 001 already detected a setup file
    if [[ -n "${SETUP_FILE_PATH:-}" ]] && [[ -f "$SETUP_FILE_PATH" ]]; then
        atomic_substep "Using pre-detected setup: $SETUP_FILE_PATH"
    else
        echo ""
        echo -e "${DIM}  ┌─────────────────────────────────────────────────────────┐${NC}"
        echo -e "${DIM}  │ Configuration files are in initialization/              │${NC}"
        echo -e "${DIM}  │                                                         │${NC}"
        echo -e "${DIM}  │   setup.md        - Project configuration               │${NC}"
        echo -e "${DIM}  │   agent-plan.md   - Agent assignments                   │${NC}"
        echo -e "${DIM}  │   audit-plan.md   - Audit profiles                      │${NC}"
        echo -e "${DIM}  │                                                         │${NC}"
        echo -e "${DIM}  │ Claude will read these files and extract config.        │${NC}"
        echo -e "${DIM}  │ Fields marked 'infer' will be populated from your       │${NC}"
        echo -e "${DIM}  │ reference materials.                                    │${NC}"
        echo -e "${DIM}  └─────────────────────────────────────────────────────────┘${NC}"
        echo ""

        # Check for initialization directory
        local default_path=""
        if [[ -f "$init_dir/setup.md" ]]; then
            default_path="$init_dir/setup.md"
        else
            # Check for legacy or alternate locations
            for check in "./initialization/setup.md" "./setup.md" "./manifest.md"; do
                if [[ -f "$check" ]]; then
                    default_path="$check"
                    break
                fi
            done
        fi

        while true; do
            if [[ -n "$default_path" ]]; then
                read -p "  Setup file path [$default_path]: " SETUP_FILE_PATH
                SETUP_FILE_PATH=${SETUP_FILE_PATH:-$default_path}
            else
                read -p "  Setup file path: " SETUP_FILE_PATH
            fi

            if [[ -z "$SETUP_FILE_PATH" ]]; then
                atomic_error "Path required"
                continue
            fi

            if [[ ! -f "$SETUP_FILE_PATH" ]]; then
                atomic_error "File not found: $SETUP_FILE_PATH"
                echo ""
                continue
            fi

            break
        done
    fi

    # Record the setup file path decision
    atomic_context_decision "Setup file: $SETUP_FILE_PATH" "configuration"

    atomic_substep "Reading setup: $SETUP_FILE_PATH"

    # Read the setup content (limited to 500 lines to protect context window)
    local setup_content
    setup_content=$(head -500 "$SETUP_FILE_PATH")
    local setup_lines=$(wc -l < "$SETUP_FILE_PATH")
    if [[ $setup_lines -gt 500 ]]; then
        setup_content+=$'\n\n[TRUNCATED: Showing 500 of '"$setup_lines"' lines]'
    fi

    # Determine initialization directory
    local setup_dir
    setup_dir=$(dirname "$SETUP_FILE_PATH")

    # Read agent-plan.md if it exists
    local agent_plan_content=""
    if [[ -f "$setup_dir/agent-plan.md" ]]; then
        atomic_substep "Reading agent plan: $setup_dir/agent-plan.md"
        agent_plan_content=$(cat "$setup_dir/agent-plan.md")
    fi

    # Read audit-plan.md if it exists
    local audit_plan_content=""
    if [[ -f "$setup_dir/audit-plan.md" ]]; then
        atomic_substep "Reading audit plan: $setup_dir/audit-plan.md"
        audit_plan_content=$(cat "$setup_dir/audit-plan.md")
    fi

    # Read any reference docs mentioned in the setup
    local reference_content=""
    local ref_docs
    ref_docs=$(grep -E '^\s*-\s*\./' "$SETUP_FILE_PATH" 2>/dev/null | sed 's/^\s*-\s*//' || true)
    ref_docs=$(echo "$ref_docs" | head -5)

    if [[ -n "$ref_docs" ]]; then
        atomic_substep "Reading reference documents..."
        while IFS= read -r ref; do
            if [[ -f "$ref" ]]; then
                atomic_substep "  Found: $ref"
                reference_content+="
=== $ref ===
$(head -200 "$ref" 2>/dev/null || true)

"
            fi
        done <<< "$ref_docs"
    fi

    # Also try to detect from git remote
    local detected_repo=""
    detected_repo=$(git remote get-url origin 2>/dev/null || true)

    # Create extraction prompt
    local prompt_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/prompts/extract-setup.md"
    mkdir -p "$(dirname "$prompt_file")"

    cat > "$prompt_file" << 'PROMPT_HEADER'
# Task: Extract Configuration from Project Setup

You are a **configuration parser** specializing in extracting structured data from semi-structured documents. Your role is to read project initialization files and output a validated JSON configuration.

## Output Requirements

Output ONLY valid JSON - no markdown wrappers, no explanation text, no code blocks.
Start with `{` and end with `}`.

## Extraction Rules

1. **Explicit values**: Use the exact value from the setup file
2. **"infer" fields**: Analyze reference materials to derive a project-specific value
3. **"default [X]" fields**: Use the literal value X shown in brackets
4. **"detect" fields**: Use the auto-detected values provided below
5. **Missing required values**: Use `null` (do NOT invent values)
6. **Malformed input**: Extract what you can, use defaults for the rest

## Edge Cases

| Situation | Response |
|-----------|----------|
| Setup file is mostly empty | Use defaults for all fields, note in constraints |
| Conflicting values | Prefer explicit setup.md values over inferred |
| Unknown project type | Default to "new-component" |
| Invalid enum value | Use closest valid option or default |
| Truncated input | Process what's available, don't fail |

## Detected Values:
PROMPT_HEADER

    echo "- Repository URL (from git): ${detected_repo:-not detected}" >> "$prompt_file"
    echo "- Directory name: $(basename "$(pwd)")" >> "$prompt_file"
    echo "" >> "$prompt_file"

    cat >> "$prompt_file" << 'PROMPT_SCHEMA'
## Output JSON Schema:

{
  "project": {
    "name": "string (max 24 chars)",
    "description": "string",
    "type": "new-component|new-frontend|new-api|new-cli|new-library|new-monorepo|existing|migration|refactor",
    "primary_goal": "string"
  },
  "repository": {
    "url": "string or null",
    "default_branch": "string",
    "pr_strategy": "direct|feature-branch|gitflow",
    "commit_strategy": "per-phase|per-task|per-prompt|manual|atomic",
    "push_strategy": "per-phase|per-commit|manual|on-close",
    "commit_format": "conventional|gitmoji|simple|custom"
  },
  "sandbox": {
    "allowed_paths": ["array of paths"] or null,
    "forbidden_paths": ["array of paths"],
    "forbidden_commands": ["array of commands"],
    "command_approval_mode": "strict|cautious|permissive",
    "network_access": "none|fetch-only|allowlist|blocklist|full",
    "blocked_ips": ["array of CIDR ranges"]
  },
  "mcp": {
    "enabled": boolean,
    "servers": ["array of server names"],
    "tool_permissions": "all|write-only|dangerous|none"
  },
  "pipeline": {
    "mode": "full|component|library|prototype",
    "skip_phases": [array of numbers] or [],
    "human_gates": [array of phase numbers]
  },
  "agents": {
    "phase_0": "string",
    "phase_1": "string",
    "phase_2": "string",
    "phase_3": "string",
    "phase_4": "string",
    "phase_5": "string",
    "phase_6": "string",
    "phase_7": "string",
    "phase_8": "string",
    "phase_9": "string"
  },
  "llm": {
    "primary_provider": "anthropic|openai|aws-bedrock|google|ollama|openrouter|azure",
    "primary_model": "string or null",
    "fast_model": "string or null",
    "local_fallback": boolean
  },
  "gardener": {
    "model": "string or 'infer' (auto-select fastest)",
    "threshold_percent": "number 50-90 (trigger adjudication at this % of context)",
    "fallback_chain": ["array of model names to try if primary fails"],
    "preserve_recent_exchanges": "number 2-8 (exchanges to keep after adjudication)",
    "preserve_opening": "boolean (keep opening messages for continuity)"
  },
  "constraints": {
    "technical": ["array of strings"] or null,
    "infrastructure": "string or null",
    "compliance": ["array of strings"] or null,
    "dependencies": ["array of strings"] or null
  }
}

## Example Output

For a Node.js API project with TypeScript and PostgreSQL:

{
  "project": {
    "name": "order-service",
    "description": "REST API for order management",
    "type": "new-api",
    "primary_goal": "Build a scalable order processing service"
  },
  "repository": {
    "url": "https://github.com/acme/order-service",
    "default_branch": "main",
    "pr_strategy": "feature-branch",
    "commit_strategy": "per-task",
    "push_strategy": "on-close",
    "commit_format": "conventional"
  },
  "sandbox": {
    "allowed_paths": null,
    "forbidden_paths": [".env*", "secrets/", "*.key"],
    "forbidden_commands": ["rm -rf /"],
    "command_approval_mode": "cautious",
    "network_access": "fetch-only",
    "blocked_ips": ["169.254.169.254/32"]
  },
  "mcp": {"enabled": false, "servers": [], "tool_permissions": "none"},
  "pipeline": {"mode": "component", "skip_phases": [], "human_gates": [0, 2, 5]},
  "agents": {
    "phase_0": "default", "phase_1": "infer", "phase_2": "infer",
    "phase_3": "infer", "phase_4": "infer", "phase_5": "infer",
    "phase_6": "infer", "phase_7": "infer", "phase_8": "infer", "phase_9": "infer"
  },
  "llm": {"primary_provider": "anthropic", "primary_model": null, "fast_model": null, "local_fallback": false},
  "gardener": {"model": "infer", "threshold_percent": 75, "fallback_chain": [], "preserve_recent_exchanges": 4, "preserve_opening": true},
  "constraints": {"technical": ["TypeScript", "PostgreSQL"], "infrastructure": "AWS", "compliance": null, "dependencies": ["express", "pg"]}
}

## Setup Content (setup.md):

PROMPT_SCHEMA

    echo "$setup_content" >> "$prompt_file"

    if [[ -n "$agent_plan_content" ]]; then
        echo "" >> "$prompt_file"
        echo "## Agent Plan (agent-plan.md):" >> "$prompt_file"
        echo "$agent_plan_content" >> "$prompt_file"
    fi

    if [[ -n "$audit_plan_content" ]]; then
        echo "" >> "$prompt_file"
        echo "## Audit Plan (audit-plan.md):" >> "$prompt_file"
        echo "$audit_plan_content" >> "$prompt_file"
    fi

    if [[ -n "$reference_content" ]]; then
        echo "" >> "$prompt_file"
        echo "## Reference Documents:" >> "$prompt_file"
        echo "$reference_content" >> "$prompt_file"
    fi

    atomic_waiting "Claude is extracting configuration..."

    # Invoke Claude to extract
    if atomic_invoke "$prompt_file" "$extracted_file" "Extract configuration from setup" --model=sonnet; then
        # Try to validate JSON
        if jq . "$extracted_file" > /dev/null 2>&1; then
            atomic_success "Configuration extracted successfully"

            # Merge into main config
            local tmp=$(atomic_mktemp)
            jq -s '.[0] * {extracted: .[1]}' "$config_file" "$extracted_file" > "$tmp" && mv "$tmp" "$config_file"
        else
            # Claude might have output markdown, try to extract JSON
            atomic_warn "Extracting JSON from response..."
            if grep -q '```json' "$extracted_file"; then
                sed -n '/```json/,/```/p' "$extracted_file" | sed '1d;$d' > "${extracted_file}.clean"
                if jq . "${extracted_file}.clean" > /dev/null 2>&1; then
                    mv "${extracted_file}.clean" "$extracted_file"
                    local tmp=$(atomic_mktemp)
                    jq -s '.[0] * {extracted: .[1]}' "$config_file" "$extracted_file" > "$tmp" && mv "$tmp" "$config_file"
                    atomic_success "Configuration extracted successfully"
                else
                    atomic_error "Failed to parse extracted JSON"
                    return 1
                fi
            else
                atomic_error "Failed to extract valid JSON"
                return 1
            fi
        fi
    else
        atomic_error "Setup extraction failed"

        # Offer fallback to guided mode
        echo ""
        echo -e "  ${YELLOW}Extraction failed. Would you like to:${NC}"
        echo -e "  ${GREEN}[r]${NC} Retry with a different setup file"
        echo -e "  ${GREEN}[g]${NC} Switch to guided mode"
        echo -e "  ${RED}[q]${NC} Quit"
        echo ""
        read -p "  Choice [r]: " fallback_choice
        fallback_choice=${fallback_choice:-r}

        case "$fallback_choice" in
            g|G)
                atomic_info "Switching to guided mode..."
                SETUP_MODE="guided"
                atomic_context_decision "Fallback: switched from document to guided mode" "configuration"
                task_002_config_guided
                return $?
                ;;
            q|Q)
                return 1
                ;;
            *)
                # Retry - clear setup path and recurse
                SETUP_FILE_PATH=""
                task_002_config_document
                return $?
                ;;
        esac
    fi

    # Record successful extraction
    atomic_context_decision "Config extracted from initialization files successfully" "configuration"
    atomic_context_artifact "extracted_config" "$extracted_file" "Extracted configuration from setup"

    return 0
}

# Guided mode: interactive Q&A
task_002_config_guided() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    atomic_step "Guided Configuration"

    echo ""
    echo -e "${DIM}  Answer the following questions to configure your project.${NC}"
    echo -e "${DIM}  Press Enter to accept default values shown in [brackets].${NC}"
    echo ""

    # --- Project Name ---
    local detected_name=$(basename "$(pwd)")
    if ! atomic_validate_project_name "$detected_name" >/dev/null 2>&1; then
        detected_name=$(echo "$detected_name" | tr ' ' '-' | tr -cd 'A-Za-z0-9_-' | cut -c1-24)
        [[ -z "$detected_name" ]] && detected_name="my-project"
    fi

    echo -e "${CYAN}  Project Name${NC}"
    echo -e "${DIM}    Max 24 chars, alphanumeric + hyphens/underscores${NC}"
    local project_name=""
    while true; do
        read -p "    Name [$detected_name]: " project_name
        project_name=${project_name:-$detected_name}
        if atomic_validate_project_name "$project_name" >/dev/null 2>&1; then
            break
        else
            atomic_error "Invalid: $(atomic_validate_project_name "$project_name")"
        fi
    done
    echo ""

    # --- Description ---
    echo -e "${CYAN}  Description${NC}"
    echo -e "${DIM}    One-line summary of what this project does${NC}"
    read -p "    Description: " description
    description=${description:-"A new software component"}
    echo ""

    # --- Project Type ---
    echo -e "${CYAN}  Project Type${NC}"
    echo -e "    ${DIM}1.${NC} new-component  - Standalone service/module"
    echo -e "    ${DIM}2.${NC} new-frontend   - Web/mobile UI application"
    echo -e "    ${DIM}3.${NC} new-api        - Backend API service"
    echo -e "    ${DIM}4.${NC} new-cli        - Command-line tool"
    echo -e "    ${DIM}5.${NC} new-library    - Shared library/package"
    echo -e "    ${DIM}6.${NC} new-monorepo   - Multi-package repository"
    echo -e "    ${DIM}7.${NC} existing       - Add to existing codebase"
    echo -e "    ${DIM}8.${NC} migration      - Technology migration"
    local project_type=""
    while true; do
        read -p "    Type [1]: " type_choice
        type_choice=${type_choice:-1}
        case "$type_choice" in
            1) project_type="new-component" ;;
            2) project_type="new-frontend" ;;
            3) project_type="new-api" ;;
            4) project_type="new-cli" ;;
            5) project_type="new-library" ;;
            6) project_type="new-monorepo" ;;
            7) project_type="existing" ;;
            8) project_type="migration" ;;
            *) atomic_error "Invalid choice"; continue ;;
        esac
        break
    done
    echo ""

    # --- Primary Goal ---
    echo -e "${CYAN}  Primary Goal${NC}"
    echo -e "${DIM}    What is the main objective of this project?${NC}"
    read -p "    Goal: " primary_goal
    primary_goal=${primary_goal:-"Build a production-ready component"}
    echo ""

    # --- Repository ---
    local detected_repo=$(git remote get-url origin 2>/dev/null || true)
    echo -e "${CYAN}  Repository URL${NC}"
    if [[ -n "$detected_repo" ]]; then
        echo -e "${DIM}    Detected: $detected_repo${NC}"
    fi
    read -p "    URL [$detected_repo]: " repo_url
    repo_url=${repo_url:-$detected_repo}
    echo ""

    # --- Pipeline Mode ---
    echo -e "${CYAN}  Pipeline Mode${NC}"
    echo -e "    ${DIM}1.${NC} component  - Build and test, no deployment"
    echo -e "    ${DIM}2.${NC} full       - Complete pipeline including deployment"
    echo -e "    ${DIM}3.${NC} library    - Minimal for shared packages"
    echo -e "    ${DIM}4.${NC} prototype  - Quick validation only"
    local pipeline_mode=""
    while true; do
        read -p "    Mode [1]: " mode_choice
        mode_choice=${mode_choice:-1}
        case "$mode_choice" in
            1) pipeline_mode="component" ;;
            2) pipeline_mode="full" ;;
            3) pipeline_mode="library" ;;
            4) pipeline_mode="prototype" ;;
            *) atomic_error "Invalid choice"; continue ;;
        esac
        break
    done
    echo ""

    # --- LLM Provider ---
    echo -e "${CYAN}  LLM Provider${NC}"
    echo -e "    ${DIM}1.${NC} anthropic    - Claude (recommended)"
    echo -e "    ${DIM}2.${NC} aws-bedrock  - AWS Bedrock"
    echo -e "    ${DIM}3.${NC} openai       - OpenAI GPT"
    echo -e "    ${DIM}4.${NC} ollama       - Local models"
    echo -e "    ${DIM}5.${NC} google       - Google Gemini"
    echo -e "    ${DIM}6.${NC} azure        - Azure OpenAI"
    local llm_provider=""
    while true; do
        read -p "    Provider [1]: " provider_choice
        provider_choice=${provider_choice:-1}
        case "$provider_choice" in
            1) llm_provider="anthropic" ;;
            2) llm_provider="aws-bedrock" ;;
            3) llm_provider="openai" ;;
            4) llm_provider="ollama" ;;
            5) llm_provider="google" ;;
            6) llm_provider="azure" ;;
            *) atomic_error "Invalid choice"; continue ;;
        esac
        break
    done
    echo ""

    # Build config JSON (using --arg for safe string handling)
    local tmp=$(atomic_mktemp)
    jq --arg name "$project_name" \
       --arg desc "$description" \
       --arg type "$project_type" \
       --arg goal "$primary_goal" \
       --arg repo "${repo_url:-}" \
       --arg mode "$pipeline_mode" \
       --arg provider "$llm_provider" \
       '. + {
        "extracted": {
            "project": {
                "name": $name,
                "description": $desc,
                "type": $type,
                "primary_goal": $goal
            },
            "repository": {
                "url": (if $repo == "" then null else $repo end),
                "default_branch": "main",
                "pr_strategy": "feature-branch",
                "commit_strategy": "per-task",
                "push_strategy": "on-close",
                "commit_format": "conventional"
            },
            "sandbox": {
                "forbidden_paths": [".env*", "secrets/", "credentials/", "*.pem", "*.key"],
                "command_approval_mode": "cautious",
                "network_access": "fetch-only",
                "blocked_ips": ["169.254.169.254/32"]
            },
            "mcp": {
                "enabled": false
            },
            "pipeline": {
                "mode": $mode,
                "skip_phases": [],
                "human_gates": [0, 2, 5, 9]
            },
            "agents": {
                "phase_0": "default",
                "phase_1": "infer",
                "phase_2": "infer",
                "phase_3": "infer",
                "phase_4": "infer",
                "phase_5": "infer",
                "phase_6": "infer",
                "phase_7": "infer",
                "phase_8": "infer",
                "phase_9": "infer"
            },
            "llm": {
                "primary_provider": $provider,
                "primary_model": null,
                "fast_model": null,
                "local_fallback": false
            }
        }
    }' "$config_file" > "$tmp" && mv "$tmp" "$config_file"

    # Record decisions to context
    atomic_context_decision "Project: $project_name ($project_type)" "configuration"
    atomic_context_decision "Pipeline mode: $pipeline_mode" "configuration"
    atomic_context_decision "LLM provider: $llm_provider" "configuration"
    if [[ -n "$repo_url" ]]; then
        atomic_context_decision "Repository: $repo_url" "configuration"
    fi

    atomic_success "Configuration collected"
    return 0
}

# Quick mode: minimal input, sensible defaults
task_002_config_quick() {
    local config_file="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/project-config.json"

    atomic_step "Quick Configuration"

    echo ""
    echo -e "  ${DIM}Using sensible defaults. Just name your project.${NC}"
    echo ""

    # --- Project Name (required) ---
    local detected_name=$(basename "$(pwd)")
    if ! atomic_validate_project_name "$detected_name" >/dev/null 2>&1; then
        detected_name=$(echo "$detected_name" | tr ' ' '-' | tr -cd 'A-Za-z0-9_-' | cut -c1-24)
        [[ -z "$detected_name" ]] && detected_name="my-project"
    fi

    echo -e "${CYAN}  Project Name${NC} ${DIM}(required)${NC}"
    local project_name=""
    while true; do
        read -p "    Name [$detected_name]: " project_name
        project_name=${project_name:-$detected_name}
        if atomic_validate_project_name "$project_name" >/dev/null 2>&1; then
            break
        else
            atomic_error "Invalid: $(atomic_validate_project_name "$project_name")"
        fi
    done
    echo ""

    # --- Optional Goal ---
    echo -e "${CYAN}  Primary Goal${NC} ${DIM}(optional, press Enter to skip)${NC}"
    read -p "    Goal: " primary_goal
    primary_goal=${primary_goal:-"Build a production-ready component"}
    echo ""

    # Detect repo
    local detected_repo=$(git remote get-url origin 2>/dev/null || true)

    # Build config with all defaults (using --arg for safe string handling)
    local tmp=$(atomic_mktemp)
    jq --arg name "$project_name" \
       --arg goal "$primary_goal" \
       --arg repo "${detected_repo:-}" \
       '. + {
        "extracted": {
            "project": {
                "name": $name,
                "description": "A new software project",
                "type": "new-component",
                "primary_goal": $goal
            },
            "repository": {
                "url": (if $repo == "" then null else $repo end),
                "default_branch": "main",
                "pr_strategy": "feature-branch",
                "commit_strategy": "per-task",
                "push_strategy": "on-close",
                "commit_format": "conventional"
            },
            "sandbox": {
                "forbidden_paths": [".env*", "secrets/", "credentials/", "*.pem", "*.key"],
                "command_approval_mode": "cautious",
                "network_access": "fetch-only",
                "blocked_ips": ["169.254.169.254/32"]
            },
            "mcp": {
                "enabled": false
            },
            "pipeline": {
                "mode": "component",
                "skip_phases": [],
                "human_gates": [0, 2, 5, 9]
            },
            "agents": {
                "phase_0": "default",
                "phase_1": "infer",
                "phase_2": "infer",
                "phase_3": "infer",
                "phase_4": "infer",
                "phase_5": "infer",
                "phase_6": "infer",
                "phase_7": "infer",
                "phase_8": "infer",
                "phase_9": "infer"
            },
            "llm": {
                "primary_provider": "anthropic",
                "primary_model": null,
                "fast_model": null,
                "local_fallback": false
            }
        }
    }' "$config_file" > "$tmp" && mv "$tmp" "$config_file"

    # Record decision
    atomic_context_decision "Quick mode: minimal config with defaults" "configuration"
    atomic_context_decision "Project name: $project_name" "configuration"

    atomic_success "Configuration collected (quick mode)"
    return 0
}

# Router for Task 002
task_002_config_collection() {
    # Verify jq is available
    if ! command -v jq &>/dev/null; then
        atomic_error "jq is required but not installed"
        return 1
    fi

    case "$SETUP_MODE" in
        document)
            task_002_config_document
            ;;
        guided)
            task_002_config_guided
            ;;
        quick)
            task_002_config_quick
            ;;
        *)
            atomic_error "Unknown setup mode: $SETUP_MODE"
            return 1
            ;;
    esac
}
