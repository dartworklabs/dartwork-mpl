"""Standard figure-width constants for Matplotlib charts.

Defines standardized figure widths commonly used in academic papers
and presentations.
"""

from .util import cm2in

__all__ = [
    "DW",
    "SW",
    "MW",  # Medium width (SW ↔ DW 중간)
    "TW",  # Two-thirds width
    "WIDTHS",  # 4-tier width tuple (SW, MW, TW, DW)
    "FS_SINGLE",
    "FS_DOUBLE",
    "FS_SQUARE",
    "FS_WIDE",
    "FS_TALL",
    "FS_GOLDEN",
    "FS_SLIDE",
    "FS_A4",
]

# ── 4-tier width system ──────────────────────────────────────────
# 보고서 내 모든 차트는 아래 4가지 폭 중 하나를 골라 사용한다.
# 세로 높이는 자유 (콘텐츠·aspect 에 따라 조정).

# Single width — 좁은 사이드 차트·범례·개요 등
# STRICTLY FOR WIDTH, DO NOT USE AS HEIGHT.
SW: float = cm2in(9)  # 3.54 in

# Medium width — 나란히 배치 2개 또는 본문 삽입용
# STRICTLY FOR WIDTH, DO NOT USE AS HEIGHT.
MW: float = cm2in(12)  # 4.72 in

# Two-thirds width — 중-대형 단일 차트
# STRICTLY FOR WIDTH, DO NOT USE AS HEIGHT.
TW: float = cm2in(14.5)  # 5.71 in

# Double width — 전체 폭 메인 차트 (최대)
# STRICTLY FOR WIDTH, DO NOT USE AS HEIGHT.
DW: float = cm2in(17)  # 6.69 in

# 4-tier tuple — iteration 용
WIDTHS: tuple[float, float, float, float] = (SW, MW, TW, DW)

# Standard figure size tuple (width, height) for single-column width.
FS_SINGLE: tuple[float, float] = (SW, SW * 0.75)

# Standard figure size tuple (width, height) for double-column width.
FS_DOUBLE: tuple[float, float] = (DW, DW * 0.5)

# Square aspect ratio figures
FS_SQUARE: tuple[float, float] = (SW, SW)

# Wide aspect ratio (good for timelines, horizontal comparisons)
FS_WIDE: tuple[float, float] = (DW, DW * 0.4)

# Tall aspect ratio (good for vertical stacking)
FS_TALL: tuple[float, float] = (SW, SW * 1.4)

# Golden ratio aspect
FS_GOLDEN: tuple[float, float] = (SW, SW / 1.618)

# 16:9 presentation slide aspect ratio
FS_SLIDE: tuple[float, float] = (10, 5.625)

# A4 paper aspect ratio (portrait)
FS_A4: tuple[float, float] = (8.27, 11.69)
