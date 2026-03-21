"""dartwork-mpl: Enhanced styling and color utilities for Matplotlib.

This package provides enhanced styling, color management, and various
utility functions for Matplotlib visualizations.
"""

__version__ = "0.3.1"

# Import cmap, font, icon, and xplot modules for explicit access
from . import (
    agent_utils,  # noqa: F401
    cmap,  # noqa: F401
    font,  # noqa: F401
    icon,  # noqa: F401
    xplot,  # noqa: F401
)

# Axes annotation
from .annotation import arrow_axis, label_axes

# Import asset_viz module exports
from .asset_viz import *  # noqa: F403

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

# Import constant module exports
from .constant import (
    DW,
    FS_A4,
    FS_DOUBLE,
    FS_GOLDEN,
    FS_SINGLE,
    FS_SLIDE,
    FS_SQUARE,
    FS_TALL,
    FS_WIDE,
    SW,
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
from .layout import auto_layout, get_bounding_box, set_xmargin, set_ymargin, simple_layout

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

# Prompt utilities
from .prompt import copy_prompt, get_prompt, list_prompts, prompt_path

# --- Explicit imports from split modules (formerly in util.py) ---
# Scaling helpers
from .scale import fs, fw, lw

# Import style module exports
from .style import Style, list_styles, load_style_dict, style, style_path

# Color utilities
from .util import cm2in, make_offset, mix_colors, pseudo_alpha, set_decimal

# Import validate module exports
from .validate import validate_figure

# Extended plot functions
from .xplot import plot_diverging_bar

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
    # Constant module
    "DW",
    "SW",
    "FS_SINGLE",
    "FS_DOUBLE",
    "FS_SQUARE",
    "FS_WIDE",
    "FS_TALL",
    "FS_GOLDEN",
    "FS_SLIDE",
    "FS_A4",
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
    # Units
    "cm2in",
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
    # Extended plots
    "plot_diverging_bar",
]

# --- Monkey-patch matplotlib.axes.Axes.twinx to always show right spine ---
import matplotlib as mpl
import matplotlib.axes

_original_twinx = matplotlib.axes.Axes.twinx

def _patched_twinx(self, *args, **kwargs):
    ax2 = _original_twinx(self, *args, **kwargs)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_linewidth(mpl.rcParams.get("axes.linewidth", 0.3))
    return ax2

matplotlib.axes.Axes.twinx = _patched_twinx

