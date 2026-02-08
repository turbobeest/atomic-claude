#!/usr/bin/env python3
"""
Example Usage: Continuity Test Runner

Demonstrates how to use the ContinuityTestRunner programmatically.
"""

from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.runners import ContinuityTestRunner, load_phase_config


def example_basic_usage():
    """Example: Basic continuity test."""
    print("="*80)
    print("Example 1: Basic Continuity Test")
    print("="*80)

    # Load configuration
    config_path = Path(__file__).parent.parent / "phase_configs" / "phase_00_tests.json"
    config = load_phase_config(config_path)

    # Create runner
    runner = ContinuityTestRunner()

    # Run test
    report = runner.run_phase_continuity_test(
        phase_num=0,
        config=config,
        mock_inputs=True  # Use mock mode for faster testing
    )

    # Check results
    if report.success:
        print("\n✓ Phase passed continuity test!")
    else:
        print("\n✗ Phase failed continuity test")
        print(f"Errors: {report.errors}")

    return report


def example_with_custom_validation():
    """Example: Continuity test with custom validation."""
    print("\n" + "="*80)
    print("Example 2: Continuity Test with Custom Validation")
    print("="*80)

    # Load config
    config_path = Path(__file__).parent.parent / "phase_configs" / "phase_00_tests.json"
    config = load_phase_config(config_path)

    # Run test
    runner = ContinuityTestRunner()
    report = runner.run_phase_continuity_test(0, config, mock_inputs=True)

    # Custom validation
    print("\n--- Custom Validation ---")

    # Check task durations
    slow_tasks = [
        r for r in report.task_results
        if r.duration_seconds > 30
    ]
    if slow_tasks:
        print(f"⚠️  {len(slow_tasks)} slow tasks detected:")
        for task in slow_tasks:
            print(f"   - Task {task.task_id}: {task.duration_seconds:.1f}s")
    else:
        print("✓ All tasks completed in reasonable time")

    # Check memory usage
    total_memory_mb = sum(
        r.resource_usage.get("memory_delta_mb", 0)
        for r in report.task_results
    )
    print(f"Total memory delta: {total_memory_mb:.1f} MB")
    if total_memory_mb > 500:
        print("⚠️  High memory usage detected")
    else:
        print("✓ Memory usage acceptable")

    # Check for warnings
    total_warnings = sum(len(r.warnings) for r in report.task_results)
    if total_warnings > 0:
        print(f"⚠️  {total_warnings} warnings detected")
    else:
        print("✓ No warnings")

    return report


def example_save_and_analyze_report():
    """Example: Save report and analyze results."""
    print("\n" + "="*80)
    print("Example 3: Save and Analyze Report")
    print("="*80)

    # Load config
    config_path = Path(__file__).parent.parent / "phase_configs" / "phase_00_tests.json"
    config = load_phase_config(config_path)

    # Run test
    runner = ContinuityTestRunner()
    report = runner.run_phase_continuity_test(0, config, mock_inputs=True)

    # Save report
    json_path, text_path = runner.save_report(report)
    print(f"\n✓ Report saved:")
    print(f"   JSON: {json_path}")
    print(f"   Text: {text_path}")

    # Analyze results
    print("\n--- Analysis ---")
    print(f"Phase: {report.phase_name}")
    print(f"Duration: {report.duration_seconds:.1f}s")
    print(f"Success Rate: {report.tasks_passed}/{report.total_tasks} "
          f"({report.tasks_passed/report.total_tasks*100:.0f}%)")

    # Find slowest task
    if report.task_results:
        slowest = max(report.task_results, key=lambda r: r.duration_seconds)
        print(f"Slowest Task: {slowest.task_id} ({slowest.duration_seconds:.1f}s)")

    # Find failed tasks
    failed = [r for r in report.task_results if not r.success]
    if failed:
        print(f"\nFailed Tasks ({len(failed)}):")
        for task in failed:
            print(f"   - Task {task.task_id}: {task.error_message}")

    return report


def example_multiple_phases():
    """Example: Test multiple phases in sequence."""
    print("\n" + "="*80)
    print("Example 4: Test Multiple Phases")
    print("="*80)

    phases_to_test = [0]  # Add more phases as they're implemented
    runner = ContinuityTestRunner()
    results = {}

    for phase_num in phases_to_test:
        print(f"\nTesting Phase {phase_num}...")

        # Load config
        config_path = (
            Path(__file__).parent.parent /
            "phase_configs" /
            f"phase_{phase_num:02d}_tests.json"
        )

        if not config_path.exists():
            print(f"   ⚠️  Config not found: {config_path}")
            continue

        config = load_phase_config(config_path)

        # Run test
        report = runner.run_phase_continuity_test(
            phase_num,
            config,
            mock_inputs=True
        )

        results[phase_num] = report.success

        status = "✓ PASSED" if report.success else "✗ FAILED"
        print(f"   {status} (Duration: {report.duration_seconds:.1f}s)")

    # Summary
    print("\n--- Summary ---")
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    print(f"Phases: {passed}/{total} passed")

    return results


def main():
    """Run all examples."""
    print("\n" + "="*80)
    print("CONTINUITY TEST RUNNER - USAGE EXAMPLES")
    print("="*80)

    try:
        # Example 1: Basic usage
        example_basic_usage()

        # Example 2: Custom validation
        example_with_custom_validation()

        # Example 3: Save and analyze
        example_save_and_analyze_report()

        # Example 4: Multiple phases
        example_multiple_phases()

        print("\n" + "="*80)
        print("All examples completed!")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
