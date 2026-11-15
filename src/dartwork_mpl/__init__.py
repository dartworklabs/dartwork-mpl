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
    color,
    colors,
    ensure_contrast,
    hex,
    list_colors,
    oklab,
    oklch,
    readable_text_color,
    rgb,
)

# Colour values
from .colorspace import Color

# Value labels, panel letters, notes (sized by the active preset)
from .compose.labels import add_note, annotate_value, label_axes, label_bars

# Layout, with what the other slices settle at the fitted size
from .compose.layout import simple_layout

# Figure size, and the active preset's canvas
from .compose.size import figsize_for
from .compose.style import join as _join_style

# Agent guidance: the skill and the anti-pattern lint
from .guide import lint as lint_code
from .labels import label_line_ends
from .legend import figure_legend, place_legend
from .length import Length, cm, col1, col2, inch, mm, pt

# Saving
from .save import save_formats
from .size import figsize

# Preset-relative sizes
from .style import fs, fw, lw

# Tick text
from .ticks import config, format_axis_myriad

# Define __all__ for explicit exports. The order is intentionally
# grouped by module/concern (Color → Icon → Style → …), not
# alphabetical, so that readers scanning the public surface see
# related names together. RUF022 is silenced for that reason.

__all__ = [  # noqa: RUF022
    # API stability markers
    # Tick-text defaults
    "config",
    # Color module
    "Color",
    "color",
    "colors",
    "hex",
    "list_colors",
    "oklab",
    "oklch",
    "rgb",
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
    # Point-unit offsets
    # Formatting
    "format_axis_myriad",
    # Saving
    "save_formats",
    # Axes annotation
    "annotate_value",
    "add_note",
    "label_axes",
    "label_bars",
    "label_line_ends",
    "place_legend",
    "figure_legend",
    # Agent guidance
    "guide",
    "lint_code",
    # Defects of a drawn figure
    "check",
]

# Eagerly register the bundled fonts on import so that
# ``plt.rcParams["font.family"] = "Inter"`` (or any bundled family) resolves
# immediately after ``import dartwork_mpl`` — matching the documented
# contract. This is a one-time ~70 ms cost; the same font-manager work would
# otherwise run on the first ``dm.style.use(...)`` anyway. Named colors and
# all ``dc.*`` colormaps register eagerly through the ``dartwork_mpl.color``
# import above.
font.ensure_loaded()

# A preset's locale picks the role colours from here on.
_join_style()
