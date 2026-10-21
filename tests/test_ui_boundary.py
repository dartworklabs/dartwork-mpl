"""Pure viewer boundaries reject ambiguous input before effects or model use."""

import ast
import json
import math
import random
from copy import deepcopy
from pathlib import Path
from typing import Literal

import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from dartwork_mpl.ui import _boundary as boundary
from dartwork_mpl.ui._param import ParamModel
from dartwork_mpl.ui._widget import descriptors_from_model
from dartwork_mpl.ui.platform import json_bounds


class Params(ParamModel):
    """Defaults, constraints, aliases and list text remain supported."""

    model_config = ConfigDict(extra="allow")
    count: int = Field(default=3, ge=1, le=9, alias="wire_count")
    values: list[float] = Field(default_factory=lambda: [1.0])
    mode: Literal["line", "bar"] = "line"


class NumericChoiceParams(ParamModel):
    """Numeric Literal choices arrive from browser selects as strings."""

    model_config = ConfigDict(extra="allow")
    ncols: Literal[1, 2, 3] = 1
    ratio: Literal[0.5, 1.0] = 0.5
    count: int = Field(default=3, ge=1, le=9)
    mode: Literal["line", "bar"] = "line"


def browser_choice(value: float) -> str:
    """Spell a numeric choice as a select option does (JS ``String(1.0) == "1"``)."""
    return str(int(value)) if float(value).is_integer() else repr(value)


class Nested(BaseModel):
    """Nested model extras must close without changing the supplied class."""

    model_config = ConfigDict(extra="allow")
    size: int = Field(default=2, ge=1, alias="wire_size")


class NestedParams(ParamModel):
    """Declared models close recursively while explicit dictionaries stay open."""

    nested: Nested = Field(default_factory=Nested)
    items: list[Nested] = Field(default_factory=list)
    options: dict[str, object] = Field(default_factory=dict)


class OptionalNestedParams(ParamModel):
    """A union cannot bypass the closed language of a selected model branch."""

    nested: None | Nested = None
    other: str | Nested = "default"
    sequence: str | list[Nested] = "default"


class ValidatedParams(ParamModel):
    """A model's own validators remain authoritative after parsing."""

    count: int = 3

    @field_validator("count")
    @classmethod
    def odd_count(cls, value: int) -> int:
        """Reject even counts to expose accidental constraint bypasses."""
        if value % 2 == 0:
            raise ValueError("count must be odd")
        return value


def request(value, route="/api/render", model=Params):
    """Exercise the public pure parser with actual UI descriptors."""
    return boundary.parse_request(
        route, value, model, descriptors_from_model(model)
    )


def test_active_fields_closed_even_when_model_extra_allows():
    """Unknown and alias keys reject while declared names/defaults/list text validate."""
    before = Params.model_config.copy(), Params.model_fields["count"].alias
    for value in [
        {"unknown": 1},
        {"wire_count": 4},
        {"count": 10},
        {"count": 1.5},
        {"values": "nan, 1"},
        {"values": [1e300, math.inf]},
    ]:
        assert isinstance(request(value), boundary.InvalidRequest), value
    result = request({"count": "5", "values": "1, 2.5, ,3"})
    assert isinstance(result, boundary.ModelRequest)
    assert result.model.count == 5
    assert result.model.values == [1.0, 2.5, 3.0]
    assert request({}).model.count == 3
    assert before == (Params.model_config, Params.model_fields["count"].alias)
    assert isinstance(
        request({"count": 2}, model=ValidatedParams), boundary.InvalidRequest
    )


@pytest.mark.parametrize(
    "route, wrap",
    [
        ("/api/render", lambda params: params),
        ("/api/save-state", lambda params: {"params": params}),
        ("/api/preset", lambda params: {"label": "p", "params": params}),
    ],
)
def test_numeric_choice_strings_convert_once_to_declared_members(route, wrap):
    """Select strings ("2", float "1") become typed members on every model route."""
    before = NumericChoiceParams.model_config.copy()
    result = request(
        wrap({"ncols": "2", "ratio": "1", "mode": "bar"}),
        route=route,
        model=NumericChoiceParams,
    )
    assert isinstance(
        result,
        (boundary.ModelRequest, boundary.StateRequest, boundary.PresetRequest),
    ), result
    assert (result.model.ncols, type(result.model.ncols)) == (2, int)
    assert (result.model.ratio, type(result.model.ratio)) == (1.0, float)
    assert result.model.mode == "bar"
    native = request(
        wrap({"ncols": 3, "ratio": 0.5}), route=route, model=NumericChoiceParams
    )
    assert (native.model.ncols, native.model.ratio) == (3, 0.5)
    assert NumericChoiceParams.model_config == before


