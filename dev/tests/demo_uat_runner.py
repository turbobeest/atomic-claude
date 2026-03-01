#!/usr/bin/env python3
"""
UAT Runner Demonstration

Demonstrates the UAT runner with a simple mock test showing HTML report generation.
This doesn't run an actual phase - it creates a mock report to show features.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dev.tests.runners.uat_runner import (
    UATRunner,
    UATReport,
    MenuCapture,
    InteractionCapture,
    FormattingIssue
)


def create_mock_report() -> UATReport:
    """Create a mock UAT report with sample data."""

    # Create report
    report = UATReport(
        phase_num=0,
        scenario="demo",
        timestamp="2024-02-06T17:00:00",
        duration=45.5,
        success=True,
        exit_code=0
    )

    # Add mock terminal output with ANSI codes
    report.raw_output = """
\x1b[1;36m================================================================================
  PHASE 0: SETUP
================================================================================\x1b[0m

\x1b[1mTask 001: Setup Introduction\x1b[0m

Welcome to Atomic Claude 2.0!

\x1b[1;33mConfiguration Mode:\x1b[0m
\x1b[32m1. Guided Mode\x1b[0m - Interactive setup with detailed prompts
\x1b[32m2. Quick Mode\x1b[0m - Use sensible defaults
\x1b[32m3. Document Mode\x1b[0m - Load from setup.md

\x1b[1mSelect mode:\x1b[0m 1

\x1b[1;32m✓ Guided mode selected\x1b[0m

\x1b[1mTask 002: Project Configuration\x1b[0m

\x1b[1m? What is your project name?\x1b[0m
my-awesome-project

\x1b[1m? What is your project description?\x1b[0m
A demonstration of the UAT runner

\x1b[1m? Select your tech stack:\x1b[0m
[a] Python
[b] Node.js
[c] Go
[d] Rust

Your choice: a

\x1b[1;32m✓ Python selected\x1b[0m

\x1b[1mTask 003: Configuration Review\x1b[0m

\x1b[1;36mProject Configuration:\x1b[0m
  Name:        my-awesome-project
  Description: A demonstration of the UAT runner
  Tech Stack:  Python
  Provider:    Anthropic
  Model:       Claude Sonnet 4.5

\x1b[1mApprove this configuration? (y/n):\x1b[0m y

\x1b[1;32m✓ Configuration approved\x1b[0m

\x1b[1;32m================================================================================
  PHASE 0 COMPLETE
================================================================================\x1b[0m

All tasks completed successfully!
    """

    # Add detected menus
    menu1 = MenuCapture()
    menu1.options = [
        "1. Guided Mode - Interactive setup with detailed prompts",
        "2. Quick Mode - Use sensible defaults",
        "3. Document Mode - Load from setup.md"
    ]
    menu1.prompt = "Select mode:"
    menu1.context = "Configuration Mode:"
    report.menus.append(menu1)

    menu2 = MenuCapture()
    menu2.options = [
        "[a] Python",
        "[b] Node.js",
        "[c] Go",
        "[d] Rust"
    ]
    menu2.prompt = "Your choice:"
    menu2.context = "Select your tech stack:"
    report.menus.append(menu2)

    # Add detected interactions
    interaction1 = InteractionCapture(
        question="? What is your project name?",
        response="my-awesome-project",
        timestamp=10.0
    )
    report.interactions.append(interaction1)

    interaction2 = InteractionCapture(
        question="? What is your project description?",
        response="A demonstration of the UAT runner",
        timestamp=15.0
    )
    report.interactions.append(interaction2)

    interaction3 = InteractionCapture(
        question="Approve this configuration? (y/n):",
        response="y",
        timestamp=40.0
    )
    report.interactions.append(interaction3)

    # Add some formatting issues (demo purposes)
    issue1 = FormattingIssue(
        line_num=5,
        issue_type="info",
        description="Banner uses 80 character width (good)",
        severity="info"
    )
    report.formatting_issues.append(issue1)

    # Add wording analysis
    report.wording_analysis = {
        "issues": {
            "typos": [],
            "unclear": [],
            "grammar": [],
            "tone": []
        },
        "word_count": 95,
        "line_count": 45
    }

    # Add checklist items
    report.checklist_items = [
        {"item": "All prompts are clear and professional", "checked": False, "notes": ""},
        {"item": "Menu options are logical and complete", "checked": False, "notes": ""},
        {"item": "Error messages are helpful and actionable", "checked": False, "notes": ""},
        {"item": "Progress indicators work correctly", "checked": False, "notes": ""},
        {"item": "Colors and formatting enhance readability", "checked": False, "notes": ""},
        {"item": "No typos or grammatical errors", "checked": False, "notes": ""},
        {"item": "Interactive flows are intuitive", "checked": False, "notes": ""},
        {"item": "Configuration display is well-organized", "checked": False, "notes": ""},
    ]

    return report


def main():
    """Run the demonstration."""
    print("=" * 80)
    print("  UAT RUNNER DEMONSTRATION")
    print("=" * 80)
    print()
    print("This demonstration shows the UAT runner capabilities:")
    print("- Captures terminal output with ANSI colors")
    print("- Detects menus and interactive prompts")
    print("- Analyzes formatting and wording")
    print("- Generates professional HTML reports")
    print()

    # Create mock report
    print("Creating mock UAT report...")
    report = create_mock_report()

    # Initialize runner
    runner = UATRunner()

    # Generate HTML report
    output_path = Path("demo_uat_report.html")
    print(f"Generating HTML report: {output_path}")

    runner.save_html_report(report, output_path)

    # Display summary
    print()
    print("=" * 80)
    print("  REPORT SUMMARY")
    print("=" * 80)
    print()
    print(f"Phase:         {report.phase_num}")
    print(f"Scenario:      {report.scenario}")
    print(f"Duration:      {report.duration:.2f}s")
    print(f"Success:       {'✓ PASSED' if report.success else '✗ FAILED'}")
    print(f"Exit Code:     {report.exit_code}")
    print()
    print("Analysis:")
    print(f"  Menus detected:        {len(report.menus)}")
    print(f"  Interactions detected: {len(report.interactions)}")
    print(f"  Formatting issues:     {len(report.formatting_issues)}")
    print(f"  Checklist items:       {len(report.checklist_items)}")
    print()
    print("Menus:")
    for i, menu in enumerate(report.menus, 1):
        print(f"  Menu {i}: {len(menu.options)} options")
        for opt in menu.options:
            print(f"    - {opt}")
    print()
    print("Interactions:")
    for i, interaction in enumerate(report.interactions, 1):
        print(f"  {i}. {interaction.question}")
        print(f"     Response: {interaction.response}")
    print()
    print("Wording Analysis:")
    print(f"  Word count: {report.wording_analysis['word_count']}")
    print(f"  Line count: {report.wording_analysis['line_count']}")
    print(f"  Issues found: {sum(len(issues) for issues in report.wording_analysis['issues'].values())}")
    print()
    print("=" * 80)
    print()
    print(f"✓ HTML report generated: {output_path.absolute()}")
    print()
    print("Open the HTML file in your browser to:")
    print("  - Review the full terminal output with colors")
    print("  - Check items on the review checklist")
    print("  - Add notes for any issues found")
    print("  - Approve or reject the UAT")
    print()
    print(f"Command: open {output_path}")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
