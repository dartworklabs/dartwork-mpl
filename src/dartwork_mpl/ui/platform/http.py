"""HTTP mechanism shared by the viewer's routes: bounded JSON request bodies and refusal responses.

Mechanism only: it reads one request body under the byte cap and maps any
named refusal (a value with ``detail``, ``code`` and ``status_code``) to the
detail/code JSON error contract. Surface: ``Refusal``, ``refusal_response``
and ``request_json``.
"""

from typing import Any, ClassVar, Protocol

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.requests import ClientDisconnect

from .fs import PartialSave
from .json_bounds import (
    MAX_REQUEST_BYTES,
    JsonValue,
    LimitExceeded,
    MalformedInput,
    decode_json,
)

__all__ = ["Refusal", "refusal_response", "request_json"]


class Refusal(Protocol):
    """A named refusal: its wire detail and code, and the HTTP status it maps to."""

    @property
    def detail(self) -> str:
        """The human-readable refusal text sent as ``detail``."""
        ...

    code: ClassVar[str]
    status_code: ClassVar[int]


def refusal_response(failure: Refusal) -> JSONResponse:
    """Map named refusals once, exposing stable codes and relative partial paths only."""
    body: dict[str, Any] = {"detail": failure.detail, "code": failure.code}
    if isinstance(failure, PartialSave):
        body["paths"] = list(failure.paths)
    return JSONResponse(body, status_code=failure.status_code)


async def request_json(
    request: Request,
) -> JsonValue | MalformedInput | LimitExceeded | JSONResponse:
    """Read once with a streaming byte cap and require plain UTF-8 JSON media."""
    media = request.headers.getlist("content-type")
    if len(media) != 1 or request.headers.getlist("content-encoding"):
        return JSONResponse(
            {
                "detail": "Use unencoded application/json with UTF-8.",
                "code": "unsupported_media_type",
            },
            status_code=415,
        )
    parts = [part.strip().lower() for part in media[0].split(";")]
    if (
        parts[0] != "application/json"
        or any(
            part not in {"charset=utf-8", 'charset="utf-8"'}
            for part in parts[1:]
        )
        or len(parts) > 2
    ):
        return JSONResponse(
            {
                "detail": "Use unencoded application/json with UTF-8.",
                "code": "unsupported_media_type",
            },
            status_code=415,
        )
    chunks: list[bytes] = []
    size = 0
    try:
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_REQUEST_BYTES:
                return LimitExceeded()
            chunks.append(chunk)
    except ClientDisconnect:
        return MalformedInput()
    return decode_json(b"".join(chunks), max_bytes=MAX_REQUEST_BYTES)
