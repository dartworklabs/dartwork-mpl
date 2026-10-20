"""Pure bounded revision, private metadata and creation-time receipt contracts.

These values confer no filesystem authority. Shells must separately authorize,
copy and verify bytes before building a receipt; a receipt is never live status.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias

from .policy import (
    RETENTION,
    ArtifactId,
    CorruptArtifact,
    InvalidRequest,
    _bounded_json,
    _exact_fields,
    _parse_time,
    _require_utc,
)

MAX_REVISION_BYTES = 16 * 1024
MAX_INPUT_METADATA_BYTES = 16 * 1024
MAX_INPUT_FILES = 8
MAX_INPUT_FILE_BYTES = 8 * 1024 * 1024
MAX_INPUT_PAYLOAD_BYTES = 32 * 1024 * 1024
MAX_INPUT_STORE_BYTES = 512 * 1024 * 1024
MAX_INPUT_STORE_SETS = 128
_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _require_name(value: object) -> None:
    """Reject ambiguous names without echoing caller data in errors."""
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise ValueError("Invalid input identifier")


def _require_hash(value: object) -> None:
    """Accept a complete lowercase SHA-256 digest without normalization."""
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError("Invalid input digest")


def _require_path(value: object) -> None:
    """Require bounded UTF-8 relative POSIX components; perform no resolution."""
    if not isinstance(value, str):
        raise ValueError("Invalid relative path")
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Invalid relative path") from exc
    if (
        not 0 < len(encoded) <= 1024
        or "\\" in value
        or "\x00" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError("Invalid relative path")


@dataclass(frozen=True)
class CopyInput:
    """A bounded explicit file selection under an operator-supplied logical root."""

    name: str
    root_id: str
    relative_path: str
    sha256: str

    def __post_init__(self) -> None:
        """Guard trusted construction without granting access to the selected root."""
        _require_name(self.name)
        _require_name(self.root_id)
        _require_path(self.relative_path)
        _require_hash(self.sha256)


@dataclass(frozen=True)
class RetainedInput:
    """A prior set/name selection whose admission must recheck availability."""

    name: str
    artifact_id: ArtifactId
    input_name: str
    sha256: str

    def __post_init__(self) -> None:
        """Require a parsed identity, valid names and an exact expected digest."""
        _require_name(self.name)
        _require_name(self.input_name)
        _require_hash(self.sha256)
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValueError("Expected a parsed retained identity")


@dataclass(frozen=True)
class Revision:
    """An explicit parent and/or nonempty ordered, uniquely named input selection."""

    parent_artifact_id: ArtifactId | None
    inputs: tuple[CopyInput | RetainedInput, ...]

    def __post_init__(self) -> None:
        """Reject missing intent, mutable sequences and duplicate or excess inputs."""
        if self.parent_artifact_id is not None and not isinstance(
            self.parent_artifact_id, ArtifactId
        ):
            raise ValueError("Expected a parsed parent identity")
        _require_entries(self.inputs, (CopyInput, RetainedInput))
        if self.parent_artifact_id is None and not self.inputs:
            raise ValueError("Revision requires a parent or inputs")


@dataclass(frozen=True)
class InputFile:
    """One measured whole-file copy, independent of its original path."""

    name: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        """Reject invalid names, digests, booleans and oversized measured files."""
        _require_name(self.name)
        _require_hash(self.sha256)
        if (
            type(self.size_bytes) is not int
            or not 0 <= self.size_bytes <= MAX_INPUT_FILE_BYTES
        ):
            raise ValueError("Invalid input byte size")


def _require_entries(entries: object, kinds: tuple[type, ...]) -> None:
    """Require an immutable bounded unique-name sequence of the declared values."""
    if not isinstance(entries, tuple) or len(entries) > MAX_INPUT_FILES:
        raise ValueError("Invalid input entries")
    if any(not isinstance(entry, kinds) for entry in entries):
        raise ValueError("Invalid input entry type")
    if len({entry.name for entry in entries}) != len(entries):
        raise ValueError("Duplicate input name")


@dataclass(frozen=True)
class InputMetadata:
    """Private ordered copy metadata sharing the child bundle's seven-day clock."""

    artifact_id: ArtifactId
    created_at: datetime
    expires_at: datetime
    files: tuple[InputFile, ...]

    def __post_init__(self) -> None:
        """Keep metadata nonempty, bounded and UTC with an exact retention interval."""
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValueError("Expected a parsed input-set identity")
        _require_utc(self.created_at)
        _require_utc(self.expires_at)
        if self.expires_at - self.created_at != RETENTION:
            raise ValueError("Invalid input retention interval")
        _require_entries(self.files, (InputFile,))
        if (
            not self.files
            or sum(entry.size_bytes for entry in self.files)
            > MAX_INPUT_PAYLOAD_BYTES
        ):
            raise ValueError("Invalid input payload size")

    def to_bytes(self) -> bytes:
        """Serialize closed metadata deterministically, with no path or receipt."""
        return json.dumps(
            {
                "schema_version": 1,
                "artifact_id": self.artifact_id.value,
                "created_at": self.created_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "expires_at": self.expires_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "files": [_file_dict(entry) for entry in self.files],
            },
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")


@dataclass(frozen=True)
class PinnedParent:
    """Admission-time identity and digests of verified immutable parent bytes."""

    artifact_id: ArtifactId
    manifest_sha256: str
    source_sha256: str

    def __post_init__(self) -> None:
        """Require a typed parent identity and exact digests without I/O."""
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValueError("Expected a parsed parent identity")
        _require_hash(self.manifest_sha256)
        _require_hash(self.source_sha256)


@dataclass(frozen=True)
class CopySelection:
    """Creation-time evidence of a Copy choice, carrying no original path."""


@dataclass(frozen=True)
class RetainedSelection:
    """Creation-time choice of the prior set/name, distinct from the child locator."""

    artifact_id: ArtifactId
    input_name: str

    def __post_init__(self) -> None:
        """Require a parsed prior identity and a bounded logical input name."""
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValueError("Expected a parsed selection identity")
        _require_name(self.input_name)


@dataclass(frozen=True)
class RetainedLocator:
    """The child's independently owned copy location, never current availability."""

    artifact_id: ArtifactId
    name: str

    def __post_init__(self) -> None:
        """Require a typed child identity and logical name, never a storage path."""
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValueError("Expected a parsed child identity")
        _require_name(self.name)


@dataclass(frozen=True)
class ProvenanceInput:
    """Measured copy identity paired with its closed creation-time selection."""

    name: str
    sha256: str
    size_bytes: int
    retained: RetainedLocator
    selection: CopySelection | RetainedSelection

    def __post_init__(self) -> None:
        """Reject invalid measured fields, mismatched names and unknown selections."""
        InputFile(self.name, self.sha256, self.size_bytes)
        if (
            not isinstance(self.retained, RetainedLocator)
            or self.retained.name != self.name
        ):
            raise ValueError("Invalid child locator")
        if not isinstance(self.selection, (CopySelection, RetainedSelection)):
            raise ValueError("Invalid input selection")


@dataclass(frozen=True)
class KnownProvenance:
    """Parsed closed v1 receipt, with constant evidence and reproducibility claims."""

    parent: PinnedParent | None
    inputs: tuple[ProvenanceInput, ...]

    def __post_init__(self) -> None:
        """Require a parent or bounded child copies sharing one set identity."""
        if self.parent is not None and not isinstance(
            self.parent, PinnedParent
        ):
            raise ValueError("Invalid pinned parent")
        _require_entries(self.inputs, (ProvenanceInput,))
        if self.parent is None and not self.inputs:
            raise ValueError("Missing revision evidence")
        if (
            sum(entry.size_bytes for entry in self.inputs)
            > MAX_INPUT_PAYLOAD_BYTES
        ):
            raise ValueError("Invalid provenance payload size")
        if len({entry.retained.artifact_id for entry in self.inputs}) > 1:
            raise ValueError("Input locators must share one child identity")

    def to_dict(self) -> dict[str, object]:
        """Return a fresh closed wire receipt, without live status or original paths."""
        return {
            "schema_version": 1,
            "parent": None
            if self.parent is None
            else {
                "artifact_id": self.parent.artifact_id.value,
                "manifest_sha256": self.parent.manifest_sha256,
                "source_sha256": self.parent.source_sha256,
            },
            "inputs": [
                {
                    **_file_dict(entry),
                    "retained": {
                        "artifact_id": entry.retained.artifact_id.value,
                        "name": entry.retained.name,
                    },
                    "selection": {"kind": "copy"}
                    if isinstance(entry.selection, CopySelection)
                    else {
                        "kind": "retained",
                        "artifact_id": entry.selection.artifact_id.value,
                        "input_name": entry.selection.input_name,
                    },
                    "evidence": "copied_and_boundary_checked",
                }
                for entry in self.inputs
            ],
            "reproducibility": "not_claimed",
        }


@dataclass(frozen=True)
class LegacyProvenance:
    """The report has no provenance; ancestry must not be inferred."""


@dataclass(frozen=True)
class UnsupportedProvenance:
    """A different integer receipt version exists and is not interpreted."""


@dataclass(frozen=True)
class InvalidProvenance:
    """A malformed receipt cannot be interpreted and carries no caller data."""


Provenance: TypeAlias = (
    KnownProvenance
    | LegacyProvenance
    | UnsupportedProvenance
    | InvalidProvenance
)


def _file_dict(entry: InputFile | ProvenanceInput) -> dict[str, object]:
    """Project measured fields only, excluding paths and selection details."""
    return {
        "name": entry.name,
        "sha256": entry.sha256,
        "size_bytes": entry.size_bytes,
    }


def _object_bytes(raw: object, limit: int) -> bytes:
    """Bound parsed JSON structure before encoding; reject cycles, depth and types.

    Container depth starts at one. The work/character budget stops wide inputs
    before serialization; compact UTF-8 encoding then enforces the exact bound.
    """
    pending = [(raw, 0)]
    budget = limit
    while pending:
        value, depth = pending.pop()
        budget -= 1
        if budget < 0:
            raise ValueError("Excessive JSON structure")
        if isinstance(value, (dict, list)):
            if type(value) not in (dict, list):
                raise ValueError("Invalid JSON container")
            depth += 1
            if depth > 4 or len(value) > budget:
                raise ValueError("Excessive JSON structure")
            if isinstance(value, dict):
                for key, item in value.items():
                    if type(key) is not str:
                        raise ValueError("Invalid JSON key")
                    budget -= len(key)
                    pending.append((item, depth))
            else:
                pending.extend((item, depth) for item in value)
        elif type(value) is str:
            budget -= len(value)
        elif value is not None and type(value) not in (bool, int, float):
            raise ValueError("Invalid JSON value")
        if budget < 0:
            raise ValueError("Excessive JSON structure")
    chunks = []
    size = 0
    encoder = json.JSONEncoder(
        ensure_ascii=False, allow_nan=False, separators=(",", ":")
    )
    for chunk in encoder.iterencode(raw):
        encoded = chunk.encode("utf-8")
        size += len(encoded)
        if size > limit:
            raise ValueError("Excessive JSON bytes")
        chunks.append(encoded)
    return b"".join(chunks)


def _version_one(raw: object) -> None:
    """Reject boolean or unknown versions rather than coercing to integer one."""
    if type(raw) is not int or raw != 1:
        raise ValueError("Unsupported schema")


def parse_revision(raw: object) -> Revision | None | InvalidRequest:
    """Parse a closed bounded revision independently of the legacy RenderRequest."""
    if raw is None:
        return None
    try:
        _object_bytes(raw, MAX_REVISION_BYTES)
        if not isinstance(raw, dict) or not {
            "schema_version"
        } <= raw.keys() <= {"schema_version", "parent_artifact_id", "inputs"}:
            raise ValueError("Invalid revision shape")
        _version_one(raw["schema_version"])
        parent = (
            ArtifactId(raw["parent_artifact_id"])
            if "parent_artifact_id" in raw
            else None
        )
        inputs = raw.get("inputs", [])
        if not isinstance(inputs, list) or len(inputs) > MAX_INPUT_FILES:
            raise ValueError("Invalid input count")
        entries: list[CopyInput | RetainedInput] = []
        for item in inputs:
            if not isinstance(item, dict):
                raise ValueError("Invalid input shape")
            if item.get("kind") == "copy":
                entry = _exact_fields(
                    item, {"kind", "name", "root_id", "relative_path", "sha256"}
                )
                entries.append(
                    CopyInput(
                        entry["name"],
                        entry["root_id"],
                        entry["relative_path"],
                        entry["sha256"],
                    )
                )
            else:
                entry = _exact_fields(
                    item,
                    {"kind", "name", "artifact_id", "input_name", "sha256"},
                )
                if entry["kind"] != "retained":
                    raise ValueError("Invalid input kind")
                entries.append(
                    RetainedInput(
                        entry["name"],
                        ArtifactId(entry["artifact_id"]),
                        entry["input_name"],
                        entry["sha256"],
                    )
                )
        return Revision(parent, tuple(entries))
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeError,
        OverflowError,
        RecursionError,
    ):
        return InvalidRequest(
            "revision", "Revision must satisfy the bounded v1 input contract."
        )


