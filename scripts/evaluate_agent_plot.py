"""Independent data-space oracle for four fixed, evaluator-owned plot episodes.

This module neither executes agent code nor trusts agent reports. Its supported
surface is native Line2D, vertical BarContainer and PathCollection artists in
ordinary data coordinates. Unsupported artists or ambiguous mappings are
explicitly unchecked and cannot produce a passing assessment.
"""

import argparse
import ast
import contextlib
import hashlib
import json
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.container import BarContainer
from matplotlib.figure import Figure

__all__ = ["assess", "load_episode", "read_artists", "replay"]

_FIXTURES = (
    Path(__file__).resolve().parents[1] / "tests/mcp/agent_loop/fixtures"
)
_CASES = ("line", "groupedbar", "scatter", "custom2panel")


def load_episode(case_id: str) -> dict[str, Any]:
    """Load a fixed request and independent expectations after checking CSV bytes.

    Unknown case IDs raise ValueError; changed fixture bytes raise ValueError.
    The returned ``expected`` member is evaluator-only, never model input.
    ``requests[2]`` is an ID placeholder to replace with the last artifact ID.
    """
    if case_id not in _CASES:
        raise ValueError(f"Unknown episode: {case_id}")
    episodes = json.loads((_FIXTURES / "episodes.json").read_text())
    expected = json.loads((_FIXTURES / "expected.json").read_text())[case_id]
    episode = episodes[case_id]
    path = _FIXTURES / episode["csv"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected["csv_sha256"]:
        raise ValueError(f"CSV digest mismatch: {case_id}")
    return {**episode, "csv_path": str(path), "expected": expected}


def _coordinates(x: Any, y: Any) -> dict[str, Any]:
    """Preserve each coordinate's mask and nonfinite status without imputation."""
    pair = np.ma.column_stack((x, y))
    values = np.asarray(pair.data, dtype=float)
    mask = np.broadcast_to(pair.mask, pair.shape) | ~np.isfinite(values)
    return {"xy": np.where(mask, 0.0, values).tolist(), "mask": mask.tolist()}


def read_artists(fig: Figure) -> dict[str, Any]:
    """Snapshot actual artist geometry, masks and labels, with no agent metadata.

    Panels are ordered by rendered horizontal position, not creation order.
    Bar labels are cross-checked with category/group geometry during assessment.
    Extra or unsupported data artists, transforms and overlapping panels remain
    unchecked. Reversed bar x axes and internally rotated rectangles are outside
    the supported left/right, vertical-bar mapping. Text, spines, grids and
    legends are outside this data-only oracle.
    """
    panels = []
    unchecked = []
    axes = sorted(fig.axes, key=lambda ax: ax.get_position().x0)
    for index, ax in enumerate(axes):
        prefix = f"panel {index}"
        bounds = ax.get_position()
        if index and bounds.x0 < axes[index - 1].get_position().x1:
            unchecked.append(f"{prefix}: overlapping panel mapping")
        panel: dict[str, Any] = {
            "lines": [],
            "scatters": [],
            "bars": [],
            "ticks": list(
                zip(
                    ax.get_xticks().tolist(),
                    [tick.get_text() for tick in ax.get_xticklabels()],
                    strict=True,
                )
            ),
        }
        for line in ax.lines:
            if line.get_transform() is not ax.transData:
                unchecked.append(f"{prefix}: line outside data coordinates")
            if not line.get_visible():
                unchecked.append(f"{prefix}: invisible line")
            x, y = line.get_data(orig=False)
            panel["lines"].append(_coordinates(x, y))
        for collection in ax.collections:
            if not isinstance(collection, PathCollection):
                unchecked.append(
                    f"{prefix}: unsupported {type(collection).__name__}"
                )
                continue
            if collection.get_offset_transform() is not ax.transData:
                unchecked.append(f"{prefix}: scatter outside data coordinates")
            if not collection.get_visible():
                unchecked.append(f"{prefix}: invisible scatter")
            # Matplotlib annotates this as ArrayLike, but returns a 2-D array.
            offsets: Any = collection.get_offsets()
            panel["scatters"].append(_coordinates(offsets[:, 0], offsets[:, 1]))
        bar_patches = set()
        for container in ax.containers:
            if not isinstance(container, BarContainer):
                unchecked.append(
                    f"{prefix}: unsupported {type(container).__name__}"
                )
                continue
            if container.orientation != "vertical":
                unchecked.append(f"{prefix}: horizontal bars")
            if ax.xaxis_inverted():
                unchecked.append(f"{prefix}: reversed bar category/group axis")
            for patch in container.patches:
                bar_patches.add(patch)
                if patch.get_data_transform() is not ax.transData:
                    unchecked.append(f"{prefix}: bar outside data coordinates")
                if not np.isclose(
                    patch.get_angle() % 360, 0, rtol=0, atol=1e-9
                ):
                    unchecked.append(f"{prefix}: internally rotated bar")
                if not patch.get_visible():
                    unchecked.append(f"{prefix}: invisible bar")
                panel["bars"].append(
                    {
                        "x": patch.get_x() + patch.get_width() / 2,
                        "y": patch.get_y(),
                        "height": patch.get_height(),
                        "width": patch.get_width(),
                        "label": container.get_label(),
                    }
                )
        unchecked.extend(
            f"{prefix}: unsupported {type(patch).__name__}"
            for patch in ax.patches
            if patch not in bar_patches
        )
        unchecked.extend(
            f"{prefix}: unsupported {type(artist).__name__}"
            for artist in [*ax.artists, *ax.images]
        )
        panels.append(panel)
    unchecked.extend(
        f"figure: unsupported {type(artist).__name__}"
        for artist in [*fig.artists, *fig.lines, *fig.patches, *fig.images]
    )
    return {"panels": panels, "unchecked": unchecked}


def _check_points(
    expected: dict[str, Any], actual: dict[str, Any], prefix: str
) -> list[str]:
    """Compare coordinates by row, retaining line order and ignoring scatter order."""
    want = np.column_stack((expected["x"], expected["y"]))
    got = np.asarray(actual["xy"], dtype=float).reshape(-1, 2)
    mask = np.asarray(actual["mask"], dtype=bool).reshape(-1, 2)
    if mask.any():
        return [f"{prefix}: unexpected masked/nonfinite measurement"]
    if got.shape != want.shape:
        return [f"{prefix}: row count {len(got)} != {len(want)}"]
    if expected["kind"] == "scatter":
        got = got[np.argsort(got[:, 0], kind="stable")]
        want = want[np.argsort(want[:, 0], kind="stable")]
    different = ~np.isclose(got, want, rtol=0.0, atol=1e-9)
    if different.any():
        row = int(np.flatnonzero(different.any(axis=1))[0])
        return [
            f"{prefix}: coordinate/order mismatch at row {expected['row_ids'][row]}"
        ]
    return []


def _check_bars(
    expected: dict[str, Any], panel: dict[str, Any], prefix: str
) -> tuple[list[str], list[str]]:
    """Map category ticks and left/right group positions onto actual rectangles."""
    categories = expected["categories"]
    groups = expected["groups"]
    ticks = panel["ticks"]
    if [label for _, label in ticks] != categories:
        return [], [f"{prefix}: ambiguous category ticks/order"]
    centers = np.asarray([position for position, _ in ticks], dtype=float)
    if not np.all(np.diff(centers) > 0):
        return [], [f"{prefix}: ambiguous category centers"]
    bars = panel["bars"]
    if len(bars) != len(expected["rows"]):
        return [f"{prefix}: bar row count mismatch"], []
    rows = {(row["category"], row["group"]): row for row in expected["rows"]}
    by_category: list[list[dict[str, Any]]] = [[] for _ in categories]
    for bar in bars:
        numeric = np.array([bar[key] for key in ("x", "y", "height", "width")])
        if not np.isfinite(numeric).all() or bar["width"] <= 0:
            return [f"{prefix}: invalid bar geometry"], []
        distances = abs(centers - bar["x"])
        category_index = int(distances.argmin())
        if (
            np.count_nonzero(np.isclose(distances, distances.min(), atol=1e-9))
            != 1
        ):
            return [], [f"{prefix}: ambiguous bar/category mapping"]
        if distances.min() >= np.diff(centers).min() / 2:
            return [], [f"{prefix}: bar outside category neighborhood"]
        by_category[category_index].append(bar)
    violations = []
    for category, members in zip(categories, by_category, strict=True):
        if len(members) != len(groups):
            violations.append(
                f"{prefix}: missing/duplicated group in {category}"
            )
            continue
        members.sort(key=lambda bar: bar["x"])
        if np.isclose(members[0]["x"], members[1]["x"], rtol=0, atol=1e-9):
            return violations, [f"{prefix}: overlapping group positions"]
        for group, bar in zip(groups, members, strict=True):
            row = rows[category, group]
            if not np.isclose(bar["y"], 0, rtol=0, atol=1e-9) or not np.isclose(
                bar["height"], row["value"], rtol=0, atol=1e-9
            ):
                violations.append(
                    f"{prefix}: changed value/group for {row['row_id']}"
                )
            if bar["label"] in groups and bar["label"] != group:
                violations.append(
                    f"{prefix}: group label disagrees with geometry"
                )
    return violations, []


def assess(case_id: str, observed: dict[str, Any]) -> dict[str, Any]:
    """Assess only observed artists against pinned independent expectations.

    ``passed`` requires no violations and no unchecked data representation.
    Extra keys, including an agent's ready/ok report, confer no authority.
    Fixture integrity and unknown-ID errors follow ``load_episode``.
    """
    expected = load_episode(case_id)["expected"]["panels"]
    unchecked = list(observed.get("unchecked", []))
    violations = []
    panels = observed["panels"]
    if len(panels) != len(expected):
        violations.append("panel count mismatch")
    else:
        for index, (want, got) in enumerate(zip(expected, panels, strict=True)):
            prefix = f"panel {index}"
            key = {"line": "lines", "scatter": "scatters", "bar": "bars"}[
                want["kind"]
            ]
            if any(
                got[other]
                for other in ("lines", "scatters", "bars")
                if other != key
            ):
                violations.append(f"{prefix}: unexpected artist family")
            if key == "bars":
                problems, unknown = _check_bars(want, got, prefix)
                violations.extend(problems)
                unchecked.extend(unknown)
            elif len(got[key]) != 1:
                violations.append(
                    f"{prefix}: expected one {want['kind']} artist"
                )
            else:
                violations.extend(_check_points(want, got[key][0], prefix))
    return {
        "passed": not violations and not unchecked,
        "violations": violations,
        "unchecked": unchecked,
    }


def _replay_inputs(source: bytes, csv: Path) -> list[str]:
    """Conservatively mark unsupported imports and file inputs before replay.

    This static review is deliberately incomplete and is not an OS sandbox.
    Only ordinary fixture readers and local plot exports are supported.
    """
    tree = ast.parse(source)
    unchecked = []
    literals = {
        target.id: node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    allowed = {
        "csv",
        "pathlib",
        "numpy",
        "pandas",
        "matplotlib",
        "dartwork_mpl",
        "math",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            if any(name.split(".")[0] not in allowed for name in names):
                unchecked.append("unsupported import/input dependency")
        if isinstance(node, ast.Attribute) and node.attr in {
            "random",
            "default_rng",
            "rand",
            "randn",
            "now",
            "today",
            "time",
            "urlopen",
            "request",
            "getenv",
            "environ",
            "read_bytes",
            "write_text",
            "write_bytes",
        }:
            unchecked.append("network/time/random/external IO dependency")
        if isinstance(node, ast.Call):
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else ""
            )
            if name in {
                "open",
                "read_csv",
                "loadtxt",
                "genfromtxt",
                "read_text",
            }:
                argument = node.args[0] if node.args else None
                path = (
                    argument.value
                    if isinstance(argument, ast.Constant)
                    and isinstance(argument.value, str)
                    else literals.get(argument.id)
                    if isinstance(argument, ast.Name)
                    else None
                )
                if path is None:
                    unchecked.append("unresolved file input")
                elif (csv.parent / path).resolve() != csv.resolve():
                    unchecked.append("file input outside fixed CSV")
            if name in {"eval", "exec", "compile", "__import__"}:
                unchecked.append("dynamic execution dependency")
    return sorted(set(unchecked))


def _replay_bytes(root: Path, cwd: Path) -> int:
    """Count shared retained evidence and owned replay cwd files once per path."""
    paths = {
        path
        for base in (root, cwd)
        for path in base.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    total = 0
    for path in paths:
        # Local exporters may rename a temporary file between listing and stat.
        with contextlib.suppress(FileNotFoundError):
            total += path.stat().st_size
    return total


def _replay_write(
    path: Path, data: bytes, root: Path, cwd: Path, limit: int
) -> bool:
    """Account controlled generated members and metadata before writing bytes."""
    replaced = path.stat().st_size if path.exists() else 0
    if _replay_bytes(root, cwd) - replaced + len(data) > limit:
        return False
    path.write_bytes(data)
    return True


def _watch_replay(
    argv: list[str],
    cwd: Path,
    env: dict[str, str],
    output: Path,
    root: Path,
    limit: int,
    timeout: float,
) -> dict[str, Any]:
    """Bound replay pipes and observe shared generated files while its group runs.

    Source writes remain trusted local IO, observed at poll boundaries rather
    than constrained by an OS filesystem quota. Controlled writes are checked
    before persistence. Partial stdout/stderr is retained up to capacity.
    """
    started = time.monotonic()
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    reason = "exit"
    try:
        with (
            (output / "stdout.txt").open("wb") as stdout,
            (output / "stderr.txt").open("wb") as stderr,
        ):
            while selector.get_map():
                if _replay_bytes(root, cwd) > limit:
                    reason = "evidence_limit"
                    break
                if time.monotonic() - started >= timeout:
                    reason = "timeout"
                    break
                for key, _ in selector.select(timeout=0.025):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    available = max(0, limit - _replay_bytes(root, cwd))
                    target = stdout if key.data == "stdout" else stderr
                    target.write(chunk[:available])
                    target.flush()
                    if len(chunk) > available:
                        reason = "evidence_limit"
                        break
                if reason != "exit":
                    break
            if reason == "exit":
                try:
                    process.wait(
                        timeout=max(
                            0.001, timeout - (time.monotonic() - started)
                        )
                    )
                except subprocess.TimeoutExpired:
                    reason = "timeout"
            if _replay_bytes(root, cwd) > limit or process.returncode == 75:
                reason = "evidence_limit"
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        selector.close()
        process.stdout.close()
        process.stderr.close()
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        cleanup = True
    else:
        cleanup = False
    return {
        "stop_reason": reason if cleanup else "cleanup_failed",
        "returncode": process.returncode,
        "cleanup_ok": cleanup,
        "elapsed_seconds": time.monotonic() - started,
    }


def replay(
    source: Path,
    csv: Path,
    case_id: str,
    output_dir: Path,
    figure_var: str = "fig",
    *,
    timeout_seconds: float = 20,
    evidence_root: Path | None = None,
    max_evidence_bytes: int = 128 * 1024 * 1024,
) -> dict[str, Any]:
    """Replay exact source in a fresh bounded process before fixture cleanup.

    The original owned CSV directory is retained as cwd so absolute CSV paths
    work without edits. Return observed artists and a separate oracle result;
    this does not establish facts about the original execution's internals.
    Shared evidence and owned-cwd files count toward max_evidence_bytes. Pipes
    and controlled members are bounded; source IO is observed, without an OS filesystem quota.
    """
    source, csv, output_dir = (
        source.resolve(),
        csv.resolve(),
        output_dir.resolve(),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    root = evidence_root.resolve() if evidence_root is not None else output_dir
    # Reserve space for explicit failure/result metadata and caller finalization.
    data_limit = max_evidence_bytes - min(64 * 1024, max_evidence_bytes // 4)
    raw, fixture = source.read_bytes(), csv.read_bytes()
    result: dict[str, Any] = {
        "status": "unchecked",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "csv_sha256": hashlib.sha256(fixture).hexdigest(),
        "cwd_mode": "original_owned_workspace",
        "figure_var": figure_var,
    }
    try:
        unknown = _replay_inputs(raw, csv)
    except SyntaxError as exc:
        unknown = [f"invalid source: {exc.msg}"]
    if _replay_bytes(root, csv.parent) > data_limit:
        result.update(
            status="failed",
            stop_reason="evidence_limit",
            process={
                "stop_reason": "evidence_limit",
                "cleanup_ok": True,
                "launched": False,
            },
        )
    elif unknown:
        result["unchecked"] = unknown
    else:
        argv = [
            sys.executable,
            str(Path(__file__).resolve()),
            "_replay",
            str(source),
            str(output_dir),
            figure_var,
            "--evidence-root",
            str(root),
            "--max-evidence-bytes",
            str(data_limit),
        ]
        env = {
            key: os.environ[key]
            for key in (
                "PATH",
                "HOME",
                "TMPDIR",
                "LANG",
                "LC_ALL",
                "VIRTUAL_ENV",
            )
            if key in os.environ
        }
        env.update(MPLBACKEND="Agg", PYTHONHASHSEED="0")
        with tempfile.TemporaryDirectory(
            prefix="agent-replay-export-", dir=csv.parent
        ) as staging:
            argv.extend(("--export-dir", staging))
            process = _watch_replay(
                argv,
                csv.parent,
                env,
                output_dir,
                root,
                data_limit,
                min(20, timeout_seconds),
            )
        result["process"] = process
        code = process["returncode"]
        observed_path = output_dir / "observed.json"
        if (
            process["stop_reason"] == "exit"
            and code == 0
            and observed_path.exists()
        ):
            result.update(
                status="ok", observed=json.loads(observed_path.read_text())
            )
            result["assessment"] = assess(case_id, result["observed"])
            result["export"] = {
                "api": "dartwork_mpl.save_formats",
                "formats": ["png", "pdf"],
                "validate": False,
                "adopt_orphan_tick_font": False,
                "staging": "owned_workspace",
            }
            result["png_sha256"] = hashlib.sha256(
                (output_dir / "plot.png").read_bytes()
            ).hexdigest()
        else:
            result.update(
                status="failed",
                stop_reason=process["stop_reason"]
                if process["stop_reason"] != "exit"
                else "execution_error",
                returncode=code,
            )
    if csv.read_bytes() != fixture:
        result.update(status="failed", stop_reason="fixture_changed")
    payload = json.dumps(result, indent=2).encode("utf-8")
    if not _replay_write(
        output_dir / "result.json",
        payload,
        root,
        csv.parent,
        max_evidence_bytes,
    ):
        result.pop("observed", None)
        result.pop("assessment", None)
        result.update(status="failed", stop_reason="evidence_limit")
        payload = json.dumps(result, indent=2).encode("utf-8")
        if not _replay_write(
            output_dir / "result.json",
            payload,
            root,
            csv.parent,
            max_evidence_bytes,
        ):
            result["result_record_saved"] = False
    return result


def _replay_child(
    source: Path,
    output: Path,
    figure_var: str,
    evidence_root: Path,
    max_evidence_bytes: int,
    export_dir: Path,
) -> None:
    """Execute unchanged UTF-8 bytes once and snapshot the explicitly named figure."""
    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(source),
    }
    exec(compile(source.read_bytes(), str(source), "exec"), namespace)
    fig = namespace[figure_var]
    if not isinstance(fig, Figure):
        raise TypeError("figure_var does not name a native Figure")
    fig.canvas.draw()
    observed = json.dumps(read_artists(fig)).encode("utf-8")
    if not _replay_write(
        output / "observed.json",
        observed,
        evidence_root,
        Path.cwd(),
        max_evidence_bytes,
    ):
        raise SystemExit(75)
    import dartwork_mpl as dm

    stem = export_dir / "plot"
    dm.save_formats(
        fig,
        str(stem),
        formats=("png", "pdf"),
        validate=False,
        adopt_orphan_tick_font=False,
    )
    if not _replay_write(
        output / "plot.png",
        stem.with_suffix(".png").read_bytes(),
        evidence_root,
        Path.cwd(),
        max_evidence_bytes,
    ):
        raise SystemExit(75)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("replay", "_replay"))
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("figure_var", nargs="?", default="fig")
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--case", choices=_CASES)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--export-dir", type=Path)
    parser.add_argument(
        "--max-evidence-bytes", type=int, default=128 * 1024 * 1024
    )
    args = parser.parse_args()
    if args.command == "_replay":
        _replay_child(
            args.source,
            args.output,
            args.figure_var,
            args.evidence_root or args.output,
            args.max_evidence_bytes,
            args.export_dir or args.output,
        )
    elif args.csv is None or args.case is None:
        parser.error("replay requires --csv and --case")
    else:
        print(
            json.dumps(
                replay(
                    args.source,
                    args.csv,
                    args.case,
                    args.output,
                    args.figure_var,
                    evidence_root=args.evidence_root,
                    max_evidence_bytes=args.max_evidence_bytes,
                )
            )
        )
