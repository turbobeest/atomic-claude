# ATOMIC-CLAUDE Development Makefile

.PHONY: sync sync-to sync-from watch install test help

# Default target
help:
	@echo ""
	@echo "ATOMIC CLAUDE - Development Commands"
	@echo ""
	@echo "Sync Commands:"
	@echo "  make sync         Push changes to test-project"
	@echo "  make sync-to      Same as 'sync' (alias)"
	@echo "  make sync-from    Pull changes from test-project back"
	@echo "  make watch        Auto-sync on file changes (requires fswatch)"
	@echo ""
	@echo "Other Commands:"
	@echo "  make install      Install dashboard dependencies"
	@echo "  make test         Run a test project"
	@echo "  make clean        Clean test-project state"
	@echo ""

# Push changes to test-project (main workflow)
sync: sync-to

sync-to:
	@./scripts/sync-to-test-project.sh

# Pull changes from test-project (reverse sync)
sync-from:
	@./scripts/sync-from-test-project.sh

# Watch for changes and auto-sync (requires fswatch)
watch:
	@if command -v fswatch >/dev/null 2>&1; then \
		echo "Watching for changes... (Press Ctrl+C to stop)"; \
		fswatch -o lib/ phases/ config/ skills/ tasks-dashboard/ scripts/ main.sh | \
		while read num; do \
			echo ""; \
			echo "Change detected - syncing..."; \
			./scripts/sync-to-test-project.sh; \
		done; \
	else \
		echo "fswatch not found. Install with: brew install fswatch"; \
		exit 1; \
	fi

# Install dashboard dependencies
install:
	@cd tasks-dashboard && npm install

# Run test project
test:
	@cd /Users/jamesterbeest/dev/test-project && ./ATOMIC-CLAUDE/main.sh run 0

# Clean test-project state
clean:
	@echo "Cleaning test-project state..."
	@rm -rf /Users/jamesterbeest/dev/test-project/ATOMIC-CLAUDE/.claude
	@rm -rf /Users/jamesterbeest/dev/test-project/ATOMIC-CLAUDE/.state
	@rm -rf /Users/jamesterbeest/dev/test-project/ATOMIC-CLAUDE/.outputs
	@rm -rf /Users/jamesterbeest/dev/test-project/ATOMIC-CLAUDE/.logs
	@echo "✓ State cleaned"
