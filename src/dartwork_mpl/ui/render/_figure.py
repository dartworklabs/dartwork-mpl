"""Render the user's figure callback to bytes in one export format.

Surface (through the ``render`` package): none; the routes in this slice use
it. Tests reach ``_figure_to_bytes`` and the export-format check directly.
"""

import io
from collections.abc import Callable
from typing import Any

import matplotlib.pyplot as plt
from fastapi import HTTPException
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


def _validate_export_format(fmt: str) -> None:
    """Reject an unsupported export format with a 400 (not a 500).

    Without this, ``savefig(format=<bogus>)`` raises deep in matplotlib
    and FastAPI returns an opaque 500.
    """
    if fmt.lower() not in _SUPPORTED_EXPORT_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported export format {fmt!r}. Supported: "
                f"{', '.join(sorted(_SUPPORTED_EXPORT_FORMATS))}."
            ),
        )
