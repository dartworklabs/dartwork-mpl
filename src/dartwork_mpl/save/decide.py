"""The ordinary save: one file per format, the same bytes for the same figure.

PDF and SVG drop the wall-clock timestamp their backends embed, and SVG salts
its element ids with the file name instead of a random value, so re-saving an
unchanged figure writes an identical file. Other formats go to savefig as
given. A caller who sets the timestamp or a global salt is in ``edges.py``.
"""

from __future__ import annotations

from .model import Format, Metadata, SavePlan, SaveRequest, Write


def write_for(request: SaveRequest, fmt: Format) -> Write:
    """The reproducible write of one format at the request's stem."""
    path = f"{request.stem.path}.{fmt.ext}"
    key = fmt.writer.timestamp_key
    if key is None:
        return Write(path, fmt.writer, request.metadata)
    metadata = (request.metadata or Metadata()).without_timestamp(key)
    return Write(path, fmt.writer, metadata, salt=request.stem.name)


def plan(request: SaveRequest) -> SavePlan:
    """Every requested format, in order."""
    return SavePlan(tuple(write_for(request, fmt) for fmt in request.formats))
