.PHONY: help install test validate lint clean run

help:
	@echo "ATOMIC CLAUDE - Python Implementation"
	@echo ""
	@echo "Available commands:"
	@echo "  make install    Install development dependencies"
	@echo "  make test       Run pytest suite"
	@echo "  make validate   Validate Python syntax"
	@echo "  make lint       Run linters (pyflakes, mypy)"
	@echo "  make clean      Remove generated files"
	@echo "  make run        Run Phase 0 (test)"

install:
	pip install -r requirements.txt
	pip install -r tests/requirements-test.txt 2>/dev/null || true

test:
	pytest tests/ -v --cov=lib --cov-report=term-missing

validate:
	@echo "Validating Python files..."
	@python scripts/validate.py

lint:
	@echo "Checking with pyflakes..."
	@pyflakes lib/*.py main.py 2>/dev/null || echo "Install pyflakes: pip install pyflakes"
	@echo "Checking with mypy..."
	@mypy lib/*.py main.py --ignore-missing-imports 2>/dev/null || echo "Install mypy: pip install mypy"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov

run:
	python main.py run 0
