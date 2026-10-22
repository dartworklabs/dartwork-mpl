"""Re-run one ``plot.py`` and dump a geometry/data snapshot of its figure.

Runs inside the case's own venv, in a fresh process::

    .venv/bin/python -I probe.py SCRIPT OUT_JSON

It records every ``Figure.savefig`` call, snapshots the figure saved as
``figure.png`` (else the last PNG, else ``plt.gcf()``) right after it is
saved, and writes JSON. The measurements use matplotlib geometry only;
``dartwork_mpl.validate_figure`` is called once and stored as an advisory
input, never as the defect source. Self-contained: standard library,
numpy and matplotlib only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import runpy
import sys
import traceback
import warnings
from collections import Counter
from itertools import pairwise
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors as mcolors
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import (
    LineCollection,
    PathCollection,
    PolyCollection,
    QuadMesh,
)
from matplotlib.container import BarContainer, ErrorbarContainer
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
from matplotlib.legend import Legend
from matplotlib.patches import PathPatch, Polygon, Rectangle
from matplotlib.text import Text

MAX_POINTS = 4000
CALLS: Counter[str] = Counter()
STYLES: list[str] = []
SAVES: list[dict] = []
STATE: dict = {"snapshot": None, "last_png_fig": None}


# --------------------------------------------------------------- helpers
def _hex(c) -> str | None:
    try:
        return mcolors.to_hex(c, keep_alpha=False)
    except (ValueError, TypeError):
        return None


def _floats(a) -> list:
    arr = np.ma.filled(np.ma.asarray(a, dtype=float), np.nan).ravel()
    return [None if not math.isfinite(v) else round(float(v), 6) for v in arr]


def _digest(values: list) -> str:
    """Order- and NaN-mask-preserving digest of a value list (None = NaN)."""
    txt = ",".join(
        "nan" if v is None or not math.isfinite(v) else f"{v:.6g}"
        for v in values
    )
    return hashlib.sha1(txt.encode()).hexdigest()[:12]


def _png_px(path: str | None) -> list[int] | None:
    try:
        with open(path, "rb") as f:
            head = f.read(24)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return [
            int.from_bytes(head[16:20], "big"),
            int.from_bytes(head[20:24], "big"),
        ]
    except (OSError, TypeError):
        return None


def _rect_clip(poly: np.ndarray, x0, y0, x1, y1) -> np.ndarray:
    """Sutherland-Hodgman clip of a polygon (N,2) against an axis box."""
    pts = [tuple(p) for p in poly]
    for axis, bound, keep_ge in (
        (0, x0, True),
        (0, x1, False),
        (1, y0, True),
        (1, y1, False),
    ):
        out = []
        n = len(pts)
        for i in range(n):
            cur, prev = pts[i], pts[i - 1]
            cin = cur[axis] >= bound if keep_ge else cur[axis] <= bound
            pin = prev[axis] >= bound if keep_ge else prev[axis] <= bound
            if cin != pin:
                d = cur[axis] - prev[axis]
                t = (bound - prev[axis]) / d if d else 0.0
                out.append(
                    (
                        prev[0] + t * (cur[0] - prev[0]),
                        prev[1] + t * (cur[1] - prev[1]),
                    )
                )
            if cin:
                out.append(cur)
        pts = out
        if not pts:
            break
    return np.asarray(pts, dtype=float).reshape(-1, 2)


def _area(poly: np.ndarray) -> float:
    if len(poly) < 3:
        return 0.0
    x, y = poly[:, 0], poly[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def _text_quad(t: Text, renderer) -> np.ndarray:
    """Rotated rectangle of a text in display px (AABB center + unrotated size)."""
    bb = t.get_window_extent(renderer)
    rot = float(t.get_rotation()) % 360
    if min(rot % 90, 90 - rot % 90) < 0.5:
        return np.array(
            [[bb.x0, bb.y0], [bb.x1, bb.y0], [bb.x1, bb.y1], [bb.x0, bb.y1]]
        )
    t.set_rotation(0)
    flat = t.get_window_extent(renderer)
    t.set_rotation(rot)
    w, h = flat.width, flat.height
    cx, cy = (bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2
    th = math.radians(rot)
    c, s = math.cos(th), math.sin(th)
    corners = [
        (-w / 2, -h / 2),
        (w / 2, -h / 2),
        (w / 2, h / 2),
        (-w / 2, h / 2),
    ]
    return np.array(
        [[cx + c * x - s * y, cy + s * x + c * y] for x, y in corners]
    )


# --------------------------------------------------------------- patches
def _patch_legend() -> None:
    """Remember which original artist each legend entry stands for.

    Legends draw proxy handles, so the handle -> label pairs are captured
    when the legend is built; series identity then does not depend on
    ``label=`` (e.g. ``ax.legend(handles, labels)`` with ``_nolegend_`` lines).
    """
    if getattr(Legend.__init__, "_eval_wrapped", False):
        return
    orig_init = Legend.__init__

    def init(self, parent, handles, labels, *args, **kwargs):
        orig_init(self, parent, handles, labels, *args, **kwargs)
        self._eval_pairs = [
            (h, str(lab)) for h, lab in zip(handles, labels, strict=False)
        ]

    init._eval_wrapped = True
    Legend.__init__ = init


_patch_legend()


def _legend_names(fig: Figure) -> dict[int, list[str]]:
    """id(original artist or container) -> legend texts naming it (visible legends only)."""
    out: dict[int, list[str]] = {}
    legends = [ax.get_legend() for ax in fig.get_axes()] + list(fig.legends)
    for lg in legends:
        if lg is None or not lg.get_visible():
            continue
        for handle, label in getattr(lg, "_eval_pairs", []):
            targets = [handle]
            if isinstance(handle, ErrorbarContainer) and handle.lines:
                targets.append(handle.lines[0])
            for t in targets:
                out.setdefault(id(t), []).append(label)
    return out


def _install_patches(use_dm: bool) -> None:
    orig_savefig = Figure.savefig

    def savefig(self, fname, *args, **kwargs):
        result = orig_savefig(self, fname, *args, **kwargs)
        path = (
            os.fspath(fname) if isinstance(fname, (str, os.PathLike)) else None
        )
        fmt = kwargs.get("format") or (
            Path(path).suffix.lstrip(".").lower() if path else None
        )
        bbox = kwargs.get("bbox_inches", matplotlib.rcParams["savefig.bbox"])
        dpi = kwargs.get("dpi", matplotlib.rcParams["savefig.dpi"])
        dpi = self.dpi if dpi in (None, "figure") else float(dpi)
        rec = {
            "path": path,
            "abspath": os.path.abspath(path) if path else None,
            "format": fmt,
            "bbox_inches": None if bbox is None else str(bbox),
            "dpi": dpi,
            "png_px": _png_px(path) if fmt == "png" else None,
        }
        SAVES.append(rec)
        if fmt == "png":
            STATE["last_png_fig"] = self
            if path and Path(path).name == "figure.png":
                try:
                    STATE["snapshot"] = snapshot(self, rec)
                except Exception:  # noqa: BLE001 - never break the script under test
                    STATE["snapshot_error"] = traceback.format_exc(limit=6)[
                        -3000:
                    ]
        return result

    Figure.savefig = savefig
    plt.show = lambda *a, **k: CALLS.update(["plt.show"])

    orig_tl = Figure.tight_layout

    def tight_layout(self, *a, **k):
        CALLS.update(["tight_layout"])
        return orig_tl(self, *a, **k)

    Figure.tight_layout = tight_layout
    if not use_dm:
        return
    import dartwork_mpl as dm

    for name in ("simple_layout", "save_formats", "figsize", "fs", "lw", "fw"):
        orig = getattr(dm, name, None)
        if orig is None:
            continue

        def wrap(*a, _orig=orig, _name=name, **k):
            CALLS.update([f"dm.{_name}"])
            return _orig(*a, **k)

        setattr(dm, name, wrap)
    style_cls = type(dm.style)
    orig_use = style_cls.use

    def use(self, preset_name, *a, **k):
        names = (
            [preset_name] if isinstance(preset_name, str) else list(preset_name)
        )
        STYLES.extend(str(n) for n in names)
        return orig_use(self, preset_name, *a, **k)

    style_cls.use = use


# --------------------------------------------------------------- snapshot
def _roles(fig: Figure, axes: list) -> dict[int, tuple[str, int | None]]:
    roles: dict[int, tuple[str, int | None]] = {}
    for name, attr in (
        ("suptitle", "_suptitle"),
        ("supxlabel", "_supxlabel"),
        ("supylabel", "_supylabel"),
    ):
        t = getattr(fig, attr, None)
        if t is not None:
            roles[id(t)] = (name, None)
    for t in fig.texts:
        roles.setdefault(id(t), ("figtext", None))
    for lg in fig.legends:
        for t in lg.get_texts():
            roles[id(t)] = ("legend", None)
        roles[id(lg.get_title())] = ("legend_title", None)
    for i, ax in enumerate(axes):
        for role, t in (
            ("title", ax.title),
            ("title_left", ax._left_title),
            ("title_right", ax._right_title),
            ("xlabel", ax.xaxis.label),
            ("ylabel", ax.yaxis.label),
            ("offset", ax.xaxis.offsetText),
            ("offset", ax.yaxis.offsetText),
        ):
            roles[id(t)] = (role, i)
        for axis, role in ((ax.xaxis, "xtick"), (ax.yaxis, "ytick")):
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                roles[id(tick.label1)] = (role, i)
                roles[id(tick.label2)] = (role, i)
        for t in ax.texts:
            roles[id(t)] = ("annotation" if hasattr(t, "xyann") else "text", i)
        lg = ax.get_legend()
        if lg is not None:
            for t in lg.get_texts():
                roles[id(t)] = ("legend", i)
            roles[id(lg.get_title())] = ("legend_title", i)
    return roles


def _segments_inside(xy: np.ndarray, box) -> int:
    x0, y0, x1, y1 = box
    n = 0
    for a, b in pairwise(xy):
        if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
            continue
        steps = max(2, int(math.hypot(*(b - a)) / 1.5))
        t = np.linspace(0, 1, steps)[:, None]
        pts = a + t * (b - a)
        n += int(
            np.sum(
                (pts[:, 0] > x0)
                & (pts[:, 0] < x1)
                & (pts[:, 1] > y0)
                & (pts[:, 1] < y1)
            )
        )
    return n


def _legend_cover(lg: Legend, axes: list, renderer) -> dict:
    bb = lg.get_window_extent(renderer)
    box = (bb.x0 + 1, bb.y0 + 1, bb.x1 - 1, bb.y1 - 1)
    larea = max(bb.width * bb.height, 1.0)
    out = {"line_px": 0, "points": 0, "bar_frac": 0.0, "poly_frac": 0.0}
    for ax in axes:
        if not bb.overlaps(ax.bbox):
            continue
        for ln in ax.get_lines():
            if not ln.get_visible() or not ln.get_transform().contains_branch(
                ax.transData
            ):
                continue
            xy = ln.get_transform().transform(ln.get_xydata())
            if ln.get_linestyle() not in ("None", "none", " ", ""):
                out["line_px"] += _segments_inside(xy, box)
            if ln.get_marker() not in (None, "None", "none", "", " "):
                inside = (
                    (xy[:, 0] > box[0])
                    & (xy[:, 0] < box[2])
                    & (xy[:, 1] > box[1])
                    & (xy[:, 1] < box[3])
                )
                out["points"] += int(np.sum(inside))
        for coll in ax.collections:
            if not coll.get_visible():
                continue
            if isinstance(coll, PathCollection):
                xy = coll.get_offset_transform().transform(
                    np.ma.filled(coll.get_offsets(), np.nan)
                )
                inside = (
                    (xy[:, 0] > box[0])
                    & (xy[:, 0] < box[2])
                    & (xy[:, 1] > box[1])
                    & (xy[:, 1] < box[3])
                )
                out["points"] += int(np.sum(inside))
            elif isinstance(coll, PolyCollection) and not isinstance(
                coll, QuadMesh
            ):
                tr = coll.get_transform()
                for p in coll.get_paths():
                    poly = tr.transform(p.vertices)
                    out["poly_frac"] += _area(_rect_clip(poly, *box)) / larea
        for patch in ax.patches:
            if (
                isinstance(patch, Rectangle)
                and patch.get_visible()
                and patch.get_transform().contains_branch(ax.transData)
            ):
                e = patch.get_window_extent(renderer)
                w = max(0.0, min(e.x1, box[2]) - max(e.x0, box[0]))
                h = max(0.0, min(e.y1, box[3]) - max(e.y0, box[1]))
                out["bar_frac"] += w * h / larea
    out["bar_frac"] = round(out["bar_frac"], 4)
    out["poly_frac"] = round(out["poly_frac"], 4)
    return out


def _legend_info(lg: Legend, fig_bb, renderer, axes) -> dict:
    bb = lg.get_window_extent(renderer)
    return {
        "bbox": [
            round(bb.x0 / fig_bb.width, 4),
            round(bb.y0 / fig_bb.height, 4),
            round(bb.x1 / fig_bb.width, 4),
            round(bb.y1 / fig_bb.height, 4),
        ],
        "loc": str(getattr(lg, "_loc", None)),
        "texts": [t.get_text() for t in lg.get_texts()],
        "fontsize": round(lg.get_texts()[0].get_fontsize(), 3)
        if lg.get_texts()
        else None,
        "cover": _legend_cover(lg, axes, renderer),
    }


def _fig_xy(ax, xy) -> list:
    """Data coords (N,2) -> figure-fraction coords, rounded."""
    fb = ax.figure.bbox
    d = ax.transData.transform(np.asarray(xy, dtype=float).reshape(-1, 2))
    return [[round(x / fb.width, 4), round(y / fb.height, 4)] for x, y in d]


def _ticks(axis, lo: float, hi: float) -> list:
    """Visible major ticks inside the view interval as [loc, text]."""
    lo, hi = min(lo, hi), max(lo, hi)
    pad = (hi - lo) * 1e-6
    out = []
    for tick in axis.get_major_ticks():
        loc = tick.get_loc()
        text = tick.label1.get_text() if tick.label1.get_visible() else ""
        text = text or (
            tick.label2.get_text() if tick.label2.get_visible() else ""
        )
        if text and loc is not None and lo - pad <= loc <= hi + pad:
            out.append([round(float(loc), 6), text])
    return out


def _alpha(artist, color=None) -> float:
    """Artist alpha times the colour's own alpha (1.0 when unset)."""
    a = artist.get_alpha()
    a = 1.0 if a is None else float(a)
    if color is not None:
        try:
            rgba = mcolors.to_rgba_array(color)
            a *= float(rgba[:, 3].max()) if len(rgba) else 0.0
        except (ValueError, TypeError):
            pass
    return round(a, 4)


