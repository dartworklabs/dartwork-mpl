"""Matplotlib을 위한 색상 관리 및 변환 유틸리티 패키지.

이 패키지는 색상의 로드, 등록, 변환 기능을 제공하며,
OKLab, OKLCH, RGB, Hex 색상 공간을 모두 지원합니다.
"""

from ._color import Color, cspace, hex, named, oklab, oklch, rgb
from ._loader import ensure_loaded as _ensure_colors_loaded
from ._typing import DartworkColor, DartworkColormap
from ._views import (
    OklabView,
    OklabViewIterator,
    OklchView,
    OklchViewIterator,
    RgbView,
    RgbViewIterator,
)

__all__ = [
    # Core
    "Color",
    "cspace",
    # Convenience constructors
    "hex",
    "named",
    "oklab",
    "oklch",
    "rgb",
    # View classes
    "OklabView",
    "OklabViewIterator",
    "OklchView",
    "OklchViewIterator",
    "RgbView",
    "RgbViewIterator",
    # Typing
    "DartworkColor",
    "DartworkColormap",
]

# Register bundled color palettes with matplotlib on first import.
_ensure_colors_loaded()
