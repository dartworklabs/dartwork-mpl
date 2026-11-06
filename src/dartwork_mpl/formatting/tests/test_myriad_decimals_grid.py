"""``format_axis_myriad(decimals=n)`` output pinned over a wide input grid.

``decimals=n`` with the default ``unit="max"`` formats each tick in its own
unit, rounded to ``n`` places with trailing zeros trimmed. The golden file
holds the text every combination printed before the two formatter
implementations were merged; any difference is a behaviour change.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

import dartwork_mpl as dm

_GOLDEN = Path(__file__).with_name("myriad_decimals_golden.json")

_VALUES = (
    0.0,
    -0.0,
    0.4,
    1.0,
    -1.0,
    2.5,
    9999.4,
    9999.5,
    9999.99,
    10_000.0,
    -10_000.0,
    12_345.678,
    99_999.0,
    123_456.0,
    1.5e6,
    12_300_000.0,
    99_990_000.0,
    1e8,
    -1.5e8,
    123_456_789.123,
    -2.5e9,
    1e12,
    3.14159e13,
    9.99e15,
    1e16,
    1.5e17,
    1e20,
    float("inf"),
    float("-inf"),
)
_RANGES = (
    (0.0, 100.0),
    (0.0, 9999.0),
    (0.0, 10_000.0),
    (-50_000.0, 50_000.0),
    (0.0, 2.5e8),
    (1e8, 3.5e8),
    (0.0, 1.2345e12),
    (-3e12, 3e12),
    (0.0, 1e17),
    (0.001, 0.009),
    (-1.0, 1.0),
    (0.0, 2.5),
)
_CASES = tuple(
    itertools.product(("ko", "ja", "zh"), (0, 1, 2, 3), ("", "$"), ("max",))
) + tuple(
    itertools.product(("ko",), (0, 1, 3), ("",), ("whole", "만", "억", ""))
)


def _case_id(locale: str, decimals: int, currency: str, unit: str) -> str:
    return f"{locale}|{decimals}|{currency}|{unit}"


def _render_case(
    locale: str, decimals: int, currency: str, unit: str
) -> dict[str, list[str]]:
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("9cm", "standard"))
    try:
        dm.format_axis_myriad(
            ax,
            "y",
            locale=locale,
            decimals=decimals,
            currency=currency,
            unit=unit,
        )
        formatter = ax.yaxis.get_major_formatter()
        out = {"values": [formatter(v) for v in _VALUES]}
        for low, high in _RANGES:
            ax.set_ylim(low, high)
            fig.canvas.draw()
            out[f"range {low:g}..{high:g}"] = [
                t.get_text() for t in ax.get_yticklabels()
            ]
        return out
    finally:
        plt.close(fig)


def _compute() -> dict[str, dict[str, list[str]]]:
    return {_case_id(*case): _render_case(*case) for case in _CASES}


@pytest.fixture(scope="module")
def golden() -> dict[str, dict[str, list[str]]]:
    return json.loads(_GOLDEN.read_text(encoding="utf-8"))


@pytest.mark.filterwarnings("ignore:Glyph .* missing from font")
@pytest.mark.parametrize("case", _CASES, ids=[_case_id(*c) for c in _CASES])
def test_myriad_decimals_output_is_pinned(
    case: tuple[str, int, str, str], golden: dict[str, dict[str, list[str]]]
) -> None:
    """Every tick and value text matches what the golden file recorded."""
    assert _render_case(*case) == golden[_case_id(*case)]


def test_myriad_decimals_golden_covers_every_case(
    golden: dict[str, dict[str, list[str]]],
) -> None:
    """The golden file has an entry for each case and no others."""
    assert set(golden) == {_case_id(*case) for case in _CASES}


if __name__ == "__main__":
    _GOLDEN.write_text(
        json.dumps(_compute(), ensure_ascii=False, indent=1, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
