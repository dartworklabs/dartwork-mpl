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
from pathlib import Path

import matplotlib.colors as mcolors


def _parse_color_data(path: str | Path) -> dict[str, str]:
    """
    Parse color data from a text file.

    Parameters
    ----------
    path : str or Path
        Path to the color data file. Each line should contain a
        color name and value separated by a colon.

    Returns
    -------
    dict[str, str]
        Dictionary mapping color names to color values.
    """
    color_dict: dict[str, str] = {}
    with open(path) as f:
        lines: list[str] = f.readlines()

    for line in lines:
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
    root_dir: Path, filename: str, prefix: str
) -> dict[str, str]:
    """Load a JSON color palette and return prefixed color entries.

    Parameters
    ----------
    root_dir : Path
        Directory containing the JSON file.
    filename : str
        Name of the JSON file (e.g. ``"tailwind_colors.json"``).
    prefix : str
        Namespace prefix (e.g. ``"tw"``).

    Returns
    -------
    dict[str, str]
        Mapping of ``"{prefix}.{name}{weight}"`` to hex color strings.
    """
    with open(root_dir / filename) as f:
        data: dict[str, list[tuple[int, str]]] = json.load(f)

    result: dict[str, str] = {}
    for name, shades in data.items():
        name_lower: str = name.lower().replace(" ", "")
        for weight, hex_val in shades:
            result[f"{prefix}.{name_lower}{weight}"] = f"#{hex_val}"
    return result


# (prefix, filename) pairs for JSON-based palettes.
_JSON_PALETTES: list[tuple[str, str]] = [
    ("tw", "tailwind_colors.json"),
    ("md", "material_colors.json"),
    ("ad", "ant_colors.json"),
    ("cu", "chakra_colors.json"),
    ("pr", "primer_colors.json"),
    ("dc", "dc_palettes.json"),
]


def _load_colors() -> None:
    """Load all color definitions from asset files and register them.

    This function loads colors from text files (Open Color, ``oc.``
    prefix) and JSON files (Tailwind ``tw.``, Material Design ``md.``,
    Ant Design ``ad.``, Chakra UI ``cu.``, Primer ``pr.``,
    Dartwork Color ``dc.``) in the ``asset/color`` directory and
    registers them with matplotlib.

    Notes
    -----
    Called lazily via `ensure_loaded` on first colour access.
    """
    color_dict: dict[str, str] = {}

    root_dir: Path = Path(__file__).parent.parent / "asset/color"

    # Open Color (.txt files → "oc." prefix).
    for path in root_dir.glob("*.txt"):
        color_dict.update(
            {f"oc.{k}": v for k, v in _parse_color_data(path).items()}
        )

    # JSON-based palettes.
    for prefix, filename in _JSON_PALETTES:
        color_dict.update(_load_json_palette(root_dir, filename, prefix))

    # Add backward compatibility aliases for 'dc.' -> 'dm.'
    compat_dict: dict[str, str] = {}
    for k, v in color_dict.items():
        if k.startswith("dc."):
            compat_dict["dm." + k[3:]] = v
    color_dict.update(compat_dict)

    # Register with matplotlib.
    mcolors.get_named_colors_mapping().update(color_dict)

    # Remove xkcd colors — they clutter color galleries and are not
    # used by this library.  CSS4 named colours (e.g. 'black') are
    # kept because matplotlib itself relies on them for rcParams.
    mapping: dict = mcolors.get_named_colors_mapping()
    for key in [k for k in mapping if k.startswith("xkcd:")]:
        del mapping[key]


_loaded: bool = False


def ensure_loaded() -> None:
    """Ensure colour definitions have been loaded (idempotent)."""
    global _loaded
    if _loaded:
        return
    _load_colors()
    _loaded = True
