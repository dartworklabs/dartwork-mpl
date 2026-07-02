"""CVD-safety enforcement gate for the shipped categorical palettes.

``gen_palettes.py`` *computes* a colour-vision-deficiency (CVD) verification
table when it generates the palettes, but nothing enforced it on the
artifact that actually ships (``dc_palettes.json``): a future hue edit could
quietly produce a palette whose colours collapse into each other for a
red-green- or blue-yellow-blind reader, and CI would stay green.

This is that gate. For every shipped palette it re-runs the generator's
exact metric — the minimum pairwise CAM02-UCS distance after a severity-100
``sRGB1+CVD`` simulation, taken across deuteranomaly / protanomaly /
tritanomaly — and requires it to clear a floor.

Two tiers:

* Strict floor :data:`_CVD_MIN_DISTANCE` (the generator's stated
  "min pairwise >= ~6-8" lower bound) for every palette by default.
* A small :data:`_CVD_ALLOWLIST` for the aesthetic palettes that
  consciously trade some CVD margin for their look (saturated jewel tones,
  low-chroma pastels, …). Each still must clear its **own** documented
  floor, so it can be relaxed only by a reviewed edit here and can never
  silently regress further. An allowlisted palette that climbs back over
  the strict floor is flagged for promotion, keeping the list honest.

colorspacious is a dev-only dependency, so the whole module skips when it
is absent (e.g. the ``test-no-extras`` CI lane).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

cspace = pytest.importorskip("colorspacious")
cspace_convert = cspace.cspace_convert

_REPO = Path(__file__).resolve().parents[1]
_PKG_JSON = (
    _REPO / "src" / "dartwork_mpl" / "asset" / "color" / "dc_palettes.json"
)

# Minimum acceptable pairwise CAM02-UCS distance under simulated CVD. From
# gen_palettes.py's own note: "CVD ok: min pairwise CAM02-UCS >= ~6-8".
_CVD_MIN_DISTANCE = 6.0

_CVD_TYPES = ("deuteranomaly", "protanomaly", "tritanomaly")

# Aesthetic palettes that consciously trade some CVD separability for their
# visual identity. Value = the palette's own floor; it must still clear
# this, so a further regression fails CI, but it is exempt from the strict
# 6.0 bar. Measured worst-case CVD distance (colorspacious 1.1.2, 2026-07)
# is in the comment; floors sit ~0.3 below to tolerate minor library jitter
# without masking a real regression.
_CVD_ALLOWLIST: dict[str, float] = {
    "jewel": 3.9,  # saturated jewel tones; protanomaly min 4.2
    "pastel": 4.5,  # low-chroma pastels; protanomaly min 4.8
    "vivid": 4.6,  # max-chroma categorical; deuteranomaly min 4.9
    "ember": 4.6,  # warm ember set; protanomaly min 4.9
    "dusty": 4.8,  # muted dusty set; protanomaly min 5.1
    "teal_indigo": 5.2,  # two-hue accent pairing; protanomaly min 5.5
    "teal_accent": 5.4,  # single teal accent + grays; min 5.7
    "coral_accent": 5.4,  # single coral accent + grays; min 5.7
}


def _load_palettes() -> dict[str, list[str]]:
    """Shipped palettes as ``name -> [hex, ...]`` (hex without ``#``)."""
    raw = json.loads(_PKG_JSON.read_text(encoding="utf-8"))
    return {name: [hx for _, hx in pairs] for name, pairs in raw.items()}


def _hex_to_rgb1(hx: str) -> list[float]:
    hx = hx.lstrip("#")
    return [int(hx[i : i + 2], 16) / 255 for i in (0, 2, 4)]


def _min_cvd_distance(hexes: list[str]) -> float:
    """Worst-case min pairwise CAM02-UCS distance across the 3 CVD types.

    Mirrors ``gen_palettes.py``'s ``verify`` exactly, generalised off its
    hard-coded 8-colour assumption.
    """
    rgb = np.array([_hex_to_rgb1(h) for h in hexes])
    n = len(hexes)
    worst = math.inf
    for cvd in _CVD_TYPES:
        sim = cspace_convert(
            rgb,
            {"name": "sRGB1+CVD", "cvd_type": cvd, "severity": 100},
            "CAM02-UCS",
        )
        pairwise_min = min(
            float(np.linalg.norm(sim[i] - sim[j]))
            for i in range(n)
            for j in range(i + 1, n)
        )
        worst = min(worst, pairwise_min)
    return worst


def _floor_for(name: str) -> float:
    return _CVD_ALLOWLIST.get(name, _CVD_MIN_DISTANCE)


def test_every_palette_meets_its_cvd_floor() -> None:
    """No shipped palette may fall below its CVD floor (strict or allowed)."""
    palettes = _load_palettes()
    failures = []
    for name, hexes in palettes.items():
        dist = _min_cvd_distance(hexes)
        floor = _floor_for(name)
        if dist < floor:
            failures.append(
                f"{name or '(default)'}: CVD min {dist:.1f} < floor {floor}"
            )
    assert not failures, "CVD-unsafe palette(s):\n  " + "\n  ".join(failures)


def test_allowlist_only_references_shipped_palettes() -> None:
    """A rename/removal must not leave a dangling allowlist exemption."""
    palettes = _load_palettes()
    unknown = sorted(set(_CVD_ALLOWLIST) - set(palettes))
    assert not unknown, f"allowlist references unknown palettes: {unknown}"


def test_allowlist_entries_still_need_the_exemption() -> None:
    """An allowlisted palette that now clears the strict bar should be
    promoted out of the allowlist so it stops hiding future regressions."""
    palettes = _load_palettes()
    stale = sorted(
        name
        for name in _CVD_ALLOWLIST
        if name in palettes
        and _min_cvd_distance(palettes[name]) >= _CVD_MIN_DISTANCE
    )
    assert not stale, (
        f"allowlisted palettes now pass the strict {_CVD_MIN_DISTANCE} bar; "
        f"remove them from _CVD_ALLOWLIST: {stale}"
    )


def test_allowlist_floors_are_below_strict_bar() -> None:
    """A floor at/above the strict bar is a mistake — it would make the
    exemption meaningless. Keeps the two tiers well-formed."""
    bad = {n: f for n, f in _CVD_ALLOWLIST.items() if f >= _CVD_MIN_DISTANCE}
    assert not bad, f"allowlist floors must be < {_CVD_MIN_DISTANCE}: {bad}"
