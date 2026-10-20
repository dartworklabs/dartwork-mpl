"""Real loopback HTTP contracts, reusable unchanged against an installed wheel.

The child owns a trusted callback, temporary files, socket, and restart observer.
No repository fixture, conftest helper, TestClient, or live service is required.
"""

import hashlib
import http.client
import importlib.metadata
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import dartwork_mpl

_BOOTSTRAP = r"""
import asyncio, json, os, socket, sys, threading
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from pydantic import Field
import dartwork_mpl as dm
from dartwork_mpl.ui import ParamModel
from dartwork_mpl.ui import ui
from dartwork_mpl.ui._files import FilesystemCapabilities
import uvicorn
root, expected, unsupported, copy_mode = sys.argv[1:]
root = Path(root)
assert Path(dm.__file__).resolve() == Path(expected).resolve()
class Params(ParamModel):
    opacity: float = Field(default=0.5, ge=0, le=1)
    values: list[int] = Field(default=[1, 2])
    fail: bool = False
    class Config:
        extra = "allow"
def plot(params: Params) -> Figure:
    assert threading.current_thread() is threading.main_thread()
    asyncio.get_running_loop()
    receipt = root / "callbacks"
    with receipt.open("a") as f:
        f.write("called\n")
    if params.fail:
        raise RuntimeError("SECRET_CALLBACK_PAYLOAD")
    if copy_mode == "late-create":
        (root / "copy2" / "raced.png").write_bytes(b"external-create")
    if copy_mode == "parent-swap":
        (root / "script" / "sub").rename(root / "script" / "moved")
        (root / "script" / "sub").symlink_to(root / "outside", target_is_directory=True)
    dm.style.use("scientific")
    fig, ax = plt.subplots(figsize=dm.figsize("5cm", "standard"))
    ax.plot(params.values, alpha=params.opacity)
    dm.simple_layout(fig)
    return fig
def restart():
    with (root / "restarts").open("a") as f:
        f.write("restart\n")
capabilities = FilesystemCapabilities(*([False] * 8)) if unsupported == "yes" else None
copies = [root / "copy", root / "copy2"]
if copy_mode == "alias": copies = [str(root / "script"), root / "script"]
if copy_mode == "relative": copies = "copy"
if copy_mode == "invalid-root":
    (root / "bad-root").write_bytes(b"not-a-directory")
    copies = [root / "copy", root / "bad-root"]
if copy_mode in {"write-failure", "cleanup-failure"}:
    from dartwork_mpl.ui import _files
    original_write = _files._write_file
    writes = 0
    def fail_second(fd, data):
        global writes
        writes += 1
        if writes == 2: raise OSError("SECRET_IO_PAYLOAD")
        original_write(fd, data)
    _files._write_file = fail_second
    if copy_mode == "cleanup-failure":
        _files._remove_file = lambda *args: False
app = ui._create_app(plot, Params, title="HTTP fixture", script_root=root / "script", copy_to=copies, host="127.0.0.1", restart=restart, capabilities=capabilities)
def serve(app):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    (root / "ready.json").write_text(json.dumps({"port": sock.getsockname()[1], "origin": dm.__file__, "version": __import__("importlib.metadata").metadata.version("dartwork-mpl")}))
    server.run(sockets=[sock])
serve(app)
"""


