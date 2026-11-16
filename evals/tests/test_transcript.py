"""Finding the script an agent ran, and what it wrote there, from Bash calls."""

from __future__ import annotations

from pathlib import Path

from evals import harness, judge


def trace(*commands: str) -> judge.Trace:
    t = judge.Trace()
    t.calls = [{"name": "Bash", "input": {"command": c}} for c in commands]
    return t


def test_script_run_sees_flags_args_and_redirections():
    t = trace(
        "ls && cat data.csv",
        "cat > /tmp/p.py <<'EOF'\nprint(1)\nEOF\npython3 -I /tmp/p.py a.csv out.png 2>&1 | tail",
    )
    assert harness.script_run(t) == ("/tmp/p.py", ["a.csv", "out.png"])


def test_script_outside_the_project_comes_from_the_transcript(tmp_path: Path):
    t = trace(
        "cat > /tmp/p.py <<'EOF'\nold\nEOF",
        "cat > /tmp/p.py <<'EOF'\nimport matplotlib\nEOF\npython3 /tmp/p.py",
    )
    assert (
        harness.script_source(t, tmp_path, "/tmp/p.py") == "import matplotlib"
    )


def test_script_inside_the_project_is_read_from_disk(tmp_path: Path):
    (tmp_path / "plot.py").write_text("on disk")
    t = trace("cat > plot.py <<'EOF'\nwritten\nEOF")
    assert harness.script_source(t, tmp_path, "plot.py") == "on disk"
