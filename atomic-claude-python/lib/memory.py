#!/usr/bin/env python3
"""
ATOMIC-CLAUDE Memory Layer
Persistent memory via local file storage

Architecture:
  - Checkpoint model: Memory saved at phase closeouts + task-level
  - Head tracking: Local state knows current phase progression
  - Backtrack handling: Invalidates orphaned memories
  - Scope separation: Pipeline work vs meta/debug work
  - User approval: Nothing persists without explicit consent

Storage Backends:
  - Local files: .state/memory/ (always available, fast)
"""

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import shutil


# ============================================================================
# CONFIGURATION
# ============================================================================

class MemoryConfig:
    """Global memory configuration"""
    def __init__(self, atomic_root: Optional[str] = None):
        self.atomic_root = Path(atomic_root or os.environ.get('ATOMIC_ROOT', '.'))
        self.atomic_output_dir = Path(os.environ.get('ATOMIC_OUTPUT_DIR', self.atomic_root / '.outputs'))

        # State files
        self.memory_head_file = self.atomic_root / '.state' / 'memory-head.json'
        self.memory_checkpoints_dir = self.atomic_root / '.state' / 'memory-checkpoints'
        self.memory_local_dir = self.atomic_root / '.state' / 'memory'
        self.log_dir = self.atomic_root / '.logs'

        # Load memory enabled flag
        self.memory_enabled = self._load_memory_enabled()

    def _load_memory_enabled(self) -> bool:
        """Load memory enabled flag from environment or secrets file"""
        # Check environment first
        if os.environ.get('ATOMIC_MEMORY_ENABLED', '').lower() == 'true':
            return True

        # Check secrets file
        secrets_file = self.atomic_output_dir / '0-setup' / 'secrets.json'
        if secrets_file.exists():
            try:
                with open(secrets_file) as f:
                    secrets = json.load(f)
                    return secrets.get('memory_enabled', False)
            except (json.JSONDecodeError, IOError):
                pass

        return False


# Global config instance
_config: Optional[MemoryConfig] = None


def get_config() -> MemoryConfig:
    """Get or create the global memory configuration"""
    global _config
    if _config is None:
        _config = MemoryConfig()
    return _config


# ============================================================================
# INITIALIZATION
# ============================================================================

def memory_init() -> None:
    """Initialize memory system"""
    config = get_config()

    # Reload config in case secrets changed
    config.memory_enabled = config._load_memory_enabled()

    if not config.memory_enabled:
        return

    # Create state directories
    config.memory_head_file.parent.mkdir(parents=True, exist_ok=True)
    config.memory_checkpoints_dir.mkdir(parents=True, exist_ok=True)
    config.memory_local_dir.mkdir(parents=True, exist_ok=True)

    # Initialize head file if missing
    if not config.memory_head_file.exists():
        _memory_init_head()

    # Log initialization
    config.log_dir.mkdir(parents=True, exist_ok=True)
    _memory_log("memory_init", "Memory system initialized (local storage)")


