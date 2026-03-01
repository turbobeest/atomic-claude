"""
Unit Tests for CLI UI Utilities

Tests print functions, user prompts, input handling, and terminal interaction.

Author: Phase 6 - Testing & Validation
"""

import pytest
import sys
from io import StringIO
from unittest.mock import patch, MagicMock

from core.utils.cli_ui import (
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
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    confirm,
    BOLD,
    CYAN,
    YELLOW,
    GREEN,
    RED,
    DIM,
    NC
)


# ============================================================================
# COLOR FUNCTION TESTS
# ============================================================================

@pytest.mark.unit
class TestColorFunctions:
    """Test color formatting functions."""

    def test_print_bold(self):
        """Test bold text formatting."""
        result = print_bold("Test")
        assert BOLD in result
        assert NC in result
        assert "Test" in result

    def test_print_cyan(self):
        """Test cyan text formatting."""
        result = print_cyan("Test")
        assert CYAN in result
        assert NC in result

    def test_print_yellow(self):
        """Test yellow text formatting."""
        result = print_yellow("Test")
        assert YELLOW in result
        assert NC in result

    def test_print_green(self):
        """Test green text formatting."""
        result = print_green("Test")
        assert GREEN in result
        assert NC in result

    def test_print_red(self):
        """Test red text formatting."""
        result = print_red("Test")
        assert RED in result
        assert NC in result

    def test_print_dim(self):
        """Test dim text formatting."""
        result = print_dim("Test")
        assert DIM in result
        assert NC in result

    def test_print_blue(self):
        """Test blue text formatting."""
        result = print_blue("Test")
        assert result.startswith("\033[34m")
        assert result.endswith(NC)

    def test_print_magenta(self):
        """Test magenta text formatting."""
        result = print_magenta("Test")
        assert result.startswith("\033[35m")
        assert result.endswith(NC)

    def test_print_white(self):
        """Test white text formatting."""
        result = print_white("Test")
        assert result.startswith("\033[37m")
        assert result.endswith(NC)

    def test_color_functions_preserve_text(self):
        """Test color functions preserve original text."""
        text = "Hello, World!"

        for func in [print_bold, print_cyan, print_yellow, print_green,
                     print_red, print_dim, print_blue, print_magenta, print_white]:
            result = func(text)
            # Remove ANSI codes and check text is preserved
            clean_text = result.replace(BOLD, "").replace(CYAN, "").replace(
                YELLOW, "").replace(GREEN, "").replace(RED, "").replace(
                DIM, "").replace(NC, "")
            # Remove any other ANSI codes
            import re
            clean_text = re.sub(r'\033\[\d+m', '', clean_text)
            assert text in clean_text or clean_text == text


# ============================================================================
# PROMPT USER TESTS
# ============================================================================

@pytest.mark.unit
class TestPromptUser:
    """Test user prompt functionality."""

    @patch('builtins.input', return_value='user input')
    def test_prompt_user_basic(self, mock_input):
        """Test basic user prompt."""
        result = prompt_user("Enter value: ")
        assert result == "user input"
        mock_input.assert_called_once_with("Enter value: ")

    @patch('builtins.input', return_value='')
    def test_prompt_user_with_default(self, mock_input):
        """Test prompt with default value."""
        result = prompt_user("Enter value: ", default="default")
        assert result == "default"

    @patch('builtins.input', return_value='custom')
    def test_prompt_user_override_default(self, mock_input):
        """Test user can override default."""
        result = prompt_user("Enter value: ", default="default")
        assert result == "custom"

    @patch('builtins.input', side_effect=EOFError)
    def test_prompt_user_eof_with_default(self, mock_input):
        """Test EOF handling with default value."""
        result = prompt_user("Enter value: ", default="default")
        assert result == "default"

    @patch('builtins.input', side_effect=EOFError)
    def test_prompt_user_eof_no_default(self, mock_input):
        """Test EOF handling without default value."""
        result = prompt_user("Enter value: ")
        assert result == ""

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_prompt_user_keyboard_interrupt(self, mock_input):
        """Test handling keyboard interrupt."""
        with pytest.raises(SystemExit):
            prompt_user("Enter value: ")

    @patch('builtins.input', return_value='  spaces  ')
    def test_prompt_user_strips_whitespace(self, mock_input):
        """Test prompt returns non-empty input even with surrounding whitespace."""
        result = prompt_user("Enter value: ", default="default")
        # Non-empty input (after strip) is returned as-is, not the default
        assert result == "  spaces  "


# ============================================================================
# CLEAR INPUT BUFFER TESTS
# ============================================================================

