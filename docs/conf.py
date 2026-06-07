import datetime
import importlib.metadata
import os
import sys
from pathlib import Path

# --- Deterministic SVG assets (byte-identical across rebuilds) ---
# matplotlib stamps a wall-clock <dc:date> and uuid4-based element ids into
# every SVG, so each docs rebuild rewrote all generated assets and dirtied
# the working tree (a constant source of noisy ``git status`` diffs).
# SOURCE_DATE_EPOCH (read by matplotlib at savefig time) pins the <dc:date>;
# svg.hashsalt pins the element ids. dmpl.mplstyle leaves svg.hashsalt
# unset, so style.use() does not clobber this value.
os.environ.setdefault("SOURCE_DATE_EPOCH", "1735689600")  # 2025-01-01 UTC
import matplotlib

# Set the salt on both the live params and the *defaults*: vanilla
# before/after comparison figures reset via rcdefaults() / style.use("default"),
# which would otherwise restore the None salt and re-introduce uuid4 ids.
matplotlib.rcParams["svg.hashsalt"] = "dartwork-mpl-docs"
matplotlib.rcParamsDefault["svg.hashsalt"] = "dartwork-mpl-docs"

# Fix for PIL truncated image errors during sphinx-gallery generation
from PIL import Image, ImageFile  # noqa: E402

ImageFile.LOAD_TRUNCATED_IMAGES = True
# Sphinx-Gallery composites can exceed PIL's default decompression bomb limit
Image.MAX_IMAGE_PIXELS = 300_000_000

sys.path.insert(0, os.path.abspath("../src"))
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import warnings  # noqa: E402

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
    (r"py:.*", r"optional"),
    (r"py:.*", r"colour"),
    (r"py:.*", r"dartwork_mpl\.color\._views\..*"),
    (r"py:.*", r"matplotlib\..*"),
    (r"py:.*", r"numpy\..*"),
    (r"py:.*", r"np\..*"),
    (r"py:.*", r"scipy\..*"),
    (r"py:.*", r"pathlib\..*"),
    (r"py:.*", r"Path"),
    (r"py:.*", r"Figure"),
    (r"py:.*", r"Axes"),
    (r"py:.*", r"GridSpec"),
    (r"py:.*", r".*SubplotSpec.*"),
    (r"py:.*", r"OptimizeResult"),
    (r"py:.*", r"ndarray"),
    (r"py:.*", r"Colormap"),
    (r"py:.*", r"FontProperties"),
    (r"py:.*", r"'auto'"),
    (r"py:.*", r"\{'x'"),
    (r"py:.*", r"'y'\}"),
    (r"py:.*", r"dartwork_mpl\.style\.use"),
    (r"py:.*", r"Bbox"),
    (r"py:.*", r"collections\.abc\.Iterator"),
    (r"py:.*", r".*VisualWarning.*"),
    (r"py:.*", r"pydantic\..*"),
    (r"py:.*", r"BaseModel"),
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
    # Internal design notes — plans, specs, and audits kept in-repo for
    # provenance but not part of the public documentation surface. They
    # were emitting toctree / xref warnings on every build.
    "superpowers/**",
    "development/api_audit.md",
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "shibuya"
html_static_path = ["_static"]
html_css_files = [
    "custom.css",
    "font-specimens.css",
    "font-face.css",
    "dynamic_ux.css",
    # Radix-design overlay — last so it wins the cascade. Token aliases
    # and component-level rules layered on top of Shibuya defaults.
    # See _static/radix-design.css for the full token catalog.
    "radix-design.css",
]
html_js_files = ["custom.js", "dynamic_ux.js"]

# Prevent sections from gallery/index from appearing in the global toctree
# toctree_object_entries = False  # Removed as it might interfere with sidebar

# Remove version from the sidebar title
html_title = f"{project} documentation"

# -- Shibuya theme options ---------------------------------------------------
html_theme_options = {
    "github_url": "https://github.com/dartworklabs/dartwork-mpl",
    "accent_color": "teal",
    # 0 = only the active branch auto-expands; every other top-level
    # section starts collapsed. Stops the 9-row "Examples Gallery"
    # sub-tree from filling the sidebar on unrelated pages (#177).
    "globaltoc_expand_depth": 0,
    "dark_code": False,  # Use light code blocks (default Shibuya style)
    # Top-nav holds 7 entries — the bar fits at 1400 px because the
    # newest entry is the two-letter "AI" (#179). Prior consolidations:
    #   - "Color System" + "Fonts"  → "Design System"  (#172)
    #   - "Changelog"               → moved out of the bar (#177; the
    #                                 GitHub icon at the far right lands
    #                                 the visitor on the repo)
    #   - "AI" re-promoted from a Philosophy sub-page → first-class
    #     entry (#179) because agent-assisted plotting is the headline
    #     workflow, not a footnote
    "nav_links": [
        {"title": "Getting Started", "url": "usage_guide/quickstart"},
        {"title": "Usage Guide", "url": "usage_guide/index"},
        {"title": "Design System", "url": "design_system/index"},
        {"title": "Examples Gallery", "url": "examples_gallery/index"},
        {"title": "AI", "url": "ai/index"},
        {"title": "API Reference", "url": "api/index"},
        {"title": "Design Philosophy", "url": "philosophy/index"},
    ],
}


# -- Sphinx Gallery configuration --------------------------------------------


sphinx_gallery_conf = {
    "examples_dirs": [
        "examples_source/01_styling_and_themes",
        "examples_source/02_color_system",
        "examples_source/03_formatting",
        "examples_source/04_layout_and_annotations",
        "examples_source/05_helpers_api",
        "examples_source/06_chart_recipes",
        "examples_source/07_real_world_dashboards",
        "examples_source/08_creative_visualizations",
        "examples_source/09_ai_templates",
    ],
    "gallery_dirs": [
        "examples_gallery/01_styling_and_themes",
        "examples_gallery/02_color_system",
        "examples_gallery/03_formatting",
        "examples_gallery/04_layout_and_annotations",
        "examples_gallery/05_helpers_api",
        "examples_gallery/06_chart_recipes",
        "examples_gallery/07_real_world_dashboards",
        "examples_gallery/08_creative_visualizations",
        "examples_gallery/09_ai_templates",
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
    cleanup_sg_execution_times,
    copy_fonts_to_static,
    create_placeholder_index,
    generate_gallery_assets,
    generate_llms_full_txt,
    generate_template_index,
    purge_stale_gallery_artifacts,
    write_manual_indices,
)


def setup(app):
    # Cleanup runs first so sphinx-gallery starts from a clean slate
    # (priority < 500 = default; lower number runs earlier).
    app.connect("builder-inited", cleanup_sg_execution_times, priority=100)
    app.connect("builder-inited", purge_stale_gallery_artifacts, priority=110)
    app.connect("builder-inited", create_placeholder_index)
    app.connect("builder-inited", generate_gallery_assets)
    app.connect("builder-inited", copy_fonts_to_static)
    app.connect("builder-inited", generate_llms_full_txt)
    app.connect("builder-inited", generate_template_index)
    app.connect("env-before-read-docs", write_manual_indices)
    return {"parallel_read_safe": True}
