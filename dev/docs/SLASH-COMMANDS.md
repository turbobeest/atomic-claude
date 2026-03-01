# Slash Commands - Quick Reference

**Created:** February 10, 2026
**Location:** `.claude/commands/`

---

## What Are Slash Commands?

Slash commands are **user-triggered shortcuts** that execute complex workflows with a simple command. Instead of typing long prompts, you type `/command-name` and Claude executes a pre-written workflow.

---

## Available Commands

### `/status` 📊
**Purpose:** Check pipeline status, see progress, identify next task

**Usage:**
```
/status
```

**Output:**
```
📊 ATOMIC CLAUDE STATUS

Phase: 2-prd
Progress: 5/8 tasks
Status: active

Recent Tasks:
  ✅ Task 203: Requirements Gathering - 45s
  ✅ Task 204: User Stories - 32s
  ✅ Task 205: PRD Authoring - 2m 15s

Next: Task 206: Validation

Outputs: .outputs/2-prd/
```

**When to use:**
- After `/clear` to see where you are
- Between work sessions
- To decide what to work on next

---

### `/backtrack <phase> [<task>]` ⏮️
**Purpose:** Safely reset pipeline to previous point

**Usage:**
```
/backtrack 2          # Go back to start of Phase 2
/backtrack 1 105      # Go back to Task 105 in Phase 1
```

**Output:**
```
⚠️  BACKTRACK WARNING

This will reset:
  • Phase 3 → Phase 2
  • Tasks 3 will be unmarked
  • Outputs in .outputs/2-prd/ will remain

Proceed? (y/n)
```

**When to use:**
- Phase output was wrong, need to regenerate
- Want to try different approach
- Found error in earlier phase

---

### `/review-task <task_id>` 🔍
**Purpose:** Deep analysis of task output with quality scoring

**Usage:**
```
/review-task 205      # Review PRD authoring output
```

**Output:**
```
🔍 TASK 205 REVIEW

Task: PRD Authoring
Phase: 2-prd
Output: .outputs/2-prd/prd.md

Quality Score: 87/100

✅ Strengths:
  • Clear acceptance criteria
  • Comprehensive user stories
  • Well-structured sections

⚠️  Issues:
  • Missing API rate limits section
  • Some requirements lack priority

💡 Recommendations:
  • Add rate limiting requirements
  • Prioritize must-have vs. nice-to-have
  • Add performance benchmarks

Regenerate? (y/n)
```

**When to use:**
- Validate task output quality
- Before moving to next phase
- When output seems incomplete

---

### `/export-phase <phase>` 📦
**Purpose:** Bundle phase outputs into shareable archive

**Usage:**
```
/export-phase 2       # Export all Phase 2 outputs
```

**Output:**
```
📦 PHASE 2 EXPORT

Archive: atomic-phase2-20260210-143022.tar.gz
Size: 2.4 MB

Contents:
  • 8 JSON files
  • 3 Markdown files
  • Task state snapshot

Location: ./atomic-phase2-20260210-143022.tar.gz

Share: scp atomic-phase2-20260210-143022.tar.gz user@server:/path/
```

**When to use:**
- Share phase outputs with team
- Archive before major refactor
- Send outputs for review

---

### `/run-phase <phase> [options]` 🚀
**Purpose:** Execute phase with validation and smart resume

**Usage:**
```
/run-phase 2                    # Run Phase 2 from beginning
/run-phase 2 --resume-at=205    # Resume at Task 205
/run-phase 2 --force            # Force re-run even if complete
```

**Output:**
```
🚀 EXECUTING PHASE 2

Command: python main.py run 2
Phase: PRD
Starting at: Task 201
Outputs: .outputs/2-prd/

Press Ctrl+C to cancel

... (phase execution) ...

✅ PHASE 2 COMPLETE

Duration: 8m 42s
Tasks: 8/8
Outputs: .outputs/2-prd/

Next: /run-phase 3
```

**When to use:**
- Start a phase with validation
- Resume after interruption
- Re-run with --force for fresh outputs

---

### `/catchup` 📝
**Purpose:** Re-read changed files after `/clear`

**Usage:**
```
/catchup
```

