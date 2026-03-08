"""Color class and public API wrapper functions.

Provides the main Color class for creating and manipulating colors
across multiple color spaces (OKLab, OKLCH, RGB, hex), along with
the cspace() interpolation function and convenience constructors.
"""

from __future__ import annotations

__all__ = [
    "Color",
    "cspace",
    "hex",
    "named",
    "oklab",
    "oklch",
    "rgb",
]

import math

import matplotlib.colors as mcolors
import numpy as np

from ._conversion import (
    _linear_srgb_to_oklab,
    _linear_to_srgb,
    _oklab_to_linear_srgb,
    _oklab_to_oklch,
    _oklch_to_oklab,
    _parse_hex,
    _rgb_to_hex,
    _srgb_to_linear,
)
from ._views import OklabView, OklchView, RgbView

# ============================================================================
# Color Class
# ============================================================================


class Color:
    """
    A color class that supports OKLab, OKLCH, RGB, and hex color spaces.

    Colors are stored internally as OKLab coordinates for efficient
    conversion. Use classmethods to create Color instances:
    from_oklab(), from_oklch(), from_rgb(), from_hex().
    """

    def __init__(self, L: float, a: float, b: float) -> None:
        """
        Private constructor. Use classmethods to create Color instances.

        Parameters
        ----------
        L, a, b : float
            OKLab coordinates.
        """
        self._L: float = float(L)
        self._a: float = float(a)
        self._b: float = float(b)

    @property
    def oklab(self) -> OklabView:
        """
        Get OKLab view of the color.

        Returns
        -------
        OklabView
            View object for OKLab color space access.

        Examples
        -----
        >>> import dartwork_mpl as dm
        >>> color = dm.oklab(0.7, 0.1, 0.2)
        >>>
        >>> # Attribute access
        >>> L = color.oklab.L
        >>> a = color.oklab.a
        >>>
        >>> # Unpacking
        >>> L, a, b = color.oklab
        >>>
        >>> # Writing
        >>> color.oklab.L += 0.1
        """
        return OklabView(self)

    @property
    def oklch(self) -> OklchView:
        """
        Get OKLCH view of the color.

        Returns
        -------
        OklchView
            View object for OKLCH color space access.

        Examples
        -----
        >>> import dartwork_mpl as dm
        >>> color = dm.oklch(0.7, 0.2, 120)
        >>>
        >>> # Attribute access
        >>> L = color.oklch.L
        >>> C = color.oklch.C
        >>> h = color.oklch.h
        >>>
        >>> # Unpacking
        >>> L, C, h = color.oklch
        >>>
        >>> # Writing
        >>> color.oklch.C *= 1.2
        """
        return OklchView(self)

    @property
    def rgb(self) -> RgbView:
        """
        Get RGB view of the color.

        Returns
        -------
        RgbView
            View object for RGB color space access.

        Examples
        -----
        >>> import dartwork_mpl as dm
        >>> color = dm.rgb(0.8, 0.2, 0.3)
        >>>
        >>> # Attribute access
        >>> r = color.rgb.r
        >>> g = color.rgb.g
        >>>
        >>> # Unpacking
        >>> r, g, b = color.rgb
        >>>
        >>> # Writing
        >>> color.rgb.r = 0.9
        """
        return RgbView(self)

    @classmethod
    def from_oklab(cls, L: float, a: float, b: float) -> Color:
        """
        Create a Color from OKLab coordinates.

        Parameters
        ----------
        L, a, b : float
            OKLab coordinates (L typically in [0, 1]).

        Returns
        -------
        Color
            Color instance.
        """
        return cls(L, a, b)

    @classmethod
    def from_oklch(cls, L: float, C: float, h: float) -> Color:
        """
        Create a Color from OKLCH coordinates.

        Parameters
        ----------
        L, C : float
            Lightness and Chroma (L typically in [0, 1], C >= 0).
        h : float
            Hue in degrees [0, 360).

        Returns
        -------
        Color
            Color instance.
        """
        # Convert degrees to radians for internal calculation
        h_rad: float = math.radians(h)
        _, a, b = _oklch_to_oklab(L, C, h_rad)
        return cls(L, a, b)

    @classmethod
    def from_rgb(cls, r: float, g: float, b: float) -> Color:
        """
        Create a Color from RGB values.

        Automatically detects if values are in [0, 1] or [0, 255] range.
        If all values are <= 1.0, treats as [0, 1]. Otherwise, treats as
        [0, 255].

        Parameters
        ----------
        r, g, b : float
            RGB values (auto-detected range).

        Returns
        -------
        Color
            Color instance.
        """
        # Auto-detect range
        r_norm: float = r
        g_norm: float = g
        b_norm: float = b
        if r > 1.0 or g > 1.0 or b > 1.0:
            # Assume 0-255 range
            r_norm = r / 255.0
            g_norm = g / 255.0
            b_norm = b / 255.0

        # Convert sRGB to linear RGB
        r_linear: float | np.ndarray = _srgb_to_linear(r_norm)
        g_linear: float | np.ndarray = _srgb_to_linear(g_norm)
        b_linear: float | np.ndarray = _srgb_to_linear(b_norm)

        # Convert to OKLab
        L: float
        a: float
        b_val: float
        L, a, b_val = _linear_srgb_to_oklab(
            float(r_linear), float(g_linear), float(b_linear)
        )

        return cls(L, a, b_val)

    @classmethod
    def from_hex(cls, hex_str: str) -> Color:
        """
        Create a Color from hex color string.

        Parameters
        ----------
        hex_str : str
            Hex color string (#RGB or #RRGGBB).

        Returns
        -------
        Color
            Color instance.
        """
        r: float
        g: float
        b: float
        r, g, b = _parse_hex(hex_str)
        return cls.from_rgb(r, g, b)

    @classmethod
    def from_name(cls, name: str) -> Color:
        """
        Create a Color from matplotlib color name.

        Supports all matplotlib color names including:
        - Basic colors: 'red', 'blue', 'green', etc.
        - Named colors: 'aliceblue', 'antiquewhite', etc.
        - Custom dartwork-mpl colors: 'oc.red5', 'tw.blue500', etc.

        Parameters
        ----------
        name : str
            Matplotlib color name (e.g., 'red', 'oc.blue5',
            'tw.blue500').

        Returns
        -------
        Color
            Color instance.

        Raises
        ------
        ValueError
            If the color name is not recognized by matplotlib.
        """
        try:
            # Use matplotlib's to_rgb to convert color name to RGB
            r: float
            g: float
            b: float
            r, g, b = mcolors.to_rgb(name)
            return cls.from_rgb(r, g, b)
        except ValueError as e:
            raise ValueError(f"Invalid color name: {name}. {e!s}") from e

    def to_oklab(self) -> tuple[float, float, float]:
        """
        Convert to OKLab coordinates.

        Returns
        -------
        tuple[float, float, float]
            (L, a, b) OKLab coordinates.
        """
        return (self._L, self._a, self._b)

    def to_oklch(self) -> tuple[float, float, float]:
        """
        Convert to OKLCH coordinates.

        Returns
        -------
        tuple[float, float, float]
            (L, C, h) OKLCH coordinates, where h is in degrees [0, 360).
        """
        L: float
        C: float
        h_rad: float
        L, C, h_rad = _oklab_to_oklch(self._L, self._a, self._b)
        # Convert radians to degrees
        h_deg: float = math.degrees(h_rad)
        # Normalize to [0, 360)
        h_deg = h_deg % 360.0
        return (L, C, h_deg)

    def to_rgb(self) -> tuple[float, float, float]:
        """
        Convert to RGB values.

        Returns
        -------
        tuple[float, float, float]
            (r, g, b) RGB values in range [0, 1].
        """
        # Convert OKLab to linear RGB
        r_linear: float
        g_linear: float
        b_linear: float
        r_linear, g_linear, b_linear = _oklab_to_linear_srgb(
            self._L, self._a, self._b
        )

        # Clamp to valid range
        r_linear_clamped: float = max(0.0, min(1.0, r_linear))
        g_linear_clamped: float = max(0.0, min(1.0, g_linear))
        b_linear_clamped: float = max(0.0, min(1.0, b_linear))

        # Convert linear RGB to sRGB
        r: float | np.ndarray = _linear_to_srgb(r_linear_clamped)
        g: float | np.ndarray = _linear_to_srgb(g_linear_clamped)
        b: float | np.ndarray = _linear_to_srgb(b_linear_clamped)

        # Convert numpy scalars/arrays to Python floats
        r_float: float = float(np.asarray(r).item())
        g_float: float = float(np.asarray(g).item())
        b_float: float = float(np.asarray(b).item())

        return (r_float, g_float, b_float)

    def to_hex(self) -> str:
        """
        Convert to hex color string.

        Returns
        -------
        str
            Hex color string (#RRGGBB).
        """
        r: float
        g: float
        b: float
        r, g, b = self.to_rgb()
        return _rgb_to_hex(r, g, b)

    def copy(self) -> Color:
        """
        Create a copy of the Color object.

        Returns
        -------
        Color
            A new Color instance with the same OKLab coordinates.

        Examples
        -----
        >>> import dartwork_mpl as dm
        >>> color = dm.oklab(0.7, 0.1, 0.2)
        >>> new_color = color.copy()
        >>>
        >>> # Modify the copy without affecting the original
        >>> new_color.oklab.L += 0.1
        >>> print(color.oklab.L)      # 0.7 (unchanged)
        >>> print(new_color.oklab.L)  # 0.8 (modified)
        """
        return Color(self._L, self._a, self._b)

    def __repr__(self) -> str:
        """
        String representation of Color.

        Returns
        -------
        str
            String representation showing OKLab coordinates.
        """
        return f"Color(oklab=({self._L:.4f}, {self._a:.4f}, {self._b:.4f}))"


