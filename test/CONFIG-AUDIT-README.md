# Configuration Audit Runner

Comprehensive validation of all configuration files and environment variable handling for ATOMIC CLAUDE.

## Overview

The Configuration Audit Runner validates:

1. **Config File Validation** - File existence, JSON validity, schema compliance
2. **Project Config Schema** - Project, repository, pipeline, agents, LLM, providers structure
3. **Secrets Config Schema** - Provider settings, network mode, API keys
4. **Environment Variables** - ATOMIC_ROOT, ATOMIC_OUTPUT_DIR, ATOMIC_UAT_MODE, etc.
5. **Provider Configuration** - Provider names, models, timeouts, fallback chains
6. **Default Values** - Minimal config, default application, optional fields
7. **Config Changes** - Reload after modify, validation, error handling
8. **Environment Propagation** - Subprocess access, bash scripts, provider vars

## Usage

### Run All Tests

```bash
python3 test/config_audit_runner.py
```

### Output

The runner provides:
- **Console output** with color-coded results (green ✓ / red ✗)
- **Real-time progress** for each test category
- **Detailed summary** with success rate and category breakdown
- **JSON report** saved to `test/reports/config-audit-TIMESTAMP.json`

### Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

## Test Categories

### 1. Config File Validation (5 tests)

- Verify project-config.json exists
- Verify secrets.json exists
- Validate JSON syntax
- Check for malformed JSON
- Detect duplicate keys

### 2. Project Config Schema (7 tests)

- Verify required fields: name, type
- Validate repository structure
- Validate pipeline configuration
- Validate agents configuration
- Validate LLM settings
- Validate providers structure

### 3. Secrets Config Schema (4 tests)

- Verify provider settings exist
- Validate Bedrock configuration
- Validate Ollama configuration
- Validate network mode

### 4. Environment Variable Handling (7 tests)

- ATOMIC_ROOT is set and valid
- ATOMIC_OUTPUT_DIR is set and valid
- ATOMIC_UAT_MODE handling (true/false/unset)
- ATOMIC_MEMORY_ENABLED handling
- ATOMIC_OFFLINE_MODE handling
- Environment variables accessible

### 5. Provider Configuration (5 tests)

- Provider names are valid (anthropic, aws-bedrock, ollama, etc.)
- Model names follow expected format
- Timeout values are reasonable (> 0, <= 3600)
- Fallback chains are valid
- No conflicting provider settings

### 6. Default Value Handling (4 tests)

- Minimal config is sufficient
- Defaults applied correctly
- Missing optional fields don't break system
- Default provider chain is reasonable

### 7. Config Change Testing (4 tests)

- Config reloaded after modification
- Invalid values detected
- Missing required keys cause errors
- Malformed JSON detected

### 8. Environment Propagation (3 tests)

- Environment variables propagate to subprocesses
- ATOMIC_* vars accessible in bash scripts
- Provider vars accessible in scripts

## Test Fixtures

Test fixtures are automatically created in `test/fixtures/config/`:

- `minimal-project-config.json` - Minimal valid configuration
- `full-project-config.json` - Complete configuration with all fields
- `secrets-config.json` - Provider and API key configuration
- `malformed.json` - Invalid JSON for error testing
- `invalid-project-config.json` - Invalid values for validation testing

## JSON Report Format

```json
{
  "timestamp": "2026-02-04T21:25:30.238176",
  "summary": {
    "total_tests": 39,
    "passed": 39,
    "failed": 0,
    "success_rate": 100.0,
    "duration": 0.13
  },
  "results": [
    {
      "name": "Test Name",
      "category": "Category Name",
      "passed": true,
      "duration": 0.001,
      "error": null
    }
  ]
}
```

## Configuration Files Validated

### project-config.json

