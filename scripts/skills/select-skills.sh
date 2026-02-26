#!/usr/bin/env bash
# select-skills.sh — Runtime skill selector for Atomic Claude.
#
# Loads the active environment profile, queries FalkorDB for matching skills,
# and exports the selected skill set for the current task.
#
# Usage:
#   source scripts/skills/select-skills.sh --task-prompt "Implement auth" --project-id PRD-403
#   # Exports: ATOMIC_SKILL_SET, ATOMIC_WORKFLOW, ATOMIC_SKILL_METHOD
#   # Generates: .claude/session-skills.md
set -euo pipefail

# ── Locate project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ACTIVE_PROFILE_YAML="${PROJECT_ROOT}/.claude/active-profile.yaml"
FALKORDB_BRIDGE="${PROJECT_ROOT}/scripts/skills/falkordb_bridge.py"
SESSION_SKILLS_MD="${PROJECT_ROOT}/.claude/session-skills.md"

# ── Parse arguments ──────────────────────────────────────────────────────────
TASK_PROMPT=""
PROJECT_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task-prompt)
            TASK_PROMPT="$2"; shift 2 ;;
        --project-id)
            PROJECT_ID="$2"; shift 2 ;;
        *)
            echo "[select-skills] ERROR: Unknown argument: $1" >&2
            echo "Usage: $0 --task-prompt PROMPT --project-id ID" >&2
            exit 1 ;;
    esac
done

if [[ -z "${TASK_PROMPT}" ]]; then
    echo "[select-skills] ERROR: --task-prompt is required." >&2
    exit 1
fi

if [[ -z "${PROJECT_ID}" ]]; then
    echo "[select-skills] ERROR: --project-id is required." >&2
    exit 1
fi

# ── Load active profile ─────────────────────────────────────────────────────
if [[ ! -f "${ACTIVE_PROFILE_YAML}" ]]; then
    echo "[select-skills] WARN: No active profile found. Running resolve-profile.sh first." >&2
    if [[ -x "${SCRIPT_DIR}/resolve-profile.sh" ]]; then
        source "${SCRIPT_DIR}/resolve-profile.sh"
    else
        echo "[select-skills] ERROR: Cannot resolve profile. Run resolve-profile.sh first." >&2
        exit 1
    fi
fi

