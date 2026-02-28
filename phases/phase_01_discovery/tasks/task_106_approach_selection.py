"""
Task 106: Direction Confirmation (Human Gate)

Review and confirm the consensus from deliberation.

This is a HUMAN GATE where:
  - The consensus from Task 105 is presented
  - Human can approve as-is or modify any section
  - Final direction is locked in for downstream phases

Outputs:
  - selected-approach.json   - Finalized direction (structured)
  - selected-approach.md     - Human-readable documentation
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.ui import success, error, warning, info, step, wrap_text

try:
    from core.discovery.canvas import (
        CanvasState, render_canvas, generate_prd_preview,
    )
    HAS_CANVAS = True
except ImportError:
    HAS_CANVAS = False


def execute(atomic_root: Path, output_dir: Path, uat_mode: bool = False, mem=None, graph=None) -> bool:
    """
    Execute Task 106: Approach Selection.

    Args:
        atomic_root: Path to atomic-claude root directory
        output_dir: Path to phase output directory
        uat_mode: If True, auto-approve first approach
        mem: Optional TaskMemory instance for recording substantive memory

    Returns:
        True if selection completed successfully, False otherwise
    """
    consensus_file = output_dir / "consensus.json"
    approaches_file = output_dir / "approaches.json"
    selected_json = output_dir / "selected-approach.json"
    selected_md = output_dir / "selected-approach.md"

    step("Direction Confirmation")

    # UAT Mode: Auto-approve first approach
    if uat_mode:
        print()
        print("  ⚡ UAT Mode: Auto-approving first approach")
        print()

        _create_uat_approach(selected_json, selected_md)
        success("Direction confirmed (UAT mode)")
        return True

    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║  HUMAN GATE: CONFIRM DIRECTION                            ║")
    print("║                                                           ║")
    print("║  Review the consensus from deliberation.                  ║")
    print("║  Approve as-is, or modify any section.                    ║")
    print("║                                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # ═══════════════════════════════════════════════════════════════
    # CHECK PREREQUISITES
    # ═══════════════════════════════════════════════════════════════

    if not consensus_file.exists():
        error("No consensus found. Run Discovery Conversation first.")
        return False

    # Load canvas state if available
    canvas = None
    if HAS_CANVAS:
        canvas_file = output_dir / "canvas.json"
        if canvas_file.exists():
            try:
                canvas = CanvasState.from_dict(json.loads(canvas_file.read_text()))
            except Exception as e:
                logger.debug("Failed to load canvas: %s", e)

    # Load consensus
    try:
        with open(consensus_file) as f:
            consensus = json.load(f)
    except json.JSONDecodeError as e:
        error(f"Consensus file is not valid JSON: {consensus_file}")
        logger.warning("Failed to parse consensus file %s: %s", consensus_file, e)
        return False

    direction = consensus.get('agreed_direction', {}).get('approach', 'No direction specified')
    rationale = consensus.get('agreed_direction', {}).get('rationale', '')
    key_decisions = consensus.get('key_decisions', [])
    open_items = consensus.get('open_items', [])
    next_steps = consensus.get('next_steps', [])
    dissenting_views = consensus.get('dissenting_views', [])

    # ═══════════════════════════════════════════════════════════════
    # SECTION 1: DIRECTION
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ 1. DIRECTION                                               ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    print(f"  {direction}")
    print()
    if rationale:
        for line in wrap_text(rationale, 60, indent="  "):
            print(line)
        print()

    print("  [enter] Accept  [edit] Modify")
    section1_action = input("  > ").strip().lower()

    if section1_action == "edit":
        print()
        print("  Enter new direction (or press enter to keep current):")
        new_direction = input("  Direction: ").strip()
        if new_direction:
            direction = new_direction

        print("  Enter new rationale (or press enter to keep current):")
        new_rationale = input("  Rationale: ").strip()
        if new_rationale:
            rationale = new_rationale

        print("  ✓ Direction updated")
    print()

    # ═══════════════════════════════════════════════════════════════
    # SECTION 2: KEY DECISIONS
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ 2. KEY DECISIONS                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    if key_decisions:
        for decision in key_decisions:
            print(f"  • {decision}")
    else:
        print("  No key decisions recorded")
    print()

    print("  [enter] Accept  [add] Add decision  [clear] Start fresh")
    section2_action = input("  > ").strip().lower()

    if section2_action == "add":
        print()
        print("  Add decisions (one per line, empty to finish):")
        while True:
            decision = input("  + ").strip()
            if not decision:
                break
            key_decisions.append(decision)
        print("  ✓ Decisions updated")
    elif section2_action == "clear":
        print()
        print("  Enter decisions (one per line, empty to finish):")
        key_decisions = []
        while True:
            decision = input("  + ").strip()
            if not decision:
                break
            key_decisions.append(decision)
        print("  ✓ Decisions replaced")
    print()

    # ═══════════════════════════════════════════════════════════════
    # SECTION 3: NEXT STEPS
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ 3. NEXT STEPS                                              ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    if next_steps:
        for i, step_item in enumerate(next_steps, 1):
            print(f"  {i}. {step_item}")
    else:
        print("  No next steps recorded")
    print()

    print("  [enter] Accept  [add] Add step  [reorder] Reprioritize  [clear] Start fresh")
    section3_action = input("  > ").strip().lower()

    if section3_action == "add":
        print()
        print("  Add steps (one per line, empty to finish):")
        while True:
            step_item = input("  + ").strip()
            if not step_item:
                break
            next_steps.append(step_item)
        print("  ✓ Steps updated")
    elif section3_action == "reorder":
        print()
        print("  Enter step numbers in new order (e.g., '3 1 2'):")
        new_order = input("  Order: ").strip()
        if new_order:
            try:
                indices = [int(n) - 1 for n in new_order.split()]
                reordered = [next_steps[i] for i in indices if 0 <= i < len(next_steps)]
                next_steps = reordered
                print("  ✓ Steps reordered")
            except (ValueError, IndexError):
                print("  ! Invalid order")
    elif section3_action == "clear":
        print()
        print("  Enter steps in priority order (one per line, empty to finish):")
        next_steps = []
        while True:
            step_item = input("  + ").strip()
            if not step_item:
                break
            next_steps.append(step_item)
        print("  ✓ Steps replaced")
    print()

    # ═══════════════════════════════════════════════════════════════
    # SECTION 4: OPEN ITEMS
    # ═══════════════════════════════════════════════════════════════

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ 4. OPEN ITEMS                                              ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    if open_items:
        for item in open_items:
            print(f"  ⚠ {item}")
    else:
        print("  No open items")
    print()

    print("  [enter] Accept  [add] Add item  [resolve] Mark resolved")
    section4_action = input("  > ").strip().lower()

    if section4_action == "add":
        print()
        print("  Add open items (one per line, empty to finish):")
        while True:
            item = input("  + ").strip()
            if not item:
                break
            open_items.append(item)
        print("  ✓ Open items updated")
    elif section4_action == "resolve":
        print()
        print("  Which items are resolved? (numbers, e.g., '1 3'):")
        for j, item in enumerate(open_items, 1):
            print(f"    {j}. {item}")
        resolved_nums = input("  Resolved: ").strip()
        if resolved_nums:
            try:
                to_resolve = set(int(n) for n in resolved_nums.split())
                open_items = [item for j, item in enumerate(open_items, 1) if j not in to_resolve]
                print("  ✓ Items resolved")
            except ValueError:
                print("  ! Invalid input")
    print()

    # ═══════════════════════════════════════════════════════════════
    # SECTION 5: DISSENTING VIEWS (Read-only acknowledgment)
    # ═══════════════════════════════════════════════════════════════

    if dissenting_views:
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║ 5. DISSENTING VIEWS                                        ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print()
        for view in dissenting_views:
            print(f"  💭 {view}")
        print()
        print("  (Noted for the record - these concerns may resurface)")
        print()

    # ── PRD Preview (canvas-based) ──
    if canvas:
        try:
            print()
            print("  " + "=" * 59)
            print("  PRD PREVIEW — Based on Discovery Coverage")
            print("  " + "=" * 59)
            print()
            print(render_canvas(canvas))

            # Load consensus for preview context
            preview_consensus = None
            consensus_file_preview = output_dir / "consensus.json"
            if consensus_file_preview.exists():
                try:
                    preview_consensus = json.loads(consensus_file_preview.read_text())
                except Exception:
                    pass

            print(generate_prd_preview(canvas, preview_consensus))
            print()

            empty_count = len(canvas.empty_sections)
            if empty_count > 0:
                print(f"  Note: {empty_count} PRD section(s) have no direct discovery evidence.")
                print("  The PRD author will infer these sections from available context.")
                print()
        except Exception as e:
            logger.debug("PRD preview failed: %s", e)

    # ═══════════════════════════════════════════════════════════════
    # FINAL CONFIRMATION
    # ═══════════════════════════════════════════════════════════════

    print("━" * 60)
    print()
    print("  Ready to lock in this direction?")
    print()
    print("    [approve]   Lock in and proceed")
    print("    [review]    See full summary first")
    print("    [reopen]    Go back to deliberation")
    if canvas:
        print("    canvas    — Show PRD coverage map")
    print()

    while True:
        final_action = input("  > ").strip().lower()

        if final_action in ('approve', 'yes', 'y'):
            break
        elif final_action == "review":
            print()
            print(f"  Direction: {direction}")
            print(f"  Rationale: {rationale}")
            print(f"  Decisions: {', '.join(key_decisions)}")
            print(f"  Next Steps: {', '.join(next_steps)}")
            print(f"  Open Items: {', '.join(open_items)}")
            print()
        elif final_action == "canvas" and canvas:
            print(render_canvas(canvas))
            print(generate_prd_preview(canvas))
        elif final_action == "reopen":
            print()
            print("  ! Returning to deliberation...")
            info("Direction not confirmed - reopen deliberation")
            return False
        else:
            print("  Type 'approve', 'review', 'reopen'" + (", or 'canvas'" if canvas else ""))

    # ═══════════════════════════════════════════════════════════════
    # SAVE FINALIZED DIRECTION
    # ═══════════════════════════════════════════════════════════════

    print()
    print("  Locking in direction...")

    # Build final JSON
    final_data = {
        "direction": {
            "summary": direction,
            "rationale": rationale
        },
        "key_decisions": key_decisions,
        "next_steps": next_steps,
        "open_items": open_items,
        "dissenting_views": dissenting_views,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "confirmed_by": "human"
    }

    with open(selected_json, 'w') as f:
        json.dump(final_data, f, indent=2)

    # Build markdown documentation
    _create_markdown_doc(selected_md, direction, rationale, key_decisions,
                        next_steps, open_items, dissenting_views)

    print("  ✓ Direction locked in")
    print()

    # Summary
    print("━" * 60)
    print()
    print("  Direction Confirmed")
    print()
    print(f"  {direction}")
    print()
    print(f"  Next steps: {len(next_steps)}")
    print(f"  Open items: {len(open_items)}")
    print()

    # Record substantive memory
    if mem:
        mem.decision(f"Approach locked: {direction}")
        if key_decisions:
            mem.decision(f"Key decisions: {', '.join(key_decisions[:5])}")
        if open_items:
            mem.warning(f"Open items: {', '.join(open_items[:3])}")
        mem.finding("Ready for Phase 2 (PRD)")

    # Write to knowledge graph
    if graph:
        # Update decisions from 105 to "accepted" status
        for i, decision in enumerate(key_decisions[:10]):
            graph.add_decision(
                id=f"DEC-106-{i+1}",
                title=str(decision),
                rationale=f"Confirmed by human at direction lock-in",
                status="accepted",
            )
        if direction:
            graph.add_finding(
                id="F-106-locked-direction",
                category="vision",
                title="Locked Direction",
                content=str(direction),
                confidence=1.0,
            )

    success("Direction confirmed")
    return True


def _create_markdown_doc(output_file: Path, direction: str, rationale: str,
                         key_decisions: List[str], next_steps: List[str],
                         open_items: List[str], dissenting_views: List[str]) -> None:
    """Create the markdown documentation file."""
    content = f"""# Selected Direction

