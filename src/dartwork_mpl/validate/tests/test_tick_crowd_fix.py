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
    for fix in fixes:
        fig, ax = _y_names()
        _run(fix, fig, ax)


# ── names laid out by set_xticks(labels=) / set_xticklabels ─────────────────
# Matplotlib keeps them as a FixedLocator and a FuncFormatter mapping each
# position to its string: a locator from a fix keeps no name it does not
# map. Every fix run as written must keep the five names.


def _fixed_labels(how: str):
    """Country bars at 0..4 named by ``how``, before any layout."""
    dm.style.use("presentation")
    if how == "sharex":
        fig, (top, ax) = plt.subplots(
            2, 1, sharex=True, figsize=dm.figsize("11.4cm", "10.5cm")
        )
        top.plot(range(5), VALUES)
    else:
        fig, ax = plt.subplots(figsize=dm.figsize("11.4cm", "10.5cm"))
    ax.bar(range(5), VALUES)
    if how == "set_xticklabels":
        ax.set_xticks(range(5))
        ax.set_xticklabels(COUNTRIES)
    else:
        ax.set_xticks(range(5), labels=COUNTRIES)
    if how == "twin":
        ax.twinx().plot(range(5), VALUES[::-1], color="dc.red4")
    return fig, ax


def _named_x(fig) -> VisualWarning:
    found = [
        w
        for w in validate_figure(fig, checks=["TICK_CROWD"], quiet=True)
        if w.detail.get("axis") == "x"
    ]
    assert found  # precondition: the names crowd
    return found[0]


def _names_kept_after(fix: str, fig, ax) -> list[str]:
    """The non-empty x tick labels the (possibly new) axes draws after
    ``fix`` runs as written; a barh fix reads them along y."""
    namespace = _run(fix, fig, ax)
    fig, ax = namespace["fig"], namespace["ax"]
    fig.canvas.draw()
    labels = ax.get_xticklabels() if "barh" not in fix else ax.get_yticklabels()
    return [t.get_text() for t in labels if t.get_text()]


@pytest.mark.parametrize(
    "how", ["set_xticks", "set_xticklabels", "sharex", "twin"]
)
def test_fixed_tick_labels_are_names_and_keep_them(how: str) -> None:
    fig, ax = _fixed_labels(how)
    warning = _named_x(fig)
    assert warning.detail.get("label_kind") == "names"
    fixes = get_fix_suggestions(warning)
    assert "nbins" not in "\n".join(fixes)
    assert "rotation=45" not in "\n".join(fixes)
    for fix in fixes:
        fig, ax = _fixed_labels(how)
        assert _names_kept_after(fix, fig, ax) in ([], COUNTRIES)


def test_the_waterfall_template_s_names_are_names() -> None:
    """``waterfall`` names its steps with ``set_xticks(x, labels)``; on a
    narrow slide canvas, before its layout, they crowd."""
    from pathlib import Path

    source = (
        Path(dm.__file__).parent / "asset/prompt/05-templates/waterfall.py"
    ).read_text(encoding="utf-8")
    source = source[: source.index("dm.simple_layout(fig")]
    source = source.replace(
        'dm.style.use("scientific")', 'dm.style.use("presentation")'
    )
    namespace: dict = {}
    exec(compile(source, "waterfall", "exec"), namespace)
    fig, ax = namespace["fig"], namespace["ax"]
    fig.set_size_inches(dm.figsize("11.4cm", "10.5cm"))
    names = list(namespace["labels"])
    warning = _named_x(fig)
    assert warning.detail.get("label_kind") == "names"
    fixes = get_fix_suggestions(warning)
    assert "nbins" not in "\n".join(fixes)
    namespace["values"] = list(namespace["deltas"])
    kept = _names_kept_after(fixes[0], fig, ax)
    assert [n.replace("\n", " ") for n in kept] == names


def test_a_numeric_formatter_on_free_ticks_stays_numbers() -> None:
    """A FuncFormatter writing numbers the locator places: fewer ticks is
    still the fix."""
    from matplotlib.ticker import FuncFormatter, MultipleLocator

    fig, ax = plt.subplots(figsize=(2, 2))
    ax.plot(range(100))
    ax.xaxis.set_major_locator(MultipleLocator(2))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _pos: f"{x:,.0f}"))
    warning = _one(fig)
    assert warning.detail.get("label_kind") == "numbers"
    assert "nbins" in "\n".join(get_fix_suggestions(warning))


# ── horizontal bars keep each observation's row ─────────────────────────────


def test_the_barh_fix_keeps_repeated_names_on_their_own_rows() -> None:
    """Two bars named alike are still two observations: the fix places
    bars by position and names them, not by their names."""
    from matplotlib.ticker import FixedFormatter, FixedLocator

    dm.style.use("presentation")
    names = [
        "North region",
        "North region",
        "South region",
        "South region",
        "Central region",
    ]
    fig, ax = plt.subplots(figsize=dm.figsize("11.4cm", "10.5cm"))
    ax.bar(range(5), VALUES)
    ax.xaxis.set_major_locator(FixedLocator(range(5)))
    ax.xaxis.set_major_formatter(FixedFormatter(names))
    fixes = get_fix_suggestions(_named_x(fig))
    barh = next(f for f in fixes if "barh" in f)
    namespace = _run(barh, fig, ax)
    rows = {
        round(p.get_y() + p.get_height() / 2, 6)
        for p in namespace["ax"].patches
    }
    assert len(rows) == 5
    namespace["fig"].canvas.draw()
    drawn = [t.get_text() for t in namespace["ax"].get_yticklabels()]
    assert [t for t in drawn if t] == names


# ── canvas fixes never shrink the canvas ────────────────────────────────────


def test_the_height_fix_grows_a_tall_crowded_y_axis() -> None:
    """Sixty names on a 20 cm tall canvas: the fix makes it taller (the
    'tall' token gave 13.5 cm) and the names clear."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "20cm"))
    ax.barh([f"Region {k}" for k in range(60)], range(60))
    before = fig.get_figheight()
    warning = _one(fig, "y")
    _run(get_fix_suggestions(warning)[0], fig, ax)
    assert fig.get_figheight() > before
    assert fig.get_figwidth() == pytest.approx(9 / 2.54)
    assert _crowd(fig, "y") == []


def test_the_canvas_fix_never_narrows_a_wider_canvas() -> None:
    """Thirty names crowd a 30 cm canvas; the preset's widest is 23.4 cm.
    The fix keeps the 30 cm rather than shrink it."""
    dm.style.use("presentation")
    names = [f"Region number {k}" for k in range(30)]
    fig, ax = plt.subplots(figsize=dm.figsize("30cm", "10.5cm"))
    ax.bar(range(30), np.arange(30) + 1.0)
    ax.set_xticks(range(30), labels=names)
    before = tuple(fig.get_size_inches())
    canvas = get_fix_suggestions(_named_x(fig))[1]
    assert "figsize_for" in canvas
    _run(canvas, fig, ax)
    after = tuple(fig.get_size_inches())
    assert after[0] >= before[0] and after[1] >= before[1]
