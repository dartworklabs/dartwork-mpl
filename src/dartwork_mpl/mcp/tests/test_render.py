"""``render`` through real child processes: the bundle, each outcome and each safety measure."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

from dartwork_mpl.mcp import library
from dartwork_mpl.mcp.model import MAX_FILE_BYTES, MAX_LOG_BYTES, RenderRequest
from dartwork_mpl.mcp.render import render

POSIX = os.name == "posix"
CHART = """
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("report")
fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=3, n_series=1))
ax.plot([0, 1, 2], [1, 3, 2])
ax.set(xlabel="Time (s)", ylabel="Response")
dm.simple_layout(fig)
"""


def go(code: str, out: Path, **kwargs):
    request = RenderRequest.parse(code, out_dir=str(out), **kwargs)
    return render(request, library.lint(code))


def printed(code: str, out: Path) -> dict:
    """Run ``code`` that prints one JSON line before drawing CHART."""
    _, report, _ = go(code + CHART, out)
    assert report.outcome.status == "rendered", report.to_json()
    return json.loads(report.stdout.text.splitlines()[0])


def test_a_chart_renders_into_a_bundle_whose_manifest_hashes_every_file(
    tmp_path,
) -> None:
    data = tmp_path / "data.csv"
    data.write_text("x,y\n0,1\n")
    out, report, manifest = go(CHART, tmp_path / "b", inputs=[str(data)])
    assert sorted(p.name for p in out.iterdir()) == [
        "figure.pdf",
        "figure.png",
        "manifest.json",
        "report.json",
        "source.py",
    ]
    assert report.outcome.status == manifest.status == "rendered"
    for f in manifest.files:
        body = (out / f.path).read_bytes()
        assert (hashlib.sha256(body).hexdigest(), len(body)) == (
            f.sha256,
            f.bytes,
        )
    assert manifest.inputs[0].path == str(data)
    assert manifest.canvas and manifest.canvas.width_px > 0
    on_disk = json.loads((out / "manifest.json").read_text())
    assert (on_disk["schema"], on_disk["version"]) == ("dartwork-mpl.bundle", 1)


def test_a_critical_lint_finding_stops_the_code_before_it_runs(
    tmp_path,
) -> None:
    marker = tmp_path / "ran"
    code = f"open({str(marker)!r}, 'w')\n" + CHART.replace(
        "figsize=dm.figsize_for(n_points=3, n_series=1)", "figsize=(4, 3)"
    )
    out, report, _ = go(code, tmp_path / "b")
    assert report.outcome.status == "lint_blocked"
    assert any(f.rule_id == "figsize-direct" for f in report.lint)
    assert not marker.exists() and not (out / "figure.png").exists()


def test_a_raise_reports_the_source_line_and_leaves_no_figure(tmp_path) -> None:
    out, report, _ = go(CHART + "1 / 0\n", tmp_path / "b")
    assert report.outcome.status == "raised"
    assert 'File "source.py", line 10' in report.outcome.error  # type: ignore[union-attr]
    assert not (out / "figure.png").exists()


def test_no_figure_is_reported_and_a_stale_one_is_removed(tmp_path) -> None:
    out = tmp_path / "b"
    go(CHART, out)
    _, report, manifest = go("x = 1\n", out)
    assert report.outcome.status == "no_figure"
    assert not (out / "figure.png").exists() and manifest.canvas is None


def test_an_unbound_figure_is_saved_with_a_note(tmp_path) -> None:
    out, report, _ = go(
        CHART.replace("fig,", "chart,").replace("(fig)", "(chart)"),
        tmp_path / "b",
    )
    assert report.outcome.status == "rendered"
    assert "current figure" in report.outcome.notes[0]  # type: ignore[union-attr]


def test_the_child_starts_in_an_empty_temporary_directory(tmp_path) -> None:
    seen = printed(
        "import json, os; print(json.dumps([os.getcwd(), os.listdir('.')]))\n",
        tmp_path / "b",
    )
    cwd, listing = seen
    assert listing == [] and Path(cwd) != Path.cwd()
    assert not Path(cwd).exists()  # removed after the run


def test_the_child_inherits_no_secrets_and_runs_agg(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-secret")
    monkeypatch.setenv("MPLBACKEND", "macosx")
    seen = printed(
        "import json, os, matplotlib\n"
        "print(json.dumps([dict(os.environ), matplotlib.get_backend()]))\n",
        tmp_path / "b",
    )
    env, backend = seen
    assert "ANTHROPIC_API_KEY" not in env and "GITHUB_TOKEN" not in env
    assert "sk-secret" not in json.dumps(env)
    assert (env["MPLBACKEND"], backend.lower()) == ("Agg", "agg")


def test_a_timeout_kills_the_whole_process_group(tmp_path) -> None:
    if not POSIX:
        pytest.skip("process groups are POSIX")
    pid_file = tmp_path / "grandchild.pid"
    code = (
        "import subprocess, time, pathlib\n"
        "p = subprocess.Popen(['sleep', '60'])\n"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(p.pid))\n"
        "time.sleep(60)\n"
    )
    started = time.monotonic()
    _, report, _ = go(code, tmp_path / "b", timeout=5)
    assert report.outcome.status == "timed_out"
    assert time.monotonic() - started < 30
    pid = int(pid_file.read_text())
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        pytest.fail("the grandchild outlived the timeout")


def test_rlimits_are_applied_where_the_platform_enforces_them(tmp_path) -> None:
    if not POSIX:
        pytest.skip("rlimits are POSIX")
    seen = printed(
        "import json, resource\n"
        "print(json.dumps([resource.getrlimit(resource.RLIMIT_CPU),"
        " resource.getrlimit(resource.RLIMIT_FSIZE),"
        " resource.getrlimit(resource.RLIMIT_AS)]))\n",
        tmp_path / "b",
    )
    cpu, fsize, address = seen
    assert cpu == [21, 21] and fsize == [MAX_FILE_BYTES] * 2
    if sys.platform.startswith("linux"):
        assert address[0] == 4 * 1024**3


def test_no_file_grows_past_the_size_limit(tmp_path) -> None:
    if not POSIX:
        pytest.skip("rlimits are POSIX")
    big = tmp_path / "big.bin"
    code = f"open({str(big)!r}, 'wb').write(b'0' * {MAX_FILE_BYTES + 1})\n"
    go(code + CHART, tmp_path / "b")  # Linux raises EFBIG, macOS truncates
    assert big.stat().st_size <= MAX_FILE_BYTES


def test_a_flood_of_output_is_cut_in_the_report(tmp_path) -> None:
    code = "print('x' * 200_000)\n" + CHART
    _, report, _ = go(code, tmp_path / "b")
    assert report.stdout.truncated and len(report.stdout.text) == MAX_LOG_BYTES
