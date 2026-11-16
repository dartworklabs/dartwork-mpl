"""The save slice's types, and the one place the caller's input becomes them.

A save request is a path stem, the formats to write and the caller's savefig
``metadata``. A stem that already ends in an image suffix (``"out/chart.png"``)
is cut back to ``"out/chart"`` so the formats append cleanly instead of
writing ``chart.png.png``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal, Protocol, TypedDict, runtime_checkable

# Suffixes savefig writes; a stem ending in one of them has it cut off.
EXTENSIONS = "png pdf svg svgz eps ps jpg jpeg tif tiff webp raw rgba"
IMAGE_SUFFIXES = frozenset(f".{ext}" for ext in EXTENSIONS.split(" "))


@dataclass(frozen=True)
class PlainWriter:
    """Any format but the three below, written by savefig as it is."""

    timestamp_key: ClassVar[str | None] = None
    svg: ClassVar[bool] = False
    gzipped: ClassVar[bool] = False


@dataclass(frozen=True)
class PdfWriter:
    """PDF, which embeds the wall-clock time as ``/CreationDate``."""

    ext: ClassVar[str] = "pdf"
    timestamp_key: ClassVar[str | None] = "CreationDate"
    svg: ClassVar[bool] = False
    gzipped: ClassVar[bool] = False


@dataclass(frozen=True)
class SvgWriter:
    """SVG: embeds the time as ``<dc:date>``; ``svg.hashsalt`` seeds its ids."""

    ext: ClassVar[str] = "svg"
    timestamp_key: ClassVar[str | None] = "Date"
    svg: ClassVar[bool] = True
    gzipped: ClassVar[bool] = False


@dataclass(frozen=True)
class SvgzWriter:
    """SVG gzipped here, with a fixed header time."""

    ext: ClassVar[str] = "svgz"
    timestamp_key: ClassVar[str | None] = "Date"
    svg: ClassVar[bool] = True
    gzipped: ClassVar[bool] = True


#: How one format is written. ``timestamp_key``: the metadata key that would
#: embed the wall-clock time (None: the format embeds none); ``svg``: writes
#: SVG, whose ids ``svg.hashsalt`` seeds; ``gzipped``: SVG gzipped here.
Writer = PlainWriter | PdfWriter | SvgWriter | SvgzWriter


def parse_writer(ext: str) -> Writer:
    """The writer for an extension; :class:`PlainWriter` for any other."""
    named = (
        w for w in (PdfWriter(), SvgWriter(), SvgzWriter()) if w.ext == ext
    )
    return next(named, PlainWriter())


# matplotlib's colour forms for ``facecolor`` / ``edgecolor`` (its
# ``ColorType``), spelled here because a model file imports no matplotlib.
RGB = tuple[float, float, float]
RGBA = tuple[float, float, float, float]
Colour = str | RGB | RGBA | tuple[str | RGB | RGBA, float]


class SaveOptions(TypedDict, total=False):
    """The keywords ``save_formats`` hands on to ``Figure.savefig``.

    ``metadata`` is read here first (timestamps, SVG salt); the rest reach
    savefig unchanged. A backend keyword not named here still reaches
    savefig at run time; the checker only knows these. The artists in
    ``bbox_extra_artists`` are only forwarded, so they stay ``object``.
    """

    dpi: float | Literal["figure"]
    metadata: Mapping[str, object] | None
    facecolor: Colour | Literal["auto"]
    edgecolor: Colour | Literal["auto"]
    transparent: bool
    pad_inches: float | Literal["layout"]
    bbox_extra_artists: Sequence[object]
    format: str
    backend: str
    orientation: Literal["landscape", "portrait"]
    papertype: str
    pil_kwargs: Mapping[str, object]


@dataclass(frozen=True)
class Stem:
    """The output path without extension, and the suffix cut from it."""

    path: str
    cut: str | None = None

    @classmethod
    def parse(cls, text: str) -> Stem:
        """``text`` with a trailing image suffix removed."""
        name = text.replace("\\", "/").rsplit("/", 1)[-1]
        dot = name.rfind(".")
        suffix = name[dot:].lower() if dot > 0 else ""
        if suffix in IMAGE_SUFFIXES:
            return cls(text[: -len(suffix)], cut=suffix)
        return cls(text)

    @property
    def name(self) -> str:
        """The file name part: the SVG id salt."""
        return self.path.replace("\\", "/").rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Format:
    """One requested format: the extension as spelled and its writer."""

    ext: str
    writer: Writer

    @classmethod
    def parse(cls, value: object) -> Format:
        """``"png"`` or ``".png"``; ``TypeError`` / ``ValueError`` otherwise."""
        if not isinstance(value, str):
            raise TypeError(
                f"formats must be strings like 'png' (got {type(value).__name__})"
            )
        ext = value.lstrip(".")
        if not ext:
            raise ValueError(f"empty format {value!r}; use e.g. 'png' or 'pdf'")
        return cls(ext, parse_writer(ext.lower()))


@runtime_checkable
class Pairs(Protocol):
    """A mapping, read for its items."""

    def items(self) -> Iterable[tuple[object, object]]:
        """The key-value pairs, in order."""
        ...


@dataclass(frozen=True)
class Metadata:
    """savefig ``metadata`` items, in order (key order reaches the PDF)."""

    items: tuple[tuple[str, object], ...] = ()

    @classmethod
    def parse(cls, value: object) -> Metadata | None:
        """The caller's ``metadata`` mapping, or ``None`` when not given."""
        if value is None:
            return None
        if not isinstance(value, Pairs):
            raise TypeError(
                f"metadata must be a dict (got {type(value).__name__})"
            )
        return cls(tuple((str(k), v) for k, v in value.items()))

    def keys(self) -> frozenset[str]:
        """The keys set."""
        return frozenset(key for key, _ in self.items)

    def without_timestamp(self, key: str) -> Metadata:
        """These items with ``key`` set to ``None`` (savefig then omits it)."""
        merged = dict(self.items)
        merged[key] = None
        return Metadata(tuple(merged.items()))

    def as_dict(self) -> dict[str, object]:
        """The mapping savefig takes."""
        return dict(self.items)


@dataclass(frozen=True)
class SaveRequest:
    """Everything the plan is decided from."""

    stem: Stem
    formats: tuple[Format, ...]
    metadata: Metadata | None = None
    ambient_salt: bool = False

    @property
    def metadata_keys(self) -> frozenset[str]:
        """The keys the caller's metadata sets."""
        return self.metadata.keys() if self.metadata else frozenset()

    @classmethod
    def parse(
        cls,
        stem: str,
        formats: Iterable[object],
        metadata: object = None,
        *,
        ambient_salt: bool = False,
    ) -> SaveRequest:
        """Parse the caller's arguments once."""
        return cls(
            Stem.parse(stem),
            tuple(Format.parse(f) for f in formats),
            Metadata.parse(metadata),
            ambient_salt,
        )


@dataclass(frozen=True)
class Write:
    """One file to write: where, how, with which metadata and SVG id salt."""

    path: str
    writer: Writer
    metadata: Metadata | None
    salt: str | None = None


@dataclass(frozen=True)
class SavePlan:
    """The files a save writes, in the requested order."""

    writes: tuple[Write, ...]
