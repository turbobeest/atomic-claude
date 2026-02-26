#!/usr/bin/env bash
# validate-skill.sh — Validate a single skill directory for security and correctness.
#
# Checks:
#   1. SKILL.md must exist
#   2. No executable binaries (except .sh, .py, .rb)
#   3. No hardcoded credentials/API keys
#   4. Warn on network call patterns in SKILL.md
#   5. Size checks (SKILL.md > 500KB = warn, dir > 10MB = warn)
#
# Exit 0 = pass, Exit 1 = fail
#
# Usage:
#   scripts/skills/validate-skill.sh /path/to/skill-directory
set -euo pipefail

SKILL_DIR="${1:-}"

if [[ -z "${SKILL_DIR}" ]]; then
    echo "[validate-skill] ERROR: Usage: $0 <skill-directory>" >&2
    exit 1
fi

if [[ ! -d "${SKILL_DIR}" ]]; then
    echo "[validate-skill] ERROR: Not a directory: ${SKILL_DIR}" >&2
    exit 1
fi

SKILL_NAME="$(basename "${SKILL_DIR}")"
FAIL=0
WARN_COUNT=0

echo "[validate-skill] Validating: ${SKILL_NAME} (${SKILL_DIR})"

# ── Helper: portable file size in bytes ───────────────────────────────────────
file_size_bytes() {
    local filepath="$1"
    # Try macOS stat first, then Linux stat
    if stat -f%z "${filepath}" 2>/dev/null; then
        return 0
    elif stat -c%s "${filepath}" 2>/dev/null; then
        return 0
    else
        # Last resort: wc -c
        wc -c < "${filepath}" | tr -d ' '
        return 0
    fi
}

# ── Helper: portable directory size in bytes ──────────────────────────────────
dir_size_bytes() {
    local dirpath="$1"
    # du -sb is Linux; du -s gives KB blocks on macOS
    if du -sb "${dirpath}" 2>/dev/null | awk '{print $1}'; then
        return 0
    else
        # macOS: du -sk gives KB, multiply by 1024
        local kb
        kb=$(du -sk "${dirpath}" 2>/dev/null | awk '{print $1}')
        echo $(( kb * 1024 ))
        return 0
    fi
}

# ── Check 1: SKILL.md must exist ─────────────────────────────────────────────
echo -n "  [1/5] SKILL.md exists... "
if [[ -f "${SKILL_DIR}/SKILL.md" ]]; then
    echo "PASS"
else
    echo "FAIL — SKILL.md not found"
    FAIL=1
fi

# ── Check 2: No executable binaries ──────────────────────────────────────────
echo -n "  [2/5] No unauthorized executables... "
BINARY_VIOLATIONS=""
while IFS= read -r -d '' file; do
    # Skip allowed extensions (scripts, text, config, and common repo files)
    case "${file}" in
        *.sh|*.py|*.rb|*.md|*.txt|*.yaml|*.yml|*.json|*.toml|*.cfg|*.ini|*.xml)
            continue ;;
        *.html|*.css|*.js|*.ts|*.jsx|*.tsx|*.sql|*.csv|*.rst|*.lock)
            continue ;;
        *.bash|*.bats|*.zsh|*.fish|*.ps1|*.bat|*.cmd)
            continue ;;
        *.gitignore|*.gitkeep|*.gitattributes|*.editorconfig|*.dockerignore)
            continue ;;
        *LICENSE*|*LICENCE*|*NOTICE*|*CHANGELOG*|*CHANGES*)
            continue ;;
    esac
    # Also skip dotfiles and common non-binary repo files by basename
    case "$(basename "${file}")" in
        .gitignore|.gitkeep|.gitattributes|.editorconfig|.dockerignore)
            continue ;;
        LICENSE|LICENCE|NOTICE|CHANGELOG|CHANGES|Makefile|Rakefile|Gemfile)
            continue ;;
    esac
    # Check if file is executable
    if [[ -x "${file}" && -f "${file}" ]]; then
        BINARY_VIOLATIONS="${BINARY_VIOLATIONS}    ${file}\n"
    fi
    # Check for ELF/Mach-O binary headers
    if [[ -f "${file}" ]] && file "${file}" 2>/dev/null | grep -qiE 'executable|shared object|mach-o|elf'; then
        BINARY_VIOLATIONS="${BINARY_VIOLATIONS}    ${file} (binary detected)\n"
    fi
done < <(find "${SKILL_DIR}" -type f -print0 2>/dev/null)

if [[ -z "${BINARY_VIOLATIONS}" ]]; then
    echo "PASS"
else
    echo "FAIL — unauthorized executables found:"
    echo -e "${BINARY_VIOLATIONS}" | sort -u | head -20
    FAIL=1
