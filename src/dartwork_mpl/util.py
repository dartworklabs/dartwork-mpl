"""Miscellaneous utilities for Matplotlib figure management.

Collects small helper functions that do not warrant their own module.
Also re-exports core functions that were moved to dedicated modules
for backward compatibility.
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


def set_decimal(ax: Axes, xn: int | None = None, yn: int | None = None) -> None:
    """Fix the number of decimal places displayed on tick labels.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The Axes to modify.
    xn : int | None, optional
        Number of decimal places for x-axis tick labels.
        If None, the x-axis is left unchanged.
    yn : int | None, optional
        Number of decimal places for y-axis tick labels.
        If None, the y-axis is left unchanged.
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
    """Blend two colors according to a given weight (alpha).

    Parameters
    ----------
    color1 : str | tuple[float, float, float]
        First color to blend. Any format recognized by matplotlib.
    color2 : str | tuple[float, float, float]
        Second color to blend.
    alpha : float, optional
        Weight of the first color (between 0 and 1). Default is 0.5.

    Returns
    -------
    tuple[float, float, float]
        RGB tuple of the blended result.
    """
    color1 = mcolors.to_rgb(color1)
    color2 = mcolors.to_rgb(color2)

    r, g, b = (
        alpha * c1 + (1 - alpha) * c2
        for c1, c2 in zip(color1[:3], color2[:3], strict=False)
    )
    return r, g, b


def pseudo_alpha(
    color: str | tuple[float, float, float],
    alpha: float = 1.0,
    background: str | tuple[float, float, float] = "white",
) -> tuple[float, float, float]:
    """Return an opaque RGB that simulates alpha transparency against a background.

    True alpha can cause darkening artifacts when lines overlap or
    cover images. This function blends the color with the background
    to produce a flat (opaque) color that visually mimics transparency.

    Parameters
    ----------
    color : str | tuple[float, float, float]
        The target foreground color.
    alpha : float, optional
        Simulated opacity (0 to 1). Default is 1.0 (fully opaque).
    background : str | tuple[float, float, float], optional
        Background color to blend against. Default is "white".

    Returns
    -------
    tuple[float, float, float]
        RGB tuple of the composited color.
    """
    return mix_colors(color, background, alpha=alpha)


def cm2in(cm: float) -> float:
    """Convert centimeters to inches (legacy helper, deprecated in 0.4).

    Returns a plain ``float``. For 0.4+ code prefer
    :func:`dartwork_mpl.cm` (alias of :func:`dartwork_mpl.units.cm`),
    which returns an :class:`~dartwork_mpl.units.Inches` tagged value
    that ``dm.subplots(width=...)`` and :func:`parse_width` recognise
    without re-interpreting it as centimeters again.

    .. deprecated:: 0.4.0
        Use :func:`dartwork_mpl.cm` instead. Will be removed in 0.5.0.
        Emits a :class:`DeprecationWarning` on every call.

    Parameters
    ----------
    cm : float
        Value in centimeters.

    Returns
    -------
    float
        Equivalent value in inches.
    """
    import warnings as _warnings

    _warnings.warn(
        "dm.cm2in is deprecated and will be removed in 0.5.0. "
        "Use dm.cm(value) (returns an Inches-tagged float that "
        "dm.subplots(width=...) recognises directly).",
        DeprecationWarning,
        stacklevel=2,
    )
    return cm / 2.54


def make_offset(x: float, y: float, fig: Figure) -> ScaledTranslation:
    """Create a translation offset transform for positioning figure elements.

    Parameters
    ----------
    x : float
        Horizontal offset in points.
    y : float
        Vertical offset in points.
    fig : matplotlib.figure.Figure
        The Figure whose DPI scale is used.

    Returns
    -------
    matplotlib.transforms.ScaledTranslation
        A translation transform that can be added to other transforms.
    """
    dx, dy = x / 72, y / 72
    offset = ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    return offset
