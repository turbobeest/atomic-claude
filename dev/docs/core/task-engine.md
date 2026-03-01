# Task Execution Engine

Complete guide to the Task Execution Engine for atomic-claude.

## Overview

The Task Execution Engine provides comprehensive task lifecycle management, including:
- Task state management with validated transitions
- Dependency resolution with DAG validation
- Task execution with retry logic and timeouts
- Progress reporting and error capture
- State persistence across sessions

## Architecture

```
core/task/
├── types.py          # Type definitions (Pydantic models)
├── state.py          # State machine for task transitions
├── dependencies.py   # Dependency graph (DAG)
├── validator.py      # Pre-execution validation
├── executor.py       # Main execution engine
└── __init__.py       # Public API exports
```

## Core Components

### 1. Task Types (`types.py`)

#### TaskState Enum
```python
class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
```

#### TaskDefinition
Defines task metadata and configuration:
```python
task = TaskDefinition(
    task_id="001",
    phase_id="0-setup",
    name="Setup Task",
    description="Initialize project setup",
    timeout=600,  # seconds
    dependencies=[TaskDependency(task_id="000")],
    script_path="/path/to/task001.sh",
    retryable=True,
    max_retries=3
)
```

#### TaskResult
Captures execution results:
```python
result = TaskResult(
    task_id="001",
    phase_id="0-setup",
    state=TaskState.COMPLETED,
    exit_code=0,
    output="Task completed successfully",
    duration=5.2,
    artifacts=["output.json"]
)
```

### 2. State Machine (`state.py`)

Manages task state transitions with validation.

#### Valid Transitions
```
PENDING → RUNNING → COMPLETED
       → RUNNING → FAILED
       → SKIPPED
COMPLETED → PENDING  (reset)
FAILED → PENDING     (reset)
FAILED → RUNNING     (retry)
```

#### Usage
```python
from core.task import TaskStateMachine, TaskState

state_machine = TaskStateMachine()

# Transition task to running
state_machine.mark_running("001")

# Complete task
state_machine.mark_completed("001")

# Get current state
state = state_machine.get_state("001")  # TaskState.COMPLETED

# Get history
history = state_machine.get_history("001")
for transition in history:
    print(f"{transition.from_state} → {transition.to_state}")
```

### 3. Dependency Graph (`dependencies.py`)

Manages task dependencies using a DAG (Directed Acyclic Graph).

#### Features
- Cycle detection
- Topological sorting
- Parallel task identification
- Dependency validation

#### Usage
```python
from core.task import TaskDependencyGraph, TaskDefinition

graph = TaskDependencyGraph()

# Add tasks
task1 = TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1")
task2 = TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2")
task3 = TaskDefinition(task_id="003", phase_id="0-setup", name="Task 3")

graph.add_task(task1)
graph.add_task(task2)
graph.add_task(task3)

# Define dependencies: task 3 depends on tasks 1 and 2
graph.add_dependency("003", "001")
graph.add_dependency("003", "002")

# Get execution order (grouped by level)
levels = graph.get_execution_order()
# Returns: [[task1, task2], [task3]]
# Level 0: tasks 1 and 2 can run in parallel
# Level 1: task 3 runs after 1 and 2 complete

# Check if task is ready
completed = {"001"}
is_ready = graph.is_ready("002", completed)  # True (no dependencies)
is_ready = graph.is_ready("003", completed)  # False (002 not complete)
```

### 4. Task Validator (`validator.py`)

Validates tasks before execution.

#### Validation Checks
- Task definition completeness
- Dependency satisfaction
- Resource availability (disk space, memory)
- State system accessibility
- Script/function existence and validity

#### Usage
```python
from core.task import TaskValidator

validator = TaskValidator(
    dependency_graph=graph,
    state_manager=state_manager,
    config=config
)

# Validate task
result = validator.validate_task(task_def, completed_tasks={"001"})

if result.valid:
    print("Task is ready to execute")
else:
    print("Validation errors:")
    for error in result.errors:
        print(f"  - {error}")

# Validate retry
retry_result = validator.validate_retry(task_def, current_retry_count=1)
```

### 5. Task Executor (`executor.py`)

Main execution engine with retry, timeout, and progress tracking.

#### Features
- Execute tasks with timeout enforcement
- Retry failed tasks with exponential backoff
- Execute phases with dependency resolution
- Track progress and report status
- Capture output and errors
- Integrate with StateManager for persistence

#### Usage

##### Execute Single Task
```python
from core.task import TaskExecutor, TaskDefinition

executor = TaskExecutor(
    state_manager=state_manager,
    config=config
)

def my_task():
    # Task logic
    return True

task = TaskDefinition(
    task_id="001",
    phase_id="0-setup",
    name="My Task",
    function=my_task,
    timeout=300,
    retryable=True,
    max_retries=3
)

result = executor.execute_task(task)

if result.success:
    print(f"Task completed in {result.duration}s")
else:
    print(f"Task failed: {result.error}")
```

##### Execute Phase
```python
tasks = [
    TaskDefinition(task_id="001", phase_id="0-setup", name="Task 1", function=task1_func),
    TaskDefinition(task_id="002", phase_id="0-setup", name="Task 2", function=task2_func),
    TaskDefinition(task_id="003", phase_id="0-setup", name="Task 3", function=task3_func),
]

results = executor.execute_phase("0-setup", tasks)

for result in results:
    status = "✓" if result.success else "✗"
    print(f"{status} Task {result.task_id}: {result.state}")
```

##### Get Progress
```python
progress = executor.get_progress("0-setup")
print(f"Phase: {progress['phase_id']}")
print(f"Progress: {progress['completion_percentage']:.1f}%")
print(f"Completed: {progress['completed_tasks']}/{progress['total_tasks']}")
print(f"Elapsed: {progress['elapsed_time']:.1f}s")
print(f"Estimated remaining: {progress['estimated_remaining']:.1f}s")
```

