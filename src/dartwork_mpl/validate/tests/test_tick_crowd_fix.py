"""TICK_CROWD's fixes for category names leave the turn to the layout.

For every crowded axis it suggested ``MaxNLocator(nbins=count // 2)`` and,
on x, ``tick_params(rotation=45)``. Under names (fixed strings, one per
position) a locator drops or misplaces them, and a hand turn overrides the
layout that wraps or turns only what would not clear; TICK_OVERLAP's fix
then says "drop your rotation" and TICK_ROTATION calls the turn unneeded.
Names now get the layout, a canvas sized for them, horizontal bars, then
fewer categories; numbers keep the locator.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.validate import validate_figure
from dartwork_mpl.validate._types import Severity, VisualWarning
from dartwork_mpl.validate.fixes import get_fix_suggestions

COUNTRIES = ["Norway", "Iceland", "Sweden", "China", "Germany"]
VALUES = [88.9, 71.0, 38.7, 25.0, 18.4]


@pytest.fixture(autouse=True)
def _own_rc():
    with matplotlib.rc_context():
        yield
    plt.close("all")


def _crowd(fig, axis: str) -> list[VisualWarning]:
    return [
        w
        for w in validate_figure(fig, checks=["TICK_CROWD"], quiet=True)
        if w.detail.get("axis") == axis
    ]


def _names_not_laid_out():
    """Country bars on a half-body slide canvas, before any layout: the
    names overlap flat."""
    dm.style.use("presentation")
    fig, ax = plt.subplots(figsize=dm.figsize("11.4cm", "10.5cm"))
    ax.bar(COUNTRIES, VALUES)
    return fig, ax


def _numbers():
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.plot(range(100))
    ax.set_xticks(range(0, 100, 2))
    return fig, ax


def _one(fig, axis: str = "x") -> VisualWarning:
    found = _crowd(fig, axis)
    assert len(found) == 1, found  # precondition
    return found[0]


def test_crowded_names_say_they_are_names() -> None:
    fig, _ax = _names_not_laid_out()
    assert _one(fig).detail.get("label_kind") == "names"


def test_crowded_numbers_say_they_are_numbers() -> None:
    fig, _ax = _numbers()
    assert _one(fig).detail.get("label_kind") == "numbers"


def test_fixes_for_names_leave_the_turn_to_the_layout() -> None:
    """The layout first (a turn of yours dropped), then a canvas sized for
    the names, horizontal bars, fewer categories; no locator, no turn."""
    fig, _ax = _names_not_laid_out()
    fixes = get_fix_suggestions(_one(fig))
    text = "\n".join(fixes)
    assert "rotation=45" not in text
    assert "nbins" not in text
    assert "set_major_locator" not in text
    assert "labelrotation=0" in fixes[0]
    assert "dm.simple_layout(fig)" in fixes[0]
    assert "labels=names" in fixes[1]
    assert "barh" in fixes[2]
    assert "Other" in fixes[3]


@pytest.mark.parametrize("axis", ["x", "y"])
def test_fixes_for_numbers_stay_as_they_were(axis: str) -> None:
    """Numbers keep fewer ticks (and, on x, the turn); so does a warning
    built by hand without the kind."""
    detail = {"axis": axis, "axes_index": 0, "count": 30, "occupancy": 1.4}
    old = get_fix_suggestions(
        VisualWarning(Severity.INFO, "TICK_CROWD", "crowded", detail)
    )
    numbers = get_fix_suggestions(
        VisualWarning(
            Severity.INFO,
            "TICK_CROWD",
            "crowded",
            {**detail, "label_kind": "numbers"},
        )
    )
    assert numbers == old
    assert f"{axis}axis.set_major_locator(plt.MaxNLocator(nbins=15))" in (
        "\n".join(numbers)
    )


def _run(fix: str, fig, ax) -> dict:
    """``fix`` run as it reads, ``fig`` and ``ax`` the warned figure, and
    ``values`` the bar heights the barh suggestion asks for."""
    namespace = {
        "fig": fig,
        "ax": ax,
        "dm": dm,
        "plt": plt,
        "np": np,
        "values": VALUES,
    }
    exec(compile(fix, "fix", "exec"), namespace)
    return namespace


def _drawn_names(fig, ax) -> list[str]:
    fig.canvas.draw()
    return [t.get_text() for t in ax.get_xticklabels() if t.get_text()]


def test_the_layout_fix_clears_the_names_and_keeps_them() -> None:
    """Run as written on the warned figure: no crowding, every name still
    under its bar (a locator would have dropped some)."""
    fig, ax = _names_not_laid_out()
    _run(get_fix_suggestions(_one(fig))[0], fig, ax)
    assert _crowd(fig, "x") == []
    assert _drawn_names(fig, ax) == COUNTRIES


def test_the_canvas_fix_takes_the_width_the_names_stand_flat_at() -> None:
    """The slide width at which the five names stand flat (23.4 cm), laid
    out again: flat, all there, not crowded."""
    fig, ax = _names_not_laid_out()
    _run(get_fix_suggestions(_one(fig))[1], fig, ax)
    assert round(fig.get_figwidth() * 2.54, 1) == 23.4
    assert _drawn_names(fig, ax) == COUNTRIES
    assert {t.get_rotation() for t in ax.get_xticklabels()} == {0.0}
    assert _crowd(fig, "x") == []


def test_every_fix_for_names_runs_as_written() -> None:
    fig, ax = _names_not_laid_out()
    for fix in get_fix_suggestions(_one(fig)):
        fig, ax = _names_not_laid_out()
        _run(fix, fig, ax)


def _y_names():
    """Twenty-four region names stacked on a short y axis."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "4cm"))
    names = [f"Region {k}" for k in range(24)]
    ax.barh(names, np.arange(24) + 1.0)
    return fig, ax


def test_fixes_for_y_names_take_height_not_a_locator() -> None:
    fig, ax = _y_names()
    warning = _one(fig, "y")
    assert warning.detail.get("label_kind") == "names"
    fixes = get_fix_suggestions(warning)
    assert "nbins" not in "\n".join(fixes)
    assert "'tall'" in fixes[0]
    for fix in fixes:
        fig, ax = _y_names()
        _run(fix, fig, ax)
