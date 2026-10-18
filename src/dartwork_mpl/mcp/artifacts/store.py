"""Private durable bundles, accessed only through a configuration-bound handle.

Opened descriptors, literal member names and UUID reservations confine effects.
The local OS user still owns the files and trusted export receives a pathname;
this is not a sandbox for code executing with that same user's privileges.
"""

import hashlib
import json
import os
import stat
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, suppress
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from .policy import (
    DATA_MEMBERS,
    MAX_BUNDLE_BYTES,
    MAX_MANIFEST_BYTES,
    MAX_SOURCE_BYTES,
    RETENTION,
    ArtifactBytes,
    ArtifactId,
    ArtifactMember,
    ArtifactTooLarge,
    ConfigurationError,
    CorruptArtifact,
    Expired,
    FileEntry,
    InvalidRequest,
    Manifest,
    NotFound,
    PublicationError,
    StoredBundle,
    StoreFailure,
    ValidationSummary,
    _require_utc,
    is_expired,
    parse_artifact_id,
    parse_manifest,
)

_CONSTRUCTION_KEY = object()
_READY_NAMES = {member.value for member in ArtifactMember}
_TEMP_MANIFEST = ".manifest.pending"
_DIRECTORY_FLAGS = (
    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
)
_FILE_FLAGS = (
    os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
)


def _descriptor_operations_available() -> bool:
    """Refuse unsafe fallback on hosts without the required handle operations."""
    flags = ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")
    calls = ("getuid", "fchmod", "fstat", "fsync")
    operations = (os.open, os.mkdir, os.stat, os.unlink, os.rmdir, os.rename)
    return (
        all(hasattr(os, flag) for flag in flags)
        and all(hasattr(os, call) for call in calls)
        and all(operation in os.supports_dir_fd for operation in operations)
        and os.listdir in os.supports_fd
    )


def _identity(fd: int) -> tuple[int, int]:
    """Identify an opened object without trusting its current pathname."""
    info = os.fstat(fd)
    return info.st_dev, info.st_ino


def _check_directory(fd: int, *, private: bool) -> None:
    """Reject non-directories and unsafe ownership/mode on private objects."""
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode):
        raise OSError("Artifact directory is invalid")
    if private and (
        info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise OSError("Artifact directory is not private")


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
        or info.st_uid != os.getuid()
        or info.st_nlink != 1
    ):
        raise OSError("Artifact member is not an owned regular file")
    if private and stat.S_IMODE(info.st_mode) != 0o600:
        raise OSError("Artifact member is not private")
    return info


def _read_file(
    directory_fd: int, name: str, limit: int, *, private: bool = True
) -> bytes | ArtifactTooLarge:
    """Read at most the allowance from a verified no-follow opened regular file."""
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
            raise OSError("Artifact member changed during reading")
        if not private:
            os.fsync(fd)
        return data
    finally:
        os.close(fd)


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


def _read_bundle(
    directory_fd: int, artifact_id: ArtifactId
) -> StoredBundle | StoreFailure:
    """Require the complete five-file marker shape and verify every size/digest."""
    try:
        raw = _read_file(
            directory_fd, ArtifactMember.MANIFEST.value, MAX_MANIFEST_BYTES
        )
    except FileNotFoundError:
        return NotFound()
    if isinstance(raw, ArtifactTooLarge):
        return CorruptArtifact()
    manifest = parse_manifest(raw)
    if isinstance(manifest, CorruptArtifact):
        return manifest
    if (
        manifest.artifact_id != artifact_id
        or set(os.listdir(directory_fd)) != _READY_NAMES
    ):
        return CorruptArtifact()
    total = len(raw) + sum(entry.size_bytes for entry in manifest.files)
    if total > MAX_BUNDLE_BYTES:
        return ArtifactTooLarge(total)
    contents = {ArtifactMember.MANIFEST: raw}
    for entry in manifest.files:
        data = _read_file(
            directory_fd,
            entry.member.value,
            MAX_BUNDLE_BYTES - sum(map(len, contents.values())),
        )
        if isinstance(data, ArtifactTooLarge):
            return ArtifactTooLarge(
                data.size_bytes + sum(map(len, contents.values()))
            )
        if (
            len(data) != entry.size_bytes
            or hashlib.sha256(data).hexdigest() != entry.sha256
        ):
            return CorruptArtifact()
        contents[entry.member] = data
    return StoredBundle(manifest, contents)


