"""Run eval cases headless in Claude Code and/or Codex.

    uv run python evals/agentic/run.py --host claude --case g01-line-gdp
    uv run python evals/agentic/run.py --jobs 4                         # 40 cases x both hosts
    uv run python evals/agentic/run.py --wheel W.whl --ab-skill SKILL_DIR --reps 2 --jobs 4

Two trees per run:

* records (``ROOT/<run-id>/``): ``manifest.json`` (config, budgets, wheel and
  every planned unit; append-only), ``run_meta.json`` and one directory per
  unit ``<host>/<case>/<arm>-r<k>/`` with ``run.json``, transcripts,
  ``artifacts/`` and later ``score.json``;
* work (``WORK_ROOT/<opaque-token>/``): the agent's project only (case CSVs,
  own ``.venv`` with the wheel + pandas, git, and for edits the rendered base
  ``plot.py``). Nothing above it names the eval, the records or the repo.

Hosts run with user-level context isolated, repo paths stripped from the
environment and per-host budgets from the manifest (identical across arms).
After a run, transcripts are scanned for any access to grading files
(``contamination``), and ``inspection`` is bound to the final PNG. Score with
``score.py``.
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
import secrets
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from itertools import pairwise
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
DEFAULT_WORK = Path.home() / "scratch" / "dartwork-mpl-evals-work"
MIN_VIEW_PX = 400  # long side; smaller views are not a usable inspection
VIEW_TOL = 3 / 255  # max abs pixel error after the host's own resize
HOST_FILTERS = (
    Image.LANCZOS,
    Image.BILINEAR,
)  # measured: Claude Read, Codex view_image


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


def repo_roots() -> list[Path]:
    """This checkout and the main checkout that owns its git directory."""
    roots = {REPO.resolve()}
    try:
        common = Path(
            sh(
                [
                    "git",
                    "-C",
                    str(REPO),
                    "rev-parse",
                    "--path-format=absolute",
                    "--git-common-dir",
                ]
            ).strip()
        )
        roots.add(common.parent.resolve())
    except RuntimeError:
        pass
    return sorted(roots)


def base_env(
    project: Path, extra: dict | None = None, hidden: list[Path] = ()
) -> dict:
    """Allowlisted environment; PATH entries inside the repo or records are dropped."""
    env = {k: os.environ[k] for k in ENV_KEEP if k in os.environ}
    banned = [str(p) for p in [*repo_roots(), *hidden]]
    env["PATH"] = os.pathsep.join(
        p
        for p in env.get("PATH", "").split(os.pathsep)
        if p and not any(p.startswith(b) for b in banned)
    )
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
    else:
        sh(
            ["uv", "build", "--wheel", "--out-dir", str(out)],
            cwd=REPO,
            timeout=900,
        )
    wheel = next(out.glob("*.whl"))
    return {
        "path": str(wheel),
        "name": wheel.name,
        "sha256": sha256(wheel),
        "given": bool(given),
    }


def prepare(
    case: dict,
    project: Path,
    unit: Path,
    wheel: dict,
    python: str,
    skill: Path | None,
) -> dict:
    """Agent-visible project: only the case inputs, its own venv and (edits) the base figure."""
    project.mkdir(parents=True)
    (project / "data").mkdir()
    for name in case["data"]:
        shutil.copy(FIXTURES / "data" / name, project / "data" / name)
    sh(["uv", "venv", "--quiet", "--python", python, str(project / ".venv")])
    py = project / ".venv" / "bin" / "python"
    local = (
        project / ".wheel" / wheel["name"]
    )  # install from inside the project, then delete
    local.parent.mkdir()
    shutil.copy(wheel["path"], local)
    sh(
        [
            "uv",
            "pip",
            "install",
            "--quiet",
            "--python",
            str(py),
            str(local),
            "pandas",
        ],
        timeout=900,
    )
    shutil.rmtree(local.parent)
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
    sh([*git, "commit", "-qm", "start"])
    return info


# ------------------------------------------------------------ hosts
def claude_cmd(prompt: str, cfg: dict) -> list[str]:
    user_md = Path.home() / ".claude" / "CLAUDE.md"
    excludes = [str(Path.home() / ".claude" / "**")] + (
        [str(user_md.resolve())] if user_md.is_symlink() else []
    )
    b = cfg["budgets"]["claude"]
    return [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        cfg["models"]["claude"],
        "--effort",
        cfg["efforts"]["claude"],
        "--permission-mode",
        "acceptEdits",
        "--permission-prompts",
        "none",
        "--tools",
        ",".join(TOOLS),
        "--allowedTools",
        *TOOLS,
        "--max-turns",
        str(b["max_turns"]),
        "--max-budget-usd",
        str(b["max_budget_usd"]),
        "--setting-sources",
        "project",
        "--strict-mcp-config",
        "--no-chrome",
        "--settings",
        json.dumps({"claudeMdExcludes": excludes}),
        "--no-session-persistence",
    ]


def codex_home(a) -> Path:
    return Path(
        a.codex_home or os.environ.get("CODEX_HOME") or Path.home() / ".codex"
    )


def user_skill_files(home: Path) -> list[str]:
    out = []
    for root in (Path.home() / ".agents" / "skills", home / "skills"):
        for d in sorted(root.iterdir()) if root.is_dir() else []:
            md = d / "SKILL.md"
            if not d.name.startswith(".") and md.exists():
                out += sorted({str(md), os.path.realpath(md)})
    return out


def codex_cmd(
    prompt: str, project: Path, unit: Path, cfg: dict, home: Path
) -> list[str]:
    off = (
        "skills.config=["
        + ", ".join(
            f'{{path="{p}", enabled=false}}' for p in user_skill_files(home)
        )
        + "]"
    )
    sub = (
        []
        if cfg["budgets"]["codex"]["subagents"]
        else ["--disable", "multi_agent"]
    )
    return [
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
        *sub,
        "-c",
        off,
        "-c",
        'approval_policy="never"',
        "-c",
        f'model_reasoning_effort="{cfg["efforts"]["codex"]}"',
        "-s",
        "workspace-write",
        "-C",
        str(project),
        "-m",
        cfg["models"]["codex"],
        "-o",
        str(unit / "final.txt"),
        prompt,
    ]


def host_context(host: str, home: Path) -> dict:
    """Global instruction files present on this machine and how the run treats them."""
    if host == "claude":
        md = Path.home() / ".claude" / "CLAUDE.md"
        return {str(md): "present, excluded" if md.exists() else "absent"}
    md = home / "AGENTS.md"
    return {
        str(md): (
            f"present, NOT excludable (sha256 {sha256(md)[:12]}, {md.stat().st_size} B)"
            if md.exists()
            else "absent"
        ),
        "user_skills_disabled": len(user_skill_files(home)),
    }


def sandbox_wrap(argv: list[str], project: Path, hide: list[Path]) -> list[str]:
    """Optional bwrap: mount empty tmpfs over the repo, records and other projects."""
    args = ["bwrap", "--dev-bind", "/", "/"]
    for p in hide:
        args += ["--tmpfs", str(p)]
    return [*args, "--bind", str(project), str(project), "--", *argv]


# ------------------------------------------------------------ rollouts / monitor
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


def _session_dirs(home: Path) -> list[Path]:
    days = {date.today() + timedelta(days=k) for k in (-1, 0, 1)}
    roots = [home / "sessions", *home.glob("accounts/*/sessions")]
    return [
        r / f"{d:%Y/%m/%d}"
        for r in roots
        for d in days
        if (r / f"{d:%Y/%m/%d}").is_dir()
    ]


def _meta(path: Path) -> dict:
    with open(path, encoding="utf-8", errors="replace") as f:
        try:
            return json.loads(f.readline()).get("payload") or {}
        except ValueError:
            return {}


def codex_rollouts(
    home: Path, thread: str | None
) -> tuple[Path | None, list[Path]]:
    """The parent rollout and every (transitive) sub-agent rollout of ``thread``."""
    if not thread:
        return None, []
    files = [p for d in _session_dirs(home) for p in d.glob("rollout-*.jsonl")]
    parent = next(
        (p for p in files if p.name.endswith(f"{thread}.jsonl")), None
    )
    metas = {p: _meta(p) for p in files}
    found, frontier = [], [thread]
    while frontier:
        t = frontier.pop()
        for p, m in metas.items():
            if m.get("parent_thread_id") == t and p not in found:
                found.append(p)
                frontier.append(m.get("id"))
    return parent, found


def _usage(rollout: list[dict]) -> dict:
    counts = [
        e["payload"]["info"]["total_token_usage"]
        for e in rollout
        if (e.get("payload") or {}).get("type") == "token_count"
        and (e["payload"].get("info") or {}).get("total_token_usage")
    ]
    return counts[-1] if counts else {}


def _total(u: dict) -> int:
    return int((u.get("input_tokens") or 0) + (u.get("output_tokens") or 0))


class CodexMonitor:
    """Kill the run when parent + sub-agent tokens exceed the manifest budget."""

    def __init__(self, home: Path, transcript: Path, budget: int):
        self.home, self.transcript, self.budget, self.thread, self.last = (
            home,
            transcript,
            budget,
            None,
            0,
        )

    def __call__(self) -> bool:
        if not self.thread:
            first = _jsonl(self.transcript)[:1]
            self.thread = first[0].get("thread_id") if first else None
        parent, subs = codex_rollouts(self.home, self.thread)
        self.last = sum(_total(_usage(_jsonl(p))) for p in [parent, *subs] if p)
        return self.last > self.budget


def run_host(
    argv, cwd, env, unit: Path, timeout: int, monitor=None
) -> tuple[int | None, str, float]:
    """Run the host; returns (exit code, termination reason, wall seconds)."""
    t0 = time.monotonic()
    reason = "exited"
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
        while proc.poll() is None:
            time.sleep(2)
            if time.monotonic() - t0 > timeout:
                reason = "timeout"
            elif monitor is not None and monitor():
                reason = "token_budget"
            if reason != "exited":
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                break
    return proc.returncode, reason, round(time.monotonic() - t0, 1)


# ------------------------------------------------------------ parsing
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
            sub = e.get("subtype")
            out.update(
                turns=e.get("num_turns"),
                tokens=tok,
                cost_usd=e.get("total_cost_usd"),
                host_error=bool(e.get("is_error")),
                result_subtype=sub,
                usage_raw={"usage": u, "modelUsage": e.get("modelUsage")},
                final=str(e.get("result"))[-2000:],
                models_used=sorted((e.get("modelUsage") or {}).keys()),
            )
            out["stop"] = {
                "success": "completed",
                "error_max_turns": "turn_limit",
                "error_max_budget_usd": "budget_usd",
            }.get(sub, "error" if e.get("is_error") else sub)
    out.setdefault("stop", "no_result")
    return out


def parse_codex(
    lines: list[dict], rollout: list[dict], subs: list[list[dict]]
) -> dict:
    """Turns and tokens from the rollouts (code-mode exec, view_image and sub-agents
    never reach the ``--json`` stream); the stream supplies thread id and failures."""
    failed = any(e.get("type") in ("turn.failed", "error") for e in lines)
    thread = next(
        (e.get("thread_id") for e in lines if e.get("thread_id")), None
    )
    calls = [
        e
        for r in [rollout, *subs]
        for e in r
        if (e.get("payload") or {}).get("type")
        in ("function_call", "custom_tool_call")
    ]
    parent_u = _usage(rollout) or {}
    sub_u = [_usage(s) for s in subs]
    raw = [e.get("usage") for e in lines if e.get("type") == "turn.completed"]
    tok = {
        k: (parent_u.get(k) or 0) + sum((u.get(k) or 0) for u in sub_u)
        for k in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
        )
    }
    tok["total"] = tok["input_tokens"] + tok["output_tokens"]
    if (
        not rollout
    ):  # no rollout: fall back to the stream (undercounts sub-agents)
        for u in raw:
            for k in (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "reasoning_output_tokens",
            ):
                tok[k] += (u or {}).get(k, 0) or 0
        tok["total"] = tok["input_tokens"] + tok["output_tokens"]
    models = sorted(
        {
            (e.get("payload") or {}).get("model")
            for r in [rollout, *subs]
            for e in r
            if e.get("type") == "turn_context"
            and (e.get("payload") or {}).get("model")
        }
    )
    return {
        "tokens": tok if (rollout or raw) else None,
        "usage_raw": {"stream": raw, "parent": parent_u, "subagents": sub_u},
        "turns": len(calls) + 1 if rollout else None,
        "tool_calls": len(calls),
        "subagents": len(subs),
        "models_used": models,
        "host_error": failed,
        "thread_id": thread,
    }


# ------------------------------------------------------------ evidence
def _ts(value) -> float | None:
    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        ).timestamp()
    except ValueError:
        return None


def _images(obj) -> list[bytes]:
    out = []
    if isinstance(obj, dict):
        src = obj.get("source")
        if (
            obj.get("type") == "image"
            and isinstance(src, dict)
            and src.get("data")
        ):
            out.append(base64.b64decode(src["data"]))
        for k, v in obj.items():
            if k != "tool_use_result":  # duplicate of the message content
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


def view_events(
    host: str, lines: list[dict], rollouts: list[list[dict]]
) -> list[tuple[float | None, bytes]]:
    """(timestamp, image bytes) for every successful image tool result, parent and children merged."""
    out = []
    if host == "claude":
        for e in lines:
            if e.get("type") != "user":
                continue
            for item in (e.get("message") or {}).get("content") or []:
                if (
                    isinstance(item, dict)
                    and item.get("type") == "tool_result"
                    and not item.get("is_error")
                ):
                    out += [
                        (_ts(e.get("timestamp")), img)
                        for img in _images(item.get("content"))
                    ]
    else:
        for r in rollouts:
            for e in r:
                p = e.get("payload") or {}
                if p.get("type") in (
                    "custom_tool_call_output",
                    "function_call_output",
                ):
                    out += [
                        (_ts(e.get("timestamp")), img)
                        for img in _images(p.get("output"))
                    ]
    return sorted(out, key=lambda v: v[0] or 0)


def same_image(viewed: bytes, final: bytes) -> str | None:
    """sha256 identity, or equality after the host's own downscale (measured filters)."""
    if sha256(viewed) == sha256(final):
        return "sha256"
    try:
        v = Image.open(io.BytesIO(viewed)).convert("RGB")
        f = Image.open(io.BytesIO(final)).convert("RGB")
    except OSError:
        return None
    if (
        max(v.size) < MIN_VIEW_PX
        or v.size[0] > f.size[0]
        or v.size[1] > f.size[1]
    ):
        return None
    va = np.asarray(v, dtype=float) / 255
    for flt in HOST_FILTERS:
        r = np.asarray(f.resize(v.size, flt), dtype=float) / 255
        if float(np.abs(r - va).max()) <= VIEW_TOL:
            return "host-resize"
    return None


