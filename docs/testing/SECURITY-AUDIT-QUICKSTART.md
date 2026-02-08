# Security Audit Quick Start

## Overview

The Security Audit Runner validates security best practices across the Atomic Claude codebase, detecting vulnerabilities, misconfigurations, and security risks.

## Quick Run

```bash
cd /Users/jamesterbeest/dev/atomic-claude2
./test/security_audit_runner.py
```

## What It Checks

### 1. Secret Detection
- Hardcoded API keys (Anthropic, AWS, etc.)
- Passwords in code
- Private keys and certificates
- .env and secrets.json security

### 2. File Permissions
- World-writable files in sensitive directories
- Executable permissions on library files
- .git directory permissions
- secrets.json permissions (should be 600)

### 3. Git Safety
- .gitignore coverage (secrets, keys, .env)
- Secrets in git history
- Tracked secrets files

### 4. Input Validation
- Command injection risks (subprocess with user input)
- Path traversal vulnerabilities
- Prompt injection risks

### 5. Network Security
- Network mode enforcement
- Sandbox configuration
- Fetch restrictions

### 6. Dashboard Security
- XSS vulnerabilities
- Sensitive data exposure
- CORS configuration

## Exit Codes

- **0**: No critical issues found
- **1**: Critical security issues detected

## Report Output

### Console Output
```
==================================================
           SECURITY AUDIT
==================================================

Secret Detection
-----------------------------------------
  ✓ Python files: No hardcoded secrets
  ✓ Shell scripts: No hardcoded secrets
  ✓ JavaScript files: No hardcoded secrets
  ✓ .env file permissions: -rw-------

File Permissions
-----------------------------------------
  ✓ No world-writable files in sensitive directories
  ✓ Library file permissions appropriate
  ✓ main.py is executable

Git Safety
-----------------------------------------
  ✓ .gitignore covers sensitive files
  ✓ No secrets files tracked in git

Input Validation
-----------------------------------------
  ✓ No obvious command injection risks
  ✓ No obvious path traversal risks
  ⚠  Prompt injection risks: 2 files

Network Security
-----------------------------------------
  ✓ Network mode enforcement present
  ✓ No sandbox bypasses detected
  ✓ URL validation present

Dashboard Security
-----------------------------------------
  ✓ No obvious XSS vulnerabilities
  ✓ No sensitive data exposure detected
  ✓ No CORS configuration (default same-origin)

==================================================
        SECURITY AUDIT SUMMARY
==================================================

  Total Checks:    18
  Duration:        0.45s

  Critical:    0
  High:        0
  Medium:      0
  Low:         2
  ──────────────────
  Total:       2

Findings by Category:

  Input Validation
    [LOW] Potential prompt injection risk
    Location: phases/2-prd/tasks/203-prd-interview.sh
    Fix: Validate and escape user input before including in prompts

Security audit passed!
```

### JSON Report

Saved to `test/reports/security-audit.json`:

```json
{
  "timestamp": "2026-02-04T21:30:00",
  "total_checks": 18,
  "findings": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 2,
    "total": 2
  },
  "duration": "0.45s",
  "details": [
    {
      "category": "Input Validation",
      "severity": "low",
      "title": "Potential prompt injection risk",
      "description": "User input included in prompts without visible sanitization",
      "location": "phases/2-prd/tasks/203-prd-interview.sh",
      "remediation": "Validate and escape user input before including in prompts",
      "details": {}
    }
  ]
}
```

## Severity Levels

### Critical
- Hardcoded secrets in code
- Secrets tracked in git
- Sensitive data exposed in dashboard
- Major security vulnerabilities

**Action**: Fix immediately, do not deploy

### High
- Insecure file permissions (world-writable secrets)
- Missing .gitignore entries
- Command injection risks
- XSS vulnerabilities

**Action**: Fix before next release

### Medium
- Group-readable secrets files
- .git directory exposed
- Overly permissive CORS
- Path traversal risks