@dataclass
class Viewer:
    """A running child and its isolated roots; requests use actual TCP HTTP."""

    root: Path
    port: int

    def request(
        self,
        method: str,
        path: str,
        value: Any = None,
        *,
        raw: bytes | None = None,
        headers: dict[str, str] | None = None,
        chunked: bool = False,
    ) -> tuple[int, bytes]:
        """Send JSON or supplied bytes and return the real response status/body."""
        body = (
            raw
            if raw is not None
            else json.dumps(value).encode()
            if value is not None
            else None
        )
        request_headers = {"Content-Type": "application/json"}
        request_headers.update(headers or {})
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.port, timeout=10
        )
        try:
            connection.request(
                method,
                path,
                body=[body] if chunked else body,
                headers=request_headers,
                encode_chunked=chunked,
            )
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def raw_request(self, request: bytes) -> tuple[int, bytes]:
        """Use HTTP/1 wire bytes to expose malformed/duplicate framing and headers."""
        with socket.create_connection(
            ("127.0.0.1", self.port), timeout=10
        ) as client:
            client.sendall(request)
            client.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                part = client.recv(65536)
                if not part:
                    break
                chunks.append(part)
        response = b"".join(chunks)
        return int(response.split(b" ", 2)[1]), response

    def manifest(self) -> dict[str, str]:
        """Hash all root files, including sentinels, so refusals cannot hide writes."""
        return {
            str(path.relative_to(self.root)): (
                "symlink:" + os.readlink(path)
                if path.is_symlink()
                else "dir"
                if path.is_dir()
                else "file:" + hashlib.sha256(path.read_bytes()).hexdigest()
            )
            for path in sorted(self.root.rglob("*"))
            if path.name not in {"ready.json", "server.log"}
        }


@contextmanager
def _viewer(
    root: Path, *, unsupported: bool = False, copy_mode: str = "multiple"
) -> Iterator[Viewer]:
    """Launch one owned child; always terminate/wait before temporary roots disappear."""
    for name in ("script", "copy", "copy2", "outside"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "outside" / "sentinel").write_bytes(b"outside-original")
    origin = Path(dartwork_mpl.__file__).resolve()
    if sys.flags.isolated:
        assert "site-packages" in origin.parts
        assert not (origin.parent.parent / "pyproject.toml").exists()
        checkout = os.environ.get("DARTWORK_HTTP_EXCLUDED_CHECKOUT")
        assert checkout and not origin.is_relative_to(Path(checkout).resolve())
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    if not sys.flags.isolated:
        env["PYTHONPATH"] = str(origin.parent.parent)
    command = [
        sys.executable,
        *(["-I"] if sys.flags.isolated else []),
        "-c",
        _BOOTSTRAP,
        str(root),
        str(origin),
        "yes" if unsupported else "no",
        copy_mode,
    ]
    with (root / "server.log").open("w") as log:
        child = subprocess.Popen(
            command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT
        )
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and child.poll() is None:
                ready = root / "ready.json"
                if ready.exists():
                    metadata = json.loads(ready.read_text())
                    assert Path(metadata["origin"]).resolve() == origin
                    viewer = Viewer(root, metadata["port"])
                    try:
                        healthy = viewer.request("GET", "/api/health")[0] == 200
                    except (OSError, http.client.HTTPException):
                        healthy = False
                    if healthy:
                        yield viewer
                        return
                time.sleep(0.02)
            pytest.fail(
                "child failed to become ready: "
                + (root / "server.log").read_text()
            )
        finally:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=10)


def test_real_http_saved_targets_are_create_only(tmp_path: Path) -> None:
    """Primary and every copy must preserve existing files before invoking a callback."""
    with _viewer(tmp_path) as viewer:
        for root in ("script", "copy", "copy2"):
            path = tmp_path / root / "existing.png"
            path.write_bytes(root.encode())
            before = viewer.manifest()
            status, _ = viewer.request(
                "POST",
                "/api/save-server/image/png",
                {"params": {}, "filename": "existing.png"},
            )
            assert status == 409
            assert viewer.manifest() == before
            path.unlink()
        (tmp_path / "script" / "fixture.py").write_bytes(b"original-script")
        before = viewer.manifest()
        assert (
            viewer.request(
                "POST",
                "/api/save-server/script",
                {"params": {}, "filename": "fixture.py"},
            )[0]
            == 409
        )
        assert viewer.manifest() == before
        status, body = viewer.request(
            "POST",
            "/api/save-server/image/png",
            {"params": {"values": "1,2,3"}, "filename": "safe/sub.png"},
        )
        assert status == 200, body
        assert len(json.loads(body)["copied_to"]) == 2
        assert (
            (tmp_path / "script" / "safe/sub.png").read_bytes()
            == (tmp_path / "copy" / "safe/sub.png").read_bytes()
            == (tmp_path / "copy2" / "safe/sub.png").read_bytes()
        )
        assert (
            viewer.request(
                "POST",
                "/api/save-server/script",
                {"params": {}, "filename": "safe/new"},
            )[0]
            == 200
        )
        assert not (tmp_path / "copy" / "safe/new.py").exists()


