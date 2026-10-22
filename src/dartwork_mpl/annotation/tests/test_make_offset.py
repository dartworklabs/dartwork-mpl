"""make_offset builds a points offset transform for a figure."""

from __future__ import annotations

import matplotlib.pyplot as plt

from dartwork_mpl.annotation import make_offset


class TestMakeOffset:
    """Tests for make_offset()."""

    def test_creates_transform(self) -> None:
        from matplotlib.transforms import ScaledTranslation

        fig, _ax = plt.subplots()
        offset = make_offset(4, -4, fig)
        assert isinstance(offset, ScaledTranslation)
        plt.close(fig)

    def test_zero_offset(self) -> None:

        fig, _ax = plt.subplots()
        offset = make_offset(0, 0, fig)
        assert offset is not None
        plt.close(fig)
