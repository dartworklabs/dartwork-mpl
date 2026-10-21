"""Output names for server saves: a bounded, portable relative path parsed once.

Only ``parse_output`` builds a ``RelativeOutput``, so every path that reaches
the filesystem has been checked. Surface (through the ``saving`` package):
``InvalidOutput``, ``RelativeOutput`` and ``parse_output``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

MAX_OUTPUT_BYTES = 1024


@dataclass(frozen=True)
class InvalidOutput:
    """An output name cannot denote a safe portable relative path."""

    detail: str = "Filename must be a bounded safe relative path."
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "invalid_output_path"


def _output_parts(filename: str) -> tuple[str, ...] | None:
    """Recognize portable relative paths without filesystem normalization or I/O."""
    try:
        if len(filename.encode("utf-8")) > MAX_OUTPUT_BYTES:
            return None
        parts = tuple(filename.split("/"))
        if not parts or any(
            not part.strip()
            or part in {".", ".."}
            or len(part.encode("utf-8")) > 255
            for part in parts
        ):
            return None
    except UnicodeEncodeError:
        return None
    if "\\" in filename or ":" in filename or "\x00" in filename:
        return None
    return parts


@dataclass(frozen=True)
class RelativeOutput:
    """A parsed portable relative filename; construction belongs to parse_output."""

    parts: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject illegal trusted construction in addition to the owner inventory."""
        if not self.parts or _output_parts("/".join(self.parts)) != self.parts:
            raise ValueError("Invalid relative output")

    @property
    def filename(self) -> str:
        """Return the accepted relative spelling for receipts and staging names."""
        return "/".join(self.parts)


def parse_output(filename: str) -> RelativeOutput | InvalidOutput:
    """Parse an output name once before directory-handle planning and effects."""
    parts = _output_parts(filename)
    return RelativeOutput(parts) if parts is not None else InvalidOutput()
