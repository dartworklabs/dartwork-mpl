"""One-shot failure harvesting with installed wheels and isolated headless hosts."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ROOT = Path.home() / "scratch" / "dartwork-mpl-smoke"
WORK = Path.home() / "scratch" / "dartwork-mpl-smoke-work"


def dump(path, value):
    """Write a durable, human-readable record outside the checkout."""
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def command(argv, cwd=None, env=None, timeout=600):
    """Run setup with closed stdin; never include credentials in error messages."""
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(
            f"{argv[0]} failed ({result.returncode}): {result.stderr[-1500:]}"
        )
    return result.stdout


def executable(name):
    """Also support user-local CLIs absent from a GUI application's PATH."""
    found = shutil.which(name)
    local = Path.home() / ".local/bin" / name
    if found:
        return found
    if local.is_file():
        return str(local)
    raise RuntimeError(f"Required executable unavailable: {name}")


def environment(project):
    """No API keys, inherited repository paths or agent nesting state."""
    env = {
        k: os.environ[k]
        for k in ("HOME", "USER", "LOGNAME", "LANG", "SHELL")
        if k in os.environ
    }
    env.update(
        PATH=f"{project}/.venv/bin:{Path.home()}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        MPLBACKEND="Agg",
        MPLCONFIGDIR=str(project / ".mplconfig"),
        TMPDIR=str(project / ".tmp"),
        CODEX_HOME=str(project / ".codex"),
        CLAUDE_CODE_DISABLE_AUTO_MEMORY="1",
        CLAUDE_CODE_TMPDIR=str(project / ".tmp"),
        TERM="dumb",
    )
    if "CLAUDE_CONFIG_DIR" in os.environ:
        env["CLAUDE_CONFIG_DIR"] = os.environ["CLAUDE_CONFIG_DIR"]
    return env


def hidden_paths():
    """Hide all checkouts sharing this repository, not just this worktree."""
    paths = [
        Path(line[9:]).resolve()
        for line in command(
            ["git", "worktree", "list", "--porcelain"], REPO
        ).splitlines()
        if line.startswith("worktree ")
    ]
    paths += [ROOT.resolve()]
    home = Path.home()
    codex = Path(os.environ.get("CODEX_HOME", home / ".codex"))
    claude = Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude"))
    for root in {
        home / ".agents",
        codex,
        home / ".codex",
        claude,
        home / ".claude",
    }:
        for name in (
            "AGENTS.md",
            "CLAUDE.md",
            "skills",
            "plugins",
            "projects",
            "sessions",
            "archived_sessions",
            "history.jsonl",
            "todos",
            "tasks",
        ):
            p = root / name
            paths.extend([p, p.resolve()])
    return sorted(set(paths))


def sandbox(argv, project, hidden, writable=None):
    """OS-enforced read denial plus write confinement; fail closed off macOS.

    Reads stay open inside ``project``. Writes are confined to ``writable``
    (the project by default; the replay passes its own subdirectory).
    """
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").exists():
        raise RuntimeError(
            "This runner currently requires macOS sandbox-exec; no unsandboxed fallback"
        )

    def quote(p):
        return json.dumps(str(p))

    clauses = [
        "(version 1)",
        "(allow default)",
        f'(deny file-write* (require-all (require-not (subpath {quote(writable or project)})) (require-not (subpath "/dev"))))',
        f"(deny file-read* (require-all (subpath {quote(WORK.resolve())}) (require-not (subpath {quote(project)}))))",
        # A host that canonicalizes its own home (Codex does) must stat each
        # ancestor. Metadata of the work root itself is allowed; its listing
        # and every sibling unit stay unreadable.
        f"(allow file-read-metadata (literal {quote(WORK.resolve())}))",
    ]
    clauses += [f"(deny file-read* (subpath {quote(p)}))" for p in hidden]
    return ["/usr/bin/sandbox-exec", "-p", "\n".join(clauses), *argv]


