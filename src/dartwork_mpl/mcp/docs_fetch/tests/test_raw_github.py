"""The Raw GitHub fetch bounds bodies, redirects, encodings and its total deadline."""

import httpx
import pytest

pytest.importorskip("fastmcp")


class _OwnedRawStream(httpx.AsyncByteStream):
    """Finite adapter-owned raw stream records actual reads and closure."""

    def __init__(self, chunks, *, delay=0, started=None):
        """Keep test chunks finite and optionally expose a cancellation checkpoint."""
        self.chunks = chunks
        self.delay = delay
        self.started = started
        self.observed = 0
        self.closed = False

    async def __aiter__(self):
        """Yield transport bytes while retaining no aggregate response body."""
        import asyncio

        for chunk in self.chunks:
            if self.started is not None:
                self.started.set()
            if self.delay:
                await asyncio.sleep(self.delay)
            self.observed += len(chunk)
            yield chunk

    async def aclose(self):
        """Record the response owner's close on every outcome."""
        self.closed = True


def _raw_transport(stream, *, headers=None, status=200):
    """Build this adapter's owned HTTPX test boundary, with close evidence."""
    import httpx

    class Stream(httpx.AsyncByteStream):
        """Adapt the finite stream to HTTPX's real streaming protocol."""

        async def __aiter__(self):
            """Delegate raw finite chunks without decoding."""
            async for chunk in stream:
                yield chunk

        async def aclose(self):
            """Keep closure visible through the genuine response context manager."""
            await stream.aclose()

    class Transport(httpx.MockTransport):
        """Own the fake remote side while exercising the genuine HTTPX client."""

        closed = False

        async def aclose(self):
            """Record owned client transport disposal."""
            self.closed = True
            await super().aclose()

    return Transport(
        lambda request: httpx.Response(status, headers=headers, stream=Stream())
    )


@pytest.mark.parametrize("length", [None, "0", "1048576"])
@pytest.mark.parametrize("extra", [0, 1])
def test_raw_fetch_counts_body_with_missing_or_false_length(length, extra):
    """Actual raw bytes decide exact acceptance or first-excess refusal and cleanup."""
    import asyncio

    from dartwork_mpl.mcp.docs_fetch import fetch_raw_github

    chunks = [b"x" * 8192] * 128 + ([b"x"] if extra else [])
    stream = _OwnedRawStream(chunks)
    transport = _raw_transport(
        stream, headers={} if length is None else {"Content-Length": length}
    )
    try:
        result = asyncio.run(
            fetch_raw_github(
                "https://raw.githubusercontent.com/arbitrary/repository/ref/doc?q=1#fragment",
                transport=transport,
            )
        )
    except ValueError as exc:
        result = exc
    if extra:
        assert isinstance(result, ValueError)
        assert "1 MiB" in str(result)
    else:
        assert result == "x" * 1048576
    assert stream.observed <= 1048576 + 8192
    assert stream.closed and transport.closed


def test_raw_fetch_invalid_utf8_replacement_has_three_byte_utf8_ceiling():
    """The byte cap permits exact replacement text without claiming a 1 MiB text cap."""
    import asyncio

    from dartwork_mpl.mcp.docs_fetch import fetch_raw_github

    stream = _OwnedRawStream([b"\xff" * 8192] * 128)
    result = asyncio.run(
        fetch_raw_github(
            "https://raw.githubusercontent.com/o/r/ref/x",
            transport=_raw_transport(stream),
        )
    )
    assert result == "\ufffd" * 1048576
    assert len(result.encode()) == 3 * 1048576
    assert stream.closed


@pytest.mark.parametrize(
    "headers",
    [
        {"Content-Encoding": "gzip"},
        {"Content-Length": "1048577"},
        {"Content-Length": "-1"},
        {"Content-Length": "bad"},
    ],
)
def test_raw_fetch_refuses_encoding_or_declared_excess_before_body(headers):
    """Encoded and explicitly oversized bodies never enter the retained buffer."""
    import asyncio

    from dartwork_mpl.mcp.docs_fetch import fetch_raw_github

    stream = _OwnedRawStream([b"not read"])
    transport = _raw_transport(stream, headers=headers)
    with pytest.raises(ValueError):
        asyncio.run(
            fetch_raw_github(
                "https://raw.githubusercontent.com/o/r/ref/x",
                transport=transport,
            )
        )
    assert stream.observed == 0
    assert stream.closed and transport.closed


