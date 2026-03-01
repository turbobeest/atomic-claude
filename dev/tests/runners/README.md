# Test Runners

This directory contains specialized test runners for validating different aspects of the atomic-claude system.

## Available Runners

### 1. UAT Runner (`uat_runner.py`)

**Purpose:** User Acceptance Testing - validates UX/UI quality

**What it tests:**
- Clarity and professionalism of prompts and messages
- Logic and completeness of menus
- Helpfulness of error messages
- Visual quality (colors, formatting, alignment)
- Grammar and wording
- Interactive flow intuitiveness

**Features:**
- Captures ALL CLI output including ANSI colors
- Converts terminal output to HTML for review
- Automatically detects menus and interactions
- Analyzes formatting and wording quality
- Generates professional HTML reports with review checklists
- Supports multiple scenarios per phase

**Usage:**
```python
from dev.tests.runners.uat_runner import UATRunner

runner = UATRunner()
report = runner.run_phase_uat(phase_num=0, scenario="guided")
runner.save_html_report(report, Path("uat_report.html"))
```

**CLI Wrapper:**
```bash
python scripts/run_uat.py --phase 0 --scenario guided
```

**Documentation:** See `docs/testing/uat-runner.md`

### 2. Continuity Runner (TODO)

**Purpose:** Validates seamless task-to-task flow without terminal errors

**What it will test:**
- Sequential task execution
- Exit codes and error handling
- State transitions between tasks
- Cleanup on task completion
- Orphaned processes/file handles

### 3. Functional Runner (TODO)

**Purpose:** Validates task behavior with 90%+ coverage

**What it will test:**
- All code paths (happy path, edge cases, errors)
- Output correctness against expected results
- State persistence and recovery
- Multiple input scenarios per task
- Code coverage metrics

## Running All Test Runners

```bash
# Run all test runners for Phase 0
python scripts/run_all_tests.py --phase 0

# Run specific runner
python scripts/run_uat.py --phase 0 --scenario guided
```

## Configuration

Test runner configuration is stored in `tests/phase_configs/phase_XX_tests.json`:

```json
{
  "phase": "0-setup",
  "uat": {
    "scenarios": ["guided", "quick", "document"],
    "human_review": true,
    "checklist": ["item1", "item2"]
  },
  "continuity": {
    "timeout_per_task": 120
  },
  "functional": {
    "coverage_target": 0.90
  }
}
```

## Output

All test runners generate reports in `test/reports/`:

- `uat_phaseXX_scenario.html` - UAT HTML reports
- `continuity_phaseXX.json` - Continuity test results
- `functional_phaseXX.json` - Functional test results with coverage

## Development

### Adding a New Runner

1. Create runner class in this directory
2. Implement required interface (run, report generation)
3. Add configuration section to phase configs
4. Create CLI wrapper in `scripts/`
5. Add documentation in `docs/testing/`
6. Write unit tests in `tests/unit/`

### Testing Runners

```bash
# Unit tests for UAT runner
python tests/unit/test_uat_runner.py

# Demo runner
python tests/demo_uat_runner.py
```

## Architecture

```
Test Runner Architecture
------------------------

Input:
  - Phase number
  - Scenario name
  - Configuration

Processing:
  - Execute phase/tasks
  - Capture output
  - Analyze results
  - Validate against criteria

Output:
  - Structured report
  - HTML/JSON/CSV
  - Pass/fail status
  - Detailed analysis
```

## Integration with Phase End Gates

Each phase must pass all three test runners before proceeding:

1. **Continuity Test** - No terminal errors, all tasks complete
2. **UAT** - User approves UX quality
3. **Functional Test** - 90%+ coverage, all assertions pass

This ensures quality at every phase boundary.

## References

- REFACTOR-PLAN.md - Phase 1, Test Runners section
- docs/testing/uat-runner.md - UAT documentation
- tests/phase_configs/ - Per-phase configuration
- tests/fixtures/ - Test fixtures and inputs
