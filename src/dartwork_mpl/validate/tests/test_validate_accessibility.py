"""Accessibility-oriented validate_figure checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.collections import PolyCollection
from matplotlib.text import Text

import dartwork_mpl as dm
from dartwork_mpl.validate import Severity, VisualWarning, validate_figure
from dartwork_mpl.validate._checks.text_contrast import check_text_contrast

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
    """The background is the figure as painted with the texts' ink hidden.

    The advanced pie's callout in the donut hole was read against the leader
    wedge (1.00:1) because the wedge's box holds the hole; contour labels and
    heatmap values were read against the bare Axes because filled
    collections and images were not looked at (T-C, 11-09). Rebuilding
    matplotlib's compositing in the check then missed image alpha arrays,
    interpolation, Axes drawing order and overlapping faces (#659 review),
    so the check now reads the rendered pixels.
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

    def test_a_marker_under_the_text_counts(self) -> None:
        fig, ax = _new_figure()
        ax.scatter([0.5], [0.5], s=4000, color=_DARK)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        _text_at_center(ax, "#222222")

        hits = _warnings_for(fig, "TEXT_CONTRAST")

        assert [h.detail["background_color"] for h in hits] == [_DARK]
        plt.close(fig)

    @pytest.mark.parametrize(("alpha", "ratio"), [(0.0, 1.0), (0.5, 3.9)])
    def test_an_image_alpha_array_shows_what_is_beneath(
        self, alpha: float, ratio: float
    ) -> None:
        # #659 review 1 / Codex: a 2D alpha was dropped, so a clear black
        # image read as opaque black behind white text.
        fig, ax = _new_figure()
        ax.imshow(
            np.zeros((2, 2)),
            cmap="gray",
            vmin=0,
            vmax=1,
            extent=(0, 1, 0, 1),
            alpha=np.full((2, 2), alpha),
        )
        _text_at_center(ax, "white", "Raster sample")

        hits = _warnings_for(fig, "TEXT_CONTRAST")

        assert [h.detail["sample"] for h in hits] == ["Raster sample"]
        assert hits[0].detail["ratio"] == pytest.approx(ratio, abs=0.1)
        plt.close(fig)

    @pytest.mark.parametrize(
        ("interpolation", "warns"), [("nearest", False), ("bilinear", True)]
    )
    def test_an_image_is_read_as_interpolated(
        self, interpolation: str, warns: bool
    ) -> None:
        # #659 review 2: the cell under the centre was read before
        # interpolation (black), not the grey bilinear draws there. Grey
        # #888888 reads on black (5.9:1), not on that grey (about 2.4:1).
        fig, ax = _new_figure()
        ax.imshow(
            [[0.0, 1.0], [0.0, 1.0]],
            cmap="gray",
            vmin=0,
            vmax=1,
            extent=(0, 1, 0, 1),
            interpolation=interpolation,
        )
        ax.text(0.4, 0.5, "Raster", color="#888888", ha="center", va="center")

        hits = _warnings_for(fig, "TEXT_CONTRAST")

        assert [h.detail["sample"] for h in hits] == (
            ["Raster"] if warns else []
        )
        plt.close(fig)

    def test_an_opaque_twin_hides_the_host_beneath(self) -> None:
        # #659 review 3 / Codex: every Axes patch was laid down before every
        # fill, so the host's black bar came back over the twin's white face.
        fig, host = _new_figure()
        host.bar(0.5, 1, width=1, color="black")
        host.set_xlim(0, 1)
        host.set_ylim(0, 1)
        twin = host.twinx()
        twin.patch.set_visible(True)
        twin.patch.set_facecolor("white")
        _text_at_center(twin, "white", "Raster sample")

        hits = _warnings_for(fig, "TEXT_CONTRAST")

        assert [
            (h.detail["sample"], h.detail["background_color"]) for h in hits
        ] == [("Raster sample", "#ffffff")]
        plt.close(fig)

    def test_overlapping_faces_are_composited(self) -> None:
        # Codex: two black faces (alpha 1.0, then 0.5) paint opaque black;
        # the last face alone read as grey and #757575 text failed at 1.16:1.
        fig, ax = _new_figure()
        square = [(0, 0), (1, 0), (1, 1), (0, 1)]
        ax.add_collection(
            PolyCollection(
                [square, square],
                facecolors=[(0, 0, 0, 1.0), (0, 0, 0, 0.5)],
                linewidths=0,
            )
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        _text_at_center(ax, "#757575")

        assert not _warnings_for(fig, "TEXT_CONTRAST")
        plt.close(fig)

    def test_a_text_at_a_missing_coordinate_is_skipped(self) -> None:
        # Codex: a nan position has no finite box; flooring it raised and
        # the whole check became CHECK_FAILED, losing every other finding.
        fig, ax = _new_figure()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.text(float("nan"), 0.5, "missing")
        ax.text(0.5, 0.5, "faint", color="#eeeeee")

        found = validate_figure(fig, checks=("TEXT_CONTRAST",), quiet=True)

        assert [(w.check_id, w.detail.get("sample")) for w in found] == [
            ("TEXT_CONTRAST", "faint")
        ]
        plt.close(fig)

    def test_the_hidden_draw_puts_every_text_back(self) -> None:
        # The ink is hidden for one draw to a renderer of the check's own:
        # colours, alphas and visibility return, and the canvas's buffer is
        # not touched.
        fig, ax = _new_figure()
        ax.plot([0, 1], [0, 1])
        ax.set_title("Title", color="#333333")
        ax.text(0.2, 0.8, "faded", color="black", alpha=0.6)
        hidden = ax.text(0.5, 0.5, "hidden", visible=False)
        texts = fig.findobj(Text)
        before = [
            (t.get_color(), t.get_alpha(), t.get_visible()) for t in texts
        ]
        fig.canvas.draw()
        buffer = bytes(fig.canvas.buffer_rgba())

        check_text_contrast(fig, fig.canvas.get_renderer())

        after = [(t.get_color(), t.get_alpha(), t.get_visible()) for t in texts]
        assert after == before
        assert not hidden.get_visible()
        assert bytes(fig.canvas.buffer_rgba()) == buffer
        plt.close(fig)

    def test_a_failed_draw_still_puts_every_text_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fig, ax = _new_figure()
        ax.set_title("Title", color="#333333")
        texts = fig.findobj(Text)
        before = [(t.get_color(), t.get_alpha()) for t in texts]
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        def broken(_renderer: object) -> None:
            raise RuntimeError("draw failed")

        monkeypatch.setattr(fig, "draw", broken)
        with pytest.raises(RuntimeError, match="draw failed"):
            check_text_contrast(fig, renderer)

        assert [(t.get_color(), t.get_alpha()) for t in texts] == before
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
        ax.set_yticks([])  # the radial tick labels sit on the dark disc
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

    def test_3d_text_is_read_where_it_is_projected(self) -> None:
        # A Text3D's own extent reads its (x, y) unprojected, off the
        # surface it sits on; text_window_extent places it as drawn.
        dm.style.use("scientific")
        fig = plt.figure(figsize=dm.figsize("9cm", "square"))
        ax = fig.add_subplot(projection="3d")
        xx, yy = np.meshgrid(np.linspace(-1, 1, 5), np.linspace(-1, 1, 5))
        ax.plot_surface(xx, yy, np.zeros_like(xx), color=_DARK, shade=False)
        ax.set_axis_off()  # its tick labels would sit on the dark surface
        # Off the centre: unprojected, (0.6, -0.6) lies far off the canvas,
        # where nothing is read; as drawn, dark text sits on the dark surface.
        ax.text(0.6, -0.6, 0, "on surface", color="#222222", ha="center")

        hits = _warnings_for(fig, "TEXT_CONTRAST")

        assert [
            (h.detail["sample"], h.detail["background_color"]) for h in hits
        ] == [("on surface", _DARK)]
        plt.close(fig)

    def test_the_text_ink_is_not_its_own_background(self) -> None:
        # Full blocks cover their box; read with the ink, white on the dark
        # patch would be "white on white".
        fig, ax = _new_figure()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.add_patch(mpatches.Rectangle((0, 0), 1, 1, facecolor=_DARK, lw=0))
        ax.text(
            0.5,
            0.5,
            "███",
            color="white",
            fontfamily="DejaVu Sans",
            ha="center",
            va="center",
        )

        assert not _warnings_for(fig, "TEXT_CONTRAST")
        plt.close(fig)

    def test_a_line_through_a_label_is_not_its_background(self) -> None:
        # The median of the box, not the one pixel at its centre.
        fig, ax = _new_figure()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axhline(0.5, color="black", lw=1)
        _text_at_center(ax, "#222222")

        assert not _warnings_for(fig, "TEXT_CONTRAST")
        plt.close(fig)

    def test_a_transparent_figure_is_read_on_white_paper(self) -> None:
        fig, ax = _new_figure()
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        _text_at_center(ax, "#222222")

        assert not _warnings_for(fig, "TEXT_CONTRAST")
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
