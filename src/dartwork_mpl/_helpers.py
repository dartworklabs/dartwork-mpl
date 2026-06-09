"""Shared internal helpers.

Small utilities used by multiple modules. Not part of the public API.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure


def create_parent_path(path: str | Path) -> None:
    """Create parent directory if it doesn't exist.

    Parameters
    ----------
    path : str or Path
        Path whose parent directory will be created.
    """
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True)


def get_renderer(fig: Figure | SubFigure) -> RendererBase:
    """Return ``fig.canvas.get_renderer()`` with the type-ignore centralised.

    Matplotlib's ``FigureCanvasBase`` does not declare ``get_renderer`` —
    only the backend subclasses (``FigureCanvasAgg`` etc.) do. mypy
    flags every call site with ``attr-defined``. Routing through this
    helper keeps the suppression in one place.

    Parameters
    ----------
    fig : matplotlib.figure.Figure or matplotlib.figure.SubFigure
        Figure (or SubFigure) whose canvas exposes a renderer (true
        for every backend dartwork-mpl supports). SubFigure delegates
        its canvas to the parent Figure, so the same call works.

    Returns
    -------
    matplotlib.backend_bases.RendererBase
        The renderer used by ``fig``'s canvas.
    """
    return fig.canvas.get_renderer()  # type: ignore[attr-defined,no-any-return]
