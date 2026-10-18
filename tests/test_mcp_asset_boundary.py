"""Bundled MCP assets stay confined through callbacks and real URI decoding."""

import asyncio
import random
import string
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

fastmcp = pytest.importorskip("fastmcp")

from dartwork_mpl.mcp import _assets, resources, tools  # noqa: E402

_SENTINEL = "OUTSIDE_ASSET_CONTENT_DO_NOT_RETURN"
_ROUTES = (
    "dartwork-mpl://templates/{plot_type}",
    "dartwork-mpl://templates/advanced/{plot_type}",
    "dartwork-mpl://styles/{preset}",
)


def _server() -> Any:
    """Register real FastMCP components without substituting its decorators."""
    server = fastmcp.FastMCP("asset-boundary-test")
    resources.register_resources(server)
    tools.register_tools(server)
    return server


def _callback(server: Any, route: str) -> Callable[..., Any]:
    """Return the callback registered on a real FastMCP resource template."""
    template = asyncio.run(server.get_resource_template(route))
    assert template is not None
    return template.fn


@pytest.fixture
def asset_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use real assets, escaped sentinels, directories and symlinks in isolation."""
    templates = tmp_path / "templates"
    styles = tmp_path / "styles"
    (templates / "advanced").mkdir(parents=True)
    styles.mkdir()
    for directory in (tmp_path, templates):
        (directory / "outside.py").write_text(_SENTINEL, encoding="utf-8")
        (directory / "outside.mplstyle").write_text(_SENTINEL, encoding="utf-8")
    (templates / "basic_only.py").write_text(
        "# basic-only template\n", encoding="utf-8"
    )
    for directory in (templates, templates / "advanced"):
        (directory / "linked.py").symlink_to(tmp_path / "outside.py")
        (directory / "directory.py").mkdir()
        (directory / "inside.py").write_text("# inside\n", encoding="utf-8")
        (directory / "alias.py").symlink_to(directory / "inside.py")
    (styles / "linked.mplstyle").symlink_to(tmp_path / "outside.mplstyle")
    (styles / "directory.mplstyle").mkdir()
    (styles / "inside.mplstyle").write_text("# inside\n", encoding="utf-8")
    (styles / "alias.mplstyle").symlink_to(styles / "inside.mplstyle")
    (styles / "MiXeD_style-1.mplstyle").write_text(
        "# case-sensitive style\n", encoding="utf-8"
    )
    for directory, suffix in (
        (templates, ".py"),
        (templates / "advanced", ".py"),
        (styles, ".mplstyle"),
    ):
        (directory / "nested").mkdir()
        (directory / "nested" / f"inside{suffix}").write_text(
            _SENTINEL, encoding="utf-8"
        )
        for stem in ("inside.dot", "inside\n"):
            (directory / f"{stem}{suffix}").write_text(
                _SENTINEL, encoding="utf-8"
            )
        (directory / f"loop{suffix}").symlink_to(f"loop{suffix}")
        (directory / f"broken{suffix}").symlink_to(f"missing{suffix}")
    # All readers see the same isolated installation of bundled assets.
    for owner in (resources, tools, _assets):
        monkeypatch.setattr(owner, "_TEMPLATE_DIR", templates)
        monkeypatch.setattr(owner, "_MPLSTYLE_DIR", styles)
    return tmp_path


@pytest.mark.parametrize("route", _ROUTES)
@pytest.mark.parametrize(
    "asset_id",
    [
        "../outside",
        "../../outside",
        "%2e%2e%2foutside",
        "%252e%252e%252foutside",
        "..\\outside",
        "",
        "\x00",
        "inside\n",
        "inside.py",
        "inside.dot",
        "nested/inside",
        "directory",
        "loop",
        "broken",
    ],
)
def test_resource_rejects_path_escape(
    asset_roots: Path, route: str, asset_id: str
) -> None:
    """Malformed IDs and nonfiles return the existing not-found response family."""
    content = _callback(_server(), route)(asset_id)
    assert _SENTINEL not in content
    assert content.startswith(("No template for ", "Style preset '"))
    assert "not found" in content or "No template for " in content


@pytest.mark.parametrize("route", _ROUTES)
def test_resource_rejects_absolute_path_escape(
    asset_roots: Path, route: str
) -> None:
    """An absolute ID cannot grant access to a real external file."""
    content = _callback(_server(), route)(str(asset_roots / "outside"))
    assert _SENTINEL not in content
    assert content.startswith(("No template for ", "Style preset '"))


@pytest.mark.parametrize("route", _ROUTES)
def test_encoded_uri_cannot_escape(asset_roots: Path, route: str) -> None:
    """Actual FastMCP URI percent decoding cannot expose escaped file contents."""

    async def read_encoded_ids() -> None:
        """Exercise encoded separators through the client and server protocol."""
        async with fastmcp.Client(_server()) as client:
            for stem in (
                "%2e%2e%2foutside",
                "%2e%2e%2f%2e%2e%2foutside",
                "%252e%252e%252foutside",
                "%2e%2e%5coutside",
                "%00",
                "nested%2finside",
            ):
                uri = route.replace("{plot_type}", stem).replace(
                    "{preset}", stem
                )
                result = await client.read_resource(uri)
                text = "".join(item.text for item in result)
                assert _SENTINEL not in text, uri
                assert "No template for " in text or "not found" in text, uri

    asyncio.run(read_encoded_ids())


@pytest.mark.parametrize("route", _ROUTES)
def test_asset_symlink_cannot_escape(asset_roots: Path, route: str) -> None:
    """A valid-looking stem cannot read a symlink targeting outside its root."""
    content = _callback(_server(), route)("linked")
    assert _SENTINEL not in content
    assert "No template for " in content or "not found" in content


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("render_template", {}),
        ("render_template_advanced", {}),
        ("compose_layered_plot", {"tier": "basic"}),
        ("compose_layered_plot", {"tier": "advanced"}),
    ],
)
def test_template_tools_reject_symlink_escape(
    asset_roots: Path, name: str, kwargs: dict[str, Any]
) -> None:
    """Render and compose reject external symlinks without code or image data."""
    tool = asyncio.run(_server().get_tool(name))
    result = tool.fn("linked", **kwargs)
    assert result["status"] == "unknown_template"
    assert result.get("png_base64") is None
    assert (
        result.get("code", "").startswith("No template named")
        or "code" not in result
    )
    assert _SENTINEL not in str(result)


@pytest.mark.parametrize(
    ("route", "stem", "relative_file"),
    [
        (_ROUTES[0], "BAR", "prompt/05-templates/bar.py"),
        (_ROUTES[1], "BAR", "prompt/05-templates/advanced/bar.py"),
        (_ROUTES[2], "font-scientific", "mplstyle/font-scientific.mplstyle"),
        (_ROUTES[2], "dmpl_light", "mplstyle/dmpl_light.mplstyle"),
    ],
)
def test_bundled_assets_remain_readable(
    route: str, stem: str, relative_file: str
) -> None:
    """Bundled basic, advanced and style successes preserve exact UTF-8 text."""
    asset_dir = Path(resources.__file__).parent.parent / "asset"
    assert _callback(_server(), route)(stem) == (
        asset_dir / relative_file
    ).read_text(encoding="utf-8")


def test_advanced_resource_falls_back_safely(asset_roots: Path) -> None:
    """A missing advanced asset still resolves a valid basic-only template."""
    # Unsafe advanced candidates are misses too: fallback must still be confined.
    (asset_roots / "templates" / "advanced" / "basic_only.py").symlink_to(
        asset_roots / "outside.py"
    )
    callback = _callback(_server(), _ROUTES[1])
    assert callback("BASIC_ONLY") == (
        asset_roots / "templates" / "basic_only.py"
    ).read_text(encoding="utf-8")


def test_generated_invalid_ids_never_escape(asset_roots: Path) -> None:
    """Seeded malformed IDs resolve only to regular files within their tier."""
    seed = 20261018
    rng = random.Random(seed)
    alphabet = string.ascii_letters + string.digits + "_-/\\%.\x00\n"
    candidates = [
        "inside",
        "alias",
        "linked",
        "directory",
        "../outside",
        "loop",
        "broken",
        "nested/inside",
        "inside.dot",
        "inside\n",
        "MiXeD_style-1",
    ]
    candidates.extend(
        "".join(rng.choices(alphabet, k=rng.randrange(0, 50)))
        for _ in range(300)
    )
    for advanced in (False, True):
        root = asset_roots / "templates"
        if advanced:
            root /= "advanced"
        for candidate in candidates:
            path = _assets.resolve_template_path(candidate, advanced=advanced)
            if path is not None:
                context = f"seed={seed} id={candidate!r} advanced={advanced}"
                assert path == path.resolve(), context
                assert path.is_file(), context
                assert path.is_relative_to(root.resolve()), context

    for candidate in candidates:
        path = _assets.resolve_style_path(candidate)
        if path is not None:
            context = f"seed={seed} style_id={candidate!r}"
            assert path == path.resolve(), context
            assert path.is_file(), context
            assert path.is_relative_to((asset_roots / "styles").resolve()), (
                context
            )


def test_style_ids_preserve_case(asset_roots: Path) -> None:
    """Style IDs retain their spelling while permitting hyphens and underscores."""
    callback = _callback(_server(), _ROUTES[2])
    assert callback("MiXeD_style-1") == "# case-sensitive style\n"
    assert (
        _assets.resolve_style_path("MiXeD_style-1")
        == (asset_roots / "styles" / "MiXeD_style-1.mplstyle").resolve()
    )
