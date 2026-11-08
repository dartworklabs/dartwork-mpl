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


def test_an_existing_namespace_with_no_near_miss_suggests_nothing() -> None:
    """Rather than reaching into another palette for something to say.

    A global fallback here would answer a ``dc.`` miss with an ``oc.`` name
    whenever no ``dc.`` name happened to be close — the opposite of what the
    namespace rule is for.
    """
    registry = mcolors.get_named_colors_mapping()
    foreign = "oc.zzzzzzzzzzzzzzzzzz"
    registry[foreign] = "#123456"
    try:
        with pytest.raises(ValueError) as caught:
            dm.color("dc.zzzzzzzzzzzzzzzzzz")
        message = str(caught.value)
        assert "No registered name is close to it" in message
        assert foreign not in message
    finally:
        del registry[foreign]


def test_an_unused_namespace_is_part_of_the_typo() -> None:
    """``dz.`` is nobody's palette, so the whole name is searched.

    Restricting to a namespace that holds no registered name at all would
    throw away the one useful answer: the caller meant ``dc.``.
    """
    with pytest.raises(ValueError) as caught:
        dm.color("dz.blue5")
    assert "'dc.blue5'" in suggested(str(caught.value))


def test_a_name_nothing_resembles_says_so_instead_of_guessing() -> None:
    with pytest.raises(ValueError) as caught:
        dm.color("notacolor_xyzzy")
    message = str(caught.value)
    assert "No registered name is close to it" in message
    assert "Closest registered names" not in message
    assert "matplotlib.colors.get_named_colors_mapping()" in message


def test_suggestions_come_from_the_live_registry() -> None:
    """A name registered after import is suggestible without a code change."""
    registry = mcolors.get_named_colors_mapping()
    sentinel = object()
    previous = registry.get("probe.teal7", sentinel)
    registry["probe.teal7"] = "#114455"
    try:
        with pytest.raises(ValueError) as caught:
            dm.color("probe.teal77")
        assert "'probe.teal7'" in suggested(str(caught.value))
    finally:
        if previous is sentinel:
            del registry["probe.teal7"]
        else:
            registry["probe.teal7"] = previous


def test_a_non_string_registry_key_does_not_change_the_exception() -> None:
    """The error path must not fail on its way to reporting the error.

    ``get_named_colors_mapping()`` is live and mutable; a non-string key in it
    made ``sorted()`` raise ``TypeError`` from inside the handler, so the
    caller lost the ``ValueError`` the API documents.
    """
    registry = mcolors.get_named_colors_mapping()
    registry[42] = "#123456"  # type: ignore[index]
    try:
        with pytest.raises(ValueError, match="Invalid color name"):
            dm.color("dc.bluee5")
    finally:
        del registry[42]  # type: ignore[arg-type]


def test_an_unreasonably_long_name_is_bounded_not_echoed() -> None:
    """A pathological value stays out of the matcher and out of the message.

    Without a bound, a 100,000-character name went through difflib's
    quadratic matcher and came back quoted whole, so one bad call could put a
    megabyte in a log.
    """
    value = "dc." + "z" * 100_000
    with pytest.raises(ValueError, match="Invalid color name") as caught:
        dm.color(value)
    message = str(caught.value)
    assert len(message) < 500
    assert "truncated, 100003 characters" in message
    assert "No registered name is close to it" in message


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
    ``Invalid color name`` would describe the wrong problem. Compared against
    what matplotlib itself raises, not merely checked for absence of the new
    wording.
    """
    with pytest.raises(ValueError) as original:
        mcolors.to_rgb(value)  # type: ignore[arg-type]
    with pytest.raises(ValueError) as caught:
        to_rgb_or_explain(value)
    assert str(caught.value) == str(original.value)
    assert "Invalid color name" not in str(caught.value)


#: How far a blend may sit from the value measured before this change. Exact
#: equality was the first formulation and it was wrong: the same source gives
#: the same bits on one machine but drifts by one or two ULPs across libm and
#: NumPy builds, so CI's Python 3.11 runner read
#: ``0.7237702208034282`` where this machine reads ``…91``. 1e-12 is a
#: thousand times that drift and still ~2.5e-10 of one 8-bit colour level, so
#: it cannot hide a change anybody could see — a reordered or rewritten blend
#: moves these numbers in the third or fourth digit.
BLEND_TOLERANCE = 1e-12

#: Blend results measured on ``cad7034f``, before this change. The package
#: holds its visual style, so a drifting blend would move shipped figures;
#: these pin that routing the name lookup through a new helper did not touch
#: the arithmetic.
BLENDS_AT_CAD7034F = [
    (
        ("dc.blue5", "dc.red5", 0.5),
        (0.7237702208034291, 0.6042478958568327, 0.7408197251046789),
    ),
    (
        ("dc.blue5", "dc.red5", 0.25),
        (0.8693137731289476, 0.5488372697959335, 0.6137466586558787),
    ),
    (
        ("red", "blue", 0.5),
        (0.5504410670996633, 0.32562068470935013, 0.6365006535344367),
    ),
    (
        ("red", "blue", 0.25),
        (0.3164174757496998, 0.2788379120925991, 0.8218085755416885),
    ),
    (
        ("dc.gray1", "white", 0.5),
        (0.9309000834480874, 0.9348764370866666, 0.9408426670350154),
    ),
    (
        ("oc.teal7", "#112233", 0.5),
        (0.09430326979606174, 0.37876708047924185, 0.3367227698751202),
    ),
]


@pytest.mark.parametrize(("arguments", "expected"), BLENDS_AT_CAD7034F)
def test_blends_still_match_the_values_measured_before_the_change(
    arguments: tuple[str, str, float], expected: tuple[float, float, float]
) -> None:
    color1, color2, alpha = arguments
    assert dm.mix_colors(color1, color2, alpha=alpha) == pytest.approx(
        expected, abs=BLEND_TOLERANCE
    )


def test_pseudo_alpha_still_matches_the_value_measured_before_the_change() -> (
    None
):
    assert dm.pseudo_alpha("dc.red5", 0.3) == pytest.approx(
        (0.9999999999999999, 0.8561922305369954, 0.848520311623812),
        abs=BLEND_TOLERANCE,
    )


def test_case_differences_still_resolve_rather_than_suggest() -> None:
    """``dc.Blue5`` resolves today; a suggestion would be a regression."""
    assert to_rgb_or_explain("dc.Blue5") == mcolors.to_rgb("dc.blue5")
