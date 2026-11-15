"""Run one case in one arm: a fresh project, an isolated ``claude -p``, the evidence.

Isolation (measured on Claude Code 2.1.325, see README): ``--bare`` is not
used because it removes the Skill tool, so the model never sees a project
skill. Instead every run gets an empty ``CLAUDE_CONFIG_DIR`` (no user
settings, plugins, skills, hooks, memory or CLAUDE.md), ``--setting-sources
project`` (the temp project holds only the installed skill),
``--strict-mcp-config``, bundled skills and built-in plugins switched off, and
a scrubbed environment. The init event is then checked against the arm.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import judge

REPO = Path(__file__).resolve().parents[1]
CASES = Path(__file__).resolve().parent / "cases"
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
KEYCHAIN_HELPER = """#!/bin/sh
security find-generic-password -s "Claude Code-credentials" -w | \
"{python}" -c 'import json,sys; print(json.load(sys.stdin)["claudeAiOauth"]["accessToken"])'
"""


@dataclass(frozen=True)
class Case:
    """One request: the prompt, its data files and the facts to check."""

    name: str
    prompt: str
    files: dict[str, str]
    expect: dict[str, Any]


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


def environment(cfg: Path) -> dict[str, str]:
    """A scrubbed environment: this checkout's Python first, a fresh config dir."""
    claude = shutil.which("claude") or "claude"
    path = [str(Path(sys.executable).parent), str(Path(claude).parent)]
    path += ["/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    env = {
        k: os.environ[k]
        for k in ("HOME", "USER", "LOGNAME", "TMPDIR")
        if k in os.environ
    }
    env |= {
        "PATH": os.pathsep.join(path),
        "LANG": "en_US.UTF-8",
        "TERM": "dumb",
        "CLAUDE_CONFIG_DIR": str(cfg),
        "CLAUDE_CODE_DISABLE_BUNDLED_SKILLS": "1",
    }
    if "ANTHROPIC_API_KEY" in os.environ:
        env["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
    return env


def auth_helper(cfg: Path) -> Path | None:
    """An apiKeyHelper reading the logged-in OAuth token, unless an API key is set."""
    if "ANTHROPIC_API_KEY" in os.environ or sys.platform != "darwin":
        return None
    helper = cfg / "api-key-helper.sh"
    helper.write_text(KEYCHAIN_HELPER.format(python=sys.executable))
    helper.chmod(0o700)
    return helper


def prepare(case: Case, arm: judge.Arm, project: Path) -> None:
    """Write the case's files and install the skill."""
    for name, text in case.files.items():
        (project / name).write_text(text.lstrip("\n"), encoding="utf-8")
    if arm.skill:
        install = [
            "-m",
            "dartwork_mpl.guide",
            "install",
            "--dest",
            str(project),
        ]
        subprocess.run(
            [sys.executable, *install], check=True, capture_output=True
        )


def newest(project: Path, suffix: str, since: float) -> Path | None:
    """The most recently written ``suffix`` file the agent left in the project."""
    files = [
        p
        for p in project.rglob(f"*{suffix}")
        if not {".claude", ".agents"} & set(p.relative_to(project).parts)
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


RUN_SCRIPT = re.compile(
    r"python3?(?:\s+-[A-Za-z]+)*\s+([^\s;&|<>-][^\s;&|<>]*\.py)([^\n;&|]*)"
)


WRITE_HEREDOC = re.compile(
    r"cat\s+>\s*(\S+)\s+<<-?\s*'?(\w+)'?\n(.*?)\n\2\b", re.S
)


def script_run(trace: judge.Trace) -> tuple[str, list[str]] | None:
    """The script the agent last ran with ``python X.py args`` (Bash), and its args."""
    for call in reversed(trace.calls):
        if call.get("name") != "Bash":
            continue
        cmd = str((call.get("input") or {}).get("command", ""))
        for match in reversed(list(RUN_SCRIPT.finditer(cmd))):
            try:
                words = shlex.split(match.group(2))
            except ValueError:
                words = []
            args: list[str] = []
            for word in words:
                if re.match(r"^\d*[<>]", word):
                    break
                args.append(word)
            return match.group(1), args
    return None


def written(trace: judge.Trace, path: str) -> str | None:
    """What the transcript last wrote to ``path`` (Write, or ``cat > path <<EOF``)."""
    text: str | None = None
    for call in trace.calls:
        given = call.get("input") or {}
        if call.get("name") == "Write" and str(
            given.get("file_path", "")
        ).endswith(path.lstrip("./")):
            text = str(given.get("content", ""))
        for match in WRITE_HEREDOC.finditer(str(given.get("command", ""))):
            if match.group(1) == path:
                text = match.group(3)
    return text


def script_source(trace: judge.Trace, project: Path, raw: str) -> str | None:
    """The run script's text: from the project, else as the transcript wrote it.

    Scripts outside the project (``/tmp/plot.py``) are shared between
    concurrent runs, so their text is taken from the transcript.
    """
    path = Path(raw).expanduser()
    path = path if path.is_absolute() else project / path
    inside = path.resolve().is_relative_to(project.resolve())
    if inside and path.is_file():
        return path.read_text(encoding="utf-8")
    return written(trace, raw) or (
        path.read_text("utf-8") if path.is_file() else None
    )


def probe(project: Path, source: str, args: list[str]) -> dict[str, Any]:
    """Re-run ``source`` in a copy of the project and measure its figure."""
    with tempfile.TemporaryDirectory(prefix="dmpl-eval-probe-") as tmp:
        copy = Path(tmp) / "project"
        shutil.copytree(project, copy, symlinks=True)
        script, out = copy / "_eval_source.py", Path(tmp) / "probe.json"
        script.write_text(source, encoding="utf-8")
        env = {
            k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")
        }
        env |= {"PYTHONPATH": str(REPO), "MPLBACKEND": "Agg"}
        try:
            done = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "evals.probe",
                    str(script),
                    str(out),
                    *args,
                ],
                cwd=copy,
                env=env,
                capture_output=True,
                text=True,
                timeout=PROBE_TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"error": "probe timed out"}
        if not out.exists():
            return {"error": f"probe crashed: {done.stderr[-800:]}"}
        return json.loads(out.read_text())


