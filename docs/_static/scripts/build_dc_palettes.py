#!/usr/bin/env python3
"""Build the package's dc_palettes.json from the verified generator output.

Reads ``dm_palettes_gen.json`` (24 CIELAB-generated + B&W/CVD-verified palettes,
the colour SSOT) and writes ``src/dartwork_mpl/asset/color/dc_palettes.json`` in
the loader's schema ``{"<snake_name>": [[weight, "HEXNOHASH"], ...]}``.

The generator names palettes by internal semantics (``teal_seq``, ``focus``,
``muted``, …); the package exposes them under clean public ``dc.<name>`` keys
(``teal``, ``teal_accent``, ``pastel``, …). ``NAME`` below is that translation
boundary — the rename SSOT. Keep it in sync with ``dc_palettes.json`` and
``categorical_explorer_data.js``; regenerating must reproduce the committed
``dc_palettes.json`` byte-for-byte.

Decision A (supersede): the 24 curated palettes REPLACE the old ad-hoc dc set
(Vivid/Sunset/Ocean/Forest/Pop/Cyber/Autumn/Nordic).
Decision B (repoint default): the unnamed "" palette (→ dc.0..7, the shared
``axes.prop_cycle``) is set to ``trustworthy`` — the everyday default.

Run after gen_palettes.py:  python3 build_dc_palettes.py
"""

from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GEN_JSON = SCRIPT_DIR / "dm_palettes_gen.json"
ROOT = SCRIPT_DIR.parents[
    2
]  # scripts -> _static -> docs ... actually dartwork-mpl
PKG_JSON = (
    ROOT / "src" / "dartwork_mpl" / "asset" / "color" / "dc_palettes.json"
)

# generator key -> public snake_case dc.<name> key (rename SSOT; identity where
# the generator name already reads well, renamed where the public API differs)
NAME = {
    "teal_seq": "teal",
    "indigo_seq": "indigo",
    "coral_seq": "coral",
    "teal_indigo": "teal_indigo",
    "forest": "forest",
    "warm_cool": "warm_cool",
    "blue_orange": "blue_orange",
    "teal_coral": "teal_coral",
    "trustworthy": "trustworthy",
    "corporate": "corporate",
    "gray_seq": "gray",
    "warm_gray": "warm_gray",
    "cool_gray": "cool_gray",
    "focus": "teal_accent",
    "focus_warm": "coral_accent",
    "muted": "pastel",
    "dusty": "dusty",
    "spectrum": "spectrum",
    "bold": "bold",
    "coolwarm": "coolwarm",
    "teal_amber_div": "teal_amber",
    "earth": "earth",
    "jewel": "jewel",
    "accessible": "accessible",
}
# emission order (spectral-width spine then intent families), for readability
ORDER = [
    "teal_seq",
    "indigo_seq",
    "coral_seq",
    "teal_indigo",
    "forest",
    "warm_cool",
    "blue_orange",
    "teal_coral",
    "trustworthy",
    "corporate",
    "gray_seq",
    "warm_gray",
    "cool_gray",
    "focus",
    "focus_warm",
    "muted",
    "dusty",
    "spectrum",
    "bold",
    "coolwarm",
    "teal_amber_div",
    "earth",
    "jewel",
    "accessible",
]


# DEPRECATED legacy aliases — the old ad-hoc dc set, kept (original colours) so
# existing code / docs examples that hardcode dc.vivid2, dc.ocean2, etc. keep
# resolving. Superseded in role by the 24 curated palettes; not featured/default.
# "Forest" is intentionally omitted — the new curated `forest` owns dc.forest.
LEGACY = {
    "Vivid": ["F59E0B", "06B6D4", "16A34A", "DC2626", "9333EA", "2563EB"],
    "Sunset": ["FFC857", "F28C28", "E63946", "457B9D", "6B4D57", "264653"],
    "Ocean": ["62B6CB", "1B98E0", "00838F", "4A6FA5", "0B3D91", "2E4057"],
    "Pop": ["FFCA3A", "8AC926", "FF924C", "FF595E", "1982C4", "6A4C93"],
    "Cyber": ["4CC9F0", "00B4D8", "F72585", "4361EE", "7209B7", "3A0CA3"],
    "Autumn": ["EEC643", "DA7B5C", "A77B5C", "BC4749", "386641", "6A4C3C"],
    "Nordic": ["B2BEC3", "00B894", "0984E3", "D63031", "636E72", "2D3436"],
}


def _rows(colors: list[str]) -> list[list[object]]:
    return [[i, colors[i].lstrip("#").upper()] for i in range(len(colors))]


def main() -> None:
    gen: dict[str, dict] = json.loads(GEN_JSON.read_text(encoding="utf-8"))
    missing = [k for k in NAME if k not in gen]
    if missing:
        raise SystemExit(f"generator output missing palettes: {missing}")

    out: dict[str, list] = {}
    # default cycle (dc.0..7) = trustworthy (Decision B)
    out[""] = _rows(gen["trustworthy"]["colors"])
    for key in ORDER:
        out[NAME[key]] = _rows(gen[key]["colors"])
    # deprecated legacy aliases (back-compat only)
    for name, hexes in LEGACY.items():
        out[name] = [[i, h] for i, h in enumerate(hexes)]

    PKG_JSON.write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {PKG_JSON}")
    print(
        f"  palettes: {len(NAME)} curated + {len(LEGACY)} legacy"
        f" + 1 default (dc.0-7 = trustworthy)"
    )
    print(f"  dc names: {', '.join(sorted(v.lower() for v in NAME.values()))}")


if __name__ == "__main__":
    main()
