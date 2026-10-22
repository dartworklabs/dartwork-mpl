"""Bounded fetch of one GitHub Raw document (the ``fetch_github_document`` tool).

Only HTTPS ``raw.githubusercontent.com`` URLs without credentials or a
nondefault port are contacted; redirects are re-checked, one total deadline
covers the transfer, and bodies are capped at 1 MiB of identity-encoded bytes.
``fetch`` returns ``Fetched`` or ``Refused`` (a refused URL, redirect,
encoding, size, deadline or HTTP/transport failure, with the message the tool
returns to the client). ``fetch_raw_github`` is the tool's edge: the text, or
that message as ``ValueError``.
"""

import asyncio
import time
from dataclasses import dataclass

import httpx

_FETCH_BYTES = 1024 * 1024
_FETCH_SECONDS = 10.0
_FETCH_REDIRECTS = 5


@dataclass(frozen=True)
class Fetched:
    """The document body decoded as UTF-8 with replacement."""

    text: str


@dataclass(frozen=True)
class Refused:
    """The fetch was refused or failed; ``message`` is the tool's error text.

    One variant serves every reason: callers only pass the message on.
    """

    message: str


_DEADLINE = Refused("Failed to fetch Raw document: total deadline exceeded.")
_TOO_LARGE = Refused("Raw document exceeds the 1 MiB byte limit.")
_REDIRECT_LIMIT = Refused("Raw document redirect limit exceeded.")


def _raw_github_url(value: str | httpx.URL) -> httpx.URL | Refused:
    """Parse the exact HTTPS Raw GitHub URL sent to HTTPX, or refuse it.

    Repository/ref/path/query remain unrestricted. Fragments are removed;
    credentials, noncanonical hosts and nondefault ports never reach a client.
    """
    try:
        url = httpx.URL(value)
    except (httpx.InvalidURL, TypeError):
        return Refused("Expected an HTTPS raw.githubusercontent.com URL.")
    if (
        url.scheme != "https"
        or url.raw_host != b"raw.githubusercontent.com"
        or url.port not in (None, 443)
        or url.userinfo
    ):
        return Refused(
            "Expected an HTTPS raw.githubusercontent.com URL without credentials or a nondefault port."
        )
    return url.copy_with(fragment=None)


async def fetch(
    value: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout_seconds: float = _FETCH_SECONDS,
) -> Fetched | Refused:
    """Fetch bounded identity Raw text through one owned async HTTPX client.

    A total deadline covers redirects and all body reads. Each redirect is
    validated before its request; every response/client closes on refusal,
    timeout and external cancellation (``CancelledError`` propagates).
    Adapter-visible reads exceed the 1 MiB body cap by at most one 8 KiB
    chunk; replacement text is at most 3 MiB UTF-8.
    """
    url = _raw_github_url(value)
    if isinstance(url, Refused):
        return url
    deadline = time.monotonic() + timeout_seconds

    async def transfer() -> Fetched | Refused:
        """Read raw chunks without decompression, following only checked redirects."""
        current = url
        async with httpx.AsyncClient(
            transport=transport,
            follow_redirects=False,
            headers={"Accept-Encoding": "identity"},
        ) as client:
            for hops in range(_FETCH_REDIRECTS + 1):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return _DEADLINE
                async with client.stream(
                    "GET", current, timeout=remaining
                ) as response:
                    if response.is_redirect:
                        if hops == _FETCH_REDIRECTS:
                            return _REDIRECT_LIMIT
                        location = response.headers.get("location")
                        if not location:
                            return Refused(
                                "Raw document redirect has no destination."
                            )
                        try:
                            target = current.join(location)
                        except httpx.InvalidURL:
                            return Refused(
                                "Expected an HTTPS raw.githubusercontent.com redirect URL."
                            )
                        checked = _raw_github_url(target)
                        if isinstance(checked, Refused):
                            return checked
                        current = checked
                        continue
                    if not response.is_success:
                        return Refused(
                            "Failed to fetch Raw document: "
                            f"HTTP {response.status_code}."
                        )
                    encoding = (
                        response.headers.get("content-encoding", "identity")
                        .strip()
                        .lower()
                    )
                    if encoding != "identity":
                        return Refused(
                            "Raw document must use identity content encoding."
                        )
                    length = response.headers.get("content-length")
                    if length is not None:
                        try:
                            declared = int(length)
                        except ValueError:
                            return Refused(
                                "Raw document has an invalid content length."
                            )
                        if declared < 0 or declared > _FETCH_BYTES:
                            return _TOO_LARGE
                    body = bytearray()
                    async for chunk in response.aiter_raw(chunk_size=8 * 1024):
                        if len(body) + len(chunk) > _FETCH_BYTES:
                            return _TOO_LARGE
                        body.extend(chunk)
                    return Fetched(body.decode("utf-8", "replace"))
        return _REDIRECT_LIMIT

    try:
        return await asyncio.wait_for(transfer(), timeout_seconds)
    except asyncio.TimeoutError:
        return _DEADLINE
    except httpx.HTTPError as exc:
        # Transport failures (connect, read, protocol) name only their type.
        return Refused(f"Failed to fetch Raw document: {type(exc).__name__}.")


async def fetch_raw_github(
    value: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout_seconds: float = _FETCH_SECONDS,
) -> str:
    """The tool's contract over ``fetch``: the text, or ``ValueError(message)`` when refused."""
    match await fetch(
        value, transport=transport, timeout_seconds=timeout_seconds
    ):
        case Fetched(text):
            return text
        case Refused(message):
            raise ValueError(message)
