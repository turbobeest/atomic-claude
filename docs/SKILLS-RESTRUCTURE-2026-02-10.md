# Skills Restructure: Moving from .claude/skills to skills/

**Date:** February 10, 2026
**Issue:** `.claude/` directories are commonly gitignored, risking skill portability
**Solution:** Move skills to top-level `skills/` directory

---

## Problem Identified

Original structure placed skills in `.claude/skills/`:
```
atomic-claude2/
└── .claude/
    └── skills/
        ├── tactical/
        └── community/
```

**Critical Risk:**
- `.claude/` directories typically contain local state (cache, logs, etc.)
- Developers commonly add `.claude/` to `.gitignore`
- If gitignored, all 85 skills would be excluded from repo
- **Defeats entire purpose of offline/portable skills**

---

## Solution: Top-Level skills/ Directory

**New structure:**
```
atomic-claude2/
├── skills/              # ← Top-level, clearly part of repo
│   ├── tactical/        # 20 in-repo skills
│   │   ├── formatting/
│   │   ├── validation/
│   │   ├── extraction/
│   │   ├── git-ops/
│   │   ├── file-ops/
│   │   ├── doc-gen/
│   │   ├── phase-checks/
│   │   └── atomic/
│   ├── community/       # 65 community skills
│   │   ├── superpowers/
│   │   ├── trailofbits/
│   │   └── ralph/
│   └── SOURCES.md       # Inventory and maintenance guide
└── .claude/
    ├── commands/        # Slash commands
    ├── audit/           # Other Claude Code config
    └── ... (no skills!)
```

**Benefits:**
- ✅ Won't be accidentally gitignored
- ✅ Clearly part of project structure (not local state)
- ✅ Easier to discover and understand
- ✅ Still portable and works offline
- ✅ Standard pattern (many projects have `skills/` at root)

---

## Changes Made

### 1. Directory Move
```bash
mv .claude/skills skills
```

### 2. Updated Files

**phases/phase00/task003_verify_skills.sh:**
```bash
# Before:
local skills_dir="$ATOMIC_ROOT/.claude/skills"

# After:
local skills_dir="$ATOMIC_ROOT/skills"
```

**skills/SOURCES.md:**
```markdown
# Before:
Located in `.claude/skills/`

# After:
Located in `skills/` at repository root
```

### 3. Claude Code Discovery

Claude Code can discover skills in multiple locations:
1. Global: `~/.claude/skills/` (user-wide skills)
2. Project: `<project>/.claude/skills/` (project-local, but risky)
3. **Project (new):** `<project>/skills/` (recommended)

For atomic-claude2, skills are in `<repo>/skills/`, which Claude Code will discover when working in the repo directory.

---

## Migration Guide

### For Existing Clones (Pre-Restructure)

If you cloned atomic-claude2 before this change:

```bash
cd /path/to/atomic-claude2

# Check if you have old structure
if [[ -d .claude/skills ]]; then
    echo "Old structure detected"

    # Pull latest
    git pull

    # Old .claude/skills will be untracked (not in new commits)
    # Safe to remove:
    rm -rf .claude/skills

    # New skills/ directory will be present from git pull
    ls -la skills/
fi
```

### For New Clones (Post-Restructure)

Just clone - skills are already in `skills/`:
```bash
git clone <repo-url>
cd atomic-claude2
ls -la skills/
# Should show: tactical/, community/, SOURCES.md
```

---

## Verification

### Check Skills Are in Correct Location

```bash
cd /path/to/atomic-claude2

# Check skills/ exists at root
ls -la skills/
# Expected: tactical/, community/, SOURCES.md

# Count skills
find skills/tactical -name "SKILL.md" | wc -l    # 20
find skills/community -name "SKILL.md" | wc -l   # 65

# Run verification
./phases/phase00/task003_verify_skills.sh
```

**Expected output:**
```
Verifying Skills System
  Tactical skills: 20
  Community skills: 65
  Total SKILL.md files: 85
✅ Skills system verified (85 skills)
```

### Check .claude/ Does NOT Contain Skills

```bash
# This should be empty or not exist:
ls -la .claude/skills 2>/dev/null || echo "Correct - no .claude/skills/"
```

---

## Documentation Updates

### Primary References (Updated)

1. **skills/SOURCES.md** - Updated paths
2. **phases/phase00/task003_verify_skills.sh** - Updated verification
3. **This document** - Restructure explanation

### Historical References (Superseded)

These docs reference old `.claude/skills/` structure (kept for history):
- `docs/SKILLS-INTEGRATION-COMPLETE.md`
- `docs/SKILLS-INTEGRATION-FINAL.md`
- `docs/SKILLS-INTEGRATION-PROPOSAL.md`
- `docs/PHASE-A-INSTALLATION-COMPLETE.md`

**Note:** Old docs are still accurate for understanding the integration process, just use `skills/` wherever you see `.claude/skills/`.

---

## Why This Matters

### The Risk Was Real

Common patterns that would break old structure:

**.gitignore examples from real projects:**
```gitignore
# Common pattern that would exclude skills:
.claude/

# Or more specific:
.claude/*
!.claude/commands/

# Without explicit exception for skills:
.claude/skills/  # ← Would break portability
```

### New Structure is Safe

```gitignore
# Even if someone adds:
.claude/

# Skills are unaffected because they're at:
skills/  # ← Not under .claude/
```

---

## Future Considerations

### Should .claude/ Be in .gitignore?

**Recommendation:** Yes, but with exceptions:

```gitignore
# .gitignore
.claude/*
!.claude/commands/
!.claude/audit/
!.claude/closeout/
# etc. - include project-specific Claude Code config

# No need to exclude skills - they're in skills/ now
```

### Adding New Skills

```bash
# New skills go in skills/, not .claude/skills/
cd skills/community
git clone <upstream-skill-repo> <skill-name>

# Update inventory
vim skills/SOURCES.md

# Commit
git add skills/
git commit -m "Add <skill-name> community skill"
```

---

## FAQ

**Q: Will Claude Code still find skills in `skills/`?**
A: Yes, Claude Code discovers skills in project directories, not just `.claude/skills/`.

**Q: Do I need to symlink to `~/.claude/skills/`?**
A: No. Claude Code finds skills in the project when working in that directory.

**Q: What about global skills in `~/.claude/skills/`?**
A: Those are user-wide skills, separate from project skills. Both can coexist.

**Q: Can I still use `.claude/skills/` if I want?**
A: Technically yes, but not recommended due to gitignore risk. Use `skills/` instead.

**Q: What about the old commits with `.claude/skills/`?**
A: Git history preserves them. The move is just a restructure, not a rewrite.

---

## Summary

**Problem:** `.claude/skills/` at risk of being gitignored
**Solution:** Move to `skills/` at repository root
**Status:** ✅ Complete
**Impact:** Safer, clearer, still portable

**Key change:**
```bash
# Before:
.claude/skills/tactical/
.claude/skills/community/

# After:
skills/tactical/
skills/community/
```

Skills are now in a standard, safe location that won't be accidentally excluded from the repository.

---

*Restructure completed: February 10, 2026*
*Reason: Prevent accidental exclusion via .gitignore*
*Impact: None on functionality, improved safety*
*Files updated: 2 (verification script + SOURCES.md)*