def _none_style(v) -> bool:
    return v in (None, "None", "none", "", " ")


def _line_visible(ln) -> bool:
    if not ln.get_visible() or _alpha(ln, ln.get_color()) <= 0:
        return False
    stroke = not _none_style(ln.get_linestyle()) and ln.get_linewidth() > 0
    marks = not _none_style(ln.get_marker()) and ln.get_markersize() > 0
    return bool(stroke or marks)


def _patch_visible(p) -> bool:
    if not p.get_visible():
        return False
    face = _alpha(p, p.get_facecolor()) > 0 and p.get_fill()
    edge = _alpha(p, p.get_edgecolor()) > 0 and p.get_linewidth() > 0
    return bool(face or edge)


def _coll_visible(c) -> bool:
    if not c.get_visible():
        return False
    sizes = c.get_sizes() if hasattr(c, "get_sizes") else [1]
    if len(sizes) and float(np.max(sizes)) <= 0:
        return False
    face = _alpha(c, c.get_facecolor()) > 0
    lws = c.get_linewidth()
    edge = (
        _alpha(c, c.get_edgecolor()) > 0 and len(lws) and float(np.max(lws)) > 0
    )
    return bool(face or edge)


def _seg(x0, y0, x1, y1) -> tuple[str, list] | None:
    if abs(y0 - y1) < 1e-9 and x0 != x1:
        return "h", [
            round(float(min(x0, x1)), 6),
            round(float(max(x0, x1)), 6),
            round(float(y0), 6),
        ]
    if abs(x0 - x1) < 1e-9 and y0 != y1:
        return "v", [
            round(float(x0), 6),
            round(float(min(y0, y1)), 6),
            round(float(max(y0, y1)), 6),
        ]
    return None


