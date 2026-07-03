"""Complete the ``validate_plot_data`` validator contract coverage.

#382 hardened the tool's dispatch/guard and the seven most common
validators. This finishes the set: the remaining eleven ``_validate_*``
helpers (twin_axis, bar_horizontal, bar_grouped, waterfall,
small_multiples, polar, plot_3d, violin, boxplot, histogram, contour),
each exercised on a valid payload and at least one issue branch — so the
full 18-template MCP data-shape contract is regression-guarded, not just
the popular subset.

Skips when ``fastmcp`` (optional dep) is absent, matching ``test_mcp.py``.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastmcp")

from dartwork_mpl.mcp import tools as _tools

_OK = "✅"


class TestSimpleShapeValidators:
    def test_bar_horizontal(self) -> None:
        assert _tools._validate_bar_horizontal(
            {"categories": ["a", "b"], "values": [1, 2]}
        ).startswith(_OK)
        assert "Length mismatch" in _tools._validate_bar_horizontal(
            {"categories": ["a", "b"], "values": [1]}
        )

    def test_bar_grouped(self) -> None:
        assert _tools._validate_bar_grouped(
            {"categories": ["a", "b"], "series": {"s1": [1, 2], "s2": [3, 4]}}
        ).startswith(_OK)
        assert "s1" in _tools._validate_bar_grouped(
            {"categories": ["a", "b"], "series": {"s1": [1]}}
        )

    def test_waterfall(self) -> None:
        assert _tools._validate_waterfall(
            {"labels": ["a", "b"], "deltas": [1, -1]}
        ).startswith(_OK)
        assert "Length mismatch" in _tools._validate_waterfall(
            {"labels": ["a", "b"], "deltas": [1]}
        )
        # optional is_total must align with deltas
        assert "is_total" in _tools._validate_waterfall(
            {"labels": ["a", "b"], "deltas": [1, 2], "is_total": [True]}
        )

    def test_polar_list_and_dict(self) -> None:
        assert _tools._validate_polar(
            {"categories": ["a", "b", "c"], "values": [1, 2, 3]}
        ).startswith(_OK)
        assert _tools._validate_polar(
            {"categories": ["a", "b"], "values": {"s1": [1, 2]}}
        ).startswith(_OK)
        assert "Length mismatch" in _tools._validate_polar(
            {"categories": ["a", "b"], "values": [1]}
        )
        assert "s1" in _tools._validate_polar(
            {"categories": ["a", "b"], "values": {"s1": [1]}}
        )


class TestTwinAxis:
    def test_valid(self) -> None:
        out = _tools._validate_twin_axis(
            {
                "x": [1, 2, 3],
                "left": {"y": [1, 2, 3], "label": "L"},
                "right": {"y": [4, 5, 6], "label": "R"},
            }
        )
        assert out.startswith(_OK)

    def test_missing_side(self) -> None:
        out = _tools._validate_twin_axis(
            {"x": [1, 2], "left": {"y": [1, 2], "label": "L"}}
        )
        assert "Missing 'right'" in out

    def test_y_length_mismatch(self) -> None:
        out = _tools._validate_twin_axis(
            {
                "x": [1, 2, 3],
                "left": {"y": [1, 2], "label": "L"},
                "right": {"y": [4, 5, 6], "label": "R"},
            }
        )
        assert "length" in out.lower()

    def test_non_dict_payload(self) -> None:
        assert "JSON object" in _tools._validate_twin_axis([1, 2, 3])


class TestSmallMultiples:
    def test_valid(self) -> None:
        out = _tools._validate_small_multiples(
            {"panels": [{"label": "p", "x": [1, 2], "y": [3, 4]}]}
        )
        assert out.startswith(_OK)

    def test_panel_length_mismatch(self) -> None:
        out = _tools._validate_small_multiples(
            {"panels": [{"label": "p", "x": [1, 2, 3], "y": [4]}]}
        )
        assert "length mismatch" in out.lower()

    def test_panels_not_a_list(self) -> None:
        assert "'panels' must be a list" in _tools._validate_small_multiples(
            {"panels": {"not": "a list"}}
        )

    def test_panel_missing_axis(self) -> None:
        out = _tools._validate_small_multiples(
            {"panels": [{"label": "p", "x": [1, 2]}]}
        )
        assert "missing 'x' or 'y'" in out.lower()


class TestPlot3D:
    def test_scatter_valid(self) -> None:
        out = _tools._validate_plot_3d({"x": [1, 2], "y": [3, 4], "z": [5, 6]})
        assert out.startswith(_OK)

    def test_surface_valid(self) -> None:
        out = _tools._validate_plot_3d(
            {"x": [1, 2], "y": [3, 4, 5], "z": [[1, 2], [3, 4], [5, 6]]}
        )
        assert out.startswith(_OK)

    def test_missing_key(self) -> None:
        assert "Missing 'z'" in _tools._validate_plot_3d({"x": [1], "y": [2]})

    def test_scatter_length_mismatch(self) -> None:
        out = _tools._validate_plot_3d({"x": [1, 2], "y": [3], "z": [5, 6]})
        assert not out.startswith(_OK)

    def test_surface_row_mismatch(self) -> None:
        out = _tools._validate_plot_3d(
            {"x": [1, 2], "y": [3, 4], "z": [[1, 2], [3, 4], [5, 6]]}
        )
        assert "Surface mode" in out


class TestGroupedSampleValidators:
    def test_violin_valid_pair_and_series(self) -> None:
        assert _tools._validate_violin(
            {"groups": ["a", "b"], "values": [[1, 2], [3, 4]]}
        ).startswith(_OK)
        assert _tools._validate_violin({"series": {"a": [1, 2, 3]}}).startswith(
            _OK
        )

    def test_violin_needs_a_shape(self) -> None:
        assert "Need either" in _tools._validate_violin({"foo": 1})

    def test_violin_group_value_mismatch(self) -> None:
        out = _tools._validate_violin(
            {"groups": ["a", "b"], "values": [[1, 2]]}
        )
        assert "Length mismatch" in out

    def test_violin_non_numeric_sample(self) -> None:
        out = _tools._validate_violin({"groups": ["a"], "values": [["x", "y"]]})
        assert "numeric" in out.lower()

    def test_boxplot_valid_and_empty_inner(self) -> None:
        assert _tools._validate_boxplot(
            {"groups": ["a"], "values": [[1, 2, 3]]}
        ).startswith(_OK)
        assert "at least one sample" in _tools._validate_boxplot(
            {"groups": ["a"], "values": [[]]}
        )


class TestHistogramContour:
    def test_histogram_valid(self) -> None:
        assert _tools._validate_histogram({"values": [1, 2, 3, 4]}).startswith(
            _OK
        )

    def test_histogram_missing_values(self) -> None:
        assert "Missing 'values'" in _tools._validate_histogram({})

    def test_histogram_bad_bins(self) -> None:
        assert ">= 1" in _tools._validate_histogram(
            {"values": [1, 2], "bins": 0}
        )
        assert "two edges" in _tools._validate_histogram(
            {"values": [1, 2], "bins": [0.5]}
        )

    def test_contour_valid(self) -> None:
        assert _tools._validate_contour({"Z": [[1, 2], [3, 4]]}).startswith(_OK)

    def test_contour_missing_z(self) -> None:
        assert "Missing 'Z'" in _tools._validate_contour({})

    def test_contour_not_2d(self) -> None:
        assert "2-D array" in _tools._validate_contour({"Z": [1, 2, 3]})

    def test_contour_ragged_rows(self) -> None:
        assert "equal length" in _tools._validate_contour({"Z": [[1, 2], [3]]})
