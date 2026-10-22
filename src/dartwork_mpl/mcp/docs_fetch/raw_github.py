"""Bounded fetch of one GitHub Raw document (the ``fetch_github_document`` tool).

Only HTTPS ``raw.githubusercontent.com`` URLs without credentials or a
nondefault port are contacted; redirects are re-checked, one total deadline
covers the transfer, and bodies are capped at 1 MiB of identity-encoded bytes.
Every refusal or transport failure raises ``ValueError`` with the message the
tool returns to the client.
"""

import asyncio
import time

import httpx

_FETCH_BYTES = 1024 * 1024
_FETCH_SECONDS = 10.0
_FETCH_REDIRECTS = 5


def _raw_github_url(value: str | httpx.URL) -> httpx.URL:
    """Parse the exact HTTPS Raw GitHub URL sent to HTTPX, or refuse it.

    Repository/ref/path/query remain unrestricted. Fragments are removed;
    credentials, noncanonical hosts and nondefault ports never reach a client.
    """
    try:
        url = httpx.URL(value)
    except (httpx.InvalidURL, TypeError) as exc:
        raise ValueError(
            "Expected an HTTPS raw.githubusercontent.com URL."
        ) from exc
    if (
        url.scheme != "https"
        or url.raw_host != b"raw.githubusercontent.com"
        or url.port not in (None, 443)
        or url.userinfo
    ):
        raise ValueError(
            "Expected an HTTPS raw.githubusercontent.com URL without credentials or a nondefault port."
        )
    return url.copy_with(fragment=None)


async def fetch_raw_github(
    value: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout_seconds: float = _FETCH_SECONDS,
) -> str:
    """Fetch bounded identity Raw text through one owned async HTTPX client.

    A total deadline covers redirects and all body reads. Each redirect is
    validated before its request; every response/client closes on refusal,
    timeout and external cancellation. Adapter-visible reads exceed the 1 MiB
    body cap by at most one 8 KiB chunk; replacement text is at most 3 MiB UTF-8.
    """
    url = _raw_github_url(value)
    deadline = time.monotonic() + timeout_seconds

    async def transfer() -> str:
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
                    raise asyncio.TimeoutError
                async with client.stream(
                    "GET", current, timeout=remaining
                ) as response:
                    if response.is_redirect:
                        if hops == _FETCH_REDIRECTS:
                            raise ValueError(
                                "Raw document redirect limit exceeded."
                            )
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError(
                                "Raw document redirect has no destination."
                            )
                        try:
                            target = current.join(location)
                        except httpx.InvalidURL as exc:
                            raise ValueError(
                                "Expected an HTTPS raw.githubusercontent.com redirect URL."
                            ) from exc
                        current = _raw_github_url(target)
                        continue
                    response.raise_for_status()
                    encoding = (
                        response.headers.get("content-encoding", "identity")
                        .strip()
                        .lower()
                    )
                    if encoding != "identity":
                        raise ValueError(
                            "Raw document must use identity content encoding."
                        )
                    length = response.headers.get("content-length")
                    if length is not None:
                        try:
                            declared = int(length)
                        except ValueError as exc:
                            raise ValueError(
                                "Raw document has an invalid content length."
                            ) from exc
                        if declared < 0 or declared > _FETCH_BYTES:
                            raise ValueError(
                                "Raw document exceeds the 1 MiB byte limit."
                            )
                    body = bytearray()
                    async for chunk in response.aiter_raw(chunk_size=8 * 1024):
                        if len(body) + len(chunk) > _FETCH_BYTES:
                            raise ValueError(
                                "Raw document exceeds the 1 MiB byte limit."
                            )
                        body.extend(chunk)
                    return body.decode("utf-8", "replace")
        raise ValueError("Raw document redirect limit exceeded.")

    try:
        return await asyncio.wait_for(transfer(), timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise ValueError(
            "Failed to fetch Raw document: total deadline exceeded."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise ValueError(
            f"Failed to fetch Raw document: HTTP {exc.response.status_code}."
        ) from exc
    except httpx.HTTPError as exc:
        raise ValueError(
            f"Failed to fetch Raw document: {type(exc).__name__}."
        ) from exc
