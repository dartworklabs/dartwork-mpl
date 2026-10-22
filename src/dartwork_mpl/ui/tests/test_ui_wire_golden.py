"""Wire golden for the viewer: every HTTP route's status and body, and the two state files' bytes.

The viewer's HTTP language is a frozen interface (ADR 0005 §1): route paths,
status codes, refusal ``detail``/``code`` strings, success keys, the
``/api/descriptors`` payload and the bytes of ``.dartwork_ui_config.json`` and
``.dartwork_ui_presets.json``. This module observes them only through HTTP
and the files on disk, so it stays valid while the code behind the routes
moves. Timestamps and absolute temporary paths are the only values
normalized; everything else is compared exactly.

A failure here means the wire changed. Fix the code, not the expectations.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

import matplotlib.pyplot as plt
import pytest
from fastapi.testclient import TestClient
from matplotlib.figure import Figure
from pydantic import Field

from dartwork_mpl.ui import ParamModel
from dartwork_mpl.ui.ui import FilesystemCapabilities, _create_app


class GoldenParams(ParamModel):
    """One field of every control kind the descriptor language knows."""

    count: int = Field(default=5, ge=1, le=10, description="Point count")
    opacity: float = Field(
        default=0.5, ge=0.0, le=1.0, json_schema_extra={"step": 0.1}
    )
    line_color: str = "#336699"
    title: str = Field(default="Demo", json_schema_extra={"group": "Text"})
    grid: bool = True
    mode: Literal["a", "b"] = "a"
    ncols: Literal[1, 2, 3] = 1
    values: list[int] = Field(default=[1, 2, 3])
    widths: tuple[float, ...] = (0.5, 1.0)
    fail: bool = False


def golden_figure(params: GoldenParams) -> Figure:
    """Draw a tiny figure; ``fail`` raises to exercise the callback refusal."""
    if params.fail:
        raise RuntimeError("callback failure")
    fig, ax = plt.subplots()
    ax.plot(params.values)
    return fig


ORIGIN = "http://127.0.0.1"
TIMESTAMP = re.compile(
    rb'"(updated_at|timestamp)": "\d{4}-\d\d-\d\dT[0-9:.]+\+00:00"'
)


def normalized(raw: bytes) -> str:
    """State bytes with only the write timestamps replaced."""
    return TIMESTAMP.sub(rb'"\1": "<time>"', raw).decode("utf-8")


@pytest.fixture
def viewer(tmp_path: Path) -> Iterator[TestClient]:
    """A started app (lifespan run) with a script root and one copy root."""
    restarts: list[str] = []
    app = _create_app(
        golden_figure,
        GoldenParams,
        title="Golden <viewer>",
        script_root=tmp_path / "script",
        copy_to=tmp_path / "copy",
        host="127.0.0.1",
        restart=lambda: restarts.append("restart"),
    )
    with TestClient(app, base_url=ORIGIN) as client:
        client.restarts = restarts  # type: ignore[attr-defined]
        yield client


def call(
    client: TestClient, method: str, path: str, body: Any = None, **kwargs: Any
) -> tuple[int, Any]:
    """Status and JSON body (or None for a non-JSON body) of one request."""
    if body is not None:
        kwargs["json"] = body
    response = client.request(method, path, **kwargs)
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.status_code, response.json()
    return response.status_code, None


DESCRIPTORS = [
    {
        "name": "count",
        "label": "Point count",
        "type_name": "int",
        "default": 5,
        "min_value": 1,
        "max_value": 10,
        "step": None,
        "group": None,
        "choices": None,
        "widget_hint": None,
        "extra": {},
    },
    {
        "name": "opacity",
        "label": "Opacity",
        "type_name": "float",
        "default": 0.5,
        "min_value": 0.0,
        "max_value": 1.0,
        "step": 0.1,
        "group": None,
        "choices": None,
        "widget_hint": None,
        "extra": {"step": 0.1},
    },
    {
        "name": "line_color",
        "label": "Line Color",
        "type_name": "str",
        "default": "#336699",
        "min_value": None,
        "max_value": None,
        "step": None,
        "group": None,
        "choices": None,
        "widget_hint": "color",
        "extra": {},
    },
    {
        "name": "title",
        "label": "Title",
        "type_name": "str",
        "default": "Demo",
        "min_value": None,
        "max_value": None,
        "step": None,
        "group": "Text",
        "choices": None,
        "widget_hint": None,
        "extra": {"group": "Text"},
    },
    {
        "name": "grid",
        "label": "Grid",
        "type_name": "bool",
        "default": True,
        "min_value": None,
        "max_value": None,
        "step": None,
        "group": None,
        "choices": None,
        "widget_hint": None,
        "extra": {},
    },
    {
        "name": "mode",
        "label": "Mode",
        "type_name": "str",
        "default": "a",
        "min_value": None,
        "max_value": None,
        "step": None,
        "group": None,
        "choices": ["a", "b"],
        "widget_hint": None,
        "extra": {},
    },
    {
        "name": "ncols",
        "label": "Ncols",
        "type_name": "int",
        "default": 1,
        "min_value": None,
        "max_value": None,
        "step": None,
        "group": None,
        "choices": [1, 2, 3],
        "widget_hint": None,
        "extra": {},
    },
    {
        "name": "values",
        "label": "Values",
        "type_name": "list_int",
        "default": "1, 2, 3",
        "min_value": None,
        "max_value": None,
        "step": None,
        "group": None,
        "choices": None,
        "widget_hint": None,
        "extra": {},
    },
    {
        "name": "widths",
        "label": "Widths",
        "type_name": "list_float",
        "default": "0.5, 1.0",
        "min_value": None,
        "max_value": None,
        "step": None,
        "group": None,
        "choices": None,
        "widget_hint": None,
        "extra": {},
    },
    {
        "name": "fail",
        "label": "Fail",
        "type_name": "bool",
        "default": False,
        "min_value": None,
        "max_value": None,
        "step": None,
        "group": None,
        "choices": None,
        "widget_hint": None,
        "extra": {},
    },
]

DEFAULTS = {d["name"]: d["default"] for d in DESCRIPTORS}
ACTIVE = {"count": 3, "values": "4, 5", "ncols": "2", "widths": [2.0]}
DUMPED = {
    "count": 3,
    "opacity": 0.5,
    "line_color": "#336699",
    "title": "Demo",
    "grid": True,
    "mode": "a",
    "ncols": 2,
    "values": [4, 5],
    "widths": [2.0],
    "fail": False,
}

CONFIG_BYTES = (
    "{\n"
    '  "function": "golden_figure",\n'
    '  "params": {\n'
    '    "count": 3,\n'
    '    "opacity": 0.5,\n'
    '    "line_color": "#336699",\n'
    '    "title": "Demo",\n'
    '    "grid": true,\n'
    '    "mode": "a",\n'
    '    "ncols": 2,\n'
    '    "values": [\n'
    "      4,\n"
    "      5\n"
    "    ],\n"
    '    "widths": [\n'
    "      2.0\n"
    "    ],\n"
    '    "fail": false\n'
    "  },\n"
    '  "updated_at": "<time>",\n'
    '  "tabs": [\n'
    "    {\n"
    '      "id": 1,\n'
    '      "name": "Tab é",\n'
    '      "params": {\n'
    '        "count": 9\n'
    "      }\n"
    "    }\n"
    "  ],\n"
    '  "figWidth": 40\n'
    "}\n"
)

PRESETS_BYTES = (
    "[\n"
    "  {\n"
    '    "label": "first",\n'
    '    "params": {\n'
    '      "count": 3,\n'
    '      "opacity": 0.5,\n'
    '      "line_color": "#336699",\n'
    '      "title": "Demo",\n'
    '      "grid": true,\n'
    '      "mode": "a",\n'
    '      "ncols": 2,\n'
    '      "values": [\n'
    "        4,\n"
    "        5\n"
    "      ],\n"
    '      "widths": [\n'
    "        2.0\n"
    "      ],\n"
    '      "fail": false\n'
    "    },\n"
    '    "timestamp": "<time>"\n'
    "  }\n"
    "]\n"
)

# The HTML page is served verbatim; its digest pins the whole client
# (markup, CSS and JS that read the descriptor keys and call every route).
PAGE_SHA256 = "961cffa35304acde6928c94f91cf0fabd14b9ba018a204f9db487e5630fc53cc"


def test_read_routes_serve_the_page_controls_defaults_and_metadata(
    viewer: TestClient,
) -> None:
    """GET routes answer with the frozen payloads before any state exists."""
    page = viewer.get("/")
    assert page.status_code == 200
    assert page.headers["content-type"] == "text/html; charset=utf-8"
    assert "<title>Golden &lt;viewer&gt;</title>" in page.text
    assert hashlib.sha256(page.content).hexdigest() == PAGE_SHA256
    assert call(viewer, "GET", "/api/descriptors") == (200, DESCRIPTORS)
    assert call(viewer, "GET", "/api/defaults") == (200, DEFAULTS)
    assert call(viewer, "GET", "/api/meta") == (
        200,
        {"function_name": "golden_figure"},
    )
    assert call(viewer, "GET", "/api/health") == (200, {"status": "ok"})
    assert call(viewer, "GET", "/api/config") == (200, {})
    assert call(viewer, "GET", "/api/presets") == (200, [])
    assert call(viewer, "POST", "/api/reload") == (200, {"status": "reloading"})
    assert viewer.restarts == ["restart"]  # type: ignore[attr-defined]


def test_state_routes_write_the_frozen_file_bytes_and_project_reads(
    viewer: TestClient, tmp_path: Path
) -> None:
    """save-state/config/preset write the frozen JSON bytes; reads project them."""
    script = tmp_path / "script"
    assert call(viewer, "POST", "/api/config", ACTIVE) == (
        200,
        {"status": "ok"},
    )
    state = {
        "params": ACTIVE,
        "tabs": [{"id": 1, "name": "Tab é", "params": {"count": 9}}],
        "figWidth": 40,
    }
    assert call(viewer, "POST", "/api/save-state", state) == (
        200,
        {"status": "ok"},
    )
    config = script / ".dartwork_ui_config.json"
    assert normalized(config.read_bytes()) == CONFIG_BYTES
    assert config.stat().st_mode & 0o777 == 0o600
    status, body = call(viewer, "GET", "/api/config")
    assert status == 200
    assert {**body, "updated_at": "<time>"} == {
        "function": "golden_figure",
        "params": DUMPED,
        "updated_at": "<time>",
        "tabs": [
            {
                "id": 1,
                "name": "Tab é",
                "params": {"count": 9},
                "dropped_fields": [],
            }
        ],
        "figWidth": 40,
        "dropped_fields": [],
    }

    preset = {"label": "first", "params": ACTIVE}
    assert call(viewer, "POST", "/api/preset", preset) == (
        200,
        {"status": "ok"},
    )
    presets = script / ".dartwork_ui_presets.json"
    assert normalized(presets.read_bytes()) == PRESETS_BYTES
    status, body = call(viewer, "GET", "/api/presets")
    assert status == 200
    assert [{**entry, "timestamp": "<time>"} for entry in body] == [
        {
            "label": "first",
            "params": DUMPED,
            "timestamp": "<time>",
            "dropped_fields": [],
        }
    ]
    assert call(viewer, "DELETE", "/api/preset/5") == (
        404,
        {"detail": "Preset index does not exist.", "code": "preset_not_found"},
    )
    assert call(viewer, "DELETE", "/api/preset/0") == (200, {"status": "ok"})
    assert presets.read_bytes() == b"[]\n"

    config.write_bytes(b"{not json")
    refused = {
        "detail": "Stored viewer state is invalid; preserve the existing file.",
        "code": "invalid_stored_state",
    }
    assert call(viewer, "GET", "/api/config") == (409, refused)
    assert call(viewer, "POST", "/api/config", ACTIVE) == (409, refused)
    assert config.read_bytes() == b"{not json"


def test_render_export_and_script_downloads(viewer: TestClient) -> None:
    """Render answers base64 PNG; downloads keep their media types and names."""
    status, body = call(viewer, "POST", "/api/render", ACTIVE)
    assert status == 200 and list(body) == ["image"]
    assert base64.b64decode(body["image"]).startswith(b"\x89PNG\r\n\x1a\n")
    for fmt, media in (
        ("png", "image/png"),
        ("svg", "image/svg+xml"),
        ("pdf", "application/pdf"),
        ("PNG", "image/png"),
        ("eps", "application/octet-stream"),
    ):
        response = viewer.post(f"/api/export/{fmt}", json=ACTIVE)
        assert response.status_code == 200, fmt
        assert response.headers["content-type"] == media
        assert response.headers["content-disposition"] == (
            f'attachment; filename="figure.{fmt.lower()}"'
        )
    response = viewer.post("/api/script", json=ACTIVE)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/x-python")
    assert response.headers["content-disposition"] == (
        'attachment; filename="generate_figure.py"'
    )
    assert response.text.startswith('"""Auto-generated figure script.')
    assert "    count=3,\n" in response.text


