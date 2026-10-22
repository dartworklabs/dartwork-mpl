"""Value-fidelity and request checks declared in a case's ``oracle`` list.

Expected values are derived from the frozen fixture CSVs. Data contracts bind
identity (series/category/group name -> data), paired coordinates, order,
multiplicity and NaN masks: a value merely appearing somewhere in the figure
never passes. ``check_oracle`` returns one result per declared check; the
``group`` field separates data fidelity (``values``) from request compliance
(``spec``).
"""

from __future__ import annotations

import ast
import colorsys
import csv
import fnmatch
import math
import operator
import re
from datetime import date
from functools import cache
from itertools import pairwise
from pathlib import Path

import numpy as np
from metrics import TICK_ROLES, defects

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "data"
NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
NAMING_ROLES = {"title", "title_left", "title_right", "ylabel"}


# ------------------------------------------------------------ fixtures
@cache
def table(name: str) -> tuple[dict, ...]:
    with open(FIXTURES / name, encoding="utf-8", newline="") as f:
        return tuple(csv.DictReader(f))


def num(s) -> float | None:
    s = str(s).strip().replace(",", "")
    if s.lower() in ("", "n/a", "na", "nan", "none"):
        return None
    return float(s)


def daynum(s: str) -> float:
    parts = [int(p) for p in re.split(r"[-./]", s.strip())[:3]]
    parts += [1] * (3 - len(parts))
    return float((date(*parts) - date(1970, 1, 1)).days)


def rows(spec: dict) -> list[dict]:
    where = spec.get("where") or {}
    return [
        r
        for r in table(spec["file"])
        if all(r[k] == str(v) for k, v in where.items())
    ]


def key(s: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", str(s).casefold())


def named(text: str, aliases: list[str]) -> bool:
    """True if ``text`` names one of ``aliases`` (1-2 letter Latin aliases must be a whole token)."""
    tk = key(text)
    tokens = {key(t) for t in re.split(r"[\s_/(),:;\-]+", str(text)) if t}
    for a in aliases:
        ka = key(a)
        short = len(ka) <= 2 and ka.isascii()
        if ka and ((short and ka in tokens) or (not short and ka in tk)):
            return True
    return False


# ------------------------------------------------------------ snapshot views
def data_axes(snap: dict) -> list[int]:
    return [
        a["index"] for a in snap["axes"] if a["has_data"] and not a["colorbar"]
    ]


def _fin(seq) -> list[float]:
    return [v for v in seq if v is not None]


def _close(a, b, rtol=1e-3, atol=1e-6) -> bool:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return a.shape == b.shape and bool(np.allclose(a, b, rtol=rtol, atol=atol))


def _texts(snap: dict, roles=None, ax=None, exclude=()) -> list[dict]:
    return [
        t
        for t in snap["texts"]
        if (roles is None or t["role"] in roles)
        and t["role"] not in exclude
        and (ax is None or t["ax"] == ax)
    ]


def _center(t: dict) -> tuple[float, float]:
    q = np.asarray(t["quad"])
    return float(q[:, 0].mean()), float(q[:, 1].mean())


def candidates(snap: dict) -> list[dict]:
    """Every series-like artist: data lines, vertical/horizontal bar containers, scatter."""
    out = []
    for i in data_axes(snap):
        d = snap["data"][i]
        out += [
            {
                "kind": "line",
                "ax": i,
                "x": ln["x"],
                "y": ln["y"],
                "label": ln["label"],
                "end": ln["end"],
                "color": ln["color"],
            }
            for ln in d["lines"]
            if ln["data"] and ln["visible"] and len(ln["y"]) >= 2
        ]
        out += [
            {
                "kind": "bars",
                "ax": i,
                "x": b["pos"],
                "y": b["values"],
                "label": b["label"],
                "end": None,
                "color": (b["colors"] or [None])[0],
            }
            for b in d["bars"]
        ]
        out += [
            {
                "kind": "scatter",
                "ax": i,
                "x": s["x"],
                "y": s["y"],
                "label": s["label"],
                "end": None,
                "color": (s["colors"] or [None])[0],
            }
            for s in d["scatter"]
        ]
    return out


def identity_texts(snap: dict, cand: dict, all_cands: list[dict]) -> list[str]:
    """Texts that name ``cand``: its label, its panel (if it is alone there), an end label."""
    names = []
    if cand["label"] and not cand["label"].startswith("_"):
        names.append(cand["label"])
    peers = [
        c for c in all_cands if c["ax"] == cand["ax"] and len(_fin(c["y"])) >= 3
    ]
    if len(peers) <= 1:
        names += [t["s"] for t in _texts(snap, NAMING_ROLES, ax=cand["ax"])]
    if cand["end"]:
        ex, ey = cand["end"]
        for t in _texts(snap, exclude=TICK_ROLES | {"legend", "legend_title"}):
            q = np.asarray(t["quad"])
            if (
                -0.03 <= q[:, 0].min() - ex <= 0.15
                and abs(q[:, 1].mean() - ey) <= 0.12
            ):
                names.append(t["s"])
    return names


# ------------------------------------------------------------ series
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _eval(expr: str, r: dict) -> float | None:
    """Arithmetic (+ - * / and parentheses) over a row's columns; no other syntax is accepted."""

    def walk(n):
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            a, b = walk(n.left), walk(n.right)
            return None if a is None or b is None else _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            v = walk(n.operand)
            return None if v is None else -v
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.Name):
            return num(r[n.id])
        raise ValueError(f"unsupported expression node {type(n).__name__}")

    return walk(ast.parse(expr, mode="eval").body)


