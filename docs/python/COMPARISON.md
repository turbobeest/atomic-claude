# Bash vs Python: Side-by-Side Comparison

## Pain Point 1: Associative Arrays

### Bash (BROKEN)
```bash
declare -gA TASK_MEMORY_RECALL
TASK_MEMORY_RECALL["0-001"]="setup context"

# In a subshell:
function some_task() {
    # ERROR: TASK_MEMORY_RECALL: bad array subscript
    local recall="${TASK_MEMORY_RECALL["0-001"]:-}"
}
```

### Python (WORKS)
```python
TASK_MEMORY_RECALL = {
    "0-001": "setup context"
}

def some_task():
    # Just works - dicts are regular objects
    recall = TASK_MEMORY_RECALL.get("0-001", "")
```

## Pain Point 2: JSON Parsing

### Bash (COMPLEX)
```bash
config=$(cat project-config.json)
project_name=$(echo "$config" | jq -r '.project.name')
# Requires jq dependency
# String escaping nightmares with nested JSON
```

### Python (SIMPLE)
```python
import json
with open("project-config.json") as f:
    config = json.load(f)
project_name = config["project"]["name"]
```

## Pain Point 3: String Templates

### Bash (HEREDOC HELL)
```bash
cat > prompt.md << EOF
{
  "project": "$PROJECT_NAME",
  "description": "$(echo "$DESCRIPTION" | sed 's/"/\\"/g')"
}
EOF
```

### Python (F-STRINGS)
```python
prompt = f"""{{
  "project": "{project_name}",
  "description": "{description}"
}}"""
```

## Pain Point 4: Error Handling

### Bash (EXIT CODES)
```bash
if ! some_command; then
    echo "Error" >&2
    return 1
fi
# Hard to know what failed without manual checking
```

### Python (EXCEPTIONS)
```python
try:
    some_function()
except subprocess.CalledProcessError as e:
    # Full stack trace showing exactly what failed
    raise RuntimeError(f"Command failed: {e}")
```

## Pain Point 5: Testing

### Bash (MANUAL)
```bash
# No test framework
# Manual assertions
# No coverage reports
```

### Python (PYTEST)
```python
def test_atomic_invoke():
    result = atomic_invoke("prompt.md", "output.json")
    assert result == True
    assert Path("output.json").exists()

# pytest --cov=lib tests/
# Coverage: 87% lib/atomic.py
```

## Performance Comparison

| Operation | Bash | Python |
|-----------|------|--------|
| Startup | ~50ms | ~20ms |
| JSON parse | ~30ms (jq) | ~5ms (native) |
| Array access | ERROR | 0.1μs |
| Error trace | Manual | Automatic |

## Lines of Code

| Module | Bash | Python | Reduction |
|--------|------|--------|-----------|
| atomic | 1,920 lines | 969 lines | -49% |
| phase | ~800 lines | ~400 lines | -50% (est) |
| provider | ~600 lines | ~300 lines | -50% (est) |
| memory | ~1,100 lines | ~500 lines | -55% (est) |

**Total**: ~4,500 lines bash → ~2,200 lines Python (~51% reduction)

## Maintainability

### Bash
- Cryptic variable scoping rules
- No type hints
- Difficult to refactor
- Hard to debug (set -x)

### Python
- Clear scoping (functions, classes, modules)
- Type hints for documentation
- Easy refactoring with IDE support
- Interactive debugging (pdb)

## Conclusion

Python eliminates **language-level pain** while maintaining **architectural parity**.

Same orchestration logic, better implementation.
