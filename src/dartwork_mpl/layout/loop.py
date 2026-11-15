"""The fit: measure, decide, write the edges; again until they hold.

Each step draws the figure, lets the slices that place things at the Axes
size settle them (bar labels, legends, line-end names, panel letters),
measures and solves. After the margins hold, date ticks are thinned (one
more fit if they changed) and crowded text is fitted, each round followed
by a fresh fit and undone if it crushed a plot.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .. import labels, legend, ticks
from ..edgecase import settle
from ..geometry import get_renderer
from . import apply, decide, measure
from .edges import FIT_EDGES, TEXT_EDGES
from .model import FIT_ROUNDS, MAX_STEPS, Edges, Sides, Step

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


def one_step(fig: Figure, margins: Sides, last: Edges | None) -> Step | None:
    """Draw, settle what sits at the Axes size, measure and solve once."""
    renderer = _redraw(fig)
    if labels.settle_bars(fig, renderer):
        renderer = _redraw(fig)
    for _round in range(SETTLE_ROUNDS):
        moved = legend.settle(fig, renderer, fig.axes)
        if not labels.space_line_ends(fig, renderer) and not moved:
            break
        renderer = _redraw(fig)
    if labels.settle_panels(fig, renderer):
        renderer = _redraw(fig)
    facts = measure.content_facts(fig, renderer, margins, last)
    fit = settle(facts, decide.fit(facts), FIT_EDGES).plan
    return decide.solve(facts, fit)


@dataclass
class Fitter:
    """The margin fit of one grid, continuing from the edges it last wrote."""

    fig: Figure
    gs: GridSpec
    margins: Sides
    last: Edges | None = None

    def fit(self) -> Step | None:
        """Fit until the edges move under half a pixel (``None``: nothing
        to measure); then once more if thinning date ticks changed them."""
        step: Step | None = None
        for _ in range(2):
            for _ in range(MAX_STEPS):
                step = one_step(self.fig, self.margins, self.last)
                if step is None:
                    break
                apply.write_edges(self.fig, self.gs, step.edges)
                self.last = step.edges
                if step.converged:
                    break
            if step is None or not ticks.thin_dates(self.fig):
                break
        return step

    def fit_text(self, start: apply.Optional4) -> None:
        """Rounds of wraps, turns and spacing, each kept unless it crushed a
        plot; a figure whose only round was undone fits as without them."""
        record = apply.record_of(self.fig)
        kept = False
        for _round in range(FIT_ROUNDS):
            renderer = get_renderer(self.fig)
            facts, objects = measure.text_facts(
                self.fig, self.gs, renderer, record
            )
            plan = settle(facts, decide.text_plan(facts), TEXT_EDGES).plan
            if plan.empty:
                return
            before = measure.plot_sizes(self.fig, renderer)
            edges = apply.grid_edges(self.gs)
            groups = {n.label: n.group for n in facts.names}
            undo = apply.text(self.gs, plan, objects, groups, record)
            if self.fit() is None:
                return
            after = measure.plot_sizes(self.fig, get_renderer(self.fig))
            if not decide.crushed(before, after):
                kept = True
                continue
            undo()
            apply.write_edges(self.fig, self.gs, edges if kept else start)
            if not kept:
                self.last = None
            self.fit()
            return


def run(fig: Figure, gs: GridSpec, margins: Sides, fit_text: bool) -> None:
    """Lay out ``fig`` on ``gs`` from the figure as its author left it."""
    apply.restore(fig)
    start = apply.grid_edges(gs)
    ticks.prepare(fig)
    fitter = Fitter(fig, gs, margins)
    step = fitter.fit()
    if fit_text and step is not None and step.converged:
        fitter.fit_text(start)
    apply.remember(fig, gs, start)