def expected_series(c: dict, s: dict) -> tuple[list, list]:
    rs = rows({"file": c["file"], "where": s.get("where") or c.get("where")})
    ys = [_eval(s["expr"], r) if "expr" in s else num(r[s["y"]]) for r in rs]
    xs: list = [None] * len(rs)
    x = c.get("x") or {"kind": "order"}
    if x["kind"] == "num":
        xs = [num(r[x["col"]]) for r in rs]
    elif x["kind"] == "date":
        xs = [daynum(r[x["col"]]) for r in rs]
    return xs, ys


def series_match(
    cand: dict, xs: list, ys: list, kind: str, scales=(1,), rtol=0.005
) -> bool:
    cy = cand["y"]
    if len(cy) != len(ys) or [v is None for v in cy] != [v is None for v in ys]:
        return False  # multiplicity or NaN-gap mismatch
    fy, fe = _fin(cy), np.asarray(_fin(ys), dtype=float)
    scale = max(np.abs(fe).max(), 1e-12) if len(fe) else 1.0
    if not any(
        _close(fy, fe * s, rtol=rtol, atol=1e-6 * scale) for s in scales
    ):
        return False
    cx = cand["x"]
    if kind == "num":
        return all(
            a is not None
            and b is not None
            and abs(a - b) <= 1e-6 * max(1, abs(b))
            for a, b in zip(cx, xs, strict=True)
        )
    if kind == "date":
        return all(
            a is not None and abs(a - b) <= 0.5
            for a, b in zip(cx, xs, strict=True)
        )
    fx = [v for v in cx if v is not None]
    return len(fx) == len(cx) and all(b > a for a, b in pairwise(fx))


def _c_series(c, probe, base):
    snap = probe["snapshot"]
    cands = [
        k
        for k in candidates(snap)
        if k["kind"] in c.get("artists", ["line", "bars", "scatter"])
    ]
    kind = (c.get("x") or {"kind": "order"})["kind"]
    problems = []
    for s in c["series"]:
        xs, ys = expected_series(c, s)
        hits = [
            k
            for k in cands
            if series_match(k, xs, ys, kind, c.get("scales", [1]))
        ]
        if not hits:
            problems.append(
                f"{s['aliases'][0]}: no artist with this data/order/NaN mask"
            )
        elif c.get("identity", "named") == "named" and not any(
            named(t, s["aliases"])
            for k in hits
            for t in identity_texts(snap, k, cands)
        ):
            problems.append(
                f"{s['aliases'][0]}: data found but not named {s['aliases']}"
            )
    return not problems, "; ".join(
        problems
    ) or "all series matched with identity"


