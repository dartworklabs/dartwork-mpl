"""Content-aware margins: :func:`simple_layout`, ``dm.simple_layout`` once
``compose.layout`` gives it the other slices' steps.

The root GridSpec's edges are set so the drawn content of every Axes (tick
labels, axis names, titles, texts, legends) sits ``margin`` from the canvas
edge, past what figure-level text and legends reserve, measured again until
no edge moves by half a pixel. No optimiser: the same figure gives the same
layout every time.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from . import decide, loop, measure
from .given import Neighbours
from .model import MarginInput, Refuse, Request, parse_margins

if TYPE_CHECKING:
    from matplotlib.figure import Figure
    from matplotlib.gridspec import GridSpecBase, SubplotSpec

__all__ = ["MarginInput", "Neighbours", "simple_layout"]


def simple_layout(
    fig: Figure,
    gs: GridSpecBase | SubplotSpec | None = None,
    *,
    margin: MarginInput = "1mm",
    ml: MarginInput | None = None,
    mr: MarginInput | None = None,
    mt: MarginInput | None = None,
    mb: MarginInput | None = None,
    fit_labels: bool = True,
    given: Neighbours,
) -> None:
    """``dm.simple_layout`` (``compose.layout``), the other slices' steps and
    records ``given``. A figure with no Axes is left alone, one without a
    GridSpec with a warning; a margin that is not finite raises
    ``ValueError``."""
    grid = measure.root_grid(fig, gs)
    request = Request(has_axes=bool(fig.axes), has_grid=grid is not None)
    answer = decide.answer(request)
    if isinstance(answer, Refuse):
        if answer.warning is not None:
            warnings.warn(answer.warning, stacklevel=3)
        return
    assert grid is not None
    size = fig.get_size_inches()
    margins = parse_margins(
        margin, (ml, mr, mt, mb), (float(size[0]), float(size[1]))
    )
    loop.run(fig, grid, margins, fit_labels, given)
