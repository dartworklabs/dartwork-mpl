"""The colour behind a value label is the colour the figure draws there."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest

import dartwork_mpl as dm
from dartwork_mpl.color import composite_layers
from dartwork_mpl.labels.measure import backdrop_layers


@pytest.mark.parametrize("alpha", [0.0, 0.4, 1.0])
def test_folded_layers_match_the_rendered_pixel(alpha: float) -> None:
    # A 100 x 100 px canvas: 2 in at 50 dpi, so pixel (50, 50) is mid-Axes.
    fig, ax = plt.subplots(figsize=dm.figsize("2in", "2in"))
    fig.set_dpi(50)
    fig.patch.set_facecolor("#336699")
    ax.set_facecolor((0.9, 0.2, 0.1, alpha))
    fig.canvas.draw()
    shown = np.asarray(fig.canvas.buffer_rgba())[50, 50, :3]  # type: ignore[attr-defined]
    folded = composite_layers(backdrop_layers([ax]))
    assert [round(c * 255) for c in folded] == pytest.approx(
        [int(v) for v in shown], abs=2
    )


def test_a_3d_axes_patch_counts_without_a_frame_switch() -> None:
    # Axes3D sets get_frame_on to None and always draws its patch.
    fig = plt.figure(facecolor="#102030")
    ax = fig.add_subplot(projection="3d", facecolor="#aabbcc")
    assert len(backdrop_layers([ax])) == 2
    ax.patch.set_visible(False)
    assert len(backdrop_layers([ax])) == 1
