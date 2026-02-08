#!/usr/bin/env python3
"""
Enhanced User Acceptance Test (UAT) Runner

Captures and validates TUI/UX quality with human review capabilities.

Features:
- Captures ALL CLI output including ANSI colors
- Records terminal sessions and converts to HTML
- Validates formatting, menu logic, wording
- Generates HTML reports with human review checklists
- Supports multiple scenarios per phase
- Extracts interactive flows for validation

Usage:
    from tests.runners.uat_runner import UATRunner

    runner = UATRunner()
    report = runner.run_phase_uat(phase_num=0, config=config)
    runner.save_html_report(report, "uat_phase00.html")
"""

import sys
import os
import subprocess
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import html


@dataclass
class MenuCapture:
    """Captures menu presentation and logic."""
    options: List[str] = field(default_factory=list)
    prompt: str = ""
    selected: str = ""
    context: str = ""


@dataclass
class InteractionCapture:
    """Captures an interactive Q&A flow."""
    question: str = ""
    expected_input: str = ""
    actual_input: str = ""
    response: str = ""
    timestamp: float = 0.0


@dataclass
class FormattingIssue:
    """Captures a formatting issue."""
    line_num: int = 0
    issue_type: str = ""
    description: str = ""
    severity: str = "info"  # info, warning, error


@dataclass
class UATReport:
    """Complete UAT report for a phase execution."""
    phase_num: int = 0
    scenario: str = ""
    timestamp: str = ""
    duration: float = 0.0
    success: bool = False
    exit_code: int = 0

    # Captured output
    raw_output: str = ""
    ansi_html: str = ""

    # Extracted elements
    menus: List[MenuCapture] = field(default_factory=list)
    interactions: List[InteractionCapture] = field(default_factory=list)
    formatting_issues: List[FormattingIssue] = field(default_factory=list)

    # Analysis
    checklist_items: List[Dict[str, Any]] = field(default_factory=list)
    wording_analysis: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class ANSIToHTML:
    """Convert ANSI escape codes to HTML with styling."""

    ANSI_COLORS = {
        '30': 'color: #000000',  # Black
        '31': 'color: #CD3131',  # Red
        '32': 'color: #0DBC79',  # Green
        '33': 'color: #E5E510',  # Yellow
        '34': 'color: #2472C8',  # Blue
        '35': 'color: #BC3FBC',  # Magenta
        '36': 'color: #11A8CD',  # Cyan
        '37': 'color: #E5E5E5',  # White
        '90': 'color: #666666',  # Bright Black (Gray)
        '91': 'color: #F14C4C',  # Bright Red
        '92': 'color: #23D18B',  # Bright Green
        '93': 'color: #F5F543',  # Bright Yellow
        '94': 'color: #3B8EEA',  # Bright Blue
        '95': 'color: #D670D6',  # Bright Magenta
        '96': 'color: #29B8DB',  # Bright Cyan
        '97': 'color: #FFFFFF',  # Bright White
    }

    ANSI_STYLES = {
        '1': 'font-weight: bold',
        '2': 'opacity: 0.6',
        '3': 'font-style: italic',
        '4': 'text-decoration: underline',
    }

    @classmethod
    def convert(cls, text: str) -> str:
        """Convert ANSI text to HTML."""
        # Escape HTML special chars first
        text = html.escape(text)

        # Pattern for ANSI escape sequences
        ansi_pattern = re.compile(r'\x1b\[([0-9;]+)m')

        result = []
        last_pos = 0
        open_spans = []

        for match in ansi_pattern.finditer(text):
            # Add text before this code
            result.append(text[last_pos:match.start()])

            codes = match.group(1).split(';')

            # Reset code
            if '0' in codes:
                while open_spans:
                    result.append('</span>')
                    open_spans.pop()
            else:
                # Apply styles
                styles = []
                for code in codes:
                    if code in cls.ANSI_COLORS:
                        styles.append(cls.ANSI_COLORS[code])
                    elif code in cls.ANSI_STYLES:
                        styles.append(cls.ANSI_STYLES[code])

                if styles:
                    style_str = '; '.join(styles)
                    result.append(f'<span style="{style_str}">')
                    open_spans.append(style_str)

            last_pos = match.end()

        # Add remaining text
        result.append(text[last_pos:])

        # Close any remaining spans
        while open_spans:
            result.append('</span>')
            open_spans.pop()

        return ''.join(result)