**Output:**
```
📝 CATCHUP REPORT

Since: 2026-02-10 12:30:15

Modified Files (3):
  • core/state.py (34 lines changed)
  • phases/phase02/orchestrator02.py (12 lines changed)
  • docs/MCP.md (new file, 450 lines)

New Files (2):
  • .claude/commands/status.md
  • .claudeignore

✅ Caught up on 5 changed files

Key changes:
  • MCP configuration added
  • Slash commands created
  • Python orchestrators updated

Ready to continue.
```

**When to use:**
- After `/clear` to regain context
- Start of new session
- After long break

---

## Benefits for Atomic-Claude2

### 1. **Faster Navigation**
```
❌ Before:
"Can you check the current phase status, list all completed tasks,
tell me what outputs were generated, and what task should run next?"

✅ After:
/status
```

### 2. **Consistent Workflows**
Every time you run `/review-task`, you get the same structured analysis:
- Quality score
- Strengths
- Issues
- Recommendations

No variation in prompt phrasing = consistent results.

### 3. **Context Recovery**
After `/clear` (when context is full):
```
/catchup          # Re-read only changed files
/status           # See where you are
/run-phase 3      # Continue work
```

### 4. **Safer Operations**
`/backtrack` validates before resetting:
- Shows what will change
- Asks for confirmation
- Preserves output files

### 5. **Team Collaboration**
Share commands across team:
- Everyone uses same `/review-task` criteria
- Consistent `/export-phase` for handoffs
- Standardized `/run-phase` validation

---

## How They Work Internally

1. **User types:** `/status`

2. **Claude Code:**
   - Locates: `.claude/commands/status.md`
   - Reads the markdown (it's a detailed prompt)
   - Executes the instructions in the markdown
   - Returns formatted output

3. **Markdown template** has:
   - Instructions for Claude
   - Output format
   - Error handling
   - Tips

**It's like a macro** - complex multi-step prompt → simple command.

---

## Creating Custom Commands

Want a command for your specific workflow?

### Example: `/test-coverage`

```markdown
# Test Coverage Report

## Instructions

1. Read `.outputs/7-integration/test-results.json`

2. Calculate coverage:
   - Lines covered / total lines
   - Files with <80% coverage

3. Show report:
   ```
   📊 TEST COVERAGE

   Overall: 87.5%

   Low Coverage Files:
     • src/api.py (45%)
     • src/utils.py (67%)
     • src/db.py (72%)

   Next: Focus on api.py tests
   ```
```

Save as `.claude/commands/test-coverage.md`, then use `/test-coverage`.

---

## Best Practices

1. **Keep commands focused** - One command, one job
2. **Use consistent format** - All outputs should look similar
3. **Add validation** - Check inputs, fail gracefully
4. **Provide next steps** - Tell user what to do after
5. **Handle errors** - Explain what went wrong, how to fix

---

## Comparison: Before vs. After

### Scenario: Check status and resume work

**Before slash commands:**
```
User: "What phase am I on? What tasks are done? What's next?"

Claude: (reads state, analyzes, formats response)

User: "OK, run the next task"

Claude: "Which phase? Which task?"

User: "Phase 2, task 205"

Claude: (runs task)
```

**After slash commands:**
```
User: /status

Claude: (instant structured report)

User: /run-phase 2 --resume-at=205

Claude: (runs with validation)
```

**Time saved:** ~60 seconds per interaction
**Consistency:** 100% (same output every time)

---

## Integration with Atomic-Claude2

Slash commands work **within Claude Code sessions**, not from bash scripts.

**Usage Pattern:**

```bash
# Start interactive Claude Code session
cd /path/to/atomic-claude
claude

# Now in Claude Code CLI:
> /status
📊 Phase 2, 5/8 tasks complete...

> /review-task 205
🔍 Quality score: 87/100...

> /run-phase 3
🚀 Starting Phase 3...
```

**For automation** (bash scripts), use `atomic_invoke` as usual.

---

## Next Steps

1. ✅ Commands created in `.claude/commands/`
2. Test them:
   ```bash
   claude
   > /status
   > /review-task 205
   ```
3. Customize for your workflow
4. Share with team

---

*Generated for atomic-claude on February 10, 2026*
