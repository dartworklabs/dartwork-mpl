"""Accessibility-oriented validate_figure checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

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

    def test_distinct_luminance_series_pass(self) -> None:
        fig, ax = _new_figure()
        ax.plot([1, 2, 3], [1, 4, 9], color="#111111")
        ax.plot([1, 2, 3], [2, 5, 10], color="#f2c94c")

        warnings = _warnings_for(fig, "GRAYSCALE_SAFETY")

        assert not [w for w in warnings if w.check_id == "GRAYSCALE_SAFETY"]
        plt.close(fig)