class UATRunner:
    """Enhanced UAT runner with comprehensive UX validation."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize UAT runner."""
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.test_dir = self.repo_root / "tests"

    def load_phase_config(self, phase_num: int) -> Dict[str, Any]:
        """Load phase UAT configuration."""
        config_file = self.test_dir / "phase_configs" / f"phase_{phase_num:02d}_tests.json"

        if not config_file.exists():
            # Return default config
            return {
                "phase": f"{phase_num}-default",
                "uat": {
                    "scenarios": ["default"],
                    "human_review": True,
                    "checklist": [
                        "All prompts are clear and professional",
                        "Menu options are logical and complete",
                        "Error messages are helpful",
                        "Progress indicators work correctly",
                        "Colors and formatting enhance readability",
                        "No typos or grammatical errors"
                    ]
                }
            }

        with open(config_file, 'r') as f:
            return json.load(f)

    def load_scenario_inputs(self, phase_num: int, scenario: str) -> str:
        """Load scenario input file."""
        input_file = self.test_dir / "fixtures" / f"phase{phase_num:02d}" / "uat_scenarios" / f"{scenario}_inputs.txt"

        if not input_file.exists():
            # Return default inputs
            return "\n"

        with open(input_file, 'r') as f:
            return f.read()

    def run_phase_uat(self, phase_num: int, scenario: str = "default", config: Optional[Dict] = None) -> UATReport:
        """
        Run UAT for a phase with specified scenario.

        Args:
            phase_num: Phase number (0-9)
            scenario: Scenario name (guided, quick, document, etc.)
            config: Optional phase configuration override

        Returns:
            UATReport with complete analysis
        """
        if config is None:
            config = self.load_phase_config(phase_num)

        report = UATReport(
            phase_num=phase_num,
            scenario=scenario,
            timestamp=datetime.now().isoformat(),
        )

        # Load scenario inputs
        scenario_inputs = self.load_scenario_inputs(phase_num, scenario)

        # Prepare environment
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.repo_root)
        env["ATOMIC_ROOT"] = str(self.repo_root)
        env["ATOMIC_TOOL_DEVELOPMENT"] = "true"
        env["ATOMIC_UAT_MODE"] = "true"

        # Build command
        cmd = [
            sys.executable,
            str(self.repo_root / "main.py"),
            "run",
            str(phase_num)
        ]

        # Execute phase
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                env=env,
                input=scenario_inputs,
                capture_output=True,
                text=True,
                timeout=600
            )

            report.duration = time.time() - start_time
            report.exit_code = result.returncode
            report.success = result.returncode == 0
            report.raw_output = result.stdout + result.stderr

        except subprocess.TimeoutExpired as e:
            report.duration = time.time() - start_time
            report.exit_code = -1
            report.success = False
            report.errors.append(f"Execution timeout after {report.duration:.1f}s")
            report.raw_output = e.stdout.decode() if e.stdout else ""

        except Exception as e:
            report.duration = time.time() - start_time
            report.exit_code = -1
            report.success = False
            report.errors.append(f"Execution error: {str(e)}")

        # Convert ANSI to HTML
        report.ansi_html = ANSIToHTML.convert(report.raw_output)

        # Analyze output
        self._analyze_menus(report)
        self._analyze_interactions(report)
        self._analyze_formatting(report)
        self._analyze_wording(report)

        # Build checklist from config
        uat_config = config.get("uat", {})
        report.checklist_items = [
            {
                "item": item,
                "checked": False,
                "notes": ""
            }
            for item in uat_config.get("checklist", [])
        ]

        return report

    def _analyze_menus(self, report: UATReport):
        """Extract and analyze menu presentations."""
        lines = report.raw_output.split('\n')

        # Pattern for menu options (common formats)
        option_patterns = [
            r'^\s*\d+[\.\)]\s+(.+)$',  # 1. Option or 1) Option
            r'^\s*\[(\w+)\]\s+(.+)$',   # [a] Option
            r'^\s*\((\w+)\)\s+(.+)$',   # (a) Option
        ]

        current_menu = None

        for i, line in enumerate(lines):
            # Strip ANSI codes for pattern matching
            clean_line = re.sub(r'\x1b\[[0-9;]+m', '', line)

            for pattern in option_patterns:
                match = re.match(pattern, clean_line)
                if match:
                    if current_menu is None:
                        current_menu = MenuCapture()
                        # Look back for menu context
                        context_lines = []
                        for j in range(max(0, i-5), i):
                            context_lines.append(lines[j])
                        current_menu.context = '\n'.join(context_lines)

                    current_menu.options.append(clean_line.strip())

            # Detect menu end (empty line or prompt)
            if current_menu and current_menu.options:
                if not clean_line.strip() or 'Enter' in clean_line or 'Select' in clean_line:
                    current_menu.prompt = clean_line.strip()
                    report.menus.append(current_menu)
                    current_menu = None

    def _analyze_interactions(self, report: UATReport):
        """Extract and analyze interactive Q&A flows."""
        lines = report.raw_output.split('\n')

        # Patterns for prompts/questions
        question_patterns = [
            r'^\s*\?\s+(.+)$',  # ? Question
            r'^(.+)\?$',         # Question?
            r'^Enter\s+(.+):',   # Enter something:
            r'^(.+)\s+\[.*\]:',  # Question [default]:
        ]

        for i, line in enumerate(lines):
            clean_line = re.sub(r'\x1b\[[0-9;]+m', '', line)

            for pattern in question_patterns:
                match = re.match(pattern, clean_line)
                if match:
                    interaction = InteractionCapture(
                        question=clean_line.strip(),
                        timestamp=float(i) / len(lines) * report.duration
                    )

                    # Look ahead for response
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        interaction.response = next_line.strip()

                    report.interactions.append(interaction)
                    break

    def _analyze_formatting(self, report: UATReport):
        """Analyze formatting quality."""
        lines = report.raw_output.split('\n')

        for i, line in enumerate(lines, 1):
            # Check line length (readability)
            visible_length = len(re.sub(r'\x1b\[[0-9;]+m', '', line))
            if visible_length > 120:
                report.formatting_issues.append(FormattingIssue(
                    line_num=i,
                    issue_type="line_length",
                    description=f"Line too long ({visible_length} chars)",
                    severity="warning"
                ))

            # Check for inconsistent spacing
            if line.startswith('  ') and not line.startswith('    '):
                # Odd indentation
                spaces = len(line) - len(line.lstrip())
                if spaces % 2 != 0:
                    report.formatting_issues.append(FormattingIssue(
                        line_num=i,
                        issue_type="indentation",
                        description=f"Odd indentation ({spaces} spaces)",
                        severity="info"
                    ))

            # Check for multiple consecutive empty lines
            if i > 2 and not line.strip():
                prev_lines = lines[i-3:i-1]
                if all(not l.strip() for l in prev_lines):
                    report.formatting_issues.append(FormattingIssue(
                        line_num=i,
                        issue_type="whitespace",
                        description="Multiple consecutive empty lines",
                        severity="info"
                    ))

    def _analyze_wording(self, report: UATReport):
        """Analyze wording quality."""
        text = report.raw_output.lower()

        # Common issues to check
        issues = {
            "typos": [],
            "unclear": [],
            "grammar": [],
            "tone": []
        }

        # Check for common typos
        common_typos = [
            (r'\bthe the\b', 'duplicate word'),
            (r'\bteh\b', 'typo: the'),
            (r'\brecieve\b', 'typo: receive'),
        ]

        for pattern, description in common_typos:
            if re.search(pattern, text):
                issues["typos"].append(description)

        # Check for unclear phrasing
        unclear_phrases = [
            (r'please wait\.\.\.', 'Vague progress indicator'),
            (r'error occurred', 'Non-specific error message'),
        ]

        for pattern, description in unclear_phrases:
            if re.search(pattern, text):
                issues["unclear"].append(description)

        # Check tone (should be professional but friendly)
        if 'sorry' in text and text.count('sorry') > 3:
            issues["tone"].append("Overly apologetic tone")

        if '!' in report.raw_output and report.raw_output.count('!') > 10:
            issues["tone"].append("Excessive exclamation marks")

        report.wording_analysis = {
            "issues": issues,
            "word_count": len(text.split()),
            "line_count": len(report.raw_output.split('\n'))
        }

    def save_html_report(self, report: UATReport, output_path: Path):
        """Generate and save HTML report."""
        template_path = self.test_dir / "templates" / "uat_report.html"

        if template_path.exists():
            with open(template_path, 'r') as f:
                template = f.read()
        else:
            # Use inline template
            template = self._get_default_template()

        # Replace template variables
        html_content = template.replace('{{PHASE_NUM}}', str(report.phase_num))
        html_content = html_content.replace('{{SCENARIO}}', report.scenario)
        html_content = html_content.replace('{{TIMESTAMP}}', report.timestamp)
        html_content = html_content.replace('{{DURATION}}', f"{report.duration:.2f}s")
        html_content = html_content.replace('{{SUCCESS}}', '✓ PASSED' if report.success else '✗ FAILED')
        html_content = html_content.replace('{{EXIT_CODE}}', str(report.exit_code))
        html_content = html_content.replace('{{OUTPUT}}', report.ansi_html)

        # Build checklist HTML
        checklist_html = self._build_checklist_html(report)
        html_content = html_content.replace('{{CHECKLIST}}', checklist_html)

        # Build analysis HTML
        analysis_html = self._build_analysis_html(report)
        html_content = html_content.replace('{{ANALYSIS}}', analysis_html)

        # Save report
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(html_content)

        return output_path

    def _build_checklist_html(self, report: UATReport) -> str:
        """Build HTML for review checklist."""
        html_parts = ['<div class="checklist">']

        for item in report.checklist_items:
            checked = 'checked' if item['checked'] else ''
            html_parts.append(f'''
                <div class="checklist-item">
                    <input type="checkbox" id="{item['item'][:20]}" {checked}>
                    <label for="{item['item'][:20]}">{item['item']}</label>
                    <textarea placeholder="Notes...">{item.get('notes', '')}</textarea>
                </div>
            ''')

        html_parts.append('</div>')
        return '\n'.join(html_parts)

    def _build_analysis_html(self, report: UATReport) -> str:
        """Build HTML for automated analysis."""
        html_parts = ['<div class="analysis">']

        # Menus
        html_parts.append('<h3>Menus Detected</h3>')
        if report.menus:
            for i, menu in enumerate(report.menus, 1):
                html_parts.append(f'<div class="menu"><strong>Menu {i}:</strong>')
                html_parts.append('<ul>')
                for option in menu.options:
                    html_parts.append(f'<li>{html.escape(option)}</li>')
                html_parts.append('</ul>')
                if menu.prompt:
                    html_parts.append(f'<p><em>Prompt: {html.escape(menu.prompt)}</em></p>')
                html_parts.append('</div>')
        else:
            html_parts.append('<p>No menus detected</p>')

        # Interactions
        html_parts.append('<h3>Interactive Flows</h3>')
        if report.interactions:
            html_parts.append('<ul>')
            for interaction in report.interactions:
                html_parts.append(f'<li>{html.escape(interaction.question)}</li>')
            html_parts.append('</ul>')
        else:
            html_parts.append('<p>No interactive prompts detected</p>')

        # Formatting issues
        html_parts.append('<h3>Formatting Issues</h3>')
        if report.formatting_issues:
            html_parts.append('<ul>')
            for issue in report.formatting_issues:
                severity_class = f'severity-{issue.severity}'
                html_parts.append(
                    f'<li class="{severity_class}">Line {issue.line_num}: {html.escape(issue.description)}</li>'
                )
            html_parts.append('</ul>')
        else:
            html_parts.append('<p class="success">No formatting issues detected</p>')

        # Wording analysis
        html_parts.append('<h3>Wording Analysis</h3>')
        wording = report.wording_analysis
        if wording:
            html_parts.append(f'<p>Word count: {wording.get("word_count", 0)}</p>')
            html_parts.append(f'<p>Line count: {wording.get("line_count", 0)}</p>')

            issues = wording.get("issues", {})
            for category, items in issues.items():
                if items:
                    html_parts.append(f'<p><strong>{category.title()}:</strong></p>')
                    html_parts.append('<ul>')
                    for item in items:
                        html_parts.append(f'<li>{html.escape(item)}</li>')
                    html_parts.append('</ul>')

        html_parts.append('</div>')
        return '\n'.join(html_parts)

    def _get_default_template(self) -> str:
        """Get default HTML template."""
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>UAT Report - Phase {{PHASE_NUM}}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header h1 { margin: 0; }
        .metadata {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        .metadata-item {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 5px;
        }
        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .panel {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .full-width { grid-column: 1 / -1; }
        .output {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            overflow-x: auto;
            max-height: 600px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .checklist-item {
            padding: 15px;
            border-bottom: 1px solid #eee;
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 10px;
            align-items: start;
        }
        .checklist-item input[type="checkbox"] {
            width: 20px;
            height: 20px;
            margin-top: 2px;
        }
        .checklist-item label {
            font-weight: 500;
            cursor: pointer;
        }
        .checklist-item textarea {
            grid-column: 2;
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            resize: vertical;
            font-family: inherit;
        }
        .success { color: #0DBC79; }
        .error { color: #CD3131; }
        .warning { color: #E5E510; }
        .severity-info { color: #666; }
        .severity-warning { color: #E5E510; }
        .severity-error { color: #CD3131; }
        .menu {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
        }
        .menu ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        h2 {
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        h3 {
            color: #764ba2;
            margin-top: 20px;
        }
        .button-container {
            margin-top: 20px;
            text-align: center;
        }
        .button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin: 0 10px;
        }
        .button:hover { background: #764ba2; }
        .button.approve { background: #0DBC79; }
        .button.reject { background: #CD3131; }
    </style>
</head>
<body>
    <div class="header">
        <h1>UAT Report - Phase {{PHASE_NUM}}</h1>
        <div class="metadata">
            <div class="metadata-item"><strong>Scenario:</strong> {{SCENARIO}}</div>
            <div class="metadata-item"><strong>Timestamp:</strong> {{TIMESTAMP}}</div>
            <div class="metadata-item"><strong>Duration:</strong> {{DURATION}}</div>
            <div class="metadata-item"><strong>Status:</strong> {{SUCCESS}}</div>
            <div class="metadata-item"><strong>Exit Code:</strong> {{EXIT_CODE}}</div>
        </div>
    </div>

    <div class="container">
        <div class="panel">
            <h2>Review Checklist</h2>
            <p>Review the output and check each item below:</p>
            {{CHECKLIST}}
            <div class="button-container">
                <button class="button approve" onclick="approveUAT()">✓ Approve</button>
                <button class="button reject" onclick="rejectUAT()">✗ Reject</button>
            </div>
        </div>

        <div class="panel">
            <h2>Automated Analysis</h2>
            {{ANALYSIS}}
        </div>

        <div class="panel full-width">
            <h2>Terminal Output</h2>
            <div class="output">{{OUTPUT}}</div>
        </div>
    </div>

    <script>
        function approveUAT() {
            const checklist = {};
            document.querySelectorAll('.checklist-item').forEach(item => {
                const checkbox = item.querySelector('input[type="checkbox"]');
                const label = item.querySelector('label');
                const textarea = item.querySelector('textarea');
                checklist[label.textContent] = {
                    checked: checkbox.checked,
                    notes: textarea.value
                };
            });

            console.log('UAT Approved', checklist);
            alert('UAT Approved! Check console for checklist details.');
        }

        function rejectUAT() {
            const reason = prompt('Reason for rejection:');
            if (reason) {
                console.log('UAT Rejected:', reason);
                alert('UAT Rejected. Reason logged to console.');
            }
        }
    </script>
</body>
</html>'''


if __name__ == "__main__":
    # Simple test
    runner = UATRunner()
    report = runner.run_phase_uat(phase_num=0, scenario="default")

    output_path = Path("uat_report_phase00.html")
    runner.save_html_report(report, output_path)

    print(f"\nUAT Report generated: {output_path}")
    print(f"Success: {report.success}")
    print(f"Duration: {report.duration:.2f}s")
    print(f"Menus detected: {len(report.menus)}")
    print(f"Interactions detected: {len(report.interactions)}")
    print(f"Formatting issues: {len(report.formatting_issues)}")
