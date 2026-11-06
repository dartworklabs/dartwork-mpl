"""Real stdio, files and owned process trees pin evaluation capture boundaries."""

import asyncio
import base64
import hashlib
import json
import os
import random
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from evaluate_agent_plot import evaluate, replay
from run_agent_plot_eval import (
    _admission_decision,
    _repair_admission,
    _reserve_stage,
    _stage_review,
    capture_process,
    recover,
    validate_capture,
)


def test_recovery_reads_every_member_without_execution(tmp_path):
    """Both exact five-member bundles survive restart without a third execution."""
    counter = tmp_path / "counter"
    store = tmp_path / "store"
    source = f"""from pathlib import Path
p = Path({str(counter)!r})
p.write_text(str(int(p.read_text()) + 1) if p.exists() else '1')
import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use('scientific')
fig, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([1, 2], [3, 4], linewidth=dm.lw(0))
dm.simple_layout(fig)
"""

    async def render_twice():
        """Use the installed server entry point and an actual private store."""
        parameters = StdioServerParameters(
            command=str(Path(sys.executable).parent / "dartwork-mpl-mcp"),
            env={**os.environ, "DARTWORK_MPL_ARTIFACT_DIR": str(store)},
            cwd=str(tmp_path),
        )
        identities = []
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                await client.initialize()
                for suffix in ("", "\nax.set_title('revision')\n"):
                    result = await client.call_tool(
                        "render_plot", {"code": source + suffix}
                    )
                    assert (
                        result.structuredContent["delivery_status"] == "ready"
                    )
                    identities.append(result.structuredContent["artifact_id"])
        return identities

    identities = asyncio.run(render_twice())
    assert counter.read_text() == "2"
    first = recover(identities, store, tmp_path / "first")
    second = recover(identities, store, tmp_path / "second")
    assert first["status"] == second["status"] == "ok"
    assert first["members"] == second["members"]
    assert first["hashes"] == second["hashes"]
    assert set(first["members"]) == set(identities)
    for identity, members in first["members"].items():
        assert set(members) == {
            "plot.png",
            "plot.pdf",
            "source.py",
            "report.json",
            "manifest.json",
        }
        for name, data in members.items():
            assert (
                hashlib.sha256(data).hexdigest()
                == first["hashes"][identity][name]
            )
    assert counter.read_text() == "2"


def test_capture_rejects_incomplete_or_contaminated_run(tmp_path):
    """Truncated framing, fixture drift and evaluator access cannot pass capture."""
    csv = tmp_path / "input.csv"
    csv.write_bytes(b"x,y\n1,2\n")
    digest = hashlib.sha256(csv.read_bytes()).hexdigest()
    events = [
        {
            "type": "system",
            "subtype": "init",
            "session_id": "session",
            "model": "selected",
            "tools": ["Read", "mcp__dartwork_mpl__render_plot"],
            "mcp_servers": [{"name": "dartwork_mpl", "status": "connected"}],
        },
        {
            "type": "result",
            "subtype": "success",
            "session_id": "session",
            "is_error": False,
        },
    ]
    path = tmp_path / "events.jsonl"
    path.write_text("".join(json.dumps(item) + "\n" for item in events))
    assert validate_capture(path, csv, digest, "selected")["status"] == "ok"
    rng = random.Random(20261020)
    raw = path.read_bytes()
    for cut in rng.sample(range(1, len(raw)), 12):
        path.write_bytes(raw[:cut])
        assert (
            validate_capture(path, csv, digest, "selected")["status"]
            == "failed"
        )
    path.write_bytes(raw)
    csv.write_bytes(b"x,y\n1,9\n")
    assert (
        "fixture_changed"
        in validate_capture(path, csv, digest, "selected")["reasons"]
    )
    csv.write_bytes(b"x,y\n1,2\n")
    events.insert(
        1,
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/outside/expected.json"},
                    }
                ]
            },
        },
    )
    path.write_text("".join(json.dumps(item) + "\n" for item in events))
    assert (
        "oracle_access"
        in validate_capture(path, csv, digest, "selected")["reasons"]
    )


_WATCHDOG_CHILD = """import json, os, subprocess, sys, time
p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
print(json.dumps({'child_pid': p.pid}), flush=True)
time.sleep(0.15)
for i in range(100):
    print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','name':'mcp__dartwork_mpl__render_plot','input':{'code':'x' * 1000}}]}}), flush=True)
    time.sleep(0.01)
time.sleep(60)
"""


@pytest.mark.parametrize(
    "limit", ["wall", "calls", "reader_calls", "bytes", "source", "render_time"]
)
def test_watchdog_stops_process_tree_and_keeps_partial_evidence(
    tmp_path, limit, monkeypatch
):
    """External limits terminate an owned child plus detached grandchild."""
    child = tmp_path / "child.py"
    child.write_text(_WATCHDOG_CHILD)
    if limit == "reader_calls":
        child.write_text(
            child.read_text().replace(
                "mcp__dartwork_mpl__render_plot", "ReadMcpResourceTool"
            )
        )
    elif limit == "source":
        child.write_text(
            child.read_text().replace("'x' * 1000", "'x' * 600000")
        )
    elif limit == "render_time":
        child.write_text(
            child.read_text().replace(
                "'code':'x' * 1000", "'code':'x' * 1000,'timeout_seconds':21"
            )
        )
    if limit == "wall":
        import run_agent_plot_eval as capture

        started = time.monotonic()
        events = tmp_path / "events.jsonl"

        def controlled_monotonic():
            """Expire after the real first event, with a bounded startup guard."""
            elapsed = time.monotonic() - started
            if (events.exists() and events.stat().st_size) or elapsed > 5:
                return started + 1 + elapsed
            return started

        monkeypatch.setattr(
            capture,
            "time",
            SimpleNamespace(monotonic=controlled_monotonic, sleep=time.sleep),
        )
    result = capture_process(
        [sys.executable, str(child)],
        tmp_path,
        dict(os.environ),
        tmp_path / "events.jsonl",
        tmp_path / "stderr.txt",
        wall_seconds=0.4 if limit == "wall" else 5,
        max_calls=1 if limit in ("calls", "reader_calls") else 1000,
        max_bytes=2000 if limit == "bytes" else 1000000,
    )
    assert (
        result["stop_reason"]
        == {
            "wall": "wall_limit",
            "calls": "call_limit",
            "reader_calls": "call_limit",
            "bytes": "byte_limit",
            "source": "source_limit",
            "render_time": "render_time_limit",
        }[limit]
    )
    assert result["cleanup_ok"]
    first = json.loads((tmp_path / "events.jsonl").read_text().splitlines()[0])
    with pytest.raises(ProcessLookupError):
        os.kill(first["child_pid"], 0)
    assert (tmp_path / "stderr.txt").exists()


