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
    "sphinx.ext.graphviz",
    "myst_parser",
    "sphinx_gallery.gen_gallery",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_tabs.tabs",
    "sphinxcontrib.mermaid",
]

# --- Graphviz (sphinx.ext.graphviz) ---
# Emit SVG (vector, crisp at any zoom) and let it shrink/grow naturally.
# Note: requires the `dot` binary on $PATH (sudo apt install graphviz / brew
# install graphviz). The diagrams PoC page uses the dot directive to render
# the module dependency graph extracted automatically from src/dartwork_mpl/.
graphviz_output_format = "svg"
graphviz_dot_args = [
    "-Gfontname=Inter, system-ui, sans-serif",
    "-Nfontname=Inter, system-ui, sans-serif",
    "-Efontname=Inter, system-ui, sans-serif",
    "-Gbgcolor=transparent",
]

# Mermaid theming — keep the diagram visually aligned with the dartwork-design
# overlay (light fills, hairline borders, accent-9 highlights).
mermaid_init_js = """mermaid.initialize({
  startOnLoad: true,
  theme: 'base',
  themeVariables: {
    fontFamily: 'Inter, system-ui, sans-serif',
    fontSize: '14px',
    primaryColor: '#ffffff',
    primaryTextColor: '#1c2024',
    primaryBorderColor: '#cdced6',
    lineColor: '#60646c',
    secondaryColor: '#f0f0f3',
    tertiaryColor: '#fcfcfd',
    edgeLabelBackground: '#ffffff'
  },
  // themeCSS is injected BEFORE Mermaid measures node geometry, so the
  // nowrap here widens each node to fit its longest <code> line instead of
  // wrapping it at a narrow default. The viewBox then grows naturally to
  // the real content width — earlier we stretched a too-narrow SVG with
  // `width: 100%`, which only blurred it (the user's "강제 확대만 한 느낌").
  themeCSS: [
    '.nodeLabel, .nodeLabel * { white-space: nowrap !important; }',
    '.nodeLabel code { font-size: 0.92em; padding: 1px 4px;',
    '  background: #f0f0f3; border-radius: 4px; }',
    '.edgeLabel { font-size: 12px; }',
    '.messageText, .actor, .labelText, .loopText, .noteText',
    '  { font-size: 13px; }'
  ].join(' '),
  // useMaxWidth: true keeps the SVG <= its container; the CSS in
  // dartwork-design.css Tier 7 then lets it use the *natural* content width
  // (up to 100%) instead of force-scaling. nodeSpacing/rankSpacing kept
  // moderate so the nowrap'd nodes don't collide.
  flowchart: {
    curve: 'basis',
    padding: 22,
    nodeSpacing: 60,
    rankSpacing: 62,
    useMaxWidth: true,
    htmlLabels: true
  },
  sequence: {
    useMaxWidth: true,
    boxMargin: 12,
    mirrorActors: false,
    actorMargin: 60,
    messageMargin: 40,
    wrap: false
  }
});"""
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
    "development/config-roadmap.md",
    "development/naming-audit.md",
    "development/path-handling-audit.md",
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
    # Radix-design overlay — token aliases + component-level rules layered on
    # top of Shibuya defaults. See _static/dartwork-design.css for the catalog.
    "dartwork-design.css",
    # Interactive primitive SSOT — loaded LAST so it wins the cascade and can
    # consume the radix tokens above. See _static/dm-interactive-system.md.
    "dm-interactive.css",
]
html_js_files = ["custom.js", "dynamic_ux.js", "mermaid_fit.js"]

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
        "examples_source/09_ai_templates_advanced",
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
        "examples_gallery/09_ai_templates_advanced",
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
    # Execute examples in parallel (joblib/loky) on a cache miss. The
    # output cache (each example's .py.md5 stamp) already skips unchanged
    # examples, so this speeds up the *changed*-example builds that the
    # cache can't help. Each example runs in its own worker process, so
    # the global rcParams a `dm.style.use(...)` mutates can't leak between
    # examples (stricter isolation than the serial path). Falls back to
    # serial automatically if joblib is unavailable. The generated gallery
    # tree is gitignored, so worker-order differences never dirty the repo.
    "parallel": True,
}

# Local fast-preview escape hatch: ``PLOT_GALLERY=0 sphinx-build ...``
# skips executing the 70+ examples (renders placeholders) so prose /
# layout changes preview in seconds. CI leaves it unset (full build).
# Must be a top-level config value, not a sphinx_gallery_conf key —
# sphinx-gallery reads ``config.plot_gallery`` and overwrites the dict
# entry at builder-inited, so the dict key alone has no effect. Keep it a
# *string* ("True"/"False") to match the config value's registered type
# (a bool trips Sphinx's "config value has type 'bool', defaults to
# 'str'" warning, which `-W` turns into a build error). Normalize the env
# input to a clean "True"/"False" so sphinx-gallery's `_bool_eval`
# ``eval()`` never sees a bare "true"/"" that would crash.
plot_gallery = (
    "False"
    if os.environ.get("PLOT_GALLERY", "1").strip().lower()
    in ("0", "false", "no", "off", "")
    else "True"
)

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
