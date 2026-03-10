"""Generate OKLCH-native colormaps for dartwork-mpl.

Produces 30+ colormaps across categories:
- Sequential Single-Hue
- Sequential Multi-Hue
- Diverging
- Cyclical
- Discrete Qualitative
"""

import sys
from pathlib import Path

import matplotlib.colors as mcolors

from dartwork_mpl.color._loader import _load_colors

# Add src to sys.path if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import dartwork_mpl as dm

CMAP_DIR = Path("src/dartwork_mpl/asset/cmap")

# ──────────────────────────────────────────────────
# Continuous colormaps — OKLCH anchor interpolation
# ──────────────────────────────────────────────────

COLORMAPS: dict[str, list[str]] = {
    # --- Sequential Single-Hue (8+ maps) ---
    "obsidian": [
        "#050505", "#1A1A1A", "#333333",
        "#666666", "#999999", "#CCCCCC", "#F5F5F5",
    ],
    "sapphire": [
        "#041029", "#0B265C", "#15428F",
        "#2463C4", "#4A8BE8", "#8CB6F0", "#D9E8FA",
    ],
    "emerald": [
        "#031C14", "#083B2C", "#11634B",
        "#1D916E", "#34C498", "#74E0BF", "#D1F5E8",
    ],
    "ruby": [
        "#29060B", "#5C0C17", "#961325",
        "#D4243A", "#F25569", "#F797A4", "#FDE3E6",
    ],
    "amethyst": [
        "#180629", "#340D5C", "#571891",
        "#8229D1", "#A857ED", "#CFA1F5", "#F2E8FA",
    ],
    "topaz": [
        "#291D04", "#5C410A", "#966A12",
        "#D1971F", "#F2BB46", "#FAD88E", "#FEF3D9",
    ],
    "graphite": [
        "#0D1117", "#1E2633", "#384457",
        "#5E6E85", "#8E9EB3", "#C4D0E0", "#F0F4F7",
    ],
    "coral": [
        "#2B0E0B", "#5C1E18", "#943329",
        "#CF4C3F", "#FA796B", "#FCB5AD", "#FEEAE8",
    ],

    # --- Sequential Multi-Hue (8+ maps) ---
    "aurora": ["#081736", "#2B478B", "#4DB39A", "#D1F5D8"],
    "sunset_glow": ["#1A0724", "#611051", "#B82E47", "#F07B37", "#FCE09D"],
    "plasma_arc": ["#0D0221", "#4A066B", "#9C1777", "#ED3B4A", "#F2AA33", "#FCEEBA"],
    "spring_bloom": ["#09212E", "#155963", "#4CA161", "#A9D95B", "#F2F5BD"],
    "deep_sea": ["#020A1A", "#082F57", "#13637D", "#3AA0A3", "#8AEDE5"],
    "autumn_leaf": ["#1C060B", "#521217", "#993116", "#D9681C", "#F0B54F"],
    "nebula_dust": ["#090517", "#27154A", "#5E2980", "#A84C9C", "#E38BBA", "#FCE3F5"],
    "tropical_fruit": ["#2E062B", "#6E1346", "#B52B4D", "#ED653E", "#F5B44C", "#FDF3C2"],

    # --- Diverging (8+ maps) ---
    "ice_fire": ["#0C275C", "#2966C7", "#F2F5F7", "#D42A38", "#570911"],
    "earth_sky": ["#382412", "#7A5029", "#F7F5F0", "#3E8FA3", "#123F4D"],
    "teal_rose": ["#064240", "#1A8A85", "#F2F7F7", "#CF3E5C", "#4A0A19"],
    "purple_lime": ["#250C42", "#5A2594", "#F5F2F7", "#76BD24", "#203806"],
    "navy_gold": ["#071638", "#1A4196", "#F2F5F7", "#D1961F", "#4D3404"],
    "forest_brick": ["#06331A", "#1D7541", "#F5F7F5", "#AD3C2B", "#421008"],
    "magenta_cyan": ["#380A2B", "#8C1B6C", "#F5F2F5", "#15828C", "#063033"],
    "slate_orange": ["#121A21", "#364A5C", "#F2F4F5", "#C75A1C", "#471D05"],

    # --- Cyclical (6 maps) ---
    "twilight_oklch": [
        "#E8B8DB", "#6441A5", "#2A0845",
        "#0F2027", "#203A43", "#3B8D99", "#E8B8DB",
    ],
    "phase_wheel": [
        "#FADEEB", "#DD7CB8", "#87277E", "#2C0947",
        "#093247", "#228587", "#84D1C1", "#FADEEB",
    ],
    "color_wheel": [
        "#FF595E", "#FFCA3A", "#8AC926", "#1982C4", "#6A4C93", "#FF595E"
    ],
    "seasons": [
        "#A8E6CF", "#DCEDC1", "#FFD3B6", "#FFAAA5", "#FF8B94", "#A8E6CF"
    ],
    "day_night": [
        "#111111", "#F89035", "#FAD87F", "#8EE4AF", "#1E688A", "#111111"
    ],
    "rainbow_cycle": [
        "#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#4B0082", "#9400D3", "#FF0000"
    ],
}


