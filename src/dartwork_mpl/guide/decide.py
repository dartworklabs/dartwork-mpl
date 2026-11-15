"""Pure guide decisions: which catalog rules a source breaks, which references a query wants.

A pattern rule matches the source text; a check rule tests each literal
colour or colormap name the source uses against matplotlib's registries.
Matches in prose (strings, comments), registrations made by the source
itself and the twin-axes condition are the named special cases in
``edges.py``. A search scores each reference by the query words it shares,
tags counting twice, templates first on a tie.
"""

from __future__ import annotations

from typing import assert_never

from .model import (
    Check,
    Finding,
    Findings,
    Kind,
    Known,
    LintFacts,
    Literal,
    Query,
    Reference,
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
        case Check.COLORMAP:
            return literal.value not in known.colormaps
        case Check.COLOR:
            return not is_color(literal, known)
        case _:
            assert_never(literal.check)


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
        else:
            spots += [
                (rule, Spot(lit.offset, lit.value))
                for lit in facts.code.literals
                if lit.check is rule.check and broken(lit, facts.known)
            ]
    found = (finding(rule, facts, spot) for rule, spot in spots)
    return tuple(sorted(found, key=lambda f: (f.offset, f.rule_id)))


def rank(
    query: Query, references: tuple[Reference, ...]
) -> tuple[Reference, ...]:
    """The references that share a word with the query, best first."""

    scored = [
        (len(query.words & ref.words) + len(query.words & ref.tags), ref)
        for ref in references
    ]
    hits = sorted(
        (pair for pair in scored if pair[0] > 0),
        key=lambda pair: (
            -pair[0],
            pair[1].kind is not Kind.TEMPLATE,
            pair[1].id,
        ),
    )
    return tuple(ref for _, ref in hits[: query.limit])
