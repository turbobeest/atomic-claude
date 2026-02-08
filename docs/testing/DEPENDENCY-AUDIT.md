# Dependency Audit Runner

**Location**: `/Users/jamesterbeest/dev/atomic-claude2/test/dependency_audit_runner.py`

## Overview

The Dependency Audit Runner validates that all required tools and versions are available for running ATOMIC CLAUDE. It checks core dependencies, Python packages, optional tools, and provides installation guidance for missing components.

## Quick Start

```bash
# Run from anywhere
cd /Users/jamesterbeest/dev/atomic-claude2
./test/run-dependency-audit.sh

# Or run directly
python3 test/dependency_audit_runner.py
```

## What It Checks

### Core Dependencies (Required)

| Dependency | Required Version | Purpose |
|------------|-----------------|---------|
| **Python** | 3.8+ | Core runtime (3.9+ recommended) |
| **Bash** | 3.2+ (macOS), 4.0+ (Linux) | Script execution |
| **git** | Any recent version | Version control |
| **jq** | Any recent version | JSON parsing in bash |

### Python Packages

#### Standard Library (Required)
- `json` - JSON parsing
- `subprocess` - CLI invocations
- `pathlib` - File operations
- `argparse` - CLI parsing
- `typing` - Type hints

#### Optional Packages
- `anthropic` - Anthropic SDK for API access
- `pytest` - Testing framework
- `pyyaml` - YAML config support
- `rich` - Enhanced terminal output

### Optional Tools

| Tool | Purpose | When Needed |
|------|---------|-------------|
| **Node.js** | Tasks dashboard | Real-time web UI |
| **claude CLI** | Claude Code integration | Max provider support |
| **shellcheck** | Bash validation | Enhanced script checking |

## Output

### Console Report

The audit displays color-coded status for each dependency:

- ✓ (green) - Installed and meets requirements
- ⚠ (yellow) - Warning or optional dependency missing
- ✗ (red) - Required dependency missing or error

### Summary Statistics

```
Total Dependencies:  16
✓ OK:                13
⚠ Warnings:          3
✗ Missing (optional): 0
✗ Errors (required):  0

Success Rate:        81.2%
Duration:            0.63s
```

### JSON Report

Reports are saved to `test/reports/dependency-audit-YYYYMMDD-HHMMSS.json`:

```json
{
  "timestamp": "2026-02-04T21:24:51.743907",
  "platform": "Darwin",
  "python_version": "3.13.9",
  "total_dependencies": 16,
  "ok_count": 13,
  "warning_count": 3,
  "missing_count": 0,
  "error_count": 0,
  "success_rate": 81.25,
  "results": [
    {
      "name": "Python",
      "category": "core",
      "status": "ok",
      "version": "3.13.9",
      "meets_requirements": true,
      "required_version": "3.8+",
      "warning": null,
      "install_command": "brew install python@3.11",
      "documentation_url": "https://www.python.org/downloads/"
    }
  ]
}
```

## Installation Guidance

### macOS (Homebrew)

```bash
# Core dependencies
brew install python@3.11
brew install bash
brew install git
brew install jq

# Optional tools
brew install node
brew install shellcheck

# Python packages
pip install anthropic pytest pyyaml rich
```

### Linux (apt)

```bash
# Core dependencies
sudo apt update
sudo apt install python3.11 bash git jq

# Optional tools
sudo apt install nodejs npm shellcheck

# Python packages
pip3 install anthropic pytest pyyaml rich
```

### Linux (yum/dnf)

```bash
# Core dependencies
sudo yum install python311 bash git jq

# Optional tools
sudo yum install nodejs ShellCheck

# Python packages
pip3 install anthropic pytest pyyaml rich
```

## Version Compatibility

### Python

The audit tests compatibility with Python versions:

- **3.8** - Minimum supported (EOL October 2024)
- **3.9** - Recommended minimum
- **3.10** - Fully supported
- **3.11** - Recommended (latest stable)
- **3.12** - Fully supported
- **3.13+** - Experimental support

### Bash

- **macOS**: Bash 3.2+ (shipped version)
- **Linux**: Bash 4.0+ (standard)
- **Recommended**: Bash 5.0+ for best compatibility

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All required dependencies satisfied |
| `1` | Required dependencies missing |

Warnings about optional dependencies do not cause non-zero exit.

## Integration with CI/CD

### GitHub Actions

```yaml
name: Dependency Audit

on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y bash git jq

      - name: Run dependency audit
        run: |
          python3 test/dependency_audit_runner.py

      - name: Upload audit report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: dependency-audit-report
          path: test/reports/dependency-audit-*.json
```

### Pre-commit Hook

```bash
#!/usr/bin/env bash
# .git/hooks/pre-commit

python3 test/dependency_audit_runner.py --quick || {
    echo "Dependency audit failed. Install missing dependencies."
    exit 1
}
```

## Architecture

### Class Structure

