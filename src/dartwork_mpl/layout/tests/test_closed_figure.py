"""A retained Figure lays out identically after pyplot closes its manager."""

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

import dartwork_mpl as dm


def _figure(kind):
    """Build ordinary, nested, subfigure and mixed-manual layout boundaries."""
    dm.style.use("report")
    if kind == "nested":
        fig = plt.figure(figsize=dm.figsize("17cm", "9cm"))
        outer = fig.add_gridspec(1, 2, wspace=0.4)
        inner = outer[0].subgridspec(2, 1, hspace=0.8)
        axes = [
            fig.add_subplot(inner[0]),
            fig.add_subplot(inner[1]),
            fig.add_subplot(outer[1]),
        ]
    elif kind == "subfigures":
        fig = plt.figure(figsize=dm.figsize("17cm", "9cm"))
        axes = [sub.subplots() for sub in fig.subfigures(1, 2, wspace=0.2)]
    elif kind == "unmanaged":
        fig = Figure(figsize=dm.figsize("13cm", "standard"))
        FigureCanvasAgg(fig)
        axes = [fig.subplots()]
    else:
        fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
        axes = [ax]
    for ax in axes:
        ax.plot([0, 1], [0, 1], label="Series")
        ax.set(xlabel="Time (s)", ylabel="Signal")
    if kind == "decorated":
        twin = axes[0].twinx()
        twin.plot([0, 1], [2, 1])
        twin.set_ylabel("Response")
        axes.append(twin)
        axes[0].annotate("Observation", xy=(0.5, 0.5), xytext=(0.5, 0.7))
        dm.place_legend(axes[0], loc="above")
    if kind == "mixed":
        inset = fig.add_axes([0.65, 0.6, 0.2, 0.2])
        inset.plot([0, 1], [1, 0])
        inset.set_in_layout(False)
    return fig, axes


def _enlarge(axes):
    """Apply the exact explicit label-size edit without changing its values."""
    for ax in axes:
        ax.xaxis.label.set_fontsize(12)
        ax.yaxis.label.set_fontsize(12)


@pytest.mark.parametrize(
    "kind", ["simple", "decorated", "nested", "subfigures", "mixed"]
)
def test_closed_figure_matches_open_layout_without_reopening(kind):
    """Closing a manager must not disconnect the supplied Figure's GridSpec."""
    results = []
    for closed in (False, True):
        fig, axes = _figure(kind)
        try:
            dm.simple_layout(fig)
            fig.canvas.draw()
            if closed:
                plt.close(fig)
            _enlarge(axes)
            before_managers = plt.get_fignums()
            before_flags = [ax.get_in_layout() for ax in fig.axes]
            manual_bounds = [
                ax.get_position().bounds
                for ax in fig.axes
                if ax.get_subplotspec() is None
            ]
            dm.simple_layout(fig)
            fig.canvas.draw()
            assert plt.get_fignums() == before_managers
            assert all(ax.get_figure(root=True) is fig for ax in fig.axes)
            assert [ax.get_in_layout() for ax in fig.axes] == before_flags
            assert [
                ax.get_position().bounds
                for ax in fig.axes
                if ax.get_subplotspec() is None
            ] == manual_bounds
            assert all(ax.xaxis.label.get_fontsize() == 12 for ax in axes)
            assert all(ax.yaxis.label.get_fontsize() == 12 for ax in axes)
            results.append([ax.get_position().bounds for ax in fig.axes])
            if kind == "simple":
                renderer = fig.canvas.get_renderer()
                for label in (axes[0].xaxis.label, axes[0].yaxis.label):
                    box = label.get_window_extent(renderer)
                    assert box.x0 >= -0.5 and box.y0 >= -0.5
                    assert box.x1 <= fig.bbox.x1 + 0.5
                    assert box.y1 <= fig.bbox.y1 + 0.5
                assert not dm.validate_figure(
                    fig, checks=("OVERFLOW", "CLIPPED_TEXT"), quiet=True
                )
        finally:
            plt.close(fig)
    np.testing.assert_allclose(results[1], results[0], atol=1e-12, rtol=0)


def test_figure_without_a_pyplot_manager_fits_explicit_label_sizes():
    """Native Figure/Agg users get real layout without creating pyplot state."""
    fig, axes = _figure("unmanaged")
    before = plt.get_fignums()
    _enlarge(axes)
    dm.simple_layout(fig)
    fig.canvas.draw()
    assert plt.get_fignums() == before
    assert axes[0].figure is fig
    assert not dm.validate_figure(
        fig, checks=("OVERFLOW", "CLIPPED_TEXT"), quiet=True
    )
    control, control_axes = _figure("simple")
    try:
        _enlarge(control_axes)
        dm.simple_layout(control)
        np.testing.assert_allclose(
            axes[0].get_position().bounds,
            control_axes[0].get_position().bounds,
            atol=1e-12,
            rtol=0,
        )
    finally:
        plt.close(control)
