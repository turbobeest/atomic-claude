#!/bin/bash
#
# Build agent-manifest.json from agent-inventory.csv
#
# This script generates the JSON manifest from the CSV source of truth.
# Run this after updating agent-inventory.csv to keep them in sync.
#
# Usage: ./build-manifest.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV_FILE="$SCRIPT_DIR/agent-inventory.csv"
JSON_FILE="$SCRIPT_DIR/agent-manifest.json"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}Building agent-manifest.json from agent-inventory.csv...${NC}"

# Verify CSV exists
if [[ ! -f "$CSV_FILE" ]]; then
    echo "Error: $CSV_FILE not found"
    exit 1
fi

# Count agents (excluding header)
agent_count=$(($(wc -l < "$CSV_FILE") - 1))
echo "  Processing $agent_count agents..."

# Use Python for proper CSV parsing
python3 << 'PYTHON_SCRIPT'
import csv
import json
from datetime import date

csv_file = "agent-inventory.csv"
json_file = "agent-manifest.json"

agents = []

with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Parse model_fallbacks from semicolon-separated to array
        fallbacks = row['model_fallbacks'].split(';') if row['model_fallbacks'] else []

        # Parse composite_score as number if present
        score = row.get('composite_score', '')
        if score:
            try:
                score = float(score)
            except ValueError:
                score = None
        else:
            score = None

        agent = {
            'name': row['name'],
            'tier': row['tier'],
            'model': row['model'],
            'model_fallbacks': fallbacks,
            'category': row.get('category', ''),
            'subcategory': row.get('subcategory', ''),
            'description': row['description'],
            'grade': row.get('grade', ''),
            'composite_score': score,
            'path': row['path'],
            'role': row.get('role', 'executor'),
            'rationale': row.get('rationale', '')
        }
        agents.append(agent)

# Sort by name for consistency
agents.sort(key=lambda x: x['name'])

manifest = {
    'version': '3.0.0',
    'name': 'Claude Orchestra Agent Pool',
    'description': 'Centralized agent definitions for Claude Orchestra. Generated from agent-inventory.csv.',
    'lastUpdated': date.today().isoformat(),
    'author': 'turbobeest',
    'repository': 'https://github.com/turbobeest/agents',
    'generatedFrom': 'agent-inventory.csv',
    'agents': agents
}

with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f"Generated {len(agents)} agents")
PYTHON_SCRIPT

# Validate the generated JSON
if jq -e . "$JSON_FILE" > /dev/null 2>&1; then
    final_count=$(jq '.agents | length' "$JSON_FILE")
    echo -e "${GREEN}✓${NC} Generated $JSON_FILE with $final_count agents"
else
    echo "Error: Generated invalid JSON"
    exit 1
fi
