"""Custom Sphinx build hooks for dartwork-mpl documentation.

Extracted from conf.py for maintainability. Handles:
- Gallery index generation (manual indices after sphinx-gallery)
- Color system asset generation
- Font file copying for HTML specimens
"""

from pathlib import Path

_GALLERY_HEADER = """Examples Gallery
================

This gallery contains examples demonstrating the features and capabilities
of dartwork-mpl. Browse the categories below for ready-to-use patterns
and techniques.
"""

_GALLERY_CATEGORIES = [
    "01_styling_and_themes",
    "02_color_system",
    "03_formatting",
    "04_layout_and_annotations",
    "05_helpers_api",
    "06_chart_recipes",
    "07_real_world_dashboards",
    "08_creative_visualizations",
]


def create_placeholder_index(app):
    """Create placeholder index.rst so toctree finds it before sphinx-gallery."""
    gallery_dir = Path(app.srcdir) / "examples_gallery"
    gallery_dir.mkdir(parents=True, exist_ok=True)

    index_file = gallery_dir / "index.rst"
    if not index_file.exists():
        index_file.write_text(
            "Examples Gallery\n================\n\nLoading...\n"
        )
        print("Created placeholder: examples_gallery/index.rst")


def generate_gallery_assets(_app):
    """Bake high-res color system, usage guide, and API images during the build."""
    from color_system.generate_assets import build_gallery_assets

    build_gallery_assets()

    from usage_guide.generate_assets import build_usage_guide_assets

    build_usage_guide_assets()

    from api.generate_assets import build_api_assets

    build_api_assets()

    from fonts.generate_assets import build_font_assets

    build_font_assets()

    from fonts.generate_html_specimens import build_html_specimens

    build_html_specimens()


def copy_fonts_to_static(app):
    """Copy bundled TTF fonts to _static/fonts/ for HTML specimens."""
    import shutil

    font_src = (
        Path(app.srcdir).parent / "src" / "dartwork_mpl" / "asset" / "font"
    )
    font_dst = Path(app.srcdir) / "_static" / "fonts"
    font_dst.mkdir(parents=True, exist_ok=True)

    for ttf in font_src.glob("*.ttf"):
        dst_file = font_dst / ttf.name
        if (
            not dst_file.exists()
            or ttf.stat().st_mtime > dst_file.stat().st_mtime
        ):
            shutil.copy2(ttf, dst_file)


def write_manual_indices(app, env, docnames):
    """Write manual index files AFTER sphinx-gallery but BEFORE Sphinx reads."""
    gallery_dir = Path(app.srcdir) / "examples_gallery"

    content_parts = [_GALLERY_HEADER]
    toctree_entries = []

    for cat in _GALLERY_CATEGORIES:
        cat_index_path = gallery_dir / cat / "index.rst"
        if not cat_index_path.exists():
            print(f"Warning: Category index not found: {cat_index_path}")
            continue

        content = cat_index_path.read_text()

        # Remove :orphan: from category index files
        if ":orphan:" in content:
            clean_content = content.replace(":orphan:\n", "").replace(
                ":orphan:", ""
            )
            cat_index_path.write_text(clean_content)

        content = content.replace(":orphan:", "")

        # Cut off at toctree
        if ".. toctree::" in content:
            content = content.split(".. toctree::")[0]

        # Downgrade headers (=== -> ---)
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if (
                line.strip()
                and all(c == "=" for c in line.strip())
                and len(line.strip()) > 3
            ):
                new_lines.append("-" * len(line))
            else:
                new_lines.append(line)

        content_parts.append("\n".join(new_lines))
        toctree_entries.append(f"{cat}/index")

    # Hidden toctree for sidebar
    toctree_block = "\n.. toctree::\n   :hidden:\n\n"
    for entry in toctree_entries:
        toctree_block += f"   {entry}\n"
    content_parts.append(toctree_block)

    main_index = gallery_dir / "index.rst"
    main_index.write_text("\n".join(content_parts))
    print("Wrote concatenated manual index: examples_gallery/index.rst")

    if "examples_gallery/index" not in docnames:
        docnames.append("examples_gallery/index")
