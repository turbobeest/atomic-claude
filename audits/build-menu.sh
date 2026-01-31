#!/bin/bash
#
# Build AUDIT-MENU.md from AUDIT-INVENTORY.csv
#
# This script generates the human-readable audit menu from the CSV source of truth.
# Run this after updating AUDIT-INVENTORY.csv to keep them in sync.
#
# Usage: ./build-menu.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV_FILE="$SCRIPT_DIR/AUDIT-INVENTORY.csv"
MD_FILE="$SCRIPT_DIR/AUDIT-MENU.md"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}Building AUDIT-MENU.md from AUDIT-INVENTORY.csv...${NC}"

# Verify CSV exists
if [[ ! -f "$CSV_FILE" ]]; then
    echo "Error: $CSV_FILE not found"
    exit 1
fi

# Count audits (excluding header)
audit_count=$(($(wc -l < "$CSV_FILE") - 1))
echo "  Processing $audit_count audits..."

# Use Python for proper CSV parsing and markdown generation
python3 << 'PYTHON_SCRIPT'
import csv
from collections import defaultdict
from datetime import date

csv_file = "AUDIT-INVENTORY.csv"
md_file = "AUDIT-MENU.md"

# Cluster definitions (category number ranges)
CLUSTERS = {
    "Core Technical": (1, 12),
    "Infrastructure": (13, 16),
    "Human & Experience": (17, 23),
    "Process & Governance": (24, 30),
    "Economics & Dependencies": (31, 33),
    "Specialized Domains": (34, 43),
}

# Category display names (slug -> display name)
CATEGORY_NAMES = {
    "security-trust": "Security & Trust",
    "performance-efficiency": "Performance & Efficiency",
    "reliability-resilience": "Reliability & Resilience",
    "scalability-capacity": "Scalability & Capacity",
    "observability-instrumentation": "Observability & Instrumentation",
    "code-quality": "Code Quality",
    "architecture-design": "Architecture & Design",
    "data-state-management": "Data & State Management",
    "api-integration": "API & Integration",
    "testing-quality-assurance": "Testing & Quality Assurance",
    "devops-ci-cd": "DevOps & CI/CD",
    "cloud-infrastructure": "Cloud Infrastructure",
    "infrastructure-as-code": "Infrastructure as Code",
    "usability-interaction": "Usability & Interaction",
    "accessibility-inclusion": "Accessibility & Inclusion",
    "seo-discoverability": "SEO & Discoverability",
    "human-organizational": "Human & Organizational",
    "ethical-societal": "Ethical & Societal",
    "compliance-legal": "Compliance & Legal",
    "vendor-third-party": "Vendor & Third Party",
    "emotional-design-trust": "Emotional Design & Trust",
    "gamification-behavioral": "Gamification & Behavioral",
    "compliance-governance": "Compliance & Governance",
    "operational-excellence": "Operational Excellence",
    "documentation-knowledge": "Documentation & Knowledge",
    "requirements-specification": "Requirements & Specification",
    "risk-management": "Risk Management",
    "configuration-management": "Configuration Management",
    "cost-economics": "Cost & Economics",
    "dependency-supply-chain": "Dependency & Supply Chain",
    "legacy-migration": "Legacy & Migration",
    "business-logic-domain": "Business Logic & Domain",
    "developer-experience": "Developer Experience",
    "internationalization-localization": "Internationalization & Localization",
    "machine-learning-ai": "Machine Learning & AI",
    "sensors-physical-systems": "Sensors & Physical Systems",
    "real-time-embedded": "Real-Time & Embedded",
    "signal-processing-data-acquisition": "Signal Processing & Data Acquisition",
    "blockchain-distributed-ledger": "Blockchain & Distributed Ledger",
    "quantum-computing": "Quantum Computing",
    "metaverse-immersive": "Metaverse & Immersive",
}

def get_cluster(cat_num):
    """Get cluster name for a category number."""
    for cluster, (start, end) in CLUSTERS.items():
        if start <= cat_num <= end:
            return cluster
    return "Other"

