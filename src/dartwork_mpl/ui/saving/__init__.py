"""Server saves: parse an output name, pin every destination, then write create-only.

A mechanism slice with no routes of its own: render and script use it for
``/api/save-server/*``. Surface: the output language (``RelativeOutput``,
``parse_output``, ``InvalidOutput``), the save request (``SaveRequest``,
``parse_save_request``, ``SaveInputFailure``, ``timestamp_slug``) and the
two-phase save (``prepare_save``, ``PreparedSave``, ``commit_save``,
``SaveReceipt``).
"""

from ._output import InvalidOutput, RelativeOutput, parse_output
from ._plan import PreparedSave, SaveReceipt, commit_save, prepare_save
from ._request import (
    SaveInputFailure,
    SaveRequest,
    parse_save_request,
    timestamp_slug,
)

__all__ = [
    "InvalidOutput",
    "PreparedSave",
    "RelativeOutput",
    "SaveInputFailure",
    "SaveReceipt",
    "SaveRequest",
    "commit_save",
    "parse_output",
    "parse_save_request",
    "prepare_save",
    "timestamp_slug",
]
