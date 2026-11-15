"""The renderer lookup ``place_legend`` still imports from here.

The point-label obstacle code moved to :mod:`dartwork_mpl.labels.measure`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._figure_geometry import get_renderer

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure


def _renderer_for_axes(ax: Axes) -> tuple[Figure | SubFigure, RendererBase]:
    fig = ax.get_figure()
    if fig is None or fig.canvas is None:
        raise ValueError("Axes must be part of a Figure with a canvas")
    fig.canvas.draw()
    return fig, get_renderer(fig)
