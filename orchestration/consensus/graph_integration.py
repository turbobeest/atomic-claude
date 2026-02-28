"""Consensus Graph Integration — persist consensus results to knowledge graph."""

import json
import logging
import uuid
from typing import Optional

from orchestration.consensus.models import ConsensusResult

logger = logging.getLogger(__name__)


def record_consensus_decision(
    result: ConsensusResult,
    task_id: str,
    graph=None,
) -> Optional[str]:
    """Record a consensus result as a Decision node in the graph.

    Creates a Decision node with confidence and vote breakdown, linked
    to the current task via INFORMED_BY.

    Args:
        result: ConsensusResult from the consensus engine.
        task_id: Current task ID.
        graph: GraphManager instance (no-op if None).

    Returns:
        Decision node ID, or None if graph unavailable.
    """
    if graph is None:
        return None

    try:
        decision_id = f"consensus-{uuid.uuid4().hex[:12]}"

        # Build alternatives from losing options
        alternatives = []
        if result.vote_breakdown:
            for option_id, count in result.vote_breakdown.items():
                if option_id != result.winning_option:
                    alternatives.append({
                        "title": option_id,
                        "reason_rejected": f"Received {count} votes",
                    })

        # Build rationale from vote summary
        rationale = (
            f"Consensus {result.status.value}: "
            f"winning={result.winning_option or 'none'}, "
            f"votes={result.vote_breakdown}"
        )

        graph.writer.create_node(
            "Decision",
            {
                "id": decision_id,
                "title": f"Consensus: {result.proposal_id}",
                "rationale": rationale,
                "confidence": result.confidence,
                "alternatives_json": json.dumps(alternatives) if alternatives else "",
                "status": "accepted" if result.winning_option else "no_consensus",
            },
        )

        # Link to task
        graph.writer.create_relationship(
            "Task", task_id,
            "INFORMED_BY",
            "Decision", decision_id,
        )

        logger.info(
            "Consensus decision %s recorded for task %s", decision_id, task_id,
        )
        return decision_id

    except Exception as e:
        logger.debug("Consensus graph recording failed: %s", e)
        return None
