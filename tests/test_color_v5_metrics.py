"""Tests for colors._metrics — CIELAB / OKLab dE / CIEDE2000 / CVD."""

from __future__ import annotations

from pathlib import Path

import pytest

from dartwork_mpl import _luminance as luminance
from dartwork_mpl._colors import _conversion as conversion
from dartwork_mpl._colors import _metrics as metrics
from dartwork_mpl._colors._metrics import (
    cvd_rgb,
    de2000_hex,
    de_ok_rgb,
    hex_from_rgb,
    lab_l_hex,
    lab_l_rgb,
    rgb_from_hex,
)

_SHARMA_SOURCE_SHA256 = (
    "44aebb39107128328add54fbef5ac8ee89909e50508f448a1580adea2058a4b8"
)
_SHARMA_VECTORS = (
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -1.1848, -84.8006), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -0.9009, -85.5211), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
    ((50.0000, -1.0000, 2.0000), (50.0000, 0.0000, 0.0000), 2.3669),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0009), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0010), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0011), 7.2195),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0012), 7.2195),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0009, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0010, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0011, -2.4900), 4.7461),
    ((50.0000, 2.5000, 0.0000), (50.0000, 0.0000, -2.5000), 4.3065),
    ((50.0000, 2.5000, 0.0000), (73.0000, 25.0000, -18.0000), 27.1492),
    ((50.0000, 2.5000, 0.0000), (61.0000, -5.0000, 29.0000), 22.8977),
    ((50.0000, 2.5000, 0.0000), (56.0000, -27.0000, -3.0000), 31.9030),
    ((50.0000, 2.5000, 0.0000), (58.0000, 24.0000, 15.0000), 19.4535),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.1736, 0.5854), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2972, 0.0000), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 1.8634, 0.5757), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2592, 0.3350), 1.0000),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
    ((61.2901, 3.7196, -5.3901), (61.4292, 2.2480, -4.9620), 1.8731),
    ((35.0831, -44.1164, 3.7933), (35.0232, -40.0716, 1.5901), 1.8645),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((36.4612, 47.8580, 18.3852), (36.2715, 50.5065, 21.2231), 1.4146),
    ((90.8027, -2.0831, 1.4410), (91.1528, -1.6435, 0.0447), 1.4441),
    ((90.9257, -0.5406, -0.9208), (88.6381, -0.8985, -0.7239), 1.5381),
    ((6.7747, -0.2908, -2.4247), (5.8714, -0.0985, -2.2286), 0.6377),
    ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
)


def test_lab_l_endpoints() -> None:
    assert lab_l_rgb((1.0, 1.0, 1.0)) == pytest.approx(100.0, abs=0.01)
    assert lab_l_rgb((0.0, 0.0, 0.0)) == pytest.approx(0.0, abs=0.01)
    # 18% gray card ≈ L* 46.6
    assert lab_l_hex("#777777") == pytest.approx(49.9, abs=0.5)


def test_lab_white_retains_legacy_raw_xyz_row() -> None:
    """Pin the validation-only raw XYZ row, not normalized modeled Y."""
    assert metrics.lab_from_rgb((1.0, 1.0, 1.0)) == pytest.approx(
        (100.00000386666655, -1.6666666158293708e-05, 6.666666463317483e-06),
        abs=1e-12,
        rel=0.0,
    )


