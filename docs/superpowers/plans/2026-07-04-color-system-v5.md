# Color System v5 Implementation Plan

> **Superseded metric model (2026-07-14).** This plan is retained as a
> historical implementation record. Current construction uses OKLab L,
> OKLCH C/h, and ΔEOK, with physical relative Y only as an optional output
> lock. See the
> [accepted redesign](../specs/2026-07-14-oklab-centered-color-system-design.md)
> and [ADR 0001](../../adr/0001-oklab-centered-color-construction.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 스펙 `docs/superpowers/specs/2026-07-03-color-system-v5-design.md`(커밋 c82569d)의 생성 공리 색 시스템을 `dartwork_mpl.colors` 레시피 컴파일러로 구현한다 — 91-파라미터 SSOT에서 팔레트(16×10)·cycle(2)·컬러맵(42종+등록 2)을 결정론적으로 생성하고, A7 게이트를 빌드 게이트로 강제하며, §11 마이그레이션 정책(레거시 동결 + opt-in remap)을 배선한다.

**Architecture:** 순수 계산 모듈(`_metrics` → `_recipe` → `_generate` → `_gates`) 위에 카탈로그 모듈(`_cmaps`·`_cycles`)을 얹고, `_build.py`가 전부 컴파일해 `_generated.py`(커밋되는 빌드 산출물)를 쓴다. 런타임은 `_generated.py`의 동결 테이블만 읽어 matplotlib에 등록한다(임포트 시 재계산 없음). 레거시는 `_compat_v4.py`가 동결 hex로 오버레이한다.

**Tech Stack:** Python ≥3.10, numpy + matplotlib (기존 런타임 의존성만 — scipy 금지, pchip은 자체 구현), pytest.

## Global Constraints

- **SSOT**: `docs/superpowers/specs/assets/2026-07-03-color-system-v5/color_v5_ssot.json` — `_recipe.py`의 리터럴 상수는 이 파일에서 이식하며, 테스트가 코드↔JSON 일치를 강제한다. golden test가 palette·cycles·cmaps hex의 SSOT 일치를 강제한다.
- **등화·측정 프로토콜(스펙 §7·§9)**: dense 경로는 **float sRGB**로 평가(hex는 최종 1회), 멀티휴 knot 보간은 **단조 3차(Fritsch–Carlson)**, 게이트/스와치 샘플은 **n-stop 직접 렌더**(round() 다운샘플 금지).
- **결정론**: `python -m dartwork_mpl.colors._build` 재실행 시 `_generated.py` byte-identical. `datetime.now()`·랜덤 금지.
- **빌드 게이트**: A7(L\* 단조, cv≤0.08, cycle 최악-CVD ΔE00≥10, 그레이 단조) + cmap 게이트 실패 시 빌드 실패(exit≠0).
- **마이그레이션(스펙 §11)**: 기존 `dc.*` 토큰은 동결 hex 유지 + 접근 시 1회 DeprecationWarning(`dm.color()` 경로), 재매핑은 `dm.set_palette_version(5)` opt-in. 내부 mplstyle은 이번에 v5로 전환.
- **파일명 컨벤션**: 스펙 §14의 `recipe.py` 등은 repo 컨벤션에 따라 `_recipe.py` 등 언더스코어 private 모듈로 구현(공개 API는 `colors/__init__.py`와 `dartwork_mpl/__init__.py` 경유).
- **코드 스타일**: 기존 repo 스타일(타입 힌트, NumPy docstring, ruff/mypy 통과). 커밋 전 `pre-commit` 훅 통과.
- **작업 브랜치**: `feat/color-system-v5` (이 워크트리). 커밋 메시지는 Conventional Commits.

## 파일 구조 (전체 조감)

```
src/dartwork_mpl/colors/
├── __init__.py       # (수정) cmap()/cycle()/set_palette_version 등 export
├── _metrics.py       # 신규 — CIELAB·OKLab ΔE·CIEDE2000·Machado CVD
├── _recipe.py        # 신규 — 91-number SSOT 상수 + 푸리에 + derive_family
├── _generate.py      # 신규 — 스와치 솔버·등화·compile_family·gray
├── _gates.py         # 신규 — A7 + cmap 게이트
├── _cmaps.py         # 신규 — 42종 카탈로그 생성기 + pchip
├── _cycles.py        # 신규 — cycle 동결 스펙 + cycler 헬퍼
├── _semantic.py      # 신규 — 로케일 시맨틱 토큰
├── _build.py         # 신규 — 빌드 CLI → _generated.py
├── _generated.py     # 신규 — 빌드 산출물 (커밋됨)
├── _compat_v4.py     # 신규 — 레거시 dc 동결 + set_palette_version
└── _loader.py        # 수정 — v5 토큰 등록 + 레거시 오버레이
src/dartwork_mpl/cmap.py            # 수정 — 레거시 로더 유지 + 2건 리네임 반영
src/dartwork_mpl/asset/cmap/        # 수정 — aurora.txt·teal_rose.txt 리네임
src/dartwork_mpl/asset/mplstyle/    # 수정 — base 등 prop_cycle·image.cmap 재배선
src/dartwork_mpl/style.py           # 수정 — 시맨틱 토큰 훅
tests/test_color_v5_*.py            # 신규 — 태스크별 테스트
```

golden test 공용 헬퍼(여러 태스크에서 사용):

```python
# tests/conftest.py 에 추가
import json
from pathlib import Path

import pytest

_SSOT_PATH = (
    Path(__file__).parents[1]
    / "docs/superpowers/specs/assets/2026-07-03-color-system-v5/color_v5_ssot.json"
)


@pytest.fixture(scope="session")
def v5_ssot() -> dict:
    """설계 확정 SSOT (스펙 §7 — 구현이 이 값을 재생산해야 함)."""
    return json.loads(_SSOT_PATH.read_text(encoding="utf-8"))
```

---

### Task 1: `_metrics.py` — 지표 3원화 커널

**Files:**
- Create: `src/dartwork_mpl/colors/_metrics.py`
- Test: `tests/test_color_v5_metrics.py`
- Modify: `tests/conftest.py` (위 `v5_ssot` fixture 추가)

**Interfaces:**
- Consumes: 없음 (순수 수학, `dartwork_mpl.colors._conversion`의 sRGB↔OKLab 행렬과 동일 계수 사용)
- Produces:
  - `lab_from_rgb(rgb: tuple[float, float, float]) -> tuple[float, float, float]` — CIELAB(D65)
  - `lab_l_rgb(rgb) -> float` / `lab_l_hex(hexstr: str) -> float`
  - `oklab_from_rgb(rgb) -> tuple[float, float, float]`
  - `de_ok_rgb(rgb1, rgb2) -> float` — OKLab 유클리드 ×100
  - `de2000_rgb(rgb1, rgb2) -> float` / `de2000_hex(h1, h2) -> float` — CIEDE2000
  - `cvd_rgb(rgb, kind: str) -> tuple` — kind ∈ {"protan","deutan","tritan","gray"} (Machado 2009 severity 1.0; gray는 등L\* 무채색)
  - `hex_from_rgb(rgb) -> str` / `rgb_from_hex(hexstr) -> tuple`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_metrics.py
"""Tests for colors._metrics — CIELAB / OKLab dE / CIEDE2000 / CVD."""

from __future__ import annotations

import pytest

from dartwork_mpl.colors._metrics import (
    cvd_rgb,
    de2000_hex,
    de_ok_rgb,
    hex_from_rgb,
    lab_l_hex,
    lab_l_rgb,
    rgb_from_hex,
)


def test_lab_l_endpoints():
    assert lab_l_rgb((1.0, 1.0, 1.0)) == pytest.approx(100.0, abs=0.01)
    assert lab_l_rgb((0.0, 0.0, 0.0)) == pytest.approx(0.0, abs=0.01)
    # 18% gray card ≈ L* 46.6
    assert lab_l_hex("#777777") == pytest.approx(49.9, abs=0.5)


def test_de2000_sharma_pairs():
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


def test_de_ok_scale():
    # OKLab L 0→1 거리 = 100 (×100 스케일 규약)
    assert de_ok_rgb((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)) == pytest.approx(100.0, abs=0.5)


def test_cvd_gray_preserves_lightness():
    g = cvd_rgb(rgb_from_hex("#e03131"), "gray")
    assert g[0] == pytest.approx(g[1], abs=1e-6) and g[1] == pytest.approx(g[2], abs=1e-6)
    assert lab_l_rgb(g) == pytest.approx(lab_l_hex("#e03131"), abs=0.2)


def test_cvd_deutan_collapses_red_green():
    red, green = rgb_from_hex("#c22"), rgb_from_hex("#2a2")
    d_normal = de2000_hex("#cc2222", "#22aa22")
    d_deutan = de2000_hex(
        hex_from_rgb(cvd_rgb(red, "deutan")), hex_from_rgb(cvd_rgb(green, "deutan"))
    )
    assert d_deutan < d_normal * 0.5
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_color_v5_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: dartwork_mpl.colors._metrics`

- [ ] **Step 3: 구현**

```python
# src/dartwork_mpl/colors/_metrics.py
"""Perceptual metric kernel — CIELAB L*, OKLab dE, CIEDE2000, Machado CVD.

스펙 §6 지표 3원화: 등화=OKLab dE, 접근성 게이트=CIEDE2000, 밝기·그레이=CIELAB L*.
모든 함수는 float sRGB(0..1 tuple)를 1급 입력으로 받는다 — 등화 파이프라인이
8-bit hex 양자화 노이즈에 오염되지 않게 하기 위함(스펙 §9 공통 프로토콜 1).
"""

from __future__ import annotations

import math

__all__ = [
    "cvd_rgb",
    "de2000_hex",
    "de2000_rgb",
    "de_ok_rgb",
    "hex_from_rgb",
    "lab_from_rgb",
    "lab_l_hex",
    "lab_l_rgb",
    "oklab_from_rgb",
    "rgb_from_hex",
]

_M_RGB2XYZ = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)
_WHITE = (0.95047, 1.0, 1.08883)

# Machado, Oliveira & Fernandes (2009), severity 1.0.
# NOTE: tritan 행렬은 스펙 §12 판정에 따라 Brettel–Viénot–Mollon(1997)로 교체
# 예정이나 v5 게이트 산출값은 Machado 기준으로 확정되었다 — SSOT 재현을 위해
# Machado를 유지하고, BVM 교체는 게이트 재산출과 함께 별도 사이클에서 수행한다.
_MACHADO = {
    "protan": ((0.152286, 1.052583, -0.204868),
               (0.114503, 0.786281, 0.099216),
               (-0.003882, -0.048116, 1.051998)),
    "deutan": ((0.367322, 0.860646, -0.227968),
               (0.280085, 0.672501, 0.047413),
               (-0.011820, 0.042940, 0.968881)),
    "tritan": ((1.255528, -0.076749, -0.178779),
               (-0.078411, 0.930809, 0.147602),
               (0.004733, 0.691367, 0.303900)),
}


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _delin(c: float) -> float:
    c = min(max(c, 0.0), 1.0)
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def rgb_from_hex(hexstr: str) -> tuple[float, float, float]:
    h = hexstr.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def hex_from_rgb(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(min(max(v, 0.0), 1.0) * 255):02x}" for v in rgb)


def lab_from_rgb(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    lin = [_lin(c) for c in rgb]
    xyz = [sum(m * v for m, v in zip(row, lin)) for row in _M_RGB2XYZ]
    f = []
    for v, w in zip(xyz, _WHITE):
        t = v / w
        f.append(t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116)
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def lab_l_rgb(rgb: tuple[float, float, float]) -> float:
    return lab_from_rgb(rgb)[0]


def lab_l_hex(hexstr: str) -> float:
    return lab_l_rgb(rgb_from_hex(hexstr))


def oklab_from_rgb(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = (_lin(c) for c in rgb)
    lm = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    mm = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    sm = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    lm, mm, sm = lm ** (1 / 3), mm ** (1 / 3), sm ** (1 / 3)
    return (0.2104542553 * lm + 0.7936177850 * mm - 0.0040720468 * sm,
            1.9779984951 * lm - 2.4285922050 * mm + 0.4505937099 * sm,
            0.0259040371 * lm + 0.7827717662 * mm - 0.8086757660 * sm)


def de_ok_rgb(rgb1: tuple, rgb2: tuple) -> float:
    """OKLab 유클리드 거리 ×100 (등화·설계 지표 — 스펙 §6)."""
    return math.dist(oklab_from_rgb(rgb1), oklab_from_rgb(rgb2)) * 100


def de2000_rgb(rgb1: tuple, rgb2: tuple) -> float:
    """CIEDE2000 (접근성 게이트 지표 — 스펙 §6)."""
    L1, a1, b1 = lab_from_rgb(rgb1)
    L2, a2, b2 = lab_from_rgb(rgb2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb**7 / (Cb**7 + 25**7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        dh = h2p - h1p
        dhp = dh - 360 if dh > 180 else (dh + 360 if dh < -180 else dh)
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)
    Lbp, Cbp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    else:
        s, d = h1p + h2p, abs(h1p - h2p)
        hbp = (s + 360) / 2 if (d > 180 and s < 360) else \
              ((s - 360) / 2 if (d > 180 and s >= 360) else s / 2)
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30))
         + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6))
         - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dth = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp**7 / (Cbp**7 + 25**7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dth)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                     + Rt * (dCp / Sc) * (dHp / Sh))


