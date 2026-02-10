# Community Skills

This directory contains **65 third-party skills** from upstream repositories, tracked in the atomic-claude2 git repository for offline use.

---

## Installed Skills

### superpowers/ (14 skills)
**Source:** https://github.com/obra/superpowers

Planning, TDD, and debugging workflows:
- brainstorming - Strategic ideation
- writing-plans - Plan documentation
- executing-plans - Plan tracking
- test-driven-development - RED-GREEN-REFACTOR
- systematic-debugging - Structured debugging
- subagent-driven-development - Parallel agents
- And 8 more...

**Used in:** All phases, especially Phase 2 (PRD), Phase 5 (Implementation)

---

### trailofbits/ (51 skills)
**Source:** https://github.com/trailofbits/skills

Security auditing, fuzzing, and static analysis:
- **Core Security (11):** audit-context-building, constant-time-analysis, etc.
- **Smart Contracts (11):** Solana, Algorand, TON, Cairo, Cosmos, Substrate scanners
- **Fuzzing (17):** AFL++, LibFuzzer, cargo-fuzz, atheris, etc.
- **Static Analysis (3):** Semgrep, CodeQL, SARIF parsing
- **Specialized (9):** Burp Suite, Firebase, YARA, etc.

**Used in:** Phase 1 (Discovery), Phase 6 (Code Review), Phase 7 (Integration)

---

### ralph/ (Framework)
**Source:** https://github.com/frankbria/ralph-claude-code

Autonomous development framework (not SKILL.md-based):
- `ralph_loop.sh` - Autonomous development loop
- `ralph_enable.sh` - Enable for project
- `ralph_monitor.sh` - Live monitoring
- Safety guardrails, rate limiting, circuit breakers

**Used in:** Phase 5 (Implementation), continuous autonomous development

---

## Installation

Skills are already installed (tracked in git). No additional installation needed.

If you need to re-clone:
```bash
cd .claude/skills/community
rm -rf superpowers trailofbits ralph

git clone https://github.com/obra/superpowers.git superpowers
git clone https://github.com/trailofbits/skills.git trailofbits
git clone https://github.com/frankbria/ralph-claude-code.git ralph
```

---

## Updates

### Manual Update (Recommended Monthly)

```bash
cd .claude/skills/community

# Update each repository
cd superpowers && git pull && cd ..
cd trailofbits && git pull && cd ..
cd ralph && git pull && cd ..

# Commit updates to atomic-claude2
cd ../../..
git add .claude/skills/community/
git commit -m "Update community skills from upstream"
```

### Phase 0 Verification

Task 003 in Phase 0 verifies skills are present and counts them:
- Tactical skills: 20 expected
- Community skills: 65 expected
- Total: 85 skills

---

## Usage

Skills are invoked by Claude during task execution when mentioned in prompts.

### Example: Task Using Skills

```bash
# In task script (e.g., task101.sh)
cat > "$prompt_file" << EOF
Analyze the codebase for security issues.

You may use the following skills:
- /audit-context-building for ultra-granular analysis
- /extract-todos to find security TODO markers
- /constant-time-analysis for timing side-channels

Provide a comprehensive security assessment.
EOF

atomic_invoke "$prompt_file" "$output_file" "Security Analysis"
```

### Manual Invocation (Interactive)

In Claude Code session:
```bash
/extract-todos src/
/test-driven-development "implement user auth"
/audit-context-building "security review"
```

---

## Skill Integration by Phase

### Phase 0: Setup
- ask-questions-if-underspecified (clarify requirements)
- brainstorming (project ideation)

### Phase 1: Discovery
- audit-context-building (security analysis)
- entry-point-analyzer (code entry points)
- extract-todos (find action items)

### Phase 2: PRD
- brainstorming (ideation)
- writing-plans (PRD documentation)
- ask-questions-if-underspecified (requirements)

### Phase 3: Tasking
- writing-plans (task breakdown)
- executing-plans (task tracking)

### Phase 4: Specification
- spec-to-code-compliance (verify specs)
- writing-plans (spec documentation)

### Phase 5: Implementation
- test-driven-development (TDD workflow)
- subagent-driven-development (parallel work)
- systematic-debugging (debug workflow)
- ralph framework (autonomous development)

### Phase 6: Code Review
- audit-context-building (security review)
- constant-time-analysis (timing attacks)
- requesting-code-review (request reviews)
- fix-review (review fixes)

### Phase 7: Integration
- property-based-testing (testing)
- coverage-analysis (test coverage)

### Phase 8: Deployment Prep
- secure-workflow-guide (security)
- guidelines-advisor (best practices)

### Phase 9: Release
- verification-before-completion (final checks)

---

## Troubleshooting

### Skills Not Found

**Issue:** Claude says "skill not found"

**Solution:**
1. Check skill exists: `find . -name "*<skill-name>*"`
2. Verify SKILL.md format
3. Restart Claude Code session

### Skill Count Mismatch

**Issue:** Different count than expected (85 total)

**Solution:**
```bash
# Count tactical skills (should be 20)
find ../tactical -name "SKILL.md" | wc -l

# Count community skills (should be 65)
find . -name "SKILL.md" | wc -l
```

### Git Conflicts on Update

**Issue:** Merge conflicts when pulling updates

**Solution:**
1. Backup: `cp -r superpowers superpowers.backup`
2. Reset: `rm -rf superpowers`
3. Re-clone: `git clone https://github.com/obra/superpowers.git`

---

## Contributing

To add new community skills:

1. Clone skill repository to `community/`
2. Update `../SOURCES.md` with skill details
3. Commit to atomic-claude2:
   ```bash
   git add .claude/skills/community/<new-skill>
   git add .claude/skills/SOURCES.md
   git commit -m "Add <new-skill> community skills"
   ```

---

## Resources

- **SOURCES.md:** Complete skill inventory and maintenance guide
- **Superpowers Docs:** https://github.com/obra/superpowers/blob/main/README.md
- **Trail of Bits Docs:** https://github.com/trailofbits/skills/blob/main/README.md
- **Ralph Docs:** https://github.com/frankbria/ralph-claude-code/blob/main/README.md
- **SKILL.md Standard:** https://github.com/anthropics/skills/blob/main/template/SKILL.md

---

*65 community skills tracked for offline use*
*Last updated: February 10, 2026*
