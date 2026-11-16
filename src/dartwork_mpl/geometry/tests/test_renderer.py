"""A figure without a live canvas is measured as a drawn Agg canvas measures it."""

from __future__ import annotations

import matplotlib as mpl
import numpy as np
import pytest
from matplotlib.artist import Artist
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from dartwork_mpl import geometry as g


def _plot(fig: Figure):
    ax = fig.subplots()
    ax.plot([0, 1, 2], [1, 3, 2])
    ax.set(xlabel="Elapsed time (s)", ylabel="Signal", title="Observation")
    fig.set_layout_engine("constrained")
    return ax


def _extents(ax, renderer) -> np.ndarray:
    texts = (ax.xaxis.label, ax.yaxis.label, ax.title)
    return np.array([t.get_window_extent(renderer).bounds for t in texts])


def _control() -> np.ndarray:
    fig = Figure(figsize=(5, 3), dpi=123)
    FigureCanvasAgg(fig)
    ax = _plot(fig)
    fig.canvas.draw()
    return _extents(ax, fig.canvas.get_renderer())


@pytest.mark.parametrize("fmt", ["png", "pdf", "svg"])
def test_a_plain_figure_measures_at_its_dpi_and_keeps_its_canvas(fmt) -> None:
    with mpl.rc_context({"savefig.format": fmt}):
        fig = Figure(figsize=(5, 3), dpi=123)
        ax = _plot(fig)
        canvas = fig.canvas
        renderer = g.get_renderer(fig)
    assert fig.canvas is canvas and fig.dpi == 123
    np.testing.assert_allclose(_extents(ax, renderer), _control(), atol=1e-10)


def test_a_live_canvas_keeps_its_own_renderer() -> None:
    fig = Figure()
    FigureCanvasAgg(fig)
    _plot(fig)
    assert g.get_renderer(fig) is fig.canvas.get_renderer()


class _Broken(Artist):
    def draw(self, renderer) -> None:
        raise RuntimeError("artist draw failed")


def test_a_failed_draw_propagates_and_the_canvas_is_restored() -> None:
    fig = Figure()
    _plot(fig)
    canvas = fig.canvas
    fig.add_artist(_Broken())
    with pytest.raises(RuntimeError, match="artist draw failed"):
        g.get_renderer(fig)
    assert fig.canvas is canvas
