"""Waits on real child processes that do not race the host's start-up speed.

A test that starts a real interpreter cannot know how long the host takes to
start it. On 2026-11-12 and 2026-11-13 the shared CI runner was slow enough
that importing Matplotlib alone took longer than the short product timeouts
and client grace periods these tests had borrowed as their own deadlines, so
main went red for reasons unrelated to the merged change (#716).

Two tools keep such a test about what the child does, not about when:

- ``HANG_GUARD_S`` bounds a wait on an event. It is not an expectation: a
  passing test never gets near it, and a wait that can see its process die
  should fail on that death first. It exists so a real hang fails the test
  instead of holding the CI job.
- ``expire_when`` stages ``run_child``'s deadline on a point the child reaches.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest

__all__ = ["HANG_GUARD_S", "expire_when", "reach"]

HANG_GUARD_S = 120.0
# The most a child can have written to one pipe and not yet had read.
_PIPE_BYTES = 64 * 1024
_AHEAD_S = 3600.0


def reach(marker: Path) -> str:
    """One line of child code that creates ``marker``: the point a test waits for."""
    return f"open({str(marker)!r}, 'w').close()\n"


def expire_when(
    monkeypatch: pytest.MonkeyPatch, reached: Callable[[], bool]
) -> None:
    """Let ``run_child``'s deadline pass once ``reached()`` holds, and not before.

    ``run_child``'s timeout covers interpreter start-up and the Matplotlib
    import as well as the submitted code. A test of what a *timed-out* child
    leaves behind needs the child to get as far as writing it, and a short
    real timeout races that against start-up.

    The clock ``run_child`` reads stands still until ``reached()`` first holds,
    so the deadline cannot pass while the child is still getting there. It
    stays still for as many more readings as collecting a full pipe takes
    (``run_child`` reads the clock once per poll and takes up to
    ``_READ_BYTES`` from each pipe per poll), so everything the child wrote
    before that point is in the report. Then it reads an hour ahead: the
    deadline has passed whatever ``timeout_seconds`` was, and ``run_child``
    takes its real timeout path — kill, reap, timeout view of the logs.

    The child must do what ``reached`` observes and then keep running, so the
    timeout and not its own exit ends it. No time is waited out. A child that
    never gets there is not waited for either: after ``HANG_GUARD_S`` the
    clock moves ahead anyway and the test fails on what the child left undone.
    """
    from dartwork_mpl.mcp._platform import process

    settle = _PIPE_BYTES // process._READ_BYTES + 2
    started = time.monotonic()
    readings_left: int | None = None

    def clock() -> float:
        """The staged reading: still, then still while the pipes drain, then ahead."""
        nonlocal readings_left
        if readings_left is None:
            if not reached() and time.monotonic() - started < HANG_GUARD_S:
                return started
            readings_left = settle
        if readings_left > 0:
            readings_left -= 1
            return started
        # A running clock again, so a later child in the same test still has
        # a deadline of its own.
        return time.monotonic() + _AHEAD_S

    monkeypatch.setattr(process, "_monotonic", clock)
