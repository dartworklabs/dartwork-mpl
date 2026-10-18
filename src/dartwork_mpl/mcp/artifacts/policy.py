"""Pure, bounded artifact parsing and immutable publication values.

This module knows no filesystem, execution framework or other feature. Persisted
bytes are parsed here before the shell uses their identities, sizes or expiry.
"""

import hashlib
import json
import keyword
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, TypeAlias

MAX_SOURCE_BYTES = 512 * 1024
MAX_MANIFEST_BYTES = 512 * 1024
MAX_BUNDLE_BYTES = 32 * 1024 * 1024
RETENTION = timedelta(days=7)
_ID = re.compile(r"[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")


@dataclass(frozen=True)
class InvalidRequest:
    """A request field cannot be parsed; diagnostics contain no submitted data."""

    field: str
    message: str


@dataclass(frozen=True)
class ConfigurationError:
    """The configured root cannot safely authorize artifact storage."""

    message: str = "Artifact storage configuration is invalid."


@dataclass(frozen=True)
class NotFound:
    """There is no published bundle for the requested identity."""


@dataclass(frozen=True)
class Expired:
    """A bundle reached its immutable publication expiry."""

    expires_at: datetime


@dataclass(frozen=True)
class CorruptArtifact:
    """Stored metadata or content failed verification, without path disclosure."""

    message: str = "Artifact contents are invalid."


@dataclass(frozen=True)
class ArtifactTooLarge:
    """Publication or reading exceeded the combined on-disk byte allowance."""

    size_bytes: int
    limit_bytes: int = MAX_BUNDLE_BYTES


@dataclass(frozen=True)
class PublicationError:
    """The store could not commit a complete bundle; no identity is published."""

    message: str = "Artifact publication failed."


StoreFailure: TypeAlias = (
    NotFound | Expired | CorruptArtifact | ArtifactTooLarge | PublicationError
)


@dataclass(frozen=True)
class ArtifactId:
    """A complete lowercase UUID4 hex identity, safe as one fixed path segment."""

    value: str

    def __post_init__(self) -> None:
        """Reject caller-built identities that bypass the boundary parser."""
        if not isinstance(self.value, str) or not _ID.fullmatch(self.value):
            raise ValueError("Expected a full lowercase UUID4 hex identity")


class ArtifactMember(str, Enum):
    """The only five names permitted in a ready bundle, in delivery order."""

    PNG = "plot.png"
    PDF = "plot.pdf"
    SOURCE = "source.py"
    REPORT = "report.json"
    MANIFEST = "manifest.json"

    @property
    def mime_type(self) -> str:
        """Return the static transport MIME associated with this literal member."""
        return {
            self.PNG: "image/png",
            self.PDF: "application/pdf",
            self.SOURCE: "text/x-python",
            self.REPORT: "application/json",
            self.MANIFEST: "application/json",
        }[self]


DATA_MEMBERS = tuple(
    member for member in ArtifactMember if member != ArtifactMember.MANIFEST
)


@dataclass(frozen=True)
class RenderRequest:
    """An exact UTF-8 source and bounded execution options accepted for rendering."""

    code: str
    figure_var: str = "fig"
    timeout_seconds: float = 20.0
    chart_type_hint: str | None = None

    def __post_init__(self) -> None:
        """Keep invalid direct constructions out of downstream execution sinks."""
        error = _request_error(
            self.code,
            self.figure_var,
            self.timeout_seconds,
            self.chart_type_hint,
        )
        if error is not None:
            raise ValueError(error.message)


@dataclass(frozen=True)
class FileEntry:
    """One verified data member's exact byte size and lowercase SHA-256 digest."""

    member: ArtifactMember
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        """Disallow self-digests, invalid sizes and ambiguous digest encodings."""
        if self.member not in DATA_MEMBERS or not isinstance(
            self.member, ArtifactMember
        ):
            raise ValueError("Expected a data member")
        if (
            type(self.size_bytes) is not int
            or not 0 <= self.size_bytes <= MAX_BUNDLE_BYTES
        ):
            raise ValueError("Invalid artifact byte size")
        if not isinstance(self.sha256, str) or not _HASH.fullmatch(self.sha256):
            raise ValueError("Invalid artifact digest")


@dataclass(frozen=True)
class ValidationSummary:
    """Ready delivery retains complete or explicitly incomplete validation."""

    status: str
    validation_complete: bool
    failed_checks: tuple[str, ...]

    def __post_init__(self) -> None:
        """Prevent an incomplete check set from being represented as clean."""
        if not isinstance(self.status, str) or self.status not in {
            "ok",
            "validation_incomplete",
        }:
            raise ValueError("Invalid ready validation status")
        if type(
            self.validation_complete
        ) is not bool or self.validation_complete != (self.status == "ok"):
            raise ValueError("Inconsistent validation completion")
        if not isinstance(self.failed_checks, tuple) or any(
            not isinstance(check, str) or not check
            for check in self.failed_checks
        ):
            raise ValueError("Invalid failed check identifiers")
        for check in self.failed_checks:
            check.encode("utf-8")
        if self.validation_complete and self.failed_checks:
            raise ValueError("Completed validation contains failed checks")


