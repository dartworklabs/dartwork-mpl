"""``dm.simple_layout`` on realistic charts, as users call it."""

from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure

import dartwork_mpl as dm

DEPARTMENTS = [
    "Customer Support",
    "Product Engineering",
    "Sales Operations",
    "Human Resources",
    "Finance and Legal",
    "Marketing Analytics",
]


def content(fig: Figure):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    boxes = [ax.get_tightbbox(renderer) for ax in fig.axes]
    return (
        min(b.x0 for b in boxes),
        max(b.x1 for b in boxes),
        min(b.y0 for b in boxes),
        max(b.y1 for b in boxes),
    )


def line_chart(**kw) -> Figure:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"), **kw)
    ax.plot(np.arange(10), np.arange(10) ** 2)
    ax.set_xlabel("Week")
    ax.set_ylabel("Signups (thousands)")
    ax.set_title("Signups")
    return fig


@pytest.mark.parametrize(("margin", "mm"), [(0, 0.0), ("5mm", 5.0)])
def test_content_sits_the_margin_from_every_edge(margin, mm) -> None:
    fig = line_chart()
    dm.simple_layout(fig, margin=margin)
    x0, x1, y0, y1 = content(fig)
    w, h = fig.bbox.width, fig.bbox.height
    px = mm / 25.4 * fig.dpi
    for gap in (x0, w - x1, y0, h - y1):
        assert gap == pytest.approx(px, abs=1.0)


def test_a_second_call_draws_the_same() -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "wide"))
    ax.bar(DEPARTMENTS[:4], [1, 2, 3, 4])
    dm.simple_layout(fig)
    first = (
        ax.get_position().bounds,
        [t.get_text() for t in ax.get_xticklabels()],
    )
    dm.simple_layout(fig)
    assert (
        ax.get_position().bounds,
        [t.get_text() for t in ax.get_xticklabels()],
    ) == first


def test_crowded_category_names_wrap_and_come_back() -> None:
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "wide"))
    ax.bar(DEPARTMENTS, [34, 58, 41, 17, 22, 29])
    dm.simple_layout(fig)
    fig.canvas.draw()
    assert any("\n" in t.get_text() for t in ax.get_xticklabels())
    dm.simple_layout(fig, fit_labels=False)
    fig.canvas.draw()
    assert [t.get_text() for t in ax.get_xticklabels()] == DEPARTMENTS


def test_crowded_numbers_turn() -> None:
    fig, ax = plt.subplots(figsize=dm.figsize("6cm", "standard"))
    ax.bar([f"{v:,}" for v in range(100_000, 1_300_000, 100_000)], range(12))
    dm.simple_layout(fig)
    assert {t.get_rotation() for t in ax.get_xticklabels()} == {90.0}


def test_a_turn_that_crushes_the_plot_is_undone() -> None:
    fig, ax = plt.subplots(figsize=dm.figsize("4cm", "wide"))
    ax.bar(
        ["Aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" + str(k) for k in range(4)],
        range(4),
    )
    dm.simple_layout(fig)
    assert {t.get_rotation() for t in ax.get_xticklabels()} == {0.0}


def test_suptitle_and_note_keep_their_edges() -> None:
    fig = line_chart()
    fig.suptitle("Quarterly signups")
    note = dm.add_note(fig, "Source: internal CRM")
    dm.simple_layout(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    ax_box = fig.axes[0].get_tightbbox(renderer)
    assert fig._suptitle.get_window_extent(renderer).y0 >= ax_box.y1  # type: ignore[union-attr]
    assert note.get_window_extent(renderer).y1 <= ax_box.y0


def test_a_figure_pyplot_does_not_manage() -> None:
    fig = Figure(figsize=dm.figsize("9cm", "standard"))
    ax = fig.add_subplot()
    ax.plot([1, 2, 3])
    ax.set_ylabel("A label that needs room")
    before = ax.get_position().bounds
    dm.simple_layout(fig)
    assert ax.get_position().bounds != before


def test_grid_with_colorbar_and_shared_axes() -> None:
    fig, axes = plt.subplots(
        2, 2, figsize=dm.figsize("13cm", "square"), sharex=True
    )
    for ax in axes.flat:
        im = ax.imshow(np.arange(25).reshape(5, 5))
        ax.set_ylabel("Row")
    fig.colorbar(im, ax=axes, label="Value")
    dm.simple_layout(fig)
    x0, x1, y0, y1 = content(fig)
    assert x0 >= -0.5 and y0 >= -0.5
    assert x1 <= fig.bbox.width + 0.5 and y1 <= fig.bbox.height + 0.5


def test_left_alone() -> None:
    empty = plt.figure()
    dm.simple_layout(empty)  # no Axes: nothing to do, no warning

    manual = plt.figure()
    manual.add_axes((0.1, 0.1, 0.8, 0.8))
    with pytest.warns(UserWarning, match="no GridSpec"):
        dm.simple_layout(manual)


def test_a_margin_that_is_not_finite_raises_before_drawing() -> None:
    fig = line_chart()
    before = fig.axes[0].get_position().bounds
    with warnings.catch_warnings(), pytest.raises(ValueError, match="finite"):
        dm.simple_layout(fig, margin=float("inf"))
    assert fig.axes[0].get_position().bounds == before