def _axes_data(ax, i: int, renderer, names: dict[int, list[str]]) -> dict:
    inv = ax.transData.inverted()
    fig_bb = ax.figure.bbox
    d: dict = {
        "index": i,
        "lines": [],
        "bars": [],
        "scatter": [],
        "polys": [],
        "paths": [],
        "hsegs": [],
        "vsegs": [],
        "images": [],
        "spans": [],
        "rects": 0,
        "xticks": _ticks(ax.xaxis, *ax.get_xlim()),
        "yticks": _ticks(ax.yaxis, *ax.get_ylim()),
    }
    parts: dict[int, str] = {}
    for c in ax.containers:
        if isinstance(c, ErrorbarContainer):
            data_line, caps, _ = c.lines
            if data_line is not None:
                parts[id(data_line)] = "errorbar_data"
            for cap in caps:
                parts[id(cap)] = "errorbar_cap"
    for ln in ax.get_lines():
        xy = ln.get_xydata()[:MAX_POINTS]
        ok = np.all(np.isfinite(xy), axis=1)
        end = None
        if ok.any():
            ex, ey = ln.get_transform().transform(xy[ok][-1])
            end = [round(ex / fig_bb.width, 4), round(ey / fig_bb.height, 4)]
        rec = {
            "label": ln.get_label(),
            "legend": names.get(id(ln), []),
            "x": _floats(xy[:, 0]),
            "y": _floats(xy[:, 1]),
            "color": _hex(ln.get_color()),
            "alpha": _alpha(ln, ln.get_color()),
            "lw": round(float(ln.get_linewidth()), 3),
            "ls": str(ln.get_linestyle()),
            "marker": str(ln.get_marker()),
            "ms": round(float(ln.get_markersize()), 3),
            "visible": _line_visible(ln),
            "zorder": ln.get_zorder(),
            "data": bool(ln.get_transform().contains_branch(ax.transData)),
            "part": parts.get(id(ln)),
            "end": end,
        }
        d["lines"].append(rec)
        if len(xy) == 2 and np.all(np.isfinite(xy)) and rec["data"]:
            seg = _seg(*xy[0], *xy[1])
            if seg:
                d["hsegs" if seg[0] == "h" else "vsegs"].append(seg[1])
    in_bars = set()
    for c in ax.containers:
        if isinstance(c, BarContainer):
            rects = list(c.patches)
            in_bars.update(id(r) for r in rects)
            horiz = c.orientation == "horizontal"
            exts = []
            for r in rects:
                e = r.get_window_extent(renderer)
                exts.append(
                    [
                        round(e.x0 / fig_bb.width, 4),
                        round(e.y0 / fig_bb.height, 4),
                        round(e.x1 / fig_bb.width, 4),
                        round(e.y1 / fig_bb.height, 4),
                    ]
                )
            label = c.get_label()
            if (not label or label.startswith("_")) and rects:
                label = rects[0].get_label()  # ax.hist labels the first patch
            legend = names.get(id(c), []) + (
                names.get(id(rects[0]), []) if rects else []
            )
            d["bars"].append(
                {
                    "label": label,
                    "legend": legend,
                    "orientation": "h" if horiz else "v",
                    "values": _floats(
                        [
                            r.get_width() if horiz else r.get_height()
                            for r in rects
                        ]
                    ),
                    "pos": _floats(
                        [
                            r.get_y() + r.get_height() / 2
                            if horiz
                            else r.get_x() + r.get_width() / 2
                            for r in rects
                        ]
                    ),
                    "base": _floats(
                        [r.get_x() if horiz else r.get_y() for r in rects]
                    ),
                    "widths": _floats(
                        [
                            r.get_height() if horiz else r.get_width()
                            for r in rects
                        ]
                    ),
                    "edge0": _floats(
                        [r.get_y() if horiz else r.get_x() for r in rects]
                    ),
                    "colors": [_hex(r.get_facecolor()) for r in rects],
                    "alpha": _alpha(rects[0], rects[0].get_facecolor())
                    if rects
                    else 0.0,
                    "vis": [_patch_visible(r) for r in rects],
                    "visible": any(_patch_visible(r) for r in rects),
                    "ext": exts,
                }
            )
    ax_bb = ax.bbox
    for patch in ax.patches:
        if id(patch) in in_bars or not patch.get_visible():
            continue
        if isinstance(patch, PathPatch) or (
            isinstance(patch, Polygon)
            and patch.get_transform().contains_branch(ax.transData)
        ):
            v = inv.transform(
                patch.get_transform().transform(patch.get_path().vertices)
            )
            v = v[np.all(np.isfinite(v), axis=1)]
            if len(v):
                d["paths"].append(
                    {
                        "bbox": [
                            round(float(v[:, 0].min()), 6),
                            round(float(v[:, 1].min()), 6),
                            round(float(v[:, 0].max()), 6),
                            round(float(v[:, 1].max()), 6),
                        ],
                        "visible": _patch_visible(patch),
                    }
                )
        if not isinstance(patch, (Rectangle, Polygon)):
            continue
        e = patch.get_window_extent(renderer)
        if (
            ax_bb.height
            and (min(e.y1, ax_bb.y1) - max(e.y0, ax_bb.y0))
            >= 0.9 * ax_bb.height
        ):
            (x0, _), (x1, _) = inv.transform([[e.x0, e.y0], [e.x1, e.y1]])
            d["spans"].append([round(float(x0), 4), round(float(x1), 4)])
        elif patch.get_transform().contains_branch(ax.transData):
            d["rects"] += 1
    for coll in ax.collections:
        if isinstance(coll, PathCollection):
            disp = coll.get_offset_transform().transform(
                np.ma.filled(coll.get_offsets(), np.nan)
            )
            xy = inv.transform(disp)[:MAX_POINTS]
            fc = coll.get_facecolor()
            d["scatter"].append(
                {
                    "label": coll.get_label(),
                    "legend": names.get(id(coll), []),
                    "x": _floats(xy[:, 0]),
                    "y": _floats(xy[:, 1]),
                    "colors": sorted({_hex(c) for c in fc})[:20]
                    if len(fc)
                    else [],
                    "alpha": _alpha(coll, fc if len(fc) else None),
                    "visible": _coll_visible(coll),
                }
            )
        elif isinstance(coll, QuadMesh):
            arr = coll.get_array()
            if arr is not None:
                coords = np.asarray(coll.get_coordinates(), dtype=float)
                centers = (coords[:-1, :-1] + coords[1:, 1:]) / 2
                d["images"].append(_image(ax, np.ma.asarray(arr), centers))
        elif isinstance(coll, LineCollection):
            for seg in coll.get_segments()[:2000]:
                seg = inv.transform(
                    coll.get_transform().transform(np.asarray(seg, dtype=float))
                )
                if len(seg) == 2 and np.all(np.isfinite(seg)):
                    found = _seg(*seg[0], *seg[1])
                    if found:
                        d["hsegs" if found[0] == "h" else "vsegs"].append(
                            found[1]
                        )
        elif isinstance(coll, PolyCollection):
            xs, ys = [], []
            for p in coll.get_paths():
                v = inv.transform(coll.get_transform().transform(p.vertices))
                xs.extend(v[:, 0])
                ys.extend(v[:, 1])
            d["polys"].append(
                {
                    "label": coll.get_label(),
                    "legend": names.get(id(coll), []),
                    "x": _floats(xs[:MAX_POINTS]),
                    "y": _floats(ys[:MAX_POINTS]),
                    "color": _hex(coll.get_facecolor()[0])
                    if len(coll.get_facecolor())
                    else None,
                    "visible": _coll_visible(coll),
                }
            )
    for im in ax.images:
        if isinstance(im, AxesImage) and im.get_array() is not None:
            arr = np.ma.asarray(im.get_array())
            if arr.ndim != 2:
                continue
            n, m = arr.shape
            left, right, bottom, top = im.get_extent()
            xs = left + (np.arange(m) + 0.5) * (right - left) / m
            first, last = (
                (top, bottom) if im.origin == "upper" else (bottom, top)
            )
            ys = first + (np.arange(n) + 0.5) * (last - first) / n
            centers = np.stack(np.meshgrid(xs, ys), axis=-1)
            d["images"].append(_image(ax, arr, centers))
    return d


