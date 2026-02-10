# Skills Integration Proposal

**Date:** February 10, 2026
**Status:** PROPOSED
**Issue:** Skills currently installed globally, not integrated into atomic-claude2 repo

---

## Problem Statement

**Current Issues:**
1. ✅ 20 tactical skills exist in `.claude/skills/` (good - already in repo)
2. ❌ 65 community skills installed to `~/.claude/skills/` (wrong - global, not portable)
3. ❌ No skill installation during Phase 0 setup
4. ❌ No mechanism for tasks to invoke skills
5. ❌ Skills are not cloned when repo is cloned

**Root cause:** Treated skills as a local machine capability, not as part of the cloneable atomic-claude2 system.

---

## Proposed Solution

### Architecture

```
atomic-claude2/
├── .claude/
│   └── skills/
│       ├── README.md                    # Skill system documentation
│       ├── tactical/                    # Our 20 tactical skills (KEEP AS-IS)
│       │   ├── formatting/
│       │   ├── validation/
│       │   ├── extraction/
│       │   ├── git-ops/
│       │   ├── file-ops/
│       │   ├── doc-gen/
│       │   ├── phase-checks/
│       │   └── atomic/
│       ├── community/                   # Community skills (INSTALL DURING PHASE 0)
│       │   ├── superpowers/             # Clone from obra/superpowers
│       │   ├── trailofbits/             # Clone from trailofbits/skills
│       │   └── ralph/                   # Clone from frankbria/ralph-claude-code
│       └── SOURCES.md                   # Track upstream repos for updates
│
├── core/
│   └── skill_manager.py                 # NEW: Python skill invocation (optional)
│
├── lib/
│   └── skills.sh                        # NEW: Bash skill helpers (optional)
│
└── phases/
    └── phase00/
        ├── orchestrator00.py
        ├── task001.sh
        ├── task002.sh
        └── task003_install_skills.sh   # NEW: Install community skills
```

---

## Implementation Plan

### Part 1: Repository Restructuring

**Step 1: Move tactical skills to `tactical/` subdirectory**

```bash
cd /Users/jamesterbeest/dev/atomic-claude2/.claude/skills
mkdir -p tactical
mv formatting validation extraction git-ops file-ops doc-gen phase-checks atomic tactical/
mv README.md tactical/
```

**Step 2: Create community skills placeholder**

```bash
cd /Users/jamesterbeest/dev/atomic-claude2/.claude/skills
mkdir -p community
cat > community/README.md << 'EOF'
# Community Skills

This directory contains third-party skills installed during Phase 0.

## Installed Skills

After Phase 0 completion, this directory will contain:

- **superpowers/** - 14 skills for planning, TDD, debugging (obra/superpowers)
- **trailofbits/** - 51 skills for security auditing, fuzzing (trailofbits/skills)
- **ralph/** - Autonomous development framework (frankbria/ralph-claude-code)

## Installation

Skills are automatically installed by Task 003 during Phase 0.

Manual installation:
```bash
cd .claude/skills/community
git clone https://github.com/obra/superpowers.git superpowers
git clone https://github.com/trailofbits/skills.git trailofbits
git clone https://github.com/frankbria/ralph-claude-code.git ralph
```

## Updates

To update community skills:
```bash
cd .claude/skills/community
cd superpowers && git pull && cd ..
cd trailofbits && git pull && cd ..
cd ralph && git pull && cd ..
```
EOF
```

**Step 3: Add SOURCES.md for tracking**

```bash
cat > /Users/jamesterbeest/dev/atomic-claude2/.claude/skills/SOURCES.md << 'EOF'
# Skill Sources

## Tactical Skills (Maintained In-Repo)

| Category | Count | Maintained By |
|---|---|---|
| formatting | 3 | atomic-claude2 |
| validation | 4 | atomic-claude2 |
| extraction | 3 | atomic-claude2 |
| git-ops | 2 | atomic-claude2 |
| file-ops | 3 | atomic-claude2 |
| doc-gen | 2 | atomic-claude2 |
| phase-checks | 2 | atomic-claude2 |
| atomic | 1 | atomic-claude2 |
| **Total** | **20** | **In-repo** |

## Community Skills (Installed from Git)

| Repository | Upstream | Skills | Last Updated |
|---|---|---|---|
| superpowers | https://github.com/obra/superpowers | 14 | Installed during Phase 0 |
| trailofbits | https://github.com/trailofbits/skills | 51 | Installed during Phase 0 |
| ralph | https://github.com/frankbria/ralph-claude-code | framework | Installed during Phase 0 |

## Update Schedule

- **Tactical skills:** Updated via git commits to atomic-claude2
- **Community skills:** Updated manually via `git pull` in each subdirectory
- **Recommended:** Check for updates monthly

## Installation

Community skills are installed by Task 003 during Phase 0.
EOF
```

