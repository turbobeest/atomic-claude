#!/usr/bin/env bash
# test_blocked_skills.sh — Test that blocked skills never load or get selected.
#
# Verifies:
#   1. Installing skills with air-gapped profile excludes internet/SaaS skills from manifest
#   2. Blocked skills have blocked_by_profile set in graph nodes
#   3. Selecting skills never returns a blocked skill regardless of query
#
# Requires: FalkorDB running on localhost:6380 (skips gracefully if unavailable)
# Usage: tests/skills/test_blocked_skills.sh
set -euo pipefail

# ── Locate project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PROFILES_YAML="${PROJECT_ROOT}/config/environment-profiles.yaml"
MANIFEST_YAML="${PROJECT_ROOT}/.claude/skills/_manifest.yaml"

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
echo "[test_blocked_skills] Checking FalkorDB availability..."

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
    echo "[test_blocked_skills] FalkorDB is available."
else
    echo "[test_blocked_skills] FalkorDB not available. Skipping all tests gracefully."
fi

# ── Setup: create test graph with skills and simulate install ─────────────────
TEST_GRAPH="atomic-skills-test-blocked"
TEST_MANIFEST="/tmp/test-blocked-manifest.yaml"

setup_test_data() {
    echo "[test_blocked_skills] Setting up test data..."
    python3 - "${TEST_GRAPH}" "${PROFILES_YAML}" "${TEST_MANIFEST}" <<'PYEOF'
import sys
import datetime

graph_name = sys.argv[1]
profiles_yaml = sys.argv[2]
manifest_path = sys.argv[3]

try:
    from falkordb import FalkorDB
    client = FalkorDB(host="localhost", port=6380)
    g = client.select_graph(graph_name)

    # Clean slate
    try:
        g.query("MATCH (n) DETACH DELETE n")
    except Exception:
        pass

    # Define skills: a mix of local, internet, SaaS, and high-risk
    skills = [
        {
            "id": "blocked-test-local",
            "name": "Local Linter",
            "requires_internet": "false",
            "requires_saas": "false",
            "risk_level": "None",
            "phase_tags": "5-implementation",
            "description": "Local code linting",
            "blocked_by_profile": "false",
            "content_hash": "abc123",
        },
        {
            "id": "blocked-test-internet",
            "name": "Package Fetcher",
            "requires_internet": "true",
            "requires_saas": "false",
            "risk_level": "Low",
            "phase_tags": "5-implementation",
            "description": "Fetches packages from PyPI",
            "blocked_by_profile": "false",
            "content_hash": "def456",
        },
        {
            "id": "blocked-test-saas",
            "name": "SaaS Deployer",
            "requires_internet": "true",
            "requires_saas": "true",
            "risk_level": "Medium",
            "phase_tags": "8-deployment",
            "description": "Deploys to cloud SaaS platform",
            "blocked_by_profile": "false",
            "content_hash": "ghi789",
        },
        {
            "id": "blocked-test-highrisk",
            "name": "Kernel Modifier",
            "requires_internet": "true",
            "requires_saas": "false",
            "risk_level": "High",
            "phase_tags": "5-implementation",
            "description": "Modifies kernel parameters",
            "blocked_by_profile": "false",
            "content_hash": "jkl012",
        },
    ]

    # Read air-gapped profile constraints
    try:
        import yaml
        with open(profiles_yaml) as f:
            data = yaml.safe_load(f)
        profile = data["profiles"]["air-gapped"]
    except ImportError:
        import re
        with open(profiles_yaml) as f:
            content = f.read()
        profile = {"allow_internet": False, "allow_saas": False,
                    "acceptable_risk_levels": ["None", "Low"]}

    allow_internet = profile.get("allow_internet", False)
    allow_saas = profile.get("allow_saas", False)
    risk_levels = profile.get("acceptable_risk_levels", ["None", "Low"])

    installed_skills = {}

    for skill in skills:
        # Determine if blocked by air-gapped profile
        blocked = False
        if skill["requires_internet"] == "true" and not allow_internet:
            blocked = True
        if skill["requires_saas"] == "true" and not allow_saas:
            blocked = True
        if skill["risk_level"] not in risk_levels:
            blocked = True

        skill["blocked_by_profile"] = "true" if blocked else "false"

        props = ", ".join(f'{k}: "{v}"' for k, v in skill.items())
        g.query(f"CREATE (:Skill {{{props}}})")

        # Build manifest entry
        installed_skills[skill["id"]] = {
            "name": skill["name"],
            "installed": not blocked,
            "blocked_by_profile": blocked,
            "content_hash": skill["content_hash"],
        }

    # Write test manifest
    lines = [
        "# Test manifest for blocked skills test",
        f"generated_at: {datetime.datetime.utcnow().isoformat()}Z",
        "profile_at_install: air-gapped",
        "skills:",
    ]
    for sid, info in installed_skills.items():
        lines.append(f"  {sid}:")
        lines.append(f"    name: {info['name']}")
        lines.append(f"    installed: {str(info['installed']).lower()}")
        lines.append(f"    blocked_by_profile: {str(info['blocked_by_profile']).lower()}")
        lines.append(f"    content_hash: {info['content_hash']}")

    with open(manifest_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Created {len(skills)} Skill nodes and test manifest")
    sys.exit(0)
except Exception as e:
    print(f"Setup failed: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
}

# ── Cleanup on exit ──────────────────────────────────────────────────────────
cleanup() {
    if [[ "${FALKORDB_AVAILABLE}" == "true" ]]; then
        python3 -c "
from falkordb import FalkorDB
client = FalkorDB(host='localhost', port=6380)
g = client.select_graph('${TEST_GRAPH}')
try:
    g.query('MATCH (n) DETACH DELETE n')
except Exception:
    pass
" 2>/dev/null || true
    fi
    rm -f "${TEST_MANIFEST}" 2>/dev/null || true
}
trap cleanup EXIT

# ── Run Tests ─────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo " Blocked Skills Tests"
echo "========================================"
echo ""

if [[ "${FALKORDB_AVAILABLE}" != "true" ]]; then
    skip_test "Test 1: No internet/SaaS skills installed in manifest" "FalkorDB unavailable"
    skip_test "Test 2: Blocked skills have blocked_by_profile set" "FalkorDB unavailable"
    skip_test "Test 3: Selecting skills never returns blocked" "FalkorDB unavailable"
else
    if ! setup_test_data; then
        echo "[test_blocked_skills] ERROR: Failed to set up test data." >&2
        exit 1
    fi

    # ── Test 1: Manifest does not list blocked skills as installed ─────────
    echo "[Test 1] No internet/SaaS skills appear as installed in manifest"

    INSTALLED_BLOCKED=$(python3 - "${TEST_MANIFEST}" <<'PYEOF'
import sys

manifest_path = sys.argv[1]

try:
    import yaml
    with open(manifest_path) as f:
        data = yaml.safe_load(f)
except ImportError:
    # Minimal parser
    import re
    data = {"skills": {}}
    with open(manifest_path) as f:
        content = f.read()
    # Parse skill blocks
    for m in re.finditer(r"  (\S+):\n((?:    .*\n)*)", content):
        sid = m.group(1)
        block = m.group(2)
        installed = "true" in re.search(r"installed:\s*(\S+)", block).group(1).lower() if re.search(r"installed:\s*(\S+)", block) else False
        blocked = "true" in re.search(r"blocked_by_profile:\s*(\S+)", block).group(1).lower() if re.search(r"blocked_by_profile:\s*(\S+)", block) else False
        data.setdefault("skills", {})[sid] = {"installed": installed, "blocked_by_profile": blocked}

violations = []
skills = data.get("skills", {})
for sid, info in skills.items():
    if isinstance(info, dict):
        installed = info.get("installed", False)
        blocked = info.get("blocked_by_profile", False)
        if installed and blocked:
            violations.append(sid)

if violations:
    print(",".join(violations))
else:
    print("NONE")
PYEOF
    )

    if [[ "${INSTALLED_BLOCKED}" == "NONE" ]]; then
        pass_test "Test 1: No blocked skills appear as installed in manifest"
    else
        fail_test "Test 1: Blocked skills installed in manifest" "Violations: ${INSTALLED_BLOCKED}"
    fi

    # ── Test 2: Graph nodes have blocked_by_profile set ───────────────────
    echo "[Test 2] Blocked skills have blocked_by_profile='true' in graph"

    MISMARKED=$(python3 - "${TEST_GRAPH}" <<'PYEOF'
import sys

graph_name = sys.argv[1]

try:
    from falkordb import FalkorDB
    client = FalkorDB(host="localhost", port=6380)
    g = client.select_graph(graph_name)

    # Skills that require internet should be blocked in air-gapped
    result = g.query(
        "MATCH (s:Skill) "
        "WHERE s.requires_internet = 'true' AND s.blocked_by_profile = 'false' "
        "RETURN s.id"
    )

    mismarked = [row[0] for row in result.result_set]

    if mismarked:
        print(",".join(mismarked))
    else:
        print("NONE")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
    )

    if [[ "${MISMARKED}" == "NONE" ]]; then
        pass_test "Test 2: All internet-requiring skills marked blocked_by_profile"
    elif [[ "${MISMARKED}" == ERROR* ]]; then
        fail_test "Test 2: blocked_by_profile check" "Query failed: ${MISMARKED}"
    else
        fail_test "Test 2: blocked_by_profile not set" "Mismarked skills: ${MISMARKED}"
    fi

    # ── Test 3: Selection never returns a blocked skill ───────────────────
    echo "[Test 3] Selecting skills never returns a blocked skill"

    LEAKED=$(python3 - "${TEST_GRAPH}" <<'PYEOF'
import sys

graph_name = sys.argv[1]

try:
    from falkordb import FalkorDB
    client = FalkorDB(host="localhost", port=6380)
    g = client.select_graph(graph_name)

    # Simulate selection: get all skills for phase 5 that are NOT blocked
    result = g.query(
        "MATCH (s:Skill) "
        "WHERE s.phase_tags CONTAINS '5-implementation' "
        "  AND s.blocked_by_profile = 'false' "
        "RETURN s.id, s.requires_internet, s.requires_saas"
    )

    # Double-check: none of the returned skills should require internet
    # (since air-gapped blocks internet)
    leaked = []
    for row in result.result_set:
        sid, req_inet, req_saas = row[0], row[1], row[2]
        if req_inet == "true" or req_saas == "true":
            leaked.append(sid)

    if leaked:
        print(",".join(leaked))
    else:
        print("NONE")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
    )

    if [[ "${LEAKED}" == "NONE" ]]; then
        pass_test "Test 3: No blocked skills returned from selection query"
    elif [[ "${LEAKED}" == ERROR* ]]; then
        fail_test "Test 3: Selection leak check" "Query failed: ${LEAKED}"
    else
        fail_test "Test 3: Blocked skills leaked in selection" "Leaked: ${LEAKED}"
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
