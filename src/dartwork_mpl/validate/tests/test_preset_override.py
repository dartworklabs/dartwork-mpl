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
    from collections.abc import Callable

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


# ------------------------------------------------------- twins (D7, 2-CB)
# The builders draw under the active preset (``TestTwinLines`` sets it).
def _overlay(**sharing: bool) -> tuple[Figure, Axes, Axes]:
    """Two Axes made separately in one GridSpec cell, ``b`` sharing ``a``."""
    fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
    gs = fig.add_gridspec(1, 1)
    a = fig.add_subplot(gs[0])
    b = fig.add_subplot(
        gs[0],
        sharex=a if sharing.get("sharex") else None,
        sharey=a if sharing.get("sharey") else None,
    )
    b.patch.set_visible(False)
    a.plot([0, 1, 2], [1, 3, 2])
    b.plot([0, 1, 2], [30, 10, 20], color="dc.orange6")
    return fig, a, b


def _twin(kind: str) -> tuple[Figure, Axes, Axes]:
    fig, a = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    b = getattr(a, kind)()
    a.plot([0, 1, 2], [1, 3, 2])
    b.plot([0, 1, 2], [30, 10, 20], color="dc.orange6")
    return fig, a, b


def _to_right(ax: Axes) -> None:
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")


def _to_top(ax: Axes) -> None:
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")


def _sharex_overlay_moved_right() -> tuple[Figure, Axes, Axes]:
    """11-3: inspected; the layout shows its right spine."""
    fig, a, b = _overlay(sharex=True)
    _to_right(b)
    return fig, a, b


def _swapped_twinx() -> tuple[Figure, Axes, Axes]:
    """11-4: the parent's scale right, the twin's left."""
    fig, a, b = _twin("twinx")
    _to_right(a)
    b.yaxis.tick_left()
    b.yaxis.set_label_position("left")
    return fig, a, b


def _sharex_overlay_drawn_like_a_twin() -> tuple[Figure, Axes, Axes]:
    """Decision 14: x axis hidden, only its label on the right."""
    fig, a, b = _overlay(sharex=True)
    b.xaxis.set_visible(False)
    b.yaxis.set_label_position("right")
    return fig, a, b


def _inset_twinx() -> tuple[Figure, Axes, Axes]:
    fig, host = plt.subplots(figsize=dm.figsize("12cm", "standard"))
    host.plot([0, 1, 2], [1, 3, 2])
    a = host.inset_axes((0.55, 0.15, 0.35, 0.35))
    b = a.twinx()
    a.plot([0, 1, 2], [1, 3, 2])
    b.plot([0, 1, 2], [30, 10, 20], color="dc.orange6")
    return fig, a, b


def _twin_with_its_x_axis_shown() -> tuple[Figure, Axes, Axes]:
    fig, a, b = _twin("twinx")
    b.xaxis.set_visible(True)
    return fig, a, b


def _sharey_overlay_moved_top() -> tuple[Figure, Axes, Axes]:
    fig, a, b = _overlay(sharey=True)
    _to_top(b)
    return fig, a, b


def _swapped_twiny() -> tuple[Figure, Axes, Axes]:
    fig, a, b = _twin("twiny")
    _to_top(a)
    b.xaxis.tick_bottom()
    b.xaxis.set_label_position("bottom")
    return fig, a, b


def _sharey_overlay_drawn_like_a_twiny() -> tuple[Figure, Axes, Axes]:
    fig, a, b = _overlay(sharey=True)
    b.yaxis.set_visible(False)
    b.xaxis.tick_top()
    return fig, a, b


