"""Fail-closed contamination controls (security review of the calibration round).

Each control is a mutation that the resolved-path-v2 rule of 229d210f got
wrong, or a backstop that must keep firing. Not collected by the default
``pytest`` run. Run explicitly:

    uv run pytest evals/agentic/test_contamination.py -q
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from itertools import pairwise
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import compare  # noqa: E402
import contamination as cont  # noqa: E402
import run as runner  # noqa: E402
import score  # noqa: E402

REPO = HERE.parents[1]


@pytest.fixture
def tree(tmp_path):
    records = tmp_path / "dartwork-mpl-evals"
    work = tmp_path / "dartwork-mpl-evals-work"
    project = work / "dd5d3632ac1fc501"
    for p in (
        records / "baseline",
        project / ".venv" / "lib",
        work / "ffff0000aaaa1111",
    ):
        p.mkdir(parents=True)
    return Namespace(records=records, work=work, project=project)


def hit(tree, *texts) -> bool:
    return cont.contamination(
        list(texts), [REPO, tree.records], tree.work, tree.project
    )["contaminated"]


def call(**kw) -> str:
    return json.dumps(kw)


# ------------------------------------------------------------ 3. tokenizer
@pytest.mark.parametrize("sep", ["\n", "\t", '\\"', '"'])
def test_separators_inside_decoded_strings_split_words(tree, sep):
    text = call(command=f"true{sep}{tree.records}/baseline/run.json")
    assert hit(tree, text)


@pytest.mark.parametrize(
    "fmt", ["--out={p}/x", "PATH=/usr/bin:{p}/bin", "x:{p}/y", "open('{p}/z')"]
)
def test_absolute_paths_anywhere_in_a_word(tree, fmt):
    assert hit(tree, call(command="cat " + fmt.format(p=tree.records)))


def test_double_leading_slash_collapses_unless_after_a_url_scheme(tree):
    assert hit(tree, call(command=f"cat /{tree.records}/baseline/run.json"))
    assert hit(tree, call(command=f"cat ///{tree.records}/baseline/run.json"))
    assert not hit(
        tree, call(command=f"curl https://example.org{tree.records}")
    )


def test_raw_output_strings_are_scanned(tree):
    out = {
        "type": "function_call_output",
        "output": f"ok\n{tree.records}/baseline/x\n",
    }
    assert hit(tree, json.dumps(out))


# ------------------------------------------------------------ 4a. name markers
@pytest.mark.parametrize(
    "name",
    [
        "evals/agentic",
        "fixtures/reference",
        "score.json",
        "manifest.json",
        "run_meta.json",
    ],
)
def test_name_markers_fire_without_a_resolvable_path(tree, name):
    assert hit(tree, call(command=f"find / -path '*{name}*'"))


# ------------------------------------------------------------ 4b. globs and expansions
@pytest.mark.parametrize(
    "fmt",
    [
        "ls {tmp}/dartwork-mpl-ev*/",
        "ls {tmp}/dartwork-mpl-evals?/",
        "ls {tmp}/[d]artwork-mpl-evals/",
        "cat {tmp}/$NAME/manifest",
        "cat {tmp}/`echo dartwork-mpl-evals`/x",
        "ls {tmp}/{{dartwork-mpl-evals,y}}/",
        "ls ../*/plot.py",
    ],
)
def test_glob_or_expansion_from_a_grading_ancestor(tree, fmt):
    assert hit(tree, call(command=fmt.format(tmp=tree.records.parent)))


@pytest.mark.parametrize(
    "cmd",
    ["ls .venv/lib/*/site-packages", "ls out/*.png", "echo $PATH", "ls *.py"],
)
def test_globs_inside_the_project_are_clean(tree, cmd):
    assert not hit(tree, call(command=cmd))


def test_glob_pattern_that_reaches_a_root_from_a_bare_slash(tree):
    _, *rest = [c for c in str(tree.records).split("/") if c]
    deep = "/*/" + "/".join(rest) + "/baseline/run.json"
    anydepth = "/**/" + tree.records.name + "/baseline/run.json"
    assert hit(tree, call(command=f"cat {deep}"))
    assert hit(tree, call(command=f"cat {anydepth}"))


def test_glob_characters_in_outputs_or_shallow_commands_are_clean(tree):
    css = "--surface-1: #fcfcfb;   /* chart surface */"
    assert not hit(
        tree, json.dumps({"type": "function_call_output", "output": css})
    )
    assert not hit(tree, call(command="ls /*"))


# ------------------------------------------------------------ 4c. leaving the project
@pytest.mark.parametrize(
    "cmd",
    [
        "cd .. && ls",
        "cd",
        "cd ~ && ls",
        "pushd /tmp",
        "/bin/bash -lc 'cd .. && ls'",
        "cd .venv && cd ../.. && ls",
    ],
)
def test_cd_out_of_the_project(tree, cmd):
    assert hit(tree, call(command=cmd))


def test_cd_within_the_project_is_clean_and_followed(tree):
    assert not hit(tree, call(command="cd .venv/lib && ls ../../data"))
    # relative paths resolve from the cd'd directory: ../../.. leaves the project
    assert hit(
        tree,
        call(command="cd .venv/lib && cat ../../../ffff0000aaaa1111/plot.py"),
    )


def test_tool_workdir_outside_the_project(tree):
    assert hit(tree, call(cmd="ls", workdir=str(tree.work)))
    assert not hit(tree, call(cmd="ls", workdir=str(tree.project)))


# ------------------------------------------------------------ 2. recheck never clears
def _unit(
    tmp_path,
    tree,
    *,
    sandbox: bool,
    at_run: bool,
    transcript: str,
    mounts: list[str] = (),
):
    unit = (
        tmp_path / "records" / "run" / "claude" / "g01-line-gdp" / "noskill-r1"
    )
    unit.mkdir(parents=True)
    cmd = ["claude", "-p", "x"]
    if sandbox:
        hide = [*runner.repo_roots(), unit.parents[3], tree.work]
        cmd = [
            "bwrap",
            *[a for h in hide for a in ("--tmpfs", str(h))],
            *mounts,
            "--bind",
            str(tree.project),
            str(tree.project),
            "--",
            *cmd,
        ]
    rec = {
        "host": "claude",
        "project": str(tree.project),
        "command": cmd,
        "contamination": {
            "contaminated": at_run,
            "hits": ["at run"] if at_run else [],
        },
    }
    common.write_json(unit / "run.json", rec)
    msg = {
        "message": {
            "content": [{"type": "tool_use", "input": {"command": transcript}}]
        }
    }
    (unit / "transcript.jsonl").write_text(json.dumps(msg) + "\n")
    return unit


def _score(unit):
    case = common.load_cases(["g01-line-gdp"])[0]
    return score.score_unit(case, unit)


def test_unsandboxed_run_time_flag_is_never_cleared_by_a_clean_recheck(
    tmp_path, tree
):
    unit = _unit(
        tmp_path, tree, sandbox=False, at_run=True, transcript="ls data"
    )
    r = _score(unit)
    assert r["sandboxed"] is False and r["contaminated"] is True


def test_unsandboxed_recheck_hit_counts_even_if_the_run_time_scan_missed(
    tmp_path, tree
):
    unit = _unit(
        tmp_path, tree, sandbox=False, at_run=False, transcript="cd .. && ls"
    )
    assert _score(unit)["contaminated"] is True


def test_sandboxed_text_evidence_is_advisory_and_kept(tmp_path, tree):
    unit = _unit(
        tmp_path, tree, sandbox=True, at_run=True, transcript="ls data"
    )
    r = _score(unit)
    assert r["sandboxed"] is True and r["contaminated"] is False
    assert r["contamination_text"]["flagged"] is True


# ------------------------------------------------------------ 1. decision runs need the sandbox
def _rows(sandboxed: bool):
    return [
        {
            "host": "claude",
            "case": f"c{i}",
            "arm": arm,
            "rep": 1,
            "unit_id": f"claude/c{i}/{arm}-r1",
            "task_success": True,
            "inspection_observed": arm == "skill",
            "lint_clean": True,
            "sandboxed": sandboxed,
            "tokens": {"total": 100},
        }
        for i in range(20)
        for arm in ("noskill", "skill")
    ]


@pytest.mark.parametrize("flag", [False, None])
def test_compare_blocks_every_verdict_with_an_unsandboxed_unit(flag):
    rows = _rows(True)
    rows[3]["sandboxed"] = flag
    ra = [r for r in rows if r["arm"] == "noskill"]
    rb = [r for r in rows if r["arm"] == "skill"]
    for res in compare.compare_rows(ra, rb, "inspection_observed"):
        assert res["success_verdict"].startswith("blocked")
    for res in compare.endpoints(ra, rb):
        assert res["decision"].startswith("blocked")


def test_compare_gives_verdicts_when_every_unit_was_sandboxed():
    rows = _rows(True)
    ra = [r for r in rows if r["arm"] == "noskill"]
    rb = [r for r in rows if r["arm"] == "skill"]
    (res,) = compare.endpoints(ra, rb)
    assert res["inspection_observed"]["verdict"] == "improved"
    assert res["decision"] == "skill helps"


def test_run_manifest_without_hide_grading_blocks_the_verdict(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    rows = _rows(True)
    (run / "manifest.json").write_text(
        json.dumps(
            {
                "config": {"hide_grading": False},
                "plans": [{"units": [r["unit_id"] for r in rows]}],
            }
        )
    )
    (run / "results.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows)
    )
    res, _ = compare.preregistered(run, None, missing_as_failure=False)
    assert all(r["decision"].startswith("blocked") for r in res)


def test_skill_arms_refuse_to_run_without_the_sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run.py",
            "--ab-skill-install",
            "--host",
            "claude",
            "--work-root",
            str(tmp_path / "w"),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 2


# ------------------------------------------------------------ sandbox coverage (addendum 2)
OTHER_CLAUDE = str(
    Path.home() / ".claude" / "projects" / "-home-x-other" / "s1.jsonl"
)
OTHER_CODEX = str(
    Path.home()
    / ".codex"
    / "sessions"
    / "2026"
    / "10"
    / "22"
    / "rollout-1-other.jsonl"
)


@pytest.mark.parametrize("path", [OTHER_CLAUDE, OTHER_CODEX])
def test_sandboxed_unit_reading_another_units_transcript_is_contaminated(
    tmp_path, tree, path
):
    unit = _unit(
        tmp_path, tree, sandbox=True, at_run=False, transcript=f"cat {path}"
    )
    r = _score(unit)
    assert r["sandboxed"] is True and r["contaminated"] is True
    assert r["contamination_text"]["gating"]


def test_sandboxed_unit_touching_only_its_project_is_clean(tmp_path, tree):
    unit = _unit(
        tmp_path,
        tree,
        sandbox=True,
        at_run=False,
        transcript="ls data && .venv/bin/python plot.py && ls out",
    )
    r = _score(unit)
    assert r["contaminated"] is False and not r["contamination_text"]["flagged"]


def test_a_store_the_sandbox_replaced_is_advisory(tmp_path, tree):
    store = str(Path.home() / ".claude" / "projects")
    unit = _unit(
        tmp_path,
        tree,
        sandbox=True,
        at_run=False,
        transcript=f"cat {OTHER_CLAUDE}",
        mounts=["--tmpfs", store],
    )
    r = _score(unit)
    assert r["contamination_text"]["flagged"] and r["contaminated"] is False


def test_grading_names_gate_even_under_the_sandbox(tmp_path, tree):
    unit = _unit(
        tmp_path,
        tree,
        sandbox=True,
        at_run=False,
        transcript="grep -r x ../../evals/agentic/cases",
    )
    assert _score(unit)["contaminated"] is True


def test_sandbox_hides_home_stores_and_gives_codex_its_own_sessions(tmp_path):
    args, sessions = runner.home_store_mounts("codex", tmp_path / "stores")
    targets = {b for a, b in pairwise(args) if a == "--tmpfs"}
    binds = {
        args[i + 2]: args[i + 1]
        for i, a in enumerate(args[:-2])
        if a == "--bind"
    }
    codex_sessions = str(Path.home() / ".codex" / "sessions")
    if Path(codex_sessions).is_dir():
        assert binds[codex_sessions] == str(sessions)
    claude_projects = str(Path.home() / ".claude" / "projects")
    if Path(claude_projects).is_dir():
        assert claude_projects in targets
    assert not any(".sqlite" in t for t in [*targets, *binds])
    args, sessions = runner.home_store_mounts("claude", tmp_path / "stores2")
    assert sessions is None
