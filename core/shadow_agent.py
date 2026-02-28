"""Shadow Agent — background audit evaluation during task execution.

Runs audit checks in the background during task execution for STANDARD
and INTENSIVE gravity tasks. Uses haiku model for token efficiency.
Writes findings as ReviewFinding nodes with shadow_finding=True.

Non-blocking: evaluate_async() submits to a 2-thread pool.
"""

import logging
import re
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Thread pool for non-blocking evaluation (module-level, reused)
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="shadow-audit")

AUDIT_PROMPT = (
    "You are a shadow auditor performing a quick review. "
    "Check the following task output against these audit criteria:\n\n"
    "Criteria:\n{criteria}\n\n"
    "Task: {task_name}\nPhase: {phase_id}\n\n"
    "Content to audit:\n{content}\n\n"
    "For each issue found, respond with one line per finding:\n"
    "FINDING: <severity>|<category>|<description>\n"
    "Severities: critical, major, minor, suggestion\n"
    "If no issues found, respond with: NO_FINDINGS"
)


@dataclass
class ShadowContext:
    """Context for shadow audit evaluation."""

    task_id: str
    task_name: str
    phase_id: str
    content: str           # Task output / memory content
    artifacts: List[str] = field(default_factory=list)


@dataclass
class ShadowFinding:
    """A finding from the shadow audit."""

    id: str
    severity: str          # critical/major/minor/suggestion
    category: str
    description: str
    task_id: str
    phase_id: str


class ShadowAgent:
    """Background audit agent activated for STANDARD/INTENSIVE gravity."""

    ACTIVE_GRAVITY_LEVELS = {"standard", "intensive"}
    # Number of audit criteria to check per gravity level
    _CRITERIA_LIMITS = {"standard": 5, "intensive": 10}

    def __init__(self, graph=None):
        self._graph = graph

    @staticmethod
    def should_activate(gravity: str) -> bool:
        """Check if the shadow agent should be active for this gravity."""
        return gravity in ShadowAgent.ACTIVE_GRAVITY_LEVELS

    def evaluate(self, context: ShadowContext) -> List[ShadowFinding]:
        """Synchronously evaluate a task against audit criteria.

        Args:
            context: Shadow audit context.

        Returns:
            List of findings (may be empty).
        """
        # Get relevant audit criteria from graph
        criteria = self._get_criteria(context)
        if not criteria:
            return []

        # Invoke LLM for audit
        findings = self._run_audit(context, criteria)

        # Write findings to graph
        for finding in findings:
            self._persist_finding(finding)

        return findings

    def evaluate_async(self, context: ShadowContext) -> Optional[Future]:
        """Submit evaluation to thread pool (non-blocking).

        Args:
            context: Shadow audit context.

        Returns:
            Future that resolves to List[ShadowFinding], or None if skipped.
        """
        try:
            return _POOL.submit(self.evaluate, context)
        except Exception as e:
            logger.debug("Shadow async submit failed: %s", e)
            return None

    def _get_criteria(self, context: ShadowContext) -> List[str]:
        """Query graph for relevant audit criteria."""
        gravity = "standard"  # Default
        limit = self._CRITERIA_LIMITS.get(gravity, 5)

        if self._graph is not None:
            try:
                nodes = self._graph.reader.get_nodes(
                    "Audit",
                    filters={"status": "active"},
                    limit=limit,
                )
                return [
                    f"[{n.get('category', '')}] {n.get('name', '')}: "
                    f"{n.get('description_what', '')}"
                    for n in nodes
                ]
            except Exception as e:
                logger.debug("Audit criteria query failed: %s", e)

        # Fallback: basic criteria
        return [
            "Check for security vulnerabilities (injection, XSS, auth bypass)",
            "Check for error handling gaps (unhandled exceptions, missing validation)",
            "Check for code quality issues (unused imports, dead code, naming)",
        ]

    def _run_audit(
        self, context: ShadowContext, criteria: List[str],
    ) -> List[ShadowFinding]:
        """Run the audit via LLM."""
        try:
            from core.llm.invoke import invoke_llm

            criteria_text = "\n".join(f"- {c}" for c in criteria)
            prompt = AUDIT_PROMPT.format(
                criteria=criteria_text,
                task_name=context.task_name,
                phase_id=context.phase_id,
                content=context.content[:3000],
            )

            response = invoke_llm(prompt=prompt, model="haiku")
            if not response:
                return []

            return self._parse_findings(response, context)

        except Exception as e:
            logger.debug("Shadow audit LLM call failed: %s", e)
            return []

    def _parse_findings(
        self, response: str, context: ShadowContext,
    ) -> List[ShadowFinding]:
        """Parse FINDING: lines from LLM response."""
        if "NO_FINDINGS" in response.upper():
            return []

        findings = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line.upper().startswith("FINDING:"):
                continue

            parts = line.split(":", 1)[1].strip().split("|", 2)
            if len(parts) < 3:
                continue

            severity = parts[0].strip().lower()
            if severity not in ("critical", "major", "minor", "suggestion"):
                severity = "suggestion"

            findings.append(ShadowFinding(
                id=f"shadow-{uuid.uuid4().hex[:12]}",
                severity=severity,
                category=parts[1].strip(),
                description=parts[2].strip(),
                task_id=context.task_id,
                phase_id=context.phase_id,
            ))

        return findings

    def _persist_finding(self, finding: ShadowFinding) -> None:
        """Write a finding to the knowledge graph."""
        if self._graph is None:
            return

        try:
            self._graph.writer.create_node(
                "ReviewFinding",
                {
                    "id": finding.id,
                    "severity": finding.severity,
                    "category": finding.category,
                    "description": finding.description,
                    "shadow_finding": True,
                    "status": "open",
                    "phase": finding.phase_id,
                },
            )

            # Link to the task
            self._graph.writer.create_relationship(
                "ReviewFinding", finding.id,
                "REVIEW_OF",
                "Task", finding.task_id,
            )

        except Exception as e:
            logger.debug("Shadow finding persist failed: %s", e)