def test_real_http_rejects_foreign_or_unknown_effect(tmp_path: Path) -> None:
    """Host and each browser source deny effects before callbacks or persisted writes."""
    with _viewer(tmp_path) as viewer:
        before = viewer.manifest()
        for headers in (
            {"Host": "evil.example"},
            {"Host": "user@localhost"},
            {"Host": "localhost:bad"},
            {"Origin": "http://evil.example"},
            {
                "Origin": f"http://127.0.0.1:{viewer.port}",
                "Referer": "http://evil.example/x",
            },
            {"Origin": "http://localhost.evil"},
        ):
            assert (
                viewer.request("POST", "/api/render", {}, headers=headers)[0]
                == 403
            )
            assert viewer.manifest() == before
        assert viewer.request("POST", "/api/unknown", {})[0] == 403
        assert viewer.request("GET", "/api/unknown")[0] == 404
        assert (
            viewer.request(
                "GET", "/api/unknown", headers={"Host": "evil.example"}
            )[0]
            == 403
        )
        assert viewer.manifest() == before
        authority = f"127.0.0.1:{viewer.port}"
        assert (
            viewer.request(
                "POST",
                "/api/render",
                {},
                headers={
                    "Origin": f"http://{authority}",
                    "Referer": f"http://{authority}/?x=1",
                },
            )[0]
            == 200
        )


def test_real_http_bounds_wire_input(tmp_path: Path) -> None:
    """The streamed body language rejects ambiguity, limits, unknown keys and wrong media."""
    with _viewer(tmp_path) as viewer:
        before = viewer.manifest()
        for raw in (
            b'{"opacity":0.2,"opacity":0.4}',
            b'{"opacity":NaN}',
            b"\xff",
            b"{",
            b'{"opacity":1e999}',
        ):
            assert viewer.request("POST", "/api/render", raw=raw)[0] == 400
        for raw in (
            b'{"x":"' + b"a" * 1048576 + b'"}',
            b"[" * 20 + b"0" + b"]" * 20,
        ):
            assert (
                viewer.request("POST", "/api/render", raw=raw, chunked=True)[0]
                == 413
            )
        for headers in (
            {"Content-Type": "text/plain"},
            {"Content-Type": "application/json; charset=latin-1"},
            {"Content-Encoding": "gzip"},
        ):
            assert (
                viewer.request("POST", "/api/render", {}, headers=headers)[0]
                == 415
            )
        for value in ({"ignored": 1}, {"opacity": 5}, {"values": "oops"}, []):
            assert viewer.request("POST", "/api/render", value)[0] == 422
        assert viewer.manifest() == before
        assert viewer.request("POST", "/api/render", {}, chunked=True)[0] == 200


