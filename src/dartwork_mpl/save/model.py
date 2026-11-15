"""The save slice's types, and the one place the caller's input becomes them.

A save request is a path stem, the formats to write and the caller's savefig
``metadata``. A stem that already ends in an image suffix (``"out/chart.png"``)
is cut back to ``"out/chart"`` so the formats append cleanly instead of
writing ``chart.png.png``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import cast

# Suffixes savefig writes; a stem ending in one of them has it cut off.
EXTENSIONS = "png pdf svg svgz eps ps jpg jpeg tif tiff webp raw rgba"
IMAGE_SUFFIXES = frozenset(f".{ext}" for ext in EXTENSIONS.split(" "))


class Writer(Enum):
    """How one format is written."""

    PLAIN = "plain"
    PDF = "pdf"
    SVG = "svg"
    SVGZ = "svgz"

    @property
    def timestamp_key(self) -> str | None:
        """The metadata key that would embed the wall-clock time."""
        return TIMESTAMP_KEYS.get(self)


# PDF writes ``/CreationDate`` and SVG ``<dc:date>`` unless the key is None.
TIMESTAMP_KEYS = {
    Writer.PDF: "CreationDate",
    Writer.SVG: "Date",
    Writer.SVGZ: "Date",
}


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
        try:
            writer = Writer(ext.lower())
        except ValueError:
            writer = Writer.PLAIN
        return cls(ext, writer)


@dataclass(frozen=True)
class Metadata:
    """savefig ``metadata`` items, in order (key order reaches the PDF)."""

    items: tuple[tuple[str, object], ...] = ()

    @classmethod
    def parse(cls, value: object) -> Metadata | None:
        """The caller's ``metadata`` mapping, or ``None`` when not given."""
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise TypeError(
                f"metadata must be a dict (got {type(value).__name__})"
            )
        items = cast(Mapping[object, object], value).items()
        return cls(tuple((str(k), v) for k, v in items))

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
