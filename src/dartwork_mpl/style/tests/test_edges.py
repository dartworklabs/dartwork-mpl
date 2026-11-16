"""The step's named edge cases."""

from __future__ import annotations

import pytest

from dartwork_mpl.edgecase import settle
from dartwork_mpl.style import apply, decide
from dartwork_mpl.style.edges import EDGES
from dartwork_mpl.style.model import Active


def _step(names, in_force=True):
    active = Active(apply.REGISTRY.parse(names), in_force)
    return settle(active, decide.step(active), EDGES)


@pytest.mark.parametrize("name", ["presentation", "presentation-kr"])
def test_slide_step_is_scientific_times_2_6(name):
    settled = _step(name)
    assert settled.fired == ("slide-step",)
    assert settled.plan.pt == pytest.approx(2.6)


@pytest.mark.parametrize(
    ("names", "in_force"),
    [
        ("scientific", True),
        (["presentation", "report"], True),
        ("presentation", False),
    ],
)
def test_no_slide_step_off_a_slide_or_after_a_reset(names, in_force):
    settled = _step(names, in_force)
    assert settled.fired == ()
    assert settled.plan.pt == 1.0
