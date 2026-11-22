"""The ordinary font table and which weight misses are by design."""

import pytest

from dartwork_mpl.font.decide import is_expected, lead_plan, table_plan
from dartwork_mpl.font.model import (
    Candidate,
    Expected,
    Face,
    Lead,
    MathText,
    Table,
    Weight,
    WeightMiss,
)


def test_the_ordinary_table_keeps_order_and_declared_weights():
    faces = (
        Face("Roboto-Light.ttf", "Roboto", Weight(300), True),
        Face("Arial.ttf", "Arial", Weight("normal"), False),
    )
    plan = table_plan(Table(faces))
    assert plan.order == (0, 1)
    assert plan.weights == (Weight(300), Weight("normal"))


def test_single_weight_families_are_bundled_names_with_one_file():
    faces = (
        Face("NotoSansMath-Regular.ttf", "Noto Sans Math", Weight(400), True),
        Face("Roboto-Light.ttf", "Roboto", Weight(300), True),
        Face("Roboto-Bold.ttf", "Roboto", Weight(700), True),
        Face("Arial.ttf", "Arial", Weight(400), False),
    )
    assert Table(faces).single_weight_families() == {"Noto Sans Math"}


EXPECTED = Expected(
    single_weight=frozenset({"Noto Sans Math"}),
    math=frozenset({"STIXGeneral"}),
    preset_weight=Weight("light"),
)


@pytest.mark.parametrize(
    ("family", "weight", "quiet"),
    [
        ("Noto Sans Math", "bold", True),  # one-weight fallback, any weight
        ("STIXGeneral", "light", True),  # math font at the preset weight
        ("STIXGeneral", "thin", False),  # the caller asked for thin
        ("Roboto", "light", False),  # a real miss
    ],
)
def test_weight_misses(family, weight, quiet):
    miss = WeightMiss(family, Weight(weight))
    assert is_expected(miss, EXPECTED) is quiet


def test_a_mathtext_string_keeps_its_first_family():
    text = MathText((Candidate("Inter", True), Candidate("Paperlogy", True)))
    assert lead_plan(text) == Lead(0)