**Confirmed:** {datetime.now(timezone.utc).isoformat()}

---

## Direction

**{direction}**

{rationale}

---

## Key Decisions

{chr(10).join(f"- {d}" for d in key_decisions) if key_decisions else "None"}

---

## Next Steps

{chr(10).join(f"{i}. {s}" for i, s in enumerate(next_steps, 1)) if next_steps else "None"}

---

## Open Items

{chr(10).join(f"- ⚠ {item}" for item in open_items) if open_items else "None"}

---

## Dissenting Views

{chr(10).join(f"- 💭 {view}" for view in dissenting_views) if dissenting_views else "None recorded"}

---

*This direction was confirmed through Discovery Conversation deliberation.*
"""

    output_file.write_text(content)


def _create_uat_approach(selected_json: Path, selected_md: Path) -> None:
    """Create minimal approach files for UAT mode."""
    with open(selected_json, 'w') as f:
        json.dump({
            "name": "UAT Test Approach",
            "description": "Auto-selected approach for UAT testing",
            "architecture": "monolithic",
            "tech_stack": ["Python", "Bash", "JSON"],
            "rationale": "UAT mode auto-approval",
            "mode": "uat"
        }, f, indent=2)

    selected_md.write_text("""# Selected Approach: UAT Test Approach

## Overview
Auto-selected approach for UAT testing.

## Architecture
Monolithic

## Tech Stack
- Python
- Bash
- JSON

## Rationale
UAT mode auto-approval
""")




if __name__ == "__main__":
    # CLI execution support
    atomic_root = Path.cwd()
    output_dir = atomic_root.parent / ".outputs" / "1-discovery"
    uat_mode = "--uat" in sys.argv

    sys.exit(0 if execute(atomic_root, output_dir, uat_mode) else 1)
