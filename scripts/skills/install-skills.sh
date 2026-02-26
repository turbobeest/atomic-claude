#!/usr/bin/env bash
# =============================================================================
# install-skills.sh — Install skills from the catalog based on active profile
#
# Reads the skill catalog from scripts/skills/skill_catalog.py, applies profile
# gates (internet, SaaS, risk), and installs skills into .claude/skills/.
#
# Usage:
#   ./scripts/skills/install-skills.sh                   # use active profile
#   ./scripts/skills/install-skills.sh --profile air-gapped
#   ./scripts/skills/install-skills.sh --approve-high-risk
#   ./scripts/skills/install-skills.sh --dry-run
#   ./scripts/skills/install-skills.sh --profile unrestricted --approve-high-risk
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve project root (works whether called from repo root or scripts/skills/)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CATALOG_PY="$PROJECT_ROOT/scripts/skills/skill_catalog.py"
SKILLS_DIR="$PROJECT_ROOT/.claude/skills"
MANIFEST="$SKILLS_DIR/_manifest.yaml"
VALIDATE_SCRIPT="$PROJECT_ROOT/scripts/skills/validate-skill.sh"
COMMUNITY_DIR="$PROJECT_ROOT/skills/community"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
PROFILE=""
APPROVE_HIGH_RISK=false
DRY_RUN=false
VERBOSE=false

# Counters
INSTALLED=0
SKIPPED_PROFILE=0
SKIPPED_RISK=0
SKIPPED_HIGH_RISK=0
SKIPPED_EXIST=0
FAILED=0
EXTERNAL_LOGGED=0

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Install skills from the catalog based on profile gates.

Options:
  --profile NAME        Use a specific profile (air-gapped, sensitive,
                        standard, unrestricted). If omitted, reads
                        from .claude/active-profile.yaml.
  --approve-high-risk   Allow installation of High-risk skills.
  --dry-run             Show what would be installed without making changes.
  --verbose             Print details for each skill.
  -h, --help            Show this help message.

Examples:
  $(basename "$0")                               # use active profile
  $(basename "$0") --profile air-gapped           # air-gapped install
  $(basename "$0") --approve-high-risk           # include high-risk skills
  $(basename "$0") --dry-run --verbose           # preview with details
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --approve-high-risk)
            APPROVE_HIGH_RISK=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() { echo "  $*"; }
log_ok() { echo "  [OK] $*"; }
log_skip() { echo "  [SKIP] $*"; }
log_fail() { echo "  [FAIL] $*"; }
log_ext() { echo "  [EXT] $*"; }
verbose() { $VERBOSE && echo "  ... $*" || true; }

# Use python3 explicitly
PYTHON="python3"

# Verify catalog module exists
if [[ ! -f "$CATALOG_PY" ]]; then
    echo "ERROR: Skill catalog not found at $CATALOG_PY" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Resolve profile
