"""The server over a real stdio session, and the reading tools' answers."""

from __future__ import annotations

import asyncio
import json
import sys

import pytest

from dartwork_mpl.mcp import library

fastmcp = pytest.importorskip("fastmcp")


async def session(tmp_path) -> dict[str, object]:
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    command = "from dartwork_mpl.mcp import main; main()"
    transport = StdioTransport(sys.executable, ["-c", command])
    async with Client(transport) as client:
        seen: dict[str, object] = {
            "tools": [t.name for t in await client.list_tools()],
            "resources": await client.list_resources(),
            "prompts": await client.list_prompts(),
        }
        guide = await client.call_tool("guide", {})
        hits = await client.call_tool(
            "search_reference", {"query": "grouped bar"}
        )
        top = hits.structured_content["result"][0]
        source = await client.call_tool(
            "get_reference", {"kind": top["kind"], "id": top["id"]}
        )
        code = source.content[0].text
        lint = await client.call_tool("lint", {"code": code})
        render = await client.call_tool(
            "render", {"code": code, "out_dir": str(tmp_path)}
        )
        seen |= {
            "guide": guide.content[0].text,
            "top": top,
            "lint": lint.structured_content["result"],
            "render": render,
            "code": code,
        }
        return seen


def test_a_stdio_session_lists_five_tools_and_each_answers(tmp_path) -> None:
    seen = asyncio.run(session(tmp_path))
    assert seen["tools"] == [
        "guide",
        "search_reference",
        "get_reference",
        "lint",
        "render",
    ]
    assert seen["resources"] == [] and seen["prompts"] == []
    assert "# dartwork-mpl" in str(seen["guide"])
    assert seen["top"]["id"].endswith("bar_grouped")
    assert seen["lint"] == []
    render = seen["render"]
    kinds = [block.type for block in render.content]
    assert kinds == ["image", "text"]
    payload = render.structured_content
    assert payload["report"]["status"] == "rendered"
    assert payload["source"] == seen["code"]
    assert (tmp_path / "figure.png").exists()
    assert json.loads((tmp_path / "manifest.json").read_text())["status"] == (
        "rendered"
    )


def test_main_serves_stdio_only(monkeypatch) -> None:
    from dartwork_mpl.mcp import main, server

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        server.server, "run", lambda **kw: calls.append(kw), raising=False
    )
    main()
    assert calls == [{"transport": "stdio", "show_banner": False}]


@pytest.mark.parametrize(
    ("query", "kind", "expected"),
    [
        ("slides", "preset", "presentation"),
        ("korean report", "preset", "report-kr"),
        ("teal", "color", "dc.teal"),
        ("figsize tuple", "rule", "figsize-direct"),
        ("heatmap", "template", "advanced/heatmap"),
    ],
)
def test_search_finds_each_kind(query, kind, expected) -> None:
    hits = library.search(query, kind)
    assert hits[0]["id"] == expected and {h["kind"] for h in hits} == {kind}


def test_get_returns_each_kind_and_refuses_unknown_ids() -> None:
    assert "dm.style.use" in library.get("template", "bar_grouped")
    preset = json.loads(library.get("preset", "report"))
    assert preset["styles"] == ["base", "font-report"] and preset["rcParams"]
    family = json.loads(library.get("color", "dc.teal"))
    assert family["kind"] == "sequential" and len(family["colors"]) == 10
    assert json.loads(library.get("color", "dc.teal4"))["hex"].startswith("#")
    assert json.loads(library.get("rule", "figsize-direct"))["fix"]
    for kind, ref in [
        ("preset", "nope"),
        ("rule", "nope"),
        ("template", "nope"),
    ]:
        with pytest.raises(ValueError):
            library.get(kind, ref)


def test_guide_reads_the_skill_or_one_topic() -> None:
    assert "Topics: colors" in library.guide(None)
    assert library.guide("layout").startswith("#")
    with pytest.raises(ValueError):
        library.guide("../../etc/passwd")