def test_watchdog_wall_limit_includes_startup_without_output(tmp_path):
    """The actual wall deadline also stops a child that never emits evidence."""
    result = capture_process(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        tmp_path,
        dict(os.environ),
        tmp_path / "events.jsonl",
        tmp_path / "stderr.txt",
        wall_seconds=0.4,
    )
    assert result["stop_reason"] == "wall_limit"
    assert result["cleanup_ok"]
    assert result["elapsed_seconds"] >= 0.4
    assert (tmp_path / "events.jsonl").read_bytes() == b""


def test_watchdog_source_limit_is_not_held_behind_slow_process_polls(
    tmp_path, monkeypatch
):
    """A call already in the stream wins even when process polls take all the time.

    On a contended host one owned-tree ``ps`` scan took ~0.6 s and made up
    nearly all of the watchdog's elapsed time. Here the watchdog clock moves
    0.6 s per scan and does not move otherwise, so the result does not depend
    on host load. A watchdog that scans before every pipe read needs one scan
    per pipe buffer, ten or more for the 600 KB call, and stops on
    ``wall_limit`` first.
    """
    import run_agent_plot_eval as capture

    child = tmp_path / "child.py"
    child.write_text(_WATCHDOG_CHILD.replace("'x' * 1000", "'x' * 600000"))
    origin = time.monotonic()
    state = {"scans": 0, "cleanup": False}
    scan, stop = capture._process_table, capture._stop_tree

    def counted_scan():
        """Charge one contended scan to the watchdog clock."""
        state["scans"] += 1
        return scan()

    def marked_stop(process, known):
        """Cleanup waits in real time once the stop reason is chosen."""
        state["cleanup"] = True
        return stop(process, known)

    def scan_driven_monotonic():
        """Only scans move time before cleanup, behind a real 5 s hang guard."""
        elapsed = time.monotonic() - origin
        charged = origin + 0.6 * state["scans"]
        return charged + elapsed if state["cleanup"] or elapsed > 5 else charged

    monkeypatch.setattr(capture, "_process_table", counted_scan)
    monkeypatch.setattr(capture, "_stop_tree", marked_stop)
    monkeypatch.setattr(
        capture,
        "time",
        SimpleNamespace(monotonic=scan_driven_monotonic, sleep=time.sleep),
    )
    result = capture_process(
        [sys.executable, str(child)],
        tmp_path,
        dict(os.environ),
        tmp_path / "events.jsonl",
        tmp_path / "stderr.txt",
        wall_seconds=5,
        max_calls=1000,
        max_bytes=1000000,
    )
    assert result["stop_reason"] == "source_limit"
    assert result["cleanup_ok"]
    first = json.loads((tmp_path / "events.jsonl").read_text().splitlines()[0])
    with pytest.raises(ProcessLookupError):
        os.kill(first["child_pid"], 0)


def _scan_driven_clock(monkeypatch, after_first_poll):
    """Let only real ``ps`` scans (0.6 s each) move the watchdog clock.

    ``after_first_poll`` runs once, at the first clock read after the first
    scan, which is after the first poll has measured the process and evidence
    trees. No later poll happens unless the watchdog polls per read. Cleanup
    runs in real time; a real 5 s guard bounds hangs.
    """
    import run_agent_plot_eval as capture

    origin = time.monotonic()
    state = {"scans": 0, "cleanup": False, "released": False}
    scan, stop = capture._process_table, capture._stop_tree

    def counted_scan():
        """Charge one contended scan to the watchdog clock."""
        state["scans"] += 1
        return scan()

    def marked_stop(process, known):
        """Cleanup waits in real time once the stop reason is chosen."""
        state["cleanup"] = True
        return stop(process, known)

    def monotonic():
        """Release the child after the first poll; then only scans move time."""
        if state["scans"] and not state["released"]:
            state["released"] = True
            after_first_poll()
        elapsed = time.monotonic() - origin
        charged = origin + 0.6 * state["scans"]
        return charged + elapsed if state["cleanup"] or elapsed > 5 else charged

    monkeypatch.setattr(capture, "_process_table", counted_scan)
    monkeypatch.setattr(capture, "_stop_tree", marked_stop)
    monkeypatch.setattr(
        capture, "time", SimpleNamespace(monotonic=monotonic, sleep=time.sleep)
    )


_FINAL_WRITE_CHILD = """import pathlib, signal, sys, time
signal.alarm(4)
go, payload, size = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3])
while not go.exists():
    time.sleep(0.001)
payload.write_bytes(b'x' * size)
print('{}', flush=True)
"""


@pytest.mark.parametrize(
    ("written", "stop_reason"),
    [(512, "exit"), (4096, "evidence_limit")],
    ids=["within", "over"],
)
def test_watchdog_admits_exit_only_within_final_evidence_limit(
    tmp_path, monkeypatch, written, stop_reason
):
    """Evidence written after the last poll still decides whether an exit is normal.

    The child writes a real file only after the first poll has measured the
    evidence tree, prints its last line and exits; no later poll runs. 4096
    bytes against a 1024-byte limit must not be admitted as ``exit``.
    """
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    go = tmp_path / "go"
    _scan_driven_clock(monkeypatch, lambda: go.write_text("go"))
    result = capture_process(
        [
            sys.executable,
            "-c",
            _FINAL_WRITE_CHILD,
            str(go),
            str(evidence / "payload.bin"),
            str(written),
        ],
        tmp_path,
        dict(os.environ),
        tmp_path / "events.jsonl",
        tmp_path / "stderr.txt",
        wall_seconds=5,
        max_bytes=1024,
        evidence_root=evidence,
    )
    assert (evidence / "payload.bin").stat().st_size == written
    assert (tmp_path / "events.jsonl").read_bytes() == b"{}\n"
    assert result["returncode"] == 0
    assert result["cleanup_ok"]
    assert result["stop_reason"] == stop_reason


