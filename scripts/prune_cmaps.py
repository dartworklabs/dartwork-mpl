"""Remove any colormap files not in the curated 16-map set."""

from pathlib import Path

CMAP_DIR = Path("src/dartwork_mpl/asset/cmap")

# We keep ONLY the newly generated bright, curated set (30+ maps)
KEEP_CMAPS: set[str] = {
    # Sequential Single-Hue
    "obsidian.txt",
    "sapphire.txt",
    "emerald.txt",
    "ruby.txt",
    "amethyst.txt",
    "topaz.txt",
    "graphite.txt",
    "coral.txt",
    # Sequential Multi-Hue
    "aurora.txt",
    "sunset_glow.txt",
    "plasma_arc.txt",
    "spring_bloom.txt",
    "deep_sea.txt",
    "autumn_leaf.txt",
    "nebula_dust.txt",
    "tropical_fruit.txt",
    # Diverging
    "ice_fire.txt",
    "earth_sky.txt",
    "teal_rose.txt",
    "purple_lime.txt",
    "navy_gold.txt",
    "forest_brick.txt",
    "magenta_cyan.txt",
    "slate_orange.txt",
    # Cyclical
    "twilight_oklch.txt",
    "phase_wheel.txt",
    # Discrete
    "vivid.txt",
    "lucid.txt",
    "chalk.txt",
    "oc_vibrant.txt",
    "oc_pastel.txt",
    "tw_candy.txt",
    "tw_pop.txt",
    "tw_macaron.txt",
}


def main() -> None:
    """Delete all .txt files not in KEEP_CMAPS."""
    if not CMAP_DIR.exists():
        print(f"Directory {CMAP_DIR} not found.")
        return

    deleted = 0
    kept = 0
    for file_path in sorted(CMAP_DIR.glob("*.txt")):
        if file_path.name in KEEP_CMAPS:
            kept += 1
        else:
            print(f"Deleting: {file_path.name}")
            file_path.unlink()
            deleted += 1

    print(f"\nDeleted: {deleted}, Kept: {kept}")


if __name__ == "__main__":
    main()
