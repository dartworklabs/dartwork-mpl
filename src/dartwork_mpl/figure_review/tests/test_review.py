"""``dm.review``: one call for save, findings, summary and a neutral baseline diff.

Masterplan stages 3-4 (docs/superpowers/plans/2026-11-04-review-api.md): the
wrapper adds no check, no fix and no style, keeps every finding, and only
lists differences; ``allow=`` marks the ones the caller expected.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mimage
import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl.figure_review import SCHEMA, Review
from dartwork_mpl.figure_review._diff import matches
from dartwork_mpl.validate import Severity


def _lines(width="13cm", ylabel="Signal", color2=None, grid=False):
    dm.style.use("report")
    fig, ax = plt.subplots(figsize=dm.figsize(width, "standard"))
    x = np.linspace(0, 10, 51)
    ax.plot(x, np.sin(x) * 1500, label="Measured")
    ax.plot(
        x,
        np.cos(x) * 1500,
        label="Model",
        **({"color": color2} if color2 else {}),
    )
    ax.set(xlabel="Time (s)", ylabel=ylabel)
    if grid:
        ax.grid(True, axis="y")
    ax.legend()
    dm.simple_layout(fig)
    return fig


def _native(value) -> bool:
    """Every value is exactly a JSON type (no numpy scalar that equals one)."""
    if type(value) is dict:
        return all(type(k) is str and _native(v) for k, v in value.items())
    if type(value) is list:
        return all(_native(v) for v in value)
    return type(value) in (str, int, float, bool, type(None))


class TestSavesLikeSaveFormats:
    """The files are the ones a plain ``save_formats`` writes."""

    def test_png_pixels_and_pdf_bytes_match(self, tmp_path: Path) -> None:
        fig = _lines()
        dm.save_formats(fig, str(tmp_path / "plain"), validate=False)
        r = dm.review(fig, tmp_path / "rev", quiet=True)
        plt.close(fig)
        assert set(r.paths) == {"png", "pdf", "json"}
        assert np.array_equal(
            mimage.imread(tmp_path / "plain.png"), mimage.imread(r.paths["png"])
        )
        assert (tmp_path / "plain.pdf").read_bytes() == r.paths[
            "pdf"
        ].read_bytes()

    def test_save_kwargs_and_formats_pass_through(self, tmp_path: Path) -> None:
        fig = _lines()
        r = dm.review(fig, tmp_path / "f", formats=("png",), dpi=50, quiet=True)
        plt.close(fig)
        assert set(r.paths) == {"png", "json"}
        height, width = mimage.imread(r.paths["png"]).shape[:2]
        w_in, h_in = fig.get_size_inches()
        assert abs(width - w_in * 50) <= 1 and abs(height - h_in * 50) <= 1


class TestFindings:
    """Every finding of validate_figure, untouched; complete is not a pass."""

    def test_findings_equal_validate_figure_including_preset_override(
        self, tmp_path: Path
    ) -> None:
        fig = _lines(grid=True)
        r = dm.review(fig, tmp_path / "f", quiet=True)
        direct = dm.validate_figure(fig, quiet=True)
        plt.close(fig)

        def key(w):
            return (w.severity, w.check_id, w.message, w.detail)

        assert [key(w) for w in r.findings] == [key(w) for w in direct]
        assert "PRESET_OVERRIDE" in {w.check_id for w in r.findings}
        assert r.complete is True and r.incomplete_checks == []

    def test_a_check_that_cannot_run_makes_the_review_incomplete(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from dartwork_mpl.validate._checks import _registry

        monkeypatch.setattr(_registry, "_REGISTRY", dict(_registry._REGISTRY))

        @_registry.register_check("FAULT_REVIEW", order=55)
        def fail(fig, renderer):
            """Raise a controlled bbox failure."""
            raise RuntimeError("controlled check failure")

        fig = _lines()
        r = dm.review(fig, tmp_path / "f", quiet=True)
        plt.close(fig)
        assert r.complete is False
        assert r.incomplete_checks == ["FAULT_REVIEW"]
        assert "CHECK_FAILED" in {w.check_id for w in r.warnings}
        doc = json.loads(r.paths["json"].read_text(encoding="utf-8"))
        assert doc["complete"] is False
        assert doc["incomplete_checks"] == ["FAULT_REVIEW"]

    def test_a_save_failure_raises_before_any_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import dartwork_mpl.figure_review as fr

        ran: list[str] = []
        monkeypatch.setattr(
            fr, "validate_figure", lambda *a, **k: ran.append("v") or []
        )
        fig = _lines()
        with pytest.raises(ValueError, match="not supported"):
            dm.review(fig, tmp_path / "f", formats=("nope",), quiet=True)
        plt.close(fig)
        assert ran == []
        assert not (tmp_path / "f.review.json").exists()


class TestSummary:
    """Titles, labels, series, ranges, legend and text outside the canvas."""

    def test_line_chart_fields(self, tmp_path: Path) -> None:
        fig = _lines()
        fig.axes[0].set_title("Left", loc="left")
        dm.simple_layout(fig)
        s = dm.review(fig, tmp_path / "f", quiet=True).summary
        plt.close(fig)
        ax = s["axes"][0]
        assert ax["title"]["left"]["text"] == "Left"
        assert ax["xlabel"]["text"] == "Time (s)"
        assert ax["ylabel"]["text"] == "Signal"
        assert [e["label"] for e in ax["series"]] == ["Measured", "Model"]
        assert {e["kind"] for e in ax["series"]} == {"line"}
        assert ax["series"][0]["n"] == 51
        assert ax["legends"][0]["labels"] == ["Measured", "Model"]
        assert ax["legends"][0]["inside"] is True
        assert ax["yticks"]["labels"][0] == "\N{MINUS SIGN}1,500"
        assert s["outside_canvas"] == []

    def test_bar_scatter_area_image_and_twin(self, tmp_path: Path) -> None:
        dm.style.use("report")
        fig, (a, b) = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
        a.bar(["A", "B", "C"], [3, 5, 2], label="Sales")
        twin = a.twinx()
        twin.plot([0, 1, 2], [10, 20, 15], color="oc.gray7")
        b.scatter([1, 2, 3], [3, 1, 2], label="points")
        b.fill_between([0, 1, 2], [0, 1, 0], alpha=0.3)
        b.imshow(np.arange(6).reshape(2, 3), extent=(0, 1, 0, 1))
        dm.simple_layout(fig)
        s = dm.review(fig, tmp_path / "f", quiet=True).summary
        plt.close(fig)
        assert len(s["axes"]) == 3
        assert s["axes"][0]["series"][0]["kind"] == "bar"
        assert s["axes"][0]["series"][0]["n"] == 3
        assert s["axes"][0]["xticks"]["labels"] == ["A", "B", "C"]
        kinds = [e["kind"] for e in s["axes"][1]["series"]]
        assert kinds == ["scatter", "area", "image"]
        assert s["axes"][2]["series"][0]["kind"] == "line"

    def test_polar_axes_and_text_outside_the_canvas(
        self, tmp_path: Path
    ) -> None:
        dm.style.use("report")
        fig = plt.figure(figsize=dm.figsize("9cm", "square"))
        ax = fig.add_subplot(projection="polar")
        ax.plot([0, 1, 2], [1, 2, 1])
        fig.text(0.95, 0.5, "a note that runs past the right edge")
        s = dm.review(fig, tmp_path / "f", quiet=True).summary
        plt.close(fig)
        assert s["axes"][0]["kind"] == "polar"
        (out,) = s["outside_canvas"]
        assert out["where"] == "figure.texts[0]"
        assert out["beyond_px"]["right"] > 0
        assert _native(s)

    def test_summary_survives_the_json_round_trip(self, tmp_path: Path) -> None:
        dm.style.use("report")
        fig, (a, b) = plt.subplots(1, 2, figsize=dm.figsize("17cm", "wide"))
        dates = np.arange("2024-01", "2025-01", dtype="datetime64[M]")
        a.plot(dates, np.r_[np.nan, np.arange(11.0)], label="with a gap")
        b.plot(["a", "b"], [1, 2], label="categories")
        r = dm.review(fig, tmp_path / "f", quiet=True)
        plt.close(fig)
        doc = json.loads(r.paths["json"].read_text(encoding="utf-8"))
        assert doc["schema"] == SCHEMA
        assert doc["summary"] == r.summary
        assert json.loads(json.dumps(r.summary, allow_nan=False)) == r.summary
        assert _native(r.summary)

    def test_nothing_about_files_or_time_enters_the_summary(
        self, tmp_path: Path
    ) -> None:
        fig = _lines()
        r = dm.review(fig, tmp_path / "some-stem-name", quiet=True)
        plt.close(fig)
        assert "some-stem-name" not in json.dumps(r.summary)


class TestBaseline:
    """A neutral list of what differs; allow= only marks expected paths."""

    def test_same_figure_under_another_stem_lists_nothing(
        self, tmp_path: Path
    ) -> None:
        dm.review(_lines(), tmp_path / "v1", quiet=True)
        for baseline in (tmp_path / "v1", str(tmp_path / "v1.review.json")):
            r = dm.review(
                _lines(), tmp_path / "v1b", baseline=baseline, quiet=True
            )
            assert r.changes == []
        plt.close("all")

    def test_one_label_edit_is_one_change(self, tmp_path: Path) -> None:
        r1 = dm.review(_lines(), tmp_path / "v1", quiet=True)
        r2 = dm.review(
            _lines(ylabel="Amplitude"),
            tmp_path / "v2",
            baseline=r1,
            allow=["axes[0].ylabel.*"],
            quiet=True,
        )
        plt.close("all")
        assert [(c.path, c.before, c.after, c.allowed) for c in r2.changes] == [
            ("axes[0].ylabel.text", "Signal", "Amplitude", True)
        ]
        assert r2.unexpected == []

    def test_one_series_colour_edit_is_one_change(self, tmp_path: Path) -> None:
        dm.review(_lines(), tmp_path / "v1", quiet=True)
        r = dm.review(
            _lines(color2="#ff0000"),
            tmp_path / "v2",
            baseline=tmp_path / "v1",
            quiet=True,
        )
        plt.close("all")
        assert [c.path for c in r.changes] == ["axes[0].series[1].color"]
        assert [c.path for c in r.unexpected] == ["axes[0].series[1].color"]

    def test_a_width_edit_moves_size_and_position_only(
        self, tmp_path: Path
    ) -> None:
        dm.review(_lines(), tmp_path / "v1", quiet=True)
        r = dm.review(
            _lines(width="9cm"),
            tmp_path / "v2",
            baseline=tmp_path / "v1",
            quiet=True,
        )
        plt.close("all")
        assert [c.path for c in r.changes] == [
            "figure.size_in",
            "axes[0].position",
        ]

    def test_data_changes_show_as_a_digest(self, tmp_path: Path) -> None:
        dm.style.use("report")

        def draw(y):
            fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
            ax.plot([0, 1, 2], y)
            ax.set_ylim(0, 5)
            return fig

        dm.review(draw([1, 2, 3]), tmp_path / "v1", quiet=True)
        r = dm.review(
            draw([1, 2, 4]),
            tmp_path / "v2",
            baseline=tmp_path / "v1",
            quiet=True,
        )
        plt.close("all")
        assert [c.path for c in r.changes] == ["axes[0].series[0].data"]

    def test_allow_patterns_treat_only_star_as_a_wildcard(self) -> None:
        assert matches("axes[0].ylabel.text", "axes[0].ylabel.*")
        assert matches("axes[3].ylabel.size", "axes[*].ylabel.*")
        assert not matches("axes0.ylabel.text", "axes[0].ylabel.*")
        assert not matches("axes[0].xlabel.text", "axes[0].ylabel.*")


class TestRefusals:
    """Ambiguous stems and missing baselines refuse before anything is written."""

    def test_a_stem_with_an_image_suffix(self, tmp_path: Path) -> None:
        fig = _lines()
        with pytest.raises(ValueError, match="image suffix"):
            dm.review(fig, tmp_path / "f.png", quiet=True)
        plt.close(fig)
        assert list(tmp_path.iterdir()) == []

    def test_a_missing_baseline(self, tmp_path: Path) -> None:
        fig = _lines()
        with pytest.raises(ValueError, match="not found"):
            dm.review(
                fig, tmp_path / "v2", baseline=tmp_path / "v1", quiet=True
            )
        plt.close(fig)
        assert list(tmp_path.iterdir()) == []

    def test_validate_arguments(self, tmp_path: Path) -> None:
        fig = _lines()
        with pytest.raises(TypeError, match="validates itself"):
            dm.review(fig, tmp_path / "f", validate=True)
        plt.close(fig)


class TestReport:
    """The printout groups findings; Review.findings keeps them all."""

    def test_printed_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        fig = _lines(grid=True)
        r = dm.review(fig, tmp_path / "f")
        plt.close(fig)
        out = capsys.readouterr().out
        assert out.startswith("[REVIEW] saved ")
        assert "PRESET_OVERRIDE x" in out
        assert "complete is not a pass" in out
        assert out.strip() == str(r)

    def test_quiet_prints_nothing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        fig = _lines()
        r = dm.review(fig, tmp_path / "f", quiet=True)
        plt.close(fig)
        assert capsys.readouterr().out == ""
        assert isinstance(r, Review)
        assert all(
            w.severity in (Severity.WARNING, Severity.INFO) for w in r.findings
        )


def _changes(tmp_path: Path, draw, edit, allow=()):
    """Review ``draw()`` as v1 and ``edit()`` against it; the change paths."""
    dm.review(draw(), tmp_path / "v1", quiet=True)
    r = dm.review(
        edit(),
        tmp_path / "v2",
        baseline=tmp_path / "v1",
        allow=allow,
        quiet=True,
    )
    plt.close("all")
    return r


class TestEditsTheSummaryMustSee:
    """Edits that change the PNG must show in the changes (codex review 5)."""

    def test_tiny_values_reordered_and_an_image_reshaped(
        self, tmp_path: Path
    ) -> None:
        def line(y):
            def draw():
                fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
                ax.plot([0, 1, 2], y)
                ax.set_ylim(0, 4e-12)
                return fig

            return draw

        r = _changes(
            tmp_path, line([1e-12, 2e-12, 3e-12]), line([3e-12, 1e-12, 2e-12])
        )
        assert [c.path for c in r.changes] == ["axes[0].series[0].data"]

        def image(shape):
            def draw():
                fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
                ax.imshow(np.arange(6).reshape(shape), extent=(0, 1, 0, 1))
                return fig

            return draw

        r = _changes(tmp_path / "img", image((2, 3)), image((3, 2)))
        assert "axes[0].series[0].data" in [c.path for c in r.changes]

    def test_a_masked_scatter_point_that_appears(self, tmp_path: Path) -> None:
        def draw(reveal):
            fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
            sc = ax.scatter([0, 1, 2], np.ma.array([1, 2, 3], mask=[0, 1, 0]))
            if reveal:
                sc.set_offsets([[0, 1], [1, 2], [2, 3]])
            ax.set(xlim=(-1, 3), ylim=(0, 4))
            return fig

        r = _changes(tmp_path, lambda: draw(False), lambda: draw(True))
        assert "axes[0].series[0].data" in [c.path for c in r.changes]

    def test_inset_and_subfigure_text(self, tmp_path: Path) -> None:
        def inset(label):
            def draw():
                fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
                child = ax.inset_axes([0.6, 0.6, 0.3, 0.3])
                child.set_ylabel(label)
                return fig

            return draw

        r = _changes(tmp_path, inset("A"), inset("B"))
        assert [c.path for c in r.changes] == ["axes[0].insets[0].ylabel.text"]

        def sub(title):
            def draw():
                fig = plt.figure(figsize=dm.figsize("13cm", "wide"))
                left, _ = fig.subfigures(1, 2)
                left.subplots()
                left.suptitle(title)
                return fig

            return draw

        r = _changes(tmp_path / "sf", sub("A"), sub("B"))
        assert [c.path for c in r.changes] == [
            "figure.subfigures[0].suptitle.text"
        ]

    def test_3d_reads_z_and_ignores_the_view(self, tmp_path: Path) -> None:
        def draw(zlabel="", elev=30):
            fig = plt.figure(figsize=dm.figsize("9cm", "square"))
            ax = fig.add_subplot(projection="3d")
            ax.plot([0, 1, 2], [0, 1, 0], [1, 2, 3])
            ax.set_zlabel(zlabel)
            ax.view_init(elev=elev, azim=-60)
            return fig

        r = _changes(tmp_path, draw, lambda: draw(zlabel="Altitude"))
        own = [
            c.path for c in r.changes if not c.path.startswith("outside_canvas")
        ]
        assert own == ["axes[0].zlabel.text"]
        r = _changes(tmp_path / "view", draw, lambda: draw(elev=60))
        assert not any(c.path.endswith(".data") for c in r.changes)
        assert not any(
            "ticks" in o["where"] for o in r.summary["outside_canvas"]
        )

    def test_a_kept_first_legend_and_legend_titles(
        self, tmp_path: Path
    ) -> None:
        def draw(first="x", title="T1"):
            fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
            (a,) = ax.plot([0, 1], [0, 1])
            (b,) = ax.plot([0, 1], [1, 0])
            kept = ax.legend([a], [first], title=title, loc="upper left")
            ax.add_artist(kept)
            ax.legend([b], ["y"], loc="lower right")
            return fig

        paths = [
            c.path
            for c in _changes(tmp_path, draw, lambda: draw(first="z")).changes
        ]
        assert paths == ["axes[0].legends[0].labels"]
        paths = [
            c.path
            for c in _changes(
                tmp_path / "t", draw, lambda: draw(title="T2")
            ).changes
        ]
        assert paths == ["axes[0].legends[0].title"]

    def test_one_bar_or_one_point_recoloured(self, tmp_path: Path) -> None:
        def bars(highlight):
            def draw():
                fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
                drawn = ax.bar(["a", "b", "c"], [1, 2, 3])
                if highlight:
                    drawn[1].set_facecolor("red")
                return fig

            return draw

        r = _changes(tmp_path, bars(False), bars(True))
        assert [c.path for c in r.changes] == ["axes[0].series[0].colors"]

        def points(highlight):
            def draw():
                fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
                colors = [
                    "#1f77b4",
                    "red" if highlight else "#1f77b4",
                    "#1f77b4",
                ]
                ax.scatter([0, 1, 2], [1, 2, 3], c=colors)
                return fig

            return draw

        r = _changes(tmp_path / "pt", points(False), points(True))
        assert [c.path for c in r.changes] == ["axes[0].series[0].colors"]

    def test_errorbar_and_histogram_keep_their_names(
        self, tmp_path: Path
    ) -> None:
        fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
        ax.errorbar([0, 1], [1, 2], yerr=0.1, label="Observed")
        ax.hist([1, 2, 2, 3], label="Counts")
        s = dm.review(fig, tmp_path / "f", quiet=True).summary
        plt.close(fig)
        labels = {e["label"] for e in s["axes"][0]["series"]}
        assert {"Observed", "Counts"} <= labels
        assert not any(label.startswith("_") for label in labels)

    def test_a_first_text_or_legend_adds_only_its_fields(
        self, tmp_path: Path
    ) -> None:
        def draw(text=False, legend=False):
            fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
            ax.plot([0, 1], [0, 1], label="x")
            if text:
                ax.text(0.5, 0.5, "note")
            if legend:
                ax.legend()
            return fig

        r = _changes(
            tmp_path,
            draw,
            lambda: draw(text=True),
            allow=["axes[0].texts[*].*"],
        )
        assert r.unexpected == []
        r = _changes(
            tmp_path / "lg",
            draw,
            lambda: draw(legend=True),
            allow=["axes[0].legends[*].*"],
        )
        assert r.unexpected == []

    def test_a_format_with_a_leading_dot(self, tmp_path: Path) -> None:
        fig = _lines()
        r = dm.review(fig, tmp_path / "chart", formats=(".png",), quiet=True)
        plt.close(fig)
        assert r.paths["png"] == tmp_path / "chart.png"
        assert r.paths["png"].is_file()
        assert not (tmp_path / "chart..png").exists()


class TestRecheckFindings:
    """The three findings of the codex re-check (review 6)."""

    def test_a_3d_line_collection_edit(self, tmp_path: Path) -> None:
        from mpl_toolkits.mplot3d.art3d import Line3DCollection

        def draw(end):
            def make():
                fig = plt.figure(figsize=dm.figsize("9cm", "square"))
                ax = fig.add_subplot(projection="3d")
                ax.add_collection3d(Line3DCollection([[[0, 0, 0], end]]))
                return fig

            return make

        r = _changes(tmp_path, draw([1, 1, 1]), draw([1, 0, 1]))
        assert "axes[0].series[0].data" in [c.path for c in r.changes]

    def test_turning_a_3d_scatter_changes_no_sizes_or_colours(
        self, tmp_path: Path
    ) -> None:
        def draw(elev=30, azim=-60):
            def make():
                fig = plt.figure(figsize=dm.figsize("9cm", "square"))
                ax = fig.add_subplot(projection="3d")
                ax.scatter(
                    [0, 1, 2],
                    [0, 1, 2],
                    [0, 1, 2],
                    c=["red", "green", "blue"],
                    s=[10, 20, 30],
                    depthshade=False,
                )
                ax.view_init(elev, azim)
                return fig

            return make

        r = _changes(tmp_path, draw(), draw(0, 180))
        series = [c.path for c in r.changes if ".series[" in c.path]
        assert series == []

    def test_canvas_paths_index_the_summary_texts(self, tmp_path: Path) -> None:
        fig = plt.figure(figsize=dm.figsize("13cm", "wide"))
        left, _ = fig.subfigures(1, 2)
        ax = left.subplots()
        left.text(0.5, 0.5, "hidden", visible=False)
        left.text(2, 2, "outside")
        ax.text(0.5, 0.5, "hidden too", visible=False)
        ax.text(5, 5, "far out", transform=ax.transAxes)
        s = dm.review(fig, tmp_path / "f", quiet=True).summary
        plt.close(fig)
        sub_texts = [e["text"] for e in s["figure"]["subfigures"][0]["texts"]]
        ax_texts = [e["text"] for e in s["axes"][0]["texts"]]
        where = {o["text"]: o["where"] for o in s["outside_canvas"]}
        assert sub_texts == ["outside"]
        assert where["outside"] == "figure.subfigures[0].texts[0]"
        assert ax_texts == ["far out"]
        assert where["far out"] == "axes[0].texts[0]"
