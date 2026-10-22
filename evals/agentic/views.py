"""Fixture access and read-only views over a probe snapshot (shared by checks)."""

from __future__ import annotations

import ast
import colorsys
import csv
import math
import operator
import re
from datetime import date
from functools import cache
from itertools import pairwise
from pathlib import Path

import numpy as np
from metrics import TICK_ROLES

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "data"
NAMING_ROLES = {"title", "title_left", "title_right", "ylabel"}
NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


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


_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def evaluate(expr: str, r: dict) -> float | None:
    """Arithmetic (+ - * / and parentheses) over a row's columns; nothing else is accepted."""

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


# ------------------------------------------------------------ names
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


def numbers(s: str) -> list[float]:
    s = s.replace(",", "").replace("\u2212", "-").replace("\u2013", "-")
    return [float(m) for m in NUM_RE.findall(s)]


def sat(hexc: str | None) -> float:
    if not hexc:
        return 0.0
    r, g, b = (int(hexc[k : k + 2], 16) / 255 for k in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)[1]


# ------------------------------------------------------------ snapshot views
def data_axes(snap: dict) -> list[int]:
    return [
        a["index"] for a in snap["axes"] if a["has_data"] and not a["colorbar"]
    ]


def fin(seq) -> list[float]:
    return [v for v in seq if v is not None]


def close(a, b, rtol=1e-3, atol=1e-6) -> bool:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return a.shape == b.shape and bool(np.allclose(a, b, rtol=rtol, atol=atol))


def texts(snap: dict, roles=None, ax=None, exclude=()) -> list[dict]:
    return [
        t
        for t in snap["texts"]
        if (roles is None or t["role"] in roles)
        and t["role"] not in exclude
        and (ax is None or t["ax"] == ax)
    ]


def center(t: dict) -> tuple[float, float]:
    q = np.asarray(t["quad"])
    return float(q[:, 0].mean()), float(q[:, 1].mean())


def candidates(snap: dict) -> list[dict]:
    """Every visible series-like data artist, with a stable id.

    Lines (except errorbar caps), bar containers and scatter collections.
    Invisible artists (hidden, alpha 0, no stroke and no marker) never count.
    """
    out = []
    for i in data_axes(snap):
        d = snap["data"][i]
        for j, ln in enumerate(d["lines"]):
            if (
                ln["data"]
                and ln["visible"]
                and len(ln["y"]) >= 2
                and ln.get("part") != "errorbar_cap"
            ):
                out.append(
                    {
                        "id": ("line", i, j),
                        "kind": "line",
                        "ax": i,
                        "x": ln["x"],
                        "y": ln["y"],
                        "label": ln["label"],
                        "legend": ln.get("legend", []),
                        "end": ln["end"],
                        "color": ln["color"],
                    }
                )
        for j, b in enumerate(d["bars"]):
            if b.get("visible", True):
                out.append(
                    {
                        "id": ("bars", i, j),
                        "kind": "bars",
                        "ax": i,
                        "x": b["pos"],
                        "y": b["values"],
                        "label": b["label"],
                        "legend": b.get("legend", []),
                        "end": None,
                        "color": (b["colors"] or [None])[0],
                    }
                )
        for j, s in enumerate(d["scatter"]):
            if s.get("visible", True) and fin(s["x"]):
                out.append(
                    {
                        "id": ("scatter", i, j),
                        "kind": "scatter",
                        "ax": i,
                        "x": s["x"],
                        "y": s["y"],
                        "label": s["label"],
                        "legend": s.get("legend", []),
                        "end": None,
                        "color": (s["colors"] or [None])[0],
                    }
                )
    return out


