"""dartwork-mpl: Enhanced styling and color utilities for Matplotlib.

This package provides enhanced styling, color management, and various
utility functions for Matplotlib visualizations.
"""

from ._build_entry import run_color_build_if_requested as _run_color_build

_run_color_build(__name__, __file__)
del _run_color_build

# ruff: noqa: E402

# Underscore-aliased so implementation imports don't leak into the
# public namespace (``dm.version`` / ``dm.Any`` /
# ``dm.PackageNotFoundError`` used to resolve).
from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _metadata_version
from typing import Any as _Any

# Derive the version from the installed distribution metadata so there
# is a single source of truth. For a built/released wheel this always
# equals ``pyproject.toml``. For an *editable* dev checkout the metadata
# is captured at install time, so a ``pyproject.toml`` version bump only
# shows up here after reinstalling (``uv sync`` / ``pip install -e .``).
# The fallback covers running from a source tree with no installed
# metadata at all.
try:
    __version__ = _metadata_version("dartwork-mpl")
except _PackageNotFoundError:  # pragma: no cover - source-tree fallback
    __version__ = "0.0.0+unknown"

# Import submodules so they are accessible under ``dm.<submodule>``
# (validate_fixes is the auto-fix companion to validate). F401 is
# silenced because ruff's "unused-import" check can't see
# attribute-style access at the package level.
from . import (  # noqa: F401
    font,
    helpers,
    icon,
    lint,
    templates,
    tokens,
    validate_fixes,
)

# Import color module exports
from ._colors import (
    Color,
    color,
    colors,
    cspace,
    ensure_contrast,
    hex,
    list_colors,
    oklab,
    oklch,
    readable_text_color,
    rgb,
    set_colors,
    show_colors,
)

# Import bundled agent-onboarding helpers
from .agent import AGENT_DOCS, agent_doc_path, get_agent_doc

# Axes annotation
from .annotation import (
    annotate_corner,
    annotate_value,
    arrow_axis,
    label_axes,
    label_hline,
    place_legend,
    wrap_axis_label,
    wrap_axis_labels,
)

# Config (process-wide behaviour-toggle defaults)
from .config import Config, config

# Import asset-diagnostic visualization helpers.
from .diagnostics import plot_fonts

# Formatting utilities
from .formatting import (
    avoid_tick_overlap,
    format_axis_billions,
    format_axis_currency,
    format_axis_millions,
    format_axis_myriad,
    format_axis_si,
    format_axis_year,
    recommend_tick_decimals,
    rotate_tick_labels,
)

# Import icon module exports
from .icon import icon_font, icon_font_path, list_icon_fonts

# I/O
from .io import save_and_show, save_formats, show

# Layout
from .layout import (
    adopt_axis_label_font,
    get_bounding_box,
    simple_layout,
    tight_crop,
)

# Prompt utilities
from .prompt import (
    copy_prompt,
    find_template,
    get_prompt,
    list_prompts,
    prompt_path,
)

# --- Explicit imports from split modules (formerly in util.py) ---
# Scaling helpers
from .scale import dpi, fs, fw, lw

# Import style module exports
from .style import (
    Style,
    install_twinx_patch,
    list_styles,
    load_style_dict,
    style,
    style_path,
)

# Extended plot functions (from templates, formerly xplot)
from .templates import plot_diverging_bar

# Unit helpers (0.4+: free-form width input)
from .units import (
    Length,
    cm,
    col1,
    col2,
    figsize,
    figsize_grid,
    inch,
    length,
    list_aspect_tokens,
    mm,
    pt,
)

# Color utilities
from .util import make_offset, mix_colors, pseudo_alpha, set_decimal

# Public surfaces that are provisional -- shape may change in a minor
# release without a full deprecation cycle. Documented in
# docs/development/api-stability.md. Empty today because the interactive
# UI is a subpackage, not an advertised top-level ``dm.ui`` attribute.
EXPERIMENTAL: frozenset[str] = frozenset()

# High-level composition helpers (T2 in the AI-readiness roadmap).
# These wrap the lower-level primitives above so that AI agents and
# humans alike can reach the most useful workflow utilities through a
# single ``dm.<name>`` access path. The submodule namespace
# (``dm.helpers.<name>``) remains available as well.
from .helpers import (
    check_figure_quality,
    make_palette,
    optimize_legend,
    suggest_chart_type,
    validate_data,
)

