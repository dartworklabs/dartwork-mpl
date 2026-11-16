"""Write a decided plan with matplotlib's savefig."""

from __future__ import annotations

import contextlib
import gzip
import io
import logging
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from .model import Format, SaveOptions, SavePlan, Write

LOG = logging.getLogger("dartwork_mpl.save")


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
    fig: Figure,
    plan: SavePlan,
    bbox_inches: str | None,
    options: SaveOptions,
    asked: frozenset[str],
) -> None:
    """Make the parent directory, then write every file in order; ``asked``:
    the metadata keys the caller set."""
    for item in plan.writes:
        Path(item.path).parent.mkdir(parents=True, exist_ok=True)
        save_one(fig, item, bbox_inches, options)
        _say(item, asked)


def _say(item: Write, asked: frozenset[str]) -> None:
    """Say what the file leaves out so that it is the same every time."""
    key = item.writer.timestamp_key
    metadata = item.metadata.as_dict() if item.metadata is not None else {}
    if (
        key is not None
        and key not in asked
        and key in metadata
        and metadata[key] is None
    ):
        LOG.info(
            "left the date out of %s so that saving the same figure again "
            'writes the same bytes; pass metadata={"%s": ...} to keep one',
            item.path,
            key,
        )
    if item.salt is not None and item.writer.svg:
        LOG.info(
            "salted the SVG ids of %s with its file name instead of a random "
            'value, for the same reason; set rcParams["svg.hashsalt"] to '
            "choose your own",
            item.path,
        )


def save_one(
    fig: Figure, item: Write, bbox_inches: str | None, options: SaveOptions
) -> None:
    """One file; SVGZ is gzipped here with a fixed header time."""
    options = options.copy()
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
        options["format"] = "svg"
        fig.savefig(buffer, bbox_inches=bbox_inches, **options)  # pyright: ignore[reportUnknownMemberType]
    with (
        open(item.path, "wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as packed,
    ):
        packed.write(buffer.getvalue())
