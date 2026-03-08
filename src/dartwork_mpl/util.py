"""Utility functions for matplotlib figure management.

This module retains small general-purpose helpers that don't justify
their own module, and re-exports symbols that were moved to
dedicated modules so that existing ``from dartwork_mpl.util import …``
statements continue to work.
"""

from __future__ import annotations

# Re-exports for backward compatibility – these were moved to
# dedicated modules but many consumers still import from util.
from .annotation import arrow_axis, label_axes
from .io import save_and_show, save_formats, show
from .layout import get_bounding_box, set_xmargin, set_ymargin, simple_layout
from .prompt import copy_prompt, get_prompt, list_prompts, prompt_path
from .scale import fs, fw, lw

__all__ = [
    # Re-exports (moved modules)
    "fs",
    "fw",
    "lw",
    "simple_layout",
    "get_bounding_box",
    "set_xmargin",
    "set_ymargin",
    "save_formats",
    "save_and_show",
    "show",
    "label_axes",
    "arrow_axis",
    "prompt_path",
    "get_prompt",
    "list_prompts",
    "copy_prompt",
    # Residual helpers (kept here)
    "set_decimal",
    "mix_colors",
    "pseudo_alpha",
    "cm2in",
    "make_offset",
]

import matplotlib.colors as mcolors
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.transforms import ScaledTranslation


def set_decimal(
    ax: Axes,
    xn: int | None = None,
    yn: int | None = None,
) -> None:
    """Set decimal places for tick labels.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes object to modify.
    xn : int, optional
        Number of decimal places for x-axis tick labels.
    yn : int, optional
        Number of decimal places for y-axis tick labels.
    """
    if xn is not None:
        xticks = ax.get_xticks()
        ax.set_xticks(xticks)
        ax.set_xticklabels([f"{x:.{xn}f}" for x in xticks])

    if yn is not None:
        yticks = ax.get_yticks()
        ax.set_yticks(yticks)
        ax.set_yticklabels([f"{y:.{yn}f}" for y in yticks])


def mix_colors(
    color1: str | tuple[float, float, float],
    color2: str | tuple[float, float, float],
    alpha: float = 0.5,
) -> tuple[float, float, float]:
    """Mix two colours.

    Parameters
    ----------
    color1 : colour
        First colour (any format accepted by matplotlib).
    color2 : colour
        Second colour (any format accepted by matplotlib).
    alpha : float, optional
        Weight of the first colour, between 0 and 1.

    Returns
    -------
    tuple
        RGB tuple of the mixed colour.
    """
    color1 = mcolors.to_rgb(color1)
    color2 = mcolors.to_rgb(color2)

    return tuple(
        alpha * c1 + (1 - alpha) * c2
        for c1, c2 in zip(color1, color2, strict=False)
    )


def pseudo_alpha(
    color: str | tuple[float, float, float],
    alpha: float = 1.0,
    background: str | tuple[float, float, float] = "white",
) -> tuple[float, float, float]:
    """Return a colour with pseudo alpha.

    Parameters
    ----------
    color : colour
        Colour to apply pseudo-transparency to.
    alpha : float, optional
        Alpha value between 0 and 1.
    background : colour, optional
        Background colour to mix with.

    Returns
    -------
    tuple
        RGB tuple of the resulting colour.
    """
    return mix_colors(color, background, alpha=alpha)


def cm2in(cm: float) -> float:
    """Convert centimetres to inches.

    Parameters
    ----------
    cm : float
        Value in centimetres.

    Returns
    -------
    float
        Value in inches.
    """
    return cm / 2.54


def make_offset(x: float, y: float, fig: Figure) -> ScaledTranslation:
    """Create a translation offset for figure elements.

    Parameters
    ----------
    x : float
        X offset in points.
    y : float
        Y offset in points.
    fig : matplotlib.figure.Figure
        Figure to create offset for.

    Returns
    -------
    matplotlib.transforms.ScaledTranslation
        Offset transform.
    """
    dx, dy = x / 72, y / 72
    offset = ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    return offset