# ---------------------------------------------------------------------------
resolve_profile() {
    if [[ -n "$PROFILE" ]]; then
        echo "$PROFILE"
        return
    fi

    local active_profile_file="$PROJECT_ROOT/.claude/active-profile.yaml"

    if [[ -f "$active_profile_file" ]]; then
        # Parse YAML with python3 — look for "profile:" key
        local resolved
        resolved=$($PYTHON -c "
import sys, pathlib
try:
    # Try PyYAML first
    import yaml
    data = yaml.safe_load(pathlib.Path('$active_profile_file').read_text())
    print(data.get('profile', data.get('name', 'standard')))
except ImportError:
    # Fallback: simple line parsing
    for line in pathlib.Path('$active_profile_file').read_text().splitlines():
        line = line.strip()
        if line.startswith('profile:') or line.startswith('name:'):
            val = line.split(':', 1)[1].strip().strip('\"').strip(\"'\")
            print(val)
            sys.exit(0)
    print('standard')
" 2>/dev/null)

        if [[ -n "$resolved" ]]; then
            echo "$resolved"
            return
        fi
    fi

    # Default to standard
    echo "standard"
}

PROFILE=$(resolve_profile)
echo "================================================================="
echo " Atomic Claude Skill Installer"
echo "================================================================="
echo ""
echo "  Profile:           $PROFILE"
echo "  Approve High-Risk: $APPROVE_HIGH_RISK"
echo "  Dry Run:           $DRY_RUN"
echo "  Skills Dir:        $SKILLS_DIR"
echo ""

# ---------------------------------------------------------------------------
# Query catalog through Python — get allowed/blocked split
# ---------------------------------------------------------------------------
echo "Reading catalog..."

# Get the full profile split as JSON
CATALOG_JSON=$($PYTHON "$CATALOG_PY" --profile "$PROFILE" --compact)
if [[ $? -ne 0 ]]; then
    echo "ERROR: Failed to read catalog for profile '$PROFILE'" >&2
    exit 1
fi

# Extract allowed skill ids and count
ALLOWED_IDS=$($PYTHON -c "
import json, sys
data = json.loads(sys.stdin.read())
for s in data['allowed']:
    print(s['id'])
" <<< "$CATALOG_JSON")

BLOCKED_IDS=$($PYTHON -c "
import json, sys
data = json.loads(sys.stdin.read())
for s in data['blocked']:
    print(s['id'])
" <<< "$CATALOG_JSON")

ALLOWED_COUNT=$(echo "$ALLOWED_IDS" | grep -c . || true)
BLOCKED_COUNT=$(echo "$BLOCKED_IDS" | grep -c . || true)

echo "  Catalog: 64 skills total"
echo "  Profile '$PROFILE' allows: $ALLOWED_COUNT, blocks: $BLOCKED_COUNT"
echo ""

# Count blocked by reason
SKIPPED_PROFILE=$BLOCKED_COUNT

# ---------------------------------------------------------------------------
# Ensure output directories
# ---------------------------------------------------------------------------
if ! $DRY_RUN; then
    mkdir -p "$SKILLS_DIR"
fi

# ---------------------------------------------------------------------------
# Begin manifest (write to temp, move at end)
# ---------------------------------------------------------------------------
MANIFEST_TMP=$(mktemp)
trap 'rm -f "$MANIFEST_TMP"' EXIT

cat > "$MANIFEST_TMP" <<MEOF
# Auto-generated by install-skills.sh — DO NOT EDIT MANUALLY
generated_at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
profile_at_install: $PROFILE
approve_high_risk: $APPROVE_HIGH_RISK
skills:
MEOF

# ---------------------------------------------------------------------------
# Install each allowed skill
# ---------------------------------------------------------------------------
echo "-----------------------------------------------------------------"
echo " Installing skills"
echo "-----------------------------------------------------------------"
echo ""

# Get full details of allowed skills as JSON array
ALLOWED_DETAILS=$($PYTHON -c "
import json, sys
data = json.loads(sys.stdin.read())
# Output one JSON object per line for easy bash processing
for s in data['allowed']:
    print(json.dumps(s))
" <<< "$CATALOG_JSON")

while IFS= read -r skill_json; do
    [[ -z "$skill_json" ]] && continue

    # Parse skill fields via python
    eval "$($PYTHON -c "
import json, sys, shlex
s = json.loads('''$skill_json''')
print(f'SKILL_ID={shlex.quote(s[\"id\"])}')
print(f'SKILL_NAME={shlex.quote(s[\"name\"])}')
print(f'SKILL_DESC={shlex.quote(s[\"description\"])}')
print(f'SKILL_CATEGORY={shlex.quote(s[\"category\"])}')
print(f'SKILL_SOURCE={shlex.quote(s[\"source\"])}')
print(f'SKILL_SOURCE_URL={shlex.quote(str(s.get(\"source_url\") or \"\"))}')
print(f'SKILL_RISK={shlex.quote(str(s.get(\"risk_level\") or \"None\"))}')
print(f'SKILL_RISK_NOTES={shlex.quote(s.get(\"risk_notes\", \"\"))}')
print(f'SKILL_LICENSE={shlex.quote(s.get(\"license\", \"MIT\"))}')
print(f'SKILL_PHASES={shlex.quote(\",\".join(str(p) for p in s.get(\"sdlc_phases\", [])))}')
print(f'SKILL_INTERNET={shlex.quote(str(s.get(\"requires_internet\", False)))}')
print(f'SKILL_SAAS={shlex.quote(str(s.get(\"requires_saas\", False)))}')
print(f'SKILL_SAAS_DEPS={shlex.quote(\",\".join(s.get(\"saas_dependencies\", [])))}')
print(f'SKILL_SCAN={shlex.quote(str(s.get(\"security_scan_needed\", False)))}')
print(f'SKILL_WELL_KNOWN={shlex.quote(str(s.get(\"well_known\", False)))}')
print(f'SKILL_OFFICIAL={shlex.quote(str(s.get(\"official\", False)))}')
" 2>/dev/null)"

    # --- High-risk gate ---
    if [[ "$SKILL_RISK" == "High" ]] && ! $APPROVE_HIGH_RISK; then
        log_skip "$SKILL_ID — High risk (use --approve-high-risk to allow)"
        SKIPPED_HIGH_RISK=$((SKIPPED_HIGH_RISK + 1))
        continue
    fi

    verbose "$SKILL_ID: source=$SKILL_SOURCE category=$SKILL_CATEGORY risk=$SKILL_RISK"

    # --- Determine install action by source ---
    SKILL_HASH=""
    INSTALL_STATUS="installed"

    case "$SKILL_SOURCE" in
        tactical-builtin)
            # Generate SKILL.md from catalog description
            SKILL_DIR="$SKILLS_DIR/$SKILL_CATEGORY/$SKILL_ID"
            SKILL_FILE="$SKILL_DIR/SKILL.md"

            if $DRY_RUN; then
                log_ok "$SKILL_ID — would generate SKILL.md at $SKILL_CATEGORY/$SKILL_ID/"
                INSTALLED=$((INSTALLED + 1))
            else
                mkdir -p "$SKILL_DIR"

                # Build tools list based on category
                TOOLS="Read, Bash"
                case "$SKILL_CATEGORY" in
                    formatting|file-ops) TOOLS="Read, Write, Bash" ;;
                    git-ops) TOOLS="Bash" ;;
                    doc-gen) TOOLS="Read, Write, Bash" ;;
                    validation) TOOLS="Read, Bash" ;;
                    extraction) TOOLS="Read, Bash" ;;
                    phase-checks) TOOLS="Read, Bash" ;;
                    data) TOOLS="Read, Write, Bash" ;;
                    architecture) TOOLS="Read, Bash" ;;
                esac

                cat > "$SKILL_FILE" <<SKILLEOF
