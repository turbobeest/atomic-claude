#!/usr/bin/env bash
#
# Validate Phase A Skills Installation
# Tests that all 65 skills were installed correctly
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Phase A Skills Installation Validation"
echo "========================================="
echo ""

# Check skills directory exists
if [[ ! -d ~/.claude/skills ]]; then
    echo -e "${RED}✗ Skills directory not found: ~/.claude/skills${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Skills directory exists${NC}"

# Check repositories exist
repos=("superpowers" "trailofbits" "ralph")
for repo in "${repos[@]}"; do
    if [[ ! -d ~/.claude/skills/$repo ]]; then
        echo -e "${RED}✗ Repository not found: $repo${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Repository exists: $repo${NC}"
done

echo ""
echo "Counting skills by repository:"
echo "----------------------------------------"

# Count superpowers skills
superpowers_count=$(find ~/.claude/skills/superpowers -name "SKILL.md" | wc -l | tr -d ' ')
echo -e "Superpowers: ${GREEN}${superpowers_count} skills${NC}"
if [[ "$superpowers_count" -ne 14 ]]; then
    echo -e "  ${YELLOW}⚠  Expected 14 skills${NC}"
fi

# Count trailofbits skills
trailofbits_count=$(find ~/.claude/skills/trailofbits -name "SKILL.md" | wc -l | tr -d ' ')
echo -e "Trail of Bits: ${GREEN}${trailofbits_count} skills${NC}"
if [[ "$trailofbits_count" -ne 51 ]]; then
    echo -e "  ${YELLOW}⚠  Expected 51 skills${NC}"
fi

# Check Ralph framework
ralph_scripts=$(find ~/.claude/skills/ralph -name "*.sh" -maxdepth 1 | wc -l | tr -d ' ')
echo -e "Ralph: ${GREEN}${ralph_scripts} bash scripts${NC} (framework, not SKILL.md)"

# Total count
total_skills=$((superpowers_count + trailofbits_count))
echo ""
echo "----------------------------------------"
echo -e "Total SKILL.md files: ${GREEN}${total_skills}${NC}"
if [[ "$total_skills" -ne 65 ]]; then
    echo -e "  ${YELLOW}⚠  Expected 65 skills total${NC}"
fi

echo ""
echo "Checking critical skills:"
echo "----------------------------------------"

# Check critical superpowers skills
critical_skills=(
    "superpowers/skills/brainstorming/SKILL.md"
    "superpowers/skills/writing-plans/SKILL.md"
    "superpowers/skills/executing-plans/SKILL.md"
    "superpowers/skills/test-driven-development/SKILL.md"
    "superpowers/skills/systematic-debugging/SKILL.md"
    "superpowers/skills/subagent-driven-development/SKILL.md"
)

for skill in "${critical_skills[@]}"; do
    skill_name=$(basename "$(dirname "$skill")")
    if [[ -f ~/.claude/skills/$skill ]]; then
        echo -e "${GREEN}✓ $skill_name${NC}"
    else
        echo -e "${RED}✗ $skill_name (MISSING)${NC}"
    fi
done

# Check critical trailofbits skills
critical_tob_skills=(
    "trailofbits/plugins/audit-context-building/skills/audit-context-building/SKILL.md"
    "trailofbits/plugins/constant-time-analysis/skills/constant-time-analysis/SKILL.md"
    "trailofbits/plugins/ask-questions-if-underspecified/skills/ask-questions-if-underspecified/SKILL.md"
)

for skill in "${critical_tob_skills[@]}"; do
    skill_name=$(basename "$skill" .md)
    if [[ -f ~/.claude/skills/$skill ]]; then
        echo -e "${GREEN}✓ $skill_name${NC}"
    else
        echo -e "${RED}✗ $skill_name (MISSING)${NC}"
    fi
done

# Check Ralph framework
echo ""
echo "Checking Ralph framework:"
echo "----------------------------------------"
ralph_scripts_check=(
    "ralph_loop.sh"
    "ralph_enable.sh"
    "ralph_monitor.sh"
)

for script in "${ralph_scripts_check[@]}"; do
    if [[ -x ~/.claude/skills/ralph/$script ]]; then
        echo -e "${GREEN}✓ $script (executable)${NC}"
    elif [[ -f ~/.claude/skills/ralph/$script ]]; then
        echo -e "${YELLOW}⚠  $script (exists but not executable)${NC}"
    else
        echo -e "${RED}✗ $script (MISSING)${NC}"
    fi
done

echo ""
echo "========================================="
echo "Validation Complete"
echo "========================================="
echo ""

if [[ "$total_skills" -eq 65 ]]; then
    echo -e "${GREEN}✓ All Phase A skills installed correctly!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Test critical workflows (see docs/PHASE-A-INSTALLATION-COMPLETE.md)"
    echo "  2. Run atomic-claude Phase 0 with new skills: python main.py run 0"
    echo "  3. Proceed to Phase B installation when ready"
    exit 0
else
    echo -e "${YELLOW}⚠  Skill count mismatch. Review installation.${NC}"
    echo ""
    echo "Expected: 65 skills (14 superpowers + 51 trailofbits)"
    echo "Found: $total_skills skills"
    echo ""
    echo "To reinstall:"
    echo "  cd ~/.claude/skills"
    echo "  rm -rf superpowers trailofbits ralph"
    echo "  git clone https://github.com/obra/superpowers.git superpowers"
    echo "  git clone https://github.com/trailofbits/skills.git trailofbits"
    echo "  git clone https://github.com/frankbria/ralph-claude-code.git ralph"
    exit 1
fi
