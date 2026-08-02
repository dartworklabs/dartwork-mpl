"""Regression tests for strict validation of the packaged color v6 SSOT."""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
V6_SSOT_PATH = REPO_ROOT / "src/dartwork_mpl/asset/color/color_v6_ssot.json"


def _canonical_sha256(value: object) -> str:
    """Hash one decoded JSON value with the canonical section encoding."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _set_nested(
    container: object, path: tuple[str | int, ...], value: object
) -> None:
    """Replace one nested decoded-JSON value."""
    target = container
    for key in path[:-1]:
        if isinstance(target, dict):
            target = target[key]
            continue
        if isinstance(target, list) and isinstance(key, int):
            target = target[key]
            continue
        raise TypeError(f"cannot descend through {type(target).__name__}")

    final = path[-1]
    if isinstance(target, dict):
        target[final] = value
        return
    if isinstance(target, list) and isinstance(final, int):
        target[final] = value
        return
    raise TypeError(f"cannot assign through {type(target).__name__}")


def _write_rehashed_section(
    tmp_path: Path, payload: dict[str, object], section: str
) -> Path:
    """Write a mutation whose in-file section hash remains self-consistent."""
    hashes = cast(dict[str, str], payload["section_hashes"])
    hashes[section] = _canonical_sha256(payload[section])
    changed = tmp_path / f"malformed-{section}.json"
    changed.write_text(
        json.dumps(payload, allow_nan=False, sort_keys=True), encoding="utf-8"
    )
    return changed


def _load_changed(path: Path) -> Mapping[str, object]:
    """Load one changed authority through the production validator."""
    from dartwork_mpl._colors import _ssot

    return _ssot._load_color_v6_ssot(path)


@pytest.fixture
def v6_payload() -> dict[str, object]:
    """Return a fresh mutable copy of the packaged v6 authority."""
    decoded: object = json.loads(V6_SSOT_PATH.read_text(encoding="utf-8"))
    if not isinstance(decoded, dict):
        raise TypeError("packaged color v6 SSOT must be an object")
    return cast(dict[str, object], decoded)


@pytest.mark.parametrize(
    ("path", "value", "error_pattern"),
    [
        (
            ("recipe", "family_params", "red", "gamma"),
            0.0,
            r"recipe family red.*gamma",
        ),
        (
            ("recipe", "family_params", "red", "tp"),
            0.0,
            r"recipe family red.*tp",
        ),
        (
            ("recipe", "family_params", "red", "cmax"),
            -0.01,
            r"recipe family red.*cmax",
        ),
        (
            ("recipe", "family_params", "red", "cend"),
            -0.01,
            r"recipe family red.*cend",
        ),
        (
            ("recipe", "family_params", "red", "c0"),
            1.01,
            r"recipe family red.*c0",
        ),
    ],
)
def test_accessor_rejects_invalid_family_parameter_domains(
    tmp_path: Path,
    v6_payload: dict[str, object],
    path: tuple[str | int, ...],
    value: object,
    error_pattern: str,
) -> None:
    """Reject invalid family domains before the external audit-pin check."""
    _set_nested(v6_payload, path, value)
    changed = _write_rehashed_section(tmp_path, v6_payload, "recipe")

    with pytest.raises(RuntimeError, match=error_pattern):
        _load_changed(changed)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SHAPE_Q", 0.0),
        ("SHAPE_R", -0.01),
        ("GAMUT_CHROMA_FRAC", 0.0),
        ("GRAY_TINT_HUE", "not-a-number"),
    ],
)
def test_accessor_rejects_invalid_recipe_constant_domains(
    tmp_path: Path, v6_payload: dict[str, object], name: str, value: object
) -> None:
    """Reject malformed construction constants before checking audit pins."""
    _set_nested(v6_payload, ("recipe", "constants", name), value)
    changed = _write_rehashed_section(tmp_path, v6_payload, "recipe")

    with pytest.raises(RuntimeError, match=rf"recipe constant {name}"):
        _load_changed(changed)


@pytest.mark.parametrize(
    "profile",
    [[0.0] * 9, [-0.01, *([0.0] * 9)], ["not-a-number", *([0.0] * 9)]],
    ids=["wrong-length", "negative-chroma", "non-numeric-chroma"],
)
def test_accessor_rejects_invalid_gray_chroma_profile(
    tmp_path: Path, v6_payload: dict[str, object], profile: list[object]
) -> None:
    """Require ten finite non-negative gray-profile chroma values."""
    _set_nested(v6_payload, ("recipe", "constants", "GRAY_C_PROFILE"), profile)
    changed = _write_rehashed_section(tmp_path, v6_payload, "recipe")

    with pytest.raises(RuntimeError, match="GRAY_C_PROFILE"):
        _load_changed(changed)


def test_accessor_rejects_adjacent_duplicates_with_unit_max_run(
    tmp_path: Path, v6_payload: dict[str, object]
) -> None:
    """Reject a row claiming an adjacent duplicate but no repeated run."""
    row_path = ("row_contracts", "palette", "amber")
    _set_nested(v6_payload, (*row_path, "unique_count"), 9)
    _set_nested(v6_payload, (*row_path, "adjacent_duplicate_count"), 1)
    _set_nested(v6_payload, (*row_path, "max_run_length"), 1)
    changed = _write_rehashed_section(tmp_path, v6_payload, "row_contracts")

    with pytest.raises(RuntimeError, match=r"row contract palette\.amber"):
        _load_changed(changed)


def test_accessor_rejects_duplicate_json_object_keys(tmp_path: Path) -> None:
    """Reject ambiguous raw JSON even when the decoded authority is unchanged."""
    raw = V6_SSOT_PATH.read_text(encoding="utf-8")
    duplicated = raw.replace("{\n", '{\n  "schema": "shadowed-duplicate",\n', 1)
    changed = tmp_path / "duplicate-key.json"
    changed.write_text(duplicated, encoding="utf-8")

    with pytest.raises(RuntimeError, match=r"duplicate.*schema"):
        _load_changed(changed)


def test_accessor_normalizes_huge_integer_overflow(
    tmp_path: Path, v6_payload: dict[str, object]
) -> None:
    """Normalize an overflowing JSON integer to the validator error contract."""
    _set_nested(v6_payload, ("recipe", "family_params", "red", "cmax"), 10**400)
    changed = _write_rehashed_section(tmp_path, v6_payload, "recipe")

    with pytest.raises(RuntimeError, match=r"recipe family red.*cmax"):
        _load_changed(changed)


def test_accessor_normalizes_invalid_utf8(tmp_path: Path) -> None:
    """Normalize an invalid UTF-8 asset to the documented decode error."""
    changed = tmp_path / "invalid-utf8.json"
    changed.write_bytes(b'\xff{"schema": "dartwork-mpl.color-ssot/v6"}')

    with pytest.raises(RuntimeError, match="could not decode color v6 SSOT"):
        _load_changed(changed)
