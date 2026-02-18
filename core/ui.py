"""
UI Module

Console user interface utilities.
"""

# Enable readline for all input() calls in the process.
# Gives arrow-key navigation, history (Up/Down), Home/End, Ctrl-A/E/K.
try:
    import readline  # noqa: F401
except ImportError:
    pass  # Windows or missing GNU readline


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


def wrap_text(text: str, width: int = 70, indent: str = "    ") -> list:
    """Wrap LLM output text preserving structure.

    Preserves:
      - Paragraph breaks (blank lines)
      - Bullet/list items (lines starting with - * or digits)
      - Indentation within structured blocks
      - Code fence blocks (``` ... ```)

    Returns list of lines ready to print (indent already applied).
    """
    if not text:
        return []

    lines = text.split('\n')
    result = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Track code fences — pass through verbatim
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            result.append(indent + stripped)
            continue

        if in_code_block:
            result.append(indent + line.rstrip())
            continue

        # Blank lines → preserve as paragraph breaks
        if not stripped:
            result.append('')
            continue

        # Detect structured lines: bullets, numbered items, headers
        is_structured = (
            stripped.startswith(('- ', '* ', '• '))
            or (len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in '.)')
            or (len(stripped) > 3 and stripped[:2].isdigit() and stripped[2] in '.)')
            or stripped.startswith('#')
            or stripped.startswith('>')
        )

        # Preserve leading whitespace for nested items
        leading = len(line) - len(line.lstrip())
        extra_indent = '  ' * (leading // 2) if leading > 0 and is_structured else ''

        # Word-wrap long lines, preserving structure prefix
        if len(stripped) <= width:
            result.append(indent + extra_indent + stripped)
        else:
            # Wrap within the line
            words = stripped.split()
            current = []
            length = 0
            first = True

            for word in words:
                if length + len(word) + len(current) > width and current:
                    result.append(indent + extra_indent + ' '.join(current))
                    current = [word]
                    length = len(word)
                    if first and is_structured:
                        # Continuation lines get extra indent under the bullet
                        extra_indent += '  '
                        first = False
                else:
                    current.append(word)
                    length += len(word)

            if current:
                result.append(indent + extra_indent + ' '.join(current))

    # Trim leading/trailing blank lines
    while result and result[0] == '':
        result.pop(0)
    while result and result[-1] == '':
        result.pop()

    return result


def print_llm_output(text: str, width: int = 70, indent: str = "    "):
    """Print LLM output with proper formatting."""
    for line in wrap_text(text, width, indent):
        print(line)
