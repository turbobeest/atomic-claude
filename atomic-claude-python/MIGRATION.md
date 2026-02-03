# Bash to Python Migration Guide

## Why Python?

The bash implementation hit fundamental limitations that Python eliminates:

| Issue | Bash Problem | Python Solution |
|-------|--------------|-----------------|
| **Array scope** | Associative arrays can't export to subshells | Dicts are regular objects |
| **JSON parsing** | Requires `jq` dependency | Native `json` module |
| **String templates** | Heredoc quoting hell | F-strings |
| **Error handling** | Exit code confusion | Try/except with stack traces |
| **Testing** | Manual bash testing | pytest with coverage |

## Architecture Parity

Python maintains **identical architecture** to bash:

```
main.py              ≡ main.sh
lib/atomic.py        ≡ lib/atomic.sh
lib/phase.py         ≡ lib/phase.sh
lib/provider.py      ≡ lib/provider.sh
lib/memory.py        ≡ lib/memory.sh
lib/task_state.py    ≡ lib/task-state.sh
```

## State File Compatibility

Python reads/writes the **same JSON state files**:
- `.claude/task-state.json`
- `.state/current-task.json`
- `.outputs/*/project-config.json`

Both implementations can coexist and share state.

## Command Compatibility

CLI interface remains identical:

```bash
# Bash
./main.sh run 0

# Python
python main.py run 0
```

## Conversion Strategy

1. ✅ Core lib/ modules converted in parallel
2. ⏳ main.py orchestrator (in progress)
3. ⏳ Phase 0 tasks (next)
4. ⏳ Remaining phases (incremental)

## Testing

```bash
cd atomic-claude-python
pytest tests/
```

## Switching Between Implementations

During transition, both work:

```bash
# Use bash version
./main.sh run 0

# Use Python version
python atomic-claude-python/main.py run 0
```

State files are compatible - you can switch mid-pipeline.

## Performance

Expected improvements:
- Faster startup (no subshell overhead)
- Better error messages (stack traces)
- Easier debugging (pdb vs set -x)
- 70-80% fewer language-level bugs

## Migration Timeline

- **Week 1**: Core lib/ + Phase 0 (CURRENT)
- **Week 2**: Phases 1-4
- **Week 3**: Phases 5-9 + full integration testing
- **Week 4**: Bash deprecation, Python as default
