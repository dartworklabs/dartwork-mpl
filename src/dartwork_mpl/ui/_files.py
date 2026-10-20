"""Confined viewer filesystem effects, independent of HTTP and model semantics.

Startup configuration grants directory-object authority. Requests provide only
parsed relative outputs; preparation pins every destination before rendering.
Outputs are create-only with best-effort rollback, never a cross-root transaction;
their files and new parents follow the process umask like an ordinary save.
Fixed state uses two separately owned private names and atomic sibling replacement.
"""

import errno
import os
import stat
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, ClassVar, TypeAlias

from ._boundary import (
    CopyTo,
    InputFailure,
    InvalidStoredState,
    LimitExceeded,
    RelativeOutput,
    StateKind,
)

__all__ = [
    "FileFailure",
    "FileIOFailure",
    "FilesystemCapabilities",
    "FixedStateStore",
    "MissingState",
    "PartialSave",
    "PreparedSave",
    "RootConflict",
    "RootScope",
    "SaveReceipt",
    "StateEditRefusal",
    "StateUnchanged",
    "StateWritten",
    "TargetConflict",
    "UnsafeTarget",
    "UnsupportedFilesystem",
    "commit_save",
    "detect_capabilities",
    "open_roots",
    "prepare_save",
]


@dataclass(frozen=True)
class UnsafeTarget:
    """A target cannot be traversed without following an unsafe filesystem object."""

    detail: str = "The output path contains an unsafe filesystem target."
    status_code: ClassVar[int] = 400
    code: ClassVar[str] = "unsafe_output_target"


@dataclass(frozen=True)
class TargetConflict:
    """An output already exists and must be preserved; choose a new name."""

    detail: str = "File exists; choose a new name."
    status_code: ClassVar[int] = 409
    code: ClassVar[str] = "output_conflict"


@dataclass(frozen=True)
class RootConflict:
    """An authorized root or pinned parent no longer occupies its configured name."""

    detail: str = (
        "The output directory changed; restart the viewer before saving."
    )
    status_code: ClassVar[int] = 409
    code: ClassVar[str] = "root_changed"


@dataclass(frozen=True)
class UnsupportedFilesystem:
    """Required no-follow directory-handle operations are unavailable on this host."""

    detail: str = "This host lacks filesystem capabilities required for safe viewer persistence."
    status_code: ClassVar[int] = 501
    code: ClassVar[str] = "unsupported_filesystem_capability"


@dataclass(frozen=True)
class FileIOFailure:
    """An I/O operation failed without disclosing exception paths or payloads."""

    detail: str = "The viewer could not complete the filesystem operation."
    status_code: ClassVar[int] = 503
    code: ClassVar[str] = "filesystem_unavailable"


@dataclass(frozen=True)
class PartialSave:
    """Best-effort cleanup left these root-qualified relative paths to inspect."""

    paths: tuple[str, ...]
    detail: str = (
        "The save failed and cleanup was incomplete; inspect the listed paths."
    )
    status_code: ClassVar[int] = 503
    code: ClassVar[str] = "partial_save"


FileFailure: TypeAlias = (
    UnsafeTarget
    | TargetConflict
    | RootConflict
    | UnsupportedFilesystem
    | FileIOFailure
    | PartialSave
    | InvalidStoredState
    | LimitExceeded
)


@dataclass(frozen=True)
class StateUnchanged:
    """An editor completed its locked decision without changing persisted bytes."""


StateEditRefusal: TypeAlias = InvalidStoredState | InputFailure | StateUnchanged


@dataclass(frozen=True)
class FilesystemCapabilities:
    """Injectable availability facts, checked before any startup directory creation."""

    no_follow: bool
    directory_handles: bool
    dir_fd_open: bool
    dir_fd_stat: bool
    dir_fd_mkdir: bool
    dir_fd_unlink: bool
    dir_fd_rmdir: bool
    dir_fd_rename: bool

    @property
    def supported(self) -> bool:
        """Require every primitive used by output and fixed-state operations."""
        return all(
            (
                self.no_follow,
                self.directory_handles,
                self.dir_fd_open,
                self.dir_fd_stat,
                self.dir_fd_mkdir,
                self.dir_fd_unlink,
                self.dir_fd_rmdir,
                self.dir_fd_rename,
            )
        )