---

### Part 2: Create Skill Installation Task

**Create `phases/phase00/task003_install_skills.sh`:**

```bash
#!/usr/bin/env bash
#
# Task 003: Install Community Skills
# Clones community skill repositories into .claude/skills/community/
#
# Input: None (git repositories)
# Output: .claude/skills/community/ populated with skills
#

set -euo pipefail
LIB_DIR="${ATOMIC_LIB_DIR:-$(dirname "$0")/../../lib}"
source "$LIB_DIR/atomic.sh"

task_003_install_skills() {
    local skills_dir="$ATOMIC_ROOT/.claude/skills/community"
    local install_log="$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/skills-installation.log"

    atomic_step "Installing Community Skills"

    # Create community directory
    mkdir -p "$skills_dir"

    # Check if already installed
    if [[ -d "$skills_dir/superpowers" ]] && \
       [[ -d "$skills_dir/trailofbits" ]] && \
       [[ -d "$skills_dir/ralph" ]]; then
        atomic_substep "Community skills already installed"

        # Count skills
        local superpowers_count=$(find "$skills_dir/superpowers" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
        local trailofbits_count=$(find "$skills_dir/trailofbits" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')

        echo "  Found:"
        echo "    • superpowers: $superpowers_count skills"
        echo "    • trailofbits: $trailofbits_count skills"
        echo "    • ralph: framework"
        echo ""

        atomic_success "Skills available"
        return 0
    fi

    atomic_substep "Cloning skill repositories..."
    echo ""

    # Install superpowers (planning, TDD, debugging)
    if [[ ! -d "$skills_dir/superpowers" ]]; then
        echo "  Installing superpowers (planning, TDD, debugging)..."
        if git clone https://github.com/obra/superpowers.git "$skills_dir/superpowers" >> "$install_log" 2>&1; then
            local count=$(find "$skills_dir/superpowers" -name "SKILL.md" | wc -l | tr -d ' ')
            echo "    ✓ Installed $count skills"
        else
            atomic_error "Failed to clone superpowers"
            return 1
        fi
    fi

    # Install Trail of Bits (security, fuzzing)
    if [[ ! -d "$skills_dir/trailofbits" ]]; then
        echo "  Installing trailofbits (security auditing, fuzzing)..."
        if git clone https://github.com/trailofbits/skills.git "$skills_dir/trailofbits" >> "$install_log" 2>&1; then
            local count=$(find "$skills_dir/trailofbits" -name "SKILL.md" | wc -l | tr -d ' ')
            echo "    ✓ Installed $count skills"
        else
            atomic_error "Failed to clone trailofbits"
            return 1
        fi
    fi

    # Install Ralph (autonomous framework)
    if [[ ! -d "$skills_dir/ralph" ]]; then
        echo "  Installing ralph (autonomous development framework)..."
        if git clone https://github.com/frankbria/ralph-claude-code.git "$skills_dir/ralph" >> "$install_log" 2>&1; then
            echo "    ✓ Installed framework"
        else
            atomic_error "Failed to clone ralph"
            return 1
        fi
    fi

    echo ""

    # Verify installation
    local total_skills=0
    local superpowers_count=$(find "$skills_dir/superpowers" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
    local trailofbits_count=$(find "$skills_dir/trailofbits" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
    total_skills=$((superpowers_count + trailofbits_count))

    atomic_substep "Installation summary"
    echo "  Installed $total_skills community skills:"
    echo "    • superpowers: $superpowers_count skills"
    echo "    • trailofbits: $trailofbits_count skills"
    echo "    • ralph: autonomous framework"
    echo ""
    echo "  Skills location: .claude/skills/community/"
    echo ""

    # Create installation report
    cat > "$ATOMIC_OUTPUT_DIR/$CURRENT_PHASE/skills-installed.json" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "skills_directory": ".claude/skills/community",
  "repositories": {
    "superpowers": {
      "url": "https://github.com/obra/superpowers",
      "skills": $superpowers_count,
      "type": "planning, TDD, debugging"
    },
    "trailofbits": {
      "url": "https://github.com/trailofbits/skills",
      "skills": $trailofbits_count,
      "type": "security, fuzzing, static analysis"
    },
    "ralph": {
      "url": "https://github.com/frankbria/ralph-claude-code",
      "type": "autonomous framework"
    }
  },
  "total_skills": $total_skills
}
EOF

    atomic_success "Community skills installed"
    return 0
}

# Execute if run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    task_003_install_skills
fi
```

