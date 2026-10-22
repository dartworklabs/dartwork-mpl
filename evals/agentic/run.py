"""Run eval cases headless in Claude Code and/or Codex.

    uv run python evals/agentic/run.py --host claude --case g01-line-gdp
    uv run python evals/agentic/run.py --jobs 4                         # 40 cases x both hosts
    uv run python evals/agentic/run.py --wheel W.whl --ab-skill SKILL_DIR --reps 2 --jobs 4

Each run unit ``ROOT/<run-id>/<host>/<case>/<arm>-r<k>/`` gets a fresh
``project/`` (own ``uv venv`` with the evaluated wheel + pandas, the case's
input CSVs and, for edit cases, the base ``plot.py`` already rendered). Only
those inputs are agent-visible: case files, oracles, references and scorer code
stay in this repository. The host runs headless with user-level context
isolated (see README); ``run.json``, the transcript, the original artifacts
(``artifacts/``) and inspection evidence are written next to ``project/``.
Units run in a seeded random order. Score afterwards with ``score.py``.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import numpy as np
from common import (
    DEFAULT_ROOT,
    FIXTURES,
    REPO,
    SUFFIX_VERSION,
    full_prompt,
    load_cases,
    read_json,
    write_json,
)
from PIL import Image

TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"]
ENV_KEEP = (
    "HOME",
    "USER",
    "LOGNAME",
    "PATH",
    "LANG",
    "LC_ALL",
    "SHELL",
    "TMPDIR",
)


def sh(
    argv: list[str],
    cwd: Path | None = None,
    env: dict | None = None,
    timeout: int = 600,
) -> str:
    proc = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )
    if proc.returncode:
        raise RuntimeError(f"{argv[:3]} failed: {proc.stderr[-2000:]}")
    return proc.stdout


def sha256(data: bytes | Path) -> str:
    return hashlib.sha256(
        data.read_bytes() if isinstance(data, Path) else data
    ).hexdigest()


def base_env(project: Path, extra: dict | None = None) -> dict:
    env = {k: os.environ[k] for k in ENV_KEEP if k in os.environ}
    env["TERM"] = "dumb"
    env["MPLCONFIGDIR"] = str(project / ".mplconfig")
    env.update(extra or {})
    return env


# ------------------------------------------------------------ setup
def get_wheel(run_dir: Path, given: Path | None) -> dict:
    out = run_dir / "wheel"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    if given:
        shutil.copy(given, out / given.name)
        source = {"given": str(given)}
    else:
        sh(
            ["uv", "build", "--wheel", "--out-dir", str(out)],
            cwd=REPO,
            timeout=900,
        )
        source = {"built_from": str(REPO)}
    wheel = next(out.glob("*.whl"))
    commit = sh(["git", "-C", str(REPO), "rev-parse", "HEAD"]).strip()
    dirty = bool(
        sh(
            [
                "git",
                "-C",
                str(REPO),
                "status",
                "--porcelain",
                "--untracked-files=no",
            ]
        ).strip()
    )
    return {
        "path": str(wheel),
        "name": wheel.name,
        "sha256": sha256(wheel),
        "repo_commit": commit,
        "repo_dirty": dirty,
        **source,
    }


def prepare(
    case: dict, unit: Path, wheel: dict, python: str, skill: Path | None
) -> dict:
    project = unit / "project"
    shutil.rmtree(project, ignore_errors=True)
    (project / "data").mkdir(parents=True)
    for name in case["data"]:  # only this case's inputs are agent-visible
        shutil.copy(FIXTURES / "data" / name, project / "data" / name)
    sh(["uv", "venv", "--quiet", "--python", python, str(project / ".venv")])
    py = project / ".venv" / "bin" / "python"
    sh(
        [
            "uv",
            "pip",
            "install",
            "--quiet",
            "--python",
            str(py),
            wheel["path"],
            "pandas",
        ],
        timeout=900,
    )
    env = base_env(project)
    sh(
        [str(py), "-c", "import dartwork_mpl, pandas, matplotlib.pyplot"],
        cwd=project,
        env=env,
    )
    info = {
        "python": sh([str(py), "--version"]).strip(),
        "freeze": sh(["uv", "pip", "freeze", "--python", str(py)]).split(),
    }
    if case["kind"] == "edit":
        shutil.copy(FIXTURES / "base" / case["base"], project / "plot.py")
        sh([str(py), "plot.py"], cwd=project, env=env, timeout=300)
        shutil.copytree(project / "out", unit / "base_out", dirs_exist_ok=True)
    if skill:
        for dest in (".claude/skills", ".agents/skills"):
            shutil.copytree(skill, project / dest / skill.name)
    (project / ".gitignore").write_text(
        ".venv/\n.mplconfig/\nout/\n__pycache__/\n"
    )
    git = [
        "git",
        "-C",
        str(project),
        "-c",
        "user.name=eval",
        "-c",
        "user.email=eval@localhost",
    ]
    sh([*git, "init", "-q"])
    sh([*git, "add", "-A"])
    sh([*git, "commit", "-qm", "eval start"])
    return info


# ------------------------------------------------------------ hosts
def claude_cmd(prompt: str, a) -> tuple[list[str], dict]:
    user_md = Path.home() / ".claude" / "CLAUDE.md"
    excludes = [str(Path.home() / ".claude" / "**")]
    if user_md.is_symlink():
        excludes.append(str(user_md.resolve()))
    argv = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        a.claude_model,
        "--effort",
        a.claude_effort,
        "--permission-mode",
        "acceptEdits",
        "--permission-prompts",
        "none",
        "--tools",
        ",".join(TOOLS),
        "--allowedTools",
        *TOOLS,
        "--max-turns",
        str(a.max_turns),
        "--max-budget-usd",
        str(a.max_budget_usd),
        "--setting-sources",
        "project",
        "--strict-mcp-config",
        "--no-chrome",
        "--settings",
        json.dumps({"claudeMdExcludes": excludes}),
        "--no-session-persistence",
    ]
    config = {
        "model": a.claude_model,
        "effort": a.claude_effort,
        "allowed_tools": TOOLS,
        "max_turns": a.max_turns,
        "setting_sources": "project",
        "mcp": "none (strict)",
        "global_instruction_files": {
            str(user_md): "present, excluded" if user_md.exists() else "absent"
        },
        "auto_memory": "disabled",
        "sandbox": "none (Bash allowed; cwd = project)",
    }
    return argv, config


def codex_home(a) -> Path:
    return Path(
        a.codex_home or os.environ.get("CODEX_HOME") or Path.home() / ".codex"
    )


def codex_cmd(
    prompt: str, project: Path, unit: Path, a
) -> tuple[list[str], dict]:
    home = codex_home(a)
    disabled = []
    for root in (Path.home() / ".agents" / "skills", home / "skills"):
        for d in sorted(root.iterdir()) if root.is_dir() else []:
            md = d / "SKILL.md"
            if not d.name.startswith(".") and md.exists():
                disabled += sorted({str(md), os.path.realpath(md)})
    cfg = (
        "skills.config=["
        + ", ".join(f'{{path="{p}", enabled=false}}' for p in disabled)
        + "]"
    )
    argv = [
        "codex",
        "exec",
        "--json",
        "--ignore-user-config",
        "--ignore-rules",
        "--disable",
        "plugins",
        "--disable",
        "memories",
        "--disable",
        "apps",
        *(["--disable", "multi_agent"] if a.codex_no_subagents else []),
        "-c",
        cfg,
        "-c",
        'approval_policy="never"',
        "-c",
        f'model_reasoning_effort="{a.codex_effort}"',
        "-s",
        "workspace-write",
        "-C",
        str(project),
        "-m",
        a.codex_model,
        "-o",
        str(unit / "final.txt"),
        prompt,
    ]
    agents_md = home / "AGENTS.md"
    config = {
        "model": a.codex_model,
        "effort": a.codex_effort,
        "sandbox": "workspace-write (no network)",
        "user_config": "ignored",
        "rules": "ignored",
        "disabled_features": ["plugins", "memories", "apps"]
        + (["multi_agent"] if a.codex_no_subagents else []),
        "subagents": "disabled"
        if a.codex_no_subagents
        else "allowed (Codex default); counted",
        "disabled_user_skills": disabled,
        "codex_home": str(home),
        "global_instruction_files": {
            str(agents_md): (
                f"present, NOT excludable (sha256 {sha256(agents_md)[:12]}, {agents_md.stat().st_size} B)"
                if agents_md.exists()
                else "absent"
            )
        },
    }
    return argv, config


def run_host(
    argv: list[str], cwd: Path, env: dict, unit: Path, timeout: int
) -> tuple[int | None, bool, float]:
    t0 = time.monotonic()
    with (
        open(unit / "transcript.jsonl", "w") as out,
        open(unit / "stderr.txt", "w") as err,
    ):
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdout=out,
            stderr=err,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            code, timed_out = proc.wait(timeout=timeout), False
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            code = proc.returncode
    return code, timed_out, round(time.monotonic() - t0, 1)


def _jsonl(path: Path) -> list[dict]:
    def parse(raw: str) -> dict | None:
        try:
            return json.loads(raw)
        except ValueError:
            return None

    lines = (
        path.read_text(errors="replace").splitlines() if path.exists() else []
    )
    return [e for e in map(parse, lines) if isinstance(e, dict)]


def parse_claude(lines: list[dict]) -> dict:
    out: dict = {"tool_counts": {}, "tool_events": []}
    for e in lines:
        if e.get("type") == "system" and e.get("subtype") == "init":
            out.update(
                model_resolved=e.get("model"),
                skills_available=e.get("skills"),
                claude_code_version=e.get("claude_code_version"),
            )
        if e.get("type") == "assistant":
            for item in e.get("message", {}).get("content", []):
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    out["tool_counts"][item["name"]] = (
                        out["tool_counts"].get(item["name"], 0) + 1
                    )
                    out["tool_events"].append(
                        {
                            "name": item["name"],
                            "input": item.get("input"),
                            "ts": e.get("timestamp"),
                        }
                    )
        if e.get("type") == "result":
            u = e.get("usage") or {}
            tok = {
                k: u.get(k, 0)
                for k in (
                    "input_tokens",
                    "cache_creation_input_tokens",
                    "cache_read_input_tokens",
                    "output_tokens",
                )
            }
            tok["total"] = sum(tok.values())
            out.update(
                turns=e.get("num_turns"),
                tokens=tok,
                cost_usd=e.get("total_cost_usd"),
                host_error=bool(e.get("is_error")),
                result_subtype=e.get("subtype"),
                usage_raw={"usage": u, "modelUsage": e.get("modelUsage")},
                final=str(e.get("result"))[-2000:],
            )
    return out


def parse_codex(lines: list[dict]) -> dict:
    tok = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
    }
    counts: dict[str, int] = {}
    raw, failed, thread = [], False, None
    for e in lines:
        thread = thread or e.get("thread_id")
        if e.get("type") == "turn.completed":
            raw.append(e.get("usage"))
            for k in tok:
                tok[k] += (e.get("usage") or {}).get(k, 0) or 0
        failed |= e.get("type") in ("turn.failed", "error")
        if e.get("type") == "item.completed":
            kind = (e.get("item") or {}).get("type", "?")
            counts[kind] = counts.get(kind, 0) + 1
    tok["total"] = tok["input_tokens"] + tok["output_tokens"]
    tools = sum(
        v
        for k, v in counts.items()
        if k not in ("agent_message", "reasoning", "todo_list")
    )
    return {
        "tokens": tok,
        "usage_raw": raw,
        "tool_counts": counts,
        "turns": tools + 1,
        "host_error": failed,
        "thread_id": thread,
    }


def _calls(rollout: list[dict]) -> list[str]:
    return [
        (e.get("payload") or {}).get("name", "?")
        for e in rollout
        if (e.get("payload") or {}).get("type")
        in ("function_call", "custom_tool_call")
    ]


def _usage(rollout: list[dict]) -> dict:
    counts = [
        e["payload"]["info"]["total_token_usage"]
        for e in rollout
        if (e.get("payload") or {}).get("type") == "token_count"
        and (e["payload"].get("info") or {}).get("total_token_usage")
    ]
    return counts[-1] if counts else {}


def codex_rollout_turns(
    rollout: list[dict], subs: list[list[dict]] = ()
) -> dict:
    """Tool calls and tokens from the rollouts, sub-agents included.

    Code-mode ``exec`` calls (file writes, ``view_image``) and spawned
    sub-agents never reach the ``--json`` event stream, so the parent's
    events alone undercount both turns and tokens.
    """
    calls = len(_calls(rollout)) + sum(len(_calls(s)) for s in subs)
    out: dict = {
        "turns": calls + 1,
        "rollout_tool_calls": calls,
        "subagents": len(subs),
    }
    if subs:
        sub = [_usage(s) for s in subs]
        out["subagent_tokens"] = sub
        out["subagent_total"] = sum(
            (u.get("input_tokens") or 0) + (u.get("output_tokens") or 0)
            for u in sub
        )
    return out


def find_subagent_rollouts(home: Path, parent: str, since: float) -> list[Path]:
    """Rollouts whose session_meta names ``parent`` (recursively) as parent thread."""
    metas = {}
    for pattern in (
        "sessions/*/*/*/rollout-*.jsonl",
        "accounts/*/sessions/*/*/*/rollout-*.jsonl",
    ):
        for p in home.glob(pattern):
            if p.stat().st_mtime < since - 5:
                continue
            with open(p, encoding="utf-8", errors="replace") as f:
                try:
                    metas[p] = json.loads(f.readline()).get("payload") or {}
                except ValueError:
                    continue
    found, frontier = [], [parent]
    while frontier:
        t = frontier.pop()
        for p, m in metas.items():
            if m.get("parent_thread_id") == t and p not in found:
                found.append(p)
                frontier.append(m.get("id"))
    return found


def find_rollout(home: Path, thread: str | None) -> Path | None:
    if not thread:
        return None
    for pattern in (
        f"sessions/*/*/*/rollout-*{thread}.jsonl",
        f"accounts/*/sessions/*/*/*/rollout-*{thread}.jsonl",
    ):
        hits = sorted(home.glob(pattern))
        if hits:
            return hits[-1]
    return None


# ------------------------------------------------------------ evidence
def _images(obj) -> list[bytes]:
    """Every base64 image payload in a transcript object (Claude tool results, Codex rollouts)."""
    out = []
    if isinstance(obj, dict):
        if (
            obj.get("type") == "image"
            and isinstance(obj.get("source"), dict)
            and obj["source"].get("data")
        ):
            out.append(base64.b64decode(obj["source"]["data"]))
        if (
            obj.get("type") == "image"
            and isinstance(obj.get("file"), dict)
            and obj["file"].get("base64")
        ):
            out.append(base64.b64decode(obj["file"]["base64"]))
        for v in obj.values():
            out += _images(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _images(v)
    elif (
        isinstance(obj, str)
        and obj.startswith("data:image/")
        and ";base64," in obj
    ):
        out.append(base64.b64decode(obj.split(";base64,", 1)[1]))
    return out


def _same_image(viewed: bytes, final: bytes) -> str | None:
    if sha256(viewed) == sha256(final):
        return "sha256"
    try:
        v = Image.open(io.BytesIO(viewed)).convert("RGB")
        f = Image.open(io.BytesIO(final)).convert("RGB").resize(v.size)
    except OSError:
        return None
    diff = (
        np.abs(np.asarray(v, dtype=float) - np.asarray(f, dtype=float)).mean()
        / 255
    )
    return "resized-pixels" if diff <= 0.012 else None


def inspection(events: list[dict], final_png: Path) -> dict:
    """Did a tool event deliver the final PNG's pixels to the model? A text self-report never counts."""
    if not events:
        return {"observed": None, "reason": "no tool event log"}
    views = [img for e in events for img in _images(e)]
    if not final_png.exists():
        return {
            "observed": False,
            "views": len(views),
            "reason": "no final PNG",
        }
    final = final_png.read_bytes()
    methods = [m for m in (_same_image(v, final) for v in views) if m]
    return {
        "observed": bool(methods),
        "views": len(views),
        "matching_views": len(methods),
        "method": methods[0] if methods else None,
        "final_sha256": sha256(final),
    }


