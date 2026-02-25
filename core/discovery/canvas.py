"""
Discovery Canvas — PRD Coverage Tracker

Maps conversation evidence to PRD section readiness during Discovery.
Updated after every substantive exchange via lightweight Haiku classification.
Displayed to the user as a progress indicator showing which PRD sections
have direct evidence and which will be inferred by the PRD author.

Cross-reference: PRD_SECTIONS here must align with the section structure
in phases/phase_02_prd/tasks/task_205_prd_authoring.py (PRD_SECTIONS constant).
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PRD Section Definitions
# ---------------------------------------------------------------------------
# These MUST align with task_205_prd_authoring.py PRD_SECTIONS (gen 1-12).
# String IDs are used for canvas keying; gen numbers match task_205.

PRD_SECTIONS = [
    {"id": "vision",        "name": "Vision & Executive Summary",     "gen": 1},
    {"id": "architecture",  "name": "Technical Architecture",          "gen": 2},
    {"id": "features",      "name": "Feature Requirements",            "gen": 3},
    {"id": "nfr",           "name": "Non-Functional Requirements",     "gen": 4},
    {"id": "dependencies",  "name": "Logical Dependency Chain",        "gen": 5},
    {"id": "phases",        "name": "Development Phases",              "gen": 6},
    {"id": "code_structure", "name": "Code Structure & Organization",  "gen": 7},
    {"id": "tdd",           "name": "TDD & Test Strategy",             "gen": 8},
    {"id": "integration",   "name": "Integration Testing Strategy",    "gen": 9},
    {"id": "documentation", "name": "Documentation Requirements",      "gen": 10},
    {"id": "operations",    "name": "Operational Requirements",        "gen": 11},
    {"id": "risks",         "name": "Risks & Success Metrics",         "gen": 12},
]

SECTION_IDS = [s["id"] for s in PRD_SECTIONS]

# Map section_id -> human-readable name for quick lookup
_SECTION_NAMES = {s["id"]: s["name"] for s in PRD_SECTIONS}

# ---------------------------------------------------------------------------
# Section Probes — targeted questions for gap-filling
# ---------------------------------------------------------------------------

SECTION_PROBES = {
    "vision": (
        "Can you articulate the core problem and why solving it matters now?"
    ),
    "architecture": (
        "What's the technical approach? Monolith vs. microservices, "
        "key technology choices, external systems it integrates with?"
    ),
    "features": (
        "What are the core features a user would interact with? "
        "What does the happy path look like?"
    ),
    "nfr": (
        "What non-functional requirements matter most — performance "
        "targets, security posture, scalability expectations, compliance needs?"
    ),
    "dependencies": (
        "What depends on what? Are there features that can't start "
        "until others are complete?"
    ),
    "phases": (
        "How should development be phased? What needs to ship first, "
        "and what can come later?"
    ),
    "code_structure": (
        "Any preferences on code organization? Monorepo vs. multi-repo, "
        "module structure, design patterns?"
    ),
    "tdd": (
        "How important is testing for this project? Any specific "
        "testing strategy, coverage targets, or TDD requirements?"
    ),
    "integration": (
        "How will components be integration-tested? Are there "
        "external services or APIs that need end-to-end validation?"
    ),
    "documentation": (
        "What documentation does this project need? API docs, user guides, "
        "developer onboarding, architecture decision records?"
    ),
    "operations": (
        "How will this be deployed and operated? Any CI/CD, monitoring, "
        "infrastructure, or DevOps requirements?"
    ),
    "risks": (
        "What keeps you up at night about this project? What could "
        "go wrong, and how would we know if it's succeeding?"
    ),
}


# ---------------------------------------------------------------------------
# Canvas State
# ---------------------------------------------------------------------------

@dataclass
class CanvasState:
    """Live coverage state for Discovery -> PRD mapping."""

    scores: Dict[str, float] = field(
        default_factory=lambda: {s["id"]: 0.0 for s in PRD_SECTIONS}
    )
    evidence: Dict[str, List[Tuple[int, str]]] = field(
        default_factory=lambda: {s["id"]: [] for s in PRD_SECTIONS}
    )
    classifications: List[Dict[str, float]] = field(default_factory=list)

    def update(self, turn: int, classification: Dict[str, float],
               exchange_snippet: str):
        """Update canvas with a new exchange classification.

        Uses diminishing returns: first evidence for a section is worth
        more than the fifth. Formula: new = current + relevance * (1 - current) * 0.5
        This asymptotically approaches 1.0 but never wastes signal.
        """
        for section_id, relevance in classification.items():
            if section_id not in self.scores:
                continue
            if relevance < 0.1:
                continue

            current = self.scores[section_id]
            increment = relevance * (1.0 - current) * 0.5
            self.scores[section_id] = min(1.0, current + increment)
            self.evidence[section_id].append((turn, exchange_snippet[:200]))

        self.classifications.append(classification)

    @property
    def overall_coverage(self) -> float:
        """Overall coverage percentage (0.0-1.0)."""
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)

    @property
    def empty_sections(self) -> List[str]:
        """Section IDs with zero coverage."""
        return [sid for sid in SECTION_IDS if self.scores.get(sid, 0.0) < 0.05]

    @property
    def thin_sections(self) -> List[str]:
        """Section IDs with some but weak coverage (0.05-0.3)."""
        return [
            sid for sid in SECTION_IDS
            if 0.05 <= self.scores.get(sid, 0.0) < 0.3
        ]

    @property
    def strong_sections(self) -> List[str]:
        """Section IDs with good coverage (>=0.5)."""
        return [sid for sid in SECTION_IDS if self.scores.get(sid, 0.0) >= 0.5]

    def get_section_label(self, section_id: str) -> str:
        """Human-readable coverage label for a section."""
        score = self.scores.get(section_id, 0.0)
        if score < 0.05:
            return "Empty"
        elif score < 0.2:
            return "Mentioned"
        elif score < 0.4:
            return "Thin"
        elif score < 0.6:
            return "Moderate"
        elif score < 0.8:
            return "Good"
        else:
            return "Strong"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSON storage."""
        return {
            "scores": dict(self.scores),
            "evidence": {k: [(t, s) for t, s in v] for k, v in self.evidence.items()},
            "overall_coverage": self.overall_coverage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CanvasState":
        """Deserialize from JSON."""
        state = cls()
        if "scores" in data:
            for sid in SECTION_IDS:
                state.scores[sid] = data["scores"].get(sid, 0.0)
        if "evidence" in data:
            for sid in SECTION_IDS:
                raw = data["evidence"].get(sid, [])
                state.evidence[sid] = [(t, s) for t, s in raw]
        return state


# ---------------------------------------------------------------------------
# Display Functions
# ---------------------------------------------------------------------------

def render_canvas(canvas: CanvasState) -> str:
    """Render the canvas as a terminal-friendly string with progress bars."""
    pct = int(canvas.overall_coverage * 100)
    lines = []
    lines.append("")
    lines.append(f"  DISCOVERY CANVAS                                    Coverage: {pct}%")
    lines.append("  " + "-" * 65)

    bar_width = 23
    for section in PRD_SECTIONS:
        sid = section["id"]
        score = canvas.scores.get(sid, 0.0)
        filled = int(score * bar_width)
        bar = "#" * filled + "." * (bar_width - filled)
        label = canvas.get_section_label(sid)
        name = section["name"]
        lines.append(f"  {bar}  {name:<38s} {label}")

    lines.append("  " + "-" * 65)

    empty_count = len(canvas.empty_sections)
    if empty_count > 0:
        lines.append(f"  {empty_count} section(s) have no coverage — the PRD will infer these.")
    else:
        lines.append("  All sections have some discovery evidence.")
    lines.append("")
    return "\n".join(lines)


def render_canvas_compact(canvas: CanvasState) -> str:
    """Render a single-line summary for inline display."""
    pct = int(canvas.overall_coverage * 100)
    parts = [f"Canvas: {pct}%"]

    strong = canvas.strong_sections
    if strong:
        names = [_SECTION_NAMES.get(s, s) for s in strong[:3]]
        short = [n.split(" ")[0] for n in names]  # First word only
        parts.append(f"Strong: {', '.join(short)}")

    empty = canvas.empty_sections
    if empty:
        names = [_SECTION_NAMES.get(s, s) for s in empty[:3]]
        short = [n.split(" ")[0] for n in names]
        suffix = f" +{len(empty) - 3}" if len(empty) > 3 else ""
        parts.append(f"Gaps: {', '.join(short)}{suffix}")

    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Gap Suggestion
# ---------------------------------------------------------------------------

def suggest_next_topic(canvas: CanvasState) -> Optional[str]:
    """Suggest what to discuss next based on the emptiest section.

    Prioritizes by PRD generation order (earlier sections have more
    downstream impact on the PRD).

    Returns None if all sections have some coverage.
    """
    empty = canvas.empty_sections
    if not empty:
        # Check thin sections
        thin = canvas.thin_sections
        if not thin:
            return None
        # Pick the thinnest by score, break ties by gen order
        thinnest = min(thin, key=lambda sid: canvas.scores.get(sid, 0.0))
        probe = SECTION_PROBES.get(thinnest)
        if probe:
            name = _SECTION_NAMES.get(thinnest, thinnest)
            return f"[{name}] {probe}"
        return None

    # Pick first empty section (already in gen order via SECTION_IDS)
    target = empty[0]
    probe = SECTION_PROBES.get(target)
    if probe:
        name = _SECTION_NAMES.get(target, target)
        return f"[{name}] {probe}"
    return None


# ---------------------------------------------------------------------------
# Classification (LLM Call)
# ---------------------------------------------------------------------------

_CLASSIFY_PROMPT_TEMPLATE = """You are a conversation classifier. Given a conversation exchange, rate its relevance to each PRD section on a scale of 0.0 to 1.0.

## Exchange
{exchange_text}

## Sections to score
vision: Vision, goals, problem statement, executive summary
architecture: Technical architecture, system design, components, APIs, databases
features: Feature requirements, user stories, functional capabilities
nfr: Non-functional requirements: performance, security, scalability, compliance
dependencies: Logical dependencies between components or features
phases: Development phases, milestones, timeline, sequencing
code_structure: Code organization, directory structure, modules, patterns
tdd: Testing strategy, TDD approach, unit tests, test coverage
integration: Integration testing, end-to-end testing, system testing
documentation: Documentation requirements, API docs, user guides
operations: Deployment, monitoring, CI/CD, infrastructure, DevOps
risks: Risks, mitigation strategies, success metrics, KPIs

## Response format
Respond ONLY with a JSON object. No other text.
Example: {{"vision": 0.9, "architecture": 0.3, "risks": 0.2}}
Only include sections with relevance > 0.0.
"""


def classify_exchange(
    exchange_text: str,
    prompts_dir: Path,
    turn: int,
    model: str = "haiku",
) -> Dict[str, float]:
    """Classify a conversation exchange against PRD sections.

    Uses a lightweight Haiku-tier LLM call (~300 token input, ~50 token output).
    Returns empty dict on any failure (graceful degradation).

    Args:
        exchange_text: Combined user input + agent response
        prompts_dir: Directory for prompt/response files
        turn: Current turn number (for file naming)
        model: LLM model tier to use (default "haiku")

    Returns:
        Dict mapping section_id -> relevance score (0.0-1.0).
        Only sections with relevance > 0.0 are included.
    """
    try:
        from core.llm import invoke_llm as invoke
    except ImportError:
        logger.debug("LLM invoke not available for canvas classification")
        return {}

    # Cap input length, truncating at the last space to avoid mid-word cuts
    if len(exchange_text) > 2000:
        truncated = exchange_text[:2000].rsplit(' ', 1)[0]
    else:
        truncated = exchange_text
    prompt = _CLASSIFY_PROMPT_TEMPLATE.format(
        exchange_text=truncated
    )

    prompt_file = prompts_dir / f"canvas-classify-{turn}.md"
    output_file = prompts_dir / f"canvas-classify-{turn}-output.txt"

    try:
        prompt_file.write_text(prompt)
        invoke(str(prompt_file), str(output_file), "Classify exchange", model=model)

        if not output_file.exists():
            return {}

        raw = output_file.read_text().strip()
        return _parse_classification(raw)

    except Exception as e:
        logger.debug("Canvas classification failed for turn %d: %s", turn, e)
        return {}


def _parse_classification(raw: str) -> Dict[str, float]:
    """Parse LLM classification response into section scores.

    Handles JSON embedded in markdown code blocks or plain JSON.
    Returns empty dict on parse failure.
    """
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (fences)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                logger.debug("Failed to parse classification JSON: %s", text[:100])
                return {}
        else:
            return {}

    if not isinstance(data, dict):
        return {}

    result = {}
    for key, value in data.items():
        if key in SECTION_IDS:
            try:
                score = float(value)
                if 0.0 < score <= 1.0:
                    result[key] = score
            except (ValueError, TypeError):
                continue

    return result


# ---------------------------------------------------------------------------
# PRD Preview
# ---------------------------------------------------------------------------

def generate_prd_preview(canvas: CanvasState, consensus: Dict[str, Any] = None) -> str:
    """Generate a preview of what each PRD section will contain.

    Uses canvas evidence to produce a status line per section.
    Sections with no evidence get [INFERRED] label.

    Args:
        canvas: Current canvas state
        consensus: Optional consensus dict from task 105

    Returns:
        Formatted string for terminal display
    """
    lines = []
    lines.append("  PRD Section Preview")
    lines.append("  " + "-" * 55)

    for section in PRD_SECTIONS:
        sid = section["id"]
        gen = section["gen"]
        name = section["name"]
        label = canvas.get_section_label(sid)
        evidence_list = canvas.evidence.get(sid, [])
        count = len(evidence_list)

        if count == 0:
            tag = "[INFERRED]"
        else:
            tag = f"[{label.upper()} — {count} finding{'s' if count != 1 else ''}]"

        # Show a snippet from the strongest evidence if available
        snippet = ""
        if evidence_list:
            # Use the latest evidence snippet
            _, last_snippet = evidence_list[-1]
            # Extract a brief quote (first sentence or 80 chars)
            brief = last_snippet[:80].replace("\n", " ")
            if len(last_snippet) > 80:
                brief += "..."
            snippet = f'\n      "{brief}"'

        lines.append(f"  {gen:>2}. {name:<38s} {tag}{snippet}")

    lines.append("  " + "-" * 55)
    return "\n".join(lines)
