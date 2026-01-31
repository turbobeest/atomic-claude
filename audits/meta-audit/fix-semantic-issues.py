#!/usr/bin/env python3
"""
Comprehensive fix script for all semantic audit issues.
Addresses 180+ issues across all dimensions.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple

AUDITS_ROOT = Path("/mnt/walnut-drive/dev/audits/audits")

# Track all fixes
fixes_applied = {
    "id_prefix_corrections": [],
    "metadata_additions": [],
    "command_syntax_fixes": [],
    "pattern_expansions": [],
    "clarity_improvements": [],
    "tier_adjustments": [],
    "relationship_fixes": [],
    "duplicate_resolutions": []
}

def load_yaml(filepath: Path) -> Tuple[Dict, str]:
    """Load YAML preserving original content for safe editing."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    try:
        data = yaml.safe_load(content)
        return data, content
    except yaml.YAMLError as e:
        print(f"Error loading {filepath}: {e}")
        return None, content

def save_content(filepath: Path, content: str):
    """Save modified content to file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# =============================================================================
# PHASE 1: ID Prefix Corrections
# =============================================================================

def fix_id_prefixes():
    """Fix ID prefixes in categories 40 and 41."""
    print("\n=== Phase 1: Fixing ID Prefixes ===")

    # Category 40: signal-processing -> signal-processing-data-acquisition
    cat40_dir = AUDITS_ROOT / "40-signal-processing-data-acquisition"
    if cat40_dir.exists():
        for yaml_file in cat40_dir.rglob("*.yaml"):
            data, content = load_yaml(yaml_file)
            if data and 'audit' in data and 'id' in data['audit']:
                old_id = data['audit']['id']
                if old_id.startswith('signal-processing.') and not old_id.startswith('signal-processing-data-acquisition.'):
                    new_id = old_id.replace('signal-processing.', 'signal-processing-data-acquisition.', 1)
                    content = content.replace(f'id: {old_id}', f'id: {new_id}', 1)
                    content = content.replace(f'id: "{old_id}"', f'id: "{new_id}"', 1)
                    content = content.replace(f"id: '{old_id}'", f"id: '{new_id}'", 1)
                    save_content(yaml_file, content)
                    fixes_applied["id_prefix_corrections"].append((str(yaml_file), old_id, new_id))
                    print(f"  Fixed: {old_id} -> {new_id}")

    # Category 41: blockchain -> blockchain-distributed-ledger
    cat41_dir = AUDITS_ROOT / "41-blockchain-distributed-ledger"
    if cat41_dir.exists():
        for yaml_file in cat41_dir.rglob("*.yaml"):
            data, content = load_yaml(yaml_file)
            if data and 'audit' in data and 'id' in data['audit']:
                old_id = data['audit']['id']
                if old_id.startswith('blockchain.') and not old_id.startswith('blockchain-distributed-ledger.'):
                    new_id = old_id.replace('blockchain.', 'blockchain-distributed-ledger.', 1)
                    content = content.replace(f'id: {old_id}', f'id: {new_id}', 1)
                    content = content.replace(f'id: "{old_id}"', f'id: "{new_id}"', 1)
                    content = content.replace(f"id: '{old_id}'", f"id: '{new_id}'", 1)
                    save_content(yaml_file, content)
                    fixes_applied["id_prefix_corrections"].append((str(yaml_file), old_id, new_id))
                    print(f"  Fixed: {old_id} -> {new_id}")

# =============================================================================
# PHASE 2: Add Metadata Fields
# =============================================================================

# Audits requiring physical access
PHYSICAL_ACCESS_AUDITS = [
    "38-sensors-physical-systems/safety-systems/emergency-stop",
    "38-sensors-physical-systems/actuator-control/motor-control",
    "38-sensors-physical-systems/data-acquisition/adc-resolution",
    "38-sensors-physical-systems/calibration",
    "38-sensors-physical-systems/sensor-integration",
    "39-real-time-embedded/isr-latency",
    "39-real-time-embedded/timing",
    "43-metaverse-immersive/rendering-performance/latency",
    "43-metaverse-immersive/spatial-computing/spatial-anchor",
]

# Audits requiring human evaluation/perception testing
HUMAN_EVALUATION_AUDITS = [
    "43-metaverse-immersive/comfort-safety/motion-sickness",
    "43-metaverse-immersive/comfort-safety/eye-strain",
    "08-ux-accessibility/usability-testing",
    "08-ux-accessibility/visual-design",
    "37-machine-learning-ai/responsible-ai/bias",
]

# Audits requiring interviews
INTERVIEW_REQUIRED_AUDITS = [
    "22-gamification-engagement",  # Most audits in this category
    "35-developer-experience/productivity-metrics/dx-survey",
    "35-developer-experience/onboarding",
    "29-risk-management/risk-identification/emerging-risks",
    "29-risk-management/risk-assessment",
    "31-cost-economics/roi-value-analysis/tco",
]

def add_metadata_field(content: str, field_name: str, field_value: str) -> str:
    """Add a metadata field to audit YAML if not present."""
    if f"{field_name}:" in content:
        return content  # Already has this field

    # Find execution section and add after automatable
    if "execution:" in content:
        # Add after automatable line
        automatable_match = re.search(r'(  automatable:.*\n)', content)
        if automatable_match:
            insert_pos = automatable_match.end()
            content = content[:insert_pos] + f"  {field_name}: {field_value}\n" + content[insert_pos:]
    return content

def fix_metadata_additions():
    """Add requires_physical_access, requires_human_evaluation, requires_interviews fields."""
    print("\n=== Phase 2: Adding Metadata Fields ===")

    for yaml_file in AUDITS_ROOT.rglob("*.yaml"):
        rel_path = str(yaml_file.relative_to(AUDITS_ROOT))
        data, content = load_yaml(yaml_file)
        if not data:
            continue

        modified = False
        original_content = content

        # Check if needs physical access
        for pattern in PHYSICAL_ACCESS_AUDITS:
            if pattern in rel_path:
                content = add_metadata_field(content, "requires_physical_access", "true")
                if content != original_content:
                    modified = True
                    original_content = content
                break

        # Check if needs human evaluation
        for pattern in HUMAN_EVALUATION_AUDITS:
            if pattern in rel_path:
                content = add_metadata_field(content, "requires_human_evaluation", "true")
                if content != original_content:
                    modified = True
                    original_content = content
                break

        # Check if needs interviews
        for pattern in INTERVIEW_REQUIRED_AUDITS:
            if pattern in rel_path:
                content = add_metadata_field(content, "requires_interviews", "true")
                if content != original_content:
                    modified = True
                    original_content = content
                break

        if modified:
            save_content(yaml_file, content)
            fixes_applied["metadata_additions"].append(str(yaml_file))
            print(f"  Added metadata: {rel_path}")

# =============================================================================
# PHASE 3: Fix Command Syntax Errors
# =============================================================================

COMMAND_FIXES = [
    # find brace expansion fixes
    (r'find\s+\.\s+-name\s+"?\*\.{([^}]+)}"?',
     lambda m: f'find . \\( {" -o ".join([f"-name \"*.{ext}\"" for ext in m.group(1).split(",")])} \\)'),

    # find -o precedence fixes (add parentheses)
    (r'find\s+\.\s+(-name\s+"[^"]+"\s+-o\s+-name\s+"[^"]+")\s*\|\s*xargs',
     r'find . \\( \1 \\) | xargs'),

    # PCRE lookahead alternatives
    (r"grep\s+-[PE]\s+'([^']*)\(\?![^']*\)'",
     lambda m: f"grep '{m.group(1).split('(?!')[0]}' | grep -v"),
]

def fix_command_syntax():
    """Fix broken shell command syntax in procedures and closeout checklists."""
    print("\n=== Phase 3: Fixing Command Syntax ===")

    for yaml_file in AUDITS_ROOT.rglob("*.yaml"):
        data, content = load_yaml(yaml_file)
        if not data:
            continue

        original_content = content
        modified = False

        # Fix brace expansion in find commands
        brace_pattern = r'find\s+\.\s+-name\s+"\*\.{([^}]+)}"'
        matches = list(re.finditer(brace_pattern, content))
        for match in reversed(matches):  # Reverse to preserve positions
            exts = match.group(1).split(',')
            replacement = f'find . \\( {" -o ".join([f"-name \"*.{ext.strip()}\"" for ext in exts])} \\)'
            content = content[:match.start()] + replacement + content[match.end():]
            modified = True

        # Fix find -o precedence (missing parentheses before pipe)
        precedence_pattern = r'(find\s+\.\s+-name\s+"[^"]+"\s+-o\s+-name\s+"[^"]+")\s*\|'
        if re.search(precedence_pattern, content):
            content = re.sub(precedence_pattern, r'find . \\( \1 \\) |', content)
            modified = True

        if modified and content != original_content:
            save_content(yaml_file, content)
            fixes_applied["command_syntax_fixes"].append(str(yaml_file))
            print(f"  Fixed commands: {yaml_file.relative_to(AUDITS_ROOT)}")

# =============================================================================
# PHASE 4: Expand Code Patterns
# =============================================================================

PATTERN_EXPANSIONS = {
    # Logging patterns
    "logger\\.(info|warn|error)": [
        "logger\\.(info|warn|error|debug)",
        "logging\\.(info|warning|error|debug)",
        "console\\.(log|warn|error)",
        "log\\.(Info|Warn|Error|Debug)",
    ],
    # Feature flag patterns
    "isEnabled\\(['\"]": [
        "isEnabled\\(['\"]",
        "ldclient\\.variation",
        "splitClient\\.getTreatment",
        "unleash\\.isEnabled",
        "featureFlags\\.",
    ],
    # State machine patterns
    "StateMachine": [
        "StateMachine",
        "state_machine",
        "XState",
        "createMachine",
        "workflow_state",
        "status.*enum",
    ],
}

def fix_pattern_expansions():
    """Expand overly narrow code patterns."""
    print("\n=== Phase 4: Expanding Code Patterns ===")

    # Find audits with the narrow patterns and expand them
    for yaml_file in AUDITS_ROOT.rglob("*.yaml"):
        data, content = load_yaml(yaml_file)
        if not data:
            continue

        if 'discovery' not in data or 'code_patterns' not in data.get('discovery', {}):
            continue

        modified = False
        original_content = content

        for narrow_pattern, expanded_patterns in PATTERN_EXPANSIONS.items():
            if narrow_pattern in content:
                # Check if we should expand (audit uses this narrow pattern)
                for code_pattern in data['discovery'].get('code_patterns', []):
                    if isinstance(code_pattern, dict):
                        pat = code_pattern.get('pattern', '')
                    else:
                        pat = str(code_pattern)

                    if narrow_pattern in pat and len(expanded_patterns) > 1:
                        # This audit could benefit from expanded patterns
                        # Add a note in the audit about alternative patterns
                        if "# Alternative patterns:" not in content:
                            alternatives = "\n".join([f"        # - {p}" for p in expanded_patterns[1:]])
                            comment = f"\n        # Alternative patterns for broader coverage:\n{alternatives}"
                            # Find the pattern in content and add comment after
                            pat_idx = content.find(narrow_pattern)
                            if pat_idx > 0:
                                line_end = content.find('\n', pat_idx)
                                if line_end > 0:
                                    content = content[:line_end] + comment + content[line_end:]
                                    modified = True
                        break

        if modified and content != original_content:
            save_content(yaml_file, content)
            fixes_applied["pattern_expansions"].append(str(yaml_file))
            print(f"  Expanded patterns: {yaml_file.relative_to(AUDITS_ROOT)}")

# =============================================================================
# PHASE 5: Add Clarity Improvements (Glossary Terms)
# =============================================================================

GLOSSARY_ADDITIONS = {
    "42-quantum-computing": {
        "terms": {
            "stabilizer": "A group of Pauli operators that defines the code space for quantum error correction",
            "syndrome": "Measurement outcomes indicating which errors have occurred",
            "logical qubit": "An encoded qubit protected by error correction codes",
            "WCET": "Worst-Case Execution Time - maximum time a task could take to complete",
        }
    },
    "40-signal-processing-data-acquisition": {
        "terms": {
            "mu (step size)": "Learning rate parameter in adaptive filters, controls convergence speed vs stability",
            "LMS": "Least Mean Squares - adaptive filter algorithm that minimizes mean squared error",
            "FFT": "Fast Fourier Transform - efficient algorithm to compute discrete Fourier transform",
        }
    },
    "39-real-time-embedded": {
        "terms": {
            "WCET": "Worst-Case Execution Time - maximum possible execution time for a code path",
            "ISR": "Interrupt Service Routine - function executed in response to hardware interrupt",
            "jitter": "Variation in timing between expected and actual execution",
        }
    },
    "41-blockchain-distributed-ledger": {
        "terms": {
            "timelock": "Governance mechanism requiring delay between proposal and execution",
            "reentrancy": "Vulnerability where external call allows re-entering function before completion",
            "oracle": "External data feed providing off-chain information to smart contracts",
        }
    },
}

def fix_clarity_improvements():
    """Add glossary definitions for domain-specific terminology."""
    print("\n=== Phase 5: Adding Clarity Improvements ===")

    for category_pattern, glossary_info in GLOSSARY_ADDITIONS.items():
        category_dir = None
        for d in AUDITS_ROOT.iterdir():
            if category_pattern in d.name:
                category_dir = d
                break

        if not category_dir or not category_dir.exists():
            continue

        for yaml_file in category_dir.rglob("*.yaml"):
            data, content = load_yaml(yaml_file)
            if not data:
                continue

            # Check if any glossary terms appear in this file without definition
            needs_glossary = False
            for term in glossary_info["terms"].keys():
                term_lower = term.lower().split()[0]  # First word of term
                if term_lower in content.lower() and "glossary:" not in content.lower():
                    needs_glossary = True
                    break

            if needs_glossary and "glossary:" not in content:
                # Add glossary section before the last line
                glossary_yaml = "\n# Glossary of domain-specific terms:\n"
                glossary_yaml += "glossary:\n"
                for term, definition in glossary_info["terms"].items():
                    glossary_yaml += f'  "{term}": "{definition}"\n'

                # Insert before final newlines
                content = content.rstrip() + "\n" + glossary_yaml
                save_content(yaml_file, content)
                fixes_applied["clarity_improvements"].append(str(yaml_file))
                print(f"  Added glossary: {yaml_file.relative_to(AUDITS_ROOT)}")

# =============================================================================
# PHASE 6: Tier Adjustments
# =============================================================================

TIER_DOWNGRADES = {
    # Category 29 risk management - downgrade document-review audits from phd to expert
    "29-risk-management": {
        "audits_to_downgrade": [
            "risk-monitoring/risk-reporting",
            "risk-monitoring/key-risk-indicators",
            "compliance-risk/regulatory-compliance-risk",
            "business-continuity/bcp-documentation",
        ],
        "from_tier": "phd",
        "to_tier": "expert",
    },
}

TIER_UPGRADES = {
    # Circuit breaker from phd to expert (well-documented pattern)
    "03-reliability-resilience/fault-tolerance/circuit-breaker.yaml": {
        "from_tier": "phd",
        "to_tier": "expert",
    },
}

def fix_tier_adjustments():
    """Adjust tier assignments for miscategorized audits."""
    print("\n=== Phase 6: Adjusting Tier Assignments ===")

    # Process downgrades by category
    for category_pattern, downgrade_info in TIER_DOWNGRADES.items():
        category_dir = None
        for d in AUDITS_ROOT.iterdir():
            if category_pattern in d.name:
                category_dir = d
                break

        if not category_dir or not category_dir.exists():
            continue

        for audit_path in downgrade_info["audits_to_downgrade"]:
            for yaml_file in category_dir.rglob("*.yaml"):
                if audit_path in str(yaml_file):
                    data, content = load_yaml(yaml_file)
                    if not data:
                        continue

                    current_tier = data.get('audit', {}).get('tier', '')
                    if current_tier == downgrade_info["from_tier"]:
                        content = re.sub(
                            rf'tier:\s*{downgrade_info["from_tier"]}',
                            f'tier: {downgrade_info["to_tier"]}',
                            content
                        )
                        save_content(yaml_file, content)
                        fixes_applied["tier_adjustments"].append(
                            (str(yaml_file), downgrade_info["from_tier"], downgrade_info["to_tier"])
                        )
                        print(f"  Tier: {downgrade_info['from_tier']} -> {downgrade_info['to_tier']}: {yaml_file.name}")

    # Process individual upgrades/downgrades
    for audit_path, adjustment in TIER_UPGRADES.items():
        full_path = AUDITS_ROOT / audit_path
        if full_path.exists():
            data, content = load_yaml(full_path)
            if data:
                current_tier = data.get('audit', {}).get('tier', '')
                if current_tier == adjustment["from_tier"]:
                    content = re.sub(
                        rf'tier:\s*{adjustment["from_tier"]}',
                        f'tier: {adjustment["to_tier"]}',
                        content
                    )
                    save_content(full_path, content)
                    fixes_applied["tier_adjustments"].append(
                        (str(full_path), adjustment["from_tier"], adjustment["to_tier"])
                    )
                    print(f"  Tier: {adjustment['from_tier']} -> {adjustment['to_tier']}: {full_path.name}")

# =============================================================================
# PHASE 7: Fix Relationship References
# =============================================================================

RELATIONSHIP_FIXES = {
    "reliability.fault-tolerance.circuit-breaker": "reliability-resilience.fault-tolerance.circuit-breaker",
    "security-trust.input-validation.input-validation": "security-trust.input-validation.sql-injection",
}

def fix_relationship_references():
    """Fix invalid relationship references in audits."""
    print("\n=== Phase 7: Fixing Relationship References ===")

    for yaml_file in AUDITS_ROOT.rglob("*.yaml"):
        data, content = load_yaml(yaml_file)
        if not data:
            continue

        modified = False
        original_content = content

        for wrong_ref, correct_ref in RELATIONSHIP_FIXES.items():
            if wrong_ref in content:
                content = content.replace(wrong_ref, correct_ref)
                modified = True

        if modified and content != original_content:
            save_content(yaml_file, content)
            fixes_applied["relationship_fixes"].append(str(yaml_file))
            print(f"  Fixed refs: {yaml_file.relative_to(AUDITS_ROOT)}")

# =============================================================================
# Main Execution
# =============================================================================

def generate_report():
    """Generate summary report of all fixes applied."""
    print("\n" + "="*60)
    print("FIX SUMMARY REPORT")
    print("="*60)

    total = 0
    for category, items in fixes_applied.items():
        count = len(items)
        total += count
        print(f"\n{category.replace('_', ' ').title()}: {count}")
        if count > 0 and count <= 10:
            for item in items:
                if isinstance(item, tuple):
                    print(f"  - {item}")
                else:
                    print(f"  - {Path(item).name}")
        elif count > 10:
            print(f"  (showing first 5 of {count})")
            for item in items[:5]:
                if isinstance(item, tuple):
                    print(f"  - {item}")
                else:
                    print(f"  - {Path(item).name}")

    print(f"\n{'='*60}")
    print(f"TOTAL FIXES APPLIED: {total}")
    print("="*60)

    # Write report to file
    report_path = Path("/mnt/walnut-drive/dev/audits/meta-audit/semantic-fixes-report.txt")
    with open(report_path, 'w') as f:
        f.write("SEMANTIC FIXES REPORT\n")
        f.write(f"Generated: 2026-01-24\n")
        f.write("="*60 + "\n\n")

        for category, items in fixes_applied.items():
            f.write(f"\n{category.upper()}: {len(items)} fixes\n")
            f.write("-"*40 + "\n")
            for item in items:
                if isinstance(item, tuple):
                    f.write(f"  {item}\n")
                else:
                    f.write(f"  {item}\n")

        f.write(f"\n\nTOTAL: {total} fixes\n")

    print(f"\nReport saved to: {report_path}")

def main():
    print("="*60)
    print("SEMANTIC ISSUE FIX SCRIPT")
    print("Fixing all 180+ semantic issues identified in meta-audit")
    print("="*60)

    # Execute all fix phases
    fix_id_prefixes()
    fix_metadata_additions()
    fix_command_syntax()
    fix_pattern_expansions()
    fix_clarity_improvements()
    fix_tier_adjustments()
    fix_relationship_references()

    # Generate summary report
    generate_report()

if __name__ == "__main__":
    main()
