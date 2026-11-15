"""The colour decisions' named special cases, applied after ``decide``.

Each entry fixes one decision's plan; the surface in ``__init__`` settles a
plan with the entry that belongs to it (``FULL_LADDER`` after
``decide.discrete`` and so on). The ``why`` says what came out wrong without
it.
"""

from __future__ import annotations

from ..edgecase import EdgeCase
from .decide import contrast
from .model import (
    ContrastFacts,
    DivergingSource,
    Form,
    Lift,
    Semantic,
    SemanticFacts,
)
from .space import Hex, Rgb

# One 8-bit step of HLS lightness.
STEP = 1.0 / 255.0


def is_full_ladder(form: Form, plan: tuple[Hex, ...]) -> bool:
    """A sequential family asked for nine or ten stops."""
    return form.family.kind.ladder and form.n.n >= 9


def whole_ladder(form: Form, plan: tuple[Hex, ...]) -> tuple[Hex, ...]:
    """The ladder's first ``n`` stops, lightest first."""
    return form.family.stops[: form.n.n]


def has_curated_row(source: DivergingSource, plan: tuple[Hex, ...]) -> bool:
    """The family ships a hand-tuned canonical row."""
    return source.curated is not None


def curated_row(
    source: DivergingSource, plan: tuple[Hex, ...]
) -> tuple[Hex, ...]:
    """The hand-tuned row in place of the ladder-derived one."""
    return source.curated or plan


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


def is_korean(facts: SemanticFacts, plan: Semantic) -> bool:
    """The role colours are for a Korean preset."""
    return facts.locale.red_gains


def red_gains_blue_losses(facts: SemanticFacts, plan: Semantic) -> Semantic:
    """Gains red 5, losses blue 6; reference and highlight kept."""
    return Semantic(
        pos=facts.catalog.ladder("red")[5],
        neg=facts.catalog.ladder("blue")[6],
        ref=plan.ref,
        hl=plan.hl,
    )


EDGES = (
    EdgeCase(
        name="sequential-full-ladder",
        why="nine or ten stops spread over stops 1..8 repeat one colour; "
        "they take the ladder from its lightest stop",
        example="test_edges.py::test_sequential_full_ladder",
        applies=is_full_ladder,
        adjust=whole_ladder,
    ),
    EdgeCase(
        name="curated-diverging-row",
        why="the ladder-derived blue_red row is lopsided: its two sides do "
        "not balance as the hand-tuned row shipped with the family does",
        example="test_edges.py::test_curated_diverging_row",
        applies=has_curated_row,
        adjust=curated_row,
    ),
    EdgeCase(
        name="hex-rounding-shortfall",
        why="dc.amber5 lifted for contrast on white rounded to #ab6700, a "
        "hair under the 4.5:1 it was asked for",
        example="test_edges.py::test_hex_rounding_shortfall",
        applies=short_after_rounding,
        adjust=step_past_rounding,
    ),
    EdgeCase(
        name="kr-semantic-tokens",
        why="a Korean chart coloured its gains green, which reads as a loss "
        "in Korean markets",
        example="test_edges.py::test_kr_semantic_tokens",
        applies=is_korean,
        adjust=red_gains_blue_losses,
    ),
)
(FULL_LADDER, CURATED_ROW, HEX_ROUNDING, KR_TOKENS) = EDGES
