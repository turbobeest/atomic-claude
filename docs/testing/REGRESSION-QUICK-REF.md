# Regression Tests - Quick Reference

## One-Line Run

```bash
./test/run-regression-tests.sh
```

## What It Tests

| Pattern | What | Expected |
|---------|------|----------|
| #1 | Arithmetic without `\|\| true` | 0 issues |
| #2 | Bash syntax errors | 0 errors |
| #3 | Missing closeout files | All orchestrators create them |
| #4 | Missing library sourcing | All tasks source atomic.sh |
| #5 | Missing execution blocks | All tasks have BASH_SOURCE guard |
| #6 | UAT bypasses | Interactive tasks have UAT mode |
| #8 | Interactive prompts | No UAT hanging |
| #9 | Dashboard port | Port 5174 everywhere |
| #10 | Documentation | Complete with valid links |

## Pass Criteria

- ✅ **PASS** - No issues found
- ❌ **FAIL** - Issues detected, must fix
- ⚠️ **WARN** - Minor issues, review later

## Reports

```bash
# Latest JSON report
cat test/reports/regression-*.json | tail -1 | jq .

# Latest Markdown report
cat test/reports/regression-*.md | tail -1 | less
```

## When to Run

- ✅ Before committing new phases
- ✅ After refactoring bash scripts
- ✅ Before merging PRs
- ✅ In CI/CD pipeline
- ✅ Weekly health checks

## Speed

- **5-15 seconds** - Full suite
- **No LLM calls** - Pure static analysis
- **No tokens** - Free to run

## Fix Common Issues

### Arithmetic without || true
```bash
# Find issues
grep -rn '((' phases/*/task*.sh | grep -v '|| true'

# Quick fix
sed -i.bak 's/((i++))/((i++)) || true/g' phases/*/task*.sh
```

### Missing library sourcing
```bash
# Check task
grep -q "source.*atomic.sh" phases/phase03/task301.sh || echo "Missing"

# Add to task
cat >> phases/phase03/task301.sh << 'EOF'
LIB_DIR="${ATOMIC_LIB_DIR:-$(dirname "$0")/../../lib}"
source "$LIB_DIR/atomic.sh"
EOF
```

### Missing execution block
```bash
# Check task
grep -q 'BASH_SOURCE' phases/phase03/task301.sh || echo "Missing"

# Add to task
cat >> phases/phase03/task301.sh << 'EOF'
# Execute if run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    task_301_entry_initialization
fi
EOF
```

### Missing UAT bypass
```bash
# Add to interactive task
cat > temp.sh << 'EOF'
task_105_opening_dialogue() {
    # UAT Mode bypass
    if [[ "${ATOMIC_UAT_MODE:-false}" == "true" ]]; then
        echo "UAT Mode: Skipping dialogue"
        # Create minimal output
        echo '{}' > "$output_file"
        return 0
    fi

    # ... rest of task ...
}
EOF
```

## Related Docs

- `test/REGRESSION-TEST-GUIDE.md` - Full guide
- `test/REGRESSION-IMPLEMENTATION-SUMMARY.md` - Tech details
- `docs/BUG-PATTERNS.md` - All bug patterns

---

**Updated:** 2026-02-04
