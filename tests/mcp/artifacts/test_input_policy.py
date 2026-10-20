"""Closed revision/receipt contracts reject ambiguity without acquiring authority."""

import copy
import json
import random
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone

import pytest

from dartwork_mpl.mcp.artifacts.input_policy import (
    CopyInput,
    CopySelection,
    InputFile,
    InputMetadata,
    InvalidProvenance,
    KnownProvenance,
    LegacyProvenance,
    PinnedParent,
    ProvenanceInput,
    RetainedInput,
    RetainedLocator,
    RetainedSelection,
    Revision,
    UnsupportedProvenance,
    build_provenance,
    can_reserve,
    classify_provenance,
    parse_input_metadata,
    parse_revision,
)
from dartwork_mpl.mcp.artifacts.policy import (
    ArtifactId,
    CorruptArtifact,
    InvalidRequest,
    RenderRequest,
)

PARENT = ArtifactId("123456789abc4def8123456789abcdef")
CHILD = ArtifactId("abcdef1234564abc9def123456789abc")
HASH = "a" * 64
NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)
MIB = 1024 * 1024


def copy_wire(name="observations", path="private/data.csv"):
    """Create a legal request whose private path must not reach the receipt."""
    return {
        "kind": "copy",
        "name": name,
        "root_id": "research",
        "relative_path": path,
        "sha256": HASH,
    }


def retained_wire(name="previous"):
    """Select a prior set independently from the new child's locator."""
    return {
        "kind": "retained",
        "name": name,
        "artifact_id": PARENT.value,
        "input_name": "old",
        "sha256": HASH,
    }


def parsed_revision(inputs=None, parent=PARENT.value):
    """Return a legal immutable revision for serializer and constructor tests."""
    raw = {
        "schema_version": 1,
        "inputs": inputs
        if inputs is not None
        else [copy_wire(), retained_wire()],
    }
    if parent is not None:
        raw["parent_artifact_id"] = parent
    result = parse_revision(raw)
    assert isinstance(result, Revision)
    return result


def metadata_for(revision):
    """Represent measured bytes in request order at the child publication instant."""
    return InputMetadata(
        CHILD,
        NOW,
        NOW + timedelta(days=7),
        tuple(InputFile(item.name, item.sha256, 7) for item in revision.inputs),
    )


def test_revision_is_closed_and_bounded():
    """Unknown keys, wrong scalar types, paths and excessive structure refuse safely."""
    valid = {"schema_version": 1, "inputs": [copy_wire()]}
    bad = [
        None,
        [],
        {},
        {"schema_version": 1},
        {"schema_version": True, "inputs": [copy_wire()]},
        {**valid, "extra": 0},
        {**valid, "parent_artifact_id": None},
        {**valid, "inputs": ()},
    ]
    for path in (
        "",
        "/data",
        "a//b",
        "a/./b",
        "a/../b",
        "a/",
        "a\\b",
        "a\x00b",
        "é" * 513,
        "\ud800",
    ):
        bad.append({"schema_version": 1, "inputs": [copy_wire(path=path)]})
    for key, value in (
        ("root_id", "é"),
        ("name", "x" * 65),
        ("sha256", "A" * 64),
        ("kind", "other"),
        ("extra", 1),
    ):
        bad.append(
            {"schema_version": 1, "inputs": [{**copy_wire(), key: value}]}
        )
    bad += [
        {"schema_version": 1, "inputs": [copy_wire(str(i)) for i in range(9)]},
        {"schema_version": 1, "inputs": [copy_wire(), copy_wire()]},
        {**valid, "extra": {"a": {"b": {"c": {}}}}},
    ]
    oversized = {**valid, "extra": ""}
    oversized["extra"] = "x" * (
        16 * 1024
        + 1
        - len(json.dumps(oversized, separators=(",", ":")).encode())
    )
    assert (
        len(json.dumps(oversized, separators=(",", ":")).encode())
        == 16 * 1024 + 1
    )
    bad.append(oversized)
    assert parse_revision(None) is None
    for raw in bad[1:]:
        result = parse_revision(raw)
        assert isinstance(result, InvalidRequest), repr(raw)[:200]
        assert result.field == "revision"
        assert "private" not in result.message
    revision = parsed_revision()
    assert isinstance(revision.inputs[0], CopyInput)
    assert isinstance(revision.inputs[1], RetainedInput)
    assert revision.parent_artifact_id == PARENT
    assert revision.inputs[1].artifact_id == PARENT
    assert parsed_revision([], PARENT.value).inputs == ()
    assert parsed_revision([copy_wire()], None).parent_artifact_id is None
    assert parsed_revision([copy_wire(path="é" * 512)], None)
    assert [field.name for field in fields(RenderRequest)] == [
        "code",
        "figure_var",
        "timeout_seconds",
        "chart_type_hint",
    ]