def inspection(
    views: list[tuple[float | None, bytes]], final_png: Path, final_ts: float
) -> dict:
    """Observed only if a view after the last write to plot.py/outputs shows the final pixels."""
    if not final_png.exists():
        return {
            "observed": False,
            "views": len(views),
            "reason": "no final PNG",
        }
    final = final_png.read_bytes()
    late = [img for ts, img in views if ts is not None and ts >= final_ts]
    methods = [m for m in (same_image(img, final) for img in late) if m]
    return {
        "observed": bool(methods),
        "views": len(views),
        "views_after_final_write": len(late),
        "matching_views": len(methods),
        "method": methods[0] if methods else None,
        "final_sha256": sha256(final),
        "final_write_ts": final_ts,
    }


def _tool_text(
    host: str, lines: list[dict], rollouts: list[list[dict]]
) -> list[str]:
    """Text of every tool call and tool output (not instructions or prompts)."""
    out = []
    if host == "claude":
        out += [
            json.dumps(
                item.get("input") or item.get("content"), ensure_ascii=False
            )
            for e in lines
            for item in (e.get("message") or {}).get("content") or []
            if isinstance(item, dict)
            and item.get("type") in ("tool_use", "tool_result")
        ]
    else:
        out += [
            json.dumps(e.get("item"), ensure_ascii=False)
            for e in lines
            if e.get("type", "").startswith("item.")
        ]
        for r in rollouts:
            for e in r:
                p = e.get("payload") or {}
                if p.get("type") in (
                    "function_call",
                    "custom_tool_call",
                    "custom_tool_call_output",
                    "function_call_output",
                ):
                    out.append(json.dumps(p, ensure_ascii=False))
    return out


