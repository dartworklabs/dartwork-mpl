"""Color loading and registration for matplotlib.

Loads color definitions from asset files and registers them with
matplotlib's internal color mapping. Supports multiple color systems:
Open Color (oc.), Tailwind CSS (tw.), Material Design (md.),
Ant Design (ad.), Chakra UI (cu.), Primer (pr.), and
Dartwork Color curated palettes (dc.).
"""

from __future__ import annotations

__all__ = ["ensure_loaded"]

import json
import threading
from importlib.resources import files
from typing import TYPE_CHECKING

import matplotlib.colors as mcolors

from ._curated import CURATED
from ._generated import PALETTE

if TYPE_CHECKING:
    # ``Traversable`` moved from ``importlib.abc`` (3.10) to
    # ``importlib.resources.abc`` (3.11+); only needed for typing.
    from importlib.resources.abc import Traversable


def _parse_color_data(text: str) -> dict[str, str]:
    """
    Parse color data from a color-definition text blob.

    Parameters
    ----------
    text : str
        Contents of a color data file. Each line should contain a
        color name and value separated by a colon; ``#`` comment and
        blank lines are ignored.

    Returns
    -------
    dict[str, str]
        Dictionary mapping color names to color values.
    """
    color_dict: dict[str, str] = {}
    for line in text.splitlines():
        # Neglect comment line.
        if line.startswith("#"):
            continue

        # Neglect empty line.
        if not line.strip():
            continue

        k: str
        v: str
        k, v = line.split(":", maxsplit=1)
        color_dict[k.strip()] = v.strip()

    return color_dict


def _load_json_palette(
    root_dir: Traversable, filename: str, prefix: str
) -> dict[str, str]:
    """Load a JSON color palette and return prefixed color entries.

    Parameters
    ----------
    root_dir : Traversable
        Resource directory containing the JSON file.
    filename : str
        Name of the JSON file (e.g. ``"tailwind_colors.json"``).
    prefix : str
        Namespace prefix (e.g. ``"tw"``).

    Returns
    -------
    dict[str, str]
        Mapping of ``"{prefix}.{name}{weight}"`` to hex color strings.
    """
    data: dict[str, list[tuple[int, str]]] = json.loads(
        (root_dir / filename).read_text(encoding="utf-8")
    )

    result: dict[str, str] = {}
    for name, shades in data.items():
        name_lower: str = name.lower().replace(" ", "")
        for weight, hex_val in shades:
            result[f"{prefix}.{name_lower}{weight}"] = f"#{hex_val}"
    return result


# Single source of truth for every bundled colour library:
#   (key, prefix, source, label).
# ``key`` is the stable id used for display order; ``prefix`` is the matplotlib
# name prefix — note Ant / Chakra / Primer register under ``ad.`` / ``cu.`` /
# ``pr.`` respectively. ``source`` is either an asset filename or the generated
# v5 palette marker. Consumers (this loader, diagnostics, the MCP server)
# derive their prefix / label / order lists from this list instead of
# re-hardcoding them.
COLOR_LIBRARIES: list[tuple[str, str, str, str]] = [
    ("dc", "dc.", "_generated.PALETTE", "dartwork Color"),
    ("opencolor", "oc.", "opencolor.txt", "OpenColor"),
    ("tw", "tw.", "tailwind_colors.json", "Tailwind"),
    ("md", "md.", "material_colors.json", "Material Design"),
    ("ant", "ad.", "ant_colors.json", "Ant Design"),
    ("chakra", "cu.", "chakra_colors.json", "Chakra UI"),
    ("primer", "pr.", "primer_colors.json", "Primer"),
]

# (prefix, filename) for JSON-based third-party palettes — derived from the
# SSOT above. Dartwork's ``dc.`` namespace is registered from the generated v5
# palette below.
_JSON_PALETTES: list[tuple[str, str]] = [
    (prefix.rstrip("."), filename)
    for _key, prefix, filename, _label in COLOR_LIBRARIES
    if filename.endswith(".json")
]

