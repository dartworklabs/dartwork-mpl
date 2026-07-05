from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.collections as mcollections
import matplotlib.colors as mcolors
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import matplotlib.text as mtext
import pytest
from matplotlib.figure import Figure

import dartwork_mpl as dm

from .scenarios import Scenario, all_scenarios


def _normal_hex_values(color: Any) -> set[str]:
    try:
        rgba_values = mcolors.to_rgba_array(color)
    except (TypeError, ValueError):
        return set()
    return {
        mcolors.to_hex(rgba, keep_alpha=False).lower() for rgba in rgba_values
    }


def _artist_color_hexes(fig: Figure) -> set[str]:
    colors: set[str] = set()
    for ax in fig.axes:
        for line in ax.lines:
            colors.update(_normal_hex_values(line.get_color()))
            colors.update(_normal_hex_values(line.get_markerfacecolor()))
            colors.update(_normal_hex_values(line.get_markeredgecolor()))
        for patch in ax.patches:
            colors.update(_normal_hex_values(patch.get_facecolor()))
            colors.update(_normal_hex_values(patch.get_edgecolor()))
        for collection in ax.collections:
            colors.update(_normal_hex_values(collection.get_facecolor()))
            colors.update(_normal_hex_values(collection.get_edgecolor()))
    return colors


def _image_count(fig: Figure) -> int:
    axes_images = sum(len(ax.images) for ax in fig.axes)
    quad_meshes = sum(
        1
        for ax in fig.axes
        for collection in ax.collections
        if isinstance(collection, mcollections.QuadMesh)
    )
    return axes_images + quad_meshes


def _text_content(fig: Figure) -> str:
    return "\n".join(text.get_text() for text in fig.findobj(mtext.Text))


def _active_font_path() -> Path:
    sans_serif = plt.rcParams.get("font.sans-serif", [])
    font_family = plt.rcParams.get("font.family", [])
    if isinstance(sans_serif, str):
        sans_serif = [sans_serif]
    if isinstance(font_family, str):
        font_family = [font_family]

    family = sans_serif[0] if sans_serif else font_family[0]
    font = font_manager.FontProperties(family=family)
    return Path(font_manager.findfont(font)).resolve()


def _assert_uses_bundled_font(scenario: Scenario) -> None:
    font_path = _active_font_path()
    font_dir = Path(dm.font.get_font_dir()).resolve()
    assert font_path == font_dir or font_dir in font_path.parents, (
        f"{scenario.name}: active font resolved outside bundled font dir: "
        f"{font_path}"
    )


@pytest.mark.parametrize("scenario", all_scenarios(), ids=lambda s: s.name)
def test_scenario_properties(scenario: Scenario) -> None:
    fig = scenario.build()
    try:
        expect = scenario.expect
        assert len(fig.axes) >= expect.n_axes, (
            f"{scenario.name}: expected at least {expect.n_axes} axes, "
            f"found {len(fig.axes)}"
        )

        line_count = sum(len(ax.lines) for ax in fig.axes)
        assert line_count >= expect.min_lines, (
            f"{scenario.name}: expected at least {expect.min_lines} lines, "
            f"found {line_count}"
        )

        patch_count = sum(len(ax.patches) for ax in fig.axes)
        assert patch_count >= expect.min_patches, (
            f"{scenario.name}: expected at least {expect.min_patches} patches, "
            f"found {patch_count}"
        )

        image_count = _image_count(fig)
        assert image_count >= expect.min_images, (
            f"{scenario.name}: expected at least {expect.min_images} images, "
            f"found {image_count}"
        )

        collection_count = sum(len(ax.collections) for ax in fig.axes)
        assert collection_count >= expect.min_collections, (
            f"{scenario.name}: expected at least {expect.min_collections} "
            f"collections, found {collection_count}"
        )

        actual_colors = _artist_color_hexes(fig)
        for token in expect.palette:
            expected_hex = mcolors.to_hex(token).lower()
            assert expected_hex in actual_colors, (
                f"{scenario.name}: expected palette token {token} "
                f"({expected_hex}) among artist colors {sorted(actual_colors)}"
            )

        content = _text_content(fig)
        for substring in expect.texts_contain:
            assert substring in content, (
                f"{scenario.name}: expected text substring {substring!r} "
                "in rendered Text artists"
            )

        if expect.require_ylabel:
            assert any(ax.get_ylabel() for ax in fig.axes), (
                f"{scenario.name}: expected at least one non-empty y-axis label"
            )

        _assert_uses_bundled_font(scenario)
    finally:
        plt.close(fig)
