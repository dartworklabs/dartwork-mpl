"""Which unclaimed data artists can be derived from the case input, and why.

A visible data artist that no contract claimed is still explained when its
data follows from the input by one of these general rules (first match
wins); anything else is unexplained and fails the figure:

* ``reference``: a constant line (horizontal or vertical);
* ``duplicate``: every point repeats a point of a claimed artist (context
  copies in other panels, endpoint or highlight markers);
* ``dataset``: its values (y; bar lengths) are a contiguous run of a column
  of an input file, or of a column within one category, in file order
  (context series from the same dataset);
* ``jitter``: a scatter whose value coordinate is a sub-multiset of one
  distribution group's observations (strip/jitter over a box or violin);
* ``ecdf``: a line that is the empirical CDF of one value group;
* ``statistic``: every point has a coordinate equal to a mean, median, min,
  max or common quantile of one value group;
* ``fit``: a straight line equal to the least-squares fit of one (x, y) group;
* ``leader``: a line of at most four vertices from a claimed point to a
  drawn text (a label connector).

Fabricated values match none of these: a decoy series of made-up numbers is
not a column, a statistic, a fit or a copy of claimed data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import estimators
import numpy as np
from views import fin, num, table

QUANTILE_LEVELS = (0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)
CATEGORY_MAX = 40
LEADER_DATA_TOL = (
    0.02  # end vertex within 2% of the axis span of a claimed point
)
LEADER_TEXT_TOL = 0.03  # other end within 3% of the figure from a drawn text


@dataclass
class Pools:
    groups: list[np.ndarray] = field(default_factory=list)
    dist: list[np.ndarray] = field(default_factory=list)
    pairs: list[np.ndarray] = field(default_factory=list)
    sequences: list[np.ndarray] = field(default_factory=list)
    claimed: set = field(default_factory=set)
    claimed_xy: dict = field(default_factory=dict)
    stats: np.ndarray = field(default_factory=lambda: np.empty(0))


def _key(x, y) -> tuple:
    return (float(f"{x:.6g}"), float(f"{y:.6g}"))


def _points(k: dict) -> list[tuple]:
    return [
        (a, b)
        for a, b in zip(k["x"], k["y"], strict=True)
        if a is not None and b is not None
    ]


def dataset_sequences(name: str) -> list[np.ndarray]:
    """Numeric columns of an input file, whole and within each category value."""
    rows = table(name)
    if not rows:
        return []
    cols = list(rows[0])

    def numeric(c):
        try:
            return [num(r[c]) for r in rows]
        except ValueError:
            return None

    nums = {c: v for c in cols if (v := numeric(c)) is not None}
    cats = [
        c
        for c in cols
        if c not in nums and len({r[c] for r in rows}) <= CATEGORY_MAX
    ]
    out = [np.asarray(fin(v), dtype=float) for v in nums.values()]
    for c in cats:
        for value in {r[c] for r in rows}:
            keep = [r[c] == value for r in rows]
            out += [
                np.asarray(fin([x for x, k in zip(v, keep, strict=True) if k]))
                for v in nums.values()
            ]
    return [s for s in out if len(s) >= 3]


def build(
    groups: list, dist: list, pairs: list, files: set[str], claimed: list[dict]
) -> Pools:
    p = Pools(
        groups=[np.asarray(g, dtype=float) for g in groups if len(g)],
        dist=[np.asarray(g, dtype=float) for g in dist if len(g)],
        pairs=[np.asarray(g, dtype=float) for g in pairs if len(g) >= 2],
    )
    for f in sorted(files):
        p.sequences += dataset_sequences(f)
    for k in claimed:
        pts = _points(k)
        p.claimed |= {_key(a, b) for a, b in pts}
        p.claimed_xy.setdefault(k["ax"], []).extend(pts)
    stats = []
    for g in p.groups + p.dist:
        if len(g) == 0:
            continue
        stats += [g.mean(), g.min(), g.max()]
        stats += list(
            np.quantile(g, QUANTILE_LEVELS)
        )  # numpy/pandas default (linear)
    p.stats = np.unique(np.asarray(stats, dtype=float))
    return p


def _is_stat(v: float, stats: np.ndarray) -> bool:
    if not len(stats):
        return False
    j = np.searchsorted(stats, v)
    near = stats[max(j - 1, 0) : j + 1]
    return bool(np.any(np.abs(near - v) <= 1e-6 * max(1.0, abs(v))))


def _contains(seq: np.ndarray, sub: np.ndarray) -> bool:
    """``sub`` is a contiguous run of ``seq`` (same order)."""
    n, m = len(seq), len(sub)
    if m < 3 or m > n:
        return False
    tol = 1e-6 * max(1.0, float(np.abs(seq).max()))
    return any(
        np.all(np.abs(seq[i : i + m] - sub) <= tol) for i in range(n - m + 1)
    )


def _submultiset(sub: np.ndarray, pool: np.ndarray) -> bool:
    if len(sub) < 3 or len(sub) > len(pool):
        return False
    a, b = np.sort(np.round(sub, 6)), list(np.sort(np.round(pool, 6)))
    j = 0
    for v in a:
        while j < len(b) and b[j] < v - 1e-9:
            j += 1
        if j == len(b) or abs(b[j] - v) > 1e-6 * max(1.0, abs(v)):
            return False
        j += 1
    return True


def _straight_fit(k: dict, pairs: list[np.ndarray]) -> bool:
    pts = np.asarray(_points(k), dtype=float)
    if len(pts) < 2 or np.ptp(pts[:, 0]) == 0:
        return False
    kk, bb = np.polyfit(pts[:, 0], pts[:, 1], 1)
    if not np.allclose(
        pts[:, 1],
        kk * pts[:, 0] + bb,
        atol=1e-6 + 1e-6 * np.abs(pts[:, 1]).max(),
    ):
        return False
    for xy in pairs:
        if np.ptp(xy[:, 0]) == 0:
            continue
        k0, b0 = np.polyfit(xy[:, 0], xy[:, 1], 1)
        yr = np.ptp(xy[:, 1]) or 1.0
        if (
            abs(kk - k0) <= 0.03 * abs(k0) + 1e-9
            and abs((kk - k0) * xy[:, 0].mean() + bb - b0) <= 0.03 * yr
        ):
            return True
    return False


def _near_text(pt, snap: dict) -> bool:
    x, y = pt
    for t in snap["texts"]:
        q = np.asarray(t["quad"])
        dx = max(q[:, 0].min() - x, 0.0, x - q[:, 0].max())
        dy = max(q[:, 1].min() - y, 0.0, y - q[:, 1].max())
        if max(dx, dy) <= LEADER_TEXT_TOL:
            return True
    return False


def _leader(k: dict, ln: dict | None, snap: dict, p: Pools) -> bool:
    if k["kind"] != "line" or not ln or not ln.get("figxy"):
        return False
    pts = _points(k)
    if not 2 <= len(pts) <= 4:
        return False
    meta = snap["axes"][k["ax"]]
    xs = abs(meta["xlim"][1] - meta["xlim"][0]) or 1.0
    ys = abs(meta["ylim"][1] - meta["ylim"][0]) or 1.0
    linear = meta["xscale"] == "linear" and meta["yscale"] == "linear"
    claimed = p.claimed_xy.get(k["ax"], [])
    fig = ln["figxy"]
    for end, other in ((0, -1), (-1, 0)):
        ex, ey = pts[end]
        on_data = any(
            (
                abs(ex - cx) / xs <= LEADER_DATA_TOL
                and abs(ey - cy) / ys <= LEADER_DATA_TOL
            )
            if linear
            else (ex, ey) == (cx, cy)
            for cx, cy in claimed
        )
        if on_data and _near_text(fig[other], snap):
            return True
    return False


def reason(k: dict, snap: dict, p: Pools) -> str | None:
    """Why the unclaimed artist ``k`` is derivable from the input, or None."""
    pts = _points(k)
    if not pts:
        return None
    xs = np.asarray([a for a, _ in pts], dtype=float)
    ys = np.asarray([b for _, b in pts], dtype=float)
    ln = (
        snap["data"][k["ax"]]["lines"][k["id"][2]]
        if k["kind"] == "line"
        else None
    )
    if (
        k["kind"] == "line"
        and len(pts) >= 2
        and (np.ptp(ys) == 0 or np.ptp(xs) == 0)
    ):
        return "reference"
    if all(_key(a, b) in p.claimed for a, b in pts):
        return "duplicate"
    if any(_contains(s, ys) for s in p.sequences):
        return "dataset"
    if k["kind"] == "scatter" and any(
        _submultiset(ys, g) or _submultiset(xs, g) for g in p.dist
    ):
        return "jitter"
    if k["kind"] == "line" and any(
        estimators.ecdf_ok(xs, ys, g) or estimators.ecdf_ok(ys, xs, g)
        for g in p.groups + p.dist
        if len(g) >= 2
    ):
        return "ecdf"
    if all(_is_stat(a, p.stats) or _is_stat(b, p.stats) for a, b in pts):
        return "statistic"
    if k["kind"] == "line" and _straight_fit(k, p.pairs):
        return "fit"
    if _leader(k, ln, snap, p):
        return "leader"
    return None