def identity_texts(snap: dict, cand: dict, all_cands: list[dict]) -> list[str]:
    """Texts that name ``cand``: its label, legend entries for it, its panel (if alone there), an end label."""
    names = list(cand.get("legend") or [])
    if cand["label"] and not cand["label"].startswith("_"):
        names.append(cand["label"])
    peers = [
        c for c in all_cands if c["ax"] == cand["ax"] and len(fin(c["y"])) >= 3
    ]
    if len(peers) <= 1:
        names += [t["s"] for t in texts(snap, NAMING_ROLES, ax=cand["ax"])]
    if cand["end"]:
        ex, ey = cand["end"]
        for t in texts(snap, exclude=TICK_ROLES | {"legend", "legend_title"}):
            q = np.asarray(t["quad"])
            if (
                -0.03 <= q[:, 0].min() - ex <= 0.15
                and abs(q[:, 1].mean() - ey) <= 0.12
            ):
                names.append(t["s"])
    return names


def nearest_tick(ticks: list, pos: float) -> str | None:
    if not ticks or pos is None:
        return None
    locs = sorted({t[0] for t in ticks})
    gaps = [b - a for a, b in pairwise(locs) if b > a]
    tol = 0.5 * min(gaps) if gaps else math.inf
    loc, text = min(ticks, key=lambda t: abs(t[0] - pos))
    return text if abs(loc - pos) <= tol else None


def observed_bars(snap: dict) -> list[dict]:
    """Every visible bar with its category (tick text at its position) and series (container name)."""
    out = []
    for i in data_axes(snap):
        d = snap["data"][i]
        for j, b in enumerate(d["bars"]):
            ticks = d["yticks"] if b["orientation"] == "h" else d["xticks"]
            names = [
                n
                for n in [b["label"], *b.get("legend", [])]
                if n and not n.startswith("_")
            ]
            vis = b.get("vis") or [True] * len(b["values"])
            for k, (v, p) in enumerate(zip(b["values"], b["pos"], strict=True)):
                if not vis[k]:
                    continue
                cats = [t for t in (nearest_tick(ticks, p),) if t]
                if len(b["values"]) == 1:
                    cats += names
                out.append(
                    {
                        "id": ("bars", i, j),
                        "value": v,
                        "pos": p,
                        "base": b["base"][k],
                        "width": b["widths"][k],
                        "cats": cats,
                        "series": names,
                        "orientation": b["orientation"],
                        "color": b["colors"][k],
                        "ext": b["ext"][k],
                        "ax": i,
                    }
                )
    return out


# ------------------------------------------------------------ series
def expected_series(c: dict, s: dict) -> tuple[list, list]:
    rs = rows({"file": c["file"], "where": s.get("where") or c.get("where")})
    ys = [evaluate(s["expr"], r) if "expr" in s else num(r[s["y"]]) for r in rs]
    xs: list = [None] * len(rs)
    x = c.get("x") or {"kind": "order"}
    if x["kind"] == "num":
        xs = [num(r[x["col"]]) for r in rs]
    elif x["kind"] == "date":
        xs = [daynum(r[x["col"]]) for r in rs]
    return xs, ys


def _x_ok(cx: list, xs: list, kind: str) -> bool:
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
    f = [v for v in cx if v is not None]
    return len(f) == len(cx) and all(b > a for a, b in pairwise(f))


def series_match(
    cand: dict, xs: list, ys: list, kind: str, scales=(1,), rtol=0.005
) -> bool:
    """Same order, same multiplicity, same NaN gaps (markers-only scatter: same finite rows)."""
    cy, cx = cand["y"], cand["x"]
    if (
        cand["kind"] == "scatter"
    ):  # markers cannot show a gap: compare the finite rows only
        keep = [k for k, v in enumerate(ys) if v is not None]
        ys, xs = [ys[k] for k in keep], [xs[k] for k in keep]
        pairs = [
            (a, b)
            for a, b in zip(cx, cy, strict=True)
            if a is not None and b is not None
        ]
        cx, cy = [a for a, _ in pairs], [b for _, b in pairs]
    if len(cy) != len(ys) or [v is None for v in cy] != [v is None for v in ys]:
        return False
    fy, fe = fin(cy), np.asarray(fin(ys), dtype=float)
    scale = max(np.abs(fe).max(), 1e-12) if len(fe) else 1.0
    if not any(close(fy, fe * s, rtol=rtol, atol=1e-6 * scale) for s in scales):
        return False
    return _x_ok(cx, xs, kind)
