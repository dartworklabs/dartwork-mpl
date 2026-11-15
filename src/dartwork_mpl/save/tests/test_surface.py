"""``dm.save_formats`` as users call it, on real figures."""

from __future__ import annotations

import gzip
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


@pytest.fixture
def fig():
    dm.style.use("report")
    figure, ax = plt.subplots(figsize=dm.figsize("9cm"))
    ax.plot([1, 2, 3], [3, 1, 2], label="a")
    ax.legend()
    dm.simple_layout(figure)
    yield figure
    plt.close(figure)


ALL = ("png", "pdf", "svg", "svgz")


def test_re_saving_an_unchanged_figure_writes_identical_bytes(fig, tmp_path):
    dm.save_formats(fig, tmp_path / "a" / "chart", formats=ALL)
    dm.save_formats(fig, tmp_path / "b" / "chart", formats=ALL)
    for ext in ALL:
        first = (tmp_path / "a" / f"chart.{ext}").read_bytes()
        assert first == (tmp_path / "b" / f"chart.{ext}").read_bytes(), ext
    svg = (tmp_path / "a" / "chart.svg").read_bytes()
    assert b"<dc:date>" not in svg
    assert gzip.decompress((tmp_path / "a" / "chart.svgz").read_bytes()) == svg
    assert b"/CreationDate" not in (tmp_path / "a" / "chart.pdf").read_bytes()


def test_default_formats_and_saved_size(fig, tmp_path):
    dm.save_formats(fig, str(tmp_path / "chart"), dpi=100)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "chart.pdf",
        "chart.png",
    ]
    png = plt.imread(tmp_path / "chart.png")
    width, height = fig.get_size_inches() * 100
    assert png.shape[:2] == pytest.approx((height, width), abs=1)


def test_a_stem_with_a_suffix_warns_and_saves_once(fig, tmp_path):
    with pytest.warns(UserWarning, match="ends with '.png'"):
        dm.save_formats(fig, str(tmp_path / "chart.png"), formats=("png",))
    assert [p.name for p in tmp_path.iterdir()] == ["chart.png"]


def test_an_unsupported_format_writes_nothing(fig, tmp_path):
    with pytest.raises(ValueError, match="'jpgg' is not supported"):
        dm.save_formats(
            fig, tmp_path / "out" / "chart", formats=("png", "jpgg")
        )
    assert not (tmp_path / "out").exists()


def test_caller_creation_date_reaches_the_pdf(fig, tmp_path):
    dm.save_formats(
        fig,
        tmp_path / "chart",
        formats=("pdf",),
        metadata={"CreationDate": None, "Title": "Sales"},
    )
    pdf = Path(tmp_path / "chart.pdf").read_bytes()
    assert b"Sales" in pdf and b"/CreationDate" not in pdf


def test_ambient_salt_is_not_overridden(fig, tmp_path):
    with plt.rc_context({"svg.hashsalt": "mine"}):
        dm.save_formats(fig, tmp_path / "a", formats=("svg",))
        dm.save_formats(fig, tmp_path / "b", formats=("svg",))
    assert (tmp_path / "a.svg").read_bytes() == (
        tmp_path / "b.svg"
    ).read_bytes()
    assert plt.rcParams["svg.hashsalt"] is None


def test_saving_does_not_restyle_the_figure(fig, tmp_path):
    ax = fig.axes[0]
    before = [t.get_fontsize() for t in ax.get_xticklabels()]
    dm.save_formats(fig, tmp_path / "chart", formats=("png",))
    assert [t.get_fontsize() for t in ax.get_xticklabels()] == before
