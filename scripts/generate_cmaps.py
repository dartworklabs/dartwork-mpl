"""Generate OKLCH-native colormaps for dartwork-mpl.

Produces 30+ colormaps across categories:
- Single-Hue
- Multi-Hue
- Diverging
- Cyclical
- Discrete Qualitative
"""

import sys
from pathlib import Path

import matplotlib.colors as mcolors

from dartwork_mpl.colors._loader import _load_colors

# Add src to sys.path if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import dartwork_mpl as dm

CMAP_DIR = Path("src/dartwork_mpl/asset/cmap")

# ──────────────────────────────────────────────────
# Continuous colormaps — OKLCH anchor interpolation
# ──────────────────────────────────────────────────

COLORMAPS: dict[str, list[str]] = {
    # --- Single-Hue (8+ maps) ---
    "obsidian": [
        "#050505",
        "#1A1A1A",
        "#333333",
        "#666666",
        "#999999",
        "#CCCCCC",
        "#F5F5F5",
    ],
    "sapphire": [
        "#041029",
        "#0B265C",
        "#15428F",
        "#2463C4",
        "#4A8BE8",
        "#8CB6F0",
        "#D9E8FA",
    ],
    "emerald": [
        "#031C14",
        "#083B2C",
        "#11634B",
        "#1D916E",
        "#34C498",
        "#74E0BF",
        "#D1F5E8",
    ],
    "ruby": [
        "#29060B",
        "#5C0C17",
        "#961325",
        "#D4243A",
        "#F25569",
        "#F797A4",
        "#FDE3E6",
    ],
    "amethyst": [
        "#180629",
        "#340D5C",
        "#571891",
        "#8229D1",
        "#A857ED",
        "#CFA1F5",
        "#F2E8FA",
    ],
    "topaz": [
        "#291D04",
        "#5C410A",
        "#966A12",
        "#D1971F",
        "#F2BB46",
        "#FAD88E",
        "#FEF3D9",
    ],
    "graphite": [
        "#0D1117",
        "#1E2633",
        "#384457",
        "#5E6E85",
        "#8E9EB3",
        "#C4D0E0",
        "#F0F4F7",
    ],
    "coral": [
        "#2B0E0B",
        "#5C1E18",
        "#943329",
        "#CF4C3F",
        "#FA796B",
        "#FCB5AD",
        "#FEEAE8",
    ],
    # --- Single-Hue (Vibrant) ---
    "neon_blue": ["#EFF6FF", "#3B82F6", "#1D4ED8", "#1E3A8A", "#0F172A"],
    "neon_green": ["#F0FDF4", "#22C55E", "#15803D", "#064E3B", "#022C22"],
    "neon_pink": ["#FDF2F8", "#EC4899", "#BE185D", "#831843", "#4C0519"],
    "neon_orange": ["#FFF7ED", "#F97316", "#C2410C", "#7C2D12", "#431407"],
    # --- Multi-Hue (Classic) ---
    "aurora": ["#081736", "#2B478B", "#4DB39A", "#D1F5D8"],
    "sunset_glow": ["#1A0724", "#611051", "#B82E47", "#F07B37", "#FCE09D"],
    "plasma_arc": [
        "#0D0221",
        "#4A066B",
        "#9C1777",
        "#ED3B4A",
        "#F2AA33",
        "#FCEEBA",
    ],
    "spring_bloom": ["#09212E", "#155963", "#4CA161", "#A9D95B", "#F2F5BD"],
    "deep_sea": ["#020A1A", "#082F57", "#13637D", "#3AA0A3", "#8AEDE5"],
    "autumn_leaf": ["#1C060B", "#521217", "#993116", "#D9681C", "#F0B54F"],
    "nebula_dust": [
        "#090517",
        "#27154A",
        "#5E2980",
        "#A84C9C",
        "#E38BBA",
        "#FCE3F5",
    ],
    "tropical_fruit": [
        "#2E062B",
        "#6E1346",
        "#B52B4D",
        "#ED653E",
        "#F5B44C",
        "#FDF3C2",
    ],
    # --- Multi-Hue (Vibrant) ---
    "cyberpunk": [
        "#020617",
        "#0F172A",
        "#6366F1",
        "#EC4899",
        "#FDE047",
        "#FEF08A",
    ],
    "synthwave": [
        "#050505",
        "#170F11",
        "#9D174D",
        "#D946EF",
        "#38BDF8",
        "#F1F5F9",
        "#FFFFFF",
    ],
    "vivid_dusk": [
        "#0F0A2A",
        "#1E1B4B",
        "#7C3AED",
        "#F43F5E",
        "#FCD34D",
        "#FEF3C7",
    ],
    "toxic_glow": [
        "#011511",
        "#022C22",
        "#059669",
        "#84CC16",
        "#FEF08A",
        "#FEF9C3",
    ],
    # --- Diverging (Classic) ---
    "ice_fire": ["#0C275C", "#2966C7", "#F2F5F7", "#D42A38", "#570911"],
    "earth_sky": ["#382412", "#7A5029", "#F7F5F0", "#3E8FA3", "#123F4D"],
    "teal_rose": ["#064240", "#1A8A85", "#F2F7F7", "#CF3E5C", "#4A0A19"],
    "purple_lime": ["#250C42", "#5A2594", "#F5F2F7", "#76BD24", "#203806"],
    "navy_gold": ["#071638", "#1A4196", "#F2F5F7", "#D1961F", "#4D3404"],
    "forest_brick": ["#06331A", "#1D7541", "#F5F7F5", "#AD3C2B", "#421008"],
    "magenta_cyan": ["#380A2B", "#8C1B6C", "#F5F2F5", "#15828C", "#063033"],
    "slate_orange": ["#121A21", "#364A5C", "#F2F4F5", "#C75A1C", "#471D05"],
    # --- Diverging (Vibrant) ---
    "cool_warm": [
        "#1E3A8A",
        "#2563EB",
        "#60A5FA",
        "#F8FAFC",
        "#F87171",
        "#DC2626",
        "#7F1D1D",
    ],
    "arctic_heat": [
        "#164E63",
        "#0891B2",
        "#67E8F9",
        "#F8FAFC",
        "#FDBA74",
        "#EA580C",
        "#7C2D12",
    ],
    "frost_flame": [
        "#0C4A6E",
        "#0369A1",
        "#38BDF8",
        "#F8FAFC",
        "#FB7185",
        "#BE123C",
        "#881337",
    ],
    "water_fire": [
        "#312E81",
        "#4338CA",
        "#818CF8",
        "#F8FAFC",
        "#FBBF24",
        "#B45309",
        "#78350F",
    ],
    "spring_autumn": [
        "#064E3B",
        "#10B981",
        "#6EE7B7",
        "#F8FAFC",
        "#F59E0B",
        "#D97706",
        "#78350F",
    ],
    "summer_winter": [
        "#831843",
        "#EC4899",
        "#F472B6",
        "#F8FAFC",
        "#06B6D4",
        "#0891B2",
        "#164E63",
    ],
    "electric_surge": [
        "#4C1D95",
        "#8B5CF6",
        "#C4B5FD",
        "#F8FAFC",
        "#EAB308",
        "#A16207",
        "#713F12",
    ],
    "neon_pulse": [
        "#701A75",
        "#D946EF",
        "#F0ABFC",
        "#F8FAFC",
        "#14B8A6",
        "#0F766E",
        "#134E4A",
    ],
    # --- Cyclical (6 maps) ---
    "twilight_oklch": [
        "#E8B8DB",
        "#6441A5",
        "#2A0845",
        "#0F2027",
        "#203A43",
        "#3B8D99",
        "#E8B8DB",
    ],
    "phase_wheel": [
        "#FADEEB",
        "#DD7CB8",
        "#87277E",
        "#2C0947",
        "#093247",
        "#228587",
        "#84D1C1",
        "#FADEEB",
    ],
    "color_wheel": [
        "#FF0000",
        "#FFEA00",
        "#00E676",
        "#2962FF",
        "#4A148C",
        "#FF0000",
    ],
    "seasons": ["#E8F5E9", "#FBC02D", "#D84315", "#1A237E", "#E8F5E9"],
    "day_night": [
        "#111111",
        "#F89035",
        "#FAD87F",
        "#8EE4AF",
        "#1E688A",
        "#111111",
    ],
    "rainbow_cycle": [
        "#FF0000",
        "#FF7F00",
        "#FFFF00",
        "#00FF00",
        "#0000FF",
        "#4B0082",
        "#9400D3",
        "#FF0000",
    ],
    # --- Cyclical (Vibrant) ---
    "neon_wheel": [
        "#4C0519",
        "#FF0055",
        "#FFBB00",
        "#F0FDF4",
        "#00FF66",
        "#00DDFF",
        "#1E1B4B",
        "#AA00FF",
        "#4C0519",
    ],
    "electric_cycle": [
        "#831843",
        "#EC4899",
        "#FBBF24",
        "#FEF3C7",
        "#34D399",
        "#60A5FA",
        "#312E81",
        "#A78BFA",
        "#831843",
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
        seg_steps = base_steps + (remainder if i == num_segments - 1 else 0)

        # Determine stops explicitly keeping them in OKLCH
        from dartwork_mpl.colors._color import cspace

        segment = cspace(anchors[i], anchors[i + 1], n=seg_steps, space="oklch")
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
    "vivid": {"L": 0.60, "L_amp": 0.25, "C": 0.22, "n": 8, "h_offset": 20},
    "lucid": {"L": 0.65, "L_amp": 0.20, "C": 0.16, "n": 8, "h_offset": 20},
    "chalk": {"L": 0.75, "L_amp": 0.15, "C": 0.08, "n": 8, "h_offset": 20},
}


def generate_discrete(name: str, spec: dict) -> None:
    """Generate N equispaced hues on the OKLCH wheel, varying L for monochrome safety."""
    import math

    n = spec["n"]
    out_path = CMAP_DIR / f"{name}.txt"
    with open(out_path, "w") as f:
        for i in range(n):
            h = (spec["h_offset"] + i * 360.0 / n) % 360.0
            L_val = spec["L"] + spec.get("L_amp", 0.0) * math.sin(
                math.radians(h)
            )
            L_val = max(0.0, min(1.0, L_val))
            c = dm.Color.from_oklch(L_val, spec["C"], h)
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
        "oc.red7",
        "oc.orange5",
        "oc.yellow2",
        "oc.green6",
        "oc.cyan4",
        "oc.blue8",
        "oc.grape9",
    ],
    "pastel": [
        "oc.red2",
        "oc.orange4",
        "oc.yellow1",
        "oc.teal5",
        "oc.blue3",
        "oc.violet6",
        "oc.pink4",
    ],
    "candy": [
        "tw.rose500",
        "tw.amber300",
        "tw.lime400",
        "tw.emerald600",
        "tw.cyan200",
        "tw.blue700",
        "tw.violet800",
    ],
    "pop": [
        "tw.red600",
        "tw.orange400",
        "tw.yellow200",
        "tw.green500",
        "tw.sky300",
        "tw.indigo700",
        "tw.fuchsia800",
    ],
    "macaron": [
        "tw.pink400",
        "tw.orange300",
        "tw.yellow100",
        "tw.lime500",
        "tw.cyan200",
        "tw.blue600",
        "tw.purple700",
    ],
}


def generate_preset_categorical(name: str, keys: list[str]) -> None:
    """Generate categorical colormaps from preset colors, sorted by OKLCH lightness."""
    out_path = CMAP_DIR / f"{name}.txt"
    mapping = mcolors.get_named_colors_mapping()
    import dartwork_mpl.colors as dc

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
    print(
        f"Generated {name}.txt from presets ({len(color_objects)} colors, sorted by Lightness)"
    )


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
    print(
        f"Total: {len(COLORMAPS)} continuous, {len(DISCRETE_SPECS)} discrete, {len(CATEGORICAL_PRESETS)} preset categorical"
    )

    # Note: after expanding the list, `prune_cmaps.py`, `cmap.py` loaders
    # or testing scripts might need updates to account for the new mapped names.


if __name__ == "__main__":
    main()