def de2000_hex(h1: str, h2: str) -> float:
    return de2000_rgb(rgb_from_hex(h1), rgb_from_hex(h2))


def cvd_rgb(rgb: tuple, kind: str) -> tuple[float, float, float]:
    """CVD 시뮬레이션 (protan/deutan/tritan) 또는 등L* 그레이 변환."""
    if kind == "gray":
        l_star = lab_l_rgb(rgb)
        fy = (l_star + 16) / 116
        y = fy**3 if fy**3 > 216 / 24389 else (116 * fy - 16) * 27 / 24389
        v = _delin(y)
        return (v, v, v)
    lin = [_lin(c) for c in rgb]
    out = [sum(m * v for m, v in zip(row, lin)) for row in _MACHADO[kind]]
    return tuple(_delin(c) for c in out)  # type: ignore[return-value]
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_color_v5_metrics.py -v`
Expected: PASS (5/5)

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_metrics.py tests/test_color_v5_metrics.py tests/conftest.py
git commit -m "feat(colors): add v5 metric kernel (CIELAB/OKLab dE/CIEDE2000/CVD)"
```

---

### Task 2: `_recipe.py` — 91-number SSOT 상수

**Files:**
- Create: `src/dartwork_mpl/colors/_recipe.py`
- Test: `tests/test_color_v5_recipe.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `FAMILY_PARAMS: dict[str, FamilyParams]` — 15 family × 8필드 frozen dataclass (`h0, dh, gamma, tp, cmax, floor, cend, c0`)
  - `FAMILIES: tuple[str, ...]` — 15 chromatic family 순서 (red→pink)
  - `FOURIER: dict[str, tuple[float, ...]]` — `cmax_k3`·`floor_k3`·`cend_k2`·`c0_k2`
  - `L_TOP=96.0, SHAPE_Q=1.2, SHAPE_R=1.5, GAMUT_CHROMA_FRAC=0.97`
  - `GRAY_FLOOR=28.0, GRAY_TINT_HUE=250, GRAY_C_PROFILE: tuple[float, ...]` (10)
  - `fourier_eval(coef, h_deg) -> float`
  - `mid_hue(p: FamilyParams) -> float` — `(h0 + dh * 0.5**gamma) % 360`
  - `derive_family(h0, dh, gamma, tp) -> FamilyParams` — 푸리에에서 유도 + 그리드 반올림 (신규 family 확장용)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_recipe.py
"""Tests for colors._recipe — 91-number SSOT constants."""

from __future__ import annotations

import pytest

from dartwork_mpl.colors._recipe import (
    FAMILIES,
    FAMILY_PARAMS,
    FOURIER,
    GRAY_C_PROFILE,
    derive_family,
    fourier_eval,
    mid_hue,
)


def test_families_complete():
    assert len(FAMILIES) == 15
    assert FAMILIES[0] == "red" and FAMILIES[-1] == "pink"
    assert set(FAMILY_PARAMS) == set(FAMILIES)


def test_params_match_ssot(v5_ssot):
    for fam, p in FAMILY_PARAMS.items():
        ref = v5_ssot["params"][fam]
        for field in ("h0", "dh", "gamma", "tp", "cmax", "floor", "cend", "c0"):
            assert getattr(p, field) == pytest.approx(ref[field]), (fam, field)


def test_fourier_match_ssot(v5_ssot):
    for key in ("cmax_k3", "floor_k3", "cend_k2", "c0_k2"):
        assert list(FOURIER[key]) == pytest.approx(v5_ssot["fourier"][key])


def test_derive_within_one_grid_step():
    # 스펙 §7: 곡선 유도값과 표는 그리드 1스텝(cmax 0.005·floor 1·c 0.05)까지
    # 어긋날 수 있고 표가 우선한다. 현행 60값 중 3값이 1스텝 차이.
    mismatch = 0
    for fam in FAMILIES:
        p = FAMILY_PARAMS[fam]
        d = derive_family(p.h0, p.dh, p.gamma, p.tp)
        assert abs(d.cmax - p.cmax) <= 0.005 + 1e-9, fam
        assert abs(d.floor - p.floor) <= 1.0 + 1e-9, fam
        assert abs(d.cend - p.cend) <= 0.05 + 1e-9, fam
        assert abs(d.c0 - p.c0) <= 0.05 + 1e-9, fam
        mismatch += sum(
            getattr(d, f) != getattr(p, f) for f in ("cmax", "floor", "cend", "c0")
        )
    assert mismatch <= 3


def test_gray_profile_len():
    assert len(GRAY_C_PROFILE) == 10


def test_fourier_eval_shape():
    # k=3 → 7계수, k=2 → 5계수
    assert fourier_eval((1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), 123.0) == 1.0
    assert mid_hue(FAMILY_PARAMS["red"]) == pytest.approx(
        (16.0 + 11.0 * 0.5**1.10) % 360, abs=1e-9
    )
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_color_v5_recipe.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 구현**

```python
# src/dartwork_mpl/colors/_recipe.py
"""91-number SSOT — 스펙 §7의 자유 60 + 푸리에 24 + 상수 7.

표(FAMILY_PARAMS)가 운영 SSOT이고 푸리에 곡선은 신규 family 확장 메커니즘이다
(유도값과 표가 그리드 1스텝 어긋날 수 있으며 표가 우선 — 스펙 §7).
값의 출처: docs/superpowers/specs/assets/2026-07-03-color-system-v5/color_v5_ssot.json
(tests/test_color_v5_recipe.py 가 코드↔JSON 일치를 강제한다).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "FAMILIES",
    "FAMILY_PARAMS",
    "FOURIER",
    "GAMUT_CHROMA_FRAC",
    "GRAY_C_PROFILE",
    "GRAY_FLOOR",
    "GRAY_TINT_HUE",
    "L_TOP",
    "SHAPE_Q",
    "SHAPE_R",
    "FamilyParams",
    "derive_family",
    "fourier_eval",
    "mid_hue",
]


@dataclass(frozen=True)
class FamilyParams:
    h0: float      # 색상 앵커 (step0 OKLCH hue)
    dh: float      # 드리프트 총량 (deg)
    gamma: float   # 드리프트 타이밍
    tp: float      # 채도 정점 위치
    cmax: float    # 정점 채도 (유도)
    floor: float   # 밝기 바닥 L* (유도)
    cend: float    # 어두운 끝 채도 잔존율 (유도)
    c0: float      # 파스텔 시작 채도 비율 (유도)


FAMILIES: tuple[str, ...] = (
    "red", "rose", "orange", "amber", "yellow", "lime", "green", "teal",
    "cyan", "sky", "blue", "indigo", "violet", "purple", "pink",
)

# 스펙 §7 확정 파라미터 표 (반올림 SSOT) — h·dh 1°, gamma·tp·c 0.05,
# cmax 0.005, floor 정수 그리드.
FAMILY_PARAMS: dict[str, FamilyParams] = {
    "red":    FamilyParams(16, +11, 1.10, 0.85, 0.210, 42, 0.90, 0.10),
    "rose":   FamilyParams(3, +14, 1.00, 0.85, 0.210, 40, 0.85, 0.10),
    "orange": FamilyParams(77, -41, 1.30, 0.85, 0.190, 54, 1.00, 0.15),
    "amber":  FamilyParams(88, -44, 1.40, 0.65, 0.185, 57, 1.00, 0.15),
    "yellow": FamilyParams(99, -46, 1.50, 0.45, 0.180, 60, 1.00, 0.15),
    "lime":   FamilyParams(122, +11, 0.60, 0.45, 0.190, 56, 0.85, 0.15),
    "green":  FamilyParams(149, -3, 0.60, 0.50, 0.185, 51, 0.75, 0.15),
    "teal":   FamilyParams(176, -13, 0.60, 0.45, 0.155, 47, 0.70, 0.15),
    "cyan":   FamilyParams(202, +13, 0.85, 0.45, 0.115, 44, 0.75, 0.15),
    "sky":    FamilyParams(220, +14, 0.85, 0.60, 0.130, 43, 0.80, 0.15),
    "blue":   FamilyParams(238, +15, 0.85, 0.75, 0.165, 42, 0.85, 0.15),
    "indigo": FamilyParams(273, -5, 1.65, 0.85, 0.210, 39, 0.85, 0.10),
    "violet": FamilyParams(298, -12, 1.25, 0.85, 0.230, 37, 0.85, 0.10),
    "purple": FamilyParams(319, +0, 1.00, 0.75, 0.220, 37, 0.85, 0.05),
    "pink":   FamilyParams(350, +18, 0.85, 0.85, 0.210, 39, 0.85, 0.05),
}

# 전역 hue 푸리에 곡선 (확장 유도용 — 상수항 + cos/sin 교대)
FOURIER: dict[str, tuple[float, ...]] = {
    "cmax_k3": (0.184409, 0.036835, -7.1e-05, -0.011187, -0.022258, 0.000429, 0.014637),
    "floor_k3": (45.816711, -3.776384, 9.500538, -4.011493, 0.266656, 0.687222, -1.346282),
    "cend_k2": (0.848962, 0.070533, 0.053148, -0.07045, 0.025104),
    "c0_k2": (0.128378, -0.049482, 0.02872, -0.015143, 0.011463),
}

# 전역 상수 (7)
L_TOP = 96.0
SHAPE_Q = 1.2
SHAPE_R = 1.5
GAMUT_CHROMA_FRAC = 0.97
GRAY_FLOOR = 28.0
GRAY_TINT_HUE = 250
GRAY_C_PROFILE: tuple[float, ...] = (
    0.003, 0.005, 0.007, 0.009, 0.010, 0.011, 0.011, 0.010, 0.008, 0.006,
)


def fourier_eval(coef: tuple[float, ...], h_deg: float) -> float:
    h = math.radians(h_deg)
    k = (len(coef) - 1) // 2
    v = coef[0]
    for i in range(1, k + 1):
        v += coef[2 * i - 1] * math.cos(i * h) + coef[2 * i] * math.sin(i * h)
    return float(v)


def mid_hue(p: FamilyParams) -> float:
    return (p.h0 + p.dh * 0.5**p.gamma) % 360


def _grid(v: float, g: float) -> float:
    return round(round(v / g) * g, 10)


def derive_family(h0: float, dh: float, gamma: float, tp: float) -> FamilyParams:
    """신규 family 확장 — 푸리에 곡선에서 유도 파라미터를 계산해 그리드 반올림."""
    hm = (h0 + dh * 0.5**gamma) % 360
    return FamilyParams(
        h0=h0, dh=dh, gamma=gamma, tp=tp,
        cmax=_grid(fourier_eval(FOURIER["cmax_k3"], hm), 0.005),
        floor=float(round(fourier_eval(FOURIER["floor_k3"], hm))),
        cend=_grid(fourier_eval(FOURIER["cend_k2"], hm), 0.05),
        c0=_grid(fourier_eval(FOURIER["c0_k2"], hm), 0.05),
    )
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_color_v5_recipe.py -v`
Expected: PASS (6/6)

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_recipe.py tests/test_color_v5_recipe.py
git commit -m "feat(colors): add v5 recipe SSOT (91 numbers: 60 free + 24 Fourier + 7 constants)"
```

---

### Task 3: `_generate.py` — 스와치 솔버 + 연속 등화 + compile_family

**Files:**
- Create: `src/dartwork_mpl/colors/_generate.py`
- Test: `tests/test_color_v5_generate.py`

**Interfaces:**
- Consumes: `_metrics` (`lab_l_rgb`, `de_ok_rgb`, `hex_from_rgb`), `_recipe` (전 상수), `._color.Color` (OKLCH→sRGB gamut 매핑)
- Produces:
  - `solve_swatch_rgb(hue_deg, chroma, l_target) -> tuple[float,float,float]` — OKLCH L 이진 탐색으로 CIELAB L\* 타깃 적중 (float sRGB)
  - `gamut_max_chroma(hue_deg, l_target) -> float`
  - `shape(t, tp, c0, cend) -> float` — A3 공통 형상 (`sin^1.2` 상승 → `t^1.5` 하강)
  - `swatch(p: FamilyParams, t: float) -> tuple` — A2~A4 레시피 (float sRGB)
  - `equalize(swatch_at, n, dense=121) -> list[tuple]` — 누적 OKLab ΔE 역보간 + 코드 반복 등화(cv<0.015, ≤14회). **엔드포인트 고정** (t=0, t=1)
  - `compile_family(p) -> list[str]` — 10-step hex
  - `compile_gray() -> list[str]` — A6 (L\* 96→28 균등 + 쿨 틴트)
  - `compile_palette() -> dict[str, list[str]]` — 15 + gray

- [ ] **Step 1: 실패하는 테스트 작성 (golden — 구현 전체를 SSOT로 고정)**

```python
# tests/test_color_v5_generate.py
"""Golden tests — compile_palette() must reproduce the approved SSOT exactly."""

from __future__ import annotations

import pytest

from dartwork_mpl.colors._generate import (
    compile_family,
    compile_gray,
    compile_palette,
    solve_swatch_rgb,
)
from dartwork_mpl.colors._metrics import lab_l_rgb
from dartwork_mpl.colors._recipe import FAMILY_PARAMS


def test_solve_swatch_hits_l_target():
    for h, c, lt in ((238.0, 0.12, 55.0), (99.0, 0.15, 80.0), (16.0, 0.18, 45.0)):
        rgb = solve_swatch_rgb(h, c, lt)
        assert lab_l_rgb(rgb) == pytest.approx(lt, abs=0.05)


def test_compile_blue_matches_ssot(v5_ssot):
    assert compile_family(FAMILY_PARAMS["blue"]) == v5_ssot["palette"]["blue"]


def test_compile_gray_matches_ssot(v5_ssot):
    assert compile_gray() == v5_ssot["palette"]["gray"]


def test_full_palette_matches_ssot(v5_ssot):
    pal = compile_palette()
    assert set(pal) == set(v5_ssot["palette"])
    for fam, row in pal.items():
        assert row == v5_ssot["palette"][fam], fam
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_color_v5_generate.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 구현**

```python
# src/dartwork_mpl/colors/_generate.py
"""Recipe compiler — 스와치 솔버 + 연속(float) 공간 OKLab 등화 (스펙 §7).