_LATE_DESCENDANT_CHILD = """import json, pathlib, signal, subprocess, sys, time
signal.alarm(20)
go = pathlib.Path(sys.argv[1])
while not go.exists():
    time.sleep(0.001)
late = subprocess.Popen(
    [sys.executable, '-c', 'import time; time.sleep(20)'],
    start_new_session=True,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
print(json.dumps({'late_pid': late.pid}), flush=True)
call = {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'mcp__dartwork_mpl__render_plot', 'input': {'code': 'x'}}]}}
for _ in range(2):
    print(json.dumps(call), flush=True)
time.sleep(20)
"""


def test_watchdog_cleanup_finds_late_detached_descendant_and_spares_unrelated(
    tmp_path, monkeypatch
):
    """Cleanup rescans, so a new-session descendant started after the last poll stops.

    The child starts its grandchild only after the first poll and no later
    poll runs, so only cleanup's own scan can find it through its live parent.
    A process the test started in its own session is not owned and survives.
    """
    go = tmp_path / "go"
    _scan_driven_clock(monkeypatch, lambda: go.write_text("go"))
    unrelated = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(20)"],
        start_new_session=True,
    )
    try:
        result = capture_process(
            [sys.executable, "-c", _LATE_DESCENDANT_CHILD, str(go)],
            tmp_path,
            dict(os.environ),
            tmp_path / "events.jsonl",
            tmp_path / "stderr.txt",
            wall_seconds=5,
            max_calls=1,
        )
        late = json.loads(
            (tmp_path / "events.jsonl").read_text().splitlines()[0]
        )["late_pid"]
        assert result["stop_reason"] == "call_limit"
        assert result["cleanup_ok"]
        assert late in result["observed_pids"]
        with pytest.raises(ProcessLookupError):
            os.kill(late, 0)
        assert unrelated.poll() is None
        assert unrelated.pid not in result["observed_pids"]
    finally:
        unrelated.kill()
        unrelated.wait()


_ORPHANING_CHILD = """import pathlib, signal, subprocess, sys, time
signal.alarm(20)
go, pidfile = map(pathlib.Path, sys.argv[1:3])
orphan = subprocess.Popen(
    [sys.executable, '-c', 'import time; time.sleep(20)'],
    start_new_session=True,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
staged = pidfile.with_suffix('.tmp')
staged.write_text(str(orphan.pid))
staged.rename(pidfile)
while not go.exists():
    time.sleep(0.001)
"""


def test_watchdog_cleanup_stops_observed_descendant_after_its_parent_exits(
    tmp_path, monkeypatch
):
    """A new-session descendant seen by one real scan stays owned once orphaned.

    The child exits only after a real process-table scan has listed its
    grandchild, so at cleanup the grandchild has another parent and another
    process group; it is found only because a poll observed it.
    """
    import run_agent_plot_eval as capture

    go, pidfile = tmp_path / "go", tmp_path / "orphan.pid"
    scan = capture._process_table

    def scan_then_release():
        """Let the child exit once a real scan has listed the grandchild."""
        table = scan()
        if pidfile.exists() and int(pidfile.read_text()) in table:
            go.write_text("go")
        return table

    monkeypatch.setattr(capture, "_process_table", scan_then_release)
    result = capture_process(
        [sys.executable, "-c", _ORPHANING_CHILD, str(go), str(pidfile)],
        tmp_path,
        dict(os.environ),
        tmp_path / "events.jsonl",
        tmp_path / "stderr.txt",
        wall_seconds=5,
    )
    orphan = int(pidfile.read_text())
    assert result["stop_reason"] == "exit"
    assert result["returncode"] == 0
    assert result["cleanup_ok"]
    assert orphan in result["observed_pids"]
    with pytest.raises(ProcessLookupError):
        os.kill(orphan, 0)


class _ReadSeam:
    """Stand-in for the watchdog's ``os`` that hooks every stream read."""

    def __init__(self, after_read):
        self.after_read = after_read

    def __getattr__(self, name):
        return getattr(os, name)

    def read(self, fd, size):
        data = os.read(fd, size)
        self.after_read(len(data))
        return data


def _gone(pid, process_table):
    """Whether a process has exited (absent or a zombie) in a real ``ps`` table."""
    row = process_table().get(pid)
    return row is None or "Z" in row[2]


_DRAINING_PARENT_CHILD = '''import pathlib, signal, subprocess, sys
signal.alarm(20)
release = pathlib.Path(sys.argv[2])
middle = """import os, pathlib, subprocess, sys, time
spawn, release, pids = map(pathlib.Path, sys.argv[1:4])
while not spawn.exists():
    time.sleep(0.001)
grandchild = subprocess.Popen(
    [sys.executable, '-c', 'import time; time.sleep(20)'],
    start_new_session=True,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
staged = pids.with_suffix('.tmp')
staged.write_text(f'{os.getpid()} {grandchild.pid}')
staged.rename(pids)
while not release.exists():
    time.sleep(0.001)
"""
subprocess.Popen(
    [sys.executable, '-c', middle, *sys.argv[1:4]],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
line = 'x' * 16383
while not release.exists():
    print(line, flush=True)
'''


