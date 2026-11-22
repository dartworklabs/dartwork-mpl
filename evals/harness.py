"""Run one case in one arm: a private uv project, an isolated ``claude -p``, the evidence.

Isolation (measured on Claude Code 2.1.325, see README): ``--bare`` is not
used because it removes the Skill tool, so the model never sees a project
skill. Instead every run gets its own root (``confine.Box``): a uv project
with this checkout's wheel installed, an empty ``HOME``, ``TMPDIR`` and
``CLAUDE_CONFIG_DIR`` (no user settings, plugins, skills, hooks, memory or
CLAUDE.md), ``--setting-sources project`` (the project holds only the
installed skill), ``--strict-mcp-config``, bundled skills and built-in
plugins switched off, and a scrubbed environment. The init event is then
checked against the arm.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path
from typing import Any

from . import confine, judge, shelltrace

REPO = Path(__file__).resolve().parents[1]
CASES = Path(__file__).resolve().parent / "cases"
SKILL_DIR = REPO / "skills" / "dartwork-mpl"
DEFAULT_MODEL = "claude-sonnet-5-5"
CLAUDE_TIMEOUT = 900.0
PROBE_TIMEOUT = 180.0
BUILTIN_PLUGINS = (
    *("agents-md", "claude-test", "diff", "easel", "mermaid", "mods-guide"),
    *("plugin-authoring", "privacy", "responsive-mode", "sec-default"),
    *("telemetry", "tips", "you-should-know"),
)
# Built-in skills that CLAUDE_CODE_DISABLE_BUNDLED_SKILLS leaves on.
BUILTIN_SKILLS = ("design", "doctor")
# HOME is the run's empty one; the keychain is found through the real one.
KEYCHAIN_HELPER = """#!/bin/sh
HOME="{home}" security find-generic-password -s "Claude Code-credentials" -w | \
"{python}" -c 'import json,sys; print(json.load(sys.stdin)["claudeAiOauth"]["accessToken"])'
"""
# The agent's project: the library from this checkout's wheel, and the
# versions the re-render (this checkout's environment) draws with.
PYPROJECT = """[project]
name = "charts"
version = "0.1.0"
requires-python = ">={python}"
dependencies = [{dependencies}]

[tool.uv]
constraint-dependencies = [{pins}]

