"""Color loading and registration for matplotlib.

Loads color definitions from asset files and registers them with
matplotlib's internal color mapping. Supports multiple color systems:
Open Color (oc.), Tailwind CSS (tw.), Material Design (md.),
Ant Design (ad.), Chakra UI (cu.), and Primer (pr.).
"""

from __future__ import annotations

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


def _load_colors() -> None:
    """
    Load all color definitions from asset files and register them.

    This function loads colors from text files and JSON files in the
    asset/color directory. It adds 'oc.' prefix
    to distinguish them from matplotlib's built-in colors.

    Tailwind CSS colors are loaded with 'tw.' prefix,
    followed by the color name and weight (e.g., 'tw.blue500',
    'tw.gray200'). Weights range from 50 to 950 in increments
    of 50 or 100.

    Material Design colors are loaded with 'md.' prefix
    (e.g., 'md.blue500', 'md.red700'). Weights range from 50 to 900.

    Ant Design colors are loaded with 'ad.' prefix
    (e.g., 'ad.blue5', 'ad.red6'). Weights range from 1 to 10.

    Chakra UI colors are loaded with 'cu.' prefix
    (e.g., 'cu.blue500', 'cu.red600'). Weights range from
    50 to 900.

    Primer colors are loaded with 'pr.' prefix
    (e.g., 'pr.blue5', 'pr.red6'). Weights range from 0 to 9.

    Notes
    -----
    This function is automatically called when the module is imported.
    """
    color_dict: dict[str, str] = {}

    root_dir: Path = Path(__file__).parent.parent / "asset/color"
    for path in root_dir.glob("*.txt"):
        color_dict.update(_parse_color_data(path))

    # Append prefix to distinguish them from matplotlib colors.
    _color_dict: dict[str, str] = {f"oc.{k}": v for k, v in color_dict.items()}

    # Tailwind colors.
    with open(root_dir / "tailwind_colors.json") as f:
        tailwind_colors: dict[str, list[tuple[int, str]]] = json.load(f)

    for k, v in tailwind_colors.items():
        k_lower: str = k.lower().replace(" ", "")
        for weight, hex_val in v:
            # Only use 'tw.' prefix, skip 'tw.' prefix since they
            # are identical
            _color_dict[f"tw.{k_lower}{weight}"] = f"#{hex_val}"

    # Material Design colors.
    with open(root_dir / "material_colors.json") as f:
        material_colors: dict[str, list[tuple[int, str]]] = json.load(f)

    for k, v in material_colors.items():
        # Remove spaces (e.g., "Deep Purple" -> "deeppurple")
        k_lower: str = k.lower().replace(" ", "")
        for weight, hex_val in v:
            _color_dict[f"md.{k_lower}{weight}"] = f"#{hex_val}"

    # Ant Design colors.
    with open(root_dir / "ant_colors.json") as f:
        ant_colors: dict[str, list[tuple[int, str]]] = json.load(f)

    for k, v in ant_colors.items():
        k_lower: str = k.lower().replace(" ", "")
        for weight, hex_val in v:
            _color_dict[f"ad.{k_lower}{weight}"] = f"#{hex_val}"

    # Chakra UI colors.
    with open(root_dir / "chakra_colors.json") as f:
        chakra_colors: dict[str, list[tuple[int, str]]] = json.load(f)

    for k, v in chakra_colors.items():
        k_lower: str = k.lower().replace(" ", "")
        for weight, hex_val in v:
            _color_dict[f"cu.{k_lower}{weight}"] = f"#{hex_val}"

    # Primer colors.
    with open(root_dir / "primer_colors.json") as f:
        primer_colors: dict[str, list[tuple[int, str]]] = json.load(f)

    for k, v in primer_colors.items():
        k_lower: str = k.lower().replace(" ", "")
        for weight, hex_val in v:
            _color_dict[f"pr.{k_lower}{weight}"] = f"#{hex_val}"

    # Add color dict to matplotlib internal color mapping.
    mcolors.get_named_colors_mapping().update(_color_dict)

    # Remove xkcd colors from matplotlib's color mapping since we don't
    # use them and they clutter the 'other' category in color galleries.
    color_mapping: dict[str, str] = mcolors.get_named_colors_mapping()
    xkcd_keys: list[str] = [
        k for k in list(color_mapping.keys()) if k.startswith("xkcd:")
    ]
    for key in xkcd_keys:
        del color_mapping[key]


_load_colors()
