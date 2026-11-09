"""TICK_CORNER_OVERLAP: an x tick label on a y tick label at a corner.

No other check sees the pair: ``TICK_OVERLAP`` compares neighbours along
one axis, ``CROSS_AXES_OVERLAP`` other plots. The oracle is the labels'
own boxes, measured in the test, and the fix it suggests, applied.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import drawn_tick_labels, get_renderer


@pytest.fixture(autouse=True)
def _own_rc():
    with matplotlib.rc_context():
        yield
    plt.close("all")


def _square(limit: float = 3.0):
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))
    x = np.linspace(-3, 3, 50)
    ax.plot(x, 3 * np.sin(x))
    ax.set_xlim(-limit, limit)
    ax.set_ylim(-limit, limit)
    dm.simple_layout(fig, fit_labels=False)
    fig.canvas.draw()
    return fig, ax


def _corner(fig):
    return [
        w
        for w in dm.validate_figure(fig, quiet=True)
        if w.check_id == "TICK_CORNER_OVERLAP"
    ]


def _one(fig):
    found = _corner(fig)
    assert len(found) == 1, [w.check_id for w in found]
    return found[0]


def _worst(fig, ax) -> float:
    fig.canvas.draw()
    renderer = get_renderer(fig)
    boxes = {
        which: [
            t.get_window_extent(renderer)
            for t in drawn_tick_labels(ax, which)
            if t.get_text().strip()
        ]
        for which in ("x", "y")
    }
    return max(
        min(
            min(a.x1, b.x1) - max(a.x0, b.x0), min(a.y1, b.y1) - max(a.y0, b.y0)
        )
        for a in boxes["x"]
        for b in boxes["y"]
    )


def test_the_corner_pair_is_reported() -> None:
    fig, ax = _square()
    assert _worst(fig, ax) > 0.5  # precondition: they collide
    warning = _one(fig)
    assert str(warning.severity.value) == "WARNING"
    assert warning.detail["corner"] == "lower left"
    minus_three = chr(0x2212) + "3"  # matplotlib's minus sign
    assert warning.detail["x_label"] == warning.detail["y_label"] == minus_three
    assert warning.detail["pairs"] == 1
    assert warning.detail["px"] == pytest.approx(_worst(fig, ax), abs=0.2)
    assert "lower left" in warning.message


def test_labels_that_clear_are_not_reported() -> None:
    fig, ax = _square(limit=3.2)
    assert _worst(fig, ax) <= 0.5
    assert _corner(fig) == []


def test_the_suggested_pad_clears_the_pair() -> None:
    """The fix names the axis that moves less and the pad that clears."""
    from dartwork_mpl.validate.fixes import get_fix_suggestions

    fig, ax = _square()
    warning = _one(fig)
    text = "\n".join(get_fix_suggestions(warning))
    assert "dm.simple_layout(fig)" in text
    axis, pad = warning.detail["axis"], warning.detail["pad"]
    owner = warning.detail.get("owner_index")
    which = warning.detail.get("which", "major")
    assert (
        f"fig.axes[{owner}].tick_params(axis={axis!r}, which={which!r}, "
        f"pad={pad:g})"
    ) in text
    ax.tick_params(axis=axis, which=which, pad=pad)
    fig.canvas.draw()
    assert _worst(fig, ax) <= 0.5
    assert _corner(fig) == []


def test_after_the_layout_nothing_is_left() -> None:
    fig, _ax = _square()
    dm.simple_layout(fig)
    assert _corner(fig) == []


def test_a_polar_plot_has_no_corner() -> None:
    """Radial labels along 0 degrees run into the ``0°`` label (38 px on a
    9 cm slide); that is the polar layout, not a corner."""
    dm.style.use("presentation")
    fig = plt.figure(figsize=dm.figsize("9cm", "square"))
    ax = fig.add_subplot(projection="polar")
    ax.plot(np.linspace(0, 6, 20), np.linspace(0, 100, 20))
    ax.set_rlabel_position(0)
    fig.canvas.draw()
    assert _worst(fig, ax) > 0.5  # precondition: theta and radial overlap
    assert _corner(fig) == []


@pytest.mark.parametrize(
    ("scene", "axis"), [("tall y labels", "y"), ("wide first name", "x")]
)
def test_the_fix_names_the_axis_that_moves_less(scene: str, axis: str) -> None:
    """Tall y labels beside a narrow ``-3`` part sideways; a first category
    name reaching under the y labels parts downwards."""
    if scene == "tall y labels":
        fig, ax = _square()
        ax.tick_params(axis="y", labelsize=14)
    else:
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.bar(["Residential heat pumps", "B", "C", "D"], [3, 5, 2, 4])
    dm.simple_layout(fig, fit_labels=False)
    warning = _one(fig)
    assert warning.detail["axis"] == axis
    ax.tick_params(axis=axis, pad=warning.detail["pad"])
    assert _worst(fig, ax) <= 0.5


# ── the fix moves the ticks and the Axes that collide (#663) ─────────────


def _minor_corner(which: str):
    """The -3 at the corner is a labelled minor tick of ``which`` (major
    ticks at -2, 0, 2), on the side that moves less: tall minor y labels,
    or wide minor x labels."""
    from matplotlib.ticker import FixedLocator

    fig, ax = _square()
    axis = ax.yaxis if which == "y" else ax.xaxis
    axis.set_major_locator(FixedLocator([-2, 0, 2]))
    axis.set_minor_locator(FixedLocator([-3, -1, 1, 3]))
    if which == "y":
        axis.set_minor_formatter("{x:g}")
        ax.tick_params(axis="y", which="minor", labelsize=14)
    else:
        axis.set_minor_formatter("{x:.2f}")
    dm.simple_layout(fig, fit_labels=False)
    fig.canvas.draw()
    return fig


def _twin_corner():
    """A twin's right labels (14 pt, so they move less) meet the last
    bottom label at the lower right corner."""
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([0, 10], [0.2, 1])
    ax.set_xlim(0, 10)
    ax.set_ylim(0.2, 1)
    right = ax.twinx()
    right.plot([0, 10], [-3, 3])
    right.set_ylim(-3, 3)
    right.tick_params(axis="y", labelsize=14)
    dm.simple_layout(fig, fit_labels=False)
    fig.canvas.draw()
    return fig


def _scene(name: str):
    if name == "major":
        return _square()[0]
    if name == "twin":
        return _twin_corner()
    return _minor_corner(name[-1])


@pytest.mark.parametrize("scene", ["major", "minor y", "minor x", "twin"])
def test_applying_the_fix_as_written_clears_the_corner(scene: str) -> None:
    """Its ``tick_params`` lines, run as they read (``ax`` the Axes the
    warning names), clear the pair: the minor ticks when a minor label
    collides, the twin's axis when its right labels do."""
    from dartwork_mpl.validate.fixes import get_fix_suggestions

    fig = _scene(scene)
    warning = _one(fig)
    lines = [
        line
        for fix in get_fix_suggestions(warning)
        for line in fix.splitlines()
        if "tick_params" in line
    ]
    assert lines
    namespace = {
        "fig": fig,
        "ax": fig.axes[warning.detail["axes_index"]],
        "dm": dm,
    }
    for line in lines:
        exec(line, namespace)
    fig.canvas.draw()
    assert _corner(fig) == []