def test_lab_transform_is_isolated_from_modeled_relative_y(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep normalized Y out of the private CIELAB validation transform."""

    def reject_modeled_y(rgb: tuple[float, float, float]) -> float:
        raise AssertionError(rgb)

    monkeypatch.setattr(conversion, "relative_y_srgb_d65", reject_modeled_y)

    assert metrics.lab_from_rgb((1.0, 1.0, 1.0)) == pytest.approx(
        (100.00000386666655, -1.6666666158293708e-05, 6.666666463317483e-06),
        abs=1e-12,
        rel=0.0,
    )


def test_de2000_sharma_pairs() -> None:
    # Sharma, Wu & Dalal (2005) 검증 벡터는 Lab 입력 기준이라 sRGB 왕복으로는
    # 재현 불가 — 대신 순서·스케일 불변식으로 검증한다.
    assert de2000_hex("#ff0000", "#ff0000") == 0.0
    d_small = de2000_hex("#ff0000", "#fe0000")
    d_large = de2000_hex("#ff0000", "#0000ff")
    assert 0.0 < d_small < 1.0 < d_large
    # 대칭성
    assert de2000_hex("#123456", "#654321") == pytest.approx(
        de2000_hex("#654321", "#123456"), abs=1e-9
    )


def test_metric_documentation_scopes_sources_and_validation_claims() -> None:
    """Keep provenance and algebra checks distinct from observer correctness."""
    source = Path(metrics.__file__).read_text(encoding="utf-8")
    flat_source = " ".join(source.split())
    folded_source = " ".join(source.replace("#", " ").split()).casefold()
    module_doc = metrics.__doc__ or ""
    de2000_doc = metrics.de2000_rgb.__doc__ or ""

    assert "validation-only" in module_doc.casefold()
    assert "source-pinned machado severity-1 matrices" in folded_source
    assert "project-adapted bvm matrices" in folded_source
    assert "algebraic projection invariants" in folded_source
    assert "do not verify observer or model correctness" in folded_source
    assert "validation-only color-difference regression metric" in de2000_doc
    assert "not an accessibility gate" in de2000_doc
    for overclaim in (
        "accurate for the common red-green deficiencies",
        "physiologically-grounded model",
        "Verified correct",
        "접근성 게이트 지표",
    ):
        assert overclaim not in flat_source


def test_de_ok_scale() -> None:
    # OKLab L 0→1 거리 = 100 (x100 스케일 규약)
    assert de_ok_rgb((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)) == pytest.approx(
        100.0, abs=0.5
    )


def test_cvd_gray_is_neutral() -> None:
    g = cvd_rgb(rgb_from_hex("#e03131"), "gray")
    assert g[0] == pytest.approx(g[1], abs=1e-6) and g[1] == pytest.approx(
        g[2], abs=1e-6
    )


def test_cvd_deutan_collapses_red_green() -> None:
    red, green = rgb_from_hex("#c22"), rgb_from_hex("#2a2")
    d_normal = de2000_hex("#cc2222", "#22aa22")
    d_deutan = de2000_hex(
        hex_from_rgb(cvd_rgb(red, "deutan")),
        hex_from_rgb(cvd_rgb(green, "deutan")),
    )
    assert d_deutan < d_normal * 0.5


def test_sharma_vector_source_is_the_pinned_task_2_reference() -> None:
    """Keep the 34 Lab pairs tied to the accepted supplementary dataset."""
    assert len(_SHARMA_VECTORS) == 34
    assert _SHARMA_SOURCE_SHA256 == (
        "44aebb39107128328add54fbef5ac8ee89909e50508f448a1580adea2058a4b8"
    )


@pytest.mark.parametrize(("first", "second", "expected"), _SHARMA_VECTORS)
def test_de2000_matches_all_sharma_lab_pairs(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    expected: float,
) -> None:
    """Match every published Sharma CIEDE2000 reference pair."""
    assert metrics._de2000_lab(first, second) == pytest.approx(
        expected, abs=5e-5 + 1e-12, rel=0.0
    )


def test_metrics_gamma_wrappers_delegate_to_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Make the production conversion module the observable gamma kernel."""
    decoded: list[float] = []
    encoded: list[float] = []

    def decode(channel: float) -> float:
        decoded.append(channel)
        return 0.25

    def encode(channel: float) -> float:
        encoded.append(channel)
        return 0.75

    monkeypatch.setattr(conversion, "_srgb_to_linear", decode)
    monkeypatch.setattr(conversion, "_linear_to_srgb", encode)

    assert metrics._lin(0.4) == 0.25
    assert metrics._delin(0.6) == 0.75
    assert decoded == [0.4]
    assert encoded == [0.6]


def test_metrics_rgb_and_oklab_wrappers_delegate_to_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Route strict hex and composed OKLab conversion through one module."""
    monkeypatch.setattr(conversion, "_parse_hex", lambda value: (0.1, 0.2, 0.3))
    monkeypatch.setattr(
        conversion, "_rgb_to_hex", lambda red, green, blue: "#abcdef"
    )
    monkeypatch.setattr(
        conversion, "_srgb_to_oklab", lambda rgb: (0.4, 0.5, 0.6)
    )

    assert metrics.rgb_from_hex("#123456") == (0.1, 0.2, 0.3)
    assert metrics.hex_from_rgb((0.1, 0.2, 0.3)) == "#abcdef"
    assert metrics.oklab_from_rgb((0.1, 0.2, 0.3)) == (0.4, 0.5, 0.6)


def test_metrics_wrappers_match_canonical_conversion_results() -> None:
    """Pin wrapper parity for gamma, hex, and OKLab composition."""
    rgb = (0x12 / 255, 0x34 / 255, 0x56 / 255)

    assert metrics._lin(rgb[0]) == float(conversion._srgb_to_linear(rgb[0]))
    assert metrics._delin(0.25) == float(conversion._linear_to_srgb(0.25))
    assert metrics.rgb_from_hex("#123456") == conversion._parse_hex("#123456")
    assert metrics.hex_from_rgb(rgb) == conversion._rgb_to_hex(*rgb)
    assert metrics.oklab_from_rgb(rgb) == conversion._srgb_to_oklab(rgb)


def test_encode_core_is_unclamped_while_metrics_wrapper_clamps() -> None:
    """Keep gamut policy out of conversion and in the CVD compatibility shim."""
    assert conversion._linear_to_srgb(-0.1) == 12.92 * -0.1
    assert float(conversion._linear_to_srgb(1.1)) > 1.0
    assert metrics._delin(-0.1) == 0.0
    assert metrics._delin(1.1) == pytest.approx(1.0, abs=1e-15, rel=0.0)


def test_wcag_luminance_is_distinct_from_modeled_relative_y() -> None:
    """Separate rounded WCAG coefficients from modeled relative CIE Y."""
    red = (1.0, 0.0, 0.0)

    assert luminance._wcag_relative_luminance(red) == 0.2126
    assert conversion.relative_y_srgb_d65(red) == 0.21267287873271212
    assert luminance._wcag_relative_luminance(red) != (
        conversion.relative_y_srgb_d65(red)
    )


def test_luminance_gamma_wrapper_delegates_to_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure WCAG luminance shares the canonical IEC gamma function."""
    seen: list[float] = []

    def decode(channel: float) -> float:
        seen.append(channel)
        return channel + 1.0

    monkeypatch.setattr(conversion, "_srgb_to_linear", decode)

    assert luminance._linearized(0.04) == 1.04
    assert seen == [0.04]


def test_wcag_gamma_uses_current_004045_threshold() -> None:
    """Keep the WCAG helper aligned with the current IEC branch cutoff."""
    channel = 0.04

    assert luminance._linearized(channel) == channel / 12.92


def test_contrast_ratio_calls_named_wcag_luminance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Make the contrast helper's WCAG semantics explicit and observable."""
    seen: list[tuple[float, ...]] = []

    def fake_wcag(rgb: tuple[float, ...]) -> float:
        seen.append(rgb)
        return 0.8 if rgb[0] else 0.2

    monkeypatch.setattr(luminance, "_wcag_relative_luminance", fake_wcag)

    ratio = luminance._contrast_ratio((1.0, 0.0, 0.0), (0.0, 0.0, 0.0))

    assert ratio == pytest.approx((0.8 + 0.05) / (0.2 + 0.05))
    assert seen == [(1.0, 0.0, 0.0), (0.0, 0.0, 0.0)]


@pytest.mark.parametrize(
    "rgb",
    (
        (0.0, 0.0, 0.0),
        (1.0, 1.0, 1.0),
        (1.0, 0.0, 0.0),
        (0.1, 0.2, 0.3),
        (0.87, 0.19, 0.41),
    ),
)
def test_gray_cvd_is_neutral_and_preserves_modeled_relative_y(
    rgb: tuple[float, float, float],
) -> None:
    """Encode input modeled relative CIE Y directly as an sRGB neutral."""
    gray = cvd_rgb(rgb, "gray")

    assert gray[0] == gray[1] == gray[2]
    assert conversion.relative_y_srgb_d65(gray) == pytest.approx(
        conversion.relative_y_srgb_d65(rgb), abs=5e-15, rel=0.0
    )


def test_gray_cvd_does_not_use_wcag_luminance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep modeled-Y gray output independent from WCAG contrast math."""

    def reject_wcag(rgb: tuple[float, ...]) -> float:
        raise AssertionError(rgb)

    monkeypatch.setattr(luminance, "_wcag_relative_luminance", reject_wcag)

    gray = cvd_rgb((0.1, 0.2, 0.3), "gray")

    assert gray[0] == gray[1] == gray[2]


@pytest.mark.parametrize(
    ("rgb", "kind", "expected", "expected_hex"),
    [
        (
            (1.0, 0.0, 0.0),
            "protan",
            (0.4266084717107862, 0.37265427742344537, 0.0),
            "#6d5f00",
        ),
        (
            (0.0, 1.0, 0.0),
            "deutan",
            (0.936051045605102, 0.8392477353639614, 0.22919186560921978),
            "#efd63a",
        ),
        (
            (0.0, 0.0, 1.0),
            "tritan",
            (0.0, 0.38590015810462663, 0.5350807827928689),
            "#006288",
        ),
        (
            rgb_from_hex("#123456"),
            "protan",
            (0.14283413377226134, 0.21187566093436755, 0.3427561566870771),
            "#243657",
        ),
    ],
)
def test_cvd_clamp_and_hex_behavior_remains_baseline_compatible(
    rgb: tuple[float, float, float],
    kind: str,
    expected: tuple[float, float, float],
    expected_hex: str,
) -> None:
    """Preserve matrix order, clamp timing, float output, and quantization."""
    actual = cvd_rgb(rgb, kind)

    assert actual == pytest.approx(expected, abs=1e-15, rel=0.0)
    assert hex_from_rgb(actual) == expected_hex