def skills_invoked(host: str, parsed: dict, rollout: list[dict]) -> list[str]:
    """Every skill the agent loaded (built-in ones such as /dataviz included)."""
    if host == "claude":
        return [
            str((e["input"] or {}).get("skill"))
            for e in parsed.get("tool_events", [])
            if e["name"] == "Skill"
        ]
    calls = [
        json.dumps(e)
        for e in rollout
        if (e.get("payload") or {}).get("type")
        in ("function_call", "custom_tool_call")
    ]
    return sorted(
        {m for c in calls for m in re.findall(r"skills/([\w.-]+)/SKILL\.md", c)}
    )


def skill_usage(
    name: str | None, host: str, parsed: dict, rollout: list[dict]
) -> dict | None:
    if not name:
        return None
    path_hint = f"{name}/SKILL.md"
    if host == "claude":
        events = parsed.get("tool_events", [])
        invoked = [
            e
            for e in events
            if (e["name"] == "Skill" and name in json.dumps(e["input"]))
            or path_hint in json.dumps(e["input"])
        ]
        return {
            "discovered": name in (parsed.get("skills_available") or []),
            "invoked": bool(invoked),
            "invocations": len(invoked),
        }
    calls = [
        e
        for e in rollout
        if (e.get("payload") or {}).get("type")
        in ("function_call", "custom_tool_call")
    ]
    first_call = rollout.index(calls[0]) if calls else len(rollout)
    discovered = any(name in json.dumps(e) for e in rollout[:first_call])
    invoked = [e for e in calls if path_hint in json.dumps(e)]
    return {
        "discovered": discovered if rollout else None,
        "invoked": bool(invoked),
        "invocations": len(invoked),
    }


