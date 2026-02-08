# Task Execution Engine - Usage Examples

Practical examples demonstrating the Task Execution Engine.

## Example 1: Simple Task Execution

```python
from core.task import TaskExecutor, TaskDefinition

def validate_config():
    """Validate configuration file exists."""
    config_path = Path(".atomic/config.json")
    if config_path.exists():
        print("Configuration valid")
        return True
    print("Configuration missing")
    return False

# Create task definition
task = TaskDefinition(
    task_id="001",
    phase_id="0-setup",
    name="Validate Configuration",
    function=validate_config,
    timeout=60
)

# Execute task
executor = TaskExecutor()
result = executor.execute_task(task)

if result.success:
    print(f"✓ Task completed in {result.duration:.2f}s")
else:
    print(f"✗ Task failed: {result.error}")
```

## Example 2: Phase Execution with Dependencies

```python
from core.task import (
    TaskExecutor,
    TaskDefinition,
    TaskDependencyGraph,
    TaskDependency
)

def setup_dirs():
    """Create project directories."""
    Path(".outputs").mkdir(exist_ok=True)
    Path(".state").mkdir(exist_ok=True)
    return True

def load_config():
    """Load configuration."""
    # Depends on dirs existing
    config = json.load(open(".outputs/config.json"))
    return True

def validate_env():
    """Validate environment."""
    # Depends on config being loaded
    required_vars = ["ANTHROPIC_API_KEY"]
    return all(os.getenv(var) for var in required_vars)

# Define tasks with dependencies
tasks = [
    TaskDefinition(
        task_id="001",
        phase_id="0-setup",
        name="Setup Directories",
        function=setup_dirs
    ),
    TaskDefinition(
        task_id="002",
        phase_id="0-setup",
        name="Load Configuration",
        function=load_config,
        dependencies=[TaskDependency(task_id="001")]
    ),
    TaskDefinition(
        task_id="003",
        phase_id="0-setup",
        name="Validate Environment",
        function=validate_env,
        dependencies=[TaskDependency(task_id="002")]
    ),
]

# Execute phase
executor = TaskExecutor()
results = executor.execute_phase("0-setup", tasks)

# Report results
for result in results:
    status = "✓" if result.success else "✗"
    print(f"{status} Task {result.task_id}: {result.state.value}")
```

## Example 3: Parallel Task Execution

```python
from core.task import TaskExecutor, TaskDefinition, TaskDependencyGraph

def fetch_data_a():
    """Fetch dataset A (can run in parallel)."""
    time.sleep(2)
    return True

def fetch_data_b():
    """Fetch dataset B (can run in parallel)."""
    time.sleep(2)
    return True

def process_data():
    """Process both datasets (depends on both fetches)."""
    return True

# Define tasks
task1 = TaskDefinition(
    task_id="001",
    phase_id="1-data",
    name="Fetch Data A",
    function=fetch_data_a
)

task2 = TaskDefinition(
    task_id="002",
    phase_id="1-data",
    name="Fetch Data B",
    function=fetch_data_b
)

task3 = TaskDefinition(
    task_id="003",
    phase_id="1-data",
    name="Process Data",
    function=process_data
)

# Set up dependency graph
executor = TaskExecutor()
executor.dependency_graph.add_task(task1)
executor.dependency_graph.add_task(task2)
executor.dependency_graph.add_task(task3)
executor.dependency_graph.add_dependency("003", "001")
executor.dependency_graph.add_dependency("003", "002")

# Get execution levels
levels = executor.dependency_graph.get_execution_order()
print(f"Level 0 (parallel): {[t.name for t in levels[0]]}")
print(f"Level 1 (after 0): {[t.name for t in levels[1]]}")

# Execute
results = executor.execute_phase("1-data", [task1, task2, task3])
```

## Example 4: Retry Handling

