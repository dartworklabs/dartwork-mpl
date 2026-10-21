"""Local-only access for the viewer: loopback binds and per-request Host/Origin checks.

Mechanism only: the grant table (which route is a read and which an effect)
comes from the caller. Host and browser-source checks constrain that grant;
they do not identify a person. Surface: ``Grant``, ``LocalAccess``,
``AccessDenied``, ``StartupRejected``, ``normalize_bind`` and
``authorize_request``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from ipaddress import ip_address
from typing import ClassVar, Literal, TypeAlias
from urllib.parse import urlsplit

__all__ = [
    "AccessDenied",
    "Grant",
    "LocalAccess",
    "StartupRejected",
    "authorize_request",
    "normalize_bind",
]

Grant: TypeAlias = Literal["local-read", "local-effect"]


@dataclass(frozen=True)
class AccessDenied:
    """The request has no local grant or contains an invalid authority."""

    detail: str = "Request is outside the local viewer policy."
    status_code: ClassVar[int] = 403
    code: ClassVar[str] = "local_access_denied"


@dataclass(frozen=True)
class StartupRejected:
    """The configured bind cannot grant approved loopback-only operation."""

    detail: str = "Use localhost or a loopback IP literal for the viewer host."
    code: ClassVar[str] = "invalid_bind"


@dataclass(frozen=True)
class LocalAccess:
    """A named route is admitted by the startup-selected local-only grant."""

    scope: Grant


def normalize_bind(host: str) -> str | StartupRejected:
    """Normalize approved literal loopback binds without consulting DNS."""
    if host.lower() == "localhost":
        return "127.0.0.1"
    if "%" in host:
        return StartupRejected()
    try:
        address = ip_address(host)
    except ValueError:
        return StartupRejected()
    return str(address) if address.is_loopback else StartupRejected()


def _authority(value: str) -> tuple[str, str | None] | None:
    """Recognize the entire ASCII HTTP authority, including a valid optional port."""
    match = re.fullmatch(
        r"(\[[0-9A-Fa-f:]+\]|[A-Za-z0-9.]+)(?::([1-9][0-9]{0,4}))?", value
    )
    if match is None:
        return None
    name, port = match.groups()
    if port is not None and int(port) > 65535:
        return None
    if name.startswith("["):
        try:
            address = ip_address(name[1:-1])
        except ValueError:
            return None
        if address.version != 6:
            return None
        name = str(address)
    else:
        name = name.lower()
    return name, port


def _source_matches(
    value: str, authority: tuple[str, str | None], *, origin: bool
) -> bool:
    """Match a complete HTTP source URL without browser/parser ambiguity."""
    if (
        any(ord(char) <= 32 or ord(char) >= 127 for char in value)
        or "\\" in value
        or "#" in value
    ):
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    if parsed.scheme != "http" or _authority(parsed.netloc) != authority:
        return False
    return not origin or (not parsed.path and "?" not in value)


def authorize_request(
    method: str,
    route_template: str | None,
    raw_headers: list[tuple[bytes, bytes]],
    bind_host: str,
    grants: Mapping[tuple[str, str], Grant],
) -> LocalAccess | AccessDenied:
    """Admit only classified routes with a valid local Host and each effect source.

    ``grants`` maps (method, route template) to the grant the entry point
    declared for it; a route missing from it is denied.
    """
    scope = grants.get((method.upper(), route_template or ""))
    normalized = normalize_bind(bind_host)
    if scope is None or isinstance(normalized, StartupRejected):
        return AccessDenied()
    selected: dict[bytes, list[str]] = {
        b"host": [],
        b"origin": [],
        b"referer": [],
    }
    for name, value in raw_headers:
        if name.lower() in selected:
            try:
                selected[name.lower()].append(value.decode("ascii"))
            except UnicodeDecodeError:
                return AccessDenied()
    if len(selected[b"host"]) != 1:
        return AccessDenied()
    authority = _authority(selected[b"host"][0])
    if authority is None or authority[0] not in {
        "localhost",
        "127.0.0.1",
        "::1",
        normalized,
    }:
        return AccessDenied()
    if scope == "local-effect":
        for name in (b"origin", b"referer"):
            values = selected[name]
            if len(values) > 1 or (
                values
                and not _source_matches(
                    values[0], authority, origin=name == b"origin"
                )
            ):
                return AccessDenied()
    return LocalAccess(scope)
