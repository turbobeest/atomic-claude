#!/usr/bin/env python3
"""
Update all supporting materials after meta-audit fixes:
1. Regenerate AUDIT-INVENTORY.csv
2. Update category documentation
3. Update AUDIT-MENU.md
4. Update README.md statistics
5. Regenerate docs/TREE.txt
6. Update taxonomy reference
"""

import os
import re
import csv
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path("/mnt/walnut-drive/dev/audits")
AUDITS_DIR = BASE_DIR / "audits"
CATEGORIES_DIR = BASE_DIR / "categories"

# =============================================================================
# 1. REGENERATE AUDIT-INVENTORY.csv
# =============================================================================

def regenerate_inventory_csv():
    """Regenerate the complete audit inventory CSV."""
    print("\n=== Regenerating AUDIT-INVENTORY.csv ===")

    csv_path = BASE_DIR / "AUDIT-INVENTORY.csv"

    # CSV headers
    headers = [
        "audit_id", "file_path", "audit_name", "category", "category_number",
        "subcategory", "tier", "status", "automatable", "severity",
        "estimated_duration", "requires_runtime", "requires_physical_access",
        "requires_human_evaluation", "requires_interviews"
    ]

    rows = []

    for yaml_file in sorted(AUDITS_DIR.rglob("*.yaml")):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                content = f.read()
                data = yaml.safe_load(content)

            if not data or 'audit' not in data:
                continue

            audit = data.get('audit', {})
            execution = data.get('execution', {})

            # Extract relative path
            rel_path = str(yaml_file.relative_to(BASE_DIR))

            row = {
                "audit_id": audit.get('id', ''),
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
                "requires_physical_access": 'true' if 'requires_physical_access' in content else 'false',
                "requires_human_evaluation": 'true' if 'requires_human_evaluation' in content else 'false',
                "requires_interviews": 'true' if 'requires_interviews' in content else 'false',
            }
            rows.append(row)
        except Exception as e:
            print(f"  Error processing {yaml_file}: {e}")

    # Write CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  Generated {csv_path.name} with {len(rows)} audits")
    return len(rows)

# =============================================================================
# 2. UPDATE CATEGORY DOCUMENTATION
# =============================================================================

