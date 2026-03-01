# Phase Test Configurations

This directory contains test configuration files for each phase of the atomic-claude pipeline.

## Configuration Format

Each phase has a configuration file: `phase_NN_tests.json`

```json
{
  "phase": "N-phase-name",
  "name": "Phase N: Phase Name",
  "tasks": ["001", "002", "003", ...],
  "continuity": {
    "inputs": "fixtures/phaseNN/continuity_inputs.txt",
    "timeout_per_task": 60
  },
  "uat": {
    "scenarios": ["guided", "quick", "document"],
    "human_review": true
  },
  "functional": {
    "fixtures": "fixtures/phaseNN/",
    "coverage_target": 0.90,
    "scenarios": ["happy_path", "edge_cases", "error_handling"]
  }
}
```

## Configuration Fields

### Top Level

- `phase` (string): Phase identifier (e.g., "0-setup", "2-prd")
- `name` (string): Human-readable phase name
- `tasks` (array): List of task IDs to execute in order

### Continuity Section

Configuration for the Continuity Test Runner:

- `inputs` (string): Path to inputs file for mocked/prescribed inputs
- `timeout_per_task` (integer): Timeout in seconds for each task (default: 60)

### UAT Section

Configuration for the User Acceptance Test Runner (TBD):

- `scenarios` (array): List of test scenarios to run
  - `"guided"`: Interactive guided mode with Q&A
  - `"quick"`: Quick mode with defaults
  - `"document"`: Document mode with initialization file
- `human_review` (boolean): Whether human review is required

### Functional Section

Configuration for the Functional Test Runner (TBD):

- `fixtures` (string): Path to fixtures directory
- `coverage_target` (float): Target code coverage (0.0-1.0)
- `scenarios` (array): Test scenarios to execute
  - `"happy_path"`: Normal execution path
  - `"edge_cases"`: Boundary conditions and edge cases
  - `"error_handling"`: Error conditions and recovery

## Usage

### Continuity Test

```bash
# Run continuity test for Phase 0
python tests/runners/continuity_runner.py 0

# Run with custom config
python tests/runners/continuity_runner.py 0 --config tests/phase_configs/phase_00_tests.json

# Run with mocked inputs (faster, no LLM calls)
python tests/runners/continuity_runner.py 0 --mock
```

### UAT Test (TBD)

```bash
# Run UAT for Phase 0
python tests/runners/uat_runner.py 0

# Run specific scenario
python tests/runners/uat_runner.py 0 --scenario guided
```

### Functional Test (TBD)

```bash
# Run functional tests for Phase 0
python tests/runners/functional_runner.py 0

# Run specific scenario
python tests/runners/functional_runner.py 0 --scenario happy_path

# Check coverage
python tests/runners/functional_runner.py 0 --coverage-report
```

## Creating New Phase Configs

When adding a new phase:

1. Copy an existing config: `cp phase_00_tests.json phase_NN_tests.json`
2. Update phase ID, name, and task list
3. Adjust timeouts and scenarios as needed
4. Create fixtures directory: `mkdir -p tests/fixtures/phaseNN`
5. Add test inputs/fixtures as needed

## Test Execution Order

Phase-end tests should be executed in this order:

1. **Continuity Test**: Ensures all tasks execute without crashes
2. **UAT Test**: Validates user experience and UI quality
3. **Functional Test**: Confirms behavior and coverage targets

All three tests must pass before proceeding to the next phase implementation.

## See Also

- `docs/testing/continuity-runner.md` - Continuity test documentation
- `docs/testing/uat-runner.md` - UAT documentation (TBD)
- `docs/testing/functional-runner.md` - Functional test documentation (TBD)
- `REFACTOR-PLAN.md` - Overall refactor plan with testing strategy
