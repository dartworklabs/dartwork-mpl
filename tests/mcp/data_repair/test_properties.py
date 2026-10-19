"""Seeded generated inputs exercise preservation, determinism and safe refusal."""

import json
import random
from decimal import Decimal

from dartwork_mpl.mcp.data_repair import (
    build_data_repair_report,
    serialize_data_repair_report,
)

SEED = 20261019
SHAPES = ("scatter", "bar", "bar_horizontal", "histogram", "heatmap")


def decode(text: str) -> dict:
    """Read report numbers mathematically and reject nonstandard output tokens."""

    def forbidden(token: str) -> None:
        """Turn a nonfinite output token into an observable property failure."""
        raise AssertionError(f"Nonstandard output constant: {token}")

    return json.loads(
        text, parse_int=Decimal, parse_float=Decimal, parse_constant=forbidden
    )


def walk_equal_except_changes(
    original: object, candidate: object, allowed: set[str], path: str = ""
) -> None:
    """Check unchanged values, object order and sequence lengths at every path."""
    if path in allowed:
        return
    if isinstance(original, dict):
        assert isinstance(candidate, dict)
        assert list(original) == list(candidate)
        for key in original:
            escaped = key.replace("~", "~0").replace("/", "~1")
            walk_equal_except_changes(
                original[key], candidate[key], allowed, path + "/" + escaped
            )
    elif isinstance(original, list):
        assert isinstance(candidate, list)
        assert len(original) == len(candidate)
        for index, item in enumerate(original):
            walk_equal_except_changes(
                item, candidate[index], allowed, path + f"/{index}"
            )
    else:
        assert original == candidate
        assert type(original) is type(candidate)


def generated_data(rng: random.Random, plot_type: str) -> dict:
    """Generate valid, candidate and mixed manual cases without an oracle clone."""
    choices = [
        0,
        1,
        -3,
        2.5,
        "1",
        "2.5",
        "01",
        "-0",
        None,
        True,
        "0.10000000000000001",
    ]
    count = rng.randint(1, 6)
    numbers = [rng.choice(choices) for _ in range(count)]
    if plot_type == "scatter":
        data = {
            "x": numbers,
            "y": [rng.choice(choices) for _ in range(rng.randint(1, 6))],
        }
    elif plot_type in ("bar", "bar_horizontal"):
        data = {
            "categories": [
                rng.choice(["01", "02", "A", None, 1]) for _ in range(count)
            ],
            "values": numbers,
        }
    elif plot_type == "histogram":
        data = {"values": numbers}
        if rng.randrange(2):
            data["bins"] = rng.choice(
                ["10", 10, [0, 1, 1, 2], ["2", "1"], [0, True], None]
            )
    else:
        data = {
            "matrix": [
                [rng.choice(choices) for _ in range(rng.randint(0, 4))]
                for _ in range(count)
            ]
        }
    data["meta~/"] = {
        "order": ["01", " 1", "2.5"],
        "integer": 2**60,
        "nested": {"b": False, "a": None},
    }
    return data


def test_seeded_admitted_inputs_preserve_original_and_only_declared_changes() -> (
    None
):
    """Every unchanged value, label, order and unknown field survives proposals."""
    rng = random.Random(SEED)
    proposals = partials = fixed_points = 0
    for index in range(250):
        plot_type = SHAPES[index % len(SHAPES)]
        raw = json.dumps(
            generated_data(rng, plot_type), ensure_ascii=bool(index % 2)
        )
        built = build_data_repair_report(plot_type, raw, recognized=True)
        text = serialize_data_repair_report(built)
        assert text == serialize_data_repair_report(
            build_data_repair_report(plot_type, raw, recognized=True)
        ), (SEED, index, raw)
        actual = decode(text)
        assert actual["original"]["raw_json"] == raw
        expected = json.loads(raw, parse_int=Decimal, parse_float=Decimal)
        assert actual["original"]["data"] == expected
        assert actual["effects"] == "none"
        assert actual["scope"]["unvalidated_paths"] == ["/meta~0~1"]
        assert actual["requires_review"] is bool(actual["changes"])
        if not actual["changes"]:
            assert "candidate" not in actual
            continue
        proposals += 1
        partials += not actual["candidate"]["valid"]
        paths = {change["path"] for change in actual["changes"]}
        walk_equal_except_changes(expected, actual["candidate"]["data"], paths)
        assert actual["candidate"]["data"]["meta~/"] == expected["meta~/"]
        for change in actual["changes"]:
            assert isinstance(change["before"], str)
            assert isinstance(change["after"], Decimal)
            assert Decimal(change["before"]) == change["after"]
            assert change["requires_review"] is True
        if actual["candidate"]["valid"]:
            fixed_points += 1
            candidate = json.loads(text)["candidate"]["data"]
            checked = decode(
                serialize_data_repair_report(
                    build_data_repair_report(
                        plot_type, json.dumps(candidate), recognized=True
                    )
                )
            )
            assert checked["status"] == "valid"
            assert checked["changes"] == []
    assert proposals > 100 and partials > 50 and fixed_points > 0


