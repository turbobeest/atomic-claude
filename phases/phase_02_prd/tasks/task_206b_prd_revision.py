"""
Task 206b: PRD Revision (LLM-Assisted Q&A)

Invoked from task 206/207 when user chooses to revise the PRD.

Flow:
  1. Read validation results
  2. Group issues by priority (P0 first)
  3. For each issue: show it, ask user how to resolve
  4. Collect all decisions into a resolution plan
  5. Split PRD into sections, match resolutions to sections
  6. For each affected section, invoke LLM with ONLY that section
  7. Reassemble, show summary, apply/discard
  8. Return to caller for re-validation

Note: This is a helper module invoked by task 206/207, not a standalone task.
"""

import logging
import re
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.llm import invoke
from core.utils.cli_ui import (
    print_bold, print_cyan, print_yellow, print_green,
    print_red, print_dim, prompt_user
)
from core.utils.file_ops import read_file, write_file


# ---------------------------------------------------------------------------
# PRD section parsing
# ---------------------------------------------------------------------------

def split_prd_into_sections(content: str) -> List[Dict[str, Any]]:
    """
    Split a PRD into sections by top-level markdown headings (# or ##).

    Returns list of dicts:
      {"heading": "# 2. Technical Architecture", "number": "2", "body": "...", "start": 0, "end": 500}

    Content before the first heading is returned as section number "0" (preamble).
    """
    # Match top-level PRD sections by numbered headings.
    # Real PRDs:     "# 1. Vision", "# 3. Feature Requirements"  (single #)
    # Skeleton PRDs: "## 0. Vision", "## 1. Executive Summary"   (double ##)
    # Try single-# first, fall back to double-##.
    heading_prefix = "#"
    matches = list(re.finditer(r'^# (\d+\.\s+.*)', content, re.MULTILINE))
    if not matches:
        heading_prefix = "##"
        matches = list(re.finditer(r'^## (\d+\.\s+.*)', content, re.MULTILINE))

    if not matches:
        # No numbered headings found — return whole document as one section
        return [{"heading": "(entire document)", "number": "0", "body": content, "start": 0, "end": len(content)}]

    sections = []

    # Preamble (content before first heading)
    if matches[0].start() > 0:
        preamble = content[:matches[0].start()]
        if preamble.strip():
            sections.append({
                "heading": "(preamble)",
                "number": "0",
                "body": preamble,
                "start": 0,
                "end": matches[0].start(),
            })

    for i, match in enumerate(matches):
        heading_text = match.group(1).strip()  # e.g., "2. Technical Architecture"
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)

        # Extract section number from heading (e.g., "2. Technical Architecture" -> "2")
        num_match = re.match(r'(\d+)', heading_text)
        section_number = num_match.group(1) if num_match else str(i + 1)

        sections.append({
            "heading": f"{heading_prefix} {heading_text}",
            "number": section_number,
            "body": content[start:end],
            "start": start,
            "end": end,
        })

    return sections


def extract_section_references(text: str) -> List[str]:
    """
    Extract section numbers referenced in a resolution text.

    Looks for patterns like "Section 6", "Section 2.1.1", "Section 8.12",
    "Appendix A", etc. Returns list of top-level section numbers.
    """
    refs = set()

    # "Section N" or "Section N.N.N"
    for m in re.finditer(r'[Ss]ection\s+(\d+)(?:\.\d+)*', text):
        refs.add(m.group(1))

    # "Section 2.15" or "section 2.1-2.5" (require "section" context)
    for m in re.finditer(r'[Ss]ections?\s+(\d{1,2})\.\d+', text):
        refs.add(m.group(1))

    # Appendix references -> section "appendix"
    if re.search(r'[Aa]ppendix', text):
        refs.add("appendix")

    return sorted(refs)


def extract_requirement_ids(text: str) -> List[str]:
    """
    Extract requirement IDs like FR-105, NFR-005, OPR-001, TC-003, etc.
    """
    return re.findall(r'\b[A-Z]{2,4}-\d{2,4}\b', text)


