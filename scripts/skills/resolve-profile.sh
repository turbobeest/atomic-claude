#!/usr/bin/env bash
# resolve-profile.sh — Resolve and lock the environment profile for Atomic Claude skills.
#
# Priority order:
#   1. ATOMIC_ENV_PROFILE env var (highest)
#   2. .claude/active-profile.yaml (persisted from previous run)
#   3. Auto-detection: no network → air-gapped, .security-sensitive → sensitive, else standard
#
# Validates against config/environment-profiles.yaml, writes locked profile,
# and exports environment variables for downstream consumers.
#
# Usage:
#   source scripts/skills/resolve-profile.sh   # to export vars into current shell
#   bash scripts/skills/resolve-profile.sh      # to just lock the profile
set -euo pipefail

# ── Locate project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PROFILES_YAML="${PROJECT_ROOT}/config/environment-profiles.yaml"
ACTIVE_PROFILE_YAML="${PROJECT_ROOT}/.claude/active-profile.yaml"

# ── Ensure prerequisites ─────────────────────────────────────────────────────
if [[ ! -f "${PROFILES_YAML}" ]]; then
    echo "[resolve-profile] ERROR: ${PROFILES_YAML} not found." >&2
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "[resolve-profile] ERROR: python3 is required but not found." >&2
    exit 1
fi

mkdir -p "${PROJECT_ROOT}/.claude"

# ── Helper: validate profile name against profiles YAML ──────────────────────
validate_profile() {
    local profile_name="$1"
    python3 -c "
import sys, os
try:
    import yaml
except ImportError:
    # Fallback: minimal YAML parsing for profile names
    with open('${PROFILES_YAML}') as f:
        content = f.read()
    # Look for top-level keys under 'profiles:'
    import re
    names = re.findall(r'^  ([a-z_-]+):\s*$', content, re.MULTILINE)
    if '${profile_name}' in names:
        sys.exit(0)
    else:
        print('Valid profiles: ' + ', '.join(names), file=sys.stderr)
        sys.exit(1)
else:
    with open('${PROFILES_YAML}') as f:
        data = yaml.safe_load(f)
    profiles = data.get('profiles', {})
    if '${profile_name}' in profiles:
        sys.exit(0)
    else:
        print('Valid profiles: ' + ', '.join(profiles.keys()), file=sys.stderr)
        sys.exit(1)
"
}

