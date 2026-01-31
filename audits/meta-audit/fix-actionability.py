#!/usr/bin/env python3
"""
Fix actionability issues identified in the meta-audit.
- Convert invalid evidence_pattern to evidence_description
- Fix verification commands with placeholder syntax
- Fix bash script syntax errors
- Fix overly broad glob patterns
"""

import yaml
import re
from pathlib import Path

# Custom YAML representer to preserve multiline strings
def str_representer(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, str_representer)

AUDITS_DIR = Path("/mnt/walnut-drive/dev/audits/audits")

# Issues to fix - extracted from actionability-report.yaml
FIXES = {
    # Evidence pattern → evidence_description conversions (pattern is actually a description)
    "14-usability-interaction/forms-input/required-field-indication.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "high", 2],
        "old": "* markers without legend explaining meaning",
    },
    "09-api-integration/pagination-filtering/pagination-strategy.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "high", 0],
        "old": "SELECT COUNT(*) executed for totalCount on large tables",
    },
    "11-devops-ci-cd/infrastructure-as-code/state-management.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "critical", 0],
        "old": "*.tfstate files in git, no remote backend configured",
    },
    "11-devops-ci-cd/build-pipeline/dependency-management.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "critical", 0],
    },
    "08-data-state-management/schema-design/null-handling-strategy.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "critical", 1],
        "old": "SUM(), AVG(), COUNT(*) without null handling",
    },
    "15-accessibility-inclusion/perceivable-visual/color-only-information.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "critical", 1],
        "old": "* with only color styling, no aria-required",
    },
    "15-accessibility-inclusion/perceivable-visual/focus-indicator-visibility.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "critical", 0],
        "old": "*:focus { outline: none } without alternative styling",
    },
    "13-infrastructure-as-code/provider-version/module-version-pinning.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "critical", 1],
        "old": "?ref=main or ?ref=master",
    },
    "02-performance-efficiency/algorithmic-efficiency/pagination-strategy.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "high", 0],
        "old": "SELECT COUNT(*) executed for total in pagination",
    },
    "02-performance-efficiency/resource-utilization/container-resource-limits.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "critical", 0],
        "old": "spec.containers[].resources.limits.memory: null",
    },
    "10-testing-quality-assurance/performance-testing/load-testing.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "critical", 0],
        "old": "Absence of load test files (*.jmx, k6/*.js, locust/*.py)",
    },
    # Fix invalid regex patterns that can be corrected
    "07-architecture-design/extensibility-evolution/backward-compatibility-design.yaml": {
        "type": "fix_regex",
        "path": ["discovery", "code_patterns", 2, "pattern"],
        "old": r"default\s*:|optional\s+|?:",
        "new": r"default\s*:|optional\s+|\?:",
    },
    "02-performance-efficiency/frontend-performance/third-party-script-impact.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "critical", 1],
    },
    "01-security-trust/data-protection/data-export-security.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "critical", 0],
    },
    "01-security-trust/authorization/cross-tenant-isolation.yaml": {
        "type": "fix_regex",
        "path": ["signals", "critical", 0],
        "field": "evidence_pattern",
        "old": r"findAll\(\)|find\(\{\})(?!.*tenantId|where.*tenant)",
        "new": r"findAll\(\)|find\(\{\}\)(?!.*tenantId|where.*tenant)",
    },
    "06-code-quality/idioms/modern-syntax-adoption.yaml": {
        "type": "fix_regex",
        "path": ["signals", "medium", 0],
        "field": "evidence_pattern",
        "old": r'"%s"|\.format\(|\+.*\+.*string',
        "new": r'"%s"|\.format\(|\+.*\+.*str',
    },
    "06-code-quality/test-code-quality/test-naming.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "medium", 0],
    },
    "06-code-quality/error-handling/defensive-programming.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "critical", 1],
    },
    "06-code-quality/error-handling/fail-fast-pattern.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "high", 1],
    },
    "06-code-quality/error-handling/error-type-hierarchy.yaml": {
        "type": "evidence_pattern_to_description",
        "path": ["signals", "medium", 0],
    },
    # Verification command fixes - wrap placeholders in quotes or mark as manual
    "12-cloud-infrastructure/cloud-security/encryption-in-transit.yaml": {
        "type": "fix_verification_placeholder",
        "indices": [1, 4],
    },
    "12-cloud-infrastructure/containers/container-image-security.yaml": {
        "type": "fix_verification_placeholder",
        "indices": [4],
    },
    "04-scalability-capacity/database-scalability/sharding-strategy.yaml": {
        "type": "fix_verification_sql",
        "indices": [1],
    },
    "04-scalability-capacity/horizontal-scaling/scale-out-speed.yaml": {
        "type": "fix_verification_placeholder",
        "indices": [1],
    },
    "14-usability-interaction/forms-input/autofill-compatibility.yaml": {
        "type": "fix_verification_quotes",
        "indices": [2],
    },
    "11-devops-ci-cd/pipeline-security/secrets-in-pipeline.yaml": {
        "type": "fix_verification_quotes",
        "indices": [0],
    },
    "01-security-trust/secrets-management/pipeline-secrets.yaml": {
        "type": "fix_verification_quotes",
        "indices": [1],
    },
    "01-security-trust/secrets-management/config-file-security.yaml": {
        "type": "fix_verification_quotes",
        "indices": [0],
    },
    # Glob pattern fix
    "17-human-organizational/team-structure/bus-factor.yaml": {
        "type": "fix_glob",
        "path": ["discovery", "file_patterns", 0, "glob"],
        "old": "**/*",
        "new": "**/*.{py,js,ts,java,rb,go,rs,cpp,c,cs}",
    },
}

