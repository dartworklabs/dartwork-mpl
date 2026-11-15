"""Save one figure to several formats: ``dm.save_formats(fig, "out/chart")``.

Saving only writes files. It does not lay out, restyle or check the figure;
call ``dm.simple_layout`` and the check slice before it.
"""

from __future__ import annotations

import os
import warnings
from collections.abc import Iterable
from typing import Unpack

from matplotlib.figure import Figure

from ..edgecase import settle
from . import apply, decide
from .edges import EDGES
from .model import SaveOptions, SaveRequest

__all__ = ["save_formats"]


def save_formats(
    fig: Figure,
    image_stem: str | os.PathLike[str],
    formats: Iterable[str] = ("png", "pdf"),
    bbox_inches: str | None = None,
    **kwargs: Unpack[SaveOptions],
) -> None:
    """Write ``fig`` to ``image_stem.<fmt>`` for each format in ``formats``.

    ``image_stem`` has no extension; a trailing image suffix
    (``"chart.png"``) is cut off with a ``UserWarning``. Missing parent
    directories are made. Other keywords go to ``savefig``. PDF and SVG
    output is byte-identical across re-saves of an unchanged figure: the
    timestamp is left out and SVG ids are salted with the file name. Pass
    ``metadata={"CreationDate": ...}`` (PDF) or ``{"Date": ...}`` (SVG) to
    keep a date, or set ``rcParams["svg.hashsalt"]`` to keep your own salt.
    An unsupported format raises ``ValueError`` before any file is written::

        dm.save_formats(fig, "out/chart", formats=("png", "pdf"), dpi=300)
    """
    request = SaveRequest.parse(
        os.fspath(image_stem),
        formats,
        kwargs.pop("metadata", None),
        ambient_salt=apply.ambient_salt(),
    )
    plan = settle(request, decide.plan(request), EDGES).plan
    apply.check_supported(fig, request.formats)
    if request.stem.cut is not None:
        warnings.warn(
            f"save_formats: image_stem {os.fspath(image_stem)!r} ends with "
            f"{request.stem.cut!r}; saving to {request.stem.path!r}.<format>. "
            "Pass the stem without an extension.",
            UserWarning,
            stacklevel=2,
        )
    apply.write(fig, plan, bbox_inches, kwargs)
