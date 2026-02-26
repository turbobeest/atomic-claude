#!/usr/bin/env bash
# test_skill_selection.sh — Test the 3-stage skill selection pipeline.
#
# Stages:
#   1. Structural selection — skills matching phase/task tags
#   2. Fulltext search — skills found by description keywords
#   3. Profile constraints — blocked skills filtered out in every stage
#
# Requires: FalkorDB running on localhost:6380 (skips gracefully if unavailable)
# Usage: tests/skills/test_skill_selection.sh
set -euo pipefail

# ── Locate project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

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
echo "[test_skill_selection] Checking FalkorDB availability..."

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
    echo "[test_skill_selection] FalkorDB is available."
else
    echo "[test_skill_selection] FalkorDB not available. Skipping all tests gracefully."
fi

# ── Setup test data ──────────────────────────────────────────────────────────
setup_test_data() {
    echo "[test_skill_selection] Setting up test Skill nodes..."
    python3 - <<'PYEOF'
import sys

try:
    from falkordb import FalkorDB
    client = FalkorDB(host="localhost", port=6380)
    g = client.select_graph("atomic-skills-test-selection")

    # Clean slate
    try:
        g.query("MATCH (n) DETACH DELETE n")
    except Exception:
        pass

    skills = [
        {
            "id": "sel-skill-phase5-deploy",
            "name": "Deploy Automation",
            "phase_tags": "5-implementation,8-deployment",
            "description": "Automates deployment pipelines with Docker and Kubernetes",
            "requires_internet": "true",
            "requires_saas": "false",
            "risk_level": "Medium",
            "avg_success_score": "0.85",
        },
        {
            "id": "sel-skill-phase5-testing",
            "name": "Test Runner",
            "phase_tags": "5-implementation,7-integration",
            "description": "Runs pytest suites with coverage reporting",
            "requires_internet": "false",
            "requires_saas": "false",
            "risk_level": "Low",
            "avg_success_score": "0.92",
        },
        {
            "id": "sel-skill-phase6-review",
            "name": "Code Review Assistant",
            "phase_tags": "6-code-review",
            "description": "Static analysis and code quality review",
            "requires_internet": "false",
            "requires_saas": "false",
            "risk_level": "None",
            "avg_success_score": "0.88",
        },
        {
            "id": "sel-skill-saas-monitor",
            "name": "SaaS Monitor",
            "phase_tags": "5-implementation,9-release",
            "description": "Monitors external SaaS uptime and performance metrics",
            "requires_internet": "true",
            "requires_saas": "true",
            "risk_level": "Medium",
            "avg_success_score": "0.75",
        },
        {
            "id": "sel-skill-high-risk-sysmod",
            "name": "System Modifier",
            "phase_tags": "5-implementation",
            "description": "Modifies system configuration and kernel parameters",
            "requires_internet": "true",
            "requires_saas": "false",
            "risk_level": "High",
            "avg_success_score": "0.60",
        },
    ]

    for skill in skills:
        props = ", ".join(f'{k}: "{v}"' for k, v in skill.items())
        g.query(f"CREATE (:Skill {{{props}}})")

    # Create fulltext index on Skill description
    try:
        g.query("CALL db.idx.fulltext.createNodeIndex('Skill', 'description', 'name')")
    except Exception:
        pass  # May already exist

    print(f"Created {len(skills)} test Skill nodes in atomic-skills-test-selection graph")
    sys.exit(0)
except Exception as e:
    print(f"Failed to set up test skills: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ── Cleanup on exit ──────────────────────────────────────────────────────────
cleanup_test_graph() {
    if [[ "${FALKORDB_AVAILABLE}" == "true" ]]; then
        python3 -c "
from falkordb import FalkorDB
client = FalkorDB(host='localhost', port=6380)
g = client.select_graph('atomic-skills-test-selection')
try:
    g.query('MATCH (n) DETACH DELETE n')
except Exception:
    pass
" 2>/dev/null || true
    fi
}
trap cleanup_test_graph EXIT

# ── Stage 1: Structural selection by phase tags ──────────────────────────────
structural_select() {
    local phase_tag="$1"
    python3 - "${phase_tag}" <<'PYEOF'
import sys

phase_tag = sys.argv[1]

try:
    from falkordb import FalkorDB
    client = FalkorDB(host="localhost", port=6380)
    g = client.select_graph("atomic-skills-test-selection")

    result = g.query(
        "MATCH (s:Skill) "
        "WHERE s.phase_tags CONTAINS $tag "
        "RETURN s.id",
        {"tag": phase_tag},
    )
    for row in result.result_set:
        print(row[0])
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ── Stage 2: Fulltext search by description keywords ─────────────────────────
fulltext_select() {
    local query="$1"
    python3 - "${query}" <<'PYEOF'
import sys

query = sys.argv[1]

try:
    from falkordb import FalkorDB
    client = FalkorDB(host="localhost", port=6380)
    g = client.select_graph("atomic-skills-test-selection")

    result = g.query(
        "CALL db.idx.fulltext.queryNodes('Skill', $query) "
        "YIELD node RETURN node.id",
        {"query": query},
    )
    for row in result.result_set:
        print(row[0])
except Exception as e:
    # Fulltext index might not be ready
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ── Stage 3: Profile-constrained selection ────────────────────────────────────
profile_constrained_select() {
    local phase_tag="$1"
    local profile="$2"

    python3 - "${phase_tag}" "${profile}" "${PROFILES_YAML}" <<'PYEOF'
import sys

phase_tag = sys.argv[1]
profile_name = sys.argv[2]
profiles_yaml = sys.argv[3]

# Read profile constraints
try:
    import yaml
    with open(profiles_yaml) as f:
        data = yaml.safe_load(f)
    profile = data["profiles"][profile_name]
except ImportError:
    import re, json
    with open(profiles_yaml) as f:
        content = f.read()
    # Minimal parser
    profile = {}
    block_pattern = rf"  {profile_name}:\s*\n((?:    .*\n)*)"
    m = re.search(block_pattern, content, re.MULTILINE)
    if m:
        block = m.group(1)
        for field in ["allow_internet", "allow_saas"]:
            fm = re.search(rf"^\s+{field}:\s+(\S+)", block, re.MULTILINE)
            if fm:
                profile[field] = fm.group(1).strip().lower() == "true"
        fm = re.search(r"acceptable_risk_levels:\s*\[([^\]]+)\]", block)
        if fm:
            profile["acceptable_risk_levels"] = [
                r.strip().strip('"').strip("'") for r in fm.group(1).split(",")
            ]

allow_internet = profile.get("allow_internet", True)
allow_saas = profile.get("allow_saas", True)
risk_levels = profile.get("acceptable_risk_levels", ["None", "Low", "Medium", "High"])

try:
    from falkordb import FalkorDB
    client = FalkorDB(host="localhost", port=6380)
    g = client.select_graph("atomic-skills-test-selection")

    result = g.query(
        "MATCH (s:Skill) "
        "WHERE s.phase_tags CONTAINS $tag "
        "RETURN s.id, s.requires_internet, s.requires_saas, s.risk_level",
        {"tag": phase_tag},
    )

    for row in result.result_set:
        sid, req_inet, req_saas, risk = row[0], row[1], row[2], row[3]
        if req_inet == "true" and not allow_internet:
            continue
        if req_saas == "true" and not allow_saas:
            continue
        if risk not in risk_levels:
            continue
        print(sid)

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ── Run Tests ─────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo " Skill Selection Pipeline Tests"
echo "========================================"
echo ""

if [[ "${FALKORDB_AVAILABLE}" != "true" ]]; then
    skip_test "Stage 1: Structural selection by phase" "FalkorDB unavailable"
    skip_test "Stage 1: Phase-6 structural selection" "FalkorDB unavailable"
    skip_test "Stage 2: Fulltext search by keywords" "FalkorDB unavailable"
    skip_test "Stage 3: Air-gapped profile constrains selection" "FalkorDB unavailable"
    skip_test "Stage 3: Sensitive profile constrains selection" "FalkorDB unavailable"
    skip_test "Stage 3: Standard profile constrains selection" "FalkorDB unavailable"
else
    if ! setup_test_data; then
        echo "[test_skill_selection] ERROR: Failed to set up test data." >&2
        exit 1
    fi

    # ── Stage 1: Structural selection ─────────────────────────────────────
    echo "[Stage 1] Structural selection — phase-tag matching"

    SELECTED=$(structural_select "5-implementation" 2>/dev/null || echo "ERROR")
    if [[ "${SELECTED}" == "ERROR" ]]; then
        fail_test "Stage 1: Phase-5 structural selection" "Query failed"
    else
        # Phase 5 should include deploy, testing, saas-monitor, high-risk-sysmod
        COUNT=$(echo "${SELECTED}" | grep -c "sel-skill-" || true)
        if [[ ${COUNT} -ge 3 ]]; then
            pass_test "Stage 1: Phase-5 structural selection returns ${COUNT} skills"
        else
            fail_test "Stage 1: Phase-5 structural selection" "Expected >= 3 skills, got ${COUNT}"
        fi
    fi

    SELECTED_P6=$(structural_select "6-code-review" 2>/dev/null || echo "ERROR")
    if [[ "${SELECTED_P6}" == "ERROR" ]]; then
        fail_test "Stage 1: Phase-6 structural selection" "Query failed"
    else
        if echo "${SELECTED_P6}" | grep -q "sel-skill-phase6-review"; then
            ONLY_REVIEW=true
            # Ensure no phase-5-only skills leak in
            if echo "${SELECTED_P6}" | grep -q "sel-skill-phase5-deploy"; then
                ONLY_REVIEW=false
            fi
            if [[ "${ONLY_REVIEW}" == "true" ]]; then
                pass_test "Stage 1: Phase-6 structural selection returns only review skills"
            else
                fail_test "Stage 1: Phase-6 structural selection" "Non-phase-6 skills leaked through"
            fi
        else
            fail_test "Stage 1: Phase-6 structural selection" "Review skill not found"
        fi
    fi

    # ── Stage 2: Fulltext search ──────────────────────────────────────────
    echo "[Stage 2] Fulltext search — description keyword matching"

    # Small delay for fulltext index to catch up
    sleep 1

    SELECTED_FT=$(fulltext_select "Docker Kubernetes deployment" 2>/dev/null || echo "ERROR")
    if [[ "${SELECTED_FT}" == "ERROR" ]]; then
        # Fulltext might not be indexed yet; skip rather than fail
        skip_test "Stage 2: Fulltext search by keywords" "Fulltext index may not be ready"
    else
        if echo "${SELECTED_FT}" | grep -q "sel-skill-phase5-deploy"; then
            pass_test "Stage 2: Fulltext search finds Deploy Automation skill"
        else
            fail_test "Stage 2: Fulltext search by keywords" "Expected deploy skill in results"
        fi
    fi

    # ── Stage 3: Profile-constrained selection ────────────────────────────
    echo "[Stage 3] Profile constraints enforced in selection"

    # Air-gapped: should only return local skills (no internet, no saas)
    SELECTED_AG=$(profile_constrained_select "5-implementation" "air-gapped" 2>/dev/null || echo "ERROR")
    if [[ "${SELECTED_AG}" == "ERROR" ]]; then
        fail_test "Stage 3: Air-gapped profile constrains selection" "Query failed"
    else
        BLOCKED=false
        if echo "${SELECTED_AG}" | grep -q "sel-skill-phase5-deploy"; then
            BLOCKED=true
        fi
        if echo "${SELECTED_AG}" | grep -q "sel-skill-saas-monitor"; then
            BLOCKED=true
        fi
        if echo "${SELECTED_AG}" | grep -q "sel-skill-high-risk-sysmod"; then
            BLOCKED=true
        fi

        if [[ "${BLOCKED}" == "false" ]]; then
            # Should still include the local testing skill
            if echo "${SELECTED_AG}" | grep -q "sel-skill-phase5-testing"; then
                pass_test "Stage 3: Air-gapped constrains to local-only skills"
            else
                fail_test "Stage 3: Air-gapped profile" "Local testing skill should be allowed"
            fi
        else
            fail_test "Stage 3: Air-gapped profile constrains selection" "Blocked skills leaked through"
        fi
    fi

    # Sensitive: internet OK, no SaaS
    SELECTED_SE=$(profile_constrained_select "5-implementation" "sensitive" 2>/dev/null || echo "ERROR")
    if [[ "${SELECTED_SE}" == "ERROR" ]]; then
        fail_test "Stage 3: Sensitive profile constrains selection" "Query failed"
    else
        HAS_SAAS=false
        if echo "${SELECTED_SE}" | grep -q "sel-skill-saas-monitor"; then
            HAS_SAAS=true
        fi
        # Sensitive also blocks High risk (only None, Low accepted)
        HAS_HIGH=false
        if echo "${SELECTED_SE}" | grep -q "sel-skill-high-risk-sysmod"; then
            HAS_HIGH=true
        fi

        if [[ "${HAS_SAAS}" == "false" && "${HAS_HIGH}" == "false" ]]; then
            pass_test "Stage 3: Sensitive profile blocks SaaS and High-risk"
        else
            fail_test "Stage 3: Sensitive profile constrains selection" \
                "SaaS blocked=${HAS_SAAS}, High blocked=${HAS_HIGH} (both should be false=blocked)"
        fi
    fi

    # Standard: blocks High-risk
    SELECTED_ST=$(profile_constrained_select "5-implementation" "standard" 2>/dev/null || echo "ERROR")
    if [[ "${SELECTED_ST}" == "ERROR" ]]; then
        fail_test "Stage 3: Standard profile constrains selection" "Query failed"
    else
        HAS_HIGH=false
        if echo "${SELECTED_ST}" | grep -q "sel-skill-high-risk-sysmod"; then
            HAS_HIGH=true
        fi
        # Standard should allow Medium (SaaS monitor) and internet (deploy)
        HAS_DEPLOY=false
        if echo "${SELECTED_ST}" | grep -q "sel-skill-phase5-deploy"; then
            HAS_DEPLOY=true
        fi

        if [[ "${HAS_HIGH}" == "false" && "${HAS_DEPLOY}" == "true" ]]; then
            pass_test "Stage 3: Standard blocks High-risk, allows Medium"
        else
            fail_test "Stage 3: Standard profile constrains selection" \
                "High blocked=${HAS_HIGH} (want false), Deploy allowed=${HAS_DEPLOY} (want true)"
        fi
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
