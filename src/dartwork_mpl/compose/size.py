"""``dm.figsize_for``: the canvas of the active preset.

The size slice decides a canvas from the page it is told; which presets are
active is the style slice's to say, and so is what a poster's font layer
declares.
"""

from __future__ import annotations

from dartwork_mpl import size
from dartwork_mpl.style import active_presets, load_style_dict

__all__ = ["figsize_for"]


def figsize_for(
    kind: str = "default",
    *,
    n_points: int | None = None,
    n_series: int | None = None,
    labels: object = None,
    dual_axis: bool = False,
    nrows: int = 1,
    ncols: int = 1,
) -> tuple[float, float]:
    """Return the active preset's canvas for a chart that names no size.

    The same arguments under the same preset always give the same canvas.
    ``kind``: ``"default"`` (lines, bars, scatter...), ``"grouped"`` (grouped
    bars), ``"barh"``, ``"compact"``, ``"matrix"`` (heatmaps), ``"dense"``,
    ``"strip"``, ``"slide"`` (under a slide title, 23.4 x 10.5 cm) or
    ``"full_slide"`` (the whole 16:9 slide). ``n_points`` (x positions) and
    ``n_series`` move the width between the preset's tiers; ``labels`` (the
    category names, in axis order) widens it until they stand flat;
    ``dual_axis`` marks a ``twinx``; ``nrows`` / ``ncols`` a panel grid (see
    :func:`grid_shape`). Raises ``ValueError`` for an unknown kind or a count
    below its minimum, ``TypeError`` for a count that is not an int or
    labels without an axis order (a string, set or mapping)::

        fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=len(years)))
    """
    return size.figsize_for(
        kind,
        n_points=n_points,
        n_series=n_series,
        labels=labels,
        dual_axis=dual_axis,
        nrows=nrows,
        ncols=ncols,
        presets=active_presets(),
        layer=load_style_dict,
    )