def test_server_saves_answer_receipts_and_refuse_conflicts(
    viewer: TestClient, tmp_path: Path
) -> None:
    """Server saves return relative names and display paths; a second save conflicts."""
    request = {"params": ACTIVE, "filename": "sub/out.png"}
    status, body = call(viewer, "POST", "/api/save-server/image/png", request)
    assert status == 200
    assert body == {
        "status": "ok",
        "path": str((tmp_path / "script/sub/out.png").resolve()),
        "filename": "sub/out.png",
        "copied_to": [str((tmp_path / "copy/sub/out.png").resolve())],
    }
    assert call(viewer, "POST", "/api/save-server/image/png", request) == (
        409,
        {
            "detail": "File exists; choose a new name.",
            "code": "output_conflict",
        },
    )
    status, body = call(
        viewer,
        "POST",
        "/api/save-server/image/svg",
        {"params": ACTIVE, "filename": "named.pdf"},
    )
    assert (status, body["filename"]) == (200, "named.pdf")
    status, body = call(
        viewer, "POST", "/api/save-server/image/png", {"params": {}}
    )
    assert status == 200 and sorted(body) == [
        "copied_to",
        "filename",
        "path",
        "status",
    ]
    assert re.fullmatch(
        r"golden_figure_\d{8}_\d{6}_[0-9a-f]{12}\.png", body["filename"]
    )
    status, body = call(
        viewer,
        "POST",
        "/api/save-server/script",
        {"params": ACTIVE, "filename": "gen"},
    )
    assert status == 200
    assert body == {
        "status": "ok",
        "path": str((tmp_path / "script/gen.py").resolve()),
        "filename": "gen.py",
    }
    assert not (tmp_path / "copy/gen.py").exists()