등화는 반드시 float sRGB에서 한다: dense 경로를 hex로 평가하면 스텝당 dE가
8-bit 양자화 오차에 묻혀 호장 적분이 노이즈에 지배된다(스펙 §9 프로토콜 1).
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Callable

from ._color import Color
from ._metrics import de_ok_rgb, hex_from_rgb, lab_l_rgb
from ._recipe import (
    FAMILIES,
    FAMILY_PARAMS,
    GRAY_C_PROFILE,
    GRAY_FLOOR,
    GRAY_TINT_HUE,
    L_TOP,
    SHAPE_Q,
    SHAPE_R,
    FamilyParams,
)

__all__ = [
    "compile_family",
    "compile_gray",
    "compile_palette",
    "equalize",
    "gamut_max_chroma",
    "shape",
    "solve_swatch_rgb",
    "swatch",
]

Rgb = tuple[float, float, float]


def solve_swatch_rgb(hue_deg: float, chroma: float, l_target: float) -> Rgb:
    """OKLCH L 이진 탐색 — gamut-map된 float sRGB의 CIELAB L*가 타깃에 오도록."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if lab_l_rgb(Color.from_oklch(mid, chroma, hue_deg).to_rgb()) < l_target:
            lo = mid
        else:
            hi = mid
    return Color.from_oklch((lo + hi) / 2, chroma, hue_deg).to_rgb()


def gamut_max_chroma(hue_deg: float, l_target: float) -> float:
    """해당 hue에서 CIELAB L* 타깃을 만족하는 최대 in-gamut OKLCH chroma (근사)."""
    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        if lab_l_rgb(Color.from_oklch(mid, 0.04, hue_deg).to_rgb()) < l_target:
            lo = mid
        else:
            hi = mid
    l_ok = (lo + hi) / 2
    c_lo, c_hi = 0.0, 0.40
    for _ in range(22):
        c_mid = (c_lo + c_hi) / 2
        if Color.from_oklch(l_ok, c_mid, hue_deg).in_gamut():
            c_lo = c_mid
        else:
            c_hi = c_mid
    return c_lo


def shape(t: float, tp: float, c0: float, cend: float) -> float:
    """A3 공통 채도 형상 — sin^q 상승 → 정점 tp → t^r 하강."""
    if t <= tp:
        return c0 + (1 - c0) * math.sin(math.pi / 2 * min(max(t / tp, 0.0), 1.0)) ** SHAPE_Q
    u = min(max((t - tp) / (1 - tp), 0.0), 1.0)
    return 1 - (1 - cend) * u**SHAPE_R


def swatch(p: FamilyParams, t: float) -> Rgb:
    """A2(floor)·A3(채도)·A4(드리프트) 레시피 — t∈[0,1], 0=밝음 1=어두움."""
    l_t = L_TOP + (p.floor - L_TOP) * t
    h = (p.h0 + p.dh * t**p.gamma) % 360
    c = p.cmax * shape(t, p.tp, p.c0, p.cend)
    return solve_swatch_rgb(h, c, l_t)


def equalize(swatch_at: Callable[[float], Rgb], n: int, dense: int = 121) -> list[Rgb]:
    """A5 — 누적 OKLab dE 역보간 배치 + 코드 dE 반복 등화 (엔드포인트 고정)."""
    ts_d = [i / (dense - 1) for i in range(dense)]
    pts = [swatch_at(t) for t in ts_d]
    cum = [0.0]
    for i in range(1, dense):
        cum.append(cum[-1] + de_ok_rgb(pts[i - 1], pts[i]))
    total = cum[-1]
    ts = []
    for k in range(n):
        tgt = total * k / (n - 1)
        i = min(max(bisect_left(cum, tgt), 1), dense - 1)
        f = (tgt - cum[i - 1]) / (cum[i] - cum[i - 1] or 1)
        ts.append(min(max(ts_d[i - 1] + f * (ts_d[i] - ts_d[i - 1]), 0.0), 1.0))
    ts[0], ts[-1] = 0.0, 1.0
    row = [swatch_at(t) for t in ts]
    for _ in range(14):
        d = [de_ok_rgb(row[i], row[i + 1]) for i in range(n - 1)]
        cumd = [0.0]
        for v in d:
            cumd.append(cumd[-1] + v)
        tot = cumd[-1]
        mean = tot / (n - 1)
        cv = (sum((x - mean) ** 2 for x in d) / (n - 1)) ** 0.5 / mean
        if cv < 0.015:
            break
        new_ts = [0.0]
        for k in range(1, n - 1):
            tgt = tot * k / (n - 1)
            i = min(max(bisect_left(cumd, tgt), 1), n - 1)
            f = (tgt - cumd[i - 1]) / (cumd[i] - cumd[i - 1] or 1)
            new_ts.append(ts[i - 1] + f * (ts[i] - ts[i - 1]))
        new_ts.append(1.0)
        ts = new_ts
        row = [row[0]] + [swatch_at(t) for t in ts[1:-1]] + [row[-1]]
    return row


def compile_family(p: FamilyParams) -> list[str]:
    return [hex_from_rgb(r) for r in equalize(lambda t: swatch(p, t), n=10)]


def compile_gray() -> list[str]:
    """A6 — L* 균등 사다리 + 약한 쿨 틴트 (등화 불필요: L* 균등이 곧 dE 균등)."""
    out = []
    for k in range(10):
        l_t = L_TOP + (GRAY_FLOOR - L_TOP) * k / 9
        out.append(hex_from_rgb(solve_swatch_rgb(GRAY_TINT_HUE, GRAY_C_PROFILE[k], l_t)))
    return out


def compile_palette() -> dict[str, list[str]]:
    pal = {fam: compile_family(FAMILY_PARAMS[fam]) for fam in FAMILIES}
    pal["gray"] = compile_gray()
    return pal
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_color_v5_generate.py -v`
Expected: PASS (4/4). golden 불일치 시 hex 몇 개가 다른지 출력을 보고 원인 추적
(가장 흔한 원인: 이진 탐색 반복 수·`shape` 경계·엔드포인트 고정 누락).
매크로 시간: 전체 팔레트 컴파일 ~10s 수준(허용).

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_generate.py tests/test_color_v5_generate.py
git commit -m "feat(colors): add v5 recipe compiler with continuous-space equalization"
```

---

### Task 4: `_gates.py` — A7 하드 게이트

**Files:**
- Create: `src/dartwork_mpl/colors/_gates.py`
- Test: `tests/test_color_v5_gates.py`

**Interfaces:**
- Consumes: `_metrics` (`lab_l_hex`, `de_ok_rgb`, `de2000_hex`, `cvd_rgb`, `rgb_from_hex`, `hex_from_rgb`)
- Produces:
  - `gate_ladder(hexes) -> dict` — `{"mono": bool, "cv": float}` (L\* 엄격 단조 + 이웃 OKLab ΔE cv)
  - `gate_cycle(hexes) -> dict` — `{"min00": float}` 최악-CVD(정상+3형) 쌍 최소 ΔE00
  - `gate_seq_cmap(hexes) -> dict` — `{"mono","cv","gray_mono","L_span"}` (0.4 L\* 허용오차 = 8-bit 그래뉼)
  - `gate_div_cmap(hexes) -> dict` — `{"apex_pct"}`
  - `gate_topo_cmap(hexes) -> dict` — `{"sea_mono","land_mono","coast_break_dL"}`
  - `gate_cyclic_cmap(hexes) -> dict` — `{"seam_ratio"}`
  - `check_all(palette, cycles, cmaps) -> list[str]` — 위반 메시지 리스트 (빈 리스트 = 통과)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_gates.py
"""Tests for colors._gates — A7 hard gates."""

from __future__ import annotations

from dartwork_mpl.colors._gates import (
    gate_cycle,
    gate_cyclic_cmap,
    gate_div_cmap,
    gate_ladder,
    gate_seq_cmap,
    gate_topo_cmap,
)


def test_palette_ladders_pass(v5_ssot):
    for fam, row in v5_ssot["palette"].items():
        g = gate_ladder(row)
        assert g["mono"], fam
        assert g["cv"] <= 0.08, (fam, g["cv"])


def test_cycle_gate_pass(v5_ssot):
    pal = v5_ssot["palette"]
    hexes = [pal[f][k] for f, k in v5_ssot["cycle_default"]["spec"]]
    assert gate_cycle(hexes)["min00"] >= 10.0


def test_gate_detects_violations():
    # 인위 실패: 비단조 사다리
    bad = ["#f0f0f0", "#101010", "#e0e0e0"] + ["#808080"] * 7
    assert not gate_ladder(bad)["mono"]
    # 인위 실패: 붕괴 cycle (tab10류 red-green)
    assert gate_cycle(["#d62728", "#2ca02c", "#1f77b4"])["min00"] < 10.0


def test_cmap_gates_pass_ssot(v5_ssot):
    sw = v5_ssot["colormaps"]["swatches_32"]
    gexp = v5_ssot["colormaps"]["gates"]
    for name, hexes in sw.items():
        exp = gexp[name]
        if "apex_pct" in exp:
            assert gate_div_cmap(hexes)["apex_pct"] == 50.0, name
        elif "sea_mono" in exp:
            g = gate_topo_cmap(hexes)
            assert g["sea_mono"] and g["land_mono"], name
        elif "seam_ratio" in exp:
            assert gate_cyclic_cmap(hexes)["seam_ratio"] <= 1.5, name
        else:
            g = gate_seq_cmap(hexes)
            assert g["mono"] and g["gray_mono"], name
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_color_v5_gates.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 구현**

```python
# src/dartwork_mpl/colors/_gates.py
"""A7 hard gates — 실패한 산출물은 출하 불가 (스펙 §5 A7·§9)."""

from __future__ import annotations

from ._metrics import cvd_rgb, de2000_hex, de_ok_rgb, hex_from_rgb, lab_l_hex, rgb_from_hex

__all__ = [
    "check_all",
    "gate_cycle",
    "gate_cyclic_cmap",
    "gate_div_cmap",
    "gate_ladder",
    "gate_seq_cmap",
    "gate_topo_cmap",
]

_CVD_KINDS = ("protan", "deutan", "tritan")


def _cv(hexes: list[str]) -> float:
    rgbs = [rgb_from_hex(h) for h in hexes]
    d = [de_ok_rgb(rgbs[i], rgbs[i + 1]) for i in range(len(rgbs) - 1)]
    m = sum(d) / len(d)
    return (sum((x - m) ** 2 for x in d) / len(d)) ** 0.5 / m


def _mono(ls: list[float], tol: float = 0.0) -> bool:
    return all(ls[i] > ls[i + 1] - tol for i in range(len(ls) - 1)) or \
           all(ls[i] < ls[i + 1] + tol for i in range(len(ls) - 1))


def gate_ladder(hexes: list[str]) -> dict:
    ls = [lab_l_hex(h) for h in hexes]
    return {"mono": all(ls[i] > ls[i + 1] for i in range(len(ls) - 1)),
            "cv": round(_cv(hexes), 4)}


def gate_cycle(hexes: list[str]) -> dict:
    worst = float("inf")
    for kind in ("normal",) + _CVD_KINDS:
        if kind == "normal":
            sim = hexes
        else:
            sim = [hex_from_rgb(cvd_rgb(rgb_from_hex(h), kind)) for h in hexes]
        for i in range(len(sim)):
            for j in range(i + 1, len(sim)):
                worst = min(worst, de2000_hex(sim[i], sim[j]))
    return {"min00": round(worst, 1)}


def gate_seq_cmap(hexes: list[str]) -> dict:
    """32-stop 직접 렌더 스와치 기준. 단조 허용오차 0.4 L* = 8-bit 그래뉼."""
    ls = [lab_l_hex(h) for h in hexes]
    gl = [lab_l_hex(hex_from_rgb(cvd_rgb(rgb_from_hex(h), "gray"))) for h in hexes]
    return {"mono": _mono(ls, 0.4), "gray_mono": _mono(gl, 0.4),
            "cv": round(_cv(hexes), 3), "L_span": round(abs(ls[-1] - ls[0]), 1)}


def gate_div_cmap(hexes: list[str]) -> dict:
    """Diverging: the brightest region must sit at the center (apex 50%).

    Reports the midpoint of the max-L* plateau (within 0.5 L* = one 8-bit
    granule), NOT a single argmax. A symmetric diverging sampled to an EVEN
    length has its true apex *between* the two center swatches (e.g. indices
    15/16 of a 32-stop), which are equally bright by construction — a single
    `.index(max())` biases to one side and reads 48.4%. The plateau midpoint
    lands at exactly 50% for a symmetric map of any parity, and drifts off 50%
    (flagging the gate) only when the arms are genuinely asymmetric.
    """
    ls = [lab_l_hex(h) for h in hexes]
    top = max(ls)
    plateau = [i for i, v in enumerate(ls) if v >= top - 0.5]
    apex = (plateau[0] + plateau[-1]) / 2
    return {"apex_pct": round(100 * apex / (len(ls) - 1), 1)}


def gate_topo_cmap(hexes: list[str]) -> dict:
    mid = len(hexes) // 2
    def half_mono(seg: list[str]) -> bool:
        return _mono([lab_l_hex(h) for h in seg], 0.4)
    return {"sea_mono": half_mono(hexes[:mid]), "land_mono": half_mono(hexes[mid:]),
            "coast_break_dL": round(abs(lab_l_hex(hexes[mid]) - lab_l_hex(hexes[mid - 1])), 1)}


def gate_cyclic_cmap(hexes: list[str]) -> dict:
    rgbs = [rgb_from_hex(h) for h in hexes]
    d = [de_ok_rgb(rgbs[i], rgbs[i + 1]) for i in range(len(rgbs) - 1)]
    seam = de_ok_rgb(rgbs[-1], rgbs[0])
    return {"seam_ratio": round(seam / (sum(d) / len(d)), 2)}


def check_all(palette: dict, cycles: dict, cmaps: dict) -> list[str]:
    """빌드 게이트 러너 — 위반 메시지 리스트 반환 (빈 리스트 = 전부 통과)."""
    bad: list[str] = []
    for fam, row in palette.items():
        g = gate_ladder(row)
        if not g["mono"]:
            bad.append(f"palette {fam}: L* not monotone")
        if g["cv"] > 0.08:
            bad.append(f"palette {fam}: cv {g['cv']} > 0.08")
    for name, hexes in cycles.items():
        g = gate_cycle(hexes)
        if g["min00"] < 10.0:
            bad.append(f"cycle {name}: worst-CVD dE00 {g['min00']} < 10")
    for name, hexes in cmaps.items():
        kind = name.split(".", 1)[0]
        if kind == "div":
            if gate_div_cmap(hexes)["apex_pct"] != 50.0:
                bad.append(f"cmap {name}: apex != 50%")
        elif kind == "topo":
            g = gate_topo_cmap(hexes)
            if not (g["sea_mono"] and g["land_mono"]):
                bad.append(f"cmap {name}: half not monotone")
        elif kind == "cyc":
            if gate_cyclic_cmap(hexes)["seam_ratio"] > 1.5:
                bad.append(f"cmap {name}: seam ratio > 1.5")
        else:
            g = gate_seq_cmap(hexes)
            if not (g["mono"] and g["gray_mono"]):
                bad.append(f"cmap {name}: mono/gray_mono fail")
    return bad
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_color_v5_gates.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_gates.py tests/test_color_v5_gates.py
git commit -m "feat(colors): add A7 hard gates (mono/cv/worst-CVD dE00/gray-mono)"
```

---

### Task 5: `_cycles.py` — categorical cycle 동결

**Files:**
- Create: `src/dartwork_mpl/colors/_cycles.py`
- Test: `tests/test_color_v5_cycles.py`

**Interfaces:**
- Consumes: 없음 (스펙 §8 확정 spec을 리터럴로 동결 — 전수 탐색은 설계 단계에서 종료)
- Produces:
  - `CYCLE_SPECS: dict[str, tuple[tuple[str, int], ...]]` — `{"default": ((blue,6),(orange,9),(green,5),(pink,3),(amber,7),(violet,8),(cyan,8)), "print": (...8...)}`
  - `cycle_hexes(name, palette) -> list[str]` — spec을 팔레트 dict에 적용

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_cycles.py
"""Tests for colors._cycles — frozen cycle specs (스펙 §8)."""

from __future__ import annotations

from dartwork_mpl.colors._cycles import CYCLE_SPECS, cycle_hexes
from dartwork_mpl.colors._gates import gate_cycle


def test_specs_match_ssot(v5_ssot):
    assert [list(x) for x in CYCLE_SPECS["default"]] == v5_ssot["cycle_default"]["spec"]
    assert [list(x) for x in CYCLE_SPECS["print"]] == v5_ssot["cycle_print"]["spec"]


def test_hexes_and_gate(v5_ssot):
    pal = v5_ssot["palette"]
    default = cycle_hexes("default", pal)
    assert len(default) == 7
    assert default[0] == pal["blue"][6]
    assert gate_cycle(default)["min00"] >= 10.0
    assert gate_cycle(cycle_hexes("print", pal))["min00"] >= 10.0
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/test_color_v5_cycles.py -v` → FAIL (module not found)

- [ ] **Step 3: 구현**

```python
# src/dartwork_mpl/colors/_cycles.py
"""Categorical cycles — 스펙 §8 전수 탐색 결과의 동결 스펙.

