"""Descriptor-confined filesystem primitives of the artifact store.

Mechanism only: no-follow handle walks, opened-object identity, verified
bounded reads, exclusive 0600 writes and quarantine restore. Bundle members,
manifests, expiry and the refusal values callers return stay in ``store``.
"""

import os
import stat
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path

from .policy import ArtifactTooLarge

_DIRECTORY_FLAGS = (
    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
)
_FILE_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_NOCTTY", 0)
)


class _UnsafeArtifactObject(OSError):
    """Distinguish verified unsafe objects from an inability to observe disk."""


def _descriptor_operations_available() -> bool:
    """Refuse unsafe fallback on hosts without the required handle operations."""
    flags = ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")
    calls = ("geteuid", "fchmod", "fstat", "fsync")
    operations = ("open", "mkdir", "stat", "unlink", "rmdir", "rename", "link")
    return (
        all(hasattr(os, flag) for flag in flags)
        and all(hasattr(os, call) for call in calls)
        and all(
            getattr(os, operation, None) in os.supports_dir_fd
            for operation in operations
        )
        and os.listdir in os.supports_fd
        and getattr(os, "link", None) in os.supports_follow_symlinks
    )


def _identity(fd: int) -> tuple[int, int]:
    """Identify an opened object without trusting its current pathname."""
    info = os.fstat(fd)
    return info.st_dev, info.st_ino


def _check_directory(fd: int, *, private: bool) -> None:
    """Reject non-directories and unsafe ownership/mode on private objects."""
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode):
        raise _UnsafeArtifactObject("Artifact directory is invalid")
    if private and (
        info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise _UnsafeArtifactObject("Artifact directory is not private")


def _open_directory(parent_fd: int, name: str, *, private: bool = True) -> int:
    """Open one literal child without following links and verify the opened dir."""
    fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    try:
        _check_directory(fd, private=private)
    except OSError:
        os.close(fd)
        raise
    return fd


def _walk_root(root: Path, *, create: bool) -> int | None:
    """Walk from the filesystem root via no-follow handles, optionally mkdir 0700."""
    fd = os.open(root.anchor, _DIRECTORY_FLAGS)
    try:
        for index, component in enumerate(root.parts[1:]):
            final = index == len(root.parts) - 2
            try:
                child = _open_directory(fd, component, private=final)
            except FileNotFoundError:
                if not create:
                    os.close(fd)
                    return None
                with suppress(FileExistsError):
                    os.mkdir(component, mode=0o700, dir_fd=fd)
                child = _open_directory(fd, component, private=final)
            os.close(fd)
            fd = child
        _check_directory(fd, private=True)
    except OSError:
        os.close(fd)
        raise
    return fd


def _check_file(fd: int, *, private: bool) -> os.stat_result:
    """Accept only an owned, unshared regular file, with private read-back mode."""
    info = os.fstat(fd)
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.geteuid()
        or info.st_nlink != 1
    ):
        raise _UnsafeArtifactObject(
            "Artifact member is not an owned regular file"
        )
    if private and stat.S_IMODE(info.st_mode) != 0o600:
        raise _UnsafeArtifactObject("Artifact member is not private")
    return info


def _read_file(
    directory_fd: int,
    name: str,
    limit: int,
    *,
    private: bool = True,
    evidence: dict[str, tuple[int, int]] | None = None,
) -> bytes | ArtifactTooLarge:
    """Read a bounded verified regular file; optionally capture its opened identity."""
    fd = os.open(name, _FILE_FLAGS, dir_fd=directory_fd)
    try:
        before = _check_file(fd, private=private)
        if before.st_size > limit:
            return ArtifactTooLarge(before.st_size, limit)
        if not private:
            os.fchmod(fd, 0o600)
            before = _check_file(fd, private=True)
        chunks = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(fd, min(remaining, 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > limit:
            return ArtifactTooLarge(len(data), limit)
        after = _check_file(fd, private=True)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) or len(data) != before.st_size:
            raise _UnsafeArtifactObject(
                "Artifact member changed during reading"
            )
        if not private:
            os.fsync(fd)
        if evidence is not None:
            evidence[name] = (after.st_dev, after.st_ino)
        return data
    finally:
        os.close(fd)


def _root_ancestry(
    root: Path, *, allow_missing: bool = False
) -> dict[tuple[int, int], tuple[str, ...]]:
    """Map opened ancestor objects to remaining lexical components, read-only.

    Components are opened without following symlinks; aliases use device/inode,
    not realpath. Only an unpinned artifact root may have an unresolved suffix,
    via allow_missing, when compared with fully observed input storage. Missing
    input roots and invalid/unsafe/unobservable paths raise OSError/ValueError.
    No directory is created or case/normalization rule guessed.
    """
    if not root.is_absolute() or ".." in root.parts or "\x00" in str(root):
        raise ValueError("Expected an absolute root without parent components")
    fd = os.open(root.anchor, _DIRECTORY_FLAGS)
    try:
        remaining = root.parts[1:]
        ancestry = {_identity(fd): remaining}
        while remaining:
            try:
                child = _open_directory(fd, remaining[0], private=False)
            except FileNotFoundError:
                if allow_missing:
                    break
                raise
            os.close(fd)
            fd = child
            remaining = remaining[1:]
            ancestry[_identity(fd)] = remaining
        return ancestry
    finally:
        os.close(fd)


def _roots_overlap(
    first: Mapping[tuple[int, int], tuple[str, ...]],
    second: Mapping[tuple[int, int], tuple[str, ...]],
) -> bool:
    """Detect an opened root object shared by both directory ancestries.

    At least one root must be fully observed. An unresolved artifact suffix is
    separated from existing storage unless it first visits that storage object.
    """
    return any(
        not first[identity] or not second[identity]
        for identity in first.keys() & second.keys()
    )


def _write_file(directory_fd: int, name: str, data: bytes) -> None:
    """Exclusively write and fsync one owned 0600 file under the opened stage."""
    fd = os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory_fd,
    )
    try:
        _check_file(fd, private=True)
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written == 0:
                raise OSError("Artifact write made no progress")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _restore_isolated(
    quarantine_fd: int, directory_fd: int, members: set[str]
) -> None:
    """Restore isolated objects exclusively; collisions retain both objects.

    link creates the old name only if absent. A directory or unsupported object
    that cannot be linked stays in quarantine instead of being deleted.
    """
    for member in sorted(members):
        with suppress(OSError):
            os.link(
                member,
                member,
                src_dir_fd=quarantine_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
            os.unlink(member, dir_fd=quarantine_fd)