# ── Helper: read a field from profiles YAML for a given profile ───────────────
read_profile_field() {
    local profile_name="$1"
    local field="$2"
    python3 -c "
import sys, json
try:
    import yaml
    with open('${PROFILES_YAML}') as f:
        data = yaml.safe_load(f)
    value = data['profiles']['${profile_name}']['${field}']
except ImportError:
    # Fallback: use a minimal approach to extract fields
    import re
    with open('${PROFILES_YAML}') as f:
        content = f.read()

    # Find the profile block
    pattern = r'^  ${profile_name}:\s*\n((?:    .*\n)*)'
    m = re.search(pattern, content, re.MULTILINE)
    if not m:
        sys.exit(1)
    block = m.group(1)

    # Extract the field
    field_pattern = r'^\s+${field}:\s+(.+)$'
    fm = re.search(field_pattern, block, re.MULTILINE)
    if not fm:
        sys.exit(1)
    raw = fm.group(1).strip()

    # Parse value (bool, list, string)
    if raw in ('true', 'True'):
        value = True
    elif raw in ('false', 'False'):
        value = False
    elif raw.startswith('['):
        # Parse YAML-style inline list
        value = [s.strip().strip('\"').strip(\"'\") for s in raw.strip('[]').split(',') if s.strip()]
    else:
        value = raw.strip('\"').strip(\"'\")

if isinstance(value, list):
    print(','.join(str(v) for v in value))
elif isinstance(value, bool):
    print('true' if value else 'false')
else:
    print(value)
" 2>/dev/null
}

# ── Helper: read persisted profile from active-profile.yaml ──────────────────
read_persisted_profile() {
    if [[ ! -f "${ACTIVE_PROFILE_YAML}" ]]; then
        return 1
    fi
    python3 -c "
import sys
try:
    import yaml
    with open('${ACTIVE_PROFILE_YAML}') as f:
        data = yaml.safe_load(f)
    name = data.get('profile')
    if name:
        print(name)
        sys.exit(0)
    sys.exit(1)
except ImportError:
    import re
    with open('${ACTIVE_PROFILE_YAML}') as f:
        content = f.read()
    m = re.search(r'^profile:\s+(\S+)', content, re.MULTILINE)
    if m:
        print(m.group(1).strip('\"').strip(\"'\"))
        sys.exit(0)
    sys.exit(1)
except Exception:
    sys.exit(1)
" 2>/dev/null
}

# ── Step 1: Resolve profile name ─────────────────────────────────────────────
RESOLVED_PROFILE=""
RESOLUTION_METHOD=""

# Priority 1: Environment variable
if [[ -n "${ATOMIC_ENV_PROFILE:-}" ]]; then
    RESOLVED_PROFILE="${ATOMIC_ENV_PROFILE}"
    RESOLUTION_METHOD="env-var"
    echo "[resolve-profile] Using ATOMIC_ENV_PROFILE from environment: ${RESOLVED_PROFILE}"
fi

# Priority 2: Persisted profile
if [[ -z "${RESOLVED_PROFILE}" ]]; then
    if PERSISTED=$(read_persisted_profile); then
        RESOLVED_PROFILE="${PERSISTED}"
        RESOLUTION_METHOD="persisted"
        echo "[resolve-profile] Using persisted profile: ${RESOLVED_PROFILE}"
    fi
fi

# Priority 3: Auto-detection
if [[ -z "${RESOLVED_PROFILE}" ]]; then
    RESOLUTION_METHOD="auto-detect"

    # Check network connectivity (2-second timeout, suppress all output)
    HAS_NETWORK=false
    if ping -c 1 -W 2 8.8.8.8 &>/dev/null 2>&1 || \
       ping -c 1 -w 2 8.8.8.8 &>/dev/null 2>&1; then
        HAS_NETWORK=true
    fi

    if [[ "${HAS_NETWORK}" == "false" ]]; then
        RESOLVED_PROFILE="air-gapped"
        echo "[resolve-profile] Auto-detected: no network → air-gapped"
    elif [[ -f "${PROJECT_ROOT}/.security-sensitive" ]]; then
        RESOLVED_PROFILE="sensitive"
        echo "[resolve-profile] Auto-detected: .security-sensitive marker → sensitive"
    else
        RESOLVED_PROFILE="standard"
        echo "[resolve-profile] Auto-detected: default → standard"
    fi
fi

# ── Step 2: Validate ─────────────────────────────────────────────────────────
if ! validate_profile "${RESOLVED_PROFILE}"; then
    echo "[resolve-profile] ERROR: '${RESOLVED_PROFILE}' is not a valid profile." >&2
    exit 1
fi

echo "[resolve-profile] Validated profile: ${RESOLVED_PROFILE}"

# ── Step 3: Read profile fields ──────────────────────────────────────────────
ALLOW_INTERNET=$(read_profile_field "${RESOLVED_PROFILE}" "allow_internet")
ALLOW_SAAS=$(read_profile_field "${RESOLVED_PROFILE}" "allow_saas")
RISK_LEVELS=$(read_profile_field "${RESOLVED_PROFILE}" "acceptable_risk_levels")
INSTALL_STRATEGY=$(read_profile_field "${RESOLVED_PROFILE}" "skill_install_strategy")

# ── Step 4: Write locked profile ─────────────────────────────────────────────
python3 -c "
import datetime, json
data = {
    'profile': '${RESOLVED_PROFILE}',
    'resolved_by': '${RESOLUTION_METHOD}',
    'locked_at': datetime.datetime.utcnow().isoformat() + 'Z',
    'allow_internet': ${ALLOW_INTERNET} == 'true' if isinstance('${ALLOW_INTERNET}', str) else ${ALLOW_INTERNET},
    'allow_saas': ${ALLOW_SAAS} == 'true' if isinstance('${ALLOW_SAAS}', str) else ${ALLOW_SAAS},
    'acceptable_risk_levels': '${RISK_LEVELS}'.split(','),
    'skill_install_strategy': '${INSTALL_STRATEGY}',
}
" 2>/dev/null || true

# Write using a heredoc for reliability
cat > "${ACTIVE_PROFILE_YAML}" <<PROFILE_EOF
# Locked environment profile — written by resolve-profile.sh
# Do not edit manually. Re-run resolve-profile.sh to change.
profile: ${RESOLVED_PROFILE}
resolved_by: ${RESOLUTION_METHOD}
locked_at: $(python3 -c "import datetime; print(datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'))")
allow_internet: ${ALLOW_INTERNET}
allow_saas: ${ALLOW_SAAS}
acceptable_risk_levels: [${RISK_LEVELS}]
skill_install_strategy: ${INSTALL_STRATEGY}
PROFILE_EOF

echo "[resolve-profile] Locked profile written to ${ACTIVE_PROFILE_YAML}"

# ── Step 5: Export environment variables ─────────────────────────────────────
export ATOMIC_ENV_PROFILE="${RESOLVED_PROFILE}"
export ATOMIC_ALLOW_INTERNET="${ALLOW_INTERNET}"
export ATOMIC_ALLOW_SAAS="${ALLOW_SAAS}"
export ATOMIC_RISK_LEVELS="${RISK_LEVELS}"
export ATOMIC_INSTALL_STRATEGY="${INSTALL_STRATEGY}"

echo "[resolve-profile] Exported:"
echo "  ATOMIC_ENV_PROFILE=${ATOMIC_ENV_PROFILE}"
echo "  ATOMIC_ALLOW_INTERNET=${ATOMIC_ALLOW_INTERNET}"
echo "  ATOMIC_ALLOW_SAAS=${ATOMIC_ALLOW_SAAS}"
echo "  ATOMIC_RISK_LEVELS=${ATOMIC_RISK_LEVELS}"
echo "  ATOMIC_INSTALL_STRATEGY=${ATOMIC_INSTALL_STRATEGY}"

# ── Step 6: Generate profile constraints rule file ────────────────────────────
CONSTRAINTS_GENERATOR="${SCRIPT_DIR}/generate_profile_constraints.py"
if [[ -f "${CONSTRAINTS_GENERATOR}" ]]; then
    echo "[resolve-profile] Generating profile constraints rule file..."
    python3 "${CONSTRAINTS_GENERATOR}" --profile "${RESOLVED_PROFILE}" || {
        echo "[resolve-profile] WARN: Failed to generate profile constraints." >&2
    }
else
    echo "[resolve-profile] WARN: ${CONSTRAINTS_GENERATOR} not found, skipping rule generation." >&2
fi
