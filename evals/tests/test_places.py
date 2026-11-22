"""Where a path the agent used lies in a recorded run, wherever the run was copied."""

from __future__ import annotations

from pathlib import Path

from evals import harness

ROOT = "/private/var/folders/nq/T/dmpl-eval-share_bars_camps-skill-qauy3f9w"
OUT = Path("/anywhere/20261123-013112/share_bars_camps/skill")


def test_each_path_of_the_run_has_one_copy():
    places = harness.places_of(f"{ROOT}/project", ROOT, OUT)
    found = {
        f"{ROOT}/project/scripts/plot.py": "project/scripts/plot.py",
        f"{ROOT.removeprefix('/private')}/tmp/s/plot.py": "tmp/s/plot.py",
        # beside the project: ``uv run python ../scripts/plot_outlook.py``
        f"{ROOT}/scripts/plot_outlook.py": "root/scripts/plot_outlook.py",
        f"{ROOT}/home/plot.py": "root/home/plot.py",
    }
    for path, copy in found.items():
        assert harness.local(path, places) == OUT / copy
    assert harness.local("/tmp/s/plot.py", places) is None


def test_a_run_from_before_the_root_has_only_its_project():
    places = harness.places_of("/T/dmpl-eval-x", None, OUT)
    assert (
        harness.local("/T/dmpl-eval-x/plot.py", places)
        == OUT / "project/plot.py"
    )
    assert harness.local("/T/scripts/plot.py", places) is None


def test_the_probe_stays_importable_when_the_agent_set_pythonpath():
    # ``PYTHONPATH=. uv run python plot.py``: the agent's path once replaced
    # the repository's, and ``python -m evals.probe`` was not found.
    env = harness.probe_env(
        {"PATH": "/bin", "CLAUDE_CODE": "1", "MPLBACKEND": "macosx"},
        (("PYTHONPATH", f"{ROOT}/project"), ("MPLBACKEND", "Agg")),
        lambda text: text.replace(ROOT, "/mirror"),
    )
    assert env["PYTHONPATH"].split(":") == [
        str(harness.REPO),
        "/mirror/project",
    ]
    assert env["MPLBACKEND"] == "Agg"
    assert "CLAUDE_CODE" not in env
    plain = harness.probe_env({"MPLBACKEND": "macosx"}, (), str)
    assert plain == {"PYTHONPATH": str(harness.REPO)}
