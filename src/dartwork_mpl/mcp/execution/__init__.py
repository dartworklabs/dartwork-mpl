"""Trusted-snippet execution with optional private input paths, without authorization.

``validate_plot`` runs a snippet and returns its ``ExecutionOutcome`` (one
variant per way a run ends, see ``.outcome``); ``to_wire`` turns an outcome
into the legacy ``validate_generated_plot`` report dict. ``export_plot`` also
saves the selected Figure and returns ``ExportedPlot`` or one ``ExportFailure``
variant; each holds its run's outcome and exposes the legacy ``report`` dict
that the artifact edge stores and returns.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias

from .checkpoint import Checkpoint, ChildExportFailed, parse_checkpoint, settle
from .outcome import (
    AnalysisExhausted,
    Diagnostics,
    ExecFailed,
    ExecutionOutcome,
    Incomplete,
    LintBlocked,
    LintRecord,
    NoFigure,
    Passed,
    SourceRefused,
    TimedOut,
    to_wire,
)

if TYPE_CHECKING:
    from .._platform import CapturedProcess

__all__ = [
    "ExecutionOutcome",
    "ExecutionRejected",
    "ExportFailure",
    "ExportRejected",
    "ExportedPlot",
    "LogLimitRejected",
    "export_plot",
    "to_wire",
    "validate_plot",
]

# Direct execution callers retain the existing ceiling. Artifact delivery
# supplies its own authoritative bundle allowance through log_limit_bytes.
_DEFAULT_EXPORT_LOG_BYTES = 32 * 1024 * 1024
_MAX_SOURCE_BYTES = 512 * 1024


@dataclass(frozen=True)
class ExportedPlot:
    """Selected Figure was validated and both output files were exported."""

    outcome: Passed | Incomplete

    @property
    def report(self) -> dict[str, Any]:
        """The legacy report (a fresh dict) for ``report.json``."""
        return to_wire(self.outcome)


@dataclass(frozen=True)
class ExecutionRejected:
    """Execution did not yield an exportable validated Figure."""

    outcome: (
        SourceRefused
        | AnalysisExhausted
        | LintBlocked
        | NoFigure
        | ExecFailed
        | TimedOut
    )

    @property
    def report(self) -> dict[str, Any]:
        """The legacy report (a fresh dict) returned with the refusal."""
        return to_wire(self.outcome)


@dataclass(frozen=True)
class LogLimitRejected:
    """A bounded incomplete report whose original logs exceed the caller's limit."""

    outcome: ExecFailed

    @property
    def report(self) -> dict[str, Any]:
        """The legacy ``exec_error`` report with the bounded diagnostics."""
        return to_wire(self.outcome)


@dataclass(frozen=True)
class ExportRejected:
    """Export failed after validation, retaining its evidence without paths."""

    outcome: ExecFailed | TimedOut
    message: str = "Artifact export failed."

    @property
    def report(self) -> dict[str, Any]:
        """The legacy report of the run whose export failed."""
        return to_wire(self.outcome)


ExportFailure: TypeAlias = ExecutionRejected | LogLimitRejected | ExportRejected


@dataclass(frozen=True)
class _Launched:
    """A reaped child with its parsed checkpoint and the pre-launch lint."""

    checkpoint: Checkpoint
    process: "CapturedProcess"
    lint: tuple[LintRecord, ...]
    hinted: bool

    def outcome(self) -> ExecutionOutcome:
        """Settle the run; a log overrun is a failed exit."""
        return settle(
            self.checkpoint,
            Diagnostics(self.lint, self.process.stdout, self.process.stderr),
            self.hinted,
            timed_out=self.process.timed_out and not self.process.log_overrun,
            exited_cleanly=self.process.returncode == 0
            and not self.process.log_overrun,
        )


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
) -> ExecutionOutcome:
    """Execute trusted source and return how the run ended, with bounded diagnostic logs.

    Source/timeout admission shares render's existing limits; unrelated legacy
    figure/hint values retain their behavior. No code runs on admission or
    handleable AST-resource refusal. This is not an OS security sandbox.
    ``to_wire`` gives the outcome's legacy report.
    """
    ran = _run(
        code, figure_var, timeout_seconds, chart_type_hint, output_stem=None
    )
    return ran.outcome() if isinstance(ran, _Launched) else ran


def export_plot(
    code: str,
    figure_var: str,
    timeout_seconds: float,
    chart_type_hint: str | None,
    *,
    output_stem: Path,
    input_paths: Mapping[str, str] | None = None,
    log_limit_bytes: int = _DEFAULT_EXPORT_LOG_BYTES,
) -> ExportedPlot | ExportFailure:
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
    ran = _run(
        code,
        figure_var,
        timeout_seconds,
        chart_type_hint,
        output_stem=output_stem,
        input_paths=input_paths,
        log_limit_bytes=log_limit_bytes,
    )
    if not isinstance(ran, _Launched):
        return ExecutionRejected(ran)
    outcome = ran.outcome()
    if ran.process.log_overrun and isinstance(outcome, ExecFailed):
        return LogLimitRejected(outcome)
    if isinstance(ran.checkpoint, ChildExportFailed) and isinstance(
        outcome, (ExecFailed, TimedOut)
    ):
        return ExportRejected(outcome)
    if isinstance(outcome, (Passed, Incomplete)):
        return ExportedPlot(outcome)
    return ExecutionRejected(outcome)


def _run(
    code: str,
    figure_var: str,
    timeout_seconds: float,
    chart_type_hint: str | None,
    *,
    output_stem: Path | None,
    input_paths: Mapping[str, str] | None = None,
    log_limit_bytes: int | None = None,
) -> SourceRefused | AnalysisExhausted | LintBlocked | _Launched:
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

    from .._platform import run_child

    if input_paths is not None:
        if not isinstance(input_paths, Mapping):
            raise TypeError("input_paths must map string names to string paths")
        input_paths = dict(input_paths)
        if not all(
            isinstance(name, str) and isinstance(path, str)
            for name, path in input_paths.items()
        ):
            raise TypeError("input_paths must map string names to string paths")

    hinted = chart_type_hint is not None
    # Match render's code/timeout admission without a reverse feature import.
    # Legacy figure/hint handling retains its independent existing behavior.
    admission_error = _source_timeout_error(code, timeout_seconds)
    if admission_error is not None:
        return SourceRefused(admission_error, hinted)

    try:
        # lint intentionally tolerates some parse failures, including recursion;
        # MCP must recognize a resource refusal before invoking trusted source.
        with suppress(SyntaxError, ValueError, UnicodeError):
            ast.parse(code)
        lint_issues = tuple(
            LintRecord(
                i.rule_id, i.severity, i.line, i.message, i.fix_suggestion
            )
            for i in _lint(code)
        )
    except (MemoryError, RecursionError) as exc:
        # Refuse a handleable parser/lint resource fault without source or paths.
        return AnalysisExhausted(type(exc).__name__, hinted)
    if any(i.severity == "critical" for i in lint_issues):
        return LintBlocked(lint_issues, hinted)

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

    def _read_result(path: Path) -> Checkpoint:
        """Read and parse the private checkpoint; missing/invalid framing records nothing."""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = None
        return parse_checkpoint(raw)

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
        return _Launched(_read_result(result_path), proc, lint_issues, hinted)