@pytest.mark.parametrize(
    "value",
    [
        {"ncols": "4"},
        {"ncols": "2.0"},
        {"ncols": "2.7"},
        {"ncols": " "},
        {"ncols": "nan"},
        {"ratio": "2"},
        {"ratio": "nan"},
        {"ratio": "inf"},
        {"ratio": "-Infinity"},
        {"ratio": "1e400"},
        {"count": "10"},
        {"mode": "2"},
        {"unknown": "2"},
    ],
)
def test_numeric_choice_conversion_keeps_membership_bounds_and_names(value):
    """Conversion never truncates, admits nonmembers or nonfinite values, or opens names."""
    assert isinstance(
        request(value, model=NumericChoiceParams), boundary.InvalidRequest
    ), value


def test_numeric_choice_conversion_runs_the_caller_validator_once():
    """A converted choice still reaches the caller's own hooks exactly once."""
    calls = []

    class HookChoices(ParamModel):
        """Record field and model validation for a numeric Literal choice."""

        ncols: Literal[1, 2, 3] = 1

        @field_validator("ncols")
        @classmethod
        def ncols_hook(cls, value):
            """Record the typed value that native validation hands to the caller."""
            calls.append(("field", value, type(value)))
            return value

        @model_validator(mode="after")
        def model_hook(self):
            """Record one completed model validation."""
            calls.append(("model",))
            return self

    result = request({"ncols": "3"}, model=HookChoices)
    assert isinstance(result, boundary.ModelRequest)
    assert calls == [("field", 3, int), ("model",)]


def test_numeric_choice_browser_spelling_round_trips_and_noise_never_crashes():
    """Every declared choice survives its select spelling; arbitrary text parses or refuses."""
    for ncols in (1, 2, 3):
        for ratio in (0.5, 1.0):
            parsed = request(
                {
                    "ncols": browser_choice(ncols),
                    "ratio": browser_choice(ratio),
                },
                model=NumericChoiceParams,
            )
            assert isinstance(parsed, boundary.ModelRequest)
            assert (parsed.model.ncols, parsed.model.ratio) == (ncols, ratio)
    rng = random.Random(4991)
    alphabet = "0123456789.-+eE_ inNaf"
    for _ in range(500):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(1, 8)))
        for field in ("ncols", "ratio"):
            parsed = request({field: text}, model=NumericChoiceParams)
            assert isinstance(
                parsed, (boundary.ModelRequest, boundary.InvalidRequest)
            ), (field, text)
            if isinstance(parsed, boundary.ModelRequest):
                chosen = getattr(parsed.model, field)
                assert chosen in ((1, 2, 3) if field == "ncols" else (0.5, 1.0))
                assert math.isfinite(chosen)


def test_old_numeric_choice_strings_in_stored_presets_remain_usable():
    """Raw historical select strings survive storage projection and parse as choices."""
    raw = json.dumps(
        [{"label": "old", "params": {"ncols": "2", "ratio": "1"}}]
    ).encode()
    stored = boundary.parse_stored("presets", raw)
    assert isinstance(stored, boundary.StoredPresets)
    (entry,) = boundary.project_stored(
        stored, frozenset(NumericChoiceParams.model_fields)
    )
    assert entry["params"] == {"ncols": "2", "ratio": "1"}
    parsed = request(entry["params"], model=NumericChoiceParams)
    assert isinstance(parsed, boundary.ModelRequest)
    assert (parsed.model.ncols, parsed.model.ratio) == (2, 1.0)


def test_nested_models_close_without_closing_explicit_dicts():
    """Nested extras and aliases reject; explicitly open dictionaries keep content."""
    for value in [
        {"nested": {"extra": 1}},
        {"nested": {"wire_size": 1}},
        {"items": [{"size": 2, "extra": True}]},
    ]:
        assert isinstance(
            request(value, model=NestedParams), boundary.InvalidRequest
        )
    result = request(
        {
            "nested": {"size": 4},
            "items": [{"size": 3}],
            "options": {"arbitrary": {"more": 1}},
        },
        model=NestedParams,
    )
    assert isinstance(result, boundary.ModelRequest)
    assert result.model.nested.size == 4
    assert result.model.items[0].size == 3
    assert result.model.options == {"arbitrary": {"more": 1}}
    assert Nested.model_config["extra"] == "allow"
    assert Nested.model_fields["size"].alias == "wire_size"


