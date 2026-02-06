# Dual-Repo Sync Strategy for python-bash Branch

## Setup Complete ✅

**Branch**: `python-bash`

**Remotes**:
- `origin`: https://github.com/turbobeest/atomic-claude.git (PUBLIC)
- `internal`: https://github.boozallencsn.com/TerBeest-James/atomic-claude.git (PRIVATE - Booz Allen)

Both repos now have the `python-bash` branch pushed.

---

## Quick Reference

### Daily Workflow (Working Locally on Bedrock)

```bash
# 1. Check status before starting work
source .git-sync-config.sh
sync-status

# 2. Pull any updates from both repos
sync-pull
git merge origin/python-bash  # if origin has changes
git merge internal/python-bash  # if internal has changes

# 3. Make your changes...
git add .
git commit -m "Your commit message"

# 4. Push to BOTH repos at once
sync-push
```

### Working from External Location (Outside Booz Allen Network)

```bash
# You can only access origin (public GitHub)
git fetch origin python-bash
git merge origin/python-bash

# Make changes...
git commit -m "External changes"
git push origin python-bash

# Later, when back on Bedrock, sync to internal:
source .git-sync-config.sh
sync-origin-to-internal
```

### When Repos Get Out of Sync

**Scenario**: You edited on GitHub web interface (either repo)

```bash
# If public repo is ahead, sync to private:
sync-origin-to-internal

# If private repo is ahead, sync to public:
sync-internal-to-origin
```

---

## Manual Commands (Without Helper Script)

### Push to both repos:
```bash
git push origin python-bash
git push internal python-bash
```

### Pull from both repos:
```bash
git fetch origin python-bash
git fetch internal python-bash
```

### Check differences:
```bash
# See what's on origin that you don't have locally
git log HEAD..origin/python-bash

# See what's on internal that you don't have locally
git log HEAD..internal/python-bash

# See what you have locally that's not on origin
git log origin/python-bash..HEAD
```

### Sync one repo to another directly:
```bash
# Sync PUBLIC → PRIVATE
git fetch origin python-bash
git push internal origin/python-bash:python-bash

# Sync PRIVATE → PUBLIC  
git fetch internal python-bash
git push origin internal/python-bash:python-bash
```

---

## Important Notes

1. **Default tracking**: Branch tracks `origin/python-bash` (public repo)
   - `git pull` = `git pull origin python-bash`
   - `git push` = `git push origin python-bash`

2. **Always pull before push**: When working from different locations
   ```bash
   git fetch origin && git fetch internal
   git merge origin/python-bash  # or internal/python-bash
   git push origin python-bash && git push internal python-bash
   ```

3. **Conflict resolution**: If both repos have diverged:
   ```bash
   git fetch origin
   git fetch internal
   
   # Merge one, then the other
   git merge origin/python-bash
   git merge internal/python-bash
   
   # Resolve conflicts, then push to both
   git push origin python-bash
   git push internal python-bash
   ```

4. **GitHub web edits**: Avoid editing on GitHub web if possible. If you do:
   - Always `sync-pull` before making local changes
   - Use `sync-origin-to-internal` or `sync-internal-to-origin` to keep them aligned

---

## Automation Option

Add to your `.bashrc` or `.zshrc`:

```bash
# Atomic Claude dual-repo sync
if [ -f ~/path/to/atomic-claude/.git-sync-config.sh ]; then
    source ~/path/to/atomic-claude/.git-sync-config.sh
fi
```

Then you can use `sync-push`, `sync-pull`, etc. from anywhere.

---

## Best Practices

1. **Commit often, push to both**: Don't let the repos drift
2. **Use sync-status regularly**: Check before starting work
3. **Pull before push**: Always fetch from both repos first
4. **Descriptive commits**: Makes merging easier if conflicts arise
5. **Test locally**: Ensure code works before pushing to both repos

---

## Troubleshooting

**Problem**: Push rejected (non-fast-forward)

```bash
# Someone else pushed to one of the repos
git fetch origin
git fetch internal

# See what changed
git log HEAD..origin/python-bash
git log HEAD..internal/python-bash

# Merge and resolve conflicts
git merge origin/python-bash
# or
git merge internal/python-bash

# Then push to both
sync-push
```

**Problem**: Can't access internal repo from external network

```bash
# This is expected - Booz Allen repo is behind VPN
# Only work with origin when external:
git push origin python-bash

# When back on Bedrock, sync:
sync-origin-to-internal
```

---

## Summary

Your repos are now synced! Use:
- `sync-push` to push to both at once
- `sync-pull` to check for updates from both
- `sync-status` to see current state
- `sync-origin-to-internal` / `sync-internal-to-origin` when one is ahead

Happy syncing! 🚀
