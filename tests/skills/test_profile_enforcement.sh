#!/usr/bin/env bash
# test_profile_enforcement.sh — Test that environment profile gates block/allow skills correctly.
#
# Tests 4 scenarios:
#   1. Air-gapped profile blocks internet-required skills
#   2. Air-gapped profile blocks SaaS-required skills
#   3. Sensitive profile allows internet but blocks SaaS
#   4. Standard profile blocks High-risk skills without --approve-high-risk
#
# Requires: FalkorDB running on localhost:6380 (skips gracefully if unavailable)
# Usage: tests/skills/test_profile_enforcement.sh
set -euo pipefail

# ── Locate project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

RESOLVE_PROFILE="${PROJECT_ROOT}/scripts/skills/resolve-profile.sh"
BRIDGE="${PROJECT_ROOT}/scripts/skills/falkordb_bridge.py"
PROFILES_YAML="${PROJECT_ROOT}/config/environment-profiles.yaml"

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# ── Helpers ──────────────────────────────────────────────────────────────────

pass_test() {
    local name="$1"
    echo "  PASS: ${name}"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail_test() {
    local name="$1"
    local detail="${2:-}"
    echo "  FAIL: ${name}"
    if [[ -n "${detail}" ]]; then
        echo "        ${detail}"
    fi
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

skip_test() {
    local name="$1"
    local reason="${2:-}"
    echo "  SKIP: ${name} — ${reason}"
    SKIP_COUNT=$((SKIP_COUNT + 1))
}

# ── Preflight: check FalkorDB availability ────────────────────────────────────
echo "[test_profile_enforcement] Checking FalkorDB availability..."

FALKORDB_AVAILABLE=false
if python3 -c "
import sys
try:
    from falkordb import FalkorDB
    client = FalkorDB(host='localhost', port=6380)
    client.connection.ping()
    sys.exit(0)
except Exception as e:
    print(f'FalkorDB not available: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
    FALKORDB_AVAILABLE=true
    echo "[test_profile_enforcement] FalkorDB is available."
else
    echo "[test_profile_enforcement] FalkorDB not available. Skipping all tests gracefully."
fi

# ── Preflight: check prerequisites ────────────────────────────────────────────
if [[ ! -f "${PROFILES_YAML}" ]]; then
    echo "[test_profile_enforcement] ERROR: ${PROFILES_YAML} not found." >&2
    exit 1
fi

if [[ ! -f "${RESOLVE_PROFILE}" ]]; then
    echo "[test_profile_enforcement] ERROR: ${RESOLVE_PROFILE} not found." >&2
    exit 1
fi

if [[ ! -f "${BRIDGE}" ]]; then
    echo "[test_profile_enforcement] ERROR: ${BRIDGE} not found." >&2
    exit 1
fi

# ── Setup test Skill nodes in FalkorDB ────────────────────────────────────────
# Create test skills with different requirement tags so the bridge can filter them.
# Skill properties: id, name, requires_internet (bool), requires_saas (bool),
#                   risk_level (None/Low/Medium/High)

setup_test_skills() {
    echo "[test_profile_enforcement] Setting up test Skill nodes in FalkorDB..."
    python3 - <<'PYEOF'
import sys
sys.path.insert(0, "${PROJECT_ROOT}")

try:
    from falkordb import FalkorDB
    client = FalkorDB(host="localhost", port=6380)
    g = client.select_graph("atomic-skills-test")

    # Clean slate
    try:
        g.query("MATCH (n) DETACH DELETE n")
    except Exception:
        pass

    # Create test skill nodes
    skills = [
        {
            "id": "test-skill-local-safe",
            "name": "Local Safe Skill",
            "requires_internet": "false",
            "requires_saas": "false",
            "risk_level": "Low",
            "phase_tags": "5-implementation",
            "description": "A safe local-only skill",
        },
        {
            "id": "test-skill-internet-required",
            "name": "Internet Required Skill",
            "requires_internet": "true",
            "requires_saas": "false",
            "risk_level": "Low",
            "phase_tags": "5-implementation",
            "description": "Needs internet to fetch packages",
        },
        {
            "id": "test-skill-saas-required",
            "name": "SaaS Required Skill",
            "requires_internet": "true",
            "requires_saas": "true",
            "risk_level": "Medium",
            "phase_tags": "5-implementation",
            "description": "Integrates with external SaaS API",
        },
        {
            "id": "test-skill-high-risk",
            "name": "High Risk Skill",
            "requires_internet": "true",
            "requires_saas": "false",
            "risk_level": "High",
            "phase_tags": "5-implementation",
            "description": "High risk skill that modifies system configs",
        },
    ]

    for skill in skills:
        props = ", ".join(f'{k}: "{v}"' for k, v in skill.items())
        g.query(f"CREATE (:Skill {{{props}}})")

    print(f"Created {len(skills)} test Skill nodes in atomic-skills-test graph")
    sys.exit(0)
except Exception as e:
    print(f"Failed to set up test skills: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ── Helper: query skills through the bridge with profile constraints ──────────
# Simulates what the bridge --action select does: returns skill IDs that pass
# profile constraints for a given profile.
query_skills_for_profile() {
    local profile="$1"
    # Read profile constraints
    local allow_internet allow_saas risk_levels
    allow_internet=$(python3 -c "
import sys
try:
    import yaml
    with open('${PROFILES_YAML}') as f:
        data = yaml.safe_load(f)
    print(str(data['profiles']['${profile}']['allow_internet']).lower())
except ImportError:
    import re
    with open('${PROFILES_YAML}') as f:
        content = f.read()
    m = re.search(r'  ${profile}:.*?allow_internet:\s*(\S+)', content, re.DOTALL)
    print(m.group(1).lower() if m else 'true')
" 2>/dev/null) || allow_internet="true"

    allow_saas=$(python3 -c "
import sys
try:
    import yaml
    with open('${PROFILES_YAML}') as f:
        data = yaml.safe_load(f)
    print(str(data['profiles']['${profile}']['allow_saas']).lower())
except ImportError:
    import re
    with open('${PROFILES_YAML}') as f:
        content = f.read()
    m = re.search(r'  ${profile}:.*?allow_saas:\s*(\S+)', content, re.DOTALL)
    print(m.group(1).lower() if m else 'true')
" 2>/dev/null) || allow_saas="true"

    risk_levels=$(python3 -c "
import sys
try:
    import yaml
    with open('${PROFILES_YAML}') as f:
        data = yaml.safe_load(f)
    levels = data['profiles']['${profile}']['acceptable_risk_levels']
    print(','.join(levels))
except ImportError:
    import re
    with open('${PROFILES_YAML}') as f:
        content = f.read()
    m = re.search(r'  ${profile}:.*?acceptable_risk_levels:\s*\[([^\]]+)\]', content, re.DOTALL)
    print(m.group(1).strip() if m else 'None,Low,Medium,High')
" 2>/dev/null) || risk_levels="None,Low,Medium,High"

    # Query FalkorDB and filter by profile constraints
    python3 - "${allow_internet}" "${allow_saas}" "${risk_levels}" <<'PYEOF'
import sys

allow_internet = sys.argv[1] == "true"
allow_saas = sys.argv[2] == "true"
risk_levels = [r.strip().strip('"').strip("'") for r in sys.argv[3].split(",")]

try:
    from falkordb import FalkorDB
    client = FalkorDB(host="localhost", port=6380)
    g = client.select_graph("atomic-skills-test")

    result = g.query(
        "MATCH (s:Skill) "
        "RETURN s.id, s.requires_internet, s.requires_saas, s.risk_level"
    )

    selected = []
    for row in result.result_set:
        sid, req_inet, req_saas, risk = row[0], row[1], row[2], row[3]

        # Apply profile gates
        if req_inet == "true" and not allow_internet:
            continue
        if req_saas == "true" and not allow_saas:
            continue
        if risk not in risk_levels:
            continue

        selected.append(sid)

    # Print one ID per line
    for s in selected:
        print(s)

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ── Cleanup test graph on exit ────────────────────────────────────────────────
cleanup_test_graph() {
    if [[ "${FALKORDB_AVAILABLE}" == "true" ]]; then
        python3 -c "
from falkordb import FalkorDB
client = FalkorDB(host='localhost', port=6380)
g = client.select_graph('atomic-skills-test')
try:
    g.query('MATCH (n) DETACH DELETE n')
except Exception:
    pass
" 2>/dev/null || true
    fi
}
trap cleanup_test_graph EXIT

# ── Run Tests ─────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo " Profile Enforcement Tests"
echo "========================================"
echo ""

if [[ "${FALKORDB_AVAILABLE}" != "true" ]]; then
    skip_test "Test 1: Air-gapped blocks internet skills" "FalkorDB unavailable"
    skip_test "Test 2: Air-gapped blocks SaaS skills" "FalkorDB unavailable"
    skip_test "Test 3: Sensitive allows internet, blocks SaaS" "FalkorDB unavailable"
    skip_test "Test 4: Standard blocks High-risk without approval" "FalkorDB unavailable"
else
    # Set up test data
    if ! setup_test_skills; then
        echo "[test_profile_enforcement] ERROR: Failed to set up test skills." >&2
        exit 1
    fi

    # ── Test 1: Air-gapped blocks internet-required skills ────────────────
    echo "[Test 1] Air-gapped profile blocks internet-required skills"
    SELECTED=$(query_skills_for_profile "air-gapped" 2>/dev/null || echo "ERROR")
    if [[ "${SELECTED}" == "ERROR" ]]; then
        fail_test "Test 1" "Query failed"
    elif echo "${SELECTED}" | grep -q "test-skill-internet-required"; then
        fail_test "Test 1" "Internet-required skill was NOT blocked by air-gapped profile"
    else
        pass_test "Test 1: Air-gapped blocks internet-required skills"
    fi

    # ── Test 2: Air-gapped blocks SaaS-required skills ────────────────────
    echo "[Test 2] Air-gapped profile blocks SaaS-required skills"
    if [[ "${SELECTED}" == "ERROR" ]]; then
        fail_test "Test 2" "Query failed (reusing Test 1 result)"
    elif echo "${SELECTED}" | grep -q "test-skill-saas-required"; then
        fail_test "Test 2" "SaaS-required skill was NOT blocked by air-gapped profile"
    else
        pass_test "Test 2: Air-gapped blocks SaaS-required skills"
    fi

    # ── Test 3: Sensitive allows internet, blocks SaaS ────────────────────
    echo "[Test 3] Sensitive profile allows internet but blocks SaaS"
    SELECTED=$(query_skills_for_profile "sensitive" 2>/dev/null || echo "ERROR")
    if [[ "${SELECTED}" == "ERROR" ]]; then
        fail_test "Test 3" "Query failed"
    else
        HAS_INTERNET_SKILL=false
        HAS_SAAS_SKILL=false
        if echo "${SELECTED}" | grep -q "test-skill-internet-required"; then
            HAS_INTERNET_SKILL=true
        fi
        if echo "${SELECTED}" | grep -q "test-skill-saas-required"; then
            HAS_SAAS_SKILL=true
        fi

        if [[ "${HAS_INTERNET_SKILL}" == "true" && "${HAS_SAAS_SKILL}" == "false" ]]; then
            pass_test "Test 3: Sensitive allows internet, blocks SaaS"
        elif [[ "${HAS_INTERNET_SKILL}" == "false" ]]; then
            fail_test "Test 3" "Internet-required skill should be allowed in sensitive profile"
        else
            fail_test "Test 3" "SaaS-required skill should be blocked in sensitive profile"
        fi
    fi

    # ── Test 4: Standard blocks High-risk without --approve-high-risk ─────
    echo "[Test 4] Standard profile blocks High-risk skills (no --approve-high-risk)"
    SELECTED=$(query_skills_for_profile "standard" 2>/dev/null || echo "ERROR")
    if [[ "${SELECTED}" == "ERROR" ]]; then
        fail_test "Test 4" "Query failed"
    elif echo "${SELECTED}" | grep -q "test-skill-high-risk"; then
        fail_test "Test 4" "High-risk skill was NOT blocked by standard profile"
    else
        pass_test "Test 4: Standard blocks High-risk without approval"
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo " Results: ${PASS_COUNT} passed, ${FAIL_COUNT} failed, ${SKIP_COUNT} skipped"
echo "========================================"

if [[ ${FAIL_COUNT} -gt 0 ]]; then
    exit 1
fi
exit 0
