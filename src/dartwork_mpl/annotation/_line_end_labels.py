"""Line-end names that replace a legend: the label_line_ends entry point."""

from __future__ import annotations

from typing import Any

import matplotlib as mpl
import numpy as np
from matplotlib.axes import Axes
from matplotlib.text import Text

from .._figure_geometry import spread_line_end_labels
from ._placement_geometry import _renderer_for_axes


def _last_point(line: Any) -> tuple[float, float] | None:
    """The last finite (x, y) of a line in drawing order, as data floats."""
    x = np.asarray(line.convert_xunits(line.get_xdata()), dtype=float)
    y = np.asarray(line.convert_yunits(line.get_ydata()), dtype=float)
    if x.size == 0 or x.shape != y.shape:
        return None
    finite = np.flatnonzero(np.isfinite(x) & np.isfinite(y))
    if finite.size == 0:
        return None
    i = finite[-1]
    return float(x[i]), float(y[i])


def label_line_ends(
    ax: Axes, lines: Any = None, *, gap_pt: float | None = None, **kw: Any
) -> list[Text]:
    """Name each line at its last point instead of a legend, in one style.

    One call for "label the line ends instead of a legend" / "범례 대신 선
    끝에 이름을", so every caller draws the same labels:

    - the line's label, left-aligned ``gap_pt`` (default the preset's
      ``axes.labelpad``) right of its last finite point, vertically centred;
    - the preset text size and weight;
    - the line's colour, darkened or lightened only as far as text needs to
      read on the axes background (:func:`dartwork_mpl.ensure_contrast`,
      4.5:1);
    - labels that would overlap move apart vertically, keeping their order.

    The axes' legend is removed and the axis limits stay;
    :func:`dartwork_mpl.simple_layout` makes room for the labels. ``lines``
    picks the lines (default: every visible line whose label does not start
    with ``_``). A ``fontsize=``, ``color=`` or other ``Text`` keyword wins::

        dm.label_line_ends(ax)
        dm.simple_layout(fig)

    Returns the labels in the order of ``lines``.
    """
    import matplotlib.colors as mcolors

    from .._colors.contrast import ensure_contrast

    if lines is None:
        lines = [
            ln
            for ln in ax.get_lines()
            if ln.get_visible() and not str(ln.get_label()).startswith("_")
        ]
    gap = float(mpl.rcParams["axes.labelpad"] if gap_pt is None else gap_pt)
    background = mcolors.to_rgba(ax.patch.get_facecolor())
    if not ax.patch.get_visible() or background[3] == 0:
        background = mcolors.to_rgba(ax.figure.get_facecolor())
    legend = ax.get_legend()
    if legend is not None:
        legend.remove()

    placed: list[tuple[Text, tuple[float, float]]] = []
    for line in lines:
        end = _last_point(line)
        if end is None:
            continue
        style: dict[str, Any] = {
            "color": ensure_contrast(line.get_color(), background),
            "ha": "left",
            "va": "center",
            "annotation_clip": False,
        }
        style.update(kw)
        label = ax.annotate(
            str(line.get_label()),
            xy=end,
            xycoords="data",
            xytext=(gap, 0.0),
            textcoords="offset points",
            **style,
        )
        placed.append((label, end))
    if len(placed) < 2:
        return [t for t, _ in placed]

    _fig, renderer = _renderer_for_axes(ax)
    spread_line_end_labels(
        ax, [t for t, _ in placed], [e for _, e in placed], gap, renderer
    )
    return [t for t, _ in placed]