INVALID_REQUEST = {
    "detail": "Input does not match the viewer request schema.",
    "code": "invalid_request",
}
INVALID_PARAMS = {
    "detail": "Parameters must use declared names and satisfy their types and constraints.",
    "code": "invalid_request",
}
DENIED = {
    "detail": "Request is outside the local viewer policy.",
    "code": "local_access_denied",
}


def test_refusals_keep_their_status_detail_and_code(viewer: TestClient) -> None:
    """Every named refusal answers its frozen status and detail/code body."""
    media = {
        "detail": "Use unencoded application/json with UTF-8.",
        "code": "unsupported_media_type",
    }
    cases: list[tuple[str, str, dict[str, Any], int, dict[str, Any]]] = [
        (
            "POST",
            "/api/render",
            {"content": b"{", "headers": {"content-type": "application/json"}},
            400,
            {
                "detail": "Input must be unambiguous finite UTF-8 JSON.",
                "code": "invalid_json",
            },
        ),
        (
            "POST",
            "/api/render",
            {"content": b"{}", "headers": {"content-type": "text/plain"}},
            415,
            media,
        ),
        (
            "POST",
            "/api/render",
            {
                "content": b" " * (1024 * 1024 + 1),
                "headers": {"content-type": "application/json"},
            },
            413,
            {
                "detail": "Input exceeds the viewer limits.",
                "code": "input_too_large",
            },
        ),
        ("POST", "/api/render", {"json": {"nope": 1}}, 422, INVALID_PARAMS),
        ("POST", "/api/render", {"json": {"count": 99}}, 422, INVALID_PARAMS),
        ("POST", "/api/render", {"json": [1]}, 422, INVALID_REQUEST),
        (
            "POST",
            "/api/render",
            {"json": {"fail": True}},
            500,
            {
                "detail": "The figure callback failed.",
                "code": "callback_failed",
            },
        ),
        (
            "POST",
            "/api/render",
            {"json": {}, "headers": {"origin": "http://evil.test"}},
            403,
            DENIED,
        ),
        ("GET", "/api/health", {"headers": {"host": "evil.test"}}, 403, DENIED),
        ("PUT", "/api/render", {"json": {}}, 403, DENIED),
        ("POST", "/unknown", {"json": {}}, 403, DENIED),
        (
            "GET",
            "/unknown",
            {},
            404,
            {"detail": "Not Found", "code": "not_found"},
        ),
        ("DELETE", "/api/preset/abc", {}, 422, INVALID_REQUEST),
        (
            "POST",
            "/api/save-state",
            {"json": {"params": {}, "figWidth": 10}},
            422,
            INVALID_REQUEST,
        ),
        (
            "POST",
            "/api/preset",
            {"json": {"label": "x" * 257, "params": {}}},
            413,
            {
                "detail": "Input exceeds the viewer limits.",
                "code": "input_too_large",
            },
        ),
        (
            "POST",
            "/api/save-server/image/png",
            {"json": {"params": {}, "filename": "../x.png"}},
            400,
            {
                "detail": "Filename must be a bounded safe relative path.",
                "code": "invalid_output_path",
            },
        ),
        (
            "POST",
            "/api/save-server/script",
            {"json": {"filename": "x"}},
            422,
            INVALID_REQUEST,
        ),
        (
            "POST",
            "/api/script",
            {"json": {"fail": "maybe"}},
            422,
            INVALID_PARAMS,
        ),
    ]
    for method, path, kwargs, status, body in cases:
        assert call(viewer, method, path, **kwargs) == (status, body), (
            method,
            path,
            kwargs.get("json"),
        )
    status, body = call(viewer, "POST", "/api/export/bogus", {})
    assert (status, body["code"]) == (400, "invalid_request")
    assert body["detail"].startswith("Unsupported export format 'bogus'.")
    status, body = call(viewer, "POST", "/api/save-server/image/bogus", {})
    assert (status, body["code"]) == (400, "invalid_request")


