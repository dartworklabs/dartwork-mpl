"""A JSON-ready summary of what a figure shows (schema 1).

Only what the review loop reads: per Axes (insets nested under their parent)
the titles, axis labels, ranges, tick labels, series, legends and free text;
the figure's and each SubFigure's own titles, texts and legends; and every
text outside the canvas. Series values, masks, shapes and non-uniform colours
are a digest, not the values. Values are JSON-native (dict, list, str, int,
float, bool, None), floats are rounded to six significant digits for display
fields only and non-finite numbers become ``"nan"`` / ``"inf"`` / ``"-inf"``,
so a summary read back from ``<stem>.review.json`` compares equal to the one in
memory and a re-render of the same figure reports no difference. No path, time
or file name enters the summary. 3-D Axes are read from their 3-D data, not the
projection, so turning the view changes no series digest.
"""

from __future__ import annotations

import hashlib
import math
from typing import TYPE_CHECKING, Any

import matplotlib.colors as mcolors
import numpy as np
from matplotlib.collections import (
    Collection,
    LineCollection,
    PathCollection,
    PolyCollection,
    QuadMesh,
)
from matplotlib.container import BarContainer
from matplotlib.font_manager import weight_dict
from matplotlib.legend import Legend

from .._figure_geometry import BBOX_ERRORS, get_renderer

if TYPE_CHECKING:
    from matplotlib.axes._base import _AxesBase
    from matplotlib.axis import Axis
    from matplotlib.backend_bases import RendererBase
    from matplotlib.figure import Figure, SubFigure
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
    """Shape, mask and exact float bytes of ``array`` (repr if not numeric).

    Nothing is rounded: re-rendering the same data gives the same bits, and
    rounding would hide real edits to small values. Masked entries count by
    their mask only, so a value hidden behind the mask does not matter but a
    point that appears or disappears does.
    """
    try:
        masked = np.ma.asarray(array, dtype=float)  # type: ignore[no-untyped-call]
    except (TypeError, ValueError):
        objects = np.asarray(array, dtype=object)
        return repr((objects.shape, list(objects.ravel()))).encode()
    mask = np.ma.getmaskarray(masked)  # type: ignore[no-untyped-call]
    data = np.where(mask, 0.0, np.ma.getdata(masked))  # type: ignore[no-untyped-call]
    data = np.where(np.isnan(data), np.nan, data)
    return bytes(repr(masked.shape).encode() + mask.tobytes() + data.tobytes())


def _digest(*arrays: Any) -> str:
    """A short fingerprint of series values (shape, mask and values)."""
    h = hashlib.sha1()
    for array in arrays:
        h.update(_value_bytes(array))
    return h.hexdigest()[:12]


def _colors(rgba: Any) -> tuple[str | None, str | None]:
    """The colour when uniform; else the first colour and a digest of all."""
    array = np.asarray(rgba, dtype=float)
    if array.size == 0:
        return None, None
    rows = array.reshape(-1, array.shape[-1]) if array.ndim > 1 else array[None]
    first = _hex(rows[0])
    if len(rows) == 1 or bool(np.all(rows == rows[0])):
        return first, None
    return first, _digest(rows)


def _container_labels(ax: _AxesBase) -> dict[int, str]:
    """The legend name of every artist that belongs to a named container."""
    names: dict[int, str] = {}
    for container in ax.containers:
        label = str(container.get_label())
        if label.startswith("_") and isinstance(container, BarContainer):
            first = container.patches[0] if container.patches else None
            if first is not None and not str(first.get_label()).startswith("_"):
                label = str(first.get_label())
        if label.startswith("_"):
            continue
        stack: list[Any] = list(container)
        while stack:
            item = stack.pop()
            if item is None:
                continue
            if isinstance(item, (list, tuple)):
                stack.extend(item)
            else:
                names[id(item)] = label
    return names


def _label(artist: Any, names: dict[int, str]) -> str:
    own = str(artist.get_label())
    if own.startswith("_") and id(artist) in names:
        return names[id(artist)]
    return own


