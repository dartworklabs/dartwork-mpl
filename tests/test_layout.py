"""Tests for layout module."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from dartwork_mpl.layout import (
    _measure_overflow,
    get_bounding_box,
    simple_layout,
)


class TestGetBoundingBox:
    """Tests for get_bounding_box()."""

    def test_single_axes(self) -> None:
        """Bounding box of a single subplot."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        fig.canvas.draw()

        boxes = [ax.get_tightbbox()]
        result = get_bounding_box(boxes)

        assert len(result) == 4
        min_x, min_y, width, height = result
        assert width > 0
        assert height > 0
        plt.close(fig)

    def test_multiple_axes(self) -> None:
        """Bounding box of multiple subplots should enclose all."""
        fig, axes = plt.subplots(1, 2)
        for ax in axes:
            ax.plot([1, 2, 3])
        fig.canvas.draw()

        boxes = [ax.get_tightbbox() for ax in axes]
        result = get_bounding_box(boxes)

        min_x, min_y, width, height = result
        assert width > 0
        assert height > 0
        plt.close(fig)


class TestSimpleLayout:
    """Tests for the new direct-calc ``simple_layout``."""

    def test_single_subplot(self) -> None:
        """simple_layout should not raise on a basic figure and must
        return None (the function no longer exposes the optimizer
        result that the legacy scipy-based implementation returned)."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        result = simple_layout(fig)
        assert result is None
        plt.close(fig)

    def test_multi_subplot(self) -> None:
        """simple_layout should handle 2x2 subplots."""
        fig, axes = plt.subplots(2, 2)
        for ax in axes.flat:
            ax.plot([1, 2, 3])
        result = simple_layout(fig)
        assert result is None
        plt.close(fig)

    def test_margin_units(self) -> None:
        """Accepts Length, percentage string, unit string, and bare
        figure-fraction floats."""
        import dartwork_mpl as dm

        for margin in (0, 0.05, "5%", "5mm", dm.cm(0.5), dm.mm(5)):
            fig, ax = plt.subplots()
            ax.plot([1, 2, 3])
            simple_layout(fig, margin=margin)
            plt.close(fig)

    def test_per_side_overrides(self) -> None:
        """``ml/mr/mt/mb`` should override the global ``margin``."""
        import dartwork_mpl as dm

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        simple_layout(fig, margin="2%", ml=dm.mm(5), mr="0%")
        plt.close(fig)

    def test_verbose_mode(self, capsys) -> None:
        """Verbose mode should print layout info."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        simple_layout(fig, verbose=True)
        captured = capsys.readouterr()
        assert "[simple_layout]" in captured.out
        plt.close(fig)

    def test_nested_gridspec_targeted_layout_moves_axes(self) -> None:
        """``use_all_axes=False`` with a nested GridSpec must actually
        measure that gridspec's axes (L1: the filter compared the
        *root* gridspec id against ``ax.get_gridspec()``'s *immediate*
        id, so nested targets silently no-opped)."""
        from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

        fig = plt.figure(figsize=(6, 4))
        outer = GridSpec(1, 2, figure=fig)
        inner = GridSpecFromSubplotSpec(2, 1, subplot_spec=outer[0])
        ax0 = fig.add_subplot(inner[0])
        ax1 = fig.add_subplot(inner[1])
        for ax in (ax0, ax1):
            ax.plot([1, 2, 3])
            ax.set_ylabel("A long y label to create overhang")
        before = ax0.get_position().bounds
        simple_layout(fig, gs=inner, use_all_axes=False)
        after = ax0.get_position().bounds
        assert before != after, "nested-gs targeted layout silently no-opped"
        plt.close(fig)

    def test_hidden_axes_do_not_constrain_layout(self) -> None:
        """An invisible panel must not push the visible axes' margins
        (L2: hidden axes kept a valid window extent and injected
        overhang)."""
        # Hidden panel with an extreme ylabel: if it constrained the
        # layout, the visible axes' left edge would be pushed far right.
        fig_hidden, axes = plt.subplots(1, 2, figsize=(6, 4))
        axes[0].plot([1, 2, 3])
        axes[0].set_ylabel("y")
        axes[1].plot([1, 2, 3])
        axes[1].set_ylabel("An extremely long hidden label " * 3)
        axes[1].set_visible(False)
        simple_layout(fig_hidden)
        hidden_case_left = axes[0].get_position().x0

        # Same figure without the hidden panel's label for comparison.
        fig_ref, axes_ref = plt.subplots(1, 2, figsize=(6, 4))
        axes_ref[0].plot([1, 2, 3])
        axes_ref[0].set_ylabel("y")
        axes_ref[1].plot([1, 2, 3])
        axes_ref[1].set_visible(False)
        simple_layout(fig_ref)
        ref_left = axes_ref[0].get_position().x0

        assert abs(hidden_case_left - ref_left) < 1e-9, (
            "hidden axes' artists leaked into the layout margins"
        )
        plt.close(fig_hidden)
        plt.close(fig_ref)


