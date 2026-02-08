# Security Audit Runner

Comprehensive security validation tool for Atomic Claude that detects vulnerabilities, misconfigurations, and security risks across the entire codebase.

## Quick Start

```bash
cd /Users/jamesterbeest/dev/atomic-claude2

# Run security audit
./test/security_audit_runner.py

# Or use the convenience wrapper
./test/run-security-audit.sh
```

**Exit Codes**:
- `0`: No critical issues found (safe to deploy)
- `1`: Critical security issues detected (do not deploy)

## What It Checks

### 1. Secret Detection (Critical)
Scans for hardcoded secrets in source code:
- Anthropic API keys (`sk-ant-...`)
- AWS credentials (Access Key ID, Secret Access Key)
- Hardcoded passwords, tokens, API keys
- Private keys (RSA, DSA, EC, OpenSSH)
- .env and secrets.json file permissions

### 2. File Permissions
Validates secure file permissions:
- World-writable files in sensitive directories
- Executable permissions on library vs entry point files
- .git directory permissions
- Secret file permissions (should be 600)

### 3. Git Safety
Ensures secrets are protected from version control:
- .gitignore coverage for sensitive files
- Secrets in git history detection
- Tracked secrets.json files

### 4. Input Validation
Detects injection vulnerabilities:
- Command injection (subprocess with user input)
- Path traversal (unvalidated file paths)
- Prompt injection (unsanitized LLM inputs)

### 5. Network Security
Validates network access controls:
- Network mode enforcement
- Sandbox configuration
- Fetch operation restrictions

### 6. Dashboard Security
Checks web security best practices:
- XSS vulnerabilities (innerHTML without sanitization)
- Sensitive data exposure in dashboard
- CORS configuration

## Output

### Console Report

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
  ✓ No world-writable files
  ✓ Library file permissions appropriate
  ✓ main.py is executable

[... continues ...]

==================================================
        SECURITY AUDIT SUMMARY
==================================================

  Total Checks:    19
  Duration:        0.45s

  Critical:    0
  High:        0
  Medium:      0
  Low:         2
  ──────────────────
  Total:       2

Security audit passed!
```

### JSON Report

Saved to `test/reports/security-audit.json`:

```json
{
  "timestamp": "2026-02-04T21:30:00",
  "total_checks": 19,
  "findings": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 2,
    "total": 2
  },
  "duration": "0.45s",
  "details": [...]
}
```

## Severity Levels

| Level | Description | Action |
|-------|-------------|--------|
| **Critical** | Hardcoded secrets, sensitive data exposure | Fix immediately, do not deploy |
| **High** | Insecure permissions, injection vulnerabilities | Fix before next release |
| **Medium** | Group-readable secrets, overly permissive CORS | Schedule for remediation |
| **Low** | Incorrect executable permissions, minor issues | Fix when convenient |

## Common Issues and Fixes

### Hardcoded Secret

```
[CRITICAL] Hardcoded Anthropic API Key detected
Location: lib/provider.py:123
```

**Fix**:
```bash
# Move to .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
chmod 600 .env

# Update code
export ANTHROPIC_API_KEY=$(cat .env | grep ANTHROPIC_API_KEY | cut -d= -f2)
```

### Insecure .env Permissions

```
[HIGH] .env file has insecure permissions
Permissions: -rw-r--r-- (should be 600)
```

**Fix**:
```bash
chmod 600 .env
```

### Secrets in Git

```
[CRITICAL] Secrets file tracked in git
Location: .outputs/0-setup/secrets.json
```

**Fix**:
```bash
git rm --cached .outputs/0-setup/secrets.json
echo "**/secrets.json" >> .gitignore
git commit -m "Remove secrets from tracking"
```

### Command Injection

```
[HIGH] Potential command injection
Location: lib/atomic.py:456
```

**Fix**:
```python
# Bad
subprocess.run(f"git commit -m '{message}'", shell=True)

# Good
import shlex
subprocess.run(['git', 'commit', '-m', message])
```

### XSS Vulnerability

```
[HIGH] Potential XSS vulnerability
Location: dashboard/public/index.html
```

**Fix**:
```javascript
// Bad
element.innerHTML = userInput;

