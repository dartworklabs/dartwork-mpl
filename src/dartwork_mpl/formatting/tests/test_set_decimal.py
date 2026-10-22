"""set_decimal installs fixed-point tick labels that follow data changes."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

from dartwork_mpl.formatting import set_decimal


class TestSetDecimal:
    """Tests for set_decimal()."""

    def test_x_decimal(self) -> None:

        fig, ax = plt.subplots()
        ax.plot([0, 1, 2], [0, 1, 2])
        fig.canvas.draw()  # Ensure ticks are set
        set_decimal(ax, xn=2)
        labels = [t.get_text() for t in ax.get_xticklabels()]
        # Should contain decimal formatted labels
        assert any("." in label for label in labels if label)
        plt.close(fig)

    def test_y_decimal(self) -> None:

        fig, ax = plt.subplots()
        ax.plot([0, 1, 2], [0, 1, 2])
        fig.canvas.draw()
        set_decimal(ax, yn=1)
        labels = [t.get_text() for t in ax.get_yticklabels()]
        assert any("." in label for label in labels if label)
        plt.close(fig)

    def test_both_decimals(self) -> None:

        fig, ax = plt.subplots()
        ax.plot([0, 1, 2], [0, 1, 2])
        fig.canvas.draw()
        set_decimal(ax, xn=3, yn=0)
        plt.close(fig)


def test_decimal_labels_follow_changed_data_without_replacing_locators():
    """Autoscaling new data keeps native visible ticks with current fixed-point labels."""
    import dartwork_mpl as dm

    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    (line,) = ax.plot([0, 1, 2], [0, 1, 2])
    locators = (ax.xaxis.get_major_locator(), ax.yaxis.get_major_locator())
    limits = (ax.get_xlim(), ax.get_ylim())
    assert dm.set_decimal(ax, xn=2, yn=1) is None
    assert (ax.get_xlim(), ax.get_ylim()) == limits
    line.set_data([100, 200, 300], [1000, 2000, 3000])
    ax.relim()
    ax.autoscale_view()
    fig.canvas.draw()
    for axis, locator, precision, bounds in zip(
        (ax.xaxis, ax.yaxis),
        locators,
        (2, 1),
        (ax.get_xlim(), ax.get_ylim()),
        strict=True,
    ):
        visible = [
            t
            for t in axis.get_major_ticks()
            if bounds[0] <= t.get_loc() <= bounds[1]
        ]
        assert visible, "new data range has no visible current tick"
        assert all(
            t.label1.get_text() == format(float(t.get_loc()), f".{precision}f")
            for t in visible
        )
        assert axis.get_major_locator() is locator


def test_decimal_keeps_custom_locator_and_none_axis():
    """Formatter installation leaves custom locator, limits and unrequested axis unchanged."""
    from matplotlib.ticker import MultipleLocator

    import dartwork_mpl as dm

    fig, ax = plt.subplots(figsize=dm.figsize("8cm", "wide"))
    locator = MultipleLocator(2.5)
    ax.xaxis.set_major_locator(locator)
    untouched = (ax.yaxis.get_major_locator(), ax.yaxis.get_major_formatter())
    limits = ax.get_xlim()
    dm.set_decimal(ax, xn=2)
    assert ax.xaxis.get_major_locator() is locator
    assert ax.get_xlim() == limits
    assert (
        ax.yaxis.get_major_locator(),
        ax.yaxis.get_major_formatter(),
    ) == untouched
    ax.set_xlim(100, 120)
    fig.canvas.draw()
    assert ax.xaxis.get_major_formatter()(102.5) == "102.50"


def test_decimal_python_rounding_and_seeded_precision_values():
    """Half-even ties, negative zero and seed501 finite values match Python formatting."""
    import random

    import dartwork_mpl as dm

    rng = random.Random(501)
    values = [-2.5, -1.5, -0.5, -0.0, 0.0, 0.5, 1.5, 2.5]
    values += [rng.uniform(-1000, 1000) for _ in range(16)]
    fig, ax = plt.subplots(figsize=dm.figsize("8cm", "wide"))
    for precision in (0, 1, 2, 5):
        ax.set_xticks(values)
        dm.set_decimal(ax, xn=precision)
        fig.canvas.draw()
        assert [t.get_text() for t in ax.get_xticklabels()] == [
            format(float(v), f".{precision}f") for v in values
        ], (501, precision)


@pytest.mark.parametrize("precision", [-1, 1.5, "invalid"])
def test_decimal_invalid_precision_rejected_before_axis_install(precision):
    """Invalid Python precision fails immediately without changing that axis formatter."""
    import dartwork_mpl as dm

    fig, ax = plt.subplots(figsize=dm.figsize("8cm", "wide"))
    previous = (
        ax.xaxis.get_major_formatter(),
        ax.xaxis.get_major_locator(),
        ax.get_xlim(),
    )
    with pytest.raises(ValueError):
        dm.set_decimal(ax, xn=precision)
    assert (
        ax.xaxis.get_major_formatter(),
        ax.xaxis.get_major_locator(),
        ax.get_xlim(),
    ) == previous
