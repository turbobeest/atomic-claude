#!/usr/bin/env python3
"""
Context Flow Audit Runner

Static analysis of all task files to detect context starvation — situations where
LLM-invoking tasks receive significantly less context than is available from prior
phases.

Audit checks:
  1. Truncation Detection       — Scan for [:N] slicing in context/prompt code
  2. Source Loading Completeness — Compare CSV available vs actual loads
  3. LLM Prompt Context Ratio   — Measure context chars vs available context
  4. Conversation History        — Verify conversational tasks pass history
  5. Cross-Phase Data Flow       — Verify entry tasks load prior closeout

Usage:
    python scripts/audit_runners/context_flow_audit_runner.py
    python scripts/audit_runners/context_flow_audit_runner.py --verbose
    python scripts/audit_runners/context_flow_audit_runner.py --fix-report
"""

import sys
import os
import re
import csv
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

# Repo root
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()

# Colors for output
class Colors:
    CYAN = '\033[0;36m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    NC = '\033[0m'


# Severity levels
CRITICAL = "critical"
HIGH = "high"
MEDIUM = "medium"
LOW = "low"
INFO = "info"

# Truncation thresholds
TRUNCATION_FAIL_THRESHOLD = 500      # [:500] or less = critical
TRUNCATION_WARN_THRESHOLD = 2000     # [:2000] or less = high
TRUNCATION_INFO_THRESHOLD = 5000     # [:5000] or less = medium

# Phase-to-phase expected data flows: entry task should load prior closeout
PHASE_FLOW = {
    "1-discovery": {"prior_phase": "0-setup", "entry_task": "101"},
    "2-prd":       {"prior_phase": "1-discovery", "entry_task": "201"},
    "3-tasking":   {"prior_phase": "2-prd", "entry_task": "301"},
    "4-specification": {"prior_phase": "3-tasking", "entry_task": "401"},
    "5-implementation": {"prior_phase": "4-specification", "entry_task": "501"},
    "6-code-review": {"prior_phase": "5-implementation", "entry_task": "601"},
    "7-integration": {"prior_phase": "6-code-review", "entry_task": "701"},
    "8-deployment-prep": {"prior_phase": "7-integration", "entry_task": "801"},
    "9-release": {"prior_phase": "8-deployment-prep", "entry_task": "901"},
}

# Tasks known to be conversational (should pass history to LLM)
CONVERSATIONAL_TASKS = {"104", "105"}

# Tasks known to invoke LLM
LLM_TASKS = {"003", "101", "103", "104", "105", "107", "205", "206", "303",
             "403", "504", "603", "604", "904"}


class Finding:
    """A single audit finding."""
    def __init__(self, task_id: str, file_path: str, severity: str,
                 check: str, description: str, recommendation: str,
                 line_number: int = 0):
        self.task_id = task_id
        self.file_path = file_path
        self.severity = severity
        self.check = check
        self.description = description
        self.recommendation = recommendation
        self.line_number = line_number

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "file_path": self.file_path,
            "severity": self.severity,
            "check": self.check,
            "description": self.description,
            "recommendation": self.recommendation,
            "line_number": self.line_number
        }