PATH_TOKEN = re.compile(r"[\w.@+~-]*/[\w.@+~/-]*")
CONTAMINATION_RULE = "resolved-path-v2"


def _resolved_paths(text: str, project: Path) -> set[str]:
    """Paths named in one tool call or output, resolved against the project.

    Absolute and ``~`` paths are taken as written; relative paths matter
    only when they climb (``..``) and are resolved from the project, which
    is every agent's working directory. Symlinks are resolved.
    """
    out = set()
    for tok in PATH_TOKEN.findall(text):
        if tok.endswith(".") and not tok.endswith(("..", "/.")):
            tok = tok[:-1]  # sentence full stop
        if tok.startswith("~"):
            tok = os.path.expanduser(tok)
        elif not tok.startswith("/"):
            if ".." not in tok.split("/"):
                continue
            tok = os.path.join(project, tok)
        if tok.startswith("//"):
            continue  # URL remainder (https://...)
        out.add(os.path.realpath(os.path.normpath(tok)))
    return out


def _inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def contamination(
    texts: list[str], roots: list, work_root: Path, project: Path
) -> dict:
    """An access whose resolved path lies in a grading root marks the run contaminated.

    Grading roots are the repo checkouts (cases, references, scorer), the
    records tree and every other project under ``work_root``. Each path a
    tool call or its output names is resolved against the project (see
    ``_resolved_paths``); a bare ``../`` that stays in the project (``.venv``
    internals) or reaches only ``work_root`` itself is not an access to
    grading files. Only absolute ``roots`` count; name fragments such as
    ``evals/agentic`` are no longer matched as substrings.
    """
    grading = sorted(
        {os.path.realpath(str(r)) for r in roots if os.path.isabs(str(r))}
    )
    work = os.path.realpath(str(work_root))
    own = os.path.realpath(str(project))
    hits = set()
    for t in texts:
        for path in _resolved_paths(t, project):
            if _inside(path, own):
                continue
            if any(_inside(path, r) for r in grading) or (
                path != work and _inside(path, work)  # another agent's project
            ):
                hits.add(path)
    hits = sorted(hits)
    return {
        "contaminated": bool(hits),
        "hits": hits[:20],
        "rule": CONTAMINATION_RULE,
    }


