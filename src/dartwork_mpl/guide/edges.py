"""The lint's named special cases, applied after ``decide.findings``.

Each one removes findings the plain rule makes where the source shows they
are not a defect; the ``why`` says which source that was.
"""

from __future__ import annotations

from typing import assert_never

from ..edgecase import EdgeCase
from .model import (
    Check,
    Code,
    ColormapName,
    ColorName,
    Findings,
    LintFacts,
    Registered,
)

HAND_MERGE = "twin-legend-hand-merge"
GLOBAL_RANDOM = "unseeded-global-random"


def quotes_a_pattern(facts: LintFacts, plan: Findings) -> bool:
    """A pattern finding starts inside a string or a comment."""
    return any(facts.code.is_quoted(f.offset) for f in plan)


def drop_quoted(facts: LintFacts, plan: Findings) -> Findings:
    """Keep the findings that start in code."""
    return tuple(f for f in plan if not facts.code.is_quoted(f.offset))


def merges_without_twin(facts: LintFacts, plan: Findings) -> bool:
    """A hand-merged legend in a source that makes no twin axes."""
    return not facts.code.twins and any(f.rule_id == HAND_MERGE for f in plan)


def drop_hand_merge(facts: LintFacts, plan: Findings) -> Findings:
    """Keep every finding but the hand-merge hint."""
    return tuple(f for f in plan if f.rule_id != HAND_MERGE)


def draws_after_a_seed(facts: LintFacts, plan: Findings) -> bool:
    """A draw from the global generator in a source that seeds it."""
    return facts.code.seeds and any(f.rule_id == GLOBAL_RANDOM for f in plan)


def drop_global_random(facts: LintFacts, plan: Findings) -> Findings:
    """Keep every finding but the global-generator one."""
    return tuple(f for f in plan if f.rule_id != GLOBAL_RANDOM)


def _registered_by(code: Code, check: Check) -> Registered:
    match check:
        case ColormapName():
            return code.colormaps
        case ColorName():
            return code.colors
        case _:
            assert_never(check)


def _self_registered(
    facts: LintFacts, plan: Findings, check: Check
) -> Findings:
    """The findings of ``check`` for names the source registers itself."""
    registered = _registered_by(facts.code, check)
    return tuple(
        f
        for f in plan
        if f.rule_id == check.rule
        and (registered.dynamic or f.name in registered.names)
    )


def registers_a_colormap(facts: LintFacts, plan: Findings) -> bool:
    """A colormap finding names a map the source registers (or names one dynamically)."""
    return bool(_self_registered(facts, plan, ColormapName()))


def drop_registered_colormaps(facts: LintFacts, plan: Findings) -> Findings:
    """Keep the colormap findings the source's own registrations do not answer."""
    mine = set(_self_registered(facts, plan, ColormapName()))
    return tuple(f for f in plan if f not in mine)


def registers_a_color(facts: LintFacts, plan: Findings) -> bool:
    """A colour finding names a colour the source adds to matplotlib's mapping."""
    return bool(_self_registered(facts, plan, ColorName()))


def drop_registered_colors(facts: LintFacts, plan: Findings) -> Findings:
    """Keep the colour findings the source's own registrations do not answer."""
    mine = set(_self_registered(facts, plan, ColorName()))
    return tuple(f for f in plan if f not in mine)


EDGES: tuple[EdgeCase[LintFacts, Findings], ...] = (
    EdgeCase(
        name="quoted-text",
        why="a docstring warning 'never figsize=(w, h)' was flagged as if it "
        "were code",
        example="test_edges.py::test_quoted_text",
        applies=quotes_a_pattern,
        adjust=drop_quoted,
    ),
    EdgeCase(
        name="hand-merge-without-twin",
        why="one legend gathered by hand from two separate panels was "
        "flagged as a twin merge, which only a twin pair has",
        example="test_edges.py::test_hand_merge_without_twin",
        applies=merges_without_twin,
        adjust=drop_hand_merge,
    ),
    EdgeCase(
        name="colormap-registered-in-source",
        why="a script that registers its own colormap got an "
        "invalid-colormap-name finding for it",
        example="test_edges.py::test_colormap_registered_in_source",
        applies=registers_a_colormap,
        adjust=drop_registered_colormaps,
    ),
    EdgeCase(
        name="color-registered-in-source",
        why="a script that adds its own colour name got an "
        "invalid-color-name finding for it",
        example="test_edges.py::test_color_registered_in_source",
        applies=registers_a_color,
        adjust=drop_registered_colors,
    ),
    EdgeCase(
        name="global-random-seeded",
        why="a script that calls np.random.seed(0) first was told its "
        "np.random.normal draws were unseeded",
        example="test_edges.py::test_global_random_seeded",
        applies=draws_after_a_seed,
        adjust=drop_global_random,
    ),
)
