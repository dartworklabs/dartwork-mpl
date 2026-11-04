"""PRESET_OVERRIDE: grid, spines and backgrounds compared with the active preset."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity, VisualWarning, validate_figure
from dartwork_mpl.validate_fixes import get_fix_suggestions

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


def _findings(fig: Figure) -> list[VisualWarning]:
    """Only the PRESET_OVERRIDE findings for ``fig``."""
    return validate_figure(fig, checks=("PRESET_OVERRIDE",), quiet=True)


def _plot(preset: str = "report") -> tuple[Figure, Axes]:
    """One line chart drawn under ``preset``."""
    dm.style.use(preset)
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([0, 1, 2], [1, 3, 2])
    return fig, ax


class TestRestyleIsReported:
    """One INFO finding per Axes and property the figure changed."""

    def test_grid_added(self) -> None:
        """A y grid the preset does not draw is one finding with its detail."""
        fig, ax = _plot()
        ax.grid(axis="y", linestyle="--")
        (finding,) = _findings(fig)
        assert finding.severity is Severity.INFO
        assert finding.message == (
            "Axes 0: y grid lines are on but the preset draws none; keep "
            "them only if the user asked for a grid."
        )
        assert finding.detail == {
            "axes_index": 0,
            "property": "grid.y",
            "preset": False,
            "figure": True,
        }

    def test_grid_axis_is_respected_when_the_preset_draws_a_grid(self) -> None:
        """With a y-only preset grid, an x grid and a removed y grid differ."""
        dm.style.use("report", axes_grid=True, **{"axes.grid.axis": "y"})
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([0, 1, 2], [1, 3, 2])
        assert _findings(fig) == []
        ax.grid(True, axis="x")
        ax.grid(False, axis="y")
        details = [w.detail for w in _findings(fig)]
        assert details == [
            {
                "axes_index": 0,
                "property": "grid.x",
                "preset": False,
                "figure": True,
            },
            {
                "axes_index": 0,
                "property": "grid.y",
                "preset": True,
                "figure": False,
            },
        ]

    def test_spines_hidden_and_shown(self) -> None:
        """Hiding a preset spine and showing a hidden one are two findings."""
        fig, ax = _plot()
        ax.spines["left"].set_visible(False)
        ax.spines["top"].set_visible(True)
        findings = _findings(fig)
        assert [
            (w.detail["property"], w.detail["figure"]) for w in findings
        ] == [("spines.left", False), ("spines.top", True)]
        assert findings[0].message == (
            "Axes 0: the left spine is hidden but the preset shows it; hide "
            "it only if the user asked."
        )

    def test_frame_off_hides_every_preset_spine(self) -> None:
        """``set_frame_on(False)`` hides the spines the preset shows."""
        fig, ax = _plot("scientific")
        ax.set_frame_on(False)
        assert [w.detail["property"] for w in _findings(fig)] == [
            "spines.left",
            "spines.bottom",
        ]

    def test_axes_facecolor(self) -> None:
        """A tinted Axes background is reported with both colours."""
        fig, ax = _plot()
        ax.set_facecolor("#f5f5f5")
        (finding,) = _findings(fig)
        assert finding.detail == {
            "axes_index": 0,
            "property": "axes.facecolor",
            "preset": "#ffffff",
            "figure": "#f5f5f5",
        }

    def test_figure_facecolor(self) -> None:
        """A tinted figure background belongs to no Axes."""
        fig, _ax = _plot()
        fig.set_facecolor("#eeeeee")
        (finding,) = _findings(fig)
        assert finding.message.startswith("Figure: the figure background is")
        assert finding.detail == {
            "axes_index": None,
            "property": "figure.facecolor",
            "preset": "#ffffff",
            "figure": "#eeeeee",
        }

    def test_colour_within_one_channel_step_is_equal(self) -> None:
        """A background one 8-bit step off renders the same and is not reported."""
        fig, ax = _plot()
        ax.set_facecolor("#fefefe")
        fig.set_facecolor("#fefefe")
        assert _findings(fig) == []

    def test_rcparam_edit_after_the_preset_is_reported(self) -> None:
        """A native rcParams grid is compared with the preset, not with itself."""
        dm.style.use("report")
        plt.rcParams["axes.grid"] = True
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([0, 1], [0, 1])
        assert [w.detail["property"] for w in _findings(fig)] == [
            "grid.x",
            "grid.y",
        ]

    def test_fix_suggestion_restores_the_preset_value(self) -> None:
        """The fix keeps the user's request first and offers the preset value."""
        fig, ax = _plot()
        ax.grid(axis="y")
        (finding,) = _findings(fig)
        suggestions = get_fix_suggestions(finding)
        assert "Unless the user asked" in suggestions[0]
        assert suggestions[1].endswith("ax.grid(False, axis='y')")


