"""Where a figure legend sits past the figure texts on its edge."""

from __future__ import annotations

import pytest

from dartwork_mpl.legend.decide import past_texts
from dartwork_mpl.vocab import Bottom, Box, Edge, Left, Top

LEGEND = Box(400.0, 460.0, 600.0, 490.0)


@pytest.mark.parametrize(
    ("edge", "legend", "texts", "placed"),
    [
        # A suptitle on the top edge: the legend goes under it.
        (
            Top(),
            LEGEND,
            (Box(350.0, 470.0, 650.0, 495.0),),
            Box(400.0, 440.0, 600.0, 470.0),
        ),
        # A note in the left corner meets nothing: the legend stays.
        (Top(), LEGEND, (Box(0.0, 470.0, 100.0, 495.0),), LEGEND),
        # A source line under a legend below: the legend goes over it.
        (
            Bottom(),
            Box(400.0, 5.0, 600.0, 35.0),
            (Box(300.0, 0.0, 700.0, 15.0),),
            Box(400.0, 15.0, 600.0, 45.0),
        ),
        # A supylabel by a legend on the left: the legend goes right of it.
        (
            Left(),
            Box(0.0, 200.0, 50.0, 300.0),
            (Box(0.0, 100.0, 20.0, 400.0),),
            Box(20.0, 200.0, 70.0, 300.0),
        ),
    ],
)
def test_past_texts(
    edge: Edge, legend: Box, texts: tuple[Box, ...], placed: Box
) -> None:
    assert past_texts(edge, legend, texts) == placed