def _lines(ax: _AxesBase, names: dict[int, str]) -> list[dict[str, Any]]:
    out = []
    for line in ax.get_lines():
        if not line.get_visible():
            continue
        if hasattr(line, "get_data_3d"):
            data = _digest(*line.get_data_3d())
        else:
            data = _digest(
                line.convert_xunits(line.get_xdata()),  # type: ignore[no-untyped-call]
                line.convert_yunits(line.get_ydata()),  # type: ignore[no-untyped-call]
            )
        out.append(
            {
                "kind": "line",
                "label": _label(line, names),
                "n": len(
                    np.atleast_1d(np.asarray(line.get_xdata(), dtype=object))
                ),
                "color": _hex(line.get_color()),
                "width": _num(line.get_linewidth()),
                "style": str(line.get_linestyle()),
                "marker": str(line.get_marker()),
                "data": data,
            }
        )
    return out


def _bars(
    ax: _AxesBase, names: dict[int, str]
) -> tuple[list[dict[str, Any]], set[int]]:
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
        color, colors = _colors([p.get_facecolor() for p in patches])
        label = str(container.get_label())
        if label.startswith("_") and container.patches:
            label = _label(container.patches[0], names)
        out.append(
            {
                "kind": "bar",
                "label": label,
                "n": len(patches),
                "orientation": str(
                    getattr(container, "orientation", "vertical")
                ),
                "color": color,
                "colors": colors,
                "data": _digest(boxes),
            }
        )
    return out, seen


def _collections(ax: _AxesBase, names: dict[int, str]) -> list[dict[str, Any]]:
    three_d = ax.name == "3d"
    out = []
    for col in ax.collections:
        if not col.get_visible():
            continue
        entry: dict[str, Any]
        rgba: Any
        if isinstance(col, PathCollection):
            offsets3d = getattr(col, "_offsets3d", None) if three_d else None
            if offsets3d is not None:
                # mplot3d sorts sizes and colours by depth for drawing; read
                # them in data order so turning the view changes nothing.
                data = _digest(*offsets3d)
                sizes = getattr(col, "_sizes3d", col.get_sizes())
                rgba = Collection.get_facecolor(col)
            else:
                data = _digest(col.get_offsets())
                sizes = col.get_sizes()
                rgba = col.get_facecolor()
            entry = {
                "kind": "scatter",
                "n": len(np.asarray(col.get_offsets())),
                "data": data,
                "sizes": _digest(sizes),
            }
        elif isinstance(col, QuadMesh):
            values = col.get_array()
            mesh: Any = [] if values is None else values
            entry = {
                "kind": "image",
                "n": int(np.size(mesh)),
                "data": _digest(mesh, col.get_coordinates()),
            }
            rgba = []
        elif isinstance(col, (PolyCollection, LineCollection)):
            kind = "area" if isinstance(col, PolyCollection) else "lines"
            if three_d:
                # 3-D data, not the projection: segments for lines, vertices
                # for polygons.
                segments = getattr(col, "_segments3d", None)
                vec = getattr(col, "_vec", None)
                if segments is not None:
                    poly: str | None = (
                        _digest(*segments) if len(segments) else _digest([])
                    )
                else:
                    poly = _digest(vec) if vec is not None else None
            else:
                verts = [p.vertices for p in col.get_paths()]
                poly = _digest(*verts) if verts else _digest([])
            entry = {"kind": kind, "n": len(col.get_paths()), "data": poly}
            rgba = (
                col.get_facecolor() if kind == "area" else col.get_edgecolor()
            )
        else:
            entry = {
                "kind": "collection",
                "n": len(col.get_paths()),
                "data": None,
            }
            rgba = []
        entry["label"] = _label(col, names)
        entry["color"], entry["colors"] = _colors(rgba)
        out.append(entry)
    return out


def _images(ax: _AxesBase) -> list[dict[str, Any]]:
    out = []
    for image in ax.images:
        if not image.get_visible():
            continue
        values = image.get_array()
        array: Any = [] if values is None else values
        out.append(
            {
                "kind": "image",
                "label": str(image.get_label()),
                "n": int(np.size(array)),
                "color": None,
                "data": _digest(array),
            }
        )
    return out


