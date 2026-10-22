"""Value-fidelity contracts and the oracle runner.

Expected values come from the frozen fixture CSVs. Data contracts bind
identity (series/category/group name -> data), paired coordinates, order,
multiplicity and NaN masks, and claim the artists they explain. After all
checks, every visible data artist must have been claimed by a contract or be
a declared auxiliary (``auxiliary: [reference_lines, fit_lines]``); extra
or decoy data fails. Results are three-state: ``ok`` True, False, or None
(unchecked: the figure uses a form no contract can verify; never a pass).
"""

from __future__ import annotations

import math
from itertools import pairwise

import derived
import estimators
import numpy as np
from metrics import TICK_ROLES
from spec_checks import SPEC_CHECKS, saved_size_cm
from views import (
    SCALE_UNITS,
    candidates,
    center,
    data_axes,
    daynum,
    evaluate,
    expected_series,
    fin,
    identity_texts,
    key,
    named,
    nearest_tick,
    num,
    numbers,
    observed_bars,
    rows,
    series_match,
    table,
    texts,
    unit_text,
)

DATA_CONTRACTS = {
    "series",
    "bars",
    "points",
    "fits",
    "dist",
    "stack",
    "errorbars",
    "matrix",
}


# ------------------------------------------------------------ series
def _label_names(k: dict) -> list[str]:
    names = list(k.get("legend") or [])
    if k["label"] and not k["label"].startswith("_"):
        names.append(k["label"])
    return names


def c_series(c, probe, base):
    snap = probe["snapshot"]
    allc = candidates(snap)
    cands = [
        k
        for k in allc
        if k["kind"] in c.get("artists", ["line", "bars", "scatter"])
    ]
    kind = (c.get("x") or {"kind": "order"})["kind"]
    every = [s["aliases"] for s in c["series"]]
    used: set = set()
    axes, problems, notes = [], [], []
    for s in c["series"]:
        xs, ys = expected_series(c, s)
        label = s["aliases"][0]
        hits = [
            k
            for k in cands
            if k["id"] not in used
            and series_match(k, xs, ys, kind, c.get("scales", [1]))
        ]
        if (
            not hits
        ):  # one consistent display scale, accepted only with its unit visible
            for f in SCALE_UNITS:
                scaled = [
                    k
                    for k in cands
                    if k["id"] not in used
                    and series_match(k, xs, ys, kind, (f,))
                    and unit_text(snap, {k["ax"]}, f)
                ]
                if scaled:
                    hits = scaled
                    notes.append(
                        f"{label} plotted x{f:g} with unit "
                        f"'{unit_text(snap, {scaled[0]['ax']}, f)}'"
                    )
                    break
        if not hits:
            problems.append(
                f"{label}: no visible artist with this data/order/NaN mask"
            )
            continue
        if c.get("identity", "named") == "named":
            hits = [
                k
                for k in hits
                if any(
                    named(t, s["aliases"])
                    for t in identity_texts(snap, k, every)
                )
            ]
            if not hits:
                problems.append(
                    f"{label}: data found but not named {s['aliases']}"
                )
                continue
        used.add(hits[0]["id"])
        axes.append(hits[0]["ax"])
    # a second artist labelled as an expected series but showing other data
    problems += [
        f"extra artist labelled {_label_names(k)} with other data"
        for k in allc
        if k["id"] not in used
        and any(
            named(n, s["aliases"]) for n in _label_names(k) for s in c["series"]
        )
    ]
    if c.get("panels") == "distinct" and len(set(axes)) != len(axes):
        problems.append("series that need their own panels share one")
    return (
        not problems,
        "; ".join(
            problems or ["all series matched one-to-one with identity", *notes]
        ),
        used,
    )


# ------------------------------------------------------------ bars
def expected_bars(c: dict) -> dict:
    """(category, series) -> value; ``columns`` turns a wide table into one bar per column."""
    groups: dict = {}
    for r in rows(c):
        if "columns" in c:
            for col in c["columns"]:
                groups.setdefault((col, None), []).append(num(r[col]))
            continue
        k = (
            r[c["category"]["col"]],
            r[c["series"]["col"]] if c.get("series") else None,
        )
        groups.setdefault(k, []).append(num(r[c["value"]]))
    out = {}
    for k, vals in groups.items():
        f = fin(vals)
        if c.get("agg") == "mean":
            out[k] = float(np.mean(f)) if f else None
        elif c.get("agg") == "sum":
            out[k] = float(np.sum(f)) if f else None
        else:
            if len(vals) != 1:
                raise ValueError(f"duplicate rows for {k} without agg")
            out[k] = vals[0]
    return out


