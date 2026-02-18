"""
CLI UI Utilities

Provides color-coded terminal output and user interaction functions.
"""

import sys
import select
import termios
import tty
from typing import Optional

# Enable readline for all input() calls in the process.
# This gives arrow-key navigation, cursor movement (Home/End),
# history recall (Up/Down), and emacs-style editing (Ctrl-A/E/K).
try:
    import readline  # noqa: F401
except ImportError:
    pass  # Windows or missing GNU readline


# ANSI color codes
BOLD = '\033[1m'
CYAN = '\033[36m'
YELLOW = '\033[33m'
GREEN = '\033[32m'
RED = '\033[31m'
DIM = '\033[2m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
WHITE = '\033[37m'
NC = '\033[0m'  # No Color / Reset


def print_bold(text: str) -> str:
    """Return bold text."""
    return f"{BOLD}{text}{NC}"


def print_cyan(text: str) -> str:
    """Return cyan text."""
    return f"{CYAN}{text}{NC}"


def print_yellow(text: str) -> str:
    """Return yellow text."""
    return f"{YELLOW}{text}{NC}"


def print_green(text: str) -> str:
    """Return green text."""
    return f"{GREEN}{text}{NC}"


def print_red(text: str) -> str:
    """Return red text."""
    return f"{RED}{text}{NC}"


def print_dim(text: str) -> str:
    """Return dim text."""
    return f"{DIM}{text}{NC}"


def print_blue(text: str) -> str:
    """Return blue text."""
    return f"{BLUE}{text}{NC}"


def print_magenta(text: str) -> str:
    """Return magenta text."""
    return f"{MAGENTA}{text}{NC}"


def print_white(text: str) -> str:
    """Return white text."""
    return f"{WHITE}{text}{NC}"


def prompt_user(prompt_text: str, default: Optional[str] = None) -> str:
    """
    Prompt user for input with optional default value.

    Args:
        prompt_text: The prompt to display
        default: Optional default value

    Returns:
        User input string (or default if empty and default provided)
    """
    try:
        if default:
            response = input(f"{prompt_text} [{default}]: ")
            return response if response.strip() else default
        else:
            return input(prompt_text)
    except EOFError:
        # Non-interactive mode
        if default:
            return default
        return ""
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        sys.exit(1)


def clear_input_buffer() -> None:
    """
    Clear stdin buffer to remove any pending input.

    This prevents accidental input carryover between prompts.
    """
    try:
        # Only works on Unix-like systems
        if sys.platform != 'win32':
            # Save terminal settings
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())

                # Drain stdin
                while select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read(1)
            finally:
                # Restore terminal settings
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    except:
        # Silently ignore errors (e.g., on Windows or non-TTY)
        pass


def print_header(title: str) -> None:
    """Print a formatted header."""
    print()
    print(print_cyan("━" * 60))
    print(print_bold(f"  {title}"))
    print(print_cyan("━" * 60))
    print()


def print_success(message: str) -> None:
    """Print a success message."""
    print(print_green(f"✓ {message}"))


def print_error(message: str) -> None:
    """Print an error message."""
    print(print_red(f"✗ {message}"))


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(print_yellow(f"⚠ {message}"))


def print_info(message: str) -> None:
    """Print an info message."""
    print(print_cyan(f"ℹ {message}"))


def prompt_menu(
    options: list[tuple[str, str]],
    header: str = "  Options:",
    default: int = 1,
) -> str:
    """
    Display a numbered menu and return the selected option key.

    Args:
        options: List of (key, label) tuples. key is returned on selection.
        header: Text displayed above the menu.
        default: 1-based index of default option (selected on bare Enter).

    Returns:
        The key string of the selected option.
    """
    print()
    print(header)
    print()
    for i, (key, label) in enumerate(options, 1):
        marker = " *" if i == default else ""
        print(f"    {i}. {label}{marker}")
    print()

    clear_input_buffer()
    choice = prompt_user(f"  Choice [default={default}]: ").strip()

    if not choice:
        return options[default - 1][0]

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return options[idx][0]
    except ValueError:
        pass

    # If typed text matches a key directly, accept it
    choice_lower = choice.lower()
    for key, _label in options:
        if key.lower() == choice_lower:
            return key

    return options[default - 1][0]


def confirm(prompt_text: str, default: bool = False) -> bool:
    """
    Ask user for yes/no confirmation.

    Args:
        prompt_text: The question to ask
        default: Default value if user presses enter

    Returns:
        True if user confirmed, False otherwise
    """
    default_str = "Y/n" if default else "y/N"
    response = prompt_user(f"{prompt_text} ({default_str}): ")

    if not response.strip():
        return default

    return response.lower() in ['y', 'yes', 'true', '1']