def test_union_branches_do_not_bypass_nested_model_closure():
    """Null/string alternatives cannot smuggle nested model extra or alias keys."""
    for value in [
        {"nested": {"extra": 1}},
        {"nested": {"wire_size": 4}},
        {"other": {"extra": 1}},
        {"sequence": [{"extra": 1}]},
    ]:
        assert isinstance(
            request(value, model=OptionalNestedParams), boundary.InvalidRequest
        )
    result = request(
        {"nested": {"size": 4}, "other": "still a string"},
        model=OptionalNestedParams,
    )
    assert isinstance(result, boundary.ModelRequest)
    assert result.model.nested.size == 4
    assert result.model.other == "still a string"


def test_default_factory_and_model_validators_keep_their_behavior():
    """Alias-free parsing inherits hooks and defaults without repeated validation."""
    calls = []

    def default_count():
        """Observe actual per-request default construction."""
        calls.append("default")
        return 3

    class HookParams(ParamModel):
        """A caller can attach defaults and validators to an aliased field."""

        count: int = Field(default_factory=default_count, alias="wire_count")

        @field_validator("count")
        @classmethod
        def count_hook(cls, value):
            """Record one validation of an explicitly supplied value."""
            calls.append("field")
            return value + 1

        @model_validator(mode="after")
        def model_hook(self):
            """Record one completed model validation."""
            calls.append("model")
            return self

    result = request({}, model=HookParams)
    assert isinstance(result, boundary.ModelRequest)
    assert isinstance(result.model, HookParams)
    assert result.model.count == 3
    assert calls == ["default", "model"]
    calls.clear()
    result = request({"count": 4}, model=HookParams)
    assert result.model.count == 5
    assert calls == ["field", "model"]
    assert HookParams.model_fields["count"].alias == "wire_count"


@pytest.mark.parametrize("kind", ["direct", "list", "optional", "union"])
def test_nested_validation_matches_one_native_pass(kind):
    """Nested before/after hooks and union selection match native Pydantic once."""
    calls = []

    class TextChild(BaseModel):
        """The first union arm must lose when its value type does not match."""

        x: str

    class Child(BaseModel):
        """A visible after-hook change detects even one duplicate validation."""

        x: int

        @model_validator(mode="before")
        @classmethod
        def before_hook(cls, value):
            """Record the raw nested validation pass."""
            calls.append("child-before")
            return value

        @model_validator(mode="after")
        def after_hook(self):
            """Increment once so duplicate validation changes observable output."""
            calls.append("child-after")
            self.x += 1
            return self

    annotations = {
        "direct": Child,
        "list": list[Child],
        "optional": None | Child,
        "union": TextChild | Child,
    }

    class NestedHooks(ParamModel):
        """An outer model retains its normal before/after execution order."""

        child: annotations[kind]

        @model_validator(mode="before")
        @classmethod
        def before_hook(cls, value):
            """Record the raw outer validation pass."""
            calls.append("outer-before")
            return value

        @model_validator(mode="after")
        def after_hook(self):
            """Record completion after the nested model validates."""
            calls.append("outer-after")
            return self

    raw = {"child": [{"x": 1}, {"x": 2}] if kind == "list" else {"x": 1}}
    expected = NestedHooks.model_validate(deepcopy(raw)).model_dump()
    native_calls = calls.copy()
    calls.clear()
    parsed = boundary.parse_request(
        "/api/render", deepcopy(raw), NestedHooks, []
    )
    assert isinstance(parsed, boundary.ModelRequest)
    assert parsed.model.model_dump() == expected
    assert calls == native_calls
    assert calls.count("child-after") == (2 if kind == "list" else 1)


def test_tab_values_are_structural_and_ids_unique():
    """Inactive tabs accept obsolete values, but never unknown keys or duplicate ids."""
    value = {
        "params": {"count": 3},
        "tabs": [{"id": 1, "name": "Old", "params": {"count": "obsolete"}}],
        "figWidth": 70,
    }
    result = request(value, "/api/save-state")
    assert isinstance(result, boundary.StateRequest)
    assert result.tabs[0].params == {"count": "obsolete"}
    for edit in [
        {"tabs": value["tabs"] * 2},
        {"tabs": [{"id": True, "name": "x", "params": {}}]},
        {"tabs": [{"id": 1, "name": "x", "params": {"gone": 1}}]},
        {"figWidth": 29},
        {"figWidth": 101},
        {"figWidth": True},
        {"params": {"count": 100}},
        {"extra": 1},
    ]:
        assert isinstance(
            request({**value, **edit}, "/api/save-state"),
            boundary.InvalidRequest,
        ), edit
    for count in [64, 65]:
        body = {
            "tabs": [{"id": i, "name": "x", "params": {}} for i in range(count)]
        }
        assert isinstance(
            request(body, "/api/save-state"),
            boundary.StateRequest if count == 64 else json_bounds.LimitExceeded,
        )