def _series(ax: _AxesBase) -> list[dict[str, Any]]:
    names = _container_labels(ax)
    bars, in_bars = _bars(ax, names)
    loose = [p for p in ax.patches if p.get_visible() and id(p) not in in_bars]
    series = [*_lines(ax, names), *bars, *_collections(ax, names), *_images(ax)]
    if loose:
        color, colors = _colors([p.get_facecolor() for p in loose])
        series.append(
            {
                "kind": "patches",
                "label": "",
                "n": len(loose),
                "color": color,
                "colors": colors,
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


def _shown_ticklabels(axis: Axis, side: int = 1) -> list[Text]:
    """Tick labels matplotlib draws on one side (1: bottom/left, 2: top/right).

    Each major tick carries both sides' labels at its own location; only those
    inside the view, visible and not empty count.
    """
    low, high = sorted(float(v) for v in axis.get_view_interval())
    eps = 1e-9 * max(abs(high - low), 1e-300)
    shown = []
    for tick in axis.get_major_ticks(len(axis.get_majorticklocs())):
        label = tick.label1 if side == 1 else tick.label2
        if (
            low - eps <= float(tick.get_loc()) <= high + eps
            and label.get_visible()
            and label.get_text()
        ):
            shown.append(label)
    return shown


def _ticks(axis: Axis) -> dict[str, Any]:
    shown = _shown_ticklabels(axis)
    other = _shown_ticklabels(axis, side=2)
    out: dict[str, Any] = {
        "labels": [t.get_text() for t in shown],
        "size": _num(shown[0].get_fontsize()) if shown else None,
    }
    if other:
        out["labels2"] = [t.get_text() for t in other]
    return out


def _inside(inner: Any, outer: Any) -> bool:
    return bool(
        inner.x0 >= outer.x0 - 1
        and inner.y0 >= outer.y0 - 1
        and inner.x1 <= outer.x1 + 1
        and inner.y1 <= outer.y1 + 1
    )


def _legends(ax: _AxesBase) -> list[Legend]:
    """Every shown legend of ``ax``: the current one and any kept with add_artist.

    A hidden legend is left out here and in the canvas check alike, so hiding
    or showing one is a change.
    """
    found = [
        c
        for c in ax.get_children()
        if isinstance(c, Legend) and c.get_visible()
    ]
    return list(dict.fromkeys(found))


def _figure_legends(owner: Figure | SubFigure) -> list[Legend]:
    """The figure's or SubFigure's shown legends."""
    return [lg for lg in owner.legends if lg.get_visible()]


def _legend(
    legend: Legend, owner: Any, renderer: RendererBase
) -> dict[str, Any]:
    inside: bool | None = None
    if owner is not None:
        try:
            inside = _inside(
                legend.get_window_extent(renderer),
                owner.get_window_extent(renderer),
            )
        except BBOX_ERRORS:
            inside = None
    return {
        "title": legend.get_title().get_text(),
        "labels": [t.get_text() for t in legend.get_texts()],
        "ncols": int(getattr(legend, "_ncols", 1)),
        "inside": inside,
    }


def _title_artists(ax: _AxesBase) -> list[tuple[str, Text]]:
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


def _axis_names(ax: _AxesBase) -> tuple[str, ...]:
    return ("x", "y", "z") if ax.name == "3d" else ("x", "y")


def _axes(ax: _AxesBase, renderer: RendererBase) -> dict[str, Any]:
    out: dict[str, Any] = {
        "kind": ax.name,
        "position": [round(float(v), 3) for v in ax.get_position().bounds],
        "title": {loc: _text(t) for loc, t in _title_artists(ax)},
    }
    for name in _axis_names(ax):
        axis = getattr(ax, f"{name}axis")
        out[f"{name}label"] = _text(axis.label)
        out[f"{name}lim"] = [_num(v) for v in getattr(ax, f"get_{name}lim")()]
        out[f"{name}scale"] = str(getattr(ax, f"get_{name}scale")())
        out[f"{name}ticks"] = _ticks(axis)
    out["series"] = _series(ax)
    out["legends"] = [_legend(lg, ax, renderer) for lg in _legends(ax)]
    out["texts"] = [_text(t) for t in _axes_free_texts(ax)]
    out["insets"] = [_axes(child, renderer) for child in ax.child_axes]
    return out


_SUP_NAMES = ("_suptitle", "_supxlabel", "_supylabel")


def _free_texts(owner: Figure | SubFigure) -> list[Text]:
    """Visible ``owner.texts`` without the sup titles (they have own fields).

    The summary's ``texts[i]`` and the canvas check's ``texts[i]`` both index
    this list, so a path in ``outside_canvas`` names a summary entry.
    """
    sups = {id(getattr(owner, name, None)) for name in _SUP_NAMES}
    return [t for t in owner.texts if id(t) not in sups and t.get_visible()]


def _axes_free_texts(ax: _AxesBase) -> list[Text]:
    """Visible ``ax.texts``, indexed the same way as :func:`_free_texts`."""
    return [t for t in ax.texts if t.get_visible()]


def _sup(owner: Figure | SubFigure, name: str) -> dict[str, Any] | None:
    artist = getattr(owner, name, None)
    return _text(artist) if artist is not None else None


def _figure_texts(
    owner: Figure | SubFigure, renderer: RendererBase
) -> dict[str, Any]:
    """Titles, free text and legends that belong to the figure or a SubFigure."""
    return {
        "suptitle": _sup(owner, "_suptitle"),
        "supxlabel": _sup(owner, "_supxlabel"),
        "supylabel": _sup(owner, "_supylabel"),
        "texts": [_text(t) for t in _free_texts(owner)],
        "legends": [
            _legend(lg, None, renderer) for lg in _figure_legends(owner)
        ],
    }


def _subfigures(
    owner: Figure | SubFigure, renderer: RendererBase
) -> list[dict[str, Any]]:
    return [
        {**_figure_texts(sf, renderer), "subfigures": _subfigures(sf, renderer)}
        for sf in owner.subfigs
    ]


def _figure(fig: Figure, renderer: RendererBase) -> dict[str, Any]:
    width, height = fig.get_size_inches()
    return {
        "size_in": [_num(width), _num(height)],
        "dpi": _num(fig.dpi),
        **_figure_texts(fig, renderer),
        "subfigures": _subfigures(fig, renderer),
    }


def _owner_texts(
    owner: Figure | SubFigure, here: str
) -> list[tuple[str, Text]]:
    found: list[tuple[str, Text]] = []
    for name in _SUP_NAMES:
        artist = getattr(owner, name, None)
        if artist is not None:
            found.append((f"{here}.{name.lstrip('_')}", artist))
    found += [
        (f"{here}.texts[{i}]", t) for i, t in enumerate(_free_texts(owner))
    ]
    for i, legend in enumerate(_figure_legends(owner)):
        found.append((f"{here}.legends[{i}].title", legend.get_title()))
        found += [(f"{here}.legends[{i}]", t) for t in legend.get_texts()]
    for i, sf in enumerate(owner.subfigs):
        found += _owner_texts(sf, f"{here}.subfigures[{i}]")
    return found


def _axes_texts(ax: _AxesBase, here: str) -> list[tuple[str, Text]]:
    found: list[tuple[str, Text]] = []
    for loc, title in _title_artists(ax):
        found.append((f"{here}.title.{loc}", title))
    for name in _axis_names(ax):
        axis = getattr(ax, f"{name}axis")
        found.append((f"{here}.{name}label", axis.label))
        if ax.name != "3d":  # mplot3d tick labels sit at stale 2-D positions
            for side in (1, 2):
                found += [
                    (f"{here}.{name}ticks", t)
                    for t in _shown_ticklabels(axis, side=side)
                ]
    found += [
        (f"{here}.texts[{j}]", t) for j, t in enumerate(_axes_free_texts(ax))
    ]
    for j, legend in enumerate(_legends(ax)):
        found.append((f"{here}.legends[{j}].title", legend.get_title()))
        found += [(f"{here}.legends[{j}]", t) for t in legend.get_texts()]
    for j, child in enumerate(ax.child_axes):
        found += _axes_texts(child, f"{here}.insets[{j}]")
    return found


def _owned_texts(fig: Figure) -> list[tuple[str, Text]]:
    """Every visible, non-empty text with the summary path that owns it."""
    found = _owner_texts(fig, "figure")
    for i, ax in enumerate(fig.axes):
        found += _axes_texts(ax, f"axes[{i}]")
    seen: set[int] = set()
    out: list[tuple[str, Text]] = []
    for where, t in found:
        if (
            id(t) in seen
            or not t.get_visible()
            or not str(t.get_text()).strip()
        ):
            continue
        seen.add(id(t))
        out.append((where, t))
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
        "figure": _figure(fig, renderer),
        "axes": [_axes(ax, renderer) for ax in fig.axes],
        "outside_canvas": _outside(fig, renderer),
    }
