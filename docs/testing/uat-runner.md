# UAT Runner Documentation

## Overview

The UAT (User Acceptance Test) Runner validates the user experience and interface quality of each phase in the atomic-claude2 pipeline. Unlike functional tests that verify correctness, UAT tests focus on:

- **Clarity**: Are prompts and messages clear and professional?
- **Usability**: Are menus logical and flows intuitive?
- **Formatting**: Is the output readable and well-organized?
- **Wording**: Is the language grammatically correct and appropriate?
- **Visual quality**: Do colors and formatting enhance (not distract from) readability?

## Key Features

### 1. Complete Output Capture
- Captures ALL CLI output including ANSI color codes
- Preserves formatting, colors, and terminal styling
- Records both stdout and stderr

### 2. ANSI to HTML Conversion
- Converts terminal colors to HTML styling
- Generates readable HTML reports
- Preserves the visual experience for review

### 3. Automated Analysis
- **Menu Detection**: Automatically identifies and extracts menu structures
- **Interaction Capture**: Records Q&A flows and prompts
- **Formatting Validation**: Checks line length, indentation, spacing
- **Wording Analysis**: Detects common typos and grammar issues

### 4. Human Review Checklist
- Configurable checklist per phase
- Interactive checkboxes in HTML report
- Space for reviewer notes
- Approve/Reject workflow

### 5. Multiple Scenarios
- Test different execution modes (guided, quick, document)
- Compare UX across scenarios
- Validate consistency

## Architecture

```
tests/
├── runners/
│   └── uat_runner.py           # Main UAT runner class
├── phase_configs/
│   └── phase_XX_tests.json     # Per-phase configuration
├── fixtures/
│   └── phaseXX/
│       └── uat_scenarios/      # Scenario input files
│           ├── guided_mode_inputs.txt
│           ├── quick_mode_inputs.txt
│           └── document_mode_inputs.txt
├── templates/
│   └── uat_report.html         # HTML report template
└── unit/
    └── test_uat_runner.py      # Unit tests for runner

scripts/
└── run_uat.py                  # CLI wrapper
```

## Usage

### Basic Usage

```bash
# Run UAT for Phase 0, default scenario
python scripts/run_uat.py --phase 0 --scenario default

# Run UAT for Phase 0, guided mode
python scripts/run_uat.py --phase 0 --scenario guided

# Run all scenarios for Phase 1
python scripts/run_uat.py --phase 1 --all-scenarios

# Run without opening browser
python scripts/run_uat.py --phase 0 --no-browser
```

### Programmatic Usage

```python
from tests.runners.uat_runner import UATRunner

# Initialize runner
runner = UATRunner()

# Run UAT
report = runner.run_phase_uat(phase_num=0, scenario="guided")

# Save HTML report
output_path = Path("reports/uat_phase00_guided.html")
runner.save_html_report(report, output_path)

# Check results
print(f"Success: {report.success}")
print(f"Duration: {report.duration:.2f}s")
print(f"Menus detected: {len(report.menus)}")
print(f"Interactions: {len(report.interactions)}")
print(f"Formatting issues: {len(report.formatting_issues)}")
```

## Configuration

### Phase Configuration File

Each phase has a configuration file: `tests/phase_configs/phase_XX_tests.json`

```json
{
  "phase": "0-setup",
  "uat": {
    "scenarios": ["guided", "quick", "document"],
    "human_review": true,
    "checklist": [
      "All prompts are clear and professional",
      "Menu options are logical and complete",
      "Error messages are helpful and actionable",
      "Progress indicators work correctly",
      "Colors and formatting enhance readability",
      "No typos or grammatical errors"
    ]
  }
}
```

### Scenario Input Files

Input files simulate user interactions: `tests/fixtures/phaseXX/uat_scenarios/scenario_inputs.txt`

```
# Example: guided_mode_inputs.txt
# Each line represents a user input (Enter key press)

a              # Select option 'a'
y              # Confirm with 'y'
               # Press Enter (empty line)
```

## HTML Report

The generated HTML report includes:

### Header Section
- Phase number and scenario
- Timestamp and duration
- Success/failure status
- Exit code

### Review Checklist
- Interactive checkboxes
- Text areas for notes
- Approve/Reject buttons
- Auto-saves to localStorage

### Automated Analysis
- **Menus Detected**: Lists all menu structures found
- **Interactive Flows**: Shows Q&A sequences
- **Formatting Issues**: Highlights line length, indentation problems
- **Wording Analysis**: Reports typos, grammar issues, tone problems

### Terminal Output
- Complete output with preserved ANSI colors
- Scrollable view
- Monospace font for readability

### Interactive Features
- **Approve Button**: Records approval with checklist JSON in console
- **Reject Button**: Prompts for reason, logs to console
- **Auto-save**: Checklist state saved to browser localStorage
- **Visual Feedback**: Background color changes on approve/reject

## Review Process

### 1. Run UAT

```bash
python scripts/run_uat.py --phase 0 --scenario guided
```

This opens the HTML report in your default browser.

### 2. Review Output

Scroll through the terminal output in the report. Look for:
- Clear, professional wording
- Logical menu structures
- Helpful error messages
- Appropriate use of colors
- Consistent formatting
- Good spacing and alignment

### 3. Check Automated Analysis

Review the automated findings:
- Are the detected menus correct?
- Are all interactions captured?
- Are formatting issues valid concerns?
- Do wording issues need attention?

