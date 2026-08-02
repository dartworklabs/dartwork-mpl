"""Quoted CVD / uniformity floats in the color docs must equal the computed
value from the shipped gates (mirrors test_docs_count_claims.py for floats).

The color-system-v5 docs quote several model-specific collision / uniformity numbers as
prose (``10.3``, ``9.0``, the Okabe-Ito benchmark, aurora-vs-viridis cv). Those
are exactly the numbers that silently rot when the ruler changes — e.g. the
tritan model swap left a stale Machado-era "11.1" Okabe-Ito benchmark and a
"twice as uniform / cv 0.044" aurora claim that was not a same-protocol
measurement. Each entry below pairs a claim-regex with the callable that
recomputes the true number from the independent compatibility oracle on the
*shipped* palette, and the regex MUST match — so rewording a claim can't
silently disable its check.

Cycle / benchmark numbers are compared at 1 dp (``gate_cycle`` rounds to 1 dp);
colormap ΔEOK cv and chroma-fit R² numbers at 3 dp.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import matplotlib as mpl
import pytest

from dartwork_mpl._colors._compatibility_metrics import ordered_quality
from dartwork_mpl._colors._gates import gate_cycle
from dartwork_mpl._colors._generated import CMAPS_256, CYCLES
from tests._docs_color_oracles import chroma_r_squared

_REPO = Path(__file__).resolve().parents[1]

# Okabe-Ito 8-color reference palette (Wong 2011, Nature Methods) — the
# model-specific collision benchmark used for the historical v5 search.
# Measurements use the same shipped Machado-2009 protan/deutan and BVM-1997
# tritan diagnostics as dc.octave, so the comparison is same-protocol.
_OKABE_ITO = [
    "#000000",
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
]


def _default_common() -> float:
    return float(gate_cycle(CYCLES["octave"])["common_min"])


def _default_tritan() -> float:
    return float(gate_cycle(CYCLES["octave"])["tritan"])


def _print_common() -> float:
    return float(gate_cycle(CYCLES["octave_print"])["common_min"])


def _print_tritan() -> float:
    return float(gate_cycle(CYCLES["octave_print"])["tritan"])


def _okabe_common() -> float:
    return float(gate_cycle(_OKABE_ITO)["common_min"])


def _okabe_tritan() -> float:
    return float(gate_cycle(_OKABE_ITO)["tritan"])


def _aurora_cv() -> float:
    # Exactly what the theory figure renders: the shipped 256-LUT sampled at
    # 32 stops (NOT the SSOT direct-render swatches_32).
    seq = [CMAPS_256["aurora"][round(i * 255 / 31)] for i in range(32)]
    value = ordered_quality(seq)["step_cv"]
    assert isinstance(value, float)
    return value


def _viridis_cv() -> float:
    vir = [
        mpl.colors.to_hex(mpl.colormaps["viridis"](i / 31)) for i in range(32)
    ]
    value = ordered_quality(vir)["step_cv"]
    assert isinstance(value, float)
    return value


# (relpath, one-group claim-regex, expected-value callable, decimal places)
_CLAIMS: list[tuple[str, str, Callable[[], float], int]] = [
    # --- design-rationale.md: cycle floors quoted at "10.3 (common) / 8.3 (tritan)" ---
    (
        "docs/color_system/design-rationale.md",
        r"`dc\.octave` measures (\d+\.\d+) \(common\)",
        _default_common,
        1,
    ),
    (
        "docs/color_system/design-rationale.md",
        r"\(common\) / (\d+\.\d+) \(tritan\)",
        _default_tritan,
        1,
    ),
    (
        "docs/color_system/design-rationale.md",
        r"`dc\.octave_print`, (\d+\.\d+) /",
        _print_common,
        1,
    ),
    (
        "docs/color_system/design-rationale.md",
        r"`dc\.octave_print`, \d+\.\d+ / (\d+\.\d+)",
        _print_tritan,
        1,
    ),
    # --- design-rationale.md: authored-catalog chroma Fourier fit ---
    (
        "docs/color_system/design-rationale.md",
        r"in-sample R² of (\d\.\d{3})",
        chroma_r_squared,
        3,
    ),
    # --- design-rationale.md: bounded same-protocol benchmark at 32 stops ---
    # (\s+ tolerates the line wrap "ΔEOK cv\n0.063 vs 0.086")
    (
        "docs/color_system/design-rationale.md",
        r"ΔEOK cv\s+(\d\.\d+)\s+vs\s+\d\.\d+",
        _aurora_cv,
        3,
    ),
    (
        "docs/color_system/design-rationale.md",
        r"ΔEOK cv\s+\d\.\d+\s+vs\s+(\d\.\d+)",
        _viridis_cv,
        3,
    ),
    (
        "docs/color_system/design-rationale.md",
        r"ΔEOK cv (\d\.\d+),",
        _aurora_cv,
        3,
    ),
    (
        "docs/color_system/design-rationale.md",
        r"viridis reports (\d\.\d+),",
        _viridis_cv,
        3,
    ),
    # --- colormaps.md: same bounded benchmark and measured values ---
    (
        "docs/color_system/colormaps.md",
        r"ΔEOK cv (\d\.\d+) vs \d\.\d+",
        _aurora_cv,
        3,
    ),
    (
        "docs/color_system/colormaps.md",
        r"ΔEOK cv \d\.\d+ vs (\d\.\d+)",
        _viridis_cv,
        3,
    ),
    # --- palettes.md: default cycle + Okabe-Ito benchmark ---
    (
        "docs/color_system/palettes.md",
        r"min ΔE00 (\d+\.\d+)",
        _default_common,
        1,
    ),
    (
        "docs/color_system/palettes.md",
        r"Okabe-Ito benchmark's (\d+\.\d+)",
        _okabe_common,
        1,
    ),
    (
        "docs/color_system/palettes.md",
        r"default\s+cycle's (\d+\.\d+) actually beats",
        _default_tritan,
        1,
    ),
    (
        "docs/color_system/palettes.md",
        r"beats Okabe-Ito's (\d+\.\d+)",
        _okabe_tritan,
        1,
    ),
]


@pytest.mark.parametrize(
    ("relpath", "claim_re", "expected", "ndp"),
    _CLAIMS,
    ids=[f"{c[0].split('/')[-1]}~{i}" for i, c in enumerate(_CLAIMS)],
)
def test_docs_float_claim_matches_gate(
    relpath: str, claim_re: str, expected: Callable[[], float], ndp: int
) -> None:
    text = (_REPO / relpath).read_text(encoding="utf-8")
    m = re.search(claim_re, text)
    assert m, (
        f"{relpath}: claim regex {claim_re!r} not found — if the prose was "
        f"reworded, update the regex so the check stays live"
    )
    quoted = round(float(m.group(1)), ndp)
    computed = round(expected(), ndp)
    assert quoted == computed, (
        f"{relpath}: claim {m.group(1)!r} (regex {claim_re!r}) != computed "
        f"{computed} from the shipped gate — the docs float drifted from the "
        f"code"
    )


def test_design_rationale_names_the_four_color_metric_layers() -> None:
    """Metric roles stay explicit without inventing unrelated luminance."""
    path = _REPO / "docs" / "color_system" / "design-rationale.md"
    text = path.read_text(encoding="utf-8")
    flat = re.sub(r"\s+", " ", text)

    for term in (
        "OKLab L",
        "ΔEOK",
        "OKLCH",
        "relative_y",
        "CIELAB",
        "ΔE00",
        "CVD",
        "WCAG relative luminance",
    ):
        assert term in flat, f"{path}: missing four-layer term {term!r}"

    assert re.search(r"construction.{0,240}OKLab L", flat, re.I)
    assert re.search(r"output.{0,240}relative_y", flat, re.I)
    assert re.search(r"validation[- ]only.{0,240}CIELAB", flat, re.I)
    assert "ΔEOK×100" in flat  # noqa: RUF001
    assert "closely related decoded-sRGB Y-like calculations" in flat
    assert "separately pinned coefficient conventions" in flat
    assert "WCAG adds a pairwise contrast ratio" in flat


@pytest.mark.parametrize(
    "relpath",
    ["docs/color_system/design-rationale.md", "docs/color_system/colormaps.md"],
    ids=("rationale", "colormaps"),
)
def test_aurora_float_claim_is_a_bounded_same_protocol_benchmark(
    relpath: str,
) -> None:
    """Keep the measured comparison local to its identical 32-stop sample."""
    text = (_REPO / relpath).read_text(encoding="utf-8")
    flat = re.sub(r"\s+", " ", text)

    assert "bounded same-protocol benchmark" in flat
    assert "32-stop" in flat
    assert (
        "does not prove universal perceptual uniformity" in flat
        or "not a claim of perfect uniformity" in flat
    )


def test_current_color_prose_has_no_cielab_construction_claims() -> None:
    """CIELAB remains a finished-output diagnostic, never the recipe axis."""
    paths = [
        _REPO / "docs" / "color_system" / "design-rationale.md",
        _REPO / "docs" / "color_system" / "colors.md",
        _REPO / "docs" / "color_system" / "colormaps.md",
        _REPO / "docs" / "design_system" / "index.md",
        _REPO / "docs" / "index.md",
        _REPO / "docs" / "_static" / "dartwork-discrete-palette-rationale.md",
        _REPO / "src" / "dartwork_mpl" / "_colors" / "_curated.py",
    ]
    stale_claims = (
        r"lightness lives on CIELAB L\\?\*",
        r"lightness is CIELAB L\\?\*",
        r"holds? L\\?\* and hue",
        r"CIELAB L\\?\* measures lightness, OKLCH does the manipulation",
        r"designed on CIELAB L\\?\*",
        r"all fifteen chromatic families",
        r"15 family anchors",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for pattern in stale_claims:
            assert not re.search(pattern, text, re.I), (
                f"{path}: stale CIELAB construction/count claim {pattern!r}"
            )
