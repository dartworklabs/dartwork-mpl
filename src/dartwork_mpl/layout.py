"""Layout optimization utilities for Matplotlib figures.

Provides the ``simple_layout`` function, which uses ``scipy.optimize``
to automatically arrange subplot areas for optimal placement.
"""

from __future__ import annotations

__all__ = [
    "auto_layout",
    "get_bounding_box",
    "set_xmargin",
    "set_ymargin",
    "simple_layout",
    "tight_crop",
]

import contextlib
from typing import TYPE_CHECKING, Any

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec, SubplotSpec
from matplotlib.transforms import Bbox

if TYPE_CHECKING:
    from scipy.optimize import OptimizeResult


def get_bounding_box(boxes: list[Bbox]) -> tuple[float, float, float, float]:
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
) -> OptimizeResult | None:
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
    # No-op on figures with no axes — nothing to lay out, and indexing
    # ``fig.axes[0]`` would IndexError.
    if not fig.axes:
        return None

    # Handle SubplotSpec by getting its parent GridSpec
    actual_gs: Any
    if gs is not None:
        actual_gs = gs.get_gridspec() if isinstance(gs, SubplotSpec) else gs
    else:
        gridspec = fig.axes[0].get_gridspec()
        if gridspec is None:
            return None
        actual_gs = gridspec

    # GridSpecFromSubplotSpec (created by e.g. fig.colorbar) has no
    # .update() — walk up to the root GridSpec that does.
    while isinstance(actual_gs, GridSpecFromSubplotSpec):
        actual_gs = actual_gs._subplot_spec.get_gridspec()  # type: ignore[attr-defined]

    _import_weights = np.array(importance_weights)
    _margins = np.array(margins) * fig.get_dpi()

    def fun(x: np.ndarray[Any, Any]) -> float:
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
            ax_bboxes = [
                bb for ax in fig.axes if (bb := ax.get_tightbbox()) is not None
            ]
        else:
            ax_bboxes = [
                bb
                for ax in fig.axes
                if id(ax.get_gridspec()) == id(actual_gs)
                and (bb := ax.get_tightbbox()) is not None
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

    return minimize(
        fun,
        x0=np.array(bounds).mean(axis=1),
        bounds=bounds,
        method="L-BFGS-B",
        options={"gtol": gtol},
    )


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
        for txt in [*ax.texts, ax.title, ax.xaxis.label, ax.yaxis.label]:
            if (
                txt is None
                or not txt.get_visible()
                or not txt.get_text().strip()
            ):
                continue
            try:
                ext = txt.get_window_extent(renderer)
            except (RuntimeError, ValueError, AttributeError):
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
                except (RuntimeError, ValueError, AttributeError):
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
    overflowing sides. Converges in 1-3 iterations for typical charts;
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
    >>> ax.set_ylabel("Temperature (°C)")
    >>> dm.auto_layout(fig)
    """
    # No-op on figures with no axes — nothing to measure or adjust, and
    # downstream ``simple_layout`` / overflow probes assume at least one
    # axes.
    if not fig.axes:
        return

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


def tight_crop(
    fig: Figure,
    *,
    padding: float = 0.05,
    verbose: bool = False,
) -> tuple[float, float]:
    """Shrink figure to its content bounding box, eliminating outer whitespace.

    Unlike ``auto_layout`` which adjusts subplot margins inside a fixed figure
    size, ``tight_crop`` measures the union bounding box of all artists
    (axes spines, tick labels, axis labels, legends, suptitle, figure-level
    text/annotations) and resizes the figure itself to fit that bbox plus
    a uniform padding.

    The result is equivalent to ``savefig(bbox_inches="tight",
    pad_inches=padding)`` but is applied to the in-memory figure so that
    every subsequent save (PNG/SVG/PDF) produces consistently cropped
    output, and the figure's own ``get_size_inches()`` reflects the
    cropped size.

    Parameters
    ----------
    fig : Figure
        The Matplotlib Figure to crop.
    padding : float, optional
        Uniform padding in inches around the content bbox. Default is 0.05
        (~1.3 mm). Set to 0 for absolute tight crop.
    verbose : bool, optional
        If True, prints before/after dimensions.

    Returns
    -------
    tuple[float, float]
        New figure size in inches ``(width, height)``.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> fig, ax = dm.subplots(width="14cm", aspect="cinema")
    >>> ax.plot([1, 2, 3])
    >>> ax.set_ylabel("Value")
    >>> dm.tight_crop(fig, padding=0.04)
    """
    if not fig.axes:
        w, h = fig.get_size_inches()
        return float(w), float(h)

    # 1. Force a draw so all artists have measurable bboxes.
    fig.canvas.draw()
    # ``get_renderer`` exists on every concrete backend canvas but not on
    # the abstract base class; ignore the type-checker complaint.
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]

    # 2. Collect tight bboxes of every visible artist.
    bboxes_disp: list[Bbox] = []
    # Catch only the narrow set of errors that ``get_tightbbox`` /
    # ``get_window_extent`` realistically raise on a partially-drawn or
    # detached artist (renderer-less, no transform, etc). Anything else
    # should propagate so layout bugs are visible.
    bbox_errors = (RuntimeError, ValueError, AttributeError)

    for ax in fig.axes:
        try:
            bb = ax.get_tightbbox(renderer)
        except bbox_errors:
            bb = None
        if bb is not None and bb.width > 0 and bb.height > 0:
            bboxes_disp.append(bb)
        leg = ax.get_legend()
        if leg is not None and leg.get_visible():
            try:
                bb = leg.get_window_extent(renderer)
            except bbox_errors:
                continue
            if bb.width > 0 and bb.height > 0:
                bboxes_disp.append(bb)

    # Figure-level artists (suptitle, fig.texts, fig.legends).
    # ``Figure._suptitle`` is a private attribute; mypy doesn't know about
    # it but it has been stable across matplotlib 3.x.
    suptitle = getattr(fig, "_suptitle", None)
    if suptitle is not None and suptitle.get_visible():
        with contextlib.suppress(*bbox_errors):
            bboxes_disp.append(suptitle.get_window_extent(renderer))
    for txt in fig.texts:
        if not txt.get_visible():
            continue
        try:
            bb = txt.get_window_extent(renderer)
        except bbox_errors:
            continue
        if bb.width > 0 and bb.height > 0:
            bboxes_disp.append(bb)

    if not bboxes_disp:
        w, h = fig.get_size_inches()
        return float(w), float(h)

    union_disp = Bbox.union(bboxes_disp)

    # 3. Convert display-coord union bbox → inches.
    dpi = fig.get_dpi()
    cur_w_in, cur_h_in = fig.get_size_inches()
    cur_w_px = cur_w_in * dpi
    cur_h_px = cur_h_in * dpi

    # Empty-space margins on each side, in pixels.
    pad_left_px = union_disp.x0
    pad_right_px = cur_w_px - union_disp.x1
    pad_bottom_px = union_disp.y0
    pad_top_px = cur_h_px - union_disp.y1

    pad_target_px = padding * dpi

    # New figure size = content + uniform target padding on all sides.
    new_w_in = (union_disp.width + 2 * pad_target_px) / dpi
    new_h_in = (union_disp.height + 2 * pad_target_px) / dpi

    # Compute current axes positions in figure-relative coords, then
    # translate them so the content bbox is recentered with the new
    # padding inside the resized figure.
    # Old content bbox in figure-relative coords:
    old_content_x0 = union_disp.x0 / cur_w_px
    old_content_y0 = union_disp.y0 / cur_h_px
    old_content_x1 = union_disp.x1 / cur_w_px
    old_content_y1 = union_disp.y1 / cur_h_px

    # Capture old axes positions (figure-relative).
    old_positions = [
        (ax, ax.get_position(original=False).bounds) for ax in fig.axes
    ]

    # Resize figure.
    fig.set_size_inches(new_w_in, new_h_in)

    # In the new figure, the content area should map to:
    #   x: [pad_target_px, pad_target_px + content_width] / new_w_px
    #   y: [pad_target_px, pad_target_px + content_height] / new_h_px
    new_w_px = new_w_in * dpi
    new_h_px = new_h_in * dpi
    new_content_x0 = pad_target_px / new_w_px
    new_content_y0 = pad_target_px / new_h_px
    new_content_w = union_disp.width / new_w_px
    new_content_h = union_disp.height / new_h_px

    # Apply affine map to each axes position.
    old_content_w = old_content_x1 - old_content_x0
    old_content_h = old_content_y1 - old_content_y0
    if old_content_w <= 0 or old_content_h <= 0:
        w, h = fig.get_size_inches()
        return float(w), float(h)

    sx = new_content_w / old_content_w
    sy = new_content_h / old_content_h
    for ax, (x, y, w, h) in old_positions:
        # Translate old position into content-local coords, scale, retranslate
        new_x = new_content_x0 + (x - old_content_x0) * sx
        new_y = new_content_y0 + (y - old_content_y0) * sy
        new_w = w * sx
        new_h = h * sy
        ax.set_position((new_x, new_y, new_w, new_h))

    if verbose:
        print(
            f"[tight_crop] {cur_w_in:.2f}x{cur_h_in:.2f}in "
            f"→ {new_w_in:.2f}x{new_h_in:.2f}in  "
            f"(L:{pad_left_px/dpi:.2f} R:{pad_right_px/dpi:.2f} "
            f"B:{pad_bottom_px/dpi:.2f} T:{pad_top_px/dpi:.2f}in trimmed)"
        )

    return (new_w_in, new_h_in)