class TestLegitimateDeparturesAreSkipped:
    """Axes whose look legitimately differs from the preset are not inspected."""

    def test_axis_off(self) -> None:
        """An Axes with the axis turned off draws no spines, grid or patch."""
        fig, ax = _plot()
        ax.axis("off")
        ax.set_facecolor("#eeeeee")
        assert _findings(fig) == []

    def test_hidden_axes(self) -> None:
        """An invisible Axes is not drawn at all."""
        fig, ax = _plot()
        ax.grid(True)
        ax.set_visible(False)
        assert _findings(fig) == []

    @pytest.mark.parametrize("projection", ["polar", "3d"])
    def test_non_rectilinear_projection(self, projection: str) -> None:
        """Polar and 3-D Axes draw their own grid and frame."""
        dm.style.use("report")
        fig = plt.figure(figsize=dm.figsize("9cm", "square"))
        ax = fig.add_subplot(projection=projection)
        ax.plot([0, 1, 2], [1, 2, 1])
        assert _findings(fig) == []

    @pytest.mark.parametrize("own_cax", [False, True])
    def test_colorbar_axes(self, own_cax: bool) -> None:
        """Colorbar Axes, from ``ax=`` or a caller-made ``cax``, are skipped."""
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))
        image = ax.imshow(np.arange(9).reshape(3, 3))
        if own_cax:
            fig.colorbar(image, cax=fig.add_axes((0.9, 0.1, 0.03, 0.8)))
        else:
            fig.colorbar(image, ax=ax)
        assert _findings(fig) == []

    def test_pie(self) -> None:
        """``Axes.pie`` turns the frame off itself."""
        dm.style.use("report")
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "square"))
        ax.pie([1, 2, 3])
        assert _findings(fig) == []

    @pytest.mark.parametrize("twin", ["twinx", "twiny"])
    def test_twin_is_skipped_but_the_host_is_not(self, twin: str) -> None:
        """The twin's own spine is legitimate; the host is still inspected."""
        fig, ax = _plot()
        partner = getattr(ax, twin)()
        partner.plot([0, 1, 2], [3, 1, 2])
        partner.spines["top"].set_visible(True)
        assert _findings(fig) == []
        ax.grid(axis="y")
        assert [w.detail["axes_index"] for w in _findings(fig)] == [0]

    def test_shared_axes_subplots_are_inspected(self) -> None:
        """``sharex``/``sharey`` panels are not twins and are inspected."""
        dm.style.use("report")
        fig, axes = plt.subplots(
            1, 2, figsize=dm.figsize("13cm", "wide"), sharex=True, sharey=True
        )
        for ax in axes:
            ax.plot([0, 1], [0, 1])
        axes[1].grid(axis="y")
        assert [w.detail["axes_index"] for w in _findings(fig)] == [1]

    def test_child_inset_axes(self) -> None:
        """Child Axes from ``ax.inset_axes`` are not in ``fig.axes``."""
        fig, ax = _plot()
        inset = ax.inset_axes((0.6, 0.6, 0.3, 0.3))
        inset.plot([0, 1], [1, 0])
        inset.grid(True)
        assert _findings(fig) == []

    def test_undrawn_background(self) -> None:
        """A background that is not drawn is not compared."""
        fig, ax = _plot()
        ax.set_facecolor("#eeeeee")
        ax.patch.set_visible(False)
        assert _findings(fig) == []


class TestNoActivePreset:
    """Without an active dartwork preset the check reports nothing."""

    def test_no_preset_applied(self) -> None:
        """A plain Matplotlib figure is never compared."""
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([0, 1], [0, 1])
        ax.grid(True)
        ax.set_facecolor("#eeeeee")
        assert _findings(fig) == []

    def test_native_reset_after_the_preset(self) -> None:
        """``plt.rcdefaults()`` ends the preset; default spines are not reported."""
        dm.style.use("report")
        plt.rcdefaults()
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([0, 1], [0, 1])
        assert _findings(fig) == []

    def test_preset_kwarg_is_the_callers_choice(self) -> None:
        """A grid asked for through ``style.use`` kwargs is the preset's own."""
        dm.style.use("report", axes_grid=True)
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.plot([0, 1], [0, 1])
        assert _findings(fig) == []


@pytest.mark.parametrize(
    "preset", ["scientific", "report", "presentation", "minimal", "dark"]
)
def test_untouched_preset_reports_nothing(preset: str) -> None:
    """Ordinary charts left to the preset produce no PRESET_OVERRIDE finding."""
    dm.style.use(preset)
    fig, (left, right) = plt.subplots(
        1, 2, figsize=dm.figsize("17cm", "wide"), sharey=True
    )
    left.plot([0, 1, 2, 3], [1, 3, 2, 4], label="a")
    left.scatter([0, 1, 2], [2, 1, 3], label="b")
    left.legend()
    left.set_xlabel("x")
    left.set_ylabel("y")
    right.bar(["p", "q", "r"], [3, 1, 2])
    right.set_title("Bars")
    dm.simple_layout(fig)
    assert _findings(fig) == []


class TestSaveLeavesItToReview:
    """``save_formats`` does not print PRESET_OVERRIDE; ``validate_figure`` does."""

    def test_a_deliberate_grid_prints_nothing_on_save(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # company-analysis charts draw a grid on purpose and fail on any 💡
        # printed at save (company-analysis CI, 2026-11-04).
        fig, ax = _plot("report")
        ax.grid(True, axis="y")
        dm.save_formats(fig, str(tmp_path / "out"), formats=("png",))
        assert "PRESET_OVERRIDE" not in capsys.readouterr().out
        assert [w.check_id for w in _findings(fig)] == ["PRESET_OVERRIDE"]
        plt.close(fig)

    def test_exclude_drops_a_check_and_refuses_unknown_ids(self) -> None:
        fig, ax = _plot("report")
        ax.grid(True, axis="y")
        found = validate_figure(fig, exclude=("PRESET_OVERRIDE",), quiet=True)
        assert all(w.check_id != "PRESET_OVERRIDE" for w in found)
        with pytest.raises(ValueError, match="Unknown check IDs"):
            validate_figure(fig, exclude=("PRESET_OVERRID",), quiet=True)
        plt.close(fig)