def test_complete_endpoint_shapes_and_label_limits():
    """Endpoint schemas consume every field and preserve defaults only where allowed."""
    assert isinstance(request({}, "/api/config"), boundary.StateRequest)
    assert isinstance(
        request({"params": {}}, "/api/save-server/script"), boundary.SaveRequest
    )
    assert isinstance(
        request({"label": "é" * 128, "params": {}}, "/api/preset"),
        boundary.PresetRequest,
    )
    assert isinstance(
        request({"label": "é" * 129, "params": {}}, "/api/preset"),
        json_bounds.LimitExceeded,
    )
    for route, value in [
        ("/api/preset", {"label": "x"}),
        ("/api/preset", {"label": 1, "params": {}}),
        ("/api/preset", {"label": "x", "params": {}, "timestamp": "untrusted"}),
        ("/api/save-server/script", {"params": {}, "filename": 1}),
        ("/api/save-server/script", {"params": {}, "other": True}),
        ("/api/render", []),
        ("/unknown", {}),
    ]:
        assert isinstance(request(value, route), boundary.InvalidRequest), (
            route,
            value,
        )


@pytest.mark.parametrize(
    "filename",
    [
        "",
        " ",
        "/absolute",
        "../outside",
        "sub/../outside",
        "./x",
        "sub//x",
        "sub/",
        "x\x00y",
        "sub\\file",
        "C:drive",
        "//host/file",
        "é" * 129,
    ],
)
def test_output_paths_reject_unsafe_components(filename):
    """The portable path grammar refuses traversal and ambiguous separators."""
    assert isinstance(boundary.parse_output(filename), boundary.InvalidOutput)


def test_output_exact_size_and_constructor_invariant():
    """Safe subpaths retain names and cannot be forged with illegal components."""
    name = "/".join(["a" * 255] * 4)
    assert len(name.encode()) == 1023
    result = boundary.parse_output(name + "b")
    assert isinstance(result, boundary.InvalidOutput)  # component bound
    exact = "/".join(["a" * 255] * 3 + ["a" * 254, "x"])
    assert len(exact.encode()) == 1024
    parsed = boundary.parse_output(exact)
    assert isinstance(parsed, boundary.RelativeOutput)
    assert parsed.filename == exact
    assert isinstance(
        boundary.parse_output(exact + "x"), boundary.InvalidOutput
    )
    assert boundary.parse_output("sub dir/figure.svg").parts == (
        "sub dir",
        "figure.svg",
    )
    with pytest.raises(ValueError):
        boundary.RelativeOutput(("..", "outside"))


def test_stored_model_drift_projects_without_mutating_raw_values():
    """Renamed fields project on reads; obsolete retained values are not corruption."""
    value = {
        "function": "old_function",
        "params": {"count": "obsolete", "removed": [1, 2]},
        "updated_at": "yesterday",
        "tabs": [
            {
                "id": 3,
                "name": "Old",
                "params": {"count": 900, "removed": {"x": 1}},
            }
        ],
        "figWidth": 999,
    }
    state = boundary.parse_stored("config", json.dumps(value).encode())
    assert isinstance(state, boundary.StoredConfig)
    projected = boundary.project_stored(state, frozenset({"count"}))
    assert projected["params"] == {"count": "obsolete"}
    assert projected["dropped_fields"] == ["removed"]
    assert projected["tabs"][0]["params"] == {"count": 900}
    assert projected["figWidth"] == 70
    assert state.value == value
    presets = [
        {"label": "Old", "params": value["params"], "timestamp": "<img>"}
    ]
    state = boundary.parse_stored("presets", json.dumps(presets).encode())
    assert isinstance(state, boundary.StoredPresets)
    assert boundary.project_stored(state, frozenset({"count"}))[0][
        "dropped_fields"
    ] == ["removed"]
    assert state.value == presets


@pytest.mark.parametrize(
    "kind, value",
    [
        ("config", []),
        ("config", {}),
        ("config", {"params": []}),
        ("config", {"params": {}, "extra": 1}),
        ("config", {"params": {}, "figWidth": True}),
        (
            "config",
            {
                "params": {},
                "tabs": [
                    {"id": 1, "name": "x", "params": {}},
                    {"id": 1, "name": "x", "params": {}},
                ],
            },
        ),
        ("presets", {}),
        ("presets", [1]),
        ("presets", [{"label": "x", "params": {}, "extra": 1}]),
        ("presets", [{"label": "x", "params": {}, "timestamp": []}]),
    ],
)
def test_stored_structural_corruption_is_distinct_from_model_drift(kind, value):
    """Malformed persisted containers and metadata never become empty defaults."""
    assert isinstance(
        boundary.parse_stored(kind, json.dumps(value).encode()),
        boundary.InvalidStoredState,
    )


