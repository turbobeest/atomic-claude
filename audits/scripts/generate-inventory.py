#!/usr/bin/env python3
"""
Generate AUDIT-INVENTORY.csv from audit YAML files.

This script scans all YAML files in the audits/ directory and generates
a comprehensive CSV inventory. It extracts metadata from each audit file
and populates the inventory with all relevant fields.

SDLC phases: If an audit YAML has an `sdlc_phases` section, those values
are used. Otherwise, defaults are applied based on the audit's scope.
"""

import os
import sys
import csv
import yaml
from pathlib import Path
from typing import Any

# Determine base directory (script can run from anywhere)
SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_DIR = SCRIPT_DIR.parent
AUDITS_DIR = BASE_DIR / "audits"
CSV_PATH = BASE_DIR / "AUDIT-INVENTORY.csv"

# CSV column headers
CSV_HEADERS = [
    "audit_id",
    "file_path",
    "audit_name",
    "category",
    "category_number",
    "subcategory",
    "tier",
    "status",
    "automatable",
    "severity",
    "estimated_duration",
    "requires_runtime",
    "requires_physical_access",
    "requires_human_evaluation",
    "requires_interviews",
    # SDLC phases
    "discovery",
    "prd",
    "task_decomposition",
    "specification",
    "implementation",
    "testing",
    "integration",
    "deployment",
    "post_production",
]

# SDLC phase names (matching CSV columns)
SDLC_PHASES = [
    "discovery",
    "prd",
    "task_decomposition",
    "specification",
    "implementation",
    "testing",
    "integration",
    "deployment",
    "post_production",
]

# Default SDLC phases based on execution scope
SCOPE_SDLC_DEFAULTS = {
    # Early phases (discovery, prd, task_decomposition, specification)
    "prd": {
        "discovery": True, "prd": True, "task_decomposition": True,
        "specification": True, "implementation": False, "testing": False,
        "integration": False, "deployment": False, "post_production": False
    },
    "architecture": {
        "discovery": True, "prd": True, "task_decomposition": True,
        "specification": True, "implementation": False, "testing": False,
        "integration": False, "deployment": True, "post_production": False
    },
    # Implementation phases
    "codebase": {
        "discovery": False, "prd": False, "task_decomposition": False,
        "specification": True, "implementation": True, "testing": True,
        "integration": True, "deployment": True, "post_production": True
    },
    "source": {
        "discovery": False, "prd": False, "task_decomposition": False,
        "specification": True, "implementation": True, "testing": True,
        "integration": True, "deployment": True, "post_production": True
    },
    "config": {
        "discovery": False, "prd": False, "task_decomposition": False,
        "specification": True, "implementation": True, "testing": True,
        "integration": True, "deployment": True, "post_production": True
    },
    "testing": {
        "discovery": False, "prd": False, "task_decomposition": False,
        "specification": True, "implementation": True, "testing": True,
        "integration": True, "deployment": False, "post_production": False
    },
    "security": {
        "discovery": False, "prd": False, "task_decomposition": False,
        "specification": True, "implementation": True, "testing": True,
        "integration": True, "deployment": True, "post_production": True
    },
    # Deployment and runtime phases
    "deployment": {
        "discovery": False, "prd": False, "task_decomposition": False,
        "specification": False, "implementation": False, "testing": False,
        "integration": True, "deployment": True, "post_production": True
    },
    "runtime": {
        "discovery": False, "prd": False, "task_decomposition": False,
        "specification": False, "implementation": False, "testing": True,
        "integration": True, "deployment": True, "post_production": True
    },
    "infrastructure": {
        "discovery": False, "prd": False, "task_decomposition": False,
        "specification": True, "implementation": True, "testing": True,
        "integration": True, "deployment": True, "post_production": True
    },
    "metrics": {
        "discovery": False, "prd": False, "task_decomposition": False,
        "specification": False, "implementation": False, "testing": True,
        "integration": True, "deployment": True, "post_production": True
    },
    # Process and organizational
    "documentation": {
        "discovery": True, "prd": True, "task_decomposition": True,
        "specification": True, "implementation": True, "testing": True,
        "integration": True, "deployment": True, "post_production": True
    },
    "process": {
        "discovery": True, "prd": True, "task_decomposition": True,
        "specification": True, "implementation": True, "testing": True,
        "integration": True, "deployment": True, "post_production": True
    },
    "organizational": {
        "discovery": True, "prd": True, "task_decomposition": True,
        "specification": True, "implementation": True, "testing": True,
        "integration": True, "deployment": True, "post_production": True
    },
    "data": {
        "discovery": False, "prd": False, "task_decomposition": False,
        "specification": True, "implementation": True, "testing": True,
        "integration": True, "deployment": True, "post_production": True
    },
    "qualitative": {
        "discovery": True, "prd": True, "task_decomposition": False,
        "specification": True, "implementation": False, "testing": False,
        "integration": False, "deployment": False, "post_production": True
    },
}

