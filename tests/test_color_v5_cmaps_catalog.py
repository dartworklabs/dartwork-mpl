"""Exact and policy-wiring tests for the 43-map NeutralTone catalog."""

import hashlib
import inspect
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

import numpy as np
import pytest

from dartwork_mpl._colors import _cmaps, _conversion, _generate

DIRECT_32_SHA256 = (
    "90f393cc14afc230438078f014a422886cf09122491637aec11abe010be187d2"
)
FULL_256_SHA256 = (
    "e026ce047dd8a186299b2857e3d8c81f2b2bc4b7249df37f35b7c0093c5240c1"
)
MULTI_TONE_RANGES = {
    "aurora": (0.2586206810344833, 0.9655172091954044),
    "afterglow": (0.2758620597701155, 0.9310344517241399),
    "blaze": (0.2413793022988511, 0.9482758304597722),
    "lava": (0.2413793022988511, 0.9568965198275883),
    "lagoon": (0.2586206810344833, 0.9655172091954044),
    "glacier": (0.2586206810344833, 0.9655172091954044),
    "canopy": (0.2586206810344833, 0.9655172091954044),
    "haze": (0.2586206810344833, 0.9655172091954044),
    "iris": (0.2586206810344833, 0.939655141091956),
}
DIVERGING_TONES = {
    ("blue", "red"): 0.6635425400424864,
    ("blue", "orange"): 0.4999999833333344,
    ("teal", "rose"): 0.5172413620689666,
    ("green", "purple"): 0.4827586045977022,
    ("purple", "orange"): 0.4999999833333344,
    ("cyan", "red"): 0.5172413620689666,
    ("teal", "amber"): 0.5172413620689666,
    ("violet", "lime"): 0.4999999833333344,
    ("indigo", "amber"): 0.4827586045977022,
    ("gray", "blue"): 0.4999999833333344,
    ("gray", "red"): 0.4999999833333344,
}


def _canonical_sha256(value: object) -> str:
    """Hash one JSON value with the frozen manifest encoding."""
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _compile_palette(*, luminance_lock: bool) -> dict[str, list[str]]:
    """Call the future palette interface while inspect tests own its shape."""
    function = cast(
        Callable[..., dict[str, list[str]]], _generate.compile_palette
    )
    return function(luminance_lock=luminance_lock)


def _compile_cmaps(
    palette: dict[str, list[str]], n: int, *, luminance_lock: bool
) -> dict[str, list[str]]:
    """Call the future cmap interface while inspect tests own its shape."""
    function = cast(Callable[..., dict[str, list[str]]], _cmaps.compile_cmaps)
    return function(palette, n=n, luminance_lock=luminance_lock)


@pytest.fixture(scope="module")
def compatibility_snapshot() -> dict[str, object]:
    """Load the immutable full-LUT fixture once for exact comparison."""
    path = (
        Path(__file__).resolve().parents[1]
        / "docs/superpowers/specs/assets/2026-07-14-oklab-centered-"
        "color-system/color_v5_compatibility.json"
    )
    decoded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(decoded, dict)
    return cast(dict[str, object], decoded)


@pytest.fixture(scope="module")
def locked_palette() -> dict[str, list[str]]:
    """Compile the shipped palette once for all catalog tests."""
    return _compile_palette(luminance_lock=True)


