"""A hidden SubFigure's text hides no bar label.

``SubFigure.set_visible(False)`` hides its Axes and texts while their own
flags stay on. The bar label settling took such text for drawn text and
hid the visible bar label under it. Two SubFigures share one cell; the
second holds a wide text over the band above the first's plot, where the
value of a bar past the limit sits. Shown, it hides that value (the
control); hidden, the values show as with no text at all.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl.annotation._bar_label_settle import _text_boxes_drawn

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def _style() -> Iterator[None]:
    dm.style.use("report")
    yield
    plt.close("all")


def _shown_labels(text: str) -> list[bool]:
    """Which bar labels show: ``text`` is "none", "shown" or "hidden"."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    cell = fig.add_gridspec(1, 1)[0]
    bars_fig, other = fig.add_subfigure(cell), fig.add_subfigure(cell)
    ax = bars_fig.subplots()
    # The last bar runs far past the limit and is too narrow for its value,
    # so its label sits beyond the limit, above the plot, where the text is.
    bars = ax.bar(range(6), [1, 2, 3, 2, 1, 1234567], width=0.2)
    labels = dm.label_bars(ax, bars)
    ax.set_ylim(0, 4)
    if text != "none":
        cover = other.subplots()
        cover.axis("off")
        cover.text(
            0.5,
            0.97,
            "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM",
            ha="center",
            va="center",
            fontsize=30,
            transform=fig.transFigure,
        )
    if text == "hidden":
        other.set_visible(False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # the hidden-label notice
        dm.simple_layout(fig)
    fig.canvas.draw()
    return [label.get_visible() for label in labels]


def test_a_hidden_subfigures_text_hides_no_bar_label() -> None:
    clear = _shown_labels("none")
    assert all(clear)
    assert not all(_shown_labels("shown"))  # the control: the text covers them
    assert _shown_labels("hidden") == clear


def _last_value(owner: str) -> tuple[bool, bool]:
    """Whether the past-limit value shows, and whether it shows under the
    wide text written by ``owner``: "axes" (an Axes of the other SubFigure,
    the control), "subfigure" (that SubFigure's own ``text``),
    "self_hidden" (that SubFigure hidden) or "ancestor_hidden" (the
    SubFigure above the writer hidden)."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    cell = fig.add_gridspec(1, 1)[0]
    bars_fig, other = fig.add_subfigure(cell), fig.add_subfigure(cell)
    ax = bars_fig.subplots()
    labels = dm.label_bars(
        ax, ax.bar(range(6), [1, 2, 3, 2, 1, 1234567], width=0.2)
    )
    ax.set_ylim(0, 4)
    if owner == "axes":
        writer: Any = other.subplots()
        writer.axis("off")
    else:
        writer = {
            "subfigure": other,
            "self_hidden": other,
            "ancestor_hidden": other.subfigures(1, 1),
        }[owner]
    text = writer.text(
        0.5,
        0.97,
        "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM",
        ha="center",
        va="center",
        fontsize=30,
        transform=fig.transFigure,
    )
    if owner in ("self_hidden", "ancestor_hidden"):
        other.set_visible(False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        dm.simple_layout(fig)
    fig.canvas.draw()
    value = labels[-1]
    shows = bool(value.get_visible())
    under = shows and value.get_window_extent().overlaps(
        text.get_window_extent()
    )
    return shows, bool(under)


@pytest.mark.parametrize("owner", ["axes", "subfigure"])
def test_no_value_shows_under_a_drawn_text(owner: str) -> None:
    """Only the figure's own texts were figure-level obstacles: a value past
    the limit showed under a shown SubFigure's text (review of #670). The
    same text written by an Axes is the control."""
    _shows, under = _last_value(owner)
    assert not under


def test_the_figures_own_text_is_still_an_obstacle() -> None:
    """Without SubFigures, the figure's own texts are obstacles, as before."""
    fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    ax.plot([0, 1], [0, 1])
    note = fig.text(0.5, 0.5, "A note on the figure")
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    box = note.get_window_extent(renderer)
    assert any(
        b.bounds == pytest.approx(box.bounds)
        for b in _text_boxes_drawn(fig, renderer)
    )


@pytest.mark.parametrize("owner", ["self_hidden", "ancestor_hidden"])
def test_a_hidden_subfigures_figure_level_text_hides_no_value(
    owner: str,
) -> None:
    shows, _under = _last_value(owner)
    assert shows


def test_a_hidden_subfigures_text_is_no_obstacle() -> None:
    """The obstacles the settling reads (review of #667's follow-up)."""
    fig = plt.figure(figsize=dm.figsize("17cm", "wide"))
    hidden, _visible = fig.subfigures(1, 2)
    ax = hidden.subplots()
    ax.axis("off")
    ax.text(0.5, 0.5, "Hidden obstacle")
    hidden.set_visible(False)
    fig.canvas.draw()
    assert _text_boxes_drawn(fig, fig.canvas.get_renderer()) == []
