"""Layout defects and edit preservation computed from a probe snapshot.

* ``defects(probe)`` — text outside the canvas, clipped at an edge, overlapping
  text, legend covering data, duplicated text, missing glyphs. Implemented here
  from raw geometry, independent of ``dm.validate_figure``.
* ``preservation(base, edit, scope, target)`` — property diff for edit cases.

Value fidelity and request checks live in ``oracle.py``.
"""

from __future__ import annotations

import fnmatch
import math
import re

import numpy as np

TICK_ROLES = {"xtick", "ytick", "offset"}
POSITION_TOL = 0.03  # figure fraction; a re-run layout may shift axes slightly


# ------------------------------------------------------------ geometry
def area(poly) -> float:
    p = np.asarray(poly, dtype=float).reshape(-1, 2)
    if len(p) < 3:
        return 0.0
    x, y = p[:, 0], p[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def clip(subject, clip_poly) -> list:
    """Sutherland-Hodgman: clip polygon ``subject`` by convex polygon ``clip_poly``."""
    out = [tuple(p) for p in subject]
    c = [tuple(p) for p in clip_poly]
    if _signed_area(c) < 0:
        c = c[::-1]
    for i in range(len(c)):
        a, b = c[i - 1], c[i]
        pts, out = out, []
        for j in range(len(pts)):
            p, q = pts[j - 1], pts[j]
            pin, qin = _left(a, b, p) >= 0, _left(a, b, q) >= 0
            if qin != pin:
                out.append(_cross(a, b, p, q))
            if qin:
                out.append(q)
        if not out:
            return []
    return out


def _signed_area(p) -> float:
    return (
        sum(
            p[i - 1][0] * p[i][1] - p[i][0] * p[i - 1][1] for i in range(len(p))
        )
        / 2
    )


def _left(a, b, p) -> float:
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _cross(a, b, p, q):
    d1, d2 = _left(a, b, p), _left(a, b, q)
    t = d1 / (d1 - d2) if d1 != d2 else 0.0
    return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))


def norm(s: str) -> str:
    return " ".join(s.replace("\n", " ").split()).casefold()


def _numeric_like(s: str) -> bool:
    return bool(re.fullmatch(r"[\s\d.,%+\-\u2212\u2013$€₩()\u00d7eE^]*", s))


# ------------------------------------------------------------ defects
def defects(probe: dict) -> dict:
    """Count deterministic layout defects in a probe result's snapshot."""
    snap = probe["snapshot"]
    w_pt, h_pt = snap["figure"]["width_pt"], snap["figure"]["height_pt"]
    tight = str((snap.get("save") or {}).get("bbox_inches")).lower() == "tight"
    texts = snap["texts"]
    canvas = [(0, 0), (w_pt, 0), (w_pt, h_pt), (0, h_pt)]
    quads = [np.asarray(t["quad"], dtype=float) * [w_pt, h_pt] for t in texts]
    outside, clipped = [], []
    for t, q in zip(texts, quads, strict=True):
        if tight:
            break  # a tight bbox grows the canvas to fit every artist
        a = area(q)
        inside = area(clip(q, canvas)) / a if a else 1.0
        over = max(
            -q[:, 0].min(),
            q[:, 0].max() - w_pt,
            -q[:, 1].min(),
            q[:, 1].max() - h_pt,
        )
        if inside < 0.25:
            outside.append(f"{t['role']}:{t['s'][:40]}")
        elif over > 1.0:
            clipped.append(f"{t['role']}:{t['s'][:40]} ({over:.1f}pt)")
    overlaps, involved = [], set()
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if norm(texts[i]["s"]) == norm(texts[j]["s"]):
                continue  # identical strings are counted as duplicates
            qi, qj = quads[i], quads[j]
            if (
                qi[:, 0].max() < qj[:, 0].min()
                or qj[:, 0].max() < qi[:, 0].min()
                or qi[:, 1].max() < qj[:, 1].min()
                or qj[:, 1].max() < qi[:, 1].min()
            ):
                continue
            inter = area(clip(qi, qj))
            small = min(area(qi), area(qj))
            if inter >= 1.0 and small and inter / small >= 0.15:
                overlaps.append(f"{texts[i]['s'][:25]} x {texts[j]['s'][:25]}")
                involved.update((i, j))
    cover = [
        f"{key}:{lg['cover']}"
        for key, lg in snap["legends"].items()
        if lg["cover"]["line_px"] >= 3
        or lg["cover"]["points"] >= 1
        or lg["cover"]["bar_frac"] > 0.01
        or lg["cover"]["poly_frac"] > 0.02
    ]
    dups = _duplicates(texts)
    counts = {
        "text_outside": len(outside),
        "text_clipped": len(clipped),
        "text_overlap": len(involved),
        "legend_covers_data": len(cover),
        "duplicate_text": len(dups),
        "missing_glyphs": 1 if probe.get("missing_glyphs") else 0,
    }
    counts["total"] = sum(counts.values())
    details = {
        "text_outside": outside,
        "text_clipped": clipped,
        "text_overlap": overlaps[:20],
        "legend_covers_data": cover,
        "duplicate_text": dups,
        "missing_glyphs": (probe.get("missing_glyphs") or [])[:5],
    }
    return {"counts": counts, "details": details, "bbox_tight": tight}


def _duplicates(texts: list[dict]) -> list[str]:
    scoped: dict[tuple, list[int]] = {}
    figure_level = []
    for i, t in enumerate(texts):
        s = norm(t["s"])
        if t["role"] in TICK_ROLES or len(s) < 2 or _numeric_like(s):
            continue
        if t["ax"] is None:
            figure_level.append(i)
        scoped.setdefault((t["ax"], s), []).append(i)
    out = [
        f"ax{k[0]}:{k[1][:30]} x{len(v)}"
        for k, v in scoped.items()
        if len(v) > 1
    ]
    for i in figure_level:
        s = norm(texts[i]["s"])
        out.extend(
            f"figure~ax{k[0]}:{s[:30]}"
            for k in scoped
            if k[1] == s and k[0] is not None
        )
    return out


# ------------------------------------------------------------ preservation
def _same(key: str, a, b) -> bool:
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(
            _same(key, x, y) for x, y in zip(a, b, strict=True)
        )
    if isinstance(a, float) and isinstance(b, float):
        if key.endswith(".position"):
            return abs(a - b) <= POSITION_TOL
        return math.isclose(a, b, rel_tol=1e-3, abs_tol=1e-3)
    return a == b


def preservation(base: dict, edit: dict, scope: str, target: list[str]) -> dict:
    """Diff the flat property maps of the base and edited figures.

    ``explicit`` edits: every base property no ``target`` pattern matches must be
    unchanged (within tolerance), so ``ok`` is a hard result. ``broad`` edits:
    the diff is reported only (``ok`` is None); data preservation is enforced by
    the oracle's data contracts instead.
    """

    def is_target(k: str) -> bool:
        return any(fnmatch.fnmatchcase(k, p) for p in target)

    keys = [k for k in base if not is_target(k)]
    changed = sorted(
        k for k in keys if k not in edit or not _same(k, base[k], edit[k])
    )
    added = sorted(k for k in edit if k not in base and not is_target(k))
    return {
        "scope": scope,
        "checked": len(keys),
        "changed": changed[:60],
        "changed_n": len(changed),
        "added": added[:30],
        "rate": round(1 - len(changed) / len(keys), 4) if keys else None,
        "ok": (not changed) if scope == "explicit" else None,
    }
