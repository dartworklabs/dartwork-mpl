"""The decider for ``dm.axis_unit`` label sync: invariants over combinations.

Review rounds on how the unit formatter keeps axis labels in step kept
finding one more case, so the controller ended them with this mechanical
check (2026-11-05, CLAUDE.md rule 2). It walks template shapes x ladders x
grids x operation sequences and, after every step (and a draw), asserts on
every label of the group of axes sharing the formatted axis:

(i)   a non-empty label shows exactly one unit token beyond the user's own
      text, and it is the current tick unit (never stale, never doubled);
(ii)  when the ticks are scaled, at least one visible label carries it;
(iii) the user's text outside the unit token is kept verbatim (modulo the
      line breaks ``dm.wrap_axis_labels`` puts in);
(iv)  an emptied label stays empty unless it is the only place left to show
      the unit (ii): then the unit goes to an outer visible label.

User texts hold no ladder symbol of their own (만억조경, k M B G T), so a
unit token is a ladder symbol found in a label and not in the user's text.
Every template shape meets every operation at least once.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.figure import Figure

matplotlib.use("Agg")

import dartwork_mpl as dm

SYMBOLS = {
    "myriad": ("만", "억", "조", "경"),
    "finance": ("k", "M", "B", "T"),
    "si": ("k", "M", "G", "T"),
}


@dataclass(frozen=True)
class Shape:
    """A template shape: where ``{unit}`` sits and the texts around it."""

    name: str
    ladder: str
    template: str | None  # None: label=None (the installer appends)
    first: str  # the installer's label before the call
    sibling: str  # a sharing axes' own label
    edit: str  # an edit the user types with the unit they see
    plain: str  # an edit without the unit token
    top: float  # data maximum
    zoom: float  # a limit one rung or more up


SHAPES = [
    Shape(
        "trailing-myriad",
        "myriad",
        "매출 ({unit}원)",
        "매출 (원)",
        "비용 (원)",
        "영업비용 ({unit}원)",
        "영업비용",
        6e11,
        6e12,
    ),
    Shape(
        "trailing-finance",
        "finance",
        "Revenue (USD {unit})",
        "Revenue (USD)",
        "Cost (USD)",
        "Cost (USD {unit})",
        "Cost",
        6e10,
        6e13,
    ),
    Shape(
        "brackets-si",
        "si",
        "Power [{unit}W]",
        "Power [W]",
        "Loss [W]",
        "Output power [{unit}W]",
        "Output power",
        6e4,
        6e7,
    ),
    Shape(
        "slash-si",
        "si",
        "Power / {unit}W",
        "Power / W",
        "Loss / W",
        "Output power / {unit}W",
        "Output power",
        6e4,
        6e7,
    ),
    Shape(
        "mid-text-si",
        "si",
        "Power ({unit}W), net",
        "Power (W), net",
        "Loss (W), net",
        "Output power ({unit}W), net",
        "Output power",
        6e4,
        6e7,
    ),
    Shape(
        "multi-line-si",
        "si",
        "Power output of\nthe plant ({unit}W)",
        "Power output of\nthe plant (W)",
        "Losses of\nthe plant (W)",
        "Output of\nthe plant ({unit}W)",
        "Output of the plant",
        6e4,
        6e7,
    ),
    Shape(
        "long-wrapped-si",
        "si",
        "Sum of quarterly electrical output power [{unit}W]",
        "Sum of quarterly electrical output power [W]",
        "Sum of quarterly electrical losses [W]",
        "Sum of quarterly electrical output, revised [{unit}W]",
        "Sum of quarterly electrical output, revised",
        6e4,
        6e7,
    ),
    Shape(
        "label-none-myriad",
        "myriad",
        None,
        "매출 (원)",
        "비용 (원)",
        "영업비용 (원) ({unit})",
        "영업비용",
        6e11,
        6e12,
    ),
    Shape(
        "label-none-finance",
        "finance",
        None,
        "Revenue",
        "Cost",
        "Cost ({unit})",
        "Cost",
        6e10,
        6e13,
    ),
]


def _tidy(text: str) -> str:
    """Whitespace runs to one space; no spaces inside bracket edges; no ()."""
    text = re.sub(r"([(\[])\s+", r"\1", text)
    text = re.sub(r"\s+([)\]])", r"\1", text)
    text = re.sub(r"\s*\(\)", "", text)
    return " ".join(text.split())


@dataclass
class State:
    """One scenario: the figure, its axes and what the user wrote where."""

    shape: Shape
    fig: Figure
    axes: list[Axes]
    which: str
    installer: Axes
    sibling: Axes | None
    user: dict[Axis, str] = field(default_factory=dict)
    seen: set[str] = field(default_factory=set)
    zoomed: bool = False

    def axis(self, ax: Axes) -> Axis:
        return ax.xaxis if self.which == "x" else ax.yaxis

    def group(self) -> list[Axis]:
        own = self.axis(self.installer)
        return [
            self.axis(a) for a in self.axes if self.axis(a).major is own.major
        ]

    def set_label(self, ax: Axes, text: str) -> None:
        if self.which == "x":
            ax.set_xlabel(text)
        else:
            ax.set_ylabel(text)

    def own_text(self, ax: Axes, text: str) -> None:
        self.user[self.axis(ax)] = _tidy(text)
        if text.strip():
            self.seen.add(_tidy(text))

    def unit(self) -> str:
        unit = dm.axis_unit_of(self.installer, self.which)
        assert unit is not None
        return unit.label


# ---------------------------------------------------------------- grids


def _single(shape: Shape) -> tuple[Figure, list[Axes], str, int, int | None]:
    fig, ax = plt.subplots(figsize=dm.figsize("6cm", "standard"))
    return fig, [ax], "y", 0, None


def _sharey_stacked(shape):
    fig, axes = plt.subplots(
        2, 1, sharey=True, figsize=dm.figsize("6cm", "square")
    )
    return fig, list(axes), "y", 0, 1


def _sharey_row_outer(shape):  # label_outer at creation: right is inner
    fig, axes = plt.subplots(1, 2, sharey=True, figsize=dm.figsize("9cm"))
    return fig, list(axes), "y", 0, 1


def _sharey_row_inner(shape):  # the installer is the inner (right) panel
    fig, axes = plt.subplots(1, 2, sharey=True, figsize=dm.figsize("9cm"))
    return fig, list(axes), "y", 1, 0


def _row_no_label_outer(shape):  # both show ticks until label_outer runs
    fig = plt.figure(figsize=dm.figsize("9cm"))
    left = fig.add_subplot(1, 2, 1)
    right = fig.add_subplot(1, 2, 2, sharey=left)
    return fig, [left, right], "y", 1, 0


def _sharex_row(shape):
    fig, axes = plt.subplots(1, 2, sharex=True, figsize=dm.figsize("9cm"))
    return fig, list(axes), "x", 0, 1


GRIDS: dict[
    str, Callable[..., tuple[Figure, list[Axes], str, int, int | None]]
] = {
    "single": _single,
    "sharey-stacked": _sharey_stacked,
    "sharey-row-outer": _sharey_row_outer,
    "sharey-row-inner": _sharey_row_inner,
    "row-no-label-outer": _row_no_label_outer,
    "sharex-row": _sharex_row,
}
# Grids whose installer starts without a label of its own.
UNLABELLED_INSTALLER = {"sharey-row-inner"}


def _build(shape: Shape, grid: str) -> State:
    dm.style.use("report-kr" if shape.ladder == "myriad" else "report")
    fig, axes, which, at, other = GRIDS[grid](shape)
    values = np.array([0.3, 0.6, 1.0]) * shape.top
    for ax in axes:
        if which == "x":
            ax.plot(values, range(3))
        else:
            ax.bar(range(3), values)
    state = State(
        shape,
        fig,
        axes,
        which,
        axes[at],
        None if other is None else axes[other],
    )
    for ax in axes:
        state.own_text(ax, state.axis(ax).label.get_text())
    if grid not in UNLABELLED_INSTALLER or shape.template is None:
        state.set_label(state.installer, shape.first)
    if state.sibling is not None and grid in ("sharey-stacked", "sharex-row"):
        state.set_label(state.sibling, shape.sibling)
        state.own_text(state.sibling, shape.sibling)
    ladder = "auto" if shape.ladder == "myriad" else shape.ladder
    dm.axis_unit(state.installer, which, label=shape.template, ladder=ladder)  # type: ignore[arg-type]
    if shape.template is not None:
        state.own_text(state.installer, shape.template.replace("{unit}", ""))
    else:
        state.own_text(
            state.installer, state.axis(state.installer).label.get_text()
        )
    return state


# ---------------------------------------------------------------- operations


def _layout(s: State, _target: str) -> None:
    dm.simple_layout(s.fig)


def _draw(s: State, _target: str) -> None:
    s.fig.canvas.draw()


def _zoom(s: State, _target: str) -> None:
    s.zoomed = not s.zoomed
    top = s.shape.zoom if s.zoomed else s.shape.top * 1.05
    if s.which == "x":
        s.installer.set_xlim(0, top)
    else:
        s.installer.set_ylim(0, top)


def _target_axes(s: State, target: str) -> Axes:
    return (
        s.sibling
        if target == "sibling" and s.sibling is not None
        else s.installer
    )


def _edit_unit(s: State, target: str) -> None:
    s.fig.canvas.draw()
    ax = _target_axes(s, target)
    s.set_label(ax, s.shape.edit.replace("{unit}", s.unit()))
    s.own_text(ax, s.shape.edit.replace("{unit}", ""))


def _edit_plain(s: State, target: str) -> None:
    ax = _target_axes(s, target)
    s.set_label(ax, s.shape.plain)
    s.own_text(ax, s.shape.plain)


def _empty(s: State, target: str) -> None:
    ax = _target_axes(s, target)
    s.set_label(ax, "")
    s.own_text(ax, "")


def _wrap(s: State, _target: str) -> None:
    s.fig.canvas.draw()
    dm.wrap_axis_labels(s.fig)


def _label_outer(s: State, _target: str) -> None:
    s.fig.canvas.draw()
    before = {s.axis(a): s.axis(a).label.get_text() for a in s.axes}
    for ax in s.axes:
        ax.label_outer()
    for ax in s.axes:
        axis = s.axis(ax)
        if before[axis] and not axis.label.get_text():
            s.own_text(ax, "")  # label_outer emptied it


OPS: dict[str, Callable[[State, str], None]] = {
    "layout": _layout,
    "draw": _draw,
    "zoom": _zoom,
    "edit-unit": _edit_unit,
    "edit-plain": _edit_plain,
    "empty": _empty,
    "wrap": _wrap,
    "relayout": _layout,
    "label-outer": _label_outer,
}
SEQUENCES = [
    ("layout", "zoom", "edit-unit:installer", "zoom", "relayout"),
    ("layout", "edit-plain:sibling", "zoom", "wrap", "zoom", "relayout"),
    (
        "layout",
        "empty:installer",
        "zoom",
        "relayout",
        "edit-plain:installer",
        "draw",
    ),
    ("layout", "label-outer", "relayout", "zoom", "edit-unit:sibling", "draw"),
    (
        "layout",
        "wrap",
        "edit-unit:installer",
        "zoom",
        "empty:sibling",
        "relayout",
    ),
]


# ---------------------------------------------------------------- invariants


def _shows_ticks(axis: Axis) -> bool:
    side = axis.get_label_position()
    return axis.get_visible() and bool(
        axis.get_tick_params(which="major").get(f"label{side}", True)
    )


def _tokens(text: str, symbols: tuple[str, ...]) -> Counter[str]:
    return Counter(ch for ch in text if ch in symbols)


def _check(s: State, step: str) -> None:
    s.fig.canvas.draw()
    unit = s.unit()
    symbols = SYMBOLS[s.shape.ladder]
    group = s.group()
    texts = {axis: axis.label.get_text() for axis in group}
    where = f"after {step}: {[texts[a] for a in group]!r}, unit {unit!r}"

    def carries(axis: Axis) -> bool:
        return bool(unit) and _tokens(texts[axis], symbols)[unit] == 1

    for axis in group:
        text = texts[axis]
        if not text:
            continue
        user = s.user.get(axis, "")
        extra = _tokens(text, symbols) - _tokens(user, symbols)
        # (i) one unit token, the current one; nothing doubled or stale
        assert extra == (Counter({unit: 1}) if unit else Counter()), where
        assert not (_tokens(user, symbols) - _tokens(text, symbols)), where
        stripped = _tidy(text.replace(unit, "", 1) if unit else text)
        if user:
            # (iii) the user's text outside the unit token, verbatim
            assert stripped == user, f"{where}: {stripped!r} != {user!r}"
        else:
            # (iv) an emptied (or never set) label gets text only as the
            # last place for the unit, with text from the group or none
            others = [a for a in group if a is not axis and carries(a)]
            assert unit and not others, where
            assert _shows_ticks(axis), where
            assert stripped in s.seen | {""}, f"{where}: {stripped!r}"
    if unit:
        # (ii) scaled ticks: some visible label carries the unit
        assert any(
            carries(a) and a.get_visible() and a.label.get_visible()
            for a in group
        ), where


def _cases() -> list[tuple[str, str, int]]:
    cases = []
    for i, shape in enumerate(SHAPES):
        for j, grid in enumerate(GRIDS):
            cases.append((shape.name, grid, (i + j) % len(SEQUENCES)))
    return cases


@pytest.fixture(autouse=True)
def _restore_rc():
    with matplotlib.rc_context():
        yield
    plt.close("all")


@pytest.mark.parametrize(("shape_name", "grid", "sequence"), _cases())
def test_label_sync_invariants(
    shape_name: str, grid: str, sequence: int
) -> None:
    shape = next(s for s in SHAPES if s.name == shape_name)
    state = _build(shape, grid)
    _check(state, "install")
    for step in SEQUENCES[sequence]:
        name, _, target = step.partition(":")
        OPS[name](state, target or "installer")
        _check(state, step)


def test_every_shape_meets_every_operation() -> None:
    met: dict[str, set[str]] = {s.name: set() for s in SHAPES}
    for shape_name, _grid, sequence in _cases():
        met[shape_name] |= {step.split(":")[0] for step in SEQUENCES[sequence]}
    assert all(ops == set(OPS) for ops in met.values()), met
