"""Axes annotation helpers.

Provides ``label_axes`` for panel labels (a, b, c, …) and
``arrow_axis`` for bidirectional axis annotations.
"""

from __future__ import annotations

__all__ = ["label_axes", "arrow_axis"]

import string

import numpy as np
from matplotlib.axes import Axes

from .scale import fs


def label_axes(
    axes: list[Axes] | np.ndarray,
    labels: list[str] | None = None,
    fontsize: float = 10,
    fontweight: str = "bold",
    x: float | str = "auto",
    y: float = 1.05,
    **kwargs,
) -> list:
    """Add standardised panel labels (a, b, c, …) to subplot axes.

    Labels are placed at the top-left corner of each axes using
    the axes coordinate system.

    Parameters
    ----------
    axes : list of Axes or ndarray
        Axes objects to label.
    labels : list of str, optional
        Custom labels. If None, uses lowercase alphabet (a, b, c, …).
    fontsize : float, optional
        Font size in points. Default is 10.
    fontweight : str, optional
        Font weight. Default is ``'bold'``.
    x : float or 'auto', optional
        X position in axes coordinates. If ``'auto'`` (default), uses
        −0.18 for axes with a y-axis label, −0.02 for axes without.
    y : float, optional
        Y position in axes coordinates. Default is 1.05.
    **kwargs
        Additional keyword arguments passed to ``ax.text()``.

    Returns
    -------
    list
        List of Text objects created.
    """
    if isinstance(axes, np.ndarray):
        axes = axes.flatten().tolist()

    if labels is None:
        labels = list(string.ascii_lowercase[: len(axes)])

    texts = []
    for ax, label in zip(axes, labels, strict=False):
        if x == "auto":
            has_ylabel = ax.get_ylabel().strip() != ""
            x_pos = -0.18 if has_ylabel else -0.02
        else:
            x_pos = x

        t = ax.text(
            x_pos,
            y,
            label,
            transform=ax.transAxes,
            fontsize=fontsize,
            fontweight=fontweight,
            va="bottom",
            ha="left",
            **kwargs,
        )
        texts.append(t)

    return texts


def arrow_axis(
    ax: Axes,
    direction: str,
    label: str,
    *,
    offset: float = -0.05,
    low: str = "Low",
    high: str = "High",
    fontsize: float | None = None,
    fontsize_label: float | None = None,
    pad: float = -0.005,
    weight: str = "normal",
    color: str = "black",
    arrow_kw: dict | None = None,
) -> None:
    """Draw a bidirectional arrow axis with Low/High labels.

    Creates  ``Low ◄── label ──► High``  along a spine edge.

    Parameters
    ----------
    ax : Axes
        Target axes.
    direction : {'x', 'y'}
        ``'x'`` places a horizontal axis below the x-spine;
        ``'y'`` places a vertical axis left of the y-spine.
    label : str
        Center axis label.
    offset : float, optional
        Axes-fraction distance from the spine. Default ``-0.05``.
    low : str, optional
        Text for the low end. Default ``'Low'``.
    high : str, optional
        Text for the high end. Default ``'High'``.
    fontsize : float or None, optional
        Font size for *low*/*high* labels. Default ``fs(-1)``.
    fontsize_label : float or None, optional
        Font size for the center *label*. Default ``fs(0)``.
    pad : float, optional
        Axes-fraction gap between text edges and arrowheads.
    weight : str, optional
        Font weight for all text elements. Default ``'normal'``.
    color : str, optional
        Color for text and arrows. Default ``'black'``.
    arrow_kw : dict or None, optional
        Override ``arrowprops`` for ``ax.annotate``.
    """
    if fontsize is None:
        fontsize = fs(-1)
    if fontsize_label is None:
        fontsize_label = fs(0)
    if arrow_kw is None:
        arrow_kw = {
            "arrowstyle": "-|>,head_width=0.1",
            "color": color,
            "lw": 0.25,
        }

    renderer = ax.get_figure().canvas.get_renderer()
    inv = ax.transAxes.inverted()
    rot_kw = (
        {"rotation": 90, "rotation_mode": "anchor"}
        if direction == "y"
        else {}
    )

    # ── place texts ──────────────────────────────────────────
    if direction == "x":
        p_lo, p_hi, p_lb = (0, offset), (1, offset), (0.5, offset)
    else:
        p_lo, p_hi, p_lb = (offset, 0), (offset, 1), (offset, 0.5)

    t_lo = ax.text(
        *p_lo,
        low,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=weight,
        color=color,
        ha="left",
        va="center",
        clip_on=False,
        **rot_kw,
    )
    t_hi = ax.text(
        *p_hi,
        high,
        transform=ax.transAxes,
        fontsize=fontsize,
        fontweight=weight,
        color=color,
        ha="right",
        va="center",
        clip_on=False,
        **rot_kw,
    )
    t_lb = ax.text(
        *p_lb,
        label,
        transform=ax.transAxes,
        fontsize=fontsize_label,
        fontweight=weight,
        color=color,
        ha="center",
        va="center",
        clip_on=False,
        **rot_kw,
    )

    # ── measure extents in axes fraction ─────────────────────
    ax.get_figure().canvas.draw()

    def _edges(t):
        bb = t.get_window_extent(renderer)
        return inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])

    i = 0 if direction == "x" else 1
    lo_end = _edges(t_lo)[1][i]
    hi_start = _edges(t_hi)[0][i]
    lb_lo = _edges(t_lb)[0][i]
    lb_hi = _edges(t_lb)[1][i]

    # ── draw arrows ──────────────────────────────────────────
    def _arrow(tip, tail):
        if direction == "x":
            ax.annotate(
                "",
                xy=(tip, offset),
                xytext=(tail, offset),
                xycoords="axes fraction",
                arrowprops=arrow_kw,
                annotation_clip=False,
            )
        else:
            ax.annotate(
                "",
                xy=(offset, tip),
                xytext=(offset, tail),
                xycoords="axes fraction",
                arrowprops=arrow_kw,
                annotation_clip=False,
            )

    _arrow(lo_end + pad, lb_lo - pad)
    _arrow(hi_start - pad, lb_hi + pad)
