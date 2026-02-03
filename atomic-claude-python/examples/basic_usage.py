#!/usr/bin/env python3
"""
ATOMIC CLAUDE - Basic Usage Examples

Demonstrates the core functionality of the Python implementation.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.atomic import (
    atomic_invoke,
    atomic_step,
    atomic_substep,
    atomic_success,
    atomic_error,
    atomic_warn,
    atomic_info,
    atomic_h1,
    atomic_h2,
    atomic_extract_json,
    atomic_validate_files,
    atomic_state_get,
    atomic_state_set,
)


def example_1_simple_invoke():
    """Example 1: Simple Claude invocation."""
    atomic_h1("EXAMPLE 1: Simple Invocation")

    atomic_step("Invoking Claude with simple prompt")

    success = atomic_invoke(
        prompt_source="What are the three laws of robotics? Respond in JSON format.",
        output_file="/tmp/robotics_laws.json",
        description="Query robotics laws",
        model="sonnet",
        format_type="json"
    )

    if success:
        atomic_success("Example 1 complete!")
        with open("/tmp/robotics_laws.json") as f:
            print("\nOutput:", f.read()[:200], "...")
    else:
        atomic_error("Example 1 failed")

    return success


def example_2_file_prompt():
    """Example 2: Using a prompt file."""
    atomic_h1("EXAMPLE 2: File-Based Prompt")

    # Create a prompt file
    prompt_file = "/tmp/analysis_prompt.md"
    with open(prompt_file, 'w') as f:
        f.write("""
# Code Review Task

Review the following Python function for potential issues:

```python
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price'] * item['quantity']
    return total
```

Provide findings in JSON format with:
- severity (low/medium/high)
- description
- recommendation
""")

    atomic_step("Running code review from prompt file")

    success = atomic_invoke(
        prompt_source=prompt_file,
        output_file="/tmp/code_review.json",
        description="Code review analysis",
        model="sonnet",
        format_type="json"
    )

    if success:
        atomic_success("Example 2 complete!")
        atomic_substep("Review results saved to /tmp/code_review.json")
    else:
        atomic_error("Example 2 failed")

    return success


def example_3_multi_step_pipeline():
    """Example 3: Multi-step pipeline with state management."""
    atomic_h1("EXAMPLE 3: Multi-Step Pipeline")

    # Step 1: Requirements analysis
    atomic_step("Step 1: Requirements Analysis")
    atomic_state_set("current_phase", "requirements")

    req_success = atomic_invoke(
        prompt_source="""
        Analyze these requirements for a todo app:
        - Users can create, read, update, delete todos
        - Todos have title, description, due date, priority
        - Users can filter by status and priority

        Output a JSON with required features and data models.
        """,
        output_file="/tmp/requirements.json",
        description="Analyze requirements",
        model="sonnet",
        format_type="json"
    )

    if not req_success:
        atomic_error("Requirements analysis failed")
        return False

    # Step 2: Design generation
    atomic_step("Step 2: Design Generation")
    atomic_state_set("current_phase", "design")

    # Read requirements for context
    with open("/tmp/requirements.json") as f:
        requirements = f.read()

    design_success = atomic_invoke(
        prompt_source=f"""
        Based on these requirements:
        {requirements}

        Generate a high-level design document including:
        - Database schema
        - API endpoints
        - Component structure

        Output as markdown.
        """,
        output_file="/tmp/design.md",
        description="Generate design document",
        model="opus"  # Use more powerful model for design
    )

    if not design_success:
        atomic_error("Design generation failed")
        return False

    # Step 3: Implementation plan
    atomic_step("Step 3: Implementation Planning")
    atomic_state_set("current_phase", "planning")

    plan_success = atomic_invoke(
        prompt_source="Based on /tmp/design.md, create a task breakdown JSON.",
        output_file="/tmp/implementation_plan.json",
        description="Create implementation plan",
        model="sonnet",
        format_type="json"
    )

    if not plan_success:
        atomic_error("Planning failed")
        return False

    # Validate all outputs
    if atomic_validate_files(
        "/tmp/requirements.json",
        "/tmp/design.md",
        "/tmp/implementation_plan.json"
    ):
        atomic_success("Example 3 complete - full pipeline succeeded!")
        atomic_info(f"Final phase: {atomic_state_get('current_phase')}")
        return True

    return False


def example_4_error_handling():
    """Example 4: Error handling and retries."""
    atomic_h1("EXAMPLE 4: Error Handling")

    atomic_step("Testing timeout and retry behavior")

    # Use a very short timeout to demonstrate retry
    success = atomic_invoke(
        prompt_source="Explain quantum computing in simple terms.",
        output_file="/tmp/quantum.txt",
        description="Quantum computing explanation",
        model="sonnet",
        timeout=1,  # Very short timeout (will likely fail)
        max_retries=2,
        retry_delay=1
    )

    if success:
        atomic_success("Somehow succeeded despite short timeout!")
    else:
        atomic_warn("Failed as expected - demonstrates retry logic")

    return True  # Success either way for demo purposes


def example_5_json_extraction():
    """Example 5: JSON extraction from mixed output."""
    atomic_h1("EXAMPLE 5: JSON Extraction")

    atomic_step("Getting Claude response with mixed output")

    # Create a response that might have markdown + JSON
    test_output = "/tmp/mixed_output.txt"
    with open(test_output, 'w') as f:
        f.write("""
Here are the results:

```json
{
  "status": "success",
  "findings": ["issue1", "issue2"],
  "count": 2
}
```

That's the analysis!
""")

    atomic_step("Extracting JSON from mixed output")

    if atomic_extract_json(test_output, "/tmp/extracted.json"):
        atomic_success("JSON extracted successfully!")
        with open("/tmp/extracted.json") as f:
            import json
            data = json.load(f)
            atomic_info(f"Extracted {data['count']} findings")
    else:
        atomic_error("JSON extraction failed")

    return True


def example_6_state_management():
    """Example 6: State management."""
    atomic_h1("EXAMPLE 6: State Management")

    atomic_step("Working with state")

    # Set various state values
    atomic_state_set("project_name", "DemoProject")
    atomic_state_set("current_phase", "testing")
    atomic_state_set("tasks_completed", 5)

    # Retrieve state
    project = atomic_state_get("project_name")
    phase = atomic_state_get("current_phase")
    tasks = atomic_state_get("tasks_completed")

    atomic_info(f"Project: {project}")
    atomic_info(f"Phase: {phase}")
    atomic_info(f"Tasks completed: {tasks}")

    atomic_success("State management working!")

    return True


def main():
    """Run all examples."""
    atomic_h1("ATOMIC CLAUDE - Python Examples")

    examples = [
        ("Simple Invocation", example_1_simple_invoke),
        ("File-Based Prompt", example_2_file_prompt),
        ("Multi-Step Pipeline", example_3_multi_step_pipeline),
        ("Error Handling", example_4_error_handling),
        ("JSON Extraction", example_5_json_extraction),
        ("State Management", example_6_state_management),
    ]

    results = []
    for name, example_func in examples:
        try:
            print("\n" + "="*72)
            success = example_func()
            results.append((name, success))
            print()
        except Exception as e:
            atomic_error(f"Example '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    atomic_h1("EXAMPLES SUMMARY")
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}  {name}")

    total = len(results)
    passed = sum(1 for _, s in results if s)
    print(f"\nTotal: {passed}/{total} passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
