"""Real MCP replies preserve normalization, serialized values and resource links."""

import asyncio
import json

import pytest

pytest.importorskip("fastmcp")
from fastmcp import Client

from dartwork_mpl.mcp.server import mcp

CASES = [
    (
        {"x_type": "categorical", "y_type": "continuous", "n_series": 3},
        {
            "recommended": "bar_grouped",
            "basic_template_uri": "dartwork-mpl://templates/bar_grouped",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/bar_grouped",
            "rationale": "x=categorical, y=continuous, n_points=50, n_series=3 → recommended: 'bar_grouped' (recommender semantic: 'grouped_bar' — rendered with the 'bar_grouped' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add realistic data, reference lines and value labels. Neither tier draws a title, subtitle or source note: add one only when the user asks (dm.add_note for a source line).",
        },
    ),
    (
        {"x_type": "categorical"},
        {
            "recommended": "bar",
            "basic_template_uri": "dartwork-mpl://templates/bar",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/bar",
            "rationale": "x=categorical, y=None, n_points=50, n_series=1 → recommended: 'bar' (recommender semantic: 'count_bar' — rendered with the 'bar' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add realistic data, reference lines and value labels. Neither tier draws a title, subtitle or source note: add one only when the user asks (dm.add_note for a source line).",
        },
    ),
    (
        {"x_type": "temporal", "y_type": "continuous", "n_points": 19},
        {
            "recommended": "line",
            "basic_template_uri": "dartwork-mpl://templates/line",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/line",
            "rationale": "x=temporal, y=continuous, n_points=19, n_series=1 → recommended: 'line' (recommender semantic: 'bar_line' — rendered with the 'line' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add realistic data, reference lines and value labels. Neither tier draws a title, subtitle or source note: add one only when the user asks (dm.add_note for a source line).",
        },
    ),
    (
        {"x_type": "temporal", "y_type": "continuous", "n_series": 3},
        {
            "recommended": "line",
            "basic_template_uri": "dartwork-mpl://templates/line",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/line",
            "rationale": "x=temporal, y=continuous, n_points=50, n_series=3 → recommended: 'line' (recommender semantic: 'multi_line' — rendered with the 'line' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add realistic data, reference lines and value labels. Neither tier draws a title, subtitle or source note: add one only when the user asks (dm.add_note for a source line).",
        },
    ),
    (
        {"x_type": "continuous", "y_type": "continuous", "n_points": 50},
        {
            "recommended": "scatter",
            "basic_template_uri": "dartwork-mpl://templates/scatter",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/scatter",
            "rationale": "x=continuous, y=continuous, n_points=50, n_series=1 → recommended: 'scatter' (recommender semantic: 'scatter_density' — rendered with the 'scatter' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add realistic data, reference lines and value labels. Neither tier draws a title, subtitle or source note: add one only when the user asks (dm.add_note for a source line).",
        },
    ),
    (
        {"x_type": "continuous", "y_type": "continuous", "n_points": 500},
        {
            "recommended": "scatter",
            "basic_template_uri": "dartwork-mpl://templates/scatter",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/scatter",
            "rationale": "x=continuous, y=continuous, n_points=500, n_series=1 → recommended: 'scatter' (recommender semantic: 'hexbin' — rendered with the 'scatter' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add realistic data, reference lines and value labels. Neither tier draws a title, subtitle or source note: add one only when the user asks (dm.add_note for a source line).",
        },
    ),
    (
        {"x_type": "continuous"},
        {
            "recommended": "histogram",
            "basic_template_uri": "dartwork-mpl://templates/histogram",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/histogram",
            "rationale": "x=continuous, y=None, n_points=50, n_series=1 → recommended: 'histogram'. Tier-1 templates show the minimal API call; tier-2 (advanced) templates add realistic data, reference lines and value labels. Neither tier draws a title, subtitle or source note: add one only when the user asks (dm.add_note for a source line).",
        },
    ),
]

#: Values outside the tool docstring's documented sets. The schema types both
#: arguments as plain strings, so these reach the recommender rather than being
#: refused by the schema. Two of these used to be pinned above as golden
#: replies — ``{"x_type": "weird"}`` came back as a ``line`` recommendation
#: with a template URI (#501 task 8).
REJECTED = [
    ({"x_type": "weird", "y_type": "continuous"}, "x_type"),
    ({"x_type": "weird"}, "x_type"),
    ({"x_type": "catagorical", "y_type": "continuous"}, "x_type"),
    ({"x_type": "CONTINUOUS"}, "x_type"),
    ({"x_type": "continuous", "y_type": "counts"}, "y_type"),
    ({"x_type": "continuous", "y_type": ""}, "y_type"),
]


@pytest.mark.parametrize(("arguments", "expected"), CASES)
def test_client_normalizes_semantics_and_reads_resources(arguments, expected):
    """Measured semantic mappings and defaults survive real transport encoding."""

    async def probe():
        """Read advertised resources without executing template code."""
        async with Client(mcp) as client:
            result = await client.call_tool("suggest_chart_type", arguments)
            assert not result.is_error
            assert result.structured_content == expected
            assert len(result.content) == 1
            assert json.loads(result.content[0].text) == expected
            for key in ("basic_template_uri", "advanced_template_uri"):
                if expected[key] is not None:
                    resources = await client.read_resource(expected[key])
                    assert resources and all(item.text for item in resources)

    asyncio.run(probe())


@pytest.mark.parametrize(("arguments", "argument"), REJECTED)
def test_client_rejects_undocumented_selection(arguments, argument):
    """An undocumented selection comes back as an error, not a recommendation.

    The reply must name the offending argument and the permitted values, and
    must not carry a template URI: the old behaviour answered a different
    question than the caller asked.
    """

    async def probe():
        """Call the real tool and read the stable error status and text."""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "suggest_chart_type", arguments, raise_on_error=False
            )
            assert result.is_error
            text = " ".join(item.text for item in result.content)
            assert argument in text
            assert "must be one of" in text
            assert "dartwork-mpl://templates/" not in text

    asyncio.run(probe())


def test_client_rejects_missing_required_x_type():
    """Schema rejection identifies the required field without dependency repr goldens."""

    async def probe():
        """Inspect the real Client's stable error status and diagnosis."""
        async with Client(mcp) as client:
            result = await client.call_tool(
                "suggest_chart_type", {}, raise_on_error=False
            )
            assert result.is_error
            text = " ".join(item.text for item in result.content).lower()
            assert "x_type" in text
            assert "required" in text

    asyncio.run(probe())