def _layout_problems(matched: list[tuple], layout: str) -> list[str]:
    """``grouped``: per category, side by side from zero. ``stacked``: per category, cumulative from zero."""
    by_cat: dict = {}
    for cat, b in matched:
        by_cat.setdefault(cat, []).append(b)
    out = []
    for cat, bars in by_cat.items():
        if len(bars) < 2:
            continue
        if layout == "grouped":
            iv = sorted(
                (b["pos"] - b["width"] / 2, b["pos"] + b["width"] / 2)
                for b in bars
            )
            overlap = any(
                b0 < a1 - 1e-6 * max(1, abs(a1))
                for (_, a1), (b0, _) in pairwise(iv)
            )
            if overlap or any(abs(b["base"]) > 1e-9 for b in bars):
                out.append(f"{cat}: bars are not side by side from zero")
        elif layout == "stacked":
            if max(b["pos"] for b in bars) - min(
                b["pos"] for b in bars
            ) > 0.5 * min(b["width"] for b in bars):
                out.append(f"{cat}: segments are not in one column")
                continue
            seg = sorted(bars, key=lambda b: b["base"])
            top, ok = 0.0, True
            for b in seg:
                ok &= abs(b["base"] - top) <= 1e-6 * max(1.0, abs(top))
                top = b["base"] + b["value"]
            if not ok:
                out.append(
                    f"{cat}: segments do not stack cumulatively from zero"
                )
    return out


def c_bars(c, probe, base):
    """Category (and series) -> value for every bar; a display scale needs its unit visible."""
    res = _bars_once(c, probe)
    if res[0]:
        return res
    snap = probe["snapshot"]
    for f in SCALE_UNITS:
        ok, detail, ids = _bars_once({**c, "scales": [f]}, probe)
        unit = unit_text(snap, {i for _, i, _ in ids}, f) if ok else None
        if unit:
            return True, f"{detail}; plotted x{f:g} with unit '{unit}'", ids
    return res


def _bars_once(c, probe):
    obs = [
        b
        for b in observed_bars(probe["snapshot"])
        if c.get("orientation", "any") in ("any", b["orientation"])
    ]
    exp = expected_bars(c)
    cat_alias = (
        (c.get("category") or {}).get("aliases") or c.get("aliases") or {}
    )
    ser_alias = (c.get("series") or {}).get("aliases") or {}
    used, problems, matched = set(), [], []
    for (cat, ser), v in exp.items():
        if v is None:
            continue
        cal = [cat, *cat_alias.get(cat, [])]
        sal = [ser, *ser_alias.get(ser, [])] if ser else None
        hit = None
        for j, b in enumerate(obs):
            if (
                j in used
                or b["value"] is None
                or not any(named(t, cal) for t in b["cats"])
            ):
                continue
            if sal and not any(named(n, sal) for n in b["series"]):
                continue
            if any(
                abs(b["value"] - v * s)
                <= 1e-6 + c.get("rtol", 0.002) * abs(v * s)
                for s in c.get("scales", [1])
            ):
                hit = j
                break
        if hit is None:
            problems.append(f"{cat}/{ser}={v:g} not found as a named bar")
        else:
            used.add(hit)
            matched.append((cat, obs[hit]))
    extra = [
        b
        for j, b in enumerate(obs)
        if j not in used and b["value"] not in (None, 0.0)
    ]
    if extra:
        problems.append(f"{len(extra)} extra/duplicate bars")
    if c.get("layout", "any") != "any":
        problems += _layout_problems(matched, c["layout"])
    ids = {b["id"] for _, b in matched}
    return (
        not problems,
        "; ".join(problems[:6]) or f"{len(used)} bars matched category->value",
        ids,
    )