def grading_roots(rec: dict, unit: Path) -> list[Path]:
    """Grading roots of a recorded unit: what the sandbox hid, else the repo and records."""
    cmd = rec.get("command") or []
    hidden = [Path(b) for a, b in pairwise(cmd) if a == "--tmpfs"]
    work = Path(rec["project"]).parent if rec.get("project") else None
    return sorted({*hidden, *repo_roots(), unit.parents[3].resolve()} - {work})


def recheck_contamination(rec: dict, unit: Path) -> dict | None:
    """Recompute contamination of a recorded unit from its stored transcript and rollouts."""
    if not rec.get("project") or not (unit / "transcript.jsonl").exists():
        return None
    lines = _jsonl(unit / "transcript.jsonl")
    rolls = [_jsonl(p) for p in sorted(unit.glob("rollout*.jsonl"))]
    project = Path(rec["project"])
    return contamination(
        _tool_text(rec["host"], lines, rolls),
        grading_roots(rec, unit),
        project.parent,
        project,
    )


def skill_usage(
    name: str | None, host: str, parsed: dict, rollout: list[dict]
) -> dict | None:
    if not name:
        return None
    hint = f"{name}/SKILL.md"
    if host == "claude":
        ev = [
            e
            for e in parsed.get("tool_events", [])
            if (e["name"] == "Skill" and name in json.dumps(e["input"]))
            or hint in json.dumps(e["input"])
        ]
        return {
            "discovered": name in (parsed.get("skills_available") or []),
            "invoked": bool(ev),
            "invocations": len(ev),
        }
    calls = [
        e
        for e in rollout
        if (e.get("payload") or {}).get("type")
        in ("function_call", "custom_tool_call")
    ]
    first = rollout.index(calls[0]) if calls else len(rollout)
    ev = [e for e in calls if hint in json.dumps(e)]
    return {
        "discovered": any(name in json.dumps(e) for e in rollout[:first])
        if rollout
        else None,
        "invoked": bool(ev),
        "invocations": len(ev),
    }


