# Output Validation Audit Runner

## Overview

The Output Validation Audit Runner validates all output files have correct structure and content after a UAT run. It performs comprehensive checks across all phases to ensure the ATOMIC CLAUDE pipeline generated valid, complete outputs.

## Location

```
/Users/jamesterbeest/dev/atomic-claude2/test/output_audit_runner.py
```

## Features

### 1. File Existence Checks
- Verifies all required files exist for each phase
- Checks for optional files (info level if missing)
- Validates phase directory structure
- Special check for PRD.md in `docs/prd/` or `.outputs/2-prd/`

### 2. JSON Validation
- Ensures all JSON files are parseable
- Validates file is not empty
- Schema validation for key files:
  - `project-config.json`: requires name, type, tech_stack
  - `closeout.json`: requires phase_id, phase_name, status, completed_at
  - `secrets.json`: checks not empty
  - `tasks.json`: validates structure

### 3. Markdown Validation
- Checks markdown files are not empty
- Validates basic markdown syntax
- **PRD.md Special Validation**: Ensures all 15 sections are present (## 0. through ## 14.)
- Detects corrupted markdown syntax

### 4. File Size Sanity
- Checks for 0-byte files
- Flags files > 10MB (potential runaway generation)
- Validates minimum sizes:
  - JSON: at least 10 bytes
  - Markdown: at least 50 bytes

### 5. Closeout Validation
- Ensures all phases have closeout.json
- Validates closeout structure
- Checks for completed_at timestamp
- Validates timestamp format
- Verifies tasks list matches expected count

## Usage

### Basic Usage

```bash
python3 test/output_audit_runner.py
```

This will:
- Check `.outputs/` directory (default)
- Save report to `test/reports/`
- Exit with code 0 (success) or 1 (failure)

### Custom Paths

```bash
python3 test/output_audit_runner.py \
  --outputs-dir /path/to/.outputs \
  --report-dir /path/to/reports
```

### After UAT Run

```bash
# Run UAT test
python test/uat_runner.py

# Validate outputs
python3 test/output_audit_runner.py --outputs-dir .outputs
```

### In CI/CD Pipeline

```bash
#!/bin/bash
# run-validation.sh

# Run the audit
if python3 test/output_audit_runner.py --outputs-dir .outputs; then
    echo "✓ Output validation passed"
    exit 0
else
    echo "✗ Output validation failed"
    exit 1
fi
```

## Output

### Console Report

The audit runner displays:
- Real-time progress for each validation category
- Summary statistics (total checks, pass/fail count, pass rate)
- Issues by severity (critical, error, warning, info)
- Detailed critical and error issues
- Overall pass/fail status

### JSON Report

Detailed report saved to `test/reports/output-audit-YYYYMMDD-HHMMSS.json`:

```json
{
  "timestamp": "2026-02-04T21:19:51.349834",
  "outputs_dir": "/path/to/.outputs",
  "summary": {
    "total_checks": 178,
    "passed_checks": 138,
    "failed_checks": 3,
    "pass_rate": "77.5%"
  },
  "issues_by_severity": {
    "critical": 0,
    "error": 3,
    "warning": 25,
    "info": 11
  },
  "issues_by_category": {
    "file_existence": 14,
    "json_validation": 1,
    "markdown": 6,
    "size": 8,
    "closeout": 10
  },
  "issues": [
    {
      "severity": "error",
      "category": "file_existence",
      "message": "Required file missing: closeout.json",
      "file_path": "/path/to/.outputs/1-discovery/closeout.json",
      "details": null
    }
  ]
}
```

## Issue Severity Levels

| Severity | Description | Exit Code Impact |
|----------|-------------|------------------|
| **critical** | Blocks pipeline execution | Causes exit 1 |
| **error** | Invalid output, data corruption | Causes exit 1 |
| **warning** | Missing optional files, minor issues | No exit code impact |
| **info** | Informational, no action needed | No exit code impact |

## Phase-Specific Expectations

### Phase 0: Setup
**Required**: `project-config.json`, `secrets.json`
**Optional**: `closeout.json`, `extracted-config.json`

### Phase 1: Discovery
**Required**: `closeout.json`
**Optional**: `selected-agents.json`, `discovery-report.json`

### Phase 2: PRD
**Required**: `closeout.json`
**Optional**: `PRD.md`, `prd-interview.json`
- PRD.md must have 15 sections (## 0. through ## 14.)

### Phase 3: Tasking
**Required**: `closeout.json`
**Optional**: `tasks.json`

### Phase 4: Specification
**Required**: `closeout.json`
**Optional**: `openspec.json`

### Phase 5: Implementation
**Required**: `closeout.json`

### Phase 6: Code Review
**Required**: `closeout.json`
**Optional**: `review-report.md`

### Phase 7: Integration
**Required**: `closeout.json`
**Optional**: `test-results.json`

### Phase 8: Deployment Prep
**Required**: `closeout.json`
**Optional**: `deployment-plan.md`

### Phase 9: Release
**Required**: `closeout.json`
**Optional**: `release-notes.md`

## Common Issues

### Empty JSON Files
```
[ERROR] Empty JSON file
File: .outputs/2-prd/prompts/guardian-gen-4-report.json
```
**Fix**: Check why the file was created but not populated. Likely LLM invocation failure.

### Missing Closeout
```
[ERROR] Required file missing: closeout.json
File: .outputs/1-discovery/closeout.json
```
**Fix**: Phase did not complete successfully. Check phase logs.

### Invalid JSON
```
[CRITICAL] Invalid JSON: Expecting value: line 1 column 1 (char 0)
File: .outputs/0-setup/project-config.json
```
**Fix**: JSON parsing error. File is corrupted or incomplete.

### Missing PRD Sections
```
[WARNING] PRD missing 3 section(s): ## 10., ## 11., ## 12.
File: docs/prd/PRD.md
```
**Fix**: PRD generation incomplete. Re-run Phase 2 or manually add sections.

## Integration with Test Suite

### Python Test Integration

```python
import subprocess
import sys

def test_output_validation():
    """Test that all outputs are valid after UAT run."""
    result = subprocess.run(
        ['python3', 'test/output_audit_runner.py', '--outputs-dir', '.outputs'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Output validation failed:\n{result.stderr}"
```

### Bash Test Integration

```bash
#!/bin/bash
# test-pipeline-outputs.sh

echo "Running output validation audit..."

if python3 test/output_audit_runner.py --outputs-dir .outputs; then
    echo "✓ All outputs valid"
    exit 0
else
    echo "✗ Output validation failed"
    cat test/reports/output-audit-*.json | tail -n 50
    exit 1
fi
```

## Class Structure

### `OutputAuditRunner`
Main audit runner class with validation methods:

```python
class OutputAuditRunner:
    def check_file_existence(self) -> ValidationResult
        """Check that expected files exist for each phase."""

    def validate_json_files(self) -> ValidationResult
        """Validate all JSON files are parseable and have correct schema."""

    def validate_markdown_files(self) -> ValidationResult
        """Validate markdown files structure."""

    def check_file_sizes(self) -> ValidationResult
        """Check file sizes are within reasonable bounds."""

    def validate_closeouts(self) -> ValidationResult
        """Validate all closeout files."""

    def run(self) -> AuditReport
        """Run all validation checks."""
```

### `ValidationResult`
Individual check result:

```python
@dataclass
class ValidationResult:
    passed: bool
    issues: List[ValidationIssue]
    checked: int
```

### `ValidationIssue`
Issue details:

```python
@dataclass
class ValidationIssue:
    severity: str  # 'critical', 'error', 'warning', 'info'
    category: str  # 'file_existence', 'json_validation', etc.
    message: str
    file_path: Optional[str]
    details: Optional[Dict]
```

### `AuditReport`
Complete audit report:

```python
@dataclass
class AuditReport:
    timestamp: str
    outputs_dir: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    issues: List[ValidationIssue]
    results: Dict[str, ValidationResult]
```

## Extending the Audit Runner

### Adding New Validation Checks

1. Add a new method to `OutputAuditRunner`:

```python
def validate_custom_check(self) -> ValidationResult:
    """Validate custom requirements."""
    result = ValidationResult(passed=True)

    # Your validation logic here
    result.checked += 1
    if condition_failed:
        result.add_issue(
            'error',
            'custom_category',
            'Custom validation failed',
            file_path='/path/to/file'
        )

    return result
```

2. Add to the checks list in `run()`:

```python
checks = [
    # ... existing checks ...
    ('Custom Check', self.validate_custom_check)
]
```

### Adding Phase-Specific Files

Update `PHASE_FILES` dictionary:

```python
PHASE_FILES = {
    '0-setup': {
        'required': ['project-config.json', 'new-required-file.json'],
        'optional': ['closeout.json', 'new-optional-file.md']
    },
    # ...
}
```

### Custom Schema Validation

Add validation helper methods:

```python
def _validate_custom_file(self, file_path: Path, data: Dict, result: ValidationResult):
    """Validate custom-file.json schema."""
    required_keys = ['custom_key_1', 'custom_key_2']

    for key in required_keys:
        if key not in data:
            result.add_issue(
                'error',
                'json_validation',
                f"Missing required key: {key}",
                str(file_path),
                {'missing_key': key}
            )
```

## Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | All validations passed (no critical or error issues) |
| 1 | Validation failed (critical or error issues found) |

## Dependencies

- Python 3.7+
- Standard library only (no external dependencies)

## Performance

- Fast execution (~1-2 seconds for full validation)
- Handles large output directories efficiently
- Memory-efficient (streams large files)

## See Also

- [UAT Runner](./uat_runner.py) - Run user acceptance tests
- [Guardian Test](./guardian-test.sh) - Run guardian validation
- [Integration Tests](../atomic-claude-python/tests/test_integration.py) - Python module tests
