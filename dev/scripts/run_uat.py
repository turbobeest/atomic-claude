#!/usr/bin/env python3
"""
UAT Runner CLI Wrapper

Simple command-line interface for running UAT tests and viewing reports.

Usage:
    python scripts/run_uat.py --phase 0 --scenario guided
    python scripts/run_uat.py --phase 1 --scenario default
    python scripts/run_uat.py --phase 0 --all-scenarios
"""

import sys
import argparse
import webbrowser
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dev.tests.runners.uat_runner import UATRunner


def main():
    parser = argparse.ArgumentParser(
        description="UAT Runner - User Acceptance Test with automated report generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_uat.py --phase 0 --scenario guided
  python scripts/run_uat.py --phase 1 --scenario default
  python scripts/run_uat.py --phase 0 --all-scenarios
  python scripts/run_uat.py --phase 2 --no-browser
        """
    )

    parser.add_argument(
        "--phase",
        type=int,
        required=True,
        choices=range(10),
        help="Phase number to test (0-9)"
    )

    parser.add_argument(
        "--scenario",
        type=str,
        default="default",
        help="Scenario to run (default, guided, quick, document)"
    )

    parser.add_argument(
        "--all-scenarios",
        action="store_true",
        help="Run all scenarios for the phase"
    )

    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically"
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("test/reports"),
        help="Output directory for reports (default: test/reports)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("  UAT RUNNER - User Acceptance Testing")
    print("=" * 80)

    # Initialize runner
    runner = UATRunner()

    # Load phase config
    config = runner.load_phase_config(args.phase)
    print(f"\nPhase: {args.phase}")
    print(f"Config loaded: {config.get('phase', 'unknown')}")

    # Determine scenarios to run
    if args.all_scenarios:
        scenarios = config.get("uat", {}).get("scenarios", ["default"])
        print(f"Running all scenarios: {', '.join(scenarios)}")
    else:
        scenarios = [args.scenario]
        print(f"Running scenario: {args.scenario}")

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Run UAT for each scenario
    reports = []
    for scenario in scenarios:
        print(f"\n{'=' * 80}")
        print(f"  Running UAT: Phase {args.phase:02d} - Scenario: {scenario}")
        print(f"{'=' * 80}\n")

        # Run UAT
        report = runner.run_phase_uat(
            phase_num=args.phase,
            scenario=scenario,
            config=config
        )

        # Generate HTML report
        report_filename = f"uat_phase{args.phase:02d}_{scenario}.html"
        report_path = args.output_dir / report_filename

        runner.save_html_report(report, report_path)

        print(f"\n{'=' * 80}")
        print(f"  UAT Report Generated")
        print(f"{'=' * 80}")
        print(f"\nReport: {report_path.absolute()}")
        print(f"Status: {'✓ PASSED' if report.success else '✗ FAILED'}")
        print(f"Duration: {report.duration:.2f}s")
        print(f"Exit Code: {report.exit_code}")
        print(f"\nAnalysis:")
        print(f"  Menus detected: {len(report.menus)}")
        print(f"  Interactions detected: {len(report.interactions)}")
        print(f"  Formatting issues: {len(report.formatting_issues)}")

        if report.errors:
            print(f"\n✗ Errors:")
            for error in report.errors:
                print(f"  - {error}")

        if report.warnings:
            print(f"\n⚠ Warnings:")
            for warning in report.warnings:
                print(f"  - {warning}")

        reports.append((scenario, report, report_path))

    # Open reports in browser
    if not args.no_browser:
        print(f"\n{'=' * 80}")
        print("  Opening reports in browser...")
        print(f"{'=' * 80}\n")

        for scenario, report, report_path in reports:
            print(f"Opening: {report_path.name}")
            webbrowser.open(f"file://{report_path.absolute()}")

    # Summary
    print(f"\n{'=' * 80}")
    print("  UAT SUMMARY")
    print(f"{'=' * 80}\n")

    all_passed = all(report.success for _, report, _ in reports)

    print(f"Total scenarios: {len(reports)}")
    print(f"Passed: {sum(1 for _, r, _ in reports if r.success)}")
    print(f"Failed: {sum(1 for _, r, _ in reports if not r.success)}")
    print(f"\nOverall: {'✓ ALL PASSED' if all_passed else '✗ SOME FAILED'}")

    print("\nNext steps:")
    print("1. Review each report in your browser")
    print("2. Check all items on the review checklist")
    print("3. Add notes for any issues found")
    print("4. Click 'Approve' or 'Reject' to record your decision")
    print("5. Check browser console for checklist JSON output")

    print(f"\n{'=' * 80}\n")

    # Exit code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
