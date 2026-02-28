"""Content Signal Detection for memory prioritization.

Detects semantic importance markers in text content. Used by memory
compaction (Capability 3) and priority-based memory (Capability 7)
to weight entries by their informational value.
"""

import re
from dataclasses import dataclass

# Compiled regexes for efficiency — evaluated once at import time.
_RE_CODE_BLOCK = re.compile(r"```")
_RE_DECISION = re.compile(
    r"\b(decided|selected|chose|chosen|approved|rejected|accepted|finalized)\b",
    re.IGNORECASE,
)
_RE_ERROR = re.compile(
    r"\b(failed|error|bug|vulnerability|breaking|critical|exception|crash)\b",
    re.IGNORECASE,
)
_RE_QUESTION = re.compile(
    r"(\?|(?<!\w)TBD(?!\w)|(?<!\w)TODO(?!\w)|open question)",
    re.IGNORECASE,
)
_RE_ROUTINE = re.compile(
    r"\b(acknowledged|skipping|already complete|no changes|no action)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ContentSignals:
    """Detected semantic signals in a piece of content."""

    has_code_block: bool         # ``` markers → +0.15
    has_decision_keywords: bool  # decided/selected/chose/approved/rejected → +0.10
    has_error_keywords: bool     # failed/error/bug/vulnerability/breaking → +0.10
    has_question_markers: bool   # ?/TBD/TODO/open question → +0.05
    has_routine_keywords: bool   # acknowledged/skipping/already complete → -0.10

    def score(self) -> float:
        """Aggregate signal score in [-0.10, +0.40]."""
        total = 0.0
        if self.has_code_block:
            total += 0.15
        if self.has_decision_keywords:
            total += 0.10
        if self.has_error_keywords:
            total += 0.10
        if self.has_question_markers:
            total += 0.05
        if self.has_routine_keywords:
            total -= 0.10
        return total


def detect_signals(content: str) -> ContentSignals:
    """Detect semantic importance signals in *content*.

    Pure pattern matching — no LLM calls.
    """
    return ContentSignals(
        has_code_block=bool(_RE_CODE_BLOCK.search(content)),
        has_decision_keywords=bool(_RE_DECISION.search(content)),
        has_error_keywords=bool(_RE_ERROR.search(content)),
        has_question_markers=bool(_RE_QUESTION.search(content)),
        has_routine_keywords=bool(_RE_ROUTINE.search(content)),
    )


def assign_priority(content: str, entry_type: str) -> str:
    """Assign a memory priority level based on content signals and entry type.

    Returns one of P0-P4:
        P0 — Critical: breaking changes, security (error signals + critical entry type)
        P1 — High: key decisions, blockers
        P2 — Standard: task outcomes (default)
        P3 — Low: progress notes
        P4 — Ephemeral: ACK, routine
    """
    signals = detect_signals(content)

    # P0: error keywords combined with checkpoint or phase closeout
    if signals.has_error_keywords and entry_type in ("checkpoint", "phase_closeout"):
        return "P0"

    # P1: decision keywords or task_end entry type
    if signals.has_decision_keywords or entry_type == "task_end":
        return "P1"

    # P4: routine keywords with no other positive signals
    if signals.has_routine_keywords and not (
        signals.has_code_block or signals.has_decision_keywords
        or signals.has_error_keywords or signals.has_question_markers
    ):
        return "P4"

    # P3: routine keywords or task_start
    if signals.has_routine_keywords or entry_type == "task_start":
        return "P3"

    # P2: default
    return "P2"
