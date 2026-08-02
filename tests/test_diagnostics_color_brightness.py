"""The diagnostics swatch heuristic must not masquerade as luminance."""

from __future__ import annotations

import inspect

import pytest

from dartwork_mpl.diagnostics import _colors


@pytest.mark.parametrize(
    ("color", "expected"),
    [
        ("#000000", 0.0),
        ("#ffffff", 1.0),
        ("#ff0000", 0.2126),
        ("#00ff00", 0.7152),
        ("#0000ff", 0.0722),
        ("#808080", 128 / 255),
    ],
)
def test_text_brightness_preserves_the_gamma_weighted_heuristic(
    color: str, expected: float
) -> None:
    assert _colors._text_brightness(color) == pytest.approx(expected, abs=1e-12)


def test_text_brightness_name_and_docs_do_not_claim_physical_or_wcag_y() -> (
    None
):
    assert not hasattr(_colors, "_relative_luminance")
    doc = inspect.getdoc(_colors._text_brightness)
    assert doc is not None
    lowered = doc.lower()
    assert "text brightness" in lowered
    assert "heuristic" in lowered
    assert "gamma-encoded" in lowered
    assert "relative luminance" not in lowered
    assert "wcag" not in lowered


def test_contrast_text_choice_is_behaviorally_unchanged() -> None:
    assert _colors._contrast_text_color("#727272") == "white"
    assert _colors._contrast_text_color("#737373") == "#333333"
    assert _colors._contrast_text_color("#ff0000") == "white"
    assert _colors._contrast_text_color("#00ff00") == "#333333"
