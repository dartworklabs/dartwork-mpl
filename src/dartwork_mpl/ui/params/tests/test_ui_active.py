"""``list[bool]`` comma text is parsed at the params boundary, never answered 500.

The browser edits list fields as comma-separated text. ``list[int]``,
``list[float]`` and ``list[str]`` text already parse; ``list[bool]`` text
raised ``KeyError`` and the viewer answered HTTP 500. These tests pin that
valid boolean text parses and invalid text gets the same 422
``invalid_request`` body as any other parameter that fails its type.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from fastapi.testclient import TestClient
from matplotlib.figure import Figure
from pydantic import Field

from dartwork_mpl.ui import ParamModel
from dartwork_mpl.ui.params import InvalidRequest, parse_active
from dartwork_mpl.ui.params._descriptors import controls_from_model
from dartwork_mpl.ui.ui import _create_app

INVALID_PARAMS = {
    "detail": "Parameters must use declared names and satisfy their types and constraints.",
    "code": "invalid_request",
}


class FlagParams(ParamModel):
    """A ``list[bool]`` field beside a ``list[int]`` reference field."""

    flags: list[bool] = Field(default=[True, False])
    values: list[int] = Field(default=[1, 2])


def flag_figure(params: FlagParams) -> Figure:
    """Draw one line so a successful render has a real figure."""
    fig, ax = plt.subplots()
    ax.plot(params.values)
    return fig


def _parse(text: str) -> FlagParams | InvalidRequest:
    """Parse ``{"flags": text}`` against ``FlagParams`` with its real controls."""
    result = parse_active(
        {"flags": text}, FlagParams, controls_from_model(FlagParams)
    )
    assert isinstance(result, (FlagParams, InvalidRequest))
    return result


@pytest.mark.parametrize(
    "text, expected",
    [
        ("true,false", [True, False]),
        ("True, False", [True, False]),
        (" TRUE ,false, ", [True, False]),
        ("", []),
    ],
)
def test_boolean_comma_text_parses_into_a_bool_list(
    text: str, expected: list[bool]
) -> None:
    """Case-insensitive ``true``/``false`` items parse; blanks are skipped like other lists."""
    result = _parse(text)

    assert isinstance(result, FlagParams)
    assert result.flags == expected


def test_serialized_default_round_trips() -> None:
    """The descriptor default text (``"True, False"``) parses back to the default."""
    (flags,) = (c for c in controls_from_model(FlagParams) if c.name == "flags")
    default_text = flags.default
    assert default_text == "True, False"

    result = _parse(default_text)

    assert isinstance(result, FlagParams)
    assert result.flags == [True, False]


@pytest.mark.parametrize("text", ["maybe", "true,maybe", "1,0", "yes"])
def test_non_boolean_item_is_a_typed_refusal(text: str) -> None:
    """Any item other than ``true``/``false`` yields ``InvalidRequest``, not an exception."""
    assert _parse(text) == InvalidRequest(INVALID_PARAMS["detail"])


def test_any_text_yields_a_model_or_a_refusal() -> None:
    """Property over seeded random comma text: parsing never raises."""
    rng = random.Random(20261022)
    alphabet = ["true", "false", "TRUE", "x", "", " ", ",", "1", "é", "\x00"]
    for _ in range(500):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8)))
        try:
            _parse(text)
        except Exception as exc:  # pragma: no cover - failure path
            pytest.fail(f"seed 20261022 input {text!r} raised {exc!r}")


@pytest.fixture
def viewer(tmp_path: Path) -> Iterator[TestClient]:
    """A started viewer over ``FlagParams`` that answers server errors as 500."""
    app = _create_app(
        flag_figure,
        FlagParams,
        title="flags",
        script_root=tmp_path / "script",
        copy_to=None,
        host="127.0.0.1",
        restart=lambda: None,
    )
    with TestClient(
        app, base_url="http://127.0.0.1", raise_server_exceptions=False
    ) as client:
        yield client


def test_http_invalid_bool_text_matches_other_invalid_list_text(
    viewer: TestClient,
) -> None:
    """Bad ``list[bool]`` text answers 422 with the exact body bad ``list[int]`` text gets."""
    reference = viewer.post("/api/render", json={"values": "oops"})
    response = viewer.post("/api/render", json={"flags": "true,maybe"})

    assert (reference.status_code, reference.json()) == (422, INVALID_PARAMS)
    assert response.status_code == 422
    assert response.json() == INVALID_PARAMS


def test_http_valid_bool_text_renders(viewer: TestClient) -> None:
    """Valid ``list[bool]`` comma text renders (200), as other list text does."""
    response = viewer.post("/api/render", json={"flags": "true,false"})

    assert response.status_code == 200