# ============================================================================
# Color Space Interpolation
# ============================================================================


def cspace(
    start_color: Color | str,
    end_color: Color | str,
    n: int,
    space: str = "oklch",
) -> list[Color]:
    """
    Generate a list of colors by interpolating between two colors.

    Inspired by np.linspace, but for colors.

    Parameters
    ----------
    start_color : Color or str
        Starting color (Color instance or hex string).
    end_color : Color or str
        Ending color (Color instance or hex string).
    n : int
        Number of colors to generate (including start and end).
    space : str, optional
        Color space for interpolation: 'oklch' (default), 'oklab', or
        'rgb'. Default is 'oklch'.

    Returns
    -------
    list[Color]
        List of interpolated Color objects.

    Raises
    ------
    TypeError
        If start_color or end_color is not a Color instance or hex
        string.
    ValueError
        If space is not one of the supported color spaces.
    """
    # Convert input colors to Color objects if needed
    start_color_obj: Color
    if isinstance(start_color, str):
        start_color_obj = Color.from_hex(start_color)
    else:
        start_color_obj = start_color

    end_color_obj: Color
    if isinstance(end_color, str):
        end_color_obj = Color.from_hex(end_color)
    else:
        end_color_obj = end_color

    if not isinstance(start_color_obj, Color):
        raise TypeError(
            f"start_color must be Color instance or hex string, got {type(start_color)}"
        )
    if not isinstance(end_color_obj, Color):
        raise TypeError(
            f"end_color must be Color instance or hex string, got {type(end_color)}"
        )

    # Convert to target color space
    if space == "oklch":
        start_L: float
        start_C: float
        start_h: float
        start_L, start_C, start_h = start_color_obj.to_oklch()
        # h is in degrees

        end_L: float
        end_C: float
        end_h: float
        end_L, end_C, end_h = end_color_obj.to_oklch()
        # h is in degrees

        # Handle hue wrapping (shortest path in degrees)
        h_diff: float = end_h - start_h
        # Normalize to [-180, 180] range for shortest path
        if h_diff > 180:
            end_h -= 360
        elif h_diff < -180:
            end_h += 360

        # Interpolate
        L_values: np.ndarray = np.linspace(start_L, end_L, n)
        C_values: np.ndarray = np.linspace(start_C, end_C, n)
        h_values: np.ndarray = np.linspace(start_h, end_h, n)

        # Normalize hue values to [0, 360) before creating Color objects
        h_values = h_values % 360.0

        # Convert back to Color objects
        colors: list[Color] = [
            Color.from_oklch(L, C, h)
            for L, C, h in zip(L_values, C_values, h_values, strict=False)
        ]

    elif space == "oklab":
        start_L, start_a, start_b = start_color_obj.to_oklab()
        end_L, end_a, end_b = end_color_obj.to_oklab()

        # Interpolate
        L_values = np.linspace(start_L, end_L, n)
        a_values: np.ndarray = np.linspace(start_a, end_a, n)
        b_values: np.ndarray = np.linspace(start_b, end_b, n)

        # Convert back to Color objects
        colors = [
            Color.from_oklab(L, a, b)
            for L, a, b in zip(L_values, a_values, b_values, strict=False)
        ]

    elif space == "rgb":
        start_r: float
        start_g: float
        start_b: float
        start_r, start_g, start_b = start_color_obj.to_rgb()
        end_r: float
        end_g: float
        end_b: float
        end_r, end_g, end_b = end_color_obj.to_rgb()

        # Interpolate
        r_values: np.ndarray = np.linspace(start_r, end_r, n)
        g_values: np.ndarray = np.linspace(start_g, end_g, n)
        b_values = np.linspace(start_b, end_b, n)

        # Convert back to Color objects
        colors = [
            Color.from_rgb(r, g, b)
            for r, g, b in zip(r_values, g_values, b_values, strict=False)
        ]

    else:
        raise ValueError(
            f"Unsupported color space: {space}. Must be 'oklch', 'oklab', or 'rgb'"
        )

    return colors


