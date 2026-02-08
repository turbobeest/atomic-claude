"""
Core utilities package.

Provides common utilities for file operations, CLI UI, and other shared functionality.
"""

from .cli_ui import (
    print_bold,
    print_cyan,
    print_yellow,
    print_green,
    print_red,
    print_dim,
    print_blue,
    print_magenta,
    print_white,
    prompt_user,
    clear_input_buffer,
)

from .file_ops import (
    ensure_dir,
    read_file,
    write_file,
    read_json,
    write_json,
    copy_file,
    move_file,
    delete_file,
    list_files,
)

__all__ = [
    # CLI UI
    'print_bold',
    'print_cyan',
    'print_yellow',
    'print_green',
    'print_red',
    'print_dim',
    'print_blue',
    'print_magenta',
    'print_white',
    'prompt_user',
    'clear_input_buffer',
    # File Operations
    'ensure_dir',
    'read_file',
    'write_file',
    'read_json',
    'write_json',
    'copy_file',
    'move_file',
    'delete_file',
    'list_files',
]
