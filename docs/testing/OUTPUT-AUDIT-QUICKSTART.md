# Output Validation Audit - Quick Start

## What is it?

The Output Validation Audit Runner validates all output files after a UAT run to ensure the ATOMIC CLAUDE pipeline generated valid, complete outputs.

## Quick Commands

### Basic Usage
```bash
python3 test/output_audit_runner.py
```

### Custom Paths
```bash
python3 test/output_audit_runner.py \
  --outputs-dir /path/to/.outputs \
  --report-dir /path/to/reports
```

### Using Example Script
```bash
./test/example-output-audit.sh /path/to/.outputs /path/to/reports
```

## What It Checks

✓ **File Existence** - All required phase files present
✓ **JSON Validation** - All JSON files parseable and valid
✓ **Markdown Structure** - PRD has 15 sections, no corrupted markdown
✓ **File Sizes** - No 0-byte or runaway files (>10MB)
✓ **Closeout Files** - All phases have valid closeout.json

## Output

### Console
- Real-time progress for each validation category
- Summary statistics (pass/fail counts, pass rate)
- Detailed critical and error issues
- Overall pass/fail status

### JSON Report
Saved to `test/reports/output-audit-YYYYMMDD-HHMMSS.json`

## Exit Codes

- `0` = All validations passed (no critical or error issues)
- `1` = Validation failed (critical or error issues found)

## Issue Severity

| Level | Description | Fails Validation? |
|-------|-------------|-------------------|
| **CRITICAL** | Blocks pipeline execution | ✗ YES |
| **ERROR** | Invalid output, data corruption | ✗ YES |
| **WARNING** | Missing optional files, minor issues | ✓ NO |
| **INFO** | Informational only | ✓ NO |

## Common Issues & Fixes

### Missing closeout.json
```
[ERROR] Required file missing: closeout.json
```
**Fix**: Phase did not complete. Check phase logs and re-run.

### Empty JSON file
```
[ERROR] Empty JSON file
```
**Fix**: LLM invocation likely failed. Check task logs.

### Invalid JSON
```
[CRITICAL] Invalid JSON: Expecting value: line 1 column 1
```
**Fix**: File is corrupted or incomplete. Re-run the task.

### Missing PRD sections
```
[WARNING] PRD missing 3 section(s): ## 10., ## 11., ## 12.
```
**Fix**: PRD generation incomplete. Re-run Phase 2 or add sections manually.

## Integration Examples

### After UAT Test
```bash
# Run UAT
python test/uat_runner.py

# Validate outputs
python3 test/output_audit_runner.py
```

### CI/CD Pipeline
```bash
#!/bin/bash
if python3 test/output_audit_runner.py --outputs-dir .outputs; then
    echo "✓ Validation passed"
    exit 0
else
    echo "✗ Validation failed"
    exit 1
fi
```

### Python Test Suite
```python
import subprocess

def test_output_validation():
    result = subprocess.run(
        ['python3', 'test/output_audit_runner.py'],
        capture_output=True
    )
    assert result.returncode == 0, "Output validation failed"
```

## Phase Requirements

### Phase 0: Setup
- **Required**: project-config.json, secrets.json
- **Optional**: closeout.json

### Phase 1: Discovery
- **Required**: closeout.json
- **Optional**: selected-agents.json

### Phase 2: PRD
- **Required**: closeout.json
- **Optional**: PRD.md (with 15 sections)

### Phase 3-9: All Other Phases
- **Required**: closeout.json
- **Optional**: Phase-specific outputs

## View Results

### Console Summary
Automatically displayed after running

### JSON Report
```bash
# View latest report
cat test/reports/output-audit-*.json | tail -n 1

# With jq for pretty output
jq . test/reports/output-audit-20260204-212104.json
```

### Quick Summary
```bash
jq '.summary' test/reports/output-audit-20260204-212104.json
```

### Issues by Severity
```bash
jq '.issues_by_severity' test/reports/output-audit-20260204-212104.json
```

### All Critical/Error Issues
```bash
jq '[.issues[] | select(.severity=="critical" or .severity=="error")]' \
  test/reports/output-audit-20260204-212104.json
```

## Next Steps

After validation passes:
1. Review any warnings/info issues (optional fixes)
2. Archive outputs for reference
3. Proceed with deployment or next pipeline stage

After validation fails:
1. Review critical/error issues in console output
2. Check detailed JSON report for all issues
3. Fix identified issues
4. Re-run validation
5. Repeat until validation passes

## See Also

- [README-OUTPUT-AUDIT.md](./README-OUTPUT-AUDIT.md) - Full documentation
- [example-output-audit.sh](./example-output-audit.sh) - Example usage script
- [output_audit_runner.py](./output_audit_runner.py) - Main audit runner
