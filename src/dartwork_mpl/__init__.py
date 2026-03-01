"""dartwork-mpl: Enhanced matplotlib styling and color utilities.

This package provides enhanced styling, color management, and utility
functions for matplotlib visualizations.
"""

__version__ = "0.1.0"

# Import font module to register fonts (no public exports)
# Import cmap module to register colormaps (no public exports)
from . import (
    cmap,  # noqa: F401
    font,  # noqa: F401
    icon,  # noqa: F401
)

# Import asset_viz module exports
from .asset_viz import *  # noqa: F403

# Import color module exports
from .color import Color, cspace, hex, named, oklab, oklch, rgb

# Import icon module exports
from .icon import icon_font, icon_font_path, list_icon_fonts

# Import constant module exports
from .constant import DW, SW

# Import install module exports
from .install import install_llm_txt, uninstall_llm_txt

# Import style module exports
from .style import Style, list_styles, load_style_dict, style, style_path

# Import util module exports
from .util import *  # noqa: F403

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
    # Prompt utilities (from util module)
    "prompt_path",
    "get_prompt",
    "list_prompts",
    "copy_prompt",
    # Figure utilities (from util module)
    "label_axes",
]