def format_subcategory(subcat):
    """Format subcategory slug to display name."""
    return subcat.replace("-", " ").title()

def get_category_display(cat_slug):
    """Get display name for category."""
    return CATEGORY_NAMES.get(cat_slug, cat_slug.replace("-", " ").title())

# Parse CSV
audits_by_category = defaultdict(lambda: defaultdict(list))
category_info = {}  # category_num -> (category_slug, audit_count)

with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cat_num = row['category_number']
        cat_slug = row['category']
        subcat = row['subcategory']
        audit_name = row['audit_name']

        # Skip invalid rows
        if not cat_num or not cat_num.isdigit():
            continue

        cat_num_int = int(cat_num)
        audits_by_category[cat_num_int][subcat].append(audit_name)

        if cat_num_int not in category_info:
            category_info[cat_num_int] = cat_slug

# Count audits per cluster
cluster_counts = defaultdict(int)
for cat_num, subcats in audits_by_category.items():
    cluster = get_cluster(cat_num)
    for subcat, audits in subcats.items():
        cluster_counts[cluster] += len(audits)

# Generate markdown
lines = []

# Header
total_audits = sum(len(a) for subcats in audits_by_category.values() for a in subcats.values())
total_categories = len(category_info)

lines.append("# Audit Taxonomy - Master Menu")
lines.append("")
lines.append("> Complete listing of all audits across all categories. Use this file to identify relevant audits for a given task, then pull the specific category file for detailed guidance.")
lines.append("")
lines.append(f"**Total Categories:** {total_categories}  ")
lines.append(f"**Total Audits:** {total_audits:,}  ")
lines.append(f"**Last Updated:** {date.today().strftime('%B %Y')}  ")
lines.append(f"**Generated From:** AUDIT-INVENTORY.csv")
lines.append("")
lines.append("---")
lines.append("")

# Quick Navigation
lines.append("## Quick Navigation")
lines.append("")
lines.append("| Cluster | Categories | Audits |")
lines.append("|---------|------------|--------|")

for cluster, (start, end) in CLUSTERS.items():
    anchor = cluster.lower().replace(" ", "-").replace("&", "")
    count = cluster_counts[cluster]
    lines.append(f"| [{cluster}](#{anchor}-categories-{start}-{end}) | {start}-{end} | {count:,} |")

lines.append("")
lines.append("---")
lines.append("")

# Generate each cluster section
for cluster, (start, end) in CLUSTERS.items():
    lines.append(f"## {cluster} (Categories {start}-{end})")
    lines.append("")

    # Get categories in this cluster
    cluster_cats = sorted([c for c in category_info.keys() if start <= c <= end])

    for cat_num in cluster_cats:
        cat_slug = category_info[cat_num]
        cat_display = get_category_display(cat_slug)
        subcats = audits_by_category[cat_num]

        # Count audits in this category
        cat_audit_count = sum(len(audits) for audits in subcats.values())

        lines.append(f"### Category {cat_num}: {cat_display}")
        lines.append(f"**File:** `{cat_num:02d}-{cat_slug}.md` | **Audits:** {cat_audit_count}")
        lines.append("")

        # Sort subcategories and list audits
        for subcat in sorted(subcats.keys()):
            audits = subcats[subcat]
            subcat_display = format_subcategory(subcat)
            lines.append(f"#### {cat_num}.{list(sorted(subcats.keys())).index(subcat)+1} {subcat_display}")

            for audit in sorted(audits):
                lines.append(f"- {audit}")

            lines.append("")

    lines.append("---")
    lines.append("")

# Write output
with open(md_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"Generated {total_audits:,} audits across {total_categories} categories")
PYTHON_SCRIPT

# Validate the generated file
if [[ -f "$MD_FILE" ]]; then
    line_count=$(wc -l < "$MD_FILE")
    echo -e "${GREEN}✓${NC} Generated $MD_FILE ($line_count lines)"
else
    echo "Error: Failed to generate markdown file"
    exit 1
fi
