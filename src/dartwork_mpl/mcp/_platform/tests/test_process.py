"""Bounded child capture and private PNG publication keep their limits and ownership."""

import pytest

pytest.importorskip("fastmcp")


def test_seeded_collector_prefix_and_saturation_properties():
    """Every incremental update stays bounded; complete selected logs match an independent decoder."""
    import random

    from dartwork_mpl.mcp._platform.process import _Capture

    rng = random.Random(49821)
    alphabet = (
        b"a",
        b" ",
        b"\r",
        b"\n",
        b"\xff",
        "한".encode(),
        b"\xe2",
        b"\x82\xac",
    )
    for _ in range(32):
        chunks = [
            rng.choice(alphabet) * rng.randrange(1, 1500) for _ in range(64)
        ]
        raw = b"".join(chunks)
        capture = _Capture(None, True)
        for channel in ("stdout", "stderr"):
            for chunk in chunks:
                for start in range(0, len(chunk), 8192):
                    capture.feed(channel, chunk[start : start + 8192])
                    assert capture.retained_bytes <= 6 * 65536, (
                        49821,
                        len(raw),
                    )
            capture.feed(channel, b"", final=True)
        decoded = raw.decode("utf-8", "replace")
        for view, reference in (
            (capture.timeout, decoded),
            (capture.normal, decoded.replace("\r\n", "\n").replace("\r", "\n")),
        ):
            out, err = view.logs()
            for actual, expected, channel in (
                (out, reference, "stdout"),
                (err, reference.strip(), "stderr"),
            ):
                assert len(actual.encode()) <= 65536, (49821, len(raw))
                marker = f"\n[dartwork-mpl: {channel} truncated; retained prefix only]\n"
                if len(expected.encode()) <= 65536:
                    assert actual == expected, (49821, len(raw))
                else:
                    assert actual.endswith(marker), (49821, len(raw))
                    assert expected.startswith(actual[: -len(marker)]), (
                        49821,
                        len(raw),
                    )


@pytest.mark.parametrize("extra", [0, 1])
def test_artifact_log_budget_selects_completion_view_at_exact_and_first_excess(
    extra,
):
    """Unused timeout-view overflow cannot refuse normalized under-cap success."""
    from dartwork_mpl.mcp._platform.process import _Capture

    capture = _Capture(128, False)
    raw = b"\r\n" * (128 + extra)
    for start in range(0, len(raw), 3):
        capture.feed("stdout", raw[start : start + 3])
        assert capture.retained_bytes <= 256
    for channel in ("stdout", "stderr"):
        capture.feed(channel, b"", final=True)
    assert capture.normal.overrun is bool(extra)
    assert capture.timeout.overrun is True
    if not extra:
        assert capture.normal.logs() == ("\n" * 128, "")
    else:
        assert (
            "stdout truncated; retained prefix only" in capture.normal.logs()[0]
        )


@pytest.mark.parametrize("budget", [0, -1, False])
def test_internal_capture_budget_rejects_impossible_constructor_values(budget):
    """Private capture state cannot be created with a nonpositive or boolean shared budget."""
    from dartwork_mpl.mcp._platform.process import _Capture

    with pytest.raises(ValueError, match="positive integer"):
        _Capture(budget, False)


def test_child_deadline_survives_early_stdout_stderr_close():
    """Closing both pipes cannot turn the direct child's wait into an unbounded wait."""
    import sys
    import time

    from dartwork_mpl.mcp._platform.process import run_child

    start = time.monotonic()
    result = run_child(
        [
            sys.executable,
            "-c",
            "import os,time; os.close(1); os.close(2); time.sleep(0.3)",
        ],
        timeout_seconds=0.05,
    )
    assert result.timed_out is True
    assert result.returncode != 0
    assert time.monotonic() - start < 1


@pytest.mark.parametrize("phase", ["open", "write", "close"])
def test_png_descriptor_write_failure_removes_only_new_file(
    tmp_path, monkeypatch, phase
):
    """A real descriptor closes and only its new path disappears on open/write/close failure."""
    import os
    import tempfile
    from pathlib import Path

    from dartwork_mpl.mcp._platform import process as _capture

    sentinel = tmp_path / "keep"
    sentinel.write_bytes(b"untouched")
    real_mkstemp = tempfile.mkstemp
    real_fdopen = os.fdopen
    descriptors = []

    def create_here(*args, **kwargs):
        """Place the actual output in a fixture-owned directory for cleanup inspection."""
        kwargs["dir"] = tmp_path
        descriptor, path = real_mkstemp(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor, path

    class FailedWriter:
        """Exercise real descriptor ownership across injected adapter failures."""

        def __init__(self, descriptor, mode):
            """Acquire the actual descriptor unless the owned open operation fails."""
            if phase == "open":
                raise OSError("controlled open failure")
            self.file = real_fdopen(descriptor, mode)

        def __enter__(self):
            """Keep file ownership within the context."""
            return self

        def __exit__(self, *args):
            """Close the genuine descriptor even when writing raises."""
            self.file.close()
            if phase == "close":
                raise OSError("controlled close failure")

        def fileno(self):
            """Expose the genuine descriptor for the regular-file check."""
            return self.file.fileno()

        def write(self, data):
            """Perform the real write or inject only its owned write error."""
            if phase == "write":
                raise OSError("controlled write failure")
            return self.file.write(data)

    with monkeypatch.context() as patch:
        patch.setattr(_capture.tempfile, "mkstemp", create_here)
        patch.setattr(_capture.os, "fdopen", FailedWriter)
        with pytest.raises(OSError, match=f"controlled {phase} failure"):
            _capture.publish_png(b"png", "owned-")
    assert sorted(Path(path).name for path in tmp_path.iterdir()) == ["keep"]
    assert sentinel.read_bytes() == b"untouched"
    with pytest.raises(OSError):
        os.fstat(descriptors[0])


def test_png_publication_rejects_nonregular_open_descriptor(
    tmp_path, monkeypatch
):
    """Regular-file admission checks the created handle, with cleanup on refusal."""
    import stat
    import tempfile
    from types import SimpleNamespace

    from dartwork_mpl.mcp._platform import process as _capture

    real_mkstemp = tempfile.mkstemp

    def create_here(*args, **kwargs):
        """Use actual exclusive file creation under the owned fixture directory."""
        kwargs["dir"] = tmp_path
        return real_mkstemp(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(_capture.tempfile, "mkstemp", create_here)
        patch.setattr(
            _capture.os,
            "fstat",
            lambda descriptor: SimpleNamespace(st_mode=stat.S_IFIFO),
        )
        with pytest.raises(OSError, match="not a regular file"):
            _capture.publish_png(b"png", "owned-")
    assert list(tmp_path.iterdir()) == []