def test_watchdog_keeps_polling_while_output_drains(tmp_path, monkeypatch):
    """Continuous output cannot postpone the next owned-tree poll by a cooldown.

    Right after the first poll, a middle process starts a new-session
    grandchild; it exits once the watchdog has read 4 MiB more output, which
    leaves the grandchild with another parent and process group. Only scans
    move the watchdog clock, so a scan starts during that output only if
    processed output itself starts one: a scan before each chunk (the original
    loop) or after each 1 MiB does, while a cooldown measured on the clock
    never ends and the grandchild escapes. A scan already under way when the
    4 MiB are reached is allowed to finish first.
    """
    import run_agent_plot_eval as capture

    spawn, release = tmp_path / "spawn", tmp_path / "release"
    pids = tmp_path / "pids"
    state = {"after_spawn": 0}
    scanning = threading.Event()
    real_table = capture._process_table
    _scan_driven_clock(monkeypatch, lambda: None)
    scan = capture._process_table

    def scan_then_spawn():
        """After the first scan, wait until the grandchild exists."""
        scanning.set()
        try:
            table = scan()
            if not spawn.exists():
                spawn.write_text("go")
                deadline = time.monotonic() + 5
                while not pids.exists() and time.monotonic() < deadline:
                    time.sleep(0.001)
            return table
        finally:
            scanning.clear()

    def count_and_release(size):
        """After 4 MiB more output, let the middle process exit and wait."""
        if not pids.exists() or release.exists():
            return
        state["after_spawn"] += size
        if state["after_spawn"] > 4 * 1024 * 1024:
            # A scan already under way may finish before the middle exits.
            deadline = time.monotonic() + 5
            while scanning.is_set() and time.monotonic() < deadline:
                time.sleep(0.001)
            release.write_text("go")
            middle = int(pids.read_text().split()[0])
            deadline = time.monotonic() + 5
            while not _gone(middle, real_table) and time.monotonic() < deadline:
                time.sleep(0.001)

    monkeypatch.setattr(capture, "_process_table", scan_then_spawn)
    monkeypatch.setattr(capture, "os", _ReadSeam(count_and_release))
    result = capture_process(
        [
            sys.executable,
            "-c",
            _DRAINING_PARENT_CHILD,
            str(spawn),
            str(release),
            str(pids),
        ],
        tmp_path,
        dict(os.environ),
        tmp_path / "events.jsonl",
        tmp_path / "stderr.txt",
        wall_seconds=5,
    )
    grandchild = int(pids.read_text().split()[1])
    assert result["cleanup_ok"]
    assert grandchild in result["observed_pids"]
    with pytest.raises(ProcessLookupError):
        os.kill(grandchild, 0)


_TRICKLE_CHILD = """import signal, sys, time
signal.alarm(20)
for _ in range(64):
    print('x' * 4095, flush=True)
    time.sleep(0.001)
"""


def test_watchdog_keeps_reading_while_a_scan_runs(tmp_path, monkeypatch):
    """A slow process-table scan does not stop the pipes from being read.

    The first scan is held open until 16 KiB more output has been read from
    the child's pipes, for at most 5 s; the child writes 256 KiB and exits. A
    watchdog that reads only between scans reads nothing while the scan is
    held, so the deadline passes.
    """
    import run_agent_plot_eval as capture

    state = {"read": 0, "held_scans": 0, "read_during_scan": False}
    scan = capture._process_table

    def count(size):
        """Count bytes read from the child's pipes."""
        state["read"] += size

    def held_scan():
        """Hold the first scan until the pipes have yielded 16 KiB more."""
        target = state["read"] + 16 * 1024
        table = scan()
        if not state["held_scans"]:
            state["held_scans"] += 1
            deadline = time.monotonic() + 5
            while state["read"] < target and time.monotonic() < deadline:
                time.sleep(0.001)
            state["read_during_scan"] = state["read"] >= target
        return table

    monkeypatch.setattr(capture, "_process_table", held_scan)
    monkeypatch.setattr(capture, "os", _ReadSeam(count))
    result = capture_process(
        [sys.executable, "-c", _TRICKLE_CHILD],
        tmp_path,
        dict(os.environ),
        tmp_path / "events.jsonl",
        tmp_path / "stderr.txt",
        wall_seconds=5,
    )
    assert state["read_during_scan"]
    assert result["stop_reason"] == "exit"
    assert result["cleanup_ok"]


def _child_ps_pids():
    """Running ``ps`` processes started by this test process, besides the probe."""
    probe = subprocess.Popen(
        ["/bin/ps", "-axo", "pid=,ppid=,comm="],
        stdout=subprocess.PIPE,
        text=True,
    )
    out, _ = probe.communicate()
    rows = (line.split(None, 2) for line in out.splitlines())
    return [
        int(pid)
        for pid, parent, command in rows
        if int(parent) == os.getpid()
        and int(pid) != probe.pid
        and Path(command.strip()).name == "ps"
    ]


@pytest.mark.parametrize("ending", ["eof", "limit", "error"])
def test_watchdog_leaves_no_scan_or_ps_behind(tmp_path, monkeypatch, ending):
    """A scan still running when capture ends is joined on every exit path.

    Every loop scan is held for 1.5 s after ``ps`` returns (cleanup scans are
    not), so the capture ends (EOF, byte limit, or the scan's own error) while
    one is in flight, and returns before a scan left running would finish.
    """
    import run_agent_plot_eval as capture

    scan, stop = capture._process_table, capture._stop_tree
    calls = {"n": 0, "cleanup": False}

    def held_scan():
        """Hold every loop scan; the first one fails in the error case."""
        table = scan()
        if calls["cleanup"]:
            return table
        calls["n"] += 1
        time.sleep(1.5)
        if ending == "error" and calls["n"] == 1:
            raise RuntimeError("scan failed")
        return table

    def marked_stop(process, known):
        """Cleanup scans run unheld."""
        calls["cleanup"] = True
        return stop(process, known)

    monkeypatch.setattr(capture, "_process_table", held_scan)
    monkeypatch.setattr(capture, "_stop_tree", marked_stop)
    child = (
        "print('{}', flush=True)"
        if ending == "eof"
        else "import time\nwhile True:\n    print('x' * 4095, flush=True)\n"
        "    time.sleep(0.001)"
    )
    threads = set(threading.enumerate())
    run = lambda: capture_process(  # noqa: E731
        [sys.executable, "-c", child],
        tmp_path,
        dict(os.environ),
        tmp_path / "events.jsonl",
        tmp_path / "stderr.txt",
        wall_seconds=5,
        max_bytes=64 * 1024,
    )
    if ending == "error":
        with pytest.raises(RuntimeError, match="scan failed"):
            run()
    else:
        result = run()
        assert (
            result["stop_reason"]
            == {"eof": "exit", "limit": "byte_limit"}[ending]
        )
        assert result["cleanup_ok"]
    assert set(threading.enumerate()) <= threads
    assert _child_ps_pids() == []


