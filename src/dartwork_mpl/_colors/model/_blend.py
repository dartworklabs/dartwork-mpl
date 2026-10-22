"""OKLab colour blending and alpha flattening over :class:`Color` values.

Part of the colour model sub-slice; exported as ``dm.mix_colors`` and
``dm.pseudo_alpha`` (and through the ``dartwork_mpl.util`` compatibility
module).
"""

from __future__ import annotations

import math

import matplotlib.colors as mcolors

from ._color import Color


def mix_colors(
    color1: str | tuple[float, float, float],
    color2: str | tuple[float, float, float],
    alpha: float = 0.5,
) -> tuple[float, float, float]:
    """Blend two colors along a perceptually oriented OKLab path.

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
