"""Behavioral tests for single-path NeutralTone colormap helpers."""

import inspect
from collections.abc import Callable, Mapping
from typing import cast

import pytest

from dartwork_mpl._colors import _cmaps, _tone

Rgb = tuple[float, float, float]


def _assert_keyword_lock(function: Callable[..., object]) -> None:
    """Require a true, keyword-only luminance-lock policy switch."""
    parameter = inspect.signature(function).parameters["luminance_lock"]

    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is True


def _call_helper(
    helper_name: str, *args: object, **kwargs: object
) -> list[str]:
    """Call a future helper while inspect tests own its signature contract."""
    function = cast(Callable[..., list[str]], getattr(_cmaps, helper_name))
    return function(*args, **kwargs)


@pytest.mark.parametrize(
    "helper_name",
    [
        "seq_single",
        "seq_gray",
        "seq_multi",
        "diverging_pair",
        "cyclic_hue",
        "cyclic_twilight",
    ],
)
def test_every_color_path_helper_has_keyword_only_lock(
    helper_name: str,
) -> None:
    """Thread the opt-out through every helper that constructs colors."""
    helper = cast(Callable[..., object], getattr(_cmaps, helper_name))

    _assert_keyword_lock(helper)


@pytest.mark.parametrize(
    ("helper_name", "parameter_name", "expected"),
    [
        ("seq_single", "tone_top", 0.9655172091954044),
        ("seq_single", "tone_bottom", 0.3448275747126444),
        ("seq_gray", "tone_top", 0.9741378985632205),
        ("seq_gray", "tone_bottom", 0.2758620597701155),
        ("seq_multi", "tone_start", 0.2586206810344833),
        ("seq_multi", "tone_end", 0.9655172091954044),
        ("diverging_pair", "tone_center", 0.9655172091954044),
        ("cyclic_hue", "tone", 0.6724137706896566),
    ],
)
def test_helper_defaults_pin_full_double_migrated_tones(
    helper_name: str, parameter_name: str, expected: float
) -> None:
    """Prevent rounded L* endpoints or bare-116 conversions from returning."""
    helper = getattr(_cmaps, helper_name)
    actual = inspect.signature(helper).parameters[parameter_name].default

    assert actual == expected


def test_pchip_is_monotone_and_has_no_overshoot() -> None:
    """Preserve the established monotone interpolation primitive."""
    knots = [0.0, 0.5, 1.0]
    values = [0.0, 9.0, 10.0]
    samples = [_cmaps.pchip(knots, values, index / 100) for index in range(101)]

    assert all(
        samples[index] <= samples[index + 1] + 1e-9 for index in range(100)
    )
    assert max(samples) <= 10.0 + 1e-9
    assert min(samples) >= -1e-9
    assert _cmaps.pchip([0.0, 1.0], [2.0, 4.0], 0.5) == pytest.approx(3.0)


def test_render_preserves_endpoint_count_and_hex_shape() -> None:
    """Keep dense arc-length rendering generic over float RGB paths."""
    output = _cmaps.render(
        lambda fraction: (fraction, fraction, fraction), n=32
    )

    assert len(output) == 32
    assert all(value.startswith("#") and len(value) == 7 for value in output)


@pytest.mark.parametrize("family", ["red", "blue", "teal", "yellow", "purple"])
def test_locked_single_hue_rows_match_frozen_direct_32(
    family: str, v5_ssot: Mapping[str, object]
) -> None:
    """Preserve representative locked direct-rendered sequential rows."""
    colormaps = cast(Mapping[str, object], v5_ssot["colormaps"])
    expected = cast(Mapping[str, list[str]], colormaps["swatches_32"])

    assert (
        _call_helper("seq_single", family, n=32, luminance_lock=True)
        == expected[family]
    )


def test_locked_gray_row_matches_frozen_direct_32(
    v5_ssot: Mapping[str, object],
) -> None:
    """Preserve the modeled-relative-CIE-Y-ordered gray direct preview."""
    colormaps = cast(Mapping[str, object], v5_ssot["colormaps"])
    expected = cast(Mapping[str, list[str]], colormaps["swatches_32"])

    assert (
        _call_helper("seq_gray", n=32, luminance_lock=True) == expected["gray"]
    )


def _patch_tone_primitives(
    monkeypatch: pytest.MonkeyPatch,
    render_tone: Callable[..., Rgb],
    max_chroma: Callable[..., float],
) -> None:
    """Patch either supported import style for construction primitives."""
    monkeypatch.setattr(_tone, "render_oklch_at_tone", render_tone)
    monkeypatch.setattr(_tone, "max_chroma_at_tone", max_chroma)
    if hasattr(_cmaps, "render_oklch_at_tone"):
        monkeypatch.setattr(_cmaps, "render_oklch_at_tone", render_tone)
    if hasattr(_cmaps, "max_chroma_at_tone"):
        monkeypatch.setattr(_cmaps, "max_chroma_at_tone", max_chroma)


def test_twilight_uses_migrated_seam_and_center_tones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin the two internal twilight endpoints after offline migration."""
    observed: list[tuple[float, bool]] = []

    def render_tone(
        *, tone: float, chroma: float, hue: float, luminance_lock: bool
    ) -> Rgb:
        """Capture construction coordinates without solving color math."""
        del chroma, hue
        observed.append((tone, luminance_lock))
        return (tone, tone, tone)

    def max_chroma(hue_degrees: float, tone: float) -> float:
        """Return a non-limiting deterministic chroma boundary."""
        del hue_degrees, tone
        return 0.4

    def sample_render(
        swatch_at: Callable[[float], Rgb],
        n: int = 256,
        dense: int = 513,
        closed: bool = False,
    ) -> list[str]:
        """Evaluate only the seam, center, and closing seam."""
        del n, dense, closed
        for fraction in (0.0, 0.5, 1.0):
            swatch_at(fraction)
        return ["#000000", "#000000", "#000000"]

    _patch_tone_primitives(monkeypatch, render_tone, max_chroma)
    monkeypatch.setattr(_cmaps, "render", sample_render)

    _call_helper("cyclic_twilight", 238.0, 16.0, n=3, luminance_lock=False)

    assert observed == [
        (0.939655141091956, False),
        (0.29310343850574777, False),
        (0.939655141091956, False),
    ]


def test_cyclic_hue_threads_unlocked_policy_to_every_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep direct OKLCH diagnostic rendering explicit on the hue ring."""
    locks: list[bool] = []

    def render_tone(
        *, tone: float, chroma: float, hue: float, luminance_lock: bool
    ) -> Rgb:
        """Capture the lock while returning an in-range placeholder."""
        del tone, chroma, hue
        locks.append(luminance_lock)
        return (0.5, 0.5, 0.5)

    def max_chroma(hue_degrees: float, tone: float) -> float:
        """Return a fixed safe boundary for every hue probe."""
        del hue_degrees, tone
        return 0.1

    _patch_tone_primitives(monkeypatch, render_tone, max_chroma)

    row = _call_helper("cyclic_hue", n=7, luminance_lock=False)

    assert len(row) == 7
    assert locks == [False] * 7