def generate_continuous(
    name: str, anchors: list[str], steps: int = 256
) -> None:
    """Interpolate anchors in OKLCH space to produce a smooth gradient."""
    num_segments = len(anchors) - 1
    base_steps = steps // num_segments
    remainder = steps % num_segments

    all_colors: list = []
    for i in range(num_segments):
        seg_steps = base_steps + (
            remainder if i == num_segments - 1 else 0
        )
        
        # Determine stops explicitly keeping them in OKLCH
        from dartwork_mpl.color._color import cspace
        
        segment = cspace(
            anchors[i], anchors[i + 1], n=seg_steps, space="oklch"
        )
        if i < num_segments - 1:
            all_colors.extend(segment[:-1])
        else:
            all_colors.extend(segment)

    out_path = CMAP_DIR / f"{name}.txt"
    with open(out_path, "w") as f:
        for c in all_colors:
            r, g, b = c.to_rgb()
            f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
    print(f"Generated {name}.txt ({len(all_colors)} colors)")


# ──────────────────────────────────────────────────
# Discrete colormaps — OKLCH hue-wheel equispacing
# ──────────────────────────────────────────────────

DISCRETE_SPECS: dict[str, dict] = {
    "vivid": {"L": 0.65, "C": 0.22, "n": 8, "h_offset": 20},
    "lucid": {"L": 0.75, "C": 0.16, "n": 8, "h_offset": 20},
    "chalk": {"L": 0.88, "C": 0.08, "n": 8, "h_offset": 20},
}


def generate_discrete(name: str, spec: dict) -> None:
    """Generate N equispaced hues on the OKLCH wheel."""
    n = spec["n"]
    out_path = CMAP_DIR / f"{name}.txt"
    with open(out_path, "w") as f:
        for i in range(n):
            h = (spec["h_offset"] + i * 360.0 / n) % 360.0
            c = dm.Color.from_oklch(spec["L"], spec["C"], h)
            r, g, b = c.to_rgb()
            r = max(0.0, min(1.0, r))
            g = max(0.0, min(1.0, g))
            b = max(0.0, min(1.0, b))
            f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
    print(f"Generated {name}.txt ({n} colors)")

# ──────────────────────────────────────────────────
# Categorical Presets (from tw. and oc.)
# ──────────────────────────────────────────────────

_load_colors()

CATEGORICAL_PRESETS: dict[str, list[str]] = {
    "vibrant": [
        "oc.red6", "oc.orange5", "oc.yellow5", "oc.green5",
        "oc.cyan5", "oc.blue6", "oc.grape5"
    ],
    "pastel": [
        "oc.red3", "oc.orange3", "oc.yellow3", "oc.teal3",
        "oc.blue3", "oc.violet3", "oc.pink3"
    ],
    "candy": [
        "tw.rose400", "tw.amber400", "tw.lime400", "tw.emerald400",
        "tw.cyan400", "tw.blue400", "tw.violet400"
    ],
    "pop": [
        "tw.red500", "tw.orange500", "tw.yellow400", "tw.green500",
        "tw.sky500", "tw.indigo500", "tw.fuchsia500"
    ],
    "macaron": [
        "tw.pink300", "tw.orange300", "tw.yellow300", "tw.lime300",
        "tw.cyan300", "tw.blue300", "tw.purple300"
    ],
}

def generate_preset_categorical(name: str, keys: list[str]) -> None:
    """Generate categorical colormaps from preset colors, sorted by OKLCH lightness."""
    out_path = CMAP_DIR / f"{name}.txt"
    mapping = mcolors.get_named_colors_mapping()
    import dartwork_mpl.color as dc
    
    color_objects = []
    for k in keys:
        hex_val = mapping[k]
        c = dc.Color.from_hex(hex_val)
        color_objects.append((c.oklch[0], hex_val))
    
    # Sort ascending lightness (darkest to lightest)
    color_objects.sort(key=lambda x: x[0])
    
    with open(out_path, "w") as f:
        for _l, hex_val in color_objects:
            r, g, b = mcolors.to_rgb(hex_val)
            f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
    print(f"Generated {name}.txt from presets ({len(color_objects)} colors, sorted by Lightness)")


def main() -> None:
    """Generate all colormaps."""
    CMAP_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Continuous colormaps ===")
    for name, anchors in COLORMAPS.items():
        generate_continuous(name, anchors)

    print("\n=== Discrete colormaps ===")
    for name, spec in DISCRETE_SPECS.items():
        generate_discrete(name, spec)

    print("\n=== Preset Categorical colormaps ===")
    for name, keys in CATEGORICAL_PRESETS.items():
        generate_preset_categorical(name, keys)

    print("\n--- DONE ---")
    print(f"Total: {len(COLORMAPS)} continuous, {len(DISCRETE_SPECS)} discrete, {len(CATEGORICAL_PRESETS)} preset categorical")

    # Note: after expanding the list, `prune_cmaps.py`, `cmap.py` loaders
    # or testing scripts might need updates to account for the new mapped names.

if __name__ == "__main__":
    main()
