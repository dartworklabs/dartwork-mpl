"""Confined server saves, independent of HTTP and model semantics.

Directory handles and the no-follow primitives live in ``platform.fs``;
startup configuration grants directory-object authority there. Requests provide only
parsed relative outputs; preparation pins every destination before rendering.
Outputs are create-only with best-effort rollback, never a cross-root transaction;
their files and new parents follow the process umask like an ordinary save.
"""

import errno
import os
import stat
import threading
from dataclasses import dataclass
from typing import BinaryIO

from ..platform import fs
from ..platform.fs import (
    FileIOFailure,
    FsFailure,
    PartialSave,
    RootConflict,
    RootScope,
    TargetConflict,
    UnsafeTarget,
)
from ._output import RelativeOutput

# Saved outputs keep the modes of an ordinary save (savefig, copy, mkdir): the
# process umask governs them (only fixed viewer state, in ``state``, is
# private).
_OUTPUT_FILE_MODE = 0o666
_OUTPUT_DIRECTORY_MODE = 0o777


# This lock serializes saves across independently opened scopes too.
# Other processes remain last-writer-wins; they are not covered by this lock.
_SAVE_LOCK = threading.Lock()


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

    root: fs.Root
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


def _target_error(error: OSError) -> FsFailure:
    """Convert expected traversal/exclusive-create failures without leaking paths."""
    if error.errno == errno.EEXIST:
        return TargetConflict()
    if error.errno in (errno.ELOOP, errno.ENOTDIR, errno.ENAMETOOLONG):
        return UnsafeTarget()
    return FileIOFailure()


def _verify_target(scope: RootScope, target: _Target) -> RootConflict | None:
    """Compare each path entry with the directory handle the plan will actually use."""
    refusal = fs.verify_root(scope, target.root)
    if refusal is not None:
        return refusal
    try:
        for parent, child in zip(target.chain, target.chain[1:], strict=False):
            current = os.stat(
                child.name, dir_fd=parent.fd, follow_symlinks=False
            )
            if (
                not stat.S_ISDIR(current.st_mode)
                or fs.object_identity(current) != child.identity
            ):
                return RootConflict()
            if fs.object_identity(fs.stat_handle(child.fd)) != child.identity:
                return RootConflict()
    except OSError:
        return RootConflict()
    return None


def _pin_directory(
    parent_fd: int, name: str, *, created: bool = False
) -> _Directory:
    """Own an opened directory immediately; failed metadata cannot leak its handle."""
    fd = fs.open_directory(parent_fd, name)
    try:
        return _Directory(
            fd, name, fs.object_identity(fs.stat_handle(fd)), created
        )
    except BaseException:
        os.close(fd)
        raise


def _inspect_target(target: _Target) -> FsFailure | None:
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


def _complete_parents(scope: RootScope, target: _Target) -> FsFailure | None:
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


def _cleanup_directories(targets: list[_Target]) -> tuple[str, ...]:
    """Remove identical, request-created empty directories; report remaining entries."""
    leftovers: list[str] = []
    for target in reversed(targets):
        leftovers.extend(
            f"{target.root.label}/" + "/".join(directory.relative)
            for directory in target.unverified
            if fs.entry_remains(directory.parent_fd, directory.name)
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
                if fs.object_identity(current) == child.identity:
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
) -> PreparedSave | FsFailure:
    """Check every destination first, then create/pin safe missing subdirectories."""
    _SAVE_LOCK.acquire()
    targets: list[_Target] = []
    refusal: FsFailure | None = None
    try:
        for root in roots.roots if include_copies else roots.roots[:1]:
            refusal = fs.verify_root(roots, root)
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
            if fs.entry_remains(
                owned.target.chain[-1].fd, owned.target.output.parts[-1]
            ):
                leftovers.append(owned.target.qualified)
            continue
        try:
            removed = fs.remove_file(
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
) -> SaveReceipt | FsFailure:
    """Reserve every sink exclusively, stream bytes once, and clean up on failure.

    Another writer's late creation conflicts. Provisional new files may be visible
    to readers. A crash may leave them, and same-owner adversarial renames are not
    covered by a global atomicity guarantee. New files take the umask-governed
    mode of an ordinary save.
    """
    if plan._closed:
        return RootConflict("This prepared save has already been closed.")
    files: list[_Reserved | _UnverifiedFile] = []
    refusal: FsFailure | None = None
    try:
        try:
            for target in plan._targets:
                refusal = _verify_target(plan._roots, target)
                if refusal is not None:
                    break
                fd = fs.reserve_file(
                    target.chain[-1].fd,
                    target.output.parts[-1],
                    mode=_OUTPUT_FILE_MODE,
                )
                files.append(_UnverifiedFile(target, fd))
                files[-1] = _Reserved(
                    target, fd, fs.object_identity(fs.stat_handle(fd))
                )
            if refusal is None:
                for target in plan._targets:
                    refusal = _verify_target(plan._roots, target)
                    if refusal is not None:
                        break
            if refusal is None:
                while data := source.read(1024 * 1024):
                    for owned in files:
                        fs.write_file(owned.fd, data)
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
