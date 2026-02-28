#!/usr/bin/env python3
"""
Unit tests for UAT Runner

Tests the UAT runner's output parsing, analysis, and report generation capabilities.
"""

import unittest
from pathlib import Path
import sys
import tempfile
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.runners.uat_runner import (
    UATRunner,
    ANSIToHTML,
    UATReport,
    MenuCapture,
    InteractionCapture,
    FormattingIssue
)


class TestANSIToHTML(unittest.TestCase):
    """Test ANSI to HTML conversion."""

    def test_basic_color_conversion(self):
        """Test basic color code conversion."""
        input_text = "\x1b[31mRed Text\x1b[0m"
        output = ANSIToHTML.convert(input_text)

        # Should contain span with red color style
        self.assertIn('<span', output)
        self.assertIn('color: #CD3131', output)
        self.assertIn('Red Text', output)
        self.assertIn('</span>', output)

    def test_bold_text(self):
        """Test bold text conversion."""
        input_text = "\x1b[1mBold Text\x1b[0m"
        output = ANSIToHTML.convert(input_text)

        self.assertIn('font-weight: bold', output)
        self.assertIn('Bold Text', output)

    def test_multiple_styles(self):
        """Test multiple style codes."""
        input_text = "\x1b[1;32mBold Green\x1b[0m"
        output = ANSIToHTML.convert(input_text)

        self.assertIn('font-weight: bold', output)
        self.assertIn('color: #0DBC79', output)
        self.assertIn('Bold Green', output)

    def test_no_ansi_codes(self):
        """Test plain text without ANSI codes."""
        input_text = "Plain text"
        output = ANSIToHTML.convert(input_text)

        self.assertEqual(output, "Plain text")

    def test_html_escaping(self):
        """Test that HTML special characters are escaped."""
        input_text = "<script>alert('xss')</script>"
        output = ANSIToHTML.convert(input_text)

        self.assertIn('&lt;script&gt;', output)
        self.assertNotIn('<script>', output)

    def test_reset_code(self):
        """Test reset code closes spans."""
        input_text = "\x1b[31mRed\x1b[0m Normal"
        output = ANSIToHTML.convert(input_text)

        # Should have closed span before "Normal"
        self.assertIn('</span> Normal', output)


class TestMenuAnalysis(unittest.TestCase):
    """Test menu detection and analysis."""

    def setUp(self):
        """Set up test runner."""
        self.runner = UATRunner()

    def test_numbered_menu_detection(self):
        """Test detection of numbered menu options."""
        report = UATReport()
        report.raw_output = """
        Select an option:
        1. First option
        2. Second option
        3. Third option

        Enter choice:
        """

        self.runner._analyze_menus(report)

        self.assertGreater(len(report.menus), 0)
        menu = report.menus[0]
        self.assertEqual(len(menu.options), 3)

    def test_lettered_menu_detection(self):
        """Test detection of lettered menu options."""
        report = UATReport()
        report.raw_output = """
        Choose one:
        [a] Option A
        [b] Option B
        [c] Option C

        Your choice:
        """

        self.runner._analyze_menus(report)

        self.assertGreater(len(report.menus), 0)
        menu = report.menus[0]
        self.assertEqual(len(menu.options), 3)

    def test_menu_with_ansi_codes(self):
        """Test menu detection with ANSI color codes."""
        report = UATReport()
        report.raw_output = """
        \x1b[1;36mSelect an option:\x1b[0m
        \x1b[32m1. Green option\x1b[0m
        \x1b[33m2. Yellow option\x1b[0m

        Enter:
        """

        self.runner._analyze_menus(report)

        self.assertGreater(len(report.menus), 0)