# ============================================================================
# Wrapper Functions
# ============================================================================


def oklab(L: float, a: float, b: float) -> Color:
    """
    Convenience function to create a Color from OKLab coordinates.

    Parameters
    ----------
    L, a, b : float
        OKLab coordinates.

    Returns
    -------
    Color
        Color instance.
    """
    return Color.from_oklab(L, a, b)


def oklch(L: float, C: float, h: float) -> Color:
    """
    Convenience function to create a Color from OKLCH coordinates.

    Parameters
    ----------
    L, C : float
        Lightness and Chroma.
    h : float
        Hue in degrees [0, 360).

    Returns
    -------
    Color
        Color instance.
    """
    return Color.from_oklch(L, C, h)


def rgb(r: float, g: float, b: float) -> Color:
    """
    Convenience function to create a Color from RGB values.

    Parameters
    ----------
    r, g, b : float
        RGB values (auto-detected range: 0-1 or 0-255).

    Returns
    -------
    Color
        Color instance.
    """
    return Color.from_rgb(r, g, b)


def hex(hex_str: str) -> Color:
    """
    Convenience function to create a Color from hex color string.

    Parameters
    ----------
    hex_str : str
        Hex color string (#RGB or #RRGGBB).

    Returns
    -------
    Color
        Color instance.
    """
    return Color.from_hex(hex_str)


def named(color_name: str) -> Color:
    """
    Convenience function to create a Color from matplotlib color name.

    Parameters
    ----------
    color_name : str
        Matplotlib color name (e.g., 'red', 'oc.blue5',
        'tw.blue500').

    Returns
    -------
    Color
        Color instance.
    """
    import warnings

    if color_name.startswith("dm."):
        warnings.warn(
            f"The 'dm.' color prefix is deprecated and will be removed in a future version. "
            f"Please use 'dc.{color_name[3:]}' instead of '{color_name}'.",
            category=DeprecationWarning,
            stacklevel=2,
        )
    return Color.from_name(color_name)