# ------------------------------------------------------------ bars
def _nearest_tick(ticks: list, pos: float) -> str | None:
    if not ticks:
        return None
    locs = sorted({t[0] for t in ticks})
    gaps = [b - a for a, b in pairwise(locs) if b > a]
    tol = 0.5 * min(gaps) if gaps else math.inf
    loc, text = min(ticks, key=lambda t: abs(t[0] - pos))
    return text if abs(loc - pos) <= tol else None


def observed_bars(snap: dict) -> list[dict]:
    out = []
    for i in data_axes(snap):
        d = snap["data"][i]
        for b in d["bars"]:
            ticks = d["yticks"] if b["orientation"] == "h" else d["xticks"]
            lab = (
                b["label"]
                if b["label"] and not b["label"].startswith("_")
                else None
            )
            for j, (v, p) in enumerate(zip(b["values"], b["pos"], strict=True)):
                cats = [
                    t
                    for t in (
                        _nearest_tick(ticks, p) if p is not None else None,
                    )
                    if t
                ]
                if len(b["values"]) == 1 and lab:
                    cats.append(lab)
                out.append(
                    {
                        "value": v,
                        "cats": cats,
                        "series": lab,
                        "orientation": b["orientation"],
                        "color": b["colors"][j],
                        "ext": b["ext"][j],
                        "ax": i,
                    }
                )
    return out


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
    agg = c.get("agg")
    out = {}
    for k, vals in groups.items():
        fin = _fin(vals)
        if agg == "mean":
            out[k] = float(np.mean(fin)) if fin else None
        elif agg == "sum":
            out[k] = float(np.sum(fin)) if fin else None
        else:
            if len(vals) != 1:
                raise ValueError(f"duplicate rows for {k} without agg")
            out[k] = vals[0]
    return out


def _c_bars(c, probe, base):
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
    used, problems = set(), []
    for (cat, ser), v in exp.items():
        if v is None:
            continue
        cal = [cat, *cat_alias.get(cat, [])]
        sal = [ser, *ser_alias.get(ser, [])] if ser else None
        hit = None
        for j, b in enumerate(obs):
            if j in used or b["value"] is None:
                continue
            if not any(named(t, cal) for t in b["cats"]):
                continue
            if sal and not (b["series"] and named(b["series"], sal)):
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
    extra = [
        b
        for j, b in enumerate(obs)
        if j not in used and b["value"] not in (None, 0.0)
    ]
    if extra:
        problems.append(f"{len(extra)} extra/duplicate bars")
    return not problems, "; ".join(
        problems[:6]
    ) or f"{len(used)} bars matched category->value"


def _numbers(s: str) -> list[float]:
    s = s.replace(",", "").replace("\u2212", "-").replace("\u2013", "-")
    return [float(m) for m in NUM_RE.findall(s)]


