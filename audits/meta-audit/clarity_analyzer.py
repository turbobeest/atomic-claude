#!/usr/bin/env python3
"""
CLARITY Meta-Audit Analyzer
Analyzes all audit files for clarity issues in descriptions, signals, and remediation steps.
"""

import os
import re
import yaml
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple

# Vague terms to detect
VAGUE_TERMS = [
    r'\bvarious\b',
    r'\betc\b\.?',
    r'\band so on\b',
    r'\bsome\b',
    r'\bmight\b',
    r'\bpossibly\b',
    r'\bmaybe\b',
    r'\bperhaps\b',
    r'\bstuff\b',
    r'\bthings\b',
    r'\bsomehow\b',
    r'\bkind of\b',
    r'\bsort of\b',
    r'\ba lot\b',
    r'\bmany\b(?!\s+(of|different|types|users|systems|applications|organizations|services|teams|files))',
    r'\bseveral\b(?!\s+(of|different|types|areas|aspects|steps|factors|components))',
]

# Pronouns without clear antecedents (at start of sentence)
PRONOUN_STARTS = [
    r'^It\s',
    r'^This\s(?!audit|signal|check|remediation|issue|finding)',
    r'^They\s',
    r'^These\s(?!steps|issues|findings|signals|patterns|practices)',
]

# Non-actionable remediation patterns
NON_ACTIONABLE = [
    r'^Consider\s',
    r'^You\s(might|may|could|should)\s',
    r'^Try\sto\s',
    r'^Look\sinto\s',
    r'^Think\sabout\s',
    r'^Be\saware\s',
    r'^Keep\sin\smind\s',
]

MIN_DESCRIPTION_LENGTH = 50
MIN_REMEDIATION_LENGTH = 20
MIN_SIGNAL_LENGTH = 15


