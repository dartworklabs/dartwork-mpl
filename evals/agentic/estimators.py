"""Distribution estimator contracts: what a drawn distribution must equal.

Each form is recomputed from the frozen raw observations:

* histogram: bin edges are read from the bars; heights must equal the counts
  of the raw values in those bins (or the same counts as density, fraction or
  percent), and every observation must fall in a bin;
* Gaussian KDE (lines, violin bodies): the drawn curve must equal, up to one
  positive scale factor, a Gaussian kernel density of the raw values for some
  bandwidth (searched, then refined) within ``KDE_TOL`` of the peak;
* box: the median line and the box edges (Q1, Q3, linear percentiles) at the
  group's tick;
* ECDF: every distinct observation is a vertex, and at every vertex the
  height lies between the share (or percent, or count) of observations < x
  and <= x: its jump at an observation, exactly the share elsewhere.

Step histograms (``stairs``, ``hist(histtype="step"|"stepfilled")``) are read
as bin edges plus heights and checked like bars.
"""

from __future__ import annotations

import math

import numpy as np

KDE_TOL = 0.02


def hist_ok(bar: dict, vals: np.ndarray) -> bool:
    order = np.argsort([e if e is not None else np.inf for e in bar["edge0"]])
    e0 = np.asarray(bar["edge0"], dtype=float)[order]
    w = np.asarray(bar["widths"], dtype=float)[order]
    h = np.asarray(bar["values"], dtype=float)[order]
    if len(h) < 3 or not np.all(np.isfinite(h)):
        return False
    if not np.allclose(
        e0[1:], e0[:-1] + w[:-1], rtol=0, atol=1e-6 * (np.ptp(e0) or 1)
    ):
        return False  # not contiguous bins
    return edges_hist_ok(np.append(e0, e0[-1] + w[-1]), h, vals)


def edges_hist_ok(edges, heights, vals: np.ndarray) -> bool:
    """Heights equal the counts of ``vals`` in ``edges`` (or density, fraction, percent)."""
    edges = np.asarray(edges, dtype=float)
    h = np.asarray(heights, dtype=float)
    if (
        len(h) < 3
        or len(edges) != len(h) + 1
        or not np.all(np.isfinite(h))
        or not np.all(np.diff(edges) > 0)
    ):
        return False
    counts = np.histogram(vals, bins=edges)[0].astype(float)
    n, w = len(vals), np.diff(edges)
    if counts.sum() != n:
        return False
    return any(
        np.allclose(h, f, rtol=1e-6, atol=1e-9)
        for f in (counts, counts / (n * w), counts / n, counts / n * 100)
    )


def ecdf_ok(xs, ys, vals: np.ndarray) -> bool:
    """The drawn vertices are the empirical CDF of ``vals`` (share, percent or count)."""
    xs, ys = np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)
    ok = np.isfinite(xs) & np.isfinite(ys)
    xs, ys = xs[ok], ys[ok]
    v = np.sort(np.asarray(vals, dtype=float))
    if len(xs) < 3 or len(v) < 2:
        return False
    tol = 1e-6 * max(1.0, float(np.abs(v).max()))
    if not all(np.any(np.abs(xs - u) <= tol) for u in np.unique(v)):
        return False  # some observation is not drawn
    n = len(v)
    upto = np.searchsorted(v, xs + tol, side="right") / n  # share <= x
    below = np.searchsorted(v, xs - tol, side="left") / n  # share < x
    return any(
        bool(
            np.all(ys >= below * s - 1e-9 * s)
            and np.all(ys <= upto * s + 1e-9 * s)
        )
        for s in (1.0, 100.0, float(n))
    )


def _kde(vals: np.ndarray, xs: np.ndarray, h: float) -> np.ndarray:
    z = (xs[:, None] - vals[None, :]) / h
    return np.exp(-0.5 * z * z).sum(axis=1) / (
        len(vals) * h * math.sqrt(2 * math.pi)
    )


def _scaled_error(f: np.ndarray, ys: np.ndarray) -> float:
    denom = float(f @ f)
    if denom <= 0 or ys.max() <= 0:
        return math.inf
    s = float(f @ ys) / denom
    if s <= 0:
        return math.inf
    return float(np.max(np.abs(s * f - ys)) / ys.max())


def kde_error(xs, ys, vals: np.ndarray) -> float:
    """Smallest max-relative error between ``ys`` and a scaled Gaussian KDE of ``vals`` at ``xs``."""
    xs, ys = np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)
    ok = np.isfinite(xs) & np.isfinite(ys)
    xs, ys = xs[ok], ys[ok]
    if len(xs) < 20 or len(vals) < 2:
        return math.inf
    sd = float(np.std(vals, ddof=1)) or 1.0
    grid = np.geomspace(0.01 * sd, 3 * sd, 140)
    errs = [_scaled_error(_kde(vals, xs, h), ys) for h in grid]
    k = int(np.argmin(errs))
    lo, hi = grid[max(k - 1, 0)], grid[min(k + 1, len(grid) - 1)]
    fine = np.geomspace(lo, hi, 60)
    return min(min(errs), *(_scaled_error(_kde(vals, xs, h), ys) for h in fine))


def kde_ok(xs, ys, vals: np.ndarray) -> bool:
    xs = np.asarray(xs, dtype=float)
    span = np.ptp(vals) or 1.0
    covers = (
        np.nanmin(xs) <= vals.min() + 0.05 * span
        and np.nanmax(xs) >= vals.max() - 0.05 * span
    )
    return bool(covers) and kde_error(xs, ys, vals) <= KDE_TOL


def violin_profile(px, py) -> tuple[np.ndarray, np.ndarray]:
    """Half-width of a vertical violin body at each y (pairs of mirrored vertices)."""
    px, py = np.asarray(px, dtype=float), np.asarray(py, dtype=float)
    ys = np.unique(np.round(py, 9))
    half = np.asarray([np.ptp(px[np.isclose(py, y)]) / 2 for y in ys])
    return ys, half


def quartiles(vals: np.ndarray) -> tuple[float, float, float]:
    q1, med, q3 = np.percentile(vals, [25, 50, 75])
    return float(q1), float(med), float(q3)
