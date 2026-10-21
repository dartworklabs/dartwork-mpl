"""Trusted-snippet execution with optional private input paths, without authorization."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._capture import diagnostic, publish_png, run_child, strip_diagnostic

__all__ = [
    "ExecutionRejected",
    "ExportRejected",
    "ExportedPlot",
    "LogLimitRejected",
    "diagnostic",
    "export_plot",
    "publish_png",
    "run_child",
    "strip_diagnostic",
    "validate_plot",
]

# Direct execution callers retain the existing ceiling. Artifact delivery
# supplies its own authoritative bundle allowance through log_limit_bytes.
_DEFAULT_EXPORT_LOG_BYTES = 32 * 1024 * 1024
_MAX_SOURCE_BYTES = 512 * 1024


@dataclass(frozen=True)
class ExportedPlot:
    """Selected Figure was validated and both output files were exported."""

    report: dict[str, Any]


@dataclass(frozen=True)
class ExecutionRejected:
    """Execution did not yield an exportable validated Figure."""

    report: dict[str, Any]


@dataclass(frozen=True)
class LogLimitRejected(ExecutionRejected):
    """A bounded incomplete report whose original logs exceed the caller's limit."""


@dataclass(frozen=True)
class ExportRejected:
    """Export failed after validation, retaining its evidence without paths."""

    report: dict[str, Any]
    message: str = "Artifact export failed."


def _source_timeout_error(code: str, timeout_seconds: float) -> str | None:
    """Return safe legacy admission diagnostics, without artifact dependencies.

    Execution owns these source/timeout checks; render independently parses its
    richer request. Keep their existing limits/messages equal while retaining
    legacy figure/hint handling. No caller content enters a refusal message.
    """
    try:
        if (
            not isinstance(code, str)
            or len(code.encode("utf-8")) > _MAX_SOURCE_BYTES
        ):
            return "code: Source must be at most 512 KiB of UTF-8."
    except UnicodeError:
        return "code: Source must be valid UTF-8."
    if (
        type(timeout_seconds) not in (int, float)
        or not 0 < timeout_seconds <= 120
        or not math.isfinite(timeout_seconds)
    ):
        return "timeout_seconds: Timeout must be finite and in (0, 120]."
    return None


def validate_plot(
    code: str,
    figure_var: str = "fig",
    timeout_seconds: float = 20.0,
    chart_type_hint: str | None = None,
) -> dict[str, Any]:
    """Execute trusted source with legacy outcomes and bounded diagnostic logs.

    Source/timeout admission shares render's existing limits; unrelated legacy
    figure/hint values retain their behavior. No code runs on admission or
    handleable AST-resource refusal. This is not an OS security sandbox.
    """
    return _run(
        code, figure_var, timeout_seconds, chart_type_hint, output_stem=None
    )


def export_plot(
    code: str,
    figure_var: str,
    timeout_seconds: float,
    chart_type_hint: str | None,
    *,
    output_stem: Path,
    input_paths: Mapping[str, str] | None = None,
    log_limit_bytes: int = _DEFAULT_EXPORT_LOG_BYTES,
) -> ExportedPlot | ExecutionRejected | ExportRejected:
    """Validate and export one selected Figure in a single child execution.

    Nonempty ``input_paths`` supplies a read-only ``dartwork_inputs`` mapping
    in the snippet globals. The caller owns authorization and file lifetime;
    this runner neither checks nor copies those files. Names and paths must
    be strings (otherwise TypeError is raised before launch). None or an
    empty mapping uses the legacy source-only protocol and injects nothing.
    Source, cwd and inherited environment retain their existing semantics;
    trusted code can expose the paths itself. Accepted processed logs remain
    exact; logs exceeding positive ``log_limit_bytes`` return LogLimitRejected
    with bounded diagnostics. Direct callers retain the 32 MiB default; artifact
    callers supply their own bundle allowance. An invalid limit raises ValueError
    before child launch. The wire schema and execution statuses are unchanged.
    """
    if type(log_limit_bytes) is not int or log_limit_bytes <= 0:
        raise ValueError("Shared log budget must be a positive integer")
    report = _run(
        code,
        figure_var,
        timeout_seconds,
        chart_type_hint,
        output_stem=output_stem,
        input_paths=input_paths,
        log_limit_bytes=log_limit_bytes,
    )
    export_failed = report.pop("_export_failed", False)
    if report.pop("_artifact_logs_too_large", False):
        return LogLimitRejected(report)
    if export_failed:
        return ExportRejected(report)
    if report["status"] in {"ok", "validation_incomplete"}:
        return ExportedPlot(report)
    return ExecutionRejected(report)