def _image(ax, arr, centers) -> dict:
    """Matrix values plus each cell's data-coord and figure-fraction centre."""
    out = {"shape": list(arr.shape)}
    if arr.ndim == 2 and arr.shape[0] <= 40 and arr.shape[1] <= 40:
        out["array"] = [_floats(row) for row in arr]
        out["xs"] = _floats(centers[0, :, 0])
        out["ys"] = _floats(centers[:, 0, 1])
        out["cells"] = [_fig_xy(ax, row) for row in centers]
    return out


def _r4(v) -> float:
    return float(f"{v:.4g}")


def _text_props(p: dict, key: str, t: Text, renderer, fig_bb) -> None:
    """Content, style and placement of one text (placement in figure fraction)."""
    p[f"{key}.text"] = t.get_text()
    p[f"{key}.fontsize"] = round(t.get_fontsize(), 3)
    p[f"{key}.fontweight"] = str(t.get_fontweight())
    p[f"{key}.color"] = _hex(t.get_color())
    p[f"{key}.alpha"] = _alpha(t, t.get_color())
    p[f"{key}.rotation"] = round(float(t.get_rotation()), 2)
    bb = t.get_window_extent(renderer)
    p[f"{key}.pos"] = [
        round((bb.x0 + bb.x1) / 2 / fig_bb.width, 3),
        round((bb.y0 + bb.y1) / 2 / fig_bb.height, 3),
    ]