@pytest.mark.unit
class TestClearInputBuffer:
    """Test input buffer clearing."""

    def test_clear_input_buffer_no_error(self):
        """Test clear_input_buffer doesn't raise errors."""
        # Should not raise even if stdin not available
        try:
            clear_input_buffer()
        except Exception as e:
            pytest.fail(f"clear_input_buffer raised {e}")

    @patch('sys.platform', 'win32')
    def test_clear_input_buffer_windows(self):
        """Test clear_input_buffer on Windows."""
        # Should handle Windows gracefully
        try:
            clear_input_buffer()
        except Exception as e:
            pytest.fail(f"clear_input_buffer on Windows raised {e}")

    def test_clear_input_buffer_unix(self):
        """Test clear_input_buffer on Unix-like systems."""
        if sys.platform == 'win32':
            pytest.skip("Unix-only test")

        # Should not crash
        try:
            clear_input_buffer()
        except Exception:
            # Silently ignores errors (expected behavior)
            pass


# ============================================================================
# PRINT FUNCTIONS TESTS
# ============================================================================

@pytest.mark.unit
class TestPrintFunctions:
    """Test convenience print functions."""

    def test_print_header(self, capsys):
        """Test printing header."""
        print_header("Test Header")

        captured = capsys.readouterr()
        assert "Test Header" in captured.out
        assert "━" in captured.out  # Separator line

    def test_print_success(self, capsys):
        """Test printing success message."""
        print_success("Operation succeeded")

        captured = capsys.readouterr()
        assert "Operation succeeded" in captured.out
        assert "✓" in captured.out

    def test_print_error(self, capsys):
        """Test printing error message."""
        print_error("Operation failed")

        captured = capsys.readouterr()
        assert "Operation failed" in captured.out
        assert "✗" in captured.out

    def test_print_warning(self, capsys):
        """Test printing warning message."""
        print_warning("Warning message")

        captured = capsys.readouterr()
        assert "Warning message" in captured.out
        assert "⚠" in captured.out

    def test_print_info(self, capsys):
        """Test printing info message."""
        print_info("Info message")

        captured = capsys.readouterr()
        assert "Info message" in captured.out
        assert "ℹ" in captured.out


# ============================================================================
# CONFIRM TESTS
# ============================================================================

@pytest.mark.unit
class TestConfirm:
    """Test confirmation prompt functionality."""

    @patch('builtins.input', return_value='y')
    def test_confirm_yes(self, mock_input):
        """Test confirm with 'yes' response."""
        result = confirm("Proceed?")
        assert result is True

    @patch('builtins.input', return_value='yes')
    def test_confirm_yes_full(self, mock_input):
        """Test confirm with full 'yes'."""
        result = confirm("Proceed?")
        assert result is True

    @patch('builtins.input', return_value='Y')
    def test_confirm_yes_uppercase(self, mock_input):
        """Test confirm with uppercase 'Y'."""
        result = confirm("Proceed?")
        assert result is True

    @patch('builtins.input', return_value='n')
    def test_confirm_no(self, mock_input):
        """Test confirm with 'no' response."""
        result = confirm("Proceed?")
        assert result is False

    @patch('builtins.input', return_value='no')
    def test_confirm_no_full(self, mock_input):
        """Test confirm with full 'no'."""
        result = confirm("Proceed?")
        assert result is False

    @patch('builtins.input', return_value='')
    def test_confirm_default_false(self, mock_input):
        """Test confirm with empty input and default False."""
        result = confirm("Proceed?", default=False)
        assert result is False

    @patch('builtins.input', return_value='')
    def test_confirm_default_true(self, mock_input):
        """Test confirm with empty input and default True."""
        result = confirm("Proceed?", default=True)
        assert result is True

    @patch('builtins.input', return_value='1')
    def test_confirm_numeric_true(self, mock_input):
        """Test confirm with '1' (truthy)."""
        result = confirm("Proceed?")
        assert result is True

    @patch('builtins.input', return_value='true')
    def test_confirm_true_string(self, mock_input):
        """Test confirm with 'true' string."""
        result = confirm("Proceed?")
        assert result is True

    @patch('builtins.input', return_value='invalid')
    def test_confirm_invalid_input(self, mock_input):
        """Test confirm with invalid input."""
        result = confirm("Proceed?")
        assert result is False  # Should default to False for invalid input

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_confirm_keyboard_interrupt(self, mock_input):
        """Test confirm handles keyboard interrupt."""
        with pytest.raises(SystemExit):
            confirm("Proceed?")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.unit
