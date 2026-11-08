"""A rejected colour name has to say how to reach a valid one (#483).

The old message was ``Invalid color name: dc.bluee5. Invalid RGBA argument:
'dc.bluee5'`` — it repeated the value twice and named no route back to a
working call. These tests pin the route, and pin that nothing which used to
work now raises: the whole value of a suggesting message is lost if it also
starts rejecting names matplotlib accepts.
"""

from __future__ import annotations

import matplotlib.colors as mcolors
import pytest

import dartwork_mpl as dm
from dartwork_mpl._colors.model import Color, to_rgb_or_explain

#: Every entry point that takes a colour name from the caller, with a call
#: that reaches the lookup. ``pseudo_alpha`` is here because it delegates to
#: ``mix_colors``: a user who typed ``background=`` still has to see their
#: own value quoted back.
ENTRY_POINTS = [
    ("color", lambda name: dm.color(name)),
    ("Color.parse", lambda name: Color.parse(name)),
    ("Color.from_name", lambda name: Color.from_name(name)),
    ("mix_colors first", lambda name: dm.mix_colors(name, "dc.red5")),
    ("mix_colors second", lambda name: dm.mix_colors("dc.red5", name)),
    ("pseudo_alpha color", lambda name: dm.pseudo_alpha(name, 0.3)),
    (
        "pseudo_alpha background",
        lambda name: dm.pseudo_alpha("dc.red5", 0.3, name),
    ),
    ("readable_text_color", lambda name: dm.readable_text_color(name)),
    ("ensure_contrast", lambda name: dm.ensure_contrast(name, "dc.gray0")),
]

#: Names a caller plausibly types, and the registered name the message must
#: offer back. A doubled letter, a missing letter, an index past the end of a
#: family and a misspelt matplotlib name all have one obvious correction.
NEAR_MISSES = [
    ("dc.bluee5", "dc.blue5"),
    ("dc.blue99", "dc.blue9"),
    ("dc.gray55", "dc.gray5"),
    ("dc.blue_oragne3", "dc.blue_orange3"),
    ("oc.blu5", "oc.blue5"),
    ("whte", "white"),
]


def suggested(message: str) -> str:
    """The suggestion clause alone.

    Read from the clause rather than the whole message on purpose: the old
    message quoted the rejected value twice, so ``'dc.blue9' in message`` was
    already true for ``'dc.blue99'`` without a suggestion existing at all.
    """
    assert "Closest registered names: " in message
    return message.split("Closest registered names: ")[1].split(
        ". dm.list_colors"
    )[0]


@pytest.mark.parametrize(("label", "call"), ENTRY_POINTS, ids=lambda v: v)
def test_every_entry_point_explains_an_unknown_name(
    label: str, call: object
) -> None:
    """One message, whichever public function the caller reached."""
    with pytest.raises(ValueError) as caught:
        call("dc.bluee5")  # type: ignore[operator]
    message = str(caught.value)
    assert "Invalid color name: 'dc.bluee5'" in message
    assert "'dc.blue5'" in suggested(message)
    assert "dm.list_colors()" in message


@pytest.mark.parametrize(("typo", "intended"), NEAR_MISSES)
def test_a_near_miss_offers_the_name_that_was_meant(
    typo: str, intended: str
) -> None:
    with pytest.raises(ValueError, match="Invalid color name") as caught:
        dm.color(typo)
    assert f"{intended!r}" in suggested(str(caught.value))


def test_a_prefixed_name_is_corrected_inside_its_own_namespace() -> None:
    """``dc.`` and ``oc.`` are different palettes, not spellings of each other.

    Suggesting ``oc.blue5`` to someone who typed ``dc.bluee5`` would hand them
    a colour from another palette that renders differently.
    """
    with pytest.raises(ValueError) as caught:
        dm.color("dc.bluee5")
    suggestions = suggested(str(caught.value))
    assert "oc." not in suggestions
    assert "dc." in suggestions


def test_a_name_nothing_resembles_says_so_instead_of_guessing() -> None:
    with pytest.raises(ValueError) as caught:
        dm.color("notacolor_xyzzy")
    message = str(caught.value)
    assert "No registered name is close to it" in message
    assert "Closest registered names" not in message
    assert "matplotlib.colors.get_named_colors_mapping()" in message


def test_suggestions_come_from_the_live_registry() -> None:
    """A name registered after import is suggestible without a code change."""
    mcolors.get_named_colors_mapping()["probe.teal7"] = "#114455"
    try:
        with pytest.raises(ValueError) as caught:
            dm.color("probe.teal77")
        assert "'probe.teal7'" in suggested(str(caught.value))
    finally:
        del mcolors.get_named_colors_mapping()["probe.teal7"]


@pytest.mark.parametrize(
    "value", ["red", "dc.blue5", "oc.red9", "#ff0000", "0.5", "C0"]
)
def test_accepted_names_are_untouched(value: str) -> None:
    assert to_rgb_or_explain(value) == mcolors.to_rgb(value)


@pytest.mark.parametrize("value", [None, (2.0, 0.0, 0.0), 5, (0.1, 0.2)])
def test_a_non_name_keeps_matplotlib_s_own_message(value: object) -> None:
    """Only a *name* miss is rewritten.

    A malformed tuple is not a lookup failure, and matplotlib's message
    already describes the shapes it accepts; replacing it with
    ``Invalid color name`` would describe the wrong problem.
    """
    with pytest.raises(ValueError) as caught:
        to_rgb_or_explain(value)
    assert "Invalid color name" not in str(caught.value)


def test_case_differences_still_resolve_rather_than_suggest() -> None:
    """``dc.Blue5`` resolves today; a suggestion would be a regression."""
    assert to_rgb_or_explain("dc.Blue5") == mcolors.to_rgb("dc.blue5")
