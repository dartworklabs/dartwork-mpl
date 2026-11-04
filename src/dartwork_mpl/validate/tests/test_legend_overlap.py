"""LEGEND_OVERLAP: a legend box over a title, axis label, tick label or figure text (#523).

``OVERLAP`` compares text with text inside one Axes, so a legend drawn on
the title (a legend above the axes plus ``ax.set_title``) passed
validation. This check names the legend and the covered text.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity, VisualWarning, validate_figure
from dartwork_mpl.validate_fixes import get_fix_suggestions


def _findings(fig) -> list[VisualWarning]:
    """Only the LEGEND_OVERLAP findings for ``fig``."""
    return validate_figure(fig, checks=("LEGEND_OVERLAP",), quiet=True)


def _chart(preset: str = "report", nrows: int = 1, ncols: int = 1):
    dm.style.use(preset)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=dm.figsize("12cm", "standard"), squeeze=False
    )
    x = np.arange(2012, 2024)
    for ax in axes.flat:
        ax.plot(x, np.sin(x), label="Korea")
        ax.plot(x, np.cos(x), label="Japan")
        ax.set(xlabel="Year", ylabel="Growth (%)")
    return fig, list(axes.flat)


class TestOverlapIsReported:
    """A legend over a title, tick labels or a suptitle is one WARNING each."""

    @pytest.mark.parametrize("preset", ("report", "scientific", "presentation"))
    def test_legend_above_on_the_title(self, preset: str) -> None:
        fig, (ax,) = _chart(preset)
        ax.set_title("Real GDP growth by country")
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=2)
        (finding,) = _findings(fig)
        assert finding.severity is Severity.WARNING
        assert finding.message == (
            "Legend of axes[0] ('Korea', 'Japan') overlaps the title "
            "'Real GDP growth by country' of axes[0]"
        )
        detail = finding.detail
        assert detail["legend_axes"] == 0
        assert detail["legend_labels"] == ["Korea", "Japan"]
        assert detail["role"] == "title"
        assert detail["artist_axes"] == 0
        assert detail["text"] == "Real GDP growth by country"
        assert detail["count"] == 1
        width, height = detail["overlap_px"]
        assert isinstance(width, float) and width > 0 and height > 0
        plt.close(fig)

    def test_legend_over_tick_labels_is_one_finding_with_a_count(self) -> None:
        fig, (ax,) = _chart()
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, 0.0), ncols=2)
        findings = _findings(fig)
        roles = {f.detail["role"] for f in findings}
        assert "x tick label" in roles
        (ticks,) = [f for f in findings if f.detail["role"] == "x tick label"]
        assert ticks.detail["count"] >= 1
        assert "x tick label" in ticks.message
        plt.close(fig)

    def test_figure_legend_on_the_suptitle(self) -> None:
        fig, (ax,) = _chart()
        fig.suptitle("Figure suptitle", y=0.99)
        fig.legend(loc="upper center", ncols=2)
        (finding,) = [
            f for f in _findings(fig) if f.detail["role"] == "suptitle"
        ]
        assert finding.detail["legend_axes"] is None
        assert finding.detail["artist_axes"] is None
        assert finding.message.startswith("Figure legend ('Korea', 'Japan')")
        assert "the suptitle 'Figure suptitle' of the figure" in finding.message
        plt.close(fig)

    def test_right_legend_over_the_next_panels_y_label(self) -> None:
        fig, (left, right) = _chart(ncols=2)
        left.legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
        right.set_ylabel("A long right-panel label")
        dm.simple_layout(fig)
        hits = [f for f in _findings(fig) if f.detail["artist_axes"] == 1]
        assert hits, "the left panel's outside legend covers the right panel"
        plt.close(fig)

    def test_fix_suggestions_point_to_place_legend(self) -> None:
        fig, (ax,) = _chart()
        ax.set_title("Title")
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=2)
        (finding,) = _findings(fig)
        suggestions = get_fix_suggestions(finding)
        assert any("place_legend(ax, loc='above')" in s for s in suggestions)
        plt.close(fig)


class TestCleanFiguresPass:
    """Legends that cover no text produce no finding."""

    def test_legend_inside_with_a_title(self) -> None:
        fig, (ax,) = _chart()
        ax.set_title("Real GDP growth by country")
        ax.legend(loc="upper right")
        dm.simple_layout(fig)
        assert _findings(fig) == []
        plt.close(fig)

    @pytest.mark.parametrize("side", ("above", "below", "right", "left"))
    def test_place_legend_outside_after_layout(self, side: str) -> None:
        fig, (ax,) = _chart()
        ax.set_title("Real GDP growth by country")
        dm.place_legend(ax, loc=side)
        dm.simple_layout(fig)
        assert _findings(fig) == []
        plt.close(fig)

    def test_raw_legend_above_after_layout(self) -> None:
        fig, (ax,) = _chart()
        ax.set_title("Real GDP growth by country")
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncols=2)
        dm.simple_layout(fig)
        assert _findings(fig) == []
        plt.close(fig)

    def test_hidden_legend_is_ignored(self) -> None:
        fig, (ax,) = _chart()
        ax.set_title("Title")
        legend = ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0))
        legend.set_visible(False)
        assert _findings(fig) == []
        plt.close(fig)