def preserve_artifacts(project: Path, unit: Path, started_ts: float) -> dict:
    art = unit / "artifacts"
    art.mkdir(exist_ok=True)
    out = {}
    for ext in ("png", "pdf"):
        src = project / "out" / f"figure.{ext}"
        if src.exists():
            shutil.copy2(src, art / src.name)
            out[ext] = sha256(src)
            out[f"{ext}_fresh"] = src.stat().st_mtime >= started_ts - 1
        else:
            out[f"{ext}_fresh"] = False
    return out


# ------------------------------------------------------------ one unit
def one(job: tuple, run_dir: Path, a, meta: dict) -> dict:
    case, host, arm, rep = job
    unit = run_dir / host / case["id"] / f"{arm}-r{rep}"
    project = unit / "project"
    shutil.rmtree(unit, ignore_errors=True)
    unit.mkdir(parents=True)
    skill = a.skill_dir if arm == "skill" else None
    rec: dict = {
        "run_id": run_dir.name,
        "host": host,
        "case": case["id"],
        "kind": case["kind"],
        "arm": arm,
        "rep": rep,
        "held_out": case["held_out"],
        "suffix_version": SUFFIX_VERSION,
        "wheel": meta["wheel"],
        "skill": {"name": skill.name, "sha256": sha256(skill / "SKILL.md")}
        if skill
        else None,
    }
    try:
        rec.update(prepare(case, unit, meta["wheel"], a.python, skill))
        prompt = full_prompt(case)
        (unit / "prompt.txt").write_text(prompt, encoding="utf-8")
        if host == "claude":
            argv, config = claude_cmd(prompt, a)
            env = base_env(project, {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"})
        else:
            argv, config = codex_cmd(prompt, project, unit, a)
            env = base_env(
                project,
                {"CODEX_HOME": str(codex_home(a))} if a.codex_home else None,
            )
        rec.update(
            command=argv,
            host_config=config,
            model=config["model"],
            effort=config["effort"],
            host_version=meta["versions"][host],
        )
        if a.dry_run:
            write_json(unit / "run.json", {**rec, "dry_run": True})
            return rec
        started = time.time()
        rec["started"] = datetime.fromtimestamp(started).isoformat(
            timespec="seconds"
        )
        rec["started_ts"] = started
        code, timed_out, wall = run_host(argv, project, env, unit, a.timeout)
        rec.update(
            exit_code=code,
            timed_out=timed_out,
            wall_s=wall,
            ended=datetime.now().isoformat(timespec="seconds"),
        )
        rec["artifacts"] = preserve_artifacts(project, unit, started)
        lines = _jsonl(unit / "transcript.jsonl")
        rollout: list[dict] = []
        if host == "claude":
            parsed = parse_claude(lines)
            evidence = [e for e in lines if e.get("type") == "user"]
        else:
            parsed = parse_codex(lines)
            path = find_rollout(codex_home(a), parsed.get("thread_id"))
            subs: list[list[dict]] = []
            if path:
                shutil.copy(path, unit / "rollout.jsonl")
                rollout = _jsonl(unit / "rollout.jsonl")
                for k, sub in enumerate(
                    find_subagent_rollouts(
                        codex_home(a), parsed["thread_id"], started
                    ),
                    1,
                ):
                    shutil.copy(sub, unit / f"rollout-sub{k}.jsonl")
                    subs.append(_jsonl(unit / f"rollout-sub{k}.jsonl"))
                parsed.update(codex_rollout_turns(rollout, subs))
                parsed["tokens"]["total"] += parsed.get("subagent_total", 0)
            rollout = rollout + [e for s in subs for e in s]
            evidence = rollout
        rec.update({k: v for k, v in parsed.items() if k != "tool_events"})
        rec["tool_sequence"] = [
            e["name"] for e in parsed.get("tool_events", [])
        ]
        rec["inspection"] = inspection(
            evidence, unit / "artifacts" / "figure.png"
        )
        rec["skill_usage"] = skill_usage(
            skill.name if skill else None, host, parsed, rollout
        )
        rec["skills_invoked"] = skills_invoked(host, parsed, rollout)
        git = ["git", "-C", str(project)]
        rec["git_status"] = sh(
            [*git, "status", "--porcelain", "--untracked-files=all"]
        ).splitlines()[:50]
        rec["plot_diff_numstat"] = sh(
            [*git, "diff", "--numstat", "--", "plot.py"]
        ).strip()
    except Exception as exc:  # noqa: BLE001 - setup failures are recorded, never silently skipped
        rec["harness_error"] = f"{type(exc).__name__}: {exc}"
    write_json(unit / "run.json", rec)
    status = (
        "ERR " + rec["harness_error"][:120]
        if rec.get("harness_error")
        else f"exit={rec.get('exit_code')} {rec.get('wall_s')}s"
    )
    print(f"[{host}] {case['id']} {arm}-r{rep}: {status}", flush=True)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--host", action="append", choices=["claude", "codex"])
    ap.add_argument(
        "--case", action="append", help="case id (repeatable); default all 40"
    )
    ap.add_argument("--run-id")
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument(
        "--wheel",
        type=Path,
        help="evaluate this prebuilt wheel (default: build from this checkout)",
    )
    arm = ap.add_mutually_exclusive_group()
    arm.add_argument(
        "--with-skill", type=Path, help="skill folder: run only the 'skill' arm"
    )
    arm.add_argument(
        "--ab-skill",
        type=Path,
        help="skill folder: run both arms (noskill, skill) on the same wheel",
    )
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument(
        "--seed",
        type=int,
        help="shuffle seed for unit order (default: random, recorded)",
    )
    ap.add_argument(
        "--jobs", type=int, default=1, help="parallel units (max 7)"
    )
    ap.add_argument("--python", default="3.12")
    ap.add_argument("--timeout", type=int, default=300, help="seconds per unit")
    ap.add_argument("--max-turns", type=int, default=20)
    ap.add_argument("--max-budget-usd", type=float, default=5.0)
    ap.add_argument("--claude-model", default="sonnet")
    ap.add_argument("--claude-effort", default="high")
    ap.add_argument("--codex-model", default="gpt-6-astra")
    ap.add_argument("--codex-effort", default="medium")
    ap.add_argument(
        "--codex-no-subagents",
        action="store_true",
        help="disable Codex multi_agent (sub-agents are otherwise allowed and counted)",
    )
    ap.add_argument(
        "--codex-home",
        help="dedicated CODEX_HOME (removes the global AGENTS.md leak)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="prepare projects and record commands only",
    )
    a = ap.parse_args()
    if a.jobs > 7:
        ap.error("--jobs is capped at 7")
    a.skill_dir = a.with_skill or a.ab_skill
    if a.skill_dir and not (a.skill_dir / "SKILL.md").exists():
        ap.error(f"{a.skill_dir} has no SKILL.md")
    arms = (
        ["noskill", "skill"]
        if a.ab_skill
        else ["skill"]
        if a.with_skill
        else ["noskill"]
    )
    hosts = a.host or ["claude", "codex"]
    cases = load_cases(a.case)
    seed = (
        a.seed if a.seed is not None else random.SystemRandom().randrange(2**31)
    )
    jobs = [
        (c, h, arm_, r)
        for c in cases
        for h in hosts
        for arm_ in arms
        for r in range(1, a.reps + 1)
    ]
    random.Random(seed).shuffle(jobs)
    commit = sh(
        ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"]
    ).strip()
    run_id = (
        a.run_id or f"{datetime.now():%Y%m%d-%H%M%S}-{commit}-{'-'.join(arms)}"
    )
    run_dir = a.root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    # An existing run keeps its wheel: later invocations (other hosts, more
    # reps) are appended so every unit of one run evaluates the same bytes.
    meta = read_json(run_dir / "run_meta.json") or {
        "run_id": run_id,
        "invocations": [],
    }
    if "wheel" not in meta or a.wheel:
        meta["wheel"] = get_wheel(run_dir, a.wheel)
    elif sha256(Path(meta["wheel"]["path"])) != meta["wheel"]["sha256"]:
        raise SystemExit(
            f"{meta['wheel']['path']} changed since the run started"
        )
    inv = {
        "argv": sys.argv,
        "args": {k: str(v) for k, v in vars(a).items()},
        "hosts": hosts,
        "arms": arms,
        "reps": a.reps,
        "seed": seed,
        "cases": [c["id"] for c in cases],
        "order": [f"{h}/{c['id']}/{arm_}-r{r}" for c, h, arm_, r in jobs],
        "versions": {h: sh([h, "--version"]).strip() for h in hosts},
        "suffix_version": SUFFIX_VERSION,
        "started": datetime.now().isoformat(timespec="seconds"),
    }
    meta["invocations"].append(inv)
    write_json(run_dir / "run_meta.json", meta)
    print(
        f"run {run_id}: {len(jobs)} units ({len(cases)} cases x {hosts} x {arms} x {a.reps} reps), seed {seed}",
        flush=True,
    )
    unit_meta = {"wheel": meta["wheel"], "versions": inv["versions"]}
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        recs = list(pool.map(lambda j: one(j, run_dir, a, unit_meta), jobs))
    inv["ended"] = datetime.now().isoformat(timespec="seconds")
    inv["harness_errors"] = [
        f"{r['host']}/{r['case']}/{r['arm']}-r{r['rep']}: {r['harness_error']}"
        for r in recs
        if r.get("harness_error")
    ]
    write_json(run_dir / "run_meta.json", meta)
    print(
        f"done; harness errors: {len(inv['harness_errors'])}. Next: uv run python evals/agentic/score.py {run_dir}"
    )
    return 1 if inv["harness_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
