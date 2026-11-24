"""Pure guide decisions: which catalog rules a source breaks.

A pattern rule matches the source text; a check rule tests each literal
colour or colormap name the source uses against matplotlib's registries.
Matches in prose (strings, comments), registrations made by the source
itself and the twin-axes condition are the named special cases in
``edges.py``.
"""

from __future__ import annotations

from typing import assert_never

from .model import (
    ColormapName,
    ColorName,
    Finding,
    Findings,
    Known,
    LintFacts,
    Literal,
    MatplotlibColormap,
    Rule,
    Rules,
    Spot,
)


def is_color(literal: Literal, known: Known) -> bool:
    """Whether matplotlib reads the literal as a colour."""
    return known.is_color(literal.value)


def broken(literal: Literal, known: Known) -> bool:
    """Whether a literal names nothing matplotlib has registered."""
    match literal.check:
        case ColormapName():
            return literal.value not in known.colormaps
        case ColorName():
            return not is_color(literal, known)
        case MatplotlibColormap():
            return False
        case _:
            assert_never(literal.check)


def foreign(literal: Literal, known: Known) -> bool:
    """Whether a colormap literal is one matplotlib ships, not a ``dc.`` map."""
    return (
        literal.check == ColormapName()
        and literal.value in known.colormaps
        and not literal.value.startswith("dc.")
    )


def breaks(rule: Rule, literal: Literal, known: Known) -> bool:
    """Whether a literal breaks a check rule."""
    if rule.check == MatplotlibColormap():
        return foreign(literal, known)
    return literal.check == rule.check and broken(literal, known)


def finding(rule: Rule, facts: LintFacts, spot: Spot) -> Finding:
    """The finding ``rule`` makes at a spot of the source."""
    message = (
        rule.message if spot.name is None else f"{spot.name!r}: {rule.message}"
    )
    return Finding(
        rule_id=rule.id,
        severity=rule.severity,
        line=facts.code.line_of(spot.offset),
        message=message,
        fix=rule.fix,
        offset=spot.offset,
        name=spot.name,
    )


def findings(facts: LintFacts, rules: Rules) -> Findings:
    """Every match of every rule, in source order."""
    spots: list[tuple[Rule, Spot]] = []
    for rule in rules.items:
        if rule.pattern is not None:
            text = facts.code.text
            spots += [
                (rule, Spot(m.start())) for m in rule.pattern.finditer(text)
            ]
    # A note on a name gives way to a pattern that already stands there
    # (``jet-cmap`` says more about ``cmap="jet"`` than "use a dc. map").
    taken = {spot.offset for _, spot in spots}
    for rule in rules.items:
        if rule.check is not None:
            spots += [
                (rule, Spot(lit.offset, lit.value))
                for lit in facts.code.literals
                if breaks(rule, lit, facts.known)
                and not (
                    rule.check == MatplotlibColormap() and lit.offset in taken
                )
            ]
    found = (finding(rule, facts, spot) for rule, spot in spots)
    return tuple(sorted(found, key=lambda f: (f.offset, f.rule_id)))
