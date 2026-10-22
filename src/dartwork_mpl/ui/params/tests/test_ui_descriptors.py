"""Descriptor extraction from ParamModel fields: kinds, bounds, hints, labels and defaults."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from dartwork_mpl.ui.params import (
    ParamModel,
    controls_from_model,
    controls_wire,
)
from dartwork_mpl.ui.params._descriptors import (
    BoolControl,
    ChoiceControl,
    ListControl,
    NumberControl,
    TextControl,
)


def descriptors_of(model: type[ParamModel]) -> list[dict]:
    """The ``/api/descriptors`` entries of ``model``."""
    return controls_wire(controls_from_model(model))


class TestDescriptorsFromModel:
    """Test the controls and their wire entries derived from Pydantic models."""

    def test_basic_model(self) -> None:
        class M(ParamModel):
            n: int = Field(default=100, ge=10, le=500)
            alpha: float = Field(default=0.5, ge=0.0, le=1.0)

        descs = descriptors_of(M)
        assert len(descs) == 2

        assert descs[0]["name"] == "n"
        assert descs[0]["type_name"] == "int"
        assert descs[0]["min_value"] == 10
        assert descs[0]["max_value"] == 500
        assert descs[0]["default"] == 100

        assert descs[1]["name"] == "alpha"
        assert descs[1]["type_name"] == "float"
        assert descs[1]["min_value"] == 0.0
        assert descs[1]["max_value"] == 1.0

    def test_literal_in_model(self) -> None:
        class M(ParamModel):
            style: Literal["solid", "dashed"] = Field(default="solid")

        descs = descriptors_of(M)
        assert descs[0]["choices"] == ["solid", "dashed"]

    def test_color_widget_hint(self) -> None:
        class M(ParamModel):
            bg_color: str = Field(
                default="#000", json_schema_extra={"widget": "color"}
            )

        descs = descriptors_of(M)
        assert descs[0]["widget_hint"] == "color"

    def test_color_auto_detect_from_name(self) -> None:
        class M(ParamModel):
            line_color: str = Field(default="#fff")

        descs = descriptors_of(M)
        assert descs[0]["widget_hint"] == "color"

    def test_description_as_label(self) -> None:
        class M(ParamModel):
            n: int = Field(default=1, description="Sample count")

        descs = descriptors_of(M)
        assert descs[0]["label"] == "Sample count"

    def test_step_from_extra(self) -> None:
        class M(ParamModel):
            freq: float = Field(
                default=1.0, ge=0.0, le=10.0, json_schema_extra={"step": 0.5}
            )

        descs = descriptors_of(M)
        assert descs[0]["step"] == 0.5

    def test_bool_type(self) -> None:
        class M(ParamModel):
            flag: bool = Field(default=True)

        descs = descriptors_of(M)
        assert descs[0]["type_name"] == "bool"
        assert descs[0]["default"] is True

    def test_to_dict(self) -> None:
        class M(ParamModel):
            n: int = Field(default=10)

        descs = descriptors_of(M)
        d = descs[0]
        assert d["name"] == "n"
        assert d["type_name"] == "int"
        assert d["default"] == 10

    def test_list_float(self) -> None:
        class M(ParamModel):
            ticks: list[float] = Field(default=[1.0, 2.0, 3.0])

        descs = descriptors_of(M)
        assert descs[0]["type_name"] == "list_float"
        assert descs[0]["default"] == "1.0, 2.0, 3.0"

    def test_list_int(self) -> None:
        class M(ParamModel):
            sizes: list[int] = Field(default=[10, 20])

        descs = descriptors_of(M)
        assert descs[0]["type_name"] == "list_int"
        assert descs[0]["default"] == "10, 20"

    def test_list_str(self) -> None:
        class M(ParamModel):
            labels: list[str] = Field(default=["a", "b"])

        descs = descriptors_of(M)
        assert descs[0]["type_name"] == "list_str"
        assert descs[0]["default"] == "a, b"

    def test_tuple_float(self) -> None:
        class M(ParamModel):
            coords: tuple[float, ...] = Field(default=(0.5, 1.5))

        descs = descriptors_of(M)
        assert descs[0]["type_name"] == "list_float"
        assert descs[0]["default"] == "0.5, 1.5"

    def test_empty_list(self) -> None:
        class M(ParamModel):
            items: list[float] = Field(default=[])

        descs = descriptors_of(M)
        assert descs[0]["type_name"] == "list_float"
        assert descs[0]["default"] == ""

    def test_group_from_extra(self) -> None:
        """Group metadata from json_schema_extra is extracted."""

        class M(ParamModel):
            n: int = Field(default=10, json_schema_extra={"group": "Signal"})

        descs = descriptors_of(M)
        assert descs[0]["group"] == "Signal"

    def test_group_default_none(self) -> None:
        """Fields without group metadata have group=None."""

        class M(ParamModel):
            n: int = Field(default=10)

        descs = descriptors_of(M)
        assert descs[0]["group"] is None


def test_each_annotation_selects_its_control_variant() -> None:
    """Kinds are variants: numbers, bools, choices, lists and the text fallback."""

    class M(ParamModel):
        n: int = 1
        x: float = 0.5
        flag: bool = True
        mode: Literal[1, 2] = 1
        values: list[float] = Field(default=[1.0])
        title: str = "t"
        other: dict = Field(default_factory=dict)

    n, x, flag, mode, values, title, other = controls_from_model(M)
    assert isinstance(n, NumberControl) and n.number == "int"
    assert isinstance(x, NumberControl) and x.number == "float"
    assert isinstance(flag, BoolControl)
    assert isinstance(mode, ChoiceControl)
    assert (mode.choices, mode.value_kind) == ((1, 2), "int")
    assert isinstance(values, ListControl) and values.item == "float"
    assert isinstance(title, TextControl) and isinstance(other, TextControl)


def test_text_valued_choice_named_color_gets_the_colour_hint() -> None:
    """The automatic colour hint follows a str wire kind, choices included."""

    class M(ParamModel):
        edge_color: Literal["red", "blue"] = "red"
        n_color: Literal[1, 2] = 1

    hints = [entry["widget_hint"] for entry in descriptors_of(M)]
    assert hints == ["color", None]
