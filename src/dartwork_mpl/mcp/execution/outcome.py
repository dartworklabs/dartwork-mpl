"""The outcomes of one trusted-snippet execution and their legacy wire report.

``ExecutionOutcome`` is the closed set of what a run can end in: refused
before lint (``SourceRefused``, ``AnalysisExhausted``), blocked by lint
(``LintBlocked``), or launched and then ``Passed``, ``Incomplete``,
``NoFigure``, ``ExecFailed`` or ``TimedOut``. Each variant holds only its own
evidence. ``to_wire`` is the one place the legacy status strings and report
keys exist: it rebuilds the exact report dict, key order included, that
``validate_generated_plot`` returns and artifacts store as ``report.json``.
"""

from dataclasses import dataclass
from typing import Any, TypeAlias

__all__ = [
    "AnalysisExhausted",
    "Assessed",
    "Checked",
    "Diagnostics",
    "ExecFailed",
    "ExecutionOutcome",
    "Incomplete",
    "LintBlocked",
    "LintRecord",
    "NoFigure",
    "Passed",
    "Progress",
    "Raised",
    "SemanticRecord",
    "SourceRefused",
    "TimedOut",
    "Unrecorded",
    "VisualRecord",
    "Warned",
    "to_wire",
]

_RESOURCE_MESSAGE = (
    "Python source analysis exceeded available parser resources."
)


@dataclass(frozen=True)
class LintRecord:
    """One lint issue as the execution report lists it (no column)."""

    rule_id: str
    severity: str
    line: int | None
    message: str
    fix_suggestion: str | None


@dataclass(frozen=True)
class VisualRecord:
    """One ``validate_figure`` warning recorded by the child; ``detail`` is its JSON object."""

    severity: str
    check_id: str
    message: str
    detail: dict[str, Any]


@dataclass(frozen=True)
class SemanticRecord:
    """One chart-type semantic warning recorded by the child."""

    check_id: str
    message: str


@dataclass(frozen=True)
class Unrecorded:
    """The child left no readable checkpoint, so no validation evidence exists."""


@dataclass(frozen=True)
class Checked:
    """The child recorded which checks failed, but no warnings yet."""

    failed_checks: tuple[str, ...]


@dataclass(frozen=True)
class Warned:
    """The child recorded failed checks and the visual warnings."""

    failed_checks: tuple[str, ...]
    visual_warnings: tuple[VisualRecord, ...]


@dataclass(frozen=True)
class Assessed:
    """The child recorded all validation evidence, semantic warnings included.

    ``semantic_warnings`` is empty when no (or an empty) chart hint was given.
    """

    failed_checks: tuple[str, ...]
    visual_warnings: tuple[VisualRecord, ...]
    semantic_warnings: tuple[SemanticRecord, ...]


Progress: TypeAlias = Unrecorded | Checked | Warned | Assessed


@dataclass(frozen=True)
class Raised:
    """An exception the snippet (or validation) raised, as the child recorded it."""

    exc_type: str
    exc_msg: str


@dataclass(frozen=True)
class Diagnostics:
    """The lint issues and processed child logs every launched run reports."""

    lint: tuple[LintRecord, ...]
    stdout: str
    stderr: str


@dataclass(frozen=True)
class SourceRefused:
    """Source or timeout failed admission; nothing was linted or launched.

    ``hinted`` (here and in every variant) records that a chart hint was
    supplied, which alone decides whether the report has ``semantic_warnings``.
    """

    message: str
    hinted: bool


@dataclass(frozen=True)
class AnalysisExhausted:
    """Parsing or linting the source ran out of a handleable resource; not launched.

    ``exc_type`` is ``MemoryError`` or ``RecursionError``; no detail is kept.
    """

    exc_type: str
    hinted: bool


@dataclass(frozen=True)
class LintBlocked:
    """Critical lint issues stopped execution before launch.

    Construction rejects a lint list without a critical issue (ValueError).
    """

    lint: tuple[LintRecord, ...]
    hinted: bool

    def __post_init__(self) -> None:
        """Only critical issues block; a list without one is not this outcome."""
        if not any(issue.severity == "critical" for issue in self.lint):
            raise ValueError("LintBlocked requires a critical lint issue")


@dataclass(frozen=True)
class Passed:
    """The selected Figure was validated with every check completing.

    Construction rejects evidence that lists failed checks (ValueError).
    """

    evidence: Assessed
    diagnostics: Diagnostics
    hinted: bool

    def __post_init__(self) -> None:
        """A completed validation has no failed checks."""
        if self.evidence.failed_checks:
            raise ValueError("Passed requires no failed checks")


@dataclass(frozen=True)
class Incomplete:
    """The selected Figure was validated, but some checks failed to run.

    Construction rejects evidence without failed checks (ValueError).
    """

    evidence: Assessed
    diagnostics: Diagnostics
    hinted: bool

    def __post_init__(self) -> None:
        """Incomplete validation names at least one failed check."""
        if not self.evidence.failed_checks:
            raise ValueError("Incomplete requires a failed check")


