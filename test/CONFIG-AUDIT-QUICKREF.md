# Config Audit Quick Reference

## Run Audit

```bash
python3 test/config_audit_runner.py
```

## Test Categories (39 tests)

| Category | Tests | Description |
|----------|-------|-------------|
| Config File Validation | 5 | File existence, JSON validity, duplicates |
| Project Config Schema | 7 | Project, repository, pipeline, agents, LLM |
| Secrets Config Schema | 4 | Provider settings, network mode |
| Environment Variables | 7 | ATOMIC_ROOT, OUTPUT_DIR, UAT_MODE, etc. |
| Provider Config | 5 | Provider names, models, timeouts, chains |
| Default Values | 4 | Minimal config, defaults, optional fields |
| Config Changes | 4 | Reload, validation, error handling |
| Env Propagation | 3 | Subprocess, bash scripts, provider vars |

## Exit Codes

- `0` = All tests passed
- `1` = Tests failed

## Output

**Console**: Color-coded results (✓ green / ✗ red)
**JSON**: `test/reports/config-audit-TIMESTAMP.json`

## Validated Files

- `.outputs/0-setup/project-config.json`
- `.outputs/0-setup/secrets.json`
- `.env` (optional)

## Key Environment Vars

**Required**:
- `ATOMIC_ROOT`
- `ATOMIC_OUTPUT_DIR`

**Optional**:
- `ATOMIC_UAT_MODE`
- `ATOMIC_MEMORY_ENABLED`
- `ATOMIC_OFFLINE_MODE`
- `CLAUDE_PROVIDER`
- `OLLAMA_HOST`

## Valid Provider Names

`anthropic` `aws-bedrock` `ollama` `openai` `google` `azure` `openrouter` `claude-code`

## Valid Project Types

`webapp` `api` `cli` `library` `new-component` `refactor`

## Valid Pipeline Modes

`component` `greenfield` `refactor`

## Valid Network Modes

`cui` `internet` `offline`

## Common Issues

| Issue | Solution |
|-------|----------|
| Config not found | Run Phase 0 first |
| Invalid JSON | Check syntax with `jq . file.json` |
| Invalid provider | Use valid provider name from list |
| ATOMIC_ROOT not set | Run from atomic-claude directory |
| Permission denied | `chmod +x test/config_audit_runner.py` |

## Quick Checks

```bash
# Validate project config JSON
jq . .outputs/0-setup/project-config.json

# Validate secrets config JSON
jq . .outputs/0-setup/secrets.json

# Check environment
echo $ATOMIC_ROOT
echo $ATOMIC_OUTPUT_DIR

# Test config loading
python3 -c "from lib.provider import ProviderManager; pm = ProviderManager(); pm.init(); pm.status()"
```

## CI/CD Integration

```bash
python3 test/config_audit_runner.py || exit 1
```

## See Also

- `CONFIG-AUDIT-README.md` - Full documentation
- `CONFIG-AUDIT-IMPLEMENTATION.md` - Implementation details
- `integration_audit_runner.py` - Integration tests
