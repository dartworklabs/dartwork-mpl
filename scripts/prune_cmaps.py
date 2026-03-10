from pathlib import Path

CMAP_DIR = Path("src/dartwork_mpl/asset/cmap")

KEEP_CMAPS = {
    # Seaborn Premium Colormaps
    "rocket.txt", "mako.txt", "flare.txt", "crest.txt", "vlag.txt", "icefire.txt",
    
    # Scientific Colormaps (Crameri) - Highly curated, perceptually uniform
    "batlow.txt", "batlowK.txt", "batlowW.txt", 
    "roma.txt", "romaO.txt",
    "vik.txt", "vikO.txt", 
    "oslo.txt", "tokyo.txt", "lajolla.txt", "lapaz.txt", "devon.txt", 
    "bam.txt", "bamO.txt", "berlin.txt", "broc.txt", "brocO.txt", "cork.txt", "corkO.txt", 
    "fes.txt", "imola.txt", "lisbon.txt", "nuuk.txt", "oleron.txt", "turku.txt",
    "buda.txt", "bukavu.txt", "davos.txt", "hawaii.txt", "bamako.txt", "acton.txt",
    
    # Dartwork Custom 
    # (Will be generated next, so we can delete their old versions if they exist to be safe,
    # but let's actually let generate_cmaps.py overwrite them, or just delete them now.)
}

def main():
    if not CMAP_DIR.exists():
        print(f"Directory {CMAP_DIR} not found.")
        return

    deleted_count = 0
    kept_count = 0

    for file_path in CMAP_DIR.glob("*.txt"):
        if file_path.name not in KEEP_CMAPS:
            print(f"Deleting redundant colormap: {file_path.name}")
            file_path.unlink()
            deleted_count += 1
        else:
            kept_count += 1

    print("\nColormap Cleanup Complete.")
    print(f"Deleted: {deleted_count}")
    print(f"Kept: {kept_count}")

if __name__ == "__main__":
    main()