탐색(ΔE00 게이트 + 라인 안전 대역)은 설계 단계에서 끝났다. 여기서는 (family,
step) 좌표만 동결하고, 빌드가 팔레트에 적용해 hex를 얻은 뒤 게이트를 재검증한다.
"""

from __future__ import annotations

__all__ = ["CYCLE_SPECS", "cycle_hexes"]

CYCLE_SPECS: dict[str, tuple[tuple[str, int], ...]] = {
    # 기본 7 chromatic — 라인 안전(L* 42~78, CR>=2.2), 최악-CVD dE00 10.3.
    # gray는 격자·기준선용으로 예약(멤버 아님 — 스펙 §8).
    "default": (
        ("blue", 6), ("orange", 9), ("green", 5), ("pink", 3),
        ("amber", 7), ("violet", 8), ("cyan", 8),
    ),
    # 인쇄 8색 — 명도 분산(전쌍 dL* >= 6.1), 최악-CVD dE00 11.0.
    "print": (
        ("blue", 9), ("orange", 2), ("green", 9), ("pink", 6),
        ("amber", 6), ("purple", 5), ("cyan", 3), ("gray", 8),
    ),
}


def cycle_hexes(name: str, palette: dict[str, list[str]]) -> list[str]:
    return [palette[fam][step] for fam, step in CYCLE_SPECS[name]]
```

- [ ] **Step 4: 통과 확인** — `pytest tests/test_color_v5_cycles.py -v` → PASS (2/2)

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_cycles.py tests/test_color_v5_cycles.py
git commit -m "feat(colors): freeze v5 categorical cycle specs (default 7 + print 8)"
```

---

### Task 6: `_cmaps.py` (1/2) — render 등화기 + 단일색·gray

**Files:**
- Create: `src/dartwork_mpl/colors/_cmaps.py`
- Test: `tests/test_color_v5_cmaps_single.py`

**Interfaces:**
- Consumes: `_generate` (`solve_swatch_rgb`, `gamut_max_chroma`), `_metrics` (`de_ok_rgb`, `hex_from_rgb`), `_recipe` (`FAMILY_PARAMS`, `FAMILIES`)
- Produces:
  - `render(swatch_at, n=256, dense=513, closed=False) -> list[str]` — float 경로 등화, hex는 최종 1회
  - `pchip(knots, vals, t) -> float` — 단조 3차 Hermite (Fritsch–Carlson)
  - `unwrap_hues(hs) -> list[float]` — 최단경로 hue 언랩
  - `seq_single(fam, n=256) -> list[str]` (L\* 96→24, 어두운 끝 채도 롤오프 `1-0.90*u^1.4`)
  - `seq_gray(n=256) -> list[str]` (L\* 97→16)
  - (2/2에서 추가) `seq_multi`, `seq_topo`, `diverging_pair`, `cyclic_hue`, `cyclic_twilight`, `CATALOG`, `compile_cmaps`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_cmaps_single.py
"""Golden tests — single-hue/gray cmaps must reproduce SSOT swatches_32."""

from __future__ import annotations

import pytest

from dartwork_mpl.colors._cmaps import pchip, render, seq_gray, seq_single
from dartwork_mpl.colors._generate import solve_swatch_rgb


def test_pchip_monotone_no_overshoot():
    knots, vals = [0.0, 0.5, 1.0], [0.0, 9.0, 10.0]
    samples = [pchip(knots, vals, i / 100) for i in range(101)]
    assert all(samples[i] <= samples[i + 1] + 1e-9 for i in range(100))
    assert max(samples) <= 10.0 + 1e-9 and min(samples) >= -1e-9
    # 2-knot 폴백 = 선형
    assert pchip([0.0, 1.0], [2.0, 4.0], 0.5) == pytest.approx(3.0)


def test_render_endpoint_and_count():
    out = render(lambda t: solve_swatch_rgb(238, 0.10, 90 - 60 * t), n=32)
    assert len(out) == 32
    assert all(isinstance(h, str) and h.startswith("#") for h in out)


@pytest.mark.parametrize("fam", ["red", "blue", "teal", "yellow", "purple"])
def test_seq_single_matches_ssot(fam, v5_ssot):
    assert seq_single(fam, n=32) == v5_ssot["colormaps"]["swatches_32"][fam]


def test_seq_gray_matches_ssot(v5_ssot):
    assert seq_gray(n=32) == v5_ssot["colormaps"]["swatches_32"]["gray"]
```

- [ ] **Step 2: 실패 확인** — `pytest tests/test_color_v5_cmaps_single.py -v` → FAIL

- [ ] **Step 3: 구현**

```python
# src/dartwork_mpl/colors/_cmaps.py
"""Colormap catalog compiler — 42종 (스펙 §9).

프로토콜(§9 공통): float 경로 등화(hex 최종 1회) · pchip knot 보간 ·
게이트/스와치는 n-stop 직접 렌더.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from collections.abc import Callable

from ._generate import gamut_max_chroma, solve_swatch_rgb
from ._metrics import de_ok_rgb, hex_from_rgb
from ._recipe import FAMILIES, FAMILY_PARAMS

__all__ = ["pchip", "render", "seq_gray", "seq_single", "unwrap_hues"]

Rgb = tuple[float, float, float]


def render(swatch_at: Callable[[float], Rgb], n: int = 256, dense: int = 513,
           closed: bool = False) -> list[str]:
    """dense float 평가 → 누적 OKLab dE 역보간 → 정확한 t*에서 재평가 → hex 1회."""
    ts = [i / (dense - 1) for i in range(dense)]
    pts = [swatch_at(t) for t in ts]
    cum = [0.0]
    for i in range(1, dense):
        cum.append(cum[-1] + de_ok_rgb(pts[i - 1], pts[i]))
    if closed:
        cum.append(cum[-1] + de_ok_rgb(pts[-1], pts[0]))
    total = cum[-1]
    out: list[Rgb] = []
    m = n if not closed else n + 1
    for k in range(m):
        tgt = total * k / (m - 1)
        i = min(max(bisect_left(cum, tgt), 1), dense - 1)
        f = (tgt - cum[i - 1]) / (cum[i] - cum[i - 1] or 1)
        t_star = min(max(ts[i - 1] + f * (ts[i] - ts[i - 1]), 0.0), 1.0)
        out.append(swatch_at(t_star))
    return [hex_from_rgb(p) for p in (out[:n] if closed else out)]


