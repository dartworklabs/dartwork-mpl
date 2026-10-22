"""Regression controls from the round-2 review of 407bda8d (scorer decider).

Every probe that exposed a false pass/fail is pinned here; each test failed on
407bda8d and passes after the fix. Not collected by the default ``pytest``
run (``testpaths`` excludes evals/). Run explicitly:

    uv run pytest evals/agentic/test_regressions.py -q
"""

from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import sys
import time
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.ticker import FormatStrFormatter
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import compare  # noqa: E402
import metrics  # noqa: E402
import oracle  # noqa: E402
import probe  # noqa: E402
import run as runner  # noqa: E402
import score  # noqa: E402
import test_scorer as fx  # noqa: E402

REPO = HERE.parents[1]


# ------------------------------------------------------------ helpers
def case_checks(case_id: str, fig) -> list[dict]:
    """All oracle checks of a case, figure-level accounting included (old API: plain checks)."""
    case = common.load_cases([case_id])[0]
    snap = probe.snapshot(fig, None)
    plt.close(fig)
    pr = {"snapshot": snap, "styles": [], "missing_glyphs": []}
    try:
        return oracle.check_oracle(
            case["oracle"],
            pr,
            None,
            auxiliary=case.get("auxiliary", []),
            figure=True,
        )
    except TypeError:  # 407bda8d signature
        return oracle.check_oracle(case["oracle"], pr)


def case_ok(case_id: str, fig) -> bool:
    return all(c["ok"] is True for c in case_checks(case_id, fig))