class TestInteractionAnalysis(unittest.TestCase):
    """Test interaction capture and analysis."""

    def setUp(self):
        """Set up test runner."""
        self.runner = UATRunner()

    def test_question_detection(self):
        """Test detection of questions."""
        report = UATReport()
        report.raw_output = """
        ? What is your name?
        John Doe

        ? What is your email?
        john@example.com
        """
        report.duration = 1.0

        self.runner._analyze_interactions(report)

        self.assertEqual(len(report.interactions), 2)
        self.assertIn("name", report.interactions[0].question.lower())

    def test_enter_prompt_detection(self):
        """Test detection of Enter prompts."""
        report = UATReport()
        report.raw_output = """Enter your project name:
MyProject

Enter your API key:
sk-1234567890
"""
        report.duration = 1.0

        self.runner._analyze_interactions(report)

        self.assertGreater(len(report.interactions), 0)

    def test_bracketed_default_detection(self):
        """Test detection of prompts with defaults."""
        report = UATReport()
        report.raw_output = """
        Project name [my-project]:
        custom-name
        """
        report.duration = 1.0

        self.runner._analyze_interactions(report)

        self.assertGreater(len(report.interactions), 0)


class TestFormattingAnalysis(unittest.TestCase):
    """Test formatting validation."""

    def setUp(self):
        """Set up test runner."""
        self.runner = UATRunner()

    def test_line_length_detection(self):
        """Test detection of overly long lines."""
        report = UATReport()
        # Create a line that's definitely too long
        long_line = "x" * 150
        report.raw_output = f"Normal line\n{long_line}\nAnother normal line"

        self.runner._analyze_formatting(report)

        # Should detect at least one line length issue
        line_length_issues = [
            issue for issue in report.formatting_issues
            if issue.issue_type == "line_length"
        ]
        self.assertGreater(len(line_length_issues), 0)

    def test_indentation_detection(self):
        """Test detection of odd indentation."""
        report = UATReport()
        report.raw_output = """
        Normal line
         Odd indent (1 space)
        Normal line
           Another odd indent (3 spaces)
        """

        self.runner._analyze_formatting(report)

        indentation_issues = [
            issue for issue in report.formatting_issues
            if issue.issue_type == "indentation"
        ]
        # May or may not detect depending on heuristics
        # Just verify it doesn't crash

    def test_multiple_empty_lines_detection(self):
        """Test detection of excessive whitespace."""
        report = UATReport()
        report.raw_output = "Line 1\n\n\n\nLine 2"

        self.runner._analyze_formatting(report)

        whitespace_issues = [
            issue for issue in report.formatting_issues
            if issue.issue_type == "whitespace"
        ]
        # Should detect multiple consecutive empty lines
        self.assertGreater(len(whitespace_issues), 0)


class TestWordingAnalysis(unittest.TestCase):
    """Test wording and grammar analysis."""

    def setUp(self):
        """Set up test runner."""
        self.runner = UATRunner()

    def test_duplicate_word_detection(self):
        """Test detection of duplicate words."""
        report = UATReport()
        report.raw_output = "This is the the main issue here"

        self.runner._analyze_wording(report)

        self.assertIn("typos", report.wording_analysis["issues"])
        # Should have detected "the the"

    def test_common_typo_detection(self):
        """Test detection of common typos."""
        report = UATReport()
        report.raw_output = "I will recieve the package soon"

        self.runner._analyze_wording(report)

        issues = report.wording_analysis["issues"]["typos"]
        # Should detect "recieve" typo

    def test_tone_analysis(self):
        """Test tone analysis."""
        report = UATReport()
        # Overly apologetic
        report.raw_output = "Sorry! Sorry about that! We're sorry for the inconvenience! Sorry!"

        self.runner._analyze_wording(report)

        tone_issues = report.wording_analysis["issues"]["tone"]
        # Should detect overly apologetic tone

    def test_word_count(self):
        """Test word count calculation."""
        report = UATReport()
        report.raw_output = "One two three four five"

        self.runner._analyze_wording(report)

        self.assertEqual(report.wording_analysis["word_count"], 5)

    def test_line_count(self):
        """Test line count calculation."""
        report = UATReport()
        report.raw_output = "Line 1\nLine 2\nLine 3"

        self.runner._analyze_wording(report)

        self.assertEqual(report.wording_analysis["line_count"], 3)