_STREAMING_CALLS_CHILD = """import json, signal
signal.alarm(20)
call = {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'mcp__dartwork_mpl__render_plot', 'input': {'code': 'x' * 900}}]}}
line = json.dumps(call)
while True:
    print(line, flush=True)
"""


@pytest.mark.parametrize("limit", ["bytes", "calls"])
def test_watchdog_stream_limits_stop_within_one_chunk_while_draining(
    tmp_path, monkeypatch, limit
):
    """Output processed between polls is still checked after every chunk.

    Only scans move the watchdog clock, so up to 1 MiB of continuous output is
    processed between two polls. Processing stops within one 64 KiB chunk of
    the byte or call limit.
    """
    _scan_driven_clock(monkeypatch, lambda: None)
    line = len(
        json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "mcp__dartwork_mpl__render_plot",
                            "input": {"code": "x" * 900},
                        }
                    ]
                },
            }
        )
    )
    result = capture_process(
        [sys.executable, "-c", _STREAMING_CALLS_CHILD],
        tmp_path,
        dict(os.environ),
        tmp_path / "events.jsonl",
        tmp_path / "stderr.txt",
        wall_seconds=5,
        max_calls=100 if limit == "calls" else 100000,
        max_bytes=300000 if limit == "bytes" else 128 * 1024 * 1024,
    )
    assert result["cleanup_ok"]
    if limit == "bytes":
        assert result["stop_reason"] == "byte_limit"
        assert result["stream_bytes"] <= 300000 + 65536
    else:
        assert result["stop_reason"] == "call_limit"
        assert result["mcp_calls"] <= 100 + 65536 // (line + 1) + 1


def test_replay_keeps_exact_source_and_absolute_csv_until_finished(tmp_path):
    """Fresh-process replay reads the original absolute CSV without rewriting."""
    csv = tmp_path / "input.csv"
    csv.write_text("x,y\n1,2\n")
    source = tmp_path / "source.py"
    source.write_text(f"""import csv
import matplotlib.pyplot as plt
import dartwork_mpl as dm
path = {str(csv)!r}
with open(path) as f:
    rows = list(csv.DictReader(f))
dm.style.use('scientific')
figure, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([float(r['x']) for r in rows], [float(r['y']) for r in rows], linewidth=dm.lw(0))
dm.simple_layout(figure)
""")
    import io

    import matplotlib.image as mpimg
    import numpy as np

    async def original_png():
        """Render identical bytes through the production stdio exporter first."""
        parameters = StdioServerParameters(
            command=str(Path(sys.executable).parent / "dartwork-mpl-mcp"),
            env={
                **os.environ,
                "DARTWORK_MPL_ARTIFACT_DIR": str(tmp_path / "original-store"),
            },
            cwd=str(tmp_path),
        )
        async with (
            stdio_client(parameters) as (reader, writer),
            ClientSession(reader, writer) as client,
        ):
            await client.initialize()
            rendered = await client.call_tool(
                "render_plot",
                {"code": source.read_text(), "figure_var": "figure"},
            )
            assert rendered.structuredContent["delivery_status"] == "ready"
            return base64.b64decode(rendered.content[0].data)

    before = source.read_bytes(), csv.read_bytes()
    original = asyncio.run(original_png())
    result = replay(source, csv, "line", tmp_path / "replay", "figure")
    np.testing.assert_array_equal(
        mpimg.imread(io.BytesIO(original)),
        mpimg.imread(tmp_path / "replay/plot.png"),
    )
    assert result["status"] == "ok"
    assert result["source_sha256"] == hashlib.sha256(before[0]).hexdigest()
    assert result["export"]["api"] == "dartwork_mpl.save_formats"
    assert result["observed"]["panels"][0]["lines"][0]["xy"] == [[1.0, 2.0]]
    assert (tmp_path / "replay/plot.png").read_bytes().startswith(b"\x89PNG")
    assert (source.read_bytes(), csv.read_bytes()) == before
    assert result["assessment"]["passed"] is False


def test_review_requires_selected_image_and_successful_report_receipt():
    """A template image or failed resource read cannot stand in for artifact review."""
    calls = [
        {
            "type": "tool_use",
            "id": "render",
            "name": "mcp__dartwork_mpl__render_plot",
            "input": {"code": "generated"},
        },
        {
            "type": "tool_use",
            "id": "report",
            "name": "ReadMcpResourceTool",
            "input": {"uri": "dartwork-mpl://artifacts/chosen/report.json"},
        },
    ]
    metadata = {
        "delivery_status": "ready",
        "artifact_id": "chosen",
        "files": [],
    }
    render = {
        "type": "tool_result",
        "tool_use_id": "render",
        "content": [
            {"type": "image", "data": "png"},
            {"type": "text", "text": json.dumps(metadata)},
        ],
    }
    report = {
        "type": "tool_result",
        "tool_use_id": "report",
        "content": [
            {
                "type": "text",
                "text": json.dumps({"status": "ok", "failed_checks": []}),
            }
        ],
    }
    events = [
        {"type": "assistant", "message": {"content": calls}},
        {"type": "user", "message": {"content": [render, report]}},
    ]
    assert _stage_review(events)["status"] == "ok"
    report["is_error"] = True
    assert "report_not_read" in _stage_review(events)["reasons"]
    report["is_error"] = False
    render["content"].pop(0)
    events.append(
        {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "unrelated-template",
                        "content": [{"type": "image", "data": "png"}],
                    }
                ]
            },
        }
    )
    assert "image_not_exposed" in _stage_review(events)["reasons"]


