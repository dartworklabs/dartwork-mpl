from __future__ import annotations

import matplotlib as mpl
import matplotlib.figure
import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm
from dartwork_mpl._colors import _generated
from dartwork_mpl._colors._discrete import discrete_colors
from dartwork_mpl._colors._families import QUALITATIVE


def test_colors_returns_registered_colormap_for_continuous_family() -> None:
    cmap = dm.colors("aurora")

    assert cmap.name == "dc.aurora"
    assert dm.colors("dc.aurora").name == "dc.aurora"
    assert dm.colors("aurora", reverse=True).name == "dc.aurora_r"


def test_colors_returns_designed_discrete_forms() -> None:
    assert dm.colors("blue", n=5) == discrete_colors("blue", 5)
    assert dm.colors("dc.blue_red", n=8) == discrete_colors("blue_red", 8)
    assert dm.colors("hue", n=12) == discrete_colors("hue", 12)
    assert dm.colors("vivid", n=6) == discrete_colors("vivid", 6)


def test_colors_unknown_name_reports_nearest_family_names() -> None:
    with pytest.raises(ValueError, match="Unknown color family 'bluue'.*blue"):
        dm.colors("bluue")


def test_set_colors_defaults_to_octave_and_requires_n_for_continuous_families() -> (
    None
):
    with mpl.rc_context():
        dm.set_colors()
        rows = list(mpl.rcParams["axes.prop_cycle"])
        assert [row["color"] for row in rows] == list(
            _generated.CYCLES["octave"]
        )

        with pytest.raises(ValueError, match="blue.*requires n="):
            dm.set_colors("blue")

        dm.set_colors("blue", n=5)
        rows = list(mpl.rcParams["axes.prop_cycle"])
        assert [row["color"] for row in rows] == discrete_colors("blue", 5)


def test_set_colors_accepts_qualitative_default_and_axes_target() -> None:
    fig, ax = plt.subplots()
    try:
        dm.set_colors("vivid", ax=ax)
        rows = list(ax._get_lines._cycler_items)
        assert [row["color"] for row in rows] == discrete_colors("vivid", 8)
    finally:
        plt.close(fig)


def test_set_colors_styles_expands_colors_by_three_linestyles() -> None:
    with mpl.rc_context():
        dm.set_colors(["#111111", "#eeeeee"], styles=True)
        rows = list(mpl.rcParams["axes.prop_cycle"])

    assert len(rows) == 6
    assert [row["color"] for row in rows[:2]] == ["#111111", "#eeeeee"]
    assert all(row["linestyle"] == "-" for row in rows[:2])
    assert rows[2]["linestyle"] == "--"
    assert rows[4]["linestyle"] == ":"


def test_list_colors_returns_model_b_family_metadata() -> None:
    records = dm.list_colors()

    assert len(records) == 56
    assert set(records[0]) == {"name", "kind", "continuous", "discrete_size"}
    assert len(dm.list_colors(kind="qualitative")) == 13
    assert {
        record["kind"] for record in dm.list_colors(kind="qualitative")
    } == {"qualitative"}
    with pytest.raises(ValueError, match="Unknown color kind 'categorical'"):
        dm.list_colors(kind="categorical")


def test_show_colors_returns_preview_figure() -> None:
    fig = dm.show_colors(kind="qualitative", names=["vivid"], n=4)
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
        assert len(fig.axes) == 1
    finally:
        plt.close(fig)


def test_qualitative_colormaps_are_registered_without_reverse_variants() -> (
    None
):
    registered = [name for name in mpl.colormaps if name.startswith("dc.")]

    assert len(registered) == 99
    for name in QUALITATIVE:
        assert f"dc.{name}" in mpl.colormaps
        assert f"dc.{name}_r" not in mpl.colormaps
    assert mpl.colormaps["dc.vivid"].N == 8


@pytest.mark.parametrize(
    "name",
    [
        "".join(("get", "_", "palette")),
        "".join(("set", "_", "cycle")),
        "cycle",
        "".join(("cycle", "_", "cycler")),
        "".join(("list", "_", "palettes")),
        "".join(("list", "_", "colormaps")),
        "".join(("plot", "_", "colors")),
        "".join(("plot", "_", "colormaps")),
        "".join(("show", "_", "palette")),
        "".join(("classify", "_", "colormap")),
        "".join(("Dartwork", "Color")),
        "".join(("Dartwork", "Colormap")),
    ],
)
def test_old_color_vocabulary_removed_from_package_root(name: str) -> None:
    assert not hasattr(dm, name)
    with pytest.raises(
        AttributeError,
        match=r"Model B color API.*dm\.(colors|set_colors|list_colors|show_colors)",
    ):
        getattr(dm, name)
