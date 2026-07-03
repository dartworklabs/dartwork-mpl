"""Smoke tests for the heavy render / exec MCP tools.

``render_template`` / ``validate_generated_plot`` / ``render_template_advanced``
each spawn a subprocess and render (or exec) a *real* figure — the
deepest, most expensive tools, previously untested end-to-end.
``compose_layered_plot`` is a guidance tool (returns template + layer
checklist, no render). These exercise the happy path plus the structured
error statuses so the whole render/validate contract is guarded, accepting
the subprocess cost.

Skips when ``fastmcp`` (optional dep) is absent, matching ``test_mcp.py``.
"""

from __future__ import annotations

import base64
import os
from unittest.mock import MagicMock

import pytest

pytest.importorskip("fastmcp")

from dartwork_mpl.mcp.tools import register_tools

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_CLEAN_CODE = """\
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import dartwork_mpl as dm

dm.style.use("scientific")
fig, ax = plt.subplots(figsize=dm.figsize("13cm", "standard"))
ax.plot([1, 2, 3], [1, 4, 9])
ax.set_xlabel("x")
ax.set_ylabel("y")
dm.simple_layout(fig)
"""


def _tools_map() -> dict:
    captured: dict = {}

    def fake_tool(*_args, **_kwargs):
        def inner(fn):
            captured[fn.__name__] = fn
            return fn

        return inner

    mock = MagicMock()
    mock.tool = fake_tool
    register_tools(mock)
    return captured


class TestRenderTemplate:
    def setup_method(self) -> None:
        self.render = _tools_map()["render_template"]

    def test_renders_bar_to_base64_png(self) -> None:
        out = self.render("bar")
        assert out["status"] == "ok", out.get("stderr")
        png = base64.b64decode(out["png_base64"])
        assert png[:8] == _PNG_MAGIC

    def test_path_format_writes_a_file(self) -> None:
        out = self.render("bar", return_format="path")
        assert out["status"] == "ok", out.get("stderr")
        assert out["png_path"] and os.path.exists(out["png_path"])
        assert out["png_base64"] is None


class TestValidateGeneratedPlot:
    def setup_method(self) -> None:
        self.validate = _tools_map()["validate_generated_plot"]

    def test_clean_code_renders_and_validates(self) -> None:
        out = self.validate(_CLEAN_CODE)
        assert out["status"] == "ok", out.get("stderr")
        assert isinstance(out["visual_warnings"], list)

    def test_critical_lint_short_circuits(self) -> None:
        # A raw figsize tuple is a critical anti-pattern — the lint pass
        # must block before the code is ever executed.
        out = self.validate(
            "import matplotlib.pyplot as plt\n"
            "fig = plt.figure(figsize=(6, 4))\n"
        )
        assert out["status"] == "lint_blocked"
        assert out["lint"]

    def test_code_without_figure_reported(self) -> None:
        out = self.validate("x = 1 + 1\n")
        assert out["status"] == "no_figure"


class TestComposeLayeredPlot:
    def setup_method(self) -> None:
        self.compose = _tools_map()["compose_layered_plot"]

    def test_ok_returns_code_and_layers(self) -> None:
        out = self.compose("bar", layers=["reference_line"])
        assert out["status"] == "ok"
        assert out["code"]
        assert isinstance(out["layers"], list)

    def test_invalid_tier(self) -> None:
        assert self.compose("bar", tier="bogus")["status"] == "invalid_tier"

    def test_unknown_template(self) -> None:
        assert (
            self.compose("definitely_not_a_template")["status"]
            == "unknown_template"
        )


class TestRenderTemplateAdvanced:
    def setup_method(self) -> None:
        self.render_adv = _tools_map()["render_template_advanced"]

    def test_renders_or_falls_back(self) -> None:
        out = self.render_adv("bar")
        assert out["status"] in ("ok", "fell_back"), out.get("stderr")

    def test_unknown_template(self) -> None:
        out = self.render_adv("definitely_not_a_template")
        assert out["status"] == "unknown_template"