def test_stored_limits_and_outgoing_serialization_are_bounded():
    """Stored counts and encoded next-state bytes are checked before replacement."""
    entry = {"label": "x", "params": {}}
    assert isinstance(
        boundary.parse_stored("presets", json.dumps([entry] * 1000).encode()),
        boundary.StoredPresets,
    )
    assert isinstance(
        boundary.parse_stored("presets", json.dumps([entry] * 1001).encode()),
        boundary.InvalidStoredState,
    )
    assert isinstance(
        boundary.parse_stored("config", b" " * (1024 * 1024 + 1)),
        boundary.InvalidStoredState,
    )
    expected = b'{\n  "params": {}\n}\n'
    result = boundary.encode_state({"params": {}}, max_bytes=len(expected))
    assert result == expected
    assert isinstance(result, bytes)
    assert isinstance(
        boundary.encode_state({"params": {}}, max_bytes=len(result) - 1),
        json_bounds.LimitExceeded,
    )
    assert isinstance(
        boundary.encode_state({"params": {"x": math.nan}}, max_bytes=100),
        json_bounds.MalformedInput,
    )
    assert isinstance(
        boundary.encode_state({"params": {"x": 10**640}}, max_bytes=1024),
        json_bounds.LimitExceeded,
    )


def test_seeded_inputs_always_parse_or_return_named_refusal():
    """Arbitrary bytes and paths never crash and accepted paths cannot escape."""
    rng = random.Random(499)
    for _ in range(500):
        raw = rng.randbytes(rng.randrange(150))
        result = json_bounds.decode_json(raw, max_bytes=128)
        assert isinstance(
            result,
            (
                str,
                int,
                float,
                bool,
                list,
                dict,
                type(None),
                boundary.InputFailure,
            ),
        ), raw
        name = "".join(
            chr(rng.randrange(0x110000)) for _ in range(rng.randrange(30))
        )
        result = boundary.parse_output(name)
        assert isinstance(
            result, (boundary.RelativeOutput, boundary.InputFailure)
        ), repr(name)
        if isinstance(result, boundary.RelativeOutput):
            assert not Path(result.filename).is_absolute()
            assert ".." not in Path(result.filename).parts
            assert "\\" not in result.filename
    for _ in range(200):
        value = {
            "count": rng.randrange(1, 10),
            "values": [rng.random() for _ in range(rng.randrange(10))],
        }
        raw = json.dumps(value).encode()
        assert json_bounds.decode_json(raw, max_bytes=1024) == value
        parsed = request(value)
        assert isinstance(parsed, boundary.ModelRequest)
        assert parsed.model.count == value["count"]
        assert parsed.model.values == value["values"]


def route_inventory(source):
    """Read actual app decorators plus framework-owned read registrations."""
    routes = {
        (method, path)
        for path in [
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc",
        ]
        for method in ["GET", "HEAD"]
    }
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "app"
            and node.func.attr
            in {"get", "post", "put", "patch", "delete", "head", "options"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            routes.add((node.func.attr.upper(), node.args[0].value))
    return routes


def constructor_violations(source, module):
    """Report direct RelativeOutput forging outside its boundary owner."""
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and (
            (
                isinstance(node.func, ast.Name)
                and node.func.id == "RelativeOutput"
            )
            or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "RelativeOutput"
            )
        )
        and module != "_boundary"
    ]


def test_route_inventory_and_handle_owner_guards_reject_injected_bypasses():
    """Every registration needs policy and only the parser owns path construction."""
    root = Path(__file__).resolve().parents[1] / "src/dartwork_mpl/ui"
    actual = route_inventory((root / "ui.py").read_text())
    assert actual <= boundary.ROUTE_POLICY.keys()
    reduced = dict(boundary.ROUTE_POLICY)
    reduced.pop(("POST", "/api/render"))
    assert not actual <= reduced.keys()
    assert (
        not route_inventory('@app.post("/unclassified")\ndef extra(): pass')
        <= boundary.ROUTE_POLICY.keys()
    )
    for path in root.glob("*.py"):
        assert not constructor_violations(path.read_text(), path.stem), path
    assert constructor_violations('RelativeOutput(("safe",))', "ui")
    assert not constructor_violations('RelativeOutput(("safe",))', "_boundary")