def _run(
    code: str,
    figure_var: str,
    timeout_seconds: float,
    chart_type_hint: str | None,
    *,
    output_stem: Path | None,
    input_paths: Mapping[str, str] | None = None,
    log_limit_bytes: int | None = None,
) -> dict[str, Any]:
    """Run a child and remove its checkpoint on return, error or timeout.

    Opt-in stdin is one ASCII JSON mapping line, a newline, then the exact
    submitted source. JSON escapes embedded newlines; the child parses data
    without eval and reads the remaining stream as source. Only a protocol
    marker enters argv, never mapping data; environment and cwd are inherited.
    A malformed private frame follows the existing exec_error outcome.
    Invalid caller mapping types raise TypeError before launch. File access
    policy and asynchronous call cancellation/draining belong to callers. Export
    callers supply a positive shared log limit; legacy validation uses per-channel
    diagnostic limits. Invalid limits raise ValueError before child launch.
    """
    import ast
    import json
    import sys
    import textwrap
    from contextlib import suppress
    from tempfile import TemporaryDirectory

    from dartwork_mpl.lint import lint as _lint

    from ._capture import run_child

    if input_paths is not None:
        if not isinstance(input_paths, Mapping):
            raise TypeError("input_paths must map string names to string paths")
        input_paths = dict(input_paths)
        if not all(
            isinstance(name, str) and isinstance(path, str)
            for name, path in input_paths.items()
        ):
            raise TypeError("input_paths must map string names to string paths")

    def _finalize(payload: dict[str, Any]) -> dict[str, Any]:
        """Keep logs and completion fields consistent on every outcome.

        Semantic warnings are present iff a chart hint was supplied.
        An error cannot claim completion, even with partial check results.
        """
        payload.setdefault("visual_warnings", [])
        payload.setdefault("stdout", "")
        payload.setdefault("failed_checks", [])
        payload["validation_complete"] = payload["status"] == "ok"
        if chart_type_hint is None:
            payload.pop("semantic_warnings", None)
        else:
            payload.setdefault("semantic_warnings", [])
        return payload

    # Match render's code/timeout admission without a reverse feature import.
    # Legacy figure/hint handling retains its independent existing behavior.
    admission_error = _source_timeout_error(code, timeout_seconds)
    if admission_error is not None:
        return _finalize(
            {"status": "exec_error", "lint": [], "stderr": admission_error}
        )

    def _resource_failure(exc: MemoryError | RecursionError) -> dict[str, Any]:
        """Refuse a handleable parser/lint resource fault without source or paths."""
        return _finalize(
            {
                "status": "exec_error",
                "lint": [],
                "exc_type": type(exc).__name__,
                "stderr": "Python source analysis exceeded available parser resources.",
            }
        )

    try:
        # lint intentionally tolerates some parse failures, including recursion;
        # MCP must recognize a resource refusal before invoking trusted source.
        with suppress(SyntaxError, ValueError, UnicodeError):
            ast.parse(code)
        lint_issues = [
            {
                "rule_id": i.rule_id,
                "severity": i.severity,
                "line": i.line,
                "message": i.message,
                "fix_suggestion": i.fix_suggestion,
            }
            for i in _lint(code)
        ]
    except (MemoryError, RecursionError) as exc:
        return _resource_failure(exc)
    critical = [i for i in lint_issues if i["severity"] == "critical"]
    if critical:
        return _finalize(
            {
                "status": "lint_blocked",
                "lint": lint_issues,
                "visual_warnings": [],
                "stderr": (
                    "Critical lint issues must be fixed before "
                    "execution: "
                    + ", ".join(str(i["rule_id"]) for i in critical)
                ),
            }
        )

    runner = textwrap.dedent(
        """\
        import json
        import sys
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        result_path = sys.argv[1]
        output_stem = {output_stem!r}
        payload = {{"status": "exec_error", "failed_checks": []}}

        def _write_result():
            '''Persist internal results independently of snippet stdout.'''
            encoded = json.dumps(payload)
            with open(result_path, "w", encoding="utf-8") as channel:
                channel.write(encoded)

        ns: dict = {{"__name__": "__sandbox__"}}
        has_inputs = sys.argv[2:] == ["--dartwork-inputs-v1"]
        user_code = "" if has_inputs else sys.stdin.read()
        try:
            if has_inputs:
                from types import MappingProxyType
                input_paths = json.loads(sys.stdin.readline())
                if not isinstance(input_paths, dict) or not all(
                    isinstance(name, str) and isinstance(path, str)
                    for name, path in input_paths.items()
                ):
                    raise TypeError("Invalid private input mapping")
                ns["dartwork_inputs"] = MappingProxyType(input_paths)
                user_code = sys.stdin.read()
            exec(compile(user_code, "<agent-snippet>", "exec"), ns)
            fig = ns.get({figure_var!r})
            if fig is None:
                # Fall back to whatever Pyplot tracked.
                figs = plt.get_fignums()
                if figs:
                    fig = plt.figure(figs[-1])
            if fig is None:
                payload["status"] = "no_figure"
            else:
                from matplotlib.figure import Figure
                if output_stem is not None and not isinstance(fig, Figure):
                    raise TypeError("Selected value is not a matplotlib Figure")
                from dartwork_mpl import validate_figure

                warnings = validate_figure(fig, quiet=True)
                payload["failed_checks"] = [
                    w.detail["check_id"] for w in warnings
                    if w.check_id == "CHECK_FAILED"
                ]
                # Keep the checkpoint incomplete until all processing finishes.
                # Preserve acquired failures even if later processing fails.
                _write_result()
                payload["visual_warnings"] = [
                    {{
                        "severity": w.severity.name
                        if hasattr(w.severity, "name")
                        else str(w.severity),
                        "check_id": w.check_id,
                        "message": w.message,
                        "detail": w.detail,
                    }}
                    for w in warnings
                ]
                _write_result()
                # ── Semantic checks (only when a chart-type hint is given) ──
                # Catch plot choices that render fine but read poorly:
                # too many pie slices, too few scatter points, bars with
                # no value labels, etc.
                chart_hint = {chart_type_hint!r}
                semantic = []
                if chart_hint:
                    hint = chart_hint.lower()
                    ax_list = list(fig.axes)

                    def _ax_has_text(ax):
                        '''Return whether explicit text supplies annotation content.'''
                        # Annotation density proxy: number of Text artists
                        # the user explicitly added (excludes tick labels,
                        # title, axis labels which exist by default).
                        return any(
                            bool(getattr(t, "get_text", lambda: "")())
                            for t in getattr(ax, "texts", [])
                        )

                    for i, ax in enumerate(ax_list):
                        label = f"axes[{{i}}]"
                        if hint == "pie":
                            wedges = [
                                p for p in ax.patches
                                if type(p).__name__ == "Wedge"
                            ]
                            if len(wedges) > 7:
                                semantic.append({{
                                    "check_id": "pie_too_many_slices",
                                    "message": (
                                        f"{{label}} has {{len(wedges)}} pie "
                                        "slices; >7 is hard to read. "
                                        "Consider bar_horizontal sorted "
                                        "by share."
                                    ),
                                }})
                        elif hint == "scatter":
                            n_points = sum(
                                len(coll.get_offsets())
                                for coll in ax.collections
                                if hasattr(coll, "get_offsets")
                            )
                            if 0 < n_points < 5:
                                semantic.append({{
                                    "check_id": "scatter_too_few_points",
                                    "message": (
                                        f"{{label}} has only "
                                        f"{{n_points}} points; weak signal."
                                    ),
                                }})
                        elif hint in ("bar", "bar_grouped",
                                      "bar_horizontal", "stacked_bar"):
                            bars = [
                                p for p in ax.patches
                                if type(p).__name__ == "Rectangle"
                            ]
                            if bars and not _ax_has_text(ax):
                                semantic.append({{
                                    "check_id": "bar_missing_value_labels",
                                    "message": (
                                        f"{{label}} has {{len(bars)}} bars "
                                        "but no value labels — readers will "
                                        "have to eyeball the y-axis."
                                    ),
                                }})
                        elif hint == "line":
                            if not ax.lines:
                                semantic.append({{
                                    "check_id": "line_no_lines",
                                    "message": (
                                        f"{{label}} declared as a line chart "
                                        "but has no Line2D artists."
                                    ),
                                }})
                        elif hint == "histogram":
                            bars = [
                                p for p in ax.patches
                                if type(p).__name__ == "Rectangle"
                            ]
                            if bars and len(bars) < 10:
                                semantic.append({{
                                    "check_id": "histogram_too_few_bins",
                                    "message": (
                                        f"{{label}} has only {{len(bars)}} "
                                        "bins; consider more for a smoother "
                                        "shape (10 to 50 is typical)."
                                    ),
                                }})

                payload["semantic_warnings"] = semantic
                validated_status = (
                    "validation_incomplete" if payload["failed_checks"] else "ok"
                )
                if output_stem is not None:
                    _write_result()
                    try:
                        from dartwork_mpl import save_formats
                        save_formats(fig, output_stem, formats=("png", "pdf"), validate=False, adopt_orphan_tick_font=False)
                    except Exception:
                        payload["_export_failed"] = True
                        _write_result()
                        sys.exit(0)
                payload["status"] = validated_status
        except Exception as exc:
            payload.update({{
                "status": "exec_error",
                "exc_type": type(exc).__name__,
                "exc_msg": str(exc),
            }})
        _write_result()
        """
    ).format(
        figure_var=figure_var,
        chart_type_hint=chart_type_hint,
        output_stem=str(output_stem) if output_stem is not None else None,
    )

    def _read_result(path: Path) -> dict[str, Any]:
        """Read the private checkpoint, or report missing/invalid framing."""
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"status": "exec_error"}
        return result if isinstance(result, dict) else {"status": "exec_error"}

    # The private absolute channel is removed on success, error and timeout.
    # Cwd stays inherited so snippet save destinations retain their meaning.
    with TemporaryDirectory(prefix="dartwork-mpl-validate-") as directory:
        result_path = Path(directory).resolve() / "result.json"
        args = [sys.executable, "-c", runner, str(result_path)]
        stdin = code
        if input_paths:
            args.append("--dartwork-inputs-v1")
            stdin = json.dumps(input_paths, ensure_ascii=True) + "\n" + code
        proc = run_child(
            args,
            stdin=stdin,
            timeout_seconds=timeout_seconds,
            shared_log_limit=log_limit_bytes,
            strip_stderr=output_stem is None,
            timeout_message=output_stem is None,
        )
        payload = _read_result(result_path)
        if proc.timed_out:
            payload["status"] = "timeout"
        elif proc.returncode != 0:
            payload["status"] = "exec_error"
        if proc.log_overrun:
            payload.update(status="exec_error", _artifact_logs_too_large=True)
        payload["lint"] = lint_issues
        payload["stdout"] = proc.stdout
        payload["stderr"] = proc.stderr
        return _finalize(payload)
