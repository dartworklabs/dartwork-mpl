"""Freeze every color value dartwork-mpl ships.

This is the control that makes color-system work reviewable. The generator,
the metrics, the gates and the docs may all change freely; if a single
shipped hex moves, this test fails and names the surface that moved.

Five surfaces are hashed independently so a failure is diagnosable without
reading any color theory:

``named``      every color name added to matplotlib's named-color mapping
``colormaps``  every added colormap, sampled at 256 stops
``presets``    each style preset's prop_cycle and color-valued rcParams
``discrete``   ``dm.colors(name, n)`` over the full family x n x reverse grid
``curated``    the hand-tuned ``CURATED`` palettes

The expected digests below are a deliberate freeze of an approved design.
Never edit them to make a failing test pass. Regenerate them only when a
color change has been reviewed and accepted, with::

    uv run python tests/test_shipped_colors_hash.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import matplotlib as mpl
import pytest

import dartwork_mpl as dm
from dartwork_mpl import style
from dartwork_mpl._colors._curated import CURATED

# Prefixes under which dartwork-mpl registers colors into matplotlib.
_DM_PREFIXES = ("ad.", "cu.", "dc.", "md.", "oc.", "pr.", "tw.")

# Widest n the public discrete API is exercised over. Values outside a
# family's supported range are recorded as their exception type, so the
# domain boundary is frozen alongside the colors.
_MAX_N = 12


def _hex(value: Any) -> str:
    return mpl.colors.to_hex(value, keep_alpha=True)


def _family_name(entry: dict[str, object]) -> str:
    return str(entry["name"])


def _named_surface() -> list[str]:
    mapping = mpl.colors.get_named_colors_mapping()
    return [
        f"{name} {_hex(mapping[name])}"
        for name in sorted(mapping)
        if name.startswith(_DM_PREFIXES)
    ]


def _colormap_surface() -> list[str]:
    rows = []
    for name in sorted(mpl.colormaps):
        if not name.startswith(_DM_PREFIXES):
            continue
        cmap = mpl.colormaps[name]
        stops = "".join(_hex(cmap(index / 255)) for index in range(256))
        rows.append(f"{name} {stops}")
    return rows


def _preset_surface() -> list[str]:
    rows = []
    with mpl.rc_context():
        for preset in sorted(style.presets_dict()):
            style.use(preset)
            cycle = ",".join(
                _hex(entry["color"])
                for entry in mpl.rcParams["axes.prop_cycle"]
            )
            rows.append(f"{preset} axes.prop_cycle {cycle}")
            for key in sorted(mpl.rcParams):
                if "color" not in key or key == "axes.prop_cycle":
                    continue
                rows.append(f"{preset} {key} {mpl.rcParams[key]!r}")
    return rows


def _discrete_surface() -> list[str]:
    rows = []
    for entry in sorted(dm.list_colors(), key=_family_name):
        name = f"dc.{_family_name(entry)}"
        for n in range(1, _MAX_N + 1):
            for reverse in (False, True):
                try:
                    value = dm.colors(name, n, reverse=reverse)
                except Exception as error:
                    # The exception type is the value: it freezes the domain
                    # boundary of each family alongside its colors.
                    token = type(error).__name__
                else:
                    token = ",".join(_hex(item) for item in value)
                rows.append(f"{name} n={n} r={int(reverse)} {token}")
    return rows


def _curated_surface() -> list[str]:
    return [
        f"{key} {json.dumps(CURATED[key], sort_keys=True)}"
        for key in sorted(CURATED)
    ]


SURFACES: dict[str, Callable[[], list[str]]] = {
    "colormaps": _colormap_surface,
    "curated": _curated_surface,
    "discrete": _discrete_surface,
    "named": _named_surface,
    "presets": _preset_surface,
}

# Row counts are pinned separately from the digests so that a surface which
# silently loses entries fails with a count mismatch rather than an opaque
# hash mismatch.
EXPECTED_COUNTS = {
    "colormaps": 99,
    "curated": 15,
    "discrete": 1344,
    "named": 1272,
    "presets": 588,
}

EXPECTED_DIGESTS = {
    "colormaps": "fd188b09f7be66d4b64514de4f274e0bbb080243a0b12f9fadac6bd380957e7f",
    "curated": "794287529f6217d1cd416dc34b2788acfb0e874907e769935344686770e6ec15",
    "discrete": "f43cc9f9a4e1880445a54a1b563c78f8b7454bad52486cc1425a46a477a2f254",
    "named": "53b8d4357773274653fa1aa47e897472af0bfa6e6021093588bebf123b6c0784",
    "presets": "72247b40588e8a56354c48c0afa1fbdfb91ed4962a8729d4923ed094f3f41d3b",
}

EXPECTED_COMBINED = (
    "ca48e12c1b91035e1c2e0312db4b5379015368b4da8313738ce22a8ef6dd06ae"
)


def _digest(rows: list[str]) -> str:
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _measure_surface(surface: str) -> list[Any]:
    rows = SURFACES[surface]()
    return [len(rows), _digest(rows)]


def _combined_from(measured: dict[str, list[Any]]) -> str:
    return _digest([f"{name} {measured[name][1]}" for name in sorted(measured)])


def _measure_surface_in_subprocess(surface: str) -> list[Any]:
    """Measure one surface in a pristine interpreter.

    Each surface gets its own process for two reasons.

    First, the question this freeze answers is "what colors does a clean
    ``import dartwork_mpl`` ship", not "what colors are registered part-way
    through a test session". An in-process measurement would inherit whatever
    earlier tests left behind, making the freeze order-dependent - and an
    order-dependent freeze eventually gets "fixed" by regenerating the digest,
    which defeats its entire purpose.

    Second, the surfaces are not independent of each other. ``presets`` applies
    every style preset, and applying a preset rebinds the locale-dependent
    semantic tokens ``dc.pos`` and ``dc.neg`` in matplotlib's global named-color
    mapping (green/red under the default presets, red/blue under the ``-kr``
    ones, following East Asian market convention). ``mpl.rc_context`` restores
    rcParams but not that mapping, so measuring ``named`` after ``presets`` in
    the same process reads whichever preset ran last. That is correct product
    behaviour, and the freeze has to be measured around it rather than fight it.
    """
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--emit", surface],
        capture_output=True,
        text=True,
        check=True,
    )
    emitted: list[Any] = json.loads(completed.stdout)
    return emitted


def _measure_all() -> dict[str, list[Any]]:
    return {
        name: _measure_surface_in_subprocess(name) for name in sorted(SURFACES)
    }


@pytest.fixture(scope="module")
def measured() -> dict[str, list[Any]]:
    return _measure_all()


@pytest.mark.parametrize("surface", sorted(SURFACES))
def test_shipped_color_surface_is_frozen(
    surface: str, measured: dict[str, list[Any]]
) -> None:
    count, digest = measured[surface]
    assert count == EXPECTED_COUNTS[surface], (
        f"{surface}: shipped color surface changed size "
        f"({count} rows, expected {EXPECTED_COUNTS[surface]}). "
        "Colors were added or removed."
    )
    assert digest == EXPECTED_DIGESTS[surface], (
        f"{surface}: a shipped color value changed. This test is the freeze on "
        "the approved design - do not update the digest to make it pass without "
        "an accepted color change."
    )


def test_combined_shipped_color_digest_is_frozen(
    measured: dict[str, list[Any]],
) -> None:
    assert _combined_from(measured) == EXPECTED_COMBINED, (
        "The combined shipped-color digest changed. Run the per-surface tests "
        "to see which surface moved."
    )


if __name__ == "__main__":
    if "--emit" in sys.argv:
        json.dump(
            _measure_surface(sys.argv[sys.argv.index("--emit") + 1]), sys.stdout
        )
    else:
        result = _measure_all()
        print(
            "EXPECTED_COUNTS =",
            json.dumps(
                {name: value[0] for name, value in result.items()},
                indent=4,
                sort_keys=True,
            ),
        )
        print(
            "EXPECTED_DIGESTS =",
            json.dumps(
                {name: value[1] for name, value in result.items()},
                indent=4,
                sort_keys=True,
            ),
        )
        print('EXPECTED_COMBINED = "' + _combined_from(result) + '"')