# (prefix, filename) for the text-based palettes (Open Color) — same
# SSOT derivation as ``_JSON_PALETTES``. Previously the ``oc.`` prefix
# was re-hardcoded here and *any* stray ``.txt`` dropped into
# ``asset/color`` would have been swept in under it.
_TXT_PALETTES: list[tuple[str, str]] = [
    (prefix.rstrip("."), filename)
    for _key, prefix, filename, _label in COLOR_LIBRARIES
    if filename.endswith(".txt")
]


def _load_colors() -> None:
    """Load all color definitions from asset files and register them.

    This function loads colors from text files (Open Color, ``oc.``
    prefix), JSON files (Tailwind ``tw.``, Material Design ``md.``,
    Ant Design ``ad.``, Chakra UI ``cu.``, Primer ``pr.``) in the
    ``asset/color`` directory, and the generated Dartwork v5 palette
    (``dc.``). It then registers them with matplotlib.

    Notes
    -----
    Called once via `ensure_loaded` at package import
    (``colors/__init__.py``) — registration is eager, not lazy.
    """
    color_dict: dict[str, str] = {}

    # Access bundled assets through importlib.resources so loading works
    # even when the package is imported from a zip / non-extracted wheel,
    # instead of assuming a filesystem layout via __file__.
    root_dir: Traversable = files("dartwork_mpl") / "asset" / "color"

    # Text-based palettes (Open Color) — file list and prefix come from
    # the ``COLOR_LIBRARIES`` SSOT, not a directory glob.
    for prefix, filename in _TXT_PALETTES:
        text = (root_dir / filename).read_text(encoding="utf-8")
        color_dict.update(
            {f"{prefix}.{k}": v for k, v in _parse_color_data(text).items()}
        )

    # JSON-based third-party palettes.
    for prefix, filename in _JSON_PALETTES:
        color_dict.update(_load_json_palette(root_dir, filename, prefix))

    # Dartwork Color v5 generated palette.
    for fam, row in PALETTE.items():
        for step, hexval in enumerate(row):
            color_dict[f"dc.{fam}{step}"] = hexval

    # Dartwork curated categorical palettes (dc.* qualitative / duo /
    # diverging / tone / accent sets — see colors/_curated.py). Registered
    # after the generated families so a family name always wins; the curated
    # SSOT excludes the three single-hue names (teal / indigo / gray) that the
    # v5 families already supersede, so there is no token collision here.
    for name, row in CURATED.items():
        if name in PALETTE:  # defensive: never shadow a generated family
            continue
        for step, hexval in enumerate(row):
            color_dict[f"dc.{name}{step}"] = hexval

    # Register with matplotlib.
    mcolors.get_named_colors_mapping().update(color_dict)

    # NOTE: we deliberately do NOT delete matplotlib's built-in xkcd:*
    # colours here. They are a documented matplotlib feature, and other
    # code in the same process may use ``color="xkcd:..."``; mutating the
    # process-global mapping to declutter our own galleries would break
    # that unrelated code. The colour galleries instead filter ``xkcd:``
    # at display time (see diagnostics/_colors.py).


_loaded: bool = False
_lock: threading.Lock = threading.Lock()


def ensure_loaded() -> None:
    """Ensure colour definitions have been loaded (idempotent).

    Thread-safe: uses double-checked locking so that concurrent first
    accesses from multiple threads register the colour mapping exactly
    once. This mirrors :func:`dartwork_mpl.cmap.ensure_loaded` and
    :func:`dartwork_mpl.font.ensure_loaded` (PR #79); the colours loader
    was previously the one sibling without the lock, so a racing first
    access could run ``_load_colors`` twice and mutate matplotlib's
    global named-colour mapping concurrently.
    """
    global _loaded

    # Fast path: skip lock once already loaded.
    if _loaded:
        return

    with _lock:
        if _loaded:
            return
        _load_colors()
        _loaded = True
