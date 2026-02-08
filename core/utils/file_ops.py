"""
File Operations Utilities

Provides common file and directory operations with error handling.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Any, List, Optional, Union


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        path: Directory path to create

    Returns:
        Path object for the created directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """
    Read text file contents.

    Args:
        file_path: Path to file
        encoding: File encoding (default: utf-8)

    Returns:
        File contents as string

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
    """
    file_path = Path(file_path)
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()


def write_file(
    file_path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8',
    create_parents: bool = True
) -> Path:
    """
    Write text to file.

    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding (default: utf-8)
        create_parents: Create parent directories if they don't exist

    Returns:
        Path object for the written file

    Raises:
        IOError: If file can't be written
    """
    file_path = Path(file_path)

    if create_parents:
        ensure_dir(file_path.parent)

    with open(file_path, 'w', encoding=encoding) as f:
        f.write(content)

    return file_path


def read_json(file_path: Union[str, Path]) -> Any:
    """
    Read and parse JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    file_path = Path(file_path)
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(
    file_path: Union[str, Path],
    data: Any,
    indent: int = 2,
    create_parents: bool = True
) -> Path:
    """
    Write data to JSON file.

    Args:
        file_path: Path to JSON file
        data: Data to serialize as JSON
        indent: JSON indentation (default: 2)
        create_parents: Create parent directories if they don't exist

    Returns:
        Path object for the written file

    Raises:
        IOError: If file can't be written
        TypeError: If data can't be serialized to JSON
    """
    file_path = Path(file_path)

    if create_parents:
        ensure_dir(file_path.parent)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent)

    return file_path


def copy_file(
    src: Union[str, Path],
    dst: Union[str, Path],
    create_parents: bool = True
) -> Path:
    """
    Copy file from source to destination.

    Args:
        src: Source file path
        dst: Destination file path
        create_parents: Create parent directories if they don't exist

    Returns:
        Path object for the destination file

    Raises:
        FileNotFoundError: If source doesn't exist
        IOError: If file can't be copied
    """
    src = Path(src)
    dst = Path(dst)

    if create_parents:
        ensure_dir(dst.parent)

    shutil.copy2(src, dst)
    return dst


def move_file(
    src: Union[str, Path],
    dst: Union[str, Path],
    create_parents: bool = True
) -> Path:
    """
    Move file from source to destination.

    Args:
        src: Source file path
        dst: Destination file path
        create_parents: Create parent directories if they don't exist

    Returns:
        Path object for the destination file

    Raises:
        FileNotFoundError: If source doesn't exist
        IOError: If file can't be moved
    """
    src = Path(src)
    dst = Path(dst)

    if create_parents:
        ensure_dir(dst.parent)

    shutil.move(str(src), str(dst))
    return dst


def delete_file(file_path: Union[str, Path]) -> bool:
    """
    Delete file if it exists.

    Args:
        file_path: Path to file

    Returns:
        True if file was deleted, False if it didn't exist

    Raises:
        IOError: If file exists but can't be deleted
    """
    file_path = Path(file_path)

    if file_path.exists():
        file_path.unlink()
        return True

    return False


def list_files(
    directory: Union[str, Path],
    pattern: str = "*",
    recursive: bool = False
) -> List[Path]:
    """
    List files in directory matching pattern.

    Args:
        directory: Directory to search
        pattern: Glob pattern to match (default: "*")
        recursive: Search recursively (default: False)

    Returns:
        List of Path objects for matching files

    Raises:
        FileNotFoundError: If directory doesn't exist
    """
    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if recursive:
        return list(directory.rglob(pattern))
    else:
        return list(directory.glob(pattern))


def file_exists(file_path: Union[str, Path]) -> bool:
    """Check if file exists."""
    return Path(file_path).exists()


def dir_exists(dir_path: Union[str, Path]) -> bool:
    """Check if directory exists."""
    path = Path(dir_path)
    return path.exists() and path.is_dir()


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get file size in bytes.

    Args:
        file_path: Path to file

    Returns:
        File size in bytes

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)
    return file_path.stat().st_size


def read_lines(file_path: Union[str, Path], encoding: str = 'utf-8') -> List[str]:
    """
    Read file and return list of lines.

    Args:
        file_path: Path to file
        encoding: File encoding (default: utf-8)

    Returns:
        List of lines (with newlines preserved)

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)
    with open(file_path, 'r', encoding=encoding) as f:
        return f.readlines()


def write_lines(
    file_path: Union[str, Path],
    lines: List[str],
    encoding: str = 'utf-8',
    create_parents: bool = True
) -> Path:
    """
    Write list of lines to file.

    Args:
        file_path: Path to file
        lines: List of lines to write
        encoding: File encoding (default: utf-8)
        create_parents: Create parent directories if they don't exist

    Returns:
        Path object for the written file
    """
    file_path = Path(file_path)

    if create_parents:
        ensure_dir(file_path.parent)

    with open(file_path, 'w', encoding=encoding) as f:
        f.writelines(lines)

    return file_path