def load_yaml(filepath):
    """Load YAML file preserving structure."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(filepath, data):
    """Save YAML file with proper formatting."""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=100)

def get_nested(data, path):
    """Get nested value by path."""
    current = data
    for key in path:
        if isinstance(current, list):
            current = current[key]
        else:
            current = current.get(key)
        if current is None:
            return None
    return current

def set_nested(data, path, value):
    """Set nested value by path."""
    current = data
    for key in path[:-1]:
        if isinstance(current, list):
            current = current[key]
        else:
            current = current[key]

    if isinstance(current, list):
        current[path[-1]] = value
    else:
        current[path[-1]] = value

def fix_evidence_pattern_to_description(data, path):
    """Convert evidence_pattern to evidence_description."""
    signal = get_nested(data, path)
    if signal and 'evidence_pattern' in signal:
        pattern = signal.pop('evidence_pattern')
        signal['evidence_description'] = pattern
        return True
    return False

def fix_verification_with_placeholder(data, indices):
    """Fix verification commands that have <placeholder> syntax."""
    checklist = data.get('closeout_checklist', [])
    fixed = 0
    for idx in indices:
        if idx < len(checklist):
            item = checklist[idx]
            if 'verification' in item and isinstance(item['verification'], str):
                old_v = item['verification']
                # Mark as requiring substitution
                if '<' in old_v and '>' in old_v:
                    item['verification'] = 'manual'
                    item['verification_notes'] = f"Requires variable substitution: {old_v}"
                    fixed += 1
    return fixed > 0

def fix_verification_sql(data, indices):
    """Fix SQL statements used as verification (not valid bash)."""
    checklist = data.get('closeout_checklist', [])
    fixed = 0
    for idx in indices:
        if idx < len(checklist):
            item = checklist[idx]
            if 'verification' in item and isinstance(item['verification'], str):
                old_v = item['verification']
                if old_v.strip().upper().startswith('SELECT'):
                    item['verification'] = 'manual'
                    item['verification_notes'] = f"SQL query - run in database: {old_v}"
                    fixed += 1
    return fixed > 0

def fix_verification_quotes(data, indices):
    """Fix verification commands with unbalanced quotes."""
    checklist = data.get('closeout_checklist', [])
    fixed = 0
    for idx in indices:
        if idx < len(checklist):
            item = checklist[idx]
            if 'verification' in item and isinstance(item['verification'], str):
                old_v = item['verification']
                # Count quotes
                single = old_v.count("'")
                double = old_v.count('"')
                if single % 2 != 0 or double % 2 != 0:
                    item['verification'] = 'manual'
                    item['verification_notes'] = f"Command has syntax issues - review: {old_v[:100]}"
                    fixed += 1
    return fixed > 0

def fix_regex_pattern(data, path, field, old_pattern, new_pattern):
    """Fix a specific regex pattern."""
    if field:
        signal = get_nested(data, path)
        if signal and field in signal:
            if signal[field] == old_pattern:
                signal[field] = new_pattern
                return True
    else:
        current_val = get_nested(data, path)
        if current_val == old_pattern:
            set_nested(data, path, new_pattern)
            return True
    return False

def fix_glob_pattern(data, path, old_glob, new_glob):
    """Fix overly broad glob pattern."""
    current_val = get_nested(data, path)
    if current_val == old_glob:
        set_nested(data, path, new_glob)
        return True
    return False

def fix_scripts(filepath):
    """Fix bash script syntax issues."""
    data = load_yaml(filepath)
    scripts = data.get('tooling', {}).get('scripts', [])
    fixed = False

    for script in scripts:
        if 'code' in script:
            code = script['code']
            # Fix brace expansion in single quotes issue
            # --include='*.{js,ts,java}' should be --include='*.js' --include='*.ts' --include='*.java'
            if "--include='*." in code and "{" in code:
                # Replace patterns like --include='*.{js,ts,java}' with multiple --include flags
                import re
                pattern = r"--include='\*\.(\{[^}]+\})'"
                def expand_include(match):
                    exts = match.group(1)[1:-1].split(',')  # Remove braces and split
                    return ' '.join(f"--include='*.{ext.strip()}'" for ext in exts)
                new_code = re.sub(pattern, expand_include, code)
                if new_code != code:
                    script['code'] = new_code
                    fixed = True

            # Fix for loop with glob in wrong place: for file in *.txt 2>/dev/null
            if 'for file in' in code and '2>/dev/null' in code:
                # The 2>/dev/null is on the wrong line
                lines = code.split('\n')
                new_lines = []
                for line in lines:
                    if line.strip().startswith('for ') and ' 2>/dev/null' in line:
                        # Move 2>/dev/null to the do line or remove it
                        line = line.replace(' 2>/dev/null', '')
                    new_lines.append(line)
                new_code = '\n'.join(new_lines)
                if new_code != code:
                    script['code'] = new_code
                    fixed = True

    if fixed:
        save_yaml(filepath, data)
    return fixed

def main():
    print("Fixing actionability issues...")
    fixed_count = 0

    for rel_path, fix_info in FIXES.items():
        filepath = AUDITS_DIR / rel_path
        if not filepath.exists():
            print(f"  SKIP: {rel_path} (file not found)")
            continue

        try:
            data = load_yaml(filepath)
            fixed = False

            if fix_info['type'] == 'evidence_pattern_to_description':
                fixed = fix_evidence_pattern_to_description(data, fix_info['path'])
            elif fix_info['type'] == 'fix_regex':
                fixed = fix_regex_pattern(data, fix_info['path'],
                                          fix_info.get('field'),
                                          fix_info.get('old', ''),
                                          fix_info.get('new', ''))
            elif fix_info['type'] == 'fix_verification_placeholder':
                fixed = fix_verification_with_placeholder(data, fix_info['indices'])
            elif fix_info['type'] == 'fix_verification_sql':
                fixed = fix_verification_sql(data, fix_info['indices'])
            elif fix_info['type'] == 'fix_verification_quotes':
                fixed = fix_verification_quotes(data, fix_info['indices'])
            elif fix_info['type'] == 'fix_glob':
                fixed = fix_glob_pattern(data, fix_info['path'],
                                         fix_info['old'], fix_info['new'])

            if fixed:
                save_yaml(filepath, data)
                print(f"  FIXED: {rel_path}")
                fixed_count += 1
            else:
                print(f"  NO CHANGE: {rel_path}")

        except Exception as e:
            print(f"  ERROR: {rel_path}: {e}")

    # Fix script issues separately
    script_files = [
        "26-testing-quality-assurance/integration-testing/database-integration-test.yaml",
        "18-ethical-societal/transparency-trust/terms-of-service-clarity.yaml",
    ]

    for rel_path in script_files:
        filepath = AUDITS_DIR / rel_path
        if filepath.exists():
            if fix_scripts(filepath):
                print(f"  FIXED SCRIPT: {rel_path}")
                fixed_count += 1

    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == '__main__':
    main()
