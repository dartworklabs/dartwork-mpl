"""Read the exact approved ``docs/superpowers`` test inputs, and refuse others.

``approved_inputs.json`` beside this module lists every file below
``docs/superpowers`` that a test may read, one exact repository-relative path
per entry (user approval, 2026-11-08). No directory, glob or alias is listed.
This module is the reader for those files:

* a path that is not exactly a manifest entry is refused before anything on
  disk is touched;
* the walk is bound to descriptors: it opens the trusted root as a directory,
  then each directory below it relative to its parent's descriptor with
  ``O_DIRECTORY | O_NOFOLLOW``, so a component that is (or is swapped into) a
  symlink is refused, and a parent replaced after it was opened cannot
  redirect the rest of the walk;
* the file is checked, opened (``O_NOFOLLOW``), ``fstat``-ed and read through
  its parent's descriptor; it must be a regular file and the opened inode the
  checked one. Every descriptor is closed, on errors too;
* a platform without descriptor-relative opens is refused rather than read
  through the path-based walk this replaces;
* a ``pinned-json`` entry's raw bytes must match the SHA-256 that the existing
  source pin records (``pin_source``/``pin_key``). The manifest names that pin
  and keeps no second copy of the value.

What this does not prove: it governs only the reads that go through it.
Product loaders such as ``load_v5_snapshot`` open their own pinned paths, a
child process is not seen, and nothing here confines arbitrary filesystem
access. The sparse ``approved-inputs`` CI job, which checks out only the
listed files, is where any other ``docs/superpowers`` read shows up as a
missing file -- for the tests that job runs.
"""

from __future__ import annotations

import errno
import functools
import hashlib
import io
import json
import os
import stat
from collections.abc import Mapping
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Literal, cast

MANIFEST_PATH = Path(__file__).with_name("approved_inputs.json")
REPO_ROOT = Path(__file__).resolve().parents[2]
APPROVED_PREFIX = "docs/superpowers/"
_SCHEMA = "dartwork-mpl.approved-test-inputs/v1"
_PIN_SOURCE = "dartwork_mpl._colors._ssot._PINNED_BASELINES"
_KINDS = ("pinned-json", "document")
_PATTERN_CHARACTERS = frozenset("*?[]{}\\")
_READ_CHUNK = 1 << 20
# Optional flags: close-on-exec, and no blocking open of a FIFO swapped in.
_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_NONBLOCK = getattr(os, "O_NONBLOCK", 0)

InputKind = Literal["pinned-json", "document"]


class UnapprovedInputError(PermissionError):
    """A path outside the manifest, or an alias of a listed path."""


class ApprovedInputPinError(RuntimeError):
    """A pinned input whose raw bytes differ from the existing source pin."""


@dataclass(frozen=True)
class ApprovedInput:
    """One exact manifest entry.

    ``pin_key`` names an entry of the existing source pin
    ``dartwork_mpl._colors._ssot._PINNED_BASELINES`` for ``pinned-json``
    inputs and is ``None`` for documents.
    """

    path: str
    kind: InputKind
    purpose: str
    pin_key: str | None


def _exact_relative_path(value: object) -> str:
    """Return ``value`` if it is one exact file path below the prefix."""
    if not isinstance(value, str) or not value.startswith(APPROVED_PREFIX):
        raise ValueError(f"{value!r} is not a path below {APPROVED_PREFIX}")
    if value.endswith("/") or _PATTERN_CHARACTERS.intersection(value):
        raise ValueError(f"{value!r} is a directory or pattern, not a file")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{value!r} is not a normalised relative path")
    if str(PurePosixPath(value)) != value:
        raise ValueError(f"{value!r} is not a normalised relative path")
    return value


