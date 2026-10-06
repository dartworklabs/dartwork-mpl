from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


def _year_formatter(locale: str, **kwargs):
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    dm.format_axis_year(ax, axis="x", locale=locale, **kwargs)  # type: ignore[arg-type]
    return fig, ax.xaxis.get_major_formatter()


@pytest.mark.parametrize(
    ("locale", "expected"),
    [("ko", "25년"), ("ja", "25年"), ("zh", "25年"), ("en", "25")],
)
def test_format_axis_year_locale_suffixes(locale: str, expected: str) -> None:
    """Tick years are two digits by default (user instruction 2026-10-06)."""
    fig, formatter = _year_formatter(locale)
    try:
        assert formatter(2025) == expected
        assert formatter(2005) == expected.replace("25", "05", 1)
    finally:
        plt.close(fig)


@pytest.mark.parametrize(
    ("locale", "expected"),
    [("ko", "2025년"), ("ja", "2025年"), ("zh", "2025年"), ("en", "2025")],
)
def test_format_axis_year_four_digits_on_request(
    locale: str, expected: str
) -> None:
    fig, formatter = _year_formatter(locale, digits=4)
    try:
        assert formatter(2025) == expected
    finally:
        plt.close(fig)


def test_format_axis_year_rejects_other_digit_counts() -> None:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    try:
        with pytest.raises(ValueError, match="digits must be 2 or 4"):
            dm.format_axis_year(ax, digits=3)  # type: ignore[arg-type]
    finally:
        plt.close(fig)


def test_format_axis_year_unknown_locale_raises() -> None:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    try:
        with pytest.raises(ValueError, match="valid locales") as exc_info:
            dm.format_axis_year(ax, axis="x", locale="fr")  # type: ignore[arg-type]

        message = str(exc_info.value)
        for locale in ("ko", "ja", "zh", "en"):
            assert locale in message
    finally:
        plt.close(fig)
