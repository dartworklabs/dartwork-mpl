"""Presets through the public surface, as a chart script uses them."""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


def _pos():
    return mcolors.get_named_colors_mapping()["dc.pos"]


def test_sizes_follow_the_preset():
    dm.style.use("scientific")
    assert (dm.fs(0), dm.fs(-1), dm.lw(1), dm.fw(1)) == (7.5, 6.5, 2.0, 300)
    dm.style.use("presentation")
    assert dm.fs(1) == pytest.approx(19.5 + 2.6)
    assert dm.lw(1) == pytest.approx(2.6 * 2)


def test_overrides_win_and_a_rejected_one_changes_nothing():
    dm.style.use("report", font_size=12)
    assert mpl.rcParams["font.size"] == 12
    with pytest.raises(ValueError):
        dm.style.use("dark", lines_linewidth="thick")
    assert dm.style.active_presets() == ("report",)


def test_a_new_preset_clears_the_last_but_keeps_your_edits():
    plt.rcParams["hist.bins"] = 20
    dm.style.use("dark")
    dm.style.use("report")
    assert mpl.rcParams["figure.facecolor"] == "white"
    assert mpl.rcParams["hist.bins"] == 20
    with dm.style.context("report"):  # not dark underneath, either
        dm.style.use("dark")
    with dm.style.context("report"):
        assert mpl.rcParams["axes.facecolor"] == "white"


def test_context_restores_rc_role_colours_and_active_preset():
    dm.style.use("report")
    before, pos = dict(mpl.rcParams), _pos()
    with dm.style.context("presentation-kr"):
        assert dm.style.active_presets() == ("presentation-kr",)
        assert _pos() != pos
        assert dm.fs(1) - dm.fs(0) == pytest.approx(2.6)
    assert dict(mpl.rcParams) == before
    assert (_pos(), dm.style.active_presets()) == (pos, ("report",))


def test_a_native_reset_drops_the_preset():
    dm.style.use("presentation")
    plt.rcdefaults()
    assert dm.fs(1) - dm.fs(0) == pytest.approx(1.0)


def test_presentation_is_scientific_times_the_slide_scale():
    dm.style.use("scientific")
    paper = dm.style.load_style_dict("font-scientific")
    slides = dm.style.load_style_dict("font-presentation")
    sizes = [k for k, v in paper.items() if isinstance(v, float)]
    assert len(sizes) >= 8
    for key in sizes:
        assert slides[key] == pytest.approx(paper[key] * dm.style.SLIDE_SCALE)