@pytest.mark.parametrize(
    "location",
    [
        "http://raw.githubusercontent.com/o/r/x",
        "https://evil.example/x",
        "https://user@raw.githubusercontent.com/x",
        "https://raw.githubusercontent.com:444/x",
    ],
)
def test_raw_fetch_denied_redirect_is_not_contacted(location):
    """Every redirect target is parsed and refused before a second connection."""
    import asyncio

    import httpx

    from dartwork_mpl.mcp.docs_fetch import fetch_raw_github

    requests = []

    def remote(request):
        """Return an owned redirect and record any unwanted second connection."""
        requests.append(request.url)
        return httpx.Response(302, headers={"Location": location})

    with pytest.raises(ValueError, match="raw.githubusercontent.com"):
        asyncio.run(
            fetch_raw_github(
                "https://raw.githubusercontent.com/o/r/ref/x",
                transport=httpx.MockTransport(remote),
            )
        )
    assert len(requests) == 1


def test_raw_fetch_allowed_relative_redirect_uses_checked_url_and_identity_encoding():
    """The exact parsed URL, query and identity header reach the HTTPX sink."""
    import asyncio

    import httpx

    from dartwork_mpl.mcp.docs_fetch import fetch_raw_github

    requests = []

    def remote(request):
        """Redirect once to an arbitrary same-host repository then provide raw text."""
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                302, headers={"Location": "/another/repo/ref/doc?q=2#ignored"}
            )
        return httpx.Response(200, stream=_OwnedRawStream([b"hello\xff"]))

    result = asyncio.run(
        fetch_raw_github(
            "https://RAW.GITHUBUSERCONTENT.COM:443/o/r/ref/x#ignored",
            transport=httpx.MockTransport(remote),
        )
    )
    assert result == "hello\ufffd"
    assert len(requests) == 2
    assert all(
        request.headers["Accept-Encoding"] == "identity" for request in requests
    )
    assert (
        str(requests[-1].url)
        == "https://raw.githubusercontent.com/another/repo/ref/doc?q=2"
    )


def test_raw_fetch_redirect_loop_is_bounded_to_five_hops():
    """A same-host loop cannot reset the bounded redirect work."""
    import asyncio

    import httpx

    from dartwork_mpl.mcp.docs_fetch import fetch_raw_github

    requests = []

    def remote(request):
        """Loop through the same admitted address while counting real HTTPX requests."""
        requests.append(request.url)
        return httpx.Response(302, headers={"Location": "/loop"})

    with pytest.raises(ValueError, match="redirect limit"):
        asyncio.run(
            fetch_raw_github(
                "https://raw.githubusercontent.com/start",
                transport=httpx.MockTransport(remote),
            )
        )
    assert len(requests) == 6


def test_raw_fetch_total_deadline_and_external_cancellation_close_streams():
    """Slow trickles cannot restart the deadline; external cancellation propagates after cleanup."""
    import asyncio
    import time

    from dartwork_mpl.mcp.docs_fetch import fetch_raw_github

    stream = _OwnedRawStream([b"x"] * 100, delay=0.01)
    transport = _raw_transport(stream)
    start = time.monotonic()
    with pytest.raises(ValueError, match="total deadline"):
        asyncio.run(
            fetch_raw_github(
                "https://raw.githubusercontent.com/x",
                transport=transport,
                timeout_seconds=0.04,
            )
        )
    assert time.monotonic() - start < 0.5
    assert stream.observed < 100
    assert stream.closed and transport.closed

    async def cancelled():
        """Cancel only after response ownership has begun, then observe both closes."""
        started = asyncio.Event()
        pending = _OwnedRawStream([b"x"], delay=60, started=started)
        owned = _raw_transport(pending)
        task = asyncio.create_task(
            fetch_raw_github(
                "https://raw.githubusercontent.com/x", transport=owned
            )
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert pending.closed and owned.closed

    asyncio.run(cancelled())
