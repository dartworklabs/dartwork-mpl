"""View classes for color space access.

Provides attribute-based access to OKLab, OKLCH, and RGB color
coordinates with support for reading, writing, unpacking, and indexing.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from ._conversion import (
    _linear_srgb_to_oklab,
    _oklab_to_linear_srgb,
    _oklab_to_oklch,
    _oklch_to_oklab,
    _linear_to_srgb,
    _srgb_to_linear,
)

if TYPE_CHECKING:
    from ._color import Color


# ============================================================================
# OKLab View
# ============================================================================


class OklabView:
    """
    View class for OKLab color space access.

    Provides attribute-based access to OKLab coordinates (L, a, b) with
    support for reading, writing, unpacking, and indexing.

    Parameters
    ----------
    color : Color
        The Color instance to view.

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
    >>> # Indexing
    >>> a = color.oklab[1]
    >>>
    >>> # Writing
    >>> color.oklab.L += 0.1
    >>> color.oklab.a = 0.2
    """

    def __init__(self, color: Color) -> None:
        """
        Initialize OklabView.

        Parameters
        ----------
        color : Color
            The Color instance to view.
        """
        self._color: Color = color

    @property
    def L(self) -> float:
        """
        Lightness component.

        Returns
        -------
        float
            Lightness value.
        """
        return self._color._L

    @L.setter
    def L(self, value: float) -> None:
        """
        Set lightness component.

        Parameters
        ----------
        value : float
            New lightness value.
        """
        self._color._L = float(value)

    @property
    def a(self) -> float:
        """
        Green-red component.

        Returns
        -------
        float
            Green-red value.
        """
        return self._color._a

    @a.setter
    def a(self, value: float) -> None:
        """
        Set green-red component.

        Parameters
        ----------
        value : float
            New green-red value.
        """
        self._color._a = float(value)

    @property
    def b(self) -> float:
        """
        Blue-yellow component.

        Returns
        -------
        float
            Blue-yellow value.
        """
        return self._color._b

    @b.setter
    def b(self, value: float) -> None:
        """
        Set blue-yellow component.

        Parameters
        ----------
        value : float
            New blue-yellow value.
        """
        self._color._b = float(value)

    def __getitem__(self, index: int) -> float:
        """
        Get component by index.

        Parameters
        ----------
        index : int
            Index (0=L, 1=a, 2=b).

        Returns
        -------
        float
            Component value.

        Raises
        ------
        IndexError
            If index is out of range.
        """
        if index == 0:
            return self.L
        elif index == 1:
            return self.a
        elif index == 2:
            return self.b
        else:
            raise IndexError(f"Index {index} out of range for OklabView")

    def __len__(self) -> int:
        """
        Get number of components.

        Returns
        -------
        int
            Always 3 (L, a, b).
        """
        return 3

    def __iter__(self) -> OklabViewIterator:
        """
        Create iterator for unpacking.

        Returns
        -------
        OklabViewIterator
            Iterator over (L, a, b).
        """
        return OklabViewIterator(self)

    def __repr__(self) -> str:
        """
        String representation.

        Returns
        -------
        str
            String representation showing (L, a, b).
        """
        return f"OklabView(L={self.L:.4f}, a={self.a:.4f}, b={self.b:.4f})"


class OklabViewIterator:
    """Iterator for OklabView unpacking."""

    def __init__(self, view: OklabView) -> None:
        """
        Initialize iterator.

        Parameters
        ----------
        view : OklabView
            The view to iterate over.
        """
        self._view: OklabView = view
        self._index: int = 0

    def __iter__(self) -> OklabViewIterator:
        """Return self as iterator."""
        return self

    def __next__(self) -> float:
        """
        Get next component.

        Returns
        -------
        float
            Next component value.

        Raises
        ------
        StopIteration
            When all components have been returned.
        """
        if self._index >= 3:
            raise StopIteration
        value: float = self._view[self._index]
        self._index += 1
        return value


# ============================================================================
# OKLCH View
# ============================================================================


class OklchView:
    """
    View class for OKLCH color space access.

    Provides attribute-based access to OKLCH coordinates (L, C, h) with
    support for reading, writing, unpacking, and indexing.

    Parameters
    ----------
    color : Color
        The Color instance to view.

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
    >>> # Indexing
    >>> C = color.oklch[1]
    >>>
    >>> # Writing
    >>> color.oklch.C *= 1.2
    >>> color.oklch.h = 180
    """

    def __init__(self, color: Color) -> None:
        """
        Initialize OklchView.

        Parameters
        ----------
        color : Color
            The Color instance to view.
        """
        self._color: Color = color

    def _get_oklch(self) -> tuple[float, float, float]:
        """
        Get current OKLCH values.

        Returns
        -------
        tuple[float, float, float]
            (L, C, h) where h is in degrees.
        """
        return self._color.to_oklch()

    def _update_oklab(self, L: float, C: float, h: float) -> None:
        """
        Update Color from OKLCH values.

        Parameters
        ----------
        L : float
            Lightness.
        C : float
            Chroma.
        h : float
            Hue in degrees.
        """
        h_rad: float = math.radians(h)
        _, a, b = _oklch_to_oklab(L, C, h_rad)
        self._color._L = float(L)
        self._color._a = float(a)
        self._color._b = float(b)

    @property
    def L(self) -> float:
        """
        Lightness component.

        Returns
        -------
        float
            Lightness value.
        """
        L, _, _ = self._get_oklch()
        return L

    @L.setter
    def L(self, value: float) -> None:
        """
        Set lightness component.

        Parameters
        ----------
        value : float
            New lightness value.
        """
        _, C, h = self._get_oklch()
        self._update_oklab(float(value), C, h)

    @property
    def C(self) -> float:
        """
        Chroma component.

        Returns
        -------
        float
            Chroma value.
        """
        _, C, _ = self._get_oklch()
        return C

    @C.setter
    def C(self, value: float) -> None:
        """
        Set chroma component.

        Parameters
        ----------
        value : float
            New chroma value (must be >= 0).
        """
        if value < 0:
            raise ValueError("Chroma must be >= 0")
        L, _, h = self._get_oklch()
        self._update_oklab(L, float(value), h)

    @property
    def h(self) -> float:
        """
        Hue component in degrees.

        Returns
        -------
        float
            Hue value in degrees [0, 360).
        """
        _, _, h = self._get_oklch()
        return h

    @h.setter
    def h(self, value: float) -> None:
        """
        Set hue component.

        Parameters
        ----------
        value : float
            New hue value in degrees.
        """
        L, C, _ = self._get_oklch()
        # Normalize to [0, 360)
        h_normalized: float = float(value) % 360.0
        self._update_oklab(L, C, h_normalized)

    def __getitem__(self, index: int) -> float:
        """
        Get component by index.

        Parameters
        ----------
        index : int
            Index (0=L, 1=C, 2=h).

        Returns
        -------
        float
            Component value.

        Raises
        ------
        IndexError
            If index is out of range.
        """
        if index == 0:
            return self.L
        elif index == 1:
            return self.C
        elif index == 2:
            return self.h
        else:
            raise IndexError(f"Index {index} out of range for OklchView")

    def __len__(self) -> int:
        """
        Get number of components.

        Returns
        -------
        int
            Always 3 (L, C, h).
        """
        return 3

    def __iter__(self) -> OklchViewIterator:
        """
        Create iterator for unpacking.

        Returns
        -------
        OklchViewIterator
            Iterator over (L, C, h).
        """
        return OklchViewIterator(self)

    def __repr__(self) -> str:
        """
        String representation.

        Returns
        -------
        str
            String representation showing (L, C, h).
        """
        return f"OklchView(L={self.L:.4f}, C={self.C:.4f}, h={self.h:.1f})"


class OklchViewIterator:
    """Iterator for OklchView unpacking."""

    def __init__(self, view: OklchView) -> None:
        """
        Initialize iterator.

        Parameters
        ----------
        view : OklchView
            The view to iterate over.
        """
        self._view: OklchView = view
        self._index: int = 0

    def __iter__(self) -> OklchViewIterator:
        """Return self as iterator."""
        return self

    def __next__(self) -> float:
        """
        Get next component.

        Returns
        -------
        float
            Next component value.

        Raises
        ------
        StopIteration
            When all components have been returned.
        """
        if self._index >= 3:
            raise StopIteration
        value: float = self._view[self._index]
        self._index += 1
        return value


# ============================================================================
# RGB View
# ============================================================================


class RgbView:
    """
    View class for RGB color space access.

    Provides attribute-based access to RGB coordinates (r, g, b) with
    support for reading, writing, unpacking, and indexing.

    Parameters
    ----------
    color : Color
        The Color instance to view.

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
    >>> # Indexing
    >>> g = color.rgb[1]
    >>>
    >>> # Writing
    >>> color.rgb.r = 0.9
    >>> color.rgb.g += 0.1
    """

    def __init__(self, color: Color) -> None:
        """
        Initialize RgbView.

        Parameters
        ----------
        color : Color
            The Color instance to view.
        """
        self._color: Color = color

    def _get_rgb(self) -> tuple[float, float, float]:
        """
        Get current RGB values.

        Returns
        -------
        tuple[float, float, float]
            (r, g, b) in range [0, 1].
        """
        return self._color.to_rgb()

    def _update_oklab(self, r: float, g: float, b: float) -> None:
        """
        Update Color from RGB values.

        Parameters
        ----------
        r : float
            Red component [0, 1].
        g : float
            Green component [0, 1].
        b : float
            Blue component [0, 1].
        """
        # Clamp to [0, 1]
        r_clamped: float = max(0.0, min(1.0, r))
        g_clamped: float = max(0.0, min(1.0, g))
        b_clamped: float = max(0.0, min(1.0, b))

        # Convert sRGB to linear RGB
        r_linear: float | np.ndarray = _srgb_to_linear(r_clamped)
        g_linear: float | np.ndarray = _srgb_to_linear(g_clamped)
        b_linear: float | np.ndarray = _srgb_to_linear(b_clamped)

        # Convert to OKLab
        L: float
        a: float
        b_val: float
        L, a, b_val = _linear_srgb_to_oklab(
            float(r_linear), float(g_linear), float(b_linear)
        )

        self._color._L = float(L)
        self._color._a = float(a)
        self._color._b = float(b_val)

    @property
    def r(self) -> float:
        """
        Red component.

        Returns
        -------
        float
            Red value in range [0, 1].
        """
        r, _, _ = self._get_rgb()
        return r

    @r.setter
    def r(self, value: float) -> None:
        """
        Set red component.

        Parameters
        ----------
        value : float
            New red value (will be clamped to [0, 1]).
        """
        _, g, b = self._get_rgb()
        self._update_oklab(float(value), g, b)

    @property
    def g(self) -> float:
        """
        Green component.

        Returns
        -------
        float
            Green value in range [0, 1].
        """
        _, g, _ = self._get_rgb()
        return g

    @g.setter
    def g(self, value: float) -> None:
        """
        Set green component.

        Parameters
        ----------
        value : float
            New green value (will be clamped to [0, 1]).
        """
        r, _, b = self._get_rgb()
        self._update_oklab(r, float(value), b)

    @property
    def b(self) -> float:
        """
        Blue component.

        Returns
        -------
        float
            Blue value in range [0, 1].
        """
        _, _, b = self._get_rgb()
        return b

    @b.setter
    def b(self, value: float) -> None:
        """
        Set blue component.

        Parameters
        ----------
        value : float
            New blue value (will be clamped to [0, 1]).
        """
        r, g, _ = self._get_rgb()
        self._update_oklab(r, g, float(value))

    def __getitem__(self, index: int) -> float:
        """
        Get component by index.

        Parameters
        ----------
        index : int
            Index (0=r, 1=g, 2=b).

        Returns
        -------
        float
            Component value.

        Raises
        ------
        IndexError
            If index is out of range.
        """
        if index == 0:
            return self.r
        elif index == 1:
            return self.g
        elif index == 2:
            return self.b
        else:
            raise IndexError(f"Index {index} out of range for RgbView")

    def __len__(self) -> int:
        """
        Get number of components.

        Returns
        -------
        int
            Always 3 (r, g, b).
        """
        return 3

    def __iter__(self) -> RgbViewIterator:
        """
        Create iterator for unpacking.

        Returns
        -------
        RgbViewIterator
            Iterator over (r, g, b).
        """
        return RgbViewIterator(self)

    def __repr__(self) -> str:
        """
        String representation.

        Returns
        -------
        str
            String representation showing (r, g, b).
        """
        return f"RgbView(r={self.r:.4f}, g={self.g:.4f}, b={self.b:.4f})"


class RgbViewIterator:
    """Iterator for RgbView unpacking."""

    def __init__(self, view: RgbView) -> None:
        """
        Initialize iterator.

        Parameters
        ----------
        view : RgbView
            The view to iterate over.
        """
        self._view: RgbView = view
        self._index: int = 0

    def __iter__(self) -> RgbViewIterator:
        """Return self as iterator."""
        return self

    def __next__(self) -> float:
        """
        Get next component.

        Returns
        -------
        float
            Next component value.

        Raises
        ------
        StopIteration
            When all components have been returned.
        """
        if self._index >= 3:
            raise StopIteration
        value: float = self._view[self._index]
        self._index += 1
        return value