def parse_input_metadata(raw: bytes) -> InputMetadata | CorruptArtifact:
    """Decode bounded duplicate-free private metadata without filesystem access."""
    try:
        payload = _exact_fields(
            _bounded_json(raw, max_bytes=MAX_INPUT_METADATA_BYTES, max_depth=4),
            {
                "schema_version",
                "artifact_id",
                "created_at",
                "expires_at",
                "files",
            },
        )
        _version_one(payload["schema_version"])
        files = payload["files"]
        if (
            not isinstance(files, list)
            or not 1 <= len(files) <= MAX_INPUT_FILES
        ):
            raise ValueError("Invalid input file count")
        entries = []
        for raw_file in files:
            file = _exact_fields(raw_file, {"name", "sha256", "size_bytes"})
            entries.append(
                InputFile(file["name"], file["sha256"], file["size_bytes"])
            )
        return InputMetadata(
            ArtifactId(payload["artifact_id"]),
            _parse_time(payload["created_at"]),
            _parse_time(payload["expires_at"]),
            tuple(entries),
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


def classify_provenance(report: object) -> Provenance:
    """Distinguish absent/unknown/invalid receipts without guessing parent history."""
    if not isinstance(report, dict):
        return InvalidProvenance()
    if "provenance" not in report:
        return LegacyProvenance()
    raw = report["provenance"]
    if not isinstance(raw, dict) or type(raw.get("schema_version")) is not int:
        return InvalidProvenance()
    if raw["schema_version"] != 1:
        return UnsupportedProvenance()
    try:
        _object_bytes(raw, MAX_INPUT_METADATA_BYTES)
        payload = _exact_fields(
            raw, {"schema_version", "parent", "inputs", "reproducibility"}
        )
        if payload["reproducibility"] != "not_claimed":
            raise ValueError("Invalid reproducibility evidence")
        parent = None
        if payload["parent"] is not None:
            parent_raw = _exact_fields(
                payload["parent"],
                {"artifact_id", "manifest_sha256", "source_sha256"},
            )
            parent = PinnedParent(
                ArtifactId(parent_raw["artifact_id"]),
                parent_raw["manifest_sha256"],
                parent_raw["source_sha256"],
            )
        inputs = payload["inputs"]
        if not isinstance(inputs, list) or len(inputs) > MAX_INPUT_FILES:
            raise ValueError("Invalid provenance input count")
        entries = []
        for item in inputs:
            entry = _exact_fields(
                item,
                {
                    "name",
                    "sha256",
                    "size_bytes",
                    "retained",
                    "selection",
                    "evidence",
                },
            )
            if entry["evidence"] != "copied_and_boundary_checked":
                raise ValueError("Invalid copy evidence")
            locator = _exact_fields(entry["retained"], {"artifact_id", "name"})
            selection_raw = entry["selection"]
            if not isinstance(selection_raw, dict):
                raise ValueError("Invalid selection")
            selection: CopySelection | RetainedSelection
            if selection_raw.get("kind") == "copy":
                _exact_fields(selection_raw, {"kind"})
                selection = CopySelection()
            else:
                selected = _exact_fields(
                    selection_raw, {"kind", "artifact_id", "input_name"}
                )
                if selected["kind"] != "retained":
                    raise ValueError("Invalid selection kind")
                selection = RetainedSelection(
                    ArtifactId(selected["artifact_id"]), selected["input_name"]
                )
            entries.append(
                ProvenanceInput(
                    entry["name"],
                    entry["sha256"],
                    entry["size_bytes"],
                    RetainedLocator(
                        ArtifactId(locator["artifact_id"]), locator["name"]
                    ),
                    selection,
                )
            )
        return KnownProvenance(parent, tuple(entries))
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeError,
        OverflowError,
        RecursionError,
    ):
        return InvalidProvenance()


