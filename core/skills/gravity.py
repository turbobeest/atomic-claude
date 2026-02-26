"""Task Gravity Assessment — 5-signal consequence density classifier.

Evaluates task risk and adjusts pipeline rigor via a weighted multi-signal
system.  The design is intentionally **asymmetric**: false-light is strictly
worse than false-intensive.  A wasted hour from over-classifying is
recoverable; a production bug from under-classifying is not.

Signals
-------
1. Prompt analysis   (weight 1.0) — linguistic markers
2. Domain detection  (weight 1.5) — high-consequence domain keywords
3. File sensitivity  (weight 1.2) — sensitive file-path patterns
4. Graph context     (weight 0.8) — FalkorDB project history (graceful fallback)
5. Reversibility     (weight 1.3) — irreversible-operation patterns

Usage::

    from core.skills.gravity import GravityClassifier
    classifier = GravityClassifier()
    result = classifier.assess("Add Stripe checkout endpoint", project_id="my-app")
    print(result.gravity, result.confidence, result.reasoning)
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

from core.skills.models import GravityAssessment, GravityLevel, GravitySignal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gravity ordering for floor comparisons
# ---------------------------------------------------------------------------
_GRAVITY_ORDER: Dict[GravityLevel, int] = {
    GravityLevel.LIGHT: 0,
    GravityLevel.STANDARD: 1,
    GravityLevel.INTENSIVE: 2,
}


def _gravity_max(a: GravityLevel, b: GravityLevel) -> GravityLevel:
    """Return the higher of two gravity levels."""
    return a if _GRAVITY_ORDER[a] >= _GRAVITY_ORDER[b] else b


# ---------------------------------------------------------------------------
# Signal 1 — Prompt analysis keyword sets
# ---------------------------------------------------------------------------
LIGHT_INDICATORS: List[str] = [
    "typo", "rename", "comment", "log", "print", "readme", "gitignore",
    "changelog", "todo", "fixme", "whitespace", "indent", "format", "lint",
    "spelling", "docs", "debug",
]

STANDARD_INDICATORS: List[str] = [
    "endpoint", "api", "component", "feature", "refactor", "pagination",
    "validation", "form", "route", "handler", "middleware", "service",
    "controller", "model",
]

INTENSIVE_INDICATORS: List[str] = [
    "migration", "schema change", "deploy", "production", "security",
    "vulnerability", "concurrent", "race condition", "transaction",
    "rollback", "breaking change", "backwards compat", "data loss",
    "irreversible",
]

# ---------------------------------------------------------------------------
# Signal 2 — High-consequence domains
# ---------------------------------------------------------------------------
HIGH_CONSEQUENCE_DOMAINS: Dict[str, Dict] = {
    "authentication": {
        "keywords": [
            "auth", "oauth", "jwt", "token", "login", "session", "password",
            "credential", "saml", "sso", "mfa", "2fa",
        ],
        "floor": GravityLevel.INTENSIVE,
        "bias": 0.6,
    },
    "payments": {
        "keywords": [
            "payment", "stripe", "billing", "subscription", "charge",
            "invoice", "refund", "transaction", "checkout", "pricing",
        ],
        "floor": GravityLevel.INTENSIVE,
        "bias": 0.7,
    },
    "encryption": {
        "keywords": [
            "encrypt", "decrypt", "aes", "rsa", "cipher", "hash", "salt",
            "pii", "gdpr", "hipaa", "pci",
        ],
        "floor": GravityLevel.INTENSIVE,
        "bias": 0.6,
    },
    "database_migration": {
        "keywords": [
            "migration", "alter table", "drop table", "add column", "schema",
            "migrate", "sequel", "flyway", "alembic",
        ],
        "floor": GravityLevel.INTENSIVE,
        "bias": 0.5,
    },
    "infrastructure": {
        "keywords": [
            "terraform", "kubernetes", "k8s", "docker", "helm", "ansible",
            "ci/cd", "pipeline", "deploy", "production",
        ],
        "floor": GravityLevel.STANDARD,
        "bias": 0.4,
    },
    "concurrency": {
        "keywords": [
            "concurrent", "parallel", "thread", "lock", "mutex", "semaphore",
            "race condition", "deadlock", "async", "atomic",
        ],
        "floor": GravityLevel.INTENSIVE,
        "bias": 0.5,
    },
    "financial": {
        "keywords": [
            "financial", "accounting", "ledger", "balance", "interest", "tax",
            "revenue", "profit", "audit trail",
        ],
        "floor": GravityLevel.INTENSIVE,
        "bias": 0.6,
    },
}

# ---------------------------------------------------------------------------
# Signal 3 — File sensitivity patterns
# ---------------------------------------------------------------------------
INTENSIVE_FILE_PATTERNS: List[str] = [
    "migration", ".env", "secrets", "credentials", "dockerfile", "terraform",
    "helm", "nginx.conf", "middleware", "interceptor",
]

STANDARD_FILE_PATTERNS: List[str] = [
    "config", "settings", "package.json", "requirements.txt", "makefile",
    "webpack",
]

# ---------------------------------------------------------------------------
# Signal 5 — Reversibility keywords
# ---------------------------------------------------------------------------
IRREVERSIBLE_KEYWORDS: List[str] = [
    "drop", "truncate", "delete all", "rm -rf", "force push",
    "reset --hard", "send email", "notify customer", "publish", "release",
    "deploy to prod", "irreversible", "permanent", "cannot undo",
    "no rollback", "destructive",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_keywords(text: str) -> List[str]:
    """Extract relevant keywords for graph queries.

    Tokenizes the input, removes common stop-words, and returns unique
    lower-cased keywords that are likely useful for similarity searches.
    """
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "shall",
        "should", "may", "might", "must", "can", "could", "and", "but", "or",
        "nor", "not", "so", "yet", "both", "either", "neither", "each",
        "every", "all", "any", "few", "more", "most", "other", "some", "such",
        "no", "only", "own", "same", "than", "too", "very", "just", "because",
        "as", "until", "while", "of", "at", "by", "for", "with", "about",
        "against", "between", "through", "during", "before", "after", "above",
        "below", "to", "from", "up", "down", "in", "out", "on", "off", "over",
        "under", "again", "further", "then", "once", "here", "there", "when",
        "where", "why", "how", "what", "which", "who", "whom", "this", "that",
        "these", "those", "i", "me", "my", "myself", "we", "our", "ours",
        "you", "your", "yours", "he", "him", "his", "she", "her", "hers",
        "it", "its", "they", "them", "their", "theirs",
    }
    tokens = re.findall(r"[a-z0-9][a-z0-9_.-]*[a-z0-9]|[a-z0-9]", text.lower())
    seen: set = set()
    keywords: List[str] = []
    for tok in tokens:
        if tok not in stop_words and tok not in seen and len(tok) > 1:
            seen.add(tok)
            keywords.append(tok)
    return keywords


def _count_matches(text: str, patterns: List[str]) -> Tuple[float, List[str]]:
    """Count how many patterns appear in *text* (already lowered).

    Returns (match_count, list_of_matched_patterns).
    """
    matched: List[str] = []
    for pat in patterns:
        if pat in text:
            matched.append(pat)
    return float(len(matched)), matched


def _word_boundary_match(text: str, keyword: str) -> bool:
    r"""Check if *keyword* appears in *text* as a whole word (or phrase).

    Uses ``\b`` word-boundary assertions so that, e.g., "sso" does NOT
    match inside "processorder".
    """
    return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text))


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class GravityClassifier:
    """Multi-signal task gravity classifier.

    Evaluates 5 orthogonal signals to classify a task as LIGHT, STANDARD,
    or INTENSIVE.  The classifier is intentionally biased toward caution:
    the asymmetric confidence gate means it is harder to classify a task as
    LIGHT than as INTENSIVE.
    """

    # Asymmetric confidence gate for LIGHT classification
    LIGHT_SCORE_THRESHOLD = -0.2
    INTENSIVE_SCORE_THRESHOLD = 0.35
    LIGHT_CONFIDENCE_THRESHOLD = 0.5
    LIGHT_PENALTY_MULTIPLIER = 0.85

    def assess(
        self,
        task_prompt: str,
        project_id: str = "default",
        user_override: Optional[GravityLevel] = None,
    ) -> GravityAssessment:
        """Classify a task's gravity.

        Parameters
        ----------
        task_prompt:
            Free-text task description.
        project_id:
            Project identifier for graph-context lookups.
        user_override:
            If provided, bypass classification entirely and use this level.

        Returns
        -------
        GravityAssessment with gravity, confidence, signals, and reasoning.
        """
        # ---------------------------------------------------------------
        # User override always wins
        # ---------------------------------------------------------------
        if user_override is not None:
            logger.info("Gravity override to %s by user request", user_override.value)
            return GravityAssessment(
                gravity=user_override,
                confidence=1.0,
                raw_score=0.0,
                gravity_floor=GravityLevel.LIGHT,
                method="user_override",
                signals=[],
                reasoning=f"User explicitly set gravity to {user_override.value}.",
            )

        text = task_prompt.lower()
        signals: List[GravitySignal] = []
        gravity_floor = GravityLevel.LIGHT

        # ---------------------------------------------------------------
        # Signal 1: Prompt Analysis (weight=1.0)
        # ---------------------------------------------------------------
        sig1 = self._signal_prompt_analysis(text)
        signals.append(sig1)

        # ---------------------------------------------------------------
        # Signal 2: Domain Detection (weight=1.5)
        # ---------------------------------------------------------------
        sig2, domain_floor = self._signal_domain_detection(text)
        signals.append(sig2)
        gravity_floor = _gravity_max(gravity_floor, domain_floor)

        # ---------------------------------------------------------------
        # Signal 3: File Sensitivity (weight=1.2)
        # ---------------------------------------------------------------
        sig3 = self._signal_file_sensitivity(text)
        signals.append(sig3)

        # ---------------------------------------------------------------
        # Signal 4: Graph Context (weight=0.8)
        # ---------------------------------------------------------------
        sig4 = self._signal_graph_context(text, project_id)
        signals.append(sig4)

        # ---------------------------------------------------------------
        # Signal 5: Reversibility (weight=1.3)
        # ---------------------------------------------------------------
        sig5 = self._signal_reversibility(text)
        signals.append(sig5)

        # ---------------------------------------------------------------
        # Scoring resolution
        # ---------------------------------------------------------------
        weighted_sum = 0.0
        weight_sum = 0.0
        for sig in signals:
            if sig.score != 0.0:
                weighted_sum += sig.score * sig.weight
                weight_sum += sig.weight

        if weight_sum == 0.0:
            weighted_score = 0.0  # neutral → standard (between light/intensive thresholds)
        else:
            weighted_score = weighted_sum / weight_sum

        # Confidence: higher when score is more decisive
        confidence = min(1.0, abs(weighted_score) * 1.5 + 0.3)

        # Classify based on weighted score
        if weighted_score <= self.LIGHT_SCORE_THRESHOLD:
            # Asymmetric gate: penalise confidence before checking threshold
            penalised_confidence = confidence * self.LIGHT_PENALTY_MULTIPLIER
            if penalised_confidence >= self.LIGHT_CONFIDENCE_THRESHOLD:
                gravity = GravityLevel.LIGHT
            else:
                # Not confident enough → default to STANDARD, never LIGHT
                gravity = GravityLevel.STANDARD
                logger.debug(
                    "Penalised confidence %.3f < %.3f threshold; "
                    "refusing to classify as LIGHT",
                    penalised_confidence,
                    self.LIGHT_CONFIDENCE_THRESHOLD,
                )
        elif weighted_score > self.INTENSIVE_SCORE_THRESHOLD:
            gravity = GravityLevel.INTENSIVE
        else:
            gravity = GravityLevel.STANDARD

        # Apply floor — domain floors are absolute
        if _GRAVITY_ORDER[gravity] < _GRAVITY_ORDER[gravity_floor]:
            logger.info(
                "Gravity floor %s overrides classification %s",
                gravity_floor.value,
                gravity.value,
            )
            gravity = gravity_floor

        # ---------------------------------------------------------------
        # Reasoning
        # ---------------------------------------------------------------
        reasoning = self._build_reasoning(
            signals, weighted_score, gravity, gravity_floor, confidence,
        )

        logger.info(
            "Gravity assessment: %s (confidence=%.2f, raw_score=%.3f, floor=%s)",
            gravity.value, confidence, weighted_score, gravity_floor.value,
        )

        return GravityAssessment(
            gravity=gravity,
            confidence=confidence,
            raw_score=weighted_score,
            gravity_floor=gravity_floor,
            method="multi_signal_classifier",
            signals=signals,
            reasoning=reasoning,
        )

    # -------------------------------------------------------------------
    # Individual signal methods
    # -------------------------------------------------------------------

    @staticmethod
    def _signal_prompt_analysis(text: str) -> GravitySignal:
        """Signal 1: linguistic markers in the task description."""
        score = 0.0
        matches: List[str] = []

        for kw in LIGHT_INDICATORS:
            if _word_boundary_match(text, kw):
                score -= 0.25
                matches.append(f"-light:{kw}")

        for kw in STANDARD_INDICATORS:
            if _word_boundary_match(text, kw):
                score += 0.1
                matches.append(f"+standard:{kw}")

        for kw in INTENSIVE_INDICATORS:
            if _word_boundary_match(text, kw):
                score += 0.4
                matches.append(f"+intensive:{kw}")

        return GravitySignal(
            name="prompt_analysis",
            score=score,
            weight=1.0,
            matches=matches,
        )

    @staticmethod
    def _signal_domain_detection(text: str) -> Tuple[GravitySignal, GravityLevel]:
        """Signal 2: high-consequence domain keyword detection."""
        score = 0.0
        matches: List[str] = []
        floor = GravityLevel.LIGHT

        for domain_name, domain in HIGH_CONSEQUENCE_DOMAINS.items():
            domain_matched = False
            for kw in domain["keywords"]:
                if _word_boundary_match(text, kw):
                    if not domain_matched:
                        # Only add bias once per domain
                        score += domain["bias"]
                        floor = _gravity_max(floor, domain["floor"])
                        domain_matched = True
                    matches.append(f"{domain_name}:{kw}")

        return (
            GravitySignal(
                name="domain_detection",
                score=score,
                weight=1.5,
                matches=matches,
                floor=floor if floor != GravityLevel.LIGHT else None,
            ),
            floor,
        )

    @staticmethod
    def _signal_file_sensitivity(text: str) -> GravitySignal:
        """Signal 3: sensitive file-path patterns in the description."""
        score = 0.0
        matches: List[str] = []

        for pat in INTENSIVE_FILE_PATTERNS:
            if pat in text:
                score += 0.3
                matches.append(f"+intensive:{pat}")

        for pat in STANDARD_FILE_PATTERNS:
            if pat in text:
                score += 0.15
                matches.append(f"+standard:{pat}")

        return GravitySignal(
            name="file_sensitivity",
            score=score,
            weight=1.2,
            matches=matches,
        )

    @staticmethod
    def _signal_graph_context(text: str, project_id: str) -> GravitySignal:
        """Signal 4: FalkorDB project-history context (graceful fallback)."""
        score = 0.0
        matches: List[str] = []

        try:
            from core.graph import get_graph, GraphUnavailableError  # noqa: F811

            graph = get_graph(phase_id="gravity-assess")

            # Check if project has security_sensitive flag
            try:
                result = graph.query(
                    "MATCH (s:Source {id: $pid}) "
                    "WHERE s.security_sensitive = true "
                    "RETURN s.id",
                    params={"pid": project_id},
                )
                if result.result_set:
                    score += 0.4
                    matches.append("project:security_sensitive")
            except Exception:
                pass

            # Query similar past episodes for failure rates
            try:
                keywords = extract_keywords(text)[:5]
                if keywords:
                    keyword_pattern = "|".join(keywords)
                    result = graph.query(
                        "MATCH (t:Task) "
                        "WHERE t.description =~ $pat "
                        "RETURN t.status, count(t) AS cnt",
                        params={"pat": f"(?i).*({keyword_pattern}).*"},
                    )
                    failed = 0
                    total = 0
                    for row in result.result_set:
                        status = row[0] if row[0] else ""
                        cnt = int(row[1]) if row[1] else 0
                        total += cnt
                        if status in ("failed", "error", "rollback"):
                            failed += cnt
                    if total > 0:
                        failure_rate = failed / total
                        if failure_rate > 0.3:
                            score += 0.3
                            matches.append(
                                f"history:failure_rate={failure_rate:.0%} "
                                f"({failed}/{total})"
                            )
            except Exception:
                pass

        except Exception:
            # Graph unavailable — neutral signal
            pass

        return GravitySignal(
            name="graph_context",
            score=score,
            weight=0.8,
            matches=matches,
        )

    @staticmethod
    def _signal_reversibility(text: str) -> GravitySignal:
        """Signal 5: irreversible-operation patterns."""
        score = 0.0
        matches: List[str] = []

        for kw in IRREVERSIBLE_KEYWORDS:
            if _word_boundary_match(text, kw):
                score += 0.35
                matches.append(f"+irreversible:{kw}")

        return GravitySignal(
            name="reversibility",
            score=score,
            weight=1.3,
            matches=matches,
        )

    # -------------------------------------------------------------------
    # Reasoning builder
    # -------------------------------------------------------------------

    @staticmethod
    def _build_reasoning(
        signals: List[GravitySignal],
        weighted_score: float,
        gravity: GravityLevel,
        gravity_floor: GravityLevel,
        confidence: float,
    ) -> str:
        """Build a human-readable reasoning string."""
        parts: List[str] = []

        fired = [s for s in signals if s.score != 0.0]
        if not fired:
            parts.append(
                "No signals fired; defaulting to STANDARD (neutral score 0.5)."
            )
        else:
            for sig in fired:
                direction = "+" if sig.score > 0 else ""
                match_summary = ", ".join(sig.matches[:5])
                if len(sig.matches) > 5:
                    match_summary += f" (+{len(sig.matches) - 5} more)"
                parts.append(
                    f"{sig.name}: score={direction}{sig.score:.2f} "
                    f"w={sig.weight} [{match_summary}]"
                )

        parts.append(f"Weighted score: {weighted_score:.3f}")

        if gravity_floor != GravityLevel.LIGHT:
            parts.append(f"Domain floor: {gravity_floor.value}")

        parts.append(
            f"Classification: {gravity.value} (confidence {confidence:.2f})"
        )

        return "; ".join(parts)
