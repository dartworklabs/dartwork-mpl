"""Year tick labels: locale suffixes, two- versus four-digit years and rejected input."""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
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


def _on(axis) -> tuple[list[float], list[str]]:
    """In-view major tick locations and texts of ``axis``, after a draw."""
    axis.axes.get_figure(root=True).canvas.draw()
    low, high = sorted(axis.get_view_interval())
    pairs = [
        (float(loc), label.get_text())
        for loc, label in zip(
            axis.get_majorticklocs(), axis.get_majorticklabels(), strict=True
        )
        if low <= loc <= high
    ]
    return [p[0] for p in pairs], [p[1] for p in pairs]


def _plain_values(axis) -> dict[float, str]:
    """Matplotlib's own numbers for the axis's ticks, no offset or exponent."""
    oracle = mticker.ScalarFormatter(useOffset=False)
    oracle.set_scientific(False)
    oracle.set_axis(axis)
    locs = [float(v) for v in axis.get_majorticklocs()]
    return dict(zip(locs, oracle.format_ticks(locs), strict=True))


@pytest.mark.parametrize("which", ["x", "y"])
@pytest.mark.parametrize("layout", [False, True], ids=["drawn", "laid-out"])
def test_format_axis_year_zoomed_reads_values_not_rounded_years(layout, which):
    """Diagnosis D, S4: ``2019.2-2019.8`` read ``19 19 19 20 20 20``.

    Between years every tick prints its value, as on the library's own year
    axes (``2019.2 … 2019.7``): never a rounded year, never an empty label.
    """
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    years = np.arange(2000, 2025)
    if which == "x":
        ax.plot(years, np.arange(25))
        ax.set_xlim(2019.2, 2019.8)
    else:
        ax.barh(years, np.arange(25) + 1)
        ax.set_ylim(2019.2, 2019.8)
    dm.format_axis_year(ax, axis=which, locale="ko")
    if layout:
        dm.simple_layout(fig)
    axis = ax.xaxis if which == "x" else ax.yaxis
    try:
        locs, labels = _on(axis)
        plain = _plain_values(axis)
        assert len(locs) >= 2, locs
        assert labels == [plain[v] for v in locs], labels
        assert len(set(labels)) == len(labels), labels
        assert axis.get_offset_text().get_text() == ""
    finally:
        plt.close(fig)


def test_format_axis_year_never_rounds_matplotlibs_half_years() -> None:
    """Without a layout matplotlib's locator steps 2.5 years: values, not ``08년``."""
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("17cm", "standard"))
    ax.plot(np.arange(2005, 2025), np.arange(20))
    dm.format_axis_year(ax, locale="ko")
    try:
        locs, labels = _on(ax.xaxis)
        assert any(v != round(v) for v in locs), locs  # 2007.5 …
        plain = _plain_values(ax.xaxis)
        assert labels == [plain[v] for v in locs], labels
        dm.simple_layout(fig)  # the year locator: whole years, with 년
        locs, labels = _on(ax.xaxis)
        assert labels == [f"{round(v) % 100:02d}년" for v in locs], labels
    finally:
        plt.close(fig)


def test_format_axis_year_gives_each_axis_its_own_formatter() -> None:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
    try:
        dm.format_axis_year(ax, axis="both")
        assert ax.xaxis.get_major_formatter() is not ax.yaxis.get_major_formatter()
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
