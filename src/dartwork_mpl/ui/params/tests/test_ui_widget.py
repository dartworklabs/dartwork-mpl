"""Tests for ui/params/_descriptors.py internal helper functions.

The high-level controls_from_model() is already tested in test_ui_descriptors.py.
This file covers the lower-level helpers: _humanize, the annotation ->
control-kind resolution, _serialize_default, and the control variants' wire
projection.
"""

from __future__ import annotations

from typing import Any

import pytest

from dartwork_mpl.ui.params._descriptors import (
    NumberControl,
    _humanize,
    _serialize_default,
    controls_from_model,
    controls_wire,
)
from dartwork_mpl.ui.params._model import ParamModel


def _type_name(annotation: Any) -> str:
    """The wire ``type_name`` of a one-field model annotated ``annotation``."""
    from pydantic import create_model

    model = create_model("M", __base__=ParamModel, x=(annotation, None))
    return controls_wire(controls_from_model(model))[0]["type_name"]


# ============================================================================
# _humanize
# ============================================================================


class TestHumanize:
    """Tests for snake_case → Title Case conversion."""

    def test_single_word(self) -> None:
        assert _humanize("alpha") == "Alpha"

    def test_multi_word(self) -> None:
        assert _humanize("line_color") == "Line Color"

    def test_three_words(self) -> None:
        assert _humanize("max_line_width") == "Max Line Width"

    def test_empty_string(self) -> None:
        assert _humanize("") == ""

    def test_no_underscores(self) -> None:
        assert _humanize("count") == "Count"


# ============================================================================
# _type_name
# ============================================================================


class TestTypeName:
    """Tests for type → string name resolution."""

    def test_int(self) -> None:
        assert _type_name(int) == "int"

    def test_float(self) -> None:
        assert _type_name(float) == "float"

    def test_str(self) -> None:
        assert _type_name(str) == "str"

    def test_bool(self) -> None:
        assert _type_name(bool) == "bool"

    def test_list_int(self) -> None:
        assert _type_name(list[int]) == "list_int"

    def test_list_float(self) -> None:
        assert _type_name(list[float]) == "list_float"

    def test_list_str(self) -> None:
        assert _type_name(list[str]) == "list_str"

    def test_list_bare(self) -> None:
        """Bare list without type args falls through to 'str'."""
        assert _type_name(list) == "str"

    def test_list_bool(self) -> None:
        """A bool item kind is spelled list_bool (its text coercion is a known defect)."""
        assert _type_name(list[bool]) == "list_bool"

    def test_tuple_float_ellipsis(self) -> None:
        assert _type_name(tuple[float, ...]) == "list_float"

    def test_unknown_type_defaults_to_str(self) -> None:
        """Unknown types fall back to 'str'."""
        assert _type_name(dict) == "str"


# ============================================================================
# _serialize_default
# ============================================================================


class TestSerializeDefault:
    """Tests for default value serialization."""

    def test_none_for_scalar(self) -> None:
        assert _serialize_default(None, False) is None

    def test_none_for_list(self) -> None:
        """None defaults to empty string for list types."""
        assert _serialize_default(None, True) == ""

    def test_list_to_comma_str(self) -> None:
        assert _serialize_default([1, 2, 3], True) == "1, 2, 3"

    def test_tuple_to_comma_str(self) -> None:
        assert _serialize_default((0.5, 1.5), True) == "0.5, 1.5"

    def test_empty_list(self) -> None:
        assert _serialize_default([], True) == ""

    def test_scalar_passthrough(self) -> None:
        assert _serialize_default(42, False) == 42
        assert _serialize_default("hello", False) == "hello"


# ============================================================================
# Control variants and their wire projection
# ============================================================================


def _number(**changes: Any) -> NumberControl:
    """A plain int control with optional field overrides."""
    fields: dict[str, Any] = {
        "name": "n",
        "label": "N",
        "default": 10,
        "minimum": None,
        "maximum": None,
        "widget_hint": None,
        "extra": {},
        "number": "int",
    }
    return NumberControl(**{**fields, **changes})


class TestParamDescriptor:
    """Tests for the wire projection of one control."""

    def test_to_dict_contains_all_fields(self) -> None:
        d = controls_wire([_number()])[0]
        assert list(d) == [
            "name",
            "label",
            "type_name",
            "default",
            "min_value",
            "max_value",
            "step",
            "group",
            "choices",
            "widget_hint",
            "extra",
        ]
        assert d["name"] == "n"
        assert d["label"] == "N"
        assert d["type_name"] == "int"
        assert d["default"] == 10
        assert d["min_value"] is None
        assert d["max_value"] is None

    def test_extra_defaults_to_empty_dict(self) -> None:
        d = controls_wire([_number(number="float", default=None)])[0]
        assert d["extra"] == {}
        assert d["type_name"] == "float"

    def test_step_and_group_come_from_extra_and_are_detached(self) -> None:
        extra = {"step": 0.5, "group": "G", "nested": [1]}
        d = controls_wire([_number(extra=extra)])[0]
        assert (d["step"], d["group"]) == (0.5, "G")
        d["extra"]["nested"].append(2)
        assert extra["nested"] == [1]

    def test_controls_are_frozen(self) -> None:
        with pytest.raises(AttributeError):
            _number().name = "m"  # type: ignore[misc]
