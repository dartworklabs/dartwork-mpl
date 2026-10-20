"""Serial, grant-backed independent input sets with conservative crash recovery.

Transactions hold the store lock through synchronous worker reap and explicit
paired settlement. Consumers settle only after their artifact-stage exits; this
module never interprets artifact storage or the grant's private fields.
"""

from __future__ import annotations

import os
import stat
import threading
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import TypeAlias

from . import input_cleanup as fs
from .input_access import InputGrant, OwnedInputFD
from .input_io import CheckJob, CopyJob, check_copies, copy_inputs
from .input_policy import (
    MAX_INPUT_METADATA_BYTES,
    MAX_INPUT_PAYLOAD_BYTES,
    MAX_INPUT_STORE_BYTES,
    CopyInput,
    InputFile,
    InputMetadata,
    RetainedInput,
    Revision,
    can_reserve,
    parse_input_metadata,
)
from .policy import (
    RETENTION,
    ArtifactId,
    ConfigurationError,
    CorruptArtifact,
    Expired,
    InvalidRequest,
    Manifest,
    NotFound,
    PublicationError,
    _require_utc,
)
from .store import CommitObservation

__all__ = [
    "AbsentInputs",
    "CommitObserver",
    "DeletedInputs",
    "InputFailure",
    "InputStage",
    "InputStore",
    "InputTransaction",
]

CommitObserver: TypeAlias = Callable[[ArtifactId], CommitObservation]
InputFailure: TypeAlias = (
    InvalidRequest
    | ConfigurationError
    | NotFound
    | Expired
    | CorruptArtifact
    | PublicationError
)
_RESERVATION = MAX_INPUT_PAYLOAD_BYTES + MAX_INPUT_METADATA_BYTES + 1
_KEY = object()


@dataclass(frozen=True)
class DeletedInputs:
    """Only this set was revoked/removed after the final root durability barrier."""

    artifact_id: ArtifactId

    def __post_init__(self) -> None:
        """Require the exact parsed identity rather than a path or arbitrary string."""
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValueError("Expected a parsed input-set identity")


@dataclass(frozen=True)
class AbsentInputs:
    """Both namespaces were safely absent after the root durability barrier."""

    artifact_id: ArtifactId

    def __post_init__(self) -> None:
        """Require a parsed identity whose absence was established by the store."""
        if not isinstance(self.artifact_id, ArtifactId):
            raise ValueError("Expected a parsed input-set identity")


@dataclass(frozen=True)
class _Copied:
    """Measured bytes still require a complete post-execution worker check."""


@dataclass(frozen=True)
class _Checked:
    """Postchecked object signatures prevent mutation before input publication."""

    signatures: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class _Rejected:
    """The sole postcheck pass was consumed; these copies cannot be published."""


@dataclass(frozen=True)
class _Committed:
    """Renamed input namespace remains counted even when root fsync fails."""

    metadata: InputMetadata
    signatures: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class _Settled:
    """The explicit post-artifact-stage observation resolved this call's stage."""


@dataclass(frozen=True)
class _Closed:
    """Descriptor ownership ended; the stage is no longer usable by a transaction."""


class InputStage:
    """Store-created opaque stage; public mapping/files are immutable observations."""

    def __init__(
        self,
        key: object,
        tx: InputTransaction,
        artifact_id: ArtifactId,
        folder: int,
        name: str,
    ) -> None:
        """Only the owning transaction may construct and mutate stage resources."""
        if key is not _KEY:
            raise ValueError("Input stages require a transaction")
        self._tx = tx
        self._id = artifact_id
        self._folder = folder
        self._name = name
        self._fds: list[int] = []
        self._metadata_fd: int | None = None
        self._files: tuple[InputFile, ...] = ()
        self._mapping: Mapping[str, str] = MappingProxyType({})
        self._state: (
            _Copied | _Checked | _Rejected | _Committed | _Settled | _Closed
        ) = _Copied()

    @property
    def execution_inputs(self) -> Mapping[str, str]:
        """Return private execution paths only; these strings confer no authority."""
        return self._mapping

    @property
    def files(self) -> tuple[InputFile, ...]:
        """Return the immutable measured name/hash/size records from the copy pass."""
        return self._files


