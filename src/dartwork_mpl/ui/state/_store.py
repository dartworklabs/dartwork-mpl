"""The two fixed viewer-state files: bounded bytes under the primary root, locked per process.

This layer knows no JSON or model schema. ``.dartwork_ui_config.json`` and
``.dartwork_ui_presets.json`` are the only names; replacement is an atomic
sibling rename of a private (0600) staging file. An editor can refuse
malformed state before replacement; separate processes can still lose
updates to one another.
"""

import errno
import os
import stat
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from ..params import InputFailure
from ..platform import fs
from ..platform.fs import FileIOFailure, FsFailure, PartialSave, RootScope
from ..platform.json_bounds import LimitExceeded
from ._language import InvalidStoredState, StateKind

FileFailure: TypeAlias = FsFailure | InvalidStoredState | LimitExceeded


@dataclass(frozen=True)
class StateUnchanged:
    """An editor completed its locked decision without changing persisted bytes."""


StateEditRefusal: TypeAlias = InvalidStoredState | InputFailure | StateUnchanged


def _replace_state(parent_fd: int, staging: str, destination: str) -> None:
    """Atomically replace a fixed state name using the verified root descriptor."""
    os.rename(staging, destination, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)


_STATE_FILE_MODE = 0o600

# This lock serializes state edits across independently opened scopes too.
# Other processes remain last-writer-wins; they are not covered by this lock.
_STATE_LOCK = threading.RLock()


@dataclass(frozen=True)
class MissingState:
    """The chosen fixed viewer state name has not been created."""


@dataclass(frozen=True)
class StateWritten:
    """The complete next bytes replaced one fixed viewer-owned state name."""


def _state_name(kind: StateKind) -> str:
    """Resolve the two trusted kinds without admitting request-selected filenames."""
    if kind == "config":
        return ".dartwork_ui_config.json"
    if kind == "presets":
        return ".dartwork_ui_presets.json"
    raise ValueError("Unknown fixed state kind")


class FixedStateStore:
    """Bounded fixed-name bytes under a root, with process-wide read/edit/write locks.

    This layer knows no JSON/model schema. An editor can refuse malformed state
    before replacement; different processes can still lose updates to one another.
    """

    def __init__(self, roots: RootScope) -> None:
        """Borrow a live scope; its owner must close it after store use finishes."""
        self._roots = roots

    def read(
        self, kind: StateKind, *, max_bytes: int
    ) -> bytes | MissingState | FileFailure:
        """Read at most the bound plus one byte, refusing symlinks/nonregular state."""
        with _STATE_LOCK:
            root = self._roots.roots[0]
            refusal = fs.verify_root(self._roots, root)
            if refusal is not None:
                return refusal
            fd: int | None = None
            try:
                fd = os.open(
                    _state_name(kind),
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=root.fd,
                )
                info = fs.stat_handle(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
                    return InvalidStoredState()
                with os.fdopen(fd, "rb") as stream:
                    fd = None
                    data = stream.read(max_bytes + 1)
                return data if len(data) <= max_bytes else InvalidStoredState()
            except FileNotFoundError:
                return MissingState()
            except OSError as error:
                return (
                    InvalidStoredState()
                    if error.errno in (errno.ELOOP, errno.EISDIR)
                    else FileIOFailure()
                )
            finally:
                if fd is not None:
                    os.close(fd)

    def update(
        self,
        kind: StateKind,
        *,
        max_bytes: int,
        edit: Callable[[bytes | MissingState], bytes | StateEditRefusal],
    ) -> StateWritten | StateEditRefusal | FileFailure:
        """Lock read/edit/bound/staging/replacement; refused edits preserve old bytes.

        Staging is created private (0600), so the replaced state stays private.
        """
        with _STATE_LOCK:
            previous = self.read(kind, max_bytes=max_bytes)
            if not isinstance(previous, (bytes, MissingState)):
                return previous
            proposed = edit(previous)
            if not isinstance(proposed, bytes):
                return proposed
            if len(proposed) > max_bytes:
                return LimitExceeded()
            root = self._roots.roots[0]
            refusal = fs.verify_root(self._roots, root)
            if refusal is not None:
                return refusal
            name = _state_name(kind)
            staging = f"{name}.{uuid.uuid4().hex}.tmp"
            fd: int | None = None
            identity: tuple[int, int] | None = None
            created = False
            result: StateWritten | FileFailure = FileIOFailure()
            try:
                fd = fs.reserve_file(root.fd, staging, mode=_STATE_FILE_MODE)
                created = True
                identity = fs.object_identity(fs.stat_handle(fd))
                fs.write_file(fd, proposed)
                os.fsync(fd)
                os.close(fd)
                fd = None
                refusal = fs.verify_root(self._roots, root)
                if refusal is not None:
                    result = refusal
                else:
                    # Re-check the name to refuse a controlled late symlink/device.
                    current = self.read(kind, max_bytes=max_bytes)
                    if not isinstance(current, (bytes, MissingState)):
                        result = current
                    else:
                        _replace_state(root.fd, staging, name)
                        created = False
                        result = StateWritten()
            except OSError:
                result = FileIOFailure()
            finally:
                if fd is not None:
                    os.close(fd)
                if created and identity is None:
                    if fs.entry_remains(root.fd, staging):
                        result = PartialSave((f"primary/{staging}",))
                elif created and identity is not None:
                    try:
                        if not fs.remove_file(root.fd, staging, identity):
                            result = PartialSave((f"primary/{staging}",))
                    except OSError:
                        result = PartialSave((f"primary/{staging}",))
            return result
