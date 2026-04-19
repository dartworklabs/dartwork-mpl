"""Layout optimization utilities for Matplotlib figures.

Provides the ``simple_layout`` function, which uses ``scipy.optimize``
to automatically arrange subplot areas for optimal placement.
"""

from __future__ import annotations

__all__ = [
    "auto_layout",
    "simple_layout",
    "get_bounding_box",
    "set_xmargin",
    "set_ymargin",
]

from typing import TYPE_CHECKING

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec, SubplotSpec

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
    gs: GridSpec | SubplotSpec | None = None,
    margins: tuple[float, float, float, float] = (0.10, 0.10, 0.08, 0.05),
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
    gs : GridSpec | SubplotSpec | None, optional
        GridSpec or SubplotSpec to optimize. If None, defaults to the GridSpec of
        ``fig.axes[0]``. If a SubplotSpec is provided, its parent GridSpec
        will be used.
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
    # Handle SubplotSpec by getting its parent GridSpec
    if gs is not None:
        if isinstance(gs, SubplotSpec):
            actual_gs: GridSpec = gs.get_gridspec()  # type: ignore[assignment]
        else:
            actual_gs = gs
    else:
        actual_gs = fig.axes[0].get_gridspec()  # type: ignore[assignment]

    # GridSpecFromSubplotSpec (created by e.g. fig.colorbar) has no
    # .update() — walk up to the root GridSpec that does.
    while isinstance(actual_gs, GridSpecFromSubplotSpec):
        actual_gs = actual_gs._subplot_spec.get_gridspec()  # type: ignore[assignment]

    _import_weights = np.array(importance_weights)
    _margins = np.array(margins) * fig.get_dpi()

    def fun(x: np.ndarray) -> float:
        """Objective function for layout optimization.

        Parameters
        ----------
        x : np.ndarray
            Array of [left, right, bottom, top] GridSpec parameters

        Returns
        -------
        float
            Loss value representing distance from target margins
        """
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


