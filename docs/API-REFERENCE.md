# Atomic Claude 2.0 - API Reference

Complete API documentation for all core modules, orchestration systems, and phase tasks.

Version: 2.0
Last Updated: 2026-02-07

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Modules](#core-modules)
   - [State Management](#state-management)
   - [Configuration](#configuration)
   - [Subprocess Runner](#subprocess-runner)
   - [LLM Core](#llm-core)
   - [Provider Management](#provider-management)
   - [Memory System](#memory-system)
3. [Orchestration Modules](#orchestration-modules)
   - [Backtracking](#backtracking)
   - [Pre-Task Validation](#pre-task-validation)
   - [Git Manager](#git-manager)
   - [Dashboard Sync](#dashboard-sync)
4. [Phase Orchestrators](#phase-orchestrators)
5. [Usage Patterns](#usage-patterns)
6. [Error Handling](#error-handling)

---

## Architecture Overview

Atomic Claude 2.0 follows a hybrid Python-Bash architecture:

```
main.py (Entry Point)
    ↓
orchestratorNN.py (Python Orchestration)
    ↓
Core Modules (State, Config, LLM, Providers)
    ↓
taskNNN.sh OR taskNNN.py (Task Execution)
    ↓
Bash Libraries (lib/*.sh) OR Python Modules
```

### Design Principles

1. **Python for Orchestration** - Flow control, state management, configuration
2. **Bash for Execution** - Task scripts, LLM invocation, rich CLI UX
3. **Clean Separation** - Core utilities, orchestration logic, and tasks are clearly separated
4. **State-Driven** - Every task tracks completion, enabling resume capability
5. **Type-Safe** - Pydantic validation for configuration, dataclasses for state

---

## Core Modules

### State Management

**Module**: `core.state`
**Purpose**: Immutable, atomic state management with transactions, snapshots, and rollback

#### StateManager

Main state coordinator for task and phase completion tracking.

```python
from core.state import StateManager

state = StateManager(
    state_dir: Path = None,      # Defaults to .state/
    atomic_root: Path = None     # Defaults to cwd
)
```

##### State Queries

**`is_task_complete(phase_id: str, task_id: str) -> bool`**

Check if a task has been completed.

```python
if state.is_task_complete("0-setup", "001"):
    print("Task 001 already complete")
```

**`is_task_failed(phase_id: str, task_id: str) -> bool`**

Check if a task has failed.

**`get_task_status(phase_id: str, task_id: str) -> str`**

Get task status: `"pending"`, `"in_progress"`, `"completed"`, or `"failed"`.

**`get_current_phase() -> Optional[str]`**

Get currently active phase ID.

**`get_current_task() -> Optional[str]`**

Get currently active task ID.

**`get_phase_tasks(phase_id: str) -> Dict[str, Dict[str, Any]]`**

Get all tasks for a phase with their metadata.

**`get_completed_tasks(phase_id: str) -> List[str]`**

Get list of completed task IDs for a phase.

##### State Mutations

**`mark_task_complete(phase_id: str, task_id: str, task_name: str, artifacts: List[str] = None, auto_save: bool = True) -> None`**

Mark a task as successfully completed.

```python
state.mark_task_complete(
    "2-prd",
    "205",
    "PRD Authoring",
    artifacts=[".outputs/2-prd/prd.md"]
)
```

**`mark_task_failed(phase_id: str, task_id: str, task_name: str, error: str = None, auto_save: bool = True) -> None`**

Mark a task as failed with optional error message.

```python
state.mark_task_failed(
    "2-prd",
    "205",
    "PRD Authoring",
    error="Invalid PRD format"
)
```

**`set_current_phase(phase_id: str) -> None`**

Set the currently active phase.

**`set_current_task(task_id: str) -> None`**

Set the currently active task.

**`mark_phase_complete(phase_id: str) -> None`**

Mark an entire phase as complete.

##### Transactions

**`begin_transaction() -> StateTransaction`**

Start a state transaction with automatic rollback on exception.

```python
with state.begin_transaction() as txn:
    txn.mark_task_complete("0-setup", "001", "Setup")
    txn.mark_task_complete("0-setup", "002", "Config")
    # Auto-commits on success, rolls back on exception
```

##### Snapshots

**`snapshot() -> StateSnapshot`**

Create a point-in-time snapshot of current state.

```python
snapshot = state.snapshot()
# ... do work ...
state.restore(snapshot)  # Rollback to snapshot
```

**`save_snapshot(name: str = None) -> Path`**

Save snapshot to disk for later restore.

**`load_snapshot(snapshot_file: Path) -> None`**

Load and restore from a saved snapshot file.

##### Display & Utilities

**`display_status() -> None`**

Print human-readable pipeline status to console.

**`reset_all() -> None`**

Reset entire pipeline state and clear all outputs.

**`reset_phase(phase_id: str) -> None`**

Reset a specific phase.

#### Data Classes

**`TaskStatus`** - Enum for task states
- `PENDING`, `IN_PROGRESS`, `COMPLETED`, `COMPLETE`, `FAILED`

**`PhaseStatus`** - Enum for phase states
- `NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`, `FAILED`

**`TaskState`** - Task state record

```python
@dataclass
class TaskState:
    task_id: str
    name: str
    status: TaskStatus
    started_at: Optional[str]
    completed_at: Optional[str]
    failed_at: Optional[str]
    error: Optional[str]
    artifacts: List[str]
```

**`PhaseState`** - Phase state record

```python
@dataclass
class PhaseState:
    phase_id: str
    status: PhaseStatus
    started_at: Optional[str]
    completed_at: Optional[str]
    tasks: Dict[str, TaskState]
```

#### Context Manager

**`task_running(phase_id: str, task_id: str, task_name: str, state_dir: Path = None)`**

Context manager for task execution tracking.

```python
with task_running("2-prd", "205", "PRD Authoring"):
    # Task logic here
    pass
```

---

### Configuration

**Module**: `core.config`
**Purpose**: Multi-source configuration management with validation and hot-reload

#### Config

Main configuration manager with environment variable priority.

```python
from core.config import Config

config = Config(
    atomic_root: Path = None,    # Defaults to cwd
    cli_args: Dict[str, Any] = None  # CLI overrides
)
```

##### Configuration Loading

**Priority Order** (highest to lowest):
1. CLI arguments
2. Environment variables
3. .env file
4. JSON config files (Phase 00 outputs)
5. Defaults

##### Configuration Access

**`get(key: str, default: Any = None) -> Any`**

Get configuration value using dot notation.

```python
project_name = config.get("project.name")
network_mode = config.get("sandbox.network_mode", "cui")
primary_model = config.get("llm.primary_model")
```

**`set(key: str, value: Any) -> None`**

Set configuration value at runtime.

```python
config.set("project.name", "my-project")
config.set("llm.primary_model", "opus")
```

##### Convenience Methods

**`get_project_name() -> str`**

Get project name (defaults to "unknown").

**`get_project_type() -> str`**

Get project type (defaults to "unknown").

**`get_network_mode() -> str`**

Get network mode: `"cui"`, `"internet"`, or `"restricted"`.

**`get_provider(role: str = "primary") -> str`**

Get LLM provider for role: `"primary"`, `"fast"`, `"heavyweight"`, or `"gardener"`.

```python
provider = config.get_provider("fast")  # Returns "ollama" if configured
```

**`get_model(role: str = "primary") -> str`**

Get model for specific role.

```python
model = config.get_model("heavyweight")  # Returns "opus"
```

**`has_bedrock() -> bool`**

Check if AWS Bedrock is configured.

**`has_ollama() -> bool`**

Check if Ollama is configured.

**`get_aws_region() -> Optional[str]`**

Get AWS region for Bedrock.

**`get_aws_profile() -> Optional[str]`**

Get AWS profile for Bedrock.

**`get_bedrock_model() -> Optional[str]`**

Get Bedrock model ID.

**`get_ollama_host() -> str`**

Get Ollama host URL (defaults to "http://localhost:11434").

**`get_ollama_context() -> int`**

Get Ollama context length (defaults to 65536).

##### Validation & Persistence

**`reload() -> None`**

Hot-reload configuration from all sources.

**`validate() -> bool`**

Validate current configuration against schema.

**`to_dict() -> Dict[str, Any]`**

Export configuration to dictionary.

**`save(path: Path) -> None`**

Persist configuration to JSON file.

#### Configuration Schema

When Pydantic is available, configuration is validated against these schemas:

**`ProjectConfig`** - Project metadata
- `name`, `type`, `description`, `target_directory`, `version`

**`LLMConfig`** - LLM configuration
- `primary_provider`, `fast_provider`, `gardener_provider`, `heavyweight_provider`
- `primary_model`, `fast_model`, `heavyweight_model`, `gardener_model`
- `max_turns`, `timeout`

**`MemoryConfig`** - Memory system settings
- `enabled`, `checkpoint_frequency`, `max_size_mb`, `compression_enabled`

**`DashboardConfig`** - Dashboard settings
- `enabled`, `host`, `tasks_port`, `agents_port`, `audits_port`

**`SecretsConfig`** - API keys and secrets
- `bedrock_enabled`, `ollama_enabled`, `aws_region`, `aws_profile`
- `bedrock_model`, `ollama_host`, `ollama_context`

#### Global Singleton

**`get_config(atomic_root: Path = None, cli_args: Dict[str, Any] = None) -> Config`**

Get or create global config instance (singleton pattern).

```python
from core.config import get_config

config = get_config()  # Reuses existing instance
```

---

### Subprocess Runner

**Module**: `core.subprocess_runner`
**Purpose**: Execute bash task scripts from Python with proper environment setup

This is the critical bridge between Python orchestrators and bash task scripts.

#### Functions

**`get_task_environment(phase_id: str, task_id: str) -> Dict[str, str]`**

Build complete environment dictionary for task execution.

Sets 50+ environment variables including:
- `ATOMIC_ROOT`, `ATOMIC_OUTPUT_DIR`, `ATOMIC_STATE_DIR`, `ATOMIC_LOG_DIR`
- `CURRENT_PHASE`, `CURRENT_TASK_ID`
- `CLAUDE_PROVIDER`, `CLAUDE_MODEL`, `CLAUDE_MAX_TURNS`, `CLAUDE_TIMEOUT`
- `CLAUDE_OLLAMA_HOST`, `CLAUDE_OLLAMA_CONTEXT`
- `ATOMIC_TASKS_PORT`, `ATOMIC_AGENTS_PORT`, `ATOMIC_AUDITS_PORT`
- `ATOMIC_NETWORK_MODE`
- `ATOMIC_AGENT_REPO`, `ATOMIC_AUDIT_REPO`, `ATOMIC_LIB_DIR`

```python
env = get_task_environment("2-prd", "205")
print(env["ATOMIC_OUTPUT_DIR"])  # /path/.outputs
```

**`run_task_script(script_path: Path, phase_id: str, task_id: str, timeout: int = 600, capture_output: bool = True) -> Tuple[int, str, str]`**

Execute a bash task script with proper environment.

```python
exit_code, stdout, stderr = run_task_script(
    Path("phases/phase02/task205.sh"),
    "2-prd",
    "205",
    timeout=1200
)

if exit_code == 0:
    print("Task succeeded")
else:
    print(f"Task failed: {stderr}")
```

**Returns**: `(exit_code, stdout, stderr)`
- `exit_code`: 0 for success, non-zero for failure, 124 for timeout
- `stdout`: Captured standard output (if capture_output=True)
- `stderr`: Captured standard error (if capture_output=True)

**`run_task_script_streaming(script_path: Path, phase_id: str, task_id: str, timeout: int = 600) -> int`**

Execute a bash task script with real-time output streaming (no capture).

Use this for tasks with lots of output that should be displayed in real-time.

```python
exit_code = run_task_script_streaming(
    Path("phases/phase02/task205.sh"),
    "2-prd",
    "205"
)
```

**Returns**: Exit code (0 for success)

**`run_bash_command(command: str, phase_id: str, task_id: str, timeout: int = 60, capture_output: bool = True) -> Tuple[int, str, str]`**

Execute a single bash command (not a script file).

```python
exit_code, stdout, stderr = run_bash_command(
    "ls -la .outputs/",
    "2-prd",
    "205"
)
```

**`validate_script_exists(script_path: Path) -> bool`**

Check if a task script exists and is readable.

**`make_script_executable(script_path: Path) -> bool`**

Make a script executable (chmod +x).

---

### LLM Core

**Module**: `core.llm`
**Purpose**: Atomic Claude invocation primitives for script-controlled LLM tasks

#### Core Function

**`atomic_invoke(prompt_source: str, output_file: str, description: str, **kwargs) -> bool`**

Core atomic Claude invocation function.

```python
from core.llm import atomic_invoke

success = atomic_invoke(
    prompt_source="prompt.md",       # Or direct prompt string
    output_file=".outputs/result.json",
    description="Analyze codebase",
    model="sonnet",                  # Optional override
    provider="max",                  # Optional override
    role="primary",                  # Role-based routing
    format_type="json",              # Expected format
    timeout=1200,                    # Timeout in seconds
    use_stdin=False,                 # Read additional context from stdin
    ollama_host="http://localhost:11434",  # Ollama override
    task_type="critical",            # For provider chain resolution
    max_retries=2,                   # Retry attempts
    retry_delay=5                    # Delay between retries
)

if success:
    print("LLM task completed")
```

**Parameters**:
- `prompt_source`: Path to prompt file or prompt string
- `output_file`: Path to output file
- `description`: Human-readable task description
- `model`: Model override (`"opus"`, `"sonnet"`, `"haiku"`)
- `provider`: Provider override (`"max"`, `"api"`, `"ollama"`, `"bedrock"`)
- `role`: Role-based routing (`"primary"`, `"fast"`, `"gardener"`, `"heavyweight"`)
- `format_type`: Expected format (`"json"`, `"markdown"`)
- `timeout`: Timeout in seconds (default: 1200)
- `use_stdin`: Read additional context from stdin
- `ollama_host`: Ollama host override
- `task_type`: Task type for provider chain resolution
- `max_retries`: Maximum retry attempts (default: 2)
- `retry_delay`: Delay between retries in seconds (default: 5)

**Returns**: `True` on success, `False` on failure

#### Helper Functions

**`atomic_extract_json(input_file: str, output_file: str) -> bool`**

Extract JSON from mixed Claude output.

```python
atomic_extract_json("output.txt", "output.json")
```

**`atomic_validate_files(*files: str) -> bool`**

Check if required files exist.

```python
if atomic_validate_files("config.json", "data.csv"):
    print("All files present")
```

#### Output Functions

**`atomic_step(message: str)`** - Print step message

**`atomic_substep(message: str)`** - Print sub-step message

**`atomic_success(message: str)`** - Print success message

**`atomic_error(message: str)`** - Print error message

**`atomic_warn(message: str)`** - Print warning message

**`atomic_waiting(message: str)`** - Print waiting message

**`atomic_info(message: str)`** - Print info message

**`atomic_h1(title: str)`** - Print major header

**`atomic_h2(title: str)`** - Print section header

```python
from core.llm import atomic_step, atomic_success, atomic_error

atomic_step("Starting PRD generation")
success = generate_prd()
if success:
    atomic_success("PRD generated successfully")
else:
    atomic_error("PRD generation failed")
```

#### Configuration Functions

**`atomic_get_primary_model() -> str`**

Get primary model from project config or fallback to default.

**`atomic_get_fast_model() -> str`**

Get fast model from project config or fallback to haiku.

**`atomic_llm_available() -> bool`**

Check if an LLM provider is available.

---

### Provider Management

**Module**: `core.providers`
**Purpose**: Hybrid LLM provider routing for cost-optimized operations

#### ProviderManager

Main provider manager for multi-provider routing and availability detection.

```python
from core.providers import ProviderManager

pm = ProviderManager(
    config_file: Optional[Path] = None,      # Defaults to .outputs/0-setup/project-config.json
    cache_dir: Optional[Path] = None,        # Defaults to .state/provider/
    health_cache_ttl: int = 60               # Health check cache TTL in seconds
)

pm.init()  # Initialize (lazy init)
```

##### Availability Detection

**`check_claude_code() -> bool`**

Check if Claude Code (subscription) is available.

**`check_anthropic() -> bool`**

Check if Anthropic API is available (ANTHROPIC_API_KEY set).

**`check_aws_bedrock() -> bool`**

Check if AWS Bedrock is available (AWS credentials configured).

**`check_openai() -> bool`**

Check if OpenAI API is available.

**`check_google() -> bool`**

Check if Google (Gemini) API is available.

**`check_azure() -> bool`**

Check if Azure OpenAI is available.

**`check_openrouter() -> bool`**

Check if OpenRouter is available.

**`check_ollama() -> bool`**

Check if any Ollama server is available.

**`check_availability(provider: str) -> bool`**

Check if a specific provider is available.

```python
if pm.check_availability("anthropic"):
    print("Anthropic API available")
```

**`get_available(priority_chain: Optional[List[str]] = None) -> List[str]`**

Get list of all available providers in priority order.

```python
available = pm.get_available()
print(f"Available providers: {available}")
# ['claude-code', 'ollama']
```

**`show_availability() -> None`**

Print availability status for all providers.

##### Provider Chain Resolution

**`resolve_chain(chain: List[str], context: str = "") -> Optional[str]`**

Resolve the best available provider from a preference chain.

```python
chain = ['anthropic', 'ollama', 'claude-code']
provider = pm.resolve_chain(chain)
print(f"Using provider: {provider}")
```

**`get_chain(task_type: str) -> List[str]`**

Get provider chain for a task type from project config.

Task types: `"critical"`, `"bulk"`, `"quick"`, `"background"`

**`resolve_for_task(task_type: str, context: str = "") -> str`**

Resolve best provider for a task type.

```python
provider = pm.resolve_for_task("bulk")  # Returns "ollama" if available
```

##### Ollama Management

**`get_ollama_server() -> Optional[OllamaServer]`**

Get the best available Ollama server.

```python
server = pm.get_ollama_server()
if server:
    print(f"Using {server.name} at {server.host}")
```

**`list_models(server: Optional[str] = None) -> List[str]`**

List available models on a server.

##### Invocation

**`invoke(prompt: str, output_file: str, task_type: str = 'critical', **kwargs) -> int`**

Invoke an LLM via the appropriate provider.

```python
exit_code = pm.invoke(
    prompt="prompt.md",
    output_file="output.json",
    task_type="bulk",
    model="mistral",
    timeout=300
)
```

##### Cache Management

**`invalidate_availability_cache() -> None`**

Invalidate all provider availability cache.

**`invalidate_health_cache() -> None`**

Invalidate health cache for all Ollama servers.

#### Data Classes

**`OllamaServer`** - Ollama server configuration

```python
@dataclass
class OllamaServer:
    name: str
    host: str
    model: str
    priority: int = 0
```

**`ProviderConfig`** - Provider configuration

```python
@dataclass
class ProviderConfig:
    ollama_enabled: bool
    ollama_failover: bool
    ollama_health_check: bool
    critical_provider: str
    bulk_provider: str
    background_provider: str
    background_model: str
    api_fallback_to_ollama: bool
    ollama_fallback_to_api: bool
    offline_mode: bool
    ollama_servers: List[OllamaServer]
    chains: Dict[str, List[str]]
```

#### Convenience Functions

**`provider_init() -> None`**

Initialize global provider manager.

**`provider_check_availability(provider: str) -> bool`**

Check if a provider is available.

**`provider_get_available(priority_chain: Optional[List[str]] = None) -> List[str]`**

Get list of available providers.

**`provider_resolve_for_task(task_type: str, context: str = "") -> str`**

Resolve best provider for a task type.

**`provider_status() -> None`**

Print provider status.

**`provider_show_availability() -> None`**

Show availability for all providers.

---

### Memory System

**Module**: `core.memory`
**Purpose**: Persistent memory storage across phases and sessions

Currently wraps `memory.sh` bash functions via subprocess. Pure Python implementation planned.

#### Lifecycle Functions

**`memory_init() -> bool`**

Initialize memory system.

**`memory_should_persist() -> bool`**

Check if memory persistence is enabled.

**`memory_has_remote() -> bool`**

Check if remote memory (claude-mem) is configured.

#### Phase Tracking

**`memory_get_head_phase() -> Optional[str]`**

Get the current head phase (last phase executed).

**`memory_set_head_phase(phase_id: str) -> bool`**

Set the current head phase.

#### Checkpoints & Backtracking

**`memory_add_checkpoint(phase_id: str, checkpoint_type: str, description: str) -> bool`**

Add a checkpoint marker.

**`memory_check_backtrack(target_phase: str) -> bool`**

Check if we're backtracking to an earlier phase.

**`memory_handle_backtrack(target_phase: str) -> bool`**

Handle backtracking (clear state ahead of target phase).

**`memory_create_checkpoint(phase_id: str, content: str, user_approved: bool = False) -> bool`**

Create a phase checkpoint with content.

**`memory_prompt_save(phase_num: int, phase_name: str, summary: str) -> bool`**

Prompt user to save phase summary to memory.

#### Task Lifecycle

**`memory_task_start(phase_id: str, task_id: str, task_name: str) -> bool`**

Mark task as started (for memory tracking).

**`memory_task_end(phase_id: str, task_id: str, success: bool = True) -> bool`**

Mark task as ended (save outputs to memory if configured).

#### Session Lifecycle

**`memory_session_start() -> Optional[str]`**

Start memory session (recall context if available).

**`memory_session_end() -> bool`**

End memory session (cleanup).

---

## Orchestration Modules

### Backtracking

**Module**: `orchestration.backtrack`
**Purpose**: Reset pipeline to any phase/task with clean slate

#### Functions

**`backtrack_to(phase: int, task: Optional[str] = None) -> None`**

Reset pipeline to a specific phase/task.

```python
from orchestration.backtrack import backtrack_to

# Backtrack to start of Phase 2
backtrack_to(2)

# Backtrack to Task 205 in Phase 2
backtrack_to(2, "205")
```

This will:
1. Prompt for confirmation
2. Clear state for all phases/tasks after target
3. Delete artifacts after target
4. Clear memory after target
5. Optionally clear generated code

---

### Pre-Task Validation

**Module**: `orchestration.pre_task_validation`
**Purpose**: Enforce directory purity - BLOCKING validation before each task

#### Functions

**`validate_directory_pristine(phase_id: str, task_id: str) -> bool`**

BLOCKING validation: Ensure atomic-claude contains ONLY tool files.

```python
from orchestration.pre_task_validation import validate_directory_pristine

if not validate_directory_pristine("2-prd", "205"):
    print("Cannot proceed - directory violations found")
    return False
```

Returns `False` if project artifacts are found in tool directory, blocking task execution.

**`find_violations() -> List[Dict[str, Any]]`**

Scan atomic-claude for project artifacts.

Returns list of violations with:
- `path`: Relative path to violating file
- `correct_location`: Where file should be
- `reason`: Why it's a violation

**`auto_cleanup() -> bool`**

Automatically move violations to correct locations.

```python
from orchestration.pre_task_validation import auto_cleanup

if auto_cleanup():
    print("Cleanup successful")
```

#### Environment Override

Set `ATOMIC_TOOL_DEVELOPMENT=true` to disable validation when developing the tool itself.

---

### Git Manager

**Module**: `orchestration.git_manager`
**Purpose**: Automated Git commit management with intelligent prompts

Coming soon - see implementation for details.

---

### Dashboard Sync

**Module**: `orchestration.dashboard_sync`
**Purpose**: Sync state to real-time web dashboard

Coming soon - see implementation for details.

---

## Phase Orchestrators

All phases follow the same orchestrator pattern.

### Orchestrator Pattern

```python
#!/usr/bin/env python3
"""
Phase N Orchestrator (orchestratorNN.py)
"""

from pathlib import Path
from core.state import StateManager
from core.ui import phase_header, phase_complete
from orchestration.pre_task_validation import validate_directory_pristine

def run_phase(resume_at: str = None) -> bool:
    """Execute Phase N."""
    phase_header(f"Phase {N}: Phase Name")

    state = StateManager()
    phase_id = "N-phase-name"

    # Task list
    tasks = [
        ("NNN", "Task name", task_NNN_function),
        ("NNN+1", "Next task", task_NNN_next_function),
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
        # Skip completed
        if state.is_task_complete(phase_id, task_id):
            print(f"✓ Task {task_id} already complete")
            continue

        # PRE-TASK VALIDATION (BLOCKER)
        if not validate_directory_pristine(phase_id, task_id):
            print(f"Cannot proceed - fix violations first")
            return False

        # Execute
        print(f"Running Task {task_id}: {task_name}")
        try:
            success = task_func()
            if not success:
                state.mark_task_failed(phase_id, task_id, task_name)
                return False
            state.mark_task_complete(phase_id, task_id, task_name)
        except Exception as e:
            state.mark_task_failed(phase_id, task_id, task_name, str(e))
            return False

    phase_complete(f"Phase {N}: Phase Name")
    return True
```

### Available Phases

- **Phase 0** (`orchestrator00.py`): Setup
- **Phase 1** (`orchestrator01.py`): Discovery
- **Phase 2** (`orchestrator02.py`): PRD
- **Phase 3** (`orchestrator03.py`): Tasking
- **Phase 4** (`orchestrator04.py`): Specification
- **Phase 5** (`orchestrator05.py`): Implementation
- **Phase 6** (`orchestrator06.py`): Code Review
- **Phase 7** (`orchestrator07.py`): Integration
- **Phase 8** (`orchestrator08.py`): Deployment Prep
- **Phase 9** (`orchestrator09.py`): Release

---

## Usage Patterns

### Pattern 1: Basic Task Execution

```python
from core.state import StateManager
from core.subprocess_runner import run_task_script_streaming
from pathlib import Path

def execute_task():
    """Execute a single task."""
    state = StateManager()
    phase_id = "2-prd"
    task_id = "205"
    task_name = "PRD Authoring"

    # Check if already complete
    if state.is_task_complete(phase_id, task_id):
        print("Task already complete")
        return True

    # Execute bash script
    script_path = Path("phases/phase02/task205.sh")
    exit_code = run_task_script_streaming(
        script_path,
        phase_id,
        task_id,
        timeout=1200
    )

    # Mark complete
    if exit_code == 0:
        state.mark_task_complete(phase_id, task_id, task_name)
        return True
    else:
        state.mark_task_failed(phase_id, task_id, task_name)
        return False
```

### Pattern 2: LLM Invocation

```python
from core.llm import atomic_invoke, atomic_step, atomic_success
from core.config import Config

def generate_prd():
    """Generate PRD using LLM."""
    config = Config()

    atomic_step("Generating PRD")

    # Build prompt
    prompt = """
    Generate a Product Requirements Document for:
    Project: {project_name}
    Type: {project_type}

    Include:
    - Overview
    - Goals
    - Features
    - Technical requirements
    """.format(
        project_name=config.get_project_name(),
        project_type=config.get_project_type()
    )

    # Invoke LLM
    success = atomic_invoke(
        prompt_source=prompt,
        output_file=".outputs/2-prd/prd.md",
        description="Generate PRD",
        model="sonnet",
        format_type="markdown",
        timeout=600
    )

    if success:
        atomic_success("PRD generated")

    return success
```

### Pattern 3: Provider Chain Resolution

```python
from core.providers import ProviderManager

def execute_bulk_task():
    """Execute bulk task with optimal provider."""
    pm = ProviderManager()
    pm.init()

    # Resolve best provider for bulk task
    provider = pm.resolve_for_task("bulk")
    print(f"Using provider: {provider}")

    # Get Ollama server if applicable
    if provider == "ollama":
        server = pm.get_ollama_server()
        if server:
            print(f"Ollama server: {server.host}")
            print(f"Model: {server.model}")
```

### Pattern 4: Transaction-Based State Updates

```python
from core.state import StateManager

def execute_multi_step_task():
    """Execute task with multiple state changes."""
    state = StateManager()

    with state.begin_transaction() as txn:
        # Multiple state changes
        txn.mark_task_complete("2-prd", "201", "Entry Validation")
        txn.mark_task_complete("2-prd", "202", "Corpus Import")
        txn.mark_task_complete("2-prd", "203", "Agent Selection")
        # Auto-commits on success, rolls back on exception
```

### Pattern 5: Configuration-Driven Behavior

```python
from core.config import Config

def configure_llm():
    """Configure LLM based on project settings."""
    config = Config()

    # Get provider and model
    provider = config.get_provider("primary")
    model = config.get_model("primary")

    print(f"Provider: {provider}")
    print(f"Model: {model}")

    # Check capabilities
    if config.has_bedrock():
        region = config.get_aws_region()
        print(f"Bedrock region: {region}")

    if config.has_ollama():
        host = config.get_ollama_host()
        context = config.get_ollama_context()
        print(f"Ollama: {host} (context: {context})")
```

### Pattern 6: Memory Integration

```python
from core.memory import (
    memory_task_start,
    memory_task_end,
    memory_create_checkpoint
)

def execute_with_memory():
    """Execute task with memory tracking."""
    phase_id = "2-prd"
    task_id = "205"
    task_name = "PRD Authoring"

    # Start memory tracking
    memory_task_start(phase_id, task_id, task_name)

    try:
        # Execute task
        success = do_work()

        # End memory tracking
        memory_task_end(phase_id, task_id, success)

        # Create checkpoint if successful
        if success:
            memory_create_checkpoint(
                phase_id,
                "PRD generation complete",
                user_approved=True
            )

        return success
    except Exception:
        memory_task_end(phase_id, task_id, False)
        raise
```

---

## Error Handling

### Common Error Patterns

#### 1. Task Execution Errors

```python
try:
    exit_code = run_task_script_streaming(script_path, phase_id, task_id)
    if exit_code != 0:
        state.mark_task_failed(phase_id, task_id, task_name)
        return False
except FileNotFoundError:
    print(f"Task script not found: {script_path}")
    state.mark_task_failed(phase_id, task_id, task_name, "Script not found")
    return False
except Exception as e:
    print(f"Task execution error: {e}")
    state.mark_task_failed(phase_id, task_id, task_name, str(e))
    return False
```

#### 2. Configuration Errors

```python
from core.config import Config

config = Config()

# Always provide defaults for optional values
project_name = config.get("project.name", "unknown")
network_mode = config.get("sandbox.network_mode", "cui")

# Validate configuration
if not config.validate():
    print("Configuration validation failed")
    return False
```

#### 3. State Errors

```python
from core.state import StateManager

state = StateManager()

# Always check state operations
if not state.is_task_complete(phase_id, task_id):
    # Task not complete, execute it
    pass
else:
    # Task already complete, skip
    pass

# Use transactions for critical state changes
try:
    with state.begin_transaction() as txn:
        txn.mark_task_complete(phase_id, task_id, task_name)
except Exception as e:
    print(f"State update failed: {e}")
    # Transaction automatically rolled back
```

#### 4. Provider Errors

```python
from core.providers import ProviderManager

pm = ProviderManager()
pm.init()

# Always check provider availability
if not pm.check_availability("anthropic"):
    print("Anthropic API not available")
    # Fall back to alternative
    provider = pm.resolve_for_task("critical")
    print(f"Using fallback: {provider}")
```

### Exit Codes

- **0**: Success
- **1**: General failure
- **124**: Timeout
- **Non-zero**: Specific error code

---

## Best Practices

1. **Always use StateManager** for task completion tracking
2. **Always validate directory** before each task (pre-task validation)
3. **Always provide defaults** when accessing configuration
4. **Always handle timeouts** gracefully
5. **Always mark tasks** as complete or failed
6. **Use transactions** for multi-step state changes
7. **Use provider chains** for cost-optimized LLM routing
8. **Cache provider availability** to reduce health check overhead
9. **Stream output** for long-running tasks
10. **Validate outputs** before marking tasks complete

---

## Version History

- **2.0** (2026-02-07): Complete Python refactor, API documentation
- **1.0**: Original bash implementation

---

For more information, see:
- [Developer Guide](DEVELOPER-GUIDE.md)
- [User Guide](USER-GUIDE.md)
- [CLAUDE.md](../CLAUDE.md) (guidance for Claude Code)
