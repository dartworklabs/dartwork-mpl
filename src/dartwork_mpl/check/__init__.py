"""Find what makes a drawn chart ugly or unreadable, without changing it.

``dm.check(fig)`` draws the figure once, measures it and returns
:class:`Findings`: each :class:`Finding` names its rule, severity, message,
a fix and the artists and panels involved; ``print(found)`` is a compact
report an agent can read. The rules, in report order, are ``EDGES`` in
``edges.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..edgecase import settle
from .edges import EDGES
from .findings import Finding, Findings, Info, Severity, Warn
from .measure import measure

if TYPE_CHECKING:
    from matplotlib.figure import Figure

__all__ = ["Finding", "Findings", "Info", "Severity", "Warn", "check", "rules"]


def check(fig: Figure) -> Findings:
    """Every defect the rules find in ``fig``; the figure is not changed.

    A rule that could not measure the figure is listed in
    ``Findings.skipped`` (and the report says NOT RUN): such a figure is
    not proven clean. ``bool(found)`` is False only for a clean figure.
    """
    facts = measure(fig)
    return settle(facts, Findings(skipped=facts.skipped), EDGES).plan


def rules() -> tuple[str, ...]:
    """The rule names, in report order."""
    return tuple(edge.name for edge in EDGES)
