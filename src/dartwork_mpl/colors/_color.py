"""Color class and public API wrapper functions.

Provides the core ``Color`` class for creating and manipulating colors
across OKLab, OKLCH, RGB, and Hex color spaces, the ``cspace()``
interpolation function, and convenient constructor functions.
"""

from __future__ import annotations

__all__ = ["Color", "color", "cspace", "hex", "oklab", "oklch", "rgb"]

import math
import re
from typing import Any

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

# Iterations for the binary chroma-reduction gamut search. ~C / 2**24
# precision — far below 8-bit (1/255) quantization, so the boundary is
# resolved exactly at hex precision while staying deterministic.
_GAMUT_SEARCH_ITERS = 24


def _linear_in_gamut(r: Any, g: Any, b: Any, tol: float = 1e-6) -> bool:
    """Whether linear-sRGB channels all fall within ``[0, 1]`` (± ``tol``)."""
    return all(
        -tol <= float(np.asarray(ch).item()) <= 1.0 + tol for ch in (r, g, b)
    )


# ============================================================================
# Color Class
# ============================================================================


class Color:
    """Color in OKLab/OKLCH/RGB/Hex color spaces.

    A wrapper over a single canonical store (OKLab coordinates) with
    per-space property views (``color.oklab`` / ``color.oklch`` /
    ``color.rgb``). The constructor takes a *string* (or pass-through
    :class:`Color`) — bare numerics are rejected because three floats
    give no way to tell OKLab apart from OKLCH or RGB. For
    already-typed numeric input, use :meth:`from_oklab` /
    :meth:`from_oklch` / :meth:`from_rgb` / :meth:`from_hex` /
    :meth:`from_name` (or the top-level wrappers :func:`oklab` /
    :func:`oklch` / :func:`rgb` / :func:`hex`).

    Equality and hashing are **by value** — two colors with the same
    OKLab coordinates compare equal (:meth:`__eq__`) and hash equal
    (:meth:`__hash__`).

    .. note::
       Unlike :class:`~dartwork_mpl.units.Length`, ``Color`` is
       currently **mutable**: the ``oklab`` / ``oklch`` / ``rgb`` views
       write back to the underlying store in place (hence :meth:`copy`).
       Because it is both mutable and value-hashable, do **not** mutate
       a ``Color`` after using it as a ``dict`` / ``set`` key. A future
       release will make ``Color`` immutable (view setters returning a
       new instance); see issue #233.

    Parameters
    ----------
    value : Color or str
        Either another :class:`Color` (returned as a fresh copy with
        the same OKLab coordinates) or a string parseable by
        :meth:`Color.parse` — hex (``"#ff0000"``), functional
        (``"rgb(1, 0, 0)"`` / ``"oklch(0.7, 0.15, 30)"`` /
        ``"oklab(...)"``), or a palette/matplotlib color name
        (``"oc.red5"``, ``"red"``).

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> dm.Color("#ff0000")
    >>> dm.Color("oklch(0.7, 0.15, 30)")
    >>> dm.Color("oc.red5")
    >>> dm.Color(dm.oklab(0.7, 0.1, 0.2))   # pass-through copy
    """

    def __init__(self, value: Color | str) -> None:
        if isinstance(value, Color):
            self._L: float = value._L
            self._a: float = value._a
            self._b: float = value._b
            return
        if isinstance(value, (bool, int, float)):
            # ``bool`` is an ``int`` subclass; trap before the str
            # branch so ``Color(True)`` and ``Color(1)`` produce the
            # same TypeError as ``Color(0.5)``.
            raise TypeError(
                f"Color(value) requires a color string like '#ff0000' / "
                f"'rgb(1, 0, 0)' / 'oklch(0.7, 0.15, 30)' / 'oc.red5', "
                f"or another Color. Got {type(value).__name__} "
                f"{value!r} — bare numbers carry no color space. For "
                f"OKLab coordinates use Color.from_oklab(L, a, b) or "
                f"dm.oklab(L, a, b); for OKLCH use Color.from_oklch / "
                f"dm.oklch; for RGB use Color.from_rgb / dm.rgb."
            )
        if not isinstance(value, str):
            raise TypeError(
                f"Color(value) accepts str or Color (got "
                f"{type(value).__name__})"
            )
        parsed = Color.parse(value)
        self._L = parsed._L
        self._a = parsed._a
        self._b = parsed._b

    @classmethod
    def _from_oklab(cls, L: float, a: float, b: float) -> Color:
        # Internal fast-path that skips str-parsing in __init__ — used
        # by every from_* factory and by copy(). Mirrors
        # ``Length._from_inch``.
        #
        # Validate finiteness at this single construction choke point so
        # a NaN/inf can never silently reach ``to_rgb`` and render as
        # white (the ``_rgb_to_hex`` NaN guard downstream is otherwise
        # unreachable in practice). Mirrors the ``from_rgb`` fail-loud
        # contract.
        for _name, _val in (("L", L), ("a", a), ("b", b)):
            if not math.isfinite(_val):
                raise ValueError(
                    f"OKLab component {_name}={_val!r} must be a finite number"
                )
        obj = cls.__new__(cls)
        obj._L = float(L)
        obj._a = float(a)
        obj._b = float(b)
        return obj

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
        return cls._from_oklab(L, a, b)

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
        # Reject negative chroma: OKLCH C is a radius (>= 0). A negative
        # value silently flips the hue by 180 deg (and breaks the
        # OKLCH round-trip), so fail loud to match the ``OklchView.C``
        # setter, which already rejects it.
        if C < 0:
            raise ValueError(f"from_oklch: C={C!r} must be >= 0")
        # Convert degrees to radians for internal calculation
        h_rad: float = math.radians(h)
        _, a, b = _oklch_to_oklab(L, C, h_rad)
        return cls._from_oklab(L, a, b)

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
        # Validate before the range heuristic so malformed input fails
        # loudly instead of silently producing an out-of-gamut color.
        for _name, _val in (("r", r), ("g", g), ("b", b)):
            if not math.isfinite(_val):
                raise ValueError(
                    f"from_rgb: {_name}={_val!r} must be a finite number"
                )
            if _val < 0.0:
                raise ValueError(
                    f"from_rgb: {_name}={_val!r} must be non-negative"
                )

        # Auto-detect range
        r_norm: float = r
        g_norm: float = g
        b_norm: float = b
        if r > 1.0 or g > 1.0 or b > 1.0:
            # At least one channel > 1.0 → interpret all as 0-255. Guard
            # the upper bound so a stray > 255 value (or a mixed-range
            # call) can't normalize to > 1.0 and silently distort the
            # color instead of erroring.
            for _name, _val in (("r", r), ("g", g), ("b", b)):
                if _val > 255.0:
                    raise ValueError(
                        f"from_rgb: {_name}={_val!r} exceeds 255 — channels "
                        f"are read as 0-255 because at least one is > 1.0; "
                        f"pass every channel in 0-1 or 0-255, not a mix"
                    )
                if 0.0 < _val < 1.0:
                    raise ValueError(
                        f"from_rgb: {_name}={_val!r} looks like a 0-1 value "
                        f"but channels are read as 0-255 because at least one "
                        f"is > 1.0; pass every channel in 0-1 or 0-255, not a mix"
                    )
            r_norm = r / 255.0
            g_norm = g / 255.0
            b_norm = b / 255.0

        # Convert sRGB to linear RGB
        r_linear: float | np.ndarray[Any, Any] = _srgb_to_linear(r_norm)
        g_linear: float | np.ndarray[Any, Any] = _srgb_to_linear(g_norm)
        b_linear: float | np.ndarray[Any, Any] = _srgb_to_linear(b_norm)

        # Convert to OKLab
        L: float
        a: float
        b_val: float
        L, a, b_val = _linear_srgb_to_oklab(
            float(r_linear), float(g_linear), float(b_linear)
        )

        return cls._from_oklab(L, a, b_val)

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

    _FUNCTIONAL_RE = re.compile(
        r"^(?P<func>rgb|oklch|oklab)\s*\(\s*(?P<args>.+?)\s*\)$", re.IGNORECASE
    )

    @classmethod
    def parse(cls, value: str) -> Color:
        """Parse a string in any supported form into a :class:`Color`.

        Routes by the leading character / token of ``value``:

        * ``"#rgb"`` / ``"#rrggbb"`` → :meth:`from_hex`.
        * ``"rgb(r, g, b)"`` (auto 0-1 / 0-255 detection),
          ``"oklch(L, C, h)"`` (h in degrees), ``"oklab(L, a, b)"``
          → corresponding factory. Function name is case-insensitive;
          arguments are comma-separated and tolerant of internal
          whitespace.
        * Anything else falls through to :meth:`from_name` (matplotlib
          named colors, ``oc.``, ``tw.``, ``md.``, ``ad.``, ``cu.``,
          ``pr.``, ``dc.``).

        Parameters
        ----------
        value : str
            The color string to parse. Surrounding whitespace is
            stripped.

        Returns
        -------
        Color

        Raises
        ------
        TypeError
            If ``value`` is not a :class:`str`.
        ValueError
            If a functional form has the wrong number of arguments,
            non-numeric arguments, or the underlying factory rejects
            the value.
        """
        if not isinstance(value, str):
            raise TypeError(
                f"Color.parse expects a str, got {type(value).__name__}"
            )
        text = value.strip()
        if text.startswith("#"):
            return cls.from_hex(text)
        match = cls._FUNCTIONAL_RE.match(text)
        if match is not None:
            func = match.group("func").lower()
            raw_args = match.group("args")
            try:
                nums = [float(part.strip()) for part in raw_args.split(",")]
            except ValueError as exc:
                raise ValueError(
                    f"{func}(...) arguments must be numeric: {raw_args!r}"
                ) from exc
            if len(nums) != 3:
                raise ValueError(
                    f"{func}(...) expects 3 arguments, got {len(nums)}: "
                    f"{raw_args!r}"
                )
            if func == "rgb":
                return cls.from_rgb(*nums)
            if func == "oklch":
                return cls.from_oklch(*nums)
            if func == "oklab":
                return cls.from_oklab(*nums)
            raise ValueError(f"unsupported color function: {func!r}")
        return cls.from_name(text)

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
            (r, g, b) sRGB values in range [0, 1].

        Notes
        -----
        Colors inside the sRGB gamut convert exactly. Out-of-gamut
        colors are gamut-mapped by **reducing chroma while holding
        lightness (L) and hue (h) fixed** — a binary search to the sRGB
        gamut boundary along the requested OKLCH hue line (CSS Color 4
        style) — so the rendered color keeps the requested L and h
        instead of the per-channel clamp's L/h drift. A final
        per-channel clamp absorbs sub-tolerance boundary residual and
        clips an achromatic L outside ``[0, 1]`` (which chroma reduction
        alone cannot represent). Use :meth:`in_gamut` to detect whether
        a color required mapping.
        """
        # Convert OKLab to linear RGB
        r_linear: float
        g_linear: float
        b_linear: float
        r_linear, g_linear, b_linear = _oklab_to_linear_srgb(
            self._L, self._a, self._b
        )

        if not _linear_in_gamut(r_linear, g_linear, b_linear):
            # Out of sRGB: reduce chroma holding L and h, binary-searching
            # the largest in-gamut chroma along the requested hue line so
            # the rendered color preserves lightness and hue.
            L, chroma, h_rad = _oklab_to_oklch(self._L, self._a, self._b)
            lo, hi = 0.0, chroma
            for _ in range(_GAMUT_SEARCH_ITERS):
                mid = (lo + hi) / 2.0
                _, a_mid, b_mid = _oklch_to_oklab(L, mid, h_rad)
                if _linear_in_gamut(*_oklab_to_linear_srgb(L, a_mid, b_mid)):
                    lo = mid
                else:
                    hi = mid
            _, a_g, b_g = _oklch_to_oklab(L, lo, h_rad)
            r_linear, g_linear, b_linear = _oklab_to_linear_srgb(L, a_g, b_g)

        # Final clamp absorbs sub-tolerance boundary residual (and clips
        # an achromatic L outside [0, 1] that chroma reduction can't fix).
        r_linear_clamped: float = max(0.0, min(1.0, r_linear))
        g_linear_clamped: float = max(0.0, min(1.0, g_linear))
        b_linear_clamped: float = max(0.0, min(1.0, b_linear))

        # Convert linear RGB to sRGB
        r: float | np.ndarray[Any, Any] = _linear_to_srgb(r_linear_clamped)
        g: float | np.ndarray[Any, Any] = _linear_to_srgb(g_linear_clamped)
        b: float | np.ndarray[Any, Any] = _linear_to_srgb(b_linear_clamped)

        # Convert numpy scalars/arrays to Python floats
        r_float: float = float(np.asarray(r).item())
        g_float: float = float(np.asarray(g).item())
        b_float: float = float(np.asarray(b).item())

        return (r_float, g_float, b_float)

    def in_gamut(self, tol: float = 1e-6) -> bool:
        """
        Whether this color is representable inside the sRGB gamut.

        Returns ``True`` when every linear-sRGB channel falls within
        ``[0, 1]`` (within ``tol``), i.e. :meth:`to_rgb` returns the
        color directly. Returns ``False`` for out-of-gamut colors, which
        :meth:`to_rgb` gamut-maps by reducing chroma while holding
        lightness and hue (so the rendered color stays close in L/h).

        Parameters
        ----------
        tol : float, optional
            Numerical tolerance on the ``[0, 1]`` bounds, to absorb
            floating-point error at the gamut boundary. Default ``1e-6``.

        Returns
        -------
        bool

        Examples
        --------
        >>> import dartwork_mpl as dm
        >>> dm.Color.from_oklch(0.7, 0.05, 30).in_gamut()
        True
        >>> dm.Color.from_oklch(0.7, 0.40, 30).in_gamut()
        False
        """
        r_linear, g_linear, b_linear = _oklab_to_linear_srgb(
            self._L, self._a, self._b
        )
        return _linear_in_gamut(r_linear, g_linear, b_linear, tol)

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
        return Color._from_oklab(self._L, self._a, self._b)

    def __repr__(self) -> str:
        """
        String representation of Color.

        Returns
        -------
        str
            String representation showing OKLab coordinates.
        """
        return f"Color(oklab=({self._L:.4f}, {self._a:.4f}, {self._b:.4f}))"

    def __eq__(self, other: object) -> bool:
        """Value equality by OKLab coordinates.

        Two colors are equal when their canonical OKLab coordinates
        match exactly. Comparison against a non-:class:`Color` returns
        ``NotImplemented`` so Python falls back to identity (``==``
        ultimately yields ``False`` against unrelated types).
        """
        if not isinstance(other, Color):
            return NotImplemented
        return (self._L, self._a, self._b) == (other._L, other._a, other._b)

    def __hash__(self) -> int:
        """Hash by OKLab coordinates (consistent with :meth:`__eq__`).

        ``Color`` is currently mutable, so treat a hashed color as
        effectively frozen: do not mutate an instance used as a
        ``dict`` / ``set`` key. See issue #233.
        """
        return hash((self._L, self._a, self._b))


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
    Interpolate between two colors to produce a list of evenly spaced colors.

    Similar to numpy's ``linspace``, but operating in color space.

    Parameters
    ----------
    start_color : Color | str
        Starting color (Color instance or hex string).
    end_color : Color | str
        Ending color (Color instance or hex string).
    n : int
        Total number of colors to generate (including start and end).
    space : str, optional
        Color space for interpolation: 'oklch' (default), 'oklab', or 'rgb'.
        'oklch' produces the most perceptually uniform results.

    Returns
    -------
    list[Color]
        List of interpolated Color objects.

    Raises
    ------
    TypeError
        If start_color or end_color is not a Color instance or hex string.
    ValueError
        If an unsupported color space is specified.
    """
    # Convert string inputs through the unified Color parser so cspace
    # accepts everything dm.color does — hex, palette names, and the
    # functional rgb(...) / oklch(...) / oklab(...) forms — not just hex
    # and palette names (the old branch rejected oklch(...) strings,
    # inconsistent with dm.color / Color(...)).
    start_color_obj: Color = (
        Color(start_color) if isinstance(start_color, str) else start_color
    )
    end_color_obj: Color = (
        Color(end_color) if isinstance(end_color, str) else end_color
    )

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
        L_values: np.ndarray[Any, Any] = np.linspace(start_L, end_L, n)
        C_values: np.ndarray[Any, Any] = np.linspace(start_C, end_C, n)
        h_values: np.ndarray[Any, Any] = np.linspace(start_h, end_h, n)

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
        a_values: np.ndarray[Any, Any] = np.linspace(start_a, end_a, n)
        b_values: np.ndarray[Any, Any] = np.linspace(start_b, end_b, n)

        # Convert back to Color objects
        colors = [
            Color.from_oklab(L, a, b)
            for L, a, b in zip(L_values, a_values, b_values, strict=False)
        ]

    elif space == "rgb":
        rgb_start_r: float
        rgb_start_g: float
        rgb_start_b: float
        rgb_start_r, rgb_start_g, rgb_start_b = start_color_obj.to_rgb()
        rgb_end_r: float
        rgb_end_g: float
        rgb_end_b: float
        rgb_end_r, rgb_end_g, rgb_end_b = end_color_obj.to_rgb()

        # Interpolate
        r_values: np.ndarray[Any, Any] = np.linspace(rgb_start_r, rgb_end_r, n)
        g_values: np.ndarray[Any, Any] = np.linspace(rgb_start_g, rgb_end_g, n)
        b_values = np.linspace(rgb_start_b, rgb_end_b, n)

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
    Convenience wrapper to create a Color from OKLab coordinates.

    Parameters
    ----------
    L, a, b : float
        OKLab color coordinates.

    Returns
    -------
    Color
        A new Color instance.
    """
    return Color.from_oklab(L, a, b)


def oklch(L: float, C: float, h: float) -> Color:
    """
    Convenience wrapper to create a Color from OKLCH coordinates.

    Parameters
    ----------
    L, C : float
        Lightness and chroma values.
    h : float
        Hue angle in degrees [0, 360).

    Returns
    -------
    Color
        A new Color instance.
    """
    return Color.from_oklch(L, C, h)


def rgb(r: float, g: float, b: float) -> Color:
    """
    Convenience wrapper to create a Color from RGB values.

    Parameters
    ----------
    r, g, b : float
        RGB color values (auto-detected as [0-1] or [0-255] range).

    Returns
    -------
    Color
        A new Color instance.
    """
    return Color.from_rgb(r, g, b)


def hex(hex_str: str) -> Color:
    """
    Convenience wrapper to create a Color from a hex string.

    Parameters
    ----------
    hex_str : str
        Hex color code string (#RGB or #RRGGBB format).

    Returns
    -------
    Color
        A new Color instance.

    Notes
    -----
    This is the public ``dm.hex`` constructor and intentionally shares the
    name of the builtin ``hex``. The shadow is scoped to this module / the
    ``dartwork_mpl`` namespace; use ``builtins.hex`` if you need the
    integer-to-hex builtin alongside it.
    """
    return Color.from_hex(hex_str)


def color(value: Color | str) -> Color:
    """Parse a string (or pass through a :class:`Color`) into a :class:`Color`.

    String-parser counterpart to :func:`hex`, :func:`rgb`,
    :func:`oklch`, :func:`oklab`, and palette-name lookup. Mirrors
    :func:`dartwork_mpl.length` for unit strings.

    Examples
    --------
    >>> import dartwork_mpl as dm
    >>> dm.color("#ff0000")            # hex
    >>> dm.color("rgb(1, 0, 0)")       # functional
    >>> dm.color("oklch(0.7, 0.15, 30)")
    >>> dm.color("oc.red5")            # palette name

    Parameters
    ----------
    value : Color or str
        A :class:`Color` instance is returned as a fresh copy with the
        same OKLab coordinates. A string is dispatched through
        :meth:`Color.parse`.

    Returns
    -------
    Color
    """
    return Color(value)
