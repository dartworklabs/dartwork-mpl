from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm


def _year_formatter(locale: str):
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    dm.format_axis_year(ax, axis="x", locale=locale)  # type: ignore[arg-type]
    return fig, ax.xaxis.get_major_formatter()


@pytest.mark.parametrize(
    ("locale", "expected"),
    [("ko", "2025년"), ("ja", "2025年"), ("zh", "2025年"), ("en", "2025")],
)
def test_format_axis_year_locale_suffixes(locale: str, expected: str) -> None:
    fig, formatter = _year_formatter(locale)
    try:
        assert formatter(2025) == expected
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