def load_yaml_file(filepath: Path) -> Optional[Dict]:
    """Load a YAML file, handling errors gracefully."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return yaml.safe_load(content)
    except yaml.YAMLError as e:
        return {'_parse_error': str(e)}
    except Exception as e:
        return {'_read_error': str(e)}


def check_vague_terms(text: str) -> List[str]:
    """Check for vague terms in text."""
    if not text:
        return []
    found = []
    for pattern in VAGUE_TERMS:
        if re.search(pattern, text, re.IGNORECASE):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                found.append(match.group(0))
    return found


def check_pronoun_starts(text: str) -> List[str]:
    """Check for pronouns without clear antecedents at start of sentences."""
    if not text:
        return []
    found = []
    sentences = re.split(r'[.!?]\s+', text)
    for sentence in sentences:
        for pattern in PRONOUN_STARTS:
            if re.match(pattern, sentence.strip()):
                found.append(sentence.strip()[:50] + '...' if len(sentence) > 50 else sentence.strip())
    return found


def check_remediation_actionable(text: str) -> List[str]:
    """Check if remediation is actionable (not vague advice)."""
    if not text:
        return []
    found = []
    sentences = re.split(r'[.!?]\s+', text)
    for sentence in sentences:
        for pattern in NON_ACTIONABLE:
            if re.match(pattern, sentence.strip(), re.IGNORECASE):
                found.append(sentence.strip()[:60] + '...' if len(sentence) > 60 else sentence.strip())
    return found


def check_signal_description(signal_text: str) -> List[str]:
    """Check if signal description clearly defines what to look for."""
    if not signal_text:
        return ["Signal description is empty"]
    issues = []

    stripped = signal_text.strip()

    # Check if it starts with pronoun/article that makes it unclear
    bad_starts = [r'^(A |An |The |It |This |That |There )']
    for pattern in bad_starts:
        if re.match(pattern, stripped):
            match = re.match(pattern, stripped)
            issues.append(f"Signal starts with article/pronoun: '{match.group(0).strip()}'")

    # Check minimum length for clarity
    if len(stripped) < MIN_SIGNAL_LENGTH:
        issues.append(f"Signal too brief ({len(stripped)} chars): '{stripped}'")

    return issues


def analyze_audit_file(filepath: Path) -> Dict[str, Any]:
    """Analyze a single audit file for clarity issues."""
    issues = []
    data = load_yaml_file(filepath)

    if not data:
        return {'issues': [{'severity': 'critical', 'issue': 'Empty file', 'field': 'file'}]}

    if '_parse_error' in data:
        return {'issues': [{'severity': 'critical', 'issue': f"YAML parse error: {data['_parse_error'][:100]}", 'field': 'file'}]}

    if '_read_error' in data:
        return {'issues': [{'severity': 'critical', 'issue': f"Read error: {data['_read_error'][:100]}", 'field': 'file'}]}

    audit_id = data.get('audit', {}).get('id', filepath.stem)

    # Check description.what
    description = data.get('description', {})
    what = description.get('what', '')
    if isinstance(what, str):
        what_text = what.strip()

        # Check minimum length
        if len(what_text) < MIN_DESCRIPTION_LENGTH:
            issues.append({
                'severity': 'high',
                'issue': f"description.what too short ({len(what_text)} chars, minimum {MIN_DESCRIPTION_LENGTH})",
                'field': 'description.what',
                'current': what_text[:100] if what_text else '(empty)',
                'recommended': 'Expand description to clearly explain what this audit examines'
            })

        # Check vague terms
        vague = check_vague_terms(what_text)
        if vague:
            issues.append({
                'severity': 'medium',
                'issue': f"description.what contains vague terms: {', '.join(set(vague))}",
                'field': 'description.what',
                'current': what_text[:100] + '...' if len(what_text) > 100 else what_text,
                'recommended': 'Replace vague terms with specific, concrete language'
            })

        # Check pronoun issues
        pronouns = check_pronoun_starts(what_text)
        if pronouns:
            issues.append({
                'severity': 'low',
                'issue': f"description.what has unclear pronoun references",
                'field': 'description.what',
                'current': pronouns[0],
                'recommended': 'Replace pronouns with specific nouns for clarity'
            })

    # Check description.why_it_matters
    why = description.get('why_it_matters', '')
    if isinstance(why, str):
        why_text = why.strip()

        if len(why_text) < MIN_DESCRIPTION_LENGTH:
            issues.append({
                'severity': 'high',
                'issue': f"description.why_it_matters too short ({len(why_text)} chars, minimum {MIN_DESCRIPTION_LENGTH})",
                'field': 'description.why_it_matters',
                'current': why_text[:100] if why_text else '(empty)',
                'recommended': 'Expand to clearly explain business/technical impact'
            })

        vague = check_vague_terms(why_text)
        if vague:
            issues.append({
                'severity': 'medium',
                'issue': f"description.why_it_matters contains vague terms: {', '.join(set(vague))}",
                'field': 'description.why_it_matters',
                'current': why_text[:100] + '...' if len(why_text) > 100 else why_text,
                'recommended': 'Use specific, measurable impact statements'
            })

    # Check signals
    signals = data.get('signals', {})
    for severity_level in ['critical', 'high', 'medium', 'low', 'positive']:
        signal_list = signals.get(severity_level, [])
        if not isinstance(signal_list, list):
            continue
        for idx, signal in enumerate(signal_list):
            if not isinstance(signal, dict):
                continue

            signal_id = signal.get('id', f'{severity_level}-{idx}')
            signal_text = signal.get('signal', '')

            # Check signal description clarity
            signal_issues = check_signal_description(signal_text)
            for sig_issue in signal_issues:
                issues.append({
                    'severity': 'medium' if 'brief' in sig_issue else 'low',
                    'issue': f"Signal {signal_id}: {sig_issue}",
                    'field': f'signals.{severity_level}[{idx}].signal',
                    'current': signal_text[:80] if signal_text else '(empty)',
                    'recommended': 'Start signal with clear noun/verb phrase describing what to look for'
                })

            # Check for missing explanation on critical/high signals
            explanation = signal.get('explanation', '')
            if severity_level in ['critical', 'high']:
                if not explanation or (isinstance(explanation, str) and len(explanation.strip()) < 30):
                    issues.append({
                        'severity': 'high',
                        'issue': f"Signal {signal_id}: {severity_level}-severity signal lacks adequate explanation",
                        'field': f'signals.{severity_level}[{idx}].explanation',
                        'current': explanation[:50] if explanation else '(missing)',
                        'recommended': 'Add detailed explanation of why this signal matters and its impact'
                    })

            # Check remediation actionability
            remediation = signal.get('remediation', '')
            if isinstance(remediation, str) and remediation.strip():
                rem_text = remediation.strip()

                # Check if remediation is too short
                if len(rem_text) < MIN_REMEDIATION_LENGTH:
                    issues.append({
                        'severity': 'medium',
                        'issue': f"Signal {signal_id}: remediation too brief ({len(rem_text)} chars)",
                        'field': f'signals.{severity_level}[{idx}].remediation',
                        'current': rem_text,
                        'recommended': 'Provide specific, actionable steps for remediation'
                    })

                # Check for non-actionable language
                non_actionable = check_remediation_actionable(remediation)
                if non_actionable:
                    issues.append({
                        'severity': 'medium',
                        'issue': f"Signal {signal_id}: remediation uses non-actionable language",
                        'field': f'signals.{severity_level}[{idx}].remediation',
                        'current': non_actionable[0],
                        'recommended': 'Use direct imperative language: "Implement X", "Configure Y", "Add Z"'
                    })

                # Check if remediation is too vague
                vague = check_vague_terms(remediation)
                if vague:
                    issues.append({
                        'severity': 'low',
                        'issue': f"Signal {signal_id}: remediation contains vague terms: {', '.join(set(vague))}",
                        'field': f'signals.{severity_level}[{idx}].remediation',
                        'current': remediation[:80] + '...' if len(remediation) > 80 else remediation,
                        'recommended': 'Replace vague terms with specific actions and values'
                    })
            elif severity_level in ['critical', 'high', 'medium']:
                # Missing remediation is a problem for actionable signals
                issues.append({
                    'severity': 'high' if severity_level in ['critical', 'high'] else 'medium',
                    'issue': f"Signal {signal_id}: missing remediation guidance",
                    'field': f'signals.{severity_level}[{idx}].remediation',
                    'current': '(empty)',
                    'recommended': 'Add specific remediation steps'
                })

    return {'audit_id': audit_id, 'issues': issues}


def main():
    """Main analysis function."""
    audits_dir = Path('/mnt/walnut-drive/dev/audits/audits')
    output_file = Path('/mnt/walnut-drive/dev/audits/meta-audit/clarity-report.yaml')

    all_issues = []
    total_files = 0
    files_with_issues = 0
    files_with_high_issues = 0
    severity_counts = defaultdict(int)
    issue_type_counts = defaultdict(int)
    category_issues = defaultdict(lambda: defaultdict(int))

    # Find all YAML files
    yaml_files = list(audits_dir.rglob('*.yaml'))
    total_files = len(yaml_files)

    print(f"Analyzing {total_files} audit files...")

    for filepath in yaml_files:
        result = analyze_audit_file(filepath)
        audit_id = result.get('audit_id', filepath.stem)

        if result['issues']:
            files_with_issues += 1
            has_high = False
            for issue in result['issues']:
                severity = issue.get('severity', 'low')
                severity_counts[severity] += 1

                if severity in ['critical', 'high']:
                    has_high = True

                # Track by category
                category = audit_id.split('.')[0] if '.' in audit_id else 'unknown'
                category_issues[category][severity] += 1

                # Categorize issue type
                issue_text = issue.get('issue', '')
                if 'too short' in issue_text or 'too brief' in issue_text:
                    issue_type_counts['description_too_short'] += 1
                elif 'vague terms' in issue_text:
                    issue_type_counts['vague_terms'] += 1
                elif 'pronoun' in issue_text:
                    issue_type_counts['pronoun_issues'] += 1
                elif 'non-actionable' in issue_text:
                    issue_type_counts['non_actionable_remediation'] += 1
                elif 'missing remediation' in issue_text:
                    issue_type_counts['missing_remediation'] += 1
                elif 'lacks adequate explanation' in issue_text:
                    issue_type_counts['missing_explanation'] += 1
                elif 'Signal' in issue_text and ('starts' in issue_text):
                    issue_type_counts['signal_description_issues'] += 1
                elif 'parse error' in issue_text.lower():
                    issue_type_counts['yaml_parse_errors'] += 1
                else:
                    issue_type_counts['other'] += 1

                all_issues.append({
                    'audit_id': audit_id,
                    'severity': severity,
                    'issue': issue['issue'],
                    'field': issue.get('field', ''),
                    'current': issue.get('current', ''),
                    'recommended': issue.get('recommended', '')
                })

            if has_high:
                files_with_high_issues += 1

    # Sort issues by severity (critical first)
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    all_issues.sort(key=lambda x: severity_order.get(x['severity'], 4))

    # Calculate pass rate
    pass_rate = (total_files - files_with_issues) / total_files if total_files > 0 else 0.0
    high_pass_rate = (total_files - files_with_high_issues) / total_files if total_files > 0 else 0.0

    # Get top issues
    top_issues = sorted(issue_type_counts.items(), key=lambda x: -x[1])[:5]
    top_issues_list = [f"{issue_type.replace('_', ' ').title()} ({count} occurrences)" for issue_type, count in top_issues]

    # Format category summary
    category_summary = {}
    for cat, counts in sorted(category_issues.items(), key=lambda x: sum(x[1].values()), reverse=True):
        category_summary[cat] = dict(counts)

    # Build report
    report = {
        'dimension_report': {
            'dimension': 'clarity',
            'audits_analyzed': total_files,
            'findings': {
                'critical': severity_counts['critical'],
                'high': severity_counts['high'],
                'medium': severity_counts['medium'],
                'low': severity_counts['low']
            },
            'issues': all_issues[:1000],  # Limit to 1000 most important issues
            'summary': {
                'pass_rate': round(pass_rate, 3),
                'high_severity_pass_rate': round(high_pass_rate, 3),
                'needs_remediation': files_with_issues,
                'needs_high_priority_remediation': files_with_high_issues,
                'top_issues': top_issues_list,
                'issue_breakdown': dict(issue_type_counts),
                'issues_by_category': category_summary
            }
        }
    }

    # Write report
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(report, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)

    print(f"\nAnalysis complete!")
    print(f"Total files analyzed: {total_files}")
    print(f"Files with issues: {files_with_issues}")
    print(f"Files with high/critical issues: {files_with_high_issues}")
    print(f"Pass rate (all issues): {pass_rate:.1%}")
    print(f"Pass rate (high+ issues only): {high_pass_rate:.1%}")
    print(f"\nSeverity breakdown:")
    print(f"  Critical: {severity_counts['critical']}")
    print(f"  High: {severity_counts['high']}")
    print(f"  Medium: {severity_counts['medium']}")
    print(f"  Low: {severity_counts['low']}")
    print(f"\nIssue type breakdown:")
    for issue_type, count in sorted(issue_type_counts.items(), key=lambda x: -x[1]):
        print(f"  {issue_type}: {count}")
    print(f"\nReport written to: {output_file}")


if __name__ == '__main__':
    main()
