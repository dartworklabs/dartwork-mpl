"""The fit: measure, decide, write the edges; again until they hold.

Each step draws the figure, lets the slices that place things at the Axes
size settle them (bar labels, legends, line-end names, panel letters, each
given as a function in :class:`~.given.Neighbours`),
measures and solves. After the margins hold, crowded text is fitted, each
round followed by a fresh fit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..edgecase import settle
from ..geometry import get_renderer
from . import apply, decide, measure, report, text
from .edges import EDGES, TEXT_EDGES
from .given import Neighbours
from .model import FIT_ROUNDS, MAX_STEPS, Sides, Step

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.gridspec import GridSpec

# Rounds of legend and line-end settling per step: matplotlib re-places an
# auto title on every draw, so a lift can need a second round.
SETTLE_ROUNDS = 3


def _redraw(fig: Figure) -> RendererBase:
    fig.canvas.draw()  # pyright: ignore[reportUnknownMemberType]
    return get_renderer(fig)


def one_step(
    fig: Figure, margins: Sides, last: Sides | None, given: Neighbours
) -> Step | None:
    """Draw, settle what sits at the Axes size, measure and solve once."""
    renderer = _redraw(fig)
    if given.settle_bars(fig, renderer):
        renderer = _redraw(fig)
    for _round in range(SETTLE_ROUNDS):
        moved = given.settle_legends(fig, renderer, fig.axes)
        if not given.space_line_ends(fig, renderer) and not moved:
            break
        renderer = _redraw(fig)
    if given.settle_panels(fig, renderer):
        renderer = _redraw(fig)
    if given.stack_figure_legends(fig, renderer):
        renderer = _redraw(fig)
    facts = measure.content_facts(fig, renderer, margins, last, given)
    counted = settle(facts, facts, EDGES).plan
    return decide.solve(counted, decide.reserves(counted))


def fit(
    fig: Figure,
    gs: GridSpec,
    margins: Sides,
    given: Neighbours,
    last: Sides | None,
) -> Step | None:
    """Fit from ``last`` until the edges move under half a pixel (``None``:
    nothing to measure)."""
    step: Step | None = None
    for _ in range(MAX_STEPS):
        step = one_step(fig, margins, last, given)
        if step is None:
            break
        apply.write_edges(fig, gs, step.edges)
        last = step.edges
        if step.converged:
            break
    return step


def run(fig: Figure, gs: GridSpec, margins: Sides, given: Neighbours) -> None:
    """Lay out ``fig`` on ``gs`` and say what it changed besides the margins."""
    before = report.look(fig, gs) if report.on() else None
    _run(fig, gs, margins, given)
    if before is not None:
        report.changes(before, report.look(fig, gs))
    given.report_bars(fig)
    given.report_legends(fig)


def _run(fig: Figure, gs: GridSpec, margins: Sides, given: Neighbours) -> None:
    """The spines its scales tick on, margins, then rounds of text fitting."""
    apply.unturn(fig)
    apply.show_scale_spines(fig)
    given.prepare_ticks(fig)
    step = fit(fig, gs, margins, given, None)
    for _round in range(FIT_ROUNDS):
        if step is None or not step.converged:
            return
        facts, objects = text.text_facts(fig, gs, get_renderer(fig))
        plan = settle(facts, decide.text_plan(facts), TEXT_EDGES).plan
        if plan.empty:
            return
        apply.text(gs, plan, objects)
        step = fit(fig, gs, margins, given, step.edges)