```python
from core.task import TaskExecutor, TaskDefinition

attempt_count = [0]

def flaky_api_call():
    """Simulates a flaky API call that succeeds on 2nd attempt."""
    attempt_count[0] += 1
    print(f"Attempt {attempt_count[0]}")

    if attempt_count[0] < 2:
        raise Exception("API temporarily unavailable")

    print("API call successful")
    return True

# Configure retryable task
task = TaskDefinition(
    task_id="001",
    phase_id="1-api",
    name="Call External API",
    function=flaky_api_call,
    retryable=True,
    max_retries=3,
    timeout=30
)

executor = TaskExecutor()
result = executor.execute_task(task)

print(f"Success: {result.success}")
print(f"Retry count: {result.retry_count}")
print(f"Total attempts: {attempt_count[0]}")
```

## Example 5: Progress Tracking

```python
import threading
import time
from core.task import TaskExecutor, TaskDefinition

def slow_task(name, duration):
    """Task that takes a while to complete."""
    def task():
        print(f"Starting {name}")
        time.sleep(duration)
        print(f"Finished {name}")
        return True
    return task

# Create multiple slow tasks
tasks = [
    TaskDefinition(
        task_id=f"00{i}",
        phase_id="2-processing",
        name=f"Process Step {i}",
        function=slow_task(f"Step {i}", 3)
    )
    for i in range(1, 6)
]

executor = TaskExecutor()

# Start progress monitor in background
def monitor_progress():
    while True:
        progress = executor.get_progress("2-processing")
        if progress["total_tasks"] == 0:
            time.sleep(1)
            continue

        pct = progress["completion_percentage"]
        completed = progress["completed_tasks"]
        total = progress["total_tasks"]
        elapsed = progress["elapsed_time"]
        remaining = progress["estimated_remaining"]

        print(f"\rProgress: {pct:.1f}% ({completed}/{total}) | "
              f"Elapsed: {elapsed:.0f}s | "
              f"Remaining: ~{remaining:.0f}s", end="")

        if completed == total:
            break

        time.sleep(1)

    print("\nComplete!")

monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
monitor_thread.start()

# Execute phase
results = executor.execute_phase("2-processing", tasks)

# Wait for monitor to finish
time.sleep(2)
```

## Example 6: Error Recovery

```python
from core.task import TaskExecutor, TaskDefinition
from core.state import StateManager

def task_that_fails():
    """Task that always fails."""
    raise Exception("Simulated failure")

def task_that_succeeds():
    """Task that succeeds."""
    return True

# Create tasks
tasks = [
    TaskDefinition(
        task_id="001",
        phase_id="3-test",
        name="Successful Task",
        function=task_that_succeeds
    ),
    TaskDefinition(
        task_id="002",
        phase_id="3-test",
        name="Failing Task",
        function=task_that_fails,
        retryable=False  # Don't retry
    ),
    TaskDefinition(
        task_id="003",
        phase_id="3-test",
        name="Third Task",
        function=task_that_succeeds
    ),
]

state_manager = StateManager()
executor = TaskExecutor(state_manager=state_manager)

# First run - task 2 will fail
print("First execution:")
results1 = executor.execute_phase("3-test", tasks)
print(f"Completed: {len([r for r in results1 if r.success])}")
print(f"Failed: {len([r for r in results1 if r.failed])}")

# Fix the failing task
def task_002_fixed():
    print("Task 002 has been fixed")
    return True

tasks[1] = TaskDefinition(
    task_id="002",
    phase_id="3-test",
    name="Fixed Task",
    function=task_002_fixed,
    retryable=False
)

# Second run - resume from failure
print("\nSecond execution (resume):")
executor.reset()  # Reset executor but keep state
results2 = executor.execute_phase("3-test", tasks)

# Check what happened
for result in results2:
    if result.state.value == "skipped":
        print(f"✓ Task {result.task_id}: Skipped (already complete)")
    elif result.success:
        print(f"✓ Task {result.task_id}: Completed")
    else:
        print(f"✗ Task {result.task_id}: Failed")
```

## Example 7: Bash Script Execution

```python
from pathlib import Path
from core.task import TaskExecutor, TaskDefinition

# Assume we have a bash script at phases/phase00/task001.sh
script_path = Path("phases/phase00/task001.sh")

task = TaskDefinition(
    task_id="001",
    phase_id="0-setup",
    name="Run Setup Script",
    script_path=str(script_path),
    timeout=300
)

executor = TaskExecutor()
result = executor.execute_task(task)

if result.success:
    print(f"Script completed with exit code {result.exit_code}")
else:
    print(f"Script failed: {result.error}")
    print(f"Exit code: {result.exit_code}")
```

