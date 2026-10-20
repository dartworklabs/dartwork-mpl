"""Startup-only operator authorization for descriptor-confined input retention.

Policies must name existing canonical roots. Local filesystem suitability and
storage outside datasets remain operator preconditions, not mount detection.
No import reads policy/environment or opens a descriptor. Only authorize_inputs
mints authority; requests select a root ID from that already-pinned grant.
"""

import os
import stat
import threading
from collections.abc import Callable
from pathlib import Path

from .input_policy import CopyInput
from .policy import ConfigurationError, InvalidRequest, _bounded_json

__all__ = ["InputGrant", "InputsDisabled", "OwnedInputFD", "authorize_inputs"]

_KEY = object()
_MAX_POLICY_BYTES = 16 * 1024


class InputsDisabled:
    """Startup had no policy; copying, retained reuse and deletion are denied."""


class OwnedInputFD:
    """An owned descriptor, closed idempotently by its context or close method.

    The integer remains available after close for diagnostics; never reuse it then.
    Callers must close per-call duplicates before closing the startup grant.
    """

    def __init__(self, fd: int) -> None:
        """Take ownership of an already-open descriptor without granting paths."""
        self.fd = fd
        self._closed = False

    def close(self) -> None:
        """Release this descriptor once; ownership must not be shared."""
        if not self._closed:
            self._closed = True
            os.close(self.fd)

    def __enter__(self) -> "OwnedInputFD":
        """Keep the owned FD alive for this context only."""
        if self._closed:
            raise ValueError("Input descriptor is closed")
        return self

    def __exit__(self, *args: object) -> None:
        """Close on success, failure and cancellation."""
        self.close()


def _identity(fd: int) -> tuple[int, int]:
    """Compare opened objects rather than path spelling or cached stat data."""
    info = os.fstat(fd)
    return info.st_dev, info.st_ino


def _canonical(raw: object) -> Path:
    """Reject aliases and noncanonical lexical paths without normalizing them."""
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise ValueError("Invalid policy path")
    path = Path(raw)
    if not path.is_absolute() or str(path) != raw or raw.startswith("//"):
        raise ValueError("Noncanonical policy path")
    if any(part in {".", ".."} for part in raw.split("/")[1:]):
        raise ValueError("Noncanonical policy path")
    return path


def _directory_info(fd: int, *, private: bool = False) -> None:
    """Require safe operator/root ancestry and exact private storage ownership."""
    info = os.fstat(fd)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid not in {0, os.geteuid()}
        or info.st_mode & 0o022
        or (
            private
            and (
                info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o700
            )
        )
    ):
        raise ValueError("Unsafe input directory")