@pytest.mark.parametrize(
    ("scene", "owner", "which"),
    [("major", 0, "major"), ("minor y", 0, "minor"), ("twin", 1, "major")],
)
def test_the_detail_names_the_axes_and_ticks_that_move(
    scene: str, owner: int, which: str
) -> None:
    fig = _scene(scene)
    detail = _one(fig).detail
    assert detail["axes_index"] == 0  # where the pair was found, as before
    assert detail.get("owner_index") == owner
    assert detail.get("which") == which
    targets = detail.get("targets") or []
    assert [(t["axes_index"], t["which"]) for t in targets] == [(owner, which)]


def test_transparent_labels_are_not_a_corner() -> None:
    """x labels at alpha 0 draw the same pixels as hidden ones, and are no
    more a pair (independent review of #663; the artist alpha replaces the
    colour's, as when matplotlib draws)."""
    fig, ax = _square()
    labels = ax.get_xticklabels()
    for label in labels:
        label.set_alpha(0)
    fig.canvas.draw()
    transparent = bytes(fig.canvas.buffer_rgba())
    found = _corner(fig)
    for label in labels:
        label.set_visible(False)
    fig.canvas.draw()
    assert bytes(fig.canvas.buffer_rgba()) == transparent  # precondition
    assert _corner(fig) == []
    assert found == []


@pytest.mark.parametrize(
    ("color", "alpha", "reported"),
    [
        ((0, 0, 0, 0), None, False),  # the colour's alpha, none set
        ((0, 0, 0, 0), 1.0, True),  # the artist's alpha replaces it
        ((0, 0, 0, 1), 0.0, False),
    ],
)
def test_the_alpha_that_counts_is_the_one_matplotlib_draws_with(
    color, alpha, reported: bool
) -> None:
    fig, ax = _square()
    for label in ax.get_xticklabels():
        label.set_color(color)
        label.set_alpha(alpha)
    fig.canvas.draw()
    assert bool(_corner(fig)) is reported
