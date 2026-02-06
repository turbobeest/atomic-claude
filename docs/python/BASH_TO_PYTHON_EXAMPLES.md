# Bash to Python Conversion Examples

This document shows side-by-side examples of how bash patterns were converted to Python.

## 1. JSON Escaping

### Bash
```bash
atomic_json_escape() {
    local input="$1"
    # Escape backslashes first (must be first!)
    input="${input//\\/\\\\}"
    # Escape double quotes
    input="${input//\"/\\\"}"
    # Escape newlines
    input="${input//$'\n'/\\n}"
    # Escape tabs
    input="${input//$'\t'/\\t}"
    # Escape carriage returns
    input="${input//$'\r'/\\r}"
    echo "$input"
}
```

### Python
```python
def atomic_json_escape(text: str) -> str:
    """Escape a string for safe inclusion in JSON."""
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    text = text.replace("\n", "\\n")
    text = text.replace("\t", "\\t")
    text = text.replace("\r", "\\r")
    return text
```

## 2. Configuration Loading

### Bash
```bash
atomic_get_primary_model() {
    local project_config="$ATOMIC_OUTPUT_DIR/0-setup/project-config.json"

    if [[ -f "$project_config" ]]; then
        local primary_model
        primary_model=$(jq -r '.extracted.llm.primary_model // empty' "$project_config" 2>/dev/null)

        if [[ -n "$primary_model" && "$primary_model" != "null" ]]; then
            echo "$primary_model"
            return 0
        fi
    fi

    echo "$CLAUDE_MODEL"
}
```

### Python
```python
def atomic_get_primary_model() -> str:
    """Get the primary model from project config or fallback to default."""
    project_config = Path(ATOMIC_OUTPUT_DIR) / "0-setup" / "project-config.json"

    if project_config.exists():
        try:
            with open(project_config) as f:
                config = json.load(f)
                model = config.get("extracted", {}).get("llm", {}).get("primary_model")
                if model:
                    return model
        except Exception:
            pass

    return CLAUDE_MODEL
```

## 3. Timeout Implementation

### Bash
```bash
_atomic_timeout() {
    local timeout_duration="$1"
    shift

    # Check if native timeout command exists
    if command -v timeout &>/dev/null; then
        timeout "$timeout_duration" "$@"
        return $?
    fi

    # Fallback: bash-native timeout implementation
    (
        "$@" &
        local cmd_pid=$!

        # Start timeout monitor
        (
            sleep "$timeout_duration"
            kill -TERM "$cmd_pid" 2>/dev/null
            sleep 1
            kill -KILL "$cmd_pid" 2>/dev/null
        ) &
        local monitor_pid=$!

        wait "$cmd_pid" 2>/dev/null
        local exit_code=$?

        kill -TERM "$monitor_pid" 2>/dev/null
        wait "$monitor_pid" 2>/dev/null

        exit $exit_code
    )
    return $?
}
```

### Python
```python
def atomic_timeout(timeout_sec: int, args: List[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command with timeout (cross-platform)."""
    return subprocess.run(
        args,
        timeout=timeout_sec,
        **kwargs
    )
```

## 4. State Management

### Bash
```bash
atomic_state_set() {
    local key="$1"
    local value="$2"
    local state_file="$ATOMIC_STATE_DIR/session.json"
    local tmp_file
    tmp_file=$(atomic_mktemp) || { echo "ERROR: Failed to create temp file" >&2; return 1; }

    if ! jq ".$key = $value" "$state_file" > "$tmp_file" 2>/dev/null; then
        echo "ERROR: jq failed in atomic_state_set for key: $key" >&2
        rm -f "$tmp_file" 2>/dev/null
        return 1
    fi

    if [[ ! -s "$tmp_file" ]] || ! jq empty "$tmp_file" 2>/dev/null; then
        echo "ERROR: Invalid JSON output in atomic_state_set" >&2
        rm -f "$tmp_file" 2>/dev/null
        return 1
    fi

    mv "$tmp_file" "$state_file"
}
```

### Python
```python
def atomic_state_set(key: str, value: Any) -> bool:
    """Set a value in session state."""
    state_file = Path(ATOMIC_STATE_DIR) / "session.json"
    try:
        with open(state_file) as f:
            state = json.load(f)
        state[key] = value
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except Exception as e:
        atomic_error(f"Failed to set state: {e}")
        return False
```

## 5. Task Header

### Bash
```bash
atomic_task_header() {
    local description="$1"
    local provider="$2"
    local model="$3"
    local role="${4:-}"
    local timeout="$5"
    # ... (50+ lines of complex logic)

    # Write status JSON
    cat > "$status_file" << EOF
{
  "active": true,
  "description": "$desc_escaped",
  "provider": "$provider_escaped",
  "model": "$model_escaped",
  "timestamp": "$(date -Iseconds)"
}
EOF

    echo ""
    echo -e "  ${CYAN}▶${NC} $description ${DIM}($provider/$model)${NC}"
}
```

