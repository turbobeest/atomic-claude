# Security Audit - Quick Reference

## Run Audit

```bash
./test/security_audit_runner.py
./test/run-security-audit.sh
```

## Exit Codes

- `0` = No critical issues (safe to deploy)
- `1` = Critical issues found (do not deploy)

## Report Location

- Console: Color-coded output
- JSON: `test/reports/security-audit.json`

## Severity Levels

| Level | Examples | Action |
|-------|----------|--------|
| 🔴 **Critical** | Hardcoded secrets, data exposure | Fix immediately |
| 🟡 **High** | Insecure permissions, XSS, injection | Fix before release |
| 🟠 **Medium** | Group permissions, CORS | Schedule fix |
| 🔵 **Low** | Incorrect +x, minor issues | Fix when convenient |

## Security Categories (6)

1. **Secret Detection** - Hardcoded API keys, passwords
2. **File Permissions** - World-writable, incorrect +x
3. **Git Safety** - .gitignore, secrets in history
4. **Input Validation** - Injection vulnerabilities
5. **Network Security** - Sandbox, network mode
6. **Dashboard Security** - XSS, CORS, data exposure

## Quick Fixes

### Hardcoded Secret
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
chmod 600 .env
```

### File Permissions
```bash
chmod 600 .env                    # Secrets
chmod 644 lib/*.py                # Code
chmod +x main.py                  # Entry point
```

### Git Safety
```bash
cat >> .gitignore << EOF
.env
**/secrets.json
*.key
*.pem
EOF
git rm --cached path/to/secrets.json
```

### Command Injection
```python
# Bad
subprocess.run(f"cmd '{user_input}'", shell=True)

# Good
subprocess.run(['cmd', user_input])
```

### XSS
```javascript
// Bad
element.innerHTML = userInput;

// Good
element.textContent = userInput;
```

## CI/CD Integration

### GitHub Actions
```yaml
- run: ./test/security_audit_runner.py
```

### Pre-commit Hook
```bash
#!/bin/bash
./test/security_audit_runner.py || exit 1
```

## Documentation

- Quick Start: `test/SECURITY-AUDIT-QUICKSTART.md`
- Full Guide: `test/README-SECURITY-AUDIT.md`
- Implementation: `test/SECURITY-AUDIT-SUMMARY.md`

## Key Metrics

- **19** security checks
- **6** security categories
- **9** secret pattern types
- **0.5-1.0s** execution time

## File Structure

```
test/
├── security_audit_runner.py       # Main script
├── run-security-audit.sh          # Wrapper
├── SECURITY-AUDIT-QUICKSTART.md   # Quick start
├── SECURITY-AUDIT-SUMMARY.md      # Implementation
├── README-SECURITY-AUDIT.md       # Full docs
├── SECURITY-AUDIT-CHEATSHEET.md   # This file
└── reports/
    └── security-audit.json        # Latest report
```

## Secure Permissions Model

| File Type | Permission | Octal |
|-----------|------------|-------|
| Secrets (.env) | `-rw-------` | 600 |
| Code (*.py) | `-rw-r--r--` | 644 |
| Executables | `-rwxr-xr-x` | 755 |
| .git directory | `drwx------` | 700 |

## Secret Patterns Detected

1. Anthropic API keys (`sk-ant-...`)
2. AWS Access Key ID
3. AWS Secret Access Key
4. Hardcoded passwords
5. Generic API keys
6. Tokens
7. Generic secrets
8. Private keys (RSA, DSA, EC, OpenSSH)
9. PEM files

## Common False Positives

- XSS in node_modules (third-party)
- Comments with example keys
- Test fixtures (auto-excluded)

## Status

✅ Production Ready
Version: 1.0.0
Last Updated: 2026-02-04