## Example 8: Complex Dependency Graph

```python
from core.task import TaskExecutor, TaskDefinition, TaskDependencyGraph

# Create complex dependency graph
#        task1
#       /  |  \
#   task2 task3 task4
#      \   |   /
#       task5
#         |
#       task6

tasks = [
    TaskDefinition(task_id="001", phase_id="4-complex", name="Task 1", function=lambda: True),
    TaskDefinition(task_id="002", phase_id="4-complex", name="Task 2", function=lambda: True),
    TaskDefinition(task_id="003", phase_id="4-complex", name="Task 3", function=lambda: True),
    TaskDefinition(task_id="004", phase_id="4-complex", name="Task 4", function=lambda: True),
    TaskDefinition(task_id="005", phase_id="4-complex", name="Task 5", function=lambda: True),
    TaskDefinition(task_id="006", phase_id="4-complex", name="Task 6", function=lambda: True),
]

executor = TaskExecutor()

# Build graph
for task in tasks:
    executor.dependency_graph.add_task(task)

# Define dependencies
executor.dependency_graph.add_dependency("002", "001")
executor.dependency_graph.add_dependency("003", "001")
executor.dependency_graph.add_dependency("004", "001")
executor.dependency_graph.add_dependency("005", "002")
executor.dependency_graph.add_dependency("005", "003")
executor.dependency_graph.add_dependency("005", "004")
executor.dependency_graph.add_dependency("006", "005")

# Visualize execution order
levels = executor.dependency_graph.get_execution_order()

print("Execution Plan:")
for i, level_tasks in enumerate(levels):
    task_names = [t.name for t in level_tasks]
    print(f"Level {i}: {', '.join(task_names)}")

# Execute
results = executor.execute_phase("4-complex", tasks)
```

## Example 9: Validation Before Execution

```python
from core.task import TaskExecutor, TaskValidator, TaskDefinition

def critical_task():
    """Task that requires validation."""
    return True

task = TaskDefinition(
    task_id="001",
    phase_id="5-critical",
    name="Critical Operation",
    function=critical_task,
    retryable=False
)

# Validate before executing
validator = TaskValidator()
validation = validator.validate_task(task)

if not validation.valid:
    print("Validation failed:")
    for error in validation.errors:
        print(f"  ✗ {error}")

    for warning in validation.warnings:
        print(f"  ⚠ {warning}")

    print("\nCannot execute task due to validation errors")
else:
    print("Validation passed, executing task...")
    executor = TaskExecutor()
    result = executor.execute_task(task)
```

## Example 10: Custom TaskResult

```python
from core.task import TaskExecutor, TaskDefinition, TaskResult, TaskState
from datetime import datetime

def task_with_custom_result():
    """Task that returns a custom TaskResult."""
    # Do work
    artifacts = ["output.json", "report.md"]

    # Return custom result
    return TaskResult(
        task_id="001",
        phase_id="6-custom",
        state=TaskState.COMPLETED,
        exit_code=0,
        output="Task completed successfully with 2 artifacts",
        artifacts=artifacts,
        duration=5.2,
        started_at=datetime.now(),
        completed_at=datetime.now(),
        metadata={
            "records_processed": 1000,
            "errors_found": 0
        }
    )

task = TaskDefinition(
    task_id="001",
    phase_id="6-custom",
    name="Custom Result Task",
    function=task_with_custom_result
)

executor = TaskExecutor()
result = executor.execute_task(task)

print(f"Output: {result.output}")
print(f"Artifacts: {result.artifacts}")
print(f"Metadata: {result.metadata}")
```

## Best Practices Summary

1. **Always validate tasks** before execution in production
2. **Set appropriate timeouts** based on expected task duration
3. **Use retries** for network/API calls, but not for validation
4. **Define clear dependencies** to enable parallel execution
5. **Track progress** for long-running phases
6. **Handle failures gracefully** with proper error messages
7. **Persist state** to enable resumable execution
8. **Test task functions** independently before integration
9. **Monitor resource usage** (disk, memory) for long phases
10. **Use metadata** to track task-specific information
