# Dependency Audit - Quick Start

**30 seconds to validate your environment**

## Run It

```bash
cd /Users/jamesterbeest/dev/atomic-claude2
./test/run-dependency-audit.sh
```

## What You'll See

### All Clear (Green)
```
✓ OK:                16
Success Rate:        100%
✓ PASSED - All dependencies satisfied
```
**Action**: You're ready to run ATOMIC CLAUDE!

### Warnings (Yellow)
```
⚠ Warnings:          3
Success Rate:        81.2%
⚠ PASSED WITH WARNINGS - Optional dependencies missing
```
**Action**: Review optional dependencies. Install if needed.

### Errors (Red)
```
✗ Errors (required):  2
Success Rate:        62.5%
✗ FAILED - Required dependencies missing
```
**Action**: Install missing required dependencies immediately.

## Quick Fixes

### Missing Python 3.8+
```bash
# macOS
brew install python@3.11

# Linux
sudo apt install python3.11
```

### Missing Bash
```bash
# macOS (upgrade from 3.2 to 5.x)
brew install bash

# Linux
sudo apt install bash
```

### Missing git
```bash
# macOS
xcode-select --install
# or
brew install git

# Linux
sudo apt install git
```

### Missing jq
```bash
# macOS
brew install jq

# Linux
sudo apt install jq
```

### Missing Node.js (optional, for dashboard)
```bash
# macOS
brew install node

# Linux
sudo apt install nodejs npm
```

## What It Checks

### Required (Must Have)
- Python 3.8+
- Bash 3.2+ (macOS) or 4.0+ (Linux)
- git
- jq

### Optional (Nice to Have)
- Node.js (for real-time dashboard)
- claude CLI (for max provider)
- shellcheck (for bash validation)
- anthropic SDK (for API access)
- pytest (for testing)

## Report Location

JSON reports saved to:
```
test/reports/dependency-audit-YYYYMMDD-HHMMSS.json
```

## Exit Codes

- **0** = All required dependencies satisfied (ready to run)
- **1** = Required dependencies missing (install them first)

## Next Steps

1. **All clear?** → Run Phase 0: `./main.sh run 0`
2. **Have warnings?** → Optional, but consider installing for full features
3. **Have errors?** → Install missing dependencies, then re-run audit

## Integration Testing

After dependency audit passes, run integration tests:

```bash
./test/run-integration-audit.sh
```

This validates that Python orchestrators can execute bash scripts correctly.

## Full Documentation

See [DEPENDENCY-AUDIT.md](./DEPENDENCY-AUDIT.md) for complete documentation.
