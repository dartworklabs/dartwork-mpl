"""View classes for color space access.

Provides attribute-based access to OKLab, OKLCH, and RGB color
coordinates with support for reading, writing, unpacking, and indexing.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Iterator

import numpy as np

from ._conversion import (
    _linear_srgb_to_oklab,
    _oklab_to_oklch,
    _oklch_to_oklab,
    _linear_to_srgb,
    _srgb_to_linear,
)

if TYPE_CHECKING:
    from ._color import Color


# ============================================================================
# Base View
# ============================================================================


class _BaseColorView(ABC):
    """Abstract base for color-space views.

    Subclasses must define ``_component_names`` and implement a
    ``__repr__`` method.  All common iteration, indexing, and
    length logic lives here.
    """

    _component_names: tuple[str, ...]
    """Names of the colour components (used for error messages)."""

    def __init__(self, color: Color) -> None:
        self._color: Color = color

    # -- Sequence protocol ---------------------------------------------------

    def __getitem__(self, index: int) -> float:
        """Get component by index.

        Parameters
        ----------
        index : int
            Component index (0-based).

        Returns
        -------
        float
            Component value.

        Raises
        ------
        IndexError
            If *index* is out of range.
        """
        try:
            name = self._component_names[index]
        except IndexError:
            cls_name = type(self).__name__
            raise IndexError(
                f"Index {index} out of range for {cls_name}",
            ) from None
        return getattr(self, name)

    def __len__(self) -> int:
        """Return number of components (always 3)."""
        return len(self._component_names)

    def __iter__(self) -> Iterator[float]:
        """Iterate over components for unpacking."""
        return _ColorViewIterator(self)

    @abstractmethod
    def __repr__(self) -> str: ...


class _ColorViewIterator:
    """Shared iterator for all colour-space views."""

    __slots__ = ("_view", "_index")

    def __init__(self, view: _BaseColorView) -> None:
        self._view = view
        self._index = 0

    def __iter__(self) -> _ColorViewIterator:
        return self

    def __next__(self) -> float:
        if self._index >= len(self._view):
            raise StopIteration
        value: float = self._view[self._index]
        self._index += 1
        return value


# ============================================================================
# OKLab View
# ============================================================================


class OklabView(_BaseColorView):
    """View class for OKLab color space access.

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

    _component_names = ("L", "a", "b")

    @property
    def L(self) -> float:
        """Lightness component."""
        return self._color._L

    @L.setter
    def L(self, value: float) -> None:
        self._color._L = float(value)

    @property
    def a(self) -> float:
        """Green-red component."""
        return self._color._a

    @a.setter
    def a(self, value: float) -> None:
        self._color._a = float(value)

    @property
    def b(self) -> float:
        """Blue-yellow component."""
        return self._color._b

    @b.setter
    def b(self, value: float) -> None:
        self._color._b = float(value)

    def __repr__(self) -> str:
        return f"OklabView(L={self.L:.4f}, a={self.a:.4f}, b={self.b:.4f})"


# ============================================================================
# OKLCH View
# ============================================================================


class OklchView(_BaseColorView):
    """View class for OKLCH color space access.

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

    _component_names = ("L", "C", "h")

    def _get_oklch(self) -> tuple[float, float, float]:
        """Get current OKLCH values."""
        return self._color.to_oklch()

    def _update_oklab(self, L: float, C: float, h: float) -> None:
        """Update Color from OKLCH values.

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
        """Lightness component."""
        L, _, _ = self._get_oklch()
        return L

    @L.setter
    def L(self, value: float) -> None:
        _, C, h = self._get_oklch()
        self._update_oklab(float(value), C, h)

    @property
    def C(self) -> float:
        """Chroma component."""
        _, C, _ = self._get_oklch()
        return C

    @C.setter
    def C(self, value: float) -> None:
        if value < 0:
            raise ValueError("Chroma must be >= 0")
        L, _, h = self._get_oklch()
        self._update_oklab(L, float(value), h)

    @property
    def h(self) -> float:
        """Hue component in degrees [0, 360)."""
        _, _, h = self._get_oklch()
        return h

    @h.setter
    def h(self, value: float) -> None:
        L, C, _ = self._get_oklch()
        h_normalized: float = float(value) % 360.0
        self._update_oklab(L, C, h_normalized)

    def __repr__(self) -> str:
        return f"OklchView(L={self.L:.4f}, C={self.C:.4f}, h={self.h:.1f})"


# ============================================================================
# RGB View
# ============================================================================


class RgbView(_BaseColorView):
    """View class for RGB color space access.

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

    _component_names = ("r", "g", "b")

    def _get_rgb(self) -> tuple[float, float, float]:
        """Get current RGB values in [0, 1]."""
        return self._color.to_rgb()

    def _update_oklab(self, r: float, g: float, b: float) -> None:
        """Update Color from RGB values.

        Parameters
        ----------
        r, g, b : float
            RGB components (clamped to [0, 1] internally).
        """
        r_c = max(0.0, min(1.0, r))
        g_c = max(0.0, min(1.0, g))
        b_c = max(0.0, min(1.0, b))

        r_lin: float | np.ndarray = _srgb_to_linear(r_c)
        g_lin: float | np.ndarray = _srgb_to_linear(g_c)
        b_lin: float | np.ndarray = _srgb_to_linear(b_c)

        L, a, b_val = _linear_srgb_to_oklab(
            float(r_lin), float(g_lin), float(b_lin),
        )
        self._color._L = float(L)
        self._color._a = float(a)
        self._color._b = float(b_val)

    @property
    def r(self) -> float:
        """Red component [0, 1]."""
        r, _, _ = self._get_rgb()
        return r

    @r.setter
    def r(self, value: float) -> None:
        _, g, b = self._get_rgb()
        self._update_oklab(float(value), g, b)

    @property
    def g(self) -> float:
        """Green component [0, 1]."""
        _, g, _ = self._get_rgb()
        return g

    @g.setter
    def g(self, value: float) -> None:
        r, _, b = self._get_rgb()
        self._update_oklab(r, float(value), b)

    @property
    def b(self) -> float:
        """Blue component [0, 1]."""
        _, _, b = self._get_rgb()
        return b

    @b.setter
    def b(self, value: float) -> None:
        r, g, _ = self._get_rgb()
        self._update_oklab(r, g, float(value))

    def __repr__(self) -> str:
        return f"RgbView(r={self.r:.4f}, g={self.g:.4f}, b={self.b:.4f})"


# -- Backward-compatible aliases for old iterator class names ----------------
OklabViewIterator = _ColorViewIterator
OklchViewIterator = _ColorViewIterator
RgbViewIterator = _ColorViewIterator
