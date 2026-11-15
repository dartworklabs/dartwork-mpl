"""Write a decided plan with matplotlib's savefig."""

from __future__ import annotations

import contextlib
import gzip
import io
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from .model import Format, SavePlan, Write


def ambient_salt() -> bool:
    """Whether ``rcParams["svg.hashsalt"]`` is already set."""
    return mpl.rcParams["svg.hashsalt"] is not None


def check_supported(fig: Figure, formats: tuple[Format, ...]) -> None:
    """Raise before any file is written if a format has no writer."""
    supported = fig.canvas.get_supported_filetypes()
    for fmt in formats:
        ext = fmt.ext.lower()
        if ext not in supported:
            names = ", ".join(sorted(supported))
            raise ValueError(f"format {ext!r} is not supported ({names})")


def write(
    fig: Figure, plan: SavePlan, bbox_inches: str | None, kwargs: dict[str, Any]
) -> None:
    """Make the parent directory, then write every file in order."""
    for item in plan.writes:
        Path(item.path).parent.mkdir(parents=True, exist_ok=True)
        save_one(fig, item, bbox_inches, kwargs)


def save_one(
    fig: Figure, item: Write, bbox_inches: str | None, kwargs: dict[str, Any]
) -> None:
    """One file; SVGZ is gzipped here with a fixed header time."""
    options: dict[str, Any] = dict(kwargs)
    if item.metadata is not None:
        options["metadata"] = item.metadata.as_dict()
    # matplotlib's stubs leave the ``PathLike`` in savefig's and rc_context's
    # path parameters unparameterised, so both read as partially unknown.
    salted = (
        plt.rc_context({"svg.hashsalt": item.salt})  # pyright: ignore[reportUnknownMemberType]
        if item.salt is not None and item.writer.svg
        else contextlib.nullcontext()
    )
    with salted:
        if not item.writer.gzipped:
            fig.savefig(item.path, bbox_inches=bbox_inches, **options)  # pyright: ignore[reportUnknownMemberType]
            return
        buffer = io.BytesIO()
        fig.savefig(buffer, format="svg", bbox_inches=bbox_inches, **options)  # pyright: ignore[reportUnknownMemberType]
    with (
        open(item.path, "wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as packed,
    ):
        packed.write(buffer.getvalue())