def test_capture_accepts_builtin_inventory_and_rejects_custom_context(tmp_path):
    """Observed builtins are host metadata; custom agents/plugins remain contamination."""
    csv = tmp_path / "input.csv"
    csv.write_bytes(b"x,y\n1,2\n")
    digest = hashlib.sha256(csv.read_bytes()).hexdigest()
    # Sanitized from the actual 2.1.303 smoke init: no user paths or credentials.
    initialized = {
        "type": "system",
        "subtype": "init",
        "model": "selected",
        "tools": [
            "Read",
            "ListMcpResourcesTool",
            "ReadMcpResourceTool",
            "mcp__dartwork_mpl__render_plot",
        ],
        "mcp_servers": [
            {"name": "dartwork_mpl", "status": "connected", "source": "dynamic"}
        ],
        "agents": [
            "claude",
            "Explore",
            "general-purpose",
            "Plan",
            "statusline-setup",
        ],
        "skills": [],
        "plugins": [
            {"name": name, "path": "builtin", "source": name + "@builtin"}
            for name in (
                "cc-plugin-agents-md",
                "cc-plugin-telemetry",
                "cc-plugin-plugin-authoring",
            )
        ],
        "additional_directories": [],
    }
    terminal = {"type": "result", "subtype": "success", "is_error": False}
    path = tmp_path / "events.jsonl"
    path.write_text(
        json.dumps(initialized) + "\n" + json.dumps(terminal) + "\n"
    )
    assert validate_capture(path, csv, digest, "selected")["status"] == "ok"
    for mutation in (
        "agent",
        "plugin_name",
        "plugin_path",
        "plugin_source",
        "skills",
        "directory",
        "tool",
        "mcp",
    ):
        changed = json.loads(json.dumps(initialized))
        if mutation == "agent":
            changed["agents"].append("custom-agent")
        elif mutation.startswith("plugin_"):
            changed["plugins"][0][mutation.removeprefix("plugin_")] = "custom"
        elif mutation == "skills":
            changed["skills"] = ["custom-skill"]
        elif mutation == "directory":
            changed["additional_directories"] = ["/outside"]
        elif mutation == "tool":
            changed["tools"].append("Bash")
        else:
            changed["mcp_servers"].append(
                {"name": "other", "status": "connected"}
            )
        path.write_text(
            json.dumps(changed) + "\n" + json.dumps(terminal) + "\n"
        )
        assert (
            validate_capture(path, csv, digest, "selected")["status"]
            == "failed"
        ), mutation


def test_stage_budget_reservations_never_exceed_authorized_corpus_cap(tmp_path):
    """Explicit repair consumes only unused smoke caps and duplicate stages refuse."""
    ledger = tmp_path / "corpus.json"
    ledger.write_text(json.dumps({"attempts": ["smoke/line"], "started_at": 0}))
    old = tmp_path / "smoke/line/original"
    old.mkdir(parents=True)
    (old / "invocation.json").write_text(json.dumps({"budget_usd": 0.4}))
    for stage in ("original", "revision", "recovery"):
        assert (
            _reserve_stage(tmp_path, "smoke-repair/line/" + stage, 0.2)[
                "status"
            ]
            == "ok"
        )
    for label in ("baseline", "candidate"):
        for case in ("line", "groupedbar", "scatter", "custom2panel"):
            for stage, cap in (
                ("original", 2),
                ("revision", 2),
                ("recovery", 1),
            ):
                assert (
                    _reserve_stage(tmp_path, f"{label}/{case}/{stage}", cap)[
                        "status"
                    ]
                    == "ok"
                )
    before = ledger.read_bytes()
    assert json.loads(before)["invoked_budget_usd_cap"] == 41
    assert (
        _reserve_stage(tmp_path, "extra", 0.01)["reason"]
        == "corpus_budget_limit"
    )
    assert (
        _reserve_stage(tmp_path, "baseline/line/original", 2)["reason"]
        == "stage_already_attempted"
    )
    assert ledger.read_bytes() == before


def test_repair_admission_only_accepts_recorded_builtin_harness_failure():
    """The one repair cannot become a model-quality or partial-stage retry."""
    original = {
        "status": "failed",
        "stop_reason": "original_integration_failed",
        "stages": {
            "original": {
                "capture": {
                    "status": "failed",
                    "reasons": ["unexpected_context"],
                },
                "process": {
                    "stop_reason": "exit",
                    "returncode": 0,
                    "cleanup_ok": True,
                },
                "review": {"status": "ok"},
            }
        },
    }
    assert _repair_admission(original, 0.4)
    assert not _repair_admission(original, 0.2)
    for mutation in (
        "extra_stage",
        "quality_failure",
        "process_failure",
        "cleanup_failure",
        "failed_review",
        "other_reason",
    ):
        changed = json.loads(json.dumps(original))
        stage = changed["stages"]["original"]
        if mutation == "extra_stage":
            changed["stages"]["revision"] = {}
        elif mutation == "quality_failure":
            changed["stop_reason"] = "render_failed"
        elif mutation == "process_failure":
            stage["process"]["returncode"] = 1
        elif mutation == "cleanup_failure":
            stage["process"]["cleanup_ok"] = False
        elif mutation == "failed_review":
            stage["review"]["status"] = "failed"
        else:
            stage["capture"]["reasons"].append("oracle_access")
        assert not _repair_admission(changed, 0.4), mutation


