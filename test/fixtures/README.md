# Test Fixtures

This directory contains sample data and expected outputs for testing atomic-claude2.

---

## Directory Structure

```
test/fixtures/
├── phase00-outputs/          # Sample Phase 0 outputs
│   ├── project-config.json   # Complete project configuration
│   ├── secrets.json          # API keys and secrets
│   └── closeout.json         # Phase completion summary
├── sample-project-configs/   # Sample project configurations
└── README.md                 # This file
```

---

## Phase 0 Outputs

**Directory**: `phase00-outputs/`

Sample outputs from Phase 0 (Setup) for the "TaskFlow API" project.

### Files

**project-config.json**
- Complete project configuration
- Extracted from setup.md
- Includes: project info, repository, sandbox, pipeline, agents, LLM config

**secrets.json**
- API keys configuration
- Provider settings
- UAT mode flags

**closeout.json**
- Phase completion summary
- Tasks completed
- Output files generated
- Validation status

### Usage

**Copy fixtures for testing**:
```bash
# Copy Phase 0 outputs to test environment
mkdir -p .outputs/0-setup
cp test/fixtures/phase00-outputs/* .outputs/0-setup/
```

**Use in tests**:
```python
import json
from pathlib import Path

# Load sample config
fixtures_dir = Path(__file__).parent / "fixtures"
with open(fixtures_dir / "phase00-outputs" / "project-config.json") as f:
    config = json.load(f)
```

---

## Sample Project: TaskFlow API

The fixtures use a sample project called **TaskFlow API**:

**Type**: REST API
**Tech Stack**: Python, FastAPI, PostgreSQL
**Scope**: Task management CRUD operations with authentication

**Features**:
- User authentication (JWT)
- Project organization
- Task CRUD operations
- User management
- RESTful API design

**Infrastructure**:
- Docker containerization
- Kubernetes deployment
- PostgreSQL database
- CI/CD with GitHub Actions

---

## Creating New Fixtures

To create fixtures for other phases:

1. **Run phase interactively**:
   ```bash
   export ATOMIC_TOOL_DEVELOPMENT="true"
   python main.py run <phase_num>
   ```

2. **Copy outputs**:
   ```bash
   mkdir -p test/fixtures/phase0<N>-outputs
   cp .outputs/<N>-<phase-name>/* test/fixtures/phase0<N>-outputs/
   ```

3. **Sanitize data**:
   - Remove real API keys
   - Remove sensitive information
   - Use example data

4. **Document**:
   - Add description to this README
   - Note any special requirements

---

## Fixture Validation

Fixtures should be:
- **Valid JSON**: All JSON files parse correctly
- **Complete**: Include all required fields
- **Realistic**: Represent actual use cases
- **Safe**: No real API keys or sensitive data
- **Documented**: Purpose and usage clear

### Validating Fixtures

```bash
# Validate JSON syntax
for file in test/fixtures/phase00-outputs/*.json; do
  echo "Validating $file..."
  jq empty "$file" && echo "✓ Valid" || echo "✗ Invalid"
done
```

---

## Using Fixtures in Tests

### Unit Tests

```python
import pytest
from pathlib import Path
import json

@pytest.fixture
def sample_phase0_config():
    """Load sample Phase 0 configuration."""
    fixture_path = Path(__file__).parent / "fixtures" / "phase00-outputs" / "project-config.json"
    with open(fixture_path) as f:
        return json.load(f)

def test_config_structure(sample_phase0_config):
    """Test that config has expected structure."""
    assert "extracted" in sample_phase0_config
    assert "project" in sample_phase0_config["extracted"]
    assert sample_phase0_config["extracted"]["project"]["name"] == "TaskFlow API"
```

### Integration Tests

```python
def test_phase1_with_phase0_fixtures(tmp_path):
    """Test Phase 1 with Phase 0 fixtures."""
    # Setup
    output_dir = tmp_path / ".outputs"
    setup_dir = output_dir / "0-setup"
    setup_dir.mkdir(parents=True)

    # Copy fixtures
    import shutil
    fixture_dir = Path("test/fixtures/phase00-outputs")
    for file in fixture_dir.glob("*.json"):
        shutil.copy(file, setup_dir)

    # Run Phase 1
    from phases.phase01 import orchestrator01
    result = orchestrator01.run_phase()

    assert result is True
```

### Continuity Tests

```bash
# Use fixtures for continuity testing
mkdir -p .outputs/0-setup
cp test/fixtures/phase00-outputs/* .outputs/0-setup/

# Run Phase 1 (will use Phase 0 fixtures)
python main.py run 1
```

---

## Future Fixtures

Plan to add:

- [ ] Phase 1 outputs (discovery results)
- [ ] Phase 2 outputs (PRD)
- [ ] Phase 3 outputs (task breakdown)
- [ ] Multiple project types (web app, CLI, library)
- [ ] Different tech stacks
- [ ] Error scenarios
- [ ] Edge cases

---

## Maintenance

- **Update fixtures** when task output formats change
- **Add new fixtures** for new features
- **Validate regularly** with automated tests
- **Document changes** in git commits

---

**Last Updated**: 2026-02-07
**Sample Project**: TaskFlow API
**Fixture Version**: 1.0