def _entry(raw: object) -> ApprovedInput:
    """Validate one decoded manifest entry."""
    if not isinstance(raw, dict):
        raise ValueError(f"manifest entry {raw!r} is not an object")
    entry = cast(dict[str, object], raw)
    kind = entry.get("kind")
    purpose = entry.get("purpose")
    if kind not in _KINDS:
        raise ValueError(f"manifest entry kind {kind!r} is not one of {_KINDS}")
    if not isinstance(purpose, str) or not purpose:
        raise ValueError("manifest entry needs a purpose")
    path = _exact_relative_path(entry.get("path"))
    if kind == "pinned-json":
        expected = {"path", "kind", "purpose", "pin_source", "pin_key"}
        pin_key = entry.get("pin_key")
        if entry.get("pin_source") != _PIN_SOURCE:
            raise ValueError(f"{path}: pin_source must be {_PIN_SOURCE}")
        if not isinstance(pin_key, str) or not pin_key:
            raise ValueError(f"{path}: a pinned-json input needs a pin_key")
    else:
        expected = {"path", "kind", "purpose"}
        pin_key = None
    if set(entry) != expected:
        raise ValueError(f"{path}: keys {sorted(entry)} != {sorted(expected)}")
    return ApprovedInput(
        path=path, kind=cast(InputKind, kind), purpose=purpose, pin_key=pin_key
    )


def load_manifest(path: Path = MANIFEST_PATH) -> Mapping[str, ApprovedInput]:
    """Decode and validate a manifest; return its entries keyed by path."""
    decoded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError(f"{path} must contain a JSON object")
    manifest = cast(dict[str, object], decoded)
    if manifest.get("schema") != _SCHEMA:
        raise ValueError(f"{path}: schema must be {_SCHEMA}")
    raw_inputs = manifest.get("inputs")
    if not isinstance(raw_inputs, list) or not raw_inputs:
        raise ValueError(f"{path}: inputs must be a non-empty list")
    entries: dict[str, ApprovedInput] = {}
    for raw in raw_inputs:
        entry = _entry(raw)
        if entry.path in entries:
            raise ValueError(f"{path}: {entry.path} is listed twice")
        entries[entry.path] = entry
    return MappingProxyType(entries)


@functools.cache
def approved_inputs() -> Mapping[str, ApprovedInput]:
    """Return the checked-in manifest, validated once per process."""
    return load_manifest()


def existing_pin(entry: ApprovedInput) -> str | None:
    """Return the existing source pin's raw SHA-256 for ``entry``.

    The pin must record the same repository path as the manifest entry, so
    the manifest cannot attach a listed file to another file's pin.
    """
    if entry.pin_key is None:
        return None
    from dartwork_mpl._colors import _ssot

    pinned_path, digest = _ssot._PINNED_BASELINES[entry.pin_key]
    if pinned_path != entry.path:
        raise ApprovedInputPinError(
            f"{entry.path}: pin {entry.pin_key!r} records {pinned_path}"
        )
    return digest


def _checked_entry(
    relative: str, manifest: Mapping[str, ApprovedInput] | None
) -> ApprovedInput:
    """Return the manifest entry for exactly ``relative`` or refuse it."""
    entries = approved_inputs() if manifest is None else manifest
    entry = entries.get(relative) if isinstance(relative, str) else None
    if entry is None:
        raise UnapprovedInputError(
            f"{relative!r} is not an approved test input "
            f"(see {MANIFEST_PATH.name})"
        )
    return entry


def _missing_descriptor_support() -> tuple[str, ...]:
    """Name what this platform lacks for a descriptor-bound walk."""
    missing = [
        name for name in ("O_DIRECTORY", "O_NOFOLLOW") if not hasattr(os, name)
    ]
    if os.open not in os.supports_dir_fd:
        missing.append("os.open(dir_fd=...)")
    if os.stat not in os.supports_dir_fd:
        missing.append("os.stat(dir_fd=...)")
    if os.stat not in os.supports_follow_symlinks:
        missing.append("os.stat(follow_symlinks=False)")
    return tuple(missing)


# Decided once, at import, from the real ``os`` functions.
MISSING_DESCRIPTOR_SUPPORT = _missing_descriptor_support()