---

### Part 3: Update Phase 0 Orchestrator

**Add task 003 to `phases/phase00/orchestrator00.py`:**

```python
def task_003_install_skills() -> bool:
    """Install community skills from git repositories."""
    script_path = Path(__file__).parent / "task003_install_skills.sh"
    exit_code = run_task_script_streaming(
        script_path,
        "0-setup",
        "003",
        timeout=600  # 10 minutes for git clones
    )
    return exit_code == 0

def run_phase(resume_at: str = None) -> bool:
    """Execute Phase 0 tasks."""
    phase_header("Phase 0: Setup")
    state = StateManager()
    phase_id = "0-setup"

    tasks = [
        ("001", "Setup Validation", task_001_validation),
        ("002", "Config Collection", task_002_config),
        ("003", "Install Community Skills", task_003_install_skills),  # NEW
        ("004", "Agent Selection", task_004_agents),
        ("005", "Audit Selection", task_005_audits),
        ("006", "Closeout", task_006_closeout),
    ]

    # ... rest of orchestrator
```

---

### Part 4: Skills Invocation (Optional)

**Question:** Do tasks need to invoke skills programmatically?

**Answer:** Generally **NO**. Here's why:

#### Skills vs. atomic_invoke

| Aspect | Skills (SKILL.md) | atomic_invoke (tasks) |
|---|---|---|
| **Purpose** | Interactive Claude assistance | Automated task execution |
| **Invocation** | Manual (`/skill-name`) or auto-invoked by Claude | Programmatic (bash scripts) |
| **Context** | Claude Code sessions | Batch processing in tasks |
| **Use case** | User-driven workflows | Pipeline automation |

#### When Tasks Use Skills

**Rare cases where tasks might reference skills:**

1. **Code review tasks** could mention "You may use /extract-todos skill"
2. **Security audit tasks** could mention "Consider /audit-context-building"
3. **Planning tasks** could mention "Use /brainstorming for ideation"

But tasks **don't programmatically invoke** skills - they provide prompts to Claude, and Claude may choose to use skills.

#### If We Need Skill Invocation (Future)

If tasks eventually need to invoke skills programmatically:

**Option A: Via Claude Code CLI**
```bash
# In task script
claude-code --skill extract-todos --args "src/"
```

**Option B: Via Python wrapper**
```python
# core/skill_manager.py
from core.llm import invoke_llm

class SkillManager:
    def invoke_skill(self, skill_name: str, args: str) -> str:
        """Invoke a skill and return output."""
        skill_path = f".claude/skills/{skill_name}/SKILL.md"
        skill_content = Path(skill_path).read_text()

        # Parse SKILL.md and execute with Claude
        prompt = f"Execute skill: {skill_name}\nArgs: {args}\n\n{skill_content}"
        return invoke_llm(prompt, model="sonnet")
```

**But this is likely unnecessary.** Skills are for interactive Claude usage, tasks use atomic_invoke.

---

## Part 5: Update .gitignore

**Add to `.gitignore`:**

```gitignore
# Community skills (installed during Phase 0, not tracked)
.claude/skills/community/superpowers/
.claude/skills/community/trailofbits/
.claude/skills/community/ralph/

# But keep the README
!.claude/skills/community/README.md
```

**Wait - should we track community skills?**

**Option A: Don't track (recommended)**
- ✅ Smaller repo size
- ✅ Always get latest skills on install
- ✅ No merge conflicts
- ❌ Requires internet during Phase 0
- ❌ Skills might break if upstream changes

**Option B: Track as git submodules**
- ✅ Versioned, reproducible
- ✅ Works offline after clone
- ❌ Larger repo
- ❌ Submodule complexity

**Option C: Track directly (not recommended)**
- ✅ Simple, versioned
- ✅ Works offline
- ❌ Very large repo (65 skills = ~10MB)
- ❌ Merge conflicts on updates

