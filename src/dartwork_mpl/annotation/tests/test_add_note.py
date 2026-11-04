"""``dm.add_note`` draws a source line the same way for every caller (#523).

The owner asked for one rule, not a per-agent choice: in the customization
eval Claude wrote the note at ``dm.fs(-1)`` and Codex at the body size.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm

PRESETS = ("report", "report-kr", "scientific", "presentation")


def _figure(preset: str):
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize_for(n_points=12, n_series=1))
    x = np.arange(2012, 2024)
    ax.plot(x, np.sin(x))
    ax.set(xlabel="Year", ylabel="Sessions")
    return fig, ax


class TestNoteStyle:
    """Lower-left corner, one step under the preset font (dm.fs(-1)), its colour."""

    @pytest.mark.parametrize("preset", PRESETS)
    def test_style_follows_the_preset(self, preset: str) -> None:
        fig, _ = _figure(preset)
        try:
            note = dm.add_note(fig, "Source: internal web logs")
            # dm.fs(-1): one point under the body text, 2.6 pt under
            # presentation (one step there, #556).
            assert note.get_fontsize() == pytest.approx(dm.fs(-1))
            assert note.get_position() == (0.0, 0.0)
            assert note.get_ha() == "left" and note.get_va() == "bottom"
            assert note in fig.texts
        finally:
            plt.close(fig)

    def test_named_keywords_win(self) -> None:
        fig, _ = _figure("report")
        try:
            note = dm.add_note(fig, "Source", fontsize=9, color="#555555")
            assert note.get_fontsize() == 9
            assert note.get_color() == "#555555"
        finally:
            plt.close(fig)


class TestNoteLayout:
    """simple_layout keeps the axes labels one ``axes.labelpad`` above it."""

    @pytest.mark.parametrize("preset", PRESETS)
    def test_gap_above_the_note_is_the_label_pad(self, preset: str) -> None:
        fig, ax = _figure(preset)
        try:
            note = dm.add_note(
                fig,
                "Source: internal web logs, weekly sessions 2024 "
                "(deduplicated by visitor ID)",
            )
            dm.simple_layout(fig)
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            gap_pt = (
                (
                    ax.xaxis.label.get_window_extent(renderer).y0
                    - note.get_window_extent(renderer).y1
                )
                * 72.0
                / fig.dpi
            )
            assert gap_pt == pytest.approx(
                mpl.rcParams["axes.labelpad"], abs=0.3
            )
            found = dm.validate_figure(
                fig, checks=("OVERLAP", "OVERFLOW", "CLIPPED_TEXT"), quiet=True
            )
            assert not found, [w.message for w in found]
        finally:
            plt.close(fig)

    def test_plain_figure_text_keeps_no_gap(self) -> None:
        """Only the note asks for the gap; other figure text is unchanged."""
        fig, ax = _figure("report")
        try:
            text = fig.text(0, 0, "plain", ha="left", va="bottom")
            dm.simple_layout(fig)
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            gap_px = (
                ax.xaxis.label.get_window_extent(renderer).y0
                - text.get_window_extent(renderer).y1
            )
            assert abs(gap_px) < 1.0
        finally:
            plt.close(fig)