def _namespace(name: str) -> tuple[ArtifactId, bool] | None:
    """Recognize exact owned pending/committed names without normalization."""
    pending = name.startswith(".pending-")
    try:
        return ArtifactId(name[9:] if pending else name), pending
    except ValueError:
        return None


def _metadata(
    folder: int, artifact_id: ArtifactId
) -> InputMetadata | CorruptArtifact:
    """Read bounded private metadata and verify its entry before/after parsing."""
    try:
        fd = fs.open_member(folder, "inputs.json")
        try:
            before = fs.signature(fd)
            raw = os.pread(fd, MAX_INPUT_METADATA_BYTES + 1, 0)
            fs.binding(folder, "inputs.json", fd)
            if before != fs.signature(fd):
                return CorruptArtifact()
            result = parse_input_metadata(raw)
            if (
                isinstance(result, InputMetadata)
                and result.artifact_id != artifact_id
            ):
                return CorruptArtifact()
            return result
        finally:
            os.close(fd)
    except OSError:
        return CorruptArtifact()


def _matches(metadata: InputMetadata, observed: Manifest) -> bool:
    """Compare only public paired-commit identity/time facts, never foreign files."""
    return (metadata.artifact_id, metadata.created_at, metadata.expires_at) == (
        observed.artifact_id,
        observed.created_at,
        observed.expires_at,
    )