def stamp(ts: float) -> str:
    return (
        datetime.fromtimestamp(ts, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def png_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    return buf.getvalue()


# ------------------------------------------------------------ item 3: extra / invisible data
def test_r01_extra_line_labelled_korea_is_rejected():
    fig = fx.gdp_fig()
    y = (
        np.nan_to_num(np.array(fx.col("gdp_growth.csv", "Korea"), dtype=float))
        + 20
    )
    fig.axes[0].plot(fx.col("gdp_growth.csv", "year"), y, label="Korea")
    assert not case_ok("g01-line-gdp", fig)


def test_r02_invisible_lines_do_not_match():
    fig = fx.gdp_fig()
    for ln in fig.axes[0].lines:
        ln.set_alpha(0)
    assert not case_ok("g01-line-gdp", fig)


def test_r03_markers_only_scatter_is_not_a_line_chart():
    fig = fx.gdp_fig()
    ax = fig.axes[0]
    for ln in list(ax.lines):
        ax.scatter(ln.get_xdata(), ln.get_ydata(), label=ln.get_label())
        ln.remove()
    assert not case_ok("g01-line-gdp", fig)


def test_r04_unlabelled_decoy_series_is_unexplained():
    fig = fx.gdp_fig()
    fig.axes[0].plot([2012, 2016, 2023], [5, -5, 5], color="0.3")
    assert not case_ok("g01-line-gdp", fig)


def test_r05_reference_line_is_auxiliary_when_declared():
    fig = fx.gdp_fig()
    fig.axes[0].plot([2012, 2023], [0, 0], color="0.5", linewidth=0.5)
    assert case_ok("g01-line-gdp", fig)


# ------------------------------------------------------------ item 7: legend handles
def test_r06_manual_legend_handles_name_the_series():
    fig = fx.gdp_fig()
    ax = fig.axes[0]
    for line in ax.lines:
        line.set_label("_nolegend_")
    ax.legend(handles=list(ax.lines), labels=fx.COUNTRIES)
    assert case_ok("g01-line-gdp", fig)


# ------------------------------------------------------------ item 8: structure
def test_r07_stacked_bars_for_a_grouped_request_are_rejected():
    fig, ax = plt.subplots()
    rs = oracle.table("quarterly_sales.csv")
    base = np.zeros(4)
    for region in ["North", "South", "East", "West"]:
        vals = [
            oracle.num(r["revenue"])
            for q in ["Q1", "Q2", "Q3", "Q4"]
            for r in rs
            if r["quarter"] == q and r["region"] == region
        ]
        ax.bar(range(4), vals, bottom=base, label=region)
        base += vals
    ax.set_xticks(range(4), ["Q1", "Q2", "Q3", "Q4"])
    ax.legend()
    assert not case_ok("g02-grouped-bar-sales", fig)


def test_r08_grouped_bars_for_a_stacked_request_are_rejected():
    fig = (
        fx.sales_fig()
    )  # grouped, right values; only the bars contract is judged here
    bars = [c for c in case_checks("g21-size-17x9", fig) if c["type"] == "bars"]
    assert bars and bars[0]["ok"] is not True


def test_r09_floating_stack_layers_are_rejected():
    fig = fx.stack_fig()
    for n, coll in enumerate(fig.axes[0].collections):
        for p in coll.get_paths():
            p.vertices[:, 1] += n * 1000
    assert not case_ok("g08-stacked-area-energy", fig)


def test_r10_all_kpis_in_one_panel_are_rejected():
    fig, axs = plt.subplots(2, 2)
    for name in ["revenue_musd", "active_users", "churn_pct", "nps"]:
        axs[0, 0].plot(range(12), fx.col("kpi_monthly.csv", name), label=name)
    for a in [axs[0, 1], axs[1, 0], axs[1, 1]]:
        a.plot([0, 11], [0, 0], label="dummy")
    axs[0, 0].legend()
    assert not case_ok("g10-dashboard-kpi", fig)


# ------------------------------------------------------------ item 2: distributions
def _rt(v):
    return np.asarray(
        [
            oracle.num(r["response_ms"])
            for r in oracle.table("response_times.csv")
            if r["variant"] == v
        ]
    )


def test_r11_fabricated_density_curves_are_rejected():
    fig, ax = plt.subplots()
    x = np.linspace(0, 1000, 201)
    for name in ["A", "B"]:
        ax.plot(x, np.full(len(x), 0.001), label=f"Variant {name}")
    ax.legend()
    assert not case_ok("g06-hist-response", fig)


def test_r12_true_gaussian_kde_is_accepted():
    fig, ax = plt.subplots()
    for name in ["A", "B"]:
        v = _rt(name)
        h = 1.06 * v.std(ddof=1) * len(v) ** -0.2
        x = np.linspace(v.min() - 3 * h, v.max() + 3 * h, 300)
        y = np.exp(-0.5 * ((x[:, None] - v[None, :]) / h) ** 2).sum(1) / (
            len(v) * h * np.sqrt(2 * np.pi)
        )
        ax.plot(x, y, label=f"Variant {name}")
    ax.legend()
    assert case_ok("g06-hist-response", fig)


def _exam(section):
    return np.asarray(
        [
            oracle.num(r["score"])
            for r in oracle.table("exam_scores.csv")
            if r["section"] == section and oracle.num(r["score"]) is not None
        ]
    )


def test_r13_violin_bodies_match_their_kde_and_fakes_do_not():
    data = [_exam(s) for s in "ABCD"]
    fig, ax = plt.subplots()
    ax.violinplot(data, positions=[1, 2, 3, 4])
    ax.set_xticks([1, 2, 3, 4], list("ABCD"))
    assert case_ok("g07-box-exam", fig)
    fig, ax = plt.subplots()
    fake = [
        np.linspace(d.min(), d.max(), len(d)) for d in data
    ]  # same range, uniform shape
    ax.violinplot(fake, positions=[1, 2, 3, 4])
    ax.set_xticks([1, 2, 3, 4], list("ABCD"))
    assert not case_ok("g07-box-exam", fig)


def test_r14_box_with_wrong_quartiles_is_rejected():
    data = [_exam(s) for s in "ABCD"]
    shifted = [
        np.concatenate([d, [np.median(d)] * 30]) for d in data
    ]  # same median, narrower box
    fig, ax = plt.subplots()
    ax.boxplot(shifted, tick_labels=list("ABCD"))
    assert not case_ok("g07-box-exam", fig)


# ------------------------------------------------------------ item 5: explicit preservation
def _preserve(mutation: str) -> dict:
    fig = fx.gdp_fig()
    ax = fig.axes[0]
    ax.set_xlabel("Year")
    ax.set_ylabel("Growth")
    ax.set_title("GDP")
    baseline = probe.snapshot(fig, None)["props"]
    ax.xaxis.label.set_fontsize(ax.xaxis.label.get_fontsize() + 1)
    ax.yaxis.label.set_fontsize(ax.yaxis.label.get_fontsize() + 1)
    if mutation == "alpha":
        ax.lines[0].set_alpha(0)
    if mutation == "tick_text":
        ax.set_xticks(ax.get_xticks(), ["WRONG"] * len(ax.get_xticks()))
    if mutation == "tick_weight":
        for t in ax.get_xticklabels():
            t.set_fontweight("bold")
    if mutation == "annotation":
        ax.text(0.5, 0.5, "UNREQUESTED", transform=ax.transAxes)
    if mutation == "legend_anchor":
        ax.legend().set_bbox_to_anchor((0.5, 0.7))
    if mutation == "extra_line":
        ax.plot([2012, 2023], [0, 1], label="made up")
    if mutation == "title_rotation":
        ax.title.set_rotation(45)
    after = probe.snapshot(fig, None)["props"]
    plt.close(fig)
    return metrics.preservation(
        baseline,
        after,
        "explicit",
        ["ax*.xlabel.fontsize", "ax*.ylabel.fontsize"],
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "alpha",
        "tick_text",
        "tick_weight",
        "annotation",
        "legend_anchor",
        "extra_line",
        "title_rotation",
    ],
)
def test_r15_explicit_edit_flags_untargeted_change(mutation):
    assert _preserve(mutation)["ok"] is False


def test_r16_explicit_edit_with_only_the_target_change_passes():
    assert _preserve("none")["ok"] is True


def test_r17_explicit_preservation_requires_a_base_snapshot():
    props = probe.snapshot(fx.gdp_fig(), None)["props"]
    plt.close("all")
    try:
        res = metrics.preservation(
            None, props, "explicit", ["ax*.xlabel.fontsize"]
        )
    except (TypeError, AttributeError):
        pytest.fail(
            "a missing base snapshot must fail explicit preservation, not crash"
        )
    assert res["ok"] is False


# ------------------------------------------------------------ items 9/10: comparison
def test_r18_five_point_gain_is_not_improved():
    a = {f"c{i}": (0.5, 100) for i in range(40)}
    b = {f"c{i}": (1.0 if i < 4 else 0.5, 100) for i in range(40)}
    assert compare.paired(a, b)["success_verdict"] != "improved"


def test_r19_ten_point_gain_with_positive_ci_is_improved():
    a = {f"c{i}": (0.0, 100) for i in range(40)}
    b = {f"c{i}": (1.0 if i < 8 else 0.0, 100) for i in range(40)}
    assert compare.paired(a, b)["success_verdict"] == "improved"


def _rows(cases, reps, ok, tokens=100):
    return [
        {
            "host": "claude",
            "case": f"c{i}",
            "rep": r,
            "task_success": ok(i, r),
            "tokens": {"total": tokens},
        }
        for i in cases
        for r in reps
    ]


def test_r20_missing_cases_make_the_comparison_incomplete():
    ra = _rows(range(40), [1, 2], lambda i, r: False)
    rb = [dict(z, task_success=True) for z in ra if z["case"] == "c0"]
    res = compare.compare_rows(ra, rb)
    assert all(r.get("success_verdict") != "improved" for r in res)


def test_r21_missing_failed_repetitions_make_the_comparison_incomplete():
    ra = _rows(range(40), [1, 2], lambda i, r: r == 1)
    rb = [dict(z) for z in ra if z["rep"] == 1]
    res = compare.compare_rows(ra, rb)
    assert all(r.get("success_verdict") != "improved" for r in res)


def test_r22_unknown_token_usage_blocks_noninferiority():
    a = {f"c{i}": (0.5, 100) for i in range(40)}
    b = {f"c{i}": (1, 100 if i == 0 else None) for i in range(40)}
    assert compare.paired(a, b).get("tokens_verdict") not in (
        "noninferior",
        "improved",
    )


def test_r23_manifest_validation_and_missing_as_failure(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    units = [
        f"claude/c{i}/{arm}-r1"
        for i in range(3)
        for arm in ("noskill", "skill")
    ]
    (run / "manifest.json").write_text(
        json.dumps({"plans": [{"units": units}]})
    )
    rows = [
        {
            "host": "claude",
            "case": u.split("/")[1],
            "arm": u.split("/")[2][:-3],
            "rep": 1,
            "unit_id": u,
            "task_success": u.endswith("skill-r1") and "noskill" not in u,
            "tokens": {"total": 100},
        }
        for u in units[:-1]
    ]
    (run / "results.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows)
    )
    res, _ = compare.compare_runs(
        run, None, "task_success", missing_as_failure=False
    )
    assert res[0]["success_verdict"] == "incomplete"
    res, _ = compare.compare_runs(
        run, None, "task_success", missing_as_failure=True
    )
    assert res[0]["success_verdict"] != "incomplete" and res[0][
        "tokens_verdict"
    ].startswith("blocked")


# ------------------------------------------------------------ items 1/12: execution binding and PDFs
def _unit(
    tmp_path: Path, case_id: str, source: str, after_run: str | None = None
) -> tuple[dict, Path]:
    case = common.load_cases([case_id])[0]
    unit = tmp_path / "unit"
    project = unit / "project"
    (project / "data").mkdir(parents=True)
    for name in case["data"]:
        (project / "data" / name).write_bytes(
            (HERE / "fixtures" / "data" / name).read_bytes()
        )
    (project / ".venv").symlink_to(REPO / ".venv", target_is_directory=True)
    (project / "plot.py").write_text(source)
    started = time.time()
    subprocess.run(
        [str(project / ".venv" / "bin" / "python"), "plot.py"],
        cwd=project,
        check=True,
        env=dict(os.environ, MPLCONFIGDIR=str(tmp_path / "mpl")),
        capture_output=True,
    )
    arts = runner.preserve_artifacts(project, unit, started)
    if after_run is not None:
        time.sleep(0.05)
        (project / "plot.py").write_text(after_run)
    common.write_json(
        unit / "run.json",
        {
            "host": "claude",
            "arm": "noskill",
            "rep": 1,
            "artifacts": arts,
            "started_ts": started,
            "project": str(project),
        },
    )
    return case, unit


def test_r24_edit_never_executed_is_not_an_execution_success(tmp_path):
    base = (HERE / "fixtures" / "base" / "b01_gdp_lines.py").read_text()
    edited = base.replace(
        'Path("out").mkdir',
        "ax.xaxis.label.set_fontsize(ax.xaxis.label.get_fontsize()+1)\n"
        'ax.yaxis.label.set_fontsize(ax.yaxis.label.get_fontsize()+1)\nPath("out").mkdir',
    )
    case, unit = _unit(tmp_path, "e01-label-step-en", base, after_run=edited)
    r = score.score_unit(case, unit)
    assert not r["execution_success"] and not r["task_success"]


def test_r25_executed_reference_is_a_task_success(tmp_path):
    ref = (HERE / "fixtures" / "reference" / "g01-line-gdp.py").read_text()
    case, unit = _unit(tmp_path, "g01-line-gdp", ref)
    r = score.score_unit(case, unit)
    assert (
        r["execution_success"] and r["rerun_matches"] and r["task_success"]
    ), r.get("execution_problems")


def test_r26_invalid_pdf_is_rejected(tmp_path):
    bad = tmp_path / "invalid.pdf"
    bad.write_bytes(b"%PDF-\n%%EOF\n")
    assert score.valid_pdf(bad) is False
    ref = (HERE / "fixtures" / "reference" / "g01-line-gdp.py").read_text()
    case, unit = _unit(
        tmp_path,
        "g01-line-gdp",
        ref + "\nPath('out/figure.pdf').write_bytes(b'%PDF-\\n%%EOF\\n')\n",
    )
    assert not score.score_unit(case, unit)["execution_success"]


def test_r27_rerun_must_be_pixel_identical(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    img = np.full((60, 80, 3), 255, dtype=np.uint8)
    Image.fromarray(img).save(a)
    img[10, 10] = [250, 250, 250]
    Image.fromarray(img).save(b)
    assert score.png_matches(a, a) and not score.png_matches(a, b)


def test_r28_contaminated_run_is_never_a_success(tmp_path):
    ref = (HERE / "fixtures" / "reference" / "g01-line-gdp.py").read_text()
    case, unit = _unit(tmp_path, "g01-line-gdp", ref)
    rec = json.loads((unit / "run.json").read_text())
    rec["contamination"] = {"contaminated": True, "hits": ["evals/agentic"]}
    (unit / "run.json").write_text(json.dumps(rec))
    assert not score.score_unit(case, unit)["task_success"]


_COPY_TO_FIGURE = """
import shutil
for ext in ("png", "pdf"):
    shutil.copyfile(f"out/figure-v2.{ext}", f"out/figure.{ext}")
"""


def test_r45_versioned_save_copied_to_the_requested_path_counts(tmp_path):
    """A skill-style save to out/figure-v2 then a byte copy to out/figure."""
    ref = (HERE / "fixtures" / "reference" / "g01-line-gdp.py").read_text()
    src = ref.replace('"out/figure"', '"out/figure-v2"') + _COPY_TO_FIGURE
    case, unit = _unit(tmp_path, "g01-line-gdp", src)
    r = score.score_unit(case, unit)
    assert r["rerun_ok"] and r["rerun_matches"] and r["task_success"], r.get(
        "rerun_error"
    )


def test_r46_copy_of_an_earlier_save_does_not_count(tmp_path):
    """The copy must be the last save: an older version is not this figure."""
    ref = (HERE / "fixtures" / "reference" / "g01-line-gdp.py").read_text()
    src = (
        ref.replace('"out/figure"', '"out/figure-v2"')
        + "ax.set_title('v3')\n"
        + 'dm.save_formats(fig, "out/figure-v3", formats=("png", "pdf"))\n'
        + _COPY_TO_FIGURE
    )
    case, unit = _unit(tmp_path, "g01-line-gdp", src)
    assert not score.score_unit(case, unit)["rerun_ok"]


# ------------------------------------------------------------ item 6: inspection
def _final(tmp_path: Path) -> tuple[Path, float]:
    fig = fx.gdp_fig()
    final = tmp_path / "final.png"
    final.write_bytes(png_bytes(fig))
    return final, final.stat().st_mtime


def test_r29_view_before_the_final_write_is_stale(tmp_path):
    final, ts = _final(tmp_path)
    views = [(ts - 60, final.read_bytes())]
    assert runner.inspection(views, final, ts)["observed"] is False


def test_r30_view_without_timestamp_does_not_count(tmp_path):
    final, ts = _final(tmp_path)
    assert (
        runner.inspection([(None, final.read_bytes())], final, ts)["observed"]
        is False
    )


def test_r31_tiny_thumbnails_do_not_count(tmp_path):
    final, ts = _final(tmp_path)
    for size in [(1, 1), (120, 90)]:
        buf = io.BytesIO()
        Image.open(final).convert("RGB").resize(size, Image.LANCZOS).save(
            buf, format="PNG"
        )
        assert runner.same_image(buf.getvalue(), final.read_bytes()) is None
    blank = io.BytesIO()
    Image.new("RGB", (1, 1), "white").save(blank, format="PNG")
    assert (
        runner.inspection([(ts + 5, blank.getvalue())], final, ts)["observed"]
        is False
    )


def test_r32_view_of_a_different_render_does_not_count(tmp_path):
    final, ts = _final(tmp_path)
    fig = fx.gdp_fig()
    fig.axes[0].xaxis.label.set_fontsize(
        fig.axes[0].xaxis.label.get_fontsize() + 1
    )
    fig.axes[0].set_xlabel("Year")
    other = png_bytes(fig)
    assert runner.inspection([(ts + 5, other)], final, ts)["observed"] is False


@pytest.mark.parametrize("flt", [Image.LANCZOS, Image.BILINEAR])
def test_r33_host_resized_view_after_the_final_write_counts(tmp_path, flt):
    final, ts = _final(tmp_path)
    im = Image.open(final).convert("RGB")
    buf = io.BytesIO()
    im.resize((int(im.width * 0.8), int(im.height * 0.8)), flt).save(
        buf, format="PNG"
    )
    assert (
        runner.inspection([(ts + 5, buf.getvalue())], final, ts)["observed"]
        is True
    )


def test_r34_claude_and_codex_view_events_are_timestamped_and_merged(tmp_path):
    final, ts = _final(tmp_path)
    data = base64.b64encode(final.read_bytes()).decode()
    claude = [
        {
            "type": "user",
            "timestamp": stamp(ts + 3),
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": [
                            {
                                "type": "image",
                                "source": {"type": "base64", "data": data},
                            }
                        ],
                    }
                ]
            },
        }
    ]
    assert (
        runner.inspection(runner.view_events("claude", claude, []), final, ts)[
            "observed"
        ]
        is True
    )
    stale = [
        {
            "timestamp": stamp(ts - 30),
            "payload": {
                "type": "custom_tool_call_output",
                "output": [
                    {
                        "type": "input_image",
                        "image_url": "data:image/png;base64," + data,
                    }
                ],
            },
        }
    ]
    assert (
        runner.inspection(runner.view_events("codex", [], [stale]), final, ts)[
            "observed"
        ]
        is False
    )


