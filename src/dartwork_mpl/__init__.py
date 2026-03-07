"""dartwork-mpl: Enhanced matplotlib styling and color utilities.

This package provides enhanced styling, color management, and utility
functions for matplotlib visualizations.
"""

__version__ = "0.1.1"

# Import cmap, font, icon, and xplot modules for explicit access
from . import (
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
from .color import Color, cspace, hex, named, oklab, oklch, rgb

# Import constant module exports
from .constant import DW, SW

# Import icon module exports
from .icon import icon_font, icon_font_path, list_icon_fonts

# Import install module exports
from .install import install_llm_txt, uninstall_llm_txt

# I/O
from .io import save_and_show, save_formats, show

# Layout
from .layout import get_bounding_box, simple_layout

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
    # Icon module
    "icon_font",
    "icon_font_path",
    "list_icon_fonts",
    # Constant module
    "DW",
    "SW",
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
    "simple_layout",
    "get_bounding_box",
    # Color utilities
    "mix_colors",
    "pseudo_alpha",
    # Units
    "cm2in",
    "make_offset",
    # Formatting
    "set_decimal",
    # I/O
    "save_formats",
    "save_and_show",
    "show",
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
