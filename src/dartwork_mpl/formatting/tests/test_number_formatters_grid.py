"""Tick text of the numeric-unit formatters, pinned over fixed ticks.

``format_axis_millions`` / ``_billions`` / ``_currency`` / ``_si`` /
``_myriad`` and ``axis_unit`` share one formatter engine. The golden file
holds what every case printed before their implementations were merged into
it (one line per case): direct values (no draw), ``format_ticks`` on fixed
ticks under a set view (``x``, ``y`` or ``both``), the same ticks with
``axes.unicode_minus`` off, and decade ticks on a log axis. ``axis_unit``
cases also record the axis label it writes. Any difference is a behaviour
change.
"""

from __future__ import annotations

import itertools
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.axis import Axis

import dartwork_mpl as dm

_GOLDEN = Path(__file__).with_name("number_formatters_golden.tsv")

_VALUES = (
    0.0,
    -0.0,
    0.4,
    -0.04,
    -0.4,
    2.5,
    999.9999999,
    1000.0,
    -1500.0,
    9999.5,
    12_345.678,
    999_999.0,
    1e6,
    -1.25e6,
    2.5e9,
    1e15,
    float("inf"),
    float("-inf"),
    float("nan"),
)
_RANGES = (
    (0.0, 2.5),
    (-1.0, 1.0),
    (0.0, 800.0),
    (0.0, 10_000.0),
    (-50_000.0, 50_000.0),
    (0.0, 1.25e6),
    (-3e6, 3e6),
    (999_000.0, 1_001_000.0),
    (0.0, 2.5e8),
    (0.0, 3.4e9),
    (-3e12, 3e12),
    (0.001, 0.009),
)
#: Fixed tick locations per range: the golden does not depend on
#: matplotlib's tick placement, text size or canvas.
_TICKS = {
    (low, high): [float(v) for v in np.linspace(low, high, 6)]
    for low, high in _RANGES
}
_LOG_TICKS = [10.0**k for k in range(10)]

_FUNCS: dict[str, Callable[..., Any]] = {
    "millions": dm.format_axis_millions,
    "billions": dm.format_axis_billions,
    "currency": dm.format_axis_currency,
    "si": dm.format_axis_si,
    "myriad": dm.format_axis_myriad,
    "axis_unit": dm.axis_unit,
}
_CONFIGS: dict[str, tuple[dict[str, Any], ...]] = {
    "millions": (
        {},
        {"decimals": 1},
        {"decimals": 0},
        {"decimals": 2},
        {"suffix": ""},
        {"suffix": "", "decimals": 1},
        {"suffix": "백만", "decimals": 0},
    ),
    "billions": (
        {},
        {"decimals": 1},
        {"decimals": 0},
        {"suffix": "bn", "decimals": 2},
    ),
    "currency": (
        {},
        {"symbol": "€", "position": "suffix", "decimals": 2},
        {"decimals": 2},
        {"symbol": "€", "position": "suffix"},
        {"symbol": "₩"},
        {"symbol": "", "decimals": 1},
        {"symbol": "USD ", "decimals": 1},
    ),
    "si": (
        {},
        {"decimals": 1},
        {"decimals": 0},
        {"decimals": 2},
        {"unit": "whole"},
        {"unit": "k"},
        {"unit": "M", "decimals": 1},
        {"unit": "", "decimals": 0},
        {"unit": "whole", "decimals": 1},
    ),
    "myriad": (
        {},
        {"decimals": 1},
        {"locale": "zh"},
        {"locale": "ja", "currency": "$"},
        {"unit": "whole"},
        {"unit": "억"},
        {"decimals": 0, "currency": "₩"},
        {"locale": "ja", "decimals": 2},
    ),
    "axis_unit": (
        {"ladder": "si"},
        {"ladder": "myriad", "label": "매출 ({unit}원)"},
        {"ladder": "finance", "label": "Revenue (USD {unit})", "decimals": 1},
        {"ladder": "si", "scale": "whole"},
        {"ladder": "myriad", "scale": "만"},
    ),
}


def _kwargs_id(kwargs: dict[str, Any]) -> str:
    return ",".join(f"{k}={v!r}" for k, v in sorted(kwargs.items()))


def _cases() -> tuple[tuple[str, str, dict[str, Any]], ...]:
    """Every config on ``y``; the first two of each function also on ``x``
    and ``both`` (``axis_unit`` takes ``x`` and ``y`` only)."""
    cases = []
    for name, configs in _CONFIGS.items():
        for index, kwargs in enumerate(configs):
            axes = ("y",)
            if index < 2:
                axes = ("x", "y") if name == "axis_unit" else ("x", "y", "both")
            cases.extend((name, axis, kwargs) for axis in axes)
    return tuple(cases)


_CASES = _cases()


def _case_id(name: str, axis: str, kwargs: dict[str, Any]) -> str:
    return f"{name}|{axis}|{_kwargs_id(kwargs)}"


