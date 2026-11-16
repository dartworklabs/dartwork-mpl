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
from .model import Plan, Table, Weight, WeightMiss

LOG = logging.getLogger("dartwork_mpl.font")

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
    files = measure.bundled_files()
    for path in files:
        font_manager.fontManager.addfont(path)  # pyright: ignore[reportUnknownMemberType]
    LOG.debug(
        "registered %d bundled font files with matplotlib, so the presets' "
        "font families resolve without installing them",
        len(files),
    )
    facts = measure.table()
    settled = settle(facts, table_plan(facts), EDGES)
    install(settled.plan)
    _say_shadowed(facts)
    WEIGHT_FILTER.single_weight = facts.single_weight_families()
    logger = logging.getLogger("matplotlib.font_manager")
    if WEIGHT_FILTER not in logger.filters:
        logger.addFilter(WEIGHT_FILTER)
        LOG.debug(
            'quieted matplotlib\'s "Failed to find font weight" notice for '
            "the one-weight families the presets name at a weight they "
            "lack; every other notice still shows"
        )


def _say_shadowed(table: Table) -> None:
    """Name the families this system also has, now found bundled first.

    The font edge cases are settled without a logger: they fire on every
    import (the Paperlogy weights are the package's own files, any system
    font sits before the bundled ones), and only a family installed twice
    changes what a name resolves to.
    """
    ours = {face.family for face in table.faces if face.bundled}
    theirs = {face.family for face in table.faces if not face.bundled}
    shadowed = sorted(ours & theirs)
    if shadowed:
        LOG.debug(
            "put the bundled %s ahead of the copies installed on this "
            "system: matplotlib took whichever it found first; name a "
            "family the package does not bundle to use your own",
            ", ".join(shadowed),
        )


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
