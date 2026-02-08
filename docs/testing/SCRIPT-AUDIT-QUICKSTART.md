# Script Audit Quick Start

**5-Minute Guide to Running Script Quality Audits**

---

## TL;DR

```bash
# Full audit (bash + Python)
./test/run_script_audit.sh --json

# View results
cat test/reports/script-audit-*.json | jq '.summary'
```

---

## Quick Commands

### Basic Usage

```bash
# Audit everything
python3 test/script_audit_runner.py

# Bash scripts only
python3 test/script_audit_runner.py --bash-only

# Python scripts only
python3 test/script_audit_runner.py --python-only

# Generate JSON report
python3 test/script_audit_runner.py --json-report
```

### Using Launcher

```bash
# Full audit with JSON report
./test/run_script_audit.sh --json

# Bash only
./test/run_script_audit.sh --bash-only

# Python only
./test/run_script_audit.sh --python-only
```

---

## What It Checks

### Bash Scripts ✓

- Syntax errors (`bash -n`)
- ShellCheck violations (if installed)
- Missing shebangs
- Missing error handling (`set -e`)
- **DANGEROUS:** `rm -rf` with variables
- Unquoted variables
- `cd` without error checking

### Python Scripts ✓

- Syntax errors (`py_compile`)
- Import resolution
- Debug statements (print, pdb)
- Missing shebangs on executables
- TODO/FIXME comments

---

## Exit Codes

| Code | Status |
|------|--------|
| `0` | ✅ All valid (no critical issues) |
| `1` | ❌ Critical issues found |

---

## Reading Results

### Console Output

```
✓ file.py                      # No critical issues
✗ script.sh                    # Has critical issues
  [CRITICAL] antipattern:42
    Dangerous: rm -rf with variable
    💡 Add safety checks
```

### Color Coding

- 🔴 **RED** = Critical (must fix)
- 🟡 **YELLOW** = Warning (should fix)
- 🔵 **BLUE** = Info (nice to fix)
- 🟢 **GREEN** = Passed

---

## Summary Report

```
AUDIT SUMMARY
================================================================================

Status: FAILED / PASSED

Files Checked:
  Total:  163
  Bash:   97
  Python: 66
  Passed: 149
  Failed: 14

Issues Found:
  Total:    5897
  Critical: 58       # ← Fix these first!
  Warnings: 4999

Execution Time: 5.23s
```

---

## JSON Report Structure

```json
{
  "summary": {
    "total_files": 163,
    "files_passed": 149,
    "files_failed": 14,
    "critical_issues": 58,
    "warnings": 4999
  },
  "files": [
    {
      "file_path": "lib/atomic.sh",
      "passed": false,
      "issues": [
        {
          "line_number": 42,
          "severity": "critical",
          "category": "antipattern",
          "message": "Dangerous: rm -rf with variable",
          "suggestion": "Add safety checks"
        }
      ]
    }
  ]
}
```

---

## Common Issues & Fixes

### 1. Dangerous rm -rf (CRITICAL)

```bash
# ❌ DANGEROUS
rm -rf $TEMP_DIR

# ✅ SAFE
if [[ -n "${TEMP_DIR:-}" && "$TEMP_DIR" != "/" ]]; then
    rm -rf "${TEMP_DIR}"
fi
```

### 2. Unquoted Variables (WARNING)

```bash
# ❌ WRONG
echo $MESSAGE
cp $FILE $DEST

# ✅ RIGHT
echo "$MESSAGE"
cp "$FILE" "$DEST"
```

### 3. Missing Error Handling (WARNING)

```bash
#!/usr/bin/env bash
# ✅ Add this near top of scripts
set -euo pipefail
```

### 4. cd Without Checking (WARNING)

```bash
# ❌ WRONG
cd /some/path

# ✅ RIGHT
cd /some/path || exit 1
```

---

## Pro Tips

### 1. Install ShellCheck

```bash
# macOS
brew install shellcheck

# Ubuntu/Debian
apt install shellcheck
```

### 2. Check Specific Files

```bash
# Bash syntax only
bash -n lib/atomic.sh

# Python syntax only
python3 -m py_compile core/llm.py

# ShellCheck
shellcheck lib/atomic.sh
```

### 3. Focus on Critical First

```bash
# See only critical issues
./test/run_script_audit.sh | grep -A 2 CRITICAL
```

### 4. JSON Query Examples

```bash
# Get critical issue count
cat test/reports/script-audit-*.json | jq '.summary.critical_issues'

# List files with critical issues
cat test/reports/script-audit-*.json | \
  jq -r '.files[] | select(.passed == false) | .file_path'

# Show all critical issues
cat test/reports/script-audit-*.json | \
  jq '.files[].issues[] | select(.severity == "critical")'
```

---

## Workflow Integration

### Pre-Commit Check

```bash
#!/usr/bin/env bash
# .git/hooks/pre-commit

echo "Running script quality audit..."
python3 test/script_audit_runner.py

if [[ $? -ne 0 ]]; then
    echo "❌ Critical issues found. Commit blocked."
    exit 1
fi
```

### CI/CD Pipeline

```yaml
# .github/workflows/quality.yml
- name: Script Quality Audit
  run: |
    python3 test/script_audit_runner.py --json-report
    if [[ $? -ne 0 ]]; then
      echo "Critical issues found"
      exit 1
    fi
```

---

## Troubleshooting

### "ShellCheck not found"

This is just a warning. The audit still runs basic checks.

**Fix:** `brew install shellcheck` (optional but recommended)

### "Permission denied"

```bash
chmod +x test/run_script_audit.sh
chmod +x test/script_audit_runner.py
```

### "Import errors" in Python audit

May be false positives for project-specific modules. Review manually.

### Audit takes too long

Use targeted audits:
```bash
# Faster - bash only
./test/run_script_audit.sh --bash-only

# Faster - python only
./test/run_script_audit.sh --python-only
```

---

## Files Created

| File | Purpose |
|------|---------|
| `test/script_audit_runner.py` | Main audit tool |
| `test/run_script_audit.sh` | Quick launcher |
| `test/reports/script-audit-*.json` | Detailed reports |
| `test/SCRIPT-AUDIT-SUMMARY.md` | Full analysis |
| `test/SCRIPT-AUDIT-QUICKSTART.md` | This guide |

---

## Current Status (as of 2026-02-04)

### Overall

- **Total Files:** 163
- **Pass Rate:** 91% (149/163)
- **Critical Issues:** 58 (all bash)
- **Warnings:** 4,999

### By Type

| Type | Files | Status |
|------|-------|--------|
| Python | 66 | ✅ 100% pass (0 critical) |
| Bash | 97 | ⚠️ 86% pass (58 critical) |

---

## Priority Actions

1. **Fix critical issues** in core lib files:
   - `lib/atomic.sh` (14 critical)
   - `lib/audit.sh` (8 critical)
   - `lib/task-state.sh` (6 critical)

2. **Install ShellCheck** for better analysis

3. **Run audit regularly** during development

---

**Ready to audit?** Run: `./test/run_script_audit.sh --json`

**Questions?** See: `test/SCRIPT-AUDIT-SUMMARY.md`
