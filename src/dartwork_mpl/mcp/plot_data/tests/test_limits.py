"""Exact admission, strict parsing and bounded refusal behavior are observable."""

import json
from decimal import Decimal

import pytest

from dartwork_mpl.mcp.plot_data import (
    build_data_repair_report,
    serialize_data_repair_report,
)


def response(raw: str, name: str = "scatter") -> tuple[str, dict]:
    """Obtain deterministic strict JSON text and exact-decimal decoded output."""
    text = serialize_data_repair_report(
        build_data_repair_report(name, raw, recognized=True)
    )
    return text, json.loads(text, parse_int=Decimal, parse_float=Decimal)


def refusal(actual: dict, limit: str, maximum: int) -> None:
    """A limit refusal is payload-free and describes a measured excess."""
    assert actual["status"] == "rejected"
    assert actual["effects"] == "none"
    assert actual["requires_review"] is False
    assert (
        "original" not in actual
        and "candidate" not in actual
        and "changes" not in actual
    )
    assert len(actual["issues"]) == 1
    assert actual["issues"][0]["code"] == "limit_exceeded"
    observed = actual["issues"][0]["observed"]
    assert observed["limit"] == limit
    assert observed["maximum"] == maximum
    assert observed["observed"] > maximum


@pytest.mark.parametrize("multibyte", [False, True])
def test_input_utf8_bytes_at_limit_and_one_over(multibyte: bool) -> None:
    """The admission bound counts UTF-8 bytes, including non-ASCII text."""
    base = '{"x":[1],"y":[2],"meta":"' + ("é" * 100 if multibyte else "") + '"}'
    raw = base + " " * (65_536 - len(base.encode("utf-8")))
    _, actual = response(raw)
    assert actual["status"] == "valid"
    assert actual["original"]["raw_json"] == raw
    _, actual = response(raw + " ")
    refusal(actual, "input_bytes", 65_536)
    assert actual["issues"][0]["observed"]["observed"] == 65_537


def test_depth_at_sixteen_and_seventeen() -> None:
    """Sixteen containers are admitted; seventeen are refused before decoding."""
    prefix = '{"x":[1],"y":[2],"meta":'
    raw = prefix + "[" * 15 + "0" + "]" * 15 + "}"
    assert response(raw)[1]["status"] == "valid"
    refused = response(prefix + "[" * 16 + "0" + "]" * 16 + "}")[1]
    refusal(refused, "depth", 16)
    # An unfinished deep prefix still hits the lexical limit before syntax.
    refusal(response("[" * 17)[1], "depth", 16)


def test_value_and_key_tokens_at_ten_thousand_and_one_over() -> None:
    """A container and each scalar or key count toward the predecode token bound."""
    raw = "[" + ",".join(["0"] * 9_999) + "]"
    assert response(raw)[1]["status"] == "needs_input"
    refusal(response(raw[:-1] + ",0]")[1], "tokens", 10_000)
    # One object + 4,999 names + 4,999 values + one array = 10,000.
    raw = "{" + ",".join(f'"k{i}":0' for i in range(4_999)) + ',"z":[]}'
    # This variant is 10,001 tokens because z is itself another key.
    refusal(response(raw)[1], "tokens", 10_000)


@pytest.mark.parametrize("proposal", [False, True])
def test_issue_and_change_counts_at_one_hundred_and_one_over(
    proposal: bool,
) -> None:
    """Neither manual issues nor numeric changes are silently truncated."""
    value = "1" if proposal else None
    raw = json.dumps({"categories": ["a"] * 100, "values": [value] * 100})
    actual = response(raw, "bar")[1]
    assert len(actual["issues"]) == 100
    assert len(actual["changes"]) == (100 if proposal else 0)
    assert actual["status"] == ("proposal" if proposal else "needs_input")
    raw = json.dumps({"categories": ["a"] * 101, "values": [value] * 101})
    refusal(response(raw, "bar")[1], "issues", 100)


def test_total_original_and_candidate_issues_share_one_hundred_budget() -> None:
    """Remaining candidate diagnostics count alongside original diagnostics."""
    raw = json.dumps({"values": ["1"] * 50 + [None] * 25})
    actual = response(raw, "histogram")[1]
    assert (
        len(actual["issues"]) + len(actual["candidate"]["remaining_issues"])
        == 100
    )
    raw = json.dumps({"values": ["1"] * 50 + [None] * 26})
    refusal(response(raw, "histogram")[1], "issues", 100)


