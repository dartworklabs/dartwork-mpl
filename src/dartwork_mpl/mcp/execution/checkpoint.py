"""The child runner's private checkpoint: parsed once, then settled into an outcome.

The runner in this package rewrites one JSON object as it progresses
(``status``, ``failed_checks``, ``visual_warnings``, ``semantic_warnings``,
``exc_type``/``exc_msg`` and the private ``_export_failed`` marker).
``parse_checkpoint`` turns that object into a ``Checkpoint``; anything outside
the protocol (unreadable, damaged or rewritten by the snippet) parses as a run
that recorded nothing. ``settle`` combines a checkpoint with the reaped
process's facts into the run's ``ExecutionOutcome``. Both are pure.
"""

from dataclasses import dataclass
from typing import Any, TypeAlias

from .outcome import (
    Assessed,
    Checked,
    Diagnostics,
    ExecFailed,
    ExecutionOutcome,
    Incomplete,
    NoFigure,
    Passed,
    Progress,
    Raised,
    SemanticRecord,
    TimedOut,
    Unrecorded,
    VisualRecord,
    Warned,
)

__all__ = [
    "Checkpoint",
    "ChildExportFailed",
    "ChildFoundNoFigure",
    "ChildStopped",
    "ChildValidated",
    "parse_checkpoint",
    "settle",
]


@dataclass(frozen=True)
class ChildValidated:
    """The child validated the Figure (and, when exporting, saved it)."""

    evidence: Assessed


@dataclass(frozen=True)
class ChildFoundNoFigure:
    """The child ran the snippet and found no figure to validate."""


@dataclass(frozen=True)
class ChildExportFailed:
    """The child validated the Figure but saving it raised."""

    evidence: Assessed


@dataclass(frozen=True)
class ChildStopped:
    """The child stopped before concluding: mid-run, or after a recorded exception."""

    progress: Progress
    raised: Raised | None


Checkpoint: TypeAlias = (
    ChildValidated | ChildFoundNoFigure | ChildExportFailed | ChildStopped
)

_NOTHING = ChildStopped(Unrecorded(), None)
_KEYS = frozenset(
    {
        "status",
        "failed_checks",
        "visual_warnings",
        "semantic_warnings",
        "_export_failed",
        "exc_type",
        "exc_msg",
    }
)


def parse_checkpoint(raw: object) -> Checkpoint:
    """Parse the decoded checkpoint JSON; off-protocol input is ``ChildStopped(Unrecorded())``."""
    if not isinstance(raw, dict) or not raw.keys() <= _KEYS:
        return _NOTHING
    status = raw.get("status")
    progress = _progress(raw)
    raised = _raised(raw)
    if progress is None or isinstance(raised, _Malformed):
        return _NOTHING
    export_failed = raw.get("_export_failed", False)
    if export_failed is not False:
        if (
            export_failed is True
            and status == "exec_error"
            and isinstance(progress, Assessed)
            and raised is None
        ):
            return ChildExportFailed(progress)
        return _NOTHING
    if status == "exec_error":
        return ChildStopped(progress, raised)
    if raised is not None:
        return _NOTHING
    if status == "no_figure" and progress == Checked(()):
        return ChildFoundNoFigure()
    if isinstance(progress, Assessed) and status == (
        "validation_incomplete" if progress.failed_checks else "ok"
    ):
        return ChildValidated(progress)
    return _NOTHING


def settle(
    checkpoint: Checkpoint,
    diagnostics: Diagnostics,
    hinted: bool,
    *,
    timed_out: bool,
    exited_cleanly: bool,
) -> ExecutionOutcome:
    """The outcome of a reaped child.

    A deadline overrun is ``TimedOut`` and an unclean exit ``ExecFailed``,
    both keeping the recorded evidence; otherwise the checkpoint decides. An
    export failure is ``ExecFailed`` here; callers that export answer it.
    """
    match checkpoint:
        case ChildValidated(evidence) | ChildExportFailed(evidence):
            progress: Progress = evidence
            raised = None
        case ChildFoundNoFigure():
            progress, raised = Checked(()), None
        case ChildStopped(progress, raised):
            pass
    if timed_out:
        return TimedOut(progress, raised, diagnostics, hinted)
    if not exited_cleanly or isinstance(checkpoint, ChildExportFailed):
        return ExecFailed(progress, raised, diagnostics, hinted)
    match checkpoint:
        case ChildValidated(evidence) if evidence.failed_checks:
            return Incomplete(evidence, diagnostics, hinted)
        case ChildValidated(evidence):
            return Passed(evidence, diagnostics, hinted)
        case ChildFoundNoFigure():
            return NoFigure(diagnostics, hinted)
        case _:
            return ExecFailed(progress, raised, diagnostics, hinted)


def _progress(raw: dict[str, Any]) -> Progress | None:
    """The recorded evidence; None when a field is malformed or out of order."""
    has = [key in raw for key in _EVIDENCE]
    if has != sorted(has, reverse=True):
        return None  # a later stage without an earlier one
    if not has[0]:
        return Unrecorded()
    checks = raw["failed_checks"]
    if not isinstance(checks, list) or not all(
        isinstance(c, str) for c in checks
    ):
        return None
    failed = tuple(checks)
    if not has[1]:
        return Checked(failed)
    visual = _visual(raw["visual_warnings"])
    if visual is None:
        return None
    if not has[2]:
        return Warned(failed, visual)
    semantic = _semantic(raw["semantic_warnings"])
    if semantic is None:
        return None
    return Assessed(failed, visual, semantic)


_EVIDENCE = ("failed_checks", "visual_warnings", "semantic_warnings")


def _visual(raw: object) -> tuple[VisualRecord, ...] | None:
    """Visual warning records, or None when any record is off-protocol."""
    if not isinstance(raw, list):
        return None
    records = []
    for item in raw:
        if not isinstance(item, dict) or list(item) != [
            "severity",
            "check_id",
            "message",
            "detail",
        ]:
            return None
        severity, check_id, message, detail = item.values()
        if not (
            isinstance(severity, str)
            and isinstance(check_id, str)
            and isinstance(message, str)
            and isinstance(detail, dict)
        ):
            return None
        records.append(VisualRecord(severity, check_id, message, detail))
    return tuple(records)


def _semantic(raw: object) -> tuple[SemanticRecord, ...] | None:
    """Semantic warning records, or None when any record is off-protocol."""
    if not isinstance(raw, list):
        return None
    records = []
    for item in raw:
        if not isinstance(item, dict) or list(item) != ["check_id", "message"]:
            return None
        check_id, message = item.values()
        if not (isinstance(check_id, str) and isinstance(message, str)):
            return None
        records.append(SemanticRecord(check_id, message))
    return tuple(records)


@dataclass(frozen=True)
class _Malformed:
    """A checkpoint field outside the protocol."""


def _raised(raw: dict[str, Any]) -> Raised | None | _Malformed:
    """The recorded exception: both fields as strings, or neither."""
    if "exc_type" not in raw and "exc_msg" not in raw:
        return None
    exc_type, exc_msg = raw.get("exc_type"), raw.get("exc_msg")
    if isinstance(exc_type, str) and isinstance(exc_msg, str):
        return Raised(exc_type, exc_msg)
    return _Malformed()