def _remove_owned(
    root_fd: int, name: str, directory_fd: int, *, ready: bool
) -> None:
    """Remove only literal known regular members of the pinned owned directory.

    Unexpected entries and links are preserved. No recursive deletion and no
    deletion by a user-provided pathname occurs, even for crash leftovers.
    """
    current = _open_directory(root_fd, name)
    try:
        if _identity(current) != _identity(directory_fd):
            return
    finally:
        os.close(current)
    names = set(os.listdir(directory_fd))
    allowed = _READY_NAMES if ready else _READY_NAMES | {_TEMP_MANIFEST}
    if ready and names != _READY_NAMES:
        return
    for member in sorted(names & allowed):
        try:
            fd = os.open(member, _FILE_FLAGS, dir_fd=directory_fd)
            try:
                _check_file(fd, private=False)
                expected = _identity(fd)
            finally:
                os.close(fd)
            info = os.stat(member, dir_fd=directory_fd, follow_symlinks=False)
            if (info.st_dev, info.st_ino) == expected:
                os.unlink(member, dir_fd=directory_fd)
        except OSError:  # noqa: PERF203 -- individual cleanup failures are independent
            # A concurrent cleanup or unsafe replacement cannot justify touching
            # anything else. The directory remains if an unknown object exists.
            continue
    if not os.listdir(directory_fd):
        os.rmdir(name, dir_fd=root_fd)


def _cleanup_expired(
    root_fd: int, now: datetime, *, exclude: ArtifactId | None = None
) -> None:
    """Lazily remove only fully verified expired UUID bundles; leave unknowns."""
    try:
        names = os.listdir(root_fd)
    except OSError:
        return
    for name in names:
        parsed = parse_artifact_id(name)
        if isinstance(parsed, InvalidRequest) or parsed == exclude:
            continue
        try:
            fd = _open_directory(root_fd, name)
            try:
                bundle = _read_bundle(fd, parsed)
                if isinstance(bundle, StoredBundle) and is_expired(
                    bundle.manifest, now
                ):
                    _remove_owned(root_fd, name, fd, ready=True)
            finally:
                os.close(fd)
        except OSError:
            continue


class StagedBundle:
    """Opaque operation-owned export stage; only its trusted output stem is public."""

    __slots__ = (
        "_active",
        "_artifact_id",
        "_directory_fd",
        "_output_stem",
        "_published",
        "_root_fd",
        "_store",
    )

    def __init__(
        self,
        key: object,
        store: "ArtifactStore",
        artifact_id: ArtifactId,
        root_fd: int,
        directory_fd: int,
        output_stem: Path,
    ) -> None:
        """Permit construction only inside the store's exclusive reservation path."""
        if key is not _CONSTRUCTION_KEY:
            raise TypeError("Artifact stages are created by their store")
        self._store = store
        self._artifact_id = artifact_id
        self._root_fd = root_fd
        self._directory_fd = directory_fd
        self._output_stem = output_stem
        self._active = True
        self._published = False

    @property
    def output_stem(self) -> Path:
        """Return the private fixed stem supplied only to the trusted exporter."""
        return self._output_stem