def skills_invoked(
    host: str, parsed: dict, rollouts: list[list[dict]]
) -> list[str]:
    if host == "claude":
        return [
            str((e["input"] or {}).get("skill"))
            for e in parsed.get("tool_events", [])
            if e["name"] == "Skill"
        ]
    calls = [
        json.dumps(e)
        for r in rollouts
        for e in r
        if (e.get("payload") or {}).get("type")
        in ("function_call", "custom_tool_call")
    ]
    return sorted(
        {m for c in calls for m in re.findall(r"skills/([\w.-]+)/SKILL\.md", c)}
    )


def preserve_artifacts(project: Path, unit: Path, started_ts: float) -> dict:
    """Copy the outputs as the agent left them (mtime kept) and pin the final source."""
    art = unit / "artifacts"
    art.mkdir(exist_ok=True)
    out: dict = {}
    for ext in ("png", "pdf"):
        src = project / "out" / f"figure.{ext}"
        if src.exists():
            shutil.copy2(src, art / src.name)
            out[ext] = sha256(src)
            out[f"{ext}_mtime"] = src.stat().st_mtime
            out[f"{ext}_fresh"] = src.stat().st_mtime >= started_ts - 1
        else:
            out[f"{ext}_fresh"] = False
    plot = project / "plot.py"
    if plot.exists():
        out["plot_sha256"], out["plot_mtime"] = (
            sha256(plot),
            plot.stat().st_mtime,
        )
    return out


