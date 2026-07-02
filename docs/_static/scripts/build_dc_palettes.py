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

The 24 curated palettes are the only public dc palettes. The old ad-hoc set
(Vivid/Sunset/Ocean/Pop/Cyber/Autumn/Nordic) was removed in 0.5 — all docs
examples and templates now use curated names.
Default (repoint): the unnamed "" palette (→ dc.0..7, the shared
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
# public name -> family (taxonomy SSOT — the explorer rail groups and the
# docs "N families" claims derive from this). Editorial note: the two
# full-hue-wheel loud sets (``vivid``, ``neon``) both live in the
# *Spectrum* family — a palette named "vivid" sitting outside a family
# named "Vivid" (as the explorer once had it) read as a bug, so the
# one-palette "Vivid" family was folded into Spectrum (24 palettes,
# 11 families).
FAMILY = {
    "teal": "Sequential",
    "indigo": "Sequential",
    "coral": "Sequential",
    "teal_indigo": "Analogous",
    "forest": "Analogous",
    "blue_orange": "Duo",
    "teal_coral": "Duo",
    "trustworthy": "Balanced",
    "pastel": "Muted",
    "dusty": "Muted",
    "vivid": "Spectrum",
    "neon": "Spectrum",
    "accessible": "Accessible",
    "gray": "Neutral",
    "warm_gray": "Neutral",
    "cool_gray": "Neutral",
    "cool_warm": "Diverging",
    "teal_amber": "Diverging",
    "purple_green": "Diverging",
    "earth": "Tone",
    "jewel": "Tone",
    "ember": "Tone",
    "teal_accent": "Emphasis",
    "coral_accent": "Emphasis",
}

NAME = {
    "teal_seq": "teal",
    "indigo_seq": "indigo",
    "coral_seq": "coral",
    "gray_seq": "gray",
    "warm_gray": "warm_gray",
    "cool_gray": "cool_gray",
    "forest": "forest",
    "teal_indigo": "teal_indigo",
    "blue_orange": "blue_orange",
    "teal_coral": "teal_coral",
    "trustworthy": "trustworthy",
    "muted": "pastel",
    "dusty": "dusty",
    "vivid": "vivid",
    "neon": "neon",
    "ember": "ember",
    "earth": "earth",
    "jewel": "jewel",
    "coolwarm": "cool_warm",
    "teal_amber_div": "teal_amber",
    "purple_green": "purple_green",
    "focus": "teal_accent",
    "focus_warm": "coral_accent",
    "accessible": "accessible",
}
# emission order (spectral-width spine then intent families), for readability
ORDER = [
    "teal_seq",
    "indigo_seq",
    "coral_seq",
    "gray_seq",
    "warm_gray",
    "cool_gray",
    "forest",
    "teal_indigo",
    "blue_orange",
    "teal_coral",
    "trustworthy",
    "muted",
    "dusty",
    "vivid",
    "neon",
    "ember",
    "earth",
    "jewel",
    "coolwarm",
    "teal_amber_div",
    "purple_green",
    "focus",
    "focus_warm",
    "accessible",
]


def _rows(colors: list[str]) -> list[list[object]]:
    return [[i, colors[i].lstrip("#").upper()] for i in range(len(colors))]


def main() -> None:
    gen: dict[str, dict] = json.loads(GEN_JSON.read_text(encoding="utf-8"))
    missing = [k for k in NAME if k not in gen]
    if missing:
        raise SystemExit(f"generator output missing palettes: {missing}")

    out: dict[str, list] = {}
    # default cycle (dc.0..7) = trustworthy
    out[""] = _rows(gen["trustworthy"]["colors"])
    for key in ORDER:
        out[NAME[key]] = _rows(gen[key]["colors"])

    PKG_JSON.write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {PKG_JSON}")
    print(f"  palettes: {len(NAME)} curated + 1 default (dc.0-7 = trustworthy)")
    print(f"  dc names: {', '.join(sorted(v.lower() for v in NAME.values()))}")


if __name__ == "__main__":
    main()
