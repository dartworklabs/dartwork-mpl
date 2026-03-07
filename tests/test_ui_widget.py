"""Tests for ui/_widget.py internal helper functions.

The high-level descriptors_from_model() is already tested in test_ui_param.py.
This file covers the lower-level helpers: _humanize, _type_name,
_serialize_default, and ParamDescriptor.
"""

from __future__ import annotations

from dartwork_mpl.ui._widget import (
    ParamDescriptor,
    _humanize,
    _serialize_default,
    _type_name,
)


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
        assert _serialize_default(None, "int") is None

    def test_none_for_list(self) -> None:
        """None defaults to empty string for list types."""
        assert _serialize_default(None, "list_float") == ""

    def test_list_to_comma_str(self) -> None:
        assert _serialize_default([1, 2, 3], "list_int") == "1, 2, 3"

    def test_tuple_to_comma_str(self) -> None:
        assert _serialize_default((0.5, 1.5), "list_float") == "0.5, 1.5"

    def test_empty_list(self) -> None:
        assert _serialize_default([], "list_float") == ""

    def test_scalar_passthrough(self) -> None:
        assert _serialize_default(42, "int") == 42
        assert _serialize_default("hello", "str") == "hello"


# ============================================================================
# ParamDescriptor
# ============================================================================


class TestParamDescriptor:
    """Tests for ParamDescriptor dataclass."""

    def test_to_dict_contains_all_fields(self) -> None:
        desc = ParamDescriptor(
            name="n",
            label="N",
            type_name="int",
            default=10,
        )
        d = desc.to_dict()
        assert d["name"] == "n"
        assert d["label"] == "N"
        assert d["type_name"] == "int"
        assert d["default"] == 10
        assert d["min_value"] is None
        assert d["max_value"] is None

    def test_extra_defaults_to_empty_dict(self) -> None:
        desc = ParamDescriptor(
            name="x", label="X", type_name="float"
        )
        assert desc.extra == {}
