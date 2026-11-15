"""Tests for orphan tick-label axis-label font adoption."""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from dartwork_mpl.layout import adopt_axis_label_font, simple_layout
from dartwork_mpl.layout._orphan_tick_font import _adopt_axis_label_font_core


def _x_tick(ax):
    return next(
        t
        for t in ax.xaxis.get_ticklabels()
        if t.get_visible() and t.get_text().strip()
    )


def _y_tick(ax):
    return next(
        t
        for t in ax.yaxis.get_ticklabels()
        if t.get_visible() and t.get_text().strip()
    )


class TestAdoptCore:
    """Ticks of an unlabeled axis adopt the axis-label font; labeled axes are untouched."""

    def test_unlabeled_x_adopts_axis_label_font(self) -> None:
        """x has no label -> x ticks take xaxis.label size+weight+family+style."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")  # y labeled, x unlabeled
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)

        xt, lbl = _x_tick(ax), ax.xaxis.label
        assert xt.get_fontsize() == lbl.get_fontsize()
        assert xt.get_fontweight() == lbl.get_fontweight()
        assert list(xt.get_fontfamily()) == list(lbl.get_fontfamily())
        assert xt.get_fontstyle() == lbl.get_fontstyle()
        plt.close(fig)

    def test_labeled_axis_ticks_untouched(self) -> None:
        """y has a label -> y ticks keep their default (lighter) style."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")
        fig.canvas.draw()
        before = _y_tick(ax).get_fontweight()
        _adopt_axis_label_font_core(fig)

        yt, lbl = _y_tick(ax), ax.yaxis.label
        assert yt.get_fontweight() == before
        # default tick weight differs from axis-label weight in this preset
        assert lbl.get_fontweight() != before
        plt.close(fig)

    def test_x_and_y_independent(self) -> None:
        """y labeled, x not -> x adopts, y does not."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")
        fig.canvas.draw()
        y_before = _y_tick(ax).get_fontweight()
        _adopt_axis_label_font_core(fig)

        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        assert _y_tick(ax).get_fontweight() == y_before
        plt.close(fig)

    def test_offset_text_adopts(self) -> None:
        """Unlabeled axis -> ScalarFormatter offset text adopts label font."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), [v * 1e9 for v in range(10)])  # forces 1e9 offset
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)

        ot = ax.yaxis.get_offset_text()
        assert ot.get_text().strip()  # offset present
        assert ot.get_fontweight() == ax.yaxis.label.get_fontweight()
        plt.close(fig)

    def test_idempotent(self) -> None:
        """Two applications produce identical font."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)
        size1, w1 = _x_tick(ax).get_fontsize(), _x_tick(ax).get_fontweight()
        _adopt_axis_label_font_core(fig)
        assert _x_tick(ax).get_fontsize() == size1
        assert _x_tick(ax).get_fontweight() == w1
        plt.close(fig)

    def test_no_ticklabels_no_error(self) -> None:
        """Unlabeled axis with no tick labels -> no error, no-op."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_xticks([])
        fig.canvas.draw()
        _adopt_axis_label_font_core(fig)  # must not raise
        plt.close(fig)


