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
    data_axes,
    expected_series,
    named,
    observed_bars,
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
    snap = probe["snapshot"]
    lgs = snap["legends"]
    if "present" in c:
        return bool(lgs) == c["present"], f"legends {list(lgs)}"
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


SPEC_CHECKS = {
    "text": c_text,
    "regex": c_regex,
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
}
