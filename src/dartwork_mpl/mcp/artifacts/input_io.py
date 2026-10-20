"""Bounded descriptor-only copy/check phases in owned, reaped POSIX processes.

Input descriptors remain caller-owned. Each call duplicates and explicitly
transfers only its job descriptors, terminates on deadline/cancellation, and
reaps before closing duplicates or returning capacity control to its caller.
Copy and postcheck each read at most 32MiB+1; together <=64MiB+2 (<65MiB).
The 10s/5s phase maxima exclude unbounded kernel wait/reap wall-clock behavior.
"""

import json
import math
import os
import subprocess
import sys
import time
from dataclasses import dataclass

from .input_policy import MAX_INPUT_FILES, MAX_INPUT_PAYLOAD_BYTES, InputFile
from .policy import InvalidRequest, PublicationError

__all__ = ["CheckJob", "CopyJob", "check_copies", "copy_inputs", "probe_worker"]


def _require_fd(fd: int) -> None:
    """Require an FD number; fstat and ownership checks occur in the worker."""
    if type(fd) is not int or fd < 0:
        raise ValueError("Invalid input descriptor")


@dataclass(frozen=True)
class CopyJob:
    """Borrowed regular source and private empty destination, with exact digest."""

    source_fd: int
    destination_fd: int
    name: str
    sha256: str

    def __post_init__(self) -> None:
        """Reject invalid trusted construction before opening a worker."""
        _require_fd(self.source_fd)
        _require_fd(self.destination_fd)
        InputFile(self.name, self.sha256, 0)


@dataclass(frozen=True)
class CheckJob:
    """Borrowed store-owned copy and its measured pre-execution identity/bytes."""

    file_fd: int
    expected: InputFile

    def __post_init__(self) -> None:
        """Require the parsed file value rather than an unchecked metadata dict."""
        _require_fd(self.file_fd)
        if not isinstance(self.expected, InputFile):
            raise ValueError("Expected measured input file")


# This child has no package import, global startup authority, cwd/env change or
# path arguments. The parent supplies a bounded private stdin control message.
# _read_chunk and _worker_code are local owned-adapter fault injection seams.
_WORKER_CODE = r'''
import hashlib
import json
import os
import stat
import sys

CHUNK = 64 * 1024
FILE_LIMIT = 8 * 1024 * 1024
PHASE_LIMIT = 32 * 1024 * 1024


class _Invalid(Exception):
    """Source, digest or boundary refusal; never carries submitted data."""


class _Publication(Exception):
    """A private destination/worker operation could not complete safely."""


def _read_chunk(fd, amount, offset):
    """Read at most one bounded chunk from the admitted object, never a path."""
    return os.pread(fd, amount, offset)


def _signature(info):
    """Detect object/data/security mutation, excluding read-induced access time."""
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_uid, info.st_mode, info.st_nlink)


def _regular(fd, owned):
    """Store objects retain exact private ownership/mode/single-link guards."""
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        raise _Invalid()
    if owned and (info.st_uid != os.geteuid() or
                  stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
        raise _Publication()
    if info.st_size > FILE_LIMIT:
        raise _Invalid()
    return info


def _write_chunk(fd, data, offset):
    """Finish partial writes without reading or reopening a destination name."""
    written = 0
    while written < len(data):
        amount = os.pwrite(fd, data[written:], offset + written)
        if amount <= 0:
            raise _Publication()
        written += amount


def _main():
    """Stream one phase with shared accounting and emit only bounded facts."""
    total = 0
    result = {"status": "publication", "read_bytes": 0}
    try:
        raw = sys.stdin.buffer.read(16 * 1024 + 1)
        if len(raw) > 16 * 1024:
            raise _Invalid()
        request = json.loads(raw)
        phase, jobs = request["phase"], request["jobs"]
        measured = []
        seen_destinations = set()
        for job in jobs:
            checking = phase == "check"
            source = job["file_fd"] if checking else job["source_fd"]
            before = _regular(source, checking)
            destination = None
            destination_before = None
            if not checking:
                destination = job["destination_fd"]
                destination_before = _regular(destination, True)
                identity = (destination_before.st_dev, destination_before.st_ino)
                if (destination_before.st_size != 0 or identity in seen_destinations
                    or identity == (before.st_dev, before.st_ino)):
                    raise _Publication()
                seen_destinations.add(identity)
            size = 0
            digest = hashlib.sha256()
            while True:
                amount = min(CHUNK, FILE_LIMIT + 1 - size,
                             PHASE_LIMIT + 1 - total)
                try:
                    chunk = _read_chunk(source, amount, size)
                except OSError:
                    raise _Invalid() from None
                size += len(chunk)
                total += len(chunk)
                if size > FILE_LIMIT or total > PHASE_LIMIT:
                    raise _Invalid()
                if not chunk:
                    break
                digest.update(chunk)
                if destination is not None:
                    _write_chunk(destination, chunk, size - len(chunk))
            after = _regular(source, checking)
            if (_signature(before) != _signature(after) or size != before.st_size
                or digest.hexdigest() != job["sha256"]
                or (checking and size != job["size_bytes"])):
                raise _Invalid()
            if destination is not None:
                final = _regular(destination, True)
                if ((final.st_dev, final.st_ino) !=
                    (destination_before.st_dev, destination_before.st_ino)
                    or final.st_size != size):
                    raise _Publication()
            measured.append({"name": job["name"], "sha256": digest.hexdigest(),
                             "size_bytes": size})
        result = {"status": "ok", "files": measured}
    except _Invalid:
        result = {"status": "invalid"}
    except (OSError, ValueError, KeyError, TypeError, _Publication):
        result = {"status": "publication"}
    result["read_bytes"] = total
    sys.stdout.buffer.write(json.dumps(result, separators=(",", ":")).encode())

_main()
'''