fi

# ── Check 3: No hardcoded credentials/API keys ───────────────────────────────
echo -n "  [3/5] No hardcoded credentials... "
# Patterns that indicate secrets
CREDENTIAL_PATTERNS=(
    'sk-[a-zA-Z0-9]{20,}'                          # OpenAI/Anthropic API keys
    'AKIA[0-9A-Z]{16}'                              # AWS Access Key IDs
    'ghp_[a-zA-Z0-9]{36}'                           # GitHub personal access tokens
    'gho_[a-zA-Z0-9]{36}'                           # GitHub OAuth tokens
    'glpat-[a-zA-Z0-9\-]{20,}'                      # GitLab personal access tokens
    '-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----'   # Private keys
    'xox[bpoas]-[a-zA-Z0-9\-]+'                     # Slack tokens
    'eyJ[a-zA-Z0-9_\-]*\.eyJ[a-zA-Z0-9_\-]*\.'     # JWT tokens (long-form)
)

CREDENTIAL_FOUND=""
for pattern in "${CREDENTIAL_PATTERNS[@]}"; do
    while IFS= read -r -d '' file; do
        if [[ -f "${file}" ]] && grep -qE "${pattern}" "${file}" 2>/dev/null; then
            MATCH=$(grep -nE "${pattern}" "${file}" 2>/dev/null | head -3)
            CREDENTIAL_FOUND="${CREDENTIAL_FOUND}    ${file}:\n${MATCH}\n"
        fi
    done < <(find "${SKILL_DIR}" -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" -o -name "*.py" -o -name "*.sh" -o -name "*.rb" -o -name "*.toml" -o -name "*.txt" -o -name "*.cfg" -o -name "*.ini" \) -print0 2>/dev/null)
done

if [[ -z "${CREDENTIAL_FOUND}" ]]; then
    echo "PASS"
else
    echo "FAIL — potential credentials detected:"
    echo -e "${CREDENTIAL_FOUND}" | head -30
    FAIL=1
fi

# ── Check 4: Warn on network call patterns ───────────────────────────────────
echo -n "  [4/5] Network call patterns... "
if [[ -f "${SKILL_DIR}/SKILL.md" ]]; then
    NETWORK_PATTERNS='(curl|wget|http[s]?://|fetch\(|requests\.get|requests\.post|urllib|httpx|aiohttp|socket\.connect)'
    NETWORK_MATCHES=$(grep -nE "${NETWORK_PATTERNS}" "${SKILL_DIR}/SKILL.md" 2>/dev/null || true)
    if [[ -n "${NETWORK_MATCHES}" ]]; then
        echo "WARN — network call patterns found in SKILL.md:"
        echo "${NETWORK_MATCHES}" | head -10 | sed 's/^/    /'
        WARN_COUNT=$((WARN_COUNT + 1))
    else
        echo "PASS"
    fi
else
    echo "SKIP (no SKILL.md)"
fi

# ── Check 5: Size checks ─────────────────────────────────────────────────────
echo -n "  [5/5] Size checks... "
SIZE_OK=true

if [[ -f "${SKILL_DIR}/SKILL.md" ]]; then
    SKILL_MD_SIZE=$(file_size_bytes "${SKILL_DIR}/SKILL.md")
    # 500KB = 512000 bytes
    if [[ "${SKILL_MD_SIZE}" -gt 512000 ]]; then
        echo ""
        echo "    WARN — SKILL.md is $(( SKILL_MD_SIZE / 1024 ))KB (> 500KB)"
        WARN_COUNT=$((WARN_COUNT + 1))
        SIZE_OK=false
    fi
fi

DIR_SIZE=$(dir_size_bytes "${SKILL_DIR}")
# 10MB = 10485760 bytes
if [[ "${DIR_SIZE}" -gt 10485760 ]]; then
    if [[ "${SIZE_OK}" == "true" ]]; then
        echo ""
    fi
    echo "    WARN — directory is $(( DIR_SIZE / 1048576 ))MB (> 10MB)"
    WARN_COUNT=$((WARN_COUNT + 1))
    SIZE_OK=false
fi

if [[ "${SIZE_OK}" == "true" ]]; then
    echo "PASS"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
if [[ "${FAIL}" -ne 0 ]]; then
    echo "[validate-skill] FAILED: ${SKILL_NAME} — fix issues above before installing."
    exit 1
else
    if [[ "${WARN_COUNT}" -gt 0 ]]; then
        echo "[validate-skill] PASSED with ${WARN_COUNT} warning(s): ${SKILL_NAME}"
    else
        echo "[validate-skill] PASSED: ${SKILL_NAME}"
    fi
    exit 0
fi
