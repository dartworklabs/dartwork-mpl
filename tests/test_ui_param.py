"""Unit tests for dartwork_mpl.ui parameter introspection and config.

These tests cover the pure-Python logic of descriptor extraction
and config persistence — no server required.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from unittest.mock import patch

from pydantic import Field

from dartwork_mpl.ui._config import (
    CONFIG_FILENAME,
    PRESET_FILENAME,
    delete_preset,
    load_config,
    load_presets,
    save_config,
    save_preset,
)
from dartwork_mpl.ui._param import ParamModel
from dartwork_mpl.ui._widget import descriptors_from_model

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
                default="#000", json_schema_extra={"widget": "color"}
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
                default=1.0, ge=0.0, le=10.0, json_schema_extra={"step": 0.5}
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

    def test_group_from_extra(self) -> None:
        """Group metadata from json_schema_extra is extracted."""

        class M(ParamModel):
            n: int = Field(default=10, json_schema_extra={"group": "Signal"})

        descs = descriptors_from_model(M)
        assert descs[0].group == "Signal"

    def test_group_default_none(self) -> None:
        """Fields without group metadata have group=None."""

        class M(ParamModel):
            n: int = Field(default=10)

        descs = descriptors_from_model(M)
        assert descs[0].group is None


# ============================================================================
# Tests: config persistence
# ============================================================================


class TestConfigPersistence:
    """Test save/load of config and history files."""

    def test_save_and_load_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / CONFIG_FILENAME
        with patch(
            "dartwork_mpl.ui._config._config_path", return_value=config_file
        ):
            save_config({"n": 42, "alpha": 0.7}, function_name="test_fn")
            loaded = load_config()

        assert loaded is not None
        assert loaded["params"]["n"] == 42
        assert loaded["params"]["alpha"] == 0.7

    def test_load_config_missing(self, tmp_path: Path) -> None:
        config_file = tmp_path / CONFIG_FILENAME
        with patch(
            "dartwork_mpl.ui._config._config_path", return_value=config_file
        ):
            assert load_config() is None

    def test_save_and_load_preset_json(self, tmp_path: Path) -> None:
        """Presets are saved to and loaded from JSON."""
        preset_file = tmp_path / PRESET_FILENAME
        with patch(
            "dartwork_mpl.ui._config._preset_path", return_value=preset_file
        ):
            save_preset("test_a", {"n": 1})
            save_preset("test_b", {"n": 2})
            presets = load_presets()

        assert len(presets) == 2
        assert presets[0]["label"] == "test_a"
        assert presets[0]["params"]["n"] == 1
        assert presets[1]["label"] == "test_b"

    def test_delete_preset(self, tmp_path: Path) -> None:
        """Deleting a preset removes it from the list."""
        preset_file = tmp_path / PRESET_FILENAME
        with patch(
            "dartwork_mpl.ui._config._preset_path", return_value=preset_file
        ):
            save_preset("a", {"x": 1})
            save_preset("b", {"x": 2})
            save_preset("c", {"x": 3})

            ok = delete_preset(1)  # delete "b"
            assert ok is True

            remaining = load_presets()
            assert len(remaining) == 2
            assert remaining[0]["label"] == "a"
            assert remaining[1]["label"] == "c"

    def test_delete_preset_invalid_index(self, tmp_path: Path) -> None:
        """Deleting with invalid index returns False."""
        preset_file = tmp_path / PRESET_FILENAME
        with patch(
            "dartwork_mpl.ui._config._preset_path", return_value=preset_file
        ):
            save_preset("a", {"x": 1})
            assert delete_preset(5) is False
            assert delete_preset(-1) is False
            assert len(load_presets()) == 1

    def test_save_config_with_tabs_and_fig_width(self, tmp_path: Path) -> None:
        """save_config persists tabs and figWidth when given."""
        config_file = tmp_path / CONFIG_FILENAME
        with patch(
            "dartwork_mpl.ui._config._config_path", return_value=config_file
        ):
            save_config(
                {"n": 1},
                function_name="fn",
                tabs=[{"id": "tab1"}],
                fig_width=80,
            )
            loaded = load_config()

        assert loaded is not None
        assert loaded["tabs"] == [{"id": "tab1"}]
        assert loaded["figWidth"] == 80

    def test_load_config_corrupt_json(self, tmp_path: Path) -> None:
        """Corrupt JSON returns None instead of crashing."""
        config_file = tmp_path / CONFIG_FILENAME
        config_file.write_text("{invalid json!!!", encoding="utf-8")
        with patch(
            "dartwork_mpl.ui._config._config_path", return_value=config_file
        ):
            assert load_config() is None

    def test_load_presets_corrupt_json(self, tmp_path: Path) -> None:
        """Corrupt preset file returns empty list."""
        preset_file = tmp_path / PRESET_FILENAME
        preset_file.write_text("not valid json", encoding="utf-8")
        with patch(
            "dartwork_mpl.ui._config._preset_path", return_value=preset_file
        ):
            assert load_presets() == []

    def test_load_presets_non_list_json(self, tmp_path: Path) -> None:
        """Preset file with a non-list JSON returns empty list."""
        preset_file = tmp_path / PRESET_FILENAME
        preset_file.write_text('{"not": "a list"}', encoding="utf-8")
        with patch(
            "dartwork_mpl.ui._config._preset_path", return_value=preset_file
        ):
            assert load_presets() == []


# ============================================================================
# Tests: set_base_dir & _serializable
# ============================================================================


class TestConfigInternals:
    """Tests for internal config helpers."""

    def test_set_and_get_base_dir(self, tmp_path: Path) -> None:
        """set_base_dir sets the directory used by path helpers."""
        from dartwork_mpl.ui._config import _get_base_dir, set_base_dir

        try:
            set_base_dir(tmp_path)
            assert _get_base_dir() == tmp_path
        finally:
            # Restore
            import dartwork_mpl.ui._config as cfg

            cfg._base_dir = None

    def test_serializable_scalar_types(self) -> None:
        """Scalar types pass through unchanged."""
        from dartwork_mpl.ui._config import _serializable

        result = _serializable(
            {"i": 42, "f": 3.14, "s": "hello", "b": True, "n": None}
        )
        assert result == {
            "i": 42,
            "f": 3.14,
            "s": "hello",
            "b": True,
            "n": None,
        }

    def test_serializable_list_and_tuple(self) -> None:
        """Lists pass through, tuples are converted to lists."""
        from dartwork_mpl.ui._config import _serializable

        result = _serializable({"lst": [1, 2], "tup": (3, 4)})
        assert result["lst"] == [1, 2]
        assert result["tup"] == [3, 4]

    def test_serializable_unknown_type(self) -> None:
        """Unknown types are str()-ified."""
        from dartwork_mpl.ui._config import _serializable

        result = _serializable({"obj": {"nested": True}})
        assert isinstance(result["obj"], str)