def c_bar_labels(c, probe, base):
    snap = probe["snapshot"]
    pool = texts(snap, exclude=TICK_ROLES | {"legend", "legend_title"})
    bars = [b for b in observed_bars(snap) if b["value"] is not None]
    missing = 0
    for b in bars:
        x0, y0, x1, y1 = b["ext"]
        end = (
            ((x1 if b["value"] >= 0 else x0), (y0 + y1) / 2)
            if b["orientation"] == "h"
            else ((x0 + x1) / 2, (y1 if b["value"] >= 0 else y0))
        )
        ok = False
        for t in pool:
            cx, cy = center(t)
            if math.hypot(cx - end[0], cy - end[1]) <= c.get("radius", 0.08):
                ok |= any(
                    abs(n - b["value"] * s) <= c.get("atol", 0.051)
                    for n in numbers(t["s"])
                    for s in c.get("scales", [1])
                )
        missing += not ok
    return bool(
        bars
    ) and not missing, f"{missing}/{len(bars)} bars lack a matching value label"


# ------------------------------------------------------------ points / fits
def _pairs(xs, ys) -> list[tuple]:
    return sorted(
        (round(a, 6), round(b, 6))
        for a, b in zip(xs, ys, strict=True)
        if a is not None and b is not None
    )


def _groups(c: dict) -> dict:
    out: dict = {}
    for r in rows(c):
        g = r[c["by"]["col"]] if c.get("by") else None
        out.setdefault(g, []).append((num(r[c["x"]]), num(r[c["y"]])))
    return out


def c_points(c, probe, base):
    snap = probe["snapshot"]
    colls = [k for k in candidates(snap) if k["kind"] == "scatter"]
    exp = _groups(c)
    aliases = (c.get("by") or {}).get("aliases") or {}
    problems, used = [], set()
    for g, pts in exp.items():
        want = _pairs([a for a, _ in pts], [b for _, b in pts])
        mine = (
            colls
            if g is None
            else [
                k
                for k in colls
                if any(
                    named(n, [g, *aliases.get(g, [])]) for n in _label_names(k)
                )
            ]
        )
        got = sorted(p for k in mine for p in _pairs(k["x"], k["y"]))
        if got != want:
            problems.append(
                f"{g}: {len(got)} named points vs {len(want)} expected or coordinates differ"
            )
        else:
            used |= {k["id"] for k in mine}
    return not problems, "; ".join(problems) or "points matched per group", used


def c_fits(c, probe, base):
    snap = probe["snapshot"]
    allc = candidates(snap)
    colls = [k for k in allc if k["kind"] == "scatter"]
    lines = [k for k in allc if k["kind"] == "line"]
    aliases = (c.get("by") or {}).get("aliases") or {}
    problems, used = [], set()
    for g, pts in _groups(c).items():
        xy = np.asarray([p for p in pts if None not in p], dtype=float)
        k, b0 = np.polyfit(xy[:, 0], xy[:, 1], 1)
        al = [g, *aliases.get(g, [])]
        colors = {
            k2["color"]
            for k2 in colls
            if any(named(n, al) for n in _label_names(k2))
        }
        hit = None
        for ln in lines:
            p2 = np.asarray(
                [
                    (x, y)
                    for x, y in zip(ln["x"], ln["y"], strict=True)
                    if None not in (x, y)
                ],
                dtype=float,
            )
            if (
                len(p2) < 2
                or np.ptp(p2[:, 0]) == 0
                or not (
                    any(named(n, al) for n in _label_names(ln))
                    or ln["color"] in colors
                )
            ):
                continue
            kk, bb = np.polyfit(p2[:, 0], p2[:, 1], 1)
            straight = np.allclose(
                p2[:, 1],
                kk * p2[:, 0] + bb,
                atol=1e-6 + 1e-6 * np.abs(p2[:, 1]).max(),
            )
            yr = np.ptp(xy[:, 1]) or 1.0
            if (
                straight
                and abs(kk - k) <= 0.03 * abs(k) + 1e-9
                and abs((kk - k) * xy[:, 0].mean() + bb - b0) <= 0.03 * yr
            ):
                hit = ln
        if hit is None:
            problems.append(
                f"{g}: no fit line (slope {k:.3f}) tied to the group by label or colour"
            )
        else:
            used.add(hit["id"])
    return not problems, "; ".join(problems) or "fit per group matched", used


# ------------------------------------------------------------ distributions
def _dist_groups(c: dict) -> dict:
    out: dict = {}
    for r in rows(c):
        v = num(r[c["value"]])
        if v is not None:
            out.setdefault(r[c["by"]["col"]], []).append(v)
    return {g: np.asarray(v) for g, v in out.items()}