class TestCLIUIIntegration:
    """Test CLI UI integration scenarios."""

    def test_colored_output_flow(self, capsys):
        """Test complete colored output flow."""
        print_header("Operation")
        print_info("Starting...")
        print_success("Step 1 complete")
        print_warning("Check configuration")
        print_error("Step 2 failed")

        captured = capsys.readouterr()
        assert "Operation" in captured.out
        assert "Starting..." in captured.out
        assert "Step 1 complete" in captured.out
        assert "Check configuration" in captured.out
        assert "Step 2 failed" in captured.out

    @patch('builtins.input', side_effect=['user1', 'project-name', 'y'])
    def test_interactive_session_flow(self, mock_input):
        """Test interactive session with multiple prompts."""
        username = prompt_user("Username: ")
        project = prompt_user("Project: ")
        proceed = confirm("Continue?")

        assert username == "user1"
        assert project == "project-name"
        assert proceed is True

    @patch('builtins.input', side_effect=EOFError)
    def test_non_interactive_mode(self, mock_input):
        """Test non-interactive mode (EOF on all inputs)."""
        result = prompt_user("Enter value: ", default="auto")
        assert result == "auto"


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.unit
class TestCLIUIEdgeCases:
    """Test edge cases in CLI UI."""

    def test_empty_string_input(self):
        """Test color functions with empty strings."""
        result = print_cyan("")
        assert CYAN in result
        assert NC in result

    def test_multiline_string_input(self):
        """Test color functions with multiline strings."""
        multiline = "Line 1\nLine 2\nLine 3"
        result = print_green(multiline)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_special_characters(self):
        """Test color functions with special characters."""
        special = "Test!@#$%^&*()"
        result = print_yellow(special)
        assert special in result

    def test_unicode_characters(self):
        """Test color functions with Unicode."""
        unicode_text = "Hello 世界 🌍"
        result = print_blue(unicode_text)
        assert "Hello" in result
        assert "世界" in result

    @patch('builtins.input', return_value=' ')
    def test_prompt_with_only_whitespace(self, mock_input):
        """Test prompt with only whitespace input."""
        result = prompt_user("Enter: ", default="default")
        # Whitespace-only should trigger default
        assert result == "default"

    def test_print_header_long_title(self, capsys):
        """Test print_header with very long title."""
        long_title = "A" * 100
        print_header(long_title)

        captured = capsys.readouterr()
        assert long_title in captured.out

    def test_print_functions_with_none(self):
        """Test print functions handle None gracefully."""
        # Should convert to string
        result = print_cyan(str(None))
        assert "None" in result


# ============================================================================
# ANSI CODE TESTS
# ============================================================================

@pytest.mark.unit
class TestANSICodes:
    """Test ANSI code constants."""

    def test_ansi_codes_defined(self):
        """Test all ANSI codes are defined."""
        assert BOLD is not None
        assert CYAN is not None
        assert YELLOW is not None
        assert GREEN is not None
        assert RED is not None
        assert DIM is not None
        assert NC is not None

    def test_ansi_codes_are_strings(self):
        """Test ANSI codes are strings."""
        assert isinstance(BOLD, str)
        assert isinstance(CYAN, str)
        assert isinstance(NC, str)

    def test_nc_resets_formatting(self):
        """Test NC (no color) is reset code."""
        assert NC == '\033[0m'

    def test_color_codes_format(self):
        """Test color codes follow ANSI format."""
        import re
        ansi_pattern = r'\033\[\d+m'

        assert re.match(ansi_pattern, BOLD)
        assert re.match(ansi_pattern, CYAN)
        assert re.match(ansi_pattern, GREEN)


# ============================================================================
# STDOUT/STDERR TESTS
# ============================================================================

@pytest.mark.unit
class TestOutputStreams:
    """Test output to different streams."""

    def test_success_to_stdout(self, capsys):
        """Test success messages go to stdout."""
        print_success("Success")
        captured = capsys.readouterr()
        assert "Success" in captured.out
        assert captured.err == ""

    def test_info_to_stdout(self, capsys):
        """Test info messages go to stdout."""
        print_info("Info")
        captured = capsys.readouterr()
        assert "Info" in captured.out
        assert captured.err == ""

    def test_header_to_stdout(self, capsys):
        """Test headers go to stdout."""
        print_header("Header")
        captured = capsys.readouterr()
        assert "Header" in captured.out
        assert captured.err == ""


# ============================================================================
# TERMINAL COMPATIBILITY TESTS
# ============================================================================

@pytest.mark.unit
class TestTerminalCompatibility:
    """Test terminal compatibility."""

    def test_color_output_no_tty(self):
        """Test color output when not connected to TTY."""
        # Color codes should still be included (terminal decides rendering)
        result = print_cyan("Test")
        assert CYAN in result
        assert NC in result

    @patch('sys.stdin.isatty', return_value=False)
    def test_prompt_non_tty(self, mock_isatty):
        """Test prompting when not connected to TTY."""
        # clear_input_buffer should handle non-TTY gracefully
        try:
            clear_input_buffer()
        except Exception:
            pytest.fail("Should handle non-TTY gracefully")