def build_provenance(
    revision: Revision,
    parent: PinnedParent | None,
    metadata: InputMetadata | None,
) -> dict[str, object]:
    """Build creation-time evidence from matching pinned/measured facts only.

    Mismatched trusted arguments are programming errors (ValueError). This
    function neither authorizes a request nor proves actual Python consumption.
    Metadata is absent exactly for parent-only revisions.
    """
    if not isinstance(revision, Revision):
        raise ValueError("Expected a parsed revision")
    if parent is not None and not isinstance(parent, PinnedParent):
        raise ValueError("Expected a pinned parent")
    if (
        None if parent is None else parent.artifact_id
    ) != revision.parent_artifact_id:
        raise ValueError("Parent does not match revision")
    if not revision.inputs:
        if metadata is not None:
            raise ValueError("Parent-only revision has no input metadata")
        return KnownProvenance(parent, ()).to_dict()
    if not isinstance(metadata, InputMetadata) or len(metadata.files) != len(
        revision.inputs
    ):
        raise ValueError("Input metadata does not match revision")
    entries = []
    for selected, file in zip(revision.inputs, metadata.files, strict=True):
        if (selected.name, selected.sha256) != (file.name, file.sha256):
            raise ValueError("Measured input does not match selection")
        selection = (
            CopySelection()
            if isinstance(selected, CopyInput)
            else RetainedSelection(selected.artifact_id, selected.input_name)
        )
        entries.append(
            ProvenanceInput(
                file.name,
                file.sha256,
                file.size_bytes,
                RetainedLocator(metadata.artifact_id, file.name),
                selection,
            )
        )
    return KnownProvenance(parent, tuple(entries)).to_dict()


def can_reserve(used_bytes: int, used_sets: int, reserved_bytes: int) -> bool:
    """Admit one next set only within both fixed store bounds.

    used_bytes/used_sets already count pending, reserved and revoked residue.
    reserved_bytes is this request's full reservation including metadata/marker
    allowance, supplied by the shell. Invalid counters deny without I/O.
    """
    return (
        all(
            type(value) is int and value >= 0
            for value in (used_bytes, used_sets, reserved_bytes)
        )
        and used_sets < MAX_INPUT_STORE_SETS
        and used_bytes + reserved_bytes <= MAX_INPUT_STORE_BYTES
    )
