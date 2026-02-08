#!/usr/bin/env python3
"""
Fix completeness issues - add discovery patterns to audits missing them.
Uses category/subcategory to determine appropriate patterns.
"""

import yaml
import os
from pathlib import Path
from collections import defaultdict

# Custom YAML representer
def str_representer(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, str_representer)

AUDITS_DIR = Path("/mnt/walnut-drive/dev/audits/audits")

# Default discovery patterns by category
CATEGORY_PATTERNS = {
    'metaverse-immersive': {
        'file_patterns': [
            {'glob': '**/*.unity', 'purpose': 'Unity scene files'},
            {'glob': '**/*.uasset', 'purpose': 'Unreal asset files'},
            {'glob': '**/*.shader', 'purpose': 'Shader files'},
            {'glob': '**/*.hlsl', 'purpose': 'HLSL shader code'},
            {'glob': '**/*.glsl', 'purpose': 'GLSL shader code'},
            {'glob': '**/ProjectSettings/**', 'purpose': 'Unity project settings'},
        ],
        'code_patterns': [
            {'pattern': r'XR|VR|AR|MixedReality|OpenXR', 'type': 'regex', 'scope': 'source', 'purpose': 'XR/VR/AR references'},
            {'pattern': r'AudioSource|SpatialAudio|FMOD|Wwise', 'type': 'regex', 'scope': 'source', 'purpose': 'Audio system references'},
        ]
    },
    'cost-economics': {
        'file_patterns': [
            {'glob': '**/*.tf', 'purpose': 'Terraform files'},
            {'glob': '**/cloudformation/**/*.yaml', 'purpose': 'CloudFormation templates'},
            {'glob': '**/*cost*.yaml', 'purpose': 'Cost configuration files'},
            {'glob': '**/*budget*.yaml', 'purpose': 'Budget configuration files'},
            {'glob': '**/*tag*.yaml', 'purpose': 'Tagging policy files'},
        ],
        'code_patterns': [
            {'pattern': r'tags\s*[=:]|cost_center|billing|budget', 'type': 'regex', 'scope': 'config', 'purpose': 'Cost/billing references'},
            {'pattern': r'reserved_instance|spot_instance|savings_plan', 'type': 'regex', 'scope': 'config', 'purpose': 'Cost optimization patterns'},
        ]
    },
    'infrastructure-as-code': {
        'file_patterns': [
            {'glob': '**/*.tf', 'purpose': 'Terraform files'},
            {'glob': '**/*.tfstate', 'purpose': 'Terraform state files'},
            {'glob': '**/terraform.tfvars', 'purpose': 'Terraform variables'},
            {'glob': '**/.terraform/**', 'purpose': 'Terraform working directory'},
            {'glob': '**/pulumi*.yaml', 'purpose': 'Pulumi configuration'},
        ],
        'code_patterns': [
            {'pattern': r'terraform|pulumi|cloudformation|ansible', 'type': 'regex', 'scope': 'config', 'purpose': 'IaC tool references'},
        ]
    },
    'human-organizational': {
        'file_patterns': [
            {'glob': '**/*.md', 'purpose': 'Documentation files'},
            {'glob': '**/CODEOWNERS', 'purpose': 'Code ownership files'},
            {'glob': '**/*.org', 'purpose': 'Org structure files'},
            {'glob': '**/team*.yaml', 'purpose': 'Team configuration'},
        ],
        'code_patterns': [
            {'pattern': r'@team|@owner|maintainer', 'type': 'regex', 'scope': 'all', 'purpose': 'Ownership references'},
        ]
    },
    'ethical-societal': {
        'file_patterns': [
            {'glob': '**/ETHICS.md', 'purpose': 'Ethics documentation'},
            {'glob': '**/PRIVACY*.md', 'purpose': 'Privacy documentation'},
            {'glob': '**/terms*.md', 'purpose': 'Terms of service'},
            {'glob': '**/policy*.md', 'purpose': 'Policy documentation'},
        ],
        'code_patterns': [
            {'pattern': r'consent|privacy|gdpr|ccpa|cookie', 'type': 'regex', 'scope': 'all', 'purpose': 'Privacy/consent references'},
        ]
    },
    'gamification-behavioral': {
        'file_patterns': [
            {'glob': '**/*reward*.{yaml,json}', 'purpose': 'Reward configuration'},
            {'glob': '**/*achievement*.{yaml,json}', 'purpose': 'Achievement configuration'},
            {'glob': '**/*notification*.{yaml,json}', 'purpose': 'Notification configuration'},
        ],
        'code_patterns': [
            {'pattern': r'gamif|reward|achievement|badge|point|level', 'type': 'regex', 'scope': 'all', 'purpose': 'Gamification references'},
            {'pattern': r'notification|push|alert|reminder', 'type': 'regex', 'scope': 'all', 'purpose': 'Notification patterns'},
        ]
    },
    'emotional-design-trust': {
        'file_patterns': [
            {'glob': '**/*.css', 'purpose': 'Style files'},
            {'glob': '**/*.scss', 'purpose': 'SCSS style files'},
            {'glob': '**/design-system/**', 'purpose': 'Design system files'},
        ],
        'code_patterns': [
            {'pattern': r'animation|transition|feedback|loading|error-message', 'type': 'regex', 'scope': 'all', 'purpose': 'UX feedback patterns'},
        ]
    },
    'compliance-governance': {
        'file_patterns': [
            {'glob': '**/COMPLIANCE*.md', 'purpose': 'Compliance documentation'},
            {'glob': '**/audit*.yaml', 'purpose': 'Audit configuration'},
            {'glob': '**/policy*.yaml', 'purpose': 'Policy configuration'},
        ],
        'code_patterns': [
            {'pattern': r'audit|compliance|policy|regulation|soc2|iso27001|hipaa|pci', 'type': 'regex', 'scope': 'all', 'purpose': 'Compliance references'},
        ]
    },
    'operational-excellence': {
        'file_patterns': [
            {'glob': '**/runbook*.md', 'purpose': 'Runbook documentation'},
            {'glob': '**/playbook*.md', 'purpose': 'Playbook documentation'},
            {'glob': '**/sop*.md', 'purpose': 'Standard operating procedures'},
            {'glob': '**/oncall*.yaml', 'purpose': 'On-call configuration'},
        ],
        'code_patterns': [
            {'pattern': r'runbook|playbook|incident|escalation|sla', 'type': 'regex', 'scope': 'all', 'purpose': 'Operations references'},
        ]
    },
    'vendor-third-party': {
        'file_patterns': [
            {'glob': '**/vendor*.yaml', 'purpose': 'Vendor configuration'},
            {'glob': '**/contract*.md', 'purpose': 'Contract documentation'},
            {'glob': '**/*integration*.yaml', 'purpose': 'Integration configuration'},
        ],
        'code_patterns': [
            {'pattern': r'vendor|supplier|partner|third.?party|external', 'type': 'regex', 'scope': 'all', 'purpose': 'Vendor references'},
        ]
    },
    'quantum-computing': {
        'file_patterns': [
            {'glob': '**/*.qasm', 'purpose': 'OpenQASM files'},
            {'glob': '**/*.quil', 'purpose': 'Quil files'},
            {'glob': '**/qiskit/**/*.py', 'purpose': 'Qiskit code'},
            {'glob': '**/cirq/**/*.py', 'purpose': 'Cirq code'},
        ],
        'code_patterns': [
            {'pattern': r'qiskit|cirq|pennylane|qubit|quantum|entangle', 'type': 'regex', 'scope': 'source', 'purpose': 'Quantum computing references'},
        ]
    },
    'blockchain-distributed-ledger': {
        'file_patterns': [
            {'glob': '**/*.sol', 'purpose': 'Solidity smart contracts'},
            {'glob': '**/contracts/**/*.sol', 'purpose': 'Smart contract files'},
            {'glob': '**/hardhat.config.*', 'purpose': 'Hardhat configuration'},
            {'glob': '**/truffle-config.js', 'purpose': 'Truffle configuration'},
        ],
        'code_patterns': [
            {'pattern': r'contract\s+\w+|pragma\s+solidity|web3|ethers', 'type': 'regex', 'scope': 'source', 'purpose': 'Blockchain/Web3 references'},
        ]
    },
}