def _keyname(s: str) -> str:
    return " ".join(s.split())[:40].replace(".", "_") or "#"


def _props(
    fig: Figure, axes: list, data: list[dict], legends: dict, renderer
) -> dict:
    """Flat property map used for edit-case preservation diffs."""
    fig_bb = fig.bbox
    p: dict = {
        "figure.size_in": [round(v, 3) for v in fig.get_size_inches()],
        "figure.n_axes": len(axes),
    }
    st = getattr(fig, "_suptitle", None)
    if st is not None and st.get_text():
        _text_props(p, "figure.suptitle", st, renderer, fig_bb)
    seen: Counter[str] = Counter()

    def unique(key: str) -> str:
        seen[key] += 1
        return key if seen[key] == 1 else f"{key}#{seen[key]}"

    for t in fig.texts:
        if t.get_visible() and t.get_text().strip():
            _text_props(
                p,
                unique(f"figure.text:{_keyname(t.get_text())}"),
                t,
                renderer,
                fig_bb,
            )
    for key, lg in legends.items():
        k = key if key.startswith("fig") else key.replace("ax", "ax", 1)
        p[f"{k}.legend.loc"] = lg["loc"]
        p[f"{k}.legend.texts"] = lg["texts"]
        p[f"{k}.legend.fontsize"] = lg["fontsize"]
        p[f"{k}.legend.bbox"] = [round(v, 3) for v in lg["bbox"]]
    for i, ax in enumerate(axes):
        k = f"ax{i}"
        p[f"{k}.position"] = [round(v, 3) for v in ax.get_position().bounds]
        p[f"{k}.visible"] = bool(ax.get_visible() and ax.axison)
        p[f"{k}.xscale"], p[f"{k}.yscale"] = ax.get_xscale(), ax.get_yscale()
        p[f"{k}.xlim"] = [_r4(v) for v in ax.get_xlim()]
        p[f"{k}.ylim"] = [_r4(v) for v in ax.get_ylim()]
        p[f"{k}.xticks"] = [[_r4(loc), txt] for loc, txt in data[i]["xticks"]]
        p[f"{k}.yticks"] = [[_r4(loc), txt] for loc, txt in data[i]["yticks"]]
        for side, sp in ax.spines.items():
            p[f"{k}.spine.{side}"] = [
                bool(sp.get_visible()),
                _hex(sp.get_edgecolor()),
                round(sp.get_linewidth(), 3),
            ]
        for role, t in (
            ("title", ax.title),
            ("title_left", ax._left_title),
            ("title_right", ax._right_title),
            ("xlabel", ax.xaxis.label),
            ("ylabel", ax.yaxis.label),
        ):
            if t.get_text() and t.get_visible():
                _text_props(p, f"{k}.{role}", t, renderer, fig_bb)
        for axis, role in ((ax.xaxis, "xtick"), (ax.yaxis, "ytick")):
            labels = [
                t
                for t in axis.get_ticklabels()
                if t.get_visible() and t.get_text()
            ]
            if labels:
                t = labels[0]
                p[f"{k}.{role}.fontsize"] = round(t.get_fontsize(), 3)
                p[f"{k}.{role}.color"] = _hex(t.get_color())
                p[f"{k}.{role}.fontweight"] = str(t.get_fontweight())
                p[f"{k}.{role}.rotation"] = round(float(t.get_rotation()), 2)
        for t in ax.texts:
            if t.get_visible() and t.get_text().strip():
                _text_props(
                    p,
                    unique(f"{k}.text:{_keyname(t.get_text())}"),
                    t,
                    renderer,
                    fig_bb,
                )
        for kind, items in (
            ("line", data[i]["lines"]),
            ("bars", data[i]["bars"]),
            ("scatter", data[i]["scatter"]),
        ):
            for j, a in enumerate(items):
                name = (
                    a["label"]
                    if a["label"] and not a["label"].startswith("_")
                    else f"#{j}"
                )
                q = unique(f"{k}.{kind}.{name.replace('.', '_')}")
                p[f"{q}.visible"] = a["visible"]
                p[f"{q}.alpha"] = a["alpha"]
                if kind == "line":
                    p[f"{q}.color"], p[f"{q}.lw"], p[f"{q}.ls"] = (
                        a["color"],
                        a["lw"],
                        a["ls"],
                    )
                    p[f"{q}.marker"], p[f"{q}.ms"] = a["marker"], a["ms"]
                    p[f"{q}.zorder"] = a["zorder"]
                    p[f"{q}.data"] = _digest(a["x"]) + ":" + _digest(a["y"])
                elif kind == "bars":
                    p[f"{q}.colors"] = a["colors"]
                    p[f"{q}.data"] = (
                        _digest(a["pos"])
                        + ":"
                        + _digest(a["values"])
                        + ":"
                        + _digest(a["base"])
                    )
                else:
                    p[f"{q}.colors"] = a["colors"]
                    p[f"{q}.data"] = _digest(a["x"]) + ":" + _digest(a["y"])
    return p