class TestMeasureOverflowLegend:
    """Regression: _measure_overflow must include legend bbox so
    simple_layout can pad for legends positioned outside axes via
    bbox_to_anchor."""

    def test_legend_outside_axes_detected(self) -> None:
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        for i in range(20):
            ax.plot([0, 1], [i, i + 1], label=f"S{i:02d}")
        ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
        ax.set_ylabel("Y")
        overflow = _measure_overflow(fig)
        assert overflow["right"] > 5.0, (
            f"legend outside axes should contribute right overflow; "
            f"got {overflow}"
        )
        plt.close(fig)

    def test_no_legend_no_extra_overflow(self) -> None:
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        ax.plot([1, 2, 3])
        ax.set_ylabel("Y")
        overflow = _measure_overflow(fig)
        assert all(v == 0.0 for v in overflow.values()), overflow
        plt.close(fig)

    def test_legend_inside_axes_no_overflow(self) -> None:
        import dartwork_mpl as dm

        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        ax.plot([1, 2, 3], label="A")
        ax.legend(loc="best")
        ax.set_ylabel("Y")
        overflow = _measure_overflow(fig)
        assert all(v == 0.0 for v in overflow.values()), overflow
        plt.close(fig)


class TestTightCrop:
    """First dedicated coverage for the public ``tight_crop`` (~130
    lines of pixel-space math that previously had zero tests)."""

    def test_no_axes_returns_original_size(self) -> None:
        from dartwork_mpl.layout import tight_crop

        fig = plt.figure(figsize=(4.0, 3.0))
        w, h = tight_crop(fig)
        assert (w, h) == (4.0, 3.0)
        plt.close(fig)

    def test_crops_whitespace(self) -> None:
        """A small plot inside a huge canvas must shrink."""
        from dartwork_mpl.layout import tight_crop

        fig = plt.figure(figsize=(10.0, 8.0))
        ax = fig.add_axes((0.4, 0.4, 0.2, 0.2))
        ax.plot([1, 2, 3])
        w, h = tight_crop(fig)
        assert w < 10.0
        assert h < 8.0
        # The returned size is the figure's actual new size.
        got_w, got_h = fig.get_size_inches()
        assert abs(got_w - w) < 1e-6
        assert abs(got_h - h) < 1e-6
        plt.close(fig)

    def test_padding_grows_result(self) -> None:
        from dartwork_mpl.layout import tight_crop

        def _make():
            fig = plt.figure(figsize=(10.0, 8.0))
            ax = fig.add_axes((0.4, 0.4, 0.2, 0.2))
            ax.plot([1, 2, 3])
            return fig

        fig_tight = _make()
        w0, h0 = tight_crop(fig_tight, padding=0.0)
        fig_padded = _make()
        w1, h1 = tight_crop(fig_padded, padding=0.5)
        # 0.5in padding on each side adds ~1in per dimension.
        assert w1 > w0 + 0.9
        assert h1 > h0 + 0.9
        plt.close(fig_tight)
        plt.close(fig_padded)

    def test_result_still_renders(self) -> None:
        """The cropped figure must remain drawable (no invalid geometry)."""
        from dartwork_mpl.layout import tight_crop

        fig, ax = plt.subplots(figsize=(6.0, 4.0))
        ax.plot([1, 2, 3])
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        tight_crop(fig)
        fig.canvas.draw()  # must not raise
        plt.close(fig)