```json
{
  "project": {
    "name": "string (required)",
    "type": "webapp|api|cli|library|component|refactor (required)",
    "description": "string (optional)"
  },
  "repository": {
    "default_branch": "string (required)",
    "pr_strategy": "feature-branch|trunk (optional)",
    "commit_strategy": "per-task|per-phase (optional)"
  },
  "pipeline": {
    "mode": "component|greenfield|refactor (required)",
    "skip_phases": "array (optional)",
    "human_gates": "array (optional)"
  },
  "agents": {
    "phase_N": "agent-name|infer|default"
  },
  "llm": {
    "primary_provider": "anthropic|aws-bedrock|ollama",
    "primary_model": "string|null",
    "fast_model": "string|null"
  },
  "providers": {
    "chains": {
      "global": "space-separated provider list",
      "critical": "override for critical tasks",
      "bulk": "override for bulk tasks"
    },
    "ollama": {
      "enabled": boolean,
      "servers": [
        {
          "name": "string",
          "host": "hostname:port",
          "model": "string"
        }
      ]
    }
  }
}
```

### secrets.json

```json
{
  "bedrock_enabled": true,
  "aws_region": "us-gov-west-1",
  "aws_profile": "profile-name",
  "bedrock_model": "model-id",
  "ollama_enabled": true,
  "ollama_host": "localhost:11434",
  "memory_enabled": true,
  "network_mode": "cui|internet|offline"
}
```

## Environment Variables

### Required

- `ATOMIC_ROOT` - Root directory of atomic-claude installation
- `ATOMIC_OUTPUT_DIR` - Output directory (default: `.outputs`)

### Optional

- `ATOMIC_UAT_MODE` - User acceptance testing mode (true/false)
- `ATOMIC_MEMORY_ENABLED` - Enable persistent memory (true/false)
- `ATOMIC_OFFLINE_MODE` - Offline/airgapped mode (true/false)
- `CLAUDE_PROVIDER` - Primary provider (max/api/ollama)
- `OLLAMA_HOST` - Ollama server URL
- `ANTHROPIC_API_KEY` - Anthropic API key
- `AWS_PROFILE` - AWS profile for Bedrock
- `AWS_REGION` - AWS region for Bedrock

## Integration with CI/CD

Add to your CI pipeline:

```bash
# Run configuration audit
python3 test/config_audit_runner.py

# Check exit code
if [ $? -ne 0 ]; then
  echo "Configuration audit failed"
  exit 1
fi
```

## Troubleshooting

### Test Failures

1. **Config File Validation failures** - Check JSON syntax, file permissions
2. **Schema validation failures** - Verify required fields present and types correct
3. **Environment variable failures** - Check environment setup, paths exist
4. **Provider configuration failures** - Validate provider names, model names
5. **Environment propagation failures** - Check subprocess execution, shell env

### Common Issues

**Issue**: "Project config does not exist"
- **Solution**: Run Phase 0 to create initial configuration

**Issue**: "Invalid JSON"
- **Solution**: Check for trailing commas, unclosed braces, invalid escapes

**Issue**: "ATOMIC_ROOT not set"
- **Solution**: Ensure running from atomic-claude directory or set ATOMIC_ROOT env var

**Issue**: "Invalid provider name"
- **Solution**: Use valid provider names: anthropic, aws-bedrock, ollama, openai, google, azure, openrouter

## Development

### Adding New Tests

1. Add test method to appropriate category in `ConfigAuditRunner` class
2. Follow naming convention: `test_descriptive_name`
3. Use assertions to validate conditions
4. Raise `AssertionError` with descriptive message on failure

Example:

```python
def test_new_validation(self):
    """Test that new feature works correctly."""
    fixture = self.fixtures_dir / "test-config.json"
    with open(fixture) as f:
        config = json.load(f)

    assert "required_field" in config, "Missing required_field"
    assert isinstance(config["required_field"], str), "Wrong type"
```

### Test Categories

Add new category by calling `_run_category()` in `run_all_tests()`:

```python
self._run_category("New Category", [
    self.test_first,
    self.test_second,
])
```

## Related Tools

- `test/integration_audit_runner.py` - Integration testing (Python ↔ Bash)
- `scripts/validate-config.sh` - Quick config validation script
- `lib/provider.py` - Provider management and configuration loading

## See Also

- `CLAUDE.md` - Project instructions and architecture
- `docs/CONFIGURATION.md` - Configuration reference
- `initialization/setup.md` - Initial project configuration template