def find_sections_by_content(
    search_terms: List[str],
    sections: List[Dict[str, Any]],
) -> List[str]:
    """
    Find which sections contain any of the given search terms.
    Returns list of section numbers (deduplicated).
    """
    found = set()
    for term in search_terms:
        for s in sections:
            if term in s["body"]:
                found.add(s["number"])
    return sorted(found)


def match_resolutions_to_sections(
    resolutions: List[Dict[str, str]],
    sections: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, str]]]:
    """
    Group resolutions by the section(s) they target.

    Matching strategy (in order):
      1. Explicit section references ("Section 6", "2.15", "Appendix")
      2. Requirement ID body search (find "FR-105" in section content)

    Returns dict: section_number -> list of resolutions for that section.
    Resolutions that match no section go to "unmatched".
    """
    section_numbers = {s["number"] for s in sections}
    grouped: Dict[str, List[Dict[str, str]]] = {}

    for res in resolutions:
        detail = res.get("detail", "") + " " + res.get("resolution", "")
        matched = False

        # Strategy 1: explicit section references
        refs = extract_section_references(detail)
        for ref in refs:
            if ref == "appendix":
                grouped.setdefault("appendix", []).append(res)
                matched = True
            elif ref in section_numbers:
                grouped.setdefault(ref, []).append(res)
                matched = True

        if matched:
            continue

        # Strategy 2: find requirement IDs (FR-105, NFR-005, etc.) in section bodies
        req_ids = extract_requirement_ids(detail)
        if req_ids:
            target_sections = find_sections_by_content(req_ids, sections)
            if target_sections:
                for sec_num in target_sections:
                    grouped.setdefault(sec_num, []).append(res)
                matched = True

        if not matched:
            grouped.setdefault("unmatched", []).append(res)

    return grouped


# ---------------------------------------------------------------------------
# Edit-block parsing and application
# ---------------------------------------------------------------------------

def parse_edit_blocks(response: str) -> List[Tuple[str, str]]:
    """
    Parse LLM response into a list of (search, replace) tuples.

    Expected format:
        <<<SEARCH>>>
        exact text to find
        <<<REPLACE>>>
        replacement text
        <<<END>>>
    """
    blocks = []
    # Split on <<<SEARCH>>> markers
    parts = re.split(r'<<<SEARCH>>>', response)

    for part in parts[1:]:  # Skip everything before the first marker
        # Split on <<<REPLACE>>>
        sr = re.split(r'<<<REPLACE>>>', part, maxsplit=1)
        if len(sr) != 2:
            continue

        search_text = sr[0].strip()

        # Split on <<<END>>>
        re_parts = re.split(r'<<<END>>>', sr[1], maxsplit=1)
        replace_text = re_parts[0].strip()

        if search_text:
            blocks.append((search_text, replace_text))

    return blocks


def apply_edit_blocks(
    content: str,
    blocks: List[Tuple[str, str]],
) -> Tuple[str, int, int]:
    """
    Apply search/replace edit blocks to section content.

    Returns (modified_content, applied_count, skipped_count).
    """
    applied = 0
    skipped = 0

    for search, replace in blocks:
        if search in content:
            content = content.replace(search, replace, 1)
            applied += 1
        else:
            # Fuzzy fallback: normalize trailing whitespace only on the search
            # term and the matched region, preserving markdown trailing-double-
            # space line breaks in surrounding text.
            def normalize(text: str) -> str:
                lines = [line.rstrip() for line in text.splitlines()]
                return "\n".join(lines)

            norm_search = normalize(search)

            # Build a line-level mapping so we can find the match region
            # in the original content without normalizing the whole document.
            orig_lines = content.split('\n')
            norm_lines = [line.rstrip() for line in orig_lines]

            # Scan normalized lines to find the range matching norm_search
            norm_search_lines = norm_search.split('\n')
            match_start_line = None
            for i in range(len(norm_lines) - len(norm_search_lines) + 1):
                if norm_lines[i:i + len(norm_search_lines)] == norm_search_lines:
                    match_start_line = i
                    break

            if match_start_line is not None:
                match_end_line = match_start_line + len(norm_search_lines)
                # Compute character offsets in the original content
                orig_start = sum(len(orig_lines[j]) + 1 for j in range(match_start_line))
                orig_end = sum(len(orig_lines[j]) + 1 for j in range(match_end_line))
                # Trim trailing newline from the replaced region
                if orig_end > 0 and orig_end <= len(content):
                    orig_end -= 1
                content = content[:orig_start] + replace + content[orig_end:]
                applied += 1
            else:
                skipped += 1

    return content, applied, skipped