def probe(project, hidden, env):
    """Actually attempt blocked reads and a permitted project read before any model call."""
    source = "import os,sys; bad=[]\nfor p in sys.argv[1:]:\n try: os.listdir(p) if os.path.isdir(p) else open(p,'rb').read(1); bad.append(p)\n except OSError: pass\nassert not bad, bad\nassert open('data.csv').read(1)\n"
    targets = [p for p in hidden if p.exists()]
    sibling = Path(tempfile.mkdtemp(prefix="probe-", dir=WORK))
    canary = sibling / "private.txt"
    canary.write_text("not an input")
    try:
        command(
            sandbox(
                [
                    str(project / ".venv/bin/python"),
                    "-c",
                    source,
                    *map(str, targets),
                    str(canary),
                ],
                project,
                hidden,
            ),
            project,
            env,
        )
    finally:
        canary.unlink(missing_ok=True)
        sibling.rmdir()


def host_command(host, prompt, project):
    """Use subscription authentication and suppress global settings/tools."""
    if host == "claude":
        profile = Path(
            os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")
        )
        excludes = [str(p) for p in hidden_paths() if p.name == "CLAUDE.md"]
        return [
            executable(host),
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "bypassPermissions",
            "--tools",
            "Bash,Read,Write,Edit,Glob,Grep,Skill",
            "--setting-sources",
            "project",
            "--strict-mcp-config",
            "--no-chrome",
            "--no-session-persistence",
            "--settings",
            json.dumps({"claudeMdExcludes": [*excludes, str(profile / "**")]}),
        ]
    args = [
        executable(host),
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
        "--disable",
        "multi_agent",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "-C",
        str(project),
    ]
    original = (
        Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        / "config.toml"
    )
    if any(
        config.exists()
        and re.search(
            r"(?m)^\s*\[mcp_servers\.github\]\s*(?:#.*)?$", config.read_text()
        )
        for config in {original, Path.home() / ".codex/config.toml"}
    ):
        args += [
            "--config=mcp_servers.github.enabled=false",
            '--config=mcp_servers.github.command="false"',
        ]
    if original.exists():
        model = tomllib.loads(original.read_text()).get("model")
        if model:
            args += ["-m", model]
    return [*args, prompt]