class ArtifactStore:
    """Configuration-bound local-user storage; requests cannot select its root."""

    def __init__(
        self, key: object, root: Path, identity: tuple[int, int] | None
    ) -> None:
        """Construct only through configure_store; keep lazy initialization bound."""
        if key is not _CONSTRUCTION_KEY:
            raise TypeError(
                "Artifact stores are created by configuration wiring"
            )
        self._root = root
        self._root_identity = identity
        self._initialization_lock = RLock()

    def _open_root(self) -> int:
        """Initialize lazily then reject a replaced root at every later effect."""
        with self._initialization_lock:
            fd = _walk_root(self._root, create=True)
            assert fd is not None
            opened = _identity(fd)
            if (
                self._root_identity is not None
                and opened != self._root_identity
            ):
                os.close(fd)
                raise OSError("Artifact root was replaced")
            self._root_identity = opened
            return fd

    def staging(self) -> AbstractContextManager[StagedBundle]:
        """Reserve a unique private export stage, cleaning it on exit unless ready.

        Infrastructure failures during entry raise a safe OSError. Publication
        refusals themselves are returned by publish, never thrown.
        """
        return self._staging()

    @contextmanager
    def _staging(self) -> Iterator[StagedBundle]:
        """Own root/directory descriptors across export, commit and cancellation."""
        try:
            root_fd = self._open_root()
        except OSError:
            raise OSError("Artifact storage is unavailable") from None
        directory_fd = None
        try:
            for _ in range(32):
                artifact_id = ArtifactId(uuid4().hex)
                try:
                    os.mkdir(artifact_id.value, mode=0o700, dir_fd=root_fd)
                except FileExistsError:
                    continue
                directory_fd = _open_directory(root_fd, artifact_id.value)
                break
            if directory_fd is None:
                raise OSError("Artifact identity reservation failed")
            stage = StagedBundle(
                _CONSTRUCTION_KEY,
                self,
                artifact_id,
                root_fd,
                directory_fd,
                self._root / artifact_id.value / "plot",
            )
            try:
                yield stage
            finally:
                if not stage._published:
                    with suppress(OSError):
                        _remove_owned(
                            root_fd,
                            artifact_id.value,
                            directory_fd,
                            ready=False,
                        )
                stage._active = False
        finally:
            if directory_fd is not None:
                os.close(directory_fd)
            os.close(root_fd)

    def _stage_is_current(self, stage: StagedBundle) -> bool:
        """Check store ownership and opened directory/root identities at publication."""
        if (
            not isinstance(stage, StagedBundle)
            or stage._store is not self
            or not stage._active
            or stage._published
        ):
            return False
        root_fd = self._open_root()
        try:
            fd = _open_directory(root_fd, stage._artifact_id.value)
            try:
                return _identity(fd) == _identity(
                    stage._directory_fd
                ) and _identity(root_fd) == _identity(stage._root_fd)
            finally:
                os.close(fd)
        finally:
            os.close(root_fd)

    def publish(
        self,
        stage: StagedBundle,
        source: bytes,
        report: dict[str, Any],
        now: datetime,
    ) -> StoredBundle | StoreFailure:
        """Commit exact source/report and trusted exports once, with a final marker.

        Expected encoding, size, staging and I/O refusals are safe frozen values.
        UTC time is injected after execution; publication never renews an old ID.
        """
        _require_utc(now)
        try:
            if not self._stage_is_current(stage):
                return PublicationError()
            if not isinstance(source, bytes):
                return PublicationError()
            if len(source) > MAX_SOURCE_BYTES:
                return ArtifactTooLarge(len(source), MAX_SOURCE_BYTES)
            source.decode("utf-8")
            report_bytes = json.dumps(
                report,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
            if len(report_bytes) + len(source) > MAX_BUNDLE_BYTES:
                return ArtifactTooLarge(len(report_bytes) + len(source))
            checks = report.get("failed_checks")
            if not isinstance(checks, list):
                return PublicationError()
            summary = ValidationSummary(
                report["status"], report["validation_complete"], tuple(checks)
            )
            contents = {
                ArtifactMember.SOURCE: source,
                ArtifactMember.REPORT: report_bytes,
            }
            for member in (ArtifactMember.PNG, ArtifactMember.PDF):
                data = _read_file(
                    stage._directory_fd,
                    member.value,
                    MAX_BUNDLE_BYTES - sum(map(len, contents.values())),
                    private=False,
                )
                if isinstance(data, ArtifactTooLarge):
                    return ArtifactTooLarge(
                        data.size_bytes + sum(map(len, contents.values()))
                    )
                contents[member] = data
            manifest = Manifest(
                stage._artifact_id,
                now,
                now + RETENTION,
                tuple(
                    FileEntry(
                        member,
                        len(contents[member]),
                        hashlib.sha256(contents[member]).hexdigest(),
                    )
                    for member in DATA_MEMBERS
                ),
                summary,
            )
            manifest_bytes = manifest.to_bytes()
            total = len(manifest_bytes) + sum(map(len, contents.values()))
            if total > MAX_BUNDLE_BYTES:
                return ArtifactTooLarge(total)
            if isinstance(parse_manifest(manifest_bytes), CorruptArtifact):
                return PublicationError()
            if set(os.listdir(stage._directory_fd)) != {
                ArtifactMember.PNG.value,
                ArtifactMember.PDF.value,
            }:
                return PublicationError()
            contents[ArtifactMember.MANIFEST] = manifest_bytes
            result = StoredBundle(manifest, contents)
            _write_file(
                stage._directory_fd, ArtifactMember.SOURCE.value, source
            )
            _write_file(
                stage._directory_fd, ArtifactMember.REPORT.value, report_bytes
            )
            _write_file(stage._directory_fd, _TEMP_MANIFEST, manifest_bytes)
            # All data is complete before the final name becomes a commit marker.
            os.rename(
                _TEMP_MANIFEST,
                ArtifactMember.MANIFEST.value,
                src_dir_fd=stage._directory_fd,
                dst_dir_fd=stage._directory_fd,
            )
            os.fsync(stage._directory_fd)
            os.fsync(stage._root_fd)
            stage._published = True
            with suppress(OSError):
                _cleanup_expired(
                    stage._root_fd, now, exclude=stage._artifact_id
                )
            return result
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            UnicodeError,
            OverflowError,
            RecursionError,
        ):
            if (
                isinstance(stage, StagedBundle)
                and stage._store is self
                and stage._active
                and not stage._published
            ):
                with suppress(OSError):
                    _remove_owned(
                        stage._root_fd,
                        stage._artifact_id.value,
                        stage._directory_fd,
                        ready=False,
                    )
            return PublicationError()

    def load(
        self, artifact_id: ArtifactId, now: datetime
    ) -> StoredBundle | StoreFailure:
        """Read a complete verified bundle through bound handles and immutable TTL."""
        _require_utc(now)
        if not isinstance(artifact_id, ArtifactId):
            raise TypeError("Expected a parsed artifact identity")
        try:
            root_fd = self._open_root()
            try:
                try:
                    fd = _open_directory(root_fd, artifact_id.value)
                except FileNotFoundError:
                    with suppress(OSError):
                        _cleanup_expired(root_fd, now)
                    return NotFound()
                try:
                    result = _read_bundle(fd, artifact_id)
                    if isinstance(result, StoredBundle) and is_expired(
                        result.manifest, now
                    ):
                        expiry = result.manifest.expires_at
                        with suppress(OSError):
                            _remove_owned(
                                root_fd, artifact_id.value, fd, ready=True
                            )
                        return Expired(expiry)
                finally:
                    os.close(fd)
                with suppress(OSError):
                    _cleanup_expired(root_fd, now, exclude=artifact_id)
                return result
            finally:
                os.close(root_fd)
        except (OSError, ValueError):
            return CorruptArtifact()

    def read_member(
        self, artifact_id: ArtifactId, member: ArtifactMember, now: datetime
    ) -> ArtifactBytes | StoreFailure:
        """Return one static-MIME member only after complete bundle verification."""
        if not isinstance(member, ArtifactMember):
            raise TypeError("Expected a literal artifact member")
        result = self.load(artifact_id, now)
        if isinstance(result, StoredBundle):
            return ArtifactBytes(result.contents[member], member.mime_type)
        return result


def configure_store(
    configured_root: str | None,
) -> ArtifactStore | ConfigurationError:
    """Resolve once and authorize an absolute private root without creating it.

    Only server configuration wiring calls this constructor in production.
    Symlinks at any existing component and nonprivate existing roots are refused.
    """
    try:
        if not _descriptor_operations_available():
            return ConfigurationError()
        if configured_root is None:
            root = Path.home() / ".cache" / "dartwork-mpl" / "artifacts"
        elif (
            not isinstance(configured_root, str)
            or not configured_root
            or not Path(configured_root).is_absolute()
        ):
            return ConfigurationError()
        else:
            root = Path(configured_root)
        if ".." in root.parts or "\x00" in str(root):
            return ConfigurationError()
        fd = _walk_root(root, create=False)
        identity = None
        if fd is not None:
            try:
                identity = _identity(fd)
            finally:
                os.close(fd)
        # No symlink components survived the opened-object walk; absolute lexical
        # normalization is enough and cannot silently follow a later replacement.
        return ArtifactStore(_CONSTRUCTION_KEY, root, identity)
    except (OSError, ValueError, RuntimeError):
        return ConfigurationError()