@pytest.fixture(scope="module")
def locked_direct_32(
    locked_palette: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Compile the locked direct previews once."""
    return _compile_cmaps(locked_palette, 32, luminance_lock=True)


@pytest.fixture(scope="module")
def locked_full_256(
    locked_palette: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Compile the shipped full LUTs once despite their dense render cost."""
    return _compile_cmaps(locked_palette, 256, luminance_lock=True)


def test_compile_cmaps_lock_is_true_and_keyword_only() -> None:
    """Keep shipped output locked unless callers name the diagnostic opt-out."""
    parameter = inspect.signature(_cmaps.compile_cmaps).parameters[
        "luminance_lock"
    ]

    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is True


def test_compile_cmaps_rejects_positional_lock(
    locked_palette: dict[str, list[str]],
) -> None:
    """Reject an opaque positional Boolean at the catalog boundary."""
    with pytest.raises(TypeError):
        cast(Callable[..., object], _cmaps.compile_cmaps)(
            locked_palette, 32, False
        )


def test_locked_direct_32_matches_frozen_exact_hash(
    locked_direct_32: dict[str, list[str]], v5_ssot: Mapping[str, object]
) -> None:
    """Pin every direct 32-stop row after the coordinate migration."""
    colormaps = cast(Mapping[str, object], v5_ssot["colormaps"])
    expected = colormaps["swatches_32"]

    assert locked_direct_32 == expected
    assert _canonical_sha256(locked_direct_32) == DIRECT_32_SHA256


def test_locked_full_256_matches_frozen_exact_hash(
    locked_full_256: dict[str, list[str]],
    compatibility_snapshot: Mapping[str, object],
) -> None:
    """Pin all 11,008 exported LUT values, not only preview rows."""
    expected = compatibility_snapshot["cmaps256"]

    assert locked_full_256 == expected
    assert _canonical_sha256(locked_full_256) == FULL_256_SHA256


def test_unlocked_direct_32_is_complete_but_not_shipped(
    locked_palette: dict[str, list[str]], locked_direct_32: dict[str, list[str]]
) -> None:
    """Expose a direct-OKLCH diagnostic catalog behind the explicit opt-out."""
    direct = _compile_cmaps(locked_palette, 32, luminance_lock=False)

    assert set(direct) == set(locked_direct_32)
    assert {name: len(row) for name, row in direct.items()} == dict.fromkeys(
        locked_direct_32, 32
    )
    assert direct != locked_direct_32


def test_compile_catalog_threads_policy_and_all_migrated_tone_ranges(
    monkeypatch: pytest.MonkeyPatch, v5_ssot: Mapping[str, object]
) -> None:
    """Pin every endpoint and propagate one lock through every helper call."""
    palette = cast(dict[str, list[str]], v5_ssot["palette"])
    multi_calls: list[tuple[float, float, bool]] = []
    diverging_calls: list[tuple[str, str, float, float, bool]] = []
    single_locks: list[bool] = []
    gray_locks: list[bool] = []
    cyclic_locks: list[bool] = []

    def seq_single(
        family: str,
        tone_top: float = 0.9655172091954044,
        tone_bottom: float = 0.3448275747126444,
        n: int = 256,
        *,
        luminance_lock: bool = True,
    ) -> list[str]:
        """Capture one single-hue delegation."""
        del family, tone_top, tone_bottom
        single_locks.append(luminance_lock)
        return ["#000000"] * n

    def seq_gray(
        tone_top: float = 0.9741378985632205,
        tone_bottom: float = 0.2758620597701155,
        n: int = 256,
        *,
        luminance_lock: bool = True,
    ) -> list[str]:
        """Capture the gray delegation."""
        del tone_top, tone_bottom
        gray_locks.append(luminance_lock)
        return ["#000000"] * n

    def seq_multi(
        hue_knots: list[float],
        chroma_knots: list[float],
        tone_start: float = 0.2586206810344833,
        tone_end: float = 0.9655172091954044,
        n: int = 256,
        *,
        luminance_lock: bool = True,
    ) -> list[str]:
        """Capture one multi-hue endpoint pair."""
        del hue_knots, chroma_knots
        multi_calls.append((tone_start, tone_end, luminance_lock))
        return ["#000000"] * n

    def diverging_pair(
        hex_a: str,
        hex_b: str,
        tone_end: float,
        tone_center: float = 0.9655172091954044,
        gamma: float = 0.85,
        half: int = 32,
        *,
        luminance_lock: bool = True,
    ) -> list[str]:
        """Capture one diverging endpoint contract."""
        del gamma
        diverging_calls.append(
            (hex_a, hex_b, tone_end, tone_center, luminance_lock)
        )
        return ["#000000"] * (2 * half - 1)

    def cyclic_hue(
        tone: float = 0.6724137706896566,
        n: int = 256,
        *,
        luminance_lock: bool = True,
    ) -> list[str]:
        """Capture the isoluminant hue delegation."""
        del tone
        cyclic_locks.append(luminance_lock)
        return ["#000000"] * n

    def cyclic_twilight(
        hue_a: float, hue_b: float, n: int = 256, *, luminance_lock: bool = True
    ) -> list[str]:
        """Capture one twilight delegation."""
        del hue_a, hue_b
        cyclic_locks.append(luminance_lock)
        return ["#000000"] * n

    monkeypatch.setattr(_cmaps, "seq_single", seq_single)
    monkeypatch.setattr(_cmaps, "seq_gray", seq_gray)
    monkeypatch.setattr(_cmaps, "seq_multi", seq_multi)
    monkeypatch.setattr(_cmaps, "diverging_pair", diverging_pair)
    monkeypatch.setattr(_cmaps, "cyclic_hue", cyclic_hue)
    monkeypatch.setattr(_cmaps, "cyclic_twilight", cyclic_twilight)

    _compile_cmaps(palette, 32, luminance_lock=False)

    assert {
        name: (start, end)
        for name, (start, end, lock) in zip(
            MULTI_TONE_RANGES, multi_calls, strict=True
        )
        if lock is False
    } == MULTI_TONE_RANGES
    endpoint_names = {
        row[6]: family
        for family, row in palette.items()
        if family
        in {
            "blue",
            "red",
            "orange",
            "teal",
            "rose",
            "green",
            "purple",
            "cyan",
            "amber",
            "violet",
            "lime",
            "indigo",
            "gray",
        }
    }
    actual_diverging = {
        (endpoint_names[hex_a], endpoint_names[hex_b]): tone_end
        for hex_a, hex_b, tone_end, tone_center, lock in diverging_calls
        if tone_center == 0.9655172091954044 and lock is False
    }
    assert actual_diverging == DIVERGING_TONES
    assert single_locks == [False] * 19
    assert gray_locks == [False]
    assert cyclic_locks == [False, False, False]


def test_blue_red_endpoint_is_mean_modeled_relative_y_tone() -> None:
    """Use normalized output Y, not either endpoint's chromatic OKLCH L."""
    blue_tone = 0.6666552828543492
    red_tone = 0.6604297972306236
    mean_tone = (blue_tone + red_tone) / 2.0

    assert mean_tone == 0.6635425400424864
    assert mean_tone**3 == pytest.approx(
        0.29215028397305226, abs=1e-16, rel=0.0
    )


def test_blue_red_tone_is_derived_from_the_supplied_locked_palette(
    monkeypatch: pytest.MonkeyPatch, v5_ssot: Mapping[str, object]
) -> None:
    """Reject a hardcoded shipped mean by changing blue6/red6 dynamically."""
    palette = {
        name: list(row)
        for name, row in cast(
            Mapping[str, list[str]], v5_ssot["palette"]
        ).items()
    }
    palette["blue"][6] = "#000000"
    palette["red"][6] = "#ffffff"
    observed: list[float] = []

    def flat_row(*args: object, **kwargs: object) -> list[str]:
        """Stand in for unrelated helpers while preserving requested count."""
        del args
        count = kwargs.get("n", 256)
        assert isinstance(count, int)
        return ["#000000"] * count

    def capture_diverging(*args: object, **kwargs: object) -> list[str]:
        """Capture the first dynamic endpoint tone passed by the catalog."""
        tone = kwargs.get("tone_end", args[2] if len(args) > 2 else None)
        half = kwargs.get("half", 32)
        assert isinstance(tone, float)
        assert isinstance(half, int)
        observed.append(tone)
        return ["#000000"] * (2 * half - 1)

    for helper_name in (
        "seq_single",
        "seq_gray",
        "seq_multi",
        "cyclic_hue",
        "cyclic_twilight",
    ):
        monkeypatch.setattr(_cmaps, helper_name, flat_row)
    monkeypatch.setattr(_cmaps, "diverging_pair", capture_diverging)

    _compile_cmaps(palette, 32, luminance_lock=True)

    endpoint_tones = []
    for value in (palette["blue"][6], palette["red"][6]):
        rgb = tuple(
            int(value[index : index + 2], 16) / 255.0 for index in (1, 3, 5)
        )
        relative_y = _conversion.relative_y_srgb_d65(
            cast(tuple[float, float, float], rgb)
        )
        endpoint_tones.append(float(np.cbrt(relative_y)))
    expected = sum(endpoint_tones) / 2.0

    assert expected == 0.5
    assert observed[0] == expected


def test_catalog_inventory_and_removed_names_remain_stable(
    locked_direct_32: dict[str, list[str]], v5_ssot: Mapping[str, object]
) -> None:
    """Keep all 43 names while retaining deliberate v5 removals."""
    colormaps = cast(Mapping[str, object], v5_ssot["colormaps"])
    counts = cast(Mapping[str, int], colormaps["counts"])

    assert counts == {
        "single": 20,
        "multi": 9,
        "diverging": 11,
        "cyclic": 3,
        "total": 43,
        "qualitative_registered": 2,
    }
    for name in ("coast", "blue_red_deep", "blue_red_soft"):
        assert name not in locked_direct_32
