"""Private durable bundles, accessed only through a configuration-bound handle.

Opened descriptors, literal member names and UUID reservations confine effects.
The local OS user still owns the files and trusted export receives a pathname;
this is not a sandbox for code executing with that same user's privileges.
The descriptor-level primitives live in ``_store_fs``; tests patch the names
this module imports from it (``_write_file``, ``_root_ancestry``) here.
"""

import errno
import hashlib
import json
import os
import stat
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from types import MappingProxyType
from typing import Any, TypeAlias
from uuid import uuid4

from ._store_fs import (
    _FILE_FLAGS,
    _check_file,
    _descriptor_operations_available,
    _identity,
    _open_directory,
    _read_file,
    _restore_isolated,
    _root_ancestry,
    _roots_overlap,
    _UnsafeArtifactObject,
    _walk_root,
    _write_file,
)
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

#: Read-only commit evidence; only NotFound proves an observed marker's absence.
CommitObservation: TypeAlias = (
    Manifest | NotFound | CorruptArtifact | PublicationError
)


def _observation_error(error: OSError) -> CorruptArtifact | PublicationError:
    """Report unsafe stored objects as corrupt, operational uncertainty as error."""
    if isinstance(error, _UnsafeArtifactObject) or error.errno in {
        errno.ELOOP,
        errno.ENOTDIR,
    }:
        return CorruptArtifact()
    return PublicationError()


def _observe_manifest(
    root_fd: int, artifact_id: ArtifactId
) -> CommitObservation:
    """Read only a bounded commit marker under one pinned private directory.

    A verified missing directory/marker is NotFound; unsafe or invalid metadata
    is CorruptArtifact. I/O failure or a directory replaced during observation
    is PublicationError. No member payload, expiry cleanup or write is involved.
    """
    try:
        directory_fd = _open_directory(root_fd, artifact_id.value)
    except FileNotFoundError:
        return NotFound()
    except OSError as error:
        return _observation_error(error)
    try:
        result: CommitObservation
        try:
            raw = _read_file(
                directory_fd, ArtifactMember.MANIFEST.value, MAX_MANIFEST_BYTES
            )
            result = (
                CorruptArtifact()
                if isinstance(raw, ArtifactTooLarge)
                else parse_manifest(raw)
            )
            if (
                isinstance(result, Manifest)
                and result.artifact_id != artifact_id
            ):
                result = CorruptArtifact()
        except FileNotFoundError:
            result = NotFound()
        except OSError as error:
            result = _observation_error(error)
        # Do not mistake a detached directory's marker/miss for the current name.
        try:
            current_fd = _open_directory(root_fd, artifact_id.value)
            try:
                if _identity(current_fd) != _identity(directory_fd):
                    return PublicationError()
            finally:
                os.close(current_fd)
        except OSError:
            return PublicationError()
        return result
    finally:
        os.close(directory_fd)