# Default fallback patterns
DEFAULT_PATTERNS = {
    'file_patterns': [
        {'glob': '**/*.md', 'purpose': 'Documentation files'},
        {'glob': '**/*.yaml', 'purpose': 'Configuration files'},
        {'glob': '**/*.json', 'purpose': 'JSON configuration'},
    ]
}

def load_yaml(filepath):
    """Load YAML file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(filepath, data):
    """Save YAML file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=100)

def has_discovery_patterns(data):
    """Check if audit has discovery patterns."""
    discovery = data.get('discovery', {})
    if not discovery:
        return False

    code_patterns = discovery.get('code_patterns', [])
    file_patterns = discovery.get('file_patterns', [])

    return (isinstance(code_patterns, list) and len(code_patterns) > 0) or \
           (isinstance(file_patterns, list) and len(file_patterns) > 0)

def get_category_from_path(filepath):
    """Extract category from file path."""
    parts = filepath.relative_to(AUDITS_DIR).parts
    if parts:
        # Category directory is like "31-cost-economics"
        cat_dir = parts[0]
        # Remove number prefix
        if '-' in cat_dir:
            return '-'.join(cat_dir.split('-')[1:])
    return None

def add_discovery_patterns(data, category):
    """Add appropriate discovery patterns based on category."""
    patterns = CATEGORY_PATTERNS.get(category, DEFAULT_PATTERNS)

    if 'discovery' not in data:
        data['discovery'] = {}

    # Add file patterns if not present
    if 'file_patterns' not in data['discovery'] or not data['discovery']['file_patterns']:
        data['discovery']['file_patterns'] = patterns.get('file_patterns', DEFAULT_PATTERNS['file_patterns'])

    # Add code patterns if available for this category
    if 'code_patterns' in patterns:
        if 'code_patterns' not in data['discovery'] or not data['discovery']['code_patterns']:
            data['discovery']['code_patterns'] = patterns['code_patterns']

    return True

def main():
    print("Fixing completeness issues - adding discovery patterns...")

    fixed_count = 0
    by_category = defaultdict(int)

    # Find all audit files
    audit_files = list(AUDITS_DIR.rglob('*.yaml'))
    print(f"Scanning {len(audit_files)} audit files...")

    for filepath in audit_files:
        try:
            data = load_yaml(filepath)
            if not data or 'audit' not in data:
                continue

            # Check if missing discovery patterns
            if not has_discovery_patterns(data):
                category = get_category_from_path(filepath)
                if add_discovery_patterns(data, category):
                    save_yaml(filepath, data)
                    fixed_count += 1
                    by_category[category] += 1

        except Exception as e:
            print(f"  ERROR: {filepath}: {e}")

    print(f"\n=== Summary ===")
    print(f"Total files fixed: {fixed_count}")
    print(f"\nBy category:")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

if __name__ == '__main__':
    main()
