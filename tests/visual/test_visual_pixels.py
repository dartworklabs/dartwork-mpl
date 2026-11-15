"""Pixel comparison of every scenario against its baseline PNG.

One test per scenario is generated at import time so each baseline has its
own test id; pytest-mpl compares against the baselines only under ``--mpl``.

Every scenario uses :data:`PIXEL_TOLERANCE`, set where renders are
deterministic (see ``docs/development/visual-regression.md``, Tolerance):
renders on the CI cells match the baselines byte for byte or within float
noise, so any visible change, one tick label included, fails.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure
from matplotlib.testing.compare import compare_images

from .scenarios import Scenario, all_scenarios

#: RMS (0-255) a render may differ from its baseline. Measured 2026-11-06:
#: the CI cells' renders are byte-identical to the baselines except
#: ``scatter_fit`` under NumPy 2.5 (RMS 0.007, 95 pixels); the smallest real
#: change measured (one character of one tick label) scores 1.65 and the
#: four-digit-year relabel of ``dual_axis_timeseries`` 11.18. 0.5 sits 70x
#: above that noise and 3x below the smallest change.
PIXEL_TOLERANCE = 0.5

_SCENARIOS = all_scenarios()
_BASELINE = Path(__file__).parent / "baseline"


def _make_pixel_test(scenario: Scenario) -> Callable[[], Figure]:
    @pytest.mark.mpl_image_compare(
        baseline_dir="baseline",
        filename=f"{scenario.name}.png",
        style="default",
        tolerance=PIXEL_TOLERANCE,
    )
    def test_pixel_scenario() -> Figure:
        return scenario.build()

    test_pixel_scenario.__name__ = f"test_pixel_{scenario.name}"
    test_pixel_scenario.__qualname__ = test_pixel_scenario.__name__
    return test_pixel_scenario


for _scenario in _SCENARIOS:
    globals()[f"test_pixel_{_scenario.name}"] = _make_pixel_test(_scenario)

del _scenario


def _rms_against_baseline(
    name: str, tmp_path: Path, relabel: Callable[[Figure], None] | None = None
) -> float:
    """Render scenario ``name`` as pytest-mpl does, ``relabel`` applied after
    it is built; its RMS against the baseline.

    pytest-mpl renders under the Agg backend. Without the switch the figure
    takes the process's pyplot backend (``macosx`` when this test runs alone
    on a Mac, with its own device pixel ratio), and the result would depend
    on whether an earlier test had already switched to Agg.
    """
    scenario = next(s for s in _SCENARIOS if s.name == name)
    out = tmp_path / f"{name}-{relabel is not None}.png"
    previous = plt.get_backend()
    plt.switch_backend("agg")
    try:
        with plt.style.context("default", after_reset=True):
            fig = scenario.build()
            if relabel is not None:
                relabel(fig)
            fig.savefig(out, metadata={"Software": None})
            plt.close(fig)
    finally:
        plt.switch_backend(previous)
    result = compare_images(
        str(_BASELINE / f"{name}.png"), str(out), tol=0, in_decorator=True
    )
    return 0.0 if result is None else float(result["rms"])


def _four_digit_years(fig: Figure) -> None:
    fig.axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%Y.%m"))


def test_pixel_tolerance_catches_a_tick_text_change(
    request: pytest.FixtureRequest, tmp_path: Path
) -> None:
    """The gate fails a render whose only change is the tick text.

    ``dual_axis_timeseries`` with four-digit years relabels the x ticks after
    the layout and moves nothing else; at the old 20-25 tolerances it passed (RMS 11.2).
    Baselines are compared only under ``--mpl``, on the platform they are
    made on.
    """
    if not request.config.getoption("--mpl"):
        pytest.skip("pixel baselines are compared only under --mpl")
    unchanged = _rms_against_baseline("dual_axis_timeseries", tmp_path)
    relabelled = _rms_against_baseline(
        "dual_axis_timeseries", tmp_path, _four_digit_years
    )
    assert unchanged <= PIXEL_TOLERANCE, unchanged
    assert relabelled > PIXEL_TOLERANCE, relabelled
