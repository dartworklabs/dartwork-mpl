"""A JSON-ready summary of what a figure shows (schema 1).

Only what the review loop reads: per Axes the titles, axis labels, ranges,
tick labels, series, legend and free text, and every text outside the canvas.
Series values are a digest, not the values. Values are JSON-native (dict, list,
str, int, float, bool, None), floats are rounded to six significant digits and
non-finite numbers become ``"nan"`` / ``"inf"`` / ``"-inf"``, so a summary read
back from ``<stem>.review.json`` compares equal to the one in memory and a
re-render of the same figure reports no difference. No path, time or file
name enters the summary.
"""

from __future__ import annotations

import hashlib
import math
from typing import TYPE_CHECKING, Any

import matplotlib.colors as mcolors
import numpy as np
from matplotlib.collections import (
    LineCollection,
    PathCollection,
    PolyCollection,
    QuadMesh,
)
from matplotlib.container import BarContainer
from matplotlib.font_manager import weight_dict

from .._figure_geometry import BBOX_ERRORS, get_renderer

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.axis import Axis
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure
    from matplotlib.text import Text

__all__ = ["summarize"]

#: A text sticking out of the canvas by more than this many pixels is listed.
_OUTSIDE_TOL_PX = 0.5


def _num(value: Any) -> float | str:
    """A float rounded to six significant digits, or a token if not finite."""
    v = float(value)
    if math.isnan(v):
        return "nan"
    if math.isinf(v):
        return "inf" if v > 0 else "-inf"
    return float(f"{v:.6g}")


def _hex(color: Any) -> str | None:
    try:
        return str(mcolors.to_hex(color, keep_alpha=False))
    except (TypeError, ValueError):
        return None


def _weight(text: Text) -> int:
    weight = text.get_fontweight()
    if isinstance(weight, str):
        return int(weight_dict.get(weight, 400))
    return int(weight)


def _text(text: Text | None) -> dict[str, Any] | None:
    if text is None:
        return None
    return {
        "text": text.get_text(),
        "size": _num(text.get_fontsize()),
        "weight": _weight(text),
        "color": _hex(text.get_color()),
    }


def _value_bytes(array: Any) -> bytes:
    """Rounded float bytes of ``array``, or its repr when it is not numeric."""
    try:
        masked = np.ma.asarray(array, dtype=float)  # type: ignore[no-untyped-call]
        values = np.asarray(np.ma.filled(masked, np.nan)).ravel()  # type: ignore[no-untyped-call]
    except (TypeError, ValueError):
        return repr(list(np.asarray(array, dtype=object).ravel())).encode()
    return bytes(np.round(values, 10).tobytes())


def _digest(*arrays: Any) -> str:
    """A short, rounding-stable fingerprint of series values."""
    h = hashlib.sha1()
    for array in arrays:
        h.update(_value_bytes(array))
    return h.hexdigest()[:12]


def _first_color(colors: Any) -> str | None:
    array = np.asarray(colors)
    if array.size == 0:
        return None
    return _hex(
        array.reshape(-1, array.shape[-1])[0] if array.ndim > 1 else array
    )


def _lines(ax: Axes) -> list[dict[str, Any]]:
    out = []
    for line in ax.get_lines():
        if not line.get_visible():
            continue
        x = line.convert_xunits(line.get_xdata())  # type: ignore[no-untyped-call]
        y = line.convert_yunits(line.get_ydata())  # type: ignore[no-untyped-call]
        out.append(
            {
                "kind": "line",
                "label": str(line.get_label()),
                "n": len(
                    np.atleast_1d(np.asarray(line.get_xdata(), dtype=object))
                ),
                "color": _hex(line.get_color()),
                "width": _num(line.get_linewidth()),
                "style": str(line.get_linestyle()),
                "marker": str(line.get_marker()),
                "data": _digest(x, y),
            }
        )
    return out


def _bars(ax: Axes) -> tuple[list[dict[str, Any]], set[int]]:
    out = []
    seen: set[int] = set()
    for container in ax.containers:
        if not isinstance(container, BarContainer):
            continue
        patches = [p for p in container.patches if p.get_visible()]
        seen.update(id(p) for p in container.patches)
        boxes = [
            (p.get_x(), p.get_y(), p.get_width(), p.get_height())
            for p in patches
        ]
        out.append(
            {
                "kind": "bar",
                "label": str(container.get_label()),
                "n": len(patches),
                "orientation": str(
                    getattr(container, "orientation", "vertical")
                ),
                "color": _hex(patches[0].get_facecolor()) if patches else None,
                "data": _digest(boxes),
            }
        )
    return out, seen