@pytest.mark.parametrize(
    "raw,code",
    [
        ("", "invalid_json"),
        ("{", "invalid_json"),
        ("{} []", "invalid_json"),
        ('{"x":1,"x":2}', "duplicate_key"),
        ('{"a":1,"\\u0061":2}', "duplicate_key"),
        ('{"meta":{"a":1,"a":2}}', "duplicate_key"),
        ('{"x":[NaN]}', "nonfinite_token"),
        ('{"x":[Infinity]}', "nonfinite_token"),
        ('{"x":[-Infinity]}', "nonfinite_token"),
        ('{"x":["\\ud800"]}', "invalid_json"),
        ('{"\\udfff":1}', "invalid_json"),
        ('{"x":["\x00"]}', "invalid_json"),
    ],
)
def test_strict_syntax_refusals_preserve_bounded_text(
    raw: str, code: str
) -> None:
    """Malformed, ambiguous and invalid-Unicode inputs never become proposals."""
    text, actual = response(raw)
    assert actual["status"] == "rejected"
    assert actual["original"] == {"raw_json": raw}
    assert actual["issues"][0]["code"] == code
    assert actual["issues"][0]["path"] == ""
    assert actual["scope"]["unvalidated_paths"] == []
    assert actual["changes"] == [] and "candidate" not in actual
    assert text.encode("utf-8")


def test_valid_surrogate_pairs_and_literal_delimiters_in_strings_are_admitted() -> (
    None
):
    """The lexical scan ignores apparent nesting and tokens inside strings."""
    raw = '{"x":[1],"y":[2],"meta":"\\ud83d\\ude00' + '[{,:}\\"' * 100 + '"}'
    actual = response(raw)[1]
    assert actual["status"] == "valid"
    assert actual["original"]["data"]["meta"].startswith("😀")


def test_output_overflow_discards_whole_payload_without_truncation() -> None:
    """Repeated escaped original and candidate data can exceed the report budget."""
    raw = json.dumps(
        {"x": ["1"], "y": [2], "meta": "\x7f" * 60_000}, ensure_ascii=False
    )
    assert len(raw.encode("utf-8")) < 65_536
    text, actual = response(raw)
    refusal(actual, "report_bytes", 1_048_576)
    assert len(text.encode("utf-8")) <= 1_048_576
    assert actual["plot_type"] == "scatter"


@pytest.mark.parametrize(
    "name",
    ["A" * 1_048_577, "\x00" * 180_000, "😀" * 90_000],
    ids=("over-budget-ascii", "over-budget-escaped-nul", "over-budget-emoji"),
)
def test_plot_name_that_cannot_fit_has_explicit_empty_name_refusal(
    name: str,
) -> None:
    """Escaped byte size governs the approved empty-name fallback."""
    text, actual = response('{"x":[1],"y":[2]}', name)
    refusal(actual, "report_bytes", 1_048_576)
    assert actual["plot_type"] == ""
    assert actual["recognized"] is actual["supported"] is False
    assert actual["issues"][0]["observed"]["field"] == "plot_type"
    assert len(text.encode("utf-8")) <= 1_048_576


@pytest.mark.parametrize(
    "name",
    ["A" * 1_046_576, 'A"\\\n\ud800', " scatter "],
    ids=(
        "near-budget-ascii",
        "escaped-invalid-unicode",
        "padded-supported-name",
    ),
)
def test_names_that_fit_keep_normalized_exact_value(name: str) -> None:
    """Escaping or invalid raw Unicode never requires a gratuitous name rewrite."""
    text, actual = response("{}", name)
    assert actual["plot_type"] == name.lower()
    assert len(text.encode("utf-8")) <= 1_048_576


def test_name_echo_overhead_can_trigger_empty_name_fallback() -> None:
    """A nearly budget-sized name is refused even when its string alone fits."""
    text, actual = response("{}", "A" * (1_048_576 - 10))
    refusal(actual, "report_bytes", 1_048_576)
    assert actual["plot_type"] == ""
    assert actual["issues"][0]["observed"]["field"] == "plot_type"
    assert len(text) < 1_000


@pytest.mark.parametrize("invalid", ["\ud800", "\udfff", "\ud800\udfff"])
def test_invalid_utf8_source_rejects_without_claiming_exact_raw(
    invalid: str,
) -> None:
    """Actual surrogates outside UTF-8 admission cannot be preserved honestly."""
    text, actual = response('{"x":["' + invalid + '"]}')
    assert actual["status"] == "rejected"
    assert actual["issues"][0]["code"] == "invalid_json"
    assert actual["issues"][0]["observed"] == {
        "offset": 7,
        "type": "invalid_utf8",
    }
    assert "original" not in actual and "candidate" not in actual
    assert actual["changes"] == []
    assert text.encode("utf-8")


def test_exact_serialized_report_budget_and_one_over() -> None:
    """Output at the exact byte budget is admitted; one more byte is refused."""
    base, _ = response("{}", "a")
    name = "a" * (1_048_576 - len(base) + 1)
    text, actual = response("{}", name)
    assert len(text.encode("utf-8")) == 1_048_576
    assert actual["status"] == "unsupported"
    text, actual = response("{}", name + "a")
    refusal(actual, "report_bytes", 1_048_576)
    assert len(text.encode("utf-8")) <= 1_048_576


def test_exponent_scalar_bin_count_is_a_manual_representation_choice() -> None:
    """A scalar bin count is never silently converted from a float lexeme."""
    _, actual = response('{"values":[1],"bins":1e1}', "histogram")
    assert actual["status"] == "needs_input"
    assert actual["issues"][0]["code"] == "invalid_bins"
    assert actual["changes"] == []
