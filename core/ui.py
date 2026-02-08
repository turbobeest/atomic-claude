"""
UI Module

Console user interface utilities.
Extracted from: lib/atomic.sh UI functions
"""


def phase_header(phase_name: str):
    """Display phase header."""
    print("\n" + "="*80)
    print(f"  {phase_name.upper()}")
    print("="*80 + "\n")


def phase_complete(phase_name: str):
    """Display phase completion message."""
    print("\n" + "="*80)
    print(f"  ✅ {phase_name.upper()} COMPLETE")
    print("="*80 + "\n")


def task_header(task_id: str, task_name: str):
    """Display task header."""
    print(f"\n⚡ Task {task_id}: {task_name}")
    print("-" * 60)


def success(message: str):
    """Display success message."""
    print(f"✅ {message}")


def error(message: str):
    """Display error message."""
    print(f"❌ {message}")


def warning(message: str):
    """Display warning message."""
    print(f"⚠️  {message}")


def info(message: str):
    """Display info message."""
    print(f"ℹ️  {message}")


def step(message: str):
    """Display step message."""
    print(f"  → {message}")


# TODO: Extract more UI functions from atomic.sh:
# - atomic_step()
# - atomic_success()
# - atomic_error()
# - atomic_warn()
# - atomic_info()
# - Progress bars
# - Spinners
