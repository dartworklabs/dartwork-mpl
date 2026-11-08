"""Accessibility-oriented validate_figure checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.collections import PathCollection, PolyCollection
from matplotlib.path import Path

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity, VisualWarning, validate_figure

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


def _new_figure() -> tuple[Figure, Axes]:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    return fig, ax


def _warnings_for(fig: Figure, check_id: str) -> list[VisualWarning]:
    return validate_figure(fig, checks=(check_id,), quiet=True)


class TestTextContrast:
    """Text contrast severity against the effective background (bbox, patch, axes)."""

    def test_light_gray_title_on_white_warns(self) -> None:
        fig, ax = _new_figure()
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.set_title("Low contrast title", color="#cccccc")

        warnings = _warnings_for(fig, "TEXT_CONTRAST")
        hits = [w for w in warnings if w.check_id == "TEXT_CONTRAST"]

        assert hits
        assert hits[0].severity == Severity.WARNING
        assert hits[0].detail["ratio"] < 3.0
        assert "Low contrast" in hits[0].detail["sample"]
        plt.close(fig)

    def test_default_title_passes(self) -> None:
        fig, ax = _new_figure()
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.set_title("Readable title")

        warnings = _warnings_for(fig, "TEXT_CONTRAST")

        assert not [w for w in warnings if w.check_id == "TEXT_CONTRAST"]
        plt.close(fig)

    def test_normal_text_between_large_and_normal_aa_is_info(self) -> None:
        fig, ax = _new_figure()
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.text(
            0.5,
            0.5,
            "Borderline text",
            color="#777777",
            fontsize=dm.fs(0),
            transform=ax.transAxes,
        )

        warnings = _warnings_for(fig, "TEXT_CONTRAST")
        hits = [w for w in warnings if w.check_id == "TEXT_CONTRAST"]

        assert hits
        assert hits[0].severity == Severity.INFO
        assert 3.0 <= hits[0].detail["ratio"] < 4.5
        plt.close(fig)

    def test_white_text_inside_dark_opaque_patch_passes(self) -> None:
        fig, ax = _new_figure()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.add_patch(
            mpatches.Rectangle(
                (0.2, 0.2), 0.6, 0.6, facecolor="#222222", edgecolor="none"
            )
        )
        ax.text(
            0.5,
            0.5,
            "inside",
            color="white",
            ha="center",
            va="center",
            fontsize=dm.fs(0),
        )

        warnings = _warnings_for(fig, "TEXT_CONTRAST")

        assert not [w for w in warnings if w.check_id == "TEXT_CONTRAST"]
        plt.close(fig)

    def test_white_text_on_bare_axes_warns(self) -> None:
        fig, ax = _new_figure()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.text(
            0.5,
            0.5,
            "bare",
            color="white",
            ha="center",
            va="center",
            fontsize=dm.fs(0),
        )

        warnings = _warnings_for(fig, "TEXT_CONTRAST")
        hits = [w for w in warnings if w.check_id == "TEXT_CONTRAST"]

        assert hits
        assert hits[0].severity == Severity.WARNING
        assert hits[0].detail["ratio"] == pytest.approx(1.0)
        assert hits[0].detail["background_color"] == "#ffffff"
        plt.close(fig)

    def test_semitransparent_patch_uses_composited_background(self) -> None:
        fig, ax = _new_figure()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.add_patch(
            mpatches.Rectangle(
                (0.2, 0.2),
                0.6,
                0.6,
                facecolor=(0.0, 0.0, 0.0, 0.5),
                edgecolor="none",
            )
        )
        ax.text(
            0.5,
            0.5,
            "alpha",
            color="white",
            ha="center",
            va="center",
            fontsize=dm.fs(0),
        )

        warnings = _warnings_for(fig, "TEXT_CONTRAST")
        hits = [w for w in warnings if w.check_id == "TEXT_CONTRAST"]

        assert hits
        assert hits[0].severity == Severity.INFO
        assert 3.0 <= hits[0].detail["ratio"] < 4.5
        assert hits[0].detail["background_color"] not in {"#000000", "#ffffff"}
        plt.close(fig)

    def test_text_bbox_facecolor_wins_over_axes_background(self) -> None:
        fig, ax = _new_figure()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.text(
            0.5,
            0.5,
            "boxed",
            color="black",
            ha="center",
            va="center",
            fontsize=dm.fs(0),
            bbox={"facecolor": "#111111", "edgecolor": "none"},
        )

        warnings = _warnings_for(fig, "TEXT_CONTRAST")
        hits = [w for w in warnings if w.check_id == "TEXT_CONTRAST"]

        assert hits
        assert hits[0].severity == Severity.WARNING
        assert hits[0].detail["background_color"] == "#111111"
        plt.close(fig)

    @pytest.mark.parametrize("clip_on", [True, False])
    def test_a_patch_counts_only_where_it_is_drawn(self, clip_on: bool) -> None:
        # Re-review N-I3: a bar past the limit is clipped at the axes edge,
        # so beyond it the text lies on the figure, not on the bar. An
        # unclipped patch is drawn there, and its colour counts.
        fig, ax = _new_figure()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.add_patch(
            mpatches.Rectangle(
                (0.4, 0.0),
                0.2,
                3.0,
                facecolor="#222222",
                edgecolor="none",
                clip_on=clip_on,
            )
        )
        ax.text(
            0.5,
            1.1,
            "beyond",
            color="black",
            ha="center",
            va="center",
            fontsize=dm.fs(0),
            clip_on=False,
        )

        hits = _warnings_for(fig, "TEXT_CONTRAST")

        if clip_on:
            assert not hits
        else:
            assert hits and hits[0].detail["background_color"] == "#222222"
        plt.close(fig)

    @pytest.mark.parametrize(
        "color", ["dc.blue9", "#1f4e79", "dc.gray9", "#222222"]
    )
    def test_bar_values_are_judged_on_what_is_drawn_behind_them(
        self, color: str
    ) -> None:
        # Re-review N-I3: the value of a bar past the limit, too wide for its
        # bar, sits beyond the limit on the figure in the text colour (13-1).
        # Read against the unclipped bar it gave a false INFO/WARNING (2.42:1
        # on #1f4e79). Real faults stay found: that value made white by the
        # caller (white on white), and a value inside the limit on its bar
        # made the bar's own colour.
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"), dpi=200)
        ax.bar([0, 1, 2, 3], [300, 4100, 520, 12500], width=0.3, color=color)
        ax.bar([5], [5000], width=0.9, color=color)  # holds its number
        ax.set_ylim(0, 1000)
        labels = dm.label_bars(ax)
        dm.simple_layout(fig)
        cut = [t for t in labels if t.get_text() in ("4,100", "12,500")]
        assert all(t.get_visible() and t.clipped and t.off_bar for t in cut)

        assert not _warnings_for(fig, "TEXT_CONTRAST")

        cut[0].set_color("white")
        hits = _warnings_for(fig, "TEXT_CONTRAST")
        assert [
            (h.detail["sample"], h.detail["background_color"]) for h in hits
        ] == [("4,100", "#ffffff")]
        assert hits[0].severity == Severity.WARNING

        cut[0].set_color("black")
        on_bar = [t for t in labels if t.get_text() == "5,000"]
        assert on_bar and on_bar[0].clipped and on_bar[0].on_bar
        assert not _warnings_for(fig, "TEXT_CONTRAST")  # its ink reads
        on_bar[0].set_color(color)
        hits = _warnings_for(fig, "TEXT_CONTRAST")
        assert [h.detail["sample"] for h in hits] == ["5,000"]
        assert hits[0].detail["ratio"] == pytest.approx(1.0)
        plt.close(fig)

    @pytest.mark.parametrize(
        ("ink", "ratio"), [("black", 2.75), ("#505458", 1.0)]
    )
    def test_stack_segment_values_in_the_wrong_ink_stay_found(
        self, ink: str, ratio: float
    ) -> None:
        # The fault PR #613's review found (segment labels inside their
        # segments classed off the bar: black, or with color="series" the
        # segment's colour) is drawn on the segment, inside the axes: the
        # clip box keeps it found. In their own ink they pass.
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"), dpi=200)
        low, high = [40.0, 52.0, 47.0, 61.0], [30.0, 26.0, 35.0, 29.0]
        ax.bar(range(4), low, width=0.6, color="#1864b0")
        ax.bar(range(4), high, bottom=low, width=0.6, color="#505458")
        labels = dm.label_bars(ax, where="inside", total=False)
        dm.simple_layout(fig)
        assert not _warnings_for(fig, "TEXT_CONTRAST")

        top = [t for t in labels if t.kind == "segment"][4:]  # on #505458
        for t in top:
            t.set_color(ink)
        hits = _warnings_for(fig, "TEXT_CONTRAST")
        assert [h.detail["background_color"] for h in hits] == ["#505458"]
        assert hits[0].detail["count"] == 4
        assert hits[0].detail["ratio"] == pytest.approx(ratio, abs=0.01)
        assert hits[0].severity == Severity.WARNING
        plt.close(fig)


_DARK = "#1f2a44"


def _text_at_center(ax: Axes, ink: str, label: str = "label") -> None:
    ax.text(
        0.5,
        0.5,
        label,
        color=ink,
        ha="center",
        va="center",
        fontsize=dm.fs(0),
        transform=ax.transAxes,
    )


class TestTextContrastBackground:
    """The background is what is painted under the text's centre (T-C, 11-09).

    The advanced pie's callout in the donut hole was read against the leader
    wedge (1.00:1) because the wedge's box holds the hole; contour labels and
    heatmap values were read against the bare Axes because filled
    collections and images were not looked at.
    """

    def test_text_in_a_donut_hole_reads_the_hole(self) -> None:
        fig, ax = _new_figure()
        ax.pie(
            [62, 38], colors=["#00c897", "#c0f1e1"], wedgeprops={"width": 0.38}
        )
        ax.text(0, 0, "hole", color="#00c897", ha="center", va="center")

        hits = _warnings_for(fig, "TEXT_CONTRAST")

        assert [
            (h.detail["sample"], h.detail["background_color"]) for h in hits
        ] == [("hole", "#ffffff")]
        assert hits[0].detail["ratio"] == pytest.approx(2.16, abs=0.01)
        plt.close(fig)

    @pytest.mark.parametrize(
        ("ink", "warns"), [("white", False), ("#222222", True)]
    )
    def test_a_filled_area_under_the_text_counts(
        self, ink: str, warns: bool
    ) -> None:
        fig, ax = _new_figure()
        ax.fill_between([0, 1], [0, 0], [1, 1], color=_DARK)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        _text_at_center(ax, ink)

        hits = _warnings_for(fig, "TEXT_CONTRAST")

        assert [h.detail["background_color"] for h in hits] == (
            [_DARK] if warns else []
        )
        plt.close(fig)

    def test_contourf_reads_the_band_under_each_label(self) -> None:
        fig, ax = _new_figure()
        x = np.linspace(0, 1, 50)
        xx, yy = np.meshgrid(x, x)
        ax.contourf(xx, yy, xx, levels=[0, 0.5, 1], colors=["white", _DARK])
        for x_pos, label in ((0.25, "on white"), (0.75, "on dark")):
            ax.text(x_pos, 0.5, label, color="white", ha="center", va="center")

        hits = _warnings_for(fig, "TEXT_CONTRAST")

        assert [h.detail["samples"] for h in hits] == [["on white"]]
        assert hits[0].detail["background_color"] == "#ffffff"
        plt.close(fig)

    @pytest.mark.parametrize("kind", ["imshow", "pcolormesh"])
    def test_an_image_cell_under_the_text_counts(self, kind: str) -> None:
        fig, ax = _new_figure()
        data = np.ma.masked_array(
            [[0.0, 1.0, 0.0]], mask=[[False, False, True]]
        )
        if kind == "imshow":
            ax.imshow(data, cmap="gray", vmin=0, vmax=1, aspect="auto")
            centres = [0.0, 1.0, 2.0]
            row = 0.0
        else:
            ax.pcolormesh(
                np.arange(4), [0, 1], data, cmap="gray", vmin=0, vmax=1
            )
            centres = [0.5, 1.5, 2.5]
            row = 0.5
        for x_pos, label in zip(
            centres, ["black cell", "white cell", "masked"], strict=True
        ):
            ax.text(x_pos, row, label, color="white", ha="center", va="center")

        hits = _warnings_for(fig, "TEXT_CONTRAST")

        assert [sorted(h.detail["samples"]) for h in hits] == [
            ["masked", "white cell"]
        ]
        assert hits[0].detail["background_color"] == "#ffffff"
        plt.close(fig)

    def test_scatter_markers_are_not_a_background(self) -> None:
        fig, ax = _new_figure()
        ax.scatter([0.5], [0.5], s=4000, color=_DARK)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        _text_at_center(ax, "#222222")

        assert not _warnings_for(fig, "TEXT_CONTRAST")
        plt.close(fig)

    def test_only_paths_drawn_where_they_are_count(self) -> None:
        # A collection scaled per path (marker sizes) or shifted by offsets
        # draws its paths elsewhere; only plain filled paths are read.
        from dartwork_mpl.validate._checks.text_contrast import _drawn_in_place

        fig, ax = _new_figure()
        filled = ax.fill_between([0, 1], [0, 0], [1, 1])
        sized = PathCollection([Path.unit_circle()], sizes=[100])
        shifted = PolyCollection([[(0, 0), (1, 0), (1, 1)]], offsets=[(5, 5)])

        assert _drawn_in_place(filled)
        assert not _drawn_in_place(sized)
        assert not _drawn_in_place(shifted)
        plt.close(fig)

    def test_overlapping_paths_read_the_one_drawn_last(self) -> None:
        fig, ax = _new_figure()
        square = [(0, 0), (1, 0), (1, 1), (0, 1)]
        ax.add_collection(
            PolyCollection([square, square], facecolors=["white", _DARK])
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        _text_at_center(ax, "white")

        assert not _warnings_for(fig, "TEXT_CONTRAST")
        plt.close(fig)

    def test_a_callout_is_read_where_its_text_is_not_its_arrow(self) -> None:
        # An annotation's extent holds its arrow; the centre of that union
        # lay on the dark fill the arrow points into, not under the words.
        fig, ax = _new_figure()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.add_patch(
            mpatches.Rectangle((0.4, 0), 0.6, 1, facecolor=_DARK, lw=0)
        )
        ax.annotate(
            "on white",
            xy=(0.95, 0.5),
            xytext=(0.02, 0.5),
            va="center",
            color="#222222",
            arrowprops={"arrowstyle": "->", "color": "#222222"},
        )

        assert not _warnings_for(fig, "TEXT_CONTRAST")
        plt.close(fig)

    def test_text_on_a_twin_reads_the_host_drawn_beneath(self) -> None:
        fig, host = _new_figure()
        host.bar([0], [1], width=2, color=_DARK)
        host.set_xlim(-0.5, 0.5)
        host.set_ylim(0, 1)
        twin = host.twinx()
        _text_at_center(twin, "white", "on host bar")

        assert not _warnings_for(fig, "TEXT_CONTRAST")
        _text_at_center(twin, "#222222", "dark on bar")
        hits = _warnings_for(fig, "TEXT_CONTRAST")
        assert [h.detail["background_color"] for h in hits] == [_DARK]
        plt.close(fig)

    def test_legend_text_reads_its_frame(self) -> None:
        fig, ax = _new_figure()
        ax.fill_between([0, 1], [0, 0], [1, 1], color=_DARK)
        ax.plot([0, 1], [0.5, 0.5], color="white", label="series")
        legend = ax.legend(loc="center", frameon=True, framealpha=1)
        legend.get_frame().set_facecolor("white")
        legend.get_texts()[0].set_color("#222222")

        assert not _warnings_for(fig, "TEXT_CONTRAST")
        legend.set_frame_on(False)  # framealpha would override a clear face
        hits = _warnings_for(fig, "TEXT_CONTRAST")
        assert [h.detail["background_color"] for h in hits] == [_DARK]
        plt.close(fig)

    def test_a_centre_on_the_polar_clip_seam_reads_what_is_painted(
        self,
    ) -> None:
        # The polar Axes' round clip path has a zero-width seam along the
        # horizontal through its centre; a centred label there is painted on
        # the disc beneath it.
        dm.style.use("scientific")
        fig, ax = plt.subplots(
            figsize=dm.figsize("9cm", "square"),
            subplot_kw={"projection": "polar"},
        )
        ax.bar(0, 1, width=2 * np.pi, bottom=0, color=_DARK)
        ax.set_ylim(0, 2)
        for theta in (0.0, np.pi):
            ax.text(theta, 0.5, "seam", color="white", ha="center", va="center")
        ax.text(0, 0, "centre", color="white", ha="center", va="center")

        assert not _warnings_for(fig, "TEXT_CONTRAST")
        plt.close(fig)

    def test_3d_axes_are_read_without_failing(self) -> None:
        dm.style.use("scientific")
        fig = plt.figure(figsize=dm.figsize("9cm", "square"))
        ax = fig.add_subplot(projection="3d")
        ax.plot([0, 1], [0, 1], [0, 1])
        ax.text(0.5, 0.5, 0.5, "faint", color="#eeeeee")

        hits = _warnings_for(fig, "TEXT_CONTRAST")

        assert [h.detail["sample"] for h in hits] == ["faint"]
        plt.close(fig)


class TestMinFontSize:
    """Text below the minimum readable size is reported."""

    def test_tiny_text_warns(self) -> None:
        fig, ax = _new_figure()
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.text(0.5, 0.5, "tiny note", fontsize=3, transform=ax.transAxes)

        warnings = _warnings_for(fig, "MIN_FONT_SIZE")
        hits = [w for w in warnings if w.check_id == "MIN_FONT_SIZE"]

        assert hits
        assert hits[0].severity == Severity.WARNING
        assert hits[0].detail["size_pt"] == 3.0
        assert "tiny note" in hits[0].detail["sample"]
        plt.close(fig)

    def test_readable_text_passes(self) -> None:
        fig, ax = _new_figure()
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.text(0.5, 0.5, "readable note", fontsize=8, transform=ax.transAxes)

        warnings = _warnings_for(fig, "MIN_FONT_SIZE")

        assert not [w for w in warnings if w.check_id == "MIN_FONT_SIZE"]
        plt.close(fig)


class TestGrayscaleSafety:
    """Series that collapse in grayscale are reported per panel, once per clash."""

    def test_same_luminance_series_emit_info(self) -> None:
        fig, ax = _new_figure()
        ax.plot([1, 2, 3], [1, 4, 9], color="#ff0000")
        ax.plot([1, 2, 3], [2, 5, 10], color="#009400")

        warnings = _warnings_for(fig, "GRAYSCALE_SAFETY")
        hits = [w for w in warnings if w.check_id == "GRAYSCALE_SAFETY"]

        assert hits
        assert hits[0].severity == Severity.INFO
        assert hits[0].detail["pairs"]
        plt.close(fig)

    def test_panels_are_judged_separately(self) -> None:
        """Two series only collapse where a reader compares them.

        Pooling every Axes reported a clash between a price panel's moving
        average and a multiple panel's series on every multi-panel chart, which
        is noise: the panels are read separately, so neither becomes harder to
        identify. Each panel here is internally well separated.
        """
        dm.style.use("scientific")
        fig, axes = plt.subplots(2, 1, figsize=dm.figsize("9cm", "standard"))
        fig.patch.set_facecolor("white")
        for ax in axes:
            ax.set_facecolor("white")
        # 0.018 vs 0.301: safely apart inside the panel.
        axes[0].plot([1, 2, 3], [1, 4, 9], color="#212529")
        axes[0].plot([1, 2, 3], [2, 5, 10], color="#339af0")
        # 0.266 vs 0.653: also safely apart, but 0.266 sits beside the 0.301
        # above, which the pooled comparison flagged.
        axes[1].plot([1, 2, 3], [1, 4, 9], color="#868e96")
        axes[1].plot([1, 2, 3], [2, 5, 10], color="#ced4da")

        warnings = _warnings_for(fig, "GRAYSCALE_SAFETY")

        assert not [w for w in warnings if w.check_id == "GRAYSCALE_SAFETY"]
        plt.close(fig)

    def test_a_clash_inside_one_panel_is_still_reported(self) -> None:
        """Per-Axes comparison must not turn the check off."""
        dm.style.use("scientific")
        fig, axes = plt.subplots(2, 1, figsize=dm.figsize("9cm", "standard"))
        fig.patch.set_facecolor("white")
        for ax in axes:
            ax.set_facecolor("white")
        axes[0].plot([1, 2, 3], [1, 4, 9], color="#212529")
        axes[1].plot([1, 2, 3], [1, 4, 9], color="#ff0000")
        axes[1].plot([1, 2, 3], [2, 5, 10], color="#009400")

        hits = [
            w
            for w in _warnings_for(fig, "GRAYSCALE_SAFETY")
            if w.check_id == "GRAYSCALE_SAFETY"
        ]

        assert hits
        plt.close(fig)

    def test_one_clash_repeated_across_panels_is_reported_once(self) -> None:
        """Small multiples share a palette; the fix is one change, not N."""
        dm.style.use("scientific")
        fig, axes = plt.subplots(3, 1, figsize=dm.figsize("9cm", "standard"))
        fig.patch.set_facecolor("white")
        for ax in axes:
            ax.set_facecolor("white")
            ax.plot([1, 2, 3], [1, 4, 9], color="#ff0000")
            ax.plot([1, 2, 3], [2, 5, 10], color="#009400")

        hits = [
            w
            for w in _warnings_for(fig, "GRAYSCALE_SAFETY")
            if w.check_id == "GRAYSCALE_SAFETY"
        ]

        assert len(hits) == 1
        assert len(hits[0].detail["pairs"]) == 1
        plt.close(fig)

    def test_distinct_luminance_series_pass(self) -> None:
        fig, ax = _new_figure()
        ax.plot([1, 2, 3], [1, 4, 9], color="#111111")
        ax.plot([1, 2, 3], [2, 5, 10], color="#f2c94c")

        warnings = _warnings_for(fig, "GRAYSCALE_SAFETY")

        assert not [w for w in warnings if w.check_id == "GRAYSCALE_SAFETY"]
        plt.close(fig)
