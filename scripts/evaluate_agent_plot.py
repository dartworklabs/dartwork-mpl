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

__all__ = [
    "assess",
    "compare",
    "evaluate",
    "load_episode",
    "read_artists",
    "replay",
]

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
                        "x": float(patch.get_x() + patch.get_width() / 2),
                        "y": float(patch.get_y()),
                        "height": float(patch.get_height()),
                        "width": float(patch.get_width()),
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


def _json(path: Path) -> dict[str, Any]:
    """Read retained evaluator evidence; never execute the referenced source."""
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected retained JSON object: {path.name}")
    return value


def _sha(path: Path) -> str:
    """Identify exact retained bytes independently of recorded hash fields."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wire_objects(value: Any) -> Any:
    """Decode nested JSON wire payloads without interpreting model prose."""
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _wire_objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from _wire_objects(item)
    elif isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        try:
            nested = json.loads(value)
        except (ValueError, RecursionError):
            return
        yield from _wire_objects(nested)


def _events(path: Path) -> list[dict[str, Any]]:
    """Use actual assistant calls and correlated user receipts, excluding echoes."""
    return [json.loads(line) for line in path.read_text().splitlines()]


def _calls_and_results(
    events: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Index complete tool events by the host's tool-use identifier."""
    calls, results = {}, {}
    for event in events:
        blocks = event.get("message", {}).get("content", [])
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if (
                event.get("type") == "assistant"
                and block.get("type") == "tool_use"
            ):
                calls[block["id"]] = block
            elif (
                event.get("type") == "user"
                and block.get("type") == "tool_result"
            ):
                results[block["tool_use_id"]] = block
    return calls, results