def test_receipt_roundtrip():
    """Receipt selection is closed, ordered, path-free and points at child copies."""
    revision = parsed_revision()
    parent = PinnedParent(PARENT, "b" * 64, "c" * 64)
    receipt = build_provenance(revision, parent, metadata_for(revision))
    assert set(receipt) == {
        "schema_version",
        "parent",
        "inputs",
        "reproducibility",
    }
    assert receipt["parent"] == {
        "artifact_id": PARENT.value,
        "manifest_sha256": "b" * 64,
        "source_sha256": "c" * 64,
    }
    assert receipt["inputs"] == [
        {
            "name": "observations",
            "sha256": HASH,
            "size_bytes": 7,
            "retained": {"artifact_id": CHILD.value, "name": "observations"},
            "selection": {"kind": "copy"},
            "evidence": "copied_and_boundary_checked",
        },
        {
            "name": "previous",
            "sha256": HASH,
            "size_bytes": 7,
            "retained": {"artifact_id": CHILD.value, "name": "previous"},
            "selection": {
                "kind": "retained",
                "artifact_id": PARENT.value,
                "input_name": "old",
            },
            "evidence": "copied_and_boundary_checked",
        },
    ]
    assert receipt["reproducibility"] == "not_claimed"
    assert "private" not in json.dumps(receipt)
    assert "research" not in json.dumps(receipt)
    known = classify_provenance({"provenance": receipt})
    assert isinstance(known, KnownProvenance)
    assert known.parent == parent
    assert isinstance(known.inputs[0].selection, CopySelection)
    assert isinstance(known.inputs[1].selection, RetainedSelection)
    assert known.inputs[1].retained.artifact_id == CHILD
    assert known.to_dict() == receipt
    receipt["inputs"].clear()
    assert len(known.inputs) == 2
    only_parent = build_provenance(parsed_revision([]), parent, None)
    assert only_parent["inputs"] == []
    assert isinstance(
        classify_provenance({"provenance": only_parent}), KnownProvenance
    )
    input_only = parsed_revision([copy_wire()], None)
    input_receipt = build_provenance(input_only, None, metadata_for(input_only))
    assert input_receipt["parent"] is None
    assert isinstance(
        classify_provenance({"provenance": input_receipt}), KnownProvenance
    )


@pytest.mark.parametrize(
    "report, expected",
    [
        ({}, LegacyProvenance),
        (
            {"provenance": {"schema_version": 2, "opaque": "not interpreted"}},
            UnsupportedProvenance,
        ),
        ({"provenance": {"schema_version": True}}, InvalidProvenance),
        ({"provenance": None}, InvalidProvenance),
        ([], InvalidProvenance),
    ],
)
def test_parent_classifications_carry_no_untrusted_data(report, expected):
    """Legacy, unsupported and invalid ancestry are distinct data-free outcomes."""
    result = classify_provenance(report)
    assert type(result) is expected
    assert fields(result) == ()


def test_receipt_rejects_ambiguous_or_invented_evidence():
    """Known v1 receipts cannot add paths, loosen selections or misdirect locators."""
    receipt = build_provenance(
        parsed_revision(),
        PinnedParent(PARENT, HASH, HASH),
        metadata_for(parsed_revision()),
    )
    mutations = []
    for key, value in (
        ("extra", "private/path"),
        ("evidence", "consumed"),
        ("size_bytes", True),
        ("size_bytes", 8 * MIB + 1),
        ("retained", {"artifact_id": CHILD.value, "name": "wrong"}),
        ("selection", {"kind": "copy", "root_id": "research"}),
    ):
        altered = copy.deepcopy(receipt)
        altered["inputs"][0][key] = value
        mutations.append(altered)
    altered = copy.deepcopy(receipt)
    altered["inputs"][1]["selection"]["extra"] = "private/path"
    mutations.append(altered)
    altered = copy.deepcopy(receipt)
    altered["inputs"][1]["retained"]["artifact_id"] = PARENT.value
    mutations.append(altered)
    mutations += [
        {**receipt, "capture_at": "now"},
        {**receipt, "reproducibility": "proven"},
        {**receipt, "inputs": receipt["inputs"] * 5},
    ]
    for raw in mutations:
        assert isinstance(
            classify_provenance({"provenance": raw}), InvalidProvenance
        )


