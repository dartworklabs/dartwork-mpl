"""The "drawn last" host rule the legend code still imports from here.

The bar-label code moved to :mod:`dartwork_mpl.labels`; the rule itself is
the platform's (:func:`dartwork_mpl._figure_geometry.host_axes`). This file
goes when the legend slice repoints its import.
"""

from __future__ import annotations

from .._figure_geometry import host_axes

__all__ = ["host_axes"]