class InputStore:
    """Startup-owned same-host lock and serial operations over a verified grant."""

    def __init__(
        self,
        key: object,
        grant: InputGrant,
        root: OwnedInputFD,
        lock: int,
        now: datetime,
    ) -> None:
        """Construction is private to open; close drains the serial lock first."""
        if key is not _KEY:
            raise ValueError("Input stores require startup authorization")
        self._grant = grant
        self._root = root
        self._lock_fd = lock
        self._serial = threading.RLock()
        self._active = False
        self._closed = False
        self._denied: set[ArtifactId] = set()
        self._now = now

    @classmethod
    def open(
        cls, grant: InputGrant, now: datetime
    ) -> InputStore | ConfigurationError:
        """Take one private persistent flock; preexisting storage is never created.

        Startup recovery removes only safe owned pending or valid own expiry.
        Unsafe residue remains counted and explicitly deletable after operator repair.
        """
        if not isinstance(grant, InputGrant):
            return ConfigurationError()
        root = grant.duplicate_storage()
        if not isinstance(root, OwnedInputFD):
            return root
        lock = None
        transferred = False
        try:
            import fcntl

            _require_utc(now)
            lock = fs.open_member(root.fd, ".lock", os.O_RDWR | os.O_CREAT)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fs.binding(root.fd, ".lock", lock)
            os.fsync(lock)
            os.fsync(root.fd)
            result = cls(_KEY, grant, root, lock, now)
            result.maintain(now)
            verified = result._authority()
            if not isinstance(verified, OwnedInputFD):
                raise OSError("Storage authority changed during startup")
            verified.close()
            transferred = True
            return result
        except (OSError, ValueError, ImportError, AttributeError):
            return ConfigurationError()
        finally:
            if not transferred:
                if lock is not None:
                    os.close(lock)
                root.close()

    def _authority(self) -> OwnedInputFD | ConfigurationError:
        """Recheck only grant storage and the pinned lifetime lock binding."""
        if self._closed:
            return ConfigurationError()
        root = self._grant.duplicate_storage()
        if not isinstance(root, OwnedInputFD):
            return root
        try:
            if fs.identity(root.fd) != fs.identity(self._root.fd):
                raise OSError("Storage object changed")
            fs.binding(root.fd, ".lock", self._lock_fd)
            return root
        except OSError:
            root.close()
            return ConfigurationError()

    @contextmanager
    def _transaction(self) -> Iterator[InputTransaction]:
        """Hold serialization through owned worker completion and stage cleanup."""
        with self._serial:
            if self._active:
                raise RuntimeError("Input transactions cannot be nested")
            self._active = True
            tx = InputTransaction(_KEY, self, self._authority())
            try:
                yield tx
            finally:
                try:
                    tx._finish()
                finally:
                    self._active = False
                    if not self._closed:
                        excluded = () if tx._stage is None else (tx._stage._id,)
                        self._maintain(self._now, excluded)

    def transaction(self) -> AbstractContextManager[InputTransaction]:
        """Create a serial transaction; admission failures are returned by prepare."""
        return self._transaction()

    def _remove(
        self, root: int, artifact_id: ArtifactId, names: tuple[str, ...]
    ) -> bool:
        """Deny immediately, then remove only fixed namespaces with common barriers."""
        self._denied.add(artifact_id)
        removed = False
        for name in names:
            removed = fs.remove_set(root, name) or removed
        if any(not fs.absent(root, name) for name in names):
            raise OSError("Input namespace changed")
        authority = self._authority()
        if not isinstance(authority, OwnedInputFD):
            raise OSError("Storage authority changed")
        authority.close()
        return removed

    def delete(
        self, id: ArtifactId
    ) -> DeletedInputs | AbsentInputs | PublicationError:
        """Remove all six states without metadata/bundle/expiry prerequisites."""
        if not isinstance(id, ArtifactId):
            raise TypeError("Expected a parsed input-set identity")
        with self._serial:
            if self._active:
                return PublicationError()
            root = self._authority()
            if not isinstance(root, OwnedInputFD):
                return PublicationError()
            try:
                with root:
                    removed = self._remove(
                        root.fd, id, (id.value, ".pending-" + id.value)
                    )
                    return DeletedInputs(id) if removed else AbsentInputs(id)
            except OSError:
                return PublicationError()
            finally:
                self._maintain(self._now, (id,))

    def _usage(self, root: int) -> tuple[int, int]:
        """Count metadata/unknown/residue bytes before acquiring a new reservation.

        Unknown directories or unobservable objects charge the whole byte budget;
        never traverse foreign subdirectories or follow symlinks to estimate usage.
        """
        total, sets = os.fstat(self._lock_fd).st_size, 0
        for name in os.listdir(root):
            if name == ".lock":
                continue
            sets += 1
            info = os.stat(name, dir_fd=root, follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode):
                total += info.st_size
                continue
            if _namespace(name) is None:
                total += MAX_INPUT_STORE_BYTES
                continue
            try:
                folder = fs.open_set(root, name)
                try:
                    for entry in os.listdir(folder):
                        member = os.stat(
                            entry, dir_fd=folder, follow_symlinks=False
                        )
                        total += (
                            member.st_size
                            if not stat.S_ISDIR(member.st_mode)
                            else MAX_INPUT_STORE_BYTES
                        )
                    fs.binding(root, name, folder, True)
                finally:
                    os.close(folder)
            except OSError:
                total += MAX_INPUT_STORE_BYTES
        return total, sets

    def maintain(self, now: datetime) -> None | PublicationError:
        """After active work, clean owned pending/verified expiry, never bundle absence.

        The lifecycle supplies wall-clock instants (including its 60s tick).
        Per-operation maintenance uses the latest explicit admission/commit clock.
        """
        return self._maintain(now, ())

    def _maintain(
        self, now: datetime, excluded: tuple[ArtifactId, ...]
    ) -> None | PublicationError:
        """Skip only the current operation's target so failed cleanup stays visible."""
        _require_utc(now)
        with self._serial:
            if self._active:
                return PublicationError()
            self._now = now
            root = self._authority()
            if not isinstance(root, OwnedInputFD):
                return PublicationError()
            failed = False
            with root:
                try:
                    for name in os.listdir(root.fd):
                        parsed = _namespace(name)
                        if parsed is None:
                            continue
                        artifact_id, pending = parsed
                        if artifact_id in excluded:
                            continue
                        try:
                            folder = fs.open_set(root.fd, name)
                            try:
                                metadata = _metadata(folder, artifact_id)
                                fs.binding(root.fd, name, folder, True)
                            finally:
                                os.close(folder)
                            if pending or (
                                isinstance(metadata, InputMetadata)
                                and now >= metadata.expires_at
                            ):
                                self._remove(root.fd, artifact_id, (name,))
                        except OSError:
                            failed = True
                except OSError:
                    failed = True
            return PublicationError() if failed else None

    def close(self) -> None:
        """Wait for active transactions/workers, then close lifetime FDs once."""
        with self._serial:
            if self._active:
                raise RuntimeError(
                    "Close must occur after the transaction exits"
                )
            if not self._closed:
                self._closed = True
                os.close(self._lock_fd)
                self._root.close()