# ---------------------------------------------------------------------------
# Section-based revision
# ---------------------------------------------------------------------------

def revise_section(
    section: Dict[str, Any],
    resolutions: List[Dict[str, str]],
    prompts_dir: Path,
    prd_toc: str,
) -> Optional[str]:
    """
    Invoke LLM to revise a single PRD section based on targeted resolutions.

    Args:
        section: Section dict with heading, number, body
        resolutions: List of resolutions targeting this section
        prompts_dir: Directory for prompt logs
        prd_toc: Table of contents / section list for context

    Returns:
        Revised section body, or None on failure
    """
    section_num = section["number"]
    resolution_text = "\n".join(
        f"- [{r.get('type', 'FIX')}] {r['detail']}\n  RESOLUTION: {r['resolution']}"
        for r in resolutions
    )

    prompt = f"""# Task: Revise PRD Section {section_num}

You are editing ONE section of a PRD. Apply the resolutions below.

## PRD Structure (for context)
{prd_toc}

## Current Section Content
{section['body']}

## Resolutions to Apply
{resolution_text}

## Instructions
1. For each resolution, identify the specific text that needs to change
2. Output ONLY search/replace blocks — do NOT output the entire section
3. Use this exact format for each change:

<<<SEARCH>>>
exact existing text (include enough context to be unique)
<<<REPLACE>>>
the replacement text
<<<END>>>

4. For additions, include the anchor line in both SEARCH and REPLACE, with new content after it
5. Make minimal, targeted changes — do not rewrite surrounding content
6. If a resolution requires no text change to this section, skip it
"""

    # Log prompt
    prompt_file = prompts_dir / f"prd-revision-section-{section_num}.md"
    write_file(prompt_file, prompt)

    try:
        response = invoke(
            prompt=prompt,
            model="opus",
            temperature=0.2,
            timeout=900,
        )

        if not response or not response.strip():
            return None

        result = response.strip()

        # Check if the LLM returned edit blocks or a full section
        if "<<<SEARCH>>>" in result:
            # Parse and apply edit blocks
            blocks = parse_edit_blocks(result)
            if not blocks:
                print(print_yellow(f"\n         ⚠ Section {section_num}: no valid edit blocks parsed"))
                return None

            modified, applied, skipped = apply_edit_blocks(section["body"], blocks)

            if applied == 0:
                print(print_yellow(f"\n         ⚠ Section {section_num}: 0/{len(blocks)} edits matched"))
                return None

            if skipped > 0:
                print(print_yellow(f"\n         ⚠ Section {section_num}: {applied} applied, {skipped} skipped"), end="")

            return modified
        else:
            # Fallback: LLM returned full section text (old behavior)
            print(print_yellow(f"\n         ⚠ Section {section_num}: LLM returned full text (no edit blocks), using as-is"), end="")

            # Basic sanity: revised section shouldn't be drastically shorter
            if len(result) < len(section["body"]) * 0.3:
                print(print_yellow(f"\n         ⚠ Section {section_num} revision suspiciously short, keeping original"))
                return None

            return result

    except Exception as e:
        print(print_red(f"         ✗ Section {section_num} revision failed: {e}"))
        return None


def generate_appendix_content(
    resolutions: List[Dict[str, str]],
    prompts_dir: Path,
    prd_toc: str,
) -> Optional[str]:
    """Generate new appendix sections from resolutions that request them."""
    resolution_text = "\n".join(
        f"- {r['detail']}\n  RESOLUTION: {r['resolution']}"
        for r in resolutions
    )

    prompt = f"""# Task: Generate PRD Appendix Content

You are adding appendix sections to a PRD.

## PRD Structure (for context)
{prd_toc}

## Appendix Requests
{resolution_text}

## Instructions
1. Generate the requested appendix content in markdown format
2. Use proper appendix heading format (## Appendix A: ..., ## Appendix B: ..., etc.)
3. Include substantive content (not just placeholders)
4. Output ONLY the appendix markdown, nothing else
"""

    prompt_file = prompts_dir / "prd-revision-appendix.md"
    write_file(prompt_file, prompt)

    try:
        response = invoke(
            prompt=prompt,
            model="opus",
            temperature=0.2,
            timeout=900,
        )
        return response.strip() if response else None
    except Exception as e:
        print(print_red(f"         ✗ Appendix generation failed: {e}"))
        return None


