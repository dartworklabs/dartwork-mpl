"""Owned real-process copy/postcheck deadlines, cancellation and byte bounds."""

import asyncio
import hashlib
import importlib
import importlib.util
import json
import os
import select
import subprocess
import sys
import time

import pytest

from dartwork_mpl.mcp.artifacts.input_policy import InputFile
from dartwork_mpl.mcp.artifacts.policy import InvalidRequest, PublicationError

MIB = 1024 * 1024


def io():
    """Expose missing bounded I/O as an assertion-visible initial RED."""
    name = "dartwork_mpl.mcp.artifacts.input_io"
    assert importlib.util.find_spec(name) is not None, (
        "owned input worker is missing"
    )
    return importlib.import_module(name)


def fd_count():
    """Count actual open descriptors without a transient directory-list FD."""
    count = 0
    for fd in range(1024):
        try:
            os.fstat(fd)
            count += 1
        except OSError:  # noqa: PERF203 - each candidate FD may be absent.
            pass
    return count


def files(root, payload=b"exact bytes"):
    """Create genuine 0600 source/destination objects and own their FDs."""
    source, dest = root / "original", root / "copy"
    source.write_bytes(payload)
    source.chmod(0o600)
    source_fd = os.open(source, os.O_RDWR)
    destination_fd = os.open(dest, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    return source_fd, destination_fd, hashlib.sha256(payload).hexdigest()


def record_reads(api, monkeypatch):
    """Observe owned worker accounting without replacing its real I/O/process."""
    measured = []
    original = api._wait_worker

    def observe(process, payload, deadline):
        """Keep raw per-phase accounting emitted by the owned worker."""
        result = original(process, payload, deadline)
        measured.append(json.loads(result)["read_bytes"])
        return result

    monkeypatch.setattr(api, "_wait_worker", observe)
    return measured


def test_exact_bytes_and_postcheck_use_owned_descriptors(
    owned_input_root, monkeypatch
):
    """Copy from already-open renamed source; verify bytes and reaped workers."""
    api = io()
    src, dst, digest = files(owned_input_root)
    reads = record_reads(api, monkeypatch)
    try:
        (owned_input_root / "original").rename(owned_input_root / "renamed")
        before = fd_count()
        result = api.copy_inputs((api.CopyJob(src, dst, "sample", digest),), 10)
        expected = InputFile("sample", digest, 11)
        assert result == (expected,)
        assert os.pread(dst, 100, 0) == b"exact bytes"
        assert api.check_copies((api.CheckJob(dst, expected),), 5) is None
        assert reads == [11, 11]
        assert fd_count() == before
    finally:
        os.close(src)
        os.close(dst)


@pytest.mark.parametrize(
    "phase,deadline",
    [("copy", 10), ("check", 5), ("cancel", 10), ("cancel_check", 5)],
)
def test_blocked_worker_is_reaped_before_release(
    owned_input_root, monkeypatch, phase, deadline
):
    """Real 10s/5s/cancel barriers finish only after child death and FD release."""
    api = io()
    src, dst, digest = files(owned_input_root)
    barrier_r, barrier_w = os.pipe()
    ready_r, ready_w = os.pipe()
    processes = []
    original_wait = api._wait_worker

    def spawn(fds):
        """Block an explicitly passed child descriptor before any data I/O."""
        prefix = (
            f"import os; os.write({ready_w}, b'R'); os.read({barrier_r}, 1);\n"
        )
        process = subprocess.Popen(
            [sys.executable, "-I", "-S", "-c", prefix + api._worker_code()],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            pass_fds=(*fds, barrier_r, ready_w),
        )
        processes.append(process)
        return process

    def wait(process, payload, seconds):
        """Synchronize with the blocked child, then deadline or cancel its owner."""
        assert select.select([ready_r], [], [], 3)[0]
        assert os.read(ready_r, 1) == b"R"
        if phase.startswith("cancel"):
            raise asyncio.CancelledError()
        return original_wait(process, payload, seconds)

    monkeypatch.setattr(api, "_spawn_worker", spawn)
    monkeypatch.setattr(api, "_wait_worker", wait)
    before = fd_count()
    started = time.monotonic()
    try:
        if phase == "check":
            os.pwrite(dst, b"exact bytes", 0)
            result = api.check_copies(
                (api.CheckJob(dst, InputFile("sample", digest, 11)),), deadline
            )
        elif phase.startswith("cancel"):
            with pytest.raises(asyncio.CancelledError):
                if phase == "cancel_check":
                    api.check_copies(
                        (api.CheckJob(dst, InputFile("sample", digest, 11)),),
                        deadline,
                    )
                else:
                    api.copy_inputs(
                        (api.CopyJob(src, dst, "sample", digest),), deadline
                    )
            result = None
        else:
            result = api.copy_inputs(
                (api.CopyJob(src, dst, "sample", digest),), deadline
            )
        elapsed = time.monotonic() - started
        if not phase.startswith("cancel"):
            assert isinstance(result, PublicationError)
            assert deadline - 0.1 <= elapsed < deadline + 4
        assert len(processes) == 1 and processes[0].returncode is not None
        with pytest.raises(ProcessLookupError):
            os.kill(processes[0].pid, 0)
        assert fd_count() == before
        print(
            json.dumps(
                {
                    "phase": phase,
                    "deadline": deadline,
                    "elapsed": elapsed,
                    "pid": processes[0].pid,
                    "returncode": processes[0].returncode,
                    "fd_before": before,
                    "fd_after": fd_count(),
                    "reaped": True,
                }
            )
        )
    finally:
        for fd in (src, dst, barrier_r, barrier_w, ready_r, ready_w):
            os.close(fd)


@pytest.mark.parametrize(
    "case", ["hash", "oversized", "postchange", "hardlink_store", "unsafe_mode"]
)
def test_changed_or_unsafe_objects_are_never_accepted(owned_input_root, case):
    """Hash/size changes and unsafe store-owned objects return named refusals."""
    api = io()
    src, dst, digest = files(owned_input_root)
    try:
        if case == "hash":
            digest = "0" * 64
        elif case == "oversized":
            os.ftruncate(src, 8 * MIB + 1)
        elif case == "hardlink_store":
            os.link(owned_input_root / "copy", owned_input_root / "other")
        elif case == "unsafe_mode":
            os.fchmod(dst, 0o644)
        if case == "postchange":
            expected = api.copy_inputs(
                (api.CopyJob(src, dst, "x", digest),), 10
            )
            assert isinstance(expected, tuple)
            os.pwrite(dst, b"changed", 0)
            result = api.check_copies((api.CheckJob(dst, expected[0]),), 5)
        else:
            result = api.copy_inputs((api.CopyJob(src, dst, "x", digest),), 10)
        assert isinstance(result, (InvalidRequest, PublicationError))
    finally:
        os.close(src)
        os.close(dst)


def test_full_boundary_accounting_and_overrun_are_below_65mib(
    owned_input_root, monkeypatch
):
    """Four 8MiB copies plus full reread and real growth never exceed 65MiB."""
    api = io()
    reads = record_reads(api, monkeypatch)
    jobs, descriptors = [], []
    payload = b"A" * (8 * MIB)
    digest = hashlib.sha256(payload).hexdigest()
    try:
        for index in range(4):
            folder = owned_input_root / str(index)
            folder.mkdir()
            src, dst, _ = files(folder, payload)
            descriptors.extend((src, dst))
            jobs.append(api.CopyJob(src, dst, f"data{index}", digest))
        copied = api.copy_inputs(tuple(jobs), 10)
        assert isinstance(copied, tuple)
        checks = tuple(
            api.CheckJob(job.destination_fd, expected)
            for job, expected in zip(jobs, copied, strict=True)
        )
        assert api.check_copies(checks, 5) is None
        assert reads == [32 * MIB, 32 * MIB]
        # Grow a stage *during* its reread, after initial fstat accepted 8MiB.
        code = api._worker_code()
        target = os.fstat(jobs[-1].destination_fd).st_ino
        inject = f"\n_original_read = _read_chunk\n_grown = False\ndef _read_chunk(fd, amount, offset):\n    global _grown\n    if not _grown and os.fstat(fd).st_ino == {target}:\n        os.ftruncate(fd, 8 * 1024 * 1024 + 1)\n        _grown = True\n    return _original_read(fd, amount, offset)\n_main()\n"
        monkeypatch.setattr(
            api, "_worker_code", lambda: code.replace("\n_main()\n", inject)
        )
        assert isinstance(api.check_copies(checks, 5), InvalidRequest)
        assert reads[-1] == 32 * MIB + 1
        assert reads[0] + reads[-1] <= 65 * MIB
        print(
            json.dumps(
                {
                    "boundary_copy": reads[0],
                    "boundary_postcheck": reads[1],
                    "overrun_postcheck": reads[2],
                    "phase_pair_bound": 64 * MIB + 2,
                    "maximum": 65 * MIB,
                }
            )
        )
    finally:
        for fd in descriptors:
            os.close(fd)


def test_streamed_source_growth_is_counted_and_refused(
    owned_input_root, monkeypatch
):
    """Growth after fstat is detected by streaming, including one overrun byte."""
    api = io()
    src, dst, digest = files(owned_input_root, b"A" * (8 * MIB))
    reads = record_reads(api, monkeypatch)
    code = api._worker_code()
    inject = "\n_original_read = _read_chunk\ndef _read_chunk(fd, amount, offset):\n    if offset == 0:\n        os.ftruncate(fd, 8 * 1024 * 1024 + 1)\n    return _original_read(fd, amount, offset)\n_main()\n"
    monkeypatch.setattr(
        api, "_worker_code", lambda: code.replace("\n_main()\n", inject)
    )
    try:
        result = api.copy_inputs((api.CopyJob(src, dst, "x", digest),), 10)
        assert isinstance(result, InvalidRequest)
        assert reads == [8 * MIB + 1]
        print(json.dumps({"growth_copy_data_reads": reads[0]}))
    finally:
        os.close(src)
        os.close(dst)


def test_child_closes_unrelated_fds_and_partial_start_failures(
    owned_input_root, monkeypatch
):
    """Explicit pass_fds drops inheritable foreign authority; failed spawn leaks none."""
    api = io()
    src, dst, digest = files(owned_input_root)
    unrelated = os.open(owned_input_root, os.O_RDONLY)
    os.set_inheritable(unrelated, True)
    before = fd_count()
    original = api._worker_code()
    check = f"import os\ntry:\n os.fstat({unrelated})\n raise SystemExit(99)\nexcept OSError:\n pass\n"
    monkeypatch.setattr(api, "_worker_code", lambda: check + original)
    try:
        result = api.copy_inputs((api.CopyJob(src, dst, "x", digest),), 10)
        assert isinstance(result, tuple), result
        assert fd_count() == before

        def fail_spawn(fds):
            """Fail the owned adapter after descriptor duplication, before exec."""
            raise OSError("private path must not escape")

        monkeypatch.setattr(api, "_spawn_worker", fail_spawn)
        assert isinstance(
            api.copy_inputs((api.CopyJob(src, dst, "x", digest),), 10),
            PublicationError,
        )
        assert fd_count() == before
    finally:
        for fd in (src, dst, unrelated):
            os.close(fd)


@pytest.mark.parametrize("fault", ["read", "write", "partial_write"])
def test_owned_worker_faults_keep_safe_outcomes_and_cleanup(
    owned_input_root, monkeypatch, fault
):
    """Inject at local worker I/O seams while keeping actual exec and files."""
    api = io()
    src, dst, digest = files(owned_input_root)
    code = api._worker_code()
    if fault == "read":
        injected = "\ndef _read_chunk(fd, amount, offset):\n    raise OSError('private sentinel path')\n_main()\n"
    elif fault == "write":
        injected = "\ndef _write_chunk(fd, data, offset):\n    raise OSError('private sentinel path')\n_main()\n"
    else:
        # A real short write still has to be completed by the owned loop.
        injected = "\n_original_pwrite = os.pwrite\ndef _short_write(fd, data, offset):\n    return _original_pwrite(fd, data[:2], offset)\nos.pwrite = _short_write\n_main()\n"
    monkeypatch.setattr(
        api, "_worker_code", lambda: code.replace("\n_main()\n", injected)
    )
    before = fd_count()
    try:
        result = api.copy_inputs((api.CopyJob(src, dst, "x", digest),), 10)
        if fault == "partial_write":
            assert result == (InputFile("x", digest, 11),)
            assert os.pread(dst, 100, 0) == b"exact bytes"
        else:
            assert isinstance(
                result, InvalidRequest if fault == "read" else PublicationError
            )
            assert "private sentinel" not in repr(result)
        assert fd_count() == before
    finally:
        os.close(src)
        os.close(dst)


def test_phase_aggregate_limit_and_constructor_invariants(
    owned_input_root, monkeypatch
):
    """A fifth 8MiB source is refused after at most 32MiB plus one data byte."""
    api = io()
    reads = record_reads(api, monkeypatch)
    jobs, descriptors = [], []
    try:
        for index in range(5):
            folder = owned_input_root / str(index)
            folder.mkdir()
            src, dst, digest = files(folder, b"A" * (8 * MIB))
            descriptors.extend((src, dst))
            jobs.append(api.CopyJob(src, dst, f"input{index}", digest))
        assert isinstance(api.copy_inputs(tuple(jobs), 10), InvalidRequest)
        assert reads == [32 * MIB + 1]
        for deadline in (0, -1, float("nan"), float("inf"), 11, True):
            assert isinstance(
                api.copy_inputs(tuple(jobs[:1]), deadline), InvalidRequest
            )
        assert isinstance(api.copy_inputs((), 10), InvalidRequest)
        with pytest.raises(ValueError):
            api.CopyJob(-1, 0, "x", "a" * 64)
        with pytest.raises(ValueError):
            api.CopyJob(0, 1, "bad/name", "a" * 64)
        with pytest.raises(ValueError):
            api.CheckJob(0, {})
        print(json.dumps({"aggregate_copy_overrun_reads": reads[0]}))
    finally:
        for fd in descriptors:
            os.close(fd)


@pytest.mark.parametrize(
    "raw", [b"[]", b"null", b"{}", b'{"status":"ok","files":null}']
)
def test_invalid_worker_report_is_safe_and_reaped(
    owned_input_root, monkeypatch, raw
):
    """Damaged owned-worker reports cannot raise, leak FDs or publish success."""
    api = io()
    src, dst, digest = files(owned_input_root)
    code = (
        "import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write("
        + repr(raw)
        + ")"
    )
    monkeypatch.setattr(api, "_worker_code", lambda: code)
    before = fd_count()
    try:
        assert isinstance(
            api.copy_inputs((api.CopyJob(src, dst, "x", digest),), 10),
            PublicationError,
        )
        assert fd_count() == before
    finally:
        os.close(src)
        os.close(dst)
