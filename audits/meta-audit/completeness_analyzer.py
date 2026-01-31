#!/usr/bin/env python3
"""
Completeness Meta-Audit Analyzer
Analyzes all audit files for missing required fields.
"""

import os
import yaml
from pathlib import Path
from collections import defaultdict
from datetime import datetime

AUDITS_DIR = "/mnt/walnut-drive/dev/audits/audits"

# Define required fields and their severity
REQUIRED_FIELDS = {
    "critical": [
        ("audit.id", ["audit", "id"]),
        ("audit.name", ["audit", "name"]),
        ("audit.category", ["audit", "category"]),
        ("audit.tier", ["audit", "tier"]),
        ("description.what", ["description", "what"]),
    ],
    "high": [
        ("execution.automatable", ["execution", "automatable"]),
        ("execution.severity", ["execution", "severity"]),
        ("description.why_it_matters", ["description", "why_it_matters"]),
        ("procedure.steps", ["procedure", "steps"]),
    ]
}

def get_nested_value(data, keys):
    """Get a nested value from a dict using a list of keys."""
    if not data or not isinstance(data, dict):
        return None

    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current

def check_signals(data):
    """Check if signals.critical OR signals.high exists and has content."""
    signals = get_nested_value(data, ["signals"])
    if not signals or not isinstance(signals, dict):
        return False

    critical = signals.get("critical")
    high = signals.get("high")

    # Check if at least one has content
    has_critical = isinstance(critical, list) and len(critical) > 0
    has_high = isinstance(high, list) and len(high) > 0

    return has_critical or has_high

def check_discovery(data):
    """Check if discovery.code_patterns OR discovery.file_patterns exists."""
    discovery = get_nested_value(data, ["discovery"])
    if not discovery or not isinstance(discovery, dict):
        return False

    code_patterns = discovery.get("code_patterns")
    file_patterns = discovery.get("file_patterns")

    has_code = isinstance(code_patterns, list) and len(code_patterns) > 0
    has_file = isinstance(file_patterns, list) and len(file_patterns) > 0

    return has_code or has_file