def test_internal_candidate_mutation_does_not_reach_the_original() -> None:
    """Nested candidate containers have no mutable aliases to original containers."""
    raw = '{"matrix":[["1",2]],"meta":{"nested":[{"value":3}]}}'
    built = build_data_repair_report("heatmap", raw, recognized=True)
    before = decode(serialize_data_repair_report(built))["original"]
    candidate = built.candidate.data
    candidate["matrix"][0].append(99)
    candidate["meta"]["nested"][0]["value"] = "changed"
    candidate["meta"]["nested"].append({})
    assert decode(serialize_data_repair_report(built))["original"] == before


def test_seeded_arbitrary_text_never_raises_and_is_deterministic() -> None:
    """Malformed, deep, Unicode, oversize and arbitrary strings yield typed results."""
    rng = random.Random(SEED)
    alphabet = '{}[],:"\\0123456789eE-. abcdef\n\t\x00é😀\ud800\udfff'
    corpus = [
        "".join(rng.choice(alphabet) for _ in range(rng.randrange(250)))
        for _ in range(400)
    ]
    corpus += [
        "[" * 2_000 + "]" * 2_000,
        " " * 65_537,
        '{"x":[1e999999999999999999999999,"2"],"y":[3,4]}',
        '{"x":[' + "9" * 5_000 + ',"2"],"y":[3,4]}',
        '{"values":["0e999999999999999999999999"]}',
        '{"values":[0e999999999999999999999999],"bins":[0e999999999999999999999999,1]}',
        '{"x":["1",null],"y":[2]}',
    ]
    for index, raw in enumerate(corpus):
        shape = "histogram" if '"values"' in raw else "scatter"
        first = serialize_data_repair_report(
            build_data_repair_report(shape, raw, recognized=True)
        )
        second = serialize_data_repair_report(
            build_data_repair_report(shape, raw, recognized=True)
        )
        assert first == second, (SEED, index, repr(raw))
        actual = json.loads(first, parse_int=str, parse_float=str)
        assert actual["effects"] == "none"
        assert len(first.encode("utf-8")) <= 1_048_576
        assert actual["status"] in {
            "valid",
            "proposal",
            "needs_input",
            "rejected",
        }
        if "original" in actual:
            assert actual["original"]["raw_json"] == raw


def test_extreme_numeric_tokens_survive_both_payloads_without_float_conversion() -> (
    None
):
    """Very long integer/exponent lexemes cannot crash or round original values."""
    for token in [
        "1e999999999999999999999999",
        "9" * 5_000,
        "0e999999999999999999999999",
    ]:
        raw = '{"x":[' + token + ',"2"],"y":[3,4],"meta":' + token + "}"
        text = serialize_data_repair_report(
            build_data_repair_report("scatter", raw, recognized=True)
        )
        # Parsing as strings avoids the independent decoder's Decimal exponent
        # limit and verifies exact emitted numeric lexemes in both data copies.
        actual = json.loads(text, parse_int=str, parse_float=str)
        assert actual["original"]["raw_json"] == raw
        assert actual["original"]["data"]["x"][0] == token
        assert actual["candidate"]["data"]["x"][0] == token
        assert actual["original"]["data"]["meta"] == token
        assert actual["candidate"]["data"]["meta"] == token