**Action**: Schedule for remediation

### Low
- Incorrect executable permissions
- Missing URL validation
- Prompt injection risks
- Code style issues

**Action**: Fix when convenient

## Common Issues and Fixes

### Issue: Hardcoded API Key

```
[CRITICAL] Hardcoded Anthropic API Key detected
Location: lib/provider.py:123
Fix: Move secret to .env file or environment variables
```

**Remediation**:
```bash
# Move to .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
chmod 600 .env

# Update code to use env var
export ANTHROPIC_API_KEY=$(cat .env | grep ANTHROPIC_API_KEY | cut -d= -f2)
```

### Issue: Insecure .env Permissions

```
[HIGH] .env file has insecure permissions
Location: .env
Permissions: -rw-r--r-- (should be 600)
Fix: Run: chmod 600 .env
```

**Remediation**:
```bash
chmod 600 .env
```

### Issue: Secrets in Git

```
[CRITICAL] Secrets file tracked in git
Location: .outputs/0-setup/secrets.json
Fix: git rm --cached .outputs/0-setup/secrets.json
```

**Remediation**:
```bash
# Remove from tracking
git rm --cached .outputs/0-setup/secrets.json

# Add to .gitignore
echo "**/secrets.json" >> .gitignore

# Commit
git commit -m "Remove secrets from tracking"

# Optional: Purge from history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .outputs/0-setup/secrets.json" \
  --prune-empty --tag-name-filter cat -- --all
```

### Issue: Command Injection Risk

```
[HIGH] Potential command injection: Subprocess with f-string
Location: lib/atomic.py:456
Fix: Use shlex.quote() or avoid shell=True
```

**Remediation**:
```python
# Bad
subprocess.run(f"git commit -m '{message}'", shell=True)

# Good
import shlex
subprocess.run(['git', 'commit', '-m', message])

# Or with validation
subprocess.run(f"git commit -m '{shlex.quote(message)}'", shell=True)
```

### Issue: XSS Vulnerability

```
[HIGH] Potential XSS vulnerability
Location: dashboard/public/index.html
Fix: Use textContent or sanitize HTML with DOMPurify
```

**Remediation**:
```javascript
// Bad
element.innerHTML = userInput;

// Good
element.textContent = userInput;

// Or with sanitization
element.innerHTML = DOMPurify.sanitize(userInput);
```

## Integration with CI/CD

Add to your CI pipeline:

```yaml
# .github/workflows/security.yml
name: Security Audit
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Security Audit
        run: ./test/security_audit_runner.py
```

## Best Practices

1. **Run regularly**: Include in pre-commit hooks or CI/CD
2. **Fix critical issues immediately**: Don't deploy with critical findings
3. **Review all findings**: Even low-severity issues can compound
4. **Keep secrets out of git**: Use .env, never commit secrets
5. **Validate all inputs**: Assume all user input is malicious
6. **Use least privilege**: 600 for secrets, 644 for code, 755 for executables
7. **Sanitize outputs**: Prevent XSS in dashboards and web interfaces

## Troubleshooting

### Permission Denied
```bash
chmod +x test/security_audit_runner.py
```

### Import Errors
```bash
# Ensure you're in the atomic-claude root
cd /Users/jamesterbeest/dev/atomic-claude2
python3 test/security_audit_runner.py
```

### False Positives

Edit the script to add exceptions for known safe patterns:

```python
# In scan_files_for_secrets()
if '#' in line or 'example' in line.lower() or 'test' in line.lower():
    continue
```

## Related Tools

- **Script Audit**: `./test/script_audit_runner.py`
- **State Audit**: `./test/state_audit_runner.py`
- **Config Audit**: `./test/config_audit_runner.py`
- **Integration Audit**: `./test/integration_audit_runner.py`

## Support

For issues or questions:
1. Check the JSON report for detailed findings
2. Review remediation steps for each finding
3. Consult security best practices documentation
4. File an issue if you believe a finding is incorrect
