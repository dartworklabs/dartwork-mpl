"""Shared JSON helpers of the verify slice."""

from __future__ import annotations

import math

import pytest

from dartwork_mpl._colors.verify._json import (
    as_mapping,
    finite_number,
    freeze,
    thaw,
)


def test_freeze_sorts_detaches_and_thaw_round_trips() -> None:
    source = {"b": [1, {"z": None}], "a": "x"}

    frozen = freeze(source, subject="probe")
    source["b"].append("mutated")  # type: ignore[union-attr]

    assert thaw(frozen) == {"a": "x", "b": [1, {"z": None}]}
    assert list(thaw(frozen)) == ["a", "b"]  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        frozen["a"] = "y"  # type: ignore[index]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ({1: "x"}, "gate mappings require string keys"),
        ({"a": object()}, "unsupported gate value: object"),
    ],
)
def test_freeze_rejects_non_json_data_naming_its_subject(
    value: object, message: str
) -> None:
    with pytest.raises(TypeError, match=message):
        freeze(value, subject="gate")


def test_readers_return_none_for_malformed_values() -> None:
    assert as_mapping({1: 2}) is None
    assert as_mapping(["a"]) is None
    assert as_mapping({"a": 1}) == {"a": 1}
    assert finite_number(True) is None
    assert finite_number(math.inf) is None
    assert finite_number(3) == 3.0
