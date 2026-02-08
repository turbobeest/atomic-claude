#!/usr/bin/env python3
"""
Alignment Meta-Audit Analyzer
Analyzes all audit files for structural alignment issues.
"""

import os
import yaml
import re
from collections import defaultdict
from pathlib import Path
from difflib import SequenceMatcher
import json

AUDIT_DIR = "/mnt/walnut-drive/dev/audits/audits"

def load_yaml_safe(filepath):
    """Load YAML file with error handling."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return yaml.safe_load(content), None
    except yaml.YAMLError as e:
        return None, f"YAML parse error: {str(e)[:100]}"
    except Exception as e:
        return None, f"Read error: {str(e)[:100]}"

def extract_path_components(filepath):
    """Extract category, subcategory from file path."""
    # Path: /mnt/walnut-drive/dev/audits/audits/10-testing-quality-assurance/unit-testing/test.yaml
    # We want: category_dir = "10-testing-quality-assurance", expected_category = "testing-quality-assurance"
    #          expected_subcategory = "unit-testing"

    # Get path relative to AUDIT_DIR
    rel_path = os.path.relpath(filepath, AUDIT_DIR)
    parts = rel_path.split(os.sep)

    if len(parts) < 1:
        return None

    # Category dir with number prefix: 10-testing-quality-assurance
    category_dir = parts[0]

    # Remove number prefix for comparison
    category_match = re.match(r'^(\d+)-(.+)$', category_dir)
    if category_match:
        category_number = int(category_match.group(1))
        expected_category = category_match.group(2)
    else:
        category_number = None
        expected_category = category_dir

    # Subcategory is second directory (if exists)
    # len(parts) > 2 means: category_dir/subcategory_dir/file.yaml
    expected_subcategory = parts[1] if len(parts) > 2 else None
    has_subcategory_dir = len(parts) > 2

    # Filename without extension
    filename = parts[-1].replace('.yaml', '')

    return {
        'category_dir': category_dir,
        'category_number': category_number,
        'expected_category': expected_category,
        'expected_subcategory': expected_subcategory,
        'has_subcategory_dir': has_subcategory_dir,
        'filename': filename,
        'rel_path': rel_path
    }

def check_id_format(audit_id, path_info, audit_category, audit_subcategory):
    """Check if audit ID matches expected format and content matches path."""
    issues = []

    if not audit_id:
        return [("Missing audit ID", "critical")]

    # Expected format: {category}.{subcategory}.{name}
    parts = audit_id.split('.')
    if len(parts) < 2:
        issues.append((f"ID has fewer than 2 parts: {audit_id}", "high"))
        return issues

    id_category = parts[0]
    id_subcategory = parts[1] if len(parts) >= 2 else None

    # Check if ID category matches the file's category field
    if id_category != audit_category:
        issues.append((f"ID category '{id_category}' doesn't match audit.category '{audit_category}'", "high"))

    # Check if ID subcategory matches the file's subcategory field
    if len(parts) >= 2 and id_subcategory != audit_subcategory:
        issues.append((f"ID subcategory '{id_subcategory}' doesn't match audit.subcategory '{audit_subcategory}'", "high"))

    return issues

def calculate_similarity(s1, s2):
    """Calculate string similarity ratio."""
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

def assess_tier_complexity(audit_data):
    """Assess if tier matches complexity based on signals, steps, knowledge sources."""
    tier = audit_data.get('audit', {}).get('tier', 'unknown')

    signals = audit_data.get('signals', {})
    signal_count = sum(len(signals.get(k, [])) for k in ['critical', 'high', 'medium', 'low', 'positive'])

    procedure = audit_data.get('procedure', {})
    step_count = len(procedure.get('steps', []))

    knowledge = audit_data.get('knowledge_sources', {})
    knowledge_count = (len(knowledge.get('specifications', [])) +
                       len(knowledge.get('guides', [])) +
                       len(knowledge.get('learning_resources', [])))

    # Scoring: focused (simple), expert (moderate), phd (complex)
    complexity_score = signal_count * 1 + step_count * 2 + knowledge_count * 1.5

    tier_expected = 'focused'
    if complexity_score > 25:
        tier_expected = 'phd'
    elif complexity_score > 12:
        tier_expected = 'expert'

    # Normalize tier names (some files use non-standard tier names)
    tier_normalized = tier.lower()
    if tier_normalized in ['standard', 'intermediate']:
        tier_normalized = 'focused'
    elif tier_normalized in ['advanced', 'comprehensive']:
        tier_normalized = 'expert'

    return {
        'actual_tier': tier,
        'normalized_tier': tier_normalized,
        'expected_tier': tier_expected,
        'complexity_score': complexity_score,
        'signal_count': signal_count,
        'step_count': step_count,
        'knowledge_count': knowledge_count,
        'mismatch': tier_normalized != tier_expected and tier != 'unknown'
    }

def main():
    issues = []
    duplicates = []
    parse_errors = []
    audits_analyzed = 0

    # Track audits for duplicate detection
    audit_names = {}  # name -> list of (id, filepath, category)
    audit_descriptions = {}  # id -> description

    category_stats = defaultdict(lambda: {'total': 0, 'mismatches': 0})
    tier_stats = defaultdict(int)
    tier_mismatches = 0

    # Track category/subcategory matches (actual alignments)
    category_matches = 0
    subcategory_matches = 0
    id_format_valid = 0

    # Track real misalignments: where audit.category doesn't match directory
    real_category_mismatches = []
    real_subcategory_mismatches = []
    real_id_mismatches = []

    # Track flat vs nested categories
    flat_categories = set()
    nested_categories = set()

    # Walk through all YAML files
    for root, dirs, files in os.walk(AUDIT_DIR):
        for filename in files:
            if not filename.endswith('.yaml'):
                continue

            filepath = os.path.join(root, filename)
            audits_analyzed += 1

            # Load YAML
            data, error = load_yaml_safe(filepath)
            if error:
                parse_errors.append({
                    'filepath': filepath,
                    'error': error
                })
                continue

            if not data or 'audit' not in data:
                parse_errors.append({
                    'filepath': filepath,
                    'error': 'No audit section found'
                })
                continue

            audit = data.get('audit', {})
            audit_id = audit.get('id', '')
            audit_name = audit.get('name', '')
            audit_category = audit.get('category', '')
            audit_subcategory = audit.get('subcategory', '')
            audit_tier = audit.get('tier', 'unknown')
            category_number = audit.get('category_number', None)

            # Extract path info
            path_info = extract_path_components(filepath)
            if not path_info:
                issues.append({
                    'audit_id': audit_id or filepath,
                    'severity': 'medium',
                    'issue': 'Could not parse directory structure',
                    'field': 'file_path',
                    'expected': 'Standard audit path structure',
                    'actual': filepath,
                    'recommended': 'Move file to proper category/subcategory directory'
                })
                continue

            # Track category structure
            if path_info['has_subcategory_dir']:
                nested_categories.add(path_info['category_dir'])
            else:
                flat_categories.add(path_info['category_dir'])

            category_stats[path_info['category_dir']]['total'] += 1
            tier_stats[audit_tier] += 1

            # Check 1: Category matches directory (without number prefix)
            if audit_category == path_info['expected_category']:
                category_matches += 1
            else:
                real_category_mismatches.append({
                    'audit_id': audit_id,
                    'severity': 'high',
                    'issue': 'Category mismatch',
                    'field': 'audit.category',
                    'expected': path_info['expected_category'],
                    'actual': audit_category,
                    'file_path': filepath,
                    'recommended': f"Update category to '{path_info['expected_category']}'"
                })
                category_stats[path_info['category_dir']]['mismatches'] += 1

            # Check 2: Subcategory matches directory (only if nested structure)
            if path_info['has_subcategory_dir']:
                if audit_subcategory == path_info['expected_subcategory']:
                    subcategory_matches += 1
                else:
                    real_subcategory_mismatches.append({
                        'audit_id': audit_id,
                        'severity': 'high',
                        'issue': 'Subcategory mismatch',
                        'field': 'audit.subcategory',
                        'expected': path_info['expected_subcategory'],
                        'actual': audit_subcategory,
                        'file_path': filepath,
                        'recommended': f"Update subcategory to '{path_info['expected_subcategory']}'"
                    })
            else:
                # Flat category - subcategory should still be defined but no directory check
                subcategory_matches += 1  # Don't penalize flat structure

            # Check 3: ID format consistency
            id_issues = check_id_format(audit_id, path_info, audit_category, audit_subcategory)
            if not id_issues:
                id_format_valid += 1
            else:
                for id_issue, severity in id_issues:
                    real_id_mismatches.append({
                        'audit_id': audit_id,
                        'severity': severity,
                        'issue': 'ID format mismatch',
                        'field': 'audit.id',
                        'expected': f"{audit_category}.{audit_subcategory}.{path_info['filename']}",
                        'actual': audit_id,
                        'file_path': filepath,
                        'recommended': id_issue
                    })

            # Check 4: Tier matches complexity
            tier_check = assess_tier_complexity(data)
            if tier_check['mismatch']:
                tier_mismatches += 1
                issues.append({
                    'audit_id': audit_id,
                    'severity': 'low',  # Tier is advisory
                    'issue': 'Tier complexity mismatch',
                    'field': 'audit.tier',
                    'expected': tier_check['expected_tier'],
                    'actual': tier_check['actual_tier'],
                    'file_path': filepath,
                    'recommended': f"Consider changing tier to '{tier_check['expected_tier']}' (complexity score: {tier_check['complexity_score']:.1f})"
                })

            # Check 5: Category number consistency
            expected_num = path_info['category_number']
            if category_number and expected_num and category_number != expected_num:
                issues.append({
                    'audit_id': audit_id,
                    'severity': 'medium',
                    'issue': 'Category number mismatch',
                    'field': 'audit.category_number',
                    'expected': expected_num,
                    'actual': category_number,
                    'file_path': filepath,
                    'recommended': f"Update category_number to {expected_num}"
                })

            # Track for duplicate detection
            name_key = audit_name.lower().strip() if audit_name else ''
            if name_key:
                if name_key not in audit_names:
                    audit_names[name_key] = []
                audit_names[name_key].append((audit_id, filepath, audit_category))

            # Store description for semantic duplicate detection
            desc = data.get('description', {})
            if isinstance(desc, dict):
                audit_descriptions[audit_id] = desc.get('what', '')[:200]

    # Add real mismatches to issues
    issues.extend(real_category_mismatches)
    issues.extend(real_subcategory_mismatches)
    issues.extend(real_id_mismatches)

    # Find duplicates by exact name match
    for name, occurrences in audit_names.items():
        if len(occurrences) > 1:
            # Check if they're in different categories (potential misplacement)
            categories = set(occ[2] for occ in occurrences)
            if len(categories) > 1:
                duplicates.append({
                    'audit_ids': [occ[0] for occ in occurrences],
                    'similarity': 'high',
                    'reason': f"Exact name match '{name}' across categories: {list(categories)}"
                })
            else:
                # Same name in same category - potential duplicate within category
                duplicates.append({
                    'audit_ids': [occ[0] for occ in occurrences],
                    'similarity': 'high',
                    'reason': f"Exact name match '{name}' within category: {list(categories)[0]}"
                })

    # Find similar names (potential duplicates) - limit checks for performance
    audit_id_list = list(audit_descriptions.keys())[:500]  # Sample for performance
    for i, id1 in enumerate(audit_id_list):
        for id2 in audit_id_list[i+1:]:
            # Extract names from IDs
            name1 = id1.split('.')[-1] if '.' in id1 else id1
            name2 = id2.split('.')[-1] if '.' in id2 else id2

            similarity = calculate_similarity(name1, name2)
            if similarity > 0.85 and similarity < 1.0:
                # Also check description similarity
                desc_sim = calculate_similarity(
                    audit_descriptions.get(id1, ''),
                    audit_descriptions.get(id2, '')
                )
                if desc_sim > 0.7:
                    duplicates.append({
                        'audit_ids': [id1, id2],
                        'similarity': 'medium',
                        'reason': f"Similar name ({similarity:.0%}) and description ({desc_sim:.0%})"
                    })

    # Categorize issues by severity
    severity_counts = defaultdict(int)
    for issue in issues:
        severity_counts[issue['severity']] += 1

    # Count unique issues
    category_mismatches = len(real_category_mismatches)
    subcategory_mismatches = len(real_subcategory_mismatches)
    id_mismatches = len(real_id_mismatches)

    # Calculate pass rate based on alignment checks
    total_checks = audits_analyzed * 3  # 3 key alignment checks per audit
    failed_checks = category_mismatches + subcategory_mismatches + id_mismatches
    pass_rate = 1.0 - (failed_checks / total_checks) if total_checks > 0 else 0.0

    # Sort issues by severity
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    sorted_issues = sorted(issues, key=lambda x: severity_order.get(x['severity'], 4))

    # Build report
    report = {
        'dimension_report': {
            'dimension': 'alignment',
            'audits_analyzed': audits_analyzed,

            'findings': {
                'critical': severity_counts.get('critical', 0),
                'high': severity_counts.get('high', 0),
                'medium': severity_counts.get('medium', 0),
                'low': severity_counts.get('low', 0)
            },

            'category_analysis': {
                'category_matches': category_matches,
                'subcategory_matches': subcategory_matches,
                'id_format_valid': id_format_valid,
                'misclassified': category_mismatches + subcategory_mismatches,
                'id_mismatches': id_mismatches,
                'potential_duplicates': len(duplicates),
                'tier_mismatches': tier_mismatches,
                'flat_structure_categories': sorted(list(flat_categories)),
                'nested_structure_categories': len(nested_categories)
            },

            'parse_errors': len(parse_errors),

            'tier_distribution': dict(tier_stats),

            'issues': sorted_issues[:100],  # Limit to first 100 issues

            'duplicates': duplicates[:50],  # Limit to first 50 duplicates

            'parse_error_details': parse_errors[:20] if parse_errors else [],

            'summary': {
                'pass_rate': round(pass_rate, 4),
                'needs_remediation': len([i for i in issues if i['severity'] in ['critical', 'high']]),
                'total_issues': len(issues),
                'total_duplicates': len(duplicates),
                'total_parse_errors': len(parse_errors),
                'categories_with_issues': sum(1 for c in category_stats.values() if c['mismatches'] > 0)
            }
        }
    }

    # Write report
    output_path = '/mnt/walnut-drive/dev/audits/meta-audit/alignment-report.yaml'
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(report, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)

    print(f"Alignment report written to {output_path}")
    print(f"\nSummary:")
    print(f"  Audits analyzed: {audits_analyzed}")
    print(f"  Category matches: {category_matches} ({100*category_matches/audits_analyzed:.1f}%)")
    print(f"  Subcategory matches: {subcategory_matches}")
    print(f"  ID format valid: {id_format_valid}")
    print(f"  Total issues: {len(issues)}")
    print(f"  High severity: {severity_counts.get('high', 0)}")
    print(f"  Parse errors: {len(parse_errors)}")
    print(f"  Potential duplicates: {len(duplicates)}")
    print(f"  Pass rate: {pass_rate:.2%}")
    print(f"\n  Flat structure categories: {len(flat_categories)}")
    print(f"  Nested structure categories: {len(nested_categories)}")

if __name__ == '__main__':
    main()