@dataclass(frozen=True)
class NoFigure:
    """The snippet ran but neither the variable nor pyplot held a figure."""

    diagnostics: Diagnostics
    hinted: bool


@dataclass(frozen=True)
class ExecFailed:
    """The launched run failed: an exception, a nonzero exit, a stop before
    completion, a log overrun or an export failure.

    ``progress`` is the evidence acquired before the failure and ``raised``
    the recorded exception, if the child recorded one.
    """

    progress: Progress
    raised: Raised | None
    diagnostics: Diagnostics
    hinted: bool


@dataclass(frozen=True)
class TimedOut:
    """The child exceeded its deadline; ``progress``/``raised`` as for ExecFailed."""

    progress: Progress
    raised: Raised | None
    diagnostics: Diagnostics
    hinted: bool


ExecutionOutcome: TypeAlias = (
    SourceRefused
    | AnalysisExhausted
    | LintBlocked
    | Passed
    | Incomplete
    | NoFigure
    | ExecFailed
    | TimedOut
)


def to_wire(outcome: ExecutionOutcome) -> dict[str, Any]:
    """The legacy report for ``outcome``: a fresh dict with the exact legacy key order.

    Every report has ``status``, ``lint``, ``visual_warnings``, ``stdout``,
    ``stderr``, ``failed_checks`` and ``validation_complete`` (true only for
    ``Passed``); ``semantic_warnings`` exactly when ``hinted``.
    """
    match outcome:
        case SourceRefused(message, hinted):
            head: dict[str, Any] = {
                "status": "exec_error",
                "lint": [],
                "stderr": message,
            }
            return _unlaunched(head, hinted)
        case AnalysisExhausted(exc_type, hinted):
            head = {
                "status": "exec_error",
                "lint": [],
                "exc_type": exc_type,
                "stderr": _RESOURCE_MESSAGE,
            }
            return _unlaunched(head, hinted)
        case LintBlocked(lint, hinted):
            critical = [i.rule_id for i in lint if i.severity == "critical"]
            head = {
                "status": "lint_blocked",
                "lint": [_lint_wire(i) for i in lint],
                "visual_warnings": [],
                "stderr": (
                    "Critical lint issues must be fixed before execution: "
                    + ", ".join(critical)
                ),
            }
            return _unlaunched(head, hinted)
        case Passed(evidence, diagnostics, hinted):
            return _launched("ok", evidence, None, diagnostics, hinted)
        case Incomplete(evidence, diagnostics, hinted):
            return _launched(
                "validation_incomplete", evidence, None, diagnostics, hinted
            )
        case NoFigure(diagnostics, hinted):
            return _launched(
                "no_figure", Checked(()), None, diagnostics, hinted
            )
        case ExecFailed(progress, raised, diagnostics, hinted):
            return _launched(
                "exec_error", progress, raised, diagnostics, hinted
            )
        case TimedOut(progress, raised, diagnostics, hinted):
            return _launched("timeout", progress, raised, diagnostics, hinted)


def _unlaunched(head: dict[str, Any], hinted: bool) -> dict[str, Any]:
    """Complete a report of a run that never launched: no logs, no evidence."""
    head.setdefault("visual_warnings", [])
    head["stdout"] = ""
    head["failed_checks"] = []
    head["validation_complete"] = False
    if hinted:
        head["semantic_warnings"] = []
    return head


def _launched(
    status: str,
    progress: Progress,
    raised: Raised | None,
    diagnostics: Diagnostics,
    hinted: bool,
) -> dict[str, Any]:
    """Recorded evidence first (in checkpoint order), then logs, then defaults."""
    wire: dict[str, Any] = {"status": status}
    if not isinstance(progress, Unrecorded):
        wire["failed_checks"] = list(progress.failed_checks)
    if isinstance(progress, (Warned, Assessed)):
        wire["visual_warnings"] = [
            {
                "severity": w.severity,
                "check_id": w.check_id,
                "message": w.message,
                "detail": w.detail,
            }
            for w in progress.visual_warnings
        ]
    if isinstance(progress, Assessed) and hinted:
        wire["semantic_warnings"] = [
            {"check_id": s.check_id, "message": s.message}
            for s in progress.semantic_warnings
        ]
    if raised is not None:
        wire["exc_type"] = raised.exc_type
        wire["exc_msg"] = raised.exc_msg
    wire["lint"] = [_lint_wire(i) for i in diagnostics.lint]
    wire["stdout"] = diagnostics.stdout
    wire["stderr"] = diagnostics.stderr
    wire.setdefault("visual_warnings", [])
    wire.setdefault("failed_checks", [])
    wire["validation_complete"] = status == "ok"
    if hinted:
        wire.setdefault("semantic_warnings", [])
    return wire


def _lint_wire(issue: LintRecord) -> dict[str, Any]:
    """One lint record in the report's key order."""
    return {
        "rule_id": issue.rule_id,
        "severity": issue.severity,
        "line": issue.line,
        "message": issue.message,
        "fix_suggestion": issue.fix_suggestion,
    }