# ---------------------------------------------------------------------------
# Main revision orchestration
# ---------------------------------------------------------------------------

def invoke_revision_agent(
    prd_file: Path,
    prompts_dir: Path,
    resolution_plan: str
) -> bool:
    """
    Apply revisions to the PRD using section-based editing.

    Instead of sending the entire PRD to the LLM, this:
    1. Splits the PRD into sections by top-level headings
    2. Matches each resolution to the section(s) it references
    3. Sends only the targeted section + its resolutions to the LLM
    4. Reassembles the PRD from revised sections

    Args:
        prd_file: Path to PRD file
        prompts_dir: Path to prompts directory
        resolution_plan: Resolution plan from Q&A (formatted text)

    Returns:
        True if revision applied successfully
    """
    print()
    prd_content = read_file(prd_file)

    # Parse resolution plan into structured list
    resolutions = parse_resolution_plan(resolution_plan)
    if not resolutions:
        print(print_yellow("  No resolutions to apply."))
        return False

    # Split PRD into sections
    sections = split_prd_into_sections(prd_content)
    print(print_cyan(f"  PRD split into {len(sections)} sections"))

    # Build table of contents for LLM context
    prd_toc = "\n".join(f"  {s['heading']}" for s in sections if s["number"] != "0")

    # Match resolutions to sections
    grouped = match_resolutions_to_sections(resolutions, sections)

    # Report plan
    affected_sections = [k for k in grouped if k not in ("unmatched", "appendix")]
    has_appendix = "appendix" in grouped
    has_unmatched = "unmatched" in grouped

    print(print_dim(f"  Sections to revise: {', '.join(affected_sections) if affected_sections else 'none'}"))
    if has_appendix:
        print(print_dim(f"  New appendix content: {len(grouped['appendix'])} items"))
    if has_unmatched:
        print(print_dim(f"  Unmatched resolutions: {len(grouped['unmatched'])} (will target broadly)"))
    print()

    # Build section lookup
    section_map = {s["number"]: s for s in sections}
    revised_sections: Dict[str, str] = {}  # section_number -> revised body
    changes_made = 0
    changes_failed = 0

    # Revise each affected section
    for section_num in affected_sections:
        section = section_map.get(section_num)
        if not section:
            continue

        section_resolutions = grouped[section_num]
        count = len(section_resolutions)
        print(print_cyan(f"  Section {section_num}") + f" — {count} resolution{'s' if count != 1 else ''}...", end=" ", flush=True)

        revised = revise_section(section, section_resolutions, prompts_dir, prd_toc)
        if revised:
            revised_sections[section_num] = revised
            changes_made += 1
            print(print_green("✓"))
        else:
            changes_failed += 1
            print(print_yellow("(kept original)"))

    # Handle unmatched resolutions — apply to the most likely section or skip
    if has_unmatched:
        unmatched = grouped["unmatched"]
        print(print_yellow(f"  Unmatched") + f" — {len(unmatched)} resolution{'s' if len(unmatched) != 1 else ''}...")
        # Try to apply unmatched items to the first/largest section as a fallback
        # Or just warn and skip
        for res in unmatched:
            print(print_dim(f"    Skipped (no section match): {res['detail'][:80]}..."))

    # Generate appendix content
    appendix_content = None
    if has_appendix:
        print(print_cyan(f"  Appendix") + f" — generating {len(grouped['appendix'])} items...", end=" ", flush=True)
        appendix_content = generate_appendix_content(grouped["appendix"], prompts_dir, prd_toc)
        if appendix_content:
            changes_made += 1
            print(print_green("✓"))
        else:
            changes_failed += 1
            print(print_yellow("(failed)"))

    # Summary
    print()
    if changes_made == 0:
        print(print_yellow("  No changes were generated."))
        return False

    print(print_green(f"  ✓ {changes_made} section(s) revised") +
          (f", {changes_failed} failed" if changes_failed else ""))
    print()

    # Reassemble PRD
    reassembled = reassemble_prd(prd_content, sections, revised_sections, appendix_content)

    # Sanity check
    if len(reassembled.strip()) < len(prd_content) * 0.5:
        print(print_red("  ✗ Reassembled PRD is much shorter than original — aborting"))
        return False

    print("    " + print_green("[apply]") + "   Apply revisions")
    print("    " + print_red("[discard]") + " Discard and keep current PRD")
    print()

    choice = prompt_user("  Choice (default: apply): ").strip().lower() or "apply"

    if choice == "apply":
        # Backup current PRD
        backup_file = prd_file.parent / f"PRD.backup.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
        write_file(backup_file, prd_content)

        # Apply revision
        write_file(prd_file, reassembled)
        print(print_green(f"  ✓ Revision applied (backup: {backup_file.name})"))
        return True
    else:
        print(print_yellow("  Revision discarded"))
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_resolution_plan(plan: str) -> List[Dict[str, str]]:
    """
    Parse the formatted resolution plan text into structured dicts.

    Input format (from conduct_qa_session):
      1. [RECOMMENDATION] P0: Add explicit mapping...
         RESOLUTION: Apply this recommendation as described

    Returns list of {"type": "RECOMMENDATION", "detail": "...", "resolution": "..."}
    """
    resolutions = []
    # Split on numbered items
    items = re.split(r'\n\d+\.\s+', "\n" + plan)

    for item in items:
        item = item.strip()
        if not item:
            continue

        # Extract type
        type_match = re.match(r'\[(\w+)\]\s*(.*)', item)
        if type_match:
            issue_type = type_match.group(1)
            rest = type_match.group(2)
        else:
            issue_type = "FIX"
            rest = item

        # Split on RESOLUTION:
        parts = re.split(r'\n\s*RESOLUTION:\s*', rest, maxsplit=1)
        detail = parts[0].strip()
        resolution = parts[1].strip() if len(parts) > 1 else "Apply as described"

        resolutions.append({
            "type": issue_type,
            "detail": detail,
            "resolution": resolution,
        })

    return resolutions


