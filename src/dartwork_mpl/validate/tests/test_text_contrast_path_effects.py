"""``TEXT_CONTRAST`` judges the ink a path effect actually draws."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.text import Text

import dartwork_mpl as dm
from dartwork_mpl.validate import VisualWarning, validate_figure
from dartwork_mpl.validate._checks.text_contrast import check_text_contrast


def _outlined_title(
    *, fill: str, outline: str, linewidth: float, background: str = "white"
) -> tuple[Figure, Text]:
    """Return a figure whose only text is ``fill`` drawn with an outline."""
    dm.style.use("scientific")
    fig = plt.figure(figsize=dm.figsize("9cm", "standard"))
    fig.patch.set_facecolor(background)
    title = fig.text(0.5, 0.5, "Outlined title", ha="center", color=fill)
    title.set_fontsize(16)
    title.set_path_effects(
        [path_effects.withStroke(linewidth=linewidth, foreground=outline)]
    )
    return fig, title


def _contrast(fig: Figure) -> list[VisualWarning]:
    found = validate_figure(fig, checks=("TEXT_CONTRAST",), quiet=True)
    plt.close(fig)
    return found


def test_white_text_with_a_dark_outline_is_legible() -> None:
    """White fill with a thin dark outline on white reads through its outline.

    The reference render kept the stroke as background and the text fill was
    compared with a whole-box median that is mostly paper, so the title was
    reported as white on white, 1:1, although a dark outline is drawn.
    """
    fig, _title = _outlined_title(fill="white", outline="#222222", linewidth=1)

    assert _contrast(fig) == []


def test_outline_that_is_faint_on_the_background_is_still_reported() -> None:
    """A lavender outline on white stays a finding; outlines are not exempt.

    White fill and a pale outline on a white figure leave only a faint ring
    to read, so the check must still warn, naming the ink it measured.
    """
    fig, _title = _outlined_title(fill="white", outline="#d5c7ff", linewidth=3)

    found = _contrast(fig)

    assert [w.check_id for w in found] == ["TEXT_CONTRAST"]
    assert found[0].detail["ratio"] < 3.0
    assert found[0].detail["text_color"] != "#ffffff"
    assert found[0].detail["background_color"] == "#ffffff"


def test_invisible_outline_leaves_the_fill_contrast_finding() -> None:
    """An outline equal to the paper adds no ink: white on white stays 1:1."""
    fig, _title = _outlined_title(fill="white", outline="white", linewidth=3)

    found = _contrast(fig)

    assert [w.detail["ratio"] for w in found] == [1.0]
    assert found[0].detail["text_color"] == "#ffffff"


def test_the_check_puts_path_effects_back() -> None:
    """The reference draw drops path effects for one render and restores them."""
    fig, title = _outlined_title(fill="white", outline="#222222", linewidth=3)
    effects = list(title.get_path_effects())
    fig.canvas.draw()

    check_text_contrast(fig, fig.canvas.get_renderer())

    assert list(title.get_path_effects()) == effects
    assert title.get_color() == "white"
    plt.close(fig)


def test_another_texts_ink_does_not_rescue_a_faint_outlined_text() -> None:
    """A dark outlined text drawn over a faint one is not the faint one's ink.

    The picture that keeps path effects held every outlined text, so the
    strong ink of an overlapping neighbour was read as the faint text's own
    and the warning disappeared.
    """
    fig, _faint = _outlined_title(fill="white", outline="#d5c7ff", linewidth=3)
    strong = fig.text(0.5, 0.5, "Overlapping", ha="center", color="#111111")
    strong.set_fontsize(16)
    strong.set_path_effects(
        [path_effects.withStroke(linewidth=1, foreground="#111111")]
    )

    found = _contrast(fig)

    assert [w.detail["sample"] for w in found] == ["Outlined title"]
    assert found[0].detail["ratio"] < 3.0
