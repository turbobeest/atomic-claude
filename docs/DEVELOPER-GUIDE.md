# Atomic Claude 2.0 - Developer Guide

Complete guide for developers working on atomic-claude or extending it with new phases and tasks.

Version: 2.0
Last Updated: 2026-02-07

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Project Structure](#project-structure)
3. [Development Setup](#development-setup)
4. [Adding New Phases](#adding-new-phases)
5. [Adding New Tasks](#adding-new-tasks)
6. [Testing Guidelines](#testing-guidelines)
7. [Code Style & Patterns](#code-style--patterns)
8. [Contributing Guidelines](#contributing-guidelines)
9. [Debugging](#debugging)
10. [Common Issues](#common-issues)

---

## Getting Started

### Prerequisites

- Python 3.10+
- Bash 4.0+ (for task scripts)
- Git
- Claude CLI (optional, for LLM tasks)
- Ollama (optional, for local LLM)

### Quick Setup

```bash
# Clone repository
git clone https://github.com/yourusername/atomic-claude.git
cd atomic-claude

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ATOMIC_TOOL_DEVELOPMENT="true"  # Disable directory purity checks

# Run tests
python -m pytest tests/

# Try a phase
python main.py run 0
```

---

## Project Structure

```
atomic-claude/
├── main.py                  # Entry point
│
├── core/                    # Core modules (DO NOT MOVE)
│   ├── state.py            # State management
│   ├── config.py           # Configuration
│   ├── subprocess_runner.py # Python ↔ Bash bridge
│   ├── llm.py              # LLM invocation
│   ├── providers.py        # Provider management
│   ├── memory.py           # Memory system
│   └── ui.py               # UI utilities
│
├── phases/                  # Phase implementations
│   ├── phase00/            # Phase 0: Setup
│   │   ├── __init__.py
│   │   ├── orchestrator00.py    # Python orchestrator
│   │   ├── task001.sh           # Bash task script (legacy)
│   │   └── tasks/               # Python task modules (new)
│   │       ├── __init__.py
│   │       ├── task_001.py
│   │       └── ...
│   └── ...                 # Phases 01-09
│
├── orchestration/           # Orchestration utilities
│   ├── backtrack.py        # Phase backtracking
│   ├── pre_task_validation.py  # Directory purity checks
│   ├── git_manager.py      # Git commit management
│   └── dashboard_sync.py   # Dashboard state sync
│
├── lib/                     # Bash libraries
│   ├── atomic.sh           # Core LLM invocation
│   ├── phase.sh            # Phase lifecycle
│   └── memory.sh           # Memory system (47KB)
│
├── config/                  # Configuration files
│   └── models.json         # LLM provider & model config
│
├── agents/                  # Agent repository (copied)
├── audits/                  # Audit repository (copied)
│
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── fixtures/           # Test fixtures
│
├── docs/                    # Documentation
│   ├── API-REFERENCE.md    # API documentation
│   ├── DEVELOPER-GUIDE.md  # This file
│   └── USER-GUIDE.md       # User documentation
│
├── .outputs/                # Phase outputs (git-ignored)
├── .state/                  # Task state & memory (git-ignored)
└── .logs/                   # Logs (git-ignored)
```

### File Organization Rules

**✅ Allowed in Root**:
- `CLAUDE.md`, `README.md`, `main.py`, `.env`, `.gitignore`
- Standard dot files (`.flake8`, `.editorconfig`, etc.)

**❌ NOT Allowed in Root**:
- Status documents → `docs/`
- Test documentation → `tests/`
- Implementation notes → `docs/`
- Any markdown except README.md and CLAUDE.md → appropriate subdirectory

**Forcing Function**: The `pre_task_validation` module enforces this automatically before each task.

---

## Development Setup

### 1. Environment Variables

Create a `.env` file:

```bash
# Core paths
ATOMIC_ROOT=/path/to/atomic-claude
ATOMIC_OUTPUT_DIR=/path/to/atomic-claude/.outputs
ATOMIC_STATE_DIR=/path/to/atomic-claude/.state
ATOMIC_LOG_DIR=/path/to/atomic-claude/.logs

# LLM configuration
CLAUDE_PROVIDER=max                     # max, api, ollama, bedrock
CLAUDE_MODEL=sonnet                     # opus, sonnet, haiku
CLAUDE_MAX_TURNS=30
CLAUDE_TIMEOUT=1200

# Ollama (if using)
CLAUDE_OLLAMA_HOST=http://localhost:11434
CLAUDE_OLLAMA_CONTEXT=65536

# API keys (if using)
ANTHROPIC_API_KEY=sk-ant-...           # For Anthropic API
OPENAI_API_KEY=sk-...                  # For OpenAI (optional)

# AWS Bedrock (if using)
AWS_REGION=us-gov-west-1
AWS_PROFILE=default
CLAUDE_CODE_USE_BEDROCK=1

# Tool development mode (IMPORTANT)
ATOMIC_TOOL_DEVELOPMENT=true           # Disables directory purity checks

# Dashboard
ATOMIC_TASKS_PORT=5173
ATOMIC_AGENTS_PORT=5174
ATOMIC_AUDITS_PORT=5175

# Network mode
ATOMIC_NETWORK_MODE=cui                # cui, internet, restricted
```

### 2. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt

# LLM dependencies (optional)
pip install -r requirements-llm.txt
```

### 3. Verify Setup

```bash
# Run preflight checks
python -c "from core.state import StateManager; print('✓ State module OK')"
python -c "from core.config import Config; print('✓ Config module OK')"
python -c "from core.llm import atomic_invoke; print('✓ LLM module OK')"

# Run unit tests
python -m pytest tests/unit/ -v

# Try a simple phase
python main.py status
```

---

## Adding New Phases

### Phase Structure

Each phase consists of:
1. **Orchestrator** (`orchestratorNN.py`) - Python flow control
2. **Tasks** (bash scripts or Python modules) - Task implementations
3. **Outputs** (`.outputs/N-phase-name/`) - Task artifacts

### Step-by-Step Guide

#### 1. Create Phase Directory

```bash
mkdir -p phases/phase10
touch phases/phase10/__init__.py
```

#### 2. Create Orchestrator

Create `phases/phase10/orchestrator10.py`:

```python
#!/usr/bin/env python3
"""
Phase 10 Orchestrator

Description: Brief description of what this phase does.

Tasks:
  1001 - Task description
  1002 - Task description
  ...
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Ensure atomic-claude root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.state import StateManager
from core.ui import phase_header, phase_complete
from orchestration.pre_task_validation import validate_directory_pristine

# Import task modules
from phases.phase10.tasks import task_1001, task_1002


def run_phase(resume_at: str = None) -> bool:
    """
    Execute Phase 10: Phase Name

    Args:
        resume_at: Optional task ID to resume from

    Returns:
        bool: True if phase completed successfully
    """
    phase_header("Phase 10: Phase Name")

    state = StateManager()
    phase_id = "10-phase-name"

    # Task list in execution order
    tasks = [
        ("1001", "Task 1 description", task_1001_wrapper),
        ("1002", "Task 2 description", task_1002_wrapper),
    ]

    # Determine starting point
    start_index = 0
    if resume_at:
        for i, (task_id, _, _) in enumerate(tasks):
            if task_id == resume_at:
                start_index = i
                break

    # Execute tasks
    for task_id, task_name, task_func in tasks[start_index:]:
        # Skip if already completed
        if state.is_task_complete(phase_id, task_id):
            print(f"✓ Task {task_id} already complete, skipping")
            continue

        # PRE-TASK VALIDATION: Ensure directory is pristine (BLOCKER)
        if not validate_directory_pristine(phase_id, task_id):
            print(f"\n🛑 Cannot proceed to Task {task_id} - fix violations first")
            return False

        # Run task
        print(f"\n⚡ Running Task {task_id}: {task_name}")

        try:
            success = task_func()
            if not success:
                print(f"\n❌ Task {task_id} failed")
                state.mark_task_failed(phase_id, task_id, task_name)
                return False

            state.mark_task_complete(phase_id, task_id, task_name)

        except Exception as e:
            print(f"\n❌ Task {task_id} error: {e}")
            state.mark_task_failed(phase_id, task_id, task_name, str(e))
            return False

    phase_complete("Phase 10: Phase Name")

    # Create closeout file
    create_closeout(phase_id, tasks)

    return True


# Task wrapper functions
def task_1001_wrapper() -> bool:
    """Execute task 1001."""
    return task_1001()

def task_1002_wrapper() -> bool:
    """Execute task 1002."""
    return task_1002()


def create_closeout(phase_id: str, tasks: list):
    """Create closeout.json file for phase completion."""
    from pathlib import Path
    import json

    outputs_dir = Path(".outputs") / phase_id
    outputs_dir.mkdir(parents=True, exist_ok=True)

    closeout = {
        "phase": phase_id,
        "phase_num": 10,
        "completed_at": datetime.now().isoformat(),
        "tasks_completed": [task_id for task_id, _, _ in tasks],
        "summary": f"Phase 10 ({phase_id}) completed successfully."
    }

    closeout_path = outputs_dir / "closeout.json"
    with open(closeout_path, "w") as f:
        json.dump(closeout, f, indent=2)

    print(f"\n✅ Closeout file created: {closeout_path}")


if __name__ == "__main__":
    success = run_phase()
    sys.exit(0 if success else 1)
```

#### 3. Create Task Modules

Create `phases/phase10/tasks/__init__.py`:

```python
"""Phase 10 tasks."""

from .task_1001 import task_1001
from .task_1002 import task_1002

__all__ = ['task_1001', 'task_1002']
```

Create `phases/phase10/tasks/task_1001.py`:

```python
"""
Task 1001: Task Name

Description: What this task does.
"""

import os
from pathlib import Path
from core.llm import atomic_invoke, atomic_step, atomic_success, atomic_error
from core.config import Config


def task_1001() -> bool:
    """
    Execute Task 1001: Task Name.

    Returns:
        bool: True if successful
    """
    atomic_step("Task 1001: Task Name")

    # Get configuration
    config = Config()
    project_name = config.get_project_name()

    # Build prompt
    prompt = f"""
    Task-specific prompt here.

    Project: {project_name}
    """

    # Output location
    output_dir = Path(".outputs/10-phase-name")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "task1001-output.json"

    # Invoke LLM
    success = atomic_invoke(
        prompt_source=prompt,
        output_file=str(output_file),
        description="Task 1001 description",
        model="sonnet",
        format_type="json",
        timeout=600
    )

    if not success:
        atomic_error("Task 1001 failed")
        return False

    # Validate output
    if not output_file.exists():
        atomic_error("Output file not created")
        return False

    atomic_success("Task 1001 completed")
    return True
```

#### 4. Update Main Entry Point

Edit `main.py` to add the new phase:

```python
PHASE_NAMES = {
    0: "Setup",
    1: "Discovery",
    2: "PRD",
    3: "Tasking",
    4: "Specification",
    5: "Implementation",
    6: "Code Review",
    7: "Integration",
    8: "Deployment Prep",
    9: "Release",
    10: "Your New Phase"  # Add this
}
```

#### 5. Test the Phase

```bash
# Test orchestrator
python phases/phase10/orchestrator10.py

# Test via main.py
python main.py run 10

# Test resumption
python main.py run 10 --resume-at=1002
```

---

## Adding New Tasks

### Task Types

1. **Python Tasks** - Pure Python logic (recommended for new tasks)
2. **Bash Tasks** - Shell scripts (legacy, being phased out)
3. **Hybrid Tasks** - Python orchestration with bash execution

### Python Task Pattern

Create `phases/phaseNN/tasks/task_NNN.py`:

```python
"""
Task NNN: Task Name

Description: Detailed description of what this task does.

Inputs:
  - Input file or configuration

Outputs:
  - .outputs/N-phase/task-output.json
  - Other artifacts

Dependencies:
  - Task NNN-1 must be complete
"""

import os
import json
from pathlib import Path
from typing import Dict, Any

from core.llm import (
    atomic_invoke,
    atomic_step,
    atomic_substep,
    atomic_success,
    atomic_error,
    atomic_validate_files
)
from core.config import Config
from core.state import StateManager


def task_NNN(
    atomic_root: Path = None,
    output_dir: Path = None,
    uat_mode: bool = False
) -> bool:
    """
    Execute Task NNN: Task Name.

    Args:
        atomic_root: Atomic root directory (defaults to current)
        output_dir: Output directory (defaults to .outputs/N-phase)
        uat_mode: UAT mode (auto-approve prompts)

    Returns:
        bool: True if successful
    """
    atomic_step("Task NNN: Task Name")

    # Setup
    atomic_root = atomic_root or Path.cwd()
    output_dir = output_dir or atomic_root / ".outputs" / "N-phase"
    output_dir.mkdir(parents=True, exist_ok=True)

    config = Config()
    state = StateManager()

    # Validate prerequisites
    phase_id = "N-phase"
    if not state.is_task_complete(phase_id, "NNN-1"):
        atomic_error("Prerequisite task NNN-1 not complete")
        return False

    # Gather inputs
    input_file = output_dir / "previous-task-output.json"
    if not atomic_validate_files(str(input_file)):
        return False

    with open(input_file) as f:
        input_data = json.load(f)

    # Build prompt
    atomic_substep("Building prompt")
    prompt = f"""
    Task-specific instructions here.

    Context:
    - Project: {config.get_project_name()}
    - Previous output: {input_data.get('summary')}

    Requirements:
    - Requirement 1
    - Requirement 2
    """

    # Execute LLM task
    atomic_substep("Invoking LLM")
    output_file = output_dir / "taskNNN-output.json"

    success = atomic_invoke(
        prompt_source=prompt,
        output_file=str(output_file),
        description="Task NNN",
        model="sonnet",
        format_type="json",
        timeout=600,
        role="primary"
    )

    if not success:
        atomic_error("LLM invocation failed")
        return False

    # Validate output
    atomic_substep("Validating output")
    try:
        with open(output_file) as f:
            result = json.load(f)

        # Task-specific validation
        if not result.get("required_field"):
            atomic_error("Output missing required field")
            return False

    except json.JSONDecodeError:
        atomic_error("Invalid JSON output")
        return False

    # Success
    atomic_success("Task NNN completed")
    return True


# Allow standalone execution
if __name__ == "__main__":
    import sys
    success = task_NNN()
    sys.exit(0 if success else 1)
```

### Bash Task Pattern (Legacy)

Create `phases/phaseNN/taskNNN.sh`:

```bash
#!/usr/bin/env bash
#
# Task NNN: Task Name
# Description of what this task does
#

# Source required libraries
set -euo pipefail
LIB_DIR="${ATOMIC_LIB_DIR:-$(dirname "$0")/../../lib}"
source "$LIB_DIR/atomic.sh"

task_NNN_function_name() {
    atomic_step "Task Name"

    # Gather context
    local input_file="${ATOMIC_OUTPUT_DIR}/N-phase/previous-output.json"
    if [[ ! -f "$input_file" ]]; then
        atomic_error "Input file not found: $input_file"
        return 1
    fi

    local context=$(cat "$input_file")

    # Build prompt
    local prompt_file=$(atomic_mktemp)
    cat > "$prompt_file" << EOF
<context>
$context
</context>

Your task is to...
EOF

    # Invoke LLM
    local output_file="${ATOMIC_OUTPUT_DIR}/N-phase/taskNNN-output.json"
    atomic_invoke "$prompt_file" "$output_file" "Task NNN" --model=sonnet --format=json

    # Validate output
    if [[ ! -f "$output_file" ]]; then
        atomic_error "Task failed - no output"
        return 1
    fi

    # Extract and validate JSON
    if ! jq empty "$output_file" 2>/dev/null; then
        atomic_error "Invalid JSON output"
        return 1
    fi

    atomic_success "Task completed"
    return 0
}

# Execute if run directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    task_NNN_function_name
fi
```

**CRITICAL: Arithmetic with set -e**

When using `set -e`, bash arithmetic returns the old value, causing exit when incrementing from 0:

```bash
# ❌ WRONG - fails with set -e when counter starts at 0
((_COUNTER++))

# ✅ CORRECT - add || true to prevent exit
((_COUNTER++)) || true
```

### Task Registration

1. Add task to orchestrator's task list
2. Add task to `tasks/__init__.py` exports
3. Create task wrapper function in orchestrator
4. Update phase closeout to include new task

---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_state.py
│   ├── test_config.py
│   └── ...
├── integration/             # Integration tests (slower)
│   ├── test_phase00.py
│   └── ...
└── fixtures/                # Test data
    ├── uat_setup.md
    └── reference/
```

### Writing Unit Tests

Create `tests/unit/test_new_module.py`:

```python
"""Unit tests for new module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from tempfile import TemporaryDirectory

from core.new_module import NewClass


class TestNewClass:
    """Test NewClass functionality."""

    def test_initialization(self):
        """Test NewClass initialization."""
        obj = NewClass()
        assert obj is not None

    def test_method_success(self):
        """Test method with successful outcome."""
        obj = NewClass()
        result = obj.method("input")
        assert result is True

    def test_method_failure(self):
        """Test method with failure."""
        obj = NewClass()
        with pytest.raises(ValueError):
            obj.method(None)

    def test_with_temp_directory(self):
        """Test with temporary directory."""
        with TemporaryDirectory() as tmpdir:
            obj = NewClass(root_dir=Path(tmpdir))
            result = obj.method()
            assert result is True

    @patch('core.new_module.external_dependency')
    def test_with_mock(self, mock_dep):
        """Test with mocked dependency."""
        mock_dep.return_value = "mocked"
        obj = NewClass()
        result = obj.method()
        assert result == "mocked"
```

### Writing Integration Tests

Create `tests/integration/test_phase10.py`:

```python
"""Integration tests for Phase 10."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from phases.phase10.orchestrator10 import run_phase
from core.state import StateManager


@pytest.fixture
def test_environment():
    """Create test environment."""
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Setup test directories
        (tmpdir / ".state").mkdir()
        (tmpdir / ".outputs").mkdir()
        (tmpdir / ".logs").mkdir()

        # Set environment variables
        import os
        os.environ["ATOMIC_ROOT"] = str(tmpdir)
        os.environ["ATOMIC_STATE_DIR"] = str(tmpdir / ".state")
        os.environ["ATOMIC_OUTPUT_DIR"] = str(tmpdir / ".outputs")

        yield tmpdir


def test_phase10_execution(test_environment):
    """Test Phase 10 complete execution."""
    # Run phase
    success = run_phase()
    assert success is True

    # Verify state
    state = StateManager(state_dir=test_environment / ".state")
    assert state.is_task_complete("10-phase", "1001")
    assert state.is_task_complete("10-phase", "1002")

    # Verify outputs
    output_dir = test_environment / ".outputs" / "10-phase"
    assert (output_dir / "closeout.json").exists()
```

### Running Tests

```bash
# All tests
python -m pytest tests/

# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only
python -m pytest tests/integration/ -v

# Specific test file
python -m pytest tests/unit/test_state.py -v

# Specific test
python -m pytest tests/unit/test_state.py::TestStateManager::test_mark_complete -v

# With coverage
python -m pytest tests/ --cov=core --cov=phases --cov-report=html

# Watch mode (requires pytest-watch)
ptw tests/
```

### Test Best Practices

1. **Isolate tests** - Use fixtures and mocks
2. **Test edge cases** - Empty inputs, None values, errors
3. **Test state changes** - Verify before and after
4. **Clean up** - Use TemporaryDirectory for file tests
5. **Mock external dependencies** - Don't call real APIs
6. **Fast tests** - Unit tests should run in milliseconds
7. **Descriptive names** - `test_method_with_invalid_input_raises_error`

---

## Code Style & Patterns

### Python Style

Follow PEP 8 with these additions:

```python
# Imports
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from core.state import StateManager  # Absolute imports
from core.config import Config


# Functions
def function_name(param: str, optional: int = 0) -> bool:
    """
    Short description.

    Longer description if needed.

    Args:
        param: Parameter description
        optional: Optional parameter (defaults to 0)

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If param is invalid
    """
    pass


# Classes
class ClassName:
    """Class description."""

    def __init__(self, param: str):
        """Initialize class."""
        self.param = param

    def method(self) -> str:
        """Method description."""
        return self.param


# Type hints
def process(data: Dict[str, Any]) -> List[str]:
    """Process data and return list."""
    return list(data.keys())
```

### Bash Style

```bash
#!/usr/bin/env bash
#
# Script description
#

# Always use strict mode
set -euo pipefail

# Constants in UPPER_CASE
readonly SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
readonly LIB_DIR="${ATOMIC_LIB_DIR:-$SCRIPT_DIR/../../lib}"

# Source libraries
source "$LIB_DIR/atomic.sh"

# Functions in snake_case
function_name() {
    local param="$1"
    local output_file="$2"

    # Use atomic_ functions for output
    atomic_step "Step description"
    atomic_substep "Sub-step"

    # Always check commands
    if ! command -v jq &>/dev/null; then
        atomic_error "jq not found"
        return 1
    fi

    # Use local variables
    local result=$(do_something)

    atomic_success "Done"
    return 0
}

# Arithmetic with || true (CRITICAL)
((_COUNTER++)) || true

# Main execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    function_name "$@"
fi
```

### Naming Conventions

- **Files**: `snake_case.py`, `taskNNN.sh`
- **Classes**: `PascalCase`
- **Functions**: `snake_case()`
- **Variables**: `snake_case`
- **Constants**: `UPPER_CASE`
- **Private**: `_leading_underscore()`

### Common Patterns

#### Pattern 1: Task Execution with State Tracking

```python
from core.state import StateManager

def execute_task(phase_id: str, task_id: str, task_name: str):
    """Execute task with state tracking."""
    state = StateManager()

    # Check if complete
    if state.is_task_complete(phase_id, task_id):
        return True

    try:
        # Execute
        result = do_work()

        # Mark complete
        state.mark_task_complete(phase_id, task_id, task_name)
        return True
    except Exception as e:
        # Mark failed
        state.mark_task_failed(phase_id, task_id, task_name, str(e))
        return False
```

#### Pattern 2: Configuration Access

```python
from core.config import Config

def get_configuration():
    """Get configuration with defaults."""
    config = Config()

    return {
        "project_name": config.get("project.name", "unknown"),
        "network_mode": config.get("sandbox.network_mode", "cui"),
        "provider": config.get_provider("primary"),
        "model": config.get_model("primary")
    }
```

#### Pattern 3: LLM Invocation

```python
from core.llm import atomic_invoke, atomic_step, atomic_success

def invoke_llm_task():
    """Invoke LLM with error handling."""
    atomic_step("Invoking LLM")

    success = atomic_invoke(
        prompt_source="prompt.md",
        output_file="output.json",
        description="Task description",
        model="sonnet",
        timeout=600
    )

    if success:
        atomic_success("LLM task completed")

    return success
```

---

## Contributing Guidelines

### Before You Start

1. **Read CLAUDE.md** - Understand the architecture
2. **Check existing issues** - Avoid duplicates
3. **Discuss major changes** - Open an issue first

### Contribution Process

1. **Fork & Branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make Changes**
   - Follow code style
   - Add tests
   - Update documentation

3. **Test**
   ```bash
   python -m pytest tests/ -v
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

5. **Push & PR**
   ```bash
   git push origin feature/your-feature
   # Create PR on GitHub
   ```

### Commit Messages

```
type: Short description (50 chars or less)

Longer description if needed. Explain what and why, not how.

- Bullet points for details
- Reference issues: #123

Co-Authored-By: Name <email>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

### PR Guidelines

- **Title**: Clear, descriptive
- **Description**: What, why, how
- **Tests**: All tests pass
- **Documentation**: Updated if needed
- **No breaking changes** without discussion

---

## Debugging

### Debug Mode

Enable verbose logging:

```bash
export ATOMIC_DEBUG=true
export ATOMIC_VERBOSE=true
```

### State Inspection

```python
from core.state import StateManager

state = StateManager()

# View all state
print(json.dumps(state._state, indent=2))

# Check specific task
phase_id = "2-prd"
task_id = "205"
print(f"Task {task_id} status: {state.get_task_status(phase_id, task_id)}")

# View phase tasks
tasks = state.get_phase_tasks(phase_id)
for tid, task_data in tasks.items():
    print(f"  {tid}: {task_data['status']}")
```

### Log Files

```bash
# View logs
tail -f .logs/atomic.log

# View task output
cat .outputs/2-prd/task205-output.json

# View task errors
cat .outputs/2-prd/task205-output.json.err
```

### Common Issues

#### Issue: Task marked complete but didn't run

**Cause**: State file corrupted or stale

**Fix**:
```bash
# View state
cat .state/task-state.json

# Reset task
python -c "
from core.state import StateManager
state = StateManager()
state._state['phases']['2-prd']['tasks'].pop('205', None)
state.save_state()
"

# Or reset entire phase
python main.py backtrack 2
```

#### Issue: Directory purity violation

**Cause**: Project files in atomic-claude directory

**Fix**:
```bash
# View violations
python orchestration/pre_task_validation.py

# Auto-fix
python orchestration/pre_task_validation.py cleanup

# Or manually move files
```

#### Issue: LLM timeout

**Cause**: Task taking too long

**Fix**:
```python
# Increase timeout
atomic_invoke(
    ...,
    timeout=3600  # 1 hour
)
```

#### Issue: Import errors

**Cause**: Python path not set correctly

**Fix**:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

---

## Common Issues

### Issue: "Module not found"

**Solution**: Ensure atomic-claude root is in Python path

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

### Issue: "State file not found"

**Solution**: Initialize state directory

```bash
mkdir -p .state .outputs .logs
python -c "from core.state import StateManager; StateManager()"
```

### Issue: "Task already complete but needs to run again"

**Solution**: Clear task state

```bash
python main.py backtrack 2 205  # Reset to task 205
```

### Issue: "Directory purity violation"

**Solution**: Enable tool development mode or fix violations

```bash
export ATOMIC_TOOL_DEVELOPMENT=true  # Disable checks
# OR
python orchestration/pre_task_validation.py cleanup  # Auto-fix
```

---

## Resources

- [API Reference](API-REFERENCE.md) - Complete API documentation
- [User Guide](USER-GUIDE.md) - User documentation
- [CLAUDE.md](../CLAUDE.md) - Guidance for Claude Code
- [GitHub Issues](https://github.com/yourusername/atomic-claude/issues) - Bug reports & feature requests

---

## Questions?

When working on atomic-claude:
1. **Read CLAUDE.md** - Architecture guidance
2. **Check existing code** - Follow established patterns
3. **Write tests** - Ensure quality
4. **Update docs** - Keep documentation current
5. **Ask questions** - Open an issue if stuck

Happy coding!