def _c_bar_labels(c, probe, base):
    snap = probe["snapshot"]
    texts = _texts(snap, exclude=TICK_ROLES | {"legend", "legend_title"})
    missing = 0
    bars = [b for b in observed_bars(snap) if b["value"] is not None]
    for b in bars:
        x0, y0, x1, y1 = b["ext"]
        end = (
            ((x1 if b["value"] >= 0 else x0), (y0 + y1) / 2)
            if b["orientation"] == "h"
            else ((x0 + x1) / 2, (y1 if b["value"] >= 0 else y0))
        )
        ok = False
        for t in texts:
            cx, cy = _center(t)
            if math.hypot(cx - end[0], cy - end[1]) <= c.get("radius", 0.08):
                ok |= any(
                    abs(n - b["value"] * s) <= c.get("atol", 0.051)
                    for n in _numbers(t["s"])
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


def _c_points(c, probe, base):
    snap = probe["snapshot"]
    colls = [s for i in data_axes(snap) for s in snap["data"][i]["scatter"]]
    exp = _groups(c)
    aliases = (c.get("by") or {}).get("aliases") or {}
    problems = []
    total_obs = sum(len(_pairs(s["x"], s["y"])) for s in colls)
    total_exp = sum(
        len(_pairs([a for a, _ in v], [b for _, b in v])) for v in exp.values()
    )
    for g, pts in exp.items():
        want = _pairs([a for a, _ in pts], [b for _, b in pts])
        mine = (
            colls
            if g is None
            else [
                s for s in colls if named(s["label"], [g, *aliases.get(g, [])])
            ]
        )
        got = sorted(p for s in mine for p in _pairs(s["x"], s["y"]))
        if got != want:
            problems.append(
                f"{g}: {len(got)} named points vs {len(want)} expected or coordinates differ"
            )
    if total_obs != total_exp:
        problems.append(f"{total_obs} points drawn vs {total_exp} rows")
    return not problems, "; ".join(
        problems
    ) or f"{total_exp} points matched per group"


def _c_fits(c, probe, base):
    snap = probe["snapshot"]
    colls = [s for i in data_axes(snap) for s in snap["data"][i]["scatter"]]
    lines = [
        ln
        for i in data_axes(snap)
        for ln in snap["data"][i]["lines"]
        if ln["data"]
    ]
    aliases = (c.get("by") or {}).get("aliases") or {}
    problems = []
    for g, pts in _groups(c).items():
        xy = np.asarray([p for p in pts if None not in p], dtype=float)
        k, b0 = np.polyfit(xy[:, 0], xy[:, 1], 1)
        al = [g, *aliases.get(g, [])]
        colors = {
            col for s in colls if named(s["label"], al) for col in s["colors"]
        }
        ok = False
        for ln in lines:
            pts2 = np.asarray(
                [
                    (x, y)
                    for x, y in zip(ln["x"], ln["y"], strict=True)
                    if None not in (x, y)
                ],
                dtype=float,
            )
            if (
                len(pts2) < 2
                or np.ptp(pts2[:, 0]) == 0
                or not (named(ln["label"], al) or ln["color"] in colors)
            ):
                continue
            kk, bb = np.polyfit(pts2[:, 0], pts2[:, 1], 1)
            straight = np.allclose(
                pts2[:, 1],
                kk * pts2[:, 0] + bb,
                atol=1e-6 + 1e-6 * np.abs(pts2[:, 1]).max(),
            )
            yr = np.ptp(xy[:, 1]) or 1.0
            ok |= (
                straight
                and abs(kk - k) <= 0.03 * abs(k) + 1e-9
                and abs((kk - k) * xy[:, 0].mean() + bb - b0) <= 0.03 * yr
            )
        if not ok:
            problems.append(
                f"{g}: no fit line (slope {k:.3f}) tied to the group by label or colour"
            )
    return not problems, "; ".join(problems) or "fit per group matched"


# ------------------------------------------------------------ distributions
def _dist_groups(c: dict) -> dict:
    out: dict = {}
    for r in rows(c):
        v = num(r[c["value"]])
        if v is not None:
            out.setdefault(r[c["by"]["col"]], []).append(v)
    return {g: np.asarray(v) for g, v in out.items()}


def _hist_ok(b: dict, vals: np.ndarray) -> bool:
    order = np.argsort([e if e is not None else np.inf for e in b["edge0"]])
    e0 = np.asarray(b["edge0"], dtype=float)[order]
    w = np.asarray(b["widths"], dtype=float)[order]
    h = np.asarray(b["values"], dtype=float)[order]
    if (
        len(h) < 3
        or not np.all(np.isfinite(h))
        or not np.allclose(
            e0[1:], e0[:-1] + w[:-1], rtol=0, atol=1e-6 * (np.ptp(e0) or 1)
        )
    ):
        return False
    counts = np.histogram(vals, bins=np.append(e0, e0[-1] + w[-1]))[0].astype(
        float
    )
    n = len(vals)
    if counts.sum() != n:
        return False
    return any(
        np.allclose(h, f, rtol=1e-6, atol=1e-9)
        for f in (counts, counts / (n * w), counts / n, counts / n * 100)
    )


def _c_dist(c, probe, base):
    snap = probe["snapshot"]
    aliases = c["by"].get("aliases") or {}
    groups = _dist_groups(c)
    accept = c.get("accept", ["hist", "box", "violin", "kde"])
    problems = []
    for g, vals in groups.items():
        al = [g, *aliases.get(g, [])]
        forms = []
        for i in data_axes(snap):
            d = snap["data"][i]
            if "hist" in accept:
                forms += [
                    "hist"
                    for b in d["bars"]
                    if named(b["label"], al) and _hist_ok(b, vals)
                ]
            if "box" in accept:
                med = float(np.median(vals))
                forms += [
                    "box"
                    for x0, x1, y in d["hsegs"]
                    if abs(y - med) <= 1e-6 * max(1, abs(med))
                    and named(
                        _nearest_tick(d["xticks"], (x0 + x1) / 2) or "", al
                    )
                ]
                forms += [
                    "box"
                    for x, y0, y1 in d["vsegs"]
                    if abs(x - med) <= 1e-6 * max(1, abs(med))
                    and named(
                        _nearest_tick(d["yticks"], (y0 + y1) / 2) or "", al
                    )
                ]
            if "violin" in accept:
                for p in d["polys"]:
                    px, py = np.asarray(_fin(p["x"])), np.asarray(_fin(p["y"]))
                    if (
                        len(px)
                        and named(
                            _nearest_tick(d["xticks"], float(px.mean())) or "",
                            al,
                        )
                        and abs(py.min() - vals.min()) <= 1e-6 * np.ptp(vals)
                        and abs(py.max() - vals.max()) <= 1e-6 * np.ptp(vals)
                    ):
                        forms.append("violin")
            if "kde" in accept:
                for ln in d["lines"]:
                    xy = np.asarray(
                        [
                            (x, y)
                            for x, y in zip(ln["x"], ln["y"], strict=True)
                            if None not in (x, y)
                        ],
                        dtype=float,
                    )
                    if (
                        ln["data"]
                        and len(xy) >= 20
                        and named(ln["label"], al)
                        and xy[:, 0].min() <= vals.min()
                        and xy[:, 0].max() >= vals.max()
                        and abs(np.trapezoid(xy[:, 1], xy[:, 0]) - 1) <= 0.05
                    ):
                        forms.append("kde")
        if not forms:
            problems.append(
                f"{g}: no {accept} form matches its {len(vals)} values"
            )
    return not problems, "; ".join(problems) or "every group drawn faithfully"


# ------------------------------------------------------------ matrix / stack / errorbars / span
def _c_matrix(c, probe, base):
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
            rvars = [var(_nearest_tick(d["yticks"], y)) for y in im["ys"]]
            cvars = [var(_nearest_tick(d["xticks"], x)) for x in im["xs"]]
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
            texts = _texts(snap, ax=i, exclude=TICK_ROLES)
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
                            math.hypot(_center(t)[0] - fx, _center(t)[1] - fy)
                            <= pitch / 2
                            and any(
                                abs(n - round(want, 2)) <= 0.0051
                                for n in _numbers(t["s"])
                            )
                            for t in texts
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


def _c_stack(c, probe, base):
    snap = probe["snapshot"]
    x = c["x"]
    rs = rows(c)
    xs = np.asarray(
        [
            num(r[x["col"]]) if x["kind"] == "num" else daynum(r[x["col"]])
            for r in rs
        ]
    )
    polys = [p for i in data_axes(snap) for p in snap["data"][i]["polys"]]
    problems = []
    for layer in c["layers"]:
        want = np.asarray([num(r[layer["y"]]) for r in rs], dtype=float)
        mine = [p for p in polys if named(p["label"], layer["aliases"])]
        ok = False
        for p in mine:
            px, py = np.asarray(_fin(p["x"])), np.asarray(_fin(p["y"]))
            idx = np.abs(px[:, None] - xs[None, :]).argmin(axis=1)
            if np.any(np.abs(px - xs[idx]) > 1e-6 * max(1, np.abs(xs).max())):
                continue
            thick = np.asarray(
                [
                    np.ptp(py[idx == k]) if np.any(idx == k) else np.nan
                    for k in range(len(xs))
                ]
            )
            ok |= bool(np.allclose(thick, want, rtol=1e-6, atol=1e-6))
        if not ok:
            problems.append(
                f"{layer['aliases'][0]}: no named layer with these thicknesses"
            )
    return not problems, "; ".join(problems) or "all layers matched"


def _c_errorbars(c, probe, base):
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


def _c_span(c, probe, base):
    snap = probe["snapshot"]
    e0, e1, tol = daynum(c["x0"]), daynum(c["x1"]), c.get("tol_days", 1.5)
    found = []
    for i in data_axes(snap):
        d = snap["data"][i]
        found += d["spans"]
        found += [
            [min(_fin(p["x"])), max(_fin(p["x"]))]
            for p in d["polys"]
            if _fin(p["x"])
        ]
    ok = any(abs(a - e0) <= tol and abs(b - e1) <= tol for a, b in found)
    return (
        ok,
        f"spans {[[round(a, 1), round(b, 1)] for a, b in found][:6]} vs [{e0}, {e1}]",
    )


# ------------------------------------------------------------ request checks
def _c_text(c, probe, base):
    pool = [t["s"] for t in _texts(probe["snapshot"], c.get("roles"))]
    missing = [
        item[0] if isinstance(item, list) else item
        for item in c["contains"]
        if not any(
            named(s, item if isinstance(item, list) else [item]) for s in pool
        )
    ]
    return not missing, f"missing {missing}" if missing else "all present"


def _c_regex(c, probe, base):
    pat = re.compile(c["pattern"])
    n = sum(
        1
        for t in _texts(probe["snapshot"], c.get("roles"))
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


def _c_size(c, probe, base):
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


def _c_scale(c, probe, base):
    snap = probe["snapshot"]
    vals = [snap["axes"][i][f"{c['axis']}scale"] for i in data_axes(snap)]
    return c["value"] in vals, f"{c['axis']}scale={vals}"


def _c_twin(c, probe, base):
    pairs = [
        a["index"]
        for a in probe["snapshot"]["axes"]
        if a["twins"] and not a["colorbar"]
    ]
    return len(pairs) >= 2, f"axes with a same-position twin: {pairs}"


def _c_legend(c, probe, base):
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


def _c_panel_ratio(c, probe, base):
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


def _c_grid(c, probe, base):
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


def _c_same_lim(c, probe, base):
    snap = probe["snapshot"]
    lims = [tuple(snap["axes"][i][f"{c['axis']}lim"]) for i in data_axes(snap)]
    same = len(lims) > 1 and all(
        np.allclose(lim, lims[0], rtol=1e-6) for lim in lims
    )
    return (
        same,
        f"{len(set(lims))} distinct {c['axis']}lim over {len(lims)} axes",
    )


def _c_count(c, probe, base):
    n = len(data_axes(probe["snapshot"]))
    op = c.get("op", "eq")
    return {"eq": n == c["n"], "ge": n >= c["n"], "le": n <= c["n"]}[
        op
    ], f"data_axes={n} ({op} {c['n']})"


def _c_bars_sorted(c, probe, base):
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


def _sat(hexc: str | None) -> float:
    if not hexc:
        return 0.0
    r, g, b = (int(hexc[k : k + 2], 16) / 255 for k in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)[1]


def _c_highlight(c, probe, base):
    snap = probe["snapshot"]
    if c.get("kind") == "bar":
        bars = [b for b in observed_bars(snap) if b["value"] is not None]
        tgt = [
            b for b in bars if any(named(t, c["aliases"]) for t in b["cats"])
        ]
        rest = [b for b in bars if b not in tgt]
        if len(tgt) != 1 or not rest:
            return False, f"{len(tgt)} target bars"
        ok = (
            _sat(tgt[0]["color"]) >= 0.25
            and max(_sat(b["color"]) for b in rest) <= 0.15
        )
        return (
            ok,
            f"target sat {_sat(tgt[0]['color']):.2f}, others max {max(_sat(b['color']) for b in rest):.2f}",
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
        max(_sat(k["color"]) for k in tgt),
        max(_sat(k["color"]) for o in others for k in o),
    )
    return (
        ts >= 0.25 and rest <= 0.15,
        f"target sat {ts:.2f}, others max {rest:.2f}",
    )


def _c_end_labels(c, probe, base):
    snap = probe["snapshot"]
    every = [a for s in c["series"] for a in s["aliases"]]
    if any(
        named(t, every) for lg in snap["legends"].values() for t in lg["texts"]
    ):
        return False, "a legend still lists the series"
    cands = [k for k in candidates(snap) if k["kind"] == "line"]
    texts = _texts(snap, exclude=TICK_ROLES | {"legend", "legend_title"})
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
                    for t in texts
                )
        if not ok:
            missing.append(s["aliases"][0])
    return (
        not missing,
        f"no end label for {missing}" if missing else "all labelled",
    )


def _c_preset(c, probe, base):
    styles = probe.get("styles") or []
    return any(
        s.startswith(p) for s in styles for p in c["prefix"]
    ), f"styles used {styles}"


def _c_fontsize_delta(c, probe, base):
    if not base or not base.get("snapshot"):
        return False, "no base snapshot"
    bp, ep = base["snapshot"]["props"], probe["snapshot"]["props"]
    keys = [k for k in bp if fnmatch.fnmatchcase(k, c["key"])]
    deltas = {k: round(ep[k] - bp[k], 3) if k in ep else None for k in keys}
    ok = bool(keys) and all(
        d is not None and c["min"] <= d <= c["max"] for d in deltas.values()
    )
    return ok, f"deltas {deltas}"


def _c_not_worse(c, probe, base):
    if not base or not base.get("snapshot"):
        return False, "no base snapshot"
    b, e = defects(base)["counts"]["total"], defects(probe)["counts"]["total"]
    return e <= b, f"defects base {b} -> edit {e}"


def _c_any_of(c, probe, base):
    res = check_oracle(c["checks"], probe, base)
    return any(r["ok"] for r in res), "; ".join(
        f"{r['name']}:{r['ok']} ({r['detail']})" for r in res
    )


CHECKS = {
    "series": _c_series,
    "bars": _c_bars,
    "bar_labels": _c_bar_labels,
    "points": _c_points,
    "fits": _c_fits,
    "dist": _c_dist,
    "matrix": _c_matrix,
    "stack": _c_stack,
    "errorbars": _c_errorbars,
    "span": _c_span,
    "text": _c_text,
    "regex": _c_regex,
    "size": _c_size,
    "scale": _c_scale,
    "twin": _c_twin,
    "legend": _c_legend,
    "panel_ratio": _c_panel_ratio,
    "grid": _c_grid,
    "same_lim": _c_same_lim,
    "count": _c_count,
    "bars_sorted": _c_bars_sorted,
    "highlight": _c_highlight,
    "end_labels": _c_end_labels,
    "preset": _c_preset,
    "fontsize_delta": _c_fontsize_delta,
    "defects_not_worse": _c_not_worse,
    "any_of": _c_any_of,
}


def check_oracle(
    checks: list[dict], probe: dict, base: dict | None = None
) -> list[dict]:
    out = []
    for chk in checks:
        try:
            ok, detail = CHECKS[chk["type"]](chk, probe, base)
        except Exception as exc:  # noqa: BLE001 - a malformed figure fails the check, not the run
            ok, detail = False, f"error: {type(exc).__name__}: {exc}"
        out.append(
            {
                "type": chk["type"],
                "group": chk.get("group", "values"),
                "name": chk.get("name", chk["type"]),
                "ok": bool(ok),
                "detail": detail,
            }
        )
    return out
