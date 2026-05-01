"""dartwork-mpl: Enhanced styling and color utilities for Matplotlib.

This package provides enhanced styling, color management, and various
utility functions for Matplotlib visualizations.
"""

__version__ = "0.4.0"

# ruff: noqa: E402

# Import submodules so they are accessible under ``dm.<submodule>``
# (validate_enhanced is the auto-fix companion to validate). The F401
# noqa is required because ruff's "unused-import" check can't see
# attribute-style access at the package level.
from . import (  # noqa: F401
    cmap,
    font,
    helpers,
    icon,
    lint,
    templates,
    validate_enhanced,
)

# Axes annotation
from .annotation import arrow_axis, label_axes

# Import color module exports
from .color import (
    Color,
    DartworkColor,
    DartworkColormap,
    cspace,
    hex,
    named,
    oklab,
    oklch,
    rgb,
)

# Import asset-diagnostic visualization helpers.
from .diagnostics import (
    classify_colormap,
    plot_colormaps,
    plot_colors,
    plot_fonts,
)

# Explore
from .explore import list_colormaps, list_palettes, show_palette

# Figure creation
from .figure import figure, subplots

# Formatting utilities
from .formatting import (
    format_axis_billions,
    format_axis_currency,
    format_axis_millions,
    format_axis_percent,
    format_axis_si,
    format_axis_thousands,
    rotate_tick_labels,
)

# Import icon module exports
from .icon import icon_font, icon_font_path, list_icon_fonts

# Import install module exports
from .install import install_llm_txt, uninstall_llm_txt

# I/O
from .io import save_and_show, save_formats, show

# Layout
from .layout import (
    auto_layout,
    get_bounding_box,
    set_xmargin,
    set_ymargin,
    simple_layout,
)

# Prompt utilities
from .prompt import copy_prompt, get_prompt, list_prompts, prompt_path

# --- Explicit imports from split modules (formerly in util.py) ---
# Scaling helpers
from .scale import fs, fw, lw

# Spine and grid utilities
from .spines import (
    add_frame,
    add_grid,
    hide_all_spines,
    hide_spines,
    minimal_axes,
    remove_grid,
    show_only_spines,
    style_spines,
)

# Import style module exports
from .style import Style, list_styles, load_style_dict, style, style_path

# Extended plot functions (from templates, formerly xplot)
from .templates import plot_diverging_bar

# Unit helpers (0.4+: free-form width input)
from .units import Inches, cm, inch, mm

# Color utilities
from .util import make_offset, mix_colors, pseudo_alpha, set_decimal

# Academic column-width sugar (0.4+).
col1: float = cm(9)
col2: float = cm(17)

# Validation entry points
from .validate import validate_figure
from .validate_enhanced import validate_with_fixes

# Define __all__ for explicit exports

__all__ = [
    # Color module
    "Color",
    "cspace",
    "hex",
    "named",
    "oklab",
    "oklch",
    "rgb",
    "DartworkColor",
    "DartworkColormap",
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
    # Install module
    "install_llm_txt",
    "uninstall_llm_txt",
    # Scaling helpers
    "fs",
    "fw",
    "lw",
    # Layout
    "auto_layout",
    "simple_layout",
    "get_bounding_box",
    "set_xmargin",
    "set_ymargin",
    # Color utilities
    "mix_colors",
    "pseudo_alpha",
    # Units (0.4+)
    "cm",
    "inch",
    "mm",
    "col1",
    "col2",
    "Inches",
    # Units (legacy helpers, kept for compatibility)
    "make_offset",
    # Formatting
    "set_decimal",
    "format_axis_percent",
    "format_axis_thousands",
    "format_axis_millions",
    "format_axis_billions",
    "format_axis_currency",
    "format_axis_si",
    "rotate_tick_labels",
    # I/O
    "save_formats",
    "save_and_show",
    "show",
    # Explore
    "list_palettes",
    "list_colormaps",
    "show_palette",
    # Figure creation
    "figure",
    "subplots",
    # Spine and grid utilities
    "hide_spines",
    "hide_all_spines",
    "show_only_spines",
    "style_spines",
    "add_grid",
    "remove_grid",
    "add_frame",
    "minimal_axes",
    # Axes annotation
    "label_axes",
    "arrow_axis",
    # Prompt utilities
    "prompt_path",
    "get_prompt",
    "list_prompts",
    "copy_prompt",
    # Validation
    "validate_figure",
    "validate_with_fixes",
    "validate_enhanced",
    # Extended plots
    "plot_diverging_bar",
    # Asset diagnostics (from diagnostics)
    "plot_colormaps",
    "plot_colors",
    "plot_fonts",
    "classify_colormap",
]

# --- Monkey-patch matplotlib.axes.Axes.twinx to always show right spine ---
import matplotlib as mpl
import matplotlib.axes

# Reentrance guard: ``importlib.reload(dartwork_mpl)`` would otherwise
# capture the already-patched function as ``_original_twinx`` and recurse
# infinitely on the next ``ax.twinx()`` call. We tag the wrapper with
# ``__dm_patched__`` and skip re-patching when that marker is present.
if not getattr(matplotlib.axes.Axes.twinx, "__dm_patched__", False):
    _original_twinx = matplotlib.axes.Axes.twinx

    def _patched_twinx(self, *args, **kwargs):
        ax2 = _original_twinx(self, *args, **kwargs)
        ax2.spines["right"].set_visible(True)
        ax2.spines["right"].set_linewidth(
            mpl.rcParams.get("axes.linewidth", 0.3)
        )
        return ax2

    _patched_twinx.__dm_patched__ = True  # type: ignore[attr-defined]
    matplotlib.axes.Axes.twinx = _patched_twinx  # type: ignore[method-assign]


# 0.3 width tokens (SW/MW/TW/DW/WIDTHS), figure-size tuples (FS_*),
# the cm2in helper, and the agent_utils/xplot module aliases were all
# deprecated in 0.4.0 and removed in 0.4.x. Accessing them now raises
# AttributeError. Migration paths: see docs/migration.md.