def _measure_overflow(fig: Figure) -> dict[str, float]:
    """Measure per-side overflow of all visual elements beyond figure bounds.

    Parameters
    ----------
    fig : Figure
        The figure to inspect (must already be drawn).

    Returns
    -------
    dict[str, float]
        Maximum overflow in pixels for each side: left, right, bottom, top.
        Positive values mean the content extends beyond the figure edge.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    fig_bbox = fig.bbox

    overflow: dict[str, float] = {
        "left": 0.0,
        "right": 0.0,
        "bottom": 0.0,
        "top": 0.0,
    }

    for ax in fig.axes:
        # Text objects: titles, labels, annotations
        for txt in ax.texts + [ax.title, ax.xaxis.label, ax.yaxis.label]:
            if (
                txt is None
                or not txt.get_visible()
                or not txt.get_text().strip()
            ):
                continue
            try:
                ext = txt.get_window_extent(renderer)
            except Exception:
                continue

            overflow["left"] = max(overflow["left"], fig_bbox.x0 - ext.x0)
            overflow["right"] = max(overflow["right"], ext.x1 - fig_bbox.x1)
            overflow["bottom"] = max(overflow["bottom"], fig_bbox.y0 - ext.y0)
            overflow["top"] = max(overflow["top"], ext.y1 - fig_bbox.y1)

        # Tick labels
        for axis in (ax.xaxis, ax.yaxis):
            vmin, vmax = axis.get_view_interval()
            tol = (vmax - vmin) * 1e-5

            for tick in axis.get_ticklabels():
                if not tick.get_visible() or not tick.get_text().strip():
                    continue
                try:
                    ext = tick.get_window_extent(renderer)
                    pos = tick.get_position()
                except Exception:
                    continue

                # Ignore ticks that are outside the view limits
                # (e.g., auto-generated ticks outside manually set ylim)
                val = pos[0] if axis == ax.xaxis else pos[1]
                if val < vmin - tol or val > vmax + tol:
                    continue

                overflow["left"] = max(overflow["left"], fig_bbox.x0 - ext.x0)
                overflow["right"] = max(overflow["right"], ext.x1 - fig_bbox.x1)
                overflow["bottom"] = max(
                    overflow["bottom"], fig_bbox.y0 - ext.y0
                )
                overflow["top"] = max(overflow["top"], ext.y1 - fig_bbox.y1)

    return overflow


def auto_layout(
    fig: Figure,
    *,
    padding: float | tuple[float, float, float, float] = 0.08,
    max_iter: int = 5,
    tolerance: float = 2.0,
    verbose: bool = False,
) -> None:
    """Content-aware layout that auto-adjusts margins to eliminate overflow.

    Wraps ``simple_layout`` with a Validate → Measure → Adjust → Retry loop.
    Starts with minimal margins, measures actual per-side overflow using
    text and tick-label bounding boxes, and increases margins only on
    overflowing sides. Converges in 1–3 iterations for typical charts;
    axes-relative annotations (which move with the subplot) may need more.

    Parameters
    ----------
    fig : Figure
        The Matplotlib Figure to lay out.
    padding : float | tuple[float, float, float, float], optional
        Initial padding in inches for all four sides (left, right, bottom, top).
        If a single float, it is used for all sides. Default is 0.08.
    max_iter : int, optional
        Maximum number of measure-and-adjust iterations. Default is 5.
    tolerance : float, optional
        Overflow tolerance in pixels. Overflows below this threshold are
        ignored. Default is 2.0 px.
    verbose : bool, optional
        If True, prints per-iteration diagnostics. Default is False.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> fig, ax = plt.subplots()
    >>> ax.plot([1, 2, 3])
    >>> ax.set_ylabel("Revenue ($M)")
    >>> dm.auto_layout(fig)
    """
    # Normalize padding to a 4-tuple
    if isinstance(padding, (int, float)):
        margins = [float(padding)] * 4
    else:
        margins = list(padding)

    BUFFER = 0.02  # extra buffer in inches added to the overflowing side
    SIDE_MAP = {"left": 0, "right": 1, "bottom": 2, "top": 3}

    # Track per-side consecutive overflow count for escalation
    consec: dict[str, int] = dict.fromkeys(SIDE_MAP, 0)

    for iteration in range(max_iter):
        # Apply layout with current margins
        simple_layout(fig, margins=tuple(margins))  # type: ignore[arg-type]

        # Measure overflow on each side
        overflow = _measure_overflow(fig)

        if verbose:
            print(
                f"[auto_layout] iter {iteration + 1}: "
                f"margins=({margins[0]:.3f}, {margins[1]:.3f}, "
                f"{margins[2]:.3f}, {margins[3]:.3f})  "
                f"overflow=L:{overflow['left']:.1f}px "
                f"R:{overflow['right']:.1f}px "
                f"B:{overflow['bottom']:.1f}px "
                f"T:{overflow['top']:.1f}px"
            )

        # Check if all sides are within tolerance
        max_overflow = max(overflow.values())
        if max_overflow <= tolerance:
            if verbose:
                print(
                    f"[auto_layout] Converged in {iteration + 1} iteration(s)."
                )
            return

        # Increase margins on overflowing sides with escalation
        dpi = fig.get_dpi()
        for side, idx in SIDE_MAP.items():
            if overflow[side] > tolerance:
                consec[side] += 1
                # Escalation: multiply increment for persistent overflow
                # (handles axes-relative content that moves with subplot)
                scale = 1.0 + 1.0 * (consec[side] - 1)
                increment = (
                    (overflow[side] + tolerance) / dpi + BUFFER
                ) * scale
                margins[idx] += increment
            else:
                consec[side] = 0

    if verbose:
        print(
            f"[auto_layout] Reached max_iter={max_iter}. "
            f"Residual overflow: {overflow}"
        )
