"""One axis name, one form: a grid does not wrap it in one panel only.

Smoke round 5 (2026-11-14, ``s04-grid-to-slide`` turn 4, Claude): a 2 x 2
grid on a full slide showed "Indoor / temp (°C)" on two lines beside the
upper row and "Indoor temp (°C)" on one line beside the lower row. The host
reported the mismatch to the user and tried a figure-level name instead.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


@pytest.fixture(autouse=True)
def _close():
    yield
    plt.close("all")


def _slide_grid(lower_name: str = "Indoor temp (°C)"):
    dm.style.use("presentation")
    fig, axes = plt.subplots(
        2, 2, figsize=dm.figsize_for("full_slide"), sharex=True, sharey=True
    )
    for i, ax in enumerate(axes.flat):
        ax.plot(range(24), [21 + i * 0.5 + (h % 12) / 6 for h in range(24)])
        ax.set_title(f"Zone {i + 1}")
    for ax in axes[-1, :]:
        ax.set_xlabel("Hour")
    axes[0, 0].set_ylabel("Indoor temp (°C)")
    axes[1, 0].set_ylabel(lower_name)
    dm.label_axes(axes)
    dm.simple_layout(fig)
    return fig, axes


def test_a_name_wrapped_beside_one_row_is_wrapped_beside_the_other():
    _fig, axes = _slide_grid()

    upper, lower = axes[0, 0].get_ylabel(), axes[1, 0].get_ylabel()

    assert "\n" in upper  # the case: the layout wraps the upper one
    assert lower == upper


def test_another_name_in_nobodys_way_stays_on_one_line():
    """Only the same words follow; a different name that fits is left."""
    _fig, axes = _slide_grid(lower_name="Temp (°C)")

    assert "\n" in axes[0, 0].get_ylabel()
    assert axes[1, 0].get_ylabel() == "Temp (°C)"


def test_the_followed_wrap_is_undone_with_the_fitting():
    fig, axes = _slide_grid()

    dm.simple_layout(fig, fit_labels=False)

    assert axes[0, 0].get_ylabel() == "Indoor temp (°C)"
    assert axes[1, 0].get_ylabel() == "Indoor temp (°C)"