# Native lint + migration entry points (T4). The ``dm.lint`` name is
# the module itself (so ``dm.lint.lint(...)`` and
# ``dm.lint.migrate_legacy_code(...)`` already work). These aliases
# expose the two most common functions at the top level under
# unambiguous names so an offline agent can call ``dm.lint_code(...)``
# without spinning up the MCP server.
from .lint import lint as lint_code
from .lint import migrate_legacy_code

# Validation entry points
from .validate import validate_figure
from .validate_fixes import validate_with_fixes

# Define __all__ for explicit exports. The order is intentionally
# grouped by module/concern (Color → Icon → Style → …), not
# alphabetical, so that readers scanning the public surface see
# related names together. RUF022 is silenced for that reason.

__all__ = [  # noqa: RUF022
    # API stability markers
    "EXPERIMENTAL",
    # Config
    "Config",
    "config",
    # Color module
    "Color",
    "color",
    "colors",
    "cspace",
    "hex",
    "list_colors",
    "oklab",
    "oklch",
    "rgb",
    "set_colors",
    "show_colors",
    "ensure_contrast",
    "readable_text_color",
    # Icon module
    "icon_font",
    "icon_font_path",
    "list_icon_fonts",
    # Style module
    "Style",
    "list_styles",
    "load_style_dict",
    "style",
    "style_path",
    # Bundled agent-onboarding helpers
    "AGENT_DOCS",
    "agent_doc_path",
    "get_agent_doc",
    # Scaling helpers
    "dpi",
    "fs",
    "fw",
    "lw",
    # Layout
    "adopt_axis_label_font",
    "simple_layout",
    "tight_crop",
    "get_bounding_box",
    # Color utilities
    "mix_colors",
    "pseudo_alpha",
    # Units (0.4+)
    "cm",
    "inch",
    "mm",
    "pt",
    "length",
    "col1",
    "col2",
    "Length",
    "figsize",
    "figsize_grid",
    "list_aspect_tokens",
    "tokens",
    # Units (legacy helpers, kept for compatibility)
    "make_offset",
    # Formatting
    "set_decimal",
    "format_axis_millions",
    "format_axis_myriad",
    "format_axis_year",
    "format_axis_billions",
    "format_axis_currency",
    "format_axis_si",
    "recommend_tick_decimals",
    "rotate_tick_labels",
    "avoid_tick_overlap",
    # I/O
    "save_formats",
    "save_and_show",
    "show",
    # Axes annotation
    "annotate_value",
    "annotate_corner",
    "label_axes",
    "label_hline",
    "place_legend",
    "wrap_axis_label",
    "wrap_axis_labels",
    "arrow_axis",
    # Prompt utilities
    "prompt_path",
    "get_prompt",
    "list_prompts",
    "copy_prompt",
    "find_template",
    # Validation
    "validate_figure",
    "validate_with_fixes",
    "validate_fixes",
    # Helpers (high-level composition utilities)
    "validate_data",
    "make_palette",
    "optimize_legend",
    "suggest_chart_type",
    "check_figure_quality",
    # Native lint + migration (T4)
    "lint_code",
    "migrate_legacy_code",
    # Extended plots
    "plot_diverging_bar",
    # Asset diagnostics (from diagnostics)
    "plot_fonts",
]

# Twin axes always show their right spine (a dartwork-mpl style rule).
install_twinx_patch()


# Eagerly register the bundled fonts on import so that
# ``plt.rcParams["font.family"] = "Inter"`` (or any bundled family) resolves
# immediately after ``import dartwork_mpl`` — matching the documented
# contract. This is a one-time ~70 ms cost; the same font-manager work would
# otherwise run on the first ``dm.style.use(...)`` anyway. Named colors and
# all ``dc.*`` colormaps register eagerly through the ``dartwork_mpl._colors``
# import above.
font.ensure_loaded()


from ._compat import missing_attribute as _missing_attribute


def __getattr__(name: str) -> _Any:
    """Surface deprecation aliases and removed-name migration hints.

    Without this, ``dm.SW`` / ``dm.cm2in`` / ``dm.subplots`` /
    ``dm.install_llm_txt`` / ``dm.FS_SINGLE`` would raise Python's
    default ``AttributeError`` with no pointer to the replacement. See
    docs/migration.md for the full mapping.
    """
    return _missing_attribute(name, globals())
