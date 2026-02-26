#!/usr/bin/env bash
# log-outcome.sh — Post-task outcome logger for the Atomic Claude skill system.
#
# Records task execution outcomes (success score, skills used, token consumption,
# duration) into FalkorDB via the bridge script for feedback-driven skill selection.
#
# Usage:
#   scripts/skills/log-outcome.sh \
#     --task-id <task_id> \
#     --score <0.0-1.0> \
#     --skills <skill1,skill2,...> \
#     --tokens <count> \
#     --duration <ms>
set -euo pipefail

# ── Locate project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ACTIVE_PROFILE_YAML="${PROJECT_ROOT}/.claude/active-profile.yaml"
FALKORDB_BRIDGE="${PROJECT_ROOT}/scripts/skills/falkordb_bridge.py"

# ── Parse arguments ──────────────────────────────────────────────────────────
TASK_ID=""
SUCCESS_SCORE=""
SKILLS_USED=""
TOKENS_CONSUMED=""
DURATION_MS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --task-id)
            TASK_ID="$2"; shift 2 ;;
        --score)
            SUCCESS_SCORE="$2"; shift 2 ;;
        --skills)
            SKILLS_USED="$2"; shift 2 ;;
        --tokens)
            TOKENS_CONSUMED="$2"; shift 2 ;;
        --duration)
            DURATION_MS="$2"; shift 2 ;;
        *)
            echo "[log-outcome] ERROR: Unknown argument: $1" >&2
            echo "Usage: $0 --task-id ID --score 0.0-1.0 --skills CSV --tokens N --duration MS" >&2
            exit 1 ;;
    esac
done

# ── Validate required arguments ──────────────────────────────────────────────
MISSING=""
[[ -z "${TASK_ID}" ]] && MISSING="${MISSING} --task-id"
[[ -z "${SUCCESS_SCORE}" ]] && MISSING="${MISSING} --score"
[[ -z "${SKILLS_USED}" ]] && MISSING="${MISSING} --skills"
[[ -z "${TOKENS_CONSUMED}" ]] && MISSING="${MISSING} --tokens"
[[ -z "${DURATION_MS}" ]] && MISSING="${MISSING} --duration"

if [[ -n "${MISSING}" ]]; then
    echo "[log-outcome] ERROR: Missing required arguments:${MISSING}" >&2
    exit 1
fi

# ── Validate score range ─────────────────────────────────────────────────────
python3 -c "
score = float('${SUCCESS_SCORE}')
if not (0.0 <= score <= 1.0):
    raise ValueError(f'Score must be 0.0-1.0, got {score}')
" || {
    echo "[log-outcome] ERROR: Invalid score '${SUCCESS_SCORE}'. Must be 0.0-1.0." >&2
    exit 1
}

# ── Read active profile ──────────────────────────────────────────────────────
PROFILE="unknown"
if [[ -f "${ACTIVE_PROFILE_YAML}" ]]; then
    PROFILE=$(python3 -c "
import sys
try:
    import yaml
    with open('${ACTIVE_PROFILE_YAML}') as f:
        data = yaml.safe_load(f)
    print(data.get('profile', 'unknown'))
except ImportError:
    import re
    with open('${ACTIVE_PROFILE_YAML}') as f:
        content = f.read()
    m = re.search(r'^profile:\s+(\S+)', content, re.MULTILINE)
    print(m.group(1).strip('\"').strip(\"'\") if m else 'unknown')
except Exception:
    print('unknown')
" 2>/dev/null) || PROFILE="unknown"
fi

echo "[log-outcome] Recording outcome for task ${TASK_ID} (profile: ${PROFILE})"
echo "  score=${SUCCESS_SCORE} skills=${SKILLS_USED} tokens=${TOKENS_CONSUMED} duration=${DURATION_MS}ms"

# ── Call FalkorDB bridge ─────────────────────────────────────────────────────
if [[ ! -f "${FALKORDB_BRIDGE}" ]]; then
    echo "[log-outcome] WARN: FalkorDB bridge not found at ${FALKORDB_BRIDGE}" >&2
    echo "[log-outcome] WARN: Outcome recorded to stdout only. Graph logging skipped." >&2
    exit 0
fi

python3 "${FALKORDB_BRIDGE}" \
    --action log-outcome \
    --task-id "${TASK_ID}" \
    --score "${SUCCESS_SCORE}" \
    --skills "${SKILLS_USED}" \
    --tokens "${TOKENS_CONSUMED}" \
    --duration "${DURATION_MS}" \
    --profile "${PROFILE}"

BRIDGE_EXIT=$?
if [[ ${BRIDGE_EXIT} -ne 0 ]]; then
    echo "[log-outcome] WARN: FalkorDB bridge returned exit code ${BRIDGE_EXIT}." >&2
    echo "[log-outcome] WARN: Outcome may not have been persisted to graph." >&2
    # Non-fatal: logging failure should not break the pipeline
    exit 0
fi

echo "[log-outcome] Outcome logged successfully."
