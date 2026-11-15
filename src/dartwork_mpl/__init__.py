"""dartwork-mpl: Enhanced styling and color utilities for Matplotlib.

This package provides enhanced styling, color management, and various
utility functions for Matplotlib visualizations.
"""

# Underscore-aliased so implementation imports don't leak into the
# public namespace (``dm.version`` / ``dm.Any`` /
# ``dm.PackageNotFoundError`` used to resolve).
from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _metadata_version

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

# Submodules reachable as ``dm.<submodule>``.
from . import font, guide, style

# Defects of a drawn figure
from .check import check

# Colour names and values (importing it registers them with matplotlib)
from .color import (
    Color,
    color,
    colors,
    cspace,
    ensure_contrast,
    hex,
    list_colors,
    make_palette,
    mix_colors,
    oklab,
    oklch,
    pseudo_alpha,
    readable_text_color,
    rgb,
    set_colors,
)

# Agent guidance: the skill, templates and anti-pattern lint
from .guide import lint as lint_code

# Value labels, panel letters, notes
from .labels import (
    add_note,
    annotate_corner,
    annotate_value,
    label_axes,
    label_bars,
    label_hline,
    label_line_ends,
)

# Layout
from .layout import simple_layout
from .legend import figure_legend, place_legend
from .length import Length, cm, col1, col2, inch, mm, pt

# Saving
from .save import save_formats

# Physical units and figure size
from .size import figsize, figsize_for, grid_shape, list_aspect_tokens

# Presets and preset-relative sizes
from .style import fs, fw, lw

# Tick text
from .ticks import (
    axis_unit,
    axis_unit_of,
    config,
    format_axis_billions,
    format_axis_currency,
    format_axis_dates,
    format_axis_millions,
    format_axis_myriad,
    format_axis_si,
    format_axis_year,
    rotate_tick_labels,
    set_decimal,
)

# Public surfaces that are provisional -- shape may change in a minor
# release without a full deprecation cycle. Documented in
# docs/development/api-stability.md. ``figsize_for`` (the preset's default
# canvas) and ``grid_shape`` may still change their kinds, tiers and layouts;
# ``add_note`` (a source line in the preset's note style) its placement;
# ``label_line_ends`` (line names instead of a legend) its spacing and colour;
# ``axis_unit`` / ``axis_unit_of`` (the axis unit in its label) their ladders,
# label template rules and unit rules; ``label_bars`` (value labels on bars)
# its placement, crowding and stacked-total rules; ``figure_legend`` (one
# legend for every panel) its side rule and which panel legends it removes.
EXPERIMENTAL: frozenset[str] = frozenset(
    {
        "add_note",
        "axis_unit",
        "axis_unit_of",
        "figsize_for",
        "figure_legend",
        "grid_shape",
        "label_bars",
        "label_line_ends",
    }
)

# Define __all__ for explicit exports. The order is intentionally
# grouped by module/concern (Color → Icon → Style → …), not
# alphabetical, so that readers scanning the public surface see
# related names together. RUF022 is silenced for that reason.

__all__ = [  # noqa: RUF022
    # API stability markers
    "EXPERIMENTAL",
    # Tick-text defaults
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
    "ensure_contrast",
    "readable_text_color",
    # Icon module
    # Presets and preset-relative sizes
    "style",
    "fs",
    "fw",
    "lw",
    # Layout
    "simple_layout",
    # Color utilities
    "mix_colors",
    "pseudo_alpha",
    # Physical units and figure size
    "cm",
    "inch",
    "mm",
    "pt",
    "col1",
    "col2",
    "Length",
    "figsize",
    "figsize_for",
    "grid_shape",
    "list_aspect_tokens",
    # Point-unit offsets
    # Formatting
    "set_decimal",
    "format_axis_millions",
    "format_axis_myriad",
    "format_axis_year",
    "format_axis_dates",
    "format_axis_billions",
    "format_axis_currency",
    "format_axis_si",
    "axis_unit",
    "axis_unit_of",
    "rotate_tick_labels",
    # Saving
    "save_formats",
    # Axes annotation
    "annotate_value",
    "add_note",
    "annotate_corner",
    "label_axes",
    "label_bars",
    "label_hline",
    "label_line_ends",
    "place_legend",
    "figure_legend",
    # Agent guidance
    "guide",
    "lint_code",
    # Defects of a drawn figure
    "check",
    "make_palette",
]

# Eagerly register the bundled fonts on import so that
# ``plt.rcParams["font.family"] = "Inter"`` (or any bundled family) resolves
# immediately after ``import dartwork_mpl`` — matching the documented
# contract. This is a one-time ~70 ms cost; the same font-manager work would
# otherwise run on the first ``dm.style.use(...)`` anyway. Named colors and
# all ``dc.*`` colormaps register eagerly through the ``dartwork_mpl.color``
# import above.
font.ensure_loaded()