def reassemble_prd(
    original: str,
    sections: List[Dict[str, Any]],
    revised_sections: Dict[str, str],
    appendix_content: Optional[str],
) -> str:
    """
    Reassemble the PRD from original + revised sections + appendix.

    For each section: use revised version if available, otherwise keep original.
    Append new appendix content at the end.
    """
    parts = []

    for section in sections:
        num = section["number"]
        if num in revised_sections:
            parts.append(revised_sections[num])
        else:
            parts.append(section["body"])

    result = "".join(parts)

    # Append new appendix content
    if appendix_content:
        result = result.rstrip() + "\n\n" + appendix_content + "\n"

    return result


# ---------------------------------------------------------------------------
# Q&A session (unchanged)
# ---------------------------------------------------------------------------

def prd_revision_flow(
    validation_file: Path,
    prd_file: Path,
    prompts_dir: Path
) -> bool:
    """
    Execute PRD revision Q&A flow.

    Args:
        validation_file: Path to validation results
        prd_file: Path to PRD file
        prompts_dir: Path to prompts directory

    Returns:
        True if revision completed, False if aborted
    """
    print()
    print(print_cyan("┌─────────────────────────────────────────────────────────┐"))
    print(print_cyan("│ " + print_bold("PRD REVISION — GUIDED Q&A") + "                               │"))
    print(print_cyan("└─────────────────────────────────────────────────────────┘"))
    print()
    print(print_dim("  Walk through each issue and decide how to resolve it."))
    print(print_dim("  Changes are applied per-section for speed and reliability."))
    print()

    # Load validation results
    try:
        with open(validation_file, 'r') as f:
            validation_data = json.load(f)
    except Exception as e:
        print(print_red(f"  ✗ Error loading validation results: {e}"))
        return False

    # Collect issues from validation
    issues = collect_issues(validation_data)

    if not issues:
        print(print_yellow("  No issues found in validation results."))
        print()
        manual_input = prompt_user("  Enter revision instructions manually (or Enter to skip): ").strip()
        if not manual_input:
            return False

        return invoke_revision_agent(prd_file, prompts_dir, manual_input)

    # Q&A session
    resolution_plan = conduct_qa_session(issues)

    if not resolution_plan:
        print(print_yellow("  No resolutions to apply."))
        return False

    # Apply revisions
    return invoke_revision_agent(prd_file, prompts_dir, resolution_plan)