def _terminal(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Identify the actual completed host session from its terminal wire event."""
    result = next(
        (event for event in reversed(events) if event.get("type") == "result"),
        {},
    )
    if (
        not result.get("session_id")
        or result.get("is_error")
        or result.get("subtype") != "success"
    ):
        raise ValueError("missing successful host terminal/session event")
    return result


def _receipt(
    events: list[dict[str, Any]], identity: str, bundle: Path
) -> dict[str, Any]:
    """Bind a decoded image and exact full report to successful results for this ID.

    Hosts can resize images before writing their event stream. Record that
    distinction; original/replay pixel equality is a separate semantic check.
    """
    import base64
    import io

    from PIL import Image

    calls, results = _calls_and_results(events)
    image, report, rendered_source = False, False, False
    png = bundle.joinpath("plot.png").read_bytes()
    source = bundle.joinpath("source.py").read_bytes()
    expected_report = _json(bundle / "report.json")
    image_receipts = {}
    for call_id, call in calls.items():
        result = results.get(call_id, {})
        if not result or result.get("is_error"):
            continue
        objects = list(_wire_objects(result))
        if call.get("name") in {
            "mcp__dartwork_mpl__render_plot",
            "mcp__dartwork_mpl__get_plot_artifact",
        } and any(
            obj.get("artifact_id") == identity
            and obj.get("delivery_status") == "ready"
            for obj in objects
        ):
            rendered_source |= (
                call.get("name") == "mcp__dartwork_mpl__render_plot"
                and call.get("input", {}).get("code", "").encode() == source
                and call.get("input") == _json(bundle / "render-arguments.json")
            )
            for obj in objects:
                if obj.get("type") == "image":
                    encoded = obj.get("source", {}).get(
                        "data", obj.get("data", "")
                    )
                    try:
                        raw = base64.b64decode(encoded, validate=True)
                        with Image.open(io.BytesIO(raw)) as decoded:
                            size = decoded.size
                            decoded.verify()
                        image = True
                        digest = hashlib.sha256(raw).hexdigest()
                        image_receipts[digest] = {
                            "sha256": digest,
                            "dimensions": list(size),
                            "exact_artifact_png": raw == png,
                        }
                    except (OSError, ValueError):
                        continue
        if (
            call.get("name") == "ReadMcpResourceTool"
            and call.get("input", {}).get("uri")
            == f"dartwork-mpl://artifacts/{identity}/report.json"
        ):
            report |= expected_report in objects
    return {
        "image": image,
        "full_report": report,
        "rendered_source": rendered_source,
        "image_receipts": list(image_receipts.values()),
    }


def _gate(status: str, **evidence: Any) -> dict[str, Any]:
    """Keep failed and unchecked outcomes distinct in the public evaluation."""
    return {"status": status, "passed": status == "passed", **evidence}


def _bundle(stage: Path, identity: str) -> dict[str, Any]:
    """Verify manifest members, collector identity and exact render arguments."""
    names = {
        "plot.png",
        "plot.pdf",
        "source.py",
        "report.json",
        "manifest.json",
    }
    if (
        not isinstance(identity, str)
        or len(identity) != 32
        or any(c not in "0123456789abcdef" for c in identity)
    ):
        raise ValueError("invalid retained artifact identity")
    manifest = _json(stage / "manifest.json")
    members = manifest["files"]
    if (
        manifest.get("schema_version") != 1
        or manifest.get("artifact_id") != identity
    ):
        raise ValueError("manifest identity/schema mismatch")
    if len(members) != 4 or {entry["name"] for entry in members} != names - {
        "manifest.json"
    }:
        raise ValueError("manifest member set mismatch")
    hashes = {name: _sha(stage / name) for name in names}
    for entry in members:
        path = stage / entry["name"]
        if (
            path.stat().st_size != entry["size_bytes"]
            or hashes[entry["name"]] != entry["sha256"]
        ):
            raise ValueError("manifest member size/hash mismatch")
    collected = stage / "collected"
    if _json(collected / "hashes.json").get(identity) != hashes:
        raise ValueError("collected hash identity mismatch")
    if any(
        (collected / identity / name).read_bytes()
        != (stage / name).read_bytes()
        for name in names
    ):
        raise ValueError("collected member bytes mismatch")
    arguments = _json(stage / "render-arguments.json")
    source = stage.joinpath("source.py").read_bytes()
    if arguments.get("code", "").encode() != source:
        raise ValueError("source/render-argument mismatch")
    events = _events(stage / "events.jsonl")
    receipt = _receipt(events, identity, stage)
    if not receipt["rendered_source"]:
        raise ValueError("source not bound to selected render result")
    return {
        "artifact_id": identity,
        "hashes": hashes,
        "receipt": receipt,
        "arguments": arguments,
        "terminal": _terminal(events),
    }


def _saved_semantics(
    run: Path, stage: str, case_id: str, bundle: dict[str, Any]
) -> dict[str, Any]:
    """Transfer supported replay observations only after exact-source/pixel checks."""
    import matplotlib.image as mpimg

    directory = run / "replay" / stage
    replayed = _json(directory / "result.json")
    if replayed.get("status") != "ok":
        return _gate(
            "unchecked",
            reason="retained replay did not complete",
            replay=replayed,
        )
    if (
        replayed.get("source_sha256") != bundle["hashes"]["source.py"]
        or replayed.get("csv_sha256")
        != load_episode(case_id)["expected"]["csv_sha256"]
    ):
        return _gate(
            "unchecked", reason="replay source/fixture identity mismatch"
        )
    if replayed.get("figure_var") != bundle["arguments"].get(
        "figure_var", "fig"
    ):
        return _gate("unchecked", reason="replay figure argument mismatch")
    expected_export = {
        "api": "dartwork_mpl.save_formats",
        "formats": ["png", "pdf"],
        "validate": False,
        "adopt_orphan_tick_font": False,
        "staging": "owned_workspace",
    }
    if replayed.get("export") != expected_export or replayed.get(
        "png_sha256"
    ) != _sha(directory / "plot.png"):
        return _gate("unchecked", reason="replay export identity mismatch")
    original = mpimg.imread(run / stage / "plot.png")
    replay_png = mpimg.imread(directory / "plot.png")
    same = np.array_equal(original, replay_png)
    if not same:
        return _gate(
            "unchecked",
            reason="decoded replay pixels differ from original",
            pixels_equal=False,
        )
    observed = _json(directory / "observed.json")
    if observed != replayed.get("observed"):
        return _gate(
            "unchecked", reason="retained observation identity mismatch"
        )
    assessment = assess(case_id, observed)
    return _gate(
        "passed"
        if assessment["passed"]
        else "unchecked"
        if assessment["unchecked"]
        else "failed",
        pixels_equal=True,
        assessment=assessment,
        replay_png_sha256=_sha(directory / "plot.png"),
    )


def evaluate(run: Path) -> dict[str, Any]:
    """Assess one retained episode without source execution or baseline repair.

    Independent image review and no-human-edit attestations live in the optional
    evaluator-owned ``evaluator-review.json`` sidecar, bound to exact PNG/source
    hashes. Missing evidence remains unchecked. CLI exit is nonzero for either
    failed or unchecked dimensions.
    """
    run = run.resolve()
    try:
        state = _json(run / "run.json")
        case_id = state["case_id"]
        expected = load_episode(case_id)["expected"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return _gate(
            "unchecked",
            run=str(run),
            reason=f"missing/invalid run evidence: {exc}",
        )
    dimensions: dict[str, Any] = {}
    bundles, semantics, reports, receipts, errors = {}, {}, {}, {}, {}
    for stage in ("original", "revision"):
        try:
            identity = state["stages"][stage]["review"]["artifact_id"]
            bundle = _bundle(run / stage, identity)
            if bundle["terminal"]["session_id"] != state["stages"][stage][
                "review"
            ]["session_id"] or set(
                bundle["terminal"].get("modelUsage", {})
            ) != {state["configured_model"]}:
                raise ValueError("captured session/model identity mismatch")
            bundles[stage] = bundle
            report = _json(run / stage / "report.json")
            manifest = _json(run / stage / "manifest.json")
            good_report = (
                report.get("status") == "ok"
                and report.get("validation_complete") is True
                and report.get("failed_checks") == []
            )
            good_report &= manifest.get("validation") == {
                key: report[key]
                for key in ("status", "validation_complete", "failed_checks")
            }
            reports[stage] = _gate(
                "passed" if good_report else "failed", report=report
            )
            receipt = bundle["receipt"]
            receipts[stage] = _gate(
                "passed"
                if receipt["image"] and receipt["full_report"]
                else "failed",
                **receipt,
            )
            try:
                semantics[stage] = _saved_semantics(run, stage, case_id, bundle)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                semantics[stage] = _gate("unchecked", reason=str(exc))
        except (OSError, ValueError, KeyError, TypeError) as exc:  # noqa: PERF203
            errors[stage] = str(exc)
            semantics.setdefault(stage, _gate("unchecked", reason=str(exc)))
    recovery = _gate(
        "unchecked", reason="both original/revision bundles required"
    )
    if len(bundles) == 2:
        try:
            ids = {bundle["artifact_id"] for bundle in bundles.values()}
            if len(ids) != 2 or set(state["artifact_ids"]) != ids:
                raise ValueError("original/revision artifact ID set mismatch")
            events = _events(run / "recovery/events.jsonl")
            calls, _ = _calls_and_results(events)
            requested = {
                call.get("input", {}).get("artifact_id")
                for call in calls.values()
                if call.get("name") == "mcp__dartwork_mpl__get_plot_artifact"
            }
            if not ids.issubset(requested) or any(
                "render" in call.get("name", "")
                or "validate_generated_plot" in call.get("name", "")
                for call in calls.values()
            ):
                raise ValueError(
                    "fresh agent did not retrieve both IDs without execution"
                )
            initial_session = state["stages"]["original"]["review"][
                "session_id"
            ]
            revision_session = state["stages"]["revision"]["review"][
                "session_id"
            ]
            recovery_session = state["stages"]["recovery"]["review"][
                "session_id"
            ]
            if _terminal(events)["session_id"] != recovery_session:
                raise ValueError(
                    "fresh-agent terminal/session identity mismatch"
                )
            if (
                not initial_session
                or initial_session != revision_session
                or not recovery_session
                or initial_session == recovery_session
            ):
                raise ValueError("resume/fresh-agent session identity mismatch")
            mechanical = run / "recovery/independent"
            recovery_receipts = {}
            for stage, bundle in bundles.items():
                identity = bundle["artifact_id"]
                recovery_receipts[identity] = _receipt(
                    events, identity, run / stage
                )
                if (
                    not recovery_receipts[identity]["image"]
                    or not recovery_receipts[identity]["full_report"]
                ):
                    raise ValueError(
                        "fresh agent image/full-report receipt missing"
                    )
                hashes = {
                    name: _sha(mechanical / identity / name)
                    for name in bundle["hashes"]
                }
                if (
                    hashes != bundle["hashes"]
                    or _json(mechanical / "hashes.json").get(identity) != hashes
                    or state.get("recovery_hashes", {}).get(identity) != hashes
                ):
                    raise ValueError(
                        "independent five-member recovery mismatch"
                    )
            recovery = _gate(
                "passed",
                agent_receipts=recovery_receipts,
                five_members_per_id=True,
                fresh_session=True,
                no_execution=True,
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            recovery = _gate("failed", reason=str(exc))
    infrastructure = (
        state.get("infrastructure_status") == "ok"
        and state.get("workspace_cleanup") is True
        and state.get("csv_sha256") == expected["csv_sha256"]
        and (run / "input.csv").is_file()
        and _sha(run / "input.csv") == expected["csv_sha256"]
    )
    dimensions["delivery"] = _gate(
        "passed"
        if infrastructure
        and len(bundles) == 2
        and recovery["passed"]
        and not errors
        else "failed",
        stages={
            stage: {
                "artifact_id": bundle["artifact_id"],
                "hashes": bundle["hashes"],
            }
            for stage, bundle in bundles.items()
        },
        recovery=recovery,
        errors=errors,
    )
    for name, stages in (
        ("declared_validation", reports),
        ("model_review", receipts),
        ("semantic_replay", semantics),
    ):
        statuses = [item["status"] for item in stages.values()]
        status = (
            "failed"
            if "failed" in statuses
            else "unchecked"
            if len(stages) != 2 or "unchecked" in statuses
            else "passed"
        )
        dimensions[name] = _gate(status, stages=stages)
    dimensions["semantic_replay"]["style_data_unchanged"] = _gate(
        dimensions["semantic_replay"]["status"],
        basis="Original and revision independently match the same pinned rows, masks, groups and panels after decoded-pixel identity checks.",
    )
    try:
        review = _json(run / "evaluator-review.json")
    except (OSError, ValueError):
        review = {}
    visual = review.get("visual_review", {})
    facets = ("labels", "units", "panels", "clipping", "readability")
    visual_ok = (
        len(bundles) == 2
        and bool(review.get("reviewer"))
        and all(
            visual.get(stage, {}).get("png_sha256")
            == bundle["hashes"]["plot.png"]
            and all(
                visual.get(stage, {}).get(key) == "passed" for key in facets
            )
            and bool(visual.get(stage, {}).get("notes"))
            for stage, bundle in bundles.items()
        )
    )
    dimensions["visual_review"] = _gate(
        "passed" if visual_ok else "unchecked" if not visual else "failed",
        reviewer=review.get("reviewer"),
        stages=visual,
    )
    attested = review.get("human_code_edits", {})
    source_hashes = {
        stage: bundle["hashes"]["source.py"]
        for stage, bundle in bundles.items()
    }
    edits_ok = (
        bool(attested.get("attested_by"))
        and bool(attested.get("provenance"))
        and type(attested.get("edits")) is int
        and attested["edits"] == 0
        and attested.get("interventions") == []
        and attested.get("source_sha256") == source_hashes
    )
    dimensions["human_code_edits"] = _gate(
        "passed" if edits_ok else "unchecked" if not attested else "failed",
        attestation=attested,
        actual_source_sha256=source_hashes,
    )
    statuses = [item["status"] for item in dimensions.values()]
    status = (
        "failed"
        if "failed" in statuses
        else "unchecked"
        if "unchecked" in statuses
        else "passed"
    )
    return _gate(
        status,
        run=str(run),
        run_sha256=_sha(run / "run.json"),
        case_id=case_id,
        recorded_status=state.get("status"),
        stop_reason=state.get("stop_reason"),
        dimensions=dimensions,
    )


def compare(baseline: Path, candidate: Path) -> dict[str, Any]:
    """Compare all four once-only episodes while preserving failures and unknowns."""
    cases: dict[str, Any] = {}
    comparability_errors: list[str] = []
    for case in _CASES:
        before, after = evaluate(baseline / case), evaluate(candidate / case)
        environment = {}
        try:
            old, new = (
                _json(baseline / case / "run.json"),
                _json(candidate / case / "run.json"),
            )
            for key in (
                "configured_model",
                "configured_effort",
                "versions",
                "font",
                "server_entry_sha256",
                "environment",
                "csv_sha256",
            ):
                environment[key] = (
                    old.get(key) == new.get(key) and key in old and key in new
                )
            for label, state in (("baseline", old), ("candidate", new)):
                environment[label + "_observed_model"] = bool(
                    state.get("effective_models")
                ) and set(state["effective_models"]) == {
                    state.get("configured_model")
                }
            configured = (
                old.get("configured_model"),
                old.get("configured_effort"),
            )
            if not all(environment.values()):
                comparability_errors.append(case)
        except (OSError, ValueError, KeyError, TypeError):
            configured = None
            comparability_errors.append(case)
        cases[case] = {
            "baseline": before,
            "candidate": after,
            "environment": environment,
            "configured": configured,
            "review_receipts": {
                label: result.get("dimensions", {})
                .get("model_review", {})
                .get("status", "unchecked")
                for label, result in (
                    ("baseline", before),
                    ("candidate", after),
                )
            },
        }
    frozen_errors: list[str] = []
    try:
        frozen = _json(baseline / "frozen-baseline.json")
        if len(frozen["cases"]) != 4 or {
            item["case"] for item in frozen["cases"]
        } != set(_CASES):
            raise ValueError("frozen case set mismatch")
        frozen_errors.extend(
            item["case"]
            for item in frozen["cases"]
            if item["run_sha256"] != _sha(baseline / item["case"] / "run.json")
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        frozen_errors.append(str(exc))
    passed = (
        not comparability_errors
        and not frozen_errors
        and all(
            pair[label]["passed"]
            for pair in cases.values()
            for label in ("baseline", "candidate")
        )
    )
    return _gate(
        "passed" if passed else "failed",
        cases=cases,
        candidate_gate=all(
            pair["candidate"]["passed"] for pair in cases.values()
        ),
        baseline_gate=all(
            pair["baseline"]["passed"] for pair in cases.values()
        ),
        comparability_errors=comparability_errors,
        frozen_baseline_errors=frozen_errors,
        limitations=[
            "Four single episodes do not establish general model performance or prompt causality.",
            "Configured effort can match while effective effort remains unobserved.",
            "Candidate evaluator normalizes native bar numeric scalars; baseline failed bar replay remains unchecked and is not reconstructed.",
            "Baseline scatter requested production-valid 60 seconds, rejected by hidden evaluator 20-second cap; not a user/tool-contract or causal prompt failure.",
            "Dynamic or external replay inputs remain unchecked; no new source execution occurs during comparison.",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("replay", "_replay", "evaluate", "compare")
    )
    parser.add_argument("source", type=Path, nargs="?")
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("figure_var", nargs="?", default="fig")
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--case", choices=_CASES)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--export-dir", type=Path)
    parser.add_argument(
        "--max-evidence-bytes", type=int, default=128 * 1024 * 1024
    )
    args = parser.parse_args()
    if args.command in {"evaluate", "compare"}:
        if args.command == "evaluate":
            if args.run is None:
                parser.error("evaluate requires --run")
            result = evaluate(args.run)
        else:
            if args.baseline is None or args.candidate is None:
                parser.error("compare requires --baseline and --candidate")
            result = compare(args.baseline, args.candidate)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["passed"] else 1)
    if args.source is None or args.output is None:
        parser.error("replay requires source and output")
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
