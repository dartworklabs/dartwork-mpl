"""Layout optimization utilities for Matplotlib figures.

Provides the ``simple_layout`` function, which uses ``scipy.optimize``
to automatically arrange subplot areas for optimal placement.
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
    """
    Compute the minimum bounding box that encloses all given box regions.

    Parameters
    ----------
    boxes : list
        List of box objects, each having at minimum p0 (bottom-left
        coordinate), width, and height attributes.

    Returns
    -------
    tuple[float, float, float, float]
        Overall bounding box as (min_x, min_y, bbox_width, bbox_height).
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
    """Set responsive margins or fixed bounds on the x-axis limits.

    Wraps ``set_xlim`` to allow specifying a global margin ratio while
    optionally pinning one or both edges to fixed values.

    Parameters
    ----------
    ax : Axes
        The matplotlib Axes to modify.
    margin : float, optional
        Fractional margin applied to both sides. Default is 0.05.
    left : float | None, optional
        Fixed left bound for the x-axis. Overrides the margin on that side.
    right : float | None, optional
        Fixed right bound for the x-axis. Overrides the margin on that side.
    """
    ax.margins(x=margin)
    xlim = list(ax.get_xlim())
    if left is not None:
        xlim[0] = left
    if right is not None:
        xlim[1] = right
    ax.set_xlim((float(xlim[0]), float(xlim[1])))


def set_ymargin(
    ax: Axes,
    margin: float = 0.05,
    *,
    bottom: float | None = None,
    top: float | None = None,
) -> None:
    """Set responsive margins or fixed bounds on the y-axis limits.

    Wraps ``set_ylim`` to allow specifying a global margin ratio while
    optionally pinning one or both edges to fixed values.

    Parameters
    ----------
    ax : Axes
        The matplotlib Axes to modify.
    margin : float, optional
        Fractional margin applied to both sides. Default is 0.05.
    bottom : float | None, optional
        Fixed bottom bound for the y-axis. Overrides the margin on that side.
    top : float | None, optional
        Fixed top bound for the y-axis. Overrides the margin on that side.
    """
    ax.margins(y=margin)
    ylim = list(ax.get_ylim())
    if bottom is not None:
        ylim[0] = bottom
    if top is not None:
        ylim[1] = top
    ax.set_ylim((float(ylim[0]), float(ylim[1])))


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
    """Apply an optimized layout to a GridSpec for fine-tuned subplot positioning.

    Uses the L-BFGS-B optimization algorithm to compute GridSpec parameters
    that best fit subplots within the specified margins and bounding box.
    Provides more consistent and predictable margin control than the built-in
    ``tight_layout``.

    Parameters
    ----------
    fig : Figure
        The Matplotlib Figure to apply the layout to.
    gs : GridSpec | None, optional
        GridSpec to optimize. If None, defaults to the GridSpec of
        ``fig.axes[0]``.
    margins : tuple[float, float, float, float], optional
        Margins in inches (left, right, bottom, top). Default is
        (0.15, 0.05, 0.05, 0.05).
    bbox : tuple[float, float, float, float], optional
        Target region in figure-relative coordinates (left, right,
        bottom, top). Default (0, 1, 0, 1) covers the entire figure.
    verbose : bool, optional
        Whether to print diagnostic logs during optimization. Default is False.
    gtol : float, optional
        Gradient tolerance for L-BFGS-B optimization. Default is 1e-2.
    bound_margin : float, optional
        Buffer margin for generating parameter bounds, controlling the
        optimization search space. Default is 0.2.
    use_all_axes : bool, optional
        If True, uses all Axes in the Figure for bounding-box computation.
        If False, only Axes belonging to *gs* are considered. Default is True.
    importance_weights : tuple[float, float, float, float], optional
        Weights (left, right, bottom, top) controlling the importance of
        matching each margin. Default is (1, 1, 1, 1).

    Returns
    -------
    OptimizeResult
        The scipy optimization result object.
    """
    actual_gs: GridSpec = gs if gs is not None else fig.axes[0].get_gridspec()  # type: ignore[assignment]

    _import_weights = np.array(importance_weights)
    _margins = np.array(margins) * fig.get_dpi()

    def fun(x: np.ndarray) -> float:
        actual_gs.update(left=x[0], right=x[1], bottom=x[2], top=x[3])

        if use_all_axes:
            ax_bboxes = [ax.get_tightbbox() for ax in fig.axes]
        else:
            ax_bboxes = [
                ax.get_tightbbox()
                for ax in fig.axes
                if id(ax.get_gridspec()) == id(actual_gs)
            ]

        all_bbox = get_bounding_box(ax_bboxes)
        values = np.array(all_bbox)

        fbox = fig.bbox
        targets = np.array(
            [
                fbox.width * bbox[0] + _margins[0],
                fbox.height * bbox[2] + _margins[2],
                fbox.width * (bbox[1] - bbox[0]) - 2 * _margins[1],
                fbox.height * (bbox[3] - bbox[2]) - 2 * _margins[3],
            ]
        )

        scales = np.array([fbox.width, fbox.height, fbox.width, fbox.height])
        loss = np.square((values - targets) / scales * _import_weights).sum()

        return float(loss)

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
