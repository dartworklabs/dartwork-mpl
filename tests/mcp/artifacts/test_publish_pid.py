"""The child pid marker the lifecycle tests wait for is never visible half-written.

The lifecycle tests wait for ``marker`` to exist and then read the child's pid
from it. ``publish_pid`` writes the pid to a temporary file beside the marker
and renames it over the marker. These tests hold a real child between the
write and the rename, so the ordering is proved rather than raced.
"""

import subprocess
import sys
import time
from pathlib import Path

from tests.mcp.artifacts.input_fixtures import publish_pid

PRELUDE = "import os, time\nfrom pathlib import Path\n"


def wait_for(predicate, timeout=10.0):
    """Poll ``predicate`` until it holds; fail (never loop forever) past ``timeout``."""
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not reached in time")
        time.sleep(0.01)


def run(code):
    """Start a real child interpreter running ``code``."""
    return subprocess.Popen([sys.executable, "-c", code])


def reap(child):
    """Leave no child behind, even when an assertion failed mid-test."""
    if child.poll() is None:
        child.kill()
    child.wait(timeout=10)


def test_marker_stays_absent_while_the_pid_is_being_written(tmp_path):
    marker, hold = tmp_path / "pid", tmp_path / "hold"
    staged = Path(str(marker) + ".tmp")
    child = run(PRELUDE + publish_pid(marker, hold=hold))
    try:
        # The child has written its pid and is held before publishing it.
        wait_for(lambda: staged.exists() and staged.read_text() != "")
        assert not marker.exists()
        hold.touch()
        assert child.wait(timeout=10) == 0
        assert int(marker.read_text()) == child.pid
        assert not staged.exists()
    finally:
        reap(child)


def test_writing_the_marker_in_place_exposes_an_empty_pid(tmp_path):
    """Control: creating the marker and then writing it is observable as ``''``.

    This is the gap the old child code had (``Path(marker).write_text(...)``
    creates the file before it writes); the CI failure read ``int('')``.
    """
    marker, hold = tmp_path / "pid", tmp_path / "hold"
    child = run(
        PRELUDE
        + f"stream = open({str(marker)!r}, 'w')\n"
        + f"while not Path({str(hold)!r}).exists(): time.sleep(0.01)\n"
        + "stream.write(str(os.getpid()))\nstream.close()\n"
    )
    try:
        wait_for(marker.exists)
        assert marker.read_text() == ""
        hold.touch()
        assert child.wait(timeout=10) == 0
        assert int(marker.read_text()) == child.pid
    finally:
        reap(child)