# ------------------------------------------------------------ item 4: leakage / contamination
def test_r35_agent_env_has_no_repo_path(tmp_path):
    old = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{REPO}/.venv/bin{os.pathsep}/usr/bin"
    try:
        env = runner.base_env(tmp_path)
    finally:
        os.environ["PATH"] = old
    assert str(REPO) not in env["PATH"] and "/usr/bin" in env["PATH"]


def test_r36_transcript_access_to_grading_files_is_contamination(tmp_path):
    work, project = tmp_path / "work", tmp_path / "work" / "abc123"
    markers = [
        str(REPO),
        "evals/agentic",
        "fixtures/reference",
        "manifest.json",
    ]
    hit = runner.contamination(
        [
            json.dumps(
                {"command": f"cat {REPO}/evals/agentic/cases/g01-line-gdp.yaml"}
            )
        ],
        markers,
        work,
        project,
    )
    other = runner.contamination(
        [json.dumps({"command": f"cat {work}/ffff0000/plot.py"})],
        markers,
        work,
        project,
    )
    clean = runner.contamination(
        [json.dumps({"command": f"cat {project}/data/gdp_growth.csv"})],
        markers,
        work,
        project,
    )
    assert (
        hit["contaminated"]
        and other["contaminated"]
        and not clean["contaminated"]
    )