class TestTwinLines:
    """The twin role is public state; the layout's twin line is expected.

    Before 2-CB the check skipped only matplotlib's native twins and
    reported every line the layout drew on any other Axes.
    """

    @pytest.fixture(autouse=True)
    def _scientific(self) -> None:
        dm.style.use("scientific")

    @pytest.mark.parametrize(
        ("build", "owner", "side"),
        [
            pytest.param(_sharex_overlay_moved_right, "b", "right", id="11-3"),
            pytest.param(_swapped_twinx, "a", "right", id="11-4"),
            pytest.param(
                _sharex_overlay_drawn_like_a_twin, "b", "right", id="14"
            ),
            pytest.param(_inset_twinx, "b", "right", id="inset_twinx"),
            pytest.param(
                _twin_with_its_x_axis_shown, "b", "right", id="twin_x_shown"
            ),
            pytest.param(_sharey_overlay_moved_top, "b", "top", id="1-A/11-3"),
            pytest.param(_swapped_twiny, "a", "top", id="1-A/11-4"),
            pytest.param(
                _sharey_overlay_drawn_like_a_twiny, "b", "top", id="1-A/14"
            ),
        ],
    )
    def test_the_layouts_twin_line_is_not_reported(
        self,
        build: Callable[[], tuple[Figure, Axes, Axes]],
        owner: str,
        side: str,
    ) -> None:
        fig, a, b = build()
        dm.simple_layout(fig)
        assert (a if owner == "a" else b).spines[side].get_visible()
        assert _findings(fig) == []

    @pytest.mark.parametrize("preset_shows", [False, True])
    def test_a_twin_line_hidden_after_the_layout_meets_the_real_preset(
        self, preset_shows: bool
    ) -> None:
        """The record does not ask for the line back: hidden, it is
        compared with the preset, and the detail and fix say the preset's
        value."""
        if preset_shows:
            dm.style.use("scientific", **{"axes.spines.right": True})
        fig, a, b = _sharex_overlay_moved_right()
        dm.simple_layout(fig)
        assert b.spines["right"].get_visible()
        b.spines["right"].set_visible(False)
        findings = _findings(fig)
        if not preset_shows:
            assert findings == []  # scientific hides the right spine
            return
        (finding,) = findings
        assert finding.detail == {
            "axes_index": 1,
            "property": "spines.right",
            "preset": True,
            "figure": False,
        }
        assert finding.message == (
            "Axes 1: the right spine is hidden but the preset shows it; hide "
            "it only if the user asked."
        )
        assert get_fix_suggestions(finding)[1].endswith(
            "ax.spines['right'].set_visible(True)"
        )

    def test_frame_off_after_the_layout_meets_the_real_preset(self) -> None:
        """The undrawn twin line is not asked back; the preset's own left
        and bottom spines are, as on any Axes with its frame off."""
        fig, a, b = _sharex_overlay_moved_right()
        dm.simple_layout(fig)
        b.set_frame_on(False)
        findings = _findings(fig)
        assert [w.detail for w in findings] == [
            {
                "axes_index": 1,
                "property": f"spines.{side}",
                "preset": True,
                "figure": False,
            }
            for side in ("left", "bottom")
        ]
        assert [
            get_fix_suggestions(w)[1].splitlines()[-1] for w in findings
        ] == [
            "ax.spines['left'].set_visible(True)",
            "ax.spines['bottom'].set_visible(True)",
        ]

    @pytest.mark.parametrize(
        ("lay_out", "owner", "side", "index"),
        [
            pytest.param(False, "b", "right", 1, id="not_laid_out"),
            pytest.param(True, "b", "top", 1, id="side_not_settled"),
            pytest.param(True, "a", "right", 0, id="axes_not_selected"),
        ],
    )
    def test_a_line_the_layout_did_not_settle_is_reported(
        self, lay_out: bool, owner: str, side: str, index: int
    ) -> None:
        fig, a, b = _sharex_overlay_moved_right()
        if lay_out:
            dm.simple_layout(fig)
        (a if owner == "a" else b).spines[side].set_visible(True)
        (finding,) = _findings(fig)
        assert finding.detail == {
            "axes_index": index,
            "property": f"spines.{side}",
            "preset": False,
            "figure": True,
        }
        assert finding.message == (
            f"Axes {index}: the {side} spine is shown but the preset hides "
            "it; show it only if the user asked."
        )
        assert get_fix_suggestions(finding)[1].endswith(
            f"ax.spines[{side!r}].set_visible(False)"
        )

    def test_an_axes_in_the_twin_role_is_skipped_whole(self) -> None:
        """Its grid and background are not compared either (decision 14's
        overlay, which matplotlib does not call a twin); the parent's are."""
        fig, a, b = _sharex_overlay_drawn_like_a_twin()
        dm.simple_layout(fig)
        b.grid(True, axis="y")
        b.patch.set_visible(True)
        b.set_facecolor("#eeeeee")
        assert _findings(fig) == []
        a.grid(True, axis="y")
        assert [
            (w.detail["axes_index"], w.detail["property"])
            for w in _findings(fig)
        ] == [(0, "grid.y")]

    def test_a_twin_out_of_the_role_is_inspected(self) -> None:
        """A twin whose x axis shows again is compared like any Axes."""
        fig, a, b = _twin_with_its_x_axis_shown()
        dm.simple_layout(fig)
        b.grid(True, axis="y")
        assert [
            (w.detail["axes_index"], w.detail["property"])
            for w in _findings(fig)
        ] == [(1, "grid.y")]
