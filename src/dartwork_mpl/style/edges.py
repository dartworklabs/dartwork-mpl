"""The step's named special cases, applied after ``decide.step``."""

from __future__ import annotations

from ..edgecase import EdgeCase
from .model import SLIDE_FAMILY, SLIDE_SCALE, Active, Points


def is_slide(active: Active, plan: Points) -> bool:
    """The last preset applied is a presentation one and still in force."""
    return (
        active.in_force
        and bool(active.presets)
        and active.presets[-1].family == SLIDE_FAMILY
    )


def slide_step(active: Active, plan: Points) -> Points:
    """A step as big as every other point size on the slide."""
    return Points(plan.pt * SLIDE_SCALE)


EDGES: tuple[EdgeCase[Active, Points], ...] = (
    EdgeCase(
        name="slide-step",
        why=(
            "the presentation presets are scientific x 2.6, so a 1 pt step "
            "there is a 0.4 pt step on paper: fs(-1) barely shrank slide text"
        ),
        example="test_edges.py::test_slide_step_is_scientific_times_2_6",
        applies=is_slide,
        adjust=slide_step,
    ),
)
