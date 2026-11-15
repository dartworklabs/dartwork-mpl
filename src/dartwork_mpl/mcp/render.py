"""Run caller code once in a child process and write the bundle: the ``render`` shell.

This is **not a sandbox**. The child runs with the server user's rights and
can read, write and connect wherever that user can. What it does get:

- an empty temporary working directory, removed afterwards;
- an allow-listed environment (:data:`ENV_KEEP` plus ``MPLBACKEND=Agg``):
  API keys, tokens and anything else the server inherited are not passed;
- its own process group (session), killed whole on timeout and after exit,
  so a subprocess the code started does not outlive the run;
- CPU-seconds, address-space and file-size rlimits where the OS enforces
  them (``report.json`` ``limits`` says which took);
- a source-size bound before launch and a byte cap on the stdout and stderr
  the report quotes.

The bundle written to ``out_dir`` is ``figure.png``, ``figure.pdf`` (when
the run rendered), ``source.py``, ``report.json`` and ``manifest.json``;
see :class:`.model.Manifest`.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from . import decide
from .model import (
    BUNDLE_FILES,
    FIGURE_FILES,
    MAX_LOG_BYTES,
    ChildRun,
    FileDigest,
    LintBlocked,
    LintFinding,
    Log,
    Manifest,
    Outcome,
    Rendered,
    RenderRequest,
    Report,
)

# Variables a matplotlib child needs to find its interpreter, fonts, caches
# and locale. Nothing else crosses into the child.
ENV_KEEP = (
    *("PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP"),
    *("LANG", "LC_ALL", "LC_CTYPE", "MPLCONFIGDIR"),
    *("XDG_CACHE_HOME", "XDG_CONFIG_HOME"),
)
POSIX = os.name == "posix"


def child_env() -> dict[str, str]:
    """The child's environment: the allow-list, with the Agg backend forced."""
    env = {k: os.environ[k] for k in ENV_KEEP if k in os.environ}
    env["MPLBACKEND"] = "Agg"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def kill_group(proc: subprocess.Popen[bytes]) -> None:
    """Kill the child's whole process group (POSIX) or the child itself."""
    if POSIX:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, signal.SIGKILL)  # the group may be gone
    elif proc.poll() is None:
        proc.kill()
    proc.wait()


def head(path: Path) -> Log:
    """The first :data:`MAX_LOG_BYTES` of a log file."""
    if not path.exists():
        return Log()
    with path.open("rb") as f:
        data = f.read(MAX_LOG_BYTES + 1)
    text = data[:MAX_LOG_BYTES].decode("utf-8", "replace")
    return Log(text, len(data) > MAX_LOG_BYTES)


def run_child(
    request: RenderRequest, out_dir: Path
) -> tuple[ChildRun, Log, Log, dict[str, int | None]]:
    """Start the child, wait at most ``timeout``, kill its group, read what it left."""
    with tempfile.TemporaryDirectory(prefix="dartwork-mpl-run-") as tmp:
        run_dir = Path(tmp)
        cwd = run_dir / "cwd"
        cwd.mkdir()
        job = run_dir / "job.json"
        job.write_text(
            json.dumps(
                {
                    "source": str(out_dir / "source.py"),
                    "out_dir": str(out_dir),
                    "result": str(run_dir / "result.json"),
                    "figure_var": request.figure_var,
                    "timeout": request.timeout,
                }
            )
        )
        with (
            (run_dir / "stdout").open("wb") as out,
            (run_dir / "stderr").open("wb") as err,
        ):
            proc = subprocess.Popen(
                [sys.executable, "-m", "dartwork_mpl.mcp.child", str(job)],
                cwd=cwd,
                env=child_env(),
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                start_new_session=POSIX,
                creationflags=getattr(
                    subprocess, "CREATE_NEW_PROCESS_GROUP", 0
                ),
            )
            try:
                proc.wait(request.timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
            finally:
                kill_group(proc)
        result = run_dir / "result.json"
        limits_file = run_dir / "limits.json"
        run = ChildRun(
            timeout=request.timeout,
            timed_out=timed_out,
            returncode=proc.returncode,
            result=ChildRun.parse_result(
                result.read_text(encoding="utf-8") if result.exists() else None
            ),
        )
        limits: dict[str, int | None] = (
            json.loads(limits_file.read_text()) if limits_file.exists() else {}
        )
        return run, head(run_dir / "stdout"), head(run_dir / "stderr"), limits


def digest(path: Path, name: str | None = None) -> FileDigest:
    """A file's SHA-256 and size, named relative to the bundle or as given."""
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            sha.update(block)
    return FileDigest(name or str(path), sha.hexdigest(), path.stat().st_size)


def declared(path: str) -> FileDigest:
    """An input file's digest by the path the caller gave; a missing one is refused."""
    file = Path(path).expanduser()
    if not file.is_file():
        raise ValueError(f"input {path!r} is not a file")
    return digest(file, path)


def png_pixels(path: Path) -> tuple[int, int]:
    """A PNG's width and height, read from its header."""
    header = path.read_bytes()[16:24]
    return int.from_bytes(header[:4], "big"), int.from_bytes(header[4:], "big")


def render(
    request: RenderRequest, lint: tuple[LintFinding, ...]
) -> tuple[Path, Report, Manifest]:
    """Lint-gate, run once, write the bundle; the directory, report and manifest."""
    started = time.monotonic()
    out_dir = (
        Path(request.out_dir).expanduser().resolve()
        if request.out_dir
        else Path(tempfile.mkdtemp(prefix="dartwork-mpl-render-"))
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in BUNDLE_FILES:  # a stale figure must not pass for this run's
        (out_dir / name).unlink(missing_ok=True)
    (out_dir / "source.py").write_text(request.code, encoding="utf-8")
    inputs = tuple(declared(p) for p in request.inputs)
    outcome: Outcome = LintBlocked()
    stdout = stderr = Log()
    limits: dict[str, int | None] = {}
    if not decide.blocks(lint):
        run, stdout, stderr, limits = run_child(request, out_dir)
        outcome = decide.outcome(run)
    if isinstance(outcome, Rendered):
        width, height = png_pixels(out_dir / "figure.png")
        outcome = replace(
            outcome,
            canvas=replace(outcome.canvas, width_px=width, height_px=height),
        )
    else:
        for name in FIGURE_FILES:  # half-written output of a failed run
            (out_dir / name).unlink(missing_ok=True)
    report = Report(outcome, lint, stdout, stderr, limits)
    write_json(out_dir / "report.json", report.to_json())
    names = [*FIGURE_FILES, "source.py", "report.json"]
    manifest = Manifest(
        status=outcome.status,
        created=datetime.now(UTC).isoformat(timespec="seconds"),
        seconds=round(time.monotonic() - started, 3),
        versions={
            "dartwork-mpl": version("dartwork-mpl"),
            "matplotlib": version("matplotlib"),
            "python": platform.python_version(),
        },
        files=tuple(
            digest(out_dir / n, n) for n in names if (out_dir / n).exists()
        ),
        inputs=inputs,
        canvas=outcome.canvas if isinstance(outcome, Rendered) else None,
    )
    write_json(out_dir / "manifest.json", manifest.to_json())
    return out_dir, report, manifest


def write_json(path: Path, data: dict[str, object]) -> None:
    """Pretty, UTF-8, one trailing newline."""
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