def collect_issues(validation_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Collect issues from validation results, sorted by priority."""
    issues = []

    # Contradictions (highest priority)
    for item in validation_data.get("consistency", {}).get("contradictions", []):
        issues.append({"type": "CONTRADICTION", "detail": item, "priority": 0})

    # Completeness gaps
    for item in validation_data.get("completeness", {}).get("gaps", []):
        issues.append({"type": "GAP", "detail": item, "priority": 1})

    # Recommendations
    for item in validation_data.get("recommendations", []):
        priority = 2
        if item.startswith("P0:"):
            priority = 0
        elif item.startswith("P1:"):
            priority = 1
        issues.append({"type": "RECOMMENDATION", "detail": item, "priority": priority})

    issues.sort(key=lambda x: x["priority"])
    return issues


def conduct_qa_session(issues: List[Dict[str, str]]) -> str:
    """Conduct Q&A session for issue resolution. Returns formatted plan string."""
    total = len(issues)

    print(f"  {print_bold(f'{total} issues to review.')} For each one you can:")
    print("    " + print_green("Enter") + "       Accept the suggested fix (default)")
    print("    " + print_cyan("Type") + "        Provide your own resolution direction")
    print("    " + print_yellow("skip") + "        Skip this issue (don't fix)")
    print("    " + print_red("done") + "        Stop reviewing, apply what you've decided so far")
    print()
    print(print_dim("─" * 60))

    resolution_plan = ""
    resolved_count = 0
    skipped_count = 0

    for idx, issue in enumerate(issues):
        num = idx + 1
        issue_type = issue["type"]
        detail = issue["detail"]

        if issue_type == "CONTRADICTION":
            color = print_red
        elif issue_type == "GAP":
            color = print_yellow
        else:
            color = print_cyan

        print()
        print(f"  {color(f'[{issue_type}]')} {print_bold(f'({num}/{total})')}")
        print(f"  {detail}")
        print()

        suggestion = suggest_resolution(issue_type, detail)
        print(print_dim(f"  Suggested: {suggestion}"))

        user_response = prompt_user("  Resolution (default: accept): ").strip()

        if user_response == "done":
            print()
            print(print_dim(f"  Stopping review. {total - num} issues remaining."))
            break
        elif user_response in ["skip", "s"]:
            skipped_count += 1
            print(print_dim("    -> Skipped"))
            continue
        elif not user_response or user_response in ["accept", "a"]:
            resolution_plan += f"{resolved_count + 1}. [{issue_type}] {detail}\n   RESOLUTION: {suggestion}\n\n"
            resolved_count += 1
            print(print_green(f"    -> {suggestion}"))
        else:
            resolution_plan += f"{resolved_count + 1}. [{issue_type}] {detail}\n   RESOLUTION: {user_response}\n\n"
            resolved_count += 1
            print(print_green(f"    -> {user_response}"))

    print()
    print(print_dim("─" * 60))
    print()
    print(f"  {print_bold('Review complete:')} {resolved_count} resolved, {skipped_count} skipped")
    print()

    return resolution_plan if resolved_count > 0 else ""


def suggest_resolution(issue_type: str, detail: str) -> str:
    """Suggest resolution based on issue type."""
    if issue_type == "CONTRADICTION":
        return "Resolve in favor of Phase 1 original requirements"
    elif issue_type == "GAP":
        return "Add the missing content to the appropriate section"
    elif issue_type == "RECOMMENDATION":
        return "Apply this recommendation as described"
    else:
        return "Address this issue appropriately"


if __name__ == "__main__":
    print("This module should be imported by task 206/207, not run directly.")
    sys.exit(1)