def test_r45_records_marker_matches_only_on_a_path_boundary(tmp_path):
    """Smoke r2 found every unit 'contaminated': the records root is a string prefix of the work root."""
    records = str(tmp_path / "dartwork-mpl-evals")
    work = tmp_path / "dartwork-mpl-evals-work"
    project = work / "f153c644d259fa57"
    own = json.dumps(
        {"command": f".venv/bin/python {project}/plot.py && ls {project}/out"}
    )
    assert not runner.contamination([own], [records], work, project)[
        "contaminated"
    ]
    peek = json.dumps(
        {
            "command": f"cat {records}/smoke/claude/g01-line-gdp/noskill-r1/score.json"
        }
    )
    assert runner.contamination([peek], [records], work, project)[
        "contaminated"
    ]


def _args(tmp_path: Path) -> Namespace:
    return Namespace(
        work_root=tmp_path / "work",
        skill_dir=None,
        codex_home=None,
        dry_run=True,
    )


def _cfg() -> dict:
    return runner.config_from(
        Namespace(
            claude_model="sonnet",
            codex_model="gpt-6-astra",
            claude_effort="high",
            codex_effort="medium",
            max_turns=20,
            max_budget_usd=5.0,
            timeout=300,
            codex_token_budget=1_500_000,
            codex_no_subagents=False,
            python="3.12",
            hide_grading=False,
            codex_home=None,
        )
    )