### Python
```python
def atomic_task_header(
    description: str,
    provider: str,
    model: str,
    role: str,
    timeout: int,
    prompt_source: str,
    output_file: str,
    ollama_host: str = ""
) -> None:
    """Print unified task header and write status JSON."""
    # ... (logic here)

    status = {
        "active": True,
        "description": description,
        "provider": provider,
        "model": model,
        "timestamp": datetime.now().isoformat()
    }

    with open(status_file, 'w') as f:
        json.dump(status, f, indent=2)

    print()
    print(f"  {C.CYAN}▶{C.NC} {description} {C.DIM}({provider}/{model}){C.NC}")
```

## 6. Command Building

### Bash
```bash
_atomic_build_invoke_cmd() {
    local prompt="$1"
    local model="$2"
    local provider="$3"
    local ollama_host="$4"

    # Escape prompt for shell
    local escaped_prompt
    escaped_prompt=$(printf '%s' "$prompt" | sed "s/'/'\\\\''/g")

    # BEDROCK mode
    if [[ "${CLAUDE_CODE_USE_BEDROCK:-}" == "1" || "$provider" == "bedrock" ]]; then
        local cmd="cd '${escaped_atomic_root}' && claude"
        cmd="${cmd} -p '${escaped_prompt}'"
        cmd="${cmd} --dangerously-skip-permissions"
        cmd="${cmd} --output-format text"
        cmd="${cmd} --max-turns 1"
        printf '%s\n' "$cmd"
        return
    fi

    # ... more cases
}
```

### Python
```python
def _atomic_build_invoke_cmd(
    prompt: str,
    model: str,
    provider: str,
    ollama_host: str
) -> str:
    """Build the invocation command for Claude CLI."""
    # Escape prompt for shell
    escaped_prompt = prompt.replace("'", "'\\''")

    # BEDROCK mode
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1" or provider == "bedrock":
        cmd = f"cd '{ATOMIC_ROOT}' && claude"
        cmd += f" -p '{escaped_prompt}'"
        cmd += " --dangerously-skip-permissions"
        cmd += " --output-format text"
        cmd += " --max-turns 1"
        return cmd

    # ... more cases
```

## 7. JSON Extraction

### Bash
```bash
atomic_extract_json() {
    local input_file="$1"
    local output_file="$2"
    local tmp_file="${output_file}.tmp.$$"

    # Try to find JSON block
    if grep -q '```json' "$input_file"; then
        sed -n '/```json/,/```/p' "$input_file" | sed '1d;$d' > "$tmp_file"
    elif grep -q '^{' "$input_file"; then
        cp "$input_file" "$tmp_file"
    else
        atomic_error "No JSON found in output"
        rm -f "$tmp_file"
        return 1
    fi

    # Validate
    if jq . "$tmp_file" > /dev/null 2>&1; then
        mv "$tmp_file" "$output_file"
        atomic_success "JSON extracted and validated"
        return 0
    else
        atomic_error "Extracted content is not valid JSON"
        rm -f "$tmp_file"
        return 1
    fi
}
```

### Python
```python
def atomic_extract_json(input_file: str, output_file: str) -> bool:
    """Extract JSON from mixed Claude output."""
    try:
        content = Path(input_file).read_text()

        # Try to find JSON block
        json_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1)
        elif content.strip().startswith('{'):
            json_content = content
        else:
            atomic_error("No JSON found in output")
            return False

        # Validate
        parsed = json.loads(json_content)
        with open(output_file, 'w') as f:
            json.dump(parsed, f, indent=2)

        atomic_success("JSON extracted and validated")
        return True
    except Exception as e:
        atomic_error(f"JSON extraction failed: {e}")
        return False
```

## 8. File Validation

### Bash
```bash
atomic_validate_files() {
    local missing=()

    for file in "$@"; do
        if [[ ! -f "$file" ]]; then
            missing+=("$file")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        atomic_error "Missing required files:"
        for f in "${missing[@]}"; do
            echo "  - $f"
        done
        return 1
    fi

    atomic_success "All required files present"
    return 0
}
```

### Python
```python
def atomic_validate_files(*files: str) -> bool:
    """Check if required files exist."""
    missing = [f for f in files if not Path(f).exists()]

    if missing:
        atomic_error("Missing required files:")
        for f in missing:
            print(f"  - {f}")
        return False

    atomic_success("All required files present")
    return True
