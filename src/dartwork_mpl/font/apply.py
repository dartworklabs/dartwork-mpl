"""Register the bundled fonts with matplotlib, once per process."""

from __future__ import annotations

import logging
import threading
from dataclasses import replace

from matplotlib import font_manager

from ..edgecase import settle
from . import measure
from .decide import is_expected, table_plan
from .edges import EDGES
from .model import Plan, Weight, WeightMiss

WEIGHT_MISS = "findfont: Failed to find font weight %s for %s, now using %s."


class ExpectedWeightMiss(logging.Filter):
    """Drop matplotlib's weight-miss notices that the presets intend."""

    def __init__(self) -> None:
        """Quiet nothing until ``register`` names the one-weight families."""
        super().__init__()
        self.single_weight: frozenset[str] = frozenset()

    def filter(self, record: logging.LogRecord) -> bool:
        """Keep every record but an expected weight miss."""
        args = record.args
        if record.msg != WEIGHT_MISS or not (
            isinstance(args, tuple) and len(args) == 3
        ):
            return True
        miss = WeightMiss(
            family=str(args[1]),
            weight=Weight(
                args[0] if isinstance(args[0], int) else str(args[0])
            ),
        )
        return not is_expected(miss, measure.expected(self.single_weight))


WEIGHT_FILTER = ExpectedWeightMiss()


def install(plan: Plan) -> None:
    """Put the planned table in place.

    Called right after ``addfont``, which clears matplotlib's lookup cache;
    nothing looks a font up in between, so no lookup holds the old table.
    """
    manager = font_manager.fontManager
    old = list(manager.ttflist)
    new: list[font_manager.FontEntry] = []
    for i in plan.order:
        weight = plan.weights[i].value
        entry = old[i]
        new.append(
            entry if entry.weight == weight else replace(entry, weight=weight)
        )
    if any(a is not b for a, b in zip(old, new, strict=True)):
        # In place: matplotlib's manager holds this list object.
        manager.ttflist[:] = new


def register() -> None:
    """Add every bundled file, then fix the table (see ``edges.py``)."""
    for path in measure.bundled_files():
        font_manager.fontManager.addfont(path)  # pyright: ignore[reportUnknownMemberType]
    facts = measure.table()
    settled = settle(facts, table_plan(facts), EDGES)
    install(settled.plan)
    WEIGHT_FILTER.single_weight = facts.single_weight_families()
    logger = logging.getLogger("matplotlib.font_manager")
    if WEIGHT_FILTER not in logger.filters:
        logger.addFilter(WEIGHT_FILTER)


_lock = threading.Lock()
_loaded = False


def ensure_loaded() -> None:
    """Register the bundled fonts if this process has not yet; thread-safe."""
    global _loaded
    if _loaded:
        return
    with _lock:
        if not _loaded:
            register()
            _loaded = True