def test_r37_projects_live_outside_the_records_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(
        runner,
        "prepare",
        lambda case, project, unit, *a: project.mkdir(parents=True) or {},
    )
    records = tmp_path / "records" / "run1"
    records.mkdir(parents=True)
    (records / "manifest.json").write_text("{}")
    case = common.load_cases(["g01-line-gdp"])[0]
    meta = {
        "wheel": {"name": "x.whl", "sha256": "0" * 64, "path": "x"},
        "versions": {"claude": "test"},
    }
    rec = runner.one(
        (case, "claude", "noskill", 1), records, _args(tmp_path), _cfg(), meta
    )
    project = Path(rec["project"])
    for anc in project.parents:
        assert (
            not (anc / "manifest.json").exists()
            and not (anc / "run_meta.json").exists()
        )
        assert anc != records and records not in project.parents
    assert str(REPO) not in json.dumps(rec.get("wheel"))


def test_r38_completed_units_are_immutable(tmp_path, monkeypatch):
    monkeypatch.setattr(
        runner,
        "prepare",
        lambda case, project, unit, *a: project.mkdir(parents=True) or {},
    )
    records = tmp_path / "records" / "run1"
    case = common.load_cases(["g01-line-gdp"])[0]
    meta = {
        "wheel": {"name": "x.whl", "sha256": "0" * 64, "path": "x"},
        "versions": {"claude": "test"},
    }
    runner.one(
        (case, "claude", "noskill", 1), records, _args(tmp_path), _cfg(), meta
    )
    with pytest.raises(SystemExit):
        runner.one(
            (case, "claude", "noskill", 1),
            records,
            _args(tmp_path),
            _cfg(),
            meta,
        )


