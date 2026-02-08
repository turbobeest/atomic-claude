# Phase 0 Test Fixtures

Test fixtures and inputs for Phase 0 (Setup) continuity and functional testing.

## Purpose

These fixtures provide prescribed inputs for testing Phase 0 tasks without requiring:
- Interactive user input
- Real LLM API calls
- Manual intervention

## Files

### continuity_inputs.txt

Prescripted inputs for continuity testing. Each line represents an input to be provided when prompted.

Example format:
```
quick
test-project
/tmp/test-project
Python web application
yes
```

### config_samples/

Sample configuration files for different test scenarios:
- `quick_mode.json` - Quick mode configuration
- `guided_mode.json` - Guided mode configuration
- `document_mode.json` - Document mode configuration

### mock_responses/

Mock LLM responses for faster testing:
- `agent_selection.txt` - Mock agent selection response
- `validation.txt` - Mock validation response

## Usage

### Continuity Testing

The continuity runner uses `continuity_inputs.txt` to provide non-interactive inputs:

```bash
python tests/runners/continuity_runner.py 0 --mock
```

### Functional Testing

Functional tests use the fixtures directory for comprehensive scenarios:

```bash
python tests/runners/functional_runner.py 0 --fixtures tests/fixtures/phase00/
```

## Creating New Fixtures

When adding new test scenarios:

1. Create a new subdirectory: `mkdir -p tests/fixtures/phase00/scenario_name`
2. Add required input files
3. Document the scenario in this README
4. Update test configuration in `tests/phase_configs/phase_00_tests.json`

## Notes

- Fixtures should be minimal but representative
- Use realistic values (not "test", "foo", "bar")
- Document any special requirements or dependencies
- Keep fixtures version-controlled and up-to-date