class ContextFlowAuditRunner:
    """Context starvation detection audit runner."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.csv_path = REPO_ROOT / "reports" / "task-traceability-matrix.csv"
        self.findings: List[Finding] = []
        self.task_files: Dict[str, Path] = {}
        self.task_sources: Dict[str, str] = {}  # task_id -> source code
        self.test_start_time = datetime.now()

        # Discover all task files
        self._discover_task_files()

    def log(self, message: str, color: str = Colors.NC):
        print(f"{color}{message}{Colors.NC}")

    def _discover_task_files(self):
        """Find all task Python files."""
        phases_dir = REPO_ROOT / "phases"
        for phase_dir in sorted(phases_dir.iterdir()):
            if not phase_dir.is_dir():
                continue
            tasks_dir = phase_dir / "tasks"
            if not tasks_dir.exists():
                continue
            for task_file in sorted(tasks_dir.glob("task_*.py")):
                # Extract task ID from filename (e.g., task_101_entry_validation.py -> 101)
                match = re.search(r'task_(\d+)', task_file.name)
                if match:
                    task_id = match.group(1)
                    self.task_files[task_id] = task_file
                    try:
                        self.task_sources[task_id] = task_file.read_text()
                    except Exception:
                        self.task_sources[task_id] = ""

    def add_finding(self, task_id: str, severity: str, check: str,
                    description: str, recommendation: str, line_number: int = 0):
        """Add an audit finding."""
        file_path = str(self.task_files.get(task_id, "unknown"))
        finding = Finding(task_id, file_path, severity, check, description,
                         recommendation, line_number)
        self.findings.append(finding)

    # ─────────────────────────────────────────────────────────────
    # CHECK 1: TRUNCATION DETECTION
    # ─────────────────────────────────────────────────────────────

    def audit_truncation_patterns(self) -> Dict:
        """Scan all task files for [:N] truncation in context/prompt code."""
        self.log("\n" + "=" * 80, Colors.CYAN)
        self.log("  CHECK 1: TRUNCATION DETECTION", Colors.CYAN)
        self.log("=" * 80, Colors.CYAN)

        results = {"tasks_scanned": 0, "truncations_found": 0, "details": []}

        # Pattern: variable[:NUMBER] where NUMBER is a literal integer
        # This catches things like content[:5000], analysis[:3000], etc.
        truncation_pattern = re.compile(
            r'(\w+)\[:(\d+)\]',
            re.MULTILINE
        )

        # Exclude variable names that aren't context truncation
        # (e.g., list slicing for preview like tasks[:5], or agents[:10])
        exclude_vars = {
            'tasks', 'test_points', 'issues', 'suggestions', 'parsed',
            'findings', 'all_findings', 'agents_array', 'decomposition_agents',
            'validation_agents', 'source_files', 'test_files', 'files',
            'preview_count', 'timestamp_issues', 'task_issues', 'missing_keys',
            'lines', 'dot_lines', 'json_lines', 'task_title', 'code',
        }

        # Line-level patterns that indicate non-context truncation
        exclude_line_patterns = [
            r'mem\.',           # Memory logging (mem.conversation, mem.finding)
            r'print\(',         # Display/formatting
            r'_count_lines',    # Utility functions
            r'str\(.*relative', # Path display
        ]

        for task_id, source in sorted(self.task_sources.items()):
            results["tasks_scanned"] += 1

            for match in truncation_pattern.finditer(source):
                var_name = match.group(1)
                limit = int(match.group(2))
                line_num = source[:match.start()].count('\n') + 1

                # Skip non-context variable names
                if var_name in exclude_vars:
                    continue

                # Skip small limits that are clearly list slicing ([:3], [:5], [:10])
                if limit <= 30:
                    continue

                # Get surrounding line for context checks
                line_start = source.rfind('\n', 0, match.start()) + 1
                line_end = source.find('\n', match.end())
                if line_end == -1:
                    line_end = len(source)
                line_text = source[line_start:line_end].strip()

                # Skip lines matching non-context patterns
                skip = False
                for pattern in exclude_line_patterns:
                    if re.search(pattern, line_text):
                        skip = True
                        break
                if skip:
                    continue

                # Determine severity based on limit value
                if limit <= TRUNCATION_FAIL_THRESHOLD:
                    severity = CRITICAL
                elif limit <= TRUNCATION_WARN_THRESHOLD:
                    severity = HIGH
                elif limit <= TRUNCATION_INFO_THRESHOLD:
                    severity = MEDIUM
                else:
                    severity = LOW

                results["truncations_found"] += 1
                detail = {
                    "task_id": task_id,
                    "variable": var_name,
                    "limit": limit,
                    "line": line_num,
                    "severity": severity,
                    "context": line_text[:120]
                }
                results["details"].append(detail)

                self.add_finding(
                    task_id=task_id,
                    severity=severity,
                    check="truncation",
                    description=f"Truncation {var_name}[:{limit}] at line {line_num}: {line_text[:80]}",
                    recommendation=f"Remove or increase [:{ limit}] limit — pass full content or use intelligent summarization",
                    line_number=line_num
                )

                if self.verbose:
                    color = {CRITICAL: Colors.RED, HIGH: Colors.YELLOW,
                             MEDIUM: Colors.CYAN, LOW: Colors.DIM}.get(severity, Colors.NC)
                    self.log(f"  [{severity.upper()}] Task {task_id} line {line_num}: "
                            f"{var_name}[:{limit}]", color)

        # Summary
        self.log(f"\n  Truncation Summary:", Colors.BOLD)
        self.log(f"    Tasks scanned:     {results['tasks_scanned']}", Colors.DIM)
        self.log(f"    Truncations found: {results['truncations_found']}",
                Colors.RED if results['truncations_found'] > 0 else Colors.GREEN)

        return results

    # ─────────────────────────────────────────────────────────────
    # CHECK 2: SOURCE LOADING COMPLETENESS
    # ─────────────────────────────────────────────────────────────

    def audit_source_loading(self) -> Dict:
        """Compare CSV available sources vs actual file reads in code."""
        self.log("\n" + "=" * 80, Colors.CYAN)
        self.log("  CHECK 2: SOURCE LOADING COMPLETENESS", Colors.CYAN)
        self.log("=" * 80, Colors.CYAN)

        results = {"tasks_checked": 0, "gaps_found": 0, "details": []}

        if not self.csv_path.exists():
            self.log(f"\n  ! CSV not found: {self.csv_path}", Colors.YELLOW)
            return results

        # Parse CSV for available sources
        csv_data = {}
        try:
            with open(self.csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    task_id = row.get("task_id", "").strip()
                    available = row.get("context_sources_available", "").strip()
                    loaded = row.get("context_sources_loaded", "").strip()
                    if task_id and available:
                        csv_data[task_id] = {
                            "available": available,
                            "loaded": loaded
                        }
        except Exception as e:
            self.log(f"\n  ! CSV parse error: {e}", Colors.YELLOW)
            return results

        for task_id, info in csv_data.items():
            if task_id not in self.task_sources:
                continue

            results["tasks_checked"] += 1
            available = info["available"]
            loaded = info["loaded"]

            if not available or available == "None":
                continue

            # Parse available sources (semicolon-separated)
            available_items = [s.strip() for s in available.split(";") if s.strip()]
            loaded_items = [s.strip() for s in loaded.split(";") if s.strip()] if loaded else []

            # Check for gaps
            source = self.task_sources[task_id]
            missing = []
            for item in available_items:
                # Check if the source code references this file/output
                # Normalize: "corpus.json" -> check for "corpus" in source
                base_name = item.split("/")[-1].replace(".json", "").replace(".md", "")
                base_name_parts = base_name.replace("-", "_").split("_")

                # Check if any significant keyword from the filename appears in source
                found = False
                for part in base_name_parts:
                    if len(part) > 3 and part.lower() in source.lower():
                        found = True
                        break

                if not found and item not in loaded_items:
                    missing.append(item)

            if missing:
                results["gaps_found"] += 1
                severity = HIGH if len(missing) > 2 else MEDIUM

                detail = {
                    "task_id": task_id,
                    "available_count": len(available_items),
                    "loaded_count": len(loaded_items),
                    "missing": missing
                }
                results["details"].append(detail)

                self.add_finding(
                    task_id=task_id,
                    severity=severity,
                    check="source_loading",
                    description=f"Task {task_id} skips {len(missing)} available sources: {', '.join(missing[:3])}",
                    recommendation=f"Load missing sources: {', '.join(missing)}"
                )

                if self.verbose:
                    self.log(f"  Task {task_id}: missing {len(missing)} of "
                            f"{len(available_items)} sources", Colors.YELLOW)

        self.log(f"\n  Source Loading Summary:", Colors.BOLD)
        self.log(f"    Tasks checked: {results['tasks_checked']}", Colors.DIM)
        self.log(f"    Gaps found:    {results['gaps_found']}",
                Colors.YELLOW if results['gaps_found'] > 0 else Colors.GREEN)

        return results

    # ─────────────────────────────────────────────────────────────
    # CHECK 3: LLM PROMPT CONTEXT RATIO
    # ─────────────────────────────────────────────────────────────

    def audit_prompt_context_ratio(self) -> Dict:
        """For LLM-invoking tasks, check if fix/review prompts include code context."""
        self.log("\n" + "=" * 80, Colors.CYAN)
        self.log("  CHECK 3: LLM PROMPT CONTEXT ANALYSIS", Colors.CYAN)
        self.log("=" * 80, Colors.CYAN)

        results = {"tasks_checked": 0, "issues_found": 0, "details": []}

        for task_id in LLM_TASKS:
            if task_id not in self.task_sources:
                continue

            results["tasks_checked"] += 1
            source = self.task_sources[task_id]

            # Check if the task builds prompts that reference files but don't include content
            # Pattern: prompt references a file path but doesn't read/include it
            has_file_reference_in_prompt = bool(
                re.search(r'["\']file["\'].*?finding|finding.*?["\']file["\']', source, re.IGNORECASE)
            )
            has_code_in_prompt = bool(
                re.search(r'read_file|\.read_text\(\)|open\(.*?\).*?read', source)
                and re.search(r'prompt.*?content|content.*?prompt|code_content|code_sample', source, re.IGNORECASE)
            )

            # Specific check: task 604 references file+line in findings but doesn't load code
            if task_id == "604":
                # Check if _apply_fix loads the referenced source file
                apply_fix_match = re.search(
                    r'def _apply_fix.*?(?=\ndef |\Z)', source, re.DOTALL
                )
                if apply_fix_match:
                    apply_fix_code = apply_fix_match.group(0)
                    reads_source_file = bool(
                        re.search(r'read_file|open\(.*?finding.*?file|source.*?read', apply_fix_code)
                    )
                    if not reads_source_file:
                        results["issues_found"] += 1
                        self.add_finding(
                            task_id="604",
                            severity=CRITICAL,
                            check="prompt_context",
                            description="Fix prompts reference file+line from findings but never load the actual source code — LLM cannot see code it's asked to fix",
                            recommendation="Read ~50 lines around finding['line'] from finding['file'] and include in fix prompt"
                        )

            # Specific check: task 504 is a stub that delegates to Claude Code CLI
            if task_id == "504":
                has_context_loading = "context_loaded" in source or "tasks_file" in source
                if ("not yet implemented" in source.lower() or "placeholder" in source.lower()) and not has_context_loading:
                    results["issues_found"] += 1
                    self.add_finding(
                        task_id="504",
                        severity=CRITICAL,
                        check="prompt_context",
                        description="TDD execution is a stub — no context loading, no LLM invocation implemented",
                        recommendation="Implement TDD execution with OpenSpec + task definition context loading"
                    )
                elif "not yet implemented" in source.lower() or "placeholder" in source.lower():
                    # Stub with context loading — delegates to Claude Code CLI
                    results["issues_found"] += 1
                    self.add_finding(
                        task_id="504",
                        severity=MEDIUM,
                        check="prompt_context",
                        description="TDD execution delegates to Claude Code CLI — context is loaded but native execution not implemented",
                        recommendation="Consider implementing native TDD execution for offline/API-only environments"
                    )

        self.log(f"\n  Prompt Context Summary:", Colors.BOLD)
        self.log(f"    LLM tasks checked: {results['tasks_checked']}", Colors.DIM)
        self.log(f"    Issues found:      {results['issues_found']}",
                Colors.RED if results['issues_found'] > 0 else Colors.GREEN)

        return results

    # ─────────────────────────────────────────────────────────────
    # CHECK 4: CONVERSATION HISTORY INCLUSION
    # ─────────────────────────────────────────────────────────────

    def audit_conversation_history(self) -> Dict:
        """Check conversational tasks pass history to LLM calls."""
        self.log("\n" + "=" * 80, Colors.CYAN)
        self.log("  CHECK 4: CONVERSATION HISTORY INCLUSION", Colors.CYAN)
        self.log("=" * 80, Colors.CYAN)

        results = {"tasks_checked": 0, "issues_found": 0, "details": []}

        for task_id in CONVERSATIONAL_TASKS:
            if task_id not in self.task_sources:
                continue

            results["tasks_checked"] += 1
            source = self.task_sources[task_id]

            # Check if conversation history is assembled and passed to LLM
            has_history_assembly = bool(
                re.search(r'conversation.*?text|conversation_text|history', source, re.IGNORECASE)
            )
            # Check if conversation/history appears in prompt building code
            passes_to_llm = bool(
                re.search(r'(invoke|llm).*?(conversation|history|prior)', source, re.IGNORECASE)
                or re.search(r'prompt.*?conversation|conversation.*?prompt', source, re.IGNORECASE)
                or re.search(r'conversation_text', source)  # Variable used in prompt f-string
            )

            if not has_history_assembly or not passes_to_llm:
                results["issues_found"] += 1
                self.add_finding(
                    task_id=task_id,
                    severity=HIGH,
                    check="conversation_history",
                    description=f"Conversational task {task_id} may not pass full conversation history to LLM calls",
                    recommendation="Ensure all prior conversation turns are included in LLM prompt context"
                )

            if self.verbose:
                status = "✓" if (has_history_assembly and passes_to_llm) else "✗"
                color = Colors.GREEN if status == "✓" else Colors.RED
                self.log(f"  Task {task_id}: history={has_history_assembly}, "
                        f"passed={passes_to_llm} {status}", color)

        self.log(f"\n  Conversation History Summary:", Colors.BOLD)
        self.log(f"    Tasks checked: {results['tasks_checked']}", Colors.DIM)
        self.log(f"    Issues found:  {results['issues_found']}",
                Colors.YELLOW if results['issues_found'] > 0 else Colors.GREEN)

        return results

    # ─────────────────────────────────────────────────────────────
    # CHECK 5: CROSS-PHASE DATA FLOW
    # ─────────────────────────────────────────────────────────────

    def audit_cross_phase_flow(self) -> Dict:
        """Verify entry tasks load prior phase closeout."""
        self.log("\n" + "=" * 80, Colors.CYAN)
        self.log("  CHECK 5: CROSS-PHASE DATA FLOW", Colors.CYAN)
        self.log("=" * 80, Colors.CYAN)

        results = {"transitions_checked": 0, "breaks_found": 0, "details": []}

        for phase_id, flow in PHASE_FLOW.items():
            entry_task = flow["entry_task"]
            prior_phase = flow["prior_phase"]

            if entry_task not in self.task_sources:
                continue

            results["transitions_checked"] += 1
            source = self.task_sources[entry_task]

            # Check if the entry task references the prior phase's closeout
            # Look for: closeout, prior phase name, or prior phase number
            prior_num = prior_phase.split("-")[0]
            has_closeout_ref = bool(
                re.search(rf'closeout|phase.?{prior_num}|{prior_phase}', source, re.IGNORECASE)
            )

            if not has_closeout_ref:
                results["breaks_found"] += 1
                self.add_finding(
                    task_id=entry_task,
                    severity=HIGH,
                    check="cross_phase_flow",
                    description=f"Entry task {entry_task} for phase {phase_id} does not reference prior phase {prior_phase} closeout",
                    recommendation=f"Load .claude/closeout/phase-{prior_num.zfill(2)}-closeout.json or .outputs/{prior_phase}/closeout.json"
                )

            if self.verbose:
                status = "✓" if has_closeout_ref else "✗"
                color = Colors.GREEN if has_closeout_ref else Colors.RED
                self.log(f"  {prior_phase} → {phase_id} (task {entry_task}): {status}", color)

        self.log(f"\n  Cross-Phase Flow Summary:", Colors.BOLD)
        self.log(f"    Transitions checked: {results['transitions_checked']}", Colors.DIM)
        self.log(f"    Breaks found:        {results['breaks_found']}",
                Colors.RED if results['breaks_found'] > 0 else Colors.GREEN)

        return results

    # ─────────────────────────────────────────────────────────────
    # REPORT GENERATION
    # ─────────────────────────────────────────────────────────────

    def generate_report(self) -> None:
        """Generate audit report with findings and recommendations."""
        self.log("\n" + "=" * 80, Colors.CYAN)
        self.log("  CONTEXT FLOW AUDIT REPORT", Colors.CYAN)
        self.log("=" * 80, Colors.CYAN)

        duration = (datetime.now() - self.test_start_time).total_seconds()

        # Count by severity
        counts = {CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        self.log(f"\n  Test Duration: {duration:.1f}s", Colors.BOLD)
        self.log(f"\n  Findings by Severity:", Colors.BOLD)
        self.log(f"    Critical: {counts[CRITICAL]}",
                Colors.RED if counts[CRITICAL] > 0 else Colors.GREEN)
        self.log(f"    High:     {counts[HIGH]}",
                Colors.RED if counts[HIGH] > 0 else Colors.GREEN)
        self.log(f"    Medium:   {counts[MEDIUM]}",
                Colors.YELLOW if counts[MEDIUM] > 0 else Colors.GREEN)
        self.log(f"    Low:      {counts[LOW]}", Colors.DIM)

        # List critical and high findings
        critical_high = [f for f in self.findings if f.severity in (CRITICAL, HIGH)]
        if critical_high:
            self.log(f"\n  Critical/High Findings:", Colors.BOLD)
            for f in critical_high:
                color = Colors.RED if f.severity == CRITICAL else Colors.YELLOW
                self.log(f"    [{f.severity.upper()}] Task {f.task_id}: {f.description[:90]}", color)

        # Overall assessment
        if counts[CRITICAL] == 0 and counts[HIGH] == 0:
            self.log(f"\n  ✅ PASS - No critical or high context starvation issues", Colors.GREEN)
        elif counts[CRITICAL] == 0:
            self.log(f"\n  ⚠️  WARN - {counts[HIGH]} high-severity issues remaining", Colors.YELLOW)
        else:
            self.log(f"\n  ❌ FAIL - {counts[CRITICAL]} critical, {counts[HIGH]} high issues", Colors.RED)

        # Save JSON report
        self._save_report(counts, duration)

    def _save_report(self, counts: Dict[str, int], duration: float):
        """Save detailed JSON report."""
        report_dir = REPO_ROOT / "reports"
        report_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        report_file = report_dir / f"context-flow-audit-{timestamp}.json"

        report = {
            "audit": "context-flow",
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "summary": {
                "total_findings": len(self.findings),
                "critical": counts.get(CRITICAL, 0),
                "high": counts.get(HIGH, 0),
                "medium": counts.get(MEDIUM, 0),
                "low": counts.get(LOW, 0),
                "pass": counts.get(CRITICAL, 0) == 0 and counts.get(HIGH, 0) == 0
            },
            "findings": [f.to_dict() for f in self.findings],
            "tasks_scanned": len(self.task_files),
            "task_files": {tid: str(path) for tid, path in self.task_files.items()}
        }

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        self.log(f"\n  Report saved: {report_file}", Colors.CYAN)

        # Also save a latest symlink-style copy
        latest_file = report_dir / "context-flow-audit-latest.json"
        with open(latest_file, "w") as f:
            json.dump(report, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Context Flow Audit Runner — detect context starvation in pipeline tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output with per-task details")
    parser.add_argument("--check", choices=["truncation", "loading", "prompt", "history", "flow"],
                       help="Run only a specific check")
    parser.add_argument("--fix-report", action="store_true",
                       help="Generate fix recommendations for all findings")

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("  ATOMIC CLAUDE 2.0 — CONTEXT FLOW AUDIT")
    print("=" * 80)

    runner = ContextFlowAuditRunner(verbose=args.verbose)

    if args.check:
        checks = {
            "truncation": runner.audit_truncation_patterns,
            "loading": runner.audit_source_loading,
            "prompt": runner.audit_prompt_context_ratio,
            "history": runner.audit_conversation_history,
            "flow": runner.audit_cross_phase_flow,
        }
        checks[args.check]()
    else:
        runner.audit_truncation_patterns()
        runner.audit_source_loading()
        runner.audit_prompt_context_ratio()
        runner.audit_conversation_history()
        runner.audit_cross_phase_flow()

    runner.generate_report()

    # Exit code based on findings
    critical_high = sum(1 for f in runner.findings if f.severity in (CRITICAL, HIGH))
    if critical_high == 0:
        print(f"\n{'=' * 80}")
        print(f"{Colors.GREEN}  ✓ CONTEXT FLOW AUDIT COMPLETE — ALL CLEAR{Colors.NC}")
        print(f"{'=' * 80}\n")
        sys.exit(0)
    else:
        print(f"\n{'=' * 80}")
        print(f"{Colors.YELLOW}  ⚠ CONTEXT FLOW AUDIT COMPLETE — {critical_high} ISSUES FOUND{Colors.NC}")
        print(f"{'=' * 80}\n")
        sys.exit(0)  # Don't fail CI, just report


if __name__ == "__main__":
    main()
