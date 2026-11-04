"""Historical recommendation aliases remain usable without optional transport."""

import importlib.util
import inspect
import os
import pickle
import subprocess
import sys
from pathlib import Path

import dartwork_mpl as dm
from dartwork_mpl import helpers
from dartwork_mpl.helpers import quality


def test_native_owner_preserves_historical_callable():
    """A direct native import preserves old aliases, annotations and pickle lookup."""
    spec = importlib.util.find_spec("dartwork_mpl.recommend")
    assert spec is not None and spec.origin is not None, "native owner missing"
    from dartwork_mpl.recommend import suggest_chart_type

    assert suggest_chart_type is dm.suggest_chart_type
    assert suggest_chart_type is helpers.suggest_chart_type
    assert suggest_chart_type is quality.suggest_chart_type
    assert suggest_chart_type.__module__ == "dartwork_mpl.helpers.quality"
    assert suggest_chart_type.__qualname__ == "suggest_chart_type"
    assert suggest_chart_type.__defaults__ == (1,)
    assert suggest_chart_type.__kwdefaults__ is None
    assert suggest_chart_type.__annotations__ == {
        "x_type": "str",
        "y_type": "str | None",
        "n_points": "int",
        "n_series": "int",
        "return": "str",
    }
    assert str(inspect.signature(suggest_chart_type)) == (
        "(x_type: 'str', y_type: 'str | None', n_points: 'int', "
        "n_series: 'int' = 1) -> 'str'"
    )
    assert pickle.loads(HISTORICAL_PICKLE) is suggest_chart_type


def test_native_execution_with_optional_transport_blocked(tmp_path):
    """Fresh direct-owner imports and calls never need MCP or FastMCP."""
    code = """
import importlib.abc
import sys
sys.path.insert(0, sys.argv[1])
class BlockTransport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'fastmcp' or fullname.startswith('fastmcp.') or fullname == 'dartwork_mpl.mcp' or fullname.startswith('dartwork_mpl.mcp.'):
            raise AssertionError('optional transport loaded: ' + fullname)
sys.meta_path.insert(0, BlockTransport())
import importlib.util
spec = importlib.util.find_spec('dartwork_mpl.recommend')
assert spec is not None and spec.origin is not None, 'native owner missing'
from dartwork_mpl.recommend import suggest_chart_type
assert suggest_chart_type('continuous', 'continuous', 500) == 'hexbin'
assert suggest_chart_type('categorical', None, 5) == 'count_bar'
assert not any(n == 'fastmcp' or n.startswith('dartwork_mpl.mcp') for n in sys.modules)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            code,
            str(Path(dm.__file__).parents[1]),
        ],
        cwd=tmp_path,
        env=dict(os.environ),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


HISTORICAL_PICKLE = b"\x80\x04\x957\x00\x00\x00\x00\x00\x00\x00\x8c\x1cdartwork_mpl.helpers.quality\x94\x8c\x12suggest_chart_type\x94\x93\x94."
