"""Request-compliance checks (``group: spec``): size, preset, layout, highlight, ...

Each check returns ``(ok, detail)``; ``ok`` is True, False or None (unchecked).
"""

from __future__ import annotations

import fnmatch
import re
from itertools import pairwise

import numpy as np
from metrics import TICK_ROLES, defects
from views import (
    candidates,
    center,
    data_axes,
    expected_series,
    fin,
    luminance,
    named,
    observed_bars,
    over,
    rgb,
    sat,
    series_match,
    texts,
)


def c_text(c, probe, base):
    pool = [t["s"] for t in texts(probe["snapshot"], c.get("roles"))]
    missing = [
        item[0] if isinstance(item, list) else item
        for item in c["contains"]
        if not any(
            named(s, item if isinstance(item, list) else [item]) for s in pool
        )
    ]
    return not missing, f"missing {missing}" if missing else "all present"


def c_regex(c, probe, base):
    pat = re.compile(c["pattern"])
    n = sum(
        1
        for t in texts(probe["snapshot"], c.get("roles"))
        if pat.search(t["s"])
    )
    return n >= c.get("min", 1), f"{n} texts match {c['pattern']!r}"


PANEL_LABEL_ROLES = {"title", "title_left", "title_right", "text", "annotation"}


def c_panel_labels(c, probe, base):
    """Each panel label (a, b, ...) leads a text of its own data panel.

    A label is the text's first token, optionally in brackets or followed
    by ``.``/``:`` (``a``, ``(a)``, ``A.``, ``(a) Annual growth``). Figure
    texts belong to the panel whose top-left corner is nearest.
    """
    snap = probe["snapshot"]
    panels = {a["index"]: a["position"] for a in snap["axes"] if a["has_data"]}

    def owner(t):
        if t["ax"] is not None:
            return t["ax"] if t["role"] in PANEL_LABEL_ROLES else None
        if t["role"] != "figtext" or not panels:
            return None
        cx, cy = center(t)
        return min(
            panels,
            key=lambda i: (
                (cx - panels[i][0]) ** 2
                + (cy - panels[i][1] - panels[i][3]) ** 2
            ),
        )

    found: dict[str, set] = {}
    for lab in c["labels"]:
        rx = re.compile(
            rf"^\s*[(\[]?{re.escape(lab)}[)\].:]?(?=\s|$)", re.IGNORECASE
        )
        found[lab] = {
            o
            for t in snap["texts"]
            if rx.search(t["s"]) and (o := owner(t)) is not None
        }
    used: set = set()
    missing = []
    for lab, owners in found.items():
        free = sorted(owners - used)
        if free:
            used.add(free[0])
        else:
            missing.append(lab)
    return (
        not missing,
        f"labels without their own panel: {missing}"
        if missing
        else f"labels {list(found)} lead texts of distinct panels",
    )


def saved_size_cm(probe: dict) -> tuple[float, float]:
    save = probe["snapshot"].get("save") or {}
    if save.get("png_px") and save.get("dpi"):
        w, h = (px / save["dpi"] * 2.54 for px in save["png_px"])
        return w, h
    w, h = probe["snapshot"]["figure"]["size_in"]
    return w * 2.54, h * 2.54


def c_size(c, probe, base):
    w, h = saved_size_cm(probe)
    tol = c.get("tol", 0.25)
    ok = all(
        [
            "width" not in c or abs(w - c["width"]) <= tol,
            "height" not in c or abs(h - c["height"]) <= tol,
            "min_width" not in c or w >= c["min_width"] - tol,
            "max_width" not in c or w <= c["max_width"] + tol,
            "aspect" not in c
            or abs(h / w - c["aspect"]) <= c.get("aspect_tol", 0.03),
        ]
    )
    return ok, f"saved {w:.2f}x{h:.2f} cm"


def c_scale(c, probe, base):
    snap = probe["snapshot"]
    vals = [snap["axes"][i][f"{c['axis']}scale"] for i in data_axes(snap)]
    return c["value"] in vals, f"{c['axis']}scale={vals}"