def test_real_http_state_drift_and_corruption(tmp_path: Path) -> None:
    """Reads project old field names; structural corruption preserves bytes on every edit."""
    with _viewer(tmp_path) as viewer:
        config = tmp_path / "script" / ".dartwork_ui_config.json"
        presets = tmp_path / "script" / ".dartwork_ui_presets.json"
        config.write_text(
            json.dumps(
                {
                    "params": {"old": 1, "opacity": 0.3},
                    "tabs": [
                        {
                            "id": 1,
                            "name": "old",
                            "params": {"old": "stale", "opacity": "bad"},
                        }
                    ],
                    "figWidth": 999,
                }
            )
        )
        old_bytes = config.read_bytes()
        status, body = viewer.request("GET", "/api/config")
        assert status == 200, body
        projected = json.loads(body)
        assert projected["params"] == {"opacity": 0.3}
        assert projected["dropped_fields"] == ["old"]
        assert projected["tabs"][0]["params"] == {"opacity": "bad"}
        assert projected["figWidth"] == 70
        assert config.read_bytes() == old_bytes
        assert (
            viewer.request("POST", "/api/render", {"opacity": "bad"})[0] == 422
        )
        status, body = viewer.request("GET", "/api/defaults")
        assert status == 200
        assert viewer.request("POST", "/api/render", json.loads(body))[0] == 200
        for state in (config, presets):
            state.write_bytes(b"\xffbad-json")
        before = viewer.manifest()
        for method, path, value in (
            ("GET", "/api/config", None),
            ("GET", "/api/presets", None),
            ("POST", "/api/config", {}),
            ("POST", "/api/save-state", {"params": {}}),
            ("POST", "/api/preset", {"label": "new", "params": {}}),
            ("DELETE", "/api/preset/0", None),
        ):
            status, body = viewer.request(method, path, value)
            assert status == 409, body
            assert json.loads(body)["code"] == "invalid_stored_state"
            assert viewer.manifest() == before


def test_real_http_downloads_and_reload(tmp_path: Path) -> None:
    """Downloads, state/tabs, presets and bodyless authorized reload preserve the native API."""
    with _viewer(tmp_path) as viewer:
        for path in (
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/docs/oauth2-redirect",
            "/api/descriptors",
            "/api/meta",
            "/api/defaults",
        ):
            assert viewer.request("GET", path)[0] == 200
        for fmt, magic in (
            ("png", b"\x89PNG"),
            ("svg", b"<?xml"),
            ("pdf", b"%PDF"),
        ):
            status, body = viewer.request("POST", f"/api/export/{fmt}", {})
            assert status == 200 and body.startswith(magic)
        assert viewer.request("POST", "/api/script", {})[0] == 200
        assert (
            viewer.request(
                "POST",
                "/api/save-state",
                {
                    "params": {"opacity": 0.4},
                    "tabs": [
                        {"id": 0, "name": "tab", "params": {"opacity": "old"}}
                    ],
                    "figWidth": 80,
                },
            )[0]
            == 200
        )
        assert (
            json.loads(viewer.request("GET", "/api/config")[1])["figWidth"]
            == 80
        )
        for label in ("one", "two"):
            assert (
                viewer.request(
                    "POST", "/api/preset", {"label": label, "params": {}}
                )[0]
                == 200
            )
        assert [
            entry["label"]
            for entry in json.loads(viewer.request("GET", "/api/presets")[1])
        ] == ["one", "two"]
        assert viewer.request("DELETE", "/api/preset/0")[0] == 200
        assert viewer.request("DELETE", "/api/preset/9")[0] == 404
        assert viewer.request("POST", "/api/reload")[0] == 200
        assert (tmp_path / "restarts").read_text() == "restart\n"


def test_real_http_unsupported_filesystem_keeps_render(tmp_path: Path) -> None:
    """Unavailable persistence explicitly returns 501 while render/download remain usable."""
    with _viewer(tmp_path, unsupported=True) as viewer:
        for method, path, value in (
            ("GET", "/api/config", None),
            ("GET", "/api/presets", None),
            ("POST", "/api/config", {}),
            ("POST", "/api/preset", {"label": "x", "params": {}}),
            ("DELETE", "/api/preset/0", None),
            ("POST", "/api/save-server/image/png", {"params": {}}),
        ):
            status, body = viewer.request(method, path, value)
            assert status == 501, body
            assert (
                json.loads(body)["code"] == "unsupported_filesystem_capability"
            )
        assert viewer.request("POST", "/api/render", {})[0] == 200
        assert viewer.request("POST", "/api/export/png", {})[0] == 200
        assert viewer.request("POST", "/api/script", {})[0] == 200