[tool.uv.sources]
dartwork-mpl = {{ path = "{wheel}" }}
"""
PINNED = ("matplotlib", "numpy", "pandas", "pillow")
# What of a run's root is not evidence: the installed library and skill, tool state.
NOT_EVIDENCE = (".claude", ".agents", ".venv", "__pycache__")
NOT_EVIDENCE += ("uv.lock", "claude-*", "uv-*.lock")


@dataclass(frozen=True)
class Case:
    """One request: the prompt, its data files and the facts to check."""

    name: str
    prompt: str
    files: dict[str, str]
    expect: dict[str, Any]


@dataclass(frozen=True)
class Setup:
    """What the runs of one sweep share: the wheel under test and what it is."""

    wheel: Path
    provenance: dict[str, Any]


def installed(name: str) -> str | None:
    """The version of a distribution in this environment, if it is there."""
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def tree_hash(folder: Path) -> str:
    """One sha256 over a folder's file names and bytes."""
    digest = hashlib.sha256()
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        digest.update(path.relative_to(folder).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def said(*cmd: str) -> str:
    """A command's stdout in the repository, stripped (empty if it failed)."""
    done = subprocess.run(
        cmd, cwd=REPO, capture_output=True, text=True, check=False
    )
    return done.stdout.strip() if done.returncode == 0 else ""


def setup(folder: Path) -> Setup:
    """Build this checkout's wheel into ``folder`` and say what the sweep runs against."""
    build = ["uv", "build", "--wheel", "--out-dir", str(folder)]
    subprocess.run(build, cwd=REPO, check=True, capture_output=True)
    wheel = next(folder.glob("*.whl")).resolve()
    version = re.search(
        r"^\s*version:\s*(\S+)", (SKILL_DIR / "SKILL.md").read_text(), re.M
    )
    provenance = {
        "library": {
            "version": installed("dartwork-mpl"),
            "commit": said("git", "rev-parse", "HEAD"),
            "dirty": bool(said("git", "status", "--porcelain")),
            "wheel": wheel.name,
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        },
        "skill": {
            "version": version.group(1) if version else None,
            "sha256": tree_hash(SKILL_DIR),
        },
        "claude": said(shutil.which("claude") or "claude", "--version"),
        "python": platform.python_version(),
        "packages": {n: installed(n) for n in PINNED},
        "confinement": "sandbox-exec" if confine.enforced() else "none",
    }
    return Setup(wheel, provenance)


def load_cases(names: list[str] | None = None) -> list[Case]:
    """The cases under ``evals/cases``, all or the named ones, by name."""
    found: list[Case] = []
    for path in sorted(CASES.glob("*.toml")):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        found.append(
            Case(
                path.stem,
                str(data["prompt"]),
                {str(k): str(v) for k, v in data.get("files", {}).items()},
                dict(data.get("expect", {})),
            )
        )
    if names:
        unknown = set(names) - {c.name for c in found}
        if unknown:
            raise SystemExit(f"unknown cases: {sorted(unknown)}")
        found = [c for c in found if c.name in names]
    return found


def settings(helper: Path | None) -> dict[str, Any]:
    """The ``--settings`` JSON: auth helper, no memory, hooks, extra skills."""
    data: dict[str, Any] = {
        "autoMemoryEnabled": False,
        "disableAllHooks": True,
        "skillOverrides": dict.fromkeys(BUILTIN_SKILLS, "off"),
        "enabledPlugins": {
            f"cc-plugin-{p}@builtin": False for p in BUILTIN_PLUGINS
        },
    }
    if helper is not None:
        data["apiKeyHelper"] = str(helper)
    return data


def command(
    arm: judge.Arm, prompt: str, model: str, helper: Path | None
) -> list[str]:
    """The exact ``claude`` command line for one run."""
    cmd = ["claude", "-p", prompt, "--model", model]
    cmd += ["--output-format", "stream-json", "--verbose"]
    cmd += ["--no-session-persistence", "--setting-sources", "project"]
    cmd += ["--settings", json.dumps(settings(helper))]
    cmd += ["--permission-mode", "bypassPermissions"]
    cmd += ["--tools", ",".join(arm.tools), "--strict-mcp-config"]
    return cmd


@cache
def uv_dir(kind: str) -> str:
    """``uv cache dir`` / ``uv python dir``: shared by the runs, outside their HOME."""
    return said("uv", kind, "dir")


def environment(box: confine.Box) -> dict[str, str]:
    """A scrubbed environment: the project's Python first, the run's own HOME and TMPDIR."""
    tools = [shutil.which(t) for t in ("claude", "uv")]
    path = [str(box.project / ".venv" / "bin")]
    path += [str(Path(t).parent) for t in tools if t]
    path += ["/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    env = {k: os.environ[k] for k in ("USER", "LOGNAME") if k in os.environ}
    env |= {
        "HOME": str(box.home),
        "TMPDIR": str(box.tmp),
        "CLAUDE_CODE_TMPDIR": str(box.tmp),
        "PATH": os.pathsep.join(dict.fromkeys(path)),
        "LANG": "en_US.UTF-8",
        "TERM": "dumb",
        "CLAUDE_CONFIG_DIR": str(box.cfg),
        "CLAUDE_CODE_DISABLE_BUNDLED_SKILLS": "1",
        "UV_CACHE_DIR": uv_dir("cache"),
        "UV_PYTHON_INSTALL_DIR": uv_dir("python"),
    }
    if "ANTHROPIC_API_KEY" in os.environ:
        env["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
    return env


def auth_helper(cfg: Path) -> Path | None:
    """An apiKeyHelper reading the logged-in OAuth token, unless an API key is set."""
    if "ANTHROPIC_API_KEY" in os.environ or sys.platform != "darwin":
        return None
    helper = cfg / "api-key-helper.sh"
    helper.write_text(
        KEYCHAIN_HELPER.format(home=Path.home(), python=sys.executable)
    )
    helper.chmod(0o700)
    return helper


def pyproject(wheel: Path) -> str:
    """The project file: dartwork-mpl from ``wheel``, drawing libraries pinned to ours."""
    pins = [f'"{n}=={v}"' for n in PINNED if (v := installed(n))]
    wanted = ["dartwork-mpl", *(["pandas"] if installed("pandas") else [])]
    return PYPROJECT.format(
        python=".".join(platform.python_version_tuple()[:2]),
        dependencies=", ".join(f'"{d}"' for d in wanted),
        pins=", ".join(pins),
        wheel=wheel,
    )


def prepare(case: Case, arm: judge.Arm, project: Path, wheel: Path) -> None:
    """Make the project a synced uv project with the case's files and the skill.

    ``uv run python plot.py``, ``python plot.py`` and ``uv run dartwork-mpl
    path`` then work in place, against the wheel, as after ``uv add``.
    """
    for name, text in case.files.items():
        (project / name).write_text(text.lstrip("\n"), encoding="utf-8")
    (project / "pyproject.toml").write_text(pyproject(wheel), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    sync = ["uv", "sync", "--quiet", "--python", sys.executable]
    subprocess.run(sync, cwd=project, env=env, check=True, capture_output=True)
    if arm.skill:
        python = str(project / ".venv" / "bin" / "python")
        install = ["-m", "dartwork_mpl.guide", "install", "--dest", "."]
        subprocess.run(
            [python, *install], cwd=project, check=True, capture_output=True
        )


def newest(folder: Path, suffix: str, since: float) -> Path | None:
    """The most recently written ``suffix`` file the agent left under ``folder``."""
    files = [
        p
        for p in folder.rglob(f"*{suffix}")
        if not set(NOT_EVIDENCE) & set(p.relative_to(folder).parts)
        and p.stat().st_mtime >= since
    ]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


HEREDOC = re.compile(r"python3?\s+-\s*<<-?\s*'?(\w+)'?\n(.*?)\n\1", re.S)


def inline_source(trace: judge.Trace) -> str | None:
    """The last Python heredoc the agent ran through Bash, if any drew a plot."""
    for call in reversed(trace.calls):
        cmd = str((call.get("input") or {}).get("command", ""))
        match = HEREDOC.search(cmd)
        if match and "matplotlib" in match.group(2):
            return match.group(2)
    return None


@dataclass(frozen=True)
class Source:
    """The script judged: its text, where its copy lies and how the agent ran it."""

    text: str | None = None
    where: Path | None = None
    script: str | None = None
    args: tuple[str, ...] = ()
    cwd: str | None = None
    env: tuple[tuple[str, str], ...] = ()
    packages: tuple[str, ...] = ()
    problem: str | None = None


# One place of the run as the agent saw it, and its copy in the run's output.
Places = list[tuple[str, Path]]


def local(path: str, places: Places) -> Path | None:
    """The copy of a path the agent used, if it lies in one of the run's places."""
    for original, copy in places:
        if shelltrace.inside(path, original):
            base = original.removeprefix("/private").rstrip("/")
            return copy / path.removeprefix("/private")[len(base) :].lstrip("/")
    return None


def find_source(
    trace: judge.Trace, places: Places, variables: dict[str, str], since: float
) -> Source:
    """The script that drew the figure: the last one run, else the newest, else a heredoc."""
    project, copy = places[0]
    calls = [c for c in trace.calls if c.get("name") == "Bash"]
    commands = [str((c.get("input") or {}).get("command", "")) for c in calls]
    runs = shelltrace.runs(commands, project, variables)
    if runs:
        run = runs[-1]
        where = local(run.script, places)
        if (
            not run.resolved
        ):  # $(mktemp -d)/plot.py: the newest file of that name
            name = posixpath.basename(run.script)
            found = [newest(c, name, since) for _, c in places if c.is_dir()]
            where = max(
                (p for p in found if p),
                key=lambda p: p.stat().st_mtime,
                default=None,
            )
        known = Source(
            script=run.script,
            args=run.args,
            cwd=run.cwd,
            env=run.env,
            packages=run.packages,
        )
        if where is None or not where.is_file():
            why = f"the script the agent ran ({run.script}) is not among its files"
            return replace(known, problem=why)
        return replace(known, text=where.read_text("utf-8"), where=where)
    script = newest(copy, ".py", since) if copy.is_dir() else None
    if script:
        return Source(script.read_text(encoding="utf-8"), script, cwd=project)
    inline = inline_source(trace)
    if inline:
        return Source(inline, cwd=project)
    return Source(problem="no script found in the transcript or the project")


def added_packages(source: Source, project: Path) -> list[str]:
    """Packages the agent's run had beyond the prepared project's."""
    added = [p for p in source.packages if not p.startswith("dartwork-mpl")]
    declared = project / "pyproject.toml"
    if declared.is_file():
        data = tomllib.loads(declared.read_text(encoding="utf-8"))
        wanted = data.get("project", {}).get("dependencies", [])
        added += [d for d in wanted if d not in ("dartwork-mpl", "pandas")]
    return list(dict.fromkeys(added))


def compare(mirror: Path, since: float, figure: Path) -> dict[str, Any]:
    """Each image the re-run wrote under ``mirror`` against the agent's figure."""
    import numpy as np
    from PIL import Image

    want = np.asarray(Image.open(figure).convert("RGBA"), dtype=float)
    renders: list[dict[str, Any]] = []
    for path in sorted(mirror.rglob("*.png")):
        if path.stat().st_mtime < since:
            continue
        got = np.asarray(Image.open(path).convert("RGBA"), dtype=float)
        same = got.shape == want.shape
        rms = float(np.sqrt(((got - want) ** 2).mean())) if same else None
        renders.append(
            {
                "path": path.relative_to(mirror).as_posix(),
                "size": [got.shape[1], got.shape[0]],
                "rms": None if rms is None else round(rms, 3),
            }
        )
    return {"figure_px": [want.shape[1], want.shape[0]], "renders": renders}


def probe(
    out: Path, places: Places, source: Source, figure: Path | None
) -> dict[str, Any]:
    """Re-run the source in a mirror of the run's places; measure and compare its figure."""
    assert source.text is not None
    with tempfile.TemporaryDirectory(prefix="dmpl-eval-probe-") as tmp:
        mirror = Path(tmp).resolve()
        for _, copy in places:
            if copy.is_dir():
                shutil.copytree(copy, mirror / copy.name, symlinks=True)
            else:
                (mirror / copy.name).mkdir()

        def there(text: str) -> str:
            for original, copy in places:
                for old in (original, original.removeprefix("/private")):
                    text = text.replace(old, str(mirror / copy.name))
            return text

        script = mirror / (
            source.where.relative_to(out)
            if source.where
            else Path(places[0][1].name) / "_eval_source.py"
        )
        script.write_text(there(source.text), encoding="utf-8")
        cwd = Path(there(source.cwd or places[0][0]))
        if not (cwd.is_dir() and cwd.is_relative_to(mirror)):
            cwd = mirror / places[0][1].name
        report_path = mirror / "_eval_probe.json"
        args = [there(a) for a in source.args]
        env = {
            k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")
        }
        # The backend stays as the agent's script found it (see probe.py).
        env.pop("MPLBACKEND", None)
        env |= {"PYTHONPATH": str(REPO)} | dict(source.env)
        cmd = [sys.executable, "-m", "evals.probe", str(script)]
        if extra := added_packages(source, places[0][1]):
            # What the agent added (uv run --with scipy, uv add) on top of ours.
            layer = [w for p in extra for w in ("--with", p)]
            uv = ["uv", "run", "--project", str(REPO), "--no-sync", *layer]
            cmd = [*uv, "python", *cmd[1:]]
        started = time.time()
        run = [*cmd, str(report_path), *args]
        try:
            done = subprocess.run(
                run,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=PROBE_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"error": "probe timed out"}
        if not report_path.exists():
            return {"error": f"probe crashed: {done.stderr[-800:]}"}
        report: dict[str, Any] = json.loads(report_path.read_text())
        if figure is None:
            return report
        report |= compare(mirror, started, figure)
        near = [r for r in report["renders"] if r["rms"] is not None]
        if near and min(r["rms"] for r in near) > judge.SAME_PICTURE_RMS:
            # Not the figure: is it this script, drawing differently each time?
            first = mirror / min(near, key=lambda r: r["rms"])["path"]
            kept = first.with_name("_eval_first.png")
            shutil.copy(first, kept)
            again = subprocess.run(
                run, cwd=cwd, env=env, capture_output=True, check=False
            )
            if again.returncode == 0:
                twice = compare(mirror, 0.0, kept)["renders"]
                same = [r for r in twice if r["path"] == near[0]["path"]]
                report["rerun_rms"] = same[0]["rms"] if same else None
        return report


def lint(source: str) -> list[dict[str, Any]]:
    """``dm.lint_code`` findings on the final source."""
    import dartwork_mpl as dm

    return [
        {
            "rule": f.rule_id,
            "severity": str(f.severity),
            "line": f.line,
            "message": f.message,
        }
        for f in dm.lint_code(source)
    ]


def launch(cmd: list[str], box: confine.Box, out: Path) -> str | None:
    """Run ``claude`` in its box into ``out/stream.jsonl``; an error message on timeout."""
    claude = [shutil.which("claude") or "claude", *cmd[1:]]
    with (
        (out / "stream.jsonl").open("wb") as stream,
        (out / "stderr.txt").open("wb") as err,
    ):
        proc = subprocess.Popen(
            confine.confine(claude, box, [uv_dir("cache")]),
            cwd=box.project,
            env=environment(box),
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=err,
        )
        try:
            proc.wait(CLAUDE_TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return f"claude timed out after {CLAUDE_TIMEOUT:.0f} s"
    return None


def harness_error(trace: judge.Trace, timeout: str | None) -> str | None:
    """Why the session itself failed, if it did."""
    if timeout or trace.result is None:
        return timeout or "no result event"
    if trace.result.get("is_error"):
        return f"claude error: {str(trace.result.get('result'))[:200]}"
    return None


INIT_KEYS = ("cwd", "model", "tools", "mcp_servers", "skills", "plugins")


INIT_KEYS = ("cwd", "model", "tools", "mcp_servers", "skills", "plugins")
SESSION_KEYS = ("command", "seconds", "started", "timeout", "root", "project")
SESSION_KEYS += ("confined", "provenance")


def strays(trace: judge.Trace, source: Source, root: str) -> list[str]:
    """Where the transcript shows work outside the run's root."""
    given = [c.get("input") or {} for c in trace.calls]
    paths = [str(g["file_path"]) for g in given if g.get("file_path")]
    if source.script and "$" not in source.script:
        paths.append(source.script)
    commands = [str(g.get("command", "")) for g in given]
    return judge.strays(paths, commands, root)


def assess(
    case: Case, arm_name: str, out: Path, session: dict[str, Any]
) -> dict[str, Any]:
    """Judge a finished session from its transcript and the copies in ``out``; write ``result.json``."""
    arm = judge.ARM_SPECS[arm_name]
    lines = (out / "stream.jsonl").read_text(errors="replace").splitlines()
    trace = judge.parse_stream(lines)
    project = str(session.get("project") or (trace.init or {}).get("cwd") or "")
    root = session.get("root")
    places: Places = [(project, out / "project")]
    variables: dict[str, str] = {}
    if root:
        places.append((f"{root}/tmp", out / "tmp"))
        variables = {"HOME": f"{root}/home", "TMPDIR": f"{root}/tmp"}
    since = float(session.get("started") or 0.0)
    made = newest(out / "project", ".png", since)
    figure_png = out / "figure.png" if made else None
    if made and figure_png:
        shutil.copy(made, figure_png)
    source = find_source(trace, places, variables, since)
    probed: dict[str, Any] = {}
    problem = source.problem
    if source.text is not None:
        (out / "source.py").write_text(source.text, encoding="utf-8")
        probed = probe(out, places, source, figure_png)
        if probed.get("figure") is None:
            problem = f"re-running it drew no figure ({probed.get('error')})"
        elif figure_png:
            size = tuple(probed["figure_px"])
            problem = judge.reproduction(
                size, probed["renders"], probed.get("rerun_rms")
            )
    found = lint(source.text) if source.text is not None else []
    figure = probed.get("figure")
    critical = [
        f"{f['rule']} (line {f['line']})"
        for f in found
        if f["severity"] == "critical"
    ]
    outside = (
        []
        if session.get("confined")
        else strays(trace, source, root or project)
    )
    verdict, reasons = judge.verdict(
        judge.Evidence(
            isolation=judge.isolation_problems(trace.init, arm),
            harness_error=harness_error(trace, session.get("timeout")),
            strays=outside,
            has_image=figure_png is not None,
            source_problem=problem,
            figure=figure,
            # The control arm is plain matplotlib: our lint does not gate it.
            lint_critical=[] if arm_name == "bare" else critical,
            missing=judge.missing_facts(case.expect, figure) if figure else [],
        )
    )
    result = trace.result or {}
    record: dict[str, Any] = {
        "case": case.name,
        "arm": arm_name,
        "verdict": verdict,
        "reasons": reasons,
        "prompt": case.prompt,
        **session,
        "isolation": {k: (trace.init or {}).get(k) for k in INIT_KEYS},
        "tools": trace.tool_names,
        "turns": result.get("num_turns"),
        "cost_usd": result.get("total_cost_usd"),
        "usage": result.get("usage"),
        "final_text": str(result.get("result") or ""),
        "image": "figure.png" if figure_png else None,
        "source": "source.py" if source.text is not None else None,
        "script": source.script,
        "script_cwd": source.cwd,
        "argv": list(source.args),
        "strays": outside,
        "source_problem": problem,
        "figure_px": probed.get("figure_px"),
        "renders": probed.get("renders"),
        "rerun_rms": probed.get("rerun_rms"),
        "probe_error": probed.get("error"),
        "figure": figure,
        "lint": found,
    }
    text = json.dumps(record, ensure_ascii=False, indent=1)
    (out / "result.json").write_text(text, encoding="utf-8")
    return record


def keep(box: confine.Box, out: Path) -> None:
    """Copy what the agent left in its project and temp dir into ``out``."""
    ignore = shutil.ignore_patterns(*NOT_EVIDENCE)
    for place in (box.project, box.tmp):
        shutil.copytree(
            place,
            out / place.name,
            ignore=ignore,
            symlinks=True,
            dirs_exist_ok=True,
        )


def run_one(
    case: Case, arm_name: str, out: Path, model: str, shared: Setup
) -> dict[str, Any]:
    """Run the case in the arm, judge it, write ``result.json`` into ``out``."""
    arm = judge.ARM_SPECS[arm_name]
    out.mkdir(parents=True, exist_ok=True)
    box = confine.make(f"{case.name}-{arm_name}")
    try:
        prepare(case, arm, box.project, shared.wheel)
        cmd = command(arm, case.prompt, model, auth_helper(box.cfg))
        started = time.time()
        timeout = launch(cmd, box, out)
        session = {
            "command": [c if c != case.prompt else "<prompt>" for c in cmd],
            "seconds": round(time.time() - started, 1),
            "started": started,
            "timeout": timeout,
            "root": str(box.root),
            "project": str(box.project),
            "confined": confine.enforced(),
            "provenance": shared.provenance,
        }
        keep(box, out)
        return assess(case, arm_name, out, session)
    finally:
        shutil.rmtree(box.root, ignore_errors=True)


def rejudge(case: Case, out: Path) -> dict[str, Any]:
    """Judge a recorded run again (transcript and the copies in ``out``), without ``claude``."""
    old = json.loads((out / "result.json").read_text(encoding="utf-8"))
    session = {k: old[k] for k in SESSION_KEYS if k in old}
    return assess(case, old["arm"], out, session)