def pchip(knots: list[float], vals: list[float], t: float) -> float:
    """단조 3차 Hermite (Fritsch–Carlson) — knot C1 연속, 오버슈트 없음."""
    n = len(knots)
    if n == 2:
        f = (t - knots[0]) / (knots[1] - knots[0])
        return vals[0] + f * (vals[1] - vals[0])
    h = [knots[i + 1] - knots[i] for i in range(n - 1)]
    d = [(vals[i + 1] - vals[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    t = min(max(t, knots[0]), knots[-1])
    i = min(max(bisect_left(knots, t) - 1, 0), n - 2)
    s = (t - knots[i]) / h[i]
    h00, h10 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s
    h01, h11 = -2 * s**3 + 3 * s**2, s**3 - s**2
    return h00 * vals[i] + h10 * h[i] * m[i] + h01 * vals[i + 1] + h11 * h[i] * m[i + 1]


def unwrap_hues(hs: list[float]) -> list[float]:
    """인접 knot이 최단경로(±180°)를 지나도록 언랩."""
    out = [hs[0]]
    for h in hs[1:]:
        d = ((h - out[-1] + 180) % 360) - 180
        out.append(out[-1] + d)
    return out


def seq_single(fam: str, L_top: float = 96.0, L_bot: float = 24.0, n: int = 256) -> list[str]:
    """A8 — family 레시피의 광역 L* 연속 렌더링 (팔레트 floor 미상속)."""
    p = FAMILY_PARAMS[fam]

    def at(t: float) -> Rgb:
        l_t = L_top + (L_bot - L_top) * t
        h = (p.h0 + p.dh * t**p.gamma) % 360
        if t <= p.tp:
            c = p.cmax * (0.12 + 0.88 * math.sin(math.pi / 2 * t / p.tp) ** 1.2)
        else:
            u = (t - p.tp) / (1 - p.tp)
            c = p.cmax * (1 - 0.90 * u**1.4)
        c = min(c, gamut_max_chroma(h, l_t) * 0.97)
        return solve_swatch_rgb(h, c, l_t)

    return render(at, n=n)


def seq_gray(L_top: float = 97.0, L_bot: float = 16.0, n: int = 256) -> list[str]:
    def at(t: float) -> Rgb:
        return solve_swatch_rgb(250, 0.006 + 0.006 * math.sin(math.pi * t),
                                L_top + (L_bot - L_top) * t)
    return render(at, n=n)
```

- [ ] **Step 4: 통과 확인** — `pytest tests/test_color_v5_cmaps_single.py -v` → PASS (8/8)

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_cmaps.py tests/test_color_v5_cmaps_single.py
git commit -m "feat(colors): add cmap render equalizer + pchip + single-hue/gray maps"
```

---

### Task 7: `_cmaps.py` (2/2) — 멀티휴·diverging·topo·cyclic + CATALOG

**Files:**
- Modify: `src/dartwork_mpl/colors/_cmaps.py` (함수·CATALOG 추가)
- Test: `tests/test_color_v5_cmaps_catalog.py`

**Interfaces:**
- Consumes: Task 6의 `render`/`pchip`/`unwrap_hues`, `_generate.compile_palette`(diverging 양극 hex), `_metrics`
- Produces:
  - `seq_multi(hue_knots, chroma_knots, L_start, L_end, n=256) -> list[str]`
  - `seq_topo(sea, land, n=256) -> list[str]` — sea/land = `(hue_knots, chroma_knots, L_from, L_to)`, 반부별 `render(n//2)`
  - `diverging_pair(hex_a, hex_b, l_end, l_center=96.0, gamma=0.85, half=32) -> list[str]` — 홀수 샘플(2·half−1), 중심 정확히 50%
  - `cyclic_hue(L=62.0, n=256) -> list[str]` — 등명도 색상환
  - `cyclic_twilight(hue_a, hue_b, n=256) -> list[str]` — 이중 로브, `render(closed=True)`
  - `ANCHORS: dict[str, float]` — 15 family h₀ (멀티휴 knot 어휘)
  - `compile_cmaps(palette, n=256) -> dict[str, list[str]]` — 42종 전체 (키: `"blue"`,`"aurora"`,`"blue_red"`,`"blue_red_deep"`,`"blue_red_soft"`,…,`"coast"`,`"hue"`,`"halo"`,`"corona"` — SSOT `swatches_32`와 동일한 평면 공개 이름)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_cmaps_catalog.py
"""Golden tests — full 42-map catalog must reproduce SSOT swatches_32."""

from __future__ import annotations

from dartwork_mpl.colors._cmaps import compile_cmaps


def test_full_catalog_matches_ssot(v5_ssot):
    cm = compile_cmaps(v5_ssot["palette"], n=32)
    expected = v5_ssot["colormaps"]["swatches_32"]
    assert set(cm) == set(expected)
    for name in expected:
        assert cm[name] == expected[name], name


def test_counts(v5_ssot):
    counts = v5_ssot["colormaps"]["counts"]
    assert counts["total"] == 42
    assert counts == {"single": 16, "multi": 9, "diverging": 13, "topo": 1,
                      "cyclic": 3, "total": 42, "qualitative_registered": 2}
```

- [ ] **Step 2: 실패 확인** — FAIL (`compile_cmaps` 없음)

- [ ] **Step 3: 구현 (기존 `_cmaps.py`에 추가)**

```python
# --- 멀티휴 (자연광 장면 — 스펙 §9. knot은 family 앵커 h0에서만) ---
ANCHORS: dict[str, float] = {fam: FAMILY_PARAMS[fam].h0 for fam in FAMILIES}


def seq_multi(hue_knots: list[float], chroma_knots: list[float],
              L_start: float = 14.0, L_end: float = 96.0, n: int = 256) -> list[str]:
    """빛 계열 관례: t=0=어두움(저값) → t=1=밝음. knot은 pchip으로 C1 통과."""
    hk = unwrap_hues(hue_knots)
    nk = len(hk)
    tk = [i / (nk - 1) for i in range(nk)]

    def at(t: float) -> Rgb:
        h = pchip(tk, hk, t) % 360
        c = pchip(tk, chroma_knots, t)
        l_t = L_start + (L_end - L_start) * t
        c = min(c, gamut_max_chroma(h, l_t) * 0.97)
        return solve_swatch_rgb(h, c, l_t)

    return render(at, n=n)


def seq_topo(sea: tuple, land: tuple, n: int = 256) -> list[str]:
    """기준면 2단 — 반부별 독립 등화, 중앙 L* 불연속은 설계 (해안선)."""
    def half(hk: list[float], ck: list[float], l0: float, l1: float) -> list[str]:
        hku = unwrap_hues(hk)
        tk = [i / (len(hku) - 1) for i in range(len(hku))]

        def at(t: float) -> Rgb:
            h = pchip(tk, hku, t) % 360
            l_t = l0 + (l1 - l0) * t
            c = min(pchip(tk, ck, t), gamut_max_chroma(h, l_t) * 0.97)
            return solve_swatch_rgb(h, c, l_t)

        return render(at, n=n // 2)

    return half(*sea) + half(*land)


def diverging_pair(hex_a: str, hex_b: str, l_end: float, l_center: float = 96.0,
                   gamma: float = 0.85, half: int = 32) -> list[str]:
    """L* 대칭 diverging — 홀수 샘플(2·half−1)로 중심이 정확히 50%에 위치.

    양극 정체성은 dc.{a}6/dc.{b}6 hex의 OKLCH chroma·hue에서 유도한다.
    포인트별 독립 솔브(등화 없음)라 hex 직접 생성으로 충분하다.
    """
    from ._color import Color

    arms: list[list[str]] = []
    for src in (hex_a, hex_b):
        _, c_max, hue = Color(src).to_oklch()
        pts = []
        for i in range(half):
            t = i / (half - 1)          # 0=끝(포화) → 1=중심(밝음)
            l_t = l_end + (l_center - l_end) * t
            c = c_max * (1 - t) ** gamma + 0.004 * t
            pts.append(hex_from_rgb(solve_swatch_rgb(hue, c, l_t)))
        arms.append(pts)
    return arms[0] + arms[1][:-1][::-1]


def cyclic_hue(L: float = 62.0, n: int = 256) -> list[str]:
    """등명도 색상환 — hue 균등(색상환은 hue가 지각축)."""
    c_safe = min(gamut_max_chroma(h, L) for h in range(0, 360, 5)) * 0.95
    return [hex_from_rgb(solve_swatch_rgb((i / n * 360) % 360, c_safe, L))
            for i in range(n)]


def cyclic_twilight(hue_a: float, hue_b: float, n: int = 256) -> list[str]:
    """이중 로브 cyclic — 밝은 이음매 → A팔 → 어두운 중심 → B팔 → 이음매."""
    L_seam, L_center = 93.0, 18.0

    def at(t: float) -> Rgb:
        if t <= 0.5:
            u, h, cmax = t / 0.5, hue_a, 0.15
        else:
            u, h, cmax = 1 - (t - 0.5) / 0.5, hue_b, 0.16
        l_t = L_seam + (L_center - L_seam) * u
        c = cmax * math.sin(math.pi * u) ** 0.85
        c = min(c, gamut_max_chroma(h % 360, l_t) * 0.96)
        return solve_swatch_rgb(h % 360, c, l_t)

    return render(at, n=n, closed=True)


def compile_cmaps(palette: dict[str, list[str]], n: int = 256) -> dict[str, list[str]]:
    """42종 카탈로그 — 키는 SSOT swatches_32와 동일한 평면 공개 이름."""
    from ._color import Color

    A = ANCHORS
    cm: dict[str, list[str]] = {}

    # 단일색 16 (family명 그대로)
    for fam in FAMILIES:
        cm[fam] = seq_single(fam, n=n)
    cm["gray"] = seq_gray(n=n)

    # 멀티휴 9 (자연광 장면 — knot·chroma·L 범위는 스펙 §9 확정값)
    multi: dict[str, tuple[list[float], list[float], float, float]] = {
        "aurora":    ([A["violet"], A["indigo"], A["sky"], A["teal"], A["lime"], A["yellow"]],
                      [0.08, 0.11, 0.13, 0.15, 0.16, 0.13], 14.0, 96.0),
        "afterglow": ([A["violet"], A["purple"], A["pink"], A["red"], A["orange"]],
                      [0.10, 0.17, 0.20, 0.19, 0.16], 16.0, 92.0),
        "blaze":     ([A["violet"], A["pink"], A["red"], A["orange"], A["yellow"]],
                      [0.09, 0.18, 0.20, 0.18, 0.13], 12.0, 94.0),
        "lava":      ([A["red"], A["orange"], A["amber"], A["yellow"]],
                      [0.15, 0.18, 0.16, 0.13], 12.0, 95.0),
        "lagoon":    ([A["blue"], A["cyan"], A["teal"], A["green"], A["lime"]],
                      [0.10, 0.12, 0.14, 0.17, 0.15], 14.0, 96.0),
        "glacier":   ([A["indigo"], A["blue"], A["sky"], A["cyan"], A["teal"]],
                      [0.10, 0.15, 0.14, 0.12, 0.12], 14.0, 96.0),
        "canopy":    ([A["teal"], A["green"], A["lime"], A["yellow"]],
                      [0.09, 0.14, 0.16, 0.13], 14.0, 96.0),
        "haze":      ([A["blue"], A["sky"], A["green"], A["yellow"]],
                      [0.05, 0.07, 0.09, 0.13], 14.0, 96.0),
        "iris":      ([A["violet"], A["blue"], A["cyan"], A["green"], A["yellow"], A["orange"]],
                      [0.14, 0.15, 0.11, 0.15, 0.16, 0.16], 14.0, 93.0),
    }
    for name, (hk, ck, l0, l1) in multi.items():
        cm[name] = seq_multi(hk, ck, L_start=l0, L_end=l1, n=n)

    # diverging 13 (저값_고값 pair — 양극 = dc.{a}6/dc.{b}6)
    # 샘플 수 규약: diverging_pair 는 홀수(2·half−1) 샘플 → endpoint-inclusive
    # 정수-stride 리샘플로 n에 맞춘다. n=32 golden 은 half=32(63→32, stride 2.0
    # 정확 — SSOT 생성 방식과 동일), n=256 export 는 half=128(255→256).
    from ._metrics import lab_l_hex

    def _resample(hexes: list[str], m: int) -> list[str]:
        last = len(hexes) - 1
        return [hexes[round(i * last / (m - 1))] for i in range(m)]

    half = max(32, n // 2)

    def dv(fa: str, fb: str, l_end: float, l_center: float = 96.0,
           gamma: float = 0.85) -> list[str]:
        return _resample(
            diverging_pair(palette[fa][6], palette[fb][6], l_end=l_end,
                           l_center=l_center, gamma=gamma, half=half), n)

    cm["blue_red"] = dv("blue", "red",
                        l_end=(lab_l_hex(palette["blue"][6]) + lab_l_hex(palette["red"][6])) / 2)
    cm["blue_red_deep"] = dv("blue", "red", l_end=21, l_center=97.5)
    cm["blue_red_soft"] = dv("blue", "red", l_end=48, l_center=90, gamma=1.1)
    for a, b, le in (("blue", "orange", 42), ("teal", "rose", 44),
                     ("green", "purple", 40), ("purple", "orange", 42),
                     ("cyan", "red", 44), ("teal", "amber", 44),
                     ("violet", "lime", 42), ("indigo", "amber", 40),
                     ("gray", "blue", 42), ("gray", "red", 42)):
        cm[f"{a}_{b}"] = dv(a, b, l_end=le)

    # topo 1
    cm["coast"] = seq_topo(
        sea=([A["indigo"], A["blue"], A["cyan"]], [0.09, 0.11, 0.10], 16.0, 84.0),
        land=([A["green"], A["lime"], A["amber"]], [0.11, 0.09, 0.03], 42.0, 96.0),
        n=n)

    # cyclic 3 (원형 빛 현상)
    hue_of = lambda fam: Color(palette[fam][6]).to_oklch()[2]  # noqa: E731
    cm["hue"] = cyclic_hue(n=n)
    cm["halo"] = cyclic_twilight(hue_of("blue"), hue_of("red"), n=n)
    cm["corona"] = cyclic_twilight(hue_of("teal"), hue_of("orange"), n=n)
    return cm
```

`__all__`에 추가: `"ANCHORS", "compile_cmaps", "cyclic_hue", "cyclic_twilight", "diverging_pair", "seq_multi", "seq_topo"`.

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/test_color_v5_cmaps_catalog.py -v`
Expected: PASS (2/2). golden 불일치 시 이름 단위로 diff. 가장 흔한 원인: diverging의
half/리샘플 규약(코드 주석 참조 — n=32에서 half=32·stride 2.0 정수가 SSOT 생성
방식과 동일해야 함), 멀티휴 knot 순서, `blue_red`의 l_end(양극 L\* 평균) 계산.

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_cmaps.py tests/test_color_v5_cmaps_catalog.py
git commit -m "feat(colors): add full v5 cmap catalog (multi/diverging/topo/cyclic, 42 maps)"
```

---

### Task 8: `_build.py` + `_generated.py` — 결정론 빌드

**Files:**
- Create: `src/dartwork_mpl/colors/_build.py`
- Create: `src/dartwork_mpl/colors/_generated.py` (빌드 실행으로 생성 후 커밋)
- Test: `tests/test_color_v5_build.py`

**Interfaces:**
- Consumes: `_generate.compile_palette`, `_cycles.cycle_hexes`, `_cmaps.compile_cmaps`, `_gates.check_all`
- Produces:
  - CLI: `python -m dartwork_mpl.colors._build` — 게이트 실패 시 exit 1, 성공 시 `_generated.py` 재작성
  - `_generated.py` 내용: `PALETTE: dict[str, tuple[str, ...]]`, `CYCLES: dict[str, tuple[str, ...]]`, `CMAPS_256: dict[str, tuple[str, ...]]` (42종 × 256), 모두 key 정렬·불변 tuple

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_build.py
"""Determinism + drift gate for the committed build artifact."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dartwork_mpl.colors import _generated


def test_generated_tables_shape():
    assert len(_generated.PALETTE) == 16
    assert all(len(row) == 10 for row in _generated.PALETTE.values())
    assert set(_generated.CYCLES) == {"default", "print"}
    assert len(_generated.CMAPS_256) == 42
    assert all(len(v) == 256 for v in _generated.CMAPS_256.values())


def test_generated_matches_ssot_palette(v5_ssot):
    for fam, row in v5_ssot["palette"].items():
        assert list(_generated.PALETTE[fam]) == row, fam


def test_rebuild_is_byte_identical(tmp_path):
    src = Path("src/dartwork_mpl/colors/_generated.py")
    before = src.read_bytes()
    r = subprocess.run([sys.executable, "-m", "dartwork_mpl.colors._build"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert src.read_bytes() == before, "rebuild drifted — nondeterminism or stale commit"
```

- [ ] **Step 2: 실패 확인** — FAIL (`_generated` 없음)

- [ ] **Step 3: 구현**

```python
# src/dartwork_mpl/colors/_build.py
"""Build CLI — 91-number SSOT에서 전 산출물 컴파일 + A7 게이트 + _generated.py.

usage: python -m dartwork_mpl.colors._build
결정론: 같은 소스에서 byte-identical 출력 (timestamp·랜덤 없음, key 정렬).
"""

from __future__ import annotations

import sys
from pathlib import Path

from ._cmaps import compile_cmaps
from ._cycles import CYCLE_SPECS, cycle_hexes
from ._gates import check_all
from ._generate import compile_palette

_OUT = Path(__file__).parent / "_generated.py"
_HEADER = '''"""AUTO-GENERATED by dartwork_mpl.colors._build — do not edit.

Regenerate: python -m dartwork_mpl.colors._build
Source of truth: colors/_recipe.py (91-number SSOT, spec 2026-07-03).
"""

from __future__ import annotations

'''


def _fmt(name: str, table: dict[str, list[str]]) -> str:
    lines = [f"{name}: dict[str, tuple[str, ...]] = {{"]
    for key in sorted(table):
        row = ", ".join(f'"{h}"' for h in table[key])
        lines.append(f'    "{key}": ({row}),')
    lines.append("}\n")
    return "\n".join(lines)


def main() -> int:
    palette = compile_palette()
    cycles = {name: cycle_hexes(name, palette) for name in CYCLE_SPECS}
    cmaps32 = compile_cmaps(palette, n=32)      # 게이트는 32-stop 직접 렌더에서
    cmaps256 = compile_cmaps(palette, n=256)    # export 테이블

    # 게이트 키에 카테고리 접두사 부여 (gate 러너의 kind 분기용)
    def prefixed(cm: dict[str, list[str]]) -> dict[str, list[str]]:
        div = {"blue_red", "blue_red_deep", "blue_red_soft", "blue_orange",
               "teal_rose", "green_purple", "purple_orange", "cyan_red",
               "teal_amber", "violet_lime", "indigo_amber", "gray_blue", "gray_red"}
        cyc = {"hue", "halo", "corona"}
        out = {}
        for k, v in cm.items():
            if k in div:
                out[f"div.{k}"] = v
            elif k in cyc:
                out[f"cyc.{k}"] = v
            elif k == "coast":
                out[f"topo.{k}"] = v
            else:
                out[f"seq.{k}"] = v
        return out

    violations = check_all(palette, cycles, prefixed(cmaps32))
    if violations:
        for v in violations:
            print(f"GATE FAIL: {v}", file=sys.stderr)
        return 1

    body = (_fmt("PALETTE", palette) + "\n" + _fmt("CYCLES", cycles) + "\n"
            + _fmt("CMAPS_256", cmaps256))
    _OUT.write_text(_HEADER + body, encoding="utf-8")
    print(f"OK: {_OUT} ({len(palette)} families, {len(cmaps256)} cmaps, gates green)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 빌드 실행 + 통과 확인**

```bash
python -m dartwork_mpl.colors._build     # _generated.py 생성 (수 분 소요 허용)
pytest tests/test_color_v5_build.py -v   # PASS (3/3)
```

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_build.py src/dartwork_mpl/colors/_generated.py tests/test_color_v5_build.py
git commit -m "feat(colors): add deterministic build CLI + committed generated tables"
```

---

### Task 9: 팔레트 토큰 등록 — `_loader.py` v5 통합

**Files:**
- Modify: `src/dartwork_mpl/colors/_loader.py`
- Test: `tests/test_color_v5_loader.py`

**Interfaces:**
- Consumes: `_generated.PALETTE`, 기존 `dc_palettes.json` 로딩 경로
- Produces: matplotlib named colors에 `dc.{family}{step}` (16×10=160토큰) + 기존 `dm.` alias 규칙 적용. **충돌 정책(스펙 §11)**: 레거시 `dc_palettes.json`과 정확히 같은 토큰명(`dc.teal0-7`·`dc.indigo0-7`·`dc.gray0-7`·`dc.coral0-7` 중 v5와 겹치는 teal/indigo/gray 24토큰)은 **레거시 hex가 기본값** — v5 값은 Task 11의 `set_palette_version(5)`로 opt-in.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_loader.py
"""v5 palette token registration + legacy collision policy (스펙 §11)."""

from __future__ import annotations

import matplotlib.colors as mcolors

import dartwork_mpl  # noqa: F401  (등록 트리거)
from dartwork_mpl.colors import _generated


def _named() -> dict:
    return mcolors.get_named_colors_mapping()


def test_v5_tokens_registered_for_noncolliding_families():
    named = _named()
    for fam in ("red", "blue", "violet", "amber"):
        for step in range(10):
            assert named[f"dc.{fam}{step}"] == _generated.PALETTE[fam][step]


def test_colliding_tokens_default_to_frozen_legacy():
    # dc.teal5 는 레거시 dc_palettes.json 값 유지 (silent recolor 금지 — §11)
    named = _named()
    assert named["dc.teal5"] != _generated.PALETTE["teal"][5]
    # 레거시에 없는 스텝(8·9)은 v5 값으로 등록
    assert named["dc.teal8"] == _generated.PALETTE["teal"][8]


def test_dm_alias_exists():
    assert _named()["dm.blue6"] == _named()["dc.blue6"]
```

- [ ] **Step 2: 실패 확인** — FAIL (v5 토큰 미등록)

- [ ] **Step 3: 구현** — `_loader.py`의 `_load_colors()` 끝부분(dm. alias 생성 **전**)에 삽입:

```python
    # --- v5 generated palette (스펙 §11 충돌 정책) --------------------
    # 레거시 dc_palettes.json 과 정확히 같은 이름의 토큰은 레거시 hex 가
    # 기본값(동결 — silent recolor 금지). v5 값은 set_palette_version(5)
    # opt-in 시 _compat_v4 가 remap 한다. 레거시에 없는 이름은 즉시 v5.
    from ._generated import PALETTE as _V5_PALETTE

    legacy_dc_names = {k for k in color_dict if k.startswith("dc.")}
    v5_tokens: dict[str, str] = {}
    for fam, row in _V5_PALETTE.items():
        for step, hexval in enumerate(row):
            token = f"dc.{fam}{step}"
            if token not in legacy_dc_names:
                v5_tokens[token] = hexval
    color_dict.update(v5_tokens)
```

그리고 모듈 말미에 v5/레거시 판별용 헬퍼 추가 (Task 11 소비):

```python
def v5_collision_tokens() -> dict[str, str]:
    """레거시가 점유 중이라 기본 등록에서 제외된 v5 토큰 → v5 hex."""
    from ._generated import PALETTE

    root = files("dartwork_mpl") / "asset" / "color"
    legacy = _load_json_palette(root, "dc_palettes.json", "dc")
    out = {}
    for fam, row in PALETTE.items():
        for step, hexval in enumerate(row):
            token = f"dc.{fam}{step}"
            if token in legacy:
                out[token] = hexval
    return out
```

- [ ] **Step 4: 통과 확인** — `pytest tests/test_color_v5_loader.py -v` → PASS (3/3).
기존 로더 테스트 회귀 확인: `pytest tests/test_color_api.py tests/test_deprecation_aliases.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_loader.py tests/test_color_v5_loader.py
git commit -m "feat(colors): register v5 palette tokens with legacy-freeze collision policy"
```

---

### Task 10: cmap 등록 (mpl 레지스트리 `dc.<name>`) + 레거시 2건 리네임

**Files:**
- Modify: `src/dartwork_mpl/cmap.py` (레거시 로더 — 변경 없음 확인만), `src/dartwork_mpl/colors/__init__.py`, `src/dartwork_mpl/__init__.py`
- Rename: `src/dartwork_mpl/asset/cmap/aurora.txt` → `legacy_aurora.txt`, `src/dartwork_mpl/asset/cmap/teal_rose.txt` → `legacy_teal_rose.txt`
- Modify: `tests/test_cmap.py` (`EXPECTED_DC_NAMES`의 `aurora`→`legacy_aurora`, `teal_rose`→`legacy_teal_rose`), `tests/test_cmap_sources_consistency.py`(참조 시)
- Create: `src/dartwork_mpl/colors/_register.py`
- Test: `tests/test_color_v5_register.py`

> **접근 방식 결정 (사용자 2026-07-04): matplotlib 레지스트리 네이티브 = 기존·익숙·기술부채 0.**
> v5 cmap은 mpl 레지스트리에 `dc.<name>`으로 등록만 하고, 접근은 기존 코드·docs가 이미 쓰는
> 표준 matplotlib 방식(`cmap="dc.aurora"` / `plt.colormaps["dc.aurora"]` / `dm.list_colormaps()`)을
> 그대로 쓴다. 별도 `dm.cmap(name)` 파이썬 접근자는 **만들지 않는다** — 그것이 기존
> `dartwork_mpl.cmap` 모듈과 충돌(파이썬 import 의미론)하고 callable-module/mypy 기술부채를
> 유발한 원인이었다. `dartwork_mpl.cmap`은 모듈로 그대로 유지(무변경).

**Files (수정):**
- Create: `src/dartwork_mpl/colors/_register.py` (등록 전용 — 접근자 함수 없음)
- **DROP**: `dartwork_mpl/__init__.py`의 `from .colors import cmap` shadowing 배선 (하지 않음)

**Interfaces:**
- Consumes: `_generated.CMAPS_256`, `_generated.CYCLES`
- Produces:
  - mpl registry: 42종 × (`dc.<name>` + `dc.<name>_r`) `ListedColormap(N=256)`; cyclic 3종 `_r`도 단순 역순
  - qualitative: `dc.cycle`(7)·`dc.cycle_print`(8) ListedColormap
  - `ensure_registered() -> None` — 최초 접근 시 42+2 등록 (double-checked locking). `colors/__init__.py`에서 팔레트 로드 다음 호출
  - **접근자 함수 없음**. 사용자는 `plt.colormaps["dc.aurora"]` / `cmap="dc.aurora"`로 접근 (기존 docs 관용). `dm.list_colormaps()`가 신규 v5 이름을 자동 포함(레지스트리 스캔)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_register.py
"""v5 cmap registration + accessor + legacy renames."""

from __future__ import annotations

import matplotlib as mpl
import pytest

import dartwork_mpl as dm
from dartwork_mpl.colors import _generated


def test_registry_names():
    for name in ("aurora", "blue", "blue_red", "coast", "halo"):
        assert f"dc.{name}" in mpl.colormaps
        assert f"dc.{name}_r" in mpl.colormaps
    assert "dc.cycle" in mpl.colormaps and "dc.cycle_print" in mpl.colormaps


def test_registry_access_matplotlib_native():
    # 기존·익숙한 방식: matplotlib 레지스트리 직접 접근 (별도 접근자 없음)
    cm = mpl.colormaps["dc.aurora"]
    assert cm.N == 256
    assert [mpl.colors.to_hex(c) for c in cm.colors] == list(_generated.CMAPS_256["aurora"])
    # _r 역방향
    assert mpl.colors.to_hex(mpl.colormaps["dc.aurora_r"].colors[0]) == \
        _generated.CMAPS_256["aurora"][-1]
    # 미존재 이름은 matplotlib 자신이 KeyError
    with pytest.raises(KeyError):
        mpl.colormaps["dc.no_such_map"]


def test_legacy_renames():
    assert "dc.legacy_aurora" in mpl.colormaps
    assert "dc.legacy_teal_rose" in mpl.colormaps
    # v5 aurora 가 이름을 가져감 — 레거시 hex 와 달라야 함
    assert list(mpl.colormaps["dc.aurora"].colors) != list(
        mpl.colormaps["dc.legacy_aurora"].colors)


def test_cmap_module_untouched():
    # dartwork_mpl.cmap 은 모듈 그대로 (shadowing 없음) — 기존 코드 무변경
    import dartwork_mpl.cmap as cmap_module
    assert hasattr(cmap_module, "ensure_loaded")
    from dartwork_mpl import cmap as pkg_attr
    assert pkg_attr is cmap_module   # 패키지 attribute도 모듈 (함수 아님)
```

- [ ] **Step 2: 실패 확인** — FAIL

- [ ] **Step 3: 구현**

```bash
git mv src/dartwork_mpl/asset/cmap/aurora.txt src/dartwork_mpl/asset/cmap/legacy_aurora.txt
git mv src/dartwork_mpl/asset/cmap/teal_rose.txt src/dartwork_mpl/asset/cmap/legacy_teal_rose.txt
```

```python
# src/dartwork_mpl/colors/_register.py
"""v5 cmap/cycle registration — matplotlib 레지스트리에 dc.<name> 등록.

접근은 matplotlib 네이티브(`plt.colormaps["dc.aurora"]` / `cmap="dc.aurora"`) —
별도 파이썬 접근자를 두지 않는다(기존 dartwork_mpl.cmap 모듈과의 충돌·기술부채 회피,
사용자 결정 2026-07-04).
"""

from __future__ import annotations

import threading

import matplotlib as mpl
import matplotlib.colors as mcolors

from ._generated import CMAPS_256, CYCLES

__all__ = ["ensure_registered"]

_loaded = False
_lock = threading.Lock()


def _register() -> None:
    for name, hexes in CMAPS_256.items():
        mpl.colormaps.register(mcolors.ListedColormap(list(hexes), name=f"dc.{name}"))
        mpl.colormaps.register(
            mcolors.ListedColormap(list(hexes)[::-1], name=f"dc.{name}_r"))
    mpl.colormaps.register(
        mcolors.ListedColormap(list(CYCLES["default"]), name="dc.cycle"))
    mpl.colormaps.register(
        mcolors.ListedColormap(list(CYCLES["print"]), name="dc.cycle_print"))


def ensure_registered() -> None:
    global _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        _register()
        _loaded = True
```

배선:
- `colors/__init__.py`: `from ._register import ensure_registered as _ensure_cmaps_registered` 추가, 파일 말미 `_ensure_cmaps_registered()` 호출(팔레트 로드 다음). **`cmap` export 없음.**
- `dartwork_mpl/__init__.py`: **변경 없음** — 기존 `from . import (cmap, ...)`(모듈) 그대로. `from .colors import cmap` shadowing은 추가하지 않는다(이것이 충돌 원인이었음).
- `tests/test_cmap.py`: `EXPECTED_DC_NAMES`에서 `"aurora"`→`"legacy_aurora"`, `"teal_rose"`→`"legacy_teal_rose"` 치환. (모듈 접근 패턴은 무변경 — shadowing이 없으므로 기존 `from dartwork_mpl import cmap as cmap_module` 등 전부 그대로 동작.)

- [ ] **Step 4: 통과 확인**

```bash
pytest tests/test_color_v5_register.py tests/test_cmap.py tests/test_cmap_sources_consistency.py -v
```
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add -A src/dartwork_mpl/asset/cmap src/dartwork_mpl/colors tests/test_color_v5_register.py tests/test_cmap.py
git commit -m "feat(colors): register 42 v5 cmaps + qualitative cycles in mpl registry

Access via matplotlib-native cmap=\"dc.aurora\" / plt.colormaps[\"dc.aurora\"]
(no bespoke accessor — dartwork_mpl.cmap stays the module).

BREAKING: legacy cmaps dc.aurora/dc.teal_rose renamed to dc.legacy_aurora/
dc.legacy_teal_rose (name ceded to v5 catalog)."
```

---

### Task 11: `_compat_v4.py` — 레거시 동결 + `set_palette_version` + DeprecationWarning

**Files:**
- Create: `src/dartwork_mpl/colors/_compat_v4.py`
- Modify: `src/dartwork_mpl/colors/_color.py` (`Color.from_name`에 deprecation 훅 1줄), `colors/__init__.py`·`dartwork_mpl/__init__.py` export
- Modify: `src/dartwork_mpl/helpers/colors.py` (`get_palette` 큐레이트 bare-name 길이 정책 — 아래 §get_palette 참조)
- Test: `tests/test_color_v5_compat.py`

**Interfaces:**
- Consumes: `_loader.v5_collision_tokens()`, 레거시 `dc_palettes.json` 로딩 결과
- Produces:
  - `set_palette_version(v: int) -> None` — `5`: 충돌 토큰(dc.teal*·dc.indigo*·dc.gray* 0-7)을 v5 hex로 remap; `4`: 동결 레거시로 복원 (mpl named mapping 직접 갱신)
  - `LEGACY_TOKEN_NAMES: frozenset[str]` — 레거시 전용 토큰(`dc.vivid*`·`dc.pastel*`·`dc.0-7` 등 v5 counterpart 없는 것 포함 전체)
  - `warn_if_legacy(name: str) -> None` — 세션당 토큰당 1회 DeprecationWarning (제거 예정 버전 명시: "+2 minor")

**§get_palette — 큐레이트 bare-name 길이 정책 (Task 9 리뷰 Important 해소):**
Task 9에서 v5 토큰을 등록하면서 `dc.teal8/9`·`dc.indigo8/9`·`dc.gray8/9`가 생겨,
`get_palette("teal")`(정규식 `dc.<name>\d+` 스캔)이 기존 8스텝(레거시 0-7)에서 10스텝
(레거시 0-7 + v5 8-9)으로 *조용히* 변했다. teal 0-7(레거시 생성기)과 teal 8-9(v5 생성기)는
서로 다른 명도·채도 곡선이라 이 10스텝은 비정합 램프다(§11 "no silent change" 위반).

**해소**: `get_palette`의 *레거시 큐레이트 3종*(teal·indigo·gray)에 대해 **버전 인식 길이 캡**을
적용한다 — 기본(v4)은 레거시 8스텝만 반환(비정합 8-9 제외, 기존 계약 보존), `set_palette_version(5)`
opt-in 시 v5 remap으로 0-7이 v5가 되어 *정합 10스텝* 반환. `helpers/colors.py`의
`_palette_color_names`(또는 `get_palette`)에 이 3종 캡 로직을 추가하고, 코드 주석으로 §11/본 Task를
가리켜 결정을 durable하게 남긴다. 그 외 family(red·blue 등 legacy 무충돌)는 항상 v5 10스텝.
테스트: 기본 `len(get_palette("teal"))==8`, `set_palette_version(5)` 후 `==10`(+원복 `set_palette_version(4)`).

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_compat.py
"""§11 migration policy — freeze by default, opt-in remap, deprecation warning."""

from __future__ import annotations

import warnings

import matplotlib.colors as mcolors
import pytest

import dartwork_mpl as dm
from dartwork_mpl.colors import _generated
from dartwork_mpl.colors._compat_v4 import set_palette_version


@pytest.fixture(autouse=True)
def _restore_version():
    yield
    set_palette_version(4)


def test_default_is_frozen_legacy():
    named = mcolors.get_named_colors_mapping()
    assert named["dc.teal5"] != _generated.PALETTE["teal"][5]


def test_opt_in_remap_and_back():
    named = mcolors.get_named_colors_mapping()
    legacy_teal5 = named["dc.teal5"]
    set_palette_version(5)
    assert named["dc.teal5"] == _generated.PALETTE["teal"][5]
    set_palette_version(4)
    assert named["dc.teal5"] == legacy_teal5


def test_legacy_token_warns_once():
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        dm.color("dc.vivid3")
        dm.color("dc.vivid3")
    dep = [w for w in rec if issubclass(w.category, DeprecationWarning)]
    assert len(dep) == 1
    assert "vivid3" in str(dep[0].message)


def test_v5_token_does_not_warn():
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        dm.color("dc.blue6")
    assert not [w for w in rec if issubclass(w.category, DeprecationWarning)]
```

- [ ] **Step 2: 실패 확인** — FAIL

- [ ] **Step 3: 구현**

```python
# src/dartwork_mpl/colors/_compat_v4.py
"""Legacy dc.* freeze + opt-in v5 remap (스펙 §11).

기본값: 구 토큰은 동결 hex 반환(시각 결과 불변, silent recolor 금지).
`set_palette_version(5)` 호출 시에만 충돌 토큰이 v5 로 remap 된다.
레거시 전용 토큰은 접근 시 1회 DeprecationWarning (최소 2 minor 후 제거).
"""

from __future__ import annotations

import warnings
from importlib.resources import files

import matplotlib.colors as mcolors

from ._loader import _load_json_palette, v5_collision_tokens

__all__ = ["LEGACY_TOKEN_NAMES", "set_palette_version", "warn_if_legacy"]


def _legacy_tokens() -> dict[str, str]:
    root = files("dartwork_mpl") / "asset" / "color"
    return _load_json_palette(root, "dc_palettes.json", "dc")


LEGACY_TOKEN_NAMES: frozenset[str] = frozenset(_legacy_tokens())
_COLLISIONS: dict[str, str] = v5_collision_tokens()          # token -> v5 hex
_FROZEN: dict[str, str] = {k: v for k, v in _legacy_tokens().items() if k in _COLLISIONS}
_warned: set[str] = set()
_version: int = 4


def set_palette_version(v: int) -> None:
    """dc.* 충돌 토큰의 해석 버전 전환 — 4(동결 레거시, 기본) 또는 5(v5 remap)."""
    global _version
    if v not in (4, 5):
        raise ValueError(f"palette version must be 4 or 5, got {v!r}")
    mapping = mcolors.get_named_colors_mapping()
    src = _COLLISIONS if v == 5 else _FROZEN
    for token, hexval in src.items():
        mapping[token] = hexval
        mapping["dm." + token[3:]] = hexval
    _version = v


def warn_if_legacy(name: str) -> None:
    """레거시 전용 dc.* 토큰 접근 시 1회 경고 (dm.color() 경로에서 호출)."""
    if name in LEGACY_TOKEN_NAMES and name not in _COLLISIONS and name not in _warned:
        _warned.add(name)
        warnings.warn(
            f"color token {name!r} is a frozen v4 legacy token and will be "
            "removed after two minor releases; see the v5 migration guide.",
            DeprecationWarning, stacklevel=3)
```

`_color.py`의 `Color.from_name()` (이름 해석 직전)에 훅 추가:

```python
        if name.startswith(("dc.", "dm.")):
            from ._compat_v4 import warn_if_legacy
            warn_if_legacy("dc." + name.split(".", 1)[1])
```

`colors/__init__.py`·`dartwork_mpl/__init__.py`에 `set_palette_version` export.

- [ ] **Step 4: 통과 확인**

```bash
pytest tests/test_color_v5_compat.py tests/test_color_api.py tests/test_color_parser.py -v
```
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_compat_v4.py src/dartwork_mpl/colors/_color.py src/dartwork_mpl/colors/__init__.py src/dartwork_mpl/__init__.py tests/test_color_v5_compat.py
git commit -m "feat(colors): add v4 freeze + set_palette_version(5) opt-in remap + deprecation warnings"
```

---

### Task 12: `dm.cycle()` API — cycle 접근 + 8색 초과 선스타일 병행

**Files:**
- Create: `src/dartwork_mpl/colors/_cycle_api.py`
- Test: `tests/test_color_v5_cycle_api.py`
- Modify: `colors/__init__.py`·`dartwork_mpl/__init__.py` export

**Interfaces:**
- Consumes: `_generated.CYCLES`
- Produces:
  - `cycle(name: str = "default") -> list[str]` — hex 리스트
  - `cycle_cycler(name: str = "default", linestyles: tuple[str, ...] = ("-", "--", ":")) -> Cycler` — `cycler(linestyle) * cycler(color)` 곱 (색이 먼저 순환, 8번째부터 dashed — 스펙 §8)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_cycle_api.py
from __future__ import annotations

import pytest

import dartwork_mpl as dm
from dartwork_mpl.colors import _generated
from dartwork_mpl.colors._cycle_api import cycle_cycler


def test_cycle_hexes():
    assert dm.cycle() == list(_generated.CYCLES["default"])
    assert dm.cycle("print") == list(_generated.CYCLES["print"])
    with pytest.raises(KeyError):
        dm.cycle("nope")


def test_cycler_product_color_first():
    cyc = list(cycle_cycler())
    n = len(_generated.CYCLES["default"])            # 7
    assert len(cyc) == n * 3
    # 처음 7개: solid + 7색 순환
    assert all(c["linestyle"] == "-" for c in cyc[:n])
    assert [c["color"] for c in cyc[:n]] == list(_generated.CYCLES["default"])
    # 8번째(색 재사용 시작)부터 dashed
    assert cyc[n]["linestyle"] == "--" and cyc[n]["color"] == cyc[0]["color"]
```

- [ ] **Step 2: 실패 확인** — FAIL

- [ ] **Step 3: 구현**

```python
# src/dartwork_mpl/colors/_cycle_api.py
"""Categorical cycle API — hex 접근 + 선스타일 병행 cycler (스펙 §8)."""

from __future__ import annotations

from cycler import Cycler, cycler

from ._generated import CYCLES

__all__ = ["cycle", "cycle_cycler"]


def cycle(name: str = "default") -> list[str]:
    if name not in CYCLES:
        raise KeyError(f"unknown cycle {name!r} — available: {sorted(CYCLES)}")
    return list(CYCLES[name])


def cycle_cycler(name: str = "default",
                 linestyles: tuple[str, ...] = ("-", "--", ":")) -> Cycler:
    """색이 먼저 순환하고, 색 재사용이 시작되는 시리즈부터 선스타일이 바뀐다."""
    return cycler(linestyle=list(linestyles)) * cycler(color=cycle(name))
```

export 배선 후:

- [ ] **Step 4: 통과 확인** — `pytest tests/test_color_v5_cycle_api.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_cycle_api.py src/dartwork_mpl/colors/__init__.py src/dartwork_mpl/__init__.py tests/test_color_v5_cycle_api.py
git commit -m "feat(colors): add dm.cycle() + linestyle-extended cycler"
```

---

### Task 13: `_semantic.py` — 로케일 시맨틱 토큰 + Style.use 훅

**Files:**
- Create: `src/dartwork_mpl/colors/_semantic.py`
- Modify: `src/dartwork_mpl/style.py` (`Style.use` 말미 1줄 훅)
- Test: `tests/test_color_v5_semantic.py`

**Interfaces:**
- Consumes: `_generated.PALETTE`
- Produces:
  - `apply_semantic(locale: str) -> None` — mpl named colors에 `dc.pos`·`dc.neg`·`dc.ref`·`dc.hl` 등록. `"kr"`: pos=red5·neg=blue6 / 그 외: pos=green6·neg=red6. 공통: ref=gray6·hl=violet6 (스펙 §10)
  - `Style.use` 말미: preset 구성에 `lang-kr` 포함 여부로 locale 판정 → `apply_semantic("kr" | "default")`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_semantic.py
from __future__ import annotations

import matplotlib.colors as mcolors

import dartwork_mpl as dm
from dartwork_mpl.colors import _generated


def _named():
    return mcolors.get_named_colors_mapping()


def test_kr_semantics():
    dm.style.use("report-kr")
    assert _named()["dc.pos"] == _generated.PALETTE["red"][5]
    assert _named()["dc.neg"] == _generated.PALETTE["blue"][6]


def test_default_semantics():
    dm.style.use("scientific")
    assert _named()["dc.pos"] == _generated.PALETTE["green"][6]
    assert _named()["dc.neg"] == _generated.PALETTE["red"][6]
    assert _named()["dc.ref"] == _generated.PALETTE["gray"][6]
    assert _named()["dc.hl"] == _generated.PALETTE["violet"][6]
```

- [ ] **Step 2: 실패 확인** — FAIL

- [ ] **Step 3: 구현**

```python
# src/dartwork_mpl/colors/_semantic.py
"""Locale-aware semantic tokens — dc.pos/neg/ref/hl (스펙 §10)."""

from __future__ import annotations

import matplotlib.colors as mcolors

from ._generated import PALETTE

__all__ = ["apply_semantic"]

_MAPS: dict[str, dict[str, str]] = {
    # 한국 금융 관행: 상승=적, 하락=청
    "kr": {"dc.pos": PALETTE["red"][5], "dc.neg": PALETTE["blue"][6]},
    "default": {"dc.pos": PALETTE["green"][6], "dc.neg": PALETTE["red"][6]},
}
_COMMON = {"dc.ref": PALETTE["gray"][6], "dc.hl": PALETTE["violet"][6]}


def apply_semantic(locale: str) -> None:
    mapping = mcolors.get_named_colors_mapping()
    sem = {**_COMMON, **_MAPS.get(locale, _MAPS["default"])}
    for token, hexval in sem.items():
        mapping[token] = hexval
        mapping["dm." + token[3:]] = hexval
```

`style.py`의 `Style.use()` 성공 경로 말미(스타일 적용 완료 직후) — locale 판정은
preset 명명 규칙(`presets.json`의 kr 변형은 전부 `*-kr` 접미사)으로 한다:

```python
        from .colors._semantic import apply_semantic
        names = preset_name if isinstance(preset_name, list) else [preset_name]
        is_kr = any(str(nm).endswith("-kr") or "lang-kr" in str(nm) for nm in names)
        apply_semantic("kr" if is_kr else "default")
```

- [ ] **Step 4: 통과 확인** — `pytest tests/test_color_v5_semantic.py tests/test_style*.py -v` → PASS

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/colors/_semantic.py src/dartwork_mpl/style.py tests/test_color_v5_semantic.py
git commit -m "feat(colors): add locale-aware semantic tokens wired into style presets"
```

---

### Task 14: mplstyle 재배선 — 내부 preset의 v5 전환

**Files:**
- Modify: `src/dartwork_mpl/asset/mplstyle/base.mplstyle` (prop_cycle + image.cmap)
- Modify: `src/dartwork_mpl/asset/mplstyle/font-scientific.mplstyle`, `font-web.mplstyle`, `font-presentation.mplstyle`, `font-minimal.mplstyle`, `font-poster.mplstyle` (prop_cycle 오버라이드 **삭제** — base 상속)
- Keep: `theme-dark.mplstyle` (레거시 vivid 유지 — 다크 배경은 v5 범위 밖, 스펙 §13)
- Test: `tests/test_color_v5_presets.py`

**Interfaces:**
- Consumes: v5 토큰(`dc.blue6` 등 — Task 9에서 비충돌 family라 항상 v5 값), `dc.aurora`(Task 10 등록)
- Produces: base.mplstyle —

```
axes.prop_cycle: cycler('linestyle', ['-', '--', ':']) * cycler('color', ['dc.blue6', 'dc.orange9', 'dc.green5', 'dc.pink3', 'dc.amber7', 'dc.violet8', 'dc.cyan8'])
image.cmap: dc.aurora
```

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/test_color_v5_presets.py
from __future__ import annotations

import matplotlib as mpl
import matplotlib.colors as mcolors

import dartwork_mpl as dm
from dartwork_mpl.colors import _generated


def _cycle_entries():
    return list(mpl.rcParams["axes.prop_cycle"])


def test_base_cycle_is_v5_with_linestyle_extension():
    dm.style.use("scientific")
    entries = _cycle_entries()
    assert len(entries) == 21                       # 7색 × 3 linestyle
    first7 = [mcolors.to_hex(mcolors.to_rgb(e["color"])) for e in entries[:7]]
    assert first7 == list(_generated.CYCLES["default"])
    assert entries[0]["linestyle"] == "-" and entries[7]["linestyle"] == "--"


def test_default_image_cmap_is_aurora():
    dm.style.use("scientific")
    assert mpl.rcParams["image.cmap"] == "dc.aurora"


def test_presets_inherit_base_cycle():
    for preset in ("report-kr", "presentation", "web", "minimal"):
        dm.style.use(preset)
        first = _cycle_entries()[0]["color"]
        assert mcolors.to_hex(mcolors.to_rgb(first)) == _generated.CYCLES["default"][0]


def test_dark_keeps_legacy_cycle():
    dm.style.use("dark")
    first = _cycle_entries()[0]["color"]
    assert mcolors.to_hex(mcolors.to_rgb(first)) != _generated.CYCLES["default"][0]
```

- [ ] **Step 2: 실패 확인** — FAIL

- [ ] **Step 3: 구현** — mplstyle 파일 수정 (위 Produces 값으로 base 교체, font-\* 5개 파일에서 `axes.prop_cycle:` 줄 삭제, theme-dark 유지). 주의: mplstyle의 cycler 곱 표현식은 matplotlib rcsetup이 파싱한다 — 만약 특정 mpl 버전에서 `*` 파싱이 거부되면 **폴백**: base에는 7색 단순 cycler를 두고, `Style.use` 말미에서 `mpl.rcParams["axes.prop_cycle"] = cycle_cycler()`로 곱을 주입한다(테스트는 동일하게 통과해야 함 — 폴백 채택 시 base.mplstyle에는 주석으로 사유 기록).

- [ ] **Step 4: 통과 확인**

```bash
pytest tests/test_color_v5_presets.py tests/test_style*.py -v
```
Expected: PASS. 시각 스모크: `python -c` 스니펫으로 7+2 시리즈 라인 차트를 base preset으로 그려 PNG 저장 후 눈 확인(8·9번째가 dashed 인지).

- [ ] **Step 5: 커밋**

```bash
git add src/dartwork_mpl/asset/mplstyle tests/test_color_v5_presets.py src/dartwork_mpl/style.py
git commit -m "feat(style): switch internal presets to v5 cycle (+linestyle extension) and dc.aurora default cmap"
```

---

### Task 15: 통합 검증 — 전체 스위트 + docs 핀 + CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`, `docs/color_system/colormaps.md`·`docs/migration/*.md`(핀 갱신 필요 시), 실패한 docs-핀 테스트가 가리키는 페이지들
- Test: 전체

**Interfaces:**
- Consumes: 전 태스크 산출물
- Produces: green 전체 스위트 + 마이그레이션 문서화

- [ ] **Step 1: 전체 테스트 실행**

```bash
pytest -x -q
```
Expected: 실패 목록 수집. 예상 실패 지점과 처방:
- `tests/test_docs_count_claims.py` — `docs/color_system/colormaps.md`의 "N curated colormaps" 카운트는 `asset/cmap/*.txt` glob 유래(리네임만 했으므로 56 유지 → 통과 예상). 실패 시 해당 페이지의 숫자를 테스트가 알려주는 파생값으로 수정.
- `tests/test_docs_color_tokens.py` — dc 토큰 수를 핀하는 페이지가 있으면 신규 160토큰 반영값으로 페이지 갱신.
- `tests/test_deprecation_registry_parity.py` — 신규 DeprecationWarning 을 repo의 deprecation 레지스트리에 등록해야 하면 그 레지스트리 파일에 legacy dc 토큰 엔트리 추가.
- `tests/test_domain_neutrality.py`·`tests/test_docstring_catalogs.py` — 신규 모듈 docstring이 규칙(도메인 중립 등)을 어기면 문구 수정.

- [ ] **Step 2: CHANGELOG + 마이그레이션 노트**

`CHANGELOG.md` Unreleased 섹션에:

```markdown
### Added
- Color system v5: generative 91-parameter palette (16 families x 10 steps),
  42 perceptually-gated colormaps (`cmap="dc.aurora"`), 2 categorical cycles
  (`dm.cycle()`), locale-aware semantic tokens (`dc.pos`/`dc.neg`/`dc.ref`/`dc.hl`),
  `dm.set_palette_version(5)` opt-in remap. Design spec:
  docs/superpowers/specs/2026-07-03-color-system-v5-design.md

### Changed
- Internal style presets now use the v5 categorical cycle with automatic
  linestyle extension from the 8th series; default `image.cmap` is `dc.aurora`.

### Deprecated
- All v4 `dc.*` tokens (`dc.vivid*`, `dc.pastel*`, `dc.0`-`dc.7`, ...) are frozen
  and emit a one-time DeprecationWarning; removal after two minor releases.

### Breaking
- Legacy colormaps `dc.aurora` / `dc.teal_rose` renamed to `dc.legacy_aurora` /
  `dc.legacy_teal_rose` (names ceded to the v5 catalog).
```

- [ ] **Step 3: 최종 게이트 + 결정론 재확인**

```bash
python -m dartwork_mpl.colors._build && git diff --exit-code src/dartwork_mpl/colors/_generated.py
pytest -q
ruff check src/dartwork_mpl/colors && mypy src/dartwork_mpl/colors
```
Expected: 전부 0 exit.

- [ ] **Step 4: 커밋**

```bash
git add -A
git commit -m "chore(colors): integration pass — docs pins, changelog, deprecation registry"
```

- [ ] **Step 5: PR 준비**

```bash
git push -u origin feat/color-system-v5
gh pr create --title "feat(colors): color system v5 — generative palette + 42-map catalog" \
  --body "Spec: docs/superpowers/specs/2026-07-03-color-system-v5-design.md (c82569d). Golden tests pin all outputs to the approved SSOT. Gates run at build; _generated.py is deterministic."
```
(머지는 사용자 승인 후.)

---

## Risk / Open Questions (스펙에서 이월된 결정 — plan에서 확정한 값)

1. **레거시 충돌 정책**: 정확히 같은 토큰명만 동결-우선(teal/indigo/gray 0-7), 나머지 v5 즉시 등록. 충돌 family의 8·9 스텝은 v5 (혼합 사다리 가능성은 compat docstring에 명시, opt-in으로 해소).
2. **`dm.cmap` 이름 충돌 (해소됨)**: 스펙 초안의 `dm.cmap(name)` 접근자는 기존 `dartwork_mpl.cmap` 모듈과 충돌(파이썬 import 의미론+mypy)해 불가능. 사용자 결정(2026-07-04)으로 별도 접근자를 폐기하고 matplotlib 레지스트리 네이티브(`cmap="dc.aurora"`)로 확정. 모듈은 무변경 (Task 10).
3. **prop_cycle 곱 표현식**: mplstyle 파싱 실패 시 `Style.use` 주입 폴백 (Task 14 Step 3).
4. **결정론 범위**: golden test는 개발/CI 단일 플랫폼 기준 byte-exact. 크로스 플랫폼 libm ULP 차이가 관측되면 그때 경로 입력 반올림(1e-9)을 도입하고 SSOT를 1회 재생성한다 — 선제 도입은 YAGNI.
5. **tritan Machado 유지**: 스펙 §12의 BVM 교체는 게이트 값 재산출이 필요해 v5.1로 이월 (Task 1 주석에 기록).
6. **다크 테마**: theme-dark는 레거시 cycle 유지 (v5.1 범위).
7. **codemod(스펙 §11-3)**: 사용자 스크립트의 구 토큰 → v5 마이그레이션 codemod(old→new ΔE 표
   출력)는 라이브러리 출하 후의 채택 도구라 본 플랜 범위 밖 — v5 릴리스 직후 별도 plan으로 수행.
8. **§14 대비 파일 편차**: 스펙 §14의 `generate.py`(gates 포함)를 `_generate.py`+`_gates.py`로
   분리(단일 책임), `compat.py`→`_compat_v4.py`, cycle 접근 API는 `_cycle_api.py`로 분리.
   전부 언더스코어 private + `__init__` 공개 export — repo 컨벤션 준수.