def test_real_http_raw_headers_and_framing(tmp_path: Path) -> None:
    """The server rejects missing/duplicate authorities and ambiguous wire framing."""
    with _viewer(tmp_path) as viewer:
        before = viewer.manifest()
        for headers in (
            b"",
            b"Host: localhost\r\nHost: localhost\r\n",
            b"Host: localhost\r\nOrigin: http://localhost\r\nOrigin: http://localhost\r\n",
            b"Host: localhost\r\nReferer: http://localhost/a\r\nReferer: http://localhost/a\r\n",
        ):
            status, _ = viewer.raw_request(
                b"POST /api/render HTTP/1.0\r\n"
                + headers
                + b"Content-Type: application/json\r\nContent-Length: 2\r\n\r\n{}"
            )
            assert status in (400, 403)
        status, _ = viewer.raw_request(
            b"POST /api/render HTTP/1.1\r\nHost: localhost\r\nContent-Length: 2\r\nContent-Length: 3\r\n\r\n{}x"
        )
        assert status == 400
        assert viewer.manifest() == before


def test_real_http_paths_and_copy_aliases(tmp_path: Path) -> None:
    """Safe relative paths work; escapes/symlinks and aliased copy roots cannot overwrite."""
    with _viewer(tmp_path, copy_mode="alias") as viewer:
        (tmp_path / "script" / "link").symlink_to(
            tmp_path / "outside", target_is_directory=True
        )
        (tmp_path / "script" / "final.png").symlink_to(
            tmp_path / "outside" / "sentinel"
        )
        before = viewer.manifest()
        for name in (
            "../outside/sentinel",
            "/absolute.png",
            "link/sentinel",
            "bad\\name.png",
            "bad\x00name.png",
            "final.png",
            " ",
        ):
            status, _ = viewer.request(
                "POST",
                "/api/save-server/image/png",
                {"params": {}, "filename": name},
            )
            assert status == 400
            assert viewer.manifest() == before
        status, body = viewer.request(
            "POST",
            "/api/save-server/image/png",
            {"params": {}, "filename": "once.png"},
        )
        assert status == 200, body
        assert json.loads(body)["copied_to"] == []


def test_real_http_callback_errors_do_not_leak(tmp_path: Path) -> None:
    """Trusted callback failures are controlled and leave prepared directories clean."""
    with _viewer(tmp_path) as viewer:
        status, body = viewer.request(
            "POST",
            "/api/save-server/image/png",
            {"params": {"fail": True}, "filename": "new/deep/fail.png"},
        )
        assert status == 500
        assert json.loads(body)["code"] == "callback_failed"
        assert b"SECRET" not in body and b"Traceback" not in body
        assert not (tmp_path / "script" / "new").exists()
        assert not (tmp_path / "copy" / "new").exists()
        assert viewer.request("POST", "/api/render", {})[0] == 200


def test_package_origin_receipt() -> None:
    """An isolated wheel run must import its installed distribution outside the checkout."""
    origin = Path(dartwork_mpl.__file__).resolve()
    assert origin.exists()
    assert importlib.metadata.version("dartwork-mpl")
    if sys.flags.isolated:
        assert "site-packages" in origin.parts
        assert not (origin.parent.parent / "pyproject.toml").exists()
        checkout = os.environ.get("DARTWORK_HTTP_EXCLUDED_CHECKOUT")
        assert checkout and not origin.is_relative_to(Path(checkout).resolve())


def test_registered_routes_all_have_explicit_policy(tmp_path: Path) -> None:
    """Inventory framework and application registrations, rejecting any omitted grant."""
    from dartwork_mpl.ui import ParamModel
    from dartwork_mpl.ui._boundary import ROUTE_POLICY
    from dartwork_mpl.ui.ui import _create_app

    class Params(ParamModel):
        """An empty valid model is sufficient to inspect app registration without startup."""

    def figure(_params: Params) -> Any:
        """This read-only inventory must never invoke the plotting callback."""
        raise AssertionError("unexpected callback")

    app = _create_app(
        figure,
        Params,
        title="inventory",
        script_root=tmp_path / "missing",
        copy_to=None,
        host="localhost",
    )

    def declared_routes() -> set[tuple[str, str]]:
        """Collect every actual route method/template directly from the built app."""
        return {
            (method, route.path)
            for route in app.routes
            for method in route.methods
        }

    assert declared_routes() <= ROUTE_POLICY.keys()
    missing_render = dict(ROUTE_POLICY)
    missing_render.pop(("POST", "/api/render"))
    with pytest.raises(AssertionError):
        assert declared_routes() <= missing_render.keys()
    app.add_api_route("/unclassified", lambda: None, methods=["POST"])
    with pytest.raises(AssertionError):
        assert declared_routes() <= ROUTE_POLICY.keys()
    assert not (tmp_path / "missing").exists()