def c_twin(c, probe, base):
    pairs = [
        a["index"]
        for a in probe["snapshot"]["axes"]
        if a["twins"] and not a["colorbar"]
    ]
    return len(pairs) >= 2, f"axes with a same-position twin: {pairs}"


def c_legend(c, probe, base):
    """A legend outside the plot area on ``side`` (``right``, the default, or ``top``), inside the canvas."""
    snap = probe["snapshot"]
    lgs = snap["legends"]
    if "present" in c:
        return bool(lgs) == c["present"], f"legends {list(lgs)}"
    if c.get("side", "right") == "top":
        _, top = _plot_area(snap)
        above = [k for k, lg in lgs.items() if lg["bbox"][1] >= top - 0.01]
        inside_canvas = all(
            lg["bbox"][3] <= 1.005
            and lg["bbox"][0] >= -0.005
            and lg["bbox"][2] <= 1.005
            for lg in lgs.values()
        )
        return (
            bool(above) and inside_canvas,
            f"axes top edge {top:.3f}; legends {[(k, lg['bbox']) for k, lg in lgs.items()]}",
        )
    right = max(
        snap["axes"][i]["position"][0] + snap["axes"][i]["position"][2]
        for i in data_axes(snap)
    )
    outside = [k for k, lg in lgs.items() if lg["bbox"][0] >= right - 0.01]
    inside_canvas = all(lg["bbox"][2] <= 1.005 for lg in lgs.values())
    return (
        bool(outside) and inside_canvas,
        f"axes right edge {right:.3f}; legends {[(k, lg['bbox']) for k, lg in lgs.items()]}",
    )


def c_panel_ratio(c, probe, base):
    snap = probe["snapshot"]
    uniq = {
        tuple(round(v, 3) for v in snap["axes"][i]["position"]): snap["axes"][i]
        for i in data_axes(snap)
    }.values()
    if c.get("axis", "height") == "height":
        sizes = [
            a["position"][3]
            for a in sorted(uniq, key=lambda a: -a["position"][1])
        ]
    else:
        sizes = [
            a["position"][2]
            for a in sorted(uniq, key=lambda a: a["position"][0])
        ]
    want, got = (
        np.asarray(c["ratios"], dtype=float),
        np.asarray(sizes, dtype=float),
    )
    if len(got) != len(want):
        return False, f"{len(got)} panels {np.round(got, 3).tolist()}"
    got, want = got / got.sum(), want / want.sum()
    return bool(
        np.all(np.abs(got - want) <= c.get("tol", 0.05))
    ), f"ratios {np.round(got, 3).tolist()}"


def c_grid(c, probe, base):
    snap = probe["snapshot"]
    pos = [snap["axes"][i]["position"] for i in data_axes(snap)]
    rows_, cols_ = (
        len({round(p[1], 2) for p in pos}),
        len({round(p[0], 2) for p in pos}),
    )
    return (rows_, cols_) == (
        c["rows"],
        c["cols"],
    ), f"{rows_} rows x {cols_} cols"


def c_same_lim(c, probe, base):
    snap = probe["snapshot"]
    lims = [tuple(snap["axes"][i][f"{c['axis']}lim"]) for i in data_axes(snap)]
    same = len(lims) > 1 and all(
        np.allclose(lim, lims[0], rtol=1e-6) for lim in lims
    )
    return (
        same,
        f"{len(set(lims))} distinct {c['axis']}lim over {len(lims)} axes",
    )


def c_count(c, probe, base):
    n = len(data_axes(probe["snapshot"]))
    op = c.get("op", "eq")
    return {"eq": n == c["n"], "ge": n >= c["n"], "le": n <= c["n"]}[
        op
    ], f"data_axes={n} ({op} {c['n']})"