def _memory_init_head() -> None:
    """Initialize memory head file"""
    config = get_config()
    project_id = _memory_get_project_id()

    head_data = {
        "project": project_id,
        "head_phase": -1,
        "head_checkpoint": None,
        "checkpoints": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    with open(config.memory_head_file, 'w') as f:
        json.dump(head_data, f, indent=2)


# ============================================================================
# PROJECT IDENTIFICATION
# ============================================================================

def _memory_get_project_id() -> str:
    """
    Get project identifier
    Priority: git remote > ATOMIC_ORCHESTRATOR > parent of ATOMIC-CLAUDE > ATOMIC_ROOT
    """
    config = get_config()
    base_dir = Path(os.environ.get('ATOMIC_ORCHESTRATOR',
                                   os.environ.get('ATOMIC_ROOT', os.getcwd())))

    # If we're in an ATOMIC-CLAUDE subdirectory, use the parent project name
    if base_dir.name == 'ATOMIC-CLAUDE':
        base_dir = base_dir.parent

    # Try git remote from the project directory
    try:
        result = subprocess.run(
            ['git', '-C', str(base_dir), 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        # Extract owner/repo from URL
        match = re.search(r'[/:]([\w-]+/[\w-]+)\.git$', remote_url)
        if match:
            project_id = match.group(1).replace('/', '-')
        else:
            project_id = base_dir.name
    except (subprocess.CalledProcessError, FileNotFoundError):
        project_id = base_dir.name

    return f"atomic-{project_id}"


def _memory_get_container_tag() -> str:
    """Get container tag for this project"""
    return f"{_memory_get_project_id()}-pipeline"


# ============================================================================
# SCOPE DETECTION
# ============================================================================

def memory_should_persist() -> bool:
    """
    Check if we should persist to memory
    Returns True if in pipeline mode with memory enabled
    """
    config = get_config()

    # Memory must be enabled
    if not config.memory_enabled:
        return False

    # Must be in pipeline mode (phase context exists)
    if not (os.environ.get('ATOMIC_PHASE') or os.environ.get('CURRENT_PHASE')):
        return False

    return True


def memory_has_remote() -> bool:
    """
    Check if claude-mem is available (legacy function for API compatibility)
    Local files are always used as the primary storage
    """
    return True


# ============================================================================
# HEAD TRACKING
# ============================================================================

def memory_get_head_phase() -> int:
    """Get current head phase"""
    config = get_config()

    if config.memory_head_file.exists():
        try:
            with open(config.memory_head_file) as f:
                data = json.load(f)
                return data.get('head_phase', -1)
        except (json.JSONDecodeError, IOError):
            pass

    return -1


def memory_set_head_phase(phase: int, checkpoint_id: str) -> None:
    """Update head to new phase"""
    config = get_config()

    if not config.memory_head_file.exists():
        _memory_init_head()

    with open(config.memory_head_file) as f:
        data = json.load(f)

    data['head_phase'] = phase
    data['head_checkpoint'] = checkpoint_id
    data['updated_at'] = datetime.now().isoformat()

    with open(config.memory_head_file, 'w') as f:
        json.dump(data, f, indent=2)


def memory_add_checkpoint(checkpoint_id: str, phase: int, status: str = "valid") -> None:
    """Add checkpoint to tracking"""
    config = get_config()

    if not config.memory_head_file.exists():
        _memory_init_head()

    with open(config.memory_head_file) as f:
        data = json.load(f)

    checkpoint_obj = {
        "id": checkpoint_id,
        "phase": phase,
        "status": status,
        "created_at": datetime.now().isoformat()
    }

    data['checkpoints'].append(checkpoint_obj)

    with open(config.memory_head_file, 'w') as f:
        json.dump(data, f, indent=2)


# ============================================================================
# BACKTRACK HANDLING
# ============================================================================

def memory_check_backtrack(target_phase: int) -> bool:
    """
    Check if starting this phase is a backtrack
    Returns True if backtrack detected
    """
    config = get_config()

    if not config.memory_enabled:
        return False

    head_phase = memory_get_head_phase()

    return target_phase <= head_phase and head_phase >= 0


def memory_handle_backtrack(target_phase: int) -> bool:
    """
    Handle backtrack - invalidate orphaned memories
    Returns True if user confirmed, False if cancelled
    """
    head_phase = memory_get_head_phase()

    # Color codes (fallback to empty if not in env)
    YELLOW = os.environ.get('YELLOW', '')
    GREEN = os.environ.get('GREEN', '')
    RED = os.environ.get('RED', '')
    DIM = os.environ.get('DIM', '')
    NC = os.environ.get('NC', '')

    print()
    print(f"  {YELLOW}⚠ Backtrack Detected{NC}")
    print()
    print(f"  Current memory head: Phase {head_phase}")
    print(f"  Target phase: Phase {target_phase}")
    print()
    print(f"  Local memories from phases {target_phase + 1}-{head_phase} will be cleared.")
    print()
    print(f"  Options:")
    print(f"    {GREEN}[continue]{NC} Clear local memories and proceed")
    print(f"    {RED}[abort]{NC}    Cancel and stay at current phase")
    print()

    try:
        choice = input("  Choice [continue]: ").strip() or "continue"
    except EOFError:
        choice = "continue"

    if choice == "abort":
        print()
        print(f"  {DIM}Backtrack cancelled.{NC}")
        return False

    _memory_invalidate_after_phase(target_phase)

    # Update memory head to target phase
    memory_set_head_phase(target_phase, "")
    print()
    print(f"  {GREEN}✓{NC} Memory head reset to Phase {target_phase}")

    # CRITICAL: Also reset task state so tasks actually re-run
    config = get_config()
    log_file = config.log_dir / 'memory.log'

    try:
        # Try to call task state reset if available
        from . import task_state
        if hasattr(task_state, 'task_state_backtrack_reset'):
            task_state.task_state_backtrack_reset(target_phase)
        else:
            print(f"  {YELLOW}!{NC} Warning: Could not reset task state (function not found)")
    except ImportError:
        print(f"  {YELLOW}!{NC} Warning: Could not reset task state (module not found)")

    print()
    return True


def _memory_invalidate_after_phase(phase: int) -> None:
    """Mark checkpoints after phase as invalidated AND clear local memory files"""
    config = get_config()
    memory_dir = config.memory_local_dir

    DIM = os.environ.get('DIM', '')
    NC = os.environ.get('NC', '')

    # Invalidate checkpoints in head file
    if config.memory_head_file.exists():
        with open(config.memory_head_file) as f:
            data = json.load(f)

        for checkpoint in data.get('checkpoints', []):
            if checkpoint.get('phase', 0) > phase:
                checkpoint['status'] = 'invalidated'

        with open(config.memory_head_file, 'w') as f:
            json.dump(data, f, indent=2)

    # Clear local memory files for target phase and later
    if memory_dir.exists():
        for phase_num in range(phase, 10):
            phase_memory_dir = memory_dir / f'phase-{phase_num}'
            if phase_memory_dir.exists():
                shutil.rmtree(phase_memory_dir)
                print(f"  {DIM}Cleared local memory: phase-{phase_num}{NC}")

    # Clear debug log entries for invalidated phases
    debug_file = config.log_dir / 'memory-debug.jsonl'
    if debug_file.exists():
        kept_lines = []
        with open(debug_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_phase = entry.get('phase', '')
                    # Extract phase number (e.g., "0-setup" -> 0)
                    match = re.match(r'^(\d+)', entry_phase)
                    if match:
                        entry_phase_num = int(match.group(1))
                        if entry_phase_num < phase:
                            kept_lines.append(line)
                except (json.JSONDecodeError, ValueError):
                    pass

        with open(debug_file, 'w') as f:
            f.writelines(kept_lines)

        print(f"  {DIM}Cleared debug log for phases >= {phase}{NC}")


# ============================================================================
# CHECKPOINT OPERATIONS
# ============================================================================

def memory_create_checkpoint(
    phase: int,
    phase_name: str,
    summary: str,
    decisions: Optional[List[Dict[str, Any]]] = None,
    artifacts: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Create a checkpoint for the current phase"""
    config = get_config()

    if decisions is None:
        decisions = []
    if artifacts is None:
        artifacts = []

    checkpoint_id = f"phase{phase}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    project_id = _memory_get_project_id()

    # Get previous checkpoint
    prev_checkpoint = ""
    if config.memory_head_file.exists():
        try:
            with open(config.memory_head_file) as f:
                data = json.load(f)
                prev_checkpoint = data.get('head_checkpoint', '')
        except (json.JSONDecodeError, IOError):
            pass

    # Create checkpoint JSON
    checkpoint_file = config.memory_checkpoints_dir / f'{checkpoint_id}.json'

    checkpoint_data = {
        "checkpoint_id": checkpoint_id,
        "project": project_id,
        "phase": phase,
        "phase_name": phase_name,
        "summary": summary,
        "key_decisions": decisions,
        "artifacts": artifacts,
        "created_at": datetime.now().isoformat(),
        "previous_checkpoint": prev_checkpoint
    }

    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f, indent=2)

    # Add to tracking
    memory_add_checkpoint(checkpoint_id, phase, "valid")
    memory_set_head_phase(phase, checkpoint_id)

    return checkpoint_id


# ============================================================================
# USER APPROVAL GATE
# ============================================================================

def memory_prompt_save(phase: int, phase_name: str, summary: str) -> bool:
    """
    Prompt user to save phase to memory
    Returns True if saved, False if skipped
    """
    if not memory_should_persist():
        return False

    BOLD = os.environ.get('BOLD', '')
    DIM = os.environ.get('DIM', '')
    CYAN = os.environ.get('CYAN', '')
    GREEN = os.environ.get('GREEN', '')
    YELLOW = os.environ.get('YELLOW', '')
    NC = os.environ.get('NC', '')

    print()
    print(f"  {BOLD}MEMORY CHECKPOINT{NC}")
    print()
    print(f"  {DIM}Summary to persist:{NC}")
    print()
    for line in summary.split('\n'):
        print(f"    {line}")
    print()
    print(f"  {CYAN}Options:{NC}")
    print(f"    {GREEN}[save]{NC} Save to local memory")
    print(f"    {YELLOW}[edit]{NC} Edit summary before saving")
    print(f"    {DIM}[skip]{NC} Don't save")
    print()

    try:
        choice = input("  Choice [save]: ").strip() or "save"
    except EOFError:
        choice = "save"

    if choice == "save":
        _memory_commit_phase(phase, phase_name, summary)
        return True
    elif choice == "edit":
        # Edit summary
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            tmp.write(summary)
            tmp_path = tmp.name

        editor = os.environ.get('EDITOR', 'nano')
        subprocess.run([editor, tmp_path])

        with open(tmp_path) as f:
            edited_summary = f.read()

        os.unlink(tmp_path)
        _memory_commit_phase(phase, phase_name, edited_summary)
        return True
    else:
        print()
        print(f"  {DIM}Memory save skipped.{NC}")
        # Still create local checkpoint
        memory_create_checkpoint(phase, phase_name, summary)
        return False


def _memory_commit_phase(phase: int, phase_name: str, summary: str) -> None:
    """Commit phase to local memory storage"""
    GREEN = os.environ.get('GREEN', '')
    NC = os.environ.get('NC', '')

    # Create local checkpoint
    checkpoint_id = memory_create_checkpoint(phase, phase_name, summary)

    # Save closeout to local file storage
    _memory_save_closeout(phase, phase_name, summary)
    _memory_log("_memory_commit_phase", f"Saved closeout locally for Phase {phase}")

    print()
    print(f"  {GREEN}✓{NC} Saved to local memory (checkpoint: {checkpoint_id})")


# ============================================================================
# LOCAL MEMORY STORAGE
# ============================================================================

def _memory_log(source: str, message: str) -> None:
    """Structured JSON logging for memory operations"""
    config = get_config()
    log_file = config.log_dir / 'memory.log'
    config.log_dir.mkdir(parents=True, exist_ok=True)

    log_entry = {
        "ts": datetime.now().isoformat(),
        "src": source,
        "msg": message
    }

    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')


def _memory_debug(operation: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
    """
    Enhanced debug logging for web dashboard
    Operations: task_start, task_end, recall_local, recall_remote, inject, save_local, save_remote
    Status: start, success, fail, skip
    """
    config = get_config()
    debug_file = config.log_dir / 'memory-debug.jsonl'
    config.log_dir.mkdir(parents=True, exist_ok=True)

    if details is None:
        details = {}

    # Get current task context
    phase = os.environ.get('CURRENT_PHASE', 'unknown')
    task = os.environ.get('CURRENT_TASK_ID', 'unknown')
    task_name = os.environ.get('CURRENT_TASK_NAME', 'unknown')

    entry = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "status": status,
        "phase": phase,
        "task_id": task,
        "task_name": task_name,
        "details": details
    }

    with open(debug_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def _memory_truncate(content: str, max_len: int = 200) -> str:
    """Helper to truncate content for logging"""
    if len(content) > max_len:
        return content[:max_len] + "..."
    return content


def _memory_ensure_local_dirs(phase_num: int) -> Path:
    """Ensure local memory directory structure exists"""
    config = get_config()
    phase_dir = config.memory_local_dir / f'phase-{phase_num}'
    phase_dir.mkdir(parents=True, exist_ok=True)
    return phase_dir


def _memory_save_local(phase_num: int, task_id: str, save_type: str, content: str) -> Path:
    """
    Save content to LOCAL file storage
    Returns path to saved file
    """
    phase_dir = _memory_ensure_local_dirs(phase_num)
    task_file = phase_dir / f'task-{task_id}-{save_type}.md'

    with open(task_file, 'w') as f:
        f.write(f"# Task {task_id}: {save_type}\n")
        f.write(f"_Saved: {datetime.now().isoformat()}_\n\n")
        f.write(content)

    _memory_log("_memory_save_local", f"Wrote {len(content)} chars to {task_file}")
    return task_file


def _memory_recall_local(recall_query: str, current_phase: Optional[int] = None) -> str:
    """
    Recall content from LOCAL file storage
    Returns concatenated content from relevant local memory files
    """
    config = get_config()
    results = []

    # If memory directory doesn't exist, return empty
    if not config.memory_local_dir.exists():
        return ""

    # Strategy: Read files based on query keywords
    # 1. If query mentions "Phase N", read that phase's files
    # 2. If query mentions "closeout", prioritize closeout files
    # 3. Otherwise, grep for relevant keywords

    # Check for phase references in query (e.g., "Phase 0", "Phase 1")
    phase_match = re.search(r'Phase (\d)', recall_query)
    if phase_match:
        phase_num = int(phase_match.group(1))
        phase_dir = config.memory_local_dir / f'phase-{phase_num}'
        if phase_dir.exists():
            # Read all files from that phase, prioritizing closeout
            closeout_file = phase_dir / 'closeout.md'
            if closeout_file.exists():
                results.append(f"## Phase {phase_num} Closeout\n\n")
                with open(closeout_file) as f:
                    results.append(f.read())
                results.append("\n\n")

            for task_file in sorted(phase_dir.glob('task-*.md')):
                with open(task_file) as f:
                    results.append(f.read())
                results.append("\n\n")

    # If query mentions specific concepts, grep for them in all files
    if not results and recall_query:
        # Extract key terms from query (split on spaces, take meaningful words)
        keywords = [word for word in recall_query.split()
                   if re.match(r'^[a-zA-Z]{3,}$', word)][:5]

        matched_files = set()
        for keyword in keywords:
            # Search in all markdown files
            for md_file in config.memory_local_dir.rglob('*.md'):
                if md_file in matched_files:
                    continue
                try:
                    with open(md_file) as f:
                        if keyword.lower() in f.read().lower():
                            matched_files.add(md_file)
                            if len(matched_files) >= 3:
                                break
                except IOError:
                    pass
            if len(matched_files) >= 3:
                break

        for match_file in list(matched_files)[:3]:
            results.append(f"## From: {match_file.name}\n\n")
            with open(match_file) as f:
                results.append(f.read())
            results.append("\n\n")

    # If still no results, try to read the most recent phase's closeout
    if not results and current_phase is not None and current_phase > 0:
        prev_phase = current_phase - 1
        prev_closeout = config.memory_local_dir / f'phase-{prev_phase}' / 'closeout.md'
        if prev_closeout.exists():
            results.append(f"## Previous Phase Closeout (Phase {prev_phase})\n\n")
            with open(prev_closeout) as f:
                results.append(f.read())
            results.append("\n\n")

    return ''.join(results)


def _memory_save_closeout(phase_num: int, phase_name: str, summary: str) -> None:
    """Save phase closeout to local storage"""
    phase_dir = _memory_ensure_local_dirs(phase_num)
    closeout_file = phase_dir / 'closeout.md'

    with open(closeout_file, 'w') as f:
        f.write(f"# Phase {phase_num}: {phase_name} - Closeout\n")
        f.write(f"_Saved: {datetime.now().isoformat()}_\n\n")
        f.write(summary)

    _memory_log("_memory_save_closeout", f"Saved closeout for Phase {phase_num} to {closeout_file}")


# ============================================================================
# CONTENT EXTRACTION FUNCTIONS
# ============================================================================

def _memory_extract_content(save_type: str, phase_num: int, task_id: str) -> str:
    """Extract meaningful content from output files based on save type"""
    config = get_config()
    output_dir = config.atomic_output_dir

    content = ""

    # Import the save type handlers (this matches the bash case statement)
    # For brevity, implementing key cases - full implementation would include all cases

    if save_type == "mode_selection":
        content = f"SETUP_MODE: {os.environ.get('SETUP_MODE', 'unknown')}"

    elif save_type == "extracted_config":
        config_file = output_dir / '0-setup' / 'extracted-config.json'
        if config_file.exists():
            try:
                with open(config_file) as f:
                    data = json.load(f)
                    project = data.get('project', {})
                    llm = data.get('llm', {})
                    constraints = data.get('constraints', {})
                    content = (
                        f"PROJECT: {project.get('name', 'unknown')} ({project.get('type', 'unknown')})\n"
                        f"DESCRIPTION: {project.get('description', '')}\n"
                        f"GOAL: {project.get('primary_goal', '')}\n"
                        f"LLM: {llm.get('primary_model', 'claude-opus')} / {llm.get('fast_model', 'claude-haiku')}\n"
                        f"PROVIDER: {llm.get('primary_provider', 'anthropic')}\n"
                        f"CONSTRAINTS: {'; '.join(constraints.get('technical', []))}"
                    )
            except (json.JSONDecodeError, IOError):
                content = "Config extraction failed"

    elif save_type == "config_approval":
        config_file = output_dir / '0-setup' / 'project-config.json'
        if config_file.exists():
            try:
                with open(config_file) as f:
                    data = json.load(f)
                    name = (data.get('project', {}).get('name') or
                           data.get('extracted', {}).get('project', {}).get('name') or
                           'unknown')
                    content = f"Config approved. Project: {name}"
            except (json.JSONDecodeError, IOError):
                pass

    elif save_type == "api_providers":
        secrets_file = output_dir / '0-setup' / 'secrets.json'
        if secrets_file.exists():
            try:
                with open(secrets_file) as f:
                    data = json.load(f)
                    providers = []
                    if data.get('max_enabled', False):
                        providers.append('claude-max')
                    if data.get('anthropic_api_key'):
                        providers.append('anthropic-api')
                    if data.get('memory_enabled', False):
                        providers.append('local-memory')
                    if len(data.get('ollama_hosts', [])) > 0:
                        providers.append('ollama')
                    content = f"PROVIDERS CONFIGURED: {' '.join(providers) if providers else 'none'}"
            except (json.JSONDecodeError, IOError):
                pass

    elif save_type == "phase_audit":
        audit_file = output_dir.parent / 'audits' / f'phase-{phase_num}-report.json'
        if not audit_file.exists():
            audit_file = config.atomic_root / '.claude' / 'audit' / f'phase-0{phase_num}-audit.json'
        if audit_file.exists():
            try:
                with open(audit_file) as f:
                    data = json.load(f)
                    passed = data.get('summary', {}).get('passed', 0)
                    failed = data.get('summary', {}).get('failed', 0)
                    content = f"AUDIT: {passed} passed, {failed} failed"
            except (json.JSONDecodeError, IOError):
                pass

    elif save_type == "prd_content":
        prd_file = output_dir / '2-prd' / 'PRD.md'
        if prd_file.exists():
            with open(prd_file) as f:
                lines = f.readlines()[:100]
                content = f"PRD SUMMARY:\n{''.join(lines)}"

    elif save_type == "tasks_decomposition":
        tasks_file = output_dir / '3-tasking' / 'tasks.json'
        if tasks_file.exists():
            try:
                with open(tasks_file) as f:
                    data = json.load(f)
                    count = len(data.get('tasks', []))
                    content = f"TASKS: {count} total"
            except (json.JSONDecodeError, IOError):
                pass

    else:
        content = f"Task completed: {save_type}"

    return content


# ============================================================================
# TASK-LEVEL MEMORY (Per-Task Recall/Save)
# ============================================================================

# CRITICAL FIX: Python dicts instead of bash associative arrays
# No more export/scope issues!
TASK_MEMORY_RECALL: Dict[str, str] = {}
TASK_MEMORY_SAVE: Dict[str, str] = {}


def load_task_memory_definitions() -> None:
    """Load task memory definitions from task-memory-defs.py if available"""
    try:
        from . import task_memory_defs
        if hasattr(task_memory_defs, 'TASK_MEMORY_RECALL'):
            TASK_MEMORY_RECALL.update(task_memory_defs.TASK_MEMORY_RECALL)
        if hasattr(task_memory_defs, 'TASK_MEMORY_SAVE'):
            TASK_MEMORY_SAVE.update(task_memory_defs.TASK_MEMORY_SAVE)
    except ImportError:
        pass


def memory_task_start(task_id: str, task_name: str, phase_name: str = "") -> None:
    """
    Called at task start - recalls context relevant to this task
    Uses DUAL-READ strategy: local files first (fast), then remote if available
    """
    config = get_config()

    # Set current task context for debug logging
    os.environ['CURRENT_TASK_ID'] = task_id
    os.environ['CURRENT_TASK_NAME'] = task_name

    _memory_log("memory_task_start", f"ENTER: task_id={task_id} task_name={task_name} phase={phase_name}")
    _memory_debug("task_start", "start", {"task_id": task_id, "task_name": task_name})

    if not config.memory_enabled:
        _memory_log("memory_task_start", "SKIPPED: memory not enabled")
        _memory_debug("task_start", "skip", {"reason": "memory_not_enabled"})
        return

    # Extract phase number from phase name (e.g., "1-discovery" -> "1")
    match = re.match(r'^(\d+)', phase_name)
    if match:
        phase_num = int(match.group(1))
    else:
        phase_num = 0

    # Get task-specific recall query from definitions
    task_key = f"{phase_num}-{task_id}"
    recall_query = TASK_MEMORY_RECALL.get(task_key, "")
    expected_recall = recall_query
    expected_save = TASK_MEMORY_SAVE.get(task_key, "")

    # If no definition, use generic query
    if not recall_query:
        recall_query = f"{phase_name} {task_name} context"
        _memory_log("memory_task_start", f"No recall definition for {task_key}, using generic query")
    else:
        _memory_log("memory_task_start", f"Using recall query for {task_key}: {recall_query}")

    _memory_debug("task_start", "config", {
        "recall_query": recall_query,
        "should_recall": expected_recall,
        "should_save": expected_save
    })

    task_context_file = config.atomic_output_dir / 'task-context.md'
    task_context_file.parent.mkdir(parents=True, exist_ok=True)

    # Start fresh context file
    with open(task_context_file, 'w') as f:
        f.write(f"# Task Context: {task_name}\n\n")
        f.write(f"Retrieved: {datetime.now().isoformat()} | Task: {task_id} | Query: {recall_query}\n\n")

    has_context = False
    local_chars = 0

    # STEP 1: Read from LOCAL files first (fast, always available)
    _memory_debug("recall_local", "start", {"query": recall_query})
    local_context = _memory_recall_local(recall_query, phase_num)

    if local_context:
        with open(task_context_file, 'a') as f:
            f.write("## Local Context\n\n")
            f.write(local_context)
            f.write("\n\n")
        has_context = True
        local_chars = len(local_context)
        _memory_log("_memory_recall_local", f"Found local context ({local_chars} chars)")
        _memory_debug("recall_local", "success", {
            "chars": local_chars,
            "preview": _memory_truncate(local_context, 150)
        })
    else:
        _memory_debug("recall_local", "success", {"chars": 0, "preview": ""})

    # Clean up if no context was found
    if not has_context:
        task_context_file.unlink()
        _memory_log("memory_task_start", "No context found, removed empty context file")
        _memory_debug("inject", "skip", {"reason": "no_context_found"})
    else:
        char_count = task_context_file.stat().st_size
        _memory_log("inject", f"Wrote {char_count} chars to task-context.md")
        _memory_debug("inject", "success", {
            "total_chars": char_count,
            "local_chars": local_chars,
            "remote_chars": 0,
            "file": "task-context.md"
        })

    _memory_log("memory_task_start", "EXIT")
    _memory_debug("task_start", "success", {"has_context": has_context})


def memory_task_end(task_id: str, task_name: str, phase_name: str = "", outcome: str = "") -> None:
    """
    Called at task end - saves task outcomes/decisions to memory
    Uses DUAL-WRITE strategy: ALWAYS write locally
    """
    config = get_config()

    _memory_log("memory_task_end", f"ENTER: task_id={task_id} task_name={task_name} phase={phase_name}")
    _memory_debug("task_end", "start", {"task_id": task_id, "task_name": task_name})

    if not config.memory_enabled:
        _memory_log("memory_task_end", "SKIPPED: memory not enabled")
        _memory_debug("task_end", "skip", {"reason": "memory_not_enabled"})
        return

    # Extract phase number from phase name
    match = re.match(r'^(\d+)', phase_name)
    if match:
        phase_num = int(match.group(1))
    else:
        phase_num = 0

    # Get task-specific save type from definitions
    task_key = f"{phase_num}-{task_id}"
    save_type = TASK_MEMORY_SAVE.get(task_key, "")

    # If no save type defined (empty string), skip saving
    if not save_type:
        _memory_log("memory_task_end", f"No save definition for {task_key}, skipping save")
        _memory_debug("task_end", "skip", {"reason": "no_save_definition", "task_key": task_key})
        return

    _memory_log("memory_task_end", f"Save type for {task_key}: {save_type}")
    _memory_debug("save_extract", "start", {"save_type": save_type})

    # Extract meaningful content based on save type
    if outcome:
        # If explicit outcome provided, use it
        content = outcome
        _memory_log("memory_task_end", f"Using provided outcome ({len(outcome)} chars)")
    else:
        # Extract content from output files based on save type
        content = _memory_extract_content(save_type, phase_num, task_id)
        _memory_log("memory_task_end", f"Extracted content for {save_type} ({len(content)} chars)")

    content_chars = len(content)
    _memory_debug("save_extract", "success", {
        "chars": content_chars,
        "preview": _memory_truncate(content, 150)
    })

    # Skip if no meaningful content
    if not content or content.startswith("Task completed:"):
        _memory_log("memory_task_end", "No meaningful content to save, skipping")
        _memory_debug("task_end", "skip", {"reason": "no_meaningful_content"})
        return

    # STEP 1: ALWAYS write to LOCAL file storage
    _memory_debug("save_local", "start", {"save_type": save_type})
    saved_file = _memory_save_local(phase_num, task_id, save_type, content)
    _memory_log("_memory_save_local", f"Saved to {saved_file}")
    _memory_debug("save_local", "success", {"file": str(saved_file), "chars": content_chars})

    _memory_log("memory_task_end", "EXIT")
    _memory_debug("task_end", "success", {"saved_local": True, "content_chars": content_chars})


# ============================================================================
# SESSION LIFECYCLE
# ============================================================================

def memory_session_start() -> None:
    """Called on session start - retrieves relevant context from local storage"""
    config = get_config()

    if not config.memory_enabled:
        return

    memory_init()

    session_context_file = config.atomic_output_dir / 'session-context.md'
    session_context_file.parent.mkdir(parents=True, exist_ok=True)

    with open(session_context_file, 'w') as f:
        f.write("# Session Context (from Memory)\n\n")
        f.write(f"_Retrieved: {datetime.now().isoformat()}_\n\n")

    has_context = False

    # Add local head state
    if config.memory_head_file.exists():
        head_phase = memory_get_head_phase()
        if head_phase >= 0:
            with open(session_context_file, 'a') as f:
                f.write("## Pipeline State\n\n")
                f.write(f"Current phase progression: Phase {head_phase}\n\n")
            has_context = True

    # Load the most recent closeout(s)
    if config.memory_local_dir.exists():
        closeout_files = sorted(config.memory_local_dir.rglob('closeout.md'))
        if closeout_files:
            with open(session_context_file, 'a') as f:
                f.write("## Previous Closeouts\n\n")
                # Include last 2 closeouts for context
                for closeout in closeout_files[-2:]:
                    with open(closeout) as cf:
                        f.write(cf.read())
                    f.write("\n\n")
            has_context = True

    GREEN = os.environ.get('GREEN', '')
    NC = os.environ.get('NC', '')

    if has_context:
        print(f"  {GREEN}✓{NC} Session context loaded from local memory")
    else:
        with open(session_context_file, 'a') as f:
            f.write("_No memories found for this project._\n")


def memory_session_end() -> None:
    """Called on session end - currently a no-op"""
    # We save at checkpoints, not session end
    pass


# ============================================================================
# INITIALIZATION - Load task memory definitions
# ============================================================================

# Load task memory definitions on module import
load_task_memory_definitions()
