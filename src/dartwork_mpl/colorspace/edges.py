"""The contrast lift's named special case, applied after ``decide.lift``."""

from __future__ import annotations

from ..edgecase import EdgeCase
from .decide import contrast
from .model import ContrastFacts, Lift, Rgb

# One 8-bit step of HLS lightness.
STEP = 1.0 / 255.0


def short_after_rounding(facts: ContrastFacts, plan: Lift | None) -> bool:
    """The lifted colour, once rounded to hex, misses the ratio."""
    if plan is None:
        return False
    shown = Rgb.from_hex(plan.rgb().hex())
    return contrast(shown, facts.background).value < facts.target.value


def step_past_rounding(facts: ContrastFacts, plan: Lift | None) -> Lift | None:
    """Step lightness one 8-bit level at a time until the hex passes."""
    lift = plan
    while lift is not None and short_after_rounding(facts, lift):
        at_pole = (
            lift.lightness >= 1.0 if lift.lighten else lift.lightness <= 0.0
        )
        if at_pole:
            break
        if lift.lighten:
            lightness = min(1.0, lift.lightness + STEP)
        else:
            lightness = max(0.0, lift.lightness - STEP)
        lift = Lift(lift.hue, lightness, lift.saturation, lift.lighten)
    return lift


LIFT_EDGES: tuple[EdgeCase[ContrastFacts, Lift | None], ...] = (
    EdgeCase(
        name="hex-rounding-shortfall",
        why="dc.amber5 lifted for contrast on white rounded to #ab6700, a "
        "hair under the 4.5:1 it was asked for",
        example="test_edges.py::test_hex_rounding_shortfall",
        applies=short_after_rounding,
        adjust=step_past_rounding,
    ),
)
