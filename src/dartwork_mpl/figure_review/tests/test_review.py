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
        assert ax["legend"]["labels"] == ["Measured", "Model"]
        assert ax["legend"]["inside"] is True
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
