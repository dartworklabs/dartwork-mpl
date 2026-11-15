"""The colour decisions' named special cases, applied after ``decide``.

Each entry fixes one decision's plan; the surface in ``__init__`` settles a
plan with the entry that belongs to it (``FULL_LADDER`` after
``decide.discrete`` and so on). The ``why`` says what came out wrong without
it.
"""

from __future__ import annotations

from ..edgecase import EdgeCase
from .decide import contrast, suggest
from .model import (
    ContrastFacts,
    DivergingSource,
    Form,
    Gradient,
    Kind,
    Lift,
    Locale,
    Lookup,
    Name,
    PaletteRequest,
    Semantic,
    SemanticFacts,
    Suggestions,
    namespace,
    shifted,
)
from .space import Hex, Oklch, Rgb

# Below this OKLCH chroma a colour is grey and its hue is noise.
ACHROMATIC = 1e-4
# One 8-bit step of HLS lightness.
STEP = 1.0 / 255.0
# Open Color shades ``make_palette`` darkens the highlighted series by, and
# lightens the rest by.
EMPHASIS = 2


def is_full_ladder(form: Form, plan: tuple[Hex, ...]) -> bool:
    """A sequential family asked for nine or ten stops."""
    return form.family.kind is Kind.SEQUENTIAL and form.n.n >= 9


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


def one_end_grey(ends: Gradient, plan: Gradient) -> bool:
    """Exactly one end of the gradient is grey."""
    return (plan.start.C < ACHROMATIC) != (plan.end.C < ACHROMATIC)


def borrow_hue(ends: Gradient, plan: Gradient) -> Gradient:
    """The grey end takes the coloured end's hue."""
    start, end = plan.start, plan.end
    if start.C < ACHROMATIC:
        return Gradient(Oklch(start.L, start.C, end.h), end)
    return Gradient(start, Oklch(end.L, end.C, start.h))


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
    return facts.locale is Locale.KR


def red_gains_blue_losses(facts: SemanticFacts, plan: Semantic) -> Semantic:
    """Gains red 5, losses blue 6; reference and highlight kept."""
    return Semantic(
        pos=facts.catalog.ladder("red")[5],
        neg=facts.catalog.ladder("blue")[6],
        ref=plan.ref,
        hl=plan.hl,
    )


def has_known_namespace(lookup: Lookup, plan: Suggestions) -> bool:
    """The rejected name's ``prefix.`` is a registered namespace."""
    prefix = namespace(lookup.name)
    return prefix is not None and any(
        name.startswith(prefix) for name in lookup.registry
    )


def within_namespace(lookup: Lookup, plan: Suggestions) -> Suggestions:
    """Suggestions drawn from that namespace only."""
    prefix = namespace(lookup.name) or ""
    same = tuple(name for name in lookup.registry if name.startswith(prefix))
    return suggest(Lookup(lookup.name, same))


def has_highlight(request: PaletteRequest, plan: tuple[Name, ...]) -> bool:
    """The request names a series to emphasise."""
    return request.highlight is not None


def emphasise(
    request: PaletteRequest, plan: tuple[Name, ...]
) -> tuple[Name, ...]:
    """The highlighted series two shades darker, the rest two lighter."""
    return tuple(
        shifted(name, EMPHASIS if i == request.highlight else -EMPHASIS)
        for i, name in enumerate(plan)
    )


EDGES = (
    EdgeCase(
        name="sequential-full-ladder",
        why="nine or ten stops cannot spread over stops 1..8 without "
        "repeating one; they take the ladder from its lightest stop",
        applies=is_full_ladder,
        adjust=whole_ladder,
    ),
    EdgeCase(
        name="curated-diverging-row",
        why="blue_red, blue_orange, teal_amber and green_purple ship a "
        "hand-tuned row whose sides balance better than the ladder stops",
        applies=has_curated_row,
        adjust=curated_row,
    ),
    EdgeCase(
        name="grey-gradient-end",
        why="a grey end's hue is noise; white to teal swung through violet "
        "before reaching teal",
        applies=one_end_grey,
        adjust=borrow_hue,
    ),
    EdgeCase(
        name="hex-rounding-shortfall",
        why="the bisected lightness meets the ratio exactly, and rounding to "
        "#rrggbb can land a hair under it; step one 8-bit level further",
        applies=short_after_rounding,
        adjust=step_past_rounding,
    ),
    EdgeCase(
        name="kr-semantic-tokens",
        why="Korean markets colour gains red and losses blue; a green gain "
        "reads as a loss there",
        applies=is_korean,
        adjust=red_gains_blue_losses,
    ),
    EdgeCase(
        name="same-namespace-suggestions",
        why="someone who typed 'dc.' wants a dc. name; 'oc.blue5' is a "
        "different palette, not a correction of 'dc.blue55'",
        applies=has_known_namespace,
        adjust=within_namespace,
    ),
    EdgeCase(
        name="highlight-series",
        why="one series in focus reads at once when it is darker and the "
        "rest recede, instead of every series shouting equally",
        applies=has_highlight,
        adjust=emphasise,
    ),
)
(
    FULL_LADDER,
    CURATED_ROW,
    GREY_END,
    HEX_ROUNDING,
    KR_TOKENS,
    SAME_NAMESPACE,
    HIGHLIGHT,
) = EDGES
