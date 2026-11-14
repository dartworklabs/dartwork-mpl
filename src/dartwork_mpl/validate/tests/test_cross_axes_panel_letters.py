"""CROSS_AXES_OVERLAP sees a ``dm.label_axes`` letter under a neighbour's text.

Smoke round 5 (2026-11-14, ``s04-grid-to-slide``, Claude's row-of-four
attempt): on a slide, the title "Meeting rooms" ran into the next panel's
letter and read "Meeting roomsc". The review reported nothing, because the
check compared titles, axis names and tick labels only; the host caught it
by eye.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl._figure_geometry import axes_titles
from tests.support.mpl_observe import drawn_renderer


@pytest.fixture(autouse=True)
def _report():
    dm.style.use("report")
    yield
    plt.close("all")


def _row(title: str):
    fig, axes = plt.subplots(1, 2, figsize=dm.figsize("12cm", "5cm"))
    for ax in axes:
        ax.plot([0, 1], [0, 1])
    letters = dm.label_axes(axes)
    axes[0].set_title(title, loc="right")
    return fig, axes, letters


def _cross(fig) -> list:
    return [
        w
        for w in dm.validate_figure(fig, quiet=True)
        if w.check_id == "CROSS_AXES_OVERLAP"
    ]


def test_a_title_over_the_next_panels_letter_is_reported():
    fig, axes, letters = _row("A title that runs on into the next panel")
    renderer = drawn_renderer(fig)
    title = axes_titles(axes[0])["right"]
    # The figure really has the collision the check is asked about.
    assert title.get_window_extent(renderer).overlaps(
        letters[1].get_window_extent(renderer)
    )

    found = _cross(fig)

    assert [w.severity.value for w in found] == ["WARNING"]
    assert found[0].detail["role_a"] == "title"
    assert found[0].detail["role_b"] == "panel label"
    assert "'b'" in found[0].message


def test_letters_clear_of_their_neighbours_are_not_reported():
    """A laid-out row with titles and letters has nothing to report."""
    fig, axes = plt.subplots(1, 2, figsize=dm.figsize("12cm", "5cm"))
    for ax, name in zip(axes, ["North office", "South office"], strict=True):
        ax.plot([0, 1], [0, 1])
        ax.set_title(name)
    dm.label_axes(axes)
    dm.simple_layout(fig)

    assert _cross(fig) == []
