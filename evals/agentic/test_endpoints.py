"""Controls for the pre-registered A/B metrics (lint conformance, preset overrides).

Not collected by the default ``pytest`` run. Run explicitly:

    uv run pytest evals/agentic/test_endpoints.py -q
"""

from __future__ import annotations

import base64
import hashlib
import stat
import sys
import zipfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import compare  # noqa: E402
import conformance  # noqa: E402
import score  # noqa: E402

REPO = HERE.parents[1]
PLAN = REPO / "docs" / "superpowers" / "plans" / "2026-10-22-agent-eval.md"
PYTHON = REPO / ".venv" / "bin" / "python"

CLEAN = """\
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("report")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot([1, 2, 3])
dm.simple_layout(fig)
dm.save_formats(fig, "out/figure", formats=("png", "pdf"))
"""


def test_preregistered_text_is_the_plan_docs_text():
    assert compare.PREREGISTERED.strip() in PLAN.read_text(), (
        "compare.PREREGISTERED and the plan doc must state the same endpoints"
    )


@pytest.mark.parametrize(
    "line, kinds",
    [
        ('plt.rcParams["font.family"] = "Noto Sans KR"', {"rcparams", "font"}),
        (
            'mpl.rcParams.update({"axes.facecolor": "#eee"})',
            {"rcparams", "facecolor"},
        ),
        ('plt.rc("font", size=9)', {"rcparams", "font"}),
        ("with mpl.rc_context({'lines.linewidth': 2}): pass", {"rcparams"}),
        ('plt.style.use("ggplot")', {"style"}),
        ('ax.set_title("t", fontfamily="serif")', {"font"}),
        ('fig.patch.set_facecolor("#fafafa")', {"facecolor"}),
        ('ax.set_facecolor("#fafafa")', {"facecolor"}),
        ('fig, ax = plt.subplots(facecolor="white")', {"facecolor"}),
        ('dm.save_formats(fig, "out/figure", facecolor="#fff")', {"facecolor"}),
    ],
)
def test_each_override_kind_is_counted(line, kinds):
    src = f"import matplotlib as mpl\nimport matplotlib.pyplot as plt\nimport dartwork_mpl as dm\n{line}\n"
    got = conformance.preset_overrides(src)
    assert {k for k in conformance.KINDS if got[k]} == kinds
    assert got["total"] == 1


@pytest.mark.parametrize(
    "line",
    [
        'dm.style.use("report")',
        'bars[0].set_facecolor("#c00")',
        'ax.bar([1], [2], facecolor="#c00")',
        'for patch in ax.patches: patch.set_facecolor("#ccc")',
        'ax.plot([1, 2], color="oc.gray5")',
    ],
)
def test_preset_use_and_artist_colours_are_not_overrides(line):
    src = (
        f"import matplotlib.pyplot as plt\nimport dartwork_mpl as dm\n{line}\n"
    )
    assert conformance.preset_overrides(src)["total"] == 0