def _write_test_admission(root: Path, review: str = "passed") -> None:
    """Create evaluator-owned admission evidence for an account-free host fixture."""
    (root / "runtime").mkdir(parents=True, exist_ok=True)
    smoke_runs = {}
    for relative in ("smoke/line/run.json", "smoke-repair/line/run.json"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"status": "failed"}))
        smoke_runs[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    record = {
        "policy": "phase0-observed-infrastructure-2026-10-20",
        "code_review": review,
        "smoke_runs": smoke_runs,
        "fresh_agent_recovery": "unverified",
        "observed": dict.fromkeys(
            (
                "image",
                "full_report",
                "resume",
                "configured_model",
                "cleanup",
                "real_stdio_recovery",
            ),
            True,
        ),
    }
    (root / "runtime/admission-decision.json").write_text(json.dumps(record))


@pytest.mark.parametrize("replay_limited", [False, True])
def test_failed_revision_keeps_exact_replay_before_workspace_cleanup(
    tmp_path, monkeypatch, replay_limited
):
    """A final report omission still preserves replay evidence before CSV deletion."""
    import time

    import run_agent_plot_eval as capture

    root = tmp_path / "evidence"
    (root / "runtime").mkdir(parents=True)
    (root / "runtime/selection.json").write_text(
        json.dumps({"model": "selected", "effort": "high"})
    )
    (root / "corpus.json").write_text(
        json.dumps({"started_at": time.time(), "attempts": []})
    )
    _write_test_admission(root)
    host = tmp_path / "owned-host"
    # Our synthetic host adapter executes the real stdio server, not a model.
    # Its revision deliberately omits report access. No live account is invoked.
    host.write_text(
        f"#!{sys.executable}\n"
        + r'''import asyncio, json, os, re, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl
args = sys.argv
config = json.load(open(args[args.index('--mcp-config') + 1]))['mcpServers']['dartwork_mpl']
revision = '--resume' in args
recovery = args[-1].startswith('Reopen both stored artifacts')
session = args[args.index('--resume' if revision else '--session-id') + 1]
code = """import csv
import matplotlib.pyplot as plt
import dartwork_mpl as dm
with open('line.csv') as handle:
    rows = [r for r in csv.DictReader(handle) if r['y'] not in ('', 'NA')]
dm.style.use('scientific')
fig, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([float(r['x']) for r in rows], [float(r['y']) for r in rows], linewidth=dm.lw(0))
dm.simple_layout(fig)
"""
if revision: code += "ax.set_title('revision')\n"
def emit(value):
    print(json.dumps(value), flush=True)
async def main():
    params = StdioServerParameters(command=config['command'], cwd=os.getcwd(), env={**os.environ, **config['env']})
    async with stdio_client(params) as (r, w), ClientSession(r, w) as client:
        await client.initialize()
        emit({'type':'system','subtype':'init','session_id':session,'model':'selected','tools':['Read','ReadMcpResourceTool','mcp__dartwork_mpl__render_plot'],'mcp_servers':[{'name':'dartwork_mpl','status':'connected'}]})
        if recovery:
            assert not os.path.exists('line.csv')
            for index, identity in enumerate(re.findall(r'\b[0-9a-f]{32}\b', args[-1])):
                call_id='get'+str(index)
                emit({'type':'assistant','message':{'content':[{'type':'tool_use','id':call_id,'name':'mcp__dartwork_mpl__get_plot_artifact','input':{'artifact_id':identity}}]}})
                stored=await client.call_tool('get_plot_artifact', {'artifact_id':identity})
                emit({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':call_id,'content':[b.model_dump(mode='json') for b in stored.content]}]}})
                uri='dartwork-mpl://artifacts/'+identity+'/report.json'
                emit({'type':'assistant','message':{'content':[{'type':'tool_use','id':'report'+str(index),'name':'ReadMcpResourceTool','input':{'uri':uri}}]}})
                report=await client.read_resource(AnyUrl(uri))
                emit({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'report'+str(index),'content':[{'type':'text','text':report.contents[0].text}]}]}})
            emit({'type':'result','subtype':'success','session_id':session,'is_error':False,'usage':{},'total_cost_usd':0,'modelUsage':{'selected':{}}})
            return
        emit({'type':'assistant','message':{'content':[{'type':'tool_use','id':'render','name':'mcp__dartwork_mpl__render_plot','input':{'code':code}}]}})
        rendered = await client.call_tool('render_plot', {'code':code})
        emit({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'render','content':[b.model_dump(mode='json') for b in rendered.content]}]}})
        if not revision:
            uri='dartwork-mpl://artifacts/'+rendered.structuredContent['artifact_id']+'/report.json'
            emit({'type':'assistant','message':{'content':[{'type':'tool_use','id':'report','name':'ReadMcpResourceTool','input':{'uri':uri}}]}})
            report=await client.read_resource(AnyUrl(uri))
            emit({'type':'user','message':{'content':[{'type':'tool_result','tool_use_id':'report','content':[{'type':'text','text':report.contents[0].text}]}]}})
        emit({'type':'result','subtype':'success','session_id':session,'is_error':False,'usage':{},'total_cost_usd':0,'modelUsage':{'selected':{}}})
asyncio.run(main())
'''
    )
    host.chmod(0o700)
    monkeypatch.setattr(capture, "_HOST", host)
    if replay_limited:
        real_replay = capture.replay

        def lowered_replay(*args, **kwargs):
            """Apply a tiny remaining replay allowance without changing source bytes."""
            evidence = args[3].parents[1]
            used = sum(
                path.stat().st_size
                for path in evidence.rglob("*")
                if path.is_file()
            )
            kwargs.update(
                evidence_root=evidence, max_evidence_bytes=used + 2048
            )
            return real_replay(*args, **kwargs)

        monkeypatch.setattr(capture, "replay", lowered_replay)
    directory = capture.run_episode("line", "baseline", root)
    state = json.loads((directory / "run.json").read_text())
    if replay_limited:
        assert state["stop_reason"] == "replay_evidence_limit"
        assert state["status"] == "failed"
        assert state["infrastructure_status"] == "failed"
        assert list(state["stages"]) == ["original"]
        assert state["replays"]["original"]["stop_reason"] == "evidence_limit"
        assert not (directory / "revision").exists()
        assert not (directory / "recovery").exists()
        ledger = json.loads((root / "corpus.json").read_text())
        assert set(ledger["stage_invocations"]) == {"baseline/line/original"}
        assert state["workspace_cleanup"]
        return
    assert state["stages"]["recovery"]["review"]["status"] == "ok"
    assert state["status"] == "failed"
    assert state["stop_reason"] == "workflow_failed"
    assert state["infrastructure_status"] == "ok"
    assert state["workflow_status"] == "failed"
    recovery_events = [
        json.loads(line)
        for line in (directory / "recovery/events.jsonl")
        .read_text()
        .splitlines()
    ]
    recovery_calls = [
        block["name"]
        for event in recovery_events
        if event.get("type") == "assistant"
        for block in event["message"]["content"]
        if block.get("type") == "tool_use"
    ]
    assert recovery_calls.count("mcp__dartwork_mpl__get_plot_artifact") == 2
    assert "mcp__dartwork_mpl__render_plot" not in recovery_calls
    assert state["recovery_hashes"]

    assert state["stages"]["revision"]["review"]["reasons"] == [
        "report_not_read"
    ]
    assert state["replays"]["revision"]["status"] == "ok"
    assert state["replays"]["revision"]["assessment"]["passed"]
    assert state["workspace_cleanup"]
    invocation = json.loads(
        (directory / "revision/invocation.json").read_text()
    )
    assert not Path(invocation["cwd"]).exists()
    assert (directory / "revision/source.py").read_bytes()
    assert (directory / "replay/revision/plot.png").exists()
    evaluated = evaluate(directory)
    assert evaluated["dimensions"]["delivery"]["passed"]
    assert evaluated["dimensions"]["declared_validation"]["passed"]
    assert evaluated["dimensions"]["semantic_replay"]["passed"]
    assert evaluated["dimensions"]["model_review"]["status"] == "failed"
    assert evaluated["dimensions"]["visual_review"]["status"] == "unchecked"
    assert evaluated["dimensions"]["human_code_edits"]["status"] == "unchecked"


def test_scored_admission_binds_both_failed_smokes_and_unknown_agent_recovery(
    tmp_path,
):
    """The explicit partial-readiness decision never upgrades smoke or missing recovery."""
    (tmp_path / "runtime").mkdir()
    evidence = {}
    for relative in ("smoke/line/run.json", "smoke-repair/line/run.json"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"status": "failed"}))
        evidence[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    decision = {
        "policy": "phase0-observed-infrastructure-2026-10-20",
        "code_review": "passed",
        "smoke_runs": evidence,
        "fresh_agent_recovery": "unverified",
        "observed": dict.fromkeys(
            (
                "image",
                "full_report",
                "resume",
                "configured_model",
                "cleanup",
                "real_stdio_recovery",
            ),
            True,
        ),
    }
    record = tmp_path / "runtime/admission-decision.json"
    record.write_text(json.dumps(decision))
    assert _admission_decision(tmp_path)["status"] == "ok"
    decision["code_review"] = "pending"
    record.write_text(json.dumps(decision))
    assert _admission_decision(tmp_path)["status"] == "failed"
    decision["code_review"] = "passed"
    decision["fresh_agent_recovery"] = "passed"
    record.write_text(json.dumps(decision))
    assert _admission_decision(tmp_path)["status"] == "failed"
    decision["fresh_agent_recovery"] = "unverified"
    record.write_text(json.dumps(decision))
    (tmp_path / "smoke/line/run.json").write_text(json.dumps({"status": "ok"}))
    assert _admission_decision(tmp_path)["status"] == "failed"
    assert not (tmp_path / "baseline").exists()


def test_evidence_copies_and_appends_refuse_bytes_above_ceiling(tmp_path):
    """Collector copies and top-level transcript duplication share the evidence cap."""
    from run_agent_plot_eval import _write_bytes

    (tmp_path / "existing").write_bytes(b"12345678")
    target = tmp_path / "member"
    assert not _write_bytes(target, b"123", tmp_path, max_bytes=10)
    assert not target.exists()
    assert _write_bytes(target, b"12", tmp_path, max_bytes=10)
    assert not _write_bytes(target, b"3", tmp_path, append=True, max_bytes=10)
    assert target.read_bytes() == b"12"


@pytest.mark.parametrize("label", ["baseline", "candidate"])
@pytest.mark.parametrize("admission", ["missing", "pending", "changed"])
def test_public_episode_rejects_admission_before_collector_or_host(
    tmp_path, monkeypatch, label, admission
):
    """Every scored entry point enforces the review decision before external work."""
    import run_agent_plot_eval as capture

    root = tmp_path / "corpus"
    _write_test_admission(
        root, "pending" if admission == "pending" else "passed"
    )
    (root / "runtime/selection.json").write_text(
        json.dumps({"model": "selected", "effort": "high"})
    )
    if admission == "missing":
        (root / "runtime/admission-decision.json").unlink()
    elif admission == "changed":
        (root / "smoke/line/run.json").write_text(json.dumps({"status": "ok"}))
    calls = []

    def collector_tripwire(request, output_dir):
        """Record an erroneously reached owned adapter without starting any host."""
        calls.append("collector")
        return {"status": "failed", "reason": "tripwire"}

    monkeypatch.setattr(capture, "_collect", collector_tripwire)
    directory = capture.run_episode("line", label, root)
    state = json.loads((directory / "run.json").read_text())
    assert calls == []
    assert state["status"] == "failed"
    assert state["stop_reason"] == "admission_rejected"
    assert state["admission_decision"]["status"] == "failed"
    assert state["stages"] == {}
    assert not (directory / "original").exists()
    assert not (root / "corpus.json").exists()


@pytest.mark.parametrize("output", ["stdout", "stderr", "members"])
def test_replay_enforces_shared_evidence_limit_during_execution(
    tmp_path, output
):
    """Replay streams and generated members cannot consume prior episode capacity."""
    csv = tmp_path / "input.csv"
    csv.write_text("x,y\n1,2\n")
    source = tmp_path / "source.py"
    source.write_text(
        """import matplotlib.pyplot as plt
import dartwork_mpl as dm
dm.style.use('scientific')
fig, ax = plt.subplots(figsize=dm.figsize('6cm', 'square'))
ax.plot([1], [2], linewidth=dm.lw(0))
dm.simple_layout(fig)
"""
        + (
            "print('x' * (512 * 1024))\n"
            if output == "stdout"
            else "raise ValueError('x' * (512 * 1024))\n"
            if output == "stderr"
            else ""
        )
    )
    cap = 128 * 1024 if output != "members" else 4 * 1024
    (tmp_path / "prior-evidence").write_bytes(b"a" * (cap // 2))
    before = csv.read_bytes(), source.read_bytes()
    result = replay(
        source,
        csv,
        "line",
        tmp_path / "replay",
        evidence_root=tmp_path,
        max_evidence_bytes=cap,
    )
    assert result["status"] == "failed"
    assert result["stop_reason"] == "evidence_limit"
    assert result["process"]["cleanup_ok"]
    assert (csv.read_bytes(), source.read_bytes()) == before
    assert (
        sum(
            path.stat().st_size
            for path in tmp_path.rglob("*")
            if path.is_file()
        )
        <= cap
    )
    assert (
        json.loads((tmp_path / "replay/result.json").read_text())["stop_reason"]
        == "evidence_limit"
    )
    if output != "members":
        partial = tmp_path / "replay" / (output + ".txt")
        assert 0 < partial.stat().st_size < 512 * 1024
