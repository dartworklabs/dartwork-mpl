# tests/robustness/test_robustness_suite.py
"""Parametrized robustness harness.

Each entry in scenarios.SCENARIOS is run through the same pipeline:

    1. Build the figure via the scenario's builder function.
    2. Run dm.validate_figure to collect warnings (quiet mode).
    3. Apply dm.auto_layout to give the layout a chance to converge.
    4. Save to PNG via dm.save_formats(validate=False) so we know the
       saved bytes are well-formed.
    5. Re-run dm.validate_figure on the post-layout figure and check
       that scenario.expect_warnings is satisfied and
       scenario.forbid_warnings is empty.
    6. Apply each scenario.pixel_checks against the post-save figure.

The scenario list is imported, so growing the suite means adding
entries to scenarios.SCENARIOS (no harness changes required).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

import dartwork_mpl as dm
from tests.robustness import pixel_assertions
from tests.robustness.scenarios import SCENARIOS, RobustnessScenario


def _scenario_id(s: object) -> str:
    """Return the pytest test id for either a bare RobustnessScenario
    or a pytest.param-wrapped one (used in Task 4+ to mark
    expected-to-fail scenarios via pytest.mark.xfail)."""
    if hasattr(s, "values"):  # pytest.param ParameterSet
        return s.values[0].name  # type: ignore[attr-defined,no-any-return]
    return s.name  # type: ignore[attr-defined,no-any-return]


@pytest.mark.parametrize(
    "scenario", SCENARIOS, ids=[_scenario_id(s) for s in SCENARIOS]
)
def test_robustness_scenario(
    scenario: RobustnessScenario, tmp_image_dir: Path
) -> None:
    fig = scenario.build()

    # Stage 1: pre-layout validation.
    pre_warnings = dm.validate_figure(fig, quiet=True)
    pre_ids = {w.check_id for w in pre_warnings}
    for must_have in scenario.expect_warnings:
        assert any(must_have in cid for cid in pre_ids), (
            f"{scenario.name}: expected pre-layout check "
            f"{must_have!r} in {pre_ids!r}"
        )

    # Stage 2: layout convergence.
    dm.auto_layout(fig, max_iter=scenario.auto_layout_max_iter)

    # Stage 3: save round-trip — must not crash, and the file must be
    # non-empty (matplotlib silently writes 0-byte files on certain
    # backend errors).
    out_stem = str(tmp_image_dir / scenario.name)
    dm.save_formats(fig, out_stem, formats=("png",), validate=False)
    out_path = Path(f"{out_stem}.png")
    assert out_path.exists(), f"PNG not written for {scenario.name}"
    assert out_path.stat().st_size > 1024, (
        f"{scenario.name}: PNG suspiciously small "
        f"({out_path.stat().st_size} bytes)"
    )

    # Stage 4: post-layout validation — forbidden warnings must not appear.
    post_warnings = dm.validate_figure(fig, quiet=True)
    post_ids = {w.check_id for w in post_warnings}
    for forbidden in scenario.forbid_warnings:
        assert all(forbidden not in cid for cid in post_ids), (
            f"{scenario.name}: post-layout still has forbidden "
            f"{forbidden!r} in {post_ids!r}"
        )

    # Stage 5: pixel-level assertions registered on the scenario.
    for check_name in scenario.pixel_checks:
        check_fn = getattr(pixel_assertions, check_name)
        check_fn(fig)