def _box(
    d: dict, al: list, vals: np.ndarray, ax: int
) -> tuple[bool | None, set]:
    """Median line and Q1/Q3 box edges at the group's tick (vertical or horizontal boxes).

    True: both match. False: a box is drawn at the tick but its median/edges
    differ. None: nothing box-like at the tick, or a median without readable
    edges (unchecked).
    """
    q1, med, q3 = estimators.quartiles(vals)
    tol = 1e-6 * max(1.0, abs(med), abs(q3))
    lines = d["lines"]
    shapes = [
        (
            min(fin(ln["y"])),
            max(fin(ln["y"])),
            min(fin(ln["x"])),
            max(fin(ln["x"])),
        )
        for ln in lines
        if ln["data"] and len(fin(ln["y"])) >= 4
    ] + [
        (p["bbox"][1], p["bbox"][3], p["bbox"][0], p["bbox"][2])
        for p in d["paths"]
    ]
    seen = False
    for orient, segs, ticks in (
        ("v", d["hsegs"], d["xticks"]),
        ("h", d["vsegs"], d["yticks"]),
    ):
        for s in segs:
            pos, value = (
                ((s[0] + s[1]) / 2, s[2])
                if orient == "v"
                else ((s[1] + s[2]) / 2, s[0])
            )
            half = (
                abs(s[1] - s[0]) / 2 if orient == "v" else abs(s[2] - s[1]) / 2
            )
            if not named(nearest_tick(ticks, pos) or "", al):
                continue
            boxes = [
                (a, b)
                for y0, y1, x0, x1 in shapes
                for a, b, c0, c1 in [
                    (y0, y1, x0, x1) if orient == "v" else (x0, x1, y0, y1)
                ]
                if abs((c0 + c1) / 2 - pos) <= half + 1e-9 and a <= value <= b
            ]
            if not boxes:
                continue
            seen = True
            if abs(value - med) <= tol and any(
                abs(a - q1) <= tol and abs(b - q3) <= tol for a, b in boxes
            ):
                span = (pos - max(half, 0.5), pos + max(half, 0.5))
                axis = "x" if orient == "v" else "y"
                ids = {
                    ("line", ax, j)
                    for j, ln in enumerate(lines)
                    if fin(ln[axis])
                    and all(span[0] <= v <= span[1] for v in fin(ln[axis]))
                }
                return True, ids
    return (False if seen else None), set()


def c_dist(c, probe, base):
    """Each group must be drawn by one accepted form recomputed from its raw values."""
    snap = probe["snapshot"]
    aliases = c["by"].get("aliases") or {}
    accept = c.get("accept", ["hist", "box", "violin", "kde", "ecdf"])
    status, problems, used = {}, [], set()
    for g, vals in _dist_groups(c).items():
        al = [g, *aliases.get(g, [])]
        seen, passed = False, False
        for i in data_axes(snap):
            d = snap["data"][i]
            if "hist" in accept:
                for j, b in enumerate(d["bars"]):
                    if any(
                        named(n, al) for n in [b["label"], *b.get("legend", [])]
                    ):
                        seen = True
                        if estimators.hist_ok(b, vals):
                            passed = True
                            used.add(("bars", i, j))
                for j, st in enumerate(d.get("steps", [])):
                    if st["visible"] and any(
                        named(n, al) for n in [st["label"], *st["legend"]]
                    ):
                        seen = True
                        if any(
                            estimators.edges_hist_ok(
                                o["edges"], o["values"], vals
                            )
                            for o in st["outlines"]
                        ):
                            passed = True
                            used.add(("steps", i, j))
            if "kde" in accept:
                for j, ln in enumerate(d["lines"]):
                    if (
                        ln["data"]
                        and ln["visible"]
                        and len(fin(ln["y"])) >= 20
                        and any(
                            named(n, al)
                            for n in [ln["label"], *ln.get("legend", [])]
                        )
                    ):
                        seen = True
                        if estimators.kde_ok(ln["x"], ln["y"], vals):
                            passed = True
                            used.add(("line", i, j))
            if "ecdf" in accept:
                for j, ln in enumerate(d["lines"]):
                    if (
                        ln["data"]
                        and ln["visible"]
                        and any(
                            named(n, al)
                            for n in [ln["label"], *ln.get("legend", [])]
                        )
                        and estimators.ecdf_ok(ln["x"], ln["y"], vals)
                    ):
                        seen = passed = True
                        used.add(("line", i, j))
            if "box" in accept:
                ok, ids = _box(d, al, vals, i)
                if ok is not None:
                    seen = True
                if ok:
                    passed = True
                    used |= ids
            if "violin" in accept:
                for p in d["polys"]:
                    px, py = np.asarray(fin(p["x"])), np.asarray(fin(p["y"]))
                    if not len(px) or not named(
                        nearest_tick(d["xticks"], float(px.mean())) or "", al
                    ):
                        continue
                    seen = True
                    span = np.ptp(vals)
                    ends = (
                        abs(py.min() - vals.min()) <= 1e-6 * span
                        and abs(py.max() - vals.max()) <= 1e-6 * span
                    )
                    ys, half = estimators.violin_profile(px, py)
                    if (
                        ends
                        and estimators.kde_error(ys, half, vals)
                        <= estimators.KDE_TOL
                    ):
                        passed = True
        status[g] = True if passed else (False if seen else None)
        if not passed:
            problems.append(
                f"{g}: {'drawn but not equal to any ' + str(accept) + ' estimate' if seen else 'no recognisable form (unchecked)'}"
            )
    vals_ = list(status.values())
    ok = False if False in vals_ else (None if None in vals_ else True)
    return (
        ok,
        "; ".join(problems) or "every group equals its recomputed estimate",
        used,
    )