def detect_capabilities() -> FilesystemCapabilities:
    """Inspect actual Python primitives; macOS advertises rename, not replace."""
    available = os.supports_dir_fd
    return FilesystemCapabilities(
        no_follow=bool(getattr(os, "O_NOFOLLOW", 0)),
        directory_handles=bool(getattr(os, "O_DIRECTORY", 0)),
        dir_fd_open=os.open in available,
        dir_fd_stat=os.stat in available
        and os.stat in os.supports_follow_symlinks,
        dir_fd_mkdir=os.mkdir in available,
        dir_fd_unlink=os.unlink in available,
        dir_fd_rmdir=os.rmdir in available,
        dir_fd_rename=os.rename in available,
    )


def _identity(info: os.stat_result) -> tuple[int, int]:
    """Identify a pinned filesystem object without trusting its display pathname."""
    return info.st_dev, info.st_ino


def _stat_handle(fd: int) -> os.stat_result:
    """Read acquired-object metadata at the owned seam for acquisition failures."""
    return os.fstat(fd)


def _directory_flags() -> int:
    """Open only a directory object and refuse a symbolic-link final component."""
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _open_root(path: Path) -> int:
    """Open a canonical startup root; the caller owns the returned descriptor."""
    return os.open(path, _directory_flags())


def _open_directory(parent_fd: int, name: str) -> int:
    """Open a relative directory without allowing a symlink or non-directory."""
    return os.open(name, _directory_flags(), dir_fd=parent_fd)


# Saved outputs keep the modes of an ordinary save (savefig, copy, mkdir): the
# process umask governs them. Only fixed viewer state is private.
_OUTPUT_FILE_MODE = 0o666
_OUTPUT_DIRECTORY_MODE = 0o777
_STATE_FILE_MODE = 0o600


def _reserve_file(parent_fd: int, name: str, *, mode: int) -> int:
    """Exclusively create a new regular file; never open or truncate an old one.

    ``mode`` is the requested creation mode before the process umask applies.
    """
    return os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        mode,
        dir_fd=parent_fd,
    )


def _write_file(fd: int, data: bytes) -> None:
    """Write all bytes to an already reserved file, including short writes."""
    remaining = memoryview(data)
    while remaining:
        written = os.write(fd, remaining)
        if written <= 0:
            raise OSError("File write made no progress")
        remaining = remaining[written:]


def _remove_file(parent_fd: int, name: str, identity: tuple[int, int]) -> bool:
    """Remove only the still-identical created object; the check/unlink is best-effort."""
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return True
    if _identity(current) != identity:
        return False
    os.unlink(name, dir_fd=parent_fd)
    return True


def _replace_state(parent_fd: int, staging: str, destination: str) -> None:
    """Atomically replace a fixed state name using the verified root descriptor."""
    os.rename(staging, destination, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)


@dataclass(frozen=True)
class _Root:
    """A startup-authorized directory object plus read-only display metadata."""

    path: Path
    fd: int
    identity: tuple[int, int]
    label: str


# These locks serialize operations across independently opened scopes too.
# Other processes remain last-writer-wins; they are not covered by these locks.
_SAVE_LOCK = threading.Lock()
_STATE_LOCK = threading.RLock()


