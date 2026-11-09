"""Shrink a figure to its content (``tight_crop``) and the union of bounding boxes."""

from __future__ import annotations

from matplotlib.figure import Figure
from matplotlib.transforms import Bbox

from .._figure_geometry import BBOX_ERRORS as _BBOX_ERRORS
from .._figure_geometry import (
    get_renderer,
    holders_shown,
    iter_figure_level_extents,
)


def get_bounding_box(boxes: list[Bbox]) -> tuple[float, float, float, float]:
    """Compute the minimum bounding box that encloses all given box regions.

    Parameters
    ----------
    boxes : list
        List of box objects, each having at minimum p0 (bottom-left
        coordinate), width, and height attributes.

    Returns
    -------
    tuple[float, float, float, float]
        Overall bounding box as ``(min_x, min_y, bbox_width, bbox_height)``.

    Raises
    ------
    ValueError
        If ``boxes`` is empty — returning the infinite sentinel tuple
        would silently poison downstream position math with inf/NaN.
    """
    if not boxes:
        raise ValueError("get_bounding_box() requires at least one box")

    min_x = float("inf")
    min_y = float("inf")
    max_x = float("-inf")
    max_y = float("-inf")

    for box in boxes:
        min_x = min(min_x, box.p0[0])
        min_y = min(min_y, box.p0[1])
        max_x = max(max_x, box.p0[0] + box.width)
        max_y = max(max_y, box.p0[1] + box.height)

    return (min_x, min_y, max_x - min_x, max_y - min_y)


# ─────────────────────────────────────────────────────────────────────
# tight_crop — independent helper, unchanged
# ─────────────────────────────────────────────────────────────────────


def tight_crop(
    fig: Figure, *, padding: float = 0.05, verbose: bool = False
) -> tuple[float, float]:
    """Shrink figure to its content bounding box, eliminating outer whitespace.

    Unlike ``simple_layout`` which adjusts subplot margins inside a fixed
    figure size, ``tight_crop`` measures the union bounding box of all
    artists (axes spines, tick labels, axis labels, legends, suptitle,
    figure-level text/annotations) and resizes the figure itself to fit
    that bbox plus a uniform padding.

    Parameters
    ----------
    fig : Figure
        The Matplotlib Figure to crop.
    padding : float, optional
        Uniform padding in inches around the content bbox. Default is
        ``0.05`` (~1.3 mm). Set to ``0`` for absolute tight crop.
    verbose : bool, optional
        If ``True``, prints before/after dimensions.

    Returns
    -------
    tuple[float, float]
        New figure size in inches ``(width, height)``.
    """
    if not fig.axes:
        w, h = fig.get_size_inches()
        return float(w), float(h)

    fig.canvas.draw()
    renderer = get_renderer(fig)

    bboxes_disp: list[Bbox] = []
    for ax in fig.axes:
        if not holders_shown(ax):
            continue  # a hidden SubFigure draws none of its Axes
        try:
            bb = ax.get_tightbbox(renderer)
        except _BBOX_ERRORS:
            bb = None
        if bb is not None and bb.width > 0 and bb.height > 0:
            bboxes_disp.append(bb)
        leg = ax.get_legend()
        if leg is not None and leg.get_visible():
            try:
                bb = leg.get_window_extent(renderer)
            except _BBOX_ERRORS:
                continue
            if bb.width > 0 and bb.height > 0:
                bboxes_disp.append(bb)

    # Figure-level artists (suptitle, sup-labels, fig.text, fig.legend)
    # share the guarded walk with the layout engine.
    for _art, bb in iter_figure_level_extents(fig, renderer):
        bboxes_disp.append(bb)

    if not bboxes_disp:
        w, h = fig.get_size_inches()
        return float(w), float(h)

    union_disp = Bbox.union(bboxes_disp)
    dpi = fig.get_dpi()
    cur_w_in, cur_h_in = fig.get_size_inches()
    cur_w_px = cur_w_in * dpi
    cur_h_px = cur_h_in * dpi
    pad_target_px = padding * dpi
    new_w_in = (union_disp.width + 2 * pad_target_px) / dpi
    new_h_in = (union_disp.height + 2 * pad_target_px) / dpi

    old_content_x0 = union_disp.x0 / cur_w_px
    old_content_y0 = union_disp.y0 / cur_h_px
    old_content_x1 = union_disp.x1 / cur_w_px
    old_content_y1 = union_disp.y1 / cur_h_px

    old_positions = [
        (ax, ax.get_position(original=False).bounds) for ax in fig.axes
    ]

    fig.set_size_inches(new_w_in, new_h_in)

    new_w_px = new_w_in * dpi
    new_h_px = new_h_in * dpi
    new_content_x0 = pad_target_px / new_w_px
    new_content_y0 = pad_target_px / new_h_px
    new_content_w = union_disp.width / new_w_px
    new_content_h = union_disp.height / new_h_px

    old_content_w = old_content_x1 - old_content_x0
    old_content_h = old_content_y1 - old_content_y0
    if old_content_w <= 0 or old_content_h <= 0:
        w, h = fig.get_size_inches()
        return float(w), float(h)

    sx = new_content_w / old_content_w
    sy = new_content_h / old_content_h
    for ax, (x, y, w, h) in old_positions:
        new_x = new_content_x0 + (x - old_content_x0) * sx
        new_y = new_content_y0 + (y - old_content_y0) * sy
        new_w = w * sx
        new_h = h * sy
        ax.set_position((new_x, new_y, new_w, new_h))

    if verbose:
        pad_left_px = union_disp.x0
        pad_right_px = cur_w_px - union_disp.x1
        pad_bottom_px = union_disp.y0
        pad_top_px = cur_h_px - union_disp.y1
        print(
            f"[tight_crop] {cur_w_in:.2f}x{cur_h_in:.2f}in "
            f"→ {new_w_in:.2f}x{new_h_in:.2f}in  "
            f"(L:{pad_left_px / dpi:.2f} R:{pad_right_px / dpi:.2f} "
            f"B:{pad_bottom_px / dpi:.2f} T:{pad_top_px / dpi:.2f}in trimmed)"
        )

    return (new_w_in, new_h_in)