# ------------------------------------------------------------ matrix / stack / errorbars / span
def c_matrix(c, probe, base):
    snap = probe["snapshot"]
    cols = c["columns"]
    data = np.asarray([[num(r[k]) for k in cols] for r in rows(c)], dtype=float)
    corr = np.corrcoef(data, rowvar=False)
    aliases = c.get("aliases") or {}

    def var(text):
        hits = [
            k
            for k in cols
            if named(text or "", [k, *aliases.get(k, [])])
            or key(text or "") == key(k)
        ]
        return hits[0] if len(hits) == 1 else None

    for i in data_axes(snap):
        d = snap["data"][i]
        for im in d["images"]:
            if "array" not in im:
                continue
            rvars = [var(nearest_tick(d["yticks"], y)) for y in im["ys"]]
            cvars = [var(nearest_tick(d["xticks"], x)) for x in im["xs"]]
            bad, pairs, text_missing = 0, set(), 0
            cells = np.asarray(im["cells"])
            pitch = min(
                np.abs(np.diff(cells[0, :, 0])).min()
                if cells.shape[1] > 1
                else 1,
                np.abs(np.diff(cells[:, 0, 1])).min()
                if cells.shape[0] > 1
                else 1,
            )
            pool = texts(snap, ax=i, exclude=TICK_ROLES)
            for r, rv in enumerate(rvars):
                for k, cv in enumerate(cvars):
                    v = im["array"][r][k]
                    if v is None or rv is None or cv is None:
                        continue
                    want = corr[cols.index(rv), cols.index(cv)]
                    bad += abs(v - want) > 0.006
                    if rv != cv:
                        pairs.add(frozenset((rv, cv)))
                    if c.get("cell_text"):
                        fx, fy = cells[r][k]
                        text_missing += not any(
                            math.hypot(center(t)[0] - fx, center(t)[1] - fy)
                            <= pitch / 2
                            and any(
                                abs(n - round(want, 2)) <= 0.0051
                                for n in numbers(t["s"])
                            )
                            for t in pool
                        )
            need = len(cols) * (len(cols) - 1) // 2
            ok = (
                bad == 0
                and len(pairs) == need
                and text_missing == 0
                and len(set(rvars) - {None}) == len(cols)
            )
            return (
                ok,
                f"{bad} wrong cells, {len(pairs)}/{need} pairs, {text_missing} cells without value text",
            )
    return False, "no labelled matrix image"