class RootScope:
    """Own startup directory handles; close after prepared saves and stores finish."""

    def __init__(self, roots: tuple[_Root, ...]) -> None:
        """Accept only roots acquired by open_roots, with the primary first."""
        self._roots = roots
        self._closed = False

    @property
    def display_roots(self) -> tuple[str, ...]:
        """Return success/display metadata, never a downstream write operation."""
        return tuple(str(root.path) for root in self._roots)

    def close(self) -> None:
        """Release every root descriptor once; repeated shutdown is harmless."""
        if not self._closed:
            self._closed = True
            for root in self._roots:
                os.close(root.fd)

    def __enter__(self) -> "RootScope":
        """Keep explicit ownership convenient in callers with lexical lifetimes."""
        return self

    def __exit__(self, *_exc: object) -> None:
        """Release roots on normal completion and exceptions alike."""
        self.close()


def _normalize_roots(
    script_root: Path, copy_to: CopyTo, cwd: Path
) -> tuple[Path, ...]:
    """Normalize trusted one/list startup configuration before acquiring handles."""
    copies = (
        copy_to
        if isinstance(copy_to, list)
        else ([] if copy_to is None else [copy_to])
    )
    paths = []
    for value in [script_root, *copies]:
        path = Path(value).expanduser()
        paths.append((path if path.is_absolute() else cwd / path).resolve())
    return tuple(paths)


def open_roots(
    script_root: Path,
    copy_to: CopyTo,
    *,
    cwd: Path,
    capabilities: FilesystemCapabilities | None = None,
) -> RootScope | FileFailure:
    """Acquire/deduplicate configured roots, creating missing roots only if supported.

    Startup configuration is trusted and may designate canonical symlink aliases.
    Requests cannot mint roots. Partial startup always closes acquired handles.
    """
    if not (capabilities or detect_capabilities()).supported:
        return UnsupportedFilesystem()
    roots: list[_Root] = []
    owned_fd: int | None = None
    try:
        paths = _normalize_roots(script_root, copy_to, cwd)
        # Reject all known bad roots before creating any configured directory.
        for path in paths:
            if path.exists() and not path.is_dir():
                return TargetConflict(
                    "A configured output root is not a directory."
                )
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
            owned_fd = _open_root(path)
            identity = _identity(_stat_handle(owned_fd))
            if any(root.identity == identity for root in roots):
                os.close(owned_fd)
                owned_fd = None
                continue
            label = "primary" if not roots else f"copy[{len(roots)}]"
            roots.append(_Root(path, owned_fd, identity, label))
            owned_fd = None
        scope = RootScope(tuple(roots))
    except (OSError, ValueError, TypeError, RuntimeError):
        if owned_fd is not None:
            os.close(owned_fd)
        for root in roots:
            os.close(root.fd)
        return FileIOFailure()
    return scope


def _verify_root(scope: RootScope, root: _Root) -> RootConflict | None:
    """Detect closed, renamed or replaced root names before filesystem effects."""
    if scope._closed:
        return RootConflict()
    try:
        current = os.stat(root.path, follow_symlinks=False)
        if (
            not stat.S_ISDIR(current.st_mode)
            or _identity(current) != root.identity
        ):
            return RootConflict()
        if _identity(_stat_handle(root.fd)) != root.identity:
            return RootConflict()
    except OSError:
        return RootConflict()
    return None


@dataclass(frozen=True)
class _Directory:
    """One pinned parent, and whether this preparation created its entry."""

    fd: int
    name: str
    identity: tuple[int, int]
    created: bool = False


@dataclass(frozen=True)
class _UnverifiedDirectory:
    """A created directory entry whose identity could not yet be pinned safely."""

    parent_fd: int
    name: str
    relative: tuple[str, ...]


@dataclass
class _Target:
    """A relative output paired with its independently pinned root/parent chain."""

    root: _Root
    output: RelativeOutput
    chain: list[_Directory]
    missing: tuple[str, ...] = ()
    unverified: tuple[_UnverifiedDirectory, ...] = ()

    @property
    def relative(self) -> str:
        """Return an output name safe to report without disclosing absolute roots."""
        return "/".join(self.output.parts)

    @property
    def qualified(self) -> str:
        """Disambiguate identical relative paths in different configured roots."""
        return f"{self.root.label}/{self.relative}"