# ------------------------------------------------------------ one unit
def unit_id(host: str, case: str, arm: str, rep: int) -> str:
    return f"{host}/{case}/{arm}-r{rep}"


def one(job: tuple, run_dir: Path, a, cfg: dict, meta: dict) -> dict:
    case, host, arm, rep = job
    uid = unit_id(host, case["id"], arm, rep)
    unit = run_dir / uid
    if (unit / "run.json").exists():
        raise SystemExit(
            f"{uid} already has a record; completed units are immutable"
        )
    unit.mkdir(parents=True)
    project = a.work_root / secrets.token_hex(8)
    skill = a.skill_dir if arm == "skill" else None
    home = codex_home(a)
    rec: dict = {
        "run_id": run_dir.name,
        "unit_id": uid,
        "host": host,
        "case": case["id"],
        "kind": case["kind"],
        "arm": arm,
        "rep": rep,
        "held_out": case["held_out"],
        "suffix_version": SUFFIX_VERSION,
        "wheel": {k: meta["wheel"][k] for k in ("name", "sha256")},
        "project": str(project),
        "skill": {"name": skill.name, "sha256": sha256(skill / "SKILL.md")}
        if skill
        else None,
        "model": cfg["models"][host],
        "effort": cfg["efforts"][host],
        "budget": cfg["budgets"][host],
        "host_version": meta["versions"][host],
        "host_context": host_context(host, home),
    }
    hide = [*repo_roots(), run_dir.parent.resolve(), a.work_root.resolve()]
    try:
        rec.update(
            prepare(case, project, unit, meta["wheel"], cfg["python"], skill)
        )
        prompt = full_prompt(case)
        (unit / "prompt.txt").write_text(prompt, encoding="utf-8")
        if host == "claude":
            argv = claude_cmd(prompt, cfg)
            env = base_env(
                project, {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}, hide
            )
            monitor = None
        else:
            argv = codex_cmd(prompt, project, unit, cfg, home)
            env = base_env(
                project,
                {"CODEX_HOME": str(home)} if a.codex_home else None,
                hide,
            )
            monitor = CodexMonitor(
                home,
                unit / "transcript.jsonl",
                cfg["budgets"]["codex"]["token_budget"],
            )
        if cfg["hide_grading"]:
            argv = sandbox_wrap(argv, project, hide)
        rec["command"] = argv
        if a.dry_run:
            write_json(unit / "run.json", {**rec, "dry_run": True})
            return rec
        started = time.time()
        rec["started"], rec["started_ts"] = (
            datetime.fromtimestamp(started).isoformat(timespec="seconds"),
            started,
        )
        code, reason, wall = run_host(
            argv, project, env, unit, cfg["budgets"][host]["timeout_s"], monitor
        )
        rec.update(
            exit_code=code,
            timed_out=reason == "timeout",
            wall_s=wall,
            ended=datetime.now().isoformat(timespec="seconds"),
        )
        rec["artifacts"] = preserve_artifacts(project, unit, started)
        lines = _jsonl(unit / "transcript.jsonl")
        rollout, subs = [], []
        if host == "claude":
            parsed = parse_claude(lines)
        else:
            thread = next(
                (e.get("thread_id") for e in lines if e.get("thread_id")), None
            )
            parent, sub_paths = codex_rollouts(home, thread)
            if parent:
                shutil.copy(parent, unit / "rollout.jsonl")
                rollout = _jsonl(unit / "rollout.jsonl")
            for k, p in enumerate(sub_paths, 1):
                shutil.copy(p, unit / f"rollout-sub{k}.jsonl")
                subs.append(_jsonl(unit / f"rollout-sub{k}.jsonl"))
            parsed = parse_codex(lines, rollout, subs)
            parsed["stop"] = (
                "completed"
                if code == 0 and not parsed["host_error"]
                else "error"
            )
        rec["termination"] = (
            reason if reason != "exited" else parsed.get("stop")
        )
        rec.update(
            {
                k: v
                for k, v in parsed.items()
                if k not in ("tool_events", "stop")
            }
        )
        rec["tool_sequence"] = [
            e["name"] for e in parsed.get("tool_events", [])
        ]
        final_ts = max(
            [
                p.stat().st_mtime
                for p in (
                    project / "plot.py",
                    project / "out" / "figure.png",
                    project / "out" / "figure.pdf",
                )
                if p.exists()
            ]
            or [started]
        )
        rec["inspection"] = inspection(
            view_events(host, lines, [rollout, *subs]),
            unit / "artifacts" / "figure.png",
            final_ts,
        )
        rec["contamination"] = contamination(
            _tool_text(host, lines, [rollout, *subs]),
            hide[:-1],
            a.work_root.resolve(),
            project,
        )
        rec["skill_usage"] = skill_usage(
            skill.name if skill else None,
            host,
            parsed,
            rollout + [e for s in subs for e in s],
        )
        rec["skills_invoked"] = skills_invoked(host, parsed, [rollout, *subs])
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
        else (
            f"exit={rec.get('exit_code')} {rec.get('termination')} {rec.get('wall_s')}s"
        )
    )
    print(f"[{uid}] {status}", flush=True)
    return rec