def test_public_bind_rejected_before_filesystem_effects(tmp_path: Path) -> None:
    """run and the app factory reject public binds before creating configured roots."""
    from dartwork_mpl.ui import ParamModel
    from dartwork_mpl.ui.ui import _create_app, run

    class Params(ParamModel):
        """No active fields are needed to test the startup authorization boundary."""

    def figure(_params: Params) -> Any:
        """Rejected startup must never reach the trusted plotting callback."""
        raise AssertionError("unexpected callback")

    before = set(tmp_path.iterdir())
    for host in ("0.0.0.0", "::", "example.test", "192.0.2.1"):
        with pytest.raises(ValueError, match="loopback"):
            _create_app(
                figure,
                Params,
                title="reject",
                script_root=tmp_path / "script",
                copy_to=tmp_path / "copy",
                host=host,
            )
        with pytest.raises(ValueError, match="loopback"):
            run(figure, Params, host=host, copy_to=tmp_path / "copy")
        assert set(tmp_path.iterdir()) == before


@pytest.mark.parametrize(
    "scenario",
    [
        "late-create",
        "parent-swap",
        "write-failure",
        "cleanup-failure",
        "invalid-root",
    ],
)
def test_real_http_owned_filesystem_failure_scenarios(
    tmp_path: Path, scenario: str
) -> None:
    """Late creates, swaps and later I/O/cleanup failures preserve old/outside bytes."""
    with _viewer(tmp_path, copy_mode=scenario) as viewer:
        before = (tmp_path / "outside" / "sentinel").read_bytes()
        if scenario == "parent-swap":
            for root in ("script", "copy", "copy2"):
                (tmp_path / root / "sub").mkdir()
        filename = "sub/new.png" if scenario == "parent-swap" else "raced.png"
        status, body = viewer.request(
            "POST",
            "/api/save-server/image/png",
            {"params": {}, "filename": filename},
        )
        result = json.loads(body)
        expected = {
            "late-create": (409, "output_conflict"),
            "parent-swap": (409, "root_changed"),
            "write-failure": (503, "filesystem_unavailable"),
            "cleanup-failure": (503, "partial_save"),
            "invalid-root": (409, "output_conflict"),
        }
        assert (status, result["code"]) == expected[scenario], body
        assert b"SECRET" not in body and b"Traceback" not in body
        assert (tmp_path / "outside" / "sentinel").read_bytes() == before
        assert not (tmp_path / "outside" / "new.png").exists()
        if scenario == "late-create":
            assert (
                tmp_path / "copy2" / "raced.png"
            ).read_bytes() == b"external-create"
            assert not (tmp_path / "script" / "raced.png").exists()
            assert not (tmp_path / "copy" / "raced.png").exists()
        elif scenario == "cleanup-failure":
            assert result["paths"]
            assert all(not path.startswith("/") for path in result["paths"])
        else:
            assert not list((tmp_path / "script").rglob("*.png"))
            assert not list((tmp_path / "copy").rglob("*.png"))


def test_real_http_string_relative_copy_root(tmp_path: Path) -> None:
    """A single relative string copy root resolves from startup CWD and saves once."""
    with _viewer(tmp_path, copy_mode="relative") as viewer:
        status, body = viewer.request(
            "POST",
            "/api/save-server/image/png",
            {"params": {}, "filename": "relative.png"},
        )
        assert status == 200, body
        assert len(json.loads(body)["copied_to"]) == 1
        assert (tmp_path / "script/relative.png").read_bytes() == (
            tmp_path / "copy/relative.png"
        ).read_bytes()
