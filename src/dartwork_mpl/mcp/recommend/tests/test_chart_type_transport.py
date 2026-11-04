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
            "rationale": "x=categorical, y=continuous, n_points=50, n_series=3 → recommended: 'bar_grouped' (recommender semantic: 'grouped_bar' — rendered with the 'bar_grouped' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add reference lines, value labels, narrative title, and source footnote — copy the advanced version when you want the agent's generated plot to read like a finished report figure.",
        },
    ),
    (
        {"x_type": "categorical"},
        {
            "recommended": "bar",
            "basic_template_uri": "dartwork-mpl://templates/bar",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/bar",
            "rationale": "x=categorical, y=None, n_points=50, n_series=1 → recommended: 'bar' (recommender semantic: 'count_bar' — rendered with the 'bar' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add reference lines, value labels, narrative title, and source footnote — copy the advanced version when you want the agent's generated plot to read like a finished report figure.",
        },
    ),
    (
        {"x_type": "temporal", "y_type": "continuous", "n_points": 19},
        {
            "recommended": "line",
            "basic_template_uri": "dartwork-mpl://templates/line",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/line",
            "rationale": "x=temporal, y=continuous, n_points=19, n_series=1 → recommended: 'line' (recommender semantic: 'bar_line' — rendered with the 'line' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add reference lines, value labels, narrative title, and source footnote — copy the advanced version when you want the agent's generated plot to read like a finished report figure.",
        },
    ),
    (
        {"x_type": "temporal", "y_type": "continuous", "n_series": 3},
        {
            "recommended": "line",
            "basic_template_uri": "dartwork-mpl://templates/line",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/line",
            "rationale": "x=temporal, y=continuous, n_points=50, n_series=3 → recommended: 'line' (recommender semantic: 'multi_line' — rendered with the 'line' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add reference lines, value labels, narrative title, and source footnote — copy the advanced version when you want the agent's generated plot to read like a finished report figure.",
        },
    ),
    (
        {"x_type": "continuous", "y_type": "continuous", "n_points": 50},
        {
            "recommended": "scatter",
            "basic_template_uri": "dartwork-mpl://templates/scatter",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/scatter",
            "rationale": "x=continuous, y=continuous, n_points=50, n_series=1 → recommended: 'scatter' (recommender semantic: 'scatter_density' — rendered with the 'scatter' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add reference lines, value labels, narrative title, and source footnote — copy the advanced version when you want the agent's generated plot to read like a finished report figure.",
        },
    ),
    (
        {"x_type": "continuous", "y_type": "continuous", "n_points": 500},
        {
            "recommended": "scatter",
            "basic_template_uri": "dartwork-mpl://templates/scatter",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/scatter",
            "rationale": "x=continuous, y=continuous, n_points=500, n_series=1 → recommended: 'scatter' (recommender semantic: 'hexbin' — rendered with the 'scatter' template). Tier-1 templates show the minimal API call; tier-2 (advanced) templates add reference lines, value labels, narrative title, and source footnote — copy the advanced version when you want the agent's generated plot to read like a finished report figure.",
        },
    ),
    (
        {"x_type": "continuous"},
        {
            "recommended": "histogram",
            "basic_template_uri": "dartwork-mpl://templates/histogram",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/histogram",
            "rationale": "x=continuous, y=None, n_points=50, n_series=1 → recommended: 'histogram'. Tier-1 templates show the minimal API call; tier-2 (advanced) templates add reference lines, value labels, narrative title, and source footnote — copy the advanced version when you want the agent's generated plot to read like a finished report figure.",
        },
    ),
    (
        {"x_type": "weird", "y_type": "continuous"},
        {
            "recommended": "scatter",
            "basic_template_uri": "dartwork-mpl://templates/scatter",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/scatter",
            "rationale": "x=weird, y=continuous, n_points=50, n_series=1 → recommended: 'scatter'. Tier-1 templates show the minimal API call; tier-2 (advanced) templates add reference lines, value labels, narrative title, and source footnote — copy the advanced version when you want the agent's generated plot to read like a finished report figure.",
        },
    ),
    (
        {"x_type": "weird"},
        {
            "recommended": "line",
            "basic_template_uri": "dartwork-mpl://templates/line",
            "advanced_template_uri": "dartwork-mpl://templates/advanced/line",
            "rationale": "x=weird, y=None, n_points=50, n_series=1 → recommended: 'line'. Tier-1 templates show the minimal API call; tier-2 (advanced) templates add reference lines, value labels, narrative title, and source footnote — copy the advanced version when you want the agent's generated plot to read like a finished report figure.",
        },
    ),
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