def c_stack(c, probe, base):
    """Named layers with the right thickness that tile [0, total] at every x."""
    snap = probe["snapshot"]
    x = c["x"]
    rs = rows(c)
    xs = np.asarray(
        [
            num(r[x["col"]]) if x["kind"] == "num" else daynum(r[x["col"]])
            for r in rs
        ]
    )
    polys = [
        p
        for i in data_axes(snap)
        for p in snap["data"][i]["polys"]
        if p.get("visible", True)
    ]
    problems, bounds = [], []
    for layer in c["layers"]:
        want = np.asarray([num(r[layer["y"]]) for r in rs], dtype=float)
        found = None
        for p in polys:
            if not any(
                named(n, layer["aliases"])
                for n in [p["label"], *p.get("legend", [])]
            ):
                continue
            px, py = np.asarray(fin(p["x"])), np.asarray(fin(p["y"]))
            idx = np.abs(px[:, None] - xs[None, :]).argmin(axis=1)
            if np.any(np.abs(px - xs[idx]) > 1e-6 * max(1, np.abs(xs).max())):
                continue
            lo = np.asarray(
                [
                    py[idx == k].min() if np.any(idx == k) else np.nan
                    for k in range(len(xs))
                ]
            )
            hi = np.asarray(
                [
                    py[idx == k].max() if np.any(idx == k) else np.nan
                    for k in range(len(xs))
                ]
            )
            if np.allclose(hi - lo, want, rtol=1e-6, atol=1e-6):
                found = (lo, hi)
        if found is None:
            problems.append(
                f"{layer['aliases'][0]}: no named layer with these thicknesses"
            )
        else:
            bounds.append(found)
    if not problems:
        lo = np.stack([b[0] for b in bounds])
        hi = np.stack([b[1] for b in bounds])
        order = np.argsort(lo, axis=0)
        lo_s, hi_s = (
            np.take_along_axis(lo, order, 0),
            np.take_along_axis(hi, order, 0),
        )
        scale = np.maximum(1.0, np.abs(hi_s).max(axis=0))
        if not (
            np.all(np.abs(lo_s[0]) <= 1e-6 * scale)
            and np.all(np.abs(lo_s[1:] - hi_s[:-1]) <= 1e-6 * scale)
        ):
            problems.append("layers are not stacked cumulatively from zero")
    return not problems, "; ".join(problems) or "all layers stacked and matched"


def c_errorbars(c, probe, base):
    snap = probe["snapshot"]
    segs = [s for i in data_axes(snap) for s in snap["data"][i]["vsegs"]]
    missing = 0
    for r in rows(c):
        x, y, e = num(r[c["x"]]), num(r[c["y"]]), num(r[c["err"]])
        missing += not any(
            abs(sx - x) <= 1e-6 * max(1, abs(x))
            and abs(a - (y - e)) <= 1e-6 * max(1, abs(y))
            and abs(b - (y + e)) <= 1e-6 * max(1, abs(y))
            for sx, a, b in segs
        )
    return missing == 0, f"{missing} rows without a matching error bar"


def c_span(c, probe, base):
    snap = probe["snapshot"]
    e0, e1, tol = daynum(c["x0"]), daynum(c["x1"]), c.get("tol_days", 1.5)
    found = []
    for i in data_axes(snap):
        d = snap["data"][i]
        found += d["spans"]
        found += [
            [min(fin(p["x"])), max(fin(p["x"]))]
            for p in d["polys"]
            if fin(p["x"])
        ]
    ok = any(abs(a - e0) <= tol and abs(b - e1) <= tol for a, b in found)
    return (
        ok,
        f"spans {[[round(a, 1), round(b, 1)] for a, b in found][:6]} vs [{e0}, {e1}]",
    )


# ------------------------------------------------------------ runner
def _straight(k: dict) -> bool:
    p = np.asarray(
        [
            (x, y)
            for x, y in zip(k["x"], k["y"], strict=True)
            if None not in (x, y)
        ],
        dtype=float,
    )
    if len(p) < 2 or np.ptp(p[:, 0]) == 0:
        return False
    kk, bb = np.polyfit(p[:, 0], p[:, 1], 1)
    return bool(
        np.allclose(
            p[:, 1], kk * p[:, 0] + bb, atol=1e-6 + 1e-6 * np.abs(p[:, 1]).max()
        )
    )


def _reference(k: dict) -> bool:
    xs, ys = fin(k["x"]), fin(k["y"])
    return len(ys) >= 2 and (np.ptp(ys) == 0 or np.ptp(xs) == 0)


def _flat(checks: list[dict]) -> list[dict]:
    out = []
    for c in checks:
        out += _flat(c["checks"]) if c["type"] == "any_of" else [c]
    return out


