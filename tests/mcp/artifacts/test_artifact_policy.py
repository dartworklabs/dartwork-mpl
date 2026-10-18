"""Pure parsing rejects ambiguous input and preserves durable expiry invariants."""

import copy
import json
import math
import random
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

pytest.importorskip("fastmcp")

from dartwork_mpl.mcp.artifacts import (
    ArtifactId,
    ArtifactMember,
    CorruptArtifact,
    InvalidRequest,
    Manifest,
    RenderRequest,
    is_expired,
    parse_artifact_id,
    parse_manifest,
    parse_render_request,
)

NOW = datetime(2026, 10, 18, tzinfo=timezone.utc)
SEED = 20261018


def manifest_input() -> dict:
    """Supply one exact v1 persisted record, independent of the serializer."""
    return {
        "schema_version": 1,
        "artifact_id": "123456781234423482341234567890ab",
        "created_at": "2026-10-18T00:00:00Z",
        "expires_at": "2026-10-25T00:00:00Z",
        "files": [
            {"name": name, "size_bytes": 1, "sha256": "a" * 64}
            for name in ("plot.png", "plot.pdf", "source.py", "report.json")
        ],
        "validation": {
            "status": "ok",
            "validation_complete": True,
            "failed_checks": [],
        },
    }


def encoded(value: object) -> bytes:
    """Encode boundary inputs as actual UTF-8 JSON bytes."""
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def test_request_bounds() -> None:
    """The source byte and finite timeout boundaries are exact."""
    limit = 512 * 1024
    assert isinstance(parse_render_request("a" * limit), RenderRequest)
    assert isinstance(parse_render_request("a" * (limit + 1)), InvalidRequest)
    assert isinstance(parse_render_request("é" * (limit // 2)), RenderRequest)
    assert isinstance(
        parse_render_request("é" * (limit // 2) + "a"), InvalidRequest
    )
    assert isinstance(parse_render_request("\ud800"), InvalidRequest)
    for timeout in [0, -1, math.nan, math.inf, -math.inf, 120.000001, True]:
        assert isinstance(
            parse_render_request("", timeout_seconds=timeout), InvalidRequest
        ), timeout
    for timeout in [0.00001, 20, 120]:
        result = parse_render_request("x = 1\n", "chosen", timeout, "line")
        assert result == RenderRequest("x = 1\n", "chosen", timeout, "line")
    for figure in ["", "x.y", "x/y", "class", "a\x00b"]:
        assert isinstance(parse_render_request("", figure), InvalidRequest)


def test_id_and_manifest_parsers_reject_ambiguous_input() -> None:
    """Only complete UUID4 identities and exact bounded v1 records are parsed."""
    raw = manifest_input()
    good = raw["artifact_id"]
    assert parse_artifact_id(good) == ArtifactId(good)
    for identity in [
        good.upper(),
        str(UUID(good)),
        good + "\n",
        "../" + good,
        "%31" + good[1:],
        good[:12] + "1" + good[13:],
        good[:16] + "1" + good[17:],
        "",
        good[:-1],
    ]:
        assert isinstance(parse_artifact_id(identity), InvalidRequest), identity
    result = parse_manifest(encoded(raw))
    assert isinstance(result, Manifest)
    assert parse_manifest(result.to_bytes()) == result
    cases = []
    for field, value in [
        ("schema_version", 2),
        ("schema_version", True),
        ("created_at", "2026-10-18T00:00:00+00:00"),
        ("expires_at", "2026-10-24T00:00:00Z"),
        ("artifact_id", "../escape"),
        ("files", []),
        ("extra", "unknown"),
    ]:
        candidate = copy.deepcopy(raw)
        candidate[field] = value
        cases.append(encoded(candidate))
    for field, value in [
        ("name", "../plot.png"),
        ("size_bytes", -1),
        ("size_bytes", True),
        ("size_bytes", 1.5),
        ("sha256", "A" * 64),
        ("sha256", "a" * 63),
        ("extra", 1),
    ]:
        candidate = copy.deepcopy(raw)
        candidate["files"][0][field] = value
        cases.append(encoded(candidate))
    candidate = copy.deepcopy(raw)
    candidate["files"].append(candidate["files"][0])
    cases.append(encoded(candidate))
    cases += [
        b'{"schema_version":1,"schema_version":1}',
        encoded(raw).replace(b'"size_bytes": 1', b'"size_bytes": NaN', 1),
        b"[" * 9 + b"0" + b"]" * 9,
        encoded({str(i): 0 for i in range(129)}),
        b" " * (512 * 1024 + 1),
        b"\xff",
        b"null",
    ]
    candidate = copy.deepcopy(raw)
    candidate["validation"] = {
        "status": "validation_incomplete",
        "validation_complete": False,
        "failed_checks": ["\ud800"],
    }
    cases.append(json.dumps(candidate, ensure_ascii=True).encode())
    for candidate in cases:
        assert isinstance(parse_manifest(candidate), CorruptArtifact), (
            candidate[:200]
        )
    for constructor in [
        lambda: ArtifactId(good.upper()),
        lambda: RenderRequest("a" * (512 * 1024 + 1)),
        lambda: ArtifactId("0" * 32),
    ]:
        with pytest.raises(ValueError):
            constructor()
    assert [member.value for member in ArtifactMember] == [
        "plot.png",
        "plot.pdf",
        "source.py",
        "report.json",
        "manifest.json",
    ]


def test_generated_policy_invariants() -> None:
    """Seeded inputs retain round trips, strict IDs and closed expiry bounds."""
    rng = random.Random(SEED)
    for index in range(250):
        raw = manifest_input()
        good = UUID(int=rng.getrandbits(128), version=4).hex
        raw["artifact_id"] = good
        for entry in raw["files"]:
            entry["size_bytes"] = rng.randrange(0, 100000)
            entry["sha256"] = f"{rng.getrandbits(256):064x}"
        record = parse_manifest(encoded(raw))
        assert isinstance(record, Manifest), (SEED, index, raw)
        assert parse_manifest(record.to_bytes()) == record, (SEED, index, raw)
        assert parse_artifact_id(good) == ArtifactId(good), (SEED, good)
        malformed = rng.choice(["/", "%2f", "..", "g", "-", "\n"]) + good
        assert isinstance(parse_artifact_id(malformed), InvalidRequest), (
            SEED,
            malformed,
        )
        assert is_expired(record, record.expires_at), (SEED, raw)
        assert not is_expired(
            record, record.expires_at - timedelta(microseconds=1)
        )
        now = record.expires_at + timedelta(microseconds=rng.randrange(100000))
        assert is_expired(record, now), (SEED, raw, now)
        noise = bytes(rng.randrange(256) for _ in range(rng.randrange(128)))
        assert isinstance(parse_manifest(noise), CorruptArtifact), (SEED, noise)
    with pytest.raises(ValueError):
        is_expired(record, datetime(2026, 10, 18))