**Recommendation:** Option A (don't track), install during Phase 0

---

## Part 6: Update Documentation

**Update `README.md`:**

```markdown
## Skills System

Atomic-claude2 includes **85 skills** across 3 categories:

### Tactical Skills (20, in-repo)
Custom skills for atomic-claude workflows:
- **Formatting** (3): format-code, lint-check, type-check
- **Validation** (4): validate-json, validate-yaml, validate-openapi, validate-prd
- **Extraction** (3): extract-todos, extract-functions, extract-imports
- **Git Ops** (2): quick-status, quick-diff
- **File Ops** (3): count-lines, find-duplicates, check-imports-unused
- **Doc Gen** (2): generate-changelog, generate-api-summary
- **Phase Checks** (2): check-phase-outputs, phase-summary
- **Atomic** (1): check-test-coverage

### Community Skills (65, installed during Phase 0)
Third-party skills from:
- **obra/superpowers** (14): Planning, TDD, debugging workflows
- **trailofbits/skills** (51): Security auditing, fuzzing, smart contracts
- **frankbria/ralph** (1 framework): Autonomous development loops

Skills are installed automatically during Phase 0, Task 003.

### Using Skills

Skills are invoked by Claude during interactive sessions:
```bash
# Claude will use skills when appropriate, or you can invoke manually:
/extract-todos src/
/test-driven-development "implement user auth"
/audit-context-building "review security"
```

For task automation, use `atomic_invoke` in bash scripts (see `lib/atomic.sh`).
```

**Update `CLAUDE.md`:**

Add section on skills:

```markdown
## Skills System

### Structure

```
.claude/skills/
├── tactical/          # 20 in-repo skills (tracked)
└── community/         # 65 installed skills (not tracked)
```

### Installation

Community skills are installed during Phase 0, Task 003:
- Clones from upstream git repositories
- Verifies installation
- Creates `.outputs/0-setup/skills-installed.json`

### Usage

**In tasks:** Use `atomic_invoke` for prompts (see `lib/atomic.sh`)
**Interactively:** Claude uses skills automatically or via `/skill-name`

### Maintenance

Update community skills:
```bash
cd .claude/skills/community
cd superpowers && git pull && cd ..
cd trailofbits && git pull && cd ..
cd ralph && git pull && cd ..
```
```

---

## Implementation Checklist

### Phase 1: Restructure (30 minutes)
- [ ] Move tactical skills to `tactical/` subdirectory
- [ ] Create `community/` with README
- [ ] Add `SOURCES.md` tracking document
- [ ] Update `.gitignore` to exclude community skills

### Phase 2: Create Installation Task (30 minutes)
- [ ] Write `task003_install_skills.sh`
- [ ] Update `orchestrator00.py` to include task 003
- [ ] Test installation in clean environment

### Phase 3: Cleanup (15 minutes)
- [ ] Remove global `~/.claude/skills/` installation
- [ ] Update all documentation (README, CLAUDE.md, docs/)
- [ ] Create validation script

### Phase 4: Testing (30 minutes)
- [ ] Clone repo to clean directory
- [ ] Run Phase 0 and verify skill installation
- [ ] Validate 85 total skills (20 tactical + 65 community)
- [ ] Run UAT with new structure

**Total time:** ~2 hours

---

## Migration from Current State

**Current:** 65 skills in `~/.claude/skills/` (global)
**Target:** 65 skills in `.claude/skills/community/` (repo-local)

**Migration steps:**

```bash
# 1. Backup global skills
mv ~/.claude/skills ~/.claude/skills.backup

# 2. Run new Phase 0 task 003
cd /Users/jamesterbeest/dev/atomic-claude2
python main.py run 0 --resume-at=003

# 3. Verify installation
find .claude/skills/community -name "SKILL.md" | wc -l
# Should output: 65

# 4. Remove backup (after validation)
rm -rf ~/.claude/skills.backup
```

---

## Benefits of This Approach

1. **Portable:** Skills are part of the repo (or installed during setup)
2. **Cloneable:** Fresh clone → Phase 0 → skills installed automatically
3. **Maintainable:** Clear separation between tactical (in-repo) and community (installed)
4. **Updatable:** Easy to update community skills via `git pull`
5. **Documented:** Clear SOURCES.md shows what's installed and from where

---

## Questions to Resolve

### Q1: Should community skills be tracked in git?

**Proposed:** No, install during Phase 0
**Reasoning:** Keeps repo small, always gets latest skills, avoids merge conflicts

### Q2: Do tasks need to invoke skills programmatically?

**Proposed:** No, tasks use `atomic_invoke`, skills are for interactive Claude
**Reasoning:** Skills are for user-driven workflows, tasks are for automation

### Q3: Should skills be installed globally or locally?

**Proposed:** Locally (`.claude/skills/community/`)
**Reasoning:** Project-specific, portable, cloneable

### Q4: When should skills be updated?

**Proposed:** Manual `git pull` in community skills directories, monthly check
**Reasoning:** Stability over freshness for reproducibility

---

## Next Steps

1. **Decision:** User approves this approach
2. **Implement Phase 1:** Restructure existing skills (30 minutes)
3. **Implement Phase 2:** Create task 003 (30 minutes)
4. **Test:** Run Phase 0 in clean environment
5. **Document:** Update all docs and create migration guide

---

*Proposal created: February 10, 2026*
*Status: AWAITING APPROVAL*