def c_bars_sorted(c, probe, base):
    snap = probe["snapshot"]
    for i in data_axes(snap):
        meta = snap["axes"][i]
        for b in snap["data"][i]["bars"]:
            if (
                b["orientation"] != c.get("orientation", "h")
                or len(b["values"]) < 3
            ):
                continue
            lim = meta["ylim"] if b["orientation"] == "h" else meta["xlim"]
            vals = [
                v
                for _, v in sorted(
                    zip(b["pos"], b["values"], strict=True), key=lambda p: p[0]
                )
            ]
            if (b["orientation"] == "h") != (lim[0] > lim[1]):
                vals = vals[
                    ::-1
                ]  # reading order: top-to-bottom / left-to-right
            return all(
                a >= b2 - 1e-9 for a, b2 in pairwise(vals)
            ), f"reading order {vals[:5]}..."
    return False, "no bar series found"


def c_highlight(c, probe, base):
    snap = probe["snapshot"]
    if c.get("kind") == "bar":
        bars = [b for b in observed_bars(snap) if b["value"] is not None]
        tgt = [
            b for b in bars if any(named(t, c["aliases"]) for t in b["cats"])
        ]
        rest = [b for b in bars if b not in tgt]
        if len(tgt) != 1 or not rest:
            return False, f"{len(tgt)} target bars"
        top = max(sat(b["color"]) for b in rest)
        return (
            sat(tgt[0]["color"]) >= 0.25 and top <= 0.15,
            f"target sat {sat(tgt[0]['color']):.2f}, others max {top:.2f}",
        )
    cands = [k for k in candidates(snap) if k["kind"] == "line"]
    kind = c["x"]["kind"]

    def find(s):
        xs, ys = expected_series(c, s)
        return [k for k in cands if series_match(k, xs, ys, kind)]

    tgt = find(c["target"])
    others = [find(s) for s in c["others"]]
    if not tgt or not all(others):
        return False, "series not found"
    ts, rest = (
        max(sat(k["color"]) for k in tgt),
        max(sat(k["color"]) for o in others for k in o),
    )
    return (
        ts >= 0.25 and rest <= 0.15,
        f"target sat {ts:.2f}, others max {rest:.2f}",
    )


def c_end_labels(c, probe, base):
    snap = probe["snapshot"]
    every = [a for s in c["series"] for a in s["aliases"]]
    if any(
        named(t, every) for lg in snap["legends"].values() for t in lg["texts"]
    ):
        return False, "a legend still lists the series"
    cands = [k for k in candidates(snap) if k["kind"] == "line"]
    pool = texts(snap, exclude=TICK_ROLES | {"legend", "legend_title"})
    missing = []
    for s in c["series"]:
        xs, ys = expected_series(c, s)
        ok = False
        for k in cands:
            if k["end"] and series_match(k, xs, ys, c["x"]["kind"]):
                ex, ey = k["end"]
                ok |= any(
                    named(t["s"], s["aliases"])
                    and -0.03 <= np.asarray(t["quad"])[:, 0].min() - ex <= 0.15
                    and abs(np.asarray(t["quad"])[:, 1].mean() - ey) <= 0.12
                    for t in pool
                )
        if not ok:
            missing.append(s["aliases"][0])
    return (
        not missing,
        f"no end label for {missing}" if missing else "all labelled",
    )


def c_preset(c, probe, base):
    styles = probe.get("styles") or []
    return any(
        s.startswith(p) for s in styles for p in c["prefix"]
    ), f"styles used {styles}"


def c_fontsize_delta(c, probe, base):
    if not base or not base.get("snapshot"):
        return False, "no base snapshot"
    bp, ep = base["snapshot"]["props"], probe["snapshot"]["props"]
    keys = [k for k in bp if fnmatch.fnmatchcase(k, c["key"])]
    deltas = {k: round(ep[k] - bp[k], 3) if k in ep else None for k in keys}
    ok = bool(keys) and all(
        d is not None and c["min"] <= d <= c["max"] for d in deltas.values()
    )
    return ok, f"deltas {deltas}"


