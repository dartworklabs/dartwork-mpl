"""Quoted CVD / uniformity floats in the color docs must equal the computed
value from the shipped gates (mirrors test_docs_count_claims.py for floats).

The color-system-v5 docs quote several accessibility / uniformity numbers as
prose (``10.3``, ``9.0``, the Okabe-Ito benchmark, aurora-vs-viridis cv). Those
are exactly the numbers that silently rot when the ruler changes — e.g. the
tritan model swap left a stale Machado-era "11.1" Okabe-Ito benchmark and a
"twice as uniform / cv 0.044" aurora claim that was not a same-protocol
measurement. Each entry below pairs a claim-regex with the callable that
recomputes the true number from ``_gates`` on the *shipped* palette, and the
regex MUST match — so rewording a claim can't silently disable its check.

Cycle / benchmark numbers are compared at 1 dp (``gate_cycle`` rounds to 1 dp);
colormap cv numbers at 3 dp (``gate_seq_cmap`` rounds to 3 dp).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import matplotlib as mpl
import pytest

from dartwork_mpl.colors._gates import gate_cycle, gate_seq_cmap
from dartwork_mpl.colors._generated import CMAPS_256, CYCLES

_REPO = Path(__file__).resolve().parents[1]

# Okabe-Ito 8-color CVD-safe palette (Wong 2011, Nature Methods) — the
# accessibility benchmark the v5 gate is calibrated against. Measured under the
# SAME shipped Brettel-1997 tritan gate as dc.octave, so the comparison is
# apples-to-apples.
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
    return float(gate_seq_cmap(seq)["cv"])


def _viridis_cv() -> float:
    vir = [
        mpl.colors.to_hex(mpl.colormaps["viridis"](i / 31)) for i in range(32)
    ]
    return float(gate_seq_cmap(vir)["cv"])


# (relpath, one-group claim-regex, expected-value callable, decimal places)
_CLAIMS: list[tuple[str, str, Callable[[], float], int]] = [
    # --- design.md: cycle floors quoted at "10.3 (common) / 8.3 (tritan)" ---
    (
        "docs/color_system/design.md",
        r"`dc\.octave` measures (\d+\.\d+) \(common\)",
        _default_common,
        1,
    ),
    (
        "docs/color_system/design.md",
        r"\(common\) / (\d+\.\d+) \(tritan\)",
        _default_tritan,
        1,
    ),
    (
        "docs/color_system/design.md",
        r"`dc\.octave_print`, (\d+\.\d+) /",
        _print_common,
        1,
    ),
    (
        "docs/color_system/design.md",
        r"`dc\.octave_print`, \d+\.\d+ / (\d+\.\d+)",
        _print_tritan,
        1,
    ),
    # --- design.md: aurora vs viridis uniformity (same-protocol @32) ---
    # (\s+ tolerates the line wrap "ΔE cv\n0.063 vs 0.086")
    (
        "docs/color_system/design.md",
        r"ΔE cv\s+(\d\.\d+)\s+vs\s+\d\.\d+",
        _aurora_cv,
        3,
    ),
    (
        "docs/color_system/design.md",
        r"ΔE cv\s+\d\.\d+\s+vs\s+(\d\.\d+)",
        _viridis_cv,
        3,
    ),
    ("docs/color_system/design.md", r"ΔE cv (\d\.\d+), L", _aurora_cv, 3),
    (
        "docs/color_system/design.md",
        r"against viridis \(cv (\d\.\d+),",
        _viridis_cv,
        3,
    ),
    # --- colormaps.md: same aurora vs viridis claim ---
    (
        "docs/color_system/colormaps.md",
        r"ΔE cv (\d\.\d+) vs \d\.\d+",
        _aurora_cv,
        3,
    ),
    (
        "docs/color_system/colormaps.md",
        r"ΔE cv \d\.\d+ vs (\d\.\d+)",
        _viridis_cv,
        3,
    ),
    # --- categorical-palettes.md: default cycle + Okabe-Ito benchmark ---
    (
        "docs/color_system/categorical-palettes.md",
        r"min ΔE00 (\d+\.\d+)",
        _default_common,
        1,
    ),
    (
        "docs/color_system/categorical-palettes.md",
        r"Okabe-Ito benchmark's (\d+\.\d+)",
        _okabe_common,
        1,
    ),
    (
        "docs/color_system/categorical-palettes.md",
        r"default cycle's (\d+\.\d+) actually beats",
        _default_tritan,
        1,
    ),
    (
        "docs/color_system/categorical-palettes.md",
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
