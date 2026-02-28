"""Consensus Prompts — templates for agent voting."""

VOTE_PROMPT = (
    "You are {agent_name}, a {agent_role} expert.\n\n"
    "A consensus vote is requested on the following question:\n"
    "{question}\n\n"
    "Context:\n{context}\n\n"
    "Options:\n{options_text}\n\n"
    "Respond in this exact format:\n"
    "VOTE: <option_id>\n"
    "CONFIDENCE: <0.0-1.0>\n"
    "REASONING: <brief explanation>\n"
    "DISSENT: <optional dissenting note, or NONE>\n"
)


def format_vote_prompt(
    agent_name: str,
    agent_role: str,
    question: str,
    context: str,
    options: list,
    shared_context: str = "",
) -> str:
    """Format a vote prompt for an agent.

    Args:
        agent_name: Agent display name.
        agent_role: Agent role (e.g. "architect").
        question: The question being voted on.
        context: Proposal context.
        options: List of ProposalOption objects.
        shared_context: Additional shared context.

    Returns:
        Formatted prompt string.
    """
    options_text = "\n".join(
        f"  [{opt.id}] {opt.title}: {opt.description}"
        for opt in options
    )

    full_context = context
    if shared_context:
        full_context = f"{context}\n\nAdditional context:\n{shared_context}"

    return VOTE_PROMPT.format(
        agent_name=agent_name,
        agent_role=agent_role,
        question=question,
        context=full_context,
        options_text=options_text,
    )


def parse_vote_response(response: str) -> dict:
    """Parse a structured vote response.

    Expected format:
        VOTE: option_id
        CONFIDENCE: 0.8
        REASONING: ...
        DISSENT: NONE

    Returns:
        Dict with keys: vote, confidence, reasoning, dissent.
        Missing fields default to sensible values.
    """
    result = {
        "vote": "",
        "confidence": 0.5,
        "reasoning": "",
        "dissent": None,
    }

    for line in response.strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("VOTE:"):
            result["vote"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("CONFIDENCE:"):
            try:
                result["confidence"] = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.upper().startswith("REASONING:"):
            result["reasoning"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("DISSENT:"):
            val = line.split(":", 1)[1].strip()
            result["dissent"] = None if val.upper() == "NONE" else val

    return result
