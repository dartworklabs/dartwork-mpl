"""The bounded JSON decoder: ambiguity, non-finite numbers and every size limit."""

import json

import pytest

from dartwork_mpl.ui.platform import json_bounds as boundary


@pytest.mark.parametrize(
    "raw",
    [
        b'{"n":1,"n":2}',
        b'{"x":{"n":1,"n":2}}',
        b"NaN",
        b"Infinity",
        b"-Infinity",
        b"1e400",
        b'"\xff"',
        b'"\\ud800"',
        b'"\\udfff"',
        b"{} trailing",
        b"01",
        b"",
    ],
)
def test_decoder_rejects_ambiguous_or_nonfinite_json(raw):
    """Duplicate fields, invalid Unicode and nonfinite numbers never reach schemas."""
    assert isinstance(
        boundary.decode_json(raw, max_bytes=1024), boundary.MalformedInput
    )


def test_decoder_exact_limits_and_one_over():
    """Every specified bound admits its exact limit and refuses one over."""
    assert boundary.decode_json(b"true", max_bytes=4) is True
    assert isinstance(
        boundary.decode_json(b"true ", max_bytes=4), boundary.LimitExceeded
    )
    assert boundary.decode_json(b"9" * 640, max_bytes=1024) == int("9" * 640)
    assert isinstance(
        boundary.decode_json(b"9" * 641, max_bytes=1024), boundary.LimitExceeded
    )
    for limit, value, larger in [
        (65536, "a" * 65536, "a" * 65537),
        (65536, "é" * 32768, "é" * 32769),
        (4096, [None] * 4096, [None] * 4097),
    ]:
        raw = json.dumps(value, ensure_ascii=False).encode()
        assert boundary.decode_json(raw, max_bytes=len(raw)) == value, limit
        raw = json.dumps(larger, ensure_ascii=False).encode()
        assert isinstance(
            boundary.decode_json(raw, max_bytes=len(raw)),
            boundary.LimitExceeded,
        )
    assert boundary.decode_json(
        b"[" * 16 + b"0" + b"]" * 16, max_bytes=1024
    ) == nested(16)
    assert isinstance(
        boundary.decode_json(b"[" * 17 + b"0" + b"]" * 17, max_bytes=1024),
        boundary.LimitExceeded,
    )
    assert isinstance(
        boundary.decode_json(
            b"[" * 10000 + b"0" + b"]" * 10000, max_bytes=32768
        ),
        boundary.MalformedInput,
    )


def nested(depth):
    """Provide an independent expected nested JSON value for depth examples."""
    value = 0
    for _ in range(depth):
        value = [value]
    return value


def test_total_json_value_bound_counts_values_in_all_containers():
    """Many individually small containers cannot bypass the total-value bound."""
    exact = [[None] * 4096 for _ in range(15)] + [[None] * 4079]
    raw = json.dumps(exact).encode()
    assert boundary.decode_json(raw, max_bytes=len(raw)) == exact
    exact[-1].append(None)
    raw = json.dumps(exact).encode()
    assert isinstance(
        boundary.decode_json(raw, max_bytes=len(raw)), boundary.LimitExceeded
    )