def lint(source: str) -> list[dict[str, Any]]:
    """``dm.lint_code`` findings on the final source."""
    import dartwork_mpl as dm

    return [
        {
            "rule": f.rule_id,
            "severity": f.severity.value,
            "line": f.line,
            "message": f.message,
        }
        for f in dm.lint_code(source)
    ]


def collect(
    trace: judge.Trace, project: Path, out: Path, since: float
) -> tuple[str | None, str | None, list[str]]:
    """Copy the final image and source into ``out``; their names and the script's args."""
    image = newest(project, ".png", since)
    ran = script_run(trace)
    script = newest(project, ".py", since)
    args = ran[1] if ran else []
    source = (
        script_source(trace, project, ran[0])
        if ran
        else script.read_text(encoding="utf-8")
        if script
        else inline_source(trace)
    )
    if source is not None:
        (out / "source.py").write_text(source, encoding="utf-8")
    if image is None or not image.exists():
        return None, "source.py" if source is not None else None, args
    shutil.copy(image, out / "figure.png")
    return "figure.png", "source.py" if source is not None else None, args


def launch(cmd: list[str], project: Path, cfg: Path, out: Path) -> str | None:
    """Run ``claude`` into ``out/stream.jsonl``; an error message on timeout."""
    with (
        (out / "stream.jsonl").open("wb") as stream,
        (out / "stderr.txt").open("wb") as err,
    ):
        proc = subprocess.Popen(
            [shutil.which("claude") or "claude", *cmd[1:]],
            cwd=project,
            env=environment(cfg),
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


def assess(
    case: Case,
    arm_name: str,
    out: Path,
    project: Path,
    session: dict[str, Any],
    since: float,
) -> dict[str, Any]:
    """Judge a finished session from its transcript and project; write ``result.json``."""
    arm = judge.ARM_SPECS[arm_name]
    lines = (out / "stream.jsonl").read_text(errors="replace").splitlines()
    trace = judge.parse_stream(lines)
    image, source_name, args = collect(trace, project, out, since)
    source = (out / "source.py").read_text("utf-8") if source_name else None
    if source and session.get("cwd"):  # a copied project: point paths at it
        cwd = str(session["cwd"])
        for old in (cwd, cwd.removeprefix("/private")):
            source = source.replace(old, str(project))
            args = [a.replace(old, str(project)) for a in args]
    probed = probe(project, source, args) if source else {"error": "no source"}
    found = lint(source) if source else []
    figure = probed.get("figure")
    critical = [
        f"{f['rule']} (line {f['line']})"
        for f in found
        if f["severity"] == "critical"
    ]
    verdict, reasons = judge.verdict(
        judge.Evidence(
            isolation=judge.isolation_problems(trace.init, arm),
            harness_error=harness_error(trace, session.get("timeout")),
            has_image=image is not None,
            figure=figure,
            probe_error=probed.get("error"),
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
        "image": image,
        "source": source_name,
        "argv": args,
        "probe_error": probed.get("error"),
        "figure": figure,
        "lint": found,
    }
    text = json.dumps(record, ensure_ascii=False, indent=1)
    (out / "result.json").write_text(text, encoding="utf-8")
    return record


def run_one(case: Case, arm_name: str, out: Path, model: str) -> dict[str, Any]:
    """Run the case in the arm, judge it, write ``result.json`` into ``out``."""
    arm = judge.ARM_SPECS[arm_name]
    out.mkdir(parents=True, exist_ok=True)
    project = Path(
        tempfile.mkdtemp(prefix=f"dmpl-eval-{case.name}-{arm_name}-")
    )
    cfg = Path(tempfile.mkdtemp(prefix="dmpl-eval-cfg-"))
    try:
        prepare(case, arm, project)
        cmd = command(arm, case.prompt, model, auth_helper(cfg))
        started = time.time()
        timeout = launch(cmd, project, cfg, out)
        session = {
            "command": [c if c != case.prompt else "<prompt>" for c in cmd],
            "seconds": round(time.time() - started, 1),
            "started": started,
            "timeout": timeout,
        }
        ignore = shutil.ignore_patterns(".claude", ".agents")
        shutil.copytree(
            project, out / "project", ignore=ignore, dirs_exist_ok=True
        )
        return assess(case, arm_name, out, project, session, started)
    finally:
        shutil.rmtree(project, ignore_errors=True)
        shutil.rmtree(cfg, ignore_errors=True)


def rejudge(case: Case, out: Path) -> dict[str, Any]:
    """Judge a recorded run again (transcript and project copy), without ``claude``."""
    old = json.loads((out / "result.json").read_text(encoding="utf-8"))
    keys = ("command", "seconds", "started", "timeout")
    session = {k: old.get(k) for k in keys}
    session["cwd"] = (old.get("isolation") or {}).get("cwd")
    project = (out / "project").resolve()
    return assess(case, old["arm"], out, project, session, 0.0)
