"""HTTP mechanism shared by the viewer's routes: bounded JSON request bodies.

Mechanism only: it reads one request body under the byte cap and returns
the decoded JSON or a named refusal. It assigns no HTTP status; the entry
point's edge maps every refusal to its status and code. Surface:
``UnsupportedMediaType``, ``CallbackFailed`` and ``request_json``.
"""

from dataclasses import dataclass

from fastapi import Request
from starlette.requests import ClientDisconnect

from .json_bounds import (
    MAX_REQUEST_BYTES,
    JsonValue,
    LimitExceeded,
    MalformedInput,
    decode_json,
)

__all__ = ["CallbackFailed", "UnsupportedMediaType", "request_json"]


@dataclass(frozen=True)
class UnsupportedMediaType:
    """The body is not one unencoded ``application/json`` (UTF-8) entity."""

    detail: str = "Use unencoded application/json with UTF-8."


@dataclass(frozen=True)
class CallbackFailed:
    """A trusted callback (figure function, export or script generation) raised; ``detail`` says which.

    The exception itself is never exposed.
    """

    detail: str


async def request_json(
    request: Request,
) -> JsonValue | UnsupportedMediaType | MalformedInput | LimitExceeded:
    """Read once with a streaming byte cap and require plain UTF-8 JSON media.

    Refusals: ``UnsupportedMediaType`` for a missing, repeated, non-JSON or
    encoded content type; ``LimitExceeded`` past ``MAX_REQUEST_BYTES``;
    ``MalformedInput`` for a client disconnect or bytes that are not one
    bounded JSON value.
    """
    media = request.headers.getlist("content-type")
    if len(media) != 1 or request.headers.getlist("content-encoding"):
        return UnsupportedMediaType()
    parts = [part.strip().lower() for part in media[0].split(";")]
    if (
        parts[0] != "application/json"
        or any(
            part not in {"charset=utf-8", 'charset="utf-8"'}
            for part in parts[1:]
        )
        or len(parts) > 2
    ):
        return UnsupportedMediaType()
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