def c_not_worse(c, probe, base):
    if not base or not base.get("snapshot"):
        return False, "no base snapshot"
    b, e = defects(base)["counts"]["total"], defects(probe)["counts"]["total"]
    return e <= b, f"defects base {b} -> edit {e}"


# ------------------------------------------------------------ customization
TITLE_ROLES = {"title", "title_left", "title_right", "suptitle"}
NOT_NOTES = TICK_ROLES | {"legend", "legend_title"}


def _plot_area(snap: dict) -> tuple[float, float]:
    """Bottom and top edges of the data axes (figure fraction)."""
    pos = [snap["axes"][i]["position"] for i in data_axes(snap)]
    return min(p[1] for p in pos), max(p[1] + p[3] for p in pos)


def _areas(snap: dict) -> dict[tuple, list[int]]:
    """Data axes grouped by position: twins share one plot area."""
    out: dict[tuple, list[int]] = {}
    for i in data_axes(snap):
        pos = tuple(round(v, 3) for v in snap["axes"][i]["position"])
        out.setdefault(pos, []).append(i)
    return out


def _on_canvas(t: dict, snap: dict, tol: float = 0.01) -> bool:
    """The text lies on the saved canvas (a tight bbox grows it to fit)."""
    if str((snap.get("save") or {}).get("bbox_inches")).lower() == "tight":
        return True
    q = np.asarray(t["quad"])
    return bool(q.min() >= -tol and q.max() <= 1 + tol)


def c_title(c, probe, base):
    """The requested title is drawn as a title.

    An axes title (centre/left/right) or the suptitle containing
    ``contains``, or a figure/axes text containing it that sits wholly
    above the plot area; on the canvas either way.
    """
    snap = probe["snapshot"]
    _, top = _plot_area(snap)
    found = [
        f"{t['role']}:{t['s'][:40]}"
        for t in texts(snap, exclude=NOT_NOTES)
        if named(t["s"], [c["contains"]])
        and _on_canvas(t, snap)
        and (
            t["role"] in TITLE_ROLES
            or np.asarray(t["quad"])[:, 1].min() >= top - c.get("tol", 0.01)
        )
    ]
    return bool(found), (
        f"title {found}"
        if found
        else f"no title or text above the plot area contains {c['contains']!r}"
    )


def c_text_below(c, probe, base):
    """A text containing ``contains`` lies below the plot area, on the canvas.

    Its top edge is at or under the bottom of the lowest data axes; any
    role but ticks and legends (a figure text, an axes annotation, a
    second x-label line).
    """
    snap = probe["snapshot"]
    bottom, _ = _plot_area(snap)
    hits = [
        t
        for t in texts(snap, exclude=NOT_NOTES)
        if named(t["s"], [c["contains"]])
    ]
    below = [
        f"{t['role']}:{t['s'][:40]}"
        for t in hits
        if np.asarray(t["quad"])[:, 1].max() <= bottom + c.get("tol", 0.01)
        and _on_canvas(t, snap)
    ]
    return bool(below), (
        f"below the plot area (bottom {bottom:.3f}): {below}"
        if below
        else f"{len(hits)} texts contain {c['contains']!r}, none below the plot area (bottom {bottom:.3f}) on the canvas"
    )


