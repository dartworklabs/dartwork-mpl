"""Independent v1 fixtures pin scoped diagnostics and reviewable proposals."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from dartwork_mpl.mcp.plot_data import (
    build_data_repair_report,
    serialize_data_repair_report,
)

CASES = json.loads(
    (Path(__file__).parent / "fixtures/reports.json").read_text()
)


def report(plot_type: str, raw: str, *, recognized: bool = True) -> dict:
    """Decode the public string as exact decimals, without float rounding."""
    return json.loads(
        serialize_data_repair_report(
            build_data_repair_report(plot_type, raw, recognized=recognized)
        ),
        parse_float=Decimal,
        parse_int=Decimal,
    )


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_independent_report_examples(case: dict) -> None:
    """Approved examples and shape cases retain exact original and paths."""
    actual = report(case["plot_type"], case["raw"])
    assert actual["version"] == 1
    assert actual["plot_type"] == case["plot_type"].lower()
    assert actual["status"] == case["status"]
    assert actual["recognized"] is actual["supported"] is True
    assert actual["original"] == {
        "raw_json": case["raw"],
        "data": json.loads(case["raw"], parse_float=Decimal, parse_int=Decimal),
    }
    assert [[i["code"], i["path"]] for i in actual["issues"]] == case["issues"]
    assert actual["scope"]["validity"] == "declared_fields_only"
    assert actual["scope"]["unvalidated_paths"] == case.get(
        "unvalidated_paths", []
    )
    assert actual["effects"] == "none"
    assert actual["requires_review"] is (case["status"] == "proposal")
    for issue in actual["issues"]:
        assert issue["message"] and issue["action"]
    if "changes" in case:
        assert actual["changes"] == case["changes"]
    if "exact_issue" in case:
        assert actual["issues"] == [case["exact_issue"]]
    if "related_paths" in case:
        assert actual["issues"][0]["related_paths"] == case["related_paths"]
        assert actual["issues"][0]["observed"] == case["observed"]
    if "candidate" in case:
        assert actual["candidate"] == case["candidate"]
    if "change_paths" in case:
        assert [c["path"] for c in actual["changes"]] == case["change_paths"]
        assert actual["candidate"]["valid"] is case["candidate_valid"]
        assert [
            [i["code"], i["path"]]
            for i in actual["candidate"]["remaining_issues"]
        ] == case["remaining"]
    if not actual["changes"]:
        assert "candidate" not in actual


@pytest.mark.parametrize(
    "value",
    [
        "-0",
        "-0.0e5",
        " 1",
        "01",
        "1e309",
        "1e-400",
        "9007199254740992",
        "0.10000000000000001",
        "1.",
        "+1",
        "1,000",
    ],
)
def test_unsafe_strings_remain_original_without_proposals(value: str) -> None:
    """Grammar, range, decimal equality and portable-integer guards are observable."""
    actual = report("histogram", json.dumps({"values": [value]}))
    assert actual["status"] == "needs_input"
    assert actual["issues"][0]["code"] == "unsafe_conversion"
    assert actual["original"]["data"]["values"] == [value]
    assert actual["changes"] == []
    assert "candidate" not in actual


@pytest.mark.parametrize(
    "value", ["0", "-1", "1e2", "2.5", "0.1", "9007199254740991"]
)
def test_safe_numeric_representations_require_review(value: str) -> None:
    """Only numeric representation changes receive explicit review proposals."""
    actual = report("histogram", json.dumps({"values": [value]}))
    assert actual["status"] == "proposal"
    assert actual["changes"][0]["before"] == value
    assert actual["changes"][0]["after"] == Decimal(value)
    assert actual["changes"][0]["requires_review"] is True
    assert actual["candidate"]["valid"] is True
    assert "lossless" not in actual["changes"][0]["reason"].lower()


def test_out_of_range_numbers_and_unknown_metadata_keep_exact_values() -> None:
    """Original and detached candidate preserve values that binary64 cannot carry."""
    raw = '{"x":[1e309,"2"],"y":[3,4],"a/b~":{"big":1e309,"precise":1.0000000000000000000001}}'
    actual = report("scatter", raw)
    assert actual["original"]["raw_json"] == raw
    assert actual["original"]["data"]["x"][0] == Decimal("1e309")
    assert actual["candidate"]["data"]["x"][0] == Decimal("1e309")
    assert (
        actual["original"]["data"]["a/b~"]
        == actual["candidate"]["data"]["a/b~"]
    )
    assert actual["candidate"]["data"]["a/b~"]["precise"] == Decimal(
        "1.0000000000000000000001"
    )
    assert actual["scope"]["unvalidated_paths"] == ["/a~1b~0"]
    assert actual["issues"][0]["code"] == "numeric_range"
    assert actual["issues"][0]["observed"] == {"token": "1e309"}
    assert actual["candidate"]["valid"] is False
    assert actual["candidate"]["remaining_issues"][0]["code"] == "numeric_range"


@pytest.mark.parametrize(
    "token,valid",
    [
        ("1e309", False),
        ("-1e309", False),
        ("1e-400", False),
        ("-1e-400", False),
        ("1.7976931348623157e308", True),
        ("1.7976931348623159e308", False),
        ("5e-324", True),
        ("-0", True),
    ],
)
def test_original_numbers_are_checked_for_range_without_rewriting(
    token: str, valid: bool
) -> None:
    """Original numeric diagnostics concern range while retained tokens stay exact."""
    raw = '{"values":[' + token + "]}"
    built = build_data_repair_report("histogram", raw, recognized=True)
    text = serialize_data_repair_report(built)
    actual = json.loads(text, parse_float=str, parse_int=str)
    assert actual["status"] == ("valid" if valid else "needs_input")
    assert actual["original"]["data"]["values"] == [token]
    assert actual["changes"] == []
    if not valid:
        assert actual["issues"][0]["code"] == "numeric_range"
        assert actual["issues"][0]["observed"]["token"] == token


@pytest.mark.parametrize(
    "plot_type,recognized",
    [("line", True), ("unknown", False), (" scatter", False)],
)
def test_unsupported_and_unknown_are_distinguishable(
    plot_type: str, recognized: bool
) -> None:
    """No alias guesses or duplicate catalog are needed to report absent coverage."""
    actual = report(plot_type, '{"x":["1"]}', recognized=recognized)
    assert actual["status"] == "unsupported"
    assert actual["recognized"] is recognized
    assert actual["supported"] is False
    assert actual["plot_type"] == plot_type
    assert actual["issues"][0]["code"] == "unsupported_plot_type"
    assert actual["changes"] == []
    assert actual["scope"]["fields"] == []
    assert actual["scope"]["unvalidated_paths"] == ["/x"]


@pytest.mark.parametrize(
    "bins", [0, -1, 1.5, 10.0, True, None, "10", [], [1], [3, 2], ["3", "2"]]
)
def test_invalid_bins_never_become_implicitly_sorted_or_coerced(
    bins: object,
) -> None:
    """Invalid bin counts and decreasing edges require the caller's source choices."""
    actual = report("histogram", json.dumps({"values": [1], "bins": bins}))
    if isinstance(bins, list) and bins == ["3", "2"]:
        assert actual["status"] == "proposal"
        assert actual["candidate"]["valid"] is False
        assert (
            actual["candidate"]["remaining_issues"][0]["code"] == "invalid_bins"
        )
        assert actual["candidate"]["data"]["bins"] == [3, 2]
    else:
        assert actual["status"] == "needs_input"
        assert actual["changes"] == []
    assert actual["original"]["data"]["bins"] == bins