def snapshot(fig: Figure, save: dict | None) -> dict:
    canvas = (
        fig.canvas
        if isinstance(fig.canvas, FigureCanvasAgg)
        else FigureCanvasAgg(fig)
    )
    drawn: dict[int, Text] = {}
    orig_draw = Text.draw

    def spy(self, renderer):
        if self.get_visible() and self.get_text().strip():
            drawn.setdefault(id(self), self)
        return orig_draw(self, renderer)

    Text.draw = spy
    try:
        canvas.draw()
    finally:
        Text.draw = orig_draw
    renderer = canvas.get_renderer()
    fig_bb = fig.bbox
    axes = list(fig.get_axes())
    roles = _roles(fig, axes)
    w_pt = fig.get_size_inches()[0] * 72
    texts = []
    for t in drawn.values():
        role, ax_i = roles.get(id(t), ("other", None))
        if role == "other" and t.axes is not None and t.axes in axes:
            ax_i = axes.index(t.axes)
        q = _text_quad(t, renderer)
        texts.append(
            {
                "s": t.get_text(),
                "role": role,
                "ax": ax_i,
                "quad": [
                    [round(x / fig_bb.width, 5), round(y / fig_bb.height, 5)]
                    for x, y in q
                ],
                "fontsize": round(t.get_fontsize(), 3),
                "rotation": round(float(t.get_rotation()), 2),
                "clip_on": bool(t.get_clip_on()),
            }
        )
    names = _legend_names(fig)
    data = [_axes_data(ax, i, renderer, names) for i, ax in enumerate(axes)]
    legends: dict = {}
    for i, ax in enumerate(axes):
        lg = ax.get_legend()
        if lg is not None and lg.get_visible():
            legends[f"ax{i}"] = _legend_info(lg, fig_bb, renderer, [ax])
    for j, lg in enumerate(fig.legends):
        if lg.get_visible():
            legends[f"fig{j}"] = _legend_info(lg, fig_bb, renderer, axes)
    meta = []
    for i, ax in enumerate(axes):
        twins = [
            j
            for j, o in enumerate(axes)
            if o is not ax
            and (
                ax.get_shared_x_axes().joined(ax, o)
                or ax.get_shared_y_axes().joined(ax, o)
            )
            and np.allclose(
                o.get_position().bounds, ax.get_position().bounds, atol=1e-3
            )
        ]
        has_data = bool(
            ax.get_lines()
            or ax.collections
            or ax.patches
            or ax.images
            or ax.containers
        )
        meta.append(
            {
                "index": i,
                "position": [round(v, 4) for v in ax.get_position().bounds],
                "colorbar": bool(
                    hasattr(ax, "_colorbar") or ax.get_label() == "<colorbar>"
                ),
                "has_data": has_data,
                "visible": bool(ax.get_visible() and ax.axison),
                "xscale": ax.get_xscale(),
                "yscale": ax.get_yscale(),
                "xlim": _floats(ax.get_xlim()),
                "ylim": _floats(ax.get_ylim()),
                "twins": twins,
                "yaxis_right": ax.yaxis.get_ticks_position() == "right"
                or ax.yaxis.get_label_position() == "right",
            }
        )
    findings: dict = {}
    try:
        import dartwork_mpl as dm

        findings = dict(
            Counter(w.check_id for w in dm.validate_figure(fig, quiet=True))
        )
    except Exception as exc:  # noqa: BLE001 - advisory input only
        findings = {"_error": f"{type(exc).__name__}: {exc}"}
    return {
        "save": save,
        "figure": {
            "size_in": [round(v, 4) for v in fig.get_size_inches()],
            "dpi": float(fig.dpi),
            "width_pt": round(w_pt, 2),
            "height_pt": round(fig.get_size_inches()[1] * 72, 2),
        },
        "texts": texts,
        "axes": meta,
        "data": data,
        "legends": legends,
        "props": _props(fig, axes, data, legends, renderer),
        "dm_findings": findings,
    }


