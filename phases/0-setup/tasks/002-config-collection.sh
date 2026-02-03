#!/usr/bin/env bash
#
# Task 002: Config Collection
# Parses initialization/setup.md with Claude to extract project configuration
#
# Input: initialization/setup.md (validated by Task 001)
# Output: .outputs/0-setup/project-config.json with extracted configuration
#

task_002_config_collection() {
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

        # Drain any buffered stdin
        while read -t 0.01 -n 1 _discard 2>/dev/null; do :; done

        while true; do
            if [[ -n "$default_path" ]]; then
                read -e -p "  Setup file path [$default_path]: " SETUP_FILE_PATH || true
                SETUP_FILE_PATH=${SETUP_FILE_PATH:-$default_path}
            else
                read -e -p "  Setup file path: " SETUP_FILE_PATH || true
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

    # Read llm-preferences.md if it exists
    local llm_prefs_content=""
    if [[ -f "$setup_dir/llm-preferences.md" ]]; then
        atomic_substep "Reading LLM preferences: $setup_dir/llm-preferences.md"
        llm_prefs_content=$(cat "$setup_dir/llm-preferences.md")
    fi

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
        atomic_substep "Reading reference documents from setup.md..."
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

    # Auto-scan for common reference files in project root
    local auto_refs=()
    for candidate in \
        "$ATOMIC_ROOT/README.md" \
        "$ATOMIC_ROOT/WHITEPAPER.md" \
        "$ATOMIC_ROOT/DESIGN.md" \
        "$ATOMIC_ROOT/ARCHITECTURE.md" \
        "$ATOMIC_ROOT/SPEC.md" \
        "$ATOMIC_ROOT/docs/README.md" \
        "$ATOMIC_ROOT/docs/design.md" \
        "$ATOMIC_ROOT/docs/architecture.md"; do
        if [[ -f "$candidate" ]]; then
            auto_refs+=("$candidate")
        fi
    done

    if [[ ${#auto_refs[@]} -gt 0 ]]; then
        atomic_substep "Auto-detected reference documents..."
        for ref in "${auto_refs[@]}"; do
            # Skip if already included from setup.md
            if [[ "$reference_content" != *"$ref"* ]]; then
                local ref_name="${ref#$ATOMIC_ROOT/}"
                atomic_substep "  Found: $ref_name"
                reference_content+="
=== $ref_name ===
$(head -500 "$ref" 2>/dev/null || true)

"
            fi
        done
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

CRITICAL: Output ONLY raw JSON. Do NOT use markdown code fences.
Do NOT wrap in ```json or ```.
Start your response with `{` and end with `}`.
No explanation text before or after.

## Extraction Rules

1. **Explicit values**: Use the exact value from the setup file
2. **"infer" fields**: Analyze reference materials (provided below) to derive a project-specific value.
   - CRITICAL: If no reference materials are provided, use the directory name for project name and use `null` for description/goal
   - NEVER invent or hallucinate project details - only extract from provided materials
3. **"default [X]" fields**: Use the literal value X shown in brackets
4. **"detect" fields**: Use the auto-detected values provided below
5. **Missing required values**: Use `null` (do NOT invent values)
6. **Malformed input**: Extract what you can, use defaults for the rest

## Edge Cases

| Situation | Response |
|-----------|----------|
| Setup file is mostly empty | Use defaults for all fields, note in constraints |
| No reference materials for "infer" | Use directory name for project.name, `null` for project.description and project.primary_goal |
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
    "network_mode": "cui|internet",
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
  "providers": {
    "chains": {
      "global": "string (space-separated provider list)",
      "critical": "string or null (override for critical tasks)",
      "bulk": "string or null (override for bulk tasks)",
      "quick": "string or null (override for quick tasks)"
    },
    "routing": {
      "critical": "primary|ollama",
      "bulk": "primary|ollama",
      "background": "primary|ollama"
    },
    "ollama": {
      "enabled": boolean,
      "servers": [{"name": "string", "host": "string", "model": "string", "max_context": number}],
      "failover": boolean,
      "health_check": boolean
    },
    "fallback": {
      "api_to_ollama": boolean,
      "ollama_to_api": boolean,
      "offline_mode": boolean
    }
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
    "network_mode": "cui",
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
  "providers": {
    "chains": {
      "global": "claude-code anthropic aws-bedrock ollama",
      "critical": null,
      "bulk": null,
      "quick": null
    },
    "routing": {
      "critical": "primary",
      "bulk": "primary",
      "background": "primary"
    },
    "ollama": {
      "enabled": false,
      "servers": [],
      "failover": true,
      "health_check": true
    },
    "fallback": {
      "api_to_ollama": false,
      "ollama_to_api": true,
      "offline_mode": false
    }
  },
  "gardener": {"model": "infer", "threshold_percent": 75, "fallback_chain": [], "preserve_recent_exchanges": 4, "preserve_opening": true},
  "constraints": {"technical": ["TypeScript", "PostgreSQL"], "infrastructure": "AWS", "compliance": null, "dependencies": ["express", "pg"]}
}

## Setup Content (setup.md):

PROMPT_SCHEMA

    echo "$setup_content" >> "$prompt_file"

    if [[ -n "$llm_prefs_content" ]]; then
        echo "" >> "$prompt_file"
        echo "## LLM Preferences (llm-preferences.md):" >> "$prompt_file"
        echo "$llm_prefs_content" >> "$prompt_file"
    fi

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

    # Invoke Claude to extract (use default model from environment/config)
    # No model override - let the system use what's available (Claude Max/API/Bedrock/Ollama)
    if atomic_invoke "$prompt_file" "$extracted_file" "Extract configuration from setup"; then
        # Check if response has markdown fences (common LLM behavior)
        if grep -q '```json' "$extracted_file"; then
            atomic_substep "Removing markdown code fences..."
            sed -n '/```json/,/```/p' "$extracted_file" | sed '1d;$d' > "${extracted_file}.clean"
            mv "${extracted_file}.clean" "$extracted_file"
        fi

        # Now validate JSON
        if ! jq . "$extracted_file" > /dev/null 2>&1; then
            atomic_error "Failed to parse extracted JSON"
            jq . "$extracted_file" 2>&1 | head -5
            return 1
        fi

        atomic_success "Configuration extracted successfully"

        # Merge into main config
        local tmp=$(atomic_mktemp)
        jq -s '.[0] * {extracted: .[1]}' "$config_file" "$extracted_file" > "$tmp" && mv "$tmp" "$config_file"
    else
        atomic_error "Setup extraction failed"

        # Offer retry option
        echo ""
        echo -e "  ${YELLOW}Extraction failed. Would you like to:${NC}"
        echo -e "  ${GREEN}[r]${NC} Retry (edit setup.md and try again)"
        echo -e "  ${RED}[q]${NC} Quit"
        echo ""
    atomic_drain_stdin
        read -e -p "  Choice [r]: " fallback_choice || true
        fallback_choice=${fallback_choice:-r}

        case "$fallback_choice" in
            q|Q)
                atomic_error "Setup aborted by user"
                return 1
                ;;
            *)
                # Retry - prompt user to edit and try again
                atomic_info "Please edit your setup.md file and press Enter to retry"
                atomic_drain_stdin
                read -e -p "  Press Enter when ready... " || true
                SETUP_FILE_PATH=""
                task_002_config_collection
                return $?
                ;;
        esac
    fi

    # Record successful extraction
    atomic_context_decision "Config extracted from initialization files successfully" "configuration"
    atomic_context_artifact "extracted_config" "$extracted_file" "Extracted configuration from setup"

    return 0
}