// Good
element.textContent = userInput;
// Or: element.innerHTML = DOMPurify.sanitize(userInput);
```

## Integration with CI/CD

### GitHub Actions

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
      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: security-report
          path: test/reports/security-audit.json
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
./test/security_audit_runner.py
if [ $? -ne 0 ]; then
    echo "Security audit failed - commit blocked"
    exit 1
fi
```

## Best Practices

1. **Run regularly**: Include in CI/CD and pre-commit hooks
2. **Fix critical issues immediately**: Don't deploy with critical findings
3. **Review all findings**: Even low-severity issues can compound
4. **Keep secrets out of git**: Use .env files, never commit secrets
5. **Validate all inputs**: Assume all user input is malicious
6. **Use least privilege**: 600 for secrets, 644 for code, 755 for executables
7. **Sanitize outputs**: Prevent XSS in dashboards and web interfaces

## Files

| File | Purpose |
|------|---------|
| `security_audit_runner.py` | Main audit script |
| `run-security-audit.sh` | Convenience wrapper |
| `SECURITY-AUDIT-QUICKSTART.md` | Quick start guide |
| `SECURITY-AUDIT-SUMMARY.md` | Implementation details |
| `README-SECURITY-AUDIT.md` | This file |
| `reports/security-audit.json` | Latest audit report |

## Performance

- **Duration**: 0.5-1.0 seconds
- **Files Scanned**: ~200-500 (excludes node_modules)
- **Checks**: 19 security validations
- **Categories**: 6 security domains

## Architecture

```python
class SecurityAuditRunner:
    """Main audit orchestrator"""

    # Category-specific checks
    def scan_for_secrets() -> Dict
    def check_file_permissions() -> Dict
    def check_git_safety() -> Dict
    def test_input_validation() -> Dict
    def test_network_security() -> Dict
    def check_dashboard_security() -> Dict

    # Orchestration
    def run_all_checks() -> SecurityReport

    # Reporting
    def save_report(report)
    def print_summary(report)
```

## Customization

### Add New Secret Pattern

Edit `SECRET_PATTERNS` in `security_audit_runner.py`:

```python
SECRET_PATTERNS = [
    # Existing patterns...
    (r'your-pattern-here', 'Description'),
]
```

### Adjust Severity

Modify severity in detection methods:

```python
self.findings.append(SecurityFinding(
    severity="high",  # critical, high, medium, low
    # ...
))
```

### Exclude False Positives

Add to exclusion logic:

```python
if '#' in line or 'example' in line.lower() or 'test' in file_path:
    continue
```

## Related Tools

- **Script Audit**: `./test/script_audit_runner.py` - Bash script validation
- **State Audit**: `./test/state_audit_runner.py` - State management validation
- **Config Audit**: `./test/config_audit_runner.py` - Configuration validation
- **Integration Audit**: `./test/integration_audit_runner.py` - Python/Bash integration
- **Memory Audit**: `./test/memory_audit_runner.py` - Memory system validation
- **Output Audit**: `./test/output_audit_runner.py` - Output file validation

## Troubleshooting

### Permission Denied

```bash
chmod +x test/security_audit_runner.py
```

### Import Errors

```bash
cd /Users/jamesterbeest/dev/atomic-claude2
python3 test/security_audit_runner.py
```

### False Positives

Known false positives:
- XSS in node_modules (third-party code)
- Test fixtures (automatically excluded)
- Comments and examples (automatically excluded)

To add exceptions, edit the exclusion logic in the script.

## Support

For issues or questions:
1. Check `test/reports/security-audit.json` for detailed findings
2. Review `SECURITY-AUDIT-QUICKSTART.md` for remediation steps
3. Consult `SECURITY-AUDIT-SUMMARY.md` for implementation details
4. File an issue if you believe a finding is incorrect

## License

Part of Atomic Claude - MIT License

## Version

- **Version**: 1.0.0
- **Last Updated**: 2026-02-04
- **Status**: Production Ready
