"""Confined directory handles for the viewer: startup roots and no-follow file primitives.

Mechanism only: it knows directory objects, their identities and exclusive
creation, not outputs, state kinds or HTTP. Startup configuration grants
directory-object authority through ``open_roots``; the primitives below let
the saving and state code act only through pinned handles. Surface: the
filesystem refusals and ``FsFailure``, ``FilesystemCapabilities``,
``detect_capabilities``, ``Root``/``RootScope``/``open_roots``,
``verify_root`` and the handle primitives.
"""

import os
import stat
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import ClassVar, TypeAlias

__all__ = [
    "CopyTo",
    "FileIOFailure",
    "FilesystemCapabilities",
    "FsFailure",
    "PartialSave",
    "Root",
    "RootConflict",
    "RootScope",
    "TargetConflict",
    "UnsafeTarget",
    "UnsupportedFilesystem",
    "detect_capabilities",
    "entry_remains",
    "object_identity",
    "open_directory",
    "open_roots",
    "remove_file",
    "reserve_file",
    "stat_handle",
    "verify_root",
    "write_file",
]

CopyTo: TypeAlias = "str | PathLike[str] | list[str | PathLike[str]] | None"


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


FsFailure: TypeAlias = (
    UnsafeTarget
    | TargetConflict
    | RootConflict
    | UnsupportedFilesystem
    | FileIOFailure
    | PartialSave
)


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


def object_identity(info: os.stat_result) -> tuple[int, int]:
    """Identify a pinned filesystem object without trusting its display pathname."""
    return info.st_dev, info.st_ino


def stat_handle(fd: int) -> os.stat_result:
    """Read acquired-object metadata at the owned seam for acquisition failures."""
    return os.fstat(fd)


def _directory_flags() -> int:
    """Open only a directory object and refuse a symbolic-link final component."""
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _open_root(path: Path) -> int:
    """Open a canonical startup root; the caller owns the returned descriptor."""
    return os.open(path, _directory_flags())


def open_directory(parent_fd: int, name: str) -> int:
    """Open a relative directory without allowing a symlink or non-directory."""
    return os.open(name, _directory_flags(), dir_fd=parent_fd)


def reserve_file(parent_fd: int, name: str, *, mode: int) -> int:
    """Exclusively create a new regular file; never open or truncate an old one.

    ``mode`` is the requested creation mode before the process umask applies.
    """
    return os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        mode,
        dir_fd=parent_fd,
    )


def write_file(fd: int, data: bytes) -> None:
    """Write all bytes to an already reserved file, including short writes."""
    remaining = memoryview(data)
    while remaining:
        written = os.write(fd, remaining)
        if written <= 0:
            raise OSError("File write made no progress")
        remaining = remaining[written:]


def remove_file(parent_fd: int, name: str, identity: tuple[int, int]) -> bool:
    """Remove only the still-identical created object; the check/unlink is best-effort."""
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return True
    if object_identity(current) != identity:
        return False
    os.unlink(name, dir_fd=parent_fd)
    return True


@dataclass(frozen=True)
class Root:
    """A startup-authorized directory object plus read-only display metadata."""

    path: Path
    fd: int
    identity: tuple[int, int]
    label: str


class RootScope:
    """Own startup directory handles; close after prepared saves and stores finish."""

    def __init__(self, roots: tuple[Root, ...]) -> None:
        """Accept only roots acquired by open_roots, with the primary first."""
        self._roots = roots
        self._closed = False

    @property
    def roots(self) -> tuple[Root, ...]:
        """Return the acquired roots, primary first, for the operations that use them."""
        return self._roots

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
) -> RootScope | FsFailure:
    """Acquire/deduplicate configured roots, creating missing roots only if supported.

    Startup configuration is trusted and may designate canonical symlink aliases.
    Requests cannot mint roots. Partial startup always closes acquired handles.
    """
    if not (capabilities or detect_capabilities()).supported:
        return UnsupportedFilesystem()
    roots: list[Root] = []
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
            identity = object_identity(stat_handle(owned_fd))
            if any(root.identity == identity for root in roots):
                os.close(owned_fd)
                owned_fd = None
                continue
            label = "primary" if not roots else f"copy[{len(roots)}]"
            roots.append(Root(path, owned_fd, identity, label))
            owned_fd = None
        scope = RootScope(tuple(roots))
    except (OSError, ValueError, TypeError, RuntimeError):
        if owned_fd is not None:
            os.close(owned_fd)
        for root in roots:
            os.close(root.fd)
        return FileIOFailure()
    return scope


def verify_root(scope: RootScope, root: Root) -> RootConflict | None:
    """Detect closed, renamed or replaced root names before filesystem effects."""
    if scope._closed:
        return RootConflict()
    try:
        current = os.stat(root.path, follow_symlinks=False)
        if (
            not stat.S_ISDIR(current.st_mode)
            or object_identity(current) != root.identity
        ):
            return RootConflict()
        if object_identity(stat_handle(root.fd)) != root.identity:
            return RootConflict()
    except OSError:
        return RootConflict()
    return None


def entry_remains(parent_fd: int, name: str) -> bool:
    """Report an unverified created name conservatively, without treating stat as deletion authority."""
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True