def _read_bundle(
    directory_fd: int,
    artifact_id: ArtifactId,
    *,
    evidence: dict[str, tuple[int, int]] | None = None,
) -> StoredBundle | StoreFailure:
    """Verify a complete bundle and optionally capture identities for safe expiry."""
    try:
        raw = _read_file(
            directory_fd,
            ArtifactMember.MANIFEST.value,
            MAX_MANIFEST_BYTES,
            evidence=evidence,
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
            evidence=evidence,
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


@dataclass(frozen=True)
class _CleanupSnapshot:
    """Borrowed opened directory and immutable evidence from complete validation."""

    directory_fd: int
    bundle: StoredBundle
    file_identities: Mapping[str, tuple[int, int]]

    def __post_init__(self) -> None:
        """Keep the captured identity map stable across external mutations."""
        object.__setattr__(
            self,
            "file_identities",
            MappingProxyType(dict(self.file_identities)),
        )


def _remove_expired(
    root_fd: int, name: str, snapshot: _CleanupSnapshot
) -> None:
    """Isolate all candidates atomically, verify actual objects, then delete.

    The verified snapshot carries both bytes and opened inode identities. No
    public member pathname is unlinked. Unknown or substituted candidates are
    restored without overwriting new names, or retained in private quarantine.
    Quarantine is operation-owned and excluded from normal UUID discovery; this
    does not sandbox arbitrary same-user mutation inside private operation state.
    """
    directory_fd = snapshot.directory_fd
    verified = snapshot.bundle
    evidence = snapshot.file_identities
    quarantine = ".cleanup-" + uuid4().hex
    os.mkdir(quarantine, mode=0o700, dir_fd=root_fd)
    quarantine_fd = _open_directory(root_fd, quarantine)
    isolated: set[str] = set()
    try:
        for member in ArtifactMember:
            os.rename(
                member.value,
                member.value,
                src_dir_fd=directory_fd,
                dst_dir_fd=quarantine_fd,
            )
            isolated.add(member.value)
        for member in ArtifactMember:
            expected = verified.contents[member]
            actual_evidence: dict[str, tuple[int, int]] = {}
            data = _read_file(
                quarantine_fd,
                member.value,
                len(expected),
                evidence=actual_evidence,
            )
            if (
                data != expected
                or actual_evidence.get(member.value) != evidence[member.value]
            ):
                return
        if os.listdir(directory_fd):
            return
        # Isolate the empty directory as well: a new public UUID entry installed
        # after this rename must never be the target of our final rmdir.
        os.rename(name, ".bundle", src_dir_fd=root_fd, dst_dir_fd=quarantine_fd)
        bundle_fd = _open_directory(quarantine_fd, ".bundle")
        try:
            if _identity(bundle_fd) != _identity(directory_fd) or os.listdir(
                bundle_fd
            ):
                return
        finally:
            os.close(bundle_fd)
        for member in ArtifactMember:
            os.unlink(member.value, dir_fd=quarantine_fd)
            isolated.remove(member.value)
        os.rmdir(".bundle", dir_fd=quarantine_fd)
    finally:
        _restore_isolated(quarantine_fd, directory_fd, isolated)
        try:
            empty = not os.listdir(quarantine_fd)
        finally:
            os.close(quarantine_fd)
        if empty:
            os.rmdir(quarantine, dir_fd=root_fd)


def _remove_owned(
    root_fd: int, name: str, directory: int | _CleanupSnapshot, *, ready: bool
) -> None:
    """Remove only literal known regular members of the pinned owned directory.

    Unexpected entries and links are preserved. No recursive deletion and no
    deletion by a user-provided pathname occurs, even for crash leftovers.
    """
    directory_fd = (
        directory.directory_fd
        if isinstance(directory, _CleanupSnapshot)
        else directory
    )
    current = _open_directory(root_fd, name)
    try:
        if _identity(current) != _identity(directory_fd):
            return
    finally:
        os.close(current)
    if ready:
        if isinstance(directory, _CleanupSnapshot):
            _remove_expired(root_fd, name, directory)
        return
    names = set(os.listdir(directory_fd))
    allowed = _READY_NAMES | {_TEMP_MANIFEST}
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
        except OSError:
            # A concurrent cleanup or unsafe replacement cannot justify touching
            # anything else. The directory remains if an unknown object exists.
            continue
    if not os.listdir(directory_fd):
        os.rmdir(name, dir_fd=root_fd)


def _cleanup_expired(
    root_fd: int, now: datetime, *, exclude: ArtifactId | None = None
) -> None:
    """Read only metadata for live bundles; fully reverify expiry before removal.

    The bounded, no-follow manifest preflight only selects candidates. Removal
    still requires complete bundle validation and its own expiry/identity checks;
    invalid or unsafe preflight metadata is preserved without reading payloads.
    """
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
                raw = _read_file(
                    fd, ArtifactMember.MANIFEST.value, MAX_MANIFEST_BYTES
                )
                if isinstance(raw, ArtifactTooLarge):
                    continue
                manifest = parse_manifest(raw)
                if (
                    isinstance(manifest, CorruptArtifact)
                    or manifest.artifact_id != parsed
                    or not is_expired(manifest, now)
                ):
                    continue
                evidence: dict[str, tuple[int, int]] = {}
                bundle = _read_bundle(fd, parsed, evidence=evidence)
                if isinstance(bundle, StoredBundle) and is_expired(
                    bundle.manifest, now
                ):
                    _remove_owned(
                        root_fd,
                        name,
                        _CleanupSnapshot(fd, bundle, evidence),
                        ready=True,
                    )
            finally:
                os.close(fd)
        except OSError:
            continue


class StagedBundle:
    """Opaque export ownership with a read-only ID and trusted exporter stem."""

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
    def artifact_id(self) -> ArtifactId:
        """Return the reserved immutable ID, still usable after stage exit.

        This identifies an attempted publication; it does not prove a commit or
        expose the stage's ownership token, descriptors or private directory.
        """
        return self._artifact_id

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

    def _open_observation_root(self) -> int:
        """Open/bind an existing private root without mkdir or accepting replacement.

        Missing, unsafe and replaced roots raise OSError, never a safe miss.
        The initialization lock shares identity pinning with legacy staging.
        """
        with self._initialization_lock:
            fd = _walk_root(self._root, create=False)
            if fd is None:
                raise OSError("Artifact root is unavailable")
            try:
                opened = _identity(fd)
                if (
                    self._root_identity is not None
                    and opened != self._root_identity
                ):
                    raise OSError("Artifact root was replaced")
                self._root_identity = opened
                return fd
            except OSError:
                os.close(fd)
                raise

    def observe_commit(self, artifact_id: ArtifactId) -> CommitObservation:
        """Observe a commit marker without creating, cleaning or loading bundles.

        Call after artifact-stage exit when settling paired input publication.
        Read at most 512 KiB plus one overrun byte, verify the requested ID and
        v1 timestamp invariants, and return the parsed Manifest even if expired.
        The caller compares its expected creation/expiry instants. This does not
        verify payloads or prove a failed fsync durable. A safe missing bundle or
        marker is NotFound; invalid/unsafe metadata is CorruptArtifact; missing,
        replaced or unobservable roots and operational failures are
        PublicationError. Ambiguous outcomes never authorize input rollback.
        """
        if not isinstance(artifact_id, ArtifactId):
            raise TypeError("Expected a parsed artifact identity")
        try:
            root_fd = self._open_observation_root()
            try:
                result = _observe_manifest(root_fd, artifact_id)
                current_fd = self._open_observation_root()
                try:
                    if _identity(current_fd) != _identity(root_fd):
                        return PublicationError()
                finally:
                    os.close(current_fd)
                return result
            finally:
                os.close(root_fd)
        except OSError:
            return PublicationError()

    def check_input_roots(
        self, storage_dir: Path, copy_roots: tuple[Path, ...]
    ) -> ConfigurationError | None:
        """Read-only overlap check for operator-supplied input policy roots.

        Refuse storage equal to, above or below the artifact root or any copy
        root, using no-follow ancestor handles and device/inode identities.
        Storage and copy roots must already exist; unresolved input roots return
        ConfigurationError. An unpinned absent artifact root remains lazy when
        its observed ancestors prove separation from the existing storage.
        Nothing is created, and copy roots may overlap one another.
        A pinned artifact root must still be present and unchanged. This only
        checks separation, not the input grant's ownership/mode policy, local
        filesystem/datasets preconditions or authorization to copy any file.
        Unsafe paths and observation failures return a path-free refusal.
        """
        try:
            with self._initialization_lock:
                fd = _walk_root(self._root, create=False)
                expected_identity = None
                if fd is None:
                    if self._root_identity is not None:
                        return ConfigurationError()
                else:
                    try:
                        expected_identity = _identity(fd)
                        if (
                            self._root_identity is not None
                            and expected_identity != self._root_identity
                        ):
                            return ConfigurationError()
                    finally:
                        os.close(fd)
                storage = _root_ancestry(storage_dir)
                if _roots_overlap(
                    storage, _root_ancestry(self._root, allow_missing=True)
                ):
                    return ConfigurationError()
                for root in copy_roots:
                    if _roots_overlap(storage, _root_ancestry(root)):
                        return ConfigurationError()
                current_fd = _walk_root(self._root, create=False)
                if current_fd is None:
                    if expected_identity is not None:
                        return ConfigurationError()
                else:
                    try:
                        if _identity(current_fd) != expected_identity:
                            return ConfigurationError()
                    finally:
                        os.close(current_fd)
            return None
        except (OSError, ValueError):
            return ConfigurationError()

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
                    evidence: dict[str, tuple[int, int]] = {}
                    result = _read_bundle(fd, artifact_id, evidence=evidence)
                    if isinstance(result, StoredBundle) and is_expired(
                        result.manifest, now
                    ):
                        expiry = result.manifest.expires_at
                        with suppress(OSError):
                            _remove_owned(
                                root_fd,
                                artifact_id.value,
                                _CleanupSnapshot(fd, result, evidence),
                                ready=True,
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


def _unusable_root_reason(root: Path, error: Exception) -> str:
    """Name what the operator must fix in a root the opened-object walk refused.

    Diagnosis only: the refusal is already decided, and this no-follow ``lstat``
    pass merely words it, naming the first symlink, non-directory or nonprivate
    final component. A concurrent change can make the sentence stale, never
    admit a root. Paths are ``repr``-quoted so the reason stays one line.
    """
    final = len(root.parts) - 1
    for index in range(len(root.parts)):
        prefix = Path(*root.parts[: index + 1])
        # The root itself, or the component of it that must be fixed.
        where = (
            f"Artifact root {str(root)!r}"
            if index == final
            else f"Component {str(prefix)!r} of artifact root {str(root)!r}"
        )
        try:
            info = os.lstat(prefix)
        except FileNotFoundError:
            break
        except OSError as failure:
            return (
                f"Cannot inspect {str(prefix)!r} inside {str(prefix.parent)!r} "
                f"({failure.strerror}); the server user needs read and search "
                f"permission on every existing directory of {str(root)!r}, or "
                "set DARTWORK_MPL_ARTIFACT_DIR elsewhere."
            )
        if stat.S_ISLNK(info.st_mode):
            return (
                f"{where} is a symbolic link; symlinks are refused, so set "
                "DARTWORK_MPL_ARTIFACT_DIR to the resolved real path instead."
            )
        if not stat.S_ISDIR(info.st_mode):
            return (
                f"{where} exists but is not a directory; set "
                "DARTWORK_MPL_ARTIFACT_DIR to a directory path."
            )
        if index == final and (
            info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700
        ):
            fix = (
                "run 'chmod 700' on it"
                if info.st_uid == os.geteuid()
                else f"chown it to uid {os.geteuid()} and run 'chmod 700'"
            )
            return (
                f"Existing artifact root {str(root)!r} is not private: it has "
                f"owner uid {info.st_uid} and mode "
                f"{stat.S_IMODE(info.st_mode):04o}, but must be owned by the "
                f"server user (uid {os.geteuid()}) with mode 0700; {fix}, or "
                "set DARTWORK_MPL_ARTIFACT_DIR elsewhere."
            )
    return (
        f"Artifact root {str(root)!r} could not be opened ({str(error)!r}); "
        "the server user needs read and search permission on every existing "
        "directory of it, or set DARTWORK_MPL_ARTIFACT_DIR elsewhere."
    )


def configure_store(
    configured_root: str | None,
) -> ArtifactStore | ConfigurationError:
    """Resolve once and authorize an absolute private root without creating it.

    Only server configuration wiring calls this constructor in production.
    Symlinks at any existing component and nonprivate existing roots are refused.
    Each refusal's ``reason`` tells the operator what to change; the wire keeps
    the fixed configuration_error message.
    """
    try:
        if not _descriptor_operations_available():
            return ConfigurationError(
                reason="This Python/OS lacks the no-follow directory-descriptor "
                "operations artifact storage needs (O_NOFOLLOW, O_DIRECTORY, "
                "dir_fd opens and hard links); run the server on Linux or "
                "macOS to enable the artifact tools."
            )
        if configured_root is None:
            setting = (
                "The default artifact root (DARTWORK_MPL_ARTIFACT_DIR unset)"
            )
            try:
                root = Path.home() / ".cache" / "dartwork-mpl" / "artifacts"
            except RuntimeError:
                return ConfigurationError(
                    reason="The home directory for the default artifact root "
                    "could not be determined; set DARTWORK_MPL_ARTIFACT_DIR to "
                    "an absolute directory path."
                )
            if not root.is_absolute():
                return ConfigurationError(
                    reason=f"The default artifact root {str(root)!r} is "
                    "relative because HOME is; set HOME or "
                    "DARTWORK_MPL_ARTIFACT_DIR to an absolute path."
                )
        elif not isinstance(configured_root, str):
            return ConfigurationError(
                reason="The artifact root must be a str path or None; got "
                f"{type(configured_root).__name__!r}."
            )
        elif not configured_root:
            return ConfigurationError(
                reason="DARTWORK_MPL_ARTIFACT_DIR is set but empty; set it to "
                "an absolute directory path, or unset it to use "
                "~/.cache/dartwork-mpl/artifacts."
            )
        elif not Path(configured_root).is_absolute():
            return ConfigurationError(
                reason="DARTWORK_MPL_ARTIFACT_DIR must be an absolute path; "
                f"got the relative path {configured_root!r}."
            )
        else:
            setting = "DARTWORK_MPL_ARTIFACT_DIR"
            root = Path(configured_root)
        if ".." in root.parts:
            return ConfigurationError(
                reason=f"{setting} must not contain '..' components; got "
                f"{str(root)!r}. Write the path without parent references."
            )
        if "\x00" in str(root):
            return ConfigurationError(
                reason=f"{setting} must not contain a NUL byte; got "
                f"{str(root)!r}."
            )
        try:
            fd = _walk_root(root, create=False)
            identity = None
            if fd is not None:
                try:
                    identity = _identity(fd)
                finally:
                    os.close(fd)
        except (OSError, ValueError, RuntimeError) as error:
            return ConfigurationError(reason=_unusable_root_reason(root, error))
        # No symlink components survived the opened-object walk; absolute lexical
        # normalization is enough and cannot silently follow a later replacement.
        return ArtifactStore(_CONSTRUCTION_KEY, root, identity)
    except (OSError, ValueError, RuntimeError) as error:
        return ConfigurationError(
            reason="Artifact storage configuration failed unexpectedly "
            f"({type(error).__name__}: {str(error)!r})."
        )