---
name: $SKILL_ID
description: $SKILL_DESC
model: haiku
tools:
$(for t in $(echo "$TOOLS" | tr ',' '\n'); do echo "  - $(echo "$t" | xargs)"; done)
context: fork
disable-model-invocation: false
---

# $SKILL_NAME

$SKILL_DESC

## Category
$SKILL_CATEGORY

## SDLC Phases
$(for p in $(echo "$SKILL_PHASES" | tr ',' '\n'); do echo "- Phase $p"; done)

## Risk Level
${SKILL_RISK}$(if [[ -n "$SKILL_RISK_NOTES" ]]; then echo " — $SKILL_RISK_NOTES"; fi)

## License
$SKILL_LICENSE
SKILLEOF

                # Compute SHA256
                if command -v shasum &>/dev/null; then
                    SKILL_HASH=$(shasum -a 256 "$SKILL_FILE" | cut -d' ' -f1)
                elif command -v sha256sum &>/dev/null; then
                    SKILL_HASH=$(sha256sum "$SKILL_FILE" | cut -d' ' -f1)
                else
                    SKILL_HASH=$($PYTHON -c "
import hashlib, pathlib
print(hashlib.sha256(pathlib.Path('$SKILL_FILE').read_bytes()).hexdigest())
")
                fi

                # Validate if validator exists (pass directory, not file)
                if [[ -x "$VALIDATE_SCRIPT" ]]; then
                    if ! "$VALIDATE_SCRIPT" "$SKILL_DIR" 2>/dev/null; then
                        log_fail "$SKILL_ID — validation failed"
                        FAILED=$((FAILED + 1))
                        INSTALL_STATUS="failed"
                        # Still write to manifest as failed
                    fi
                fi

                if [[ "$INSTALL_STATUS" == "installed" ]]; then
                    log_ok "$SKILL_ID — generated SKILL.md ($SKILL_CATEGORY/)"
                    INSTALLED=$((INSTALLED + 1))
                fi
            fi
            ;;

        community)
            # Check if skill already exists in skills/community/
            FOUND_IN_COMMUNITY=false
            COMMUNITY_SKILL_PATH=""

            # Search superpowers and trailofbits
            for repo_dir in "$COMMUNITY_DIR"/*/; do
                [[ ! -d "$repo_dir" ]] && continue
                repo_name=$(basename "$repo_dir")

                # superpowers: skills in skills/ or hooks/ subdirs
                if [[ "$repo_name" == "superpowers" ]]; then
                    for check_dir in "$repo_dir/skills" "$repo_dir/hooks"; do
                        if [[ -d "$check_dir" ]]; then
                            # Match by skill id (kebab-case) to directory names
                            for candidate in "$check_dir"/*/; do
                                cname=$(basename "$candidate")
                                # Normalize: writing-plans -> planning, test-driven-development -> tdd, etc.
                                if [[ "$cname" == "$SKILL_ID" ]] || \
                                   [[ "$cname" == *"$SKILL_ID"* ]] || \
                                   [[ "$SKILL_ID" == "tdd" && "$cname" == "test-driven-development" ]] || \
                                   [[ "$SKILL_ID" == "debugging" && "$cname" == "systematic-debugging" ]] || \
                                   [[ "$SKILL_ID" == "planning" && ("$cname" == "writing-plans" || "$cname" == "executing-plans") ]] || \
                                   [[ "$SKILL_ID" == "research" && "$cname" == "brainstorming" ]] || \
                                   [[ "$SKILL_ID" == "code-review-assistant" && "$cname" == "requesting-code-review" ]] || \
                                   [[ "$SKILL_ID" == "performance-optimization" && "$cname" == *"performance"* ]]; then
                                    FOUND_IN_COMMUNITY=true
                                    COMMUNITY_SKILL_PATH="$candidate"
                                    break 2
                                fi
                            done
                        fi
                    done
                fi

                # trailofbits: skills in plugins/ subdir
                if [[ "$repo_name" == "trailofbits" ]]; then
                    for candidate in "$repo_dir/plugins"/*/; do
                        cname=$(basename "$candidate")
                        if [[ "$cname" == "$SKILL_ID" ]] || \
                           [[ "$cname" == *"$SKILL_ID"* ]] || \
                           [[ "$SKILL_ID" == "security-audit" && "$cname" == "audit-context-building" ]] || \
                           [[ "$SKILL_ID" == "dependency-scan" && "$cname" == *"depend"* ]] || \
                           [[ "$SKILL_ID" == "secrets-detection" && "$cname" == *"secret"* ]] || \
                           [[ "$SKILL_ID" == "static-analysis" && "$cname" == *"semgrep"* ]] || \
                           [[ "$SKILL_ID" == "supply-chain-audit" && "$cname" == *"supply"* ]] || \
                           [[ "$SKILL_ID" == "fuzzing-harness" && "$cname" == *"fuzz"* ]]; then
                            FOUND_IN_COMMUNITY=true
                            COMMUNITY_SKILL_PATH="$candidate"
                            break 2
                        fi
                    done
                fi
            done

            if $FOUND_IN_COMMUNITY; then
                if $DRY_RUN; then
                    log_ok "$SKILL_ID — already in community/ ($(basename "$(dirname "$COMMUNITY_SKILL_PATH")")/$(basename "$COMMUNITY_SKILL_PATH"))"
                else
                    # Compute hash of the community skill (use SKILL.md if present, else directory)
                    SKILL_FILE_CHECK="$COMMUNITY_SKILL_PATH/SKILL.md"
                    if [[ -f "$SKILL_FILE_CHECK" ]]; then
                        if command -v shasum &>/dev/null; then
                            SKILL_HASH=$(shasum -a 256 "$SKILL_FILE_CHECK" | cut -d' ' -f1)
                        elif command -v sha256sum &>/dev/null; then
                            SKILL_HASH=$(sha256sum "$SKILL_FILE_CHECK" | cut -d' ' -f1)
                        else
                            SKILL_HASH=$($PYTHON -c "
import hashlib, pathlib
print(hashlib.sha256(pathlib.Path('$SKILL_FILE_CHECK').read_bytes()).hexdigest())
")
                        fi
                    else
                        SKILL_HASH="no-skill-md"
                    fi

                    log_ok "$SKILL_ID — found in community/"
                fi
                INSTALLED=$((INSTALLED + 1))
                INSTALL_STATUS="community-existing"
            else
                if $DRY_RUN; then
                    log_skip "$SKILL_ID — community skill not found locally"
                else
                    log_skip "$SKILL_ID — community skill not found in $COMMUNITY_DIR"
                fi
                SKIPPED_EXIST=$((SKIPPED_EXIST + 1))
                INSTALL_STATUS="community-missing"
            fi
            ;;

        playbooks|awesome-claude-code|anthropic-official)
            # External skills — log that they would need cloning
            if $DRY_RUN; then
                log_ext "$SKILL_ID — external, would clone from $SKILL_SOURCE_URL"
            else
                log_ext "$SKILL_ID — external ($SKILL_SOURCE), needs: git clone $SKILL_SOURCE_URL"

                # Generate a placeholder SKILL.md so the manifest has something to track
                SKILL_DIR="$SKILLS_DIR/$SKILL_CATEGORY/$SKILL_ID"
                mkdir -p "$SKILL_DIR"

                SKILL_FILE="$SKILL_DIR/SKILL.md"
                cat > "$SKILL_FILE" <<SKILLEOF
---
name: $SKILL_ID
description: $SKILL_DESC
model: sonnet
tools:
  - Read
  - Write
  - Bash
context: fork
disable-model-invocation: false
---

# $SKILL_NAME

> **External skill** — source: $SKILL_SOURCE
> URL: $SKILL_SOURCE_URL

$SKILL_DESC

## Category
$SKILL_CATEGORY

## SDLC Phases
$(for p in $(echo "$SKILL_PHASES" | tr ',' '\n'); do echo "- Phase $p"; done)

## Risk Level
${SKILL_RISK}$(if [[ -n "$SKILL_RISK_NOTES" ]]; then echo " — $SKILL_RISK_NOTES"; fi)

## License
$SKILL_LICENSE

## Installation
This skill was generated from the catalog as a placeholder.
To get the full implementation, clone from the source:

\`\`\`bash
# Replace with actual clone command when available
git clone $SKILL_SOURCE_URL
\`\`\`
SKILLEOF

                # Compute hash
                if command -v shasum &>/dev/null; then
                    SKILL_HASH=$(shasum -a 256 "$SKILL_FILE" | cut -d' ' -f1)
                elif command -v sha256sum &>/dev/null; then
                    SKILL_HASH=$(sha256sum "$SKILL_FILE" | cut -d' ' -f1)
                else
                    SKILL_HASH=$($PYTHON -c "
import hashlib, pathlib
print(hashlib.sha256(pathlib.Path('$SKILL_FILE').read_bytes()).hexdigest())
")
                fi

                # Validate if validator exists (pass directory, not file)
                if [[ -x "$VALIDATE_SCRIPT" ]]; then
                    "$VALIDATE_SCRIPT" "$SKILL_DIR" 2>/dev/null || true
                fi
            fi
            EXTERNAL_LOGGED=$((EXTERNAL_LOGGED + 1))
            INSTALLED=$((INSTALLED + 1))
            INSTALL_STATUS="external-placeholder"
            ;;

        *)
            log_fail "$SKILL_ID — unknown source: $SKILL_SOURCE"
            FAILED=$((FAILED + 1))
            INSTALL_STATUS="failed"
            ;;
    esac

    # --- Write manifest entry ---
    if ! $DRY_RUN && [[ -n "$SKILL_ID" ]]; then
        cat >> "$MANIFEST_TMP" <<MENTRY
  $SKILL_ID:
    name: "$SKILL_NAME"
    category: $SKILL_CATEGORY
    source: $SKILL_SOURCE
    risk_level: $SKILL_RISK
    status: $INSTALL_STATUS
    sha256: "${SKILL_HASH:-none}"
    phases: [$SKILL_PHASES]
    installed_at: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
MENTRY
    fi

done <<< "$ALLOWED_DETAILS"

# ---------------------------------------------------------------------------
# Also log blocked skills in manifest
# ---------------------------------------------------------------------------
if ! $DRY_RUN; then
    cat >> "$MANIFEST_TMP" <<BEOF
blocked:
BEOF

    BLOCKED_DETAILS=$($PYTHON -c "
import json, sys
data = json.loads(sys.stdin.read())
for s in data['blocked']:
    print(json.dumps(s))
" <<< "$CATALOG_JSON")

    while IFS= read -r skill_json; do
        [[ -z "$skill_json" ]] && continue
        eval "$($PYTHON -c "
import json, shlex
s = json.loads('''$skill_json''')
print(f'BLK_ID={shlex.quote(s[\"id\"])}')
print(f'BLK_RISK={shlex.quote(str(s.get(\"risk_level\") or \"None\"))}')
print(f'BLK_INTERNET={shlex.quote(str(s.get(\"requires_internet\", False)))}')
print(f'BLK_SAAS={shlex.quote(str(s.get(\"requires_saas\", False)))}')
" 2>/dev/null)"

        # Determine block reason
        BLOCK_REASON="profile"
        if [[ "$BLK_INTERNET" == "True" ]]; then
            BLOCK_REASON="requires_internet"
        elif [[ "$BLK_SAAS" == "True" ]]; then
            BLOCK_REASON="requires_saas"
        elif [[ "$BLK_RISK" == "High" || "$BLK_RISK" == "Medium" ]]; then
            BLOCK_REASON="risk_level_$BLK_RISK"
        fi

        cat >> "$MANIFEST_TMP" <<BENTRY
  $BLK_ID:
    reason: $BLOCK_REASON
    risk_level: $BLK_RISK
BENTRY

    done <<< "$BLOCKED_DETAILS"
fi

# ---------------------------------------------------------------------------
# Finalize manifest
# ---------------------------------------------------------------------------
if ! $DRY_RUN; then
    mv "$MANIFEST_TMP" "$MANIFEST"
    log "Manifest written to $MANIFEST"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "================================================================="
echo " Installation Summary"
echo "================================================================="
echo ""
echo "  Profile:                $PROFILE"
echo "  Total in catalog:       64"
echo "  Installed:              $INSTALLED"
echo "    (external/placeholder: $EXTERNAL_LOGGED)"
echo "  Skipped (profile gate): $SKIPPED_PROFILE"
echo "  Skipped (high-risk):    $SKIPPED_HIGH_RISK"
echo "  Skipped (not found):    $SKIPPED_EXIST"
echo "  Failed:                 $FAILED"
echo ""

if $DRY_RUN; then
    echo "  ** DRY RUN — no files were written **"
    echo ""
fi

# Exit with failure if any skills failed validation
if [[ $FAILED -gt 0 ]]; then
    exit 1
fi

exit 0