class TestAdoptPublic:
    """The public ``adopt_axis_label_font`` draws before applying and tolerates empty figures."""

    def test_public_draws_and_applies(self) -> None:
        """adopt_axis_label_font draws then applies (no manual draw needed)."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        adopt_axis_label_font(fig)
        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        plt.close(fig)

    def test_empty_figure_no_error(self) -> None:
        fig = plt.figure()
        adopt_axis_label_font(fig)  # no axes -> no-op
        plt.close(fig)


class TestSimpleLayoutIntegration:
    """``simple_layout`` adopts the font only on request and sizes margins for it."""

    def test_simple_layout_keeps_tick_font_by_default(self) -> None:
        dm.style.use("scientific")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")  # x unlabeled
        ax.tick_params(axis="x", labelsize=5.5)
        fig.canvas.draw()
        before = (_x_tick(ax).get_fontsize(), _x_tick(ax).get_fontweight())
        simple_layout(fig)
        after = (_x_tick(ax).get_fontsize(), _x_tick(ax).get_fontweight())
        assert after == before
        plt.close(fig)

    def test_simple_layout_explicit_true_adopts(self) -> None:
        dm.style.use("scientific")
        fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
        ax.plot(range(10), range(10))
        simple_layout(fig, adopt_orphan_tick_font=True)
        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        plt.close(fig)

    def test_margin_reflects_enlarged_orphan_ticks(self) -> None:
        """A larger axis-label font on an unlabeled axis grows the bottom
        margin because simple_layout measures the restyled ticks."""
        dm.style.use("scientific")

        def build():
            fig, ax = plt.subplots(figsize=dm.figsize("12cm", "standard"))
            ax.plot(range(10), range(10))
            ax.xaxis.label.set_fontsize(24)  # empty label, large font
            return fig, ax

        fig_on, ax_on = build()
        simple_layout(fig_on, adopt_orphan_tick_font=True)
        bottom_on = ax_on.get_gridspec().bottom

        fig_off, ax_off = build()
        simple_layout(fig_off, adopt_orphan_tick_font=False)
        bottom_off = ax_off.get_gridspec().bottom

        assert _x_tick(ax_on).get_fontsize() == 24
        # bigger ticks push the axes up -> larger bottom edge fraction
        assert bottom_on > bottom_off + 0.01
        plt.close(fig_on)
        plt.close(fig_off)


def test_exported_at_package_root() -> None:
    assert hasattr(dm, "adopt_axis_label_font")
    assert "adopt_axis_label_font" in dm.__all__


class TestConfigGlobalDefault:
    """`dm.config.adopt_orphan_tick_font` flips the default on every
    entry point that accepts the matching keyword. Explicit per-call
    kwargs still win over the global default."""

    def _build(self):
        """Return (fig, ax) with one orphan x-axis and an enlarged label
        font, mirroring TestSimpleLayoutIntegration."""
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")  # x is the orphan
        return fig, ax

    def test_config_on_applies_simple_layout_adoption(self) -> None:
        fig, ax = self._build()
        try:
            dm.config.adopt_orphan_tick_font = True
            simple_layout(fig)
        finally:
            dm.config.adopt_orphan_tick_font = False
        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        plt.close(fig)

    def test_per_call_true_overrides_global_off(self) -> None:
        fig, ax = self._build()
        try:
            dm.config.adopt_orphan_tick_font = False
            simple_layout(fig, adopt_orphan_tick_font=True)
        finally:
            dm.config.adopt_orphan_tick_font = False
        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        plt.close(fig)

    def test_per_call_false_overrides_global_on(self) -> None:
        fig, ax = self._build()
        fig.canvas.draw()
        default_weight = _x_tick(ax).get_fontweight()
        try:
            dm.config.adopt_orphan_tick_font = True
            simple_layout(fig, adopt_orphan_tick_font=False)
        finally:
            dm.config.adopt_orphan_tick_font = False
        assert _x_tick(ax).get_fontweight() == default_weight
        plt.close(fig)


class TestConfigOverrideContextManager:
    """`with dm.config.override(...)` scopes a temporary change and
    always restores the prior state, including on exception."""

    def test_override_restores_after_block(self) -> None:
        assert not dm.config.adopt_orphan_tick_font
        with dm.config.override(adopt_orphan_tick_font=True):
            assert dm.config.adopt_orphan_tick_font
        assert not dm.config.adopt_orphan_tick_font

    def test_override_restores_after_exception(self) -> None:
        assert not dm.config.adopt_orphan_tick_font
        try:
            with dm.config.override(adopt_orphan_tick_font=True):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert not dm.config.adopt_orphan_tick_font

    def test_override_unknown_field_raises(self) -> None:

        with pytest.raises(AttributeError, match="no attribute"):
            with dm.config.override(nonexistent=True):
                pass

    def test_override_affects_simple_layout_inside_block(self) -> None:
        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")
        fig.canvas.draw()
        with dm.config.override(adopt_orphan_tick_font=True):
            simple_layout(fig)
        assert _x_tick(ax).get_fontweight() == ax.xaxis.label.get_fontweight()
        plt.close(fig)


def test_config_exported_at_package_root() -> None:
    assert hasattr(dm, "config")
    assert hasattr(dm, "Config")
    assert "config" in dm.__all__
    assert "Config" in dm.__all__
    assert not dm.config.adopt_orphan_tick_font  # ships as off


class TestWarnOnOrphanTickAdoption:
    """`dm.config.warn_on_orphan_tick_adoption` controls whether the
    adoption emits a UserWarning. Off by default so the common path
    stays quiet; on when a user wants to debug a figure whose ticks
    change unexpectedly after a save."""

    def test_default_ships_off(self) -> None:
        assert not dm.config.warn_on_orphan_tick_adoption

    def test_warn_when_enabled_and_adoption_mutates(self) -> None:
        import warnings

        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")  # x orphan -> mutation expected

        try:
            dm.config.warn_on_orphan_tick_adoption = True
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                simple_layout(fig, adopt_orphan_tick_font=True)
        finally:
            dm.config.warn_on_orphan_tick_adoption = False

        adoption_warnings = [
            w
            for w in caught
            if issubclass(w.category, UserWarning)
            and "Orphan tick-label font adoption" in str(w.message)
        ]
        assert adoption_warnings, (
            "Expected a UserWarning naming the orphan-tick adoption"
        )
        plt.close(fig)

    def test_no_warn_when_disabled(self) -> None:
        import warnings

        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_ylabel("y label")

        assert not dm.config.warn_on_orphan_tick_adoption
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            simple_layout(fig)

        adoption_warnings = [
            w
            for w in caught
            if issubclass(w.category, UserWarning)
            and "Orphan tick-label font adoption" in str(w.message)
        ]
        assert not adoption_warnings, (
            "Should be silent unless dm.config.warn_on_orphan_tick_adoption=True"
        )
        plt.close(fig)

    def test_no_warn_when_no_mutation(self) -> None:
        """Both axes labeled → no mutation → no warning even when
        the toggle is on."""
        import warnings

        dm.style.use("scientific")
        fig, ax = plt.subplots()
        ax.plot(range(10), range(10))
        ax.set_xlabel("x label")
        ax.set_ylabel("y label")  # both labeled — nothing to adopt

        try:
            dm.config.warn_on_orphan_tick_adoption = True
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                simple_layout(fig, adopt_orphan_tick_font=True)
        finally:
            dm.config.warn_on_orphan_tick_adoption = False

        adoption_warnings = [
            w
            for w in caught
            if issubclass(w.category, UserWarning)
            and "Orphan tick-label font adoption" in str(w.message)
        ]
        assert not adoption_warnings, (
            "No axes had orphan ticks; the warning should not fire"
        )
        plt.close(fig)

    def test_override_context_manager_scopes_warn_toggle(self) -> None:
        """`dm.config.override(warn_on_orphan_tick_adoption=True)` should
        scope the change to a `with` block and restore it on exit."""
        assert not dm.config.warn_on_orphan_tick_adoption
        with dm.config.override(warn_on_orphan_tick_adoption=True):
            assert dm.config.warn_on_orphan_tick_adoption
        assert not dm.config.warn_on_orphan_tick_adoption
