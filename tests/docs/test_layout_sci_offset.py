"""The layout guide's scientific-notation example keeps its ``1e6`` on the canvas.

``docs/usage_guide/layout.md`` used to send a request equal to matplotlib's
defaults (``style="sci"``) after the layout. That applies it, but the
offset text (``1e6``) then has no room and is drawn above the figure: the
reader sees ``0.0 … 3.0`` with no multiplier, and no check reports it
(W8 spec year-axis-sci-intent, D9). The guide now shows an order-free path;
this runs that fence and measures the multiplier, with the two orders the
guide names as controls.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.ticker import ScalarFormatter

import dartwork_mpl as dm

_LAYOUT_MD = Path(__file__).resolve().parents[2] / "docs/usage_guide/layout.md"
_FENCE = re.compile(r"```python\n(.*?)```", re.S)
_VALUES = [0, 0.8e6, 1.5e6, 2.2e6, 3.0e6]


def _offset_box(fig, ax):
    fig.canvas.draw()
    text = ax.yaxis.get_offset_text()
    return text.get_text(), text.get_window_extent(fig.canvas.get_renderer())


def _guide_fence() -> str:
    text = _LAYOUT_MD.read_text(encoding="utf-8")
    (fence,) = [
        body
        for body in _FENCE.findall(text)
        if "ticklabel_format" in body and "ScalarFormatter()" in body
    ]
    return fence


def test_the_guide_example_keeps_the_multiplier_inside_the_figure() -> None:
    namespace: dict[str, object] = {"plt": plt, "dm": dm}
    exec(compile(_guide_fence(), str(_LAYOUT_MD), "exec"), namespace)
    fig, ax = namespace["fig"], namespace["ax"]
    try:
        offset, box = _offset_box(fig, ax)
        assert offset == "1e6"
        assert [t.get_text() for t in ax.get_yticklabels()][1:3] == [
            "0.0",
            "0.5",
        ]
        canvas = fig.bbox
        assert box.y1 <= canvas.y1 + 0.5
        assert box.x0 >= canvas.x0 - 0.5
    finally:
        plt.close(fig)


@pytest.mark.parametrize(("relayout", "inside"), [(False, False), (True, True)])
def test_a_request_after_the_layout_needs_the_layout_again(
    relayout: bool, inside: bool
) -> None:
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    try:
        ax.plot(range(5), _VALUES)
        dm.simple_layout(fig)
        ax.ticklabel_format(axis="y", style="sci")
        if relayout:
            dm.simple_layout(fig)
        offset, box = _offset_box(fig, ax)
        assert offset == "1e6"
        assert bool(box.y1 <= fig.bbox.y1 + 0.5) == inside
    finally:
        plt.close(fig)


def test_scalar_formatter_first_and_non_default_values_hold_before_layout() -> (
    None
):
    for prepare in (
        lambda ax: ax.yaxis.set_major_formatter(ScalarFormatter()),
        None,
    ):
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        try:
            ax.plot(range(5), _VALUES)
            if prepare is not None:
                prepare(ax)
                ax.ticklabel_format(axis="y", style="sci")
            else:
                ax.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))
            dm.simple_layout(fig)
            offset, box = _offset_box(fig, ax)
            assert offset == "1e6"
            assert box.y1 <= fig.bbox.y1 + 0.5
        finally:
            plt.close(fig)