@dataclass(frozen=True)
class Manifest:
    """Parsed v1 commit metadata whose expiry is exactly seven days from creation."""

    artifact_id: ArtifactId
    created_at: datetime
    expires_at: datetime
    files: tuple[FileEntry, ...]
    validation: ValidationSummary

    def __post_init__(self) -> None:
        """Enforce local invariants even for trusted publication-side construction."""
        if not isinstance(self.artifact_id, ArtifactId) or not isinstance(
            self.validation, ValidationSummary
        ):
            raise ValueError("Invalid manifest values")
        _require_utc(self.created_at)
        _require_utc(self.expires_at)
        if self.expires_at - self.created_at != RETENTION:
            raise ValueError("Invalid artifact retention interval")
        if (
            not isinstance(self.files, tuple)
            or any(not isinstance(entry, FileEntry) for entry in self.files)
            or tuple(entry.member for entry in self.files) != DATA_MEMBERS
        ):
            raise ValueError("Expected four ordered unique data entries")
        if sum(entry.size_bytes for entry in self.files) > MAX_BUNDLE_BYTES:
            raise ValueError("Artifact data exceeds bundle limit")

    def to_bytes(self) -> bytes:
        """Serialize the exact v1 shape as deterministic UTF-8 with UTC Z times."""
        payload = {
            "schema_version": 1,
            "artifact_id": self.artifact_id.value,
            "created_at": self.created_at.isoformat().replace("+00:00", "Z"),
            "expires_at": self.expires_at.isoformat().replace("+00:00", "Z"),
            "files": [
                {
                    "name": entry.member.value,
                    "size_bytes": entry.size_bytes,
                    "sha256": entry.sha256,
                }
                for entry in self.files
            ],
            "validation": {
                "status": self.validation.status,
                "validation_complete": self.validation.validation_complete,
                "failed_checks": list(self.validation.failed_checks),
            },
        }
        return json.dumps(
            payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")


@dataclass(frozen=True)
class StoredBundle:
    """A complete parsed manifest and immutable mapping of five verified contents."""

    manifest: Manifest
    contents: Mapping[ArtifactMember, bytes]

    def __post_init__(self) -> None:
        """Copy verified contents so later caller mutations cannot alter the value."""
        if not isinstance(self.manifest, Manifest):
            raise ValueError("Expected a parsed manifest")
        if set(self.contents) != set(ArtifactMember) or any(
            not isinstance(member, ArtifactMember)
            or not isinstance(data, bytes)
            for member, data in self.contents.items()
        ):
            raise ValueError("Expected five byte contents")
        if sum(map(len, self.contents.values())) > MAX_BUNDLE_BYTES:
            raise ValueError("Bundle exceeds combined byte limit")
        if (
            parse_manifest(self.contents[ArtifactMember.MANIFEST])
            != self.manifest
        ):
            raise ValueError("Manifest contents do not match metadata")
        for entry in self.manifest.files:
            data = self.contents[entry.member]
            if (
                len(data) != entry.size_bytes
                or hashlib.sha256(data).hexdigest() != entry.sha256
            ):
                raise ValueError("Data does not match metadata")
        object.__setattr__(
            self, "contents", MappingProxyType(dict(self.contents))
        )


@dataclass(frozen=True)
class ArtifactBytes:
    """Verified resource bytes paired with the member's static MIME type."""

    data: bytes
    mime_type: str

    def __post_init__(self) -> None:
        """Reject mutable bytes and unknown MIME values at the value boundary."""
        if not isinstance(self.data, bytes) or self.mime_type not in {
            member.mime_type for member in ArtifactMember
        }:
            raise ValueError("Invalid artifact resource bytes")


def _require_utc(now: datetime) -> None:
    """Reject naive or non-UTC clocks rather than interpreting local time."""
    if (
        not isinstance(now, datetime)
        or now.tzinfo is None
        or now.utcoffset() != timedelta(0)
    ):
        raise ValueError("Expected an aware UTC datetime")


def _request_error(
    code: str,
    figure_var: str,
    timeout_seconds: float,
    chart_type_hint: str | None,
) -> InvalidRequest | None:
    """Recognize request fields without changing source or execution options."""
    try:
        if (
            not isinstance(code, str)
            or len(code.encode("utf-8")) > MAX_SOURCE_BYTES
        ):
            return InvalidRequest(
                "code", "Source must be at most 512 KiB of UTF-8."
            )
    except UnicodeError:
        return InvalidRequest("code", "Source must be valid UTF-8.")
    if (
        not isinstance(figure_var, str)
        or not figure_var.isidentifier()
        or keyword.iskeyword(figure_var)
    ):
        return InvalidRequest(
            "figure_var", "Figure variable must be a Python identifier."
        )
    if (
        type(timeout_seconds) not in (int, float)
        or not 0 < timeout_seconds <= 120
        or not math.isfinite(timeout_seconds)
    ):
        return InvalidRequest(
            "timeout_seconds", "Timeout must be finite and in (0, 120]."
        )
    if chart_type_hint is not None and not isinstance(chart_type_hint, str):
        return InvalidRequest(
            "chart_type_hint", "Chart type hint must be text or null."
        )
    return None


def parse_render_request(
    code: str,
    figure_var: str = "fig",
    timeout_seconds: float = 20.0,
    chart_type_hint: str | None = None,
) -> RenderRequest | InvalidRequest:
    """Parse raw request fields into an executable value or a safe named refusal."""
    error = _request_error(code, figure_var, timeout_seconds, chart_type_hint)
    return (
        error
        if error is not None
        else RenderRequest(code, figure_var, timeout_seconds, chart_type_hint)
    )


def parse_artifact_id(raw: str) -> ArtifactId | InvalidRequest:
    """Accept exactly one lowercase UUID4 hex segment; never normalize escapes."""
    try:
        return ArtifactId(raw)
    except ValueError:
        return InvalidRequest(
            "artifact_id", "Expected a full lowercase UUID4 hex identity."
        )


def _bounded_json(raw: bytes) -> Any:
    """Bound JSON before recursive decoding and reject duplicate/nonfinite values."""
    if not isinstance(raw, bytes) or len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Manifest exceeds parser byte bound")
    text = raw.decode("utf-8")
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 8:
                raise ValueError("Manifest exceeds parser depth bound")
        elif char in "]}":
            depth -= 1
    fields = 0

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        """Reject duplicate keys and cap all object fields during decoding."""
        nonlocal fields
        fields += len(pairs)
        if fields > 128 or len(dict(pairs)) != len(pairs):
            raise ValueError("Ambiguous or excessive manifest fields")
        return dict(pairs)

    def reject_constant(value: str) -> None:
        """Forbid JSON extensions for NaN and positive/negative infinity."""
        raise ValueError("Nonfinite JSON number")

    return json.loads(
        text, object_pairs_hook=object_pairs, parse_constant=reject_constant
    )


def _exact_fields(raw: Any, fields: set[str]) -> dict[str, Any]:
    """Require an object with exactly the declared fields, never silently ignore."""
    if not isinstance(raw, dict) or raw.keys() != fields:
        raise ValueError("Unexpected manifest shape")
    return raw


def _parse_time(raw: Any) -> datetime:
    """Recognize only UTC RFC3339 Z timestamps with representable precision."""
    if not isinstance(raw, str) or not _TIME.fullmatch(raw):
        raise ValueError("Invalid UTC timestamp")
    return datetime.fromisoformat(raw[:-1]).replace(tzinfo=timezone.utc)


def parse_manifest(raw: bytes) -> Manifest | CorruptArtifact:
    """Parse bounded exact-v1 bytes into immutable values or a safe corruption."""
    try:
        payload = _exact_fields(
            _bounded_json(raw),
            {
                "schema_version",
                "artifact_id",
                "created_at",
                "expires_at",
                "files",
                "validation",
            },
        )
        if (
            type(payload["schema_version"]) is not int
            or payload["schema_version"] != 1
        ):
            raise ValueError("Unsupported schema")
        files = payload["files"]
        if not isinstance(files, list) or len(files) != 4:
            raise ValueError("Invalid member count")
        entries = []
        for file in files:
            entry = _exact_fields(file, {"name", "size_bytes", "sha256"})
            entries.append(
                FileEntry(
                    ArtifactMember(entry["name"]),
                    entry["size_bytes"],
                    entry["sha256"],
                )
            )
        validation = _exact_fields(
            payload["validation"],
            {"status", "validation_complete", "failed_checks"},
        )
        if not isinstance(validation["failed_checks"], list):
            raise ValueError("Invalid failed check list")
        return Manifest(
            ArtifactId(payload["artifact_id"]),
            _parse_time(payload["created_at"]),
            _parse_time(payload["expires_at"]),
            tuple(entries),
            ValidationSummary(
                validation["status"],
                validation["validation_complete"],
                tuple(validation["failed_checks"]),
            ),
        )
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeError,
        OverflowError,
        RecursionError,
    ):
        return CorruptArtifact()


def is_expired(manifest: Manifest, now: datetime) -> bool:
    """Deny at and after immutable expiry; reads never extend retention."""
    _require_utc(now)
    return now >= manifest.expires_at
