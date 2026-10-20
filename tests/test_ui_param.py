"""Unit tests for dartwork_mpl.ui parameter introspection and config.

These tests cover the pure-Python logic of descriptor extraction
and config persistence — no server required.
"""

from __future__ import annotations

import json
import random
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from unittest.mock import patch

import pytest
from pydantic import BaseModel, ConfigDict, Field

from dartwork_mpl.ui import _config as config
from dartwork_mpl.ui._boundary import (
    MAX_CONFIG_BYTES,
    MAX_PRESET_BYTES,
    InvalidStoredState,
    LimitExceeded,
    PresetRequest,
    StateRequest,
    Tab,
    parse_request,
)
from dartwork_mpl.ui._config import (
    CONFIG_FILENAME,
    PRESET_FILENAME,
    delete_preset,
    load_config,
    load_presets,
    save_config,
    save_preset,
)
from dartwork_mpl.ui._files import (
    FixedStateStore,
    MissingState,
    RootScope,
    StateWritten,
    open_roots,
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


class _StateParams(ParamModel):
    """A current model whose old stored values may exceed current constraints."""

    opacity: float = Field(default=0.5, ge=0, le=1)


@contextmanager
def _state_at(
    tmp_path: Path, fields: frozenset[str] = frozenset({"opacity"})
) -> Iterator[config.ViewerState]:
    """Exercise the real confined store and close its borrowed root after each test."""
    roots = open_roots(tmp_path, None, cwd=tmp_path)
    assert isinstance(roots, RootScope)
    try:
        assert hasattr(config, "ViewerState"), (
            "The approved state persistence contract is absent"
        )
        yield config.ViewerState(FixedStateStore(roots), fields)
    finally:
        roots.close()


def test_drift_projects_reads_without_rewriting(tmp_path: Path) -> None:
    """Old keys disappear only from responses, and retained invalid values remain visible."""
    path = tmp_path / CONFIG_FILENAME
    raw = json.dumps(
        {
            "params": {"alpha": 0.2, "opacity": 0.5},
            "tabs": [
                {
                    "id": 1,
                    "name": "old",
                    "params": {"alpha": 4, "opacity": "obsolete"},
                }
            ],
            "figWidth": 900,
        }
    ).encode()
    path.write_bytes(raw)
    with _state_at(tmp_path) as state:
        result = state.load_config()
        assert isinstance(result, config.ConfigLoaded)
        assert result.value["params"] == {"opacity": 0.5}
        assert result.value["dropped_fields"] == ["alpha"]
        assert result.value["tabs"] == [
            {
                "id": 1,
                "name": "old",
                "params": {"opacity": "obsolete"},
                "dropped_fields": ["alpha"],
            }
        ]
        assert result.value["figWidth"] == 70
    assert path.read_bytes() == raw


def test_other_preset_entries_survive_append_delete(tmp_path: Path) -> None:
    """Seeded historical JSON values and metadata survive unrelated preset edits exactly."""
    rng = random.Random(499)
    historical = [
        {
            "label": f"old {index}",
            "params": {
                "alpha": [rng.random(), {"nested": None}],
                "opacity": "obsolete",
            },
            "timestamp": f"timestamp-{index}",
        }
        for index in range(30)
    ]
    path = tmp_path / PRESET_FILENAME
    path.write_text(json.dumps(historical))
    with _state_at(tmp_path) as state:
        assert isinstance(
            state.save_preset(PresetRequest("current", _StateParams())),
            StateWritten,
        )
        assert json.loads(path.read_bytes())[:-1] == historical
        assert isinstance(state.delete_preset(len(historical)), StateWritten)
    assert json.loads(path.read_bytes()) == historical


def test_preset_reads_project_without_rewriting(tmp_path: Path) -> None:
    """Preset reads report removed keys and retain obsolete values without rewriting bytes."""
    path = tmp_path / PRESET_FILENAME
    raw = b'[{"label":"old","params":{"alpha":0.2,"opacity":"obsolete"},"timestamp":"unchanged"}]'
    path.write_bytes(raw)
    with _state_at(tmp_path) as state:
        result = state.load_presets()
        assert isinstance(result, config.PresetsLoaded)
        assert result.value == [
            {
                "label": "old",
                "params": {"opacity": "obsolete"},
                "timestamp": "unchanged",
                "dropped_fields": ["alpha"],
            }
        ]
    assert path.read_bytes() == raw


def test_shared_directory_models_do_not_corrupt_state(tmp_path: Path) -> None:
    """Two function models independently project one shared file without migration."""
    path = tmp_path / CONFIG_FILENAME
    raw = b'{"function":"first", "params":{"alpha":0.2,"opacity":0.5}}'
    path.write_bytes(raw)
    with (
        _state_at(tmp_path) as first,
        _state_at(tmp_path, frozenset({"alpha"})) as second,
    ):
        a, b = first.load_config(), second.load_config()
        assert isinstance(a, config.ConfigLoaded)
        assert isinstance(b, config.ConfigLoaded)
        assert a.value["params"] == {"opacity": 0.5}
        assert b.value["params"] == {"alpha": 0.2}
        assert b.value["dropped_fields"] == ["opacity"]
    assert path.read_bytes() == raw


@pytest.mark.parametrize(
    "kind,raw",
    [
        ("config", b"\xff"),
        ("config", b"{"),
        ("config", b"[]"),
        (
            "config",
            b'{"params":{},"tabs":[{"id":true,"name":"bad","params":{}}]}',
        ),
        ("config", b" " * (MAX_CONFIG_BYTES + 1)),
        ("presets", b"\xff"),
        ("presets", b"null"),
        ("presets", b'[{"label":"old","params":[]}]'),
        ("presets", b" " * (MAX_PRESET_BYTES + 1)),
    ],
    ids=[
        "config-utf8",
        "config-json",
        "config-shape",
        "config-tabs",
        "config-size",
        "presets-utf8",
        "presets-shape",
        "presets-entry",
        "presets-size",
    ],
)
def test_structural_corruption_blocks_update_delete(
    tmp_path: Path, kind: str, raw: bytes
) -> None:
    """Malformed, non-UTF8, wrong-shape and oversized state is never silently replaced."""
    path = tmp_path / (CONFIG_FILENAME if kind == "config" else PRESET_FILENAME)
    path.write_bytes(raw)
    with _state_at(tmp_path) as state:
        results = (
            [
                state.load_config(),
                state.save_config(StateRequest(_StateParams()), "plot"),
            ]
            if kind == "config"
            else [
                state.load_presets(),
                state.save_preset(PresetRequest("new", _StateParams())),
                state.delete_preset(0),
            ]
        )
        assert all(isinstance(result, InvalidStoredState) for result in results)
        assert all(result.status_code == 409 for result in results)
    assert path.read_bytes() == raw


def test_missing_state_keeps_defaults_and_named_preset_misses(
    tmp_path: Path,
) -> None:
    """Absent state stays absent on reads and out-of-range deletes are named misses."""
    with _state_at(tmp_path) as state:
        assert isinstance(state.load_config(), MissingState)
        presets = state.load_presets()
        assert isinstance(presets, config.PresetsLoaded)
        assert presets.value == []
        assert state.delete_preset(0) == config.PresetNotFound(0)
        assert state.delete_preset(-1) == config.PresetNotFound(-1)
    assert list(tmp_path.iterdir()) == []


def test_config_serializes_supported_model_types_and_optional_fields(
    tmp_path: Path,
) -> None:
    """Model JSON serialization preserves tuples, booleans and explicit state options."""

    class Supported(ParamModel):
        """Representative supported Pydantic parameter values."""

        coords: tuple[float, ...] = (1.0, 2.0)
        enabled: bool = True

    model = Supported()
    with _state_at(tmp_path, frozenset(Supported.model_fields)) as state:
        assert isinstance(
            state.save_config(
                StateRequest(model, (Tab(2, "tab", {"coords": [3.0]}),), 80),
                "plot",
            ),
            StateWritten,
        )
    value = json.loads((tmp_path / CONFIG_FILENAME).read_bytes())
    assert value["params"] == {"coords": [1.0, 2.0], "enabled": True}
    assert value["tabs"] == [
        {"id": 2, "name": "tab", "params": {"coords": [3.0]}}
    ]
    assert value["figWidth"] == 80
    assert value["function"] == "plot"
    assert value["updated_at"].endswith("+00:00")


@pytest.mark.parametrize("kind", ["config", "presets"])
def test_alias_serialization_round_trips_declared_state_names(
    tmp_path: Path, kind: str
) -> None:
    """Successful config/preset saves retain declared values despite native alias dumps."""

    class AliasedChild(BaseModel):
        """Nested native serialization aliases must stay out of stored params."""

        model_config = ConfigDict(serialize_by_alias=True)
        count: int = Field(default=2, alias="wire_child_count")

    class AliasedParams(ParamModel):
        """Caller serialization settings remain available inside trusted callbacks."""

        model_config = ConfigDict(serialize_by_alias=True)
        count: int = Field(default=3, alias="wire_count")
        child: AliasedChild = Field(alias="wire_child")

    expected = {"count": 5, "child": {"count": 7}}
    original_config = AliasedParams.model_config.copy()
    child_config = AliasedChild.model_config.copy()
    body = (
        expected if kind == "config" else {"label": "alias", "params": expected}
    )
    parsed = parse_request(
        "/api/config" if kind == "config" else "/api/preset",
        body,
        AliasedParams,
        descriptors_from_model(AliasedParams),
    )
    assert isinstance(
        parsed, StateRequest if kind == "config" else PresetRequest
    )
    assert parsed.model.model_dump(mode="json") == {
        "wire_count": 5,
        "wire_child": {"wire_child_count": 7},
    }
    with _state_at(tmp_path, frozenset(AliasedParams.model_fields)) as state:
        if isinstance(parsed, StateRequest):
            assert isinstance(state.save_config(parsed, "plot"), StateWritten)
            loaded = state.load_config()
            assert isinstance(loaded, config.ConfigLoaded)
            entry = loaded.value
            filename = CONFIG_FILENAME
        else:
            assert isinstance(state.save_preset(parsed), StateWritten)
            loaded_presets = state.load_presets()
            assert isinstance(loaded_presets, config.PresetsLoaded)
            entry = loaded_presets.value[0]
            filename = PRESET_FILENAME
        assert entry["params"] == expected
        assert entry["dropped_fields"] == []
    stored = json.loads((tmp_path / filename).read_bytes())
    assert (stored if kind == "config" else stored[0])["params"] == expected
    assert AliasedParams.model_config == original_config
    assert AliasedChild.model_config == child_config
    assert AliasedParams.model_fields["count"].alias == "wire_count"
    assert AliasedChild.model_fields["count"].alias == "wire_child_count"


def test_serialized_config_overflow_preserves_previous_bytes(
    tmp_path: Path,
) -> None:
    """Pretty JSON can exceed the file bound even when the proposed tree is bounded."""

    class Large(ParamModel):
        """Twenty-four individually legal strings exceed the serialized config cap."""

        values: list[str]

    path = tmp_path / CONFIG_FILENAME
    raw = b'{"params":{}}'
    path.write_bytes(raw)
    model = Large(values=["x" * 50000] * 24)
    with _state_at(tmp_path, frozenset({"values"})) as state:
        result = state.save_config(StateRequest(model), "plot")
        assert isinstance(result, LimitExceeded)
        assert result.status_code == 413
    assert path.read_bytes() == raw


def test_one_thousand_presets_is_exact_append_boundary(tmp_path: Path) -> None:
    """The thousandth preset succeeds and the next proposed edit preserves old bytes."""
    path = tmp_path / PRESET_FILENAME
    path.write_text(
        json.dumps(
            [{"label": str(index), "params": {}} for index in range(999)]
        )
    )
    with _state_at(tmp_path) as state:
        assert isinstance(
            state.save_preset(PresetRequest("last", _StateParams())),
            StateWritten,
        )
        raw = path.read_bytes()
        result = state.save_preset(PresetRequest("overflow", _StateParams()))
        assert isinstance(result, LimitExceeded)
        assert result.status_code == 413
        assert path.read_bytes() == raw
        assert isinstance(state.delete_preset(999), StateWritten)
        raw = path.read_bytes()
        assert state.delete_preset(999) == config.PresetNotFound(999)
        assert path.read_bytes() == raw
