import datetime
import importlib.metadata
import os
import sys
from pathlib import Path

# Fix for PIL truncated image errors during sphinx-gallery generation
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True
# Sphinx-Gallery composites can exceed PIL's default decompression bomb limit
Image.MAX_IMAGE_PIXELS = 300_000_000

sys.path.insert(0, os.path.abspath("../src"))
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
warnings.filterwarnings("ignore", category=UserWarning, module="dartwork_mpl")

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

nitpick_ignore_regex = [
    (r'py:.*', r'optional'),
    (r'py:.*', r'colour'),
    (r'py:.*', r'dartwork_mpl\.color\._views\..*'),
    (r'py:.*', r'matplotlib\..*'),
    (r'py:.*', r'numpy\..*'),
    (r'py:.*', r'np\..*'),
    (r'py:.*', r'scipy\..*'),
    (r'py:.*', r'pathlib\..*'),
    (r'py:.*', r'Path'),
    (r'py:.*', r'Figure'),
    (r'py:.*', r'Axes'),
    (r'py:.*', r'GridSpec'),
    (r'py:.*', r'OptimizeResult'),
    (r'py:.*', r'ndarray'),
    (r'py:.*', r'Colormap'),
    (r'py:.*', r'FontProperties'),
    (r'py:.*', r"'auto'"),
    (r'py:.*', r"\{'x'"),
    (r'py:.*', r"'y'\}"),
    (r'py:.*', r'dartwork_mpl\.style\.use'),
    (r'py:.*', r'Bbox'),
    (r'py:.*', r'VisualWarning'),
    (r'py:.*', r'pydantic\..*'),
    (r'py:.*', r'BaseModel'),
]

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    # Helper READMEs inside example sources
    "examples_source/README.rst",
    "examples_source/*/README.rst",
    # Internal quality standards (not user-facing docs)
    "examples_source/_LAYOUT_RECIPES.md",
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
        {"title": "Getting Started", "url": "usage_guide/quickstart"},
        {"title": "Usage Guide", "url": "usage_guide/index"},
        {"title": "Color System", "url": "color_system/index"},
        {"title": "Fonts", "url": "fonts/index"},
        {"title": "Examples Gallery", "url": "examples_gallery/index"},
        {"title": "API Reference", "url": "api/index"},
        {"title": "Design Philosophy", "url": "philosophy/index"},
        {"title": "AI Integration", "url": "integrations/index"},
        {"title": "Changelog", "url": "https://github.com/dartwork-repo/dartwork-mpl/blob/main/CHANGELOG.md"},
    ],
}


# -- Sphinx Gallery configuration --------------------------------------------


sphinx_gallery_conf = {
    "examples_dirs": [
        "examples_source/01_styling_and_themes",
        "examples_source/02_color_system",
        "examples_source/02_formatting",
        "examples_source/03_layout_and_annotations",
        "examples_source/04_advanced_components",
        "examples_source/05_creative_visualizations",
    ],
    "gallery_dirs": [
        "examples_gallery/01_styling_and_themes",
        "examples_gallery/02_color_system",
        "examples_gallery/02_formatting",
        "examples_gallery/03_layout_and_annotations",
        "examples_gallery/04_advanced_components",
        "examples_gallery/05_creative_visualizations",
    ],
    "filename_pattern": "/plot_",
    "nested_sections": False,
    "within_subsection_order": "FileNameSortKey",
    "backreferences_dir": None,
    "show_signature": False,
    "remove_config_comments": True,
    "image_scrapers": ("matplotlib",),
    "image_srcset": ["2x"],
    "capture_repr": (),
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
