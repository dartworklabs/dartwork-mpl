from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.ticker import Formatter

import dartwork_mpl as dm


def _myriad_formatter(
    *, locale: str = "ko", currency: str = ""
) -> tuple[Figure, Formatter]:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    ax.plot([0, 1], [0, 150_000_000])
    dm.format_axis_myriad(ax, axis="y", locale=locale, currency=currency)
    return fig, ax.yaxis.get_major_formatter()


def test_format_axis_myriad_ko_units() -> None:
    fig, fmt = _myriad_formatter()
    try:
        assert fmt(12_300_000) == "1,230만"
        assert fmt(150_000_000) == "1.5억"
        assert fmt(1_200_000_000_000) == "1.2조"
        assert fmt(1_0000_0000_0000_0000) == "1경"
        assert fmt(8_000) == "8,000"
        assert fmt(0) == "0"
        assert fmt(-150_000_000) == "-1.5억"
        assert fmt(100_000_000) == "1억"
    finally:
        plt.close(fig)


def test_format_axis_myriad_zh_units() -> None:
    fig, fmt = _myriad_formatter(locale="zh")
    try:
        assert fmt(150_000_000) == "1.5亿"
    finally:
        plt.close(fig)


def test_format_axis_myriad_ja_units() -> None:
    fig, fmt = _myriad_formatter(locale="ja")
    try:
        assert fmt(150_000_000) == "1.5億"
    finally:
        plt.close(fig)


def test_format_axis_myriad_currency_prefix() -> None:
    fig, fmt = _myriad_formatter(currency="₩")
    try:
        assert fmt(150_000_000) == "₩1.5억"
        assert fmt(-150_000_000) == "-₩1.5억"
    finally:
        plt.close(fig)
