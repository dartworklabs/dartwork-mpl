"""The five MCP tools, over stdio only.

Each tool is a few lines of wiring onto :mod:`.library` (reading) or
:mod:`.render` (running); the docstrings are what the agent sees.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from mcp.types import ContentBlock, TextContent

from . import library
from .model import Rendered, RenderRequest
from .render import render as run_render

if TYPE_CHECKING:
    from fastmcp.tools import ToolResult
else:
    try:
        from fastmcp.tools import ToolResult
    except ImportError:  # fastmcp 2.x keeps it in the tool module
        from fastmcp.tools.tool import ToolResult

server = FastMCP("dartwork-mpl")


@server.tool
def guide(topic: str | None = None) -> str:
    """Read the dartwork-mpl rules before writing plotting code.

    No topic: the skill (presets by purpose, sizing, layout, saving, data
    rules, edits, the review loop) with the list of topics. A topic
    (``layout``, ``colors``, ``editing``, ``korean``, ``recipes``,
    ``review``, ``anti-patterns``): that reference page.
    """
    return library.guide(topic)


@server.tool
def search_reference(
    query: str, kind: str | None = None
) -> list[dict[str, str]]:
    """Find a starting point: templates, style presets, colour families or lint rules.

    ``search_reference("grouped bar")`` ranks the grouped-bar templates
    first. ``kind`` narrows to ``template``, ``preset``, ``color`` or
    ``rule``. Each hit has ``kind``, ``id`` and a one-line ``summary``; pass
    the kind and id to ``get_reference``.
    """
    return library.search(query, kind)


@server.tool
def get_reference(kind: str, id: str) -> str:
    """Get one reference by the kind and id ``search_reference`` returned.

    ``template``: the runnable script (``bar_grouped``, ``advanced/bar``).
    ``preset``: its style stack and rcParams. ``color``: a family's designed
    steps (``dc.teal``) or one colour's hex (``dc.teal4``). ``rule``: a lint
    rule's message and fix.
    """
    return library.get(kind, id)


@server.tool
def lint(code: str) -> list[dict[str, object]]:
    """Check a script against the anti-pattern catalog without running it.

    Each finding has ``rule_id``, ``severity`` (critical, warning, info),
    ``line``, ``message`` and ``fix``. Fix every critical one; ``render``
    refuses to run code that has one.
    """
    return [asdict(f) for f in library.lint(code)]


@server.tool
def render(
    code: str,
    figure_var: str = "fig",
    timeout: float = 20.0,
    out_dir: str | None = None,
    inputs: list[str] | None = None,
) -> ToolResult:
    """Run a plotting script once and return the image, its check report and the bundle.

    The code runs in a fresh Python process with the Agg backend, an empty
    working directory and no inherited secrets, and is killed after
    ``timeout`` seconds (at most 120). It is NOT a sandbox: it runs with the
    server user's rights. A critical lint finding stops it before it runs.
    The figure bound to ``figure_var`` is saved (else pyplot's current one,
    noted). ``out_dir`` (default: a new temporary directory) receives
    ``figure.png``, ``figure.pdf``, ``source.py``, ``report.json`` and
    ``manifest.json``; ``inputs`` names data files the code reads (absolute
    paths), hashed into the manifest. Read ``report.findings``: fix WARNING,
    weigh INFO, then look at the image.
    """
    request = RenderRequest.parse(code, figure_var, timeout, out_dir, inputs)
    bundle, report, manifest = run_render(request, library.lint(request.code))
    payload = {
        "out_dir": str(bundle),
        "report": report.to_json(),
        "manifest": manifest.to_json(),
        "source": request.code,
    }
    content: list[ContentBlock] = []
    if isinstance(report.outcome, Rendered):
        content.append(Image(path=bundle / "figure.png").to_image_content())
    content.append(TextContent(type="text", text=json.dumps(payload, indent=2)))
    return ToolResult(content=content, structured_content=payload)
