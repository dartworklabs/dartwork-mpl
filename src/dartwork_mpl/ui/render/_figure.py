"""Render the user's figure callback to bytes in one export format.

Also parses the ``{fmt}`` path segment of the export and image-save routes
into an ``ExportFormat`` or an ``UnsupportedFormat`` refusal. Surface (through
the ``render`` package): none; the routes in this slice use it. Tests reach
``_figure_to_bytes`` and ``parse_export_format`` directly.
"""

import io
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.figure import Figure

_SUPPORTED_EXPORT_FORMATS: frozenset[str] = frozenset(
    FigureCanvasBase.get_supported_filetypes()
)


def _figure_to_bytes(
    figure_fn: Callable[[Any], Figure], model: Any, fmt: str
) -> bytes:
    """Render ``figure_fn(model)`` to ``fmt`` bytes, always closing the figure.

    The figure is closed in a ``finally`` so a ``savefig`` failure (bad
    format, non-finite data, …) can't leak it. Render/export are hot
    paths (fired on every param change), so an un-closed figure per
    failure accumulates unboundedly in pyplot's global figure registry.
    """
    fig = figure_fn(model)
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format=fmt)
        return buf.getvalue()
    finally:
        plt.close(fig)


@dataclass(frozen=True)
class ExportFormat:
    """A lower-case file format matplotlib's canvas can write; built by ``parse_export_format``."""

    name: str

    def __post_init__(self) -> None:
        """Reject a name that is not a lower-case supported format (a caller defect)."""
        if self.name not in _SUPPORTED_EXPORT_FORMATS:
            raise ValueError(f"Unsupported export format {self.name!r}")


@dataclass(frozen=True)
class UnsupportedFormat:
    """The requested export format is not one matplotlib can write; the detail lists them."""

    detail: str


def parse_export_format(fmt: str) -> ExportFormat | UnsupportedFormat:
    """Parse a route's format segment case-insensitively; pure.

    Refusing here keeps a bogus format from reaching ``savefig``, which would
    raise deep in matplotlib and surface as an opaque 500.
    """
    if fmt.lower() not in _SUPPORTED_EXPORT_FORMATS:
        return UnsupportedFormat(
            f"Unsupported export format {fmt!r}. Supported: "
            f"{', '.join(sorted(_SUPPORTED_EXPORT_FORMATS))}."
        )
    return ExportFormat(fmt.lower())