def _apply(ax: Axes, name: str, axis: str, kwargs: dict[str, Any]) -> None:
    _FUNCS[name](ax, axis, **kwargs)


def _new_axes() -> tuple[Any, Axes]:
    dm.style.use("scientific")
    return plt.subplots(figsize=dm.figsize("9cm", "standard"))


def _targets(ax: Axes, axis: str) -> dict[str, Axis]:
    names = ("x", "y") if axis == "both" else (axis,)
    return {n: ax.xaxis if n == "x" else ax.yaxis for n in names}


def _guard(call: Callable[[], str]) -> str:
    try:
        return call()
    except Exception as exc:  # the error class is the output
        return f"!{type(exc).__name__}"


def _ranges(ax: Axes, target: Axis, label: bool) -> dict[str, list[str]]:
    out = {}
    formatter = target.get_major_formatter()
    for low, high in _RANGES:
        target.set_view_interval(low, high, ignore=True)
        texts = list(formatter.format_ticks(_TICKS[(low, high)]))
        if label:
            texts.append(f"label={target.label.get_text()}")
        out[f"{low:g}..{high:g}"] = texts
    low, high = _RANGES[6]
    target.set_view_interval(low, high, ignore=True)
    with mpl.rc_context({"axes.unicode_minus": False}):
        out["ascii minus"] = list(formatter.format_ticks(_TICKS[(low, high)]))
    return out


def _render_case(
    name: str, axis: str, kwargs: dict[str, Any]
) -> dict[str, Any]:
    label = name == "axis_unit"
    out: dict[str, Any] = {}
    fig, ax = _new_axes()
    try:
        _apply(ax, name, axis, kwargs)
        targets = _targets(ax, axis)
        if axis != "both":
            formatter = targets[axis].get_major_formatter()
            out["values"] = [_guard(lambda v=v: formatter(v)) for v in _VALUES]
        for which, target in targets.items():
            out[which] = _ranges(ax, target, label)
    finally:
        plt.close(fig)
    # Log scale first: setting a scale resets the axis's formatter.
    fig, ax = _new_axes()
    try:
        if axis in ("x", "both"):
            ax.set_xscale("log")
        if axis in ("y", "both"):
            ax.set_yscale("log")
        _apply(ax, name, axis, kwargs)
        for which, target in _targets(ax, axis).items():
            target.set_view_interval(1.0, 1e9, ignore=True)
            out[f"{which} log"] = list(
                target.get_major_formatter().format_ticks(_LOG_TICKS)
            )
    finally:
        plt.close(fig)
    return out


def _compute() -> dict[str, dict[str, Any]]:
    return {_case_id(*case): _render_case(*case) for case in _CASES}


def _load() -> dict[str, dict[str, Any]]:
    """One line per case: ``id<TAB>json``."""
    golden: dict[str, dict[str, Any]] = {}
    for line in _GOLDEN.read_text(encoding="utf-8").splitlines():
        key, payload = line.split("\t", 1)
        golden[key] = json.loads(payload)
    return golden


@pytest.fixture(scope="module")
def golden() -> dict[str, dict[str, Any]]:
    return _load()


@pytest.mark.filterwarnings("ignore:Glyph .* missing from font")
@pytest.mark.parametrize("case", _CASES, ids=[_case_id(*c) for c in _CASES])
def test_number_formatter_output_is_pinned(
    case: tuple[str, str, dict[str, Any]], golden: dict[str, dict[str, Any]]
) -> None:
    """Every value and tick text matches what the golden file recorded."""
    assert _render_case(*case) == golden[_case_id(*case)]


def test_number_formatter_golden_covers_every_case(
    golden: dict[str, dict[str, Any]],
) -> None:
    """The golden file has an entry for each case and no others."""
    assert set(golden) == {_case_id(*case) for case in _CASES}


def test_cases_cover_axes_decimals_and_currency() -> None:
    """The grid holds every axis choice, fixed decimals and both positions."""
    seen = {(name, axis) for name, axis, _kwargs in _CASES}
    for name in _FUNCS:
        axes = ("x", "y") if name == "axis_unit" else ("x", "y", "both")
        assert all((name, axis) in seen for axis in axes)
    kinds = {
        (name, "decimals" in kwargs, kwargs.get("position"))
        for name, kwargs in itertools.chain.from_iterable(
            ((n, k) for k in c) for n, c in _CONFIGS.items()
        )
    }
    assert ("currency", True, "suffix") in kinds
    assert ("currency", False, None) in kinds
    for name in ("millions", "billions", "si", "myriad"):
        assert (name, True, None) in kinds and (name, False, None) in kinds


if __name__ == "__main__":
    # Rewrites the golden. Run it only for an intended change of these
    # formatters' output; never to make a failure pass.
    _GOLDEN.write_text(
        "".join(
            f"{key}\t{json.dumps(value, ensure_ascii=False)}\n"
            for key, value in sorted(_compute().items())
        ),
        encoding="utf-8",
    )
