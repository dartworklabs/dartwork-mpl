"""Robustness suite ↔ anti-pattern catalog alignment (T7).

Two SSOTs describe "things AI agents get wrong":

1. ``src/dartwork_mpl/asset/prompt/02-anti-patterns.yaml`` — static
   regex/substring patterns the lint engine flags in source code.
2. ``tests/robustness/scenarios.py`` — runtime/visual problems
   ``validate_figure()`` catches at render time (long labels, twinx,
   NaN data, log scale, dense ticks, …).

These cover **different layers** of the agent's failure space:
linting can't see overflowing tick labels, and validate_figure can't
see ``figsize=(...)`` in the source. T7's contract is therefore not
"every scenario maps to a rule" but "every scenario declares which
SSOT it belongs to, and any scenario that *does* claim a rule
references one that actually exists."

This file is the meta-test that enforces that contract.
"""

from __future__ import annotations

from collections.abc import Iterator

from dartwork_mpl.lint import load_rules

from .scenarios import SCENARIOS, RobustnessScenario


def _all_rule_ids() -> set[str]:
    return {r.id for r in load_rules()}


def _unwrap(entry: object) -> RobustnessScenario:
    """Return the underlying ``RobustnessScenario``.

    A few entries in ``SCENARIOS`` are wrapped in ``pytest.param(...)``
    because they sit on the KNOWN_LIMITATIONS xfail list. Strip that
    wrapper if present so the alignment test sees a uniform stream.
    """
    if isinstance(entry, RobustnessScenario):
        return entry
    # ``pytest.param`` returns a ``ParameterSet`` whose first value is
    # the wrapped scenario.
    values = getattr(entry, "values", None)
    if values:
        scenario = values[0]
        if isinstance(scenario, RobustnessScenario):
            return scenario
    raise TypeError(f"unexpected SCENARIOS entry: {entry!r}")


def _iter_scenarios() -> Iterator[RobustnessScenario]:
    for entry in SCENARIOS:
        yield _unwrap(entry)


def test_every_scenario_has_a_category() -> None:
    """Each scenario must declare ``visual-only`` or ``rule:<id>``."""
    for scenario in _iter_scenarios():
        category = scenario.category
        assert category == "visual-only" or category.startswith("rule:"), (
            f"scenario {scenario.name!r} has invalid category "
            f"{category!r}; use 'visual-only' or 'rule:<rule-id>'"
        )


def test_rule_categories_reference_existing_rules() -> None:
    """When a scenario claims a lint rule, that rule must exist in
    the bundled anti-pattern catalog."""
    rule_ids = _all_rule_ids()
    for scenario in _iter_scenarios():
        category = scenario.category
        if not category.startswith("rule:"):
            continue
        rule_id = category.removeprefix("rule:")
        assert rule_id in rule_ids, (
            f"scenario {scenario.name!r} references unknown rule "
            f"{rule_id!r}; known rules: {sorted(rule_ids)}"
        )


def test_coverage_summary_shape() -> None:
    """Print a small coverage summary so CI logs surface the split.

    This is informational — the assertion is just that we can
    compute the split (i.e. the scenario list is non-empty)."""
    scenarios = list(_iter_scenarios())
    assert scenarios, "robustness suite is empty"

    visual_only = [s for s in scenarios if s.category == "visual-only"]
    rule_mapped = [s for s in scenarios if s.category.startswith("rule:")]

    print()
    print(f"  total scenarios     : {len(scenarios)}")
    print(f"  visual-only         : {len(visual_only)}")
    print(f"  mapped to lint rule : {len(rule_mapped)}")
    if rule_mapped:
        print("  --- rule mappings ---")
        for s in rule_mapped:
            print(f"    {s.name:40s} → {s.category}")


def test_per_scenario_category_string() -> None:
    """Per-scenario classification with one assertion failure per
    offender so the report names the bad scenario directly.

    A plain loop (not parametrize) is used here because parametrize
    interacts badly with the ``pytest.param(..., marks=xfail)``
    wrappers in ``SCENARIOS``: the alignment test would inherit the
    xfail mark and report XPASS / XFAIL instead of plain pass/fail.
    """
    bad: list[str] = []
    for scenario in _iter_scenarios():
        category = scenario.category
        if not isinstance(category, str) or not category:
            bad.append(f"{scenario.name}: empty/non-str category")
            continue
        if category != "visual-only" and not category.startswith("rule:"):
            bad.append(
                f"{scenario.name}: category {category!r} is neither "
                "'visual-only' nor 'rule:<id>'"
            )
    assert not bad, "category violations:\n  " + "\n  ".join(bad)
