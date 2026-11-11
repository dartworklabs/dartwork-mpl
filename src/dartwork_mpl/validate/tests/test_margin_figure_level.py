"""Figure-level artists count as content for ``MARGIN_ASYMMETRY``."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

from dartwork_mpl.validate import VisualWarning, validate_figure


def _lower_panel_figure() -> tuple[Figure, plt.Axes]:
    """Return a 6x6 in figure whose only axes sits in the lower half."""
    fig, ax = plt.subplots(figsize=(6, 6), dpi=100)
    ax.plot([1, 2, 3], [1, 2, 3], label="series")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.subplots_adjust(left=0.15, right=0.9, bottom=0.15, top=0.55)
    return fig, ax


def _vertical(fig: Figure) -> list[VisualWarning]:
    """Return the vertical MARGIN_ASYMMETRY findings for ``fig``."""
    warnings = validate_figure(fig, checks=("MARGIN_ASYMMETRY",), quiet=True)
    return [w for w in warnings if w.detail.get("axis") == "vertical"]


def test_empty_header_is_still_reported_as_vertical_asymmetry() -> None:
    """The control: a really empty header keeps its vertical warning."""
    fig, _ax = _lower_panel_figure()

    found = _vertical(fig)
    plt.close(fig)

    assert [w.detail["side"] for w in found] == ["top"]


@pytest.mark.parametrize("header", ["suptitle", "figure_legend"])
def test_header_filled_by_a_figure_level_artist_is_not_empty(
    header: str,
) -> None:
    """A suptitle or ``fig.legend`` in the top band is content, not whitespace.

    The check unioned only axes tight boxes and ``ax.texts``, so a header
    occupied by figure-level text or a legend was measured as empty and the
    figure was reported as top-heavy with whitespace.
    """
    fig, ax = _lower_panel_figure()
    if header == "suptitle":
        fig.suptitle("A title that fills the header", y=0.92, va="top")
    else:
        fig.legend(
            *ax.get_legend_handles_labels(),
            loc="upper center",
            bbox_to_anchor=(0.5, 0.92),
        )

    found = _vertical(fig)
    plt.close(fig)

    assert found == []
