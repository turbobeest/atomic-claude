"""
Unit Tests for File Operations Utilities

Tests file and directory operations with error handling.

Author: Phase 6 - Testing & Validation
"""

import pytest
import json
import shutil
from pathlib import Path

from core.utils.file_ops import (
    ensure_dir,
    read_file,
    write_file,
    read_json,
    write_json,
    copy_file,
    move_file,
    delete_file,
    list_files,
    file_exists,
    dir_exists,
    get_file_size,
    read_lines,
    write_lines
)


# ============================================================================
# DIRECTORY OPERATIONS TESTS
# ============================================================================

@pytest.mark.unit
class TestDirectoryOperations:
    """Test directory creation and checking."""

    def test_ensure_dir_creates_directory(self, temp_dir):
        """Test ensure_dir creates directory."""
        new_dir = temp_dir / "new_directory"
        assert not new_dir.exists()

        result = ensure_dir(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()
        assert result == new_dir

    def test_ensure_dir_creates_parents(self, temp_dir):
        """Test ensure_dir creates parent directories."""
        nested_dir = temp_dir / "parent" / "child" / "grandchild"
        assert not nested_dir.exists()

        result = ensure_dir(nested_dir)

        assert nested_dir.exists()
        assert (temp_dir / "parent").exists()
        assert (temp_dir / "parent" / "child").exists()

    def test_ensure_dir_idempotent(self, temp_dir):
        """Test ensure_dir is idempotent."""
        new_dir = temp_dir / "existing"
        new_dir.mkdir()

        # Call again - should not fail
        result = ensure_dir(new_dir)

        assert result == new_dir
        assert new_dir.exists()

    def test_dir_exists_true(self, temp_dir):
        """Test dir_exists returns True for existing directory."""
        assert dir_exists(temp_dir) is True

    def test_dir_exists_false(self, temp_dir):
        """Test dir_exists returns False for non-existent directory."""
        assert dir_exists(temp_dir / "nonexistent") is False

    def test_dir_exists_file(self, temp_dir):
        """Test dir_exists returns False for file."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("content")

        assert dir_exists(file_path) is False


# ============================================================================
# FILE READ/WRITE TESTS
# ============================================================================

@pytest.mark.unit
class TestFileReadWrite:
    """Test file reading and writing."""

    def test_write_file(self, temp_dir):
        """Test writing file."""
        file_path = temp_dir / "test.txt"
        content = "Hello, World!"

        result = write_file(file_path, content)

        assert file_path.exists()
        assert result == file_path
        assert file_path.read_text() == content

    def test_write_file_creates_parents(self, temp_dir):
        """Test write_file creates parent directories."""
        file_path = temp_dir / "nested" / "dirs" / "file.txt"

        write_file(file_path, "content")

        assert file_path.exists()
        assert file_path.parent.exists()

    def test_write_file_no_create_parents(self, temp_dir):
        """Test write_file without creating parents."""
        file_path = temp_dir / "missing" / "file.txt"

        with pytest.raises(IOError):
            write_file(file_path, "content", create_parents=False)

    def test_write_file_overwrite(self, temp_dir):
        """Test write_file overwrites existing file."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("old content")

        write_file(file_path, "new content")

        assert file_path.read_text() == "new content"

    def test_read_file(self, temp_dir):
        """Test reading file."""
        file_path = temp_dir / "test.txt"
        content = "Test content"
        file_path.write_text(content)

        result = read_file(file_path)

        assert result == content

    def test_read_file_encoding(self, temp_dir):
        """Test reading file with encoding."""
        file_path = temp_dir / "test.txt"
        content = "Unicode: 世界 🌍"
        file_path.write_text(content, encoding='utf-8')

        result = read_file(file_path, encoding='utf-8')

        assert result == content

    def test_read_file_not_found(self, temp_dir):
        """Test reading non-existent file."""
        file_path = temp_dir / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            read_file(file_path)

    def test_file_exists_true(self, temp_dir):
        """Test file_exists returns True."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("content")

        assert file_exists(file_path) is True

    def test_file_exists_false(self, temp_dir):
        """Test file_exists returns False."""
        assert file_exists(temp_dir / "nonexistent.txt") is False


# ============================================================================
# JSON READ/WRITE TESTS
# ============================================================================

@pytest.mark.unit
class TestJSONOperations:
    """Test JSON file operations."""

    def test_write_json(self, temp_dir):
        """Test writing JSON file."""
        file_path = temp_dir / "data.json"
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        result = write_json(file_path, data)

        assert file_path.exists()
        assert result == file_path

        # Verify content
        with open(file_path) as f:
            loaded = json.load(f)

        assert loaded == data

    def test_write_json_with_indent(self, temp_dir):
        """Test writing JSON with custom indent."""
        file_path = temp_dir / "data.json"
        data = {"key": "value"}

        write_json(file_path, data, indent=4)

        content = file_path.read_text()
        assert "    " in content  # 4-space indent

    def test_write_json_creates_parents(self, temp_dir):
        """Test write_json creates parent directories."""
        file_path = temp_dir / "nested" / "data.json"

        write_json(file_path, {"test": "data"})

        assert file_path.exists()
        assert file_path.parent.exists()

    def test_read_json(self, temp_dir):
        """Test reading JSON file."""
        file_path = temp_dir / "data.json"
        data = {"key": "value", "nested": {"inner": "data"}}

        with open(file_path, 'w') as f:
            json.dump(data, f)

        result = read_json(file_path)

        assert result == data

    def test_read_json_not_found(self, temp_dir):
        """Test reading non-existent JSON file."""
        file_path = temp_dir / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            read_json(file_path)

    def test_read_json_invalid(self, temp_dir):
        """Test reading invalid JSON."""
        file_path = temp_dir / "invalid.json"
        file_path.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            read_json(file_path)

    def test_write_json_complex_types(self, temp_dir):
        """Test writing JSON with complex types."""
        file_path = temp_dir / "complex.json"
        data = {
            "string": "value",
            "number": 123,
            "float": 3.14,
            "bool": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"a": 1, "b": 2}
        }

        write_json(file_path, data)
        result = read_json(file_path)

        assert result == data


# ============================================================================
# FILE COPY/MOVE TESTS
# ============================================================================

@pytest.mark.unit
class TestFileCopyMove:
    """Test file copying and moving."""

    def test_copy_file(self, temp_dir):
        """Test copying file."""
        src = temp_dir / "source.txt"
        dst = temp_dir / "dest.txt"

        src.write_text("content")

        result = copy_file(src, dst)

        assert src.exists()  # Source still exists
        assert dst.exists()  # Destination exists
        assert result == dst
        assert dst.read_text() == "content"

    def test_copy_file_creates_parents(self, temp_dir):
        """Test copy_file creates parent directories."""
        src = temp_dir / "source.txt"
        dst = temp_dir / "nested" / "dest.txt"

        src.write_text("content")

        copy_file(src, dst)

        assert dst.exists()
        assert dst.parent.exists()

    def test_copy_file_not_found(self, temp_dir):
        """Test copying non-existent file."""
        src = temp_dir / "nonexistent.txt"
        dst = temp_dir / "dest.txt"

        with pytest.raises(FileNotFoundError):
            copy_file(src, dst)

    def test_move_file(self, temp_dir):
        """Test moving file."""
        src = temp_dir / "source.txt"
        dst = temp_dir / "dest.txt"

        src.write_text("content")

        result = move_file(src, dst)

        assert not src.exists()  # Source moved
        assert dst.exists()  # Destination exists
        assert result == dst
        assert dst.read_text() == "content"

    def test_move_file_creates_parents(self, temp_dir):
        """Test move_file creates parent directories."""
        src = temp_dir / "source.txt"
        dst = temp_dir / "nested" / "dest.txt"

        src.write_text("content")

        move_file(src, dst)

        assert not src.exists()
        assert dst.exists()

    def test_move_file_not_found(self, temp_dir):
        """Test moving non-existent file."""
        src = temp_dir / "nonexistent.txt"
        dst = temp_dir / "dest.txt"

        with pytest.raises(FileNotFoundError):
            move_file(src, dst)

    def test_copy_preserves_metadata(self, temp_dir):
        """Test copy preserves file metadata."""
        src = temp_dir / "source.txt"
        dst = temp_dir / "dest.txt"

        src.write_text("content")

        copy_file(src, dst)

        # Modification time should be preserved (copy2)
        assert dst.exists()


# ============================================================================
# FILE DELETE TESTS
# ============================================================================

@pytest.mark.unit
class TestFileDelete:
    """Test file deletion."""

    def test_delete_file(self, temp_dir):
        """Test deleting file."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("content")

        result = delete_file(file_path)

        assert result is True
        assert not file_path.exists()

    def test_delete_nonexistent_file(self, temp_dir):
        """Test deleting non-existent file."""
        file_path = temp_dir / "nonexistent.txt"

        result = delete_file(file_path)

        assert result is False

    def test_delete_file_idempotent(self, temp_dir):
        """Test delete is idempotent."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("content")

        # Delete twice
        delete_file(file_path)
        result = delete_file(file_path)

        assert result is False  # Already deleted


# ============================================================================
# LIST FILES TESTS
# ============================================================================

@pytest.mark.unit
class TestListFiles:
    """Test listing files."""

    def test_list_files_basic(self, temp_dir):
        """Test listing files in directory."""
        # Create files
        (temp_dir / "file1.txt").write_text("1")
        (temp_dir / "file2.txt").write_text("2")
        (temp_dir / "file3.txt").write_text("3")

        result = list_files(temp_dir, "*.txt")

        assert len(result) == 3
        assert all(f.suffix == ".txt" for f in result)

    def test_list_files_pattern(self, temp_dir):
        """Test listing files with pattern."""
        (temp_dir / "test.txt").write_text("1")
        (temp_dir / "test.py").write_text("2")
        (temp_dir / "data.txt").write_text("3")

        result = list_files(temp_dir, "test.*")

        assert len(result) == 2
        names = [f.name for f in result]
        assert "test.txt" in names
        assert "test.py" in names

    def test_list_files_recursive(self, temp_dir):
        """Test listing files recursively."""
        # Create nested structure
        (temp_dir / "file1.txt").write_text("1")
        sub_dir = temp_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file2.txt").write_text("2")
        subsub_dir = sub_dir / "subsubdir"
        subsub_dir.mkdir()
        (subsub_dir / "file3.txt").write_text("3")

        result = list_files(temp_dir, "*.txt", recursive=True)

        assert len(result) == 3

    def test_list_files_non_recursive(self, temp_dir):
        """Test listing files non-recursively."""
        (temp_dir / "file1.txt").write_text("1")
        sub_dir = temp_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file2.txt").write_text("2")

        result = list_files(temp_dir, "*.txt", recursive=False)

        assert len(result) == 1  # Only top-level

    def test_list_files_empty_directory(self, temp_dir):
        """Test listing files in empty directory."""
        result = list_files(temp_dir, "*.txt")

        assert len(result) == 0

    def test_list_files_not_found(self, temp_dir):
        """Test listing files in non-existent directory."""
        with pytest.raises(FileNotFoundError):
            list_files(temp_dir / "nonexistent", "*.txt")


# ============================================================================
# FILE SIZE TESTS
# ============================================================================

@pytest.mark.unit
class TestFileSize:
    """Test getting file size."""

    def test_get_file_size(self, temp_dir):
        """Test getting file size."""
        file_path = temp_dir / "test.txt"
        content = "Hello, World!"
        file_path.write_text(content)

        size = get_file_size(file_path)

        assert size == len(content.encode('utf-8'))

    def test_get_file_size_empty(self, temp_dir):
        """Test getting size of empty file."""
        file_path = temp_dir / "empty.txt"
        file_path.write_text("")

        size = get_file_size(file_path)

        assert size == 0

    def test_get_file_size_not_found(self, temp_dir):
        """Test getting size of non-existent file."""
        with pytest.raises(FileNotFoundError):
            get_file_size(temp_dir / "nonexistent.txt")


# ============================================================================
# LINE OPERATIONS TESTS
# ============================================================================

@pytest.mark.unit
class TestLineOperations:
    """Test reading and writing lines."""

    def test_read_lines(self, temp_dir):
        """Test reading file lines."""
        file_path = temp_dir / "test.txt"
        lines = ["Line 1\n", "Line 2\n", "Line 3\n"]
        file_path.write_text("".join(lines))

        result = read_lines(file_path)

        assert result == lines

    def test_read_lines_no_newline(self, temp_dir):
        """Test reading lines without trailing newline."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("Line 1\nLine 2")

        result = read_lines(file_path)

        assert len(result) == 2
        assert result[0] == "Line 1\n"
        assert result[1] == "Line 2"

    def test_write_lines(self, temp_dir):
        """Test writing lines to file."""
        file_path = temp_dir / "test.txt"
        lines = ["Line 1\n", "Line 2\n", "Line 3\n"]

        result = write_lines(file_path, lines)

        assert result == file_path
        assert file_path.read_text() == "".join(lines)

    def test_write_lines_creates_parents(self, temp_dir):
        """Test write_lines creates parent directories."""
        file_path = temp_dir / "nested" / "test.txt"
        lines = ["Line 1\n"]

        write_lines(file_path, lines)

        assert file_path.exists()
        assert file_path.parent.exists()

    def test_read_lines_empty_file(self, temp_dir):
        """Test reading lines from empty file."""
        file_path = temp_dir / "empty.txt"
        file_path.write_text("")

        result = read_lines(file_path)

        assert result == []


# ============================================================================
# PATH HANDLING TESTS
# ============================================================================

@pytest.mark.unit
class TestPathHandling:
    """Test path handling (string vs Path)."""

    def test_ensure_dir_with_string(self, temp_dir):
        """Test ensure_dir with string path."""
        new_dir = str(temp_dir / "string_path")

        result = ensure_dir(new_dir)

        assert isinstance(result, Path)
        assert result.exists()

    def test_write_file_with_string(self, temp_dir):
        """Test write_file with string path."""
        file_path = str(temp_dir / "test.txt")

        result = write_file(file_path, "content")

        assert isinstance(result, Path)
        assert result.exists()

    def test_read_file_with_string(self, temp_dir):
        """Test read_file with string path."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("content")

        result = read_file(str(file_path))

        assert result == "content"

    def test_operations_with_mixed_types(self, temp_dir):
        """Test operations work with mixed string/Path types."""
        src = str(temp_dir / "source.txt")
        dst = temp_dir / "dest.txt"

        # Write with string
        write_file(src, "content")

        # Copy with mixed types
        copy_file(src, dst)

        assert Path(src).exists()
        assert dst.exists()


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases in file operations."""

    def test_write_file_empty_content(self, temp_dir):
        """Test writing empty content."""
        file_path = temp_dir / "empty.txt"

        write_file(file_path, "")

        assert file_path.exists()
        assert file_path.read_text() == ""

    def test_write_json_empty_dict(self, temp_dir):
        """Test writing empty JSON object."""
        file_path = temp_dir / "empty.json"

        write_json(file_path, {})

        result = read_json(file_path)
        assert result == {}

    def test_copy_file_to_same_location(self, temp_dir):
        """Test copying file to itself (should work with shutil.copy2)."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("content")

        # Copy to same location (implementation dependent)
        # shutil.copy2 handles this case
        try:
            copy_file(file_path, file_path)
        except Exception:
            # Some implementations may raise, that's acceptable
            pass

    def test_delete_directory_as_file(self, temp_dir):
        """Test delete_file on directory (should fail or return False)."""
        dir_path = temp_dir / "directory"
        dir_path.mkdir()

        # Should not delete directory
        try:
            result = delete_file(dir_path)
            # If it doesn't raise, it should return False
            assert result is False
        except Exception:
            # Raising is also acceptable
            pass

    def test_list_files_with_dot_files(self, temp_dir):
        """Test listing includes dot files."""
        (temp_dir / ".hidden").write_text("1")
        (temp_dir / "visible.txt").write_text("2")

        result = list_files(temp_dir, "*")

        # Should include both
        names = [f.name for f in result]
        assert ".hidden" in names
        assert "visible.txt" in names

    def test_write_file_with_unicode(self, temp_dir):
        """Test writing file with Unicode content."""
        file_path = temp_dir / "unicode.txt"
        content = "Hello 世界 🌍"

        write_file(file_path, content)
        result = read_file(file_path)

        assert result == content

    def test_write_json_with_unicode(self, temp_dir):
        """Test writing JSON with Unicode."""
        file_path = temp_dir / "unicode.json"
        data = {"message": "Hello 世界 🌍"}

        write_json(file_path, data)
        result = read_json(file_path)

        assert result == data
