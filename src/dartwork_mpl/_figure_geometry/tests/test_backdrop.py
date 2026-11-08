"""``backdrop_layers`` lists the patch colours behind data; folded they match the drawn pixel."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl._colors.contrast import composite_layers, composite_over
from dartwork_mpl._figure_geometry import backdrop_layers


def test_composite_over_blends_by_alpha() -> None:
    assert composite_over((1.0, 0.0, 0.0, 0.25), (1.0, 1.0, 1.0)) == (
        1.0,
        0.75,
        0.75,
    )
    assert composite_over((0.2, 0.4, 0.6, 1.0), (1.0, 1.0, 1.0)) == (
        0.2,
        0.4,
        0.6,
    )
    assert composite_layers([]) == (1.0, 1.0, 1.0)


def test_layers_run_figure_subfigure_then_axes_by_zorder() -> None:
    fig = plt.figure(facecolor="#102030")
    sub = fig.subfigures(1, 1, facecolor="#405060", frameon=True)
    low = sub.add_subplot(111, facecolor="#aabbcc")
    high = low.twinx()
    high.set_zorder(5)
    low.set_zorder(1)
    high.set_frame_on(True)
    high.patch.set_visible(True)
    high.patch.set_facecolor("#112233")
    layers = backdrop_layers([high, low])
    assert [round(c * 255) for c in layers[0][:3]] == [16, 32, 48]
    assert [round(c * 255) for c in layers[1][:3]] == [64, 80, 96]
    assert [round(c * 255) for c in layers[2][:3]] == [170, 187, 204]
    assert [round(c * 255) for c in layers[3][:3]] == [17, 34, 51]
    plt.close(fig)


def test_hidden_patches_add_nothing() -> None:
    fig, ax = plt.subplots()
    fig.patch.set_visible(False)
    ax.set_frame_on(False)
    assert backdrop_layers([ax]) == []
    plt.close(fig)


def test_a_3d_axes_patch_counts_without_a_frame_switch() -> None:
    # Axes3D sets get_frame_on to None and always draws its patch.
    fig = plt.figure(facecolor="#102030")
    ax = fig.add_subplot(projection="3d", facecolor="#aabbcc")
    layers = backdrop_layers([ax])
    assert [[round(c * 255) for c in layer[:3]] for layer in layers] == [
        [16, 32, 48],
        [170, 187, 204],
    ]
    ax.patch.set_visible(False)
    assert len(backdrop_layers([ax])) == 1
    plt.close(fig)


@pytest.mark.parametrize("alpha", [0.0, 0.4, 1.0])
def test_folded_layers_match_the_rendered_pixel(alpha: float) -> None:
    # A 100 x 100 px canvas: 2 in at 50 dpi, so pixel (50, 50) is mid-Axes.
    fig, ax = plt.subplots(figsize=dm.figsize("2in", "2in"))
    fig.set_dpi(50)
    fig.patch.set_facecolor("#336699")
    ax.set_facecolor((0.9, 0.2, 0.1, alpha))
    fig.canvas.draw()
    pixels = np.asarray(fig.canvas.buffer_rgba())  # type: ignore[attr-defined]
    shown = pixels[50, 50, :3]
    folded = composite_layers(backdrop_layers([ax]))
    assert [round(c * 255) for c in folded] == pytest.approx(
        [int(v) for v in shown], abs=2
    )
    plt.close(fig)