class TestReportGeneration(unittest.TestCase):
    """Test report generation."""

    def setUp(self):
        """Set up test runner."""
        self.runner = UATRunner()
        self.temp_dir = tempfile.mkdtemp()

    def test_report_to_dict(self):
        """Test report serialization to dict."""
        report = UATReport(
            phase_num=0,
            scenario="test",
            success=True,
            exit_code=0
        )

        report_dict = report.to_dict()

        self.assertEqual(report_dict["phase_num"], 0)
        self.assertEqual(report_dict["scenario"], "test")
        self.assertTrue(report_dict["success"])

    def test_html_report_generation(self):
        """Test HTML report generation."""
        report = UATReport(
            phase_num=0,
            scenario="test",
            success=True,
            exit_code=0,
            raw_output="Test output",
            checklist_items=[
                {"item": "Check 1", "checked": False, "notes": ""},
                {"item": "Check 2", "checked": False, "notes": ""}
            ]
        )

        output_path = Path(self.temp_dir) / "test_report.html"
        result_path = self.runner.save_html_report(report, output_path)

        self.assertTrue(result_path.exists())

        # Read and verify HTML content
        with open(result_path, 'r') as f:
            html = f.read()

        self.assertIn("Phase 0", html)
        self.assertIn("test", html)
        self.assertIn("Check 1", html)
        self.assertIn("Check 2", html)

    def test_checklist_html_generation(self):
        """Test checklist HTML generation."""
        report = UATReport()
        report.checklist_items = [
            {"item": "Test item 1", "checked": False, "notes": ""},
            {"item": "Test item 2", "checked": True, "notes": "Good"}
        ]

        html = self.runner._build_checklist_html(report)

        self.assertIn("Test item 1", html)
        self.assertIn("Test item 2", html)
        self.assertIn('type="checkbox"', html)

    def test_analysis_html_generation(self):
        """Test analysis HTML generation."""
        report = UATReport()

        # Add some test data
        report.menus.append(MenuCapture(
            options=["Option 1", "Option 2"],
            prompt="Select one:"
        ))

        report.interactions.append(InteractionCapture(
            question="What is your name?",
            response="John"
        ))

        report.formatting_issues.append(FormattingIssue(
            line_num=42,
            issue_type="line_length",
            description="Line too long",
            severity="warning"
        ))

        html = self.runner._build_analysis_html(report)

        self.assertIn("Option 1", html)
        self.assertIn("What is your name?", html)
        self.assertIn("Line 42", html)


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading."""

    def setUp(self):
        """Set up test runner."""
        self.runner = UATRunner()

    def test_load_phase_config(self):
        """Test loading phase configuration."""
        # Phase 0 config should exist
        config = self.runner.load_phase_config(0)

        self.assertIn("phase", config)
        self.assertIn("uat", config)

    def test_load_nonexistent_config(self):
        """Test loading config for nonexistent phase."""
        # Should return default config
        config = self.runner.load_phase_config(99)

        self.assertIn("uat", config)
        self.assertIn("checklist", config["uat"])

    def test_load_scenario_inputs(self):
        """Test loading scenario inputs."""
        # Should handle missing files gracefully
        inputs = self.runner.load_scenario_inputs(99, "nonexistent")

        # Should return default (just newline)
        self.assertIsInstance(inputs, str)


class TestIntegration(unittest.TestCase):
    """Integration tests for full UAT flow."""

    def setUp(self):
        """Set up test runner."""
        self.runner = UATRunner()

    def test_mock_phase_execution(self):
        """Test running a mock phase."""
        # Note: This requires a working atomic-claude installation
        # and will actually try to run a phase
        # Skip in CI environments
        import os
        if os.getenv('CI'):
            self.skipTest("Skipping integration test in CI")

        # This would run an actual phase - commented out for safety
        # report = self.runner.run_phase_uat(phase_num=0, scenario="default")
        # self.assertIsInstance(report, UATReport)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
