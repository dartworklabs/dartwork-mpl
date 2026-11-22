"""The font table for the ordinary install, and which weight misses are noise.

Ordinarily nothing moves: matplotlib appends each bundled file and keeps the
weight the file declares. The fixes some files and machines need are the
named cases in ``edges.py``.
"""

from __future__ import annotations

from .model import Expected, Lead, MathText, Plan, Table, WeightMiss


def table_plan(table: Table) -> Plan:
    """Every face where matplotlib put it, with the weight it declares."""
    return Plan(
        order=tuple(range(len(table.faces))),
        weights=tuple(face.weight for face in table.faces),
    )


def is_expected(miss: WeightMiss, expected: Expected) -> bool:
    """Whether a "failed to find font weight" notice is by design.

    A one-weight fallback family misses every other weight on purpose, and
    mathtext asks matplotlib's own math fonts (regular and bold only) for the
    preset's light weight. An explicit other weight on a math font is the
    caller's choice and keeps its notice.
    """
    if miss.family in expected.single_weight:
        return True
    return (
        miss.family in expected.math and miss.weight == expected.preset_weight
    )


def lead_plan(text: MathText) -> Lead:
    """A mathtext string keeps the family its list names first."""
    del text
    return Lead(0)