## Task Execution Flow

```
1. Validate Task
   ├─> Check definition
   ├─> Check dependencies
   ├─> Check resources
   └─> Check executable exists

2. Transition to RUNNING
   └─> Update state machine

3. Execute Task
   ├─> Set timeout
   ├─> Run bash script OR Python function
   ├─> Capture output/errors
   └─> Measure duration

4. Handle Result
   ├─> SUCCESS: Transition to COMPLETED
   │   └─> Persist to StateManager
   └─> FAILURE: Check if retryable
       ├─> YES: Retry with exponential backoff
       └─> NO: Transition to FAILED
           └─> Persist to StateManager
```

## Retry Logic

Tasks can be automatically retried on failure:

### Retry Configuration
```python
task = TaskDefinition(
    task_id="001",
    phase_id="0-setup",
    name="Flaky Task",
    function=flaky_func,
    retryable=True,
    max_retries=3  # Try up to 3 times after initial failure
)
```

### Exponential Backoff
```
Attempt 1: Execute immediately
Attempt 2: Wait 2^1 = 2 seconds
Attempt 3: Wait 2^2 = 4 seconds
Attempt 4: Wait 2^3 = 8 seconds
```

### Retry Conditions
- Retry on: Timeout, transient errors
- Don't retry on: Validation errors, critical failures (retryable=False)

## Timeout Enforcement

Tasks are automatically killed if they exceed their timeout:

```python
task = TaskDefinition(
    task_id="001",
    phase_id="0-setup",
    name="Long Task",
    function=long_running_func,
    timeout=300  # 5 minutes
)

result = executor.execute_task(task)

if result.exit_code == 124:
    print("Task timed out")
```

## Parallel Execution

Tasks with no dependencies can be executed in parallel:

```python
# Define task dependencies
graph.add_dependency("003", "001")
graph.add_dependency("003", "002")

# Get execution levels
levels = graph.get_execution_order()

# Level 0: [task1, task2] - can run in parallel
# Level 1: [task3] - runs after level 0 completes
```

Note: Parallel execution is identified but not yet implemented in TaskExecutor. Tasks currently run sequentially within each level.

## State Persistence

Task state is automatically persisted to StateManager:

```python
# Task completion is persisted
executor.execute_task(task)

# Check if task is complete (in new session)
if state_manager.is_task_complete("0-setup", "001"):
    print("Task already completed, skipping")
```

## Error Handling

### Validation Errors
```python
result = executor.execute_task(task)

if result.failed and "validation" in result.error.lower():
    print("Pre-execution validation failed")
    print(result.error)
```

### Execution Errors
```python
result = executor.execute_task(task)

if result.failed:
    print(f"Task failed with exit code {result.exit_code}")
    print(f"Error: {result.error}")
    if result.retry_count > 0:
        print(f"Failed after {result.retry_count} retries")
```

### Critical Failures
```python
# Non-retryable task that fails stops phase execution
task = TaskDefinition(
    task_id="002",
    phase_id="0-setup",
    name="Critical Task",
    function=critical_func,
    retryable=False
)

results = executor.execute_phase("0-setup", tasks)
# Execution stops after critical task fails
```

## Best Practices

### 1. Define Clear Dependencies
```python
# Good: Explicit dependencies
task_setup = TaskDefinition(task_id="001", ...)
task_validate = TaskDefinition(
    task_id="002",
    dependencies=[TaskDependency(task_id="001")]
)
task_execute = TaskDefinition(
    task_id="003",
    dependencies=[TaskDependency(task_id="002")]
)
```

### 2. Set Appropriate Timeouts
```python
# Short tasks: 60-300 seconds
# LLM tasks: 300-600 seconds
# Heavy processing: 600-1800 seconds
task = TaskDefinition(
    task_id="001",
    timeout=300,  # 5 minutes
    ...
)
```

### 3. Use Retries for Transient Failures
```python
# Enable retries for flaky operations
task = TaskDefinition(
    task_id="001",
    retryable=True,
    max_retries=3,
    ...
)

# Disable retries for validation/setup tasks
task = TaskDefinition(
    task_id="002",
    retryable=False,  # Fail fast
    ...
)
```

### 4. Validate Before Executing
```python
# Always validate first
validation = validator.validate_task(task)
if not validation.valid:
    print(f"Cannot execute: {validation.errors}")
    return

result = executor.execute_task(task)
```

### 5. Track Progress
```python
# Monitor long-running phases
import time
import threading

def monitor_progress():
    while True:
        progress = executor.get_progress()
        print(f"Progress: {progress['completion_percentage']:.1f}%")
        time.sleep(5)

monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
monitor_thread.start()

results = executor.execute_phase("0-setup", tasks)
```

## Performance Targets

- **State transition:** < 2ms
- **Dependency resolution:** < 5ms
- **Task scheduling:** < 10ms
- **Executor overhead:** < 100ms per task

## Testing

Comprehensive test suite included:

```bash
# Unit tests (89 tests)
pytest tests/unit/test_task_types.py -v
pytest tests/unit/test_task_state.py -v
pytest tests/unit/test_task_dependencies.py -v
pytest tests/unit/test_task_validator.py -v
pytest tests/unit/test_task_executor.py -v

# Integration tests (15 tests)
pytest tests/integration/test_task_integration.py -v

# All task tests
pytest tests/unit/test_task_*.py tests/integration/test_task_*.py -v
```

## API Reference

See individual module documentation:
- [Task Dependencies](task-dependencies.md)
- [Task Execution](task-execution.md)
