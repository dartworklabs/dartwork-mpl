"""Unit tests for dartwork_mpl.ui parameter introspection and config.

These tests cover the pure-Python logic of descriptor extraction
and config persistence — no server required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from unittest.mock import patch

import pytest
from pydantic import Field

from dartwork_mpl.ui._config import (
    CONFIG_FILENAME,
    HISTORY_FILENAME,
    append_history,
    load_config,
    load_history,
    load_presets,
    save_config,
)
from dartwork_mpl.ui._param import ParamModel
from dartwork_mpl.ui._widget import (
    ParamDescriptor,
    descriptors_from_model,
)


# ============================================================================
# Tests: descriptors_from_model
# ============================================================================


class TestDescriptorsFromModel:
    """Test extraction of ParamDescriptor from Pydantic models."""

    def test_basic_model(self) -> None:
        class M(ParamModel):
            n: int = Field(default=100, ge=10, le=500)
            alpha: float = Field(default=0.5, ge=0.0, le=1.0)

        descs = descriptors_from_model(M)
        assert len(descs) == 2

        assert descs[0].name == "n"
        assert descs[0].type_name == "int"
        assert descs[0].min_value == 10
        assert descs[0].max_value == 500
        assert descs[0].default == 100

        assert descs[1].name == "alpha"
        assert descs[1].type_name == "float"
        assert descs[1].min_value == 0.0
        assert descs[1].max_value == 1.0

    def test_literal_in_model(self) -> None:
        class M(ParamModel):
            style: Literal["solid", "dashed"] = Field(default="solid")

        descs = descriptors_from_model(M)
        assert descs[0].choices == ["solid", "dashed"]

    def test_color_widget_hint(self) -> None:
        class M(ParamModel):
            bg_color: str = Field(
                default="#000",
                json_schema_extra={"widget": "color"},
            )

        descs = descriptors_from_model(M)
        assert descs[0].widget_hint == "color"

    def test_color_auto_detect_from_name(self) -> None:
        class M(ParamModel):
            line_color: str = Field(default="#fff")

        descs = descriptors_from_model(M)
        assert descs[0].widget_hint == "color"

    def test_description_as_label(self) -> None:
        class M(ParamModel):
            n: int = Field(default=1, description="Sample count")

        descs = descriptors_from_model(M)
        assert descs[0].label == "Sample count"

    def test_step_from_extra(self) -> None:
        class M(ParamModel):
            freq: float = Field(
                default=1.0,
                ge=0.0,
                le=10.0,
                json_schema_extra={"step": 0.5},
            )

        descs = descriptors_from_model(M)
        assert descs[0].step == 0.5

    def test_bool_type(self) -> None:
        class M(ParamModel):
            flag: bool = Field(default=True)

        descs = descriptors_from_model(M)
        assert descs[0].type_name == "bool"
        assert descs[0].default is True

    def test_to_dict(self) -> None:
        class M(ParamModel):
            n: int = Field(default=10)

        descs = descriptors_from_model(M)
        d = descs[0].to_dict()
        assert d["name"] == "n"
        assert d["type_name"] == "int"
        assert d["default"] == 10

    def test_list_float(self) -> None:
        class M(ParamModel):
            ticks: list[float] = Field(default=[1.0, 2.0, 3.0])

        descs = descriptors_from_model(M)
        assert descs[0].type_name == "list_float"
        assert descs[0].default == "1.0, 2.0, 3.0"

    def test_list_int(self) -> None:
        class M(ParamModel):
            sizes: list[int] = Field(default=[10, 20])

        descs = descriptors_from_model(M)
        assert descs[0].type_name == "list_int"
        assert descs[0].default == "10, 20"

    def test_list_str(self) -> None:
        class M(ParamModel):
            labels: list[str] = Field(default=["a", "b"])

        descs = descriptors_from_model(M)
        assert descs[0].type_name == "list_str"
        assert descs[0].default == "a, b"

    def test_tuple_float(self) -> None:
        class M(ParamModel):
            coords: tuple[float, ...] = Field(default=(0.5, 1.5))

        descs = descriptors_from_model(M)
        assert descs[0].type_name == "list_float"
        assert descs[0].default == "0.5, 1.5"

    def test_empty_list(self) -> None:
        class M(ParamModel):
            items: list[float] = Field(default=[])

        descs = descriptors_from_model(M)
        assert descs[0].type_name == "list_float"
        assert descs[0].default == ""


# ============================================================================
# Tests: config persistence
# ============================================================================


class TestConfigPersistence:
    """Test save/load of config and history files."""

    def test_save_and_load_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / CONFIG_FILENAME
        with patch(
            "dartwork_mpl.ui._config._config_path",
            return_value=config_file,
        ):
            save_config(
                {"n": 42, "alpha": 0.7}, function_name="test_fn"
            )
            loaded = load_config()

        assert loaded is not None
        assert loaded["n"] == 42
        assert loaded["alpha"] == 0.7

    def test_load_config_missing(self, tmp_path: Path) -> None:
        config_file = tmp_path / CONFIG_FILENAME
        with patch(
            "dartwork_mpl.ui._config._config_path",
            return_value=config_file,
        ):
            assert load_config() is None

    def test_append_and_load_history(self, tmp_path: Path) -> None:
        history_file = tmp_path / HISTORY_FILENAME
        with patch(
            "dartwork_mpl.ui._config._history_path",
            return_value=history_file,
        ):
            append_history({"n": 1})
            append_history({"n": 2}, label="preset_a")
            append_history({"n": 3})

            records = load_history()
            assert len(records) == 3

            presets = load_presets()
            assert len(presets) == 1
            assert presets[0]["label"] == "preset_a"
            assert presets[0]["params"]["n"] == 2

    def test_history_jsonl_format(self, tmp_path: Path) -> None:
        history_file = tmp_path / HISTORY_FILENAME
        with patch(
            "dartwork_mpl.ui._config._history_path",
            return_value=history_file,
        ):
            append_history({"x": 10})
            append_history({"x": 20})

        lines = history_file.read_text().strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            data = json.loads(line)
            assert "timestamp" in data
            assert "params" in data