def test_missing_filesystem_capabilities_refuse_state_but_keep_rendering(
    tmp_path: Path,
) -> None:
    """Without safe directory handles, state and saves answer 501 and render still works."""
    app = _create_app(
        golden_figure,
        GoldenParams,
        title="t",
        script_root=tmp_path / "script",
        copy_to=None,
        host="localhost",
        capabilities=FilesystemCapabilities(*([False] * 8)),
    )
    unsupported = {
        "detail": "This host lacks filesystem capabilities required for safe viewer persistence.",
        "code": "unsupported_filesystem_capability",
    }
    with TestClient(app, base_url=ORIGIN) as client:
        assert call(client, "GET", "/api/config") == (501, unsupported)
        assert call(client, "GET", "/api/presets") == (501, unsupported)
        assert call(
            client, "POST", "/api/preset", {"label": "x", "params": {}}
        ) == (501, unsupported)
        assert call(
            client, "POST", "/api/save-server/script", {"params": {}}
        ) == (501, unsupported)
        assert call(client, "POST", "/api/render", {})[0] == 200
    assert not (tmp_path / "script").exists()


def test_descriptor_payload_is_plain_json(viewer: TestClient) -> None:
    """The descriptor body round-trips through JSON with its null spellings intact."""
    raw = viewer.get("/api/descriptors").content
    assert json.loads(raw) == DESCRIPTORS
    assert b'"min_value":null' in raw