def _collections(ax: Axes) -> list[dict[str, Any]]:
    out = []
    for col in ax.collections:
        if not col.get_visible():
            continue
        if isinstance(col, PathCollection):
            offsets = np.asarray(col.get_offsets())
            entry = {
                "kind": "scatter",
                "n": len(offsets),
                "data": _digest(offsets),
            }
            color = _first_color(col.get_facecolor())
        elif isinstance(col, QuadMesh):
            values = col.get_array()
            mesh: Any = [] if values is None else values
            entry = {
                "kind": "image",
                "n": int(np.size(mesh)),
                "data": _digest(mesh),
            }
            color = None
        elif isinstance(col, (PolyCollection, LineCollection)):
            kind = "area" if isinstance(col, PolyCollection) else "lines"
            paths = col.get_paths()
            verts = [p.vertices for p in paths]
            entry = {
                "kind": kind,
                "n": len(paths),
                "data": _digest(*verts) if verts else _digest([]),
            }
            color = _first_color(
                col.get_facecolor() if kind == "area" else col.get_edgecolor()
            )
        else:
            entry = {
                "kind": "collection",
                "n": len(col.get_paths()),
                "data": None,
            }
            color = None
        entry["label"] = str(col.get_label())
        entry["color"] = color
        out.append(entry)
    return out


def _images(ax: Axes) -> list[dict[str, Any]]:
    out = []
    for image in ax.images:
        if not image.get_visible():
            continue
        values = image.get_array()
        out.append(
            {
                "kind": "image",
                "label": str(image.get_label()),
                "n": int(np.size(values)) if values is not None else 0,
                "color": None,
                "data": _digest(values if values is not None else []),
            }
        )
    return out


def _series(ax: Axes) -> list[dict[str, Any]]:
    bars, in_bars = _bars(ax)
    loose = [p for p in ax.patches if p.get_visible() and id(p) not in in_bars]
    series = [*_lines(ax), *bars, *_collections(ax), *_images(ax)]
    if loose:
        series.append(
            {
                "kind": "patches",
                "label": "",
                "n": len(loose),
                "color": _hex(loose[0].get_facecolor()),
                "data": _digest(
                    *(
                        p.get_path()
                        .transformed(p.get_patch_transform())
                        .vertices
                        for p in loose
                    )
                ),
            }
        )
    return series


def _shown_ticklabels(axis: Axis) -> list[Text]:
    """Major tick labels matplotlib draws: inside the view, visible, not empty."""
    low, high = sorted(float(v) for v in axis.get_view_interval())
    eps = 1e-9 * max(abs(high - low), 1e-300)
    labels = axis.get_majorticklabels()
    locs = axis.get_majorticklocs()
    return [
        label
        for label, loc in zip(labels, locs, strict=False)
        if low - eps <= float(loc) <= high + eps
        and label.get_visible()
        and label.get_text()
    ]


def _ticks(axis: Axis) -> dict[str, Any]:
    shown = _shown_ticklabels(axis)
    return {
        "labels": [t.get_text() for t in shown],
        "size": _num(shown[0].get_fontsize()) if shown else None,
    }


def _inside(inner: Any, outer: Any) -> bool:
    return bool(
        inner.x0 >= outer.x0 - 1
        and inner.y0 >= outer.y0 - 1
        and inner.x1 <= outer.x1 + 1
        and inner.y1 <= outer.y1 + 1
    )


def _legend(ax: Axes, renderer: RendererBase) -> dict[str, Any] | None:
    legend = ax.get_legend()
    if legend is None:
        return None
    try:
        inside = _inside(
            legend.get_window_extent(renderer), ax.get_window_extent(renderer)
        )
    except BBOX_ERRORS:
        inside = None
    return {
        "labels": [t.get_text() for t in legend.get_texts()],
        "ncols": int(getattr(legend, "_ncols", 1)),
        "inside": inside,
    }


def _titles(ax: Axes) -> dict[str, Any]:
    return {
        "left": _text(getattr(ax, "_left_title", None)),
        "center": _text(ax.title),
        "right": _text(getattr(ax, "_right_title", None)),
    }