# Fallback default for unknown scopes
DEFAULT_SDLC = {
    "discovery": False, "prd": False, "task_decomposition": False,
    "specification": True, "implementation": True, "testing": True,
    "integration": True, "deployment": True, "post_production": True
}


def load_existing_csv() -> dict[str, dict[str, str]]:
    """Load existing CSV to preserve SDLC phases for audits without them in YAML."""
    existing = {}
    if CSV_PATH.exists():
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                audit_id = row.get('audit_id', '')
                if audit_id:
                    existing[audit_id] = row
    return existing


def get_sdlc_phases(data: dict[str, Any], scope: str, existing_row: dict[str, str] | None) -> dict[str, str]:
    """
    Get SDLC phases for an audit.

    Priority:
    1. sdlc_phases section in YAML file
    2. Existing values from current CSV (if CSV has SDLC columns)
    3. Defaults based on scope
    """
    # Check for sdlc_phases in YAML
    sdlc_yaml = data.get('sdlc_phases', {})
    if sdlc_yaml:
        return {
            phase: "Yes" if sdlc_yaml.get(phase, False) else "No"
            for phase in SDLC_PHASES
        }

    # Check existing CSV for this audit (only if it has SDLC columns)
    if existing_row and 'discovery' in existing_row:
        return {
            phase: existing_row.get(phase, "No")
            for phase in SDLC_PHASES
        }

    # Use scope-based defaults
    scope_defaults = SCOPE_SDLC_DEFAULTS.get(scope, DEFAULT_SDLC)
    return {
        phase: "Yes" if scope_defaults.get(phase, False) else "No"
        for phase in SDLC_PHASES
    }


def parse_yaml_file(yaml_path: Path, existing_csv: dict[str, dict[str, str]]) -> dict[str, str] | None:
    """Parse a single YAML audit file and extract CSV row data."""
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            content = f.read()
            data = yaml.safe_load(content)

        if not data or 'audit' not in data:
            return None

        audit = data.get('audit', {})
        execution = data.get('execution', {})

        # Get relative path from base directory
        rel_path = str(yaml_path.relative_to(BASE_DIR))

        # Extract audit ID
        audit_id = audit.get('id', '')

        # Get existing row for SDLC phase lookup
        existing_row = existing_csv.get(audit_id)

        # Get scope for SDLC defaults
        scope = execution.get('scope', 'codebase')

        # Get SDLC phases
        sdlc_phases = get_sdlc_phases(data, scope, existing_row)

        # Build row
        row = {
            "audit_id": audit_id,
            "file_path": rel_path,
            "audit_name": audit.get('name', ''),
            "category": audit.get('category', ''),
            "category_number": str(audit.get('category_number', '')).zfill(2),
            "subcategory": audit.get('subcategory', ''),
            "tier": audit.get('tier', ''),
            "status": audit.get('status', 'active'),
            "automatable": execution.get('automatable', ''),
            "severity": execution.get('severity', ''),
            "estimated_duration": audit.get('estimated_duration', ''),
            "requires_runtime": str(audit.get('requires_runtime', False)).lower(),
            "requires_physical_access": str(audit.get('requires_physical_access', False)).lower(),
            "requires_human_evaluation": str(audit.get('requires_human_evaluation', False)).lower(),
            "requires_interviews": str(execution.get('requires_interviews', False)).lower(),
        }

        # Add SDLC phases
        row.update(sdlc_phases)

        return row

    except yaml.YAMLError as e:
        print(f"  YAML error in {yaml_path}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error processing {yaml_path}: {e}", file=sys.stderr)
        return None


def generate_inventory() -> int:
    """Generate the AUDIT-INVENTORY.csv from all YAML files."""
    print(f"Scanning audits in: {AUDITS_DIR}")

    # Load existing CSV for SDLC phase preservation
    existing_csv = load_existing_csv()
    print(f"Loaded {len(existing_csv)} existing audit records")

    # Find and process all YAML files
    rows = []
    errors = 0

    for yaml_file in sorted(AUDITS_DIR.rglob("*.yaml")):
        row = parse_yaml_file(yaml_file, existing_csv)
        if row:
            rows.append(row)
        else:
            errors += 1

    # Sort by category_number, then by audit_id for consistent ordering
    rows.sort(key=lambda r: (r['category_number'], r['audit_id']))

    # Write CSV
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {CSV_PATH.name} with {len(rows)} audits")
    if errors:
        print(f"  ({errors} files skipped due to errors)")

    return len(rows)


def main():
    """Main entry point."""
    if not AUDITS_DIR.exists():
        print(f"Error: Audits directory not found: {AUDITS_DIR}", file=sys.stderr)
        sys.exit(1)

    count = generate_inventory()
    print(f"\nInventory generation complete: {count} audits")


if __name__ == "__main__":
    main()