```python
class DependencyAuditRunner:
    def check_core_dependencies(self) -> Dict[str, DependencyResult]
    def check_python_packages(self) -> Dict[str, DependencyResult]
    def check_optional_tools(self) -> Dict[str, DependencyResult]
    def check_versions(self) -> Dict[str, bool]
    def run_all_checks(self) -> AuditReport
```

### Data Models

```python
@dataclass
class VersionInfo:
    installed: bool
    version: Optional[str]
    meets_requirements: bool
    required_version: Optional[str]
    warning: Optional[str]

@dataclass
class DependencyResult:
    name: str
    category: str  # core, python, optional
    status: str    # ok, warning, missing, error
    version_info: VersionInfo
    install_command: Optional[str]
    documentation_url: Optional[str]

@dataclass
class AuditReport:
    timestamp: str
    platform: str
    python_version: str
    total_dependencies: int
    ok_count: int
    warning_count: int
    missing_count: int
    error_count: int
    results: List[DependencyResult]
```

## Customization

### Adding New Dependencies

Edit the `check_*_dependencies()` methods:

```python
# Add to core dependencies
def check_core_dependencies(self) -> Dict[str, DependencyResult]:
    results = {}
    results["new_tool"] = self._check_new_tool()
    return results

# Add check method
def _check_new_tool(self) -> DependencyResult:
    print(f"  Checking new_tool...", end=" ")
    # Implementation
```

### Platform-Specific Logic

```python
if self.is_macos:
    install_cmd = "brew install tool"
elif self.is_linux:
    install_cmd = "sudo apt install tool"
else:
    install_cmd = "See https://example.com"
```

## Troubleshooting

### Python Version Issues

**Problem**: "Python version too old"

```bash
# Check current version
python3 --version

# Install newer version
brew install python@3.11  # macOS
sudo apt install python3.11  # Linux

# Update alternatives
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### Bash Version Issues (macOS)

**Problem**: "Consider upgrading to Bash 5+"

```bash
# Install new bash
brew install bash

# Add to /etc/shells
echo /opt/homebrew/bin/bash | sudo tee -a /etc/shells

# Change default shell
chsh -s /opt/homebrew/bin/bash
```

### Missing jq

**Problem**: "jq not found"

```bash
# macOS
brew install jq

# Linux
sudo apt install jq

# Verify
jq --version
```

### Node.js for Dashboard

**Problem**: "Tasks dashboard won't work"

```bash
# Install Node.js
brew install node  # macOS
sudo apt install nodejs npm  # Linux

# Or use nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install --lts
```

## Best Practices

1. **Run before setup**: Check dependencies before running Phase 0
2. **Run after updates**: Re-check after system updates or Python version changes
3. **Include in CI**: Add to continuous integration pipelines
4. **Document exceptions**: If optional dependencies are intentionally skipped
5. **Monitor warnings**: Track optional tools for enhanced functionality

## Related Documentation

- [Integration Audit](./INTEGRATION-AUDIT.md) - Python/Bash integration testing
- [CLAUDE.md](../CLAUDE.md) - Main project documentation
- [Atomic Core](../atomic-claude-python/lib/atomic.py) - Python implementation

## Example Output

```
======================================================================
ATOMIC CLAUDE - Dependency Audit
======================================================================

Platform: Darwin
Python:   3.13.9

Checking Core Dependencies...
  Checking Python... ✓ 3.13.9
  Checking Bash... ✓ 5.3
  Checking git... ✓ 2.50.1
  Checking jq... ✓ 1.7.1-apple
  Checking Node.js (optional)... ✓ 24.7.0

Checking Python Packages...
  Checking json (stdlib)... ✓
  Checking subprocess (stdlib)... ✓
  Checking pathlib (stdlib)... ✓
  Checking argparse (stdlib)... ✓
  Checking typing (stdlib)... ✓
  Checking anthropic (optional)... ✗ Not installed
  Checking pytest (optional)... ✓
  Checking pyyaml (optional)... ✗ Not installed
  Checking rich (optional)... ✓

Checking Optional Tools...
  Checking claude CLI... ✓ Found
  Checking shellcheck... ✗ Not found

Version Compatibility...
  Python 3.8: ~ (not tested)
  Python 3.9: ~ (not tested)
  Python 3.10: ~ (not tested)
  Python 3.11: ~ (not tested)
  Python 3.12: ~ (not tested)

======================================================================
Summary
======================================================================

  Total Dependencies:  16
  ✓ OK:                13
  ⚠ Warnings:          3
  ✗ Missing (optional): 0
  ✗ Errors (required):  0

  Success Rate:        81.2%
  Duration:            0.63s

  ⚠ PASSED WITH WARNINGS - Optional dependencies missing

Optional Dependencies (Recommended):

  anthropic
    Note:    Anthropic SDK for API access
    Install: pip install anthropic
    Docs:    https://pypi.org/project/anthropic/

  pyyaml
    Note:    YAML config support
    Install: pip install pyyaml
    Docs:    https://pypi.org/project/pyyaml/

  shellcheck
    Note:    shellcheck provides enhanced bash validation
    Install: brew install shellcheck
    Docs:    https://www.shellcheck.net/

Report saved: test/reports/dependency-audit-20260204-212451.json
```
