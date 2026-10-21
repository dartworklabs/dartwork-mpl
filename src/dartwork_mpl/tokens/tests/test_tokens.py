from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


def test_scientific_semantic_token_values() -> None:
    dm.style.use("scientific")

    assert dm.tokens.fs_body() == pytest.approx(7.5)
    assert dm.tokens.fs_tick() == pytest.approx(7.0)
    assert dm.tokens.fs_title() == pytest.approx(8.5)
    assert dm.tokens.fs_annotation() == pytest.approx(6.5)
    assert dm.tokens.fs_label() == pytest.approx(7.5)
    assert dm.tokens.fs_emphasis() == pytest.approx(9.0)
    assert dm.tokens.lw_hairline() == pytest.approx(0.3)
    assert dm.tokens.lw_reference() == pytest.approx(0.3)
    assert dm.tokens.lw_trend() == pytest.approx(1.0)
    assert dm.tokens.lw_emphasis() == pytest.approx(1.6)
    assert dm.tokens.scatter_size() == pytest.approx(30.0)
    assert dm.tokens.scatter_size("small") == pytest.approx(16.0)
    assert dm.tokens.scatter_size("emphasis") == pytest.approx(45.0)
    assert dm.tokens.space() == pytest.approx(8.0)
    assert dm.tokens.space("xs") == pytest.approx(2.0)
    assert dm.tokens.space("xl") == pytest.approx(16.0)


def test_font_size_token_tracks_active_preset() -> None:
    dm.style.use("presentation")

    expected = float(plt.rcParams["font.size"])
    assert dm.tokens.fs_body() == pytest.approx(expected)


def test_as_dict_exports_all_resolved_tokens() -> None:
    dm.style.use("scientific")

    expected_keys = {
        "fs_annotation",
        "fs_tick",
        "fs_body",
        "fs_label",
        "fs_title",
        "fs_emphasis",
        "lw_hairline",
        "lw_reference",
        "lw_trend",
        "lw_emphasis",
        "scatter_small",
        "scatter_default",
        "scatter_emphasis",
        "space_xs",
        "space_sm",
        "space_md",
        "space_lg",
        "space_xl",
    }

    tokens = dm.tokens.as_dict()

    assert set(tokens) == expected_keys
    assert len(tokens) == 18
    assert all(isinstance(value, float) for value in tokens.values())


def test_version() -> None:
    assert dm.tokens.version() == "2"


def test_unknown_scatter_size_level_raises() -> None:
    with pytest.raises(ValueError, match="Valid levels"):
        dm.tokens.scatter_size("bogus")  # type: ignore[arg-type]


def test_unknown_spacing_level_raises() -> None:
    with pytest.raises(ValueError, match="Valid levels"):
        dm.tokens.space("bogus")  # type: ignore[arg-type]
