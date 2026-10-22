"""Controls for the pre-registered A/B metrics (lint conformance, preset overrides).

Not collected by the default ``pytest`` run. Run explicitly:

    uv run pytest evals/agentic/test_endpoints.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
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
    m_bad = score.source_metrics(case, PYTHON, bad)
    m_good = score.source_metrics(case, PYTHON, good)
    assert m_bad["lint_clean"] is False
    assert {"figsize-direct", "tight-layout"} <= set(m_bad["lint"]["rules"])
    assert m_good["lint_findings"] == 0 and m_good["lint_clean"] is True
    assert m_good["preset_overrides_total"] == 0


def test_missing_source_is_not_clean(tmp_path):
    m = score.source_metrics({"id": "x"}, PYTHON, tmp_path / "nope.py")
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
    m = score.source_metrics({"id": "x"}, PYTHON, src)
    assert (
        m["lint"]["rules"].get("raw-hex-color") and m["lint_findings_all"] >= 1
    )
    assert m["lint_findings"] == 0 and m["lint_clean"] is True