def _open_directory(path: Path, *, private: bool = False) -> int:
    """Walk every existing ancestor with no-follow FD-relative opens."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        _directory_info(fd)
        for part in path.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
            _directory_info(fd)
        _directory_info(fd, private=private)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_policy(path: Path) -> dict[str, object]:
    """Read at most 16KiB plus one overrun byte from a verified policy object."""
    directory = _open_directory(path.parent)
    try:
        fd = os.open(
            path.name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY,
            dir_fd=directory,
        )
    finally:
        os.close(directory)
    try:
        before = os.fstat(fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or before.st_mode & 0o022
            or before.st_size > _MAX_POLICY_BYTES
        ):
            raise ValueError("Unsafe input policy")
        raw = bytearray()
        while len(raw) <= _MAX_POLICY_BYTES:
            chunk = os.read(fd, _MAX_POLICY_BYTES + 1 - len(raw))
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(fd)
        if before != after:
            # atime may move on read; only object/data/security fields matter.
            fields = (
                "st_dev",
                "st_ino",
                "st_uid",
                "st_mode",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
            )
            if any(
                getattr(before, name) != getattr(after, name) for name in fields
            ):
                raise ValueError("Input policy changed")
        payload = _bounded_json(
            bytes(raw),
            max_bytes=_MAX_POLICY_BYTES,
            max_depth=3,
            max_fields=_MAX_POLICY_BYTES,
        )
        if not isinstance(payload, dict) or payload.keys() != {
            "schema_version",
            "storage_dir",
            "copy_roots",
        }:
            raise ValueError("Invalid input policy shape")
        if (
            type(payload["schema_version"]) is not int
            or payload["schema_version"] != 1
        ):
            raise ValueError("Invalid input policy version")
        return payload
    finally:
        os.close(fd)


def _check_capabilities(fd: int) -> bool:
    """Probe required locks and explicit descriptor-transfer process support.

    The directory probe is not the store's startup lock. Task 4 owns that lock's
    file and lifetime. Optional mechanisms are imported only here, never globally.
    """
    try:
        import fcntl

        from .input_io import probe_worker

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return probe_worker(fd)
    except (ImportError, OSError, ValueError, NotImplementedError):
        return False


def _platform_supported() -> bool:
    """Fail retention closed while preserving imports/legacy on unsupported OSs."""
    return (
        os.name == "posix"
        and all(
            hasattr(os, name)
            for name in (
                "geteuid",
                "O_NOFOLLOW",
                "O_DIRECTORY",
                "O_NONBLOCK",
                "O_NOCTTY",
                "pread",
                "pwrite",
            )
        )
        and os.open in os.supports_dir_fd
    )


class InputGrant:
    """Sealed startup authority over pinned roots, not a path-string permission.

    Task 4 receives duplicate_storage() and storage_path only. The path is solely
    for execution's private name→path channel, never policy reload/authorization,
    report/error/locator construction, or interpretation of foreign storage.
    """

    def __init__(
        self,
        key: object,
        storage: tuple[Path, int],
        roots: dict[str, tuple[Path, int]],
    ) -> None:
        """Accept only the authorization constructor key and owned pinned FDs."""
        if key is not _KEY:
            raise ValueError("Input grants require startup authorization")
        self._storage = storage
        self._roots = roots
        self._lock = threading.RLock()
        self._closed = False

    @property
    def storage_path(self) -> Path:
        """Expose the canonical execution-only root; this value grants no access."""
        return self._storage[0]

    def _unchanged(self, pins: tuple[tuple[Path, int], ...]) -> bool:
        """Check only the pins this operation uses, preserving storage independence."""
        if self._closed:
            return False
        for path, pinned in pins:
            current = _open_directory(path, private=path == self._storage[0])
            try:
                if _identity(current) != _identity(pinned):
                    return False
            finally:
                os.close(current)
        return True

    def duplicate_storage(self) -> OwnedInputFD | ConfigurationError:
        """Duplicate storage authority independently of original-copy-root liveness.

        Task 4 uses this for retained/delete/maintenance without opening original
        copy roots or files. Changed storage ancestry/mode/identity still refuses.
        The caller owns and closes the returned descriptor.
        """
        with self._lock:
            try:
                if not self._unchanged((self._storage,)):
                    return ConfigurationError()
                return OwnedInputFD(os.dup(self._storage[1]))
            except (OSError, ValueError):
                return ConfigurationError()

    def open_copy(
        self, spec: CopyInput
    ) -> OwnedInputFD | InvalidRequest | ConfigurationError:
        """Open one regular descendant without reopening names after admission.

        An already-open source may legally be renamed or have other hardlink names;
        this is no origin-uniqueness claim. Store-owned objects have stronger guards
        in their owning store and in the copy/postcheck worker.
        """
        with self._lock:
            if (
                not isinstance(spec, CopyInput)
                or spec.root_id not in self._roots
            ):
                return InvalidRequest(
                    "revision.inputs", "Input selection is not authorized."
                )
            try:
                if not self._unchanged(
                    (self._storage, self._roots[spec.root_id])
                ):
                    return ConfigurationError()
            except (OSError, ValueError):
                return ConfigurationError()
            fd = None
            try:
                fd = os.dup(self._roots[spec.root_id][1])
                parts = spec.relative_path.split("/")
                for index, part in enumerate(parts):
                    flags = os.O_RDONLY | os.O_NOFOLLOW
                    flags |= (
                        os.O_NONBLOCK | os.O_NOCTTY
                        if index == len(parts) - 1
                        else os.O_DIRECTORY
                    )
                    child = os.open(part, flags, dir_fd=fd)
                    os.close(fd)
                    fd = child
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    return InvalidRequest(
                        "revision.inputs", "Input must be a regular file."
                    )
                result = OwnedInputFD(fd)
                fd = None
                return result
            except OSError:
                return InvalidRequest(
                    "revision.inputs", "Input selection is unavailable."
                )
            finally:
                if fd is not None:
                    os.close(fd)

    def close(self) -> None:
        """Stop grant use and close startup pins after admitted callers drain."""
        with self._lock:
            if not self._closed:
                self._closed = True
                for _, fd in (self._storage, *self._roots.values()):
                    os.close(fd)


def authorize_inputs(
    policy_path: str | None,
    check_roots: Callable[[Path, tuple[Path, ...]], ConfigurationError | None],
) -> InputGrant | InputsDisabled | ConfigurationError:
    """Authorize a startup policy once, pin before callback, recheck afterward.

    The lifecycle alone reads DARTWORK_MPL_INPUT_POLICY and supplies its value.
    This function never reads environment variables or creates policy/root files.
    """
    if policy_path is None:
        return InputsDisabled()
    pins: list[int] = []
    try:
        if not _platform_supported():
            return ConfigurationError()
        payload = _read_policy(_canonical(policy_path))
        storage_path = _canonical(payload["storage_dir"])
        storage_fd = _open_directory(storage_path, private=True)
        pins.append(storage_fd)
        roots = payload["copy_roots"]
        if not isinstance(roots, dict):
            raise ValueError("Invalid copy roots")
        pinned_roots = {}
        for name, raw in roots.items():
            # Reuse the pure public constructor's exact identifier language.
            CopyInput("input", name, "file", "0" * 64)
            path = _canonical(raw)
            fd = _open_directory(path)
            pins.append(fd)
            pinned_roots[name] = (path, fd)
        if not _check_capabilities(storage_fd):
            return ConfigurationError()
        if (
            check_roots(
                storage_path, tuple(path for path, _ in pinned_roots.values())
            )
            is not None
        ):
            return ConfigurationError()
        # Rewalk after the callback; never adopt a replacement's identity.
        for path, pinned in (
            (storage_path, storage_fd),
            *pinned_roots.values(),
        ):
            current = _open_directory(path, private=path == storage_path)
            try:
                if _identity(current) != _identity(pinned):
                    return ConfigurationError()
            finally:
                os.close(current)
        if not _check_capabilities(storage_fd):
            return ConfigurationError()
        grant = InputGrant(_KEY, (storage_path, storage_fd), pinned_roots)
        pins.clear()
        return grant
    except (
        OSError,
        ValueError,
        TypeError,
        UnicodeError,
        OverflowError,
        RecursionError,
        NotImplementedError,
    ):
        return ConfigurationError()
    finally:
        for fd in pins:
            os.close(fd)
