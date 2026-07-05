# tests/robustness/test_robustness_suite.py
"""Parametrized robustness harness.

Each entry in scenarios.SCENARIOS is run through the same pipeline:

    1. Build the figure via the scenario's builder function.
    2. Run dm.validate_figure pre-layout and check that
       scenario.expect_warnings substrings appear in the warning ids.
    3. Apply dm.simple_layout to give the layout a chance to converge.
    4. Save to PNG via dm.save_formats(validate=False) so we know the
       saved bytes are well-formed.
    5. Re-run dm.validate_figure post-layout and check that
       scenario.forbid_warnings substrings are absent.
    6. Apply each scenario.pixel_checks against the post-save figure.

The scenario list is imported, so growing the suite means adding
entries to scenarios.SCENARIOS (no harness changes required).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import dartwork_mpl as dm
from tests.robustness import pixel_assertions
from tests.robustness.scenarios import SCENARIOS, RobustnessScenario

# A blank 13 cm canvas renders to >8 KB on the Agg backend. 1 KB is a
# conservative floor that catches 0-byte writes from a backend error
# while never tripping on a legitimately rendered figure.
_MIN_PNG_BYTES: int = 1024


def _scenario_id(s: object) -> str:
    """Return the pytest test id for either a bare RobustnessScenario
    or for a ``pytest.param``-wrapped one if any are ever added (none
    today).

    pytest.param exposes ``.values``; RobustnessScenario has none.
    """
    if hasattr(s, "values"):
        return s.values[0].name  # type: ignore[attr-defined,no-any-return]
    return s.name  # type: ignore[attr-defined,no-any-return]


@pytest.mark.parametrize(
    "scenario", SCENARIOS, ids=[_scenario_id(s) for s in SCENARIOS]
)
def test_robustness_scenario(
    scenario: RobustnessScenario, tmp_image_dir: Path
) -> None:
    # Stage 0: build the figure.
    fig = scenario.build()

    # Stage 1: pre-layout validation.
    pre_warnings = dm.validate_figure(fig, quiet=True)
    pre_ids = {w.check_id for w in pre_warnings}
    for must_have in scenario.expect_warnings:
        assert any(must_have in cid for cid in pre_ids), (
            f"{scenario.name}: expected pre-layout check "
            f"{must_have!r} in {pre_ids!r}"
        )

    # Stage 2: layout convergence. The ``layout_padding`` field
    # is in inches (legacy ``simple_layout`` semantics); convert to a
    # :class:`~dartwork_mpl.Length` so the new ``simple_layout`` keeps
    # the same physical margin. ``simple_layout_max_iter`` no longer
    # has an effect — direct-calc converges deterministically.
    margin = (
        dm.Length.from_inch(scenario.layout_padding)
        if scenario.layout_padding
        else 0
    )
    dm.simple_layout(fig, margin=margin)

    # Stage 3: save round-trip — must not crash, and the file must be
    # non-empty (matplotlib silently writes 0-byte files on certain
    # backend errors).
    out_stem = str(tmp_image_dir / scenario.name)
    dm.save_formats(fig, out_stem, formats=("png",), validate=False)
    out_path = Path(f"{out_stem}.png")
    assert out_path.exists(), f"PNG not written for {scenario.name}"
    assert out_path.stat().st_size > _MIN_PNG_BYTES, (
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
        check_fn = getattr(pixel_assertions, check_name, None)
        if check_fn is None:
            raise AttributeError(
                f"{scenario.name}: pixel check {check_name!r} not found "
                f"in pixel_assertions"
            )
        check_fn(fig)