def test_metadata_roundtrip_rejects_duplicates_and_wrong_lifetime():
    """Only bounded closed v1 UTF-8 bytes with exact seven-day UTC expiry persist."""
    metadata = metadata_for(parsed_revision())
    encoded = metadata.to_bytes()
    assert encoded == metadata.to_bytes()
    assert parse_input_metadata(encoded) == metadata
    payload = json.loads(encoded)
    assert set(payload) == {
        "schema_version",
        "artifact_id",
        "created_at",
        "expires_at",
        "files",
    }
    assert set(payload["files"][0]) == {"name", "sha256", "size_bytes"}
    assert "selection" not in encoded.decode()
    invalid = [
        b'{"schema_version":1,"schema_version":1}',
        b'{"x":{"x":{"x":{"x":{}}}}}',
        b" " * (16 * 1024 + 1),
        b"\xff",
        b"NaN",
        encoded + b" " * (16 * 1024 + 1 - len(encoded)),
    ]
    for key, value in (
        ("extra", 1),
        ("schema_version", True),
        ("created_at", "2026-10-20T00:00:00+00:00"),
        ("expires_at", "2026-10-28T00:00:00Z"),
        ("files", []),
        ("files", payload["files"] * 2),
    ):
        invalid.append(json.dumps({**payload, key: value}).encode())
    invalid.append(
        encoded.replace(
            b'"name":"observations"',
            b'"name":"observations","name":"observations"',
        )
    )
    for raw in invalid:
        assert isinstance(parse_input_metadata(raw), CorruptArtifact)


def test_direct_constructors_guard_invariants_and_freeze():
    """Trusted construction still rejects invalid states instead of deferring checks."""
    constructors = [
        lambda: CopyInput("bad.name", "root", "a", HASH),
        lambda: CopyInput("good", "root", "../x", HASH),
        lambda: RetainedInput("good", PARENT.value, "old", HASH),
        lambda: Revision(None, ()),
        lambda: Revision(PARENT, []),
        lambda: Revision(PARENT, (parsed_revision().inputs[0],) * 2),
        lambda: InputFile("good", HASH, True),
        lambda: InputFile("good", HASH, 8 * MIB + 1),
        lambda: InputMetadata(
            CHILD, NOW, NOW + timedelta(days=8), (InputFile("a", HASH, 0),)
        ),
        lambda: InputMetadata(
            CHILD,
            NOW.replace(tzinfo=None),
            NOW + timedelta(days=7),
            (InputFile("a", HASH, 0),),
        ),
        lambda: InputMetadata(
            CHILD,
            NOW,
            NOW + timedelta(days=7),
            tuple(InputFile(str(i), HASH, 8 * MIB) for i in range(5)),
        ),
        lambda: PinnedParent(PARENT, "A" * 64, HASH),
        lambda: RetainedSelection(PARENT.value, "old"),
        lambda: RetainedLocator(CHILD, "bad.name"),
        lambda: ProvenanceInput(
            "x", HASH, 0, RetainedLocator(CHILD, "y"), CopySelection()
        ),
        lambda: ProvenanceInput(
            "x", HASH, 0, RetainedLocator(CHILD, "x"), "copy"
        ),
        lambda: KnownProvenance(None, ()),
        lambda: KnownProvenance(PinnedParent(PARENT, HASH, HASH), []),
        lambda: KnownProvenance(
            None,
            tuple(
                ProvenanceInput(
                    str(i),
                    HASH,
                    8 * MIB,
                    RetainedLocator(CHILD, str(i)),
                    CopySelection(),
                )
                for i in range(5)
            ),
        ),
    ]
    for constructor in constructors:
        with pytest.raises(ValueError):
            constructor()
    revision = parsed_revision()
    with pytest.raises(FrozenInstanceError):
        revision.inputs = ()
    with pytest.raises(ValueError):
        build_provenance(revision, None, metadata_for(revision))
    with pytest.raises(ValueError):
        build_provenance(revision, PinnedParent(PARENT, HASH, HASH), None)
    with pytest.raises(ValueError):
        build_provenance(
            parsed_revision([]),
            PinnedParent(PARENT, HASH, HASH),
            metadata_for(revision),
        )