def test_lint_counts_findings_of_the_final_source(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text(
        "import matplotlib.pyplot as plt\nfig, ax = plt.subplots(figsize=(4, 3))\n"
        "ax.plot([1, 2])\nplt.tight_layout()\nfig.savefig('x.png')\n"
    )
    good = tmp_path / "good.py"
    good.write_text(CLEAN)
    case = {"id": "x"}
    m_bad = score.source_metrics(case, bad)
    m_good = score.source_metrics(case, good)
    assert m_bad["lint_clean"] is False
    assert {"figsize-direct", "tight-layout"} <= set(m_bad["lint"]["rules"])
    assert m_good["lint_findings"] == 0 and m_good["lint_clean"] is True
    assert m_good["preset_overrides_total"] == 0


def test_missing_source_is_not_clean(tmp_path):
    m = score.source_metrics({"id": "x"}, tmp_path / "nope.py")
    assert (
        m["lint_clean"] is None
        and not compare.per_case(
            [{"case": "x", "lint_clean": m["lint_clean"]}], "lint_clean"
        )["x"][0]
    )


def test_info_findings_are_reported_but_not_counted(tmp_path):
    src = tmp_path / "hex.py"
    src.write_text(
        CLEAN.replace(
            "ax.plot([1, 2, 3])", 'ax.plot([1, 2, 3], color="#1f77b4")'
        )
    )
    m = score.source_metrics({"id": "x"}, src)
    assert (
        m["lint"]["rules"].get("raw-hex-color") and m["lint_findings_all"] >= 1
    )
    assert m["lint_findings"] == 0 and m["lint_clean"] is True


BAD = (
    "import matplotlib.pyplot as plt\nfig, ax = plt.subplots(figsize=(4, 3))\n"
    "ax.plot([1, 2])\nplt.tight_layout()\nfig.savefig('out/figure.png')\n"
)


def test_a_patched_project_venv_cannot_clean_the_lint(tmp_path):
    """The agent can write its venv: a lint_code that returns [] must not count."""
    unit = tmp_path / "run" / "claude" / "g01-line-gdp" / "noskill-r1"
    project = tmp_path / "work" / "abc"
    (project / ".venv" / "bin").mkdir(parents=True)
    unit.mkdir(parents=True)
    fake = project / ".venv" / "bin" / "python"
    fake.write_text(
        '#!/bin/sh\necho \'{"findings": 0, "rules": {}, "severity": {}}\'\n'
    )
    fake.chmod(0o755)
    (project / "plot.py").write_text(BAD)
    common.write_json(
        unit / "run.json",
        {"host": "claude", "project": str(project), "started_ts": 0},
    )
    case = common.load_cases(["g01-line-gdp"])[0]
    rec = score.score_unit(case, unit)
    assert rec["lint_findings"] >= 2 and rec["lint_clean"] is False
    assert rec["lint"]["interpreter"] != str(fake)
    assert rec["lint"]["sandbox"] == "bwrap-ro"


def test_lint_records_the_trusted_interpreter_and_wheel(tmp_path):
    run = tmp_path / "run"
    (run / "wheel").mkdir(parents=True)
    src = tmp_path / "p.py"
    src.write_text(BAD)
    m = score.source_metrics({"id": "x"}, src, run)  # no wheel: harness env
    assert m["lint"]["interpreter"] == sys.executable
    assert m["lint"]["wheel_sha256"] is None


def _mini_wheel(dest: Path) -> Path:
    """A real wheel whose ``dartwork_mpl.lint_code`` always reports 3 findings."""
    files = {
        "dartwork_mpl/__init__.py": (
            "from collections import namedtuple\n__version__ = '0.0.1'\n"
            "Issue = namedtuple('Issue', 'rule_id severity')\n"
            "def lint_code(code):\n"
            "    return [Issue('wheel-check', 'critical')] * 3\n"
        ),
        "dartwork_mpl-0.0.1.dist-info/METADATA": (
            "Metadata-Version: 2.1\nName: dartwork-mpl\nVersion: 0.0.1\n"
        ),
        "dartwork_mpl-0.0.1.dist-info/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\n"
            "Tag: py3-none-any\n"
        ),
    }
    record = []
    for name, text in files.items():
        raw = text.encode()
        h = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=")
        record.append(f"{name},sha256={h.decode()},{len(raw)}")
    record.append("dartwork_mpl-0.0.1.dist-info/RECORD,,")
    files["dartwork_mpl-0.0.1.dist-info/RECORD"] = "\n".join(record) + "\n"
    whl = dest / "dartwork_mpl-0.0.1-py3-none-any.whl"
    with zipfile.ZipFile(whl, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return whl


def test_a_planted_lint_env_in_the_records_tree_is_ignored(tmp_path):
    """Envs are built per scoring session in a fresh 0700 dir, never looked up by path."""
    run = tmp_path / "records" / "run1"
    (run / "wheel").mkdir(parents=True)
    whl = _mini_wheel(run / "wheel")
    digest = hashlib.sha256(whl.read_bytes()).hexdigest()
    common.write_json(
        run / "manifest.json",
        {"wheel": {"sha256": digest}, "config": {"python": "3.12"}},
    )
    planted = run.parent / "lint-envs" / digest[:16] / "bin"
    planted.mkdir(parents=True)
    (planted / "python").write_text(
        '#!/bin/sh\necho \'{"findings": 0, "rules": {}, "severity": {}}\'\n'
    )
    (planted / "python").chmod(0o755)
    src = tmp_path / "p.py"
    src.write_text(CLEAN)
    m = score.source_metrics({"id": "x"}, src, run)
    interp = Path(m["lint"]["interpreter"])
    assert m["lint_findings"] == 3 and m["lint"]["rules"] == {"wheel-check": 3}
    assert m["lint"]["wheel_sha256"] == digest
    assert (
        score.LINT_CACHE in interp.parents and run.parent not in interp.parents
    )
    session = interp.parents[2]
    assert session.name.startswith("session-")
    assert stat.S_IMODE(session.stat().st_mode) == 0o700


def test_a_wheel_that_differs_from_the_manifest_is_refused(tmp_path):
    run = tmp_path / "run"
    (run / "wheel").mkdir(parents=True)
    _mini_wheel(run / "wheel")
    common.write_json(run / "manifest.json", {"wheel": {"sha256": "0" * 64}})
    with pytest.raises(RuntimeError):
        score.trusted_linter(run)


def test_override_count_never_runs_project_code(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        score.subprocess, "run", lambda *a, **k: calls.append(a) or None
    )
    over = conformance.preset_overrides('plt.rcParams["font.size"] = 9\n')
    assert over["total"] == 1 and not calls