def update_category_docs():
    """Rename and update category 21 documentation."""
    print("\n=== Updating Category Documentation ===")

    # Rename category 21 file
    old_cat21 = CATEGORIES_DIR / "21-ethical-societal.md"
    new_cat21 = CATEGORIES_DIR / "21-responsible-design.md"

    if old_cat21.exists():
        # Create new content
        new_content = """# Category 21: Responsible Design

**Cluster:** Human & Experience
**Slug:** `responsible-design`

## Overview

Audits covering harm prevention, dark pattern avoidance, addiction/manipulation prevention,
algorithmic fairness, consent transparency, and environmental impact of digital products.

This category was renamed from "ethical-societal" to better distinguish it from Category 18
(Ethical & Societal) which focuses on broader societal impact and AI ethics.

## Subcategories

- **addiction-manipulation**: Audits for engagement ethics, notification manipulation, FOMO exploitation
- **algorithmic-fairness**: Bias detection, disparate impact, fairness metrics
- **consent-transparency**: Informed consent, data usage transparency, opt-in/opt-out defaults
- **content-harm**: Harmful content moderation, misinformation, radicalization vectors
- **dark-pattern-avoidance**: Misdirection, bait-and-switch, confirmshaming, roach motel patterns
- **economic-fairness**: Dynamic pricing transparency, predatory pricing, accessibility pricing
- **environmental-impact**: Energy efficiency, carbon footprint, green hosting, compute optimization

## Audit Patterns

This category primarily uses:
- **Code review pattern** for detecting dark patterns in UI code
- **Configuration audit pattern** for consent and transparency settings
- **Documentation pattern** for policy compliance verification

## Related Categories

- **Category 18 (Ethical & Societal)**: Broader ethics including AI safety, privacy by design, societal impact
- **Category 22 (Gamification & Behavioral)**: Engagement mechanics with ethical considerations
- **Category 37 (Machine Learning & AI)**: Responsible AI and bias detection

## Key Standards & Frameworks

- EU Digital Services Act (DSA)
- UK Online Safety Act
- California Consumer Privacy Act (CCPA)
- FTC guidelines on dark patterns
- ACM Code of Ethics
"""

        # Remove old file and create new
        old_cat21.unlink()
        with open(new_cat21, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  Renamed and updated: 21-ethical-societal.md -> 21-responsible-design.md")
    else:
        print(f"  Category 21 file already updated or not found")

    # Update any other category docs that reference old category 21
    for md_file in CATEGORIES_DIR.glob("*.md"):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        if "21-ethical-societal" in content or "Category 21: Ethical" in content:
            content = content.replace("21-ethical-societal", "21-responsible-design")
            content = content.replace("Category 21: Ethical & Societal", "Category 21: Responsible Design")
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Updated reference in: {md_file.name}")

# =============================================================================
# 3. UPDATE AUDIT-MENU.md
# =============================================================================

def update_audit_menu():
    """Update AUDIT-MENU.md with current category names and counts."""
    print("\n=== Updating AUDIT-MENU.md ===")

    menu_path = BASE_DIR / "AUDIT-MENU.md"

    with open(menu_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update category 21 references
    content = content.replace("21-ethical-societal", "21-responsible-design")
    content = content.replace("ethical-societal.addiction", "responsible-design.addiction")
    content = content.replace("ethical-societal.algorithmic", "responsible-design.algorithmic")
    content = content.replace("ethical-societal.consent", "responsible-design.consent")
    content = content.replace("ethical-societal.content", "responsible-design.content")
    content = content.replace("ethical-societal.dark-pattern", "responsible-design.dark-pattern")
    content = content.replace("ethical-societal.economic", "responsible-design.economic")
    content = content.replace("ethical-societal.environmental", "responsible-design.environmental")

    # Update category title if present
    content = re.sub(
        r'## 21\. Ethical & Societal',
        '## 21. Responsible Design',
        content
    )

    with open(menu_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  Updated AUDIT-MENU.md")

# =============================================================================
# 4. UPDATE README.md
# =============================================================================

def update_readme():
    """Update README.md with current statistics."""
    print("\n=== Updating README.md ===")

    readme_path = BASE_DIR / "README.md"

    # Count audits and categories
    audit_count = len(list(AUDITS_DIR.rglob("*.yaml")))
    category_count = len([d for d in AUDITS_DIR.iterdir() if d.is_dir()])

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update audit count
    content = re.sub(
        r'\*\*[\d,]+\+?\s*audits?\*\*',
        f'**{audit_count:,} audits**',
        content
    )

    # Update category count
    content = re.sub(
        r'\*\*\d+\s*categories?\*\*',
        f'**{category_count} categories**',
        content
    )

    # Update any "2,189" references to current count
    content = re.sub(r'2,?189', str(audit_count), content)

    # Update category 21 references
    content = content.replace("21-ethical-societal", "21-responsible-design")

    # Add/update last updated date
    today = datetime.now().strftime("%Y-%m-%d")
    if "Last updated:" in content:
        content = re.sub(r'Last updated: \d{4}-\d{2}-\d{2}', f'Last updated: {today}', content)

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  Updated README.md (audits: {audit_count}, categories: {category_count})")

# =============================================================================
# 5. REGENERATE docs/TREE.txt
# =============================================================================

def regenerate_tree():
    """Regenerate the directory tree structure."""
    print("\n=== Regenerating docs/TREE.txt ===")

    tree_path = BASE_DIR / "docs" / "TREE.txt"

    lines = [
        "# Audit Framework Directory Structure",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d')}",
        "#" + "="*60,
        "",
        "audits/",
    ]

    # Get all categories sorted
    categories = sorted([d for d in AUDITS_DIR.iterdir() if d.is_dir()])

    for cat_dir in categories:
        cat_name = cat_dir.name
        audit_count = len(list(cat_dir.rglob("*.yaml")))
        lines.append(f"├── {cat_name}/ ({audit_count} audits)")

        # Get subcategories
        subcats = sorted([d for d in cat_dir.iterdir() if d.is_dir()])
        for i, subcat in enumerate(subcats):
            prefix = "│   └──" if i == len(subcats) - 1 else "│   ├──"
            subcat_count = len(list(subcat.glob("*.yaml")))
            lines.append(f"{prefix} {subcat.name}/ ({subcat_count})")

    # Add summary
    total_audits = len(list(AUDITS_DIR.rglob("*.yaml")))
    lines.extend([
        "",
        "#" + "="*60,
        f"# Total: {len(categories)} categories, {total_audits} audits",
        "#" + "="*60,
    ])

    with open(tree_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"  Generated TREE.txt")

# =============================================================================
# 6. UPDATE TAXONOMY REFERENCE
# =============================================================================

def update_taxonomy_reference():
    """Update the audit taxonomy reference document."""
    print("\n=== Updating audit-taxonomy-reference.md ===")

    taxonomy_path = BASE_DIR / "docs" / "audit-taxonomy-reference.md"

    if not taxonomy_path.exists():
        print(f"  Taxonomy file not found, skipping")
        return

    with open(taxonomy_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update category 21 references
    content = content.replace("21-ethical-societal", "21-responsible-design")
    content = content.replace("Ethical & Societal (21)", "Responsible Design (21)")
    content = content.replace("ethical-societal", "responsible-design")

    # Update ID prefix references for categories 40 and 41
    content = content.replace("signal-processing.", "signal-processing-data-acquisition.")
    content = content.replace("blockchain.", "blockchain-distributed-ledger.")

    with open(taxonomy_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  Updated audit-taxonomy-reference.md")

# =============================================================================
# 7. GENERATE CATEGORY SUMMARY TABLE
# =============================================================================

def generate_category_summary():
    """Generate a markdown summary table of all categories."""
    print("\n=== Generating Category Summary ===")

    summary_path = BASE_DIR / "docs" / "CATEGORY-SUMMARY.md"

    lines = [
        "# Audit Category Summary",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d')}*",
        "",
        "| # | Category | Audits | Subcategories |",
        "|---|----------|--------|---------------|",
    ]

    total_audits = 0
    categories = sorted([d for d in AUDITS_DIR.iterdir() if d.is_dir()])

    for cat_dir in categories:
        cat_name = cat_dir.name
        # Extract number and name
        match = re.match(r'(\d+)-(.+)', cat_name)
        if match:
            num, name = match.groups()
            name_display = name.replace('-', ' ').title()
        else:
            num = "?"
            name_display = cat_name

        audit_count = len(list(cat_dir.rglob("*.yaml")))
        total_audits += audit_count

        subcats = [d.name for d in cat_dir.iterdir() if d.is_dir()]
        subcat_count = len(subcats)

        lines.append(f"| {num} | {name_display} | {audit_count} | {subcat_count} |")

    lines.extend([
        "",
        f"**Total: {len(categories)} categories, {total_audits} audits**",
        "",
        "## Category Clusters",
        "",
        "| Cluster | Categories |",
        "|---------|------------|",
        "| Core Quality | 01-07 (Security, Performance, Reliability, Scalability, Observability, Code Quality, Architecture) |",
        "| Data & State | 08 (Data & State Management) |",
        "| Integration | 09 (API & Integration) |",
        "| Testing | 10, 26 (Testing & QA) |",
        "| Infrastructure | 11-16 (DevOps, Cloud, IaC, Network, Storage) |",
        "| Human Experience | 17-23 (Usability, Accessibility, SEO, Human/Org, Responsible Design, Gamification, Emotional Design) |",
        "| Governance | 24-25 (Compliance, Operational Excellence) |",
        "| Process | 27-28 (Documentation, Requirements) |",
        "| Risk & Cost | 29-31 (Risk, Configuration, Cost) |",
        "| Dependencies | 32-33 (Supply Chain, Legacy/Migration) |",
        "| Domain | 34-35 (Business Logic, Developer Experience) |",
        "| Specialized | 36-43 (i18n, ML/AI, Sensors, Embedded, Signal Processing, Blockchain, Quantum, Metaverse) |",
    ])

    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"  Generated CATEGORY-SUMMARY.md")

# =============================================================================
# 8. UPDATE OTHER DOCS
# =============================================================================

def update_other_docs():
    """Update any other docs that reference old category names."""
    print("\n=== Updating Other Documentation ===")

    docs_dir = BASE_DIR / "docs"

    replacements = [
        ("21-ethical-societal", "21-responsible-design"),
        ("ethical-societal.", "responsible-design."),
        ("signal-processing.", "signal-processing-data-acquisition."),
        ("blockchain.", "blockchain-distributed-ledger."),
    ]

    updated_files = []

    for doc_file in docs_dir.glob("*.md"):
        with open(doc_file, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content
        for old, new in replacements:
            # Don't replace if it's already the full form
            if old == "signal-processing." and "signal-processing-data-acquisition." in content:
                continue
            if old == "blockchain." and "blockchain-distributed-ledger." in content:
                continue
            content = content.replace(old, new)

        if content != original:
            with open(doc_file, 'w', encoding='utf-8') as f:
                f.write(content)
            updated_files.append(doc_file.name)

    if updated_files:
        print(f"  Updated: {', '.join(updated_files)}")
    else:
        print(f"  No additional updates needed")

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*60)
    print("UPDATING SUPPORTING MATERIALS")
    print("="*60)

    audit_count = regenerate_inventory_csv()
    update_category_docs()
    update_audit_menu()
    update_readme()
    regenerate_tree()
    update_taxonomy_reference()
    generate_category_summary()
    update_other_docs()

    print("\n" + "="*60)
    print("SUPPORTING MATERIALS UPDATE COMPLETE")
    print("="*60)
    print(f"\nUpdated files:")
    print(f"  - AUDIT-INVENTORY.csv ({audit_count} audits)")
    print(f"  - categories/21-responsible-design.md (renamed)")
    print(f"  - AUDIT-MENU.md")
    print(f"  - README.md")
    print(f"  - docs/TREE.txt")
    print(f"  - docs/audit-taxonomy-reference.md")
    print(f"  - docs/CATEGORY-SUMMARY.md (new)")

if __name__ == "__main__":
    main()
