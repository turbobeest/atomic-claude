# Atomic Claude v1→v2 Migration Quick Start

**5-Minute Migration Guide**

---

## Prerequisites

- Python 3.9+
- Backup of v1 state
- 15 minutes of time

---

## Quick Migration Steps

### 1. Backup v1 State (2 min)

```bash
cd /path/to/atomic-claude
tar -czf ~/atomic-backup-$(date +%Y%m%d_%H%M%S).tar.gz .state .outputs .env
```

### 2. Clone v2 (1 min)

```bash
cd /path/to/projects
git clone https://github.com/yourusername/atomic-claude2.git
cd atomic-claude2
```

### 3. Install Dependencies (2 min)

```bash
pip install -r requirements.txt
```

### 4. Copy Configuration (1 min)

```bash
cp ../atomic-claude/.env .env
```

### 5. Run Migration (2 min)

```bash
python scripts/migrate.py \
  --old-state ../atomic-claude/.state \
  --new-state .state
```

### 6. Verify (1 min)

```bash
python main.py status
```

### 7. Copy Repos (Optional, 2 min)

```bash
ln -s ../atomic-claude/agents agents
ln -s ../atomic-claude/audits audits
```

---

## Quick Commands

**Run phase:**
```bash
python main.py run 2
```

**Resume from task:**
```bash
python main.py run 2 --resume-at=205
```

**Check status:**
```bash
python main.py status
```

**Backtrack:**
```bash
python main.py backtrack 2 205
```

---

## Troubleshooting

**State is empty:**
```bash
python scripts/migrate.py --old-state ../atomic-claude/.state --new-state .state
```

**Config not loaded:**
```bash
cat .env
# Verify ANTHROPIC_API_KEY or AWS credentials
```

**Task scripts missing:**
```bash
cp -r ../atomic-claude/phases/0-setup/tasks/* phases/phase00/
```

---

## Rollback

```bash
cd ../atomic-claude
cp .state.backup.*/task-state.json .state/
cd phases/0-setup
bash orchestrator.sh
```

---

## Full Documentation

See [MIGRATION-GUIDE.md](MIGRATION-GUIDE.md) for comprehensive instructions, troubleshooting, and FAQ.

---

## What Changed?

- **CLI:** `bash orchestrator.sh` → `python main.py run 2`
- **Structure:** Scattered files → Grouped phases
- **State:** Simple JSON → Transactional with snapshots
- **Config:** Env only → Multi-source with validation
- **Organization:** Manual → Automatic forcing function

## What Stayed the Same?

- Task scripts (still bash)
- LLM invocation patterns
- Phase workflow
- Output structure
- Agent/audit repositories

---

**That's it! You're migrated in 5-10 minutes.**

For detailed information, see [MIGRATION-GUIDE.md](MIGRATION-GUIDE.md).
