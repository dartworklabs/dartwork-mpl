import datetime
import importlib.metadata
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
copyright = f"{datetime.datetime.now().year} Dartwork"
author = "Sangwon Lee, Wonjun Choi"

version = importlib.metadata.version("dartwork-mpl")
release = version

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
html_css_files = ["custom.css", "font-specimens.css", "font-face.css"]
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
        {"title": "Usage Guide", "url": "usage_guide/index"},
        {"title": "Examples Gallery", "url": "examples_gallery/index"},
        {"title": "Color System", "url": "color_system/index"},
        {"title": "Fonts", "url": "fonts/index"},
        {"title": "API Reference", "url": "api/index"},
        {"title": "Design Philosophy", "url": "philosophy/index"},
        {"title": "AI Integration", "url": "integrations/index"},
    ],
}


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
        "examples_source/real_world",
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
        "examples_gallery/real_world",
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


# -- Build hooks (extracted to _ext/build_hooks.py) ---------------------------
sys.path.insert(0, str(Path(__file__).parent / "_ext"))

from build_hooks import (  # noqa: E402
    copy_fonts_to_static,
    create_placeholder_index,
    generate_gallery_assets,
    write_manual_indices,
)


def setup(app):
    app.connect("builder-inited", create_placeholder_index)
    app.connect("builder-inited", generate_gallery_assets)
    app.connect("builder-inited", copy_fonts_to_static)
    app.connect("env-before-read-docs", write_manual_indices)
    return {"parallel_read_safe": True}

