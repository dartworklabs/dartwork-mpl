"""Complete the ``validate_plot_data`` validator contract coverage.

#382 hardened the tool's dispatch/guard and the seven most common
validators. This finishes the set: the remaining eleven ``parse_*``
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

from dartwork_mpl.mcp.plot_data import validators as _validators
from dartwork_mpl.mcp.plot_data.validate import reply

_OK = "✅"


def _message(plot_type: str):
    """Parse with ``plot_type``'s parser, then render the tool's reply text."""
    parse = _validators.PARSERS[plot_type]
    return lambda data: reply(plot_type, parse(data))


class TestSimpleShapeValidators:
    """Shape checks for bar, grouped bar, waterfall and polar payloads."""

    def test_bar_horizontal(self) -> None:
        assert _message("bar_horizontal")(
            {"categories": ["a", "b"], "values": [1, 2]}
        ).startswith(_OK)
        assert "Length mismatch" in _message("bar_horizontal")(
            {"categories": ["a", "b"], "values": [1]}
        )

    def test_bar_grouped(self) -> None:
        assert _message("bar_grouped")(
            {"categories": ["a", "b"], "series": {"s1": [1, 2], "s2": [3, 4]}}
        ).startswith(_OK)
        assert "s1" in _message("bar_grouped")(
            {"categories": ["a", "b"], "series": {"s1": [1]}}
        )

    def test_waterfall(self) -> None:
        assert _message("waterfall")(
            {"labels": ["a", "b"], "deltas": [1, -1]}
        ).startswith(_OK)
        assert "Length mismatch" in _message("waterfall")(
            {"labels": ["a", "b"], "deltas": [1]}
        )
        # optional is_total must align with deltas
        assert "is_total" in _message("waterfall")(
            {"labels": ["a", "b"], "deltas": [1, 2], "is_total": [True]}
        )

    def test_polar_list_and_dict(self) -> None:
        assert _message("polar")(
            {"categories": ["a", "b", "c"], "values": [1, 2, 3]}
        ).startswith(_OK)
        assert _message("polar")(
            {"categories": ["a", "b"], "values": {"s1": [1, 2]}}
        ).startswith(_OK)
        assert "Length mismatch" in _message("polar")(
            {"categories": ["a", "b"], "values": [1]}
        )
        assert "s1" in _message("polar")(
            {"categories": ["a", "b"], "values": {"s1": [1]}}
        )


class TestTwinAxis:
    """Twin-axis payloads need both sides with y series matching x in length."""

    def test_valid(self) -> None:
        out = _message("twin_axis")(
            {
                "x": [1, 2, 3],
                "left": {"y": [1, 2, 3], "label": "L"},
                "right": {"y": [4, 5, 6], "label": "R"},
            }
        )
        assert out.startswith(_OK)

    def test_missing_side(self) -> None:
        out = _message("twin_axis")(
            {"x": [1, 2], "left": {"y": [1, 2], "label": "L"}}
        )
        assert "Missing 'right'" in out

    def test_y_length_mismatch(self) -> None:
        out = _message("twin_axis")(
            {
                "x": [1, 2, 3],
                "left": {"y": [1, 2], "label": "L"},
                "right": {"y": [4, 5, 6], "label": "R"},
            }
        )
        assert "length" in out.lower()

    def test_non_dict_payload(self) -> None:
        assert "JSON object" in _message("twin_axis")([1, 2, 3])


class TestSmallMultiples:
    """Small-multiples payloads need a list of complete, equal-length panels."""

    def test_valid(self) -> None:
        out = _message("small_multiples")(
            {"panels": [{"label": "p", "x": [1, 2], "y": [3, 4]}]}
        )
        assert out.startswith(_OK)

    def test_panel_length_mismatch(self) -> None:
        out = _message("small_multiples")(
            {"panels": [{"label": "p", "x": [1, 2, 3], "y": [4]}]}
        )
        assert "length mismatch" in out.lower()

    def test_panels_not_a_list(self) -> None:
        assert "'panels' must be a list" in _message("small_multiples")(
            {"panels": {"not": "a list"}}
        )

    def test_panel_missing_axis(self) -> None:
        out = _message("small_multiples")(
            {"panels": [{"label": "p", "x": [1, 2]}]}
        )
        assert "missing 'x' or 'y'" in out.lower()


class TestPlot3D:
    """3D scatter and surface payloads: required keys and consistent dimensions."""

    def test_scatter_valid(self) -> None:
        out = _message("plot_3d")({"x": [1, 2], "y": [3, 4], "z": [5, 6]})
        assert out.startswith(_OK)

    def test_surface_valid(self) -> None:
        out = _message("plot_3d")(
            {"x": [1, 2], "y": [3, 4, 5], "z": [[1, 2], [3, 4], [5, 6]]}
        )
        assert out.startswith(_OK)

    def test_missing_key(self) -> None:
        assert "Missing 'z'" in _message("plot_3d")({"x": [1], "y": [2]})

    def test_scatter_length_mismatch(self) -> None:
        out = _message("plot_3d")({"x": [1, 2], "y": [3], "z": [5, 6]})
        assert not out.startswith(_OK)

    def test_surface_row_mismatch(self) -> None:
        out = _message("plot_3d")(
            {"x": [1, 2], "y": [3, 4], "z": [[1, 2], [3, 4], [5, 6]]}
        )
        assert "Surface mode" in out


class TestGroupedSampleValidators:
    """Violin and boxplot payloads: accepted shapes, group/value agreement, numeric samples."""

    def test_violin_valid_pair_and_series(self) -> None:
        assert _message("violin")(
            {"groups": ["a", "b"], "values": [[1, 2], [3, 4]]}
        ).startswith(_OK)
        assert _message("violin")({"series": {"a": [1, 2, 3]}}).startswith(_OK)

    def test_violin_needs_a_shape(self) -> None:
        assert "Need either" in _message("violin")({"foo": 1})

    def test_violin_group_value_mismatch(self) -> None:
        out = _message("violin")({"groups": ["a", "b"], "values": [[1, 2]]})
        assert "Length mismatch" in out

    def test_violin_non_numeric_sample(self) -> None:
        out = _message("violin")({"groups": ["a"], "values": [["x", "y"]]})
        assert "numeric" in out.lower()

    def test_boxplot_valid_and_empty_inner(self) -> None:
        assert _message("boxplot")(
            {"groups": ["a"], "values": [[1, 2, 3]]}
        ).startswith(_OK)
        assert "at least one sample" in _message("boxplot")(
            {"groups": ["a"], "values": [[]]}
        )


class TestHistogramContour:
    """Histogram values and bins, and contour grids that must be rectangular 2D."""

    def test_histogram_valid(self) -> None:
        assert _message("histogram")({"values": [1, 2, 3, 4]}).startswith(_OK)

    def test_histogram_missing_values(self) -> None:
        assert "Missing 'values'" in _message("histogram")({})

    def test_histogram_bad_bins(self) -> None:
        assert ">= 1" in _message("histogram")({"values": [1, 2], "bins": 0})
        assert "two edges" in _message("histogram")(
            {"values": [1, 2], "bins": [0.5]}
        )

    def test_contour_valid(self) -> None:
        assert _message("contour")({"Z": [[1, 2], [3, 4]]}).startswith(_OK)

    def test_contour_missing_z(self) -> None:
        assert "Missing 'Z'" in _message("contour")({})

    def test_contour_not_2d(self) -> None:
        assert "2-D array" in _message("contour")({"Z": [1, 2, 3]})

    def test_contour_ragged_rows(self) -> None:
        assert "equal length" in _message("contour")({"Z": [[1, 2], [3]]})


class TestValidators:
    """Individual ``parse_*`` parsers' issue branches."""

    def test_tornado_valid_and_mismatch(self) -> None:
        assert _message("tornado")(
            {"categories": ["a"], "positive": [1]}
        ).startswith("✅")
        assert "Length mismatch" in _message("tornado")(
            {"categories": ["a", "b"], "positive": [1]}
        )

    def test_bar_missing_and_mismatch(self) -> None:
        assert "Missing 'values'" in _message("bar")({"categories": ["a"]})
        assert "Length mismatch" in _message("bar")(
            {"categories": ["a", "b"], "values": [1]}
        )

    def test_heatmap_requires_2d(self) -> None:
        assert "2D array" in _message("heatmap")({"matrix": [1, 2, 3]})
        assert _message("heatmap")({"matrix": [[1, 2], [3, 4]]}).startswith(
            "✅"
        )

    def test_stacked_bar_series_length(self) -> None:
        out = _message("stacked_bar")(
            {"categories": ["a", "b"], "series": {"s1": [1]}}
        )
        assert "s1" in out and "length" in out.lower()

    def test_pie_length_mismatch(self) -> None:
        assert "Length mismatch" in _message("pie")(
            {"labels": ["a", "b"], "sizes": [1]}
        )

    def test_line_needs_y_or_series(self) -> None:
        out = _message("line")({"x": [1, 2, 3]})
        assert "y" in out.lower() and "series" in out.lower()


class TestVerdicts:
    """Parsers return one verdict per payload and never raise for JSON input."""

    def test_invalid_requires_an_issue(self) -> None:
        with pytest.raises(ValueError, match="at least one issue"):
            _validators.Invalid(())

    def test_verdict_kinds(self) -> None:
        assert _validators.parse_bar(
            {"categories": ["a"], "values": [1]}
        ) == _validators.Parsed("bar plot")
        assert _validators.parse_bar({}) == _validators.Invalid(
            (
                "Missing 'categories' key (list of category labels).",
                "Missing 'values' key (list of numeric values).",
            )
        )
        malformed = _validators.parse_bar({"categories": 5, "values": [1]})
        assert malformed == _validators.Malformed(
            "TypeError", "object of type 'int' has no len()"
        )

    @pytest.mark.parametrize(
        "payload", [None, True, 3, 1.5, "xyz", [], ["x", "y"], {}, {"x": 1}]
    )
    def test_every_parser_is_total(self, payload: object) -> None:
        for parse in _validators.PARSERS.values():
            assert isinstance(
                parse(payload),
                (
                    _validators.Parsed,
                    _validators.Invalid,
                    _validators.Malformed,
                ),
            )
