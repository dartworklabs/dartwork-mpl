"""Internal validate representations: check outcomes, typed details, readers."""

from __future__ import annotations

import dataclasses

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity, VisualWarning
from dartwork_mpl.validate._checks import RegisteredCheck
from dartwork_mpl.validate._checks._detail import AXES, SIDES, choice, number
from dartwork_mpl.validate._checks.text_contrast import _ContrastGroup
from dartwork_mpl.validate._orchestrator import (
    CheckCompleted,
    CheckFailed,
    _outcome_warnings,
    _run_check_safely,
)
from dartwork_mpl.validate.fixes import get_fix_suggestions


class TestCheckOutcome:
    """A check run is either completed (maybe clean) or failed, never None."""

    def test_completed_keeps_warnings_even_when_empty(self) -> None:
        """A clean run is CheckCompleted([]), distinct from a failure."""
        check = RegisteredCheck("CLEAN", 0, lambda fig, renderer: [])
        outcome = _run_check_safely(check, None, None)
        assert outcome == CheckCompleted([])
        assert _outcome_warnings(outcome) == []

    def test_failed_becomes_the_check_failed_wire_warning(self) -> None:
        """CheckFailed renders as the unchanged CHECK_FAILED warning."""
        [warning] = _outcome_warnings(CheckFailed("OVERFLOW"))
        assert warning == VisualWarning(
            Severity.WARNING,
            "CHECK_FAILED",
            "Check OVERFLOW could not run; validation is incomplete.",
            {"check_id": "OVERFLOW"},
        )


class TestDetailReaders:
    """Readers return the typed value, or the default for absent/ill-typed keys."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [({"px": 3}, 3), ({"px": 2.5}, 2.5), ({"px": "3"}, 0), ({}, 0)],
    )
    def test_number(self, raw, expected) -> None:
        """Numbers pass through unchanged; others fall back to the default."""
        value = number(raw, "px", 0)
        assert value == expected and type(value) is type(expected)

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [({"side": "top"}, "top"), ({"side": "z"}, None), ({}, None)],
    )
    def test_choice(self, raw, expected) -> None:
        """Only a listed option is read; anything else is no choice."""
        assert choice(raw, "side", SIDES) == expected

    def test_axis_choices(self) -> None:
        """Tick checks report only the x or y axis."""
        assert AXES == ("x", "y")


def _fixes(check_id: str, detail: dict) -> list[str]:
    return get_fix_suggestions(
        VisualWarning(Severity.WARNING, check_id, "m", detail)
    )


class TestFixHandlersReadTypedDetails:
    """Handlers keep their documented defaults for hand-built details."""

    def test_overflow_tick_variant_has_no_edge_suggestion(self) -> None:
        """The tick-label OVERFLOW variant carries no side, so no suggestion."""
        assert _fixes("OVERFLOW", {"text": "1", "px": 9.0}) == []

    def test_overflow_side_without_px_uses_zero(self) -> None:
        """A missing px reads as 0."""
        assert "left=0.15" in _fixes("OVERFLOW", {"side": "left"})[0]

    def test_defaults_for_missing_keys(self) -> None:
        """Each handler's default when its key is absent."""
        assert "ax.yaxis" in _fixes("TICK_DECIMAL", {})[0]
        assert "{x:.0f}" in _fixes("TICK_DECIMAL", {})[0]
        assert "ax.yaxis" in _fixes("UNIT_DUP", {})[0]
        assert "pctdistance=0.70" in _fixes("PIE_LABEL_OFFSET", {})[0]
        assert "rotation=45" in _fixes("TICK_ROTATION", {})[0]
        assert "nbins=0" in _fixes("TICK_CROWD", {})[0]
        assert "vertically" in _fixes("MARGIN_ASYMMETRY", {})[0]

    def test_values_are_formatted_as_given(self) -> None:
        """Present values keep their type in the suggestion text."""
        assert (
            "rotation=0)"
            in _fixes("TICK_ROTATION", {"recommended_rotation": 0})[0]
        )
        assert (
            "{x:.2f}"
            in _fixes("TICK_DECIMAL", {"axis": "x", "recommended_decimals": 2})[
                0
            ]
        )
        assert "nbins=15" in _fixes("TICK_CROWD", {"axis": "x", "count": 30})[0]


class TestContrastGroup:
    """Contrast groups are values; adding a sample returns a new group."""

    def test_with_sample_counts_and_caps_samples(self) -> None:
        """Count grows on every sample; samples stop at the cap."""
        group = _ContrastGroup(Severity.INFO, 4.0, 4.5, "#111", "#222", False)
        for index in range(10):
            group = group.with_sample(f"s{index}")
        assert group.count == 10
        assert group.samples == ("s0", "s1", "s2")

    def test_group_is_frozen(self) -> None:
        """A group cannot be mutated in place."""
        group = _ContrastGroup(Severity.INFO, 4.0, 4.5, "#111", "#222", False)
        with pytest.raises(dataclasses.FrozenInstanceError):
            group.count = 1  # type: ignore[misc]


def test_check_details_are_plain_dicts() -> None:
    """Checks still hand callers plain ``dict`` details with the old keys."""
    fig, ax = plt.subplots(figsize=dm.figsize("6cm", "standard"))
    try:
        ax.set_ylabel("a very long label " * 8)
        fig.text(1.2, 0.5, "off canvas")
        warnings = dm.validate_figure(fig, quiet=True)
        overflow = [w for w in warnings if w.check_id == "OVERFLOW"]
        assert overflow
        for warning in overflow:
            assert type(warning.detail) is dict
            assert set(warning.detail) in (
                {"text", "side", "px"},
                {"text", "px"},
            )
    finally:
        plt.close(fig)