def _target_error(error: OSError) -> FileFailure:
    """Convert expected traversal/exclusive-create failures without leaking paths."""
    if error.errno == errno.EEXIST:
        return TargetConflict()
    if error.errno in (errno.ELOOP, errno.ENOTDIR, errno.ENAMETOOLONG):
        return UnsafeTarget()
    return FileIOFailure()


def _verify_target(scope: RootScope, target: _Target) -> RootConflict | None:
    """Compare each path entry with the directory handle the plan will actually use."""
    refusal = _verify_root(scope, target.root)
    if refusal is not None:
        return refusal
    try:
        for parent, child in zip(target.chain, target.chain[1:], strict=False):
            current = os.stat(
                child.name, dir_fd=parent.fd, follow_symlinks=False
            )
            if (
                not stat.S_ISDIR(current.st_mode)
                or _identity(current) != child.identity
            ):
                return RootConflict()
            if _identity(_stat_handle(child.fd)) != child.identity:
                return RootConflict()
    except OSError:
        return RootConflict()
    return None


def _pin_directory(
    parent_fd: int, name: str, *, created: bool = False
) -> _Directory:
    """Own an opened directory immediately; failed metadata cannot leak its handle."""
    fd = _open_directory(parent_fd, name)
    try:
        return _Directory(fd, name, _identity(_stat_handle(fd)), created)
    except BaseException:
        os.close(fd)
        raise


