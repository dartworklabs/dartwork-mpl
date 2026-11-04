"""Calibration controls from the real baseline run (baseline-main-20261022).

Each fixture in ``fixtures/calibration/`` is an agent's final ``plot.py``
copied verbatim from one baseline unit (``*.plot.txt`` so lint and format
hooks never rewrite it; provenance in ``index.json``). Three kinds:

* must pass: the pre-calibration scorer failed the unit, the audit
  (``calibration/2026-10-22-baseline-audit.md``) judged the figure correct;
* must fail: the audit's true failure (an edit the agent never executed);
* mutations: a real source changed to fabricate data, hide a unit or add an
  unrequested text must fail, so the general rules do not over-accept;
* contamination: the real tool calls the old ``../`` rule flagged stay
  inside the project; climbing into another project, the records or the
  repo is still contamination.

Not collected by the default ``pytest`` run. Run explicitly:

    uv run pytest evals/agentic/test_calibration.py -q
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import run as runner  # noqa: E402
import score  # noqa: E402

REPO = HERE.parents[1]
CAL = HERE / "fixtures" / "calibration"
INDEX = json.loads((CAL / "index.json").read_text())
PYTHON = REPO / ".venv" / "bin" / "python"


def _project(root: Path, case: dict, source: str) -> Path:
    root.mkdir(parents=True)
    (root / "data").mkdir()
    for name in case["data"]:
        (root / "data" / name).write_bytes(
            (HERE / "fixtures" / "data" / name).read_bytes()
        )
    (root / "plot.py").write_text(source, encoding="utf-8")
    return root


def _source(name: str, mutate: tuple[str, str] | None = None) -> str:
    src = (CAL / name).read_text(encoding="utf-8")
    if mutate:
        old, new = mutate
        assert old in src, f"mutation anchor missing in {name}: {old!r}"
        src = src.replace(old, new)
    return src


def _evaluate(tmp_path: Path, name: str, mutate=None) -> dict:
    case = common.load_cases([INDEX[name]["case"]])[0]
    project = _project(tmp_path / "agent", case, _source(name, mutate))
    probe = score.run_probe(PYTHON, project)
    base = None
    if case["kind"] == "edit":
        bdir = _project(
            tmp_path / "base",
            case,
            (HERE / "fixtures" / "base" / case["base"]).read_text(),
        )
        base = score.run_probe(PYTHON, bdir)
    rec = score.evaluate(case, probe, base)
    rec["failing"] = [
        f"{c['name']}: {c['detail']}"
        for c in rec["checks"]
        if c["ok"] is not True
    ]
    pres = rec.get("preservation") or {}
    if pres.get("ok") is False:
        rec["failing"].append(f"preservation: {pres}")
    return rec


MUST_PASS = sorted(n for n, v in INDEX.items() if v["expect"] == "must pass")


@pytest.mark.parametrize("name", MUST_PASS)
def test_real_correct_output_passes(name, tmp_path):
    rec = _evaluate(tmp_path, name)
    assert rec["rerun_ok"], rec["rerun_error"]
    assert score.checks_pass(rec), rec["failing"]


MUTATIONS = {
    "context_lines_shifted": (
        "claude-g09-small-multiples-ko.plot.txt",
        (
            "ax.plot(wide.index, wide[other],",
            "ax.plot(wide.index, wide[other] + 3,",
        ),
    ),
    "scale_unit_hidden": (
        "claude-g10-dashboard-kpi.plot.txt",
        (" (thousands)", ""),
    ),
    "leader_not_from_data": (
        "codex-g24-vague-ko.plot.txt",
        (
            "ax.plot([3.04, 3.19, 3.28], [values[-1],",
            "ax.plot([2.2, 3.19, 3.28], [values[-1] + 90,",
        ),
    ),
    "statistic_marker_moved": (
        "codex-g06-hist-response.plot.txt",
        ("ecdf.scatter(p95, .95,", "ecdf.scatter(p95 * 1.1, .95,"),
    ),
    "jitter_values_fabricated": (
        "claude-g07-box-exam.plot.txt",
        ("len(g)), g, s=6,", "len(g)), g + 7, s=6,"),
    ),
    "extra_text_beyond_one_per_series": (
        "claude-e07-end-labels-en.plot.txt",
        (
            'Path("out").mkdir(exist_ok=True)',
            'ax.text(0.5, 0.5, "UNREQUESTED", transform=ax.transAxes)\n'
            'Path("out").mkdir(exist_ok=True)',
        ),
    ),
}


@pytest.mark.parametrize("label", sorted(MUTATIONS))
def test_fabricated_mutation_of_real_output_fails(label, tmp_path):
    name, mutate = MUTATIONS[label]
    rec = _evaluate(tmp_path, name, mutate)
    assert rec["rerun_ok"], rec["rerun_error"]
    assert not score.checks_pass(rec)


def test_real_unexecuted_edit_fails(tmp_path):
    """codex g23: plot.py was edited 20 s after the last saved figure (recorded mtimes)."""
    name = "codex-g23-vague-en.plot.txt"
    meta = INDEX[name]
    case = common.load_cases([meta["case"]])[0]
    unit = tmp_path / "unit"
    project = _project(unit / "project", case, _source(name))
    (project / ".venv").symlink_to(REPO / ".venv", target_is_directory=True)
    subprocess.run(
        [str(PYTHON), "plot.py"],
        cwd=project,
        check=True,
        env=dict(os.environ, MPLCONFIGDIR=str(tmp_path / "mpl")),
        capture_output=True,
    )
    art, t0 = meta["artifacts"], meta["started_ts"]
    started = time.time() - 300
    for path, key in (
        (project / "out" / "figure.png", "png_mtime"),
        (project / "out" / "figure.pdf", "pdf_mtime"),
        (project / "plot.py", "plot_mtime"),
    ):
        ts = started + (art[key] - t0)
        os.utime(path, (ts, ts))
    arts = runner.preserve_artifacts(project, unit, started)
    common.write_json(
        unit / "run.json",
        {
            "host": "codex",
            "arm": "noskill",
            "rep": 1,
            "artifacts": arts,
            "started_ts": started,
            "project": str(project),
        },
    )
    rec = score.score_unit(case, unit)
    assert not rec["execution_success"] and not rec["task_success"]
    assert any("never executed" in p for p in rec["execution_problems"])
    assert score.checks_pass(rec), (
        "fails only because the edit was never executed"
    )


# Tool calls the pre-calibration rule flagged for a bare "../" (verbatim from
# baseline units; {own} is the unit's project directory name).
REAL_RELATIVE_ACCESS = {
    "claude g04": {
        "command": "ls .venv/lib/python3.12/site-packages/dartwork_mpl/../ | grep -i dartwork"
    },
    "claude g08": {
        "command": "ls $P/../dartwork_mpl-0.5.6.dist-info; ls ../ 2>/dev/null | head; ls -a"
    },
    "codex e04": {
        "command": "/bin/bash -lc 'find .. -name AGENTS.md -print'",
        "aggregated_output": "../{own}/.venv/lib/python3.12/site-packages/dartwork_mpl/asset/agent/AGENTS.md ",
    },
}


def _roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    records = tmp_path / "dartwork-mpl-evals"
    work = tmp_path / "dartwork-mpl-evals-work"
    project = work / "dd5d3632ac1fc501"
    for p in (records, project):
        p.mkdir(parents=True)
    return records, work, project


@pytest.mark.parametrize("unit", sorted(REAL_RELATIVE_ACCESS))
def test_real_relative_access_inside_the_project_is_not_contamination(
    unit, tmp_path
):
    records, work, project = _roots(tmp_path)
    call = {
        k: v.replace("{own}", project.name)
        for k, v in REAL_RELATIVE_ACCESS[unit].items()
    }
    res = runner.contamination(
        [json.dumps(call)], [REPO, records], work, project
    )
    assert not res["contaminated"], res


def test_relative_access_to_another_project_or_the_records_is_contamination(
    tmp_path,
):
    records, work, project = _roots(tmp_path)
    other = json.dumps(
        {
            "command": "/bin/bash -lc 'find .. -name plot.py -print'",
            "aggregated_output": "../ffff0000aaaa1111/plot.py",
        }
    )
    peek = json.dumps(
        {"command": "cat ../../dartwork-mpl-evals/baseline/run_meta.json"}
    )
    repo = json.dumps({"command": f"ls {REPO}/evals/agentic/cases"})
    for text in (other, peek, repo):
        res = runner.contamination([text], [REPO, records], work, project)
        assert res["contaminated"], text