# ------------------------------------------------------------ items 11/13: budgets and manifest
def test_r39_new_repetitions_get_new_ids_and_config_changes_are_refused(
    tmp_path,
):
    case = common.load_cases(["g01-line-gdp"])[0]
    manifest = {
        "plans": [
            {
                "units": [
                    "claude/g01-line-gdp/noskill-r1",
                    "claude/g01-line-gdp/noskill-r2",
                ]
            }
        ],
        "wheel": {"sha256": runner.sha256(b"wheel")},
        "config": _cfg(),
    }
    jobs = runner.plan_jobs(
        manifest, [case], ["claude"], ["noskill"], 2, seed=1
    )
    assert sorted(j[3] for j in jobs) == [3, 4]
    w = tmp_path / "w.whl"
    w.write_bytes(b"wheel")
    runner.assert_same_run(manifest, _cfg(), w, None)
    changed = dict(
        _cfg(),
        budgets={
            **_cfg()["budgets"],
            "claude": {**_cfg()["budgets"]["claude"], "max_turns": 40},
        },
    )
    with pytest.raises(SystemExit):
        runner.assert_same_run(manifest, changed, w, None)
    other = tmp_path / "other.whl"
    other.write_bytes(b"other")
    with pytest.raises(SystemExit):
        runner.assert_same_run(manifest, _cfg(), w, other)


