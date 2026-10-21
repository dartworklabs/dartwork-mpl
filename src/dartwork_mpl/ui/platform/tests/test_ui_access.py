"""Loopback binds and the per-request Host/Origin/Referer checks against a grant table."""

import pytest

from dartwork_mpl.ui.platform import access as boundary
from dartwork_mpl.ui.platform.access import (
    AccessDenied,
    LocalAccess,
    StartupRejected,
    authorize_request,
    normalize_bind,
)

# A grant table of the shape the viewer declares: one effect, one read and
# the explicit marker for unmatched reads.
GRANTS: dict[tuple[str, str], boundary.Grant] = {
    ("POST", "/api/render"): "local-effect",
    ("GET", "/api/health"): "local-read",
    ("GET", "<unmatched>"): "local-read",
    ("HEAD", "<unmatched>"): "local-read",
}


def headers(host=b"localhost:8501", **sources):
    """Build raw ASGI headers without framework normalization."""
    return [(b"host", host)] + [
        (name.encode("ascii"), value.encode("ascii"))
        for name, value in sources.items()
    ]


@pytest.mark.parametrize(
    "host",
    [
        "0.0.0.0",
        "::",
        "example.org",
        "192.0.2.1",
        "127.0.0.1.evil",
        "",
        " localhost",
        "[::1]",
        "::1%lo0",
    ],
)
def test_public_bind_rejected_before_effects(host):
    """Only approved literal loopback binds can grant local effects."""
    result = boundary.normalize_bind(host)
    assert isinstance(result, boundary.StartupRejected)
    assert "loopback" in result.detail


@pytest.mark.parametrize(
    "host, expected",
    [
        ("localhost", "127.0.0.1"),
        ("LOCALHOST", "127.0.0.1"),
        ("127.23.45.67", "127.23.45.67"),
        ("::1", "::1"),
        ("0:0:0:0:0:0:0:1", "::1"),
    ],
)
def test_loopback_bind_is_normalized_without_dns(host, expected):
    """Localhost mapping and every approved loopback literal are deterministic."""
    assert boundary.normalize_bind(host) == expected


@pytest.mark.parametrize(
    "host",
    [
        b"evil.example:8501",
        b"localhost.evil",
        b"user@localhost:8501",
        b"localhost/path",
        b"localhost?x",
        b"localhost#x",
        b"localhost:",
        b"localhost:abc",
        b"localhost:65536",
        b"localhost:0",
        b"::1",
        b"[::1]junk",
        b" localhost",
        b"localhost\t",
        b"localhost:01",
        b"localhost,localhost",
    ],
)
def test_effect_denied_for_bad_authority(host):
    """Host must be a complete unambiguous local HTTP authority."""
    result = boundary.authorize_request(
        "POST", "/api/render", headers(host), "127.0.0.1", GRANTS
    )
    assert isinstance(result, boundary.AccessDenied)


def test_every_source_is_checked_and_native_clients_are_allowed():
    """A valid Origin cannot hide a foreign Referer; bind-port differences work."""
    for supplied in [
        [],
        [*headers(), (b"host", b"localhost:8501")],
        headers(origin="http://localhost:8501", referer="http://evil.example/"),
        headers(origin="http://localhost:8501/path"),
        headers(origin="http://localhost:8501?"),
        headers(origin="https://localhost:8501"),
        headers(referer="http://user@localhost:8501/"),
        headers(referer="http://localhost:8501/#x"),
        [
            *headers(),
            (b"origin", b"http://localhost:8501"),
            (b"origin", b"http://localhost:8501"),
        ],
    ]:
        assert isinstance(
            boundary.authorize_request(
                "POST", "/api/render", supplied, "127.0.0.1", GRANTS
            ),
            boundary.AccessDenied,
        )
    for supplied in [
        headers(),
        headers(
            origin="http://localhost:8501", referer="http://localhost:8501/a?b"
        ),
        headers(b"[::1]:8502", origin="http://[::1]:8502"),
        headers(b"127.23.45.67:8765"),
    ]:
        assert isinstance(
            boundary.authorize_request(
                "POST", "/api/render", supplied, "127.23.45.67", GRANTS
            ),
            boundary.LocalAccess,
        )
    assert isinstance(
        boundary.authorize_request(
            "POST", "/not-declared", headers(), "127.0.0.1", GRANTS
        ),
        boundary.AccessDenied,
    )
    assert isinstance(
        boundary.authorize_request(
            "GET", "/api/health", headers(origin="foreign"), "127.0.0.1", GRANTS
        ),
        boundary.LocalAccess,
    )


def test_unmatched_read_classification_preserves_host_checks_and_denies_effects():
    """An explicit missing-read marker preserves 404 handling without new grants."""
    for method in ("GET", "HEAD"):
        assert isinstance(
            boundary.authorize_request(
                method, "<unmatched>", headers(), "127.0.0.1", GRANTS
            ),
            boundary.LocalAccess,
        )
        assert isinstance(
            boundary.authorize_request(
                method,
                "<unmatched>",
                headers(b"evil.example"),
                "127.0.0.1",
                GRANTS,
            ),
            boundary.AccessDenied,
        )
    for method, route in [("POST", "<unmatched>"), ("GET", "/unclassified")]:
        assert isinstance(
            boundary.authorize_request(
                method, route, headers(), "127.0.0.1", GRANTS
            ),
            boundary.AccessDenied,
        )


class TestLocalRequestPolicy:
    """The single policy denies foreign/missing authorities and checks each source."""

    @pytest.mark.parametrize("source", ["origin", "referer"])
    def test_foreign_source_denied(self, source: str) -> None:
        """Each browser source is independently checked before an effect."""
        result = authorize_request(
            "POST",
            "/api/render",
            [
                (b"host", b"localhost:8501"),
                (source.encode(), b"http://evil.example"),
            ],
            "127.0.0.1",
            GRANTS,
        )
        assert isinstance(result, AccessDenied)

    def test_native_and_same_authority_allowed(self) -> None:
        """Native clients omit sources; local browser clients use the request authority."""
        for source in (
            [],
            [
                (b"origin", b"http://localhost:9999"),
                (b"referer", b"http://localhost:9999/page"),
            ],
        ):
            result = authorize_request(
                "POST",
                "/api/render",
                [(b"host", b"localhost:9999"), *source],
                "127.0.0.1",
                GRANTS,
            )
            assert isinstance(result, LocalAccess)

    @pytest.mark.parametrize(
        "host", [None, b"evil.example", b"localhost:invalid", b"user@localhost"]
    )
    def test_bad_host_denied(self, host: bytes | None) -> None:
        """All reads and effects require one complete valid local Host authority."""
        headers = [] if host is None else [(b"host", host)]
        assert isinstance(
            authorize_request(
                "GET", "/api/health", headers, "127.0.0.1", GRANTS
            ),
            AccessDenied,
        )

    @pytest.mark.parametrize(
        "host", ["0.0.0.0", "::", "192.0.2.1", "example.test"]
    )
    def test_public_bind_rejected(self, host: str) -> None:
        """Unapproved bind addresses cannot issue a local-effect grant."""
        assert isinstance(normalize_bind(host), StartupRejected)