# --------------------------------------------------------------- main
def main() -> int:
    script, out_json = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    source = script.read_text(encoding="utf-8", errors="replace")
    use_dm = "dartwork_mpl" in source
    result: dict = {"script": str(script), "ok": False, "error": None}
    _install_patches(use_dm)
    sys.path.insert(0, str(script.parent))
    sys.argv = [str(script)]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            runpy.run_path(str(script), run_name="__main__")
            result["ok"] = True
        except SystemExit as exc:
            result["ok"] = exc.code in (None, 0)
            if not result["ok"]:
                result["error"] = f"SystemExit({exc.code})"
        except BaseException:  # noqa: BLE001 - record any failure of the script
            result["error"] = traceback.format_exc(limit=8)[-4000:]
        snap = STATE["snapshot"]
        target = "figure.png" if snap is not None else None
        try:
            if snap is None and STATE["last_png_fig"] is not None:
                snap, target = (
                    snapshot(STATE["last_png_fig"], SAVES[-1]),
                    "last_png",
                )
            elif snap is None and plt.get_fignums():
                snap, target = snapshot(plt.gcf(), None), "gcf"
        except Exception:  # noqa: BLE001 - a failed snapshot is recorded, not raised
            STATE["snapshot_error"] = traceback.format_exc(limit=6)[-3000:]
    msgs = [str(w.message) for w in caught]
    glyphs = sorted({m for m in msgs if "Glyph" in m and "missing from" in m})
    if use_dm:
        try:
            import dartwork_mpl as dm

            result["lint"] = dict(
                Counter(
                    getattr(i, "rule_id", str(i)) for i in dm.lint_code(source)
                )
            )
            result["dm_version"] = getattr(dm, "__version__", None)
        except Exception as exc:  # noqa: BLE001 - advisory input only
            result["lint"] = {"_error": f"{type(exc).__name__}: {exc}"}
    result.update(
        {
            "target": target,
            "saves": SAVES,
            "calls": dict(CALLS),
            "styles": STYLES,
            "missing_glyphs": glyphs,
            "warnings": sorted(set(msgs) - set(glyphs))[:30],
            "snapshot": snap,
            "snapshot_error": STATE.get("snapshot_error"),
            "matplotlib": matplotlib.__version__,
        }
    )
    out_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