```

## 9. Provider Config Loading

### Bash
```bash
_atomic_load_provider_config() {
    local config_file="$ATOMIC_ROOT/config/models.json"

    if [[ ! -f "$config_file" ]]; then
        return 0
    fi

    # Validate JSON
    if ! jq -e '.' "$config_file" >/dev/null 2>&1; then
        atomic_warn "Config file is invalid JSON: $config_file - using defaults"
        return 0
    fi

    # Load default provider
    local default_provider
    default_provider=$(jq -r '.providers.default_provider // empty' "$config_file" 2>/dev/null)
    [[ -n "$default_provider" ]] && CLAUDE_PROVIDER="$default_provider"

    # Load role-to-provider mapping
    local role_primary role_fast role_gardener role_heavyweight
    role_primary=$(jq -r '.providers.role_routing.primary // empty' "$config_file" 2>/dev/null)
    role_fast=$(jq -r '.providers.role_routing.fast // empty' "$config_file" 2>/dev/null)

    [[ -n "$role_primary" ]] && PROVIDER_ROLE_MAP[primary]="$role_primary"
    [[ -n "$role_fast" ]] && PROVIDER_ROLE_MAP[fast]="$role_fast"

    _ATOMIC_CONFIG_LOADED=true
}
```

### Python
```python
def _atomic_load_provider_config() -> None:
    """Load provider configuration from config/models.json."""
    global CLAUDE_PROVIDER, PROVIDER_ROLE_MAP, _ATOMIC_CONFIG_LOADED

    config_file = Path(ATOMIC_ROOT) / "config" / "models.json"

    if not config_file.exists():
        _ATOMIC_CONFIG_LOADED = True
        return

    try:
        with open(config_file) as f:
            config = json.load(f)

        # Load default provider
        default_provider = config.get("providers", {}).get("default_provider")
        if default_provider:
            CLAUDE_PROVIDER = default_provider

        # Load role-to-provider mapping
        role_routing = config.get("providers", {}).get("role_routing", {})
        for role, provider in role_routing.items():
            if provider:
                PROVIDER_ROLE_MAP[role] = provider

        _ATOMIC_CONFIG_LOADED = True
    except Exception as e:
        atomic_warn(f"Failed to load config: {e}")
        _ATOMIC_CONFIG_LOADED = True
```

## 10. Main Invocation Logic

### Bash
```bash
atomic_invoke() {
    local prompt_source="$1"
    local output_file="$2"
    local description="$3"
    shift 3

    # Parse options
    local model
    model=$(atomic_get_primary_model 2>/dev/null || echo "$CLAUDE_MODEL")
    local provider="$CLAUDE_PROVIDER"
    local timeout="$CLAUDE_TIMEOUT"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --model=*) model="${1#*=}" ;;
            --provider=*) provider="${1#*=}" ;;
            --timeout=*) timeout="${1#*=}" ;;
            *) atomic_warn "Unknown option: $1" ;;
        esac
        shift
    done

    # Build invocation command
    local invoke_cmd
    invoke_cmd=$(_atomic_build_invoke_cmd "$prompt_content" "$model" "$provider" "$ollama_host")

    # Execute with timeout
    if _atomic_timeout "$timeout" bash -c "$invoke_cmd" < /dev/null > "$output_file" 2>"${output_file}.err"; then
        atomic_success "Claude completed task"
        return 0
    else
        atomic_error "Claude task failed"
        return 1
    fi
}
```

### Python
```python
def atomic_invoke(
    prompt_source: str,
    output_file: str,
    description: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    timeout: Optional[int] = None,
    **kwargs
) -> bool:
    """Core atomic Claude invocation function."""
    # Set defaults
    if model is None:
        model = atomic_get_primary_model()
    if provider is None:
        provider = CLAUDE_PROVIDER
    if timeout is None:
        timeout = CLAUDE_TIMEOUT

    # Build invocation command
    invoke_cmd = _atomic_build_invoke_cmd(prompt_content, model, provider, ollama_host)

    # Execute with timeout
    try:
        result = subprocess.run(
            ["bash", "-c", invoke_cmd],
            stdin=subprocess.DEVNULL,
            stdout=open(output_file, 'w'),
            stderr=open(f"{output_file}.err", 'w'),
            timeout=timeout
        )

        if result.returncode == 0:
            atomic_success("Claude completed task")
            return True
        else:
            atomic_error("Claude task failed")
            return False
    except subprocess.TimeoutExpired:
        atomic_error("Claude task timed out")
        return False
```

## Key Patterns Summary

| Pattern | Bash | Python |
|---------|------|--------|
| **Variable assignment** | `local var="value"` | `var = "value"` |
| **Function return** | `echo "result"` | `return "result"` |
| **Exit codes** | `return 0/1` | `return True/False` |
| **Conditionals** | `[[ condition ]]` | `if condition:` |
| **Loops** | `for x in $list` | `for x in list:` |
| **Command substitution** | `$(command)` | `subprocess.run()` |
| **JSON parsing** | `jq` | `json.load()` |
| **String manipulation** | `${var//find/replace}` | `var.replace()` |
| **File checks** | `[[ -f "$file" ]]` | `Path(file).exists()` |
| **Arrays** | `local arr=()` | `arr: List = []` |
| **Associative arrays** | `declare -A map` | `map: Dict = {}` |
| **Error output** | `>&2` | `file=sys.stderr` |
| **Temp files** | `mktemp` | `tempfile.mkstemp()` |

## Benefits Summary

1. **No External Dependencies**: No need for jq, realpath, etc.
2. **Better Error Handling**: Try/except instead of complex exit code checking
3. **Type Safety**: Type hints catch errors at development time
4. **Native Data Structures**: Dicts and lists instead of string manipulation
5. **Cleaner Code**: ~70% reduction in line count
6. **Better Testing**: Can use pytest, unittest, etc.
7. **Cross-Platform**: Works on Windows natively
8. **IDE Support**: Autocomplete, inline docs, refactoring tools
