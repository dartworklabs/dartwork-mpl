"""``shared_axes`` and ``twin_partners`` over the figure shapes that matter."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from dartwork_mpl._figure_geometry import shared_axes, twin_partners


def test_twinx_and_twiny_partners() -> None:
    fig, ax = plt.subplots()
    right = ax.twinx()
    top = ax.twiny()
    assert twin_partners(ax) == [right, top]
    assert twin_partners(right) == [ax, top]
    assert shared_axes(ax, "x") == [ax, right]
    assert shared_axes(ax, "y") == [ax, top]
    plt.close(fig)


def test_twin_of_a_twin_joins_the_set() -> None:
    fig, ax = plt.subplots()
    first = ax.twinx()
    second = first.twinx()
    assert twin_partners(ax) == [first, second]
    assert twin_partners(second) == [ax, first]
    plt.close(fig)


def test_shared_panels_are_not_twins() -> None:
    fig, axs = plt.subplots(2, 2, sharex=True, sharey=True)
    flat = list(axs.flat)
    assert all(twin_partners(ax) == [] for ax in flat)
    assert shared_axes(flat[3], "x") == flat
    assert shared_axes(flat[0], "y") == flat
    plt.close(fig)


def test_plain_overlays_are_not_twins() -> None:
    fig = plt.figure()
    first = fig.add_axes((0.1, 0.1, 0.8, 0.8))
    second = fig.add_axes((0.1, 0.1, 0.8, 0.8))
    shared = fig.add_axes((0.1, 0.1, 0.8, 0.8), sharex=first)
    assert twin_partners(first) == []
    assert twin_partners(second) == []
    assert twin_partners(shared) == []
    plt.close(fig)


def test_invisible_twin_still_counts() -> None:
    fig, ax = plt.subplots()
    twin = ax.twinx()
    twin.set_visible(False)
    assert twin_partners(ax) == [twin]
    plt.close(fig)


def test_secondary_axis_and_inset_have_no_partners() -> None:
    fig, ax = plt.subplots()
    ax.secondary_xaxis("top")
    inset = ax.inset_axes((0.5, 0.5, 0.4, 0.4))
    assert twin_partners(ax) == []
    assert twin_partners(inset) == []
    assert shared_axes(inset, "x") == [inset]
    plt.close(fig)


def test_shared_axes_follow_figure_order() -> None:
    fig, axs = plt.subplots(1, 3, sharey=True)
    last = axs[2]
    assert shared_axes(last, "y") == list(axs)
    plt.close(fig)