def _inspect_target(target: _Target) -> FileFailure | None:
    """Pin existing parents and reject a present leaf without creating anything."""
    try:
        parent_parts = target.output.parts[:-1]
        for index, part in enumerate(parent_parts):
            try:
                directory = _pin_directory(target.chain[-1].fd, part)
            except FileNotFoundError:
                target.missing = parent_parts[index:]
                return None
            target.chain.append(directory)
        try:
            leaf = os.stat(
                target.output.parts[-1],
                dir_fd=target.chain[-1].fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return None
        return (
            UnsafeTarget() if stat.S_ISLNK(leaf.st_mode) else TargetConflict()
        )
    except OSError as error:
        return _target_error(error)


def _complete_parents(scope: RootScope, target: _Target) -> FileFailure | None:
    """Create safe missing parents only after the complete destination set validated.

    New parents take the umask-governed mode of an ordinary ``mkdir``.
    """
    try:
        for part in target.missing:
            refusal = _verify_target(scope, target)
            if refusal is not None:
                return refusal
            created = False
            try:
                os.mkdir(
                    part, _OUTPUT_DIRECTORY_MODE, dir_fd=target.chain[-1].fd
                )
                created = True
                target.unverified += (
                    _UnverifiedDirectory(
                        target.chain[-1].fd,
                        part,
                        (*tuple(node.name for node in target.chain[1:]), part),
                    ),
                )
            except FileExistsError:
                pass
            target.chain.append(
                _pin_directory(target.chain[-1].fd, part, created=created)
            )
            if created:
                target.unverified = target.unverified[:-1]
        target.missing = ()
    except OSError as error:
        return _target_error(error)
    return None


def _entry_remains(parent_fd: int, name: str) -> bool:
    """Report an unverified created name conservatively, without treating stat as deletion authority."""
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _cleanup_directories(targets: list[_Target]) -> tuple[str, ...]:
    """Remove identical, request-created empty directories; report remaining entries."""
    leftovers: list[str] = []
    for target in reversed(targets):
        leftovers.extend(
            f"{target.root.label}/" + "/".join(directory.relative)
            for directory in target.unverified
            if _entry_remains(directory.parent_fd, directory.name)
        )
        for index in range(len(target.chain) - 1, 0, -1):
            child = target.chain[index]
            if not child.created:
                continue
            path = f"{target.root.label}/" + "/".join(
                node.name for node in target.chain[1 : index + 1]
            )
            try:
                parent = target.chain[index - 1]
                current = os.stat(
                    child.name, dir_fd=parent.fd, follow_symlinks=False
                )
                if _identity(current) == child.identity:
                    os.rmdir(child.name, dir_fd=parent.fd)
                else:
                    leftovers.append(path)
            except FileNotFoundError:
                continue
            except OSError:
                leftovers.append(path)
    return tuple(sorted(set(leftovers)))


def _close_targets(targets: list[_Target]) -> None:
    """Release every duplicated root and traversed parent after cleanup finishes."""
    for target in targets:
        for directory in reversed(target.chain):
            os.close(directory.fd)


class PreparedSave:
    """Own pinned parents and the process save lock until commit or explicit close.

    Callers must close an abandoned plan if rendering fails. A committed plan is
    consumed once; cleanup preserves pre-existing and externally replaced files.
    """

    def __init__(self, roots: RootScope, targets: list[_Target]) -> None:
        """Transfer already acquired parents and lock ownership from prepare_save."""
        self._roots = roots
        self._targets = targets
        self._closed = False
        self._complete = False

    def close(self) -> PartialSave | None:
        """Release once and report any empty parents an abandoned plan could not remove."""
        leftovers: tuple[str, ...] = ()
        if not self._closed:
            try:
                if not self._complete:
                    leftovers = _cleanup_directories(self._targets)
                _close_targets(self._targets)
            finally:
                self._closed = True
                _SAVE_LOCK.release()
        return PartialSave(leftovers) if leftovers else None

    def __enter__(self) -> "PreparedSave":
        """Keep an abandoned plan's cleanup tied to callback/rendering lifetime."""
        return self

    def __exit__(self, *_exc: object) -> None:
        """Release parents and lock even when rendering raises."""
        self.close()


def prepare_save(
    roots: RootScope, output: RelativeOutput, *, include_copies: bool
) -> PreparedSave | FileFailure:
    """Check every destination first, then create/pin safe missing subdirectories."""
    _SAVE_LOCK.acquire()
    targets: list[_Target] = []
    refusal: FileFailure | None = None
    try:
        for root in roots._roots if include_copies else roots._roots[:1]:
            refusal = _verify_root(roots, root)
            if refusal is not None:
                break
            fd = os.dup(root.fd)
            target = _Target(root, output, [_Directory(fd, "", root.identity)])
            targets.append(target)
            refusal = _inspect_target(target)
            if refusal is not None:
                break
        if refusal is None:
            for target in targets:
                refusal = _complete_parents(roots, target)
                if refusal is not None:
                    break
    except OSError as error:
        refusal = _target_error(error)
    except BaseException:
        try:
            _cleanup_directories(targets)
            _close_targets(targets)
        finally:
            _SAVE_LOCK.release()
        raise
    if refusal is not None:
        try:
            leftovers = _cleanup_directories(targets)
            _close_targets(targets)
        finally:
            _SAVE_LOCK.release()
        return PartialSave(leftovers) if leftovers else refusal
    return PreparedSave(roots, targets)


@dataclass(frozen=True)
class SaveReceipt:
    """Completed primary/copy names, plus display-only absolute success metadata."""

    primary: str
    copies: tuple[str, ...]
    primary_display: str
    copy_displays: tuple[str, ...]


@dataclass(frozen=True)
class _Reserved:
    """An exclusively created file whose handle and identity remain request-owned."""

    target: _Target
    fd: int
    identity: tuple[int, int]


@dataclass(frozen=True)
class _UnverifiedFile:
    """An exclusively created file owned before its identity could be established."""

    target: _Target
    fd: int


def _rollback_files(
    files: list[_Reserved | _UnverifiedFile],
) -> tuple[str, ...]:
    """Best-effort identity cleanup never deliberately unlinks another writer's file."""
    leftovers = []
    for owned in reversed(files):
        if isinstance(owned, _UnverifiedFile):
            if _entry_remains(
                owned.target.chain[-1].fd, owned.target.output.parts[-1]
            ):
                leftovers.append(owned.target.qualified)
            continue
        try:
            removed = _remove_file(
                owned.target.chain[-1].fd,
                owned.target.output.parts[-1],
                owned.identity,
            )
            if not removed:
                leftovers.append(owned.target.qualified)
        except OSError:
            leftovers.append(owned.target.qualified)
    return tuple(sorted(leftovers))


def commit_save(
    plan: PreparedSave, source: BinaryIO
) -> SaveReceipt | FileFailure:
    """Reserve every sink exclusively, stream bytes once, and clean up on failure.

    Another writer's late creation conflicts. Provisional new files may be visible
    to readers. A crash may leave them, and same-owner adversarial renames are not
    covered by a global atomicity guarantee. New files take the umask-governed
    mode of an ordinary save.
    """
    if plan._closed:
        return RootConflict("This prepared save has already been closed.")
    files: list[_Reserved | _UnverifiedFile] = []
    refusal: FileFailure | None = None
    try:
        try:
            for target in plan._targets:
                refusal = _verify_target(plan._roots, target)
                if refusal is not None:
                    break
                fd = _reserve_file(
                    target.chain[-1].fd,
                    target.output.parts[-1],
                    mode=_OUTPUT_FILE_MODE,
                )
                files.append(_UnverifiedFile(target, fd))
                files[-1] = _Reserved(target, fd, _identity(_stat_handle(fd)))
            if refusal is None:
                for target in plan._targets:
                    refusal = _verify_target(plan._roots, target)
                    if refusal is not None:
                        break
            if refusal is None:
                while data := source.read(1024 * 1024):
                    for owned in files:
                        _write_file(owned.fd, data)
        except OSError as error:
            refusal = _target_error(error)
        except Exception:  # noqa: BLE001 - BinaryIO implementations may raise ordinary Python errors
            refusal = FileIOFailure()
        finally:
            for owned in files:
                os.close(owned.fd)
        if refusal is not None:
            leftovers = (
                *_rollback_files(files),
                *_cleanup_directories(plan._targets),
            )
            plan._complete = True
            return (
                PartialSave(tuple(sorted(set(leftovers))))
                if leftovers
                else refusal
            )
        plan._complete = True
        primary, *copies = plan._targets
        return SaveReceipt(
            primary.relative,
            tuple(target.relative for target in copies),
            str(primary.root.path.joinpath(*primary.output.parts)),
            tuple(
                str(target.root.path.joinpath(*target.output.parts))
                for target in copies
            ),
        )
    finally:
        # Cancellation and other BaseException paths still relinquish ownership.
        try:
            if not plan._complete:
                _rollback_files(files)
                _cleanup_directories(plan._targets)
                plan._complete = True
        finally:
            plan.close()


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
            root = self._roots._roots[0]
            refusal = _verify_root(self._roots, root)
            if refusal is not None:
                return refusal
            fd: int | None = None
            try:
                fd = os.open(
                    _state_name(kind),
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=root.fd,
                )
                info = _stat_handle(fd)
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
            root = self._roots._roots[0]
            refusal = _verify_root(self._roots, root)
            if refusal is not None:
                return refusal
            name = _state_name(kind)
            staging = f"{name}.{uuid.uuid4().hex}.tmp"
            fd: int | None = None
            identity: tuple[int, int] | None = None
            created = False
            result: StateWritten | FileFailure = FileIOFailure()
            try:
                fd = _reserve_file(root.fd, staging, mode=_STATE_FILE_MODE)
                created = True
                identity = _identity(_stat_handle(fd))
                _write_file(fd, proposed)
                os.fsync(fd)
                os.close(fd)
                fd = None
                refusal = _verify_root(self._roots, root)
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
                    if _entry_remains(root.fd, staging):
                        result = PartialSave((f"primary/{staging}",))
                elif created and identity is not None:
                    try:
                        if not _remove_file(root.fd, staging, identity):
                            result = PartialSave((f"primary/{staging}",))
                    except OSError:
                        result = PartialSave((f"primary/{staging}",))
            return result