class InputTransaction:
    """Store-owned serial scope with one input-bearing call and its reservation."""

    def __init__(
        self,
        key: object,
        store: InputStore,
        root: OwnedInputFD | ConfigurationError,
    ) -> None:
        """Borrow startup authority via an owned per-operation root duplicate."""
        if key is not _KEY:
            raise ValueError("Input transactions require a store")
        self._store = store
        self._root = root
        self._stage: InputStage | None = None
        self._closed = False

    def _retained(
        self,
        spec: RetainedInput,
        at: datetime,
        observe: CommitObserver,
        pins: list[tuple[int, str, str, int]],
    ) -> OwnedInputFD | InputFailure:
        """Admit live committed bytes; one later copy/hash pass verifies content."""
        if not isinstance(self._root, OwnedInputFD):
            return self._root
        if spec.artifact_id in self._store._denied:
            return NotFound()
        try:
            folder = fs.open_set(self._root.fd, spec.artifact_id.value)
        except FileNotFoundError:
            return NotFound()
        except OSError:
            return CorruptArtifact()
        keep = False
        owned = None
        try:
            if not fs.absent(folder, ".revoked"):
                return NotFound()
            metadata = _metadata(folder, spec.artifact_id)
            if not isinstance(metadata, InputMetadata):
                return metadata
            if at >= metadata.expires_at:
                return Expired(metadata.expires_at)
            observed = observe(spec.artifact_id)
            if not isinstance(observed, Manifest):
                return observed
            if not _matches(metadata, observed):
                return CorruptArtifact()
            expected_names = {
                "inputs.json",
                *fs.PAYLOAD_NAMES[: len(metadata.files)],
            }
            if set(os.listdir(folder)) != expected_names:
                return CorruptArtifact()
            for index, file in enumerate(metadata.files):
                if file.name == spec.input_name:
                    if file.sha256 != spec.sha256:
                        return InvalidRequest(
                            "revision.inputs", "Input digest does not match."
                        )
                    name = fs.PAYLOAD_NAMES[index]
                    fd = fs.open_member(folder, name)
                    owned = OwnedInputFD(fd)
                    if os.fstat(fd).st_size != file.size_bytes:
                        return CorruptArtifact()
                    pins.append((folder, spec.artifact_id.value, name, fd))
                    keep = True
                    return owned
            return NotFound()
        except OSError:
            return CorruptArtifact()
        finally:
            if not keep:
                if owned is not None:
                    owned.close()
                os.close(folder)

    def _guard_stage(self, stage: InputStage) -> None:
        """Check stage ownership and every current name against its pinned object."""
        if (
            self._closed
            or stage is not self._stage
            or stage._tx is not self
            or isinstance(stage._state, (_Closed, _Settled))
            or not isinstance(self._root, OwnedInputFD)
        ):
            raise OSError("Inactive input stage")
        authority = self._store._authority()
        if not isinstance(authority, OwnedInputFD):
            raise OSError("Storage authority changed")
        authority.close()
        fs.binding(self._root.fd, stage._name, stage._folder, True)
        expected = set(fs.PAYLOAD_NAMES[: len(stage._fds)])
        if stage._metadata_fd is not None:
            expected.add("inputs.json")
            fs.binding(stage._folder, "inputs.json", stage._metadata_fd)
        if set(os.listdir(stage._folder)) != expected:
            raise OSError("Unsafe input stage namespace")
        for index, fd in enumerate(stage._fds):
            fs.binding(stage._folder, fs.PAYLOAD_NAMES[index], fd)
        if isinstance(
            stage._state, (_Checked, _Committed)
        ) and stage._state.signatures != tuple(
            fs.signature(fd) for fd in stage._fds
        ):
            raise OSError("Checked input copies changed")

    def prepare(
        self,
        id: ArtifactId,
        specs: tuple[CopyInput | RetainedInput, ...],
        admitted_at: datetime,
        observe: CommitObserver,
    ) -> InputStage | InputFailure:
        """Pin sources, reserve maximum space, then run exactly one 10s copy/hash.

        No maintenance precedes requested-set admission, preserving Expired.
        Retained sources receive private namespace/object guards around that pass.
        """
        if self._closed or not isinstance(self._root, OwnedInputFD):
            return ConfigurationError()
        self._store._now = admitted_at
        if self._stage is not None:
            return PublicationError()
        try:
            _require_utc(admitted_at)
            if not isinstance(id, ArtifactId):
                raise ValueError("Expected a parsed input-set identity")
            Revision(None, specs)
        except (ValueError, TypeError):
            return InvalidRequest(
                "revision.inputs", "Invalid input selections."
            )
        sources: list[OwnedInputFD] = []
        pins: list[tuple[int, str, str, int]] = []
        try:
            for spec in specs:
                opened = (
                    self._store._grant.open_copy(spec)
                    if isinstance(spec, CopyInput)
                    else self._retained(spec, admitted_at, observe, pins)
                )
                if not isinstance(opened, OwnedInputFD):
                    return opened
                sources.append(opened)
            used, sets = self._store._usage(self._root.fd)
            if not can_reserve(used, sets, _RESERVATION):
                return PublicationError()
            pending = ".pending-" + id.value
            if not fs.absent(self._root.fd, id.value) or not fs.absent(
                self._root.fd, pending
            ):
                return PublicationError()
            fs._fault("pending_create")
            os.mkdir(pending, 0o700, dir_fd=self._root.fd)
            folder = fs.open_set(self._root.fd, pending)
            stage = InputStage(_KEY, self, id, folder, pending)
            self._stage = stage
            fs._fault("pending_created")
            for index in range(len(specs)):
                stage._fds.append(
                    fs.open_member(
                        folder,
                        fs.PAYLOAD_NAMES[index],
                        os.O_RDWR | os.O_CREAT | os.O_EXCL,
                    )
                )
            for parent, name, member, fd in pins:
                fs.binding(self._root.fd, name, parent, True)
                fs.binding(parent, member, fd)
            before = [fs.signature(fd) for _, _, _, fd in pins]
            self._guard_stage(stage)
            result = copy_inputs(
                tuple(
                    CopyJob(src.fd, dst, spec.name, spec.sha256)
                    for src, dst, spec in zip(
                        sources, stage._fds, specs, strict=True
                    )
                ),
                10,
            )
            if not isinstance(result, tuple):
                return result
            for (parent, name, member, fd), prior in zip(
                pins, before, strict=True
            ):
                fs.binding(self._root.fd, name, parent, True)
                fs.binding(parent, member, fd)
                if fs.signature(fd) != prior:
                    raise OSError("Retained source changed")
            self._guard_stage(stage)
            stage._files = result
            stage._mapping = MappingProxyType(
                {
                    file.name: str(
                        self._store._grant.storage_path
                        / pending
                        / fs.PAYLOAD_NAMES[index]
                    )
                    for index, file in enumerate(result)
                }
            )
            return stage
        except OSError:
            return PublicationError()
        finally:
            for source in sources:
                source.close()
            for parent, _, _, _ in pins:
                os.close(parent)

    def check(self, stage: InputStage) -> None | InputFailure:
        """Postcheck all pinned copies once with the production 5s worker deadline."""
        try:
            self._guard_stage(stage)
            if not isinstance(stage._state, _Copied) or not stage.files:
                return PublicationError()
            before = tuple(fs.signature(fd) for fd in stage._fds)
            stage._state = _Rejected()
            result = check_copies(
                tuple(
                    CheckJob(fd, file)
                    for fd, file in zip(stage._fds, stage.files, strict=True)
                ),
                5,
            )
            if result is not None:
                return result
            self._guard_stage(stage)
            if before != tuple(fs.signature(fd) for fd in stage._fds):
                return InvalidRequest(
                    "revision.inputs", "Input copies changed."
                )
            stage._state = _Checked(
                tuple(fs.signature(fd) for fd in stage._fds)
            )
            return None
        except OSError:
            return PublicationError()

    def commit(
        self, stage: InputStage, created_at: datetime
    ) -> InputMetadata | InputFailure:
        """Fsync payload/metadata/set, rename, then root fsync using the shared clock."""
        try:
            self._guard_stage(stage)
            if not isinstance(stage._state, _Checked):
                return PublicationError()
            _require_utc(created_at)
            metadata = InputMetadata(
                stage._id, created_at, created_at + RETENTION, stage.files
            )
            raw = metadata.to_bytes()
            if len(raw) > MAX_INPUT_METADATA_BYTES:
                return PublicationError()
            for fd in stage._fds:
                fs._fault("input_payload_fsync")
                os.fsync(fd)
            meta_fd = fs.open_member(
                stage._folder,
                "inputs.json",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            )
            stage._metadata_fd = meta_fd
            fs._fault("input_metadata_write")
            fs.write_all(meta_fd, raw)
            fs._fault("input_metadata_fsync")
            os.fsync(meta_fd)
            fs.binding(stage._folder, "inputs.json", meta_fd)
            self._guard_stage(stage)
            fs._fault("input_set_fsync")
            os.fsync(stage._folder)
            assert isinstance(self._root, OwnedInputFD)
            if not fs.absent(self._root.fd, stage._id.value):
                return PublicationError()
            fs._fault("input_rename")
            os.rename(
                stage._name,
                stage._id.value,
                src_dir_fd=self._root.fd,
                dst_dir_fd=self._root.fd,
            )
            stage._name = stage._id.value
            stage._state = _Committed(metadata, stage._state.signatures)
            self._store._now = created_at
            self._guard_stage(stage)
            fs.binding(stage._folder, "inputs.json", meta_fd)
            fs._fault("input_root_fsync")
            os.fsync(self._root.fd)
            self._guard_stage(stage)
            return metadata
        except (OSError, ValueError, OverflowError):
            return PublicationError()

    def settle(
        self, stage: InputStage, observation: CommitObservation
    ) -> None | PublicationError:
        """After artifact-stage exit, preserve matching/ambiguous committed sets.

        Only this call's stage and a public safe NotFound observation permit
        rollback of a renamed set. No implicit observer runs at transaction exit.
        """
        try:
            self._guard_stage(stage)
            assert isinstance(self._root, OwnedInputFD)
            if (
                isinstance(stage._state, _Committed)
                and isinstance(observation, Manifest)
                and _matches(stage._state.metadata, observation)
            ):
                stage._state = _Settled()
                return None
            if isinstance(observation, NotFound):
                self._store._remove(self._root.fd, stage._id, (stage._name,))
                stage._state = _Settled()
                return None
            return PublicationError()
        except OSError:
            return PublicationError()

    def _finish(self) -> None:
        """Reap is already complete; remove pending only, then close owned pins."""
        if self._closed:
            return
        self._closed = True
        stage = self._stage
        try:
            if (
                stage is not None
                and isinstance(self._root, OwnedInputFD)
                and isinstance(stage._state, (_Copied, _Checked, _Rejected))
            ):
                with suppress(OSError):
                    self._store._denied.add(stage._id)
                    fs.binding(self._root.fd, stage._name, stage._folder, True)
                    self._store._remove(
                        self._root.fd, stage._id, (stage._name,)
                    )
        finally:
            if stage is not None:
                for fd in stage._fds:
                    os.close(fd)
                if stage._metadata_fd is not None:
                    os.close(stage._metadata_fd)
                os.close(stage._folder)
                stage._state = _Closed()
            if isinstance(self._root, OwnedInputFD):
                self._root.close()
