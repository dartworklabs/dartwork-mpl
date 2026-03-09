"""Layout optimization for matplotlib figures.

Provides ``simple_layout`` which uses ``scipy.optimize`` to
automatically position subplot panes within a figure.
"""

from __future__ import annotations

__all__ = ["simple_layout", "get_bounding_box", "set_xmargin", "set_ymargin"]

from typing import TYPE_CHECKING

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

if TYPE_CHECKING:
    from scipy.optimize import OptimizeResult


def get_bounding_box(boxes: list) -> tuple[float, float, float, float]:
    """Get the bounding box that contains all given boxes.

    Parameters
    ----------
    boxes : list
        List of box objects with p0, width, and height attributes.

    Returns
    -------
    tuple
        (min_x, min_y, bbox_width, bbox_height) of the bounding box.
    """
    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    for box in boxes:
        min_x = min(min_x, box.p0[0])
        min_y = min(min_y, box.p0[1])
        max_x = max(max_x, box.p0[0] + box.width)
        max_y = max(max_y, box.p0[1] + box.height)

    bbox_width = max_x - min_x
    bbox_height = max_y - min_y

    return (min_x, min_y, bbox_width, bbox_height)


def set_xmargin(
    ax: Axes,
    margin: float = 0.05,
    *,
    left: float | None = None,
    right: float | None = None,
) -> None:
    """Set responsive specific margin bounds on x-axis limit.

    This function modifies ``set_xlim`` to establish
    a one-side or bounded margins while preserving the dynamic data span.

    Parameters
    ----------
    ax : Axes
        The matplotlib axes object to adjust.
    margin : float, default 0.05
        The default margin ratio.
    left : float, optional
        Fixed left boundary for x-axis. Overrides global margin.
    right : float, optional
        Fixed right boundary for x-axis. Overrides global margin.
    """
    ax.margins(x=margin)
    xlim = list(ax.get_xlim())
    if left is not None:
        xlim[0] = left
    if right is not None:
        xlim[1] = right
    ax.set_xlim(xlim)


def set_ymargin(
    ax: Axes,
    margin: float = 0.05,
    *,
    bottom: float | None = None,
    top: float | None = None,
) -> None:
    """Set responsive specific margin bounds on y-axis limit.

    This function modifies ``set_ylim`` to establish
    a one-side or bounded margins while preserving the dynamic data span.

    Parameters
    ----------
    ax : Axes
        The matplotlib axes object to adjust.
    margin : float, default 0.05
        The default margin ratio.
    bottom : float, optional
        Fixed bottom boundary for y-axis. Overrides global margin.
    top : float, optional
        Fixed top boundary for y-axis. Overrides global margin.
    """
    ax.margins(y=margin)
    ylim = list(ax.get_ylim())
    if bottom is not None:
        ylim[0] = bottom
    if top is not None:
        ylim[1] = top
    ax.set_ylim(ylim)


def simple_layout(
    fig: Figure,
    gs: GridSpec | None = None,
    margins: tuple[float, float, float, float] = (0.15, 0.05, 0.05, 0.05),
    bbox: tuple[float, float, float, float] = (0, 1, 0, 1),
    verbose: bool = False,
    gtol: float = 1e-2,
    bound_margin: float = 0.2,
    use_all_axes: bool = True,
    importance_weights: tuple[float, float, float, float] = (1, 1, 1, 1),
) -> OptimizeResult:
    """Apply optimised layout to a GridSpec.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure object.
    gs : matplotlib.gridspec.GridSpec, optional
        GridSpec object. None uses the first GridSpec.
    margins : tuple[float, float, float, float], optional
        Inch margins (left, right, bottom, top).
    bbox : tuple[float, float, float, float], optional
        Figure-coordinate bounding box (left, right, bottom, top).
    verbose : bool, optional
        Print optimisation diagnostics.
    gtol : float, optional
        Gradient tolerance for L-BFGS-B.
    bound_margin : float, optional
        Margin for generating parameter bounds.
    use_all_axes : bool, optional
        If True, use all axes; otherwise only those from *gs*.
    importance_weights : tuple[float, float, float, float], optional
        Importance weights for each target (left, right, bottom, top).

    Returns
    -------
    scipy.optimize.OptimizeResult
        Optimization result.
    """
    if gs is None:
        gs = fig.axes[0].get_gridspec()

    importance_weights = np.array(importance_weights)
    margins = np.array(margins) * fig.get_dpi()

    def fun(x: np.ndarray) -> float:
        gs.update(left=x[0], right=x[1], bottom=x[2], top=x[3])

        if use_all_axes:
            ax_bboxes = [ax.get_tightbbox() for ax in fig.axes]
        else:
            ax_bboxes = [
                ax.get_tightbbox()
                for ax in fig.axes
                if id(ax.get_gridspec()) == id(gs)
            ]

        all_bbox = get_bounding_box(ax_bboxes)
        values = np.array(all_bbox)

        fbox = fig.bbox
        targets = np.array(
            [
                fbox.width * bbox[0] + margins[0],
                fbox.height * bbox[2] + margins[2],
                fbox.width * (bbox[1] - bbox[0]) - 2 * margins[1],
                fbox.height * (bbox[3] - bbox[2]) - 2 * margins[3],
            ]
        )

        scales = np.array([fbox.width, fbox.height, fbox.width, fbox.height])
        loss = np.square((values - targets) / scales * importance_weights).sum()

        return loss

    bounds = [
        (bbox[0], bbox[0] + bound_margin),
        (bbox[1] - bound_margin, bbox[1]),
        (bbox[2], bbox[2] + bound_margin),
        (bbox[3] - bound_margin, bbox[3]),
    ]

    from scipy.optimize import minimize

    result = minimize(
        fun,
        x0=np.array(bounds).mean(axis=1),
        bounds=bounds,
        method="L-BFGS-B",
        options={"gtol": gtol},
    )

    return result
