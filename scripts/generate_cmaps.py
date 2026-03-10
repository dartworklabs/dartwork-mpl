import sys
from pathlib import Path

# Add src to sys.path if needed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import dartwork_mpl as dm

CMAP_DIR = Path("src/dartwork_mpl/asset/cmap")

# Define color anchors for custom colormaps
COLORMAPS = {
    "ocean": ["#0B1B3D", "#1A5F7A", "#47B5A4", "#E8F9FD"],
    "sunset": ["#1A1235", "#6B1F5E", "#D84A49", "#F2A73B", "#FDF1D6"],
    "emerald": ["#082D16", "#145934", "#30985E", "#8DEB9D", "#F0FDF4"],
    "berry": ["#2D112C", "#7A1C4B", "#D9326F", "#FCA9A0", "#FFF0F5"],
    "balance": ["#1D3557", "#457B9D", "#F1FAEE", "#E63946", "#85182A"],
    "earth": ["#3E2723", "#795548", "#FFF8E1", "#4CAF50", "#1B5E20"],
    "twilight_oklch": ["#E8B8DB", "#6441A5", "#2A0845", "#0F2027", "#203A43", "#3B8D99", "#E8B8DB"],
    "nebula": ["#1A0B2E", "#4B1B54", "#9E2A6B", "#D35C4A", "#F8B65A", "#F9F871"],
    "marine": ["#0B1D3A", "#25465C", "#48787E", "#72B0A4", "#C6E4D1"],
    "neon": ["#000B29", "#3E006A", "#9C0084", "#ED1A70", "#FF6B36", "#FFC800"],
    "steel": ["#081226", "#142D4C", "#2A5580", "#5A8BBA", "#A6C8E6", "#EBF3FA"],
    "flame": ["#360812", "#6E1322", "#B32930", "#ED654C", "#F7B296", "#FDEBE3"],
    "lavender": ["#1A0C2B", "#391C5C", "#633A96", "#9C73D1", "#D1BCE8", "#F2EBF9"],
    "ash": ["#111111", "#333333", "#555555", "#888888", "#BBBBBB", "#EEEEEE"],
    # --- New Sequential Single-Hue ---
    "amber": ["#3D1C00", "#8B5E0A", "#D4A017", "#F0D060", "#FAE8B0", "#FFF8E7"],
    "teal": ["#04201E", "#0A3D3A", "#17716A", "#3AAFA9", "#8ED8D3", "#E6FAF8"],
    "copper": ["#2C1006", "#5C3317", "#8D5B34", "#C08A5E", "#E0BB9A", "#F8ECDF"],
    # --- New Sequential Multi-Hue ---
    "arctic": ["#020B1A", "#0E2E54", "#1F5F8B", "#6BA3C8", "#B8DDF0", "#F0F7FC"],
    "thermal": ["#0D0221", "#3D0F58", "#8C1B6E", "#D44040", "#F0A030", "#FCE4A8"],
    "verdant": ["#0C200A", "#1B4418", "#2E7D32", "#66BB6A", "#C5E26A", "#F5FBE8"],
    "dusk": ["#0A0A1E", "#2D1B4E", "#6B3A6E", "#B56B78", "#E0A870", "#F8E8D0"],
    # --- New Diverging ---
    "delta": ["#0B4F4A", "#3AAFA9", "#F0F0EC", "#E88A3A", "#8B4513"],
    "polar": ["#3B0764", "#9333EA", "#F5F0FF", "#22C55E", "#064E3B"],
    "spectrum": ["#1E3A5F", "#6B9FD1", "#F0F0EC", "#D16B6B", "#5F1E1E"],
    "fiscal": ["#064E3B", "#34D399", "#FAFAF5", "#F87171", "#7F1D1D"],
    # --- Academic Special ---
    "prism": ["#1A1636", "#3D3478", "#6B6BBD", "#A0A0E0", "#D0D0F0", "#F2F0FA"],
    "monochrome": ["#0A0A0A", "#2A2A2A", "#505050", "#808080", "#B0B0B0", "#E8E8E8", "#FAFAFA"],
}

def generate_multipart_colormap(name: str, anchors: list[str], steps: int = 256):
    """Generate a cohesive colormap by interpolating multiple anchors in OKLCH space."""
    num_segments = len(anchors) - 1
    # Distribute the 256 steps among the segments
    base_steps = steps // num_segments
    remainder = steps % num_segments
    
    all_colors = []
    
    for i in range(num_segments):
        start_color = anchors[i]
        end_color = anchors[i+1]
        
        # Add the remainder to the last segment
        segment_steps = base_steps + (remainder if i == num_segments - 1 else 0)
        
        # Interpolate in OKLCH space using dm.cspace
        segment_colors = dm.cspace(start_color, end_color, n=segment_steps, space="oklch")
        
        # Avoid duplicating the ending color of the segment if it's not the final segment
        if i < num_segments - 1:
            all_colors.extend(segment_colors[:-1])
        else:
            all_colors.extend(segment_colors)
            
    # Write to file
    out_path = CMAP_DIR / f"{name}.txt"
    with open(out_path, "w") as f:
        for c in all_colors:
            r, g, b = c.to_rgb()
            f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
    print(f"Generated {name}.txt ({len(all_colors)} colors)")

def main():
    CMAP_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating OKLCH continuous colormaps...")
    
    for name, anchors in COLORMAPS.items():
        generate_multipart_colormap(name, anchors)

if __name__ == "__main__":
    main()