def is_empty_value(value):
    """Check if a value is effectively empty."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    return False

def analyze_audit_file(filepath):
    """Analyze a single audit file for completeness issues."""
    issues = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [{
            "audit_id": os.path.basename(filepath),
            "severity": "critical",
            "issue": f"YAML parsing error: {str(e)[:100]}",
            "field": "file",
            "recommended": "Fix YAML syntax errors"
        }]
    except Exception as e:
        return [{
            "audit_id": os.path.basename(filepath),
            "severity": "critical",
            "issue": f"File read error: {str(e)[:100]}",
            "field": "file",
            "recommended": "Ensure file is readable"
        }]

    if not data:
        return [{
            "audit_id": os.path.basename(filepath),
            "severity": "critical",
            "issue": "Empty or null YAML content",
            "field": "file",
            "recommended": "Add required audit content"
        }]

    # Get audit ID for reporting
    audit_id = get_nested_value(data, ["audit", "id"]) or os.path.basename(filepath)

    # Check critical fields
    for field_name, keys in REQUIRED_FIELDS["critical"]:
        value = get_nested_value(data, keys)
        if value is None:
            issues.append({
                "audit_id": audit_id,
                "severity": "critical",
                "issue": "Missing required field",
                "field": field_name,
                "recommended": "Add required field with appropriate value"
            })
        elif is_empty_value(value):
            issues.append({
                "audit_id": audit_id,
                "severity": "medium",
                "issue": "Empty required field",
                "field": field_name,
                "recommended": "Populate field with meaningful content"
            })

    # Check high severity fields
    for field_name, keys in REQUIRED_FIELDS["high"]:
        value = get_nested_value(data, keys)
        if value is None:
            issues.append({
                "audit_id": audit_id,
                "severity": "high",
                "issue": "Missing required field",
                "field": field_name,
                "recommended": "Add required field with appropriate value"
            })
        elif is_empty_value(value):
            issues.append({
                "audit_id": audit_id,
                "severity": "medium",
                "issue": "Empty required field",
                "field": field_name,
                "recommended": "Populate field with meaningful content"
            })

    # Check signals (at least critical or high required)
    if not check_signals(data):
        issues.append({
            "audit_id": audit_id,
            "severity": "critical",
            "issue": "Missing signals - no critical or high level signals defined",
            "field": "signals.critical OR signals.high",
            "recommended": "Add at least one critical or high severity signal"
        })

    # Check discovery patterns
    if not check_discovery(data):
        issues.append({
            "audit_id": audit_id,
            "severity": "high",
            "issue": "Missing discovery patterns",
            "field": "discovery.code_patterns OR discovery.file_patterns",
            "recommended": "Add code patterns or file patterns for discovery"
        })

    return issues

def calculate_field_coverage(all_files_data):
    """Calculate percentage coverage for each field."""
    total = len(all_files_data)
    if total == 0:
        return {}

    coverage = {
        "audit.id": 0,
        "audit.name": 0,
        "audit.category": 0,
        "audit.tier": 0,
        "execution.automatable": 0,
        "execution.severity": 0,
        "description.what": 0,
        "description.why_it_matters": 0,
        "signals": 0,
        "discovery": 0,
        "procedure.steps": 0,
    }

    field_mappings = {
        "audit.id": ["audit", "id"],
        "audit.name": ["audit", "name"],
        "audit.category": ["audit", "category"],
        "audit.tier": ["audit", "tier"],
        "execution.automatable": ["execution", "automatable"],
        "execution.severity": ["execution", "severity"],
        "description.what": ["description", "what"],
        "description.why_it_matters": ["description", "why_it_matters"],
        "procedure.steps": ["procedure", "steps"],
    }

    for data in all_files_data:
        if not data:
            continue

        for field_name, keys in field_mappings.items():
            value = get_nested_value(data, keys)
            if value is not None and not is_empty_value(value):
                coverage[field_name] += 1

        if check_signals(data):
            coverage["signals"] += 1

        if check_discovery(data):
            coverage["discovery"] += 1

    # Convert to percentages
    for field in coverage:
        coverage[field] = round((coverage[field] / total) * 100, 2)

    return coverage

def main():
    print("Starting completeness meta-audit...")

    # Find all YAML files
    audit_files = []
    for root, dirs, files in os.walk(AUDITS_DIR):
        for file in files:
            if file.endswith('.yaml'):
                audit_files.append(os.path.join(root, file))

    print(f"Found {len(audit_files)} audit files")

    all_issues = []
    all_files_data = []
    files_with_issues = set()
    fully_complete_count = 0

    for filepath in audit_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            all_files_data.append(data)
        except:
            all_files_data.append(None)

        issues = analyze_audit_file(filepath)
        if issues:
            all_issues.extend(issues)
            files_with_issues.add(filepath)
        else:
            fully_complete_count += 1

    # Count issues by severity
    severity_counts = defaultdict(int)
    for issue in all_issues:
        severity_counts[issue["severity"]] += 1

    # Calculate field coverage
    field_coverage = calculate_field_coverage(all_files_data)

    # Calculate stats
    total_audits = len(audit_files)
    needs_remediation = len(files_with_issues)
    partially_complete = needs_remediation  # Files with issues but not fully broken

    # Files with only medium/low issues are partially complete
    critical_high_files = set()
    for issue in all_issues:
        if issue["severity"] in ["critical", "high"]:
            critical_high_files.add(issue["audit_id"])

    pass_rate = round(fully_complete_count / total_audits, 4) if total_audits > 0 else 0.0

    # Build report
    report = {
        "dimension_report": {
            "dimension": "completeness",
            "audits_analyzed": total_audits,
            "generated_at": datetime.now().isoformat(),
            "findings": {
                "critical": severity_counts.get("critical", 0),
                "high": severity_counts.get("high", 0),
                "medium": severity_counts.get("medium", 0),
                "low": severity_counts.get("low", 0),
            },
            "field_coverage": field_coverage,
            "issues": all_issues,
            "summary": {
                "pass_rate": pass_rate,
                "needs_remediation": needs_remediation,
                "fully_complete": fully_complete_count,
                "partially_complete": partially_complete,
            }
        }
    }

    # Write report
    output_path = "/mnt/walnut-drive/dev/audits/meta-audit/completeness-report.yaml"
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(report, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)

    print(f"\nReport written to: {output_path}")
    print(f"\n=== Summary ===")
    print(f"Audits analyzed: {total_audits}")
    print(f"Fully complete: {fully_complete_count}")
    print(f"Needs remediation: {needs_remediation}")
    print(f"Pass rate: {pass_rate:.2%}")
    print(f"\nFindings by severity:")
    print(f"  Critical: {severity_counts.get('critical', 0)}")
    print(f"  High: {severity_counts.get('high', 0)}")
    print(f"  Medium: {severity_counts.get('medium', 0)}")
    print(f"  Low: {severity_counts.get('low', 0)}")
    print(f"\nField Coverage:")
    for field, pct in field_coverage.items():
        print(f"  {field}: {pct}%")

if __name__ == "__main__":
    main()