### 4. Complete Checklist

Go through each checklist item:
- Check the box if the item passes
- Add notes for any issues or concerns
- Be thorough and honest

### 5. Make Decision

Click either:
- **Approve**: If UX quality meets standards
- **Reject**: If improvements are needed (provide reason)

### 6. Extract Results

Open browser console (F12) to see:
- Complete checklist JSON
- Approval/rejection details
- Copy for documentation

## Adding New Scenarios

### 1. Add to Phase Config

Edit `tests/phase_configs/phase_XX_tests.json`:

```json
{
  "uat": {
    "scenarios": ["guided", "quick", "document", "my_new_scenario"]
  }
}
```

### 2. Create Input File

Create `tests/fixtures/phaseXX/uat_scenarios/my_new_scenario_inputs.txt`:

```
# Scenario-specific inputs
# One input per line
```

### 3. Run the Scenario

```bash
python scripts/run_uat.py --phase X --scenario my_new_scenario
```

## Best Practices

### For Test Authors

1. **Test all interaction modes**: Guided, quick, and document modes
2. **Use realistic inputs**: Simulate actual user behavior
3. **Cover edge cases**: Try unusual but valid inputs
4. **Document expectations**: Clear checklist items
5. **Keep scenarios focused**: One scenario per user journey

### For Reviewers

1. **Review with fresh eyes**: Don't skip because it "seems fine"
2. **Check consistency**: Terminology, formatting, tone should be uniform
3. **Think like a user**: Is it intuitive? Would you understand?
4. **Note improvements**: Even if approving, suggest enhancements
5. **Be thorough**: Every prompt, menu, message matters

### For Developers

1. **Run UAT before committing**: Catch UX issues early
2. **Address all rejections**: Fix issues before proceeding
3. **Iterate on feedback**: UAT findings improve the product
4. **Keep checklist updated**: Add items as patterns emerge
5. **Automate where possible**: But always require human review

## Troubleshooting

### Report Doesn't Open

```bash
# Specify output directory explicitly
python scripts/run_uat.py --phase 0 --output-dir ./my-reports

# Then manually open
open ./my-reports/uat_phase00_default.html
```

### ANSI Colors Not Showing

The HTML report converts ANSI codes to HTML styling. If colors aren't showing:
- Check if the output actually contains ANSI codes
- Verify your terminal emulator supports ANSI
- Try running with `FORCE_COLOR=1` environment variable

### Timeout Errors

```bash
# Increase timeout in runner code
# Edit tests/runners/uat_runner.py, line with timeout=600
```

### Checklist Not Saving

The checklist auto-saves to browser localStorage. If it's not working:
- Check browser console for JavaScript errors
- Try a different browser
- Clear localStorage and try again

## Advanced Features

### Custom HTML Template

Create a custom template at `tests/templates/uat_report.html`. Use placeholders:

- `{{PHASE_NUM}}`: Phase number
- `{{SCENARIO}}`: Scenario name
- `{{TIMESTAMP}}`: Execution timestamp
- `{{DURATION}}`: Duration in seconds
- `{{SUCCESS}}`: Success/failure text
- `{{EXIT_CODE}}`: Process exit code
- `{{OUTPUT}}`: Terminal output (with HTML)
- `{{CHECKLIST}}`: Generated checklist HTML
- `{{ANALYSIS}}`: Generated analysis HTML

### Programmatic Report Analysis

```python
from tests.runners.uat_runner import UATRunner

runner = UATRunner()
report = runner.run_phase_uat(0, "guided")

# Access report data
print(f"Menus: {len(report.menus)}")
for menu in report.menus:
    print(f"  Options: {menu.options}")

# Analyze interactions
for interaction in report.interactions:
    print(f"Q: {interaction.question}")
    print(f"A: {interaction.response}")

# Check formatting
for issue in report.formatting_issues:
    print(f"Line {issue.line_num}: {issue.description}")

# Export as JSON
import json
with open('report.json', 'w') as f:
    json.dump(report.to_dict(), f, indent=2)
```

### Integration with CI/CD

```yaml
# .github/workflows/uat.yml
name: UAT Tests

on: [push, pull_request]

jobs:
  uat:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9

      - name: Run UAT
        run: |
          python scripts/run_uat.py --phase 0 --no-browser

      - name: Upload Reports
        uses: actions/upload-artifact@v2
        with:
          name: uat-reports
          path: test/reports/*.html
```

## Unit Testing the UAT Runner

See `tests/unit/test_uat_runner.py` for comprehensive unit tests covering:
- ANSI to HTML conversion
- Menu detection
- Interaction capture
- Formatting analysis
- Wording validation
- Report generation

Run unit tests:

```bash
pytest tests/unit/test_uat_runner.py -v
```

## Future Enhancements

- **Screenshot capture**: Actual terminal screenshots
- **Video recording**: Full session recording
- **Diff view**: Compare scenarios side-by-side
- **Regression detection**: Compare against baseline reports
- **Accessibility checks**: WCAG compliance for output
- **Performance metrics**: Response time analysis
- **Natural language analysis**: AI-powered wording review

## References

- REFACTOR-PLAN.md: Phase 1, UAT Runner section
- tests/runners/uat_runner.py: Implementation
- scripts/run_uat.py: CLI wrapper
- tests/templates/uat_report.html: HTML template