def _drawn_grid(snap: dict, i: int, axis: str) -> set[float]:
    """Tick locations of ``axis`` with a drawn line across >= 90% of the plot area.

    Gridlines drawn by hand: ``axhline``/``axvline`` (or a two-point line)
    and ``hlines``/``vlines`` segments at the tick positions.
    """
    d, meta = snap["data"][i], snap["axes"][i]
    locs = [t[0] for t in d[f"{axis}ticks"]]
    k = 1 if axis == "y" else 0  # the figure coordinate a gridline holds
    span = meta["position"][2] if axis == "y" else meta["position"][3]

    def tick(v):
        return next(
            (loc for loc in locs if abs(loc - v) <= 1e-6 * max(1.0, abs(loc))),
            None,
        )

    hits = set()
    for ln in d["lines"]:
        vals, f = fin(ln["y"] if axis == "y" else ln["x"]), ln.get("figxy")
        if not (ln["visible"] and f and len(f) >= 2 and vals):
            continue
        f = np.asarray(f, dtype=float)
        if (
            max(vals) == min(vals)
            and np.ptp(f[:, k]) < 1e-3
            and np.ptp(f[:, 1 - k]) >= 0.9 * span
        ):
            hits.add(tick(vals[0]))
    lim = sorted(meta["xlim"] if axis == "y" else meta["ylim"])
    for s in d["hsegs"] if axis == "y" else d["vsegs"]:
        a, b, v = (s[0], s[1], s[2]) if axis == "y" else (s[1], s[2], s[0])
        if b - a >= 0.9 * (lim[1] - lim[0]):
            hits.add(tick(v))
    return hits - {None}


def c_gridlines(c, probe, base):
    """Visible major gridlines along ``axis`` (``y``: horizontal lines) in every plot area.

    A plot area's twin axes count for it. Lines drawn by hand across the
    plot area at two or more ticks count as gridlines too.
    """
    snap = probe["snapshot"]
    axis, props = c.get("axis", "y"), snap["props"]
    how = {}
    for idx in _areas(snap).values():
        native = [i for i in idx if props.get(f"ax{i}.grid.{axis}.visible")]
        drawn = {i: len(_drawn_grid(snap, i, axis)) for i in idx}
        how["+".join(f"ax{i}" for i in idx)] = (
            "grid"
            if native
            else next(
                (f"lines at {n} ticks" for n in drawn.values() if n >= 2),
                "none",
            )
        )
    return bool(how) and "none" not in how.values(), f"{axis} gridlines {how}"


def c_dark_background(c, probe, base):
    """Every plot area is dark as saved: WCAG luminance below ``max_luminance``.

    A plot area's colour is its visible axes faces composited over the
    saved canvas (savefig's facecolor, else the figure's, over white). A
    transparent save leaves the background to the viewer and fails.
    """
    snap = probe["snapshot"]
    save, fig = snap.get("save") or {}, snap["figure"]
    if save.get("transparent"):
        return (
            False,
            "saved with transparent=True: the background is the viewer's",
        )
    face, alpha = (
        (save["facecolor"], save.get("face_alpha"))
        if save.get("facecolor")
        else (fig.get("facecolor"), fig.get("face_alpha"))
    )
    if not face:
        return False, "no canvas colour recorded"
    canvas = over(rgb(face), 1.0 if alpha is None else alpha, (1.0, 1.0, 1.0))
    limit = c.get("max_luminance", 0.3)
    areas = {}
    for idx in _areas(snap).values():
        bg = canvas
        for i in idx:
            a = snap["axes"][i]
            if a.get("patch_visible") and a.get("facecolor"):
                bg = over(rgb(a["facecolor"]), a.get("face_alpha") or 0.0, bg)
        areas["+".join(f"ax{i}" for i in idx)] = round(luminance(bg), 3)
    return bool(areas) and all(v < limit for v in areas.values()), (
        f"canvas luminance {luminance(canvas):.3f}; plot areas {areas} (dark < {limit})"
    )


SPEC_CHECKS = {
    "text": c_text,
    "regex": c_regex,
    "panel_labels": c_panel_labels,
    "size": c_size,
    "scale": c_scale,
    "twin": c_twin,
    "legend": c_legend,
    "panel_ratio": c_panel_ratio,
    "grid": c_grid,
    "same_lim": c_same_lim,
    "count": c_count,
    "bars_sorted": c_bars_sorted,
    "highlight": c_highlight,
    "end_labels": c_end_labels,
    "preset": c_preset,
    "fontsize_delta": c_fontsize_delta,
    "defects_not_worse": c_not_worse,
    "title": c_title,
    "text_below": c_text_below,
    "gridlines": c_gridlines,
    "dark_background": c_dark_background,
}
