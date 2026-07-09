"""Miscellaneous utilities for Matplotlib figure management.

Collects small helper functions that do not warrant their own module.
Also re-exports core functions that were moved to dedicated modules
for backward compatibility.
"""

from __future__ import annotations

import math

# Re-exports for backward compatibility - these were moved to
# dedicated modules but many consumers still import from util.
from .annotation import arrow_axis, label_axes
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

import matplotlib.colors as mcolors
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.transforms import ScaledTranslation

from ._colors import Color


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
    """Blend two colors in OKLab space (perceptually uniform blend).

    Blends in OKLab rather than gamma-encoded sRGB, so midpoints avoid the
    "muddy" saturation dip that naive RGB mixing produces for saturated hues
    (e.g. red + blue → purple, not a dark desaturated grey).

    Parameters
    ----------
    color1 : str | tuple[float, float, float]
        First color to blend. Any format recognized by matplotlib.
    color2 : str | tuple[float, float, float]
        Second color to blend. Any format recognized by matplotlib.
    alpha : float, optional
        Weight of *color1* (0 → color2, 1 → color1). Default is 0.5.

    Returns
    -------
    tuple[float, float, float]
        sRGB tuple of the blended result, compatible with any matplotlib
        ``color=`` argument.

    Raises
    ------
    ValueError
        If ``alpha`` is not a finite number in ``[0, 1]``. Values outside
        the closed interval extrapolate and gamut-clamp to a
        plausible-looking but wrong colour (e.g. ``alpha=2`` yields
        salmon for a red/blue blend), so they are rejected rather than
        silently returned.

    Notes
    -----
    The result will differ subtly from previous versions for non-grayscale
    blends — gradients now look smoother and less desaturated through
    saturated midpoints.  ``dm.pseudo_alpha`` (which delegates to this
    function) inherits the same improvement.
    """
    if not math.isfinite(alpha) or not 0.0 <= alpha <= 1.0:
        raise ValueError(
            f"alpha must be a finite number in [0, 1], got {alpha!r}"
        )
    r1, g1, b1 = mcolors.to_rgb(color1)
    r2, g2, b2 = mcolors.to_rgb(color2)
    c1 = Color.from_rgb(r1, g1, b1)
    c2 = Color.from_rgb(r2, g2, b2)
    L1, a1, b1_ok = c1.to_oklab()
    L2, a2, b2_ok = c2.to_oklab()
    L = alpha * L1 + (1.0 - alpha) * L2
    a = alpha * a1 + (1.0 - alpha) * a2
    b_blend = alpha * b1_ok + (1.0 - alpha) * b2_ok
    return Color.from_oklab(L, a, b_blend).to_rgb()


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
    return ScaledTranslation(dx, dy, fig.dpi_scale_trans)
