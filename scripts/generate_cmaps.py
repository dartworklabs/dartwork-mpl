"""Generate OKLCH-native colormaps for dartwork-mpl.

Produces 16 colormaps:
- 10 continuous (sequential / diverging / cyclical)
- 3 continuous Crameri OKLCH recreations (batlow, berlin, lajolla)
- 3 discrete qualitative (bold, muted, pastel)
"""

import sys
from pathlib import Path

# Add src to sys.path if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import dartwork_mpl as dm

CMAP_DIR = Path("src/dartwork_mpl/asset/cmap")

# ──────────────────────────────────────────────────
# Continuous colormaps — OKLCH anchor interpolation
# ──────────────────────────────────────────────────

COLORMAPS: dict[str, list[str]] = {
    # --- Sequential Single-Hue ---
    "steel": [
        "#081226", "#142D4C", "#2A5580",
        "#5A8BBA", "#A6C8E6", "#EBF3FA",
    ],
    "flame": [
        "#360812", "#6E1322", "#B32930",
        "#ED654C", "#F7B296", "#FDEBE3",
    ],
    "monochrome": [
        "#0A0A0A", "#2A2A2A", "#505050",
        "#808080", "#B0B0B0", "#E8E8E8", "#FAFAFA",
    ],
    # --- Sequential Multi-Hue ---
    "ocean": ["#0B1B3D", "#1A5F7A", "#47B5A4", "#E8F9FD"],
    "sunset": [
        "#1A1235", "#6B1F5E", "#D84A49",
        "#F2A73B", "#FDF1D6",
    ],
    "thermal": [
        "#0D0221", "#3D0F58", "#8C1B6E",
        "#D44040", "#F0A030", "#FCE4A8",
    ],
    # --- Diverging ---
    "balance": ["#1D3557", "#457B9D", "#F1FAEE", "#E63946", "#85182A"],
    "earth": [
        "#3E2723", "#795548", "#FFF8E1",
        "#4CAF50", "#1B5E20",
    ],
    "delta": ["#0B4F4A", "#3AAFA9", "#F0F0EC", "#E88A3A", "#8B4513"],
    # --- Cyclical ---
    "twilight_oklch": [
        "#E8B8DB", "#6441A5", "#2A0845",
        "#0F2027", "#203A43", "#3B8D99", "#E8B8DB",
    ],
    # --- Crameri OKLCH recreations ---
    "batlow": [
        "#1D1147", "#1B4B5A", "#2D7A4A", "#7CB342",
        "#F5C842", "#E8734A", "#D4508A", "#F0C4D8",
    ],
    "berlin": [
        "#7EB8DA", "#2477A4", "#0A1929",
        "#8B2020", "#E8A0A0",
    ],
    "lajolla": [
        "#FFFDE7", "#F9E547", "#E6A817",
        "#B5651D", "#5D2906", "#1A0A00",
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
        segment = dm.cspace(
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
    "bold": {"L": 0.55, "C": 0.19, "n": 8, "h_offset": 30},
    "muted": {"L": 0.65, "C": 0.10, "n": 8, "h_offset": 30},
    "pastel": {"L": 0.85, "C": 0.07, "n": 8, "h_offset": 30},
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
    print(f"Generated {name}.txt ({n} discrete colors)")


def main() -> None:
    """Generate all colormaps."""
    CMAP_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Continuous colormaps ===")
    for name, anchors in COLORMAPS.items():
        generate_continuous(name, anchors)

    print("\n=== Discrete colormaps ===")
    for name, spec in DISCRETE_SPECS.items():
        generate_discrete(name, spec)


if __name__ == "__main__":
    main()