def run_host(argv, project, env, unit, timeout):
    """Stream directly to disk and kill the entire process group at the deadline."""
    start = time.monotonic()
    # Pipes matter: Node initializes inherited regular descriptors by reopening
    # them, which Seatbelt correctly denies when they point into the result tree.
    proc = subprocess.Popen(
        argv,
        cwd=project,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    def drain(stream, path, timeline=None):
        with path.open("wb") as output:
            for line in iter(stream.readline, b""):
                output.write(line)
                output.flush()
                if timeline is not None:
                    with timeline.open("a") as stamps:
                        stamps.write(
                            json.dumps(
                                {
                                    "received_at": time.time(),
                                    "line": line.decode(
                                        "utf-8", errors="replace"
                                    ),
                                }
                            )
                            + "\n"
                        )

    readers = [
        threading.Thread(
            target=drain,
            args=(proc.stdout, unit / "events.jsonl", unit / "timeline.jsonl"),
        ),
        threading.Thread(target=drain, args=(proc.stderr, unit / "stderr.txt")),
    ]
    for reader in readers:
        reader.start()
    try:
        code = proc.wait(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        code = None
        timed_out = True
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        for reader in readers:
            reader.join()
    return {
        "exit_code": code if code is not None else proc.returncode,
        "timed_out": timed_out,
        "wall_s": round(time.monotonic() - start, 2),
    }


def events(path):
    """Retain malformed raw output on disk, ignoring it only for summary extraction."""
    rows = []
    for line in path.read_text().splitlines() if path.exists() else []:
        with contextlib.suppress(ValueError):
            rows.append(json.loads(line))
    return rows


def usage(host, rows):
    """Keep the host's usage schema rather than inventing equivalent billing totals."""
    if host == "claude":
        result = next(
            (r for r in reversed(rows) if r.get("type") == "result"), {}
        )
        return {
            "tokens": result.get("usage"),
            "turns": result.get("num_turns"),
            "host_error": result.get("is_error"),
        }
    turns = [r for r in rows if r.get("type") == "turn.completed"]
    totals = {}
    for row in turns:
        for key, value in row.get("usage", {}).items():
            if isinstance(value, int):
                totals[key] = totals.get(key, 0) + value
    return {
        "tokens": totals or None,
        "turns": len(turns) or None,
        "host_error": any(
            r.get("type") in {"error", "turn.failed"} for r in rows
        ),
    }


def same_file(tool_path, cwd, target):
    """Whether a tool's path argument, read from ``cwd``, names ``target``."""
    path = Path(tool_path)
    if not path.is_absolute():
        path = Path(cwd or ".") / path
    return os.path.realpath(path) == os.path.realpath(target)


def inspection(
    host, rows, rollouts, final_png, final_time, timeline=(), cwd=None
):
    """Bind successful image-tool results to a path and final artifact write time."""
    if not final_png:
        return "no final PNG"
    if host == "claude":
        pending = {}
        for received in timeline:
            try:
                row = json.loads(received["line"])
            except (KeyError, ValueError):
                continue
            for block in row.get("message", {}).get("content", []):
                if not isinstance(block, dict):
                    continue
                if (
                    block.get("type") == "tool_use"
                    and block.get("name") == "Read"
                ):
                    path = block.get("input", {}).get("file_path", "")
                    if same_file(path, cwd, final_png):
                        pending[block["id"]] = path
                # The result's time decides: a Read requested in the same
                # message as the render is issued before the file exists but
                # runs, and returns the image, after it.
                if (
                    block.get("type") == "tool_result"
                    and block.get("tool_use_id") in pending
                    and received["received_at"] >= final_time
                ):
                    content = block.get("content", [])
                    if (
                        isinstance(content, list)
                        and not block.get("is_error")
                        and any(
                            c.get("type") == "image"
                            for c in content
                            if isinstance(c, dict)
                        )
                    ):
                        return "yes (successful image Read after final write)"
        return "unknown (no timestamped successful image evidence)"
    # Rollouts retain tool-level timestamps omitted by the public JSON stream.
    for row in rollouts:
        payload = row.get("payload", {})
        if (
            payload.get("type") != "function_call"
            or payload.get("name") != "view_image"
        ):
            continue
        try:
            args = json.loads(payload["arguments"])
            stamp = datetime.fromisoformat(
                row["timestamp"].replace("Z", "+00:00")
            ).timestamp()
            if same_file(args["path"], cwd, final_png) and stamp >= final_time:
                return "attempted (view_image after final write; verify image result in rollout)"
        except (KeyError, ValueError, TypeError):
            continue
    return "unknown (no matching timestamped view_image call)"


REPLAY = r"""
import json, runpy, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import dartwork_mpl as dm
reports = []
original = Figure.savefig
def save(self, *args, **kwargs):
    reports.append({"saved": str(args[0]) if args else str(kwargs.get("fname")),
                    "findings": [{"check_id": w.check_id, "severity": w.severity.value,
                                  "message": w.message} for w in dm.validate_figure(self, quiet=True)]})
    return original(self, *args, **kwargs)
Figure.savefig = save
runpy.run_path(sys.argv[1], run_name="__main__")
for n in plt.get_fignums():
    fig = plt.figure(n)
    reports.append({"open_figure": n, "findings": [{"check_id": w.check_id, "severity": w.severity.value,
                    "message": w.message} for w in dm.validate_figure(fig, quiet=True)]})
Path("validator.json").write_text(json.dumps(reports, indent=2))
"""


def has_base(case):
    """Edits and repairs start from a script the host must leave as it is."""
    return case["kind"] in {"edit", "repair"}


def final_script(case):
    """A revision is kept beside its base; a new figure is the only script."""
    return "revision.py" if has_base(case) else "plot.py"


def warning_ids(reports):
    """The distinct WARNING ids over every validated save and open figure."""
    return sorted(
        {
            f["check_id"]
            for r in reports
            for f in r["findings"]
            if f["severity"] == "WARNING"
        }
    )


def replay(project, script, py, env, hidden, unit, tag=""):
    """Re-run a copy of ``script`` and validate each figure as it is saved.

    The copy lives in its own directory, the only place it may write, so a
    script with absolute paths cannot touch the host's ``out/``. It takes a
    copy of ``out/`` too: a revision reviewed against ``out/original`` reads
    the review the host left there. Only files the replay itself wrote are
    kept as re-rendered outputs. The directory is removed afterwards: a base
    is replayed before the host starts, and the host must not find its
    findings.
    """
    folder = project / "replay"
    folder.mkdir()
    try:
        for path in project.iterdir():
            if (
                not path.is_symlink()
                and not path.name.startswith(".")
                and path.name != "replay"
            ):
                target = folder / path.name
                shutil.copytree(
                    path, target, symlinks=True
                ) if path.is_dir() else shutil.copy2(path, target)
        (folder / "_validate.py").write_text(REPLAY)
        replay_env = dict(env)
        for key, name in (("TMPDIR", ".tmp"), ("MPLCONFIGDIR", ".mplconfig")):
            (folder / name).mkdir()
            replay_env[key] = str(folder / name)
        copied = {
            path: path.stat().st_mtime_ns
            for path in (folder / "out").rglob("*")
            if path.is_file() and not path.is_symlink()
        }
        log = command(
            sandbox([py, "_validate.py", script], project, hidden, folder),
            folder,
            replay_env,
            timeout=120,
        )
        (unit / f"{tag}replay.log").write_text(log)
        shutil.copy2(folder / "validator.json", unit / f"{tag}validator.json")
        if (folder / "out").is_dir() and not (folder / "out").is_symlink():
            for path in sorted((folder / "out").rglob("*")):
                if (
                    path.is_file()
                    and not path.is_symlink()
                    and path.stat().st_mtime_ns != copied.get(path)
                ):
                    target = (
                        unit
                        / f"{tag}replay-artifacts"
                        / path.relative_to(folder / "out")
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
        reports = json.loads((unit / f"{tag}validator.json").read_text())
        if not reports:
            raise RuntimeError(
                "Script ran but no saved/open figure could be validated"
            )
        return reports
    finally:
        shutil.rmtree(folder)


def host_outputs(project):
    """Whether the host left a real out/figure.png and out/figure.pdf."""
    return all(
        (project / "out" / name).is_file()
        and not (project / "out" / name).is_symlink()
        for name in ("figure.png", "figure.pdf")
    )


def preserve(project, unit):
    """Collect every script and rendered artifact, excluding the venv and host state."""
    paths = []
    for folder, dirs, files in os.walk(project):
        dirs[:] = [
            d for d in dirs if not d.startswith(".") and d != "__pycache__"
        ]
        for name in files:
            path = Path(folder) / name
            if (
                path.suffix.lower() in {".py", ".png", ".pdf", ".json"}
                and not path.is_symlink()
            ):
                rel = path.relative_to(project)
                target = unit / "artifacts" / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                paths.append(str(rel))
    return sorted(paths)


def one(case, host, wheel, run, timeout):
    """A unit owns its project, venv, process group, transcript and failure receipt."""
    unit = run / case["id"] / host
    unit.mkdir(parents=True)
    (unit / "request.txt").write_text(case["request"] + "\n")
    record = {
        "case": case["id"],
        "host": host,
        "tokens": None,
        "turns": None,
        "execution": "failure",
        "warnings": [],
    }
    with tempfile.TemporaryDirectory(prefix="unit-", dir=WORK) as folder:
        project = Path(folder).resolve()
        env = environment(project)
        hidden = hidden_paths()
        try:
            for name in (".tmp", ".codex", ".mplconfig"):
                (project / name).mkdir()
            for source in (HERE / "cases" / case["id"]).iterdir():
                if source.name != "case.json":
                    shutil.copy2(source, project / source.name)
            command(
                [
                    executable("uv"),
                    "venv",
                    "--python",
                    "3.11",
                    str(project / ".venv"),
                ]
            )
            py = str(project / ".venv/bin/python")
            command(
                [
                    executable("uv"),
                    "pip",
                    "install",
                    "--python",
                    py,
                    str(wheel),
                    "pandas",
                ]
            )
            (unit / "skill-help.txt").write_text(
                command(
                    [py, "-m", "dartwork_mpl.skills", "install", "--help"],
                    project,
                    env,
                )
            )
            (unit / "skill-install.txt").write_text(
                command(
                    [py, "-m", "dartwork_mpl.skills", "install", "--copy"],
                    project,
                    env,
                )
            )
            original_home = Path(
                os.environ.get("CODEX_HOME", Path.home() / ".codex")
            )
            if host == "codex" and (original_home / "auth.json").exists():
                shutil.copy2(
                    original_home / "auth.json", project / ".codex/auth.json"
                )
                (project / ".codex/auth.json").chmod(0o600)
            probe(project, hidden, env)
            record["isolation_probe"] = (
                "passed: checkout/results/global instructions/sibling reads denied"
            )
            if has_base(case):
                command(sandbox([py, "plot.py"], project, hidden), project, env)
                shutil.copytree(project / "out", unit / "base")
                shutil.rmtree(project / "out")
                # What the validator says about the base, for before → after.
                record["base_validator"] = "could not re-run"
                try:
                    record["base_warnings"] = warning_ids(
                        replay(
                            project, "plot.py", py, env, hidden, unit, "base-"
                        )
                    )
                    record["base_validator"] = "re-ran"
                except (
                    RuntimeError,
                    OSError,
                    subprocess.TimeoutExpired,
                ) as exc:
                    record["base_replay_error"] = str(exc)
            final = final_script(case)
            prompt = (
                case["request"]
                + f"\n\nProject notes: dartwork-mpl and pandas are installed in .venv. Use .venv/bin/python. The installed dartwork-mpl skill is available in this project. Keep the final runnable script as {final} and final outputs as out/figure.png and out/figure.pdf. Do the work yourself without subagents."
            )
            (unit / "prompt.txt").write_text(prompt)
            argv = host_command(host, prompt, project)
            record.update(
                run_host(
                    sandbox(argv, project, hidden), project, env, unit, timeout
                )
            )
            record.update(usage(host, events(unit / "events.jsonl")))
            rollouts = []
            for index, path in enumerate(
                (project / ".codex/sessions").rglob("*.jsonl")
            ):
                shutil.copy2(path, unit / f"rollout-{index}.jsonl")
                rollouts += events(path)
            record["files"] = preserve(project, unit)
            # Judged before the replay, which must not be able to supply them.
            produced = host_outputs(project)
            png = project / "out/figure.png"
            script = project / final
            final_time = max(
                (
                    p.stat().st_mtime
                    for p in (png, script, project / "out/figure.pdf")
                    if p.exists()
                ),
                default=0,
            )
            record["opened_final_png"] = inspection(
                host,
                events(unit / "events.jsonl"),
                rollouts,
                png if png.exists() else None,
                final_time,
                events(unit / "timeline.jsonl"),
                project,
            )
            record["validator"] = "could not re-run"
            if script.is_file() and not script.is_symlink():
                # Re-run a copy: validation must not overwrite the agent's outputs.
                try:
                    reports = replay(project, final, py, env, hidden, unit)
                    record["validator"] = "re-ran"
                    record["warnings"] = warning_ids(reports)
                except (
                    RuntimeError,
                    OSError,
                    subprocess.TimeoutExpired,
                ) as exc:
                    record["replay_error"] = str(exc)
            if (
                record["exit_code"] == 0
                and not record["host_error"]
                and produced
                and record["validator"] == "re-ran"
            ):
                record["execution"] = "success"
        except Exception as exc:  # noqa: BLE001 - every setup failure needs a receipt
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["files"] = preserve(project, unit)
        finally:
            dump(unit / "run.json", record)
    print(f"{case['id']}/{host}: {record['execution']}", flush=True)
    return record


def summary(run, records):
    """A review index, never a score or statistical verdict."""
    lines = [
        "# Smoke round",
        "",
        "Execution is a process/artifact check, not figure correctness. Inspect PNGs and transcripts.",
        "",
        "| Case / host | Execution | Files | Base WARNING ids | Validator WARNING ids | Host tokens | Turns | Wall s | Opened final PNG after last write |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        prefix = f"{r['case']}/{r['host']}"
        files = ", ".join(
            f"[{p}]({prefix}/artifacts/{p})" for p in r.get("files", [])
        )
        findings = ", ".join(r["warnings"]) or (
            "none" if r.get("validator") == "re-ran" else "could not re-run"
        )
        if "base_validator" not in r:
            base = "no base"
        elif r["base_validator"] != "re-ran":
            base = "could not re-run"
        else:
            base = ", ".join(r["base_warnings"]) or "none"
        lines.append(
            f"| [{prefix}]({prefix}/run.json) | {r['execution']} | {files} | {base} | {findings} | {json.dumps(r['tokens'])} | {r['turns']} | {r.get('wall_s', 'NOTRUN')} | {r.get('opened_final_png', 'unknown')} |"
        )
    (run / "SUMMARY.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        nargs="+",
        help="case ids (space or comma separated); default all",
    )
    parser.add_argument("--hosts", nargs="+", default=["claude", "codex"])
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--run-id", default=datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    args = parser.parse_args()
    cases = [
        json.loads(p.read_text())
        for p in sorted((HERE / "cases").glob("*/case.json"))
    ]
    selected = {v for arg in args.cases or [] for v in arg.split(",")}
    hosts = [v for arg in args.hosts for v in arg.split(",")]
    if selected - {c["id"] for c in cases} or set(hosts) - {"claude", "codex"}:
        parser.error("unknown case or host")
    if len(set(hosts)) != len(hosts) or args.jobs < 1 or args.timeout < 1:
        parser.error("hosts must be unique; jobs and timeout must be positive")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_id):
        parser.error("run-id must be a single safe path component")
    if selected:
        cases = [c for c in cases if c["id"] in selected]
    ROOT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    run = ROOT / args.run_id
    run.mkdir()  # Refuse overwrite, including partially completed rounds.
    wheel_dir = run / "wheel"
    wheel_dir.mkdir()
    command(
        [executable("uv"), "build", "--wheel", "--out-dir", str(wheel_dir)],
        REPO,
        timeout=900,
    )
    wheel = next(wheel_dir.glob("*.whl"))
    dump(
        run / "manifest.json",
        {
            "commit": command(["git", "rev-parse", "HEAD"], REPO).strip(),
            "wheel": wheel.name,
            "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "runner_sha256": hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            "cases": [c["id"] for c in cases],
            "hosts": hosts,
            "jobs": args.jobs,
            "timeout": args.timeout,
            "versions": {
                h: command([executable(h), "--version"]).strip() for h in hosts
            },
        },
    )
    records = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [
            pool.submit(one, c, h, wheel, run, args.timeout)
            for c in cases
            for h in hosts
        ]
        for future in futures:
            records.append(future.result())
            summary(run, records)
    print(run / "SUMMARY.md")
    return int(any(r["execution"] != "success" for r in records))


if __name__ == "__main__":
    raise SystemExit(main())
