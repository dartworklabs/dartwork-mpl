"""Compatibility re-exports for names that used to live in ``dartwork_mpl.util``.

Each function now lives in the slice that owns it (ADR 0005); this module
only re-exports them unchanged so ``from dartwork_mpl.util import X`` keeps
working. tests/test_util.py pins that every name is its owner's object.
"""

from __future__ import annotations

from ._colors.blend import mix_colors, pseudo_alpha
from .annotation import arrow_axis, label_axes, make_offset
from .formatting import set_decimal
from .io import save_and_show, save_formats, show
from .layout import get_bounding_box, simple_layout
from .prompt import copy_prompt, get_prompt, list_prompts, prompt_path
from .scale import fs, fw, lw

__all__ = [
    "arrow_axis",
    "copy_prompt",
    "fs",
    "fw",
    "get_bounding_box",
    "get_prompt",
    "label_axes",
    "list_prompts",
    "lw",
    "make_offset",
    "mix_colors",
    "prompt_path",
    "pseudo_alpha",
    "save_and_show",
    "save_formats",
    "set_decimal",
    "show",
    "simple_layout",
]