# ------------------------------------------------------------ manifest
def config_from(a) -> dict:
    return {
        "models": {"claude": a.claude_model, "codex": a.codex_model},
        "efforts": {"claude": a.claude_effort, "codex": a.codex_effort},
        "budgets": {
            "claude": {
                "max_turns": a.max_turns,
                "max_budget_usd": a.max_budget_usd,
                "timeout_s": a.timeout,
            },
            "codex": {
                "timeout_s": a.timeout,
                "token_budget": a.codex_token_budget,
                "subagents": not a.codex_no_subagents,
            },
        },
        "python": a.python,
        "suffix_version": SUFFIX_VERSION,
        "hide_grading": a.hide_grading,
        "codex_home": str(codex_home(a)) if a.codex_home else None,
    }


def assert_same_run(
    manifest: dict, cfg: dict, run_wheel: Path, given: Path | None
) -> None:
    """Extending a run must keep the exact wheel bytes and the exact config (budgets, models...)."""
    want = manifest["wheel"]["sha256"]
    if sha256(run_wheel) != want or (given and sha256(given) != want):
        raise SystemExit(
            "wheel differs from the run's manifest; start a new run id"
        )
    if cfg != manifest["config"]:
        raise SystemExit(
            f"config differs from the run's manifest; start a new run id\n{cfg}\n!=\n{manifest['config']}"
        )


