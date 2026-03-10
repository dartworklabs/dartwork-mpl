"""Remove any colormap files not in the curated 16-map set."""

from pathlib import Path

CMAP_DIR = Path("src/dartwork_mpl/asset/cmap")

KEEP_CMAPS: set[str] = {
    # Sequential Single-Hue
    "steel.txt", "flame.txt", "monochrome.txt",
    # Sequential Multi-Hue
    "ocean.txt", "sunset.txt", "thermal.txt",
    # Diverging
    "balance.txt", "earth.txt", "delta.txt",
    # Cyclical
    "twilight_oklch.txt",
    # Crameri OKLCH recreations
    "batlow.txt", "berlin.txt", "lajolla.txt",
    # Discrete / Categorical
    "bold.txt", "muted.txt", "pastel.txt",
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