@pytest.mark.parametrize("bins", [1, 10, [0, 0, 1], ["0", "0", "1"]])
def test_positive_counts_and_duplicate_edges_are_valid(bins: object) -> None:
    """Nondecreasing edges explicitly permit duplicates."""
    actual = report("histogram", json.dumps({"values": [1], "bins": bins}))
    assert (
        actual.get("candidate", {"valid": actual["status"] == "valid"})["valid"]
        is True
    )


@pytest.mark.parametrize(
    "plot_type,raw,expected",
    [
        ("scatter", "[]", [("expected_object", "")]),
        ("scatter", "{}", [("missing_field", "/x"), ("missing_field", "/y")]),
        (
            "scatter",
            '{"x":false,"y":[]}',
            [("expected_array", "/x"), ("empty_array", "/y")],
        ),
        ("heatmap", '{"matrix":[]}', [("empty_array", "/matrix")]),
        (
            "heatmap",
            '{"matrix":[[],null]}',
            [("empty_array", "/matrix/0"), ("expected_array", "/matrix/1")],
        ),
    ],
)
def test_manual_shape_failures_name_locations(
    plot_type: str, raw: str, expected: list
) -> None:
    """Missing, empty and incorrect containers remain explicit manual choices."""
    actual = report(plot_type, raw)
    assert actual["status"] == "needs_input"
    assert [(i["code"], i["path"]) for i in actual["issues"]] == expected
    assert actual["changes"] == []


def test_parent_shape_issues_precede_numeric_children_in_index_order() -> None:
    """Diagnostics follow declared fields, parent paths and numeric array indexes."""
    actual = report(
        "scatter", json.dumps({"y": ["2"], "x": ["1"] * 12, "z": 0, "a": 0})
    )
    assert [i["path"] for i in actual["issues"]] == [
        "/x",
        *[f"/x/{i}" for i in range(12)],
        "/y/0",
    ]
    assert [c["path"] for c in actual["changes"]] == [
        *[f"/x/{i}" for i in range(12)],
        "/y/0",
    ]
    assert actual["scope"]["unvalidated_paths"] == ["/a", "/z"]