def plan_jobs(
    manifest: dict,
    cases: list[dict],
    hosts: list[str],
    arms: list[str],
    reps: int,
    seed: int,
) -> list:
    """New repetitions get new ids after any already planned for the same (host, case, arm)."""
    planned = [u for p in manifest["plans"] for u in p["units"]]
    jobs = []
    for c in cases:
        for h in hosts:
            for arm in arms:
                prefix = f"{h}/{c['id']}/{arm}-r"
                start = max(
                    [
                        int(u[len(prefix) :])
                        for u in planned
                        if u.startswith(prefix)
                    ]
                    or [0]
                )
                jobs += [(c, h, arm, start + r) for r in range(1, reps + 1)]
    random.Random(seed).shuffle(jobs)
    return jobs


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
    ap.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT, help="records tree"
    )
    ap.add_argument(
        "--work-root",
        type=Path,
        default=DEFAULT_WORK,
        help="agent projects tree (kept separate)",
    )
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
    ap.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="wall-clock seconds per unit (both hosts)",
    )
    ap.add_argument(
        "--max-turns", type=int, default=20, help="Claude --max-turns"
    )
    ap.add_argument(
        "--max-budget-usd",
        type=float,
        default=5.0,
        help="Claude --max-budget-usd (list cost)",
    )
    ap.add_argument(
        "--codex-token-budget",
        type=int,
        default=1_500_000,
        help="Codex input+output tokens incl. sub-agents; monitored, killed on overrun",
    )
    ap.add_argument(
        "--codex-no-subagents",
        action="store_true",
        help="disable Codex multi_agent",
    )
    ap.add_argument("--claude-model", default="sonnet")
    ap.add_argument("--claude-effort", default="high")
    ap.add_argument("--codex-model", default="gpt-6-astra")
    ap.add_argument("--codex-effort", default="medium")
    ap.add_argument(
        "--codex-home",
        help="dedicated CODEX_HOME (removes the global AGENTS.md leak)",
    )
    ap.add_argument(
        "--hide-grading",
        action="store_true",
        help="wrap hosts in bwrap with tmpfs over the repo, records and other projects",
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
    if a.hide_grading and not shutil.which("bwrap"):
        ap.error("--hide-grading needs bwrap")
    a.work_root.mkdir(parents=True, exist_ok=True)
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
    commit = sh(
        ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"]
    ).strip()
    run_id = (
        a.run_id or f"{datetime.now():%Y%m%d-%H%M%S}-{commit}-{'-'.join(arms)}"
    )
    run_dir = a.root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    cfg = config_from(a)
    manifest = read_json(run_dir / "manifest.json")
    if manifest is None:
        wheel = get_wheel(run_dir, a.wheel)
        manifest = {
            "run_id": run_id,
            "created": datetime.now().isoformat(timespec="seconds"),
            "wheel": {k: wheel[k] for k in ("name", "sha256", "given")},
            "harness_commit": commit,
            "config": cfg,
            "plans": [],
        }
    else:  # extending: same wheel bytes and identical config, or refuse
        wheel = {
            "path": str(next((run_dir / "wheel").glob("*.whl"))),
            **manifest["wheel"],
        }
        assert_same_run(manifest, cfg, Path(wheel["path"]), a.wheel)
    jobs = plan_jobs(manifest, cases, hosts, arms, a.reps, seed)
    manifest["plans"].append(
        {
            "created": datetime.now().isoformat(timespec="seconds"),
            "seed": seed,
            "argv": sys.argv,
            "units": [unit_id(h, c["id"], arm_, r) for c, h, arm_, r in jobs],
        }
    )
    write_json(run_dir / "manifest.json", manifest)
    meta = {
        "wheel": wheel,
        "versions": {h: sh([h, "--version"]).strip() for h in hosts},
    }
    log = read_json(run_dir / "run_meta.json") or {
        "run_id": run_id,
        "invocations": [],
    }
    inv = {
        "argv": sys.argv,
        "seed": seed,
        "versions": meta["versions"],
        "started": datetime.now().isoformat(timespec="seconds"),
    }
    log["invocations"].append(inv)
    write_json(run_dir / "run_meta.json", log)
    print(
        f"run {run_id}: {len(jobs)} units ({len(cases)} cases x {hosts} x {arms} x {a.reps} reps), seed {seed}",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        recs = list(pool.map(lambda j: one(j, run_dir, a, cfg, meta), jobs))
    inv["ended"] = datetime.now().isoformat(timespec="seconds")
    inv["harness_errors"] = [
        f"{r['unit_id']}: {r['harness_error']}"
        for r in recs
        if r.get("harness_error")
    ]
    write_json(run_dir / "run_meta.json", log)
    print(
        f"done; harness errors: {len(inv['harness_errors'])}. Next: uv run python evals/agentic/score.py {run_dir}"
    )
    return 1 if inv["harness_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
