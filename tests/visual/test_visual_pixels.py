from __future__ import annotations

from collections.abc import Callable

import pytest
from matplotlib.figure import Figure

from .scenarios import Scenario, all_scenarios

_SCENARIOS = all_scenarios()


def _make_pixel_test(scenario: Scenario) -> Callable[[], Figure]:
    @pytest.mark.mpl_image_compare(
        baseline_dir="baseline",
        filename=f"{scenario.name}.png",
        style="default",
        tolerance=scenario.expect.tolerance,
    )
    def test_pixel_scenario() -> Figure:
        return scenario.build()

    test_pixel_scenario.__name__ = f"test_pixel_{scenario.name}"
    test_pixel_scenario.__qualname__ = test_pixel_scenario.__name__
    return test_pixel_scenario


for _scenario in _SCENARIOS:
    globals()[f"test_pixel_{_scenario.name}"] = _make_pixel_test(_scenario)

del _scenario
