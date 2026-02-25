"""Discovery subsystem — PRD coverage tracking during Phase 1."""

from core.discovery.canvas import (
    CanvasState,
    PRD_SECTIONS,
    SECTION_PROBES,
    classify_exchange,
    render_canvas,
    render_canvas_compact,
    suggest_next_topic,
    generate_prd_preview,
)

__all__ = [
    "CanvasState",
    "PRD_SECTIONS",
    "SECTION_PROBES",
    "classify_exchange",
    "render_canvas",
    "render_canvas_compact",
    "suggest_next_topic",
    "generate_prd_preview",
]