def _require_descriptor_walk() -> None:
    """Refuse a platform that cannot open relative to a directory descriptor.

    The path-based walk this replaces cannot be made safe against a parent
    swapped for a symlink, so there is no fallback.
    """
    if MISSING_DESCRIPTOR_SUPPORT:
        raise UnapprovedInputError(
            "approved inputs need descriptor-relative opens; this platform "
            f"lacks {', '.join(MISSING_DESCRIPTOR_SUPPORT)}"
        )


def _open_directory(
    name: str, parent: int, relative: str, descriptors: ExitStack
) -> int:
    """Open one child directory of ``parent`` without following a symlink."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | _CLOEXEC
    try:
        descriptor = os.open(name, flags, dir_fd=parent)
    except OSError as error:
        # Linux reports a symlink under O_DIRECTORY | O_NOFOLLOW as ENOTDIR,
        # other systems as ELOOP; a regular file is ENOTDIR everywhere.
        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise UnapprovedInputError(
                f"{relative}: {name} is a symlink or not a directory; "
                "aliases are refused"
            ) from error
        raise
    descriptors.callback(os.close, descriptor)
    return descriptor


def _read_regular_file(
    name: str, parent: int, relative: str, descriptors: ExitStack
) -> bytes:
    """Check, open, ``fstat`` and read one regular file of ``parent``."""
    checked = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if stat.S_ISLNK(checked.st_mode):
        raise UnapprovedInputError(
            f"{relative}: {name} is a symlink; aliases are refused"
        )
    if not stat.S_ISREG(checked.st_mode):
        raise UnapprovedInputError(f"{relative} is not a regular file")
    flags = os.O_RDONLY | os.O_NOFOLLOW | _NONBLOCK | _CLOEXEC
    try:
        descriptor = os.open(name, flags, dir_fd=parent)
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise UnapprovedInputError(
                f"{relative}: {name} became a symlink; aliases are refused"
            ) from error
        raise
    descriptors.callback(os.close, descriptor)
    opened = os.fstat(descriptor)
    if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
        checked.st_dev,
        checked.st_ino,
    ):
        raise UnapprovedInputError(f"{relative} changed while opening")
    chunks: list[bytes] = []
    while chunk := os.read(descriptor, _READ_CHUNK):
        chunks.append(chunk)
    return b"".join(chunks)


def read_approved_bytes(
    relative: str,
    *,
    root: Path = REPO_ROOT,
    manifest: Mapping[str, ApprovedInput] | None = None,
) -> bytes:
    """Return the raw bytes of one approved input after its checks.

    ``root`` is trusted and may itself be reached through symlinks; nothing
    below it is. A missing component raises ``FileNotFoundError``, as
    reading the path directly would. A ``pinned-json`` input whose bytes
    differ from the existing source pin raises ``ApprovedInputPinError``.
    """
    entry = _checked_entry(relative, manifest)
    _require_descriptor_walk()
    *directories, name = relative.split("/")
    with ExitStack() as descriptors:
        current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | _CLOEXEC)
        descriptors.callback(os.close, current)
        for part in directories:
            current = _open_directory(part, current, relative, descriptors)
        raw = _read_regular_file(name, current, relative, descriptors)
    expected = existing_pin(entry)
    if expected is not None:
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise ApprovedInputPinError(
                f"{relative} SHA-256 mismatch: expected {expected}, "
                f"got {actual}"
            )
    return raw


def read_approved_text(
    relative: str,
    *,
    root: Path = REPO_ROOT,
    manifest: Mapping[str, ApprovedInput] | None = None,
) -> str:
    """Return one approved input as ``Path.read_text(encoding="utf-8")`` would.

    The same text decoding (UTF-8, universal newlines) runs on the checked
    bytes, so a caller that used ``read_text`` sees identical text.
    """
    raw = read_approved_bytes(relative, root=root, manifest=manifest)
    with io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8") as text:
        return text.read()
