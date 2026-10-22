"""Execution outcomes: their invariants, the checkpoint parse, settling and the legacy wire."""

import json

import pytest

from dartwork_mpl.mcp.execution.checkpoint import (
    ChildExportFailed,
    ChildFoundNoFigure,
    ChildStopped,
    ChildValidated,
    parse_checkpoint,
    settle,
)
from dartwork_mpl.mcp.execution.outcome import (
    AnalysisExhausted,
    Assessed,
    Checked,
    Diagnostics,
    ExecFailed,
    Incomplete,
    LintBlocked,
    LintRecord,
    NoFigure,
    Passed,
    Raised,
    SemanticRecord,
    SourceRefused,
    TimedOut,
    Unrecorded,
    VisualRecord,
    Warned,
    to_wire,
)

WARNING = LintRecord("DM101", "warning", 3, "use dm.fs", None)
CRITICAL = LintRecord("DM001", "critical", 1, "no tight_layout", "fix")
LOGS = Diagnostics((WARNING,), "out\n", "err")
VISUAL = VisualRecord("WARNING", "OVERFLOW", "text overflows", {"k": 1})
SEMANTIC = SemanticRecord("line_no_lines", "no lines")
CLEAN = Assessed((), (VISUAL,), (SEMANTIC,))
FAILED = Assessed(("ORIGINAL_FAILURE",), (), ())


def keys(outcome):
    """The report's keys in wire order."""
    return list(to_wire(outcome))


def test_lint_blocked_requires_a_critical_issue():
    """A lint list without a critical issue cannot be a blocked run."""
    with pytest.raises(ValueError, match="critical"):
        LintBlocked((WARNING,), hinted=False)


def test_passed_and_incomplete_split_on_failed_checks():
    """Passed has no failed check and Incomplete has at least one."""
    with pytest.raises(ValueError, match="no failed checks"):
        Passed(FAILED, LOGS, hinted=False)
    with pytest.raises(ValueError, match="failed check"):
        Incomplete(CLEAN, LOGS, hinted=False)


def test_unlaunched_reports_keep_their_legacy_shape():
    """Admission, analysis and lint refusals report no logs and no evidence."""
    assert to_wire(SourceRefused("code: too big", hinted=True)) == {
        "status": "exec_error",
        "lint": [],
        "stderr": "code: too big",
        "visual_warnings": [],
        "stdout": "",
        "failed_checks": [],
        "validation_complete": False,
        "semantic_warnings": [],
    }
    assert keys(AnalysisExhausted("RecursionError", hinted=False)) == [
        "status",
        "lint",
        "exc_type",
        "stderr",
        "visual_warnings",
        "stdout",
        "failed_checks",
        "validation_complete",
    ]
    blocked = to_wire(LintBlocked((WARNING, CRITICAL), hinted=False))
    assert blocked["status"] == "lint_blocked"
    assert blocked["stderr"] == (
        "Critical lint issues must be fixed before execution: DM001"
    )
    assert list(blocked) == [
        "status",
        "lint",
        "visual_warnings",
        "stderr",
        "stdout",
        "failed_checks",
        "validation_complete",
    ]


def test_launched_reports_list_evidence_before_logs():
    """Checkpoint evidence keeps its order; semantic warnings appear only when hinted."""
    assert keys(Passed(CLEAN, LOGS, hinted=True)) == [
        "status",
        "failed_checks",
        "visual_warnings",
        "semantic_warnings",
        "lint",
        "stdout",
        "stderr",
        "validation_complete",
    ]
    assert "semantic_warnings" not in to_wire(Passed(CLEAN, LOGS, hinted=False))
    stopped = to_wire(
        ExecFailed(Checked(("X",)), Raised("ValueError", "boom"), LOGS, True)
    )
    assert list(stopped) == [
        "status",
        "failed_checks",
        "exc_type",
        "exc_msg",
        "lint",
        "stdout",
        "stderr",
        "visual_warnings",
        "validation_complete",
        "semantic_warnings",
    ]
    assert to_wire(TimedOut(Unrecorded(), None, LOGS, False))["status"] == (
        "timeout"
    )
    assert to_wire(Incomplete(FAILED, LOGS, False))["validation_complete"] is (
        False
    )
    assert to_wire(NoFigure(LOGS, False))["status"] == "no_figure"


def test_checkpoint_parses_each_protocol_stage():
    """Each stage the child writes parses to the evidence recorded so far."""
    checked = {"status": "exec_error", "failed_checks": ["A"]}
    assert parse_checkpoint(checked) == ChildStopped(Checked(("A",)), None)
    warned = {
        **checked,
        "visual_warnings": [
            {
                "severity": "WARNING",
                "check_id": "C",
                "message": "m",
                "detail": {},
            }
        ],
    }
    assert parse_checkpoint(warned) == ChildStopped(
        Warned(("A",), (VisualRecord("WARNING", "C", "m", {}),)), None
    )
    done = {
        **warned,
        "semantic_warnings": [],
        "status": "validation_incomplete",
    }
    assert isinstance(parse_checkpoint(done), ChildValidated)
    raised = {**checked, "exc_type": "KeyError", "exc_msg": "'x'"}
    assert parse_checkpoint(raised) == ChildStopped(
        Checked(("A",)), Raised("KeyError", "'x'")
    )
    assert parse_checkpoint({"status": "no_figure", "failed_checks": []}) == (
        ChildFoundNoFigure()
    )
    exported = {**done, "status": "exec_error", "_export_failed": True}
    assert isinstance(parse_checkpoint(exported), ChildExportFailed)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        [],
        {"status": "exec_error"},
        {"status": "ok", "failed_checks": []},
        {"status": "exec_error", "failed_checks": [1]},
        {"status": "exec_error", "failed_checks": [], "extra": 1},
        {"status": "exec_error", "failed_checks": [], "semantic_warnings": []},
        {"status": "exec_error", "failed_checks": [], "exc_type": "E"},
        {"status": "no_figure", "failed_checks": ["A"]},
        {"status": "exec_error", "failed_checks": [], "_export_failed": True},
    ],
)
def test_off_protocol_checkpoints_record_nothing(raw):
    """Anything the runner never writes parses as a run that recorded nothing."""
    assert parse_checkpoint(json.loads(json.dumps(raw))) == ChildStopped(
        Unrecorded(), None
    )


def test_settle_lets_the_process_overrule_the_checkpoint():
    """A timeout or unclean exit keeps the evidence; a clean exit trusts the child."""
    validated = ChildValidated(CLEAN)
    assert settle(
        validated, LOGS, False, timed_out=True, exited_cleanly=False
    ) == TimedOut(CLEAN, None, LOGS, False)
    assert settle(
        validated, LOGS, False, timed_out=False, exited_cleanly=False
    ) == ExecFailed(CLEAN, None, LOGS, False)
    assert settle(
        validated, LOGS, False, timed_out=False, exited_cleanly=True
    ) == Passed(CLEAN, LOGS, False)
    assert settle(
        ChildValidated(FAILED), LOGS, True, timed_out=False, exited_cleanly=True
    ) == Incomplete(FAILED, LOGS, True)
    assert settle(
        ChildExportFailed(CLEAN),
        LOGS,
        False,
        timed_out=False,
        exited_cleanly=True,
    ) == ExecFailed(CLEAN, None, LOGS, False)
    assert settle(
        ChildFoundNoFigure(), LOGS, False, timed_out=False, exited_cleanly=True
    ) == NoFigure(LOGS, False)