def input_pools(checks: list[dict], snap: dict, matched: set) -> derived.Pools:
    """Value groups, observation pairs and data files the contracts declare, plus claimed points."""
    groups, dist, pairs, files = [], [], [], set()
    for c in _flat(checks):
        if "file" not in c:
            continue
        files.add(c["file"])
        if c["type"] == "series":
            kind = (c.get("x") or {"kind": "order"})["kind"]
            for s in c["series"]:
                xs, ys = expected_series(c, s)
                groups.append(fin(ys))
                if kind in ("num", "date"):
                    pairs.append(
                        [
                            (a, b)
                            for a, b in zip(xs, ys, strict=True)
                            if None not in (a, b)
                        ]
                    )
        elif c["type"] == "dist":
            dist += list(_dist_groups(c).values())
        elif c["type"] in ("points", "fits"):
            for pts in _groups(c).values():
                ok = [(a, b) for a, b in pts if None not in (a, b)]
                pairs.append(ok)
                groups += [[a for a, _ in ok], [b for _, b in ok]]
        elif c["type"] == "bars":
            groups.append(fin(expected_bars(c).values()))
    claimed = [k for k in candidates(snap) if k["id"] in matched]
    return derived.build(groups, dist, pairs, files, claimed)


def unexplained(
    snap: dict,
    matched: set,
    auxiliary: list[str],
    checks: list[dict] | None = None,
) -> tuple[list[str], dict]:
    """Visible data artists no contract claimed and no derivation rule explains.

    Returns the unexplained artists and, for the explained-by-derivation ones,
    the rule that explained each (reported in the check detail).
    """
    pools = input_pools(checks or [], snap, matched)
    out, why = [], {}
    for k in candidates(snap):
        if k["id"] in matched:
            continue
        if (
            k["kind"] == "line"
            and "reference_lines" in auxiliary
            and _reference(k)
        ):
            continue
        if k["kind"] == "line" and "fit_lines" in auxiliary and _straight(k):
            continue
        rule = derived.reason(k, snap, pools)
        if rule:
            why[rule] = why.get(rule, 0) + 1
            continue
        out.append(
            f"{k['kind']} {_label_names(k) or k['label']} on axes {k['ax']}"
        )
    return out, why


def c_any_of(c, probe, base):
    res = check_oracle(c["checks"], probe, base)
    states = [r["ok"] for r in res]
    ok = True if True in states else (None if None in states else False)
    used = set().union(*(r.get("matched", set()) for r in res))
    return (
        ok,
        "; ".join(f"{r['name']}:{r['ok']} ({r['detail']})" for r in res),
        used,
    )


CHECKS = {
    "series": c_series,
    "bars": c_bars,
    "bar_labels": c_bar_labels,
    "points": c_points,
    "fits": c_fits,
    "dist": c_dist,
    "matrix": c_matrix,
    "stack": c_stack,
    "errorbars": c_errorbars,
    "span": c_span,
    "any_of": c_any_of,
    **SPEC_CHECKS,
}


def check_oracle(
    checks: list[dict],
    probe: dict,
    base: dict | None = None,
    auxiliary: list[str] | None = None,
    figure: bool = False,
) -> list[dict]:
    """Run ``checks``; with ``figure=True`` also require every visible data artist to be explained."""
    out, matched = [], set()
    for chk in checks:
        try:
            res = CHECKS[chk["type"]](chk, probe, base)
        except Exception as exc:  # noqa: BLE001 - a malformed figure fails the check, not the run
            res = (False, f"error: {type(exc).__name__}: {exc}")
        ok, detail, used = (*res, set()) if len(res) == 2 else res
        matched |= used  # claimed even when the contract fails: it already fails the figure
        out.append(
            {
                "type": chk["type"],
                "group": chk.get("group", "values"),
                "name": chk.get("name", chk["type"]),
                "ok": ok if ok is None else bool(ok),
                "detail": detail,
                "matched": used,
            }
        )
    if figure and any(
        c["type"] in DATA_CONTRACTS or c["type"] == "any_of" for c in checks
    ):
        extra, why = unexplained(
            probe["snapshot"], matched, auxiliary or [], checks
        )
        derived_note = ", ".join(f"{n} {r}" for r, n in sorted(why.items()))
        out.append(
            {
                "type": "explained",
                "group": "values",
                "name": "no unexplained data artists",
                "ok": not extra,
                "detail": "; ".join(extra[:8])
                or "every visible data artist is accounted for"
                + (f" (derived: {derived_note})" if why else ""),
                "matched": set(),
            }
        )
    if not figure:
        return out
    for r in out:  # JSON-friendly
        r["matched"] = sorted(map(list, r["matched"]))
    return out


__all__ = [
    "CHECKS",
    "check_oracle",
    "evaluate",
    "num",
    "saved_size_cm",
    "table",
]
