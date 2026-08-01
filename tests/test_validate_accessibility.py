"""Accessibility-oriented validate_figure checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pytest

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


class TestMinFontSize:
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