def _axes(ax: Axes, renderer: RendererBase) -> dict[str, Any]:
    return {
        "kind": ax.name,
        "position": [round(float(v), 3) for v in ax.get_position().bounds],
        "title": _titles(ax),
        "xlabel": _text(ax.xaxis.label),
        "ylabel": _text(ax.yaxis.label),
        "xlim": [_num(v) for v in ax.get_xlim()],
        "ylim": [_num(v) for v in ax.get_ylim()],
        "xscale": str(ax.get_xscale()),
        "yscale": str(ax.get_yscale()),
        "xticks": _ticks(ax.xaxis),
        "yticks": _ticks(ax.yaxis),
        "series": _series(ax),
        "legend": _legend(ax, renderer),
        "texts": [_text(t) for t in ax.texts if t.get_visible()],
    }


def _figure(fig: Figure) -> dict[str, Any]:
    width, height = fig.get_size_inches()
    suptitle = getattr(fig, "_suptitle", None)
    return {
        "size_in": [_num(width), _num(height)],
        "dpi": _num(fig.dpi),
        "suptitle": _text(suptitle) if suptitle is not None else None,
        "texts": [_text(t) for t in fig.texts if t.get_visible()],
        "legends": [
            [t.get_text() for t in lg.get_texts()] for lg in fig.legends
        ],
    }


def _owned_texts(fig: Figure) -> list[tuple[str, Text]]:
    """Every visible, non-empty text with the summary path that owns it."""
    found: list[tuple[str, Text]] = []
    for name in ("_suptitle", "_supxlabel", "_supylabel"):
        artist = getattr(fig, name, None)
        if artist is not None:
            found.append((f"figure.{name.lstrip('_')}", artist))
    found += [(f"figure.texts[{i}]", t) for i, t in enumerate(fig.texts)]
    for i, fig_legend in enumerate(fig.legends):
        found += [(f"figure.legends[{i}]", t) for t in fig_legend.get_texts()]
    for i, ax in enumerate(fig.axes):
        here = f"axes[{i}]"
        for loc, title in _titles_artists(ax):
            found.append((f"{here}.title.{loc}", title))
        found.append((f"{here}.xlabel", ax.xaxis.label))
        found.append((f"{here}.ylabel", ax.yaxis.label))
        found += [(f"{here}.xticks", t) for t in _shown_ticklabels(ax.xaxis)]
        found += [(f"{here}.yticks", t) for t in _shown_ticklabels(ax.yaxis)]
        found += [(f"{here}.texts[{j}]", t) for j, t in enumerate(ax.texts)]
        legend = ax.get_legend()
        if legend is not None:
            found += [(f"{here}.legend", t) for t in legend.get_texts()]
    return [
        (where, t)
        for where, t in found
        if t.get_visible() and str(t.get_text()).strip()
    ]


def _titles_artists(ax: Axes) -> list[tuple[str, Text]]:
    out = []
    for loc, name in (
        ("left", "_left_title"),
        ("center", "title"),
        ("right", "_right_title"),
    ):
        title = getattr(ax, name, None)
        if title is not None:
            out.append((loc, title))
    return out


def _outside(fig: Figure, renderer: RendererBase) -> list[dict[str, Any]]:
    canvas = fig.bbox
    out = []
    for where, text in _owned_texts(fig):
        try:
            box = text.get_window_extent(renderer)
        except BBOX_ERRORS:
            continue
        beyond = {
            "left": max(0.0, canvas.x0 - box.x0),
            "bottom": max(0.0, canvas.y0 - box.y0),
            "right": max(0.0, box.x1 - canvas.x1),
            "top": max(0.0, box.y1 - canvas.y1),
        }
        if max(beyond.values()) > _OUTSIDE_TOL_PX:
            out.append(
                {
                    "where": where,
                    "text": str(text.get_text()),
                    "beyond_px": {
                        k: round(float(v), 1) for k, v in beyond.items()
                    },
                }
            )
    return out


def summarize(fig: Figure) -> dict[str, Any]:
    """The figure summary the review reports and compares (schema 1)."""
    fig.canvas.draw()
    renderer = get_renderer(fig)
    return {
        "figure": _figure(fig),
        "axes": [_axes(ax, renderer) for ax in fig.axes],
        "outside_canvas": _outside(fig, renderer),
    }