def _worker_code() -> str:
    """Supply the owned child implementation; tests inject I/O faults here."""
    return _WORKER_CODE


def _spawn_worker(fds: tuple[int, ...]) -> subprocess.Popen[bytes]:
    """Exec a fresh interpreter with explicit FD transfer, unrelated FDs closed."""
    return subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", _worker_code()],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        pass_fds=fds,
    )


def _wait_worker(
    process: subprocess.Popen[bytes], payload: bytes, deadline: float
) -> bytes:
    """Wait within the remaining phase deadline; timeout/cancel cleanup is owned."""
    output, _ = process.communicate(input=payload, timeout=deadline)
    return output


def _reap(process: subprocess.Popen[bytes]) -> None:
    """Kill an unfinished child and always wait before caller releases capacity."""
    try:
        if process.poll() is None:
            process.kill()
    except ProcessLookupError:
        pass
    finally:
        # No bounded wall-clock claim for a kernel-blocked child or waitpid.
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()


def probe_worker(fd: int) -> bool:
    """Startup-only real exec/FD probe; preserve imports when POSIX is absent."""
    process = None
    try:
        if os.name != "posix":
            return False
        process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                "import os,sys; os.fstat(int(sys.stdin.buffer.read(32)))",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            pass_fds=(fd,),
        )
        process.communicate(str(fd).encode("ascii"), timeout=2)
        return process.returncode == 0
    except (
        OSError,
        ValueError,
        subprocess.TimeoutExpired,
        NotImplementedError,
    ):
        return False
    finally:
        if process is not None:
            _reap(process)


def _run_phase(
    jobs: tuple[CopyJob, ...] | tuple[CheckJob, ...],
    deadline_seconds: float,
    *,
    checking: bool,
) -> tuple[InputFile, ...] | InvalidRequest | PublicationError:
    """Duplicate borrowed FDs, run one owned phase, then reap before release."""
    maximum = 5 if checking else 10
    kind = CheckJob if checking else CopyJob
    if (
        not isinstance(jobs, tuple)
        or not 1 <= len(jobs) <= MAX_INPUT_FILES
        or any(not isinstance(job, kind) for job in jobs)
        or type(deadline_seconds) not in (float, int)
        or not math.isfinite(deadline_seconds)
        or not 0 < deadline_seconds <= maximum
    ):
        return InvalidRequest("revision.inputs", "Invalid input I/O phase.")
    names = [
        job.expected.name if isinstance(job, CheckJob) else job.name
        for job in jobs
    ]
    if len(set(names)) != len(names):
        return InvalidRequest("revision.inputs", "Input names must be unique.")
    if (
        checking
        and sum(
            job.expected.size_bytes for job in jobs if isinstance(job, CheckJob)
        )
        > MAX_INPUT_PAYLOAD_BYTES
    ):
        return InvalidRequest(
            "revision.inputs", "Input payload exceeds its bound."
        )
    descriptors = []
    request_jobs = []
    process = None
    started = time.monotonic()
    try:
        for job in jobs:
            if isinstance(job, CheckJob):
                fd = os.dup(job.file_fd)
                descriptors.append(fd)
                request_jobs.append(
                    {
                        "file_fd": fd,
                        "name": job.expected.name,
                        "sha256": job.expected.sha256,
                        "size_bytes": job.expected.size_bytes,
                    }
                )
            else:
                source_fd = os.dup(job.source_fd)
                descriptors.append(source_fd)
                destination_fd = os.dup(job.destination_fd)
                descriptors.append(destination_fd)
                request_jobs.append(
                    {
                        "source_fd": source_fd,
                        "destination_fd": destination_fd,
                        "name": job.name,
                        "sha256": job.sha256,
                    }
                )
        payload = json.dumps(
            {"phase": "check" if checking else "copy", "jobs": request_jobs},
            separators=(",", ":"),
        ).encode("utf-8")
        process = _spawn_worker(tuple(descriptors))
        remaining = deadline_seconds - (time.monotonic() - started)
        if remaining <= 0:
            return PublicationError()
        output = _wait_worker(process, payload, remaining)
        if process.returncode != 0 or len(output) > 16 * 1024:
            return PublicationError()
        result = json.loads(output)
        if not isinstance(result, dict):
            return PublicationError()
        if result.get("status") == "invalid":
            return InvalidRequest(
                "revision.inputs",
                "Input bytes or boundary verification failed.",
            )
        if result.get("status") != "ok":
            return PublicationError()
        measured = tuple(
            InputFile(entry["name"], entry["sha256"], entry["size_bytes"])
            for entry in result["files"]
        )
        if len(measured) != len(jobs):
            return PublicationError()
        return measured
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.TimeoutExpired,
        NotImplementedError,
    ):
        return PublicationError()
    finally:
        try:
            if process is not None:
                _reap(process)
        finally:
            for fd in descriptors:
                os.close(fd)


def copy_inputs(
    jobs: tuple[CopyJob, ...], deadline_seconds: float
) -> tuple[InputFile, ...] | InvalidRequest | PublicationError:
    """Copy/hash once within <=10s; failures leave cleanup to the owning stage."""
    return _run_phase(jobs, deadline_seconds, checking=False)


def check_copies(
    jobs: tuple[CheckJob, ...], deadline_seconds: float
) -> None | InvalidRequest | PublicationError:
    """Reread all copies within <=5s; only exact safe copies pass publication."""
    result = _run_phase(jobs, deadline_seconds, checking=True)
    return None if isinstance(result, tuple) else result
