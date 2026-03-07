import os
import sys
from pathlib import Path

# Fix for PIL truncated image errors during sphinx-gallery generation
from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

sys.path.insert(0, os.path.abspath("../src"))
sys.path.insert(0, str(Path(__file__).parent.resolve()))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "dartwork-mpl"
copyright = "2025 Dartwork"
author = " Sangwon Lee, Wonjun Choi"

version = "0.2.1"
release = "0.2.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "myst_parser",
    "sphinx_gallery.gen_gallery",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_tabs.tabs",
]

autodoc_mock_imports = ["pydantic", "fastapi"]

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    # Helper READMEs inside example sources
    "examples_source/README.rst",
    "examples_source/*/README.rst",
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "shibuya"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_js_files = ["custom.js"]

# Prevent sections from gallery/index from appearing in the global toctree
# toctree_object_entries = False  # Removed as it might interfere with sidebar

# Remove version from the sidebar title
html_title = f"{project} documentation"

# -- Shibuya theme options ---------------------------------------------------
html_theme_options = {
    "github_url": "https://github.com/dartworklabs/dartwork-mpl",
    "accent_color": "teal",
    "globaltoc_expand_depth": 1,  # Allow expanding sidebar items
    "dark_code": False,  # Use light code blocks (default Shibuya style)
    "nav_links": [
        {"title": "Installation", "url": "installation/index"},
        {"title": "Design Philosophy", "url": "philosophy/index"},
        {"title": "Usage Guide", "url": "usage_guide/index"},
        {"title": "Color System", "url": "color_system/index"},
        {"title": "Fonts", "url": "fonts/index"},
        {"title": "Examples Gallery", "url": "examples_gallery/index"},
        {"title": "API Reference", "url": "api/index"},
    ],
}


# -- Sphinx Gallery configuration --------------------------------------------
# -- Sphinx Gallery configuration --------------------------------------------

sphinx_gallery_conf = {
    "examples_dirs": [
        "examples_source/basic_plots",
        "examples_source/statistical_plots",
        "examples_source/bar_charts",
        "examples_source/scientific_plots",
        "examples_source/time_series",
        "examples_source/specialized_plots",
        "examples_source/layout_styling",
        "examples_source/colors_images",
    ],
    "gallery_dirs": [
        "examples_gallery/basic_plots",
        "examples_gallery/statistical_plots",
        "examples_gallery/bar_charts",
        "examples_gallery/scientific_plots",
        "examples_gallery/time_series",
        "examples_gallery/specialized_plots",
        "examples_gallery/layout_styling",
        "examples_gallery/colors_images",
    ],
    "filename_pattern": "/plot_",
    "nested_sections": False,
    "within_subsection_order": "FileNameSortKey",
    "backreferences_dir": None,
    "show_signature": False,
    "remove_config_comments": True,
    "image_scrapers": ("matplotlib",),
    "image_srcset": ["2x"],
}

# -- MyST Parser configuration -----------------------------------------------
myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3


# -- Manual gallery index system ----------------------------------------------
# sphinx-gallery overwrites index files, so we write our manual indices
# AFTER sphinx-gallery runs but BEFORE Sphinx reads the rst files

_GALLERY_HEADER = """Examples Gallery
================

This gallery contains examples demonstrating the features and capabilities
of dartwork-mpl. Browse the categories below for ready-to-use patterns
and techniques.
"""


def _write_manual_indices(app, env, docnames):
    """Write manual index files AFTER sphinx-gallery but BEFORE Sphinx reads docs."""
    gallery_dir = Path(app.srcdir) / "examples_gallery"

    # Define the order of categories
    categories = [
        "basic_plots",
        "statistical_plots",
        "bar_charts",
        "scientific_plots",
        "time_series",
        "specialized_plots",
        "layout_styling",
        "colors_images",
    ]

    content_parts = [_GALLERY_HEADER]
    toctree_entries = []

    for cat in categories:
        cat_index_path = gallery_dir / cat / "index.rst"
        if not cat_index_path.exists():
            print(f"Warning: Category index not found: {cat_index_path}")
            continue

        # Read the generated category index
        content = cat_index_path.read_text()

        # Remove :orphan: from category index files to include them in toctree/sidebar
        if ":orphan:" in content:
            clean_content = content.replace(":orphan:\n", "").replace(
                ":orphan:", ""
            )
            cat_index_path.write_text(clean_content)

        # Extract content before the toctree
        # The generated file usually ends with a toctree or a footer
        # We want the header, description, and thumbnail grid

        # 1. Remove :orphan: if present
        content = content.replace(":orphan:", "")

        # 2. Find where the toctree starts and cut off
        if ".. toctree::" in content:
            content = content.split(".. toctree::")[0]

        # 3. Downgrade headers (=== -> ---)
        # Assuming the first header is the title with === underline
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if (
                line.strip()
                and all(c == "=" for c in line.strip())
                and len(line.strip()) > 3
            ):
                # Replace === with --- for H2
                new_lines.append("-" * len(line))
            else:
                new_lines.append(line)

        processed_content = "\n".join(new_lines)
        content_parts.append(processed_content)

        # Add to toctree list
        toctree_entries.append(f"{cat}/index")

    # Add the hidden toctree at the end to maintain sidebar structure
    toctree_block = "\n.. toctree::\n   :hidden:\n\n"
    for entry in toctree_entries:
        toctree_block += f"   {entry}\n"

    content_parts.append(toctree_block)

    # Write the concatenated main index
    main_index = gallery_dir / "index.rst"
    main_index.write_text("\n".join(content_parts))
    print("Wrote concatenated manual index: examples_gallery/index.rst")

    # Add to docnames so Sphinx builds the newly written index
    if "examples_gallery/index" not in docnames:
        docnames.append("examples_gallery/index")


def _generate_gallery_assets(_app):
    """Bake high-res color system images during the build."""
    from color_system.generate_assets import build_gallery_assets

    build_gallery_assets()  # Outputs to color_system/images/ by default


def _create_placeholder_index(app):
    """Create placeholder index.rst so toctree can find it before sphinx-gallery runs."""
    gallery_dir = Path(app.srcdir) / "examples_gallery"
    gallery_dir.mkdir(parents=True, exist_ok=True)

    index_file = gallery_dir / "index.rst"
    if not index_file.exists():
        # Write minimal placeholder that will be overwritten later
        index_file.write_text(
            "Examples Gallery\n================\n\nLoading...\n"
        )
        print("Created placeholder: examples_gallery/index.rst")


def setup(app):
    # Create placeholder index FIRST so toctree can find it
    app.connect("builder-inited", _create_placeholder_index)
    app.connect("builder-inited", _generate_gallery_assets)
    # Write manual indices AFTER sphinx-gallery runs but BEFORE docs are read
    app.connect("env-before-read-docs", _write_manual_indices)
    return {"parallel_read_safe": True}