FAKE_CODEX = """
import json, sys, time
from pathlib import Path
from datetime import date
home = Path(sys.argv[1]); thread = "01fake-thread"
print(json.dumps({"type": "thread.started", "thread_id": thread}), flush=True)
day = home / "sessions" / f"{date.today():%Y/%m/%d}"; day.mkdir(parents=True, exist_ok=True)
roll = day / f"rollout-x-{thread}.jsonl"
with open(roll, "w") as f:
    f.write(json.dumps({"type": "session_meta", "payload": {"id": thread}}) + "\\n")
for k in range(1000):
    with open(roll, "a") as f:
        f.write(json.dumps({"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage":
                {"input_tokens": 400 * k, "output_tokens": 10 * k}}}}) + "\\n")
    time.sleep(0.2)
"""


def test_r40_codex_token_budget_kills_the_run(tmp_path):
    home, unit = tmp_path / "codex_home", tmp_path / "unit"
    unit.mkdir()
    script = tmp_path / "fake_codex.py"
    script.write_text(FAKE_CODEX)
    mon = runner.CodexMonitor(home, unit / "transcript.jsonl", budget=2000)
    _, reason, wall = runner.run_host(
        [sys.executable, str(script), str(home)],
        tmp_path,
        dict(os.environ),
        unit,
        timeout=60,
        monitor=mon,
    )
    assert reason == "token_budget" and wall < 30 and mon.last > 2000


def test_r41_wall_clock_budget_is_enforced(tmp_path):
    unit = tmp_path / "unit"
    unit.mkdir()
    _, reason, wall = runner.run_host(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        tmp_path,
        dict(os.environ),
        unit,
        timeout=3,
    )
    assert reason == "timeout" and wall < 30


# ------------------------------------------------------------ add-on: meaningless decimals
def _decimals(fig) -> list[str]:
    snap = probe.snapshot(fig, None)
    plt.close(fig)
    return metrics.defects({"snapshot": snap, "missing_glyphs": []})[
        "details"
    ].get("meaningless_decimals", [])


def test_r42_integer_ticks_with_trailing_zeros_are_flagged():
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 200, 400])
    ax.set_yticks([0, 100, 200, 300, 400])
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    assert any("y ticks" in d for d in _decimals(fig))


def test_r43_integer_value_labels_with_trailing_zeros_are_flagged():
    fig, ax = plt.subplots()
    bars = ax.bar(["a", "b", "c"], [12, 30, 45])
    ax.bar_label(bars, fmt="%.1f")
    assert any("value labels" in d for d in _decimals(fig))


def test_r44_fractional_steps_and_clean_integers_are_not_flagged():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [17.5, 22.5])
    ax.set_yticks([17.5, 20.0, 22.5])
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    bars = ax.bar([0.2, 0.8], [12.5, 13.0], width=0.1)
    ax.bar_label(bars, fmt="%.1f")
    assert _decimals(fig) == []
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0, 200, 400])
    assert _decimals(fig) == []
