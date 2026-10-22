"""simple_layout runs on single and multi-subplot figures."""

from __future__ import annotations

import matplotlib.pyplot as plt

from dartwork_mpl.layout import simple_layout


class TestSimpleLayout:
    """Tests for simple_layout()."""

    def test_does_not_crash(self) -> None:
        """simple_layout should not raise on a basic figure."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        # Should not raise
        simple_layout(fig)
        plt.close(fig)

    def test_multisubplot(self) -> None:
        """simple_layout should handle multi-subplot figures."""
        fig, axes = plt.subplots(2, 2)
        for ax in axes.flat:
            ax.plot([1, 2, 3])
        simple_layout(fig)
        plt.close(fig)