# Read profile fields using python3 (portable, no yq/jq dependency)
PROFILE_DATA=$(python3 -c "
import sys, json, datetime
try:
    import yaml
    with open('${ACTIVE_PROFILE_YAML}') as f:
        data = yaml.safe_load(f)
    # Convert non-JSON-serializable types
    for k, v in list(data.items()):
        if isinstance(v, (datetime.datetime, datetime.date)):
            data[k] = v.isoformat()
        elif v is None:
            data[k] = ''
    # Ensure risk levels are strings (YAML parses bare None as Python None)
    if 'acceptable_risk_levels' in data:
        data['acceptable_risk_levels'] = [str(x) if x is not None else 'None' for x in data['acceptable_risk_levels']]
except ImportError:
    import re
    with open('${ACTIVE_PROFILE_YAML}') as f:
        content = f.read()
    data = {}
    for key in ['profile', 'allow_internet', 'allow_saas', 'skill_install_strategy']:
        m = re.search(r'^' + key + r':\s+(.+)$', content, re.MULTILINE)
        if m:
            val = m.group(1).strip()
            if val in ('true', 'True'):
                data[key] = True
            elif val in ('false', 'False'):
                data[key] = False
            else:
                data[key] = val.strip('\"').strip(\"'\")
    # Parse risk levels list
    m = re.search(r'^acceptable_risk_levels:\s+\[(.+)\]', content, re.MULTILINE)
    if m:
        data['acceptable_risk_levels'] = [s.strip().strip('\"').strip(\"'\") for s in m.group(1).split(',')]
    else:
        data['acceptable_risk_levels'] = []

print(json.dumps(data))
" 2>/dev/null) || {
    echo "[select-skills] ERROR: Failed to parse active profile." >&2
    exit 1
}

PROFILE_NAME=$(echo "${PROFILE_DATA}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('profile','unknown'))")
echo "[select-skills] Active profile: ${PROFILE_NAME}"
echo "[select-skills] Task: ${TASK_PROMPT}"
echo "[select-skills] Project: ${PROJECT_ID}"

# ── Call FalkorDB bridge for skill selection ──────────────────────────────────
if [[ ! -f "${FALKORDB_BRIDGE}" ]]; then
    echo "[select-skills] WARN: FalkorDB bridge not found. Using fallback skill selection." >&2

    # Fallback: export empty/default values
    export ATOMIC_SKILL_SET=""
    export ATOMIC_WORKFLOW="default"
    export ATOMIC_SKILL_METHOD="fallback"

    # Generate minimal session-skills.md
    cat > "${SESSION_SKILLS_MD}" <<FALLBACK_EOF
# Session Skills (Fallback)

**Profile:** ${PROFILE_NAME}
**Task:** ${TASK_PROMPT}
**Project:** ${PROJECT_ID}
**Selection Method:** fallback (FalkorDB bridge unavailable)

No skills selected. Using default agent capabilities.
FALLBACK_EOF

    echo "[select-skills] Fallback session-skills.md written to ${SESSION_SKILLS_MD}"
    exit 0
fi

# Call the bridge and capture JSON output
SELECTION_JSON=$(python3 "${FALKORDB_BRIDGE}" \
    --action select \
    --task-prompt "${TASK_PROMPT}" \
    --project-id "${PROJECT_ID}" \
    --profile-json "${PROFILE_DATA}" \
    2>/dev/null) || {
    echo "[select-skills] WARN: FalkorDB skill selection failed. Using fallback." >&2
    export ATOMIC_SKILL_SET=""
    export ATOMIC_WORKFLOW="default"
    export ATOMIC_SKILL_METHOD="fallback-error"

    cat > "${SESSION_SKILLS_MD}" <<ERR_EOF
# Session Skills (Fallback — Error)

**Profile:** ${PROFILE_NAME}
**Task:** ${TASK_PROMPT}
**Project:** ${PROJECT_ID}
**Selection Method:** fallback (bridge error)

No skills selected. Using default agent capabilities.
ERR_EOF
    exit 0
}

# ── Parse selection result with python3 ──────────────────────────────────────
PARSED=$(python3 -c "
import sys, json

data = json.loads('''${SELECTION_JSON}''')

skills = data.get('skills', [])
workflow = data.get('workflow', 'default')
method = data.get('method', 'graph')

# Skill set as comma-separated IDs
skill_ids = ','.join(s.get('id', s) if isinstance(s, dict) else str(s) for s in skills)

print(f'SKILL_SET={skill_ids}')
print(f'WORKFLOW={workflow}')
print(f'METHOD={method}')

# Generate markdown for session-skills.md
print('---MARKDOWN---')
print('# Session Skills')
print()
print(f'**Profile:** {data.get(\"profile\", \"unknown\")}')
print(f'**Task:** {data.get(\"task\", \"\")}')
print(f'**Project:** {data.get(\"project\", \"\")}')
print(f'**Selection Method:** {method}')
print(f'**Workflow:** {workflow}')
print()
if skills:
    print(f'## Selected Skills ({len(skills)})')
    print()
    for s in skills:
        if isinstance(s, dict):
            name = s.get('name', s.get('id', 'unknown'))
            risk = s.get('risk_level', 'unknown')
            desc = s.get('description', '')
            print(f'- **{name}** (risk: {risk})')
            if desc:
                print(f'  {desc}')
        else:
            print(f'- {s}')
else:
    print('No skills selected for this task.')
" 2>/dev/null) || {
    echo "[select-skills] ERROR: Failed to parse selection result." >&2
    export ATOMIC_SKILL_SET=""
    export ATOMIC_WORKFLOW="default"
    export ATOMIC_SKILL_METHOD="parse-error"
    exit 0
}

# ── Extract and export values ────────────────────────────────────────────────
SKILL_SET=$(echo "${PARSED}" | grep '^SKILL_SET=' | cut -d= -f2-)
WORKFLOW=$(echo "${PARSED}" | grep '^WORKFLOW=' | cut -d= -f2-)
METHOD=$(echo "${PARSED}" | grep '^METHOD=' | cut -d= -f2-)

export ATOMIC_SKILL_SET="${SKILL_SET}"
export ATOMIC_WORKFLOW="${WORKFLOW}"
export ATOMIC_SKILL_METHOD="${METHOD}"

# ── Write session-skills.md ──────────────────────────────────────────────────
echo "${PARSED}" | sed -n '/^---MARKDOWN---$/,$ p' | tail -n +2 > "${SESSION_SKILLS_MD}"

echo "[select-skills] Selected skills: ${SKILL_SET:-none}"
echo "[select-skills] Workflow: ${WORKFLOW}"
echo "[select-skills] Method: ${METHOD}"
echo "[select-skills] Session skills written to ${SESSION_SKILLS_MD}"

# ── Export summary ───────────────────────────────────────────────────────────
echo "[select-skills] Exported:"
echo "  ATOMIC_SKILL_SET=${ATOMIC_SKILL_SET}"
echo "  ATOMIC_WORKFLOW=${ATOMIC_WORKFLOW}"
echo "  ATOMIC_SKILL_METHOD=${ATOMIC_SKILL_METHOD}"
