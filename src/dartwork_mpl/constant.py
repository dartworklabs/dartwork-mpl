"""Matplotlib 차트를 위한 표준 피규어 너비(Width) 상수 모듈.

이 모듈은 학술 논문 및 프레젠테이션에서 흔히 사용되는
표준화된 피규어 너비 상수들을 제공합니다.
"""

from .util import cm2in

__all__ = ["DW", "SW"]

# Single column figure width.
SW: float = cm2in(9)

# Double column figure width.
DW: float = cm2in(17)
