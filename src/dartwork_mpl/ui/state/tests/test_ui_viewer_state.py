"""ViewerState over a real fixed-file store: projected reads, bounded edits, drift and corruption."""

from __future__ import annotations

import json
import random
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, Field

from dartwork_mpl.ui.params import ParamModel
from dartwork_mpl.ui.params._descriptors import descriptors_from_model
from dartwork_mpl.ui.platform.fs import RootScope, open_roots
from dartwork_mpl.ui.platform.json_bounds import LimitExceeded
from dartwork_mpl.ui.state import _viewer_state as config
from dartwork_mpl.ui.state._language import (
    MAX_CONFIG_BYTES,
    MAX_PRESET_BYTES,
    FigWidth,
    FullStateUpdate,
    InvalidStoredState,
    ParamsUpdate,
    PresetRequest,
    Tab,
    parse_params_update,
    parse_preset_request,
)
from dartwork_mpl.ui.state._store import (
    FixedStateStore,
    MissingState,
    StateWritten,
)

# The viewer's fixed state file names (a file-format contract).
CONFIG_FILENAME = ".dartwork_ui_config.json"
PRESET_FILENAME = ".dartwork_ui_presets.json"


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
                state.save_config(ParamsUpdate(_StateParams()), "plot"),
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
                FullStateUpdate(
                    model, (Tab(2, "tab", {"coords": [3.0]}),), FigWidth(80)
                ),
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
    parse = parse_params_update if kind == "config" else parse_preset_request
    parsed = parse(body, AliasedParams, descriptors_from_model(AliasedParams))
    assert isinstance(
        parsed, ParamsUpdate if kind == "config" else PresetRequest
    )
    assert parsed.model.model_dump(mode="json") == {
        "wire_count": 5,
        "wire_child": {"wire_child_count": 7},
    }
    with _state_at(tmp_path, frozenset(AliasedParams.model_fields)) as state:
        if isinstance(parsed, ParamsUpdate):
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
        result = state.save_config(ParamsUpdate(model), "plot")
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
