"""The viewer's HTTP edge for refusals: every named refusal's status, code and body, in one match.

Refusal values carry only their own data (``detail``, and ``paths`` for a
partial save); which status and wire ``code`` answers each is transport
knowledge and lives here alone. The ``detail``/``code`` strings and statuses
are a frozen wire contract. Surface: ``ViewerRefusal``, ``RestartFailed``
and ``refusal_response``.
"""

from dataclasses import dataclass
from typing import Any, TypeAlias

from fastapi.responses import JSONResponse

from .params import InvalidRequest
from .platform.access import AccessDenied
from .platform.fs import (
    FileIOFailure,
    PartialSave,
    RootConflict,
    TargetConflict,
    UnsafeTarget,
    UnsupportedFilesystem,
)
from .platform.http import CallbackFailed, UnsupportedMediaType
from .platform.json_bounds import LimitExceeded, MalformedInput
from .render import RenderRefusal, UnsupportedFormat
from .saving import InvalidOutput
from .script import ScriptRefusal
from .state import InvalidStoredState, PresetNotFound, StateRefusal


@dataclass(frozen=True)
class RestartFailed:
    """The owned restart callback raised; the exception is not exposed."""

    detail: str = "Viewer restart failed."


ViewerRefusal: TypeAlias = (
    RenderRefusal | ScriptRefusal | StateRefusal | AccessDenied | RestartFailed
)


def _status_and_code(failure: ViewerRefusal) -> tuple[int, str]:
    """The HTTP status and wire ``code`` that answer ``failure``."""
    match failure:
        case MalformedInput():
            return 400, "invalid_json"
        case UnsupportedMediaType():
            return 415, "unsupported_media_type"
        case LimitExceeded():
            return 413, "input_too_large"
        case InvalidRequest():
            return 422, "invalid_request"
        case UnsupportedFormat():
            return 400, "invalid_request"
        case InvalidOutput():
            return 400, "invalid_output_path"
        case UnsafeTarget():
            return 400, "unsafe_output_target"
        case TargetConflict():
            return 409, "output_conflict"
        case RootConflict():
            return 409, "root_changed"
        case UnsupportedFilesystem():
            return 501, "unsupported_filesystem_capability"
        case FileIOFailure():
            return 503, "filesystem_unavailable"
        case PartialSave():
            return 503, "partial_save"
        case InvalidStoredState():
            return 409, "invalid_stored_state"
        case PresetNotFound():
            return 404, "preset_not_found"
        case CallbackFailed():
            return 500, "callback_failed"
        case AccessDenied():
            return 403, "local_access_denied"
        case RestartFailed():
            return 500, "restart_failed"


def refusal_response(failure: ViewerRefusal) -> JSONResponse:
    """Answer ``failure`` with its status and ``{"detail", "code"}`` body.

    A partial save adds ``paths``: the root-qualified relative paths left
    behind, never absolute ones.
    """
    status, code = _status_and_code(failure)
    body: dict[str, Any] = {"detail": failure.detail, "code": code}
    if isinstance(failure, PartialSave):
        body["paths"] = list(failure.paths)
    return JSONResponse(body, status_code=status)