def test_capacity_counts_the_next_set_and_reserved_bytes():
    """Reservations include pending/residue usage and stop at either hard bound."""
    assert can_reserve(512 * MIB - 1, 127, 1)
    assert not can_reserve(512 * MIB, 127, 1)
    assert not can_reserve(0, 128, 0)
    assert not can_reserve(-1, 0, 1)
    assert not can_reserve(0, False, 1)
    assert not can_reserve(0, 0, -1)


def test_seeded_parser_roundtrip_and_capacity_properties():
    """Seed 20261020 covers arbitrary JSON, immutable roundtrips and monotone quotas."""
    rng = random.Random(20261020)
    for index in range(300):
        count = rng.randint(1, 8)
        names = [f"input_{index}_{i}" for i in range(count)]
        entries = [
            copy_wire(name) if rng.randrange(2) else retained_wire(name)
            for name in names
        ]
        revision = parsed_revision(entries)
        assert (
            parse_revision(
                json.loads(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "parent_artifact_id": PARENT.value,
                            "inputs": entries,
                        }
                    )
                )
            )
            == revision
        )
        metadata = InputMetadata(
            CHILD,
            NOW,
            NOW + timedelta(days=7),
            tuple(
                InputFile(
                    item.name,
                    item.sha256,
                    rng.randint(0, min(8 * MIB, 32 * MIB // count)),
                )
                for item in revision.inputs
            ),
        )
        parent = PinnedParent(PARENT, HASH, HASH)
        receipt = build_provenance(revision, parent, metadata)
        known = classify_provenance(
            {"provenance": json.loads(json.dumps(receipt))}
        )
        assert isinstance(known, KnownProvenance), (index, receipt)
        assert known.to_dict() == receipt
        assert parse_input_metadata(metadata.to_bytes()) == metadata
        raw = rng.choice(
            [
                None,
                rng.getrandbits(32),
                "\ud800",
                [],
                {},
                {
                    "schema_version": rng.choice([1, True, 2]),
                    "inputs": entries,
                    "extra": rng.random(),
                },
            ]
        )
        assert isinstance(
            parse_revision(raw), (Revision, InvalidRequest, type(None))
        ), (index, raw)
        assert isinstance(
            parse_input_metadata(rng.randbytes(rng.randrange(100))),
            CorruptArtifact,
        )
        used = rng.randrange(512 * MIB + 1)
        sets = rng.randrange(130)
        reserved = rng.randrange(64 * MIB)
        if can_reserve(used, sets, reserved):
            assert used + reserved <= 512 * MIB and sets < 128
            assert can_reserve(used, sets, 0)
        else:
            assert used + reserved > 512 * MIB or sets >= 128


def test_seeded_malformed_fields_and_paths_never_escape_parser():
    """Seed 44004 exercises every request field/type and generated POSIX paths."""
    rng = random.Random(44004)
    for entry in (copy_wire(), retained_wire()):
        for field in entry:
            missing = entry.copy()
            del missing[field]
            assert isinstance(
                parse_revision({"schema_version": 1, "inputs": [missing]}),
                InvalidRequest,
            )
            for value in (None, True, 17, [], {}, "\ud800"):
                altered = {**entry, field: value}
                result = parse_revision(
                    {"schema_version": 1, "inputs": [altered]}
                )
                assert isinstance(result, InvalidRequest), (field, value)
    for index in range(300):
        path = "".join(rng.choices("ab./\\\x00é", k=rng.randrange(50)))
        result = parse_revision(
            {"schema_version": 1, "inputs": [copy_wire(path=path)]}
        )
        assert isinstance(result, (Revision, InvalidRequest)), (index, path)
        if isinstance(result, Revision):
            assert result.inputs[0].relative_path == path
    cycle = {"schema_version": 1}
    cycle["inputs"] = [cycle]
    assert isinstance(parse_revision(cycle), InvalidRequest)
    assert isinstance(
        parse_revision(
            {"schema_version": 1, "inputs": [copy_wire()], "x": float("nan")}
        ),
        InvalidRequest,
    )
